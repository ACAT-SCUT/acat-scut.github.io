# ACAT @ SCUT

华南理工大学先进计算体系结构团队网站。

正式站：https://acat-scut.github.io/

`site/` 是 GitHub Pages 发布的静态源文件，可直接编辑各页。

- `index.html`：团队简介、研究方向、最新动态、代表性成果、招生与联系。
- `research.html` 和 `projects.html`：研究方向与科研项目。
- `publications.html`：论文完整题名、作者与原文链接。新增条目时，保留已有论文锚点，并更新相关方向目录。
- `people.html`：团队负责人、在校成员与往届成员。成员状态以团队确认的名录为准。
- `join.html`：招生及应聘入口。
- `sources.html` 和 `assets/CREDITS.md`：资料和图片来源。

本地验证：

```sh
python3 scripts/check.py
python3 -m http.server 8765 --directory site
```

浏览器访问 http://localhost:8765/ 。提交到 `main` 后，GitHub Actions 检查站内链接并发布 `site/`。
