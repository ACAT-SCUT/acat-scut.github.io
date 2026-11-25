# 数据维护与填写说明

[项目指南](../README.md) · [建设需求](../ROADMAP.md) · [变更申请 CSV 模板](templates/member-requests.csv)

## 数据分工

六类业务内容分为七份 JSON，是公开内容的唯一维护来源。`scripts/content.py` 统一读取并验证，构建不抓取外部数据、不改变核查日期。以下字段列出了当前全部维护接口；只读派生内容无需手填。

| 文件 | 必填字段 | 可选字段及说明 | 维护者 |
|---|---|---|---|
| `team.json` | `contentUpdated`、`description`、`about`、`lead`、`contact`、`achievements`、`identity`、`links`、`copy` | 各子对象见下表；荣誉允许空数组；`wechat` 可省略 | 团队指定维护者 |
| `research.json` | 每行 `id`、`title`、`short`、`en`、`summary`、`topics`、`memberOrder`、`examples`、`source` | `source` 是公开学习资源链接；`memberOrder` 供旧接口排序，归属由经历表生成；例子允许空数组 | 方向负责人建议，维护者审核 |
| `members.json` | 每行 `id`、`name`、`displayExperienceId` | `url` 为 HTTPS 主页，`sortName` 为小写、按音节用空格分隔的拼音排序键；姓名及主页由所有经历共用 | 学生申请，维护者审核 |
| `member-experiences.json` | 每行 `id`、`memberId`、`role`、`status`、`graduationConfirmed`、`researchIds`；硕博须有 `entryYear` | 博士后的 `entryYear` 为入站年，可省略；一段经历一条，方向归属只在本表维护 | 学生申请，维护者审核 |
| `papers.json` | 每行 `id`、`name`、`title`、`authors`、`venue`、`year`、`area`、`summary`、`url` | `short` 简称、`presentation` 已确认的展示形式（Oral／Spotlight／Poster）、`code` 代码地址、`codeVisibility`（默认 `public`，私有填 `private`）、`figure` 方法图路径、`publicationDetails` 正式出版补充信息、`correspondingAuthors` 已确认的通讯作者姓名数组、`chineseExplanationUrl` 一个经核实的中文解读 HTTPS 链接，在 Paper、Code 旁显示为「推文」 | 作者或方向负责人建议，维护者审核 |
| `projects.json` | 每行 `id`、`title`、`category`（`vertical`／`horizontal`） | `funding` 资助或合作信息，`period` 起止年月（`YYYY.MM—YYYY.MM`），`start` 供缺完整区间时排序，`url` 公开项目页 | 项目相关人员提供，维护者审核 |
| `homepage.json` | `year`、`featured`、`updates`、`legacyPaperAnchors` | 列表允许为空；首页条目由人工选取 | 团队指定维护者 |

`team.json` 子对象：

| 子对象 | 字段与用途 |
|---|---|
| `identity` | `shortName`、`suffix`、`name`、`englishName`、`affiliation`（按行文本数组）、`location`、`logo`（favicon）、`sidebarLogo`（侧栏透明图）、`copyrightYear` |
| `lead` | `name`、`englishName`、`url`、`title`、`photo`、`position`、`affiliations`、`interests`、`honor`、`sidebarPosition`、`bioAfterName`（姓名链接后的简介片段） |
| `contact` | `email`（首页、侧栏与应聘区共用）、`address`（首页地址）、`intro`（首页欢迎语片段）、`admissionsUrl`（学校招生网）、可选 `mastersAdmissionsUrl`、`doctoralAdmissionsUrl`（学院招生入口）、可选 `postdocNotice`（下文） |
| `links` | `baseUrl`（站点绝对根地址，末尾 `/`）、`organization`（GitHub 组织）、`scholar`（负责人学术主页）、`college`（负责人学院个人主页） |
| `achievements` | 荣誉列表，每项 `title`、`text`；团队与个人荣誉不混用 |
| `copy` | `publicationsDescription`（论文页首简介） |
| `wechat` | `name`（公众号全名）、`qrCode`（相对 `site/` 的原始二维码路径）。用于首页代表性成果末尾的关注入口 |

博士后公告在 `contact.postdocNotice` 中维护。填写原公告 `url` 与 ISO 发布日期 `publishedOn`。按需填写公告计划数 `plannedPositions`、依原序整理的研究方向 `directions`（每项 `title`、`summary`）、研究经历 `experience`（文字数组）、申请材料 `materials` 和 `mailSubject`。移除整个公告字段后，详情页省略博士后板块。

片段是 `[{"text": "文字"}, {"text": "重点", "tag": "strong"}]`，`tag` 只可省略或为 `strong`／`b`，不填写 HTML。模板负责转义和排版。

首页的 `featured` 和 `updates` 均通过 `paper` 引用论文，可按需填 `recognition`（独立的荣誉标签）。题名按论文 ID 链接到本站论文条目，刊会和展示形式从论文记录读取，中文解读随论文维护。动态还须填写 `date`（`YYYY-MM` 或 `YYYY-MM-DD`），按所选 `year` 的日期倒序展示，最多五条。代表性成果按录入顺序展示。已对外使用的首页论文锚点保存在 `legacyPaperAnchors`，更换精选时仍可直达。

### 论文解读来源

论文的 `summary` 用中文概括问题、方法和贡献。已有对应解读时，通过 `chineseExplanationUrl` 填写一条原页地址，网站统一显示为「推文」。

可信公众号的使用优先顺序如下。

1. **ABC学术技术分享**，团队公众号。
2. **时空探索之旅**。

名单内的账号通过来源审核。接入前核对原文显示的发文账号和技术内容，确认正文对应论文及其版本。会议版和期刊扩展版分别匹配。解读正文同时讲解两个版本时，两条记录可共用链接。两家公众号均无已核实的匹配时，可选经核实的作者解读或学院通报。核对信息留内部台账。

## ID、关系与人工判断

- 人员 ID（如 `m001`）和原 `member-m001` 页面锚点保持不变，姓名不是主键，允许同名。新增人员由工具分配 `member-` 开头的唯一 ID。
- 一人多段经历，经历通过 `memberId` 指向人员。迁移经历为 `m001-e01` 等，新经历分配 `experience-` 开头 ID；新增经历不会覆盖历史经历或自动切换主经历。
- `displayExperienceId` 指向该人的主经历，用于保留历史人员锚点和旧数据接口；维护者可在核对后直接调整该引用，学生不填写。
- `role` 为 `postdoc`／`phd`／`master`；`entryYear` 为完整四位年份。硕博表示入学年，博士后表示入站年；不知道博士后入站年时不补造。
- `status` 为 `current`／`former`；`graduationConfirmed` 为布尔值。只有明确毕业并经审核的硕博经历才设为 `true`，同时为 `former`；`false` 表示尚未确认，不能理解为未毕业。博士后不能标记毕业。
- 研究归属只维护在经历的 `researchIds`，允许跨方向、暂未归属，毕业后保留这段经历的方向。研究表 `memberOrder` 供旧接口排序，名单的方向归属由经历决定。
- 成员页按方向展示当前经历，往届经历集中展示。未归方向的当前经历保留稳定锚点。分组内按身份、年份和姓名排序。有中文姓名新增或更正时，维护者可在人员表补填 `sortName`（例如 `lin wei wei`）。缺值时沿用姓名排序。
- 论文 ID 为固定锚点，如 `paper-sparsetsf-2026`。改题名或年份不改 ID，会议与期刊扩展版分别维护。方向、项目 ID 同样保持稳定。
- `contentUpdated` 是实际公开内容修改日，由维护者维护。导入不自动改日期、构建或发布；页面计数、分组、链接及站点地图由构建生成。

## 展示字段设计与当前接口

- 项目按已核实的 `category` 分组，组内按起始年月倒序、同月按 ID 排序。已确认完整公开区间时填 `period`，仅确认起始年月时可用 `start` 排序。
- 论文 `year` 和 `publicationDetails` 用于书目。与论文相关的荣誉动态引用原论文 ID，使用独立的动态日期和公开新闻链接。

## 学生填写与审核导入

学生通过简短表单提出新增、修改或毕业申请；维护者在导出结果中逐行标记“通过／待核对／退回”。目前提供平台无关 CSV，尚未接入云服务；权限由以后选定的平台配置。填写结果、审核表和备份放 `.local/成员维护/`，不进入公开仓库。

空白模板只有表头，允许仅提供本次需要的列：

| CSV 列 | 用途 |
|---|---|
| `申请编号` | 可由收集服务提供，跨批次须唯一；为空时由申请内容和匹配目标生成稳定标识 |
| `申请类型` | `新增经历`、`修改资料`、`申请毕业`（也接受 add／update／graduate） |
| `姓名`、`身份`、`入学年份` | 定位成员与经历；身份可用中文或 postdoc／phd／master，年份用四位整数；博士后可暂缺 |
| `研究方向`、`个人主页` | 新增经历时填写；方向支持 ID 或完整中文名，多项用英文分号分隔，主页仅接受 HTTPS |
| `修改字段`、`新值` | 修改资料时填写；字段为姓名、个人主页、身份、入学年份或研究方向。身份修改仅用于纠错，升学应新增经历 |
| `明确清空` | 填“是”才清空主页、方向或博士后年份；空白不覆盖，不允许清空硕博年份或姓名 |
| `确认毕业` | 申请毕业时明确填“是”，仅作用于定位到的那段硕博经历 |
| `审核结果` | 明确填写“通过”才进入预览；其他值及空白均跳过 |
| `匹配人员编号`、`匹配经历编号` | 维护者填写，唯一匹配时可留空；有歧义时必须选择。新增同名但不同的人时，人员编号明确填 `new` |
| `审核备注` | 维护者可填，仅存本地日志，不写入正式 JSON |

同一人的姓名和主页变化会由全部经历共用；方向、年级和毕业确认属于单段经历。缺失申请行不删除人员。重复编号、错误引用、歧义、冲突或非法的通过项会停止整批处理，不部分写入。空白修改和已符合现状的申请会跳过并说明原因。

维护者先预览，再显式应用同一份 CSV：

```sh
python -B -X utf8 scripts/import_members.py .local/成员维护/已审核.csv
python -B -X utf8 scripts/import_members.py .local/成员维护/已审核.csv --apply
python -B -X utf8 scripts/build.py
python -B -X utf8 scripts/check.py
python -B -X utf8 -m unittest discover -s scripts -p "test_*.py"
```

预览只保存本地回执，不修改正式数据。应用会检查 CSV 和数据是否仍与预览一致；变化后需重新预览。成功应用的申请写入本地台账，重复导入会跳过；同一编号改成不同申请会报错。同一数据目录的维护命令串行执行，写入前会保存备份，普通写入失败恢复原文件；进程中断的未完成事务在下次维护命令启动时恢复。

应用结果返回 `batchId`。需要撤回且该批次后没有其他数据变化时：

```sh
python -B -X utf8 scripts/import_members.py --restore 返回的批次编号
python -B -X utf8 scripts/build.py
python -B -X utf8 scripts/check.py
```

恢复检查文件哈希，拒绝覆盖后续修改；备份和日志位于 `.local/member-maintenance/`。恢复不会自动构建或发布。演示 CSV 带有“演示”用途或 demo 编号，正式工具会拒绝应用。旧单身份成员 CSV 不再直接写入，请转换为新申请模板。

测试时使用 `--content-dir .local/成员维护/测试数据`，仅允许本项目正式内容目录或 `.local/` 中的数据副本。未来收集服务可以映射到上述简短列，或输出结构化 `申请内容` JSON；后者必须符合相同申请校验规则。

## 公开边界

七份 JSON、空白模板和本说明均为公开仓库内容。仅填写展示所需的公开信息；原始名单、私人联系方式、离组日期及原因、审核答复、来源差异与核查备注放 `.local/` 或本地资料台账。内部核查材料不会参与构建。

素材路径相对于 `site/`；方法图保持原比例并可查看原图。新增素材时更新[素材署名](../site/assets/CREDITS.md)。没有公开代码时设置 `codeVisibility: "private"`，省略代码地址；匿名访问失败不自动改变公开状态。
