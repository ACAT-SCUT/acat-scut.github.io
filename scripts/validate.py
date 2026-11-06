"""Validate public content and stable references using only the standard library."""
from datetime import date
import re
from urllib.parse import urlparse


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
        if paper.get("codeVisibility", "public") not in ("public", "private"):
            errors.append(label + ": invalid code visibility")
        for field in ("url", "code"):
            if paper.get(field):
                url(paper[field], label + ": " + field)
        if set(paper) & {"verification", "verificationNote", "codeNote"}:
            errors.append(label + ": keep verification notes in local records")
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
    references(homepage.get("featured"), ids["papers"], "homepage featured")
    for field in ("updates", "recognition"):
        rows = homepage.get(field)
        if not isinstance(rows, list) or any(not isinstance(x, dict) for x in rows):
            errors.append("homepage " + field + ": requires array of objects")
            continue
        for row in rows:
            references([row.get("paper")], ids["papers"], "homepage " + field)
            if field == "updates":
                require(row, ("summary",), "homepage updates")
                texts(row, ("summary",), "homepage updates")
            else:
                rich(row.get("label"), "homepage recognition")
    for project in data["projects"]:
        require(project, ("id", "title", "period", "note"), "project")
        texts(project, ("title", "period", "note"), "project")
        if project.get("url"):
            url(project["url"], "project url")

    meta = data["meta"]
    require(meta, ("description", "about", "contentUpdated", "lead", "contact", "identity", "links", "copy", "achievements"), "team")
    texts(meta, ("description", "about"), "team")
    try:
        date.fromisoformat(meta.get("contentUpdated", ""))
    except (ValueError, TypeError):
        errors.append("team: invalid contentUpdated date")
    nested = {
        "identity": ("shortName", "suffix", "name", "englishName", "affiliation", "location", "logo", "copyrightYear"),
        "links": ("baseUrl", "organization", "scholar", "college"),
        "lead": ("name", "englishName", "url", "title", "photo", "position", "affiliations", "interests", "honor", "sidebarPosition", "bioAfterName"),
        "contact": ("email", "address", "admissionsUrl", "intro", "admissionsNote"),
        "copy": ("researchDescription", "peopleDescription", "publicationsDescription", "formerNote", "projectSourceLabel", "projectNote"),
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
    if isinstance(meta.get("lead"), dict):
        url(meta["lead"].get("url"), "lead url")
        rich(meta["lead"].get("bioAfterName"), "lead bio")
        asset(meta["lead"].get("photo"), "lead photo")
    if isinstance(meta.get("contact"), dict):
        url(meta["contact"].get("admissionsUrl"), "admissions url")
        rich(meta["contact"].get("intro"), "contact intro")
    if isinstance(meta.get("links"), dict):
        for key in nested["links"]:
            url(meta["links"].get(key), "team link " + key)
        if not str(meta["links"].get("baseUrl", "")).endswith("/"):
            errors.append("team links: baseUrl must end with /")
    if not isinstance(meta.get("achievements"), list) or any(not isinstance(x, dict) or not x.get("title") or not x.get("text") for x in meta.get("achievements", [])):
        errors.append("team achievements: requires title and text")
    return errors
