"""Validate public content and stable references using only the standard library."""
from datetime import date
import re
from urllib.parse import urlparse


PRESENTATION_TYPES = ("Oral", "Spotlight", "Poster")


def paper_id(paper):
    return paper["id"]


def validate_data(data):
    errors = []

    def require(obj, fields, label):
        for field in fields:
            if field not in obj or obj[field] in (None, ""):
                errors.append(f"{label}: missing {field}")

    def texts(obj, fields, label):
        for field in fields:
            if not isinstance(obj.get(field), str) or not obj[field].strip():
                errors.append(f"{label}: {field} must be nonempty text")

    def asset(value, label):
        if (not isinstance(value, str) or not value.startswith("assets/") or "\\" in value
                or any(part in ("", ".", "..") for part in value.split("/")) or urlparse(value).scheme):
            errors.append(label + ": requires a site-relative assets/ path")

    def url(value, label):
        if not isinstance(value, str) or urlparse(value).scheme != "https" or not urlparse(value).netloc:
            errors.append(label + ": URL must use https and include a host")

    def rich(value, label):
        if not isinstance(value, list) or not value:
            errors.append(label + ": requires text segments")
            return
        for segment in value:
            if (not isinstance(segment, dict) or not isinstance(segment.get("text"), str)
                    or set(segment) - {"text", "tag"} or segment.get("tag") not in (None, "b", "strong")):
                errors.append(label + ": invalid text segment")

    if not isinstance(data, dict):
        return ["content must be an object"]
    for field in ("meta", "homepage", "research", "papers", "members", "projects"):
        if field not in data:
            return ["missing top-level field: " + field]
    for field in ("meta", "homepage"):
        if not isinstance(data[field], dict):
            return [field + " must be an object"]
    for field in ("research", "papers", "members", "projects"):
        if not isinstance(data[field], list) or any(not isinstance(x, dict) for x in data[field]):
            return [field + " must be an array of objects"]

    ids = {}
    for table in ("research", "members", "papers", "projects"):
        values = [row.get("id") for row in data[table]]
        if any(not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", value) for value in values):
            errors.append(table + ": missing or invalid stable id")
        strings = [value for value in values if isinstance(value, str)]
        if len(strings) != len(set(strings)):
            errors.append(table + ": duplicate stable id")
        ids[table] = set(strings)

    for member in data["members"]:
        label = str(member.get("id", "member"))
        require(member, ("id", "name", "role", "status"), label)
        texts(member, ("name",), label)
        if member.get("role") not in ("postdoc", "phd", "master"):
            errors.append(label + ": invalid role")
        if member.get("status") not in ("current", "former"):
            errors.append(label + ": invalid status")
        if set(member) - {"id", "name", "role", "status", "entryYear", "url"}:
            errors.append(label + ": unsupported member fields; departure details are private")
        year = member.get("entryYear")
        if (year is not None or member.get("role") != "postdoc") and (type(year) is not int or not 1900 <= year <= 2100):
            errors.append(label + ": invalid entry year")
        if member.get("url"):
            url(member["url"], label + ": homepage")

    for paper in data["papers"]:
        label = str(paper.get("id", "paper"))
        require(paper, ("id", "name", "title", "authors", "venue", "year", "area", "summary", "url"), label)
        texts(paper, ("name", "title", "authors", "venue", "summary"), label)
        if not isinstance(paper.get("area"), str) or paper["area"] not in ids["research"]:
            errors.append(label + ": unknown research area")
        if type(paper.get("year")) is not int or not 1900 <= paper["year"] <= 2100:
            errors.append(label + ": invalid publication year")
        if not str(paper.get("id", "")).startswith("paper-"):
            errors.append(label + ": paper id must start with paper-")
        if "presentation" in paper and paper["presentation"] not in PRESENTATION_TYPES:
            errors.append(label + ": invalid presentation format")
        venue = paper.get("venue")
        if isinstance(venue, str) and venue.endswith(tuple(" · " + value for value in PRESENTATION_TYPES)):
            errors.append(label + ": keep presentation separate from venue")
        if paper.get("codeVisibility", "public") not in ("public", "private"):
            errors.append(label + ": invalid code visibility")
        for field in ("url", "code"):
            if paper.get(field):
                url(paper[field], label + ": " + field)
        if set(paper) & {"verification", "verificationNote", "codeNote"}:
            errors.append(label + ": keep verification notes in local records")
        corresponding = paper.get("correspondingAuthors", [])
        authors = paper.get("authors")
        if not isinstance(corresponding, list) or any(
            not isinstance(name, str) or not isinstance(authors, str) or name not in authors.split(", ")
            for name in corresponding
        ):
            errors.append(label + ": corresponding authors must be listed paper authors")
        if "chineseExplanationUrl" in paper:
            url(paper["chineseExplanationUrl"], label + ": Chinese explanation")
        if "coverage" in paper:
            errors.append(label + ": select one article for chineseExplanationUrl")
        if "publicationDetails" in paper:
            texts(paper, ("publicationDetails",), label)
        if paper.get("figure"):
            asset(paper["figure"], label + ": figure")

    def references(value, allowed, label):
        if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
            errors.append(label + ": references must be a list of ids")
            return
        if len(value) != len(set(value)):
            errors.append(label + ": duplicate reference")
        for ref in value:
            if ref not in allowed:
                errors.append(label + ": unknown reference " + ref)

    for group in data["research"]:
        label = str(group.get("id", "research"))
        require(group, ("title", "short", "en", "summary", "topics", "memberIds", "examples", "source"), label)
        texts(group, ("title", "short", "en", "summary"), label)
        references(group.get("memberIds"), ids["members"], label + ": members")
        references(group.get("examples"), ids["papers"], label + ": papers")
        if not isinstance(group.get("topics"), list) or any(not isinstance(x, str) for x in group.get("topics", [])):
            errors.append(label + ": topics must be text list")
        url(group.get("source"), label + ": learning resource")
    homepage = data["homepage"]
    if type(homepage.get("year")) is not int or not 1900 <= homepage["year"] <= 2100:
        errors.append("homepage: invalid selection year")
    references(homepage.get("legacyPaperAnchors"), ids["papers"], "homepage legacy anchors")
    for field in ("updates", "featured"):
        rows = homepage.get(field)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            errors.append("homepage " + field + ": requires array of objects")
            continue
        references([row.get("paper") for row in rows], ids["papers"], "homepage " + field)
        for row in rows:
            label = "homepage " + field
            if field == "updates" or "date" in row:
                value = row.get("date", "")
                try:
                    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}(?:-[0-9]{2})?", value):
                        raise ValueError
                    date.fromisoformat(value + "-01" if len(value) == 7 else value)
                except ValueError:
                    errors.append(label + ": invalid date")
            if "recognition" in row:
                texts(row, ("recognition",), label)
            if "label" in row or "format" in row:
                errors.append(label + ": use paper presentation or a separate recognition field")
            if "url" in row:
                errors.append(label + ": title links use the paper ID; put explainers in the paper record")

    month = r"[0-9]{4}\.(?:0[1-9]|1[0-2])"
    for project in data["projects"]:
        label = str(project.get("id", "project"))
        require(project, ("id", "title", "category"), label)
        texts(project, ("title",), label)
        if project.get("category") not in ("vertical", "horizontal"):
            errors.append(label + ": invalid project category")
        if "funding" in project:
            texts(project, ("funding",), label)
        if "period" in project:
            value = project["period"]
            if not isinstance(value, str) or not re.fullmatch(month + "—" + month, value):
                errors.append(label + ": period must use YYYY.MM—YYYY.MM")
            elif value[:7] > value[8:]:
                errors.append(label + ": project period ends before it starts")
        if "start" in project and (not isinstance(project["start"], str) or not re.fullmatch(month, project["start"])):
            errors.append(label + ": start must use YYYY.MM")
        if "url" in project:
            url(project["url"], "project url")

    meta = data["meta"]
    require(meta, ("description", "about", "contentUpdated", "lead", "contact", "identity", "links", "copy", "achievements"), "team")
    texts(meta, ("description", "about"), "team")
    try:
        date.fromisoformat(meta.get("contentUpdated", ""))
    except (ValueError, TypeError):
        errors.append("team: invalid contentUpdated date")
    nested = {
        "identity": ("shortName", "suffix", "name", "englishName", "affiliation", "location", "logo", "sidebarLogo", "copyrightYear"),
        "links": ("baseUrl", "organization", "scholar", "college"),
        "lead": ("name", "englishName", "url", "title", "photo", "position", "affiliations", "interests", "honor", "sidebarPosition", "bioAfterName"),
        "contact": ("email", "address", "admissionsUrl", "intro"),
        "copy": ("publicationsDescription",),
    }
    for key, fields in nested.items():
        if not isinstance(meta.get(key), dict):
            errors.append("team: " + key + " must be an object")
        else:
            require(meta[key], fields, "team " + key)
            texts(meta[key], [field for field in fields if field not in ("affiliation", "copyrightYear", "intro", "bioAfterName")], "team " + key)
    if isinstance(meta.get("identity"), dict):
        identity = meta["identity"]
        if not isinstance(identity.get("affiliation"), list) or not identity["affiliation"] or any(not isinstance(x, str) for x in identity.get("affiliation", [])):
            errors.append("team identity: affiliation must be a nonempty text list")
        if type(identity.get("copyrightYear")) is not int:
            errors.append("team identity: copyrightYear must be an integer")
        asset(identity.get("logo"), "team logo")
        asset(identity.get("sidebarLogo"), "sidebar logo")
    if isinstance(meta.get("lead"), dict):
        url(meta["lead"].get("url"), "lead url")
        rich(meta["lead"].get("bioAfterName"), "lead bio")
        asset(meta["lead"].get("photo"), "lead photo")
    if isinstance(meta.get("contact"), dict):
        contact = meta["contact"]
        url(contact.get("admissionsUrl"), "admissions url")
        rich(contact.get("intro"), "contact intro")
        for field in ("mastersAdmissionsUrl", "doctoralAdmissionsUrl"):
            if field in contact:
                url(contact[field], "team contact " + field)
        if "postdocNotice" in contact:
            notice = contact["postdocNotice"]
            if not isinstance(notice, dict):
                errors.append("team postdoc notice: must be an object")
            else:
                url(notice.get("url"), "team postdoc notice")
                try:
                    date.fromisoformat(notice.get("publishedOn", ""))
                except (TypeError, ValueError):
                    errors.append("team postdoc notice: invalid publishedOn date")
                texts(notice, [field for field in ("plannedPositions", "materials", "mailSubject") if field in notice],
                      "team postdoc notice")
                if "directions" in notice:
                    directions = notice["directions"]
                    if not isinstance(directions, list) or not directions or any(not isinstance(item, dict) for item in directions):
                        errors.append("team postdoc notice: directions must be a nonempty list of objects")
                    else:
                        for item in directions:
                            texts(item, ("title", "summary"), "team postdoc direction")
                if "experience" in notice:
                    experience = notice["experience"]
                    if not isinstance(experience, list) or not experience or any(not isinstance(item, str) or not item.strip() for item in experience):
                        errors.append("team postdoc notice: experience must be a nonempty list of text")
    if isinstance(meta.get("links"), dict):
        for key in nested["links"]:
            url(meta["links"].get(key), "team link " + key)
        if not str(meta["links"].get("baseUrl", "")).endswith("/"):
            errors.append("team links: baseUrl must end with /")
    if "wechat" in meta:
        account = meta["wechat"]
        if not isinstance(account, dict):
            errors.append("team wechat: must be an object")
        else:
            texts(account, ("name",), "team wechat")
            asset(account.get("qrCode"), "team wechat QR code")
    if not isinstance(meta.get("achievements"), list) or any(not isinstance(x, dict) or not x.get("title") or not x.get("text") for x in meta.get("achievements", [])):
        errors.append("team achievements: requires title and text")
    return errors
