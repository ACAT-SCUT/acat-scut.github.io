"""Render public member cohorts with stable person and experience anchors."""
from collections import defaultdict
from html import escape


ROLES = {"postdoc": "博士后", "phd": "博士", "master": "硕士"}
ROLE_ORDER = tuple(ROLES)
ALUMNI = {"id": "former", "title": "往届成员", "short": "往届成员"}


def section_id(group):
    return "former" if group is ALUMNI else "members-" + group["id"]


def render_index(groups):
    items = "\n".join(
        f'<li><a href="#{escape(section_id(group))}">{escape(group["short"])}</a></li>'
        for group in (*groups, ALUMNI)
    )
    return f'<nav class="page-index member-index page-rail" aria-label="成员目录"><h2 class="rail-title">页内目录</h2><ul>\n{items}\n</ul></nav>'


def render_groups(people, experiences, groups):
    members = {person["id"]: person for person in people}
    used = {"by-research"}

    def anchor(id):
        if id in used:
            return ""
        used.add(id)
        return f'<span class="anchor-target" id="{escape(id)}"></span>'

    def entry(experience):
        member = members[experience["memberId"]]
        person_id = "member-" + member["id"]
        experience_id = "experience-" + experience["id"]
        attrs = f' data-member-id="{escape(member["id"])}" data-experience-id="{escape(experience["id"])}"'
        if member["displayExperienceId"] == experience["id"] and person_id not in used:
            attrs += f' id="{escape(person_id)}"'
            used.add(person_id)
        name = escape(member["name"])
        if member.get("url"):
            name = f'<a href="{escape(member["url"])}">{name}</a>'
        return f'<li class="member-entry"{attrs}>{anchor(experience_id)}{name}</li>'

    def cohort_order(experience):
        person = members[experience["memberId"]]
        return person.get("sortName", person["name"]).casefold(), person["id"], experience["id"]

    def roster_section(group, experiences):
        id = section_id(group)
        used.add(id)
        former = group is ALUMNI
        status = "former" if former else "current"
        title = escape(group["title"])
        if not former:
            title = f'<a href="/research.html#{escape(group["id"])}">{title}</a>'
        rows = [f'<section class="section member-direction" id="{id}" tabindex="-1"><h3>{title}</h3>']
        for role in ROLE_ORDER:
            by_year = defaultdict(list)
            for experience in experiences:
                if experience["role"] == role:
                    by_year[experience.get("entryYear")].append(experience)
            if not by_year:
                continue
            rows.append(f'<section class="member-role" data-role="{role}">'
                        f'{anchor(status + "-" + role)}<h4>{ROLES[role]}</h4><dl class="member-cohorts">')
            for year, cohort in sorted(by_year.items(), key=lambda item: (item[0] is None, item[0] or 0)):
                label = "年份未补充" if year is None else str(year) + ("年入站" if role == "postdoc" else "级")
                cohort.sort(key=cohort_order)
                members_html = "".join(entry(experience) for experience in cohort)
                rows.append(f'<div class="member-cohort" data-year="{year if year is not None else ""}">'
                            f'<dt>{label}</dt><dd><ul class="member-names">{members_html}</ul></dd></div>')
            rows.append('</dl></section>')
        rows.append('</section>')
        return "\n".join(rows)

    current = [experience for experience in experiences if experience["status"] == "current"]
    former = [experience for experience in experiences if experience["status"] == "former"]
    sections = [roster_section(group, [exp for exp in current if group["id"] in exp["researchIds"]]) for group in groups]
    sections.append(roster_section(ALUMNI, former))
    expected = {"current", "members-unassigned"}
    expected.update(f"{status}-{role}" for status in ("current", "former") for role in ROLE_ORDER)
    expected.update("member-" + person["id"] for person in people)
    expected.update("experience-" + experience["id"] for experience in experiences)
    fallback = "".join(anchor(id) for id in sorted(expected - used))
    heading = '<div class="section-heading"><h2>研究成员<span lang="en">Research Members</span></h2></div>'
    return '<section class="section" id="by-research">\n' + heading + fallback + "\n".join(sections) + '\n</section>'
