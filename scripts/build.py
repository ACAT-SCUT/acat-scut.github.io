"""Generate the ACAT website using only Python's standard library."""
from pathlib import Path
import hashlib
import html
from content import load_data
from validate import paper_id

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site"
DATA = load_data()
GROUPS, PAPERS, MEMBERS = DATA["research"], DATA["papers"], DATA["members"]
META = DATA["meta"]
LEAD, CONTACT = META["lead"], META["contact"]
IDENTITY, LINKS, COPY = META["identity"], META["links"], META["copy"]
MEMBER_MAP = {m["id"]: m for m in MEMBERS}
PAPER_MAP = {p["id"]: p for p in PAPERS}
# Text reading normalizes CRLF, so a Windows checkout has the same cache version.
STYLE_VERSION = hashlib.sha256((OUT / "styles.css").read_text(encoding="utf-8").encode("utf-8")).hexdigest()[:10]


def e(value):
    return html.escape(str(value), quote=True)


def a(url, label, cls=""):
    return f'<a class="{e(cls)}" href="{e(url)}">{label}</a>'


def rich(segments):
    return "".join(f'<{part["tag"]}>{e(part["text"])}</{part["tag"]}>' if part.get("tag") else e(part["text"]) for part in segments)


def paper_href(p):
    return "/publications.html#" + paper_id(p)


def heading(title, english="", extra=""):
    subtitle = f"<span>{e(english)}</span>" if english else ""
    return f'<div class="section-heading"><h2>{e(title)}{subtitle}</h2>{extra}</div>'


def pagehead(kicker, title, description):
    return f'<header class="page-head"><p class="kicker">{e(kicker)}</p><h1>{e(title)}</h1><p>{e(description)}</p></header>'


def shell(title, active, body):
    nav = [("index.html", "团队简介", "home"), ("research.html", "研究方向", "research"),
           ("publications.html", "论文成果", "publications"), ("people.html", "团队成员", "people"),
           ("index.html#join", "联系与招生", "join")]
    menu = "".join(f'<a href="/{url}"' + (' aria-current="page"' if key == active else "") + f'>{label}</a>' for url, label, key in nav)
    localnav = '<div class="local-nav"><a href="#research">研究方向</a><a href="#updates">成果动态</a><a href="#papers">代表成果</a></div>' if active == "home" else ""
    filename = "" if active == "home" else active + ".html"
    return f"""<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#0f3d75"><title>{e(title)} · {e(IDENTITY['shortName'])} {e(IDENTITY['suffix'])}</title>
<meta name="description" content="{e(META['description'])}">
<meta property="og:title" content="{e(title)} · ACAT @ SCUT">
<meta property="og:description" content="{e(META['description'])}">
<meta property="og:type" content="website">
<link rel="canonical" href="{e(LINKS['baseUrl'])}{filename}">
<link rel="icon" href="/{e(IDENTITY['logo'])}"><link rel="stylesheet" href="/styles.css?v={STYLE_VERSION}">
<script src="/script.js" defer></script></head>
<body><a class="skip-link" href="#main">跳到正文</a>
<div class="page-shell"><aside class="sidebar" aria-label="实验室概览">
<div class="lab-identity"><a href="/" aria-label="{e(IDENTITY['shortName'])} 首页"><img class="lab-logo" src="/{e(IDENTITY['logo'])}" width="146" height="146" alt="{e(IDENTITY['shortName'])} {e(IDENTITY['name'])}标志"></a>
<div><a class="lab-name" href="/">{e(IDENTITY['shortName'])} <span>{e(IDENTITY['suffix'])}</span></a><p class="lab-chinese">{e(IDENTITY['name'])}</p>
<p class="affiliation">{'<br>'.join(e(x) for x in IDENTITY['affiliation'])}</p><p class="location">{e(IDENTITY['location'])}</p></div></div>
<div class="sidebar-lead"><img src="/{e(LEAD['photo'])}" width="44" height="44" alt="{e(LEAD['name'])}{e(LEAD['title'])}">
<div>{a(LEAD['url'], e(LEAD['name']) + ' <span>' + e(LEAD['englishName']) + '</span>')}<p>{e(LEAD['sidebarPosition'])}</p></div></div>
<nav class="site-nav" aria-label="网站导航">{menu}</nav>{localnav}
<div class="sidebar-links">{a('mailto:' + CONTACT['email'], e(CONTACT['email']))}
<a href="{e(LINKS['organization'])}">GitHub Organization ↗</a>
<a href="{e(LINKS['scholar'])}">Google Scholar ↗</a>
<a href="{e(LINKS['college'])}">学院主页 ↗</a></div></aside>
<div class="page-content"><main id="main" tabindex="-1">{body}</main>
<footer><span>© {IDENTITY['copyrightYear']} {e(IDENTITY['shortName'])} {e(IDENTITY['suffix'])}</span><a href="#main">回到顶部 ↑</a></footer>
</div></div></body></html>"""


def write(filename, text):
    (OUT / filename).write_text(text, encoding="utf-8", newline="\n")


def paper_links(p):
    links = a(p["url"], "Paper")
    if p.get("code") and p.get("codeVisibility", "public") == "public":
        links += a(p["code"], "Code")
    return '<div class="paper-links">' + links + "</div>"


def paperlist(items, figures=False):
    rows = []
    for p in items:
        area = next(g["short"] for g in GROUPS if g["id"] == p["area"])
        figure = p.get("figure") if figures else None
        img = ""
        if figure:
            src = "/" + figure.lstrip("/")
            img = f'<a class="paper-figure" href="{e(src)}" aria-label="查看 {e(p["name"])} 方法图原图"><img src="{e(src)}" alt="{e(p["name"])} 论文图示" width="180" height="110" loading="lazy"><span>方法图 ↗</span></a>'
        title = e(p["title"])
        if ":" in title:
            prefix, rest = title.split(":", 1)
            title = f"<strong>{prefix}:</strong>{rest}"
        title = a(p["url"], title)
        authors = '<p class="authors">' + e(p["authors"]).replace(e(LEAD["englishName"]), "<strong>" + e(LEAD["englishName"]) + "</strong>") + "</p>"
        rows.append(f'<article class="paper" id="{paper_id(p)}"><div class="paper-top"><span class="venue">{e(p["venue"])}</span><span class="paper-year">{p["year"]}</span><span class="paper-area">{e(area)}</span></div><div class="paper-body {"has-figure" if figure else ""}">{img}<div><h3>{title}</h3>{authors}<p class="paper-summary">{e(p["summary"])}</p>{paper_links(p)}</div></div></article>')
    return "".join(rows)


def member_link(m, detailed=False):
    return a(m["url"] if detailed and m.get("url") else "/people.html#member-" + m["id"], e(m["name"]))


def group_people(g, status):
    return "、".join(member_link(MEMBER_MAP[ref]) for ref in g["memberIds"] if MEMBER_MAP[ref]["status"] == status)


def group_people_block(g):
    current, former = group_people(g, "current"), group_people(g, "former")
    result = f'<p class="group-members"><strong>当前成员：</strong>{current}</p>' if current else ""
    if former:
        result += f'<p class="group-members former-members"><strong>往届关联：</strong>{former}</p>'
    return result


def leadbio():
    return f'<p class="lead-bio">{a(LEAD["url"], "<strong>" + e(LEAD["name"]) + e(LEAD["title"]) + "</strong>")}{rich(LEAD["bioAfterName"])}</p>'


def home():
    about = e(META["about"]).replace(e(IDENTITY["shortName"]), "<strong>" + e(IDENTITY["shortName"]) + "</strong>", 1)
    recognition = "、".join(f'<a href="{paper_href(PAPER_MAP[item["paper"]])}">{rich(item["label"])}</a>' for item in DATA["homepage"]["recognition"])
    intro = f"""<section class="about" id="about">
<p class="kicker">ABOUT / 团队简介</p><h1>{e(IDENTITY['name'])}</h1>
<p class="english-name">{e(IDENTITY['englishName'])}</p><p>{about}</p>{leadbio()}
<p class="recognition"><strong>代表成果：</strong>{recognition}。</p></section>"""
    research = '<section class="section" id="research">' + heading("研究方向", "Research", a("/research.html", "详细介绍 →", "more-link")) + '<div class="research-overview">'
    for g in GROUPS:
        examples = " / ".join(a(paper_href(PAPER_MAP[key]), e(PAPER_MAP[key]["name"])) for key in g["examples"])
        topics = " · ".join(e(topic) for topic in g["topics"][:2])
        research += f'<div class="research-row"><h3>{a("/research.html#" + g["id"], e(g["title"]))}</h3><p>{topics}<span class="research-examples">{examples}</span></p></div>'
    research += "</div></section>"
    updates = '<section class="section" id="updates">' + heading("成果动态", "Highlights") + '<ul class="news-list">'
    for item in DATA["homepage"]["updates"]:
        p = PAPER_MAP[item["paper"]]
        updates += f'<li><span class="news-year">{p["year"]}</span><p>{a(paper_href(p), "<strong>" + e(p["name"]) + "</strong>")} · {e(item["summary"])}。<b>{e(p["venue"])}</b></p></li>'
    updates += "</ul></section>"
    selected = [PAPER_MAP[key] for key in DATA["homepage"]["featured"]]
    featured = '<section class="section" id="papers">' + heading("代表论文", "Selected Publications", a("/publications.html", f"全部精选论文（{len(PAPERS)}） →", "more-link")) + paperlist(selected, figures=True) + "</section>"
    join = '<section class="section contact" id="join">' + heading("联系与招生", "Contact")
    join += f'<p>{rich(CONTACT["intro"])}</p><p><strong>联系导师：</strong>{a(LEAD["url"], e(LEAD["name"]) + e(LEAD["title"]))}　 <strong>邮箱：</strong>{a("mailto:" + CONTACT["email"], e(CONTACT["email"]))}<br><strong>地址：</strong>{e(CONTACT["address"])}</p><p class="note">{e(CONTACT["admissionsNote"])}{a(CONTACT["admissionsUrl"], "研究生招生信息 ↗")}</p></section>'
    return intro + research + updates + featured + join


def research_page():
    body = pagehead("RESEARCH", "研究方向", COPY["researchDescription"])
    body += '<nav class="page-index" aria-label="研究方向定位">' + "".join(a("#" + g["id"], e(g["short"])) for g in GROUPS) + "</nav>"
    for g in GROUPS:
        body += f'<section class="section research-detail" id="{g["id"]}">' + heading(g["title"], g["en"])
        body += f'<p>{e(g["summary"])}</p><ul class="topics">' + "".join(f"<li>{e(t)}</li>" for t in g["topics"]) + "</ul>"
        body += '<div class="research-related"><strong>相关成果</strong>' + "".join(a(paper_href(p), e(p["name"]) + f' <small>{e(p["venue"])} · {p["year"]}</small>') for p in PAPERS if p["area"] == g["id"]) + "</div>"
        body += group_people_block(g) + '<div class="research-links">' + a(g["source"], "学习资源 ↗") + a("/people.html#members-" + g["id"], "方向成员索引 →") + "</div></section>"
    body += '<section class="section">' + heading("科研项目", "Selected Projects") + '<div class="project-list">'
    for project in DATA["projects"]:
        title = a(project["url"], e(project["title"])) if project.get("url") else e(project["title"])
        body += f'<article><span>{e(project["period"])}</span><div><strong>{title}</strong><small>{e(project["note"])}</small></div></article>'
    return body + '</div><p class="note">来源：' + a(LEAD["url"], e(LEAD["name"]) + e(COPY["projectSourceLabel"])) + e(COPY["projectNote"]) + "</p></section>"


def faculty():
    body = '<section class="faculty">' + heading("团队负责人", "Team Lead")
    body += f'<div class="faculty-intro"><img src="/{e(LEAD["photo"])}" width="110" height="110" alt="{e(LEAD["name"])}{e(LEAD["title"])}"><div><h3>{e(LEAD["name"])} <span>{e(LEAD["englishName"])}</span></h3><p>{e(LEAD["position"])}<br>{e(LEAD["affiliations"])}</p><div class="paper-links">{a(LEAD["url"], "个人主页")}{a(LINKS["scholar"], "Google Scholar")}{a("mailto:" + CONTACT["email"], "Email")}</div></div></div>'
    body += f'<p>主要研究兴趣包括{e(LEAD["interests"])}。{e(LEAD["honor"])}</p><ul class="achievements">'
    return body + "".join(f'<li><strong>{e(x["title"])}</strong>：{e(x["text"])}</li>' for x in META["achievements"]) + "</ul></section>"


def member_section(status, role):
    items = sorted((m for m in MEMBERS if m["status"] == status and m["role"] == role), key=lambda m: -m.get("entryYear", 0))
    if not items:
        return ""
    label = {"postdoc": "博士后", "phd": "博士生", "master": "硕士生"}[role]
    if status == "former":
        label = {"postdoc": "博士后", "phd": "博士", "master": "硕士"}[role]
    result = f'<section class="member-group" id="{status}-{role}"><h3>{label}<span class="count">{len(items)}</span></h3><div class="member-list">'
    for m in items:
        name = a(m["url"], e(m["name"])) if m.get("url") else e(m["name"])
        result += f'<article class="member-card" id="member-{m["id"]}"><h4>{name}</h4>'
        if m.get("entryYear"):
            result += f'<p class="member-year">{m["entryYear"]} 级</p>'
        related = [g for g in GROUPS if m["id"] in g["memberIds"]]
        if related:
            result += '<div class="member-tags">' + "".join(a("/research.html#" + g["id"], e(g["short"])) for g in related) + "</div>"
        result += "</article>"
    return result + "</div></section>"


def people_page():
    body = pagehead("PEOPLE", "团队成员", COPY["peopleDescription"])
    body += '<nav class="page-index" aria-label="成员分类定位"><a href="#current">当前成员</a><a href="#current-phd">博士生</a><a href="#current-master">硕士生</a><a href="#former">往届成员</a><a href="#by-research">按方向查找</a></nav>' + faculty()
    for status, title, english in (("current", "当前成员", "Current Members"), ("former", "往届成员", "Former Members")):
        body += f'<section class="section roster-section" id="{status}">' + heading(title, english)
        if status == "former":
            body += '<p class="note">' + e(COPY['formerNote']) + '</p>'
        body += "".join(member_section(status, role) for role in ("postdoc", "phd", "master")) + "</section>"
    body += '<section class="section direction-index" id="by-research">' + heading("方向成员索引", "By Research")
    for g in GROUPS:
        body += f'<section class="direction-group" id="members-{g["id"]}"><h3>{a("/research.html#" + g["id"], e(g["title"]))}</h3>{group_people_block(g)}</section>'
    return body + "</section>"


def publications_page():
    body = pagehead("PUBLICATIONS", "论文成果", COPY["publicationsDescription"])
    body += '<nav class="topic-index" aria-label="按研究方向定位论文">'
    for g in GROUPS:
        items = sorted((p for p in PAPERS if p["area"] == g["id"]), key=lambda p: -p["year"])
        body += "<div><strong>" + e(g["short"]) + "</strong><span>" + "".join(a("#" + paper_id(p), e(p.get("short", p["name"])) + f' <small>{p["year"]}</small>') for p in items) + "</span></div>"
    body += '</nav><p class="note">完整论文目录请查阅 <a href="' + e(LINKS['scholar']) + '">Google Scholar ↗</a>。</p>'
    for year in sorted({p["year"] for p in PAPERS}, reverse=True):
        body += '<section class="section year-group">' + heading(str(year)) + paperlist([p for p in PAPERS if p["year"] == year]) + "</section>"
    return body



pages = [
    ("index.html", IDENTITY["name"], "home", home()),
    ("research.html", "研究方向", "research", research_page()),
    ("people.html", "团队成员", "people", people_page()),
    ("publications.html", "论文成果", "publications", publications_page()),
    ("404.html", "页面未找到", "404", pagehead("404", "页面未找到", "这个地址没有对应的页面，请返回首页继续浏览。") + a("/", "返回首页 →")),
]
OUT.mkdir(exist_ok=True)
for filename, title, active, body in pages:
    write(filename, shell(title, active, body))
# Compatibility only: the former sources URL is not a content page.
write("sources.html", '<!doctype html>\n<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>页面已迁移</title><meta http-equiv="refresh" content="0;url=/"><link rel="canonical" href="' + e(LINKS["baseUrl"]) + '"><meta name="robots" content="noindex"></head><body><h1>页面已迁移</h1><p><a href="/">前往团队首页</a></p></body></html>\n')
write(".nojekyll", "")
write("robots.txt", "User-agent: *\nAllow: /\nSitemap: " + LINKS["baseUrl"] + "sitemap.xml\n")
write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f'<url><loc>{e(LINKS["baseUrl"])}{f}</loc><lastmod>{META["contentUpdated"]}</lastmod></url>' for f in ("", "research.html", "people.html", "publications.html")) + "</urlset>\n")
print(f"Built {len(pages)} pages with {len(MEMBERS)} members.")
