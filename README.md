# ACAT @ SCUT

华南理工大学先进计算体系结构团队网站，服务于学术展示与招生交流。ACAT 由林伟伟教授带领，团队介绍、研究、成果、成员及联系入口采用统一的团队口径。页面安排与建设进度见路线图。

[访问网站](https://acat-scut.github.io/) · [GitHub Pages 审核预览](https://acat-scut.github.io/acat-preview/) · [数据维护说明](content/README.md) · [建设需求与进度](ROADMAP.md) · [AI 协作规则](AGENTS.md)

## 快速开始

需要 Python 3.11 或以上版本，无第三方包、npm 或数据库服务。在项目根目录执行：

```sh
python -B -X utf8 scripts/build.py
python -B -X utf8 scripts/check.py
python -B -X utf8 -m unittest discover -s scripts -p "test_*.py"
python -m http.server 8765 --bind 127.0.0.1 --directory site
```

浏览器打开 <http://127.0.0.1:8765/>，按 Ctrl+C 停止预览。如果终端找不到 `python`，使用已安装解释器的绝对路径替代即可，不需要安装项目依赖。

## 项目结构

本地成员维护演示可用下列命令启动，浏览器打开 <http://127.0.0.1:8766/>；使用虚构资料，不修改正式名册或页面。试用步骤和数据位置见[演示说明](scripts/member_demo/README.md)。

```sh
python -B -X utf8 scripts/member_demo/server.py --port 8766
```

```text
content/       六类业务内容、七份 JSON（人员与经历分表）、数据字典和申请模板
scripts/       数据读取、导入、静态构建、检查与测试
site/          生成页面、样式和正式素材（素材署名见 assets/CREDITS.md）
.github/       PR 检查及 GitHub Pages 发布流程
ROADMAP.md     建设需求、阶段范围、验收条件与进度
AGENTS.md      AI 协作规则
docs/          本地交付文档与历史报告，不进入仓库
.local/        原始资料、填写结果、核查证据及缓存，不进入仓库
```

## 常用维护

| 要修改的内容 | 入口 |
|---|---|
| 团队、负责人、联系方式和荣誉 | `content/team.json` |
| 方向简介和学习资源 | `content/research.json` |
| 成员姓名、主页、拼音排序键和主经历引用 | `content/members.json` |
| 各段经历的身份、年份、状态、毕业确认和方向 | `content/member-experiences.json` |
| 论文书目、摘要、方法图和链接 | `content/papers.json` |
| 纵向、横向项目及公开链接 | `content/projects.json` |
| 首页最新动态、代表性成果和历史锚点 | `content/homepage.json` |

修改数据后构建并检查，不直接编辑生成的 HTML。成员、方向和论文通过固定 ID 关联；更改名称或论文年份时保留 ID。具体字段、填写职责及新增记录方法见[数据字典](content/README.md)。

成员通过[简短变更申请](content/templates/member-requests.csv)分散填写，再由维护者逐行标记“通过”后导入：

```sh
python -B -X utf8 scripts/import_members.py .local/成员维护/已审核.csv
python -B -X utf8 scripts/import_members.py .local/成员维护/已审核.csv --apply
```

第一条只预览，第二条写入数据；资料或 CSV 改变后需要重新预览。之后仍需构建、检查和审核。导入结果包含可恢复的批次编号，恢复与填写细则见[数据维护说明](content/README.md)。旧成员 CSV 不直接写入新结构。通用模板可导入团队自行选择的共享表格，本项目未绑定云服务。

## 构建与发布

- PR 自动运行数据及导入测试、构建和站内链接检查，不发布。
- 推送 `main` 或手动运行发布工作流会在检查通过后部署 `site/` 到 GitHub Pages。
- 本地导入、构建和共享表格编辑不会直接更新线上网站。
- 正式数据、素材、脚本和生成页面均纳入版本管理；文本使用 UTF-8、LF，连续构建应稳定。

本站全部预渲染，导航和内容关联使用原生链接，无 JavaScript 也可使用。材料与核查底稿只在本地保留，保存在项目内不等于已备份。

当前进行可持续维护的初步建设，资料按需补充。后续布局、适配及验收需求统一见 [ROADMAP](ROADMAP.md)。
