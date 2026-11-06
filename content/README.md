# 数据维护与填写说明

[项目指南](../README.md) · [建设需求](../ROADMAP.md) · [成员 CSV 模板](templates/members.csv)

## 数据分工

六份 JSON 是公开内容的唯一维护来源。`scripts/content.py` 统一读取并验证，构建不抓取外部数据、不改变核查日期。以下字段列出了当前全部维护接口；只读派生内容无需手填。

| 文件 | 必填字段 | 可选字段及说明 | 维护者 |
|---|---|---|---|
| `team.json` | `contentUpdated`、`description`、`about`、`lead`、`contact`、`achievements`、`identity`、`links`、`copy` | 各子对象见下表；荣誉允许空数组 | 团队指定维护者 |
| `research.json` | 每行 `id`、`title`、`short`、`en`、`summary`、`topics`、`memberIds`、`examples`、`source` | `source` 是公开学习资源链接；成员和例子允许空数组 | 方向负责人建议，维护者审核 |
| `members.json` | 每行 `id`、`name`、`role`、`status`；硕博须有 `entryYear` | `url` 为 HTTPS 主页；博士后可省略 `entryYear` | 学生自填，维护者审核 |
| `papers.json` | 每行 `id`、`name`、`title`、`authors`、`venue`、`year`、`area`、`summary`、`url` | `short` 简称、`code` 代码地址、`codeVisibility`（默认 `public`，私有填 `private`）、`figure` 方法图路径、`publicationDetails` 正式出版补充信息 | 作者或方向负责人建议，维护者审核 |
| `projects.json` | 每行 `id`、`title`、`period`、`note` | `url`：可公开的 HTTPS 项目页；无链接时不显示按钮 | 项目相关人员提供，维护者审核 |
| `homepage.json` | `featured`、`updates`、`recognition` | 允许空数组；首页推荐完全由人工选取 | 团队指定维护者 |

`team.json` 子对象：

| 子对象 | 字段与用途 |
|---|---|
| `identity` | `shortName`、`suffix`、`name`、`englishName`、`affiliation`（按行文本数组）、`location`、`logo`（相对 site 路径）、`copyrightYear` |
| `lead` | `name`、`englishName`、`url`、`title`、`photo`、`position`、`affiliations`、`interests`、`honor`、`sidebarPosition`、`bioAfterName`（姓名链接后的简介片段） |
| `contact` | `email`、`address`、`admissionsUrl`、`intro`（欢迎语片段）、`admissionsNote` |
| `links` | `baseUrl`（站点绝对根地址，末尾 `/`）、`organization`、`scholar`、`college` |
| `achievements` | 荣誉列表，每项 `title`、`text`；团队与个人荣誉不混用 |
| `copy` | `researchDescription`、`peopleDescription`、`publicationsDescription`、`formerNote`、`projectSourceLabel`、`projectNote`，供现有页面复用 |

片段是 `[{"text": "文字"}, {"text": "重点", "tag": "strong"}]`，`tag` 只可省略或为 `strong`／`b`，不填写 HTML。模板负责转义和排版。

`homepage.json`：`featured` 是论文 ID 数组；`updates` 每项为 `paper` 和人工撰写的 `summary`；`recognition` 每项为 `paper` 和片段数组 `label`。三者只引用论文，不重复维护书目。方向页的 `examples` 同样引用论文 ID。

## ID、关系与人工判断

- 现有成员 `m001` 等和方向 `power`、`scheduling`、`llm`、`ts`、`fl` 的 ID 不变。新增成员由维护者分配未使用的 ID；姓名不是主键，允许同名。
- 论文 ID 为已固定的页面锚点，如 `paper-sparsetsf-2026`。新增论文由维护者分配唯一的 `paper-` 开头 ID；改题名或年份时不改 ID。会议与期刊扩展版分别建记录。
- 项目使用独立 ID，如 `project-001`；数组顺序决定同年论文、方向及项目的展示顺序。
- 成员归属只保存在 `research[].memberIds`，允许跨方向和暂未归属。成员页反向索引由此生成；导入器把填写的方向 ID 转换为这份关系，不在成员表复制。
- `role` 为 `postdoc`／`phd`／`master`；`status` 为 `current`／`former`。往届不等于取得学位；身份和状态由人审核，不按年级自动推断。
- `contentUpdated` 是本次公开内容实际修改日，由维护者更新，不是全站资料核实日。导入和构建不会自动改它。
- 页面内计数、分组、关联、站点地图和样式缓存版本自动生成。论文级别、公开状态、项目进展和首页推荐由人工决定。

## 学生填写与审核导入

将空白 CSV 模板复制到 `.local/成员维护/`，也可将表头导入共享云表格，成员各填自己的一行。当前不绑定任何云服务，访问权限由团队管理。填写结果不放进 `content/` 或公开仓库。

| CSV 列 | 填写规则 |
|---|---|
| `action` | 修改现有人填 `update`（空白也按 update）；新增必须明确填 `add` |
| `id` | 必填，由维护者提供；拼错的未知 ID 不会自动新增 |
| `name` | 姓名；新增必填，修改时空白保留原值 |
| `role` | `postdoc`／`phd`／`master`，新增必填 |
| `status` | `current`／`former`，新增必填，维护者审核 |
| `entryYear` | 四位入学年级整数，硕博必填；不填离组日期 |
| `url` | 自愿填写的公开 HTTPS 个人主页 |
| `researchIds` | 建议方向 ID，多个用英文分号分隔，如 `power;ts`；维护者审核 |

只需提供 `id` 及要修改的列；模板完整表头可直接使用。空白单元格保留原值；缺失行保留整条记录。`__CLEAR__` 仅用于明确清空主页、博士后年级或全部方向关系；不能清空姓名、身份、状态或硕博年级。方向一旦填写，将替换该成员的全部方向关系，不是追加。

从共享表格导出 UTF-8 CSV（允许 BOM）。审核差异后先预览，再应用：

```sh
python -B -X utf8 scripts/import_members.py .local/成员维护/已审核.csv
python -B -X utf8 scripts/import_members.py .local/成员维护/已审核.csv --apply
python -B -X utf8 scripts/build.py
python -B -X utf8 scripts/check.py
python -B -X utf8 -m unittest discover -s scripts -p "test_*.py"
```

预览不写文件；重复 ID、未知方向、错误字段或不完整新增会使整批导入失败。应用仅修改成员表和方向关系，保持未涉及成员及既有关系顺序，不会更新日期、构建、提交或发布。保留审核 CSV；如果需要撤回未提交的导入，先保留当前数据，再按预览差异恢复对应字段，避免用整文件回退覆盖他人的修改。

在临时数据副本验证时可使用 `--content-dir .local/成员维护/测试数据`。导入器会拒绝读取期间已被其他修改改变的成员或方向数据；请避免两位维护者同时应用导入。

## 公开边界

六份 JSON、空白模板和本说明均为公开仓库内容。仅填写展示所需的公开信息；原始名单、私人联系方式、离组日期及原因、审核答复、来源差异与核查备注放 `.local/` 或本地资料台账。内部核查材料不会参与构建。

素材路径相对于 `site/`；方法图保持原比例并可查看原图。新增素材时更新[素材署名](../site/assets/CREDITS.md)。没有公开代码时设置 `codeVisibility: "private"`，保留真实地址但不显示 Code 链接；匿名访问失败不自动改变公开状态。
