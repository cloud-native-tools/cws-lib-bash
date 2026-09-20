---
name: summarize-project
description: |
  项目总结呈现技能（由 manage-project 重构而来）。定位是项目的**呈现/输出工具**，不是管理/输入工具：只读项目现有事实源，产出一份派生的项目总结报告，不修改项目的任何管理工件。报告**文本综述与可视化图表并重**——文字总结覆盖项目概览、需求与特性叙述，图形呈现覆盖功能分解（WBS 工作分解图）、里程碑视图（按独立成图规则条件出图，否则合并进甘特图）、任务进展甘特图；四张图统一编码状态（**工作项四态色板**：已完成绿 / 进行中蓝 / **延期红** / 未开始灰，每态配冗余符号 `✓ ● ⚠ ○`）、完成度（甘特 `is N% complete` 条内填充 + WBS 节点 `NN%` 第三行）、日期（yyyy-mm-dd；里程碑菱形自带日期与已达成/待达成/逾期符号 `✓ ◇ ⚠`）与**负责人**——人员维度在 WBS 节点、甘特条形、里程碑标签及报告 `### 人员与分工` 小节均有强制承载位，缺失一律显式声明、绝不静默丢弃。报告按五个呈现层面分解，每个层面回答外部读者的一个问题（项目目标是什么、要交付哪些能力、包含哪些任务、里程碑是什么/完成了哪些、每个任务什么状态与整体进度安排），并对应 references/ 下一份层参考文档。**进度是贯穿五个章节的一等呈现维度**，不只出现在《任务进展》：`## 项目概览` 末尾固定 `### 整体进度摘要`、`## 需求与特性` 的特性表带「进度%」列与开篇量化句、`## 功能分解` 固定 `### 工作项进度`、`## 项目里程碑` 出里程碑进度汇总表（达成率 / 已达成 / 逾期 / 待达成 / 最大逾期天数）与跟踪表「达成进度」「延期天数」列、`## 任务进展` 固定 `### 进度叙述`；同一实体的进度跨章节同值同源（呈现位总表、呈现模板、叙述规范、跨章节一致门禁与空值降级见 references/progress-presentation.md）。**项目关键信息用 SQLite 关系建模，校验由数据库强约束承担**：七个核心实体各一张表（`project` / `people` / `phases` / `work_items` / `milestones` / `features` / `sources`，另有依赖联结表 `work_item_deps` 等），**字段定义与约束的唯一权威是 `schema/project.sql`（DDL）**——`NOT NULL`（R 档必填）、`PRIMARY KEY` + 触发器（`*_id` 跨实体全局唯一）、`FOREIGN KEY`（`phase_id`/`owner_id`/`anchor_item_id`/依赖关系可解析）、`CHECK`（日期是零填充 `yyyy-mm-dd` 且真实日历日、状态取值域、`progress_pct` 0–100、无出处的百分比/权重一律拒收），**具备强约束的数据不用 Markdown 的模糊描述来记录**。项目管理信息通常**不在代码仓库里**（一个项目常横跨多个 repo，真正的排期/负责人/里程碑活在项目管理程序里），因此本技能**默认不扫 repo**——三段式输入：① 从当前上下文与用户提供的外部材料（管理系统导出、需求/任务/进度文档、Excel/Word/PDF、看板导出）按**规范字段名**（snake_case，字段名即列名、也是实体间关联键：`project_name`/`baseline_date`/`phase_id`/`item_id`/`owner_id`/`milestone_id`/`anchor_item_id`/`depends_on`…）摄取成表单（人工可写的输入面，落位交付目录 `data/project-input.yaml`，空白模板 `templates/project-input.template.yaml`，技能**只读不改**）；② **装载进 SQLite（`scripts/project-db.py --load`，装载即校验**，约束违规即报错并给出可读原因，默认每次运行重建数据库；用户希望基于已有历史库按最新信息更新时用 `--update`，UPSERT + 变更摘要）；③ 齐备则**查询数据库**驱动后续章节与图表，R 档缺失（`project_name`、`baseline_date`，且 `work_items` 与 `milestones` 至少一组非空）或数据库拒绝任何一行则**阻断**并呈现只含真正缺失项的待填表单。**装载后数据库是查询与校验的唯一事实源**；I 档（阶段划分、依赖、角色、状态归一化、ID 生成等）由模型/装载器**推断并在 `inferred_fields` 留痕（`inferred_from` 依据非空）**、汇总进元信息推断字段清单，O 档缺失显式降级（`NULL` 语义明确：`progress_pct IS NULL` = 无可计数依据、不是 0）。字段名在 DDL、必要信息表（references/required-info.md 讲业务含义与三档必填性）、引擎输出与各文档引用**四处一致**。**git repo 取材完全 opt-in**：仅当表单 `project.repos[]` 声明了仓库、且某字段被标为「从 repo 推导」（`derive_fields`）时，才对该字段做**定向小范围查询**，默认一律不查、禁止全仓扫描；可选补充源阶梯与按语言的取材点（如 `.specify/specs/*/requirements.md`、`tasks.md`、`memory/features.md`、语言清单、git 标签）见 references/source-tiers.md，全程只读、可溯源、输入不限于代码。材料稀疏或缺失时**诚实降级**：缺什么就显式声明什么（章节声明句 / 图内 caption / 元信息「材料缺口」清单三处承载），进度百分比、里程碑日期、工期、负责人、任务状态五类信息无依据时一律走合法终态而**绝不臆造**；无里程碑材料时该章节仅保留声明、无排期材料时甘特不出图，报告随材料量伸缩、宁短勿虚。所有图表的 PlantUML 源码**不进报告正文**，只作为交付目录 `assets/<图名>.puml` 文件交付——`.puml` 文件是可编辑、可 diff、可版本管理的权威形态，`summary.md` 正文每张图只放渲染图片的相对路径引用 + 图说；渲染校验一律委托 draw-plantuml 技能完成。四项核心内容（项目概览、项目里程碑、功能分解 WBS、任务进展甘特图）默认逐层交互式确认后落盘——WBS 与甘特图须先渲染出图再确认；非交互模式（用户显式声明跳过）自动确认并在元信息标注。报告是派生产物，支持重复运行刷新。**日期与进度的计算全部下沉到脚本、且用 SQL 完成**：`scripts/progress-engine.py` 以交付目录 `data/project.db`（派生产物，默认每次重建、绝不写入目标项目管理工件）为输入，从库里取数并用 SQL 完成查询与聚合（天数差 `julianday`、阶段与项目级 `GROUP BY`、时间轴 `ORDER BY`），一次算出状态、进度百分比与算式、延期天数、阶段/项目聚合、里程碑达成与逾期、甘特 today 偏移与出图判据、覆盖闭合等式；Markdown 文档与报告**只调用脚本并引用其输出字段**，不比较日期先后、不算天数差、不重述任何算法；无计划完成日的条目引擎给 `unknown-schedule`，报告如实声明「无计划日期，无法判定延期」而**不判逾期、不上红色**。**交付物是一个自包含的交付目录**（SpecKit 项目默认 `.specify/project/summary/`，非 SpecKit 项目默认 `docs/project-summary/`）：`summary.md` 主报告 + `assets/`（每张图的 `.puml` 源与渲染出的 `.svg`/`.png`，同名配对）+ `data/`（**项目输入表单 `project-input.yaml`** + **项目数据库 `project.db`**、引擎输出、脚本校验结果等）；报告正文每张图只以**相对路径**引用渲染图片（如 `![功能分解 WBS](assets/wbs.svg)`）+ 图说，**正文不出现 PlantUML 源码块**（源码在 `assets/` 内的同名 `.puml` 文件里）；目录内相对路径引用齐全、禁止引用目录外文件与外链 URL——整个目录可整体移动、打包、对外分发；重复运行刷新整个目录。
  Use when the user mentions "项目总结", "总结项目", "项目现状", "项目报告", "项目汇报", "项目进展", "项目概览", "项目可视化", "需求特性", "功能分解", "里程碑", "进度追踪", "项目进度", "summarize project", "project summary", "project report", "project overview", "project status", "project dashboard", "project visualization", "milestone", "progress tracking", "WBS", "工作分解", "甘特图".
skill_id: "<SKILL:.specify/skills/summarize-project/SKILL.md>"
---

# 项目总结呈现技能

以**一个自包含的交付目录**（SpecKit 项目默认 `.specify/project/summary/`，非 SpecKit 项目默认 `docs/project-summary/`）呈现项目现状。报告是**派生产物**：只读事实源、不修改任何管理工件，重复运行**刷新**整个目录（保留 `## 附注` 节）。

```
<交付目录>/
├── summary.md   # 主报告（正文只引用 assets/ 内渲染图片 + 图说，不含 PlantUML 源码块）
├── assets/      # 每张图 .puml 源码 + .svg/.png 渲染产物（同名配对，可编辑）
└── data/        # project-input.yaml（表单，技能只读）+ project.db（派生数据库）+ 引擎输出
```

报告按**五个呈现层面**分解，每个回答外部读者的一个问题，对应一份层参考文档：

| 呈现层面 | 外部读者的问题 | 报告章节 | 层参考文档 |
|----------|---------------|----------|-----------|
| 项目概览 | 项目的目标是什么？ | `## 项目概览` | [project-overview.md](references/project-overview.md) |
| 需求与特性 | 项目要交付哪些能力？ | `## 需求与特性` | [requirements-features.md](references/requirements-features.md) |
| 功能分解 | 项目包含哪些任务？ | `## 功能分解` | [work-breakdown.md](references/work-breakdown.md) |
| 项目里程碑 | 完成了哪些里程碑？ | `## 项目里程碑` | [milestones.md](references/milestones.md) |
| 任务进展 | 整体进度安排？ | `## 任务进展` | [task-progress.md](references/task-progress.md) |

进度贯穿五章节（呈现位总表与模板见 [progress-presentation.md](references/progress-presentation.md)）；一切进度与日期计算在 `scripts/progress-engine.py`，文档与报告只引用引擎输出字段。图表以 `assets/*.puml` **源码**文件交付（可编辑、可 diff），正文只放渲染图片的相对路径引用 + 图说；渲染委托 **draw-plantuml**（`@startwbs` / `@startgantt`）。跨层图表呈现公约、渲染契约、目录自包含规则见 [reporting-playbook.md](references/reporting-playbook.md)。

## 核心原则

- **呈现而非管理**：只读事实源、产出派生报告，不修改 `.specify/`、需求文档、任务清单等任何源工件。
- **关系建模 + 数据库强约束校验**：项目信息用 SQLite 关系建模（七实体各一表），字段定义与约束权威是 [schema/project.sql](schema/project.sql)，业务含义与必要信息表（三档必填性 R/I/O）见 [required-info.md](references/required-info.md)；装载即校验（`project-db.py --load`），违规即报错并阻断。
- **报告可再生**：重复运行刷新报告（重读事实源、重生成图表与表格）；`## 附注` 节原样保留。
- **单一呈现口径**：先产出一棵功能分解树（阶段→任务→子任务），WBS、甘特、里程碑视图都由它派生，三处命名逐字一致。
- **进度贯穿五章节，计算下沉引擎**：五章节各有固定进度呈现位；状态四态 completed / in-progress / not-started / delayed、进度百分比、天数差、逾期判定全部由引擎产出，报告不含算式与日期比较。
- **可溯源，不臆造**：每个呈现条目可溯源到表单 `source` 字段；推断项标 `inferred` + 依据；缺失走诚实降级（合法终态与声明位见 [degradation.md](references/degradation.md)），绝不静默省略。
- **图源成文件，渲染委托**：`.puml` 源码落 `assets/`，正文不出现源码块；通用绘图规则以 draw-plantuml 为唯一权威。
- **跨图统一编码**：统一四态色板（`✓ ● ⚠ ○`）、yyyy-mm-dd 日期、里程碑 Mn 短编号 + 菱形标签自带日期与三态符号；负责人跨图逐字一致（字面量与映射见 [people-encoding.md](references/people-encoding.md)）。
- **人员是一等维度**：负责人在 WBS 节点、甘特条形、里程碑标签、`### 人员与分工` 小节均有承载位；缺失写 `未记录`，绝不静默丢弃。
- **目录自包含交付**：交付目录不依赖目录外任何文件；禁止引用目录外文件与外链 URL；目录整体可移动、打包、分发。
- **确认后落盘**：四项核心内容（概览、里程碑、WBS、甘特）默认逐层交互式确认，WBS 与甘特须先渲染出图再确认。
- **项目无关（可移植性）**：具体数字/路径/语言均为示例，判定须有确定性依据（DB 约束/SQL/脚本输出/材料明写），不依赖经验值（见 [portability.md](references/portability.md)）。

## 项目信息输入模型

项目管理信息**不在代码仓库里**（常横跨多个 repo），输入不限于代码。三段式：

| 段 | 做什么 | 产物 |
|----|--------|------|
| **A 上下文摄取** | 从对话上下文 + 用户提供的外部材料（管理系统导出、需求/进度文档、Excel/PDF、看板导出）按规范字段名归集成表单 | `data/project-input.yaml` |
| **B 装载进 SQLite** | `project-db.py --load`（约束即校验，违规即阻断并报可读原因）；`validate-project-input.py` 检查 R 档齐备性 | `data/project.db` |
| **C 齐备则查询驱动 / 缺则阻断出表单补填** | 齐备（退出码 0）→ 查询数据库驱动章节与图表；R 档缺失或数据库拒绝（退出码 3）→ 呈现只含缺失必填项的待填表单 | 用户补填后的表单 |

R 档只三条：`project_name`、`baseline_date`、`work_items`/`milestones` 至少一组非空。**默认不扫**任何 git 仓库；仅当表单 `project.repos[]` 声明仓库、且字段在 `derive_fields` 中标注时才做 opt-in 定向查询。表单是用户的，技能只读不改。装载/校验/查询命令、字段定义、必要信息表（三档必填性 R/I/O）详见 [required-info.md](references/required-info.md)；opt-in 取材规程见 [source-tiers.md](references/source-tiers.md)。脚本：`validate-project-input.py`（齐备性+表单骨架）、`project-db.py`（装载校验+查询）、`detect-project-sources.py`（opt-in 仓库探测）、`progress-engine.py`（计算）、`verify-chart-data.py`（图元校验）、`check-coherence.py`（落盘门禁）。

## 工作流

按以下 7 个步骤顺序执行。

### Step 1: 输入摄取与装载校验

上下文摄取 → `validate-project-input.py` + `project-db.py --load`（装载即校验）→ 齐备则进入 Step 2，R 档缺失或约束违规（退出码 3）则阻断出表单补填。`--update` 模式基于历史库 UPSERT。详见 [required-info.md](references/required-info.md) §1、§5。

### Step 2: 归集记录层并运行进度引擎

按记录层四结构组织库中数据（见 [data-model.md](references/data-model.md)），I 档推断已在装载时留痕。运行 `progress-engine.py --db <交付目录>/data/project.db --baseline <D0>`（一次运行、全报告共用）；引擎用 SQL 完成全部日期与进度计算，报告只引用输出字段。判定语义见 [consistency-rules.md](references/consistency-rules.md)，进度呈现骨架见 [progress-presentation.md](references/progress-presentation.md)。

### Step 3: 组织呈现模型

构建单一功能分解树（阶段→任务→子任务）+ 特性清单 + 里程碑清单。分解深度与命名见 [work-breakdown.md](references/work-breakdown.md)，里程碑识别与锚定见 [milestones.md](references/milestones.md)。**分解树覆盖完整性门禁**（§11）必做：穷尽候选全集 C，逐项归属到树或残差清单 R，进度分母集合须等于覆盖范围，由 `check-coherence.py` 的 CG-COVERAGE 机械兜底。

### Step 4: 逐层交互式确认（四道门禁）

四项核心内容各设门禁，按序逐层确认：起草 → 呈现 → 等待确认（通过/修改/跳过）。门禁 1 项目概览（含 `### 整体进度摘要`）；门禁 2 项目里程碑（跟踪表格 + 条件出图的里程碑视图 `happens` 条目 + 锚定 + 进度汇总表）；门禁 3 功能分解 WBS（须渲染确认，含 `### 工作项进度` + `### 人员与分工`）；门禁 4 任务进展甘特图（须渲染确认，含 `### 进度叙述`）。确认即冻结；非交互模式（用户显式声明跳过）自动通过全部门禁并标注。详见各层参考文档与 [reporting-playbook.md](references/reporting-playbook.md) §3。
> Gate probe: gate-summarize-project-four-gates — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).

### Step 5: 组装报告与剩余内容

按报告骨架（见 [reporting-playbook.md](references/reporting-playbook.md) §2）组装五章节：四道门禁冻结内容 + 需求与特性（[requirements-features.md](references/requirements-features.md)）+ 保留的 `## 附注` 节。五章节进度呈现位逐一在位。

### Step 6: 渲染与图片落位（委托 draw-plantuml）

`assets/` 下每个 `.puml` 逐个经 draw-plantuml 渲染为 `.svg` + `.png`；正文只写相对路径图片引用 + 图说。渲染契约（成功标准、≤2 轮修正、失败可见告示）见 [reporting-playbook.md](references/reporting-playbook.md) §1.4。单图过大时图集拆分（见同文档 §4）。

### Step 7: 一致性自检与报告落盘

三图一致性自检 + 进度呈现自检 + 人员图元自检 + 目录自包含检查 + 可移植性自检（清单见 [reporting-playbook.md](references/reporting-playbook.md) §5、§7）。机械门禁必跑：`project-db.py --check` + `progress-engine.py`（退出码 0）→ `check-coherence.py`（FAIL=0 才落盘）→ `verify-chart-data.py`（图元⇄引擎日期）。全部通过后写入报告并刷新元信息。

## 信息不足与澄清

R 档缺失 → 阻断出表单（不降级）；I/O 档缺失 → 诚实降级（取合法终态并在三处声明位显式呈现）。个别字段需落值时按固定顺序判定：仅凭合法终态会误导范围/时间/状态时发起一轮澄清（≤4 问题），否则给合理默认并标 `（推断）` + 元信息假设区登记。详见 [degradation.md](references/degradation.md)。

## 大项目与图集拆分

单图放不下时拆为概览图 + 每阶段下钻子图。拆分规则与阈值见 [reporting-playbook.md](references/reporting-playbook.md) §4。

## 呈现范围与受众粒度

用户可限定呈现周期（如本迭代/本季度）或受众粒度（如高管层只看阶段级）；周期受限时甘特与叙述只覆盖该范围，粒度受限时分解到指定深度即止。详见 [reporting-playbook.md](references/reporting-playbook.md) §6。

## 参考文档

**层参考文档**（一层一文档）：

| 文档 | 内容 |
|------|------|
| [project-overview.md](references/project-overview.md) | 项目概览层 |
| [requirements-features.md](references/requirements-features.md) | 需求与特性层 |
| [work-breakdown.md](references/work-breakdown.md) | 功能分解层 |
| [milestones.md](references/milestones.md) | 里程碑层 |
| [task-progress.md](references/task-progress.md) | 任务进展层 |

**跨层公共约定**：

| 文档 | 内容 |
|------|------|
| [required-info.md](references/required-info.md) | 必要信息表（业务语义、三档必填性、装载校验命令） |
| [consistency-rules.md](references/consistency-rules.md) | 判定规则单一权威 + 落盘门禁 |
| [reporting-playbook.md](references/reporting-playbook.md) | 跨层图表呈现公约、报告结构、刷新、图集拆分 |
| [progress-presentation.md](references/progress-presentation.md) | 进度贯穿五章节的呈现骨架 |
| [data-model.md](references/data-model.md) | 记录层四结构与关系模型对应 |
| [people-encoding.md](references/people-encoding.md) | 人员承载与图元编码 |
| [degradation.md](references/degradation.md) | 字段缺失时的诚实降级 |
| [portability.md](references/portability.md) | 可移植性纪律 |
| [source-tiers.md](references/source-tiers.md) | opt-in repo 补充源取材规程 |
| [schema/project.sql](schema/project.sql) | 字段定义与约束唯一权威（DDL） |

### 本技能脚本清单

| 脚本 | 职责 | 何时运行 |
|------|------|----------|
| `project-db.py` | 关系模型读写、校验、查询 | Step 1 |
| `validate-project-input.py` | R 档齐备性 + 表单骨架 | Step 1 |
| `detect-project-sources.py` | opt-in 仓库探测（可选） | Step 1（opt-in 时） |
| `progress-engine.py` | 日期与进度计算 | Step 2 |
| `verify-chart-data.py` | 图元⇄引擎日期校验 | Step 7 |
| `check-coherence.py` | 落盘文本自洽门禁 | Step 7 |

计算只在引擎里；六支顺序固定、判据不重叠。

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:summarize-project" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
