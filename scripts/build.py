"""Generate the ACAT website using only Python's standard library."""
import hashlib
from html import escape
from pathlib import Path

from content import load_data
from member_render import render_index, render_groups


OUT = Path(__file__).resolve().parents[1] / "site"
DATA = load_data()
GROUPS, PAPERS = DATA["research"], DATA["papers"]
PAPER_MAP = {p["id"]: p for p in PAPERS}
META = DATA["meta"]
LEAD, CONTACT = META["lead"], META["contact"]
IDENTITY, LINKS = META["identity"], META["links"]

PAGES = (
    ("index.html", "团队简介", "home"),
    ("research.html", "研究方向", "research"),
    ("publications.html", "论文成果", "publications"),
    ("projects.html", "科研项目", "projects"),
    ("people.html", "团队成员", "people"),
)
UTILITY_ICONS = {
    "faculty": '<path d="M3 21h18M4 21V11l8-6 8 6v10M10 21v-5h4v5m-2-11v1"/>',
    "scholar": '<path d="m2 10 10-5 10 5-10 5-10-5Zm4 2v4c3 3 9 3 12 0v-4m4-2v6"/>',
    "github": '<circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="5" r="2"/><path d="M6 7v10m12-10a5 5 0 0 1-5 5H6"/>',
    "email": '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m2 7 10 6 10-6"/>',
}
PUBLICATION_ICONS = {
    "arrow-up-to-line": ("M5 3h14", "m18 13-6-6-6 6", "M12 7v14"),
    "file-text": (
        "M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z",
        "M14 2v5a1 1 0 0 0 1 1h5", "M10 9H8", "M16 13H8", "M16 17H8",
    ),
    "code-xml": ("m18 16 4-4-4-4", "m6 8-4 4 4 4", "m14.5 4-5 16"),
}


def e(value):
    return escape(str(value), quote=True)


def a(url, label, cls=""):
    style = f' class="{e(cls)}"' if cls else ""
    return f'<a href="{e(url)}"{style}>{label}</a>'


def rich(segments):
    return "".join(f'<{part["tag"]}>{e(part["text"])}</{part["tag"]}>' if part.get("tag") else e(part["text"]) for part in segments)


def icon(markup, size, css_class="site-icon"):
    return (
        f'<svg class="{css_class}" width="{size}" height="{size}" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true" focusable="false">{markup}</svg>'
    )


def publication_icon(name, size=16):
    return icon("".join(f'<path d="{shape}"/>' for shape in PUBLICATION_ICONS[name]), size)


def heading(title, english="", destination=""):
    subtitle = f'<span lang="en">{e(english)}</span>' if english else ""
    action = f'<a class="home-detail" href="{e(destination)}" aria-label="查看详情：{e(title)}">查看详情</a>' if destination else ""
    return f'<div class="section-heading"><h2>{e(title)}{subtitle}</h2>{action}</div>'


def page_head(kicker, title, introduction=""):
    scope = f"<p>{e(introduction)}</p>" if introduction else ""
    return f'<header class="page-head"><p class="kicker">{e(kicker)}</p><h1>{e(title)}</h1>{scope}</header>'


def linked_asset(name, prefix):
    # Normalize line endings so both Windows and Linux produce the same cache key.
    content = (OUT / name).read_text(encoding="utf-8")
    version = hashlib.sha256(content.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}{name}?v={version}"


def shell(title, active, body):
    prefix = "/" if active == "404" else ""
    nav = (*PAGES, ("index.html#join", "加入我们", "join"))
    menu = "\n".join(
        f'<a href="{prefix}{url}"' + (' aria-current="page"' if key == active else "") + f'>{label}</a>'
        for url, label, key in nav
    )
    utility = (
        ("faculty", LINKS["college"], LEAD["name"] + " · 学院个人主页", ""),
        ("scholar", LINKS["scholar"], LEAD["name"] + " · Google Scholar", "utility-mobile"),
        ("github", LINKS["organization"], IDENTITY["shortName"] + " · GitHub", "utility-mobile"),
        ("email", "mailto:" + CONTACT["email"], CONTACT["email"], ""),
    )
    utilities = "\n".join(
        a(url, icon(UTILITY_ICONS[key], 16, "utility-icon") + f"<span>{e(label)}</span>", css_class)
        for key, url, label, css_class in utility
    )
    page_styles = {"home": ("home.css",), "people": ("people.css",)}
    styles = ("styles.css", "pages.css", *page_styles.get(active, ()), "sidebar.css", "logo.css", "utilities.css", "layout.css")
    if active == "publications":
        styles += ("publication-layout.css",)
    styles_html = "\n".join(f'<link rel="stylesheet" href="{linked_asset(name, prefix)}">' for name in styles)
    scripts = {"people": "member-navigation.js", "publications": "publication-navigation.js"}
    script = f'\n<script src="{linked_asset(scripts[active], prefix)}" defer></script>' if active in scripts else ""
    page_class = {"publications": " publication-page", "people": " people-page"}.get(active, "")
    canonical = "" if active == "404" else f'\n<link rel="canonical" href="{e(LINKS["baseUrl"])}{"" if active == "home" else active + ".html"}">'
    brand = f'{e(IDENTITY["shortName"])} {e(IDENTITY["suffix"])}'
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0f3d75">
<meta name="description" content="{e(META['description'])}">
<meta property="og:title" content="{e(title)} · {brand}">
<meta property="og:description" content="{e(META['description'])}">
<meta property="og:type" content="website">
<title>{e(title)} · {brand}</title>{canonical}
<link rel="icon" href="{prefix}{e(IDENTITY['logo'])}">
{styles_html}{script}
</head>
<body class="back-to-top-page{page_class}">
<div id="page-top" tabindex="-1" role="region" aria-label="页首"></div>
<a class="skip-link" href="#main">跳到正文</a>
<div class="page-shell">
<aside class="sidebar" aria-label="ACAT 团队概览">
  <div class="lab-identity">
    <a href="{prefix}index.html" aria-label="{e(IDENTITY['shortName'])} 首页"><img class="lab-logo" src="{prefix}{e(IDENTITY['sidebarLogo'])}" width="146" height="146" alt="{e(IDENTITY['shortName'])} {e(IDENTITY['name'])}标志"></a>
    <div><a class="lab-name" href="{prefix}index.html">{e(IDENTITY['shortName'])} <span>{e(IDENTITY['suffix'])}</span></a>
    <p class="lab-chinese">{e(IDENTITY['name'])}</p>
    <p class="affiliation">{'<br>'.join(e(x) for x in IDENTITY['affiliation'])}</p>
    <p class="location">{e(IDENTITY['location'])}</p></div>
  </div>
  <div class="sidebar-lead">
    <img src="{prefix}{e(LEAD['photo'])}" width="42" height="42" alt="{e(LEAD['name'])}{e(LEAD['title'])}">
    <div>{a(LEAD['url'], e(LEAD['name']) + ' <span>' + e(LEAD['englishName']) + '</span>')}
    <p>{e(LEAD['sidebarPosition'])}</p></div>
  </div>
  <nav class="site-nav" aria-label="网站导航">
{menu}
  </nav>
  <div class="sidebar-links">
{utilities}
  </div>
</aside>
<div class="page-content">
<main id="main" tabindex="-1">
{body}
</main>
<footer><span>© {IDENTITY['copyrightYear']} {brand}</span></footer>
</div>
</div>
<a class="back-to-top" href="#page-top" aria-label="回到顶部">{publication_icon("arrow-up-to-line", 20)}</a>
</body>
</html>
"""


def venue_parts(paper):
    venue, separator, format_label = paper["venue"].rpartition(" · ")
    if separator and format_label in ("Spotlight", "Oral", "Poster"):
        return venue, format_label
    return paper["venue"], ""


def venue_badges(venue, format_label=""):
    presentation = f' <span class="venue venue-presentation">{e(format_label)}</span>' if format_label else ""
    return f'<span class="venue">{e(venue)}</span>{presentation}'


def publication_authors(paper):
    corresponding = set(paper.get("correspondingAuthors", ()))
    return ", ".join(
        f'<span class="corresponding-author">{e(name)}<sup aria-hidden="true">*</sup>'
        '<span class="paper-sr-only">（通讯作者）</span></span>' if name in corresponding else e(name)
        for name in paper["authors"].split(", ")
    )


def article(paper):
    figure_html = ""
    if figure := paper.get("figure"):
        figure_html = (
            f'<a class="paper-figure" href="{e(figure)}" aria-label="查看 {e(paper["name"])} 方法图原图">'
            f'<img src="{e(figure)}" alt="{e(paper["name"])} 论文方法图" loading="lazy"></a>'
        )
    links = a(paper["url"], publication_icon("file-text") + " Paper")
    if paper.get("code") and paper.get("codeVisibility", "public") == "public":
        links += a(paper["code"], publication_icon("code-xml") + " Code")
    layout = "paper-body has-figure" if figure_html else "paper-body"
    details = paper.get("publicationDetails")
    detail_html = f'<p class="publication-detail">{e(details)}</p>' if details and details not in paper["summary"] else ""
    return f"""<article class="paper" id="{e(paper['id'])}">
  <div class="paper-top">{venue_badges(*venue_parts(paper))}</div>
  <h4 class="paper-title">{e(paper['title'])}</h4>
  <div class="{layout}"><div class="paper-copy">
    <p class="authors">{publication_authors(paper)}</p><p class="paper-summary">{e(paper['summary'])}</p>
    {detail_html}<div class="paper-links">{links}</div>
  </div>{figure_html}</div>
</article>"""


def home_rows(items, *, recent=False):
    rows = []
    for item in items:
        paper = PAPER_MAP[item["paper"]]
        date = item.get("date", str(paper["year"]))
        url = item.get("url", f'publications.html#{paper["id"]}')
        venue, _ = venue_parts(paper)
        ident = "" if recent else f' id="{e(paper["id"])}"'
        rows.append(
            f'<li{ident}><div class="achievement-meta"><time datetime="{e(date)}">{e(date[:7].replace("-", "."))}</time>'
            f'{venue_badges(item.get("label", venue), item.get("format"))}</div>'
            f'{a(url, e(paper["title"]), "achievement-title")}</li>'
        )
    return '<ul class="home-achievements">\n' + "\n".join(rows) + "\n</ul>"


def home():
    short = e(IDENTITY["shortName"])
    about = e(META["about"]).replace(short, f"<strong>{short}</strong>", 1)
    lead = a(LEAD["url"], f'<strong>{e(LEAD["name"])}{e(LEAD["title"])}</strong>')
    intro = f"""<section class="about" id="about">
  <p class="kicker">ABOUT / 团队简介</p><h1>{e(IDENTITY['name'])}</h1>
  <p class="english-name">{e(IDENTITY['englishName'])}</p><p>{about}</p>
  <p class="lead-bio">{lead}{rich(LEAD['bioAfterName'])}</p>
</section>"""
    research = '<section class="section" id="research">' + heading("研究方向", "Research", "research.html") + '<div class="research-overview">'
    for group in GROUPS:
        topics = " · ".join(e(topic) for topic in group["topics"][:2])
        research += f'<div class="research-row"><h3>{e(group["title"])}</h3><p>{topics}</p></div>'
    research += "</div></section>"

    selection = DATA["homepage"]
    items = (item for item in selection["updates"] if item["date"][:4] == str(selection["year"]))
    latest = sorted(items, key=lambda item: item["date"], reverse=True)[:5]
    featured = selection["featured"]
    aliases = "".join(
        f'<span class="preserved-anchor" id="{e(ident)}"></span>'
        for ident in selection["legacyPaperAnchors"] if ident not in {row["paper"] for row in featured}
    )
    updates = '<span class="preserved-anchor" id="updates"></span>'
    if latest:
        updates = '<section class="section" id="updates">' + heading("最新动态", "Latest News") + home_rows(latest, recent=True) + "</section>"
    highlights = '<span class="preserved-anchor" id="papers"></span>' + aliases
    if featured:
        highlights = '<section class="section" id="papers">' + aliases + heading("代表性成果", "Selected Results", "publications.html") + home_rows(featured) + "</section>"
    join = '<section class="section contact" id="join">' + heading("加入我们", "Join Us")
    join += (f'<p>{rich(CONTACT["intro"])}</p><p>{a("mailto:" + CONTACT["email"], "联系团队")} · '
             f'{a(CONTACT["admissionsUrl"], "研究生招生信息")}<br>{e(CONTACT["address"])}</p>'
             f'<p class="note">{e(CONTACT["admissionsNote"])}</p></section>')
    return "\n".join((intro, research, updates, highlights, join))


def research_page():
    body = [page_head("RESEARCH", "研究方向")]
    for group in GROUPS:
        key = e(group["id"])
        topics = "".join(f"<li>{e(topic)}</li>" for topic in group["topics"])
        links = (a(f"publications.html#papers-{key}", "查看该方向论文"),
                 a(f"people.html#members-{key}", "查看方向成员"), a(group["source"], "学习资源"))
        body.append(
            f'<section class="section research-detail" id="{key}">{heading(group["title"], group["en"])}'
            f'<p>{e(group["summary"])}</p><ul class="topics">{topics}</ul>'
            f'<div class="research-links">{" ".join(links)}</div></section>'
        )
    return "\n".join(body)


def publication_rail(by_direction):
    rows = []
    for direction in GROUPS:
        key = direction["id"]
        years = by_direction[key]
        if not years:
            continue
        groups = []
        for year, papers in years.items():
            year_link = a(f"#papers-{key}-{year}", e(year), "publication-rail-year")
            entries = "".join(f'<li>{a("#" + paper["id"], e(paper.get("short") or paper["name"]))}</li>' for paper in papers)
            groups.append(f'<li>{year_link}<ul>{entries}</ul></li>')
        initial = " open" if not rows else ""
        rows.append(
            f'<details data-direction="papers-{e(key)}"{initial}>'
            f'<summary>{e(direction["short"])}</summary><ul>{"".join(groups)}</ul></details>'
        )
    return f'<nav class="publication-rail page-rail" aria-label="论文页内目录"><h2 class="rail-title">页内目录</h2>{"".join(rows)}</nav>'


def publications_page():
    body = page_head("PUBLICATIONS", "论文成果", META["copy"]["publicationsDescription"])
    by_direction = {group["id"]: {} for group in GROUPS}
    for paper in sorted(PAPERS, key=lambda paper: -paper["year"]):
        by_direction[paper["area"]].setdefault(paper["year"], []).append(paper)
    body += '<nav class="publication-overview" aria-label="近年代表论文概览"><div class="publication-overview-grid">'
    for direction in GROUPS:
        key = direction["id"]
        years = by_direction[key]
        if not years:
            continue
        index = []
        for year, entries in years.items():
            for paper in entries:
                label = f'{e(paper.get("short") or paper["name"])} <time datetime="{year}">{year}</time>'
                index.append(f'<li>{a("#" + paper["id"], label)}</li>')
        body += (
            '<div class="publication-overview-row">'
            f'{a("#papers-" + key, e(direction["short"]), "publication-overview-direction")}'
            f'<ul>{"".join(index)}</ul></div>'
        )
    body += "</div></nav>" + publication_rail(by_direction) + '<div class="publication-list">'
    for direction in GROUPS:
        key = e(direction["id"])
        body += f'<section class="section publication-direction" id="papers-{key}">' + heading(direction["title"], direction["en"])
        for year, entries in by_direction[direction["id"]].items():
            body += f'<section class="publication-year" id="papers-{key}-{year}"><h3 class="publication-year-title">{year}</h3>'
            body += "\n".join(article(paper) for paper in entries) + "</section>"
        body += "</section>"
    return body + "</div>"


def project_order(project):
    start = project.get("start") or project.get("period", "").partition("—")[0]
    return -int(start.replace(".", "") or "0"), project["id"]


def projects_page():
    body = page_head("Research Projects", "科研项目")
    projects = sorted(DATA["projects"], key=project_order)
    for category, title in (("vertical", "纵向课题"), ("horizontal", "横向课题")):
        body += f'<section class="section project-section" id="{category}">{heading(title)}<div class="project-list project-groups">'
        for project in projects:
            if project["category"] != category:
                continue
            name = e(project["title"])
            if project.get("url"):
                name = a(project["url"], name)
            metadata = " ".join(f'<span class="project-{field}">{e(project[field])}</span>' for field in ("funding", "period") if project.get(field))
            detail = f'<p class="project-metadata">{metadata}</p>' if metadata else ""
            body += f'<article id="{e(project["id"])}"><h3>{name}</h3>{detail}</article>'
        body += "</div></section>"
    return body


def faculty():
    links = (a(LEAD["url"], "个人主页"), a(LINKS["scholar"], "Google Scholar"), a("mailto:" + CONTACT["email"], "Email"))
    return (
        '<section class="faculty">' + heading("团队负责人", "Team Lead")
        + f'<div class="faculty-intro"><img src="{e(LEAD["photo"])}" width="110" height="110" alt="{e(LEAD["name"])}">'
        f'<div><h3>{e(LEAD["name"])} <span lang="en">{e(LEAD["englishName"])}</span></h3>'
        f'<p>{e(LEAD["position"])}<br>{e(LEAD["affiliations"])}</p><div class="paper-links">{" ".join(links)}</div></div></div>'
        f'<p>主要研究兴趣包括{e(LEAD["interests"])}。{e(LEAD["honor"])}</p><ul class="achievements">'
        + "".join(f'<li><strong>{e(row["title"])}</strong>：{e(row["text"])}</li>' for row in META["achievements"])
        + "</ul></section>"
    )


def people_page():
    return (
        page_head("PEOPLE", "团队成员") + render_index(GROUPS) + faculty()
        + render_groups(DATA["memberRecords"], DATA["memberExperiences"], GROUPS)
    )


def write(filename, text):
    (OUT / filename).write_text(text, encoding="utf-8", newline="\n")


def main():
    renderers = {"home": home, "research": research_page, "publications": publications_page, "projects": projects_page, "people": people_page}
    for filename, title, active in PAGES:
        write(filename, shell(IDENTITY["name"] if active == "home" else title, active, renderers[active]()))
    write("404.html", shell("页面未找到", "404", page_head("404", "页面未找到", "这个地址没有对应的页面，请返回首页继续浏览。") + a("/", "返回首页 →")))
    # Preserve the historical redirect without advertising or indexing it.
    write("sources.html", '<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>页面已迁移</title><meta http-equiv="refresh" content="0;url=/"><link rel="canonical" href="' + e(LINKS["baseUrl"]) + '"><meta name="robots" content="noindex"></head><body><h1>页面已迁移</h1><p><a href="/">前往团队首页</a></p></body></html>\n')
    write(".nojekyll", "")
    write("robots.txt", "User-agent: *\nAllow: /\nSitemap: " + LINKS["baseUrl"] + "sitemap.xml\n")
    locations = ("" if active == "home" else filename for filename, _, active in PAGES)
    entries = "".join(f'<url><loc>{e(LINKS["baseUrl"])}{name}</loc><lastmod>{META["contentUpdated"]}</lastmod></url>' for name in locations)
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + entries + "</urlset>\n")
    print(f"Built {len(PAGES)} content pages and the 404 page with {len(DATA['memberRecords'])} member records.")


if __name__ == "__main__":
    main()
