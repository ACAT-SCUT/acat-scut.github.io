from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
import json
root=Path(__file__).resolve().parents[1]/'site'
class Page(HTMLParser):
 def __init__(self,text):
  super().__init__();self.refs=[];self.ids=[];self.headings=0;self.feed(text)
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id' in a:self.ids.append(a['id'])
  if tag=='h1':self.headings+=1
  for attr in ['href','src']:
   if attr in a:self.refs.append(a[attr])
errors=[]
for f in root.glob('*.html'):
 p=Page(f.read_text())
 if len(set(p.ids))!=len(p.ids):errors.append(f'{f.name}: duplicate ids')
 if p.headings!=1:errors.append(f'{f.name}: h1 count')
 for ref in p.refs:
  u=urlparse(ref)
  if u.scheme or u.netloc:continue
  target=(root/unquote(u.path).lstrip('/')) if u.path else f
  if target.is_dir():target=target/'index.html'
  if not target.exists():errors.append(f'{f.name}: missing {ref}')
  elif u.fragment and target.suffix=='.html' and u.fragment not in Page(target.read_text()).ids:errors.append(f'{f.name}: missing anchor {ref}')
print(json.dumps({'pages':len(list(root.glob('*.html'))),'errors':errors},ensure_ascii=False))
raise SystemExit(bool(errors))
