---
name: summarize-project
description: |
  项目总结呈现技能（由 manage-project 重构而来）。定位是项目的**呈现/输出工具**，不是管理/输入工具：只读项目现有事实源，产出一份派生的项目总结报告，不修改项目的任何管理工件。报告**文本综述与可视化图表并重**——文字总结覆盖项目概览、需求与特性叙述，图形呈现覆盖功能分解（WBS 工作分解图）、里程碑视图、任务进展甘特图。报告按五个呈现层面分解，每个层面回答外部读者的一个问题（项目目标是什么、要交付哪些能力、包含哪些任务、里程碑是什么/完成了哪些、每个任务什么状态与整体进度安排），并对应 references/ 下一份层参考文档。信息源识别：若目标项目已使用 SpecKit 框架管理（存在 .specify/ 目录及相应结构），以该目录中的工件（specs/*/requirements.md、specs/*/tasks.md、memory/features.md 等）为主要信息源总结项目信息；非 SpecKit 项目回退到代码结构、README/docs、外部需求/任务/进度文档、git 历史等来源——输入源不限于代码，外部文件与文档均可作为材料。所有图表以 PlantUML 源码嵌入报告（可编辑、可 diff、可版本管理），渲染校验一律委托 draw-plantuml 技能完成。四项核心内容（项目概览、项目里程碑、功能分解 WBS、任务进展甘特图）默认逐层交互式确认后落盘——WBS 与甘特图须先渲染出图再确认；非交互模式（用户显式声明跳过）自动确认并在元信息标注。报告是派生产物，支持重复运行刷新。报告单文件自包含：所有图表必须渲染并将渲染结果内联嵌入正文，不依赖本地文件、相对路径图片或读者端渲染工具，可直接对外分发。
  Use when the user mentions "项目总结", "总结项目", "项目现状", "项目报告", "项目汇报", "项目进展", "项目概览", "项目可视化", "需求特性", "功能分解", "里程碑", "进度追踪", "项目进度", "summarize project", "project summary", "project report", "project overview", "project status", "project dashboard", "project visualization", "milestone", "progress tracking", "WBS", "工作分解", "甘特图".
skill_id: "<SKILL:.specify/skills/summarize-project/SKILL.md>"
---

# 项目总结呈现技能

以**一份项目总结报告**（SpecKit 项目默认 `.specify/project/summary.md`，非 SpecKit 项目默认 `docs/project-summary.md`，用户可指定其他位置）呈现项目当前现状。**文本综述与可视化图表并重**：文字总结回答"项目是什么、要交付什么、进展如何"，图表让外部读者一眼看清结构与进度。报告是**派生产物**：事实源永远在项目自身材料中，本技能只读取、总结、可视化，不代替项目管理工具维护任何事实。

报告按**五个呈现层面**分解，每个层面回答外部读者的一个问题，并对应 `references/` 目录下**一份层参考文档**（一层一文档；生成该章节前先读对应层文档）：

| 呈现层面 | 回答外部读者的问题 | 报告章节 | 形态 | 层参考文档 |
|----------|--------------------|----------|------|------------|
| 1. 项目概览 | 项目的目标是什么？ | `## 项目概览` 节 | Markdown 文本（背景、目标、范围——提炼自事实源，注明出处） | [references/project-overview.md](references/project-overview.md) |
| 2. 需求与特性 | 项目要交付哪些能力？ | `## 需求与特性` 节 | 特性清单表格（名称、来源、状态）+ 可选 `@startmindmap` 概览图（PlantUML 源码嵌入） | [references/requirements-features.md](references/requirements-features.md) |
| 3. 功能分解 | 项目包含哪些任务？ | `## 功能分解` 节 | WBS 工作分解图：`@startwbs`（PlantUML 源码嵌入） | [references/work-breakdown.md](references/work-breakdown.md) |
| 4. 项目里程碑 | 里程碑是什么？完成了哪些里程碑？ | `## 项目里程碑` 节 | 里程碑视图：仅含 `happens` 条目的 `@startgantt` 图（PlantUML 源码嵌入）+ 跟踪表格 | [references/milestones.md](references/milestones.md) |
| 5. 任务进展 | 每个任务当前的状态？整体进度安排？ | `## 任务进展` 节 | 甘特图：`@startgantt`，三态进度 + 当前日期参照线（PlantUML 源码嵌入）+ 整体进度叙述 | [references/task-progress.md](references/task-progress.md) |

**图表即文本，交付自包含**：所有图表的 PlantUML 源码以 ```` ```plantuml ```` 代码块保留在报告中——源码是可编辑、可 diff、可随 git 演进的权威形态；同时每张图**必须渲染**并将渲染结果（内联 SVG 文本）**内联嵌入**报告正文，使报告成为单文件自包含交付物：读者无需 PlantUML、draw-plantuml 或本项目任何文件即可完整阅读。禁止以相对/绝对路径引用同目录图片文件，禁止外链图片 URL。

图表语法、渲染与产物约定全部委托 **draw-plantuml** 技能；本技能只做信息读取、组织与可视化呈现，不含渲染脚本。

## 核心原则

- **呈现而非管理**：本技能是项目的最终呈现工具——只读事实源、产出派生报告，**绝不修改** `.specify/`、需求文档、任务清单等任何源工件。项目事实的录入与维护由项目管理框架（如 SpecKit 的 `/speckit.*` 流程）或用户自行完成。
- **报告可再生**：重复运行本技能时**刷新**报告（重新读取事实源、重生成图表与表格）。报告正文不承载人工维护的事实；用户若在报告内手工补充了 `## 附注` 节，刷新时原样保留该节，其余章节视为可再生的派生内容。
- **单一呈现口径**：先产出一棵**功能分解树**（阶段 → 任务 →（可选）子任务），WBS 图、甘特图、里程碑视图都由它派生——三处工作项/里程碑命名逐字一致，无孤儿条目。
- **可溯源，不臆造**：每个呈现条目（特性、工作项、里程碑）必须能溯源到信息源材料（`.specify/` 工件、外部文档、代码结构、git 历史、用户描述）。材料里没有的内容，宁可提问也绝不编造；推断性内容显式标注。
- **图源嵌入，渲染委托**：PlantUML 源码嵌入报告；WBS 走 draw-plantuml 的 `@startwbs` 能力，里程碑视图与甘特图走 `@startgantt` 能力。产物机制以 draw-plantuml 为准。
- **自包含交付**：报告面向外部读者分发，最终落盘的报告必须是**单文件自包含**文档，不依赖本地或本项目的任何依赖——所有图表渲染产物内联嵌入正文（不允许相对路径/绝对路径引用图片文件），不允许外部图片 URL，不要求读者端安装任何渲染工具。报告内注明的事实源路径仅作出处标注，不构成阅读依赖。
- **确认后落盘**：四项项目管理核心内容——项目概览（背景介绍）、项目里程碑、功能分解（WBS）、任务进展（甘特图）——默认逐层**交互式确认**，用户确认通过的内容才允许写入报告；WBS 与甘特图必须先经 draw-plantuml **渲染出图**、连图带源码一并呈现确认，不得拿未渲染源码要求确认。非交互运行（用户显式声明跳过确认）自动通过全部门禁，并在 `## 元信息` 标注「未经交互确认」。
- **读者兼顾**：命名用业务语言，避免内部黑话；每张图配一段简要说明，外部读者不读代码也能看懂。

## 信息源识别

运行检测脚本识别目标项目的信息源格局（确定性逻辑，勿凭猜测手工判断）：

```bash
python3 ${SKILL_HOME}/scripts/detect-project-sources.py --target <项目根目录>
```

脚本输出 JSON：`speckit`（是否存在 `.specify/` 管理结构）、已发现的 SpecKit 工件清单（constitution、features 索引、各 spec 的 requirements/tasks/plan/verification）、候选外部文档（README、docs/ 等）、以及默认报告路径。按其输出选择下表的信息源优先级：

| 呈现内容 | SpecKit 项目信息源（检测到 `.specify/`） | 非 SpecKit 项目回退 |
|----------|------------------------------------------|----------------------|
| 项目概览 | `memory/constitution.md`、specs 规格、README | README、docs/、外部项目文档、用户描述 |
| 需求与特性 | `memory/features.md` 与 `memory/features/<ID>.md`、`specs/<key>/requirements.md` | 需求文档、产品功能清单、issue 导出 |
| 功能分解 | `specs/<key>/plan.md` / `tasks.md` 的结构层级、模块目录结构 | 代码目录结构、架构文档、任务清单 |
| 项目里程碑 | git 标签、features.md 状态列、规格完成节点 | git 标签、发布记录、路线图文档 |
| 任务进展 | `specs/<key>/tasks.md` 勾选状态、`verification.md`、checklists | 任务清单/看板导出、进度文档 |

- **SpecKit 优先**：检测到 `.specify/` 时以上表左列为主要信息源，外部文档仅作补充；`.specify/` 结构不完整时按脚本输出的实际工件清单降级，缺失项回退到右列来源。
- **多源融合**：输入不限于代码——用户提供的外部文件（Word/PDF/Markdown 需求文档、任务清单、会议纪要、路线图）与代码结构、git 历史同为材料；逐条记录每个条目来自哪个源。
- **只读**：对所有信息源只读取、不写入。

## 工作流

按以下 7 个步骤顺序执行。

### Step 1: 识别信息源

运行「信息源识别」节的检测脚本，确定：目标项目是否为 SpecKit 管理、可用的工件/文档清单、默认报告路径。用户指定了额外材料（外部文件、文档目录）时一并登记为信息源。随后检查报告目标位置是否已有既有报告：存在 → 读取其中的 `## 附注` 节以备保留；不存在 → 直接生成。

### Step 2: 采集项目现状信息

按映射表从信息源读取：项目概览素材（目标、范围）、需求与特性条目、工作项、里程碑事件。逐层采集时遵循对应**层参考文档**的「取材优先级」与组织规则。为每个条目记录：**名称、来源出处、状态（completed / in-progress / not-started）、进度百分比（in-progress 时必填）、时间信息（若有）、负责人（若有）**；为每个里程碑记录：**名称、锚定方式（绝对日期或关联工作项结束点）、达成状态**。材料不足时按「信息不足与澄清」节处理，不臆造。

### Step 3: 组织呈现模型

把工作项自顶向下组织为**阶段 → 任务 →（可选）子任务**的单一功能分解树，并确定特性清单与里程碑清单（关键评审、发布、验收节点）。这棵树与这两份清单是后续所有图表的唯一数据源：先在上下文中定稿（命名、层级、归属、锚定），再进入确认门禁。分解深度与命名规范见 [references/work-breakdown.md](references/work-breakdown.md)；里程碑识别与锚定规则见 [references/milestones.md](references/milestones.md)。

### Step 4: 逐层交互式确认（四道门禁）

四项核心内容各设一道确认门禁，按以下顺序逐层进行。每道门禁流程固定：**起草内容 → 向用户呈现 → 等待确认**——借助当前工具的交互提问能力（如 AskUserQuestion）给出「确认通过 / 提出修改 / 跳过本门禁（记为未确认）」三个选项；确认通过才进入下一道门禁，提出修改则原地修订后**再次呈现确认**（同一门禁内迭代直至通过）。**未经确认的内容不得写入最终报告。**

1. **门禁 1 — 项目概览（背景介绍）**：按 [references/project-overview.md](references/project-overview.md) 起草 `## 项目概览` 文本（背景、目标、范围，逐条注明出处）→ 呈现全文 → 确认。
2. **门禁 2 — 项目里程碑**：按 [references/milestones.md](references/milestones.md) 起草里程碑视图与跟踪材料 → 呈现 → 确认。里程碑视图为仅含 `happens` 条目的紧凑 `@startgantt` 图——每个里程碑用 `[名称] happens <日期>` 或 `happens at [工作项]'s end` 声明为零工期菱形节点；配套「里程碑 | 锚定 | 状态」Markdown 表格与达成叙述（完成了哪些里程碑）。
3. **门禁 3 — 功能分解（WBS，须渲染确认）**：按 [references/work-breakdown.md](references/work-breakdown.md) 生成 `@startwbs` 源码（语法遵循 draw-plantuml 的 `references/howto/13-wbs-diagram.md`；项目过大时按「大项目与图集拆分」节拆分）→ **委托 draw-plantuml 渲染出图** → 将渲染图片（路径）与源码**一并呈现** → 确认。渲染失败先修正源码重试；不得拿未渲染的源码要求确认。
4. **门禁 4 — 任务进展（甘特图，须渲染确认）**：按 [references/task-progress.md](references/task-progress.md) 生成 `@startgantt` 源码（语法遵循 `references/howto/14-gantt-diagram.md`）→ **渲染出图** → 图与源码一并呈现 → 确认。源码必须包含：
   - **进度状态语义**：completed / in-progress（带完成百分比）/ not-started 三态视觉可辨；项目进行期须标出当前日期参照线，且 `today` **必须**以 `today is N days after start` 相对项目起点显式定位——不得依赖渲染环境时钟；
   - **里程碑**：**逐条复制**门禁 2 已确认的全部 `happens` 条目（同名同锚定）——一致性在生成时保证，而非留待落盘前自检兜底；
   - **依赖关系**：工作项间先后依赖按材料呈现，无依据时不虚构依赖。

- **确认即冻结**：门禁通过后对应章节内容即冻结；后续步骤发现一致性问题时，凡改动冻结内容须回到对应门禁**重新确认**。
- **刷新运行的批量确认**：重复运行刷新报告时，与既有报告对应章节逐字一致的门禁内容可合并为一次「全部沿用」确认；有变化的章节仍逐层确认。
- **非交互模式**：用户显式声明跳过确认（或调用方以非交互方式运行）时，四道门禁自动通过，并在 `## 元信息` 标注「未经交互确认」。

### Step 5: 组装报告与剩余内容

1. **需求与特性**（无门禁层）：按 [references/requirements-features.md](references/requirements-features.md) 起草特性清单表格；特性数量适合图示时以 `@startmindmap` 附特性分组概览图——特性以表格为主、图为辅。
2. 按报告骨架（见 [references/reporting-playbook.md](references/reporting-playbook.md)）组装五个章节：四道门禁冻结的内容 + 需求与特性 + 保留的既有 `## 附注` 节。

### Step 6: 渲染与内联嵌入（委托 draw-plantuml）

所有 PlantUML 代码块**必须**逐块经 draw-plantuml 渲染：WBS 与甘特图在门禁 3/4 已渲染确认、确认后源码未再改动的，直接沿用其渲染结果；其余块（里程碑视图、特性概览图，以及门禁确认后被修订过的 WBS/甘特）重新渲染，验证语法正确、版面可读（布局与输出约定见其 `references/howto/12-rendering-and-output.md`）。校验失败则修正源码后重试——若修正涉及门禁冻结内容，须回到对应门禁重新确认。

渲染产物按「自包含交付」原则嵌入报告：

1. 每张图的 **SVG 渲染结果以内联文本形式**嵌入报告正文，紧随对应 `plantuml` 源码块之后；源码块永不删除，始终是权威形态；
2. **禁止**以相对路径或绝对路径引用同目录/本项目的图片文件，**禁止**外链图片 URL——报告落盘后是单文件，移动、复制、发送给外部读者均不失效；
3. 单图 SVG 体积过大时按「大项目与图集拆分」节拆分，而非退化为外部文件引用；
4. 面向会剥离内联 SVG 的渲染环境分发时，可**附加**产出一份单文件自包含 HTML（图片 base64 内嵌，组装约定见 draw-plantuml `references/howto/12-rendering-and-output.md`）——HTML 是附加分发物，Markdown 报告仍是权威形态。

### Step 7: 一致性自检与报告落盘

执行**三图一致性自检**：WBS 叶子工作项（带时间信息的）与甘特条目一一对应、命名一致；里程碑视图与甘特图中的里程碑同名同锚定；三态口径在图与叙述间一致；特性清单表格与概览叙述一致。清单见 [references/reporting-playbook.md](references/reporting-playbook.md)。同时执行**自包含检查**：报告内无相对/绝对路径图片引用、无外链图片 URL，每个 `plantuml` 源码块之后均有其内联渲染图。全部通过后写入报告（保留既有 `## 附注` 节），并刷新元信息：生成日期、信息源清单、估计假设逐条显式标注、**四道门禁确认状态**（全部确认 / 部分跳过 / 未经交互确认）。

## 信息不足与澄清

材料不足以支撑概览叙述、分解或排期时，二选一：(a) 给出合理默认并在报告中**显式标注为估计假设**；(b) 当猜测会实质性误导范围/时间/状态时，最多发起**一轮**澄清提问（不超过 4 个问题），随后继续执行。猜测不得静默扭曲工作范围、日期或状态。

## 大项目与图集拆分

单图放不下时做图集拆分：一张概览图（只到阶段层）+ 每个阶段一张下钻子图，每张子图都是报告内独立的 PlantUML 源码块，图间命名/配色/编号一致并互相交叉引用。拆分规则与阈值见 [references/reporting-playbook.md](references/reporting-playbook.md)。

## 呈现范围与受众粒度

用户可限定**呈现周期**（如本迭代/本季度）或**受众粒度**（如高管层只看阶段级）：周期受限时甘特时间轴与叙述只覆盖该范围，范围外工作省略或明显弱化；粒度受限时分解到指定深度即止，保持阶段级结构完整。详见 [references/reporting-playbook.md](references/reporting-playbook.md)。

## 参考文档

**层参考文档**（一层一文档，各含：呈现要素、取材优先级、组织/推断规则、落笔检查）：

- [references/project-overview.md](references/project-overview.md) — 项目概览层：项目的目标是什么（背景、目标、范围提炼）
- [references/requirements-features.md](references/requirements-features.md) — 需求与特性层：特性清单、状态映射、可选概览图
- [references/work-breakdown.md](references/work-breakdown.md) — 功能分解层：项目包含哪些任务（分解深度、命名规范、单一数据源约定）
- [references/milestones.md](references/milestones.md) — 里程碑层：里程碑是什么、完成了哪些（识别、锚定、achieved/pending/at-risk 跟踪）
- [references/task-progress.md](references/task-progress.md) — 任务进展层：每个任务的状态与整体进度安排（状态推断、退化情形、today 锚定、估计假设、依赖）

**跨层公共约定与工具**：

- [references/reporting-playbook.md](references/reporting-playbook.md) — 层参考文档索引、报告结构、刷新规则、图集拆分、三图一致性清单、范围/粒度控制、落盘检查单、外部文档取材
- `${SKILL_HOME}/scripts/detect-project-sources.py` — 信息源检测脚本（SpecKit 结构识别 + 候选文档发现，JSON 输出）
- draw-plantuml 技能：`references/howto/13-wbs-diagram.md`（WBS）、`references/howto/14-gantt-diagram.md`（甘特图与里程碑）、`references/howto/12-rendering-and-output.md`（渲染与输出约定）

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At the end of a substantial run of this skill, perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this run reached a meaningful wrap-up. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against this skill's declared purpose and produce a short review plus ≥1 concrete, skill-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this skill's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id`; if a parent flow already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "skill:summarize-project" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
