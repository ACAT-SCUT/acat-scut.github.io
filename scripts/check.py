"""Check source references and generated pages without contacting external sites."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse
import json

from validate import paper_id, validate_data
from content import load_data

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
data = load_data()
errors = validate_data(data)


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.refs, self.ids, self.members = [], [], []
        self.headings = 0
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "h1":
            self.headings += 1
        if "member-card" in attrs.get("class", "").split():
            self.members.append(attrs.get("id"))
        for field in ("href", "src"):
            if field in attrs:
                self.refs.append(attrs[field])


pages = {p.name: Page(p.read_text(encoding="utf-8")) for p in SITE.glob("*.html")}
for filename, page in pages.items():
    if len(page.ids) != len(set(page.ids)):
        errors.append(filename + ": duplicate ids")
    if page.headings != 1:
        errors.append(filename + ": requires exactly one h1")
    for ref in page.refs:
        url = urlparse(ref)
        if url.scheme or url.netloc:
            continue
        target = SITE / unquote(url.path).lstrip("/") if url.path else SITE / filename
        if target.is_dir():
            target = target / "index.html"
        if not target.exists():
            errors.append(f"{filename}: missing file {ref}")
        elif url.fragment and target.suffix == ".html":
            target_page = pages.get(target.name)
            if target_page is None or url.fragment not in target_page.ids:
                errors.append(f"{filename}: missing anchor {ref}")
    for paper in data["papers"]:
        if paper.get("codeVisibility") == "private" and paper.get("code") in page.refs:
            errors.append(f"{filename}: private code link exposed for {paper['name']}")
people = pages.get("people.html")
if people is None:
    errors.append("missing people.html")
else:
    expected = {"member-" + m["id"] for m in data["members"]}
    if set(people.members) != expected or len(people.members) != len(expected):
        errors.append("people.html: member cards do not match the source roster exactly")
    for group in data["research"]:
        if "members-" + group["id"] not in people.ids:
            errors.append("people.html: missing legacy direction anchor " + group["id"])
publications = pages.get("publications.html")
if publications is None or any(paper_id(p) not in publications.ids for p in data["papers"]):
    errors.append("publications.html: missing paper anchor")
for filename in ("index.html", "research.html", "people.html", "publications.html", "404.html"):
    if filename not in pages:
        errors.append("missing " + filename)
    elif "/sources.html" in pages[filename].refs:
        errors.append(filename + ": sources page must not be advertised")
redirect = SITE / "sources.html"
if not redirect.exists() or 'content="0;url=/"' not in redirect.read_text(encoding="utf-8"):
    errors.append("sources.html: missing home redirect")
if "sources.html" in (SITE / "sitemap.xml").read_text(encoding="utf-8"):
    errors.append("sitemap: sources redirect must not be indexed")
print(json.dumps({"pages": len(pages), "members": len(data["members"]), "errors": errors}, ensure_ascii=False))
raise SystemExit(bool(errors))
