# ACAT @ SCUT

华南理工大学先进计算体系结构团队网站。

Website: https://acat-scut.github.io/

## 内容维护

- `content/site.json`：五个研究方向、研究成员、精选论文与来源。
- `scripts/build.py`：共享页面模板、导师介绍、科研项目和联系信息。
- `site/styles.css`：响应式样式。
- `site/script.js`：保留的脚本入口；导航使用原生链接，无脚本依赖。
- `site/assets/`：团队原有标志、导师公开头像。

修改后运行：

```sh
python3 scripts/build.py
python3 scripts/check.py
python3 -m http.server 8765 --directory site
```

浏览器访问 http://localhost:8765/ 。提交到 `main` 后，GitHub Actions 自动构建与发布 `site/` 目录。无需 npm、第三方字体服务或数据库。

## 资料说明

资料核对日期：2026-09-12。具体来源见网站 `sources.html` 和 `content/site.json`。

- 教师信息来自导师本人公开主页；未推断其他教师归属。
- 成员按现有组织介绍分组，不推断当前在读身份与毕业去向。
- 未沿用旧页面的师生人数、引用量等动态统计。
- SparseTSF 会议版与期刊扩展版分开列出，使用各自标题与作者。
- Concord 已有出版 DOI，正式卷期为 2026 年 10 月。
- 论文列表为精选，不是完整成果目录；招生以学校及导师通知为准。
- 团队徽标与导师照片仍归原权利人所有，不对图片另行授予许可。

页面全部预渲染，采用左侧团队资料与右侧连续正文的紧凑学术布局；桌面和手机导航均使用原生链接，禁用 JavaScript 也可完整使用。站点不收集访问者信息。
