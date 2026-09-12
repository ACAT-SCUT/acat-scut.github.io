from pathlib import Path
import json, html
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'site'
OUT.mkdir(exist_ok=True)
DATA=json.loads((ROOT/'content/site.json').read_text())
GROUPS=DATA['research']; PAPERS=DATA['papers']
def e(s): return html.escape(str(s),quote=True)
def a(url,label,cls=''): return f'<a class="{cls}" href="{e(url)}">{label}</a>'
def sectionhead(title,en='',extra=''):
 return f'<div class="section-heading"><h2>{title} <span>{en}</span></h2>{extra}</div>'
def shell(title,active,body):
 nav=[('index.html','团队简介','home'),('research.html','研究方向','research'),('publications.html','论文成果','publications'),('people.html','团队成员','people'),('index.html#join','联系与招生','join')]
 menu=''.join(f'<a href="{url}" {"aria-current=page" if key==active else ""}>{label}</a>' for url,label,key in nav)
 localnav='<div class="local-nav"><a href="#research">研究方向</a><a href="#updates">近期成果</a><a href="#papers">代表论文</a></div>' if active=='home' else ''
 return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="theme-color" content="#0f3d75"><title>{title} · ACAT @ SCUT</title><meta name="description" content="华南理工大学先进计算体系结构团队。团队负责人林伟伟教授，研究云计算与绿色计算、算力调度、大模型、时间序列与边缘智能。"><link rel="canonical" href="https://acat-scut.github.io/{'' if active=='home' else active+'.html'}"><link rel="icon" href="assets/acat-logo.png"><link rel="stylesheet" href="styles.css"><script src="script.js" defer></script></head><body><a class="skip-link" href="#main">跳到正文</a><div class="page-shell"><aside class="sidebar" aria-label="实验室概览"><div class="lab-identity"><a href="index.html"><img class="lab-logo" src="assets/acat-logo.png" width="146" height="146" alt="ACAT 先进计算体系结构团队标志"></a><div><a class="lab-name" href="index.html">ACAT <span>@ SCUT</span></a><p class="lab-chinese">先进计算体系结构团队</p><p class="affiliation">华南理工大学<br>计算机科学与工程学院</p><p class="location">Guangzhou, China</p></div></div><div class="sidebar-lead"><img src="assets/weiwei-lin.jpg" width="44" height="44" alt="林伟伟教授"><div><a href="https://www.scholat.com/linweiwei">林伟伟 <span>Weiwei Lin</span></a><p>团队负责人 · 教授 · 博士生导师</p></div></div><nav class="site-nav" aria-label="网站导航">{menu}</nav>{localnav}<div class="sidebar-links"><a href="mailto:linww@scut.edu.cn">linww@scut.edu.cn</a><a href="https://github.com/ACAT-SCUT">GitHub Organization ↗</a><a href="https://scholar.google.com/citations?user=IWsha94AAAAJ">Google Scholar ↗</a><a href="https://www2.scut.edu.cn/cs/">学院主页 ↗</a></div></aside><div class="page-content"><main id="main">{body}</main><footer><span>© 2026 ACAT @ SCUT</span><a href="sources.html">资料来源 · 2026.09.12 更新</a><a href="#main">回到顶部 ↑</a></footer></div></div></body></html>'''
def paperlist(items,figures=False):
 out=''
 for p in items:
  figure=p.get('figure') if figures else None
  title=e(p['title'])
  if ':' in title:
   prefix,rest=title.split(':',1);title=f'<strong>{prefix}:</strong>{rest}'
  out+=f'<article class="paper"><div class="paper-top"><span class="venue">{e(p["venue"])}</span><span class="paper-year">{p["year"]}</span><span class="paper-area">{e(next(g["short"] for g in GROUPS if g["id"]==p["area"]))}</span></div><div class="paper-body {"has-figure" if figure else ""}">'
  if figure: out+=f'<a class="paper-figure" href="{e(p["url"])}"><img src="{e(figure)}" alt="{e(p["name"])} 论文图示" width="180" height="105" loading="lazy"></a>'
  out+=f'<div><h3>{a(p["url"],title)}</h3><p class="authors">{e(p["authors"])}</p><p class="paper-summary">{e(p["summary"])}</p><div class="paper-links">{a(p["url"],"Paper")}{a(p["code"],"Code") if p.get("code") else ""}</div></div></div></article>'
 return out
def peoplelinks(group):
 return '、'.join(a(p['url'],e(p['name'])) if p.get('url') else e(p['name']) for p in group['people'])
def leadbio():
 return '''<p><a href="https://www.scholat.com/linweiwei"><strong>林伟伟教授</strong></a>担任团队负责人，博士生导师、鹏城实验室双聘研究员，<strong>CCF 杰出会员、IEEE 高级会员</strong>。研究工作贯穿云计算调度与节能、算力能效优化、大模型与边缘智能、时序预测等方向。</p>'''
def projects():
 return '''<div class="project-list"><article><span>2025—2028</span><div><strong>异构算力系统能效模型及仿真系统研究</strong><small>山东联合基金 · 2025.05—2028.04</small></div></article><article><span>2025—2028</span><div><strong>面向智算中心的 AI 算力综合管理平台及关键技术研究与应用示范</strong><small>广西重点研发 · 2025.03—2028.02</small></div></article><article><span>2025—2026</span><div><strong>AI 集群中的作业优先级调度和碎片整理</strong><small>华为云合作项目 · 2025.09—2026.04</small></div></article></div>'''
intro='''<section class="about" id="about"><p class="kicker">ABOUT / 团队简介</p><h1>先进计算体系结构团队</h1><p class="english-name">Advanced Computing Architecture Team</p><p><strong>ACAT</strong> 是华南理工大学计算机科学与工程学院的科研团队，前身为 2005 年成立的计算机系统结构研究所。我们聚焦<strong>云计算与绿色计算、算力与大模型优化、物联网与边缘智能</strong>，研究面向真实应用的高效、智能与可持续计算技术。</p>'''+leadbio()+'''<p class="recognition"><strong>代表成果：</strong>ICML 2024 <b>Oral</b>、NeurIPS 2024 <b>Spotlight</b>、IEEE <b>TPAMI</b> 与 <b>TPDS</b>、AAAI 2026 等。<a href="publications.html">论文与代码 →</a></p></section>'''
research='<section class="section" id="research">'+sectionhead('研究方向','Research',a('research.html','详细介绍 →','more-link'))+'<div class="research-overview">'
for g in GROUPS:
 research+=f'<div class="research-row"><h3>{a("research.html#"+g["id"],e(g["title"]))}</h3><p>{" · ".join(e(x) for x in g["topics"][:3])}</p></div>'
research+='</div></section>'
updates='<section class="section" id="updates">'+sectionhead('近期成果','Recent Work')+'<ul class="news-list">'
for p,label in [(PAPERS[0],'2026'),(PAPERS[1],'2026'),(PAPERS[2],'2026'),(PAPERS[6],'2026')]:
 short={'Concord':'GPU 集群干扰建模与非对称作业组合','ExFairS':'面向用户体验的大模型推理公平调度','NoSPF':'云数据中心服务器非平稳功耗预测','Double-Bench':'文档检索增强生成的评测基准'}[p['name']]
 updates+=f'<li><span class="news-year">{label}</span><p>{a(p["url"],"<strong>"+e(p["name"])+"</strong>")} · {short}。<b>{e(p["venue"])}</b></p></li>'
updates+='</ul></section>'
selected=[PAPERS[i] for i in [3,4,5,8,14,9]]
homepapers='<section class="section" id="papers">'+sectionhead('代表论文','Selected Publications',a('publications.html','全部精选论文（16） →','more-link'))+paperlist(selected,True)+'</section>'
join='''<section class="section contact" id="join">'''+sectionhead('联系与招生','Contact')+'''<p>欢迎对<strong>云计算、人工智能与先进计算系统</strong>感兴趣的同学，以及寻求学术交流与科研合作的研究者联系团队。</p><p><strong>联系导师：</strong><a href="https://www.scholat.com/linweiwei">林伟伟教授</a>　 <strong>邮箱：</strong><a href="mailto:linww@scut.edu.cn">linww@scut.edu.cn</a><br><strong>地址：</strong>广州市大学城 · 华南理工大学计算机学院 B3 栋</p><p class="note">招生要求、名额与时间安排，以学校及导师最新通知为准。<a href="https://yz.scut.edu.cn/">研究生招生信息 ↗</a></p></section>'''
(OUT/'index.html').write_text(shell('先进计算体系结构团队','home',intro+research+updates+homepapers+join))
def pagehead(k,title,description):return f'<div class="page-head"><p class="kicker">{k}</p><h1>{title}</h1><p>{description}</p></div>'
rbody=pagehead('RESEARCH','研究方向','围绕云端算力、智能模型与边缘设备，开展计算系统与算法的协同研究。')
for i,g in enumerate(GROUPS):
 rbody+=f'<section class="section research-detail" id="{g["id"]}">'+sectionhead(g['title'],g['en'])+f'<p>{e(g["summary"])}</p><ul class="topics">'+''.join(f'<li>{e(t)}</li>' for t in g['topics'])+'</ul><div class="research-related"><strong>相关成果</strong>'+''.join(a(p['url'],f'{e(p["name"])} <small>{e(p["venue"])} · {p["year"]}</small>') for p in PAPERS if p['area']==g['id'])+f'</div><p class="group-members"><strong>研究成员：</strong>{peoplelinks(g)}</p>'+a(g['source'],'学习资源与完整研究资料 ↗','more-link')+'</section>'
rbody+='<section class="section">'+sectionhead('科研项目','Selected Projects')+projects()+'<p class="note">来源：<a href="https://www.scholat.com/linweiwei">林伟伟教授公开主页</a>，列出部分项目及计划周期。</p></section>'
(OUT/'research.html').write_text(shell('研究方向','research',rbody))
pbody=pagehead('PEOPLE','团队成员','按研究方向整理的团队公开成员目录。')+'<section class="faculty">'+sectionhead('团队负责人','Team Lead')+'<div class="faculty-intro"><img src="assets/weiwei-lin.jpg" width="110" height="110" alt="林伟伟教授"><div><h3>林伟伟 <span>Weiwei Lin</span></h3><p>华南理工大学教授 · 博士生导师<br>鹏城实验室双聘研究员 · CCF 杰出会员 · IEEE 高级会员</p><div class="paper-links"><a href="https://www.scholat.com/linweiwei">个人主页</a><a href="https://scholar.google.com/citations?user=IWsha94AAAAJ">Google Scholar</a><a href="mailto:linww@scut.edu.cn">Email</a></div></div></div><p>主要研究兴趣包括云计算调度优化与节能、算力能效建模与优化、大模型与边缘智能、时序预测建模与应用。2021—2025 年连续入选斯坦福大学全球前 2% 顶尖科学家榜单。</p><ul class="achievements"><li><strong>广东省科技进步奖二等奖（2020）</strong>：“云计算调度优化技术”，排名第一。</li><li><strong>中国国际大学生创新大赛金奖（2023、2024）</strong>：作为第一指导老师，指导学生获产业命题赛道总决赛金奖。</li><li><strong>国家标准 GB 43630-2023</strong>：参与制定《塔式和机架式服务器能效限定值及能效等级》。</li></ul></section><section class="section">'+sectionhead('研究成员','Research Members')+'<p class="note">依据团队公开目录分组；成员当前身份与毕业去向以个人主页为准。</p>'
for g in GROUPS:
 pbody+=f'<section class="member-group"><h3>{e(g["title"])}</h3><div class="member-list">'+''.join(a(p['url'],e(p['name']),'member') if p.get('url') else f'<span class="member">{e(p["name"])}</span>' for p in g['people'])+'</div></section>'
pbody+='</section>'
(OUT/'people.html').write_text(shell('团队成员','people',pbody))
pubbody=pagehead('PUBLICATIONS','论文成果','精选近年代表成果；会议版与期刊扩展版分别列出。')+'<p class="note">完整论文目录请查阅 <a href="https://scholar.google.com/citations?user=IWsha94AAAAJ">Google Scholar ↗</a>。论文题名、年份与作者依原文或作者资料核对。</p>'
for year in sorted({p['year'] for p in PAPERS},reverse=True):
 pubbody+=f'<section class="section year-group">'+sectionhead(str(year))+paperlist([p for p in PAPERS if p['year']==year])+'</section>'
(OUT/'publications.html').write_text(shell('论文成果','publications',pubbody))
sbody=pagehead('SOURCES','资料来源','内容核实日期：2026 年 9 月 12 日。')+'<section class="section prose">'+sectionhead('内容依据')+'<p>团队介绍及研究成员以实验室公开组织资料为基础，导师信息参考本人主页，论文优先使用出版方、作者论文与项目仓库。</p><ul>'+''.join(f'<li>{a(x["url"],e(x["name"]))}<p>{e(x["note"])}</p></li>' for x in DATA['sources'])+'</ul>'+sectionhead('内容说明')+'<p>论文列表为精选，并非完整成果目录。预印本年份、在线发表年份与正式卷期年份可能不同，以论文链接为准。Concord 已有 DOI，正式卷期为 2026 年 10 月。</p><p>成员分组依据组织公开目录，不推断当前在读身份或毕业去向；尚未核实完整教师名录，故仅单独展示公开确认的团队负责人。旧介绍中的人数、引用量等动态统计未直接沿用。招生以学校及导师通知为准。</p></section>'
(OUT/'sources.html').write_text(shell('资料来源','sources',sbody))
(OUT/'404.html').write_text(shell('页面未找到','404',pagehead('404','页面未找到','请返回首页继续浏览。')+a('/','返回首页 →')))
(OUT/'.nojekyll').touch()
(OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: https://acat-scut.github.io/sitemap.xml\n')
(OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>https://acat-scut.github.io/{f}</loc><lastmod>2026-09-12</lastmod></url>' for f in ['','research.html','people.html','publications.html','sources.html'])+'</urlset>')
print('Built 6 pages.')
