# 跨层规范：进度贯穿五章节的呈现骨架 (Progress Presentation)

`summarize-project` 的**跨层强制规范**：把"进度"从《任务进展》一节的局部话题，升级为**贯穿五个章节的一等呈现维度**——五个章节各有**固定的进度呈现位、固定形态、固定字段来源**。工作流主框架见 [../SKILL.md](../SKILL.md)；报告骨架与落盘检查单见 [reporting-playbook.md](reporting-playbook.md)；缺料降级见 [degradation.md](degradation.md)；记录层 schema 见 [data-model.md](data-model.md)。

**本文档存在的原因**：上一轮报告的进度信息只在《任务进展》出现——读者读完《项目概览》仍不知道"这个项目做到哪了"，《需求与特性》只有状态词没有完成度，《项目里程碑》只有达成/未达成没有达成率与逾期天数。进度是外部读者最先想知道的一件事，必须在每一章都能看到，且**同一个数字在各章必须同值同源**。

## 0. 三条边界（读本文档前先立住）

1. **计算在引擎，不在文档、不在报告正文**。百分比、天数差、达成率、逾期判定、阶段聚合、完成度分布、"当前处于哪个阶段"——全部由进度引擎 `${SKILL_HOME}/scripts/progress-engine.py` 计算，输出结构化**进度数据**（JSON）。本文档只规定"数字放在哪一节、写成什么句式、取哪个字段"。
2. **呈现层只做"取字段 + 拼字符串"**。报告中每一个进度数字都必须能指名到进度数据里的**一个字段**。本文档与报告正文**禁止**出现"用 A 除以 B 得到百分比""若计划日早于基准日则判逾期""基准日减锚定日得到天数"这类计算描述——需要一个数字，就写"取引擎输出的 `<字段>`"。
3. **图形编码不在此**。色板、填充比例、符号、进度条字形、图例——权威出处是 draw-plantuml 与 [reporting-playbook.md](reporting-playbook.md)「跨层图表呈现公约」。本文档只写**进度信息落在哪个呈现位**，不设计视觉编码。

> **与其他文档的消歧**：[consistency-rules.md](consistency-rules.md) 中一切**算式类/判定类**规则（阶段进度等权平均、逾期与 at-risk 判定顺序、百分比分子分母、分桶闭合），以及 [people-encoding.md](people-encoding.md) 4.2 的里程碑三态与逾期判定，描述的都是**引擎的计算职责**；呈现层不重算、不复核算术，只引用引擎输出并按枚举查表呈现。措辞上若出现"呈现层是否要自己算"的歧义，一律按本文档第 0 节第 1、2 条判：**计算在引擎，呈现只引用**。

---

## 1. 唯一数字来源：进度数据（引擎输出）

### 1.1 呈现层可引用的字段清单（引用契约）

进度数据在 Step 2 采集后由引擎一次性产出，**是报告中一切进度数字的唯一来源**。呈现层可引用的字段如下（字段名以引擎输出 schema 为准；引擎调整字段名时同步本表，呈现层**永不**改为自行计算）：

| 引用路径 | 含义 | 主要呈现位 | 无依据时引擎给出的值 |
|----------|------|-----------|---------------------|
| `baseline` | 基准日（`D0`，yyyy-mm-dd，即 `--baseline` 入参） | 各章"截至 <日期>"、图题、元信息 | 必有（由调用方传入） |
| `gantt.today_offset_days`（配 `gantt.title_baseline` / `gantt.today_directive`） | today 参照线相对项目起点的偏移天数 | 甘特 `today is <N> days after start` | `null`（无项目起点 → 不画 today 线） |
| `project.progress.progress_pct` | 项目整体完成度百分比 | 项目概览摘要、任务进展叙述、图说结论 | `null` |
| `project.progress.formula` | 整体完成度算式串（**自带分子/分母与百分比**，逐字照抄） | 与百分比同处（写成 `分子/分母 = 百分比%`） | `null`（此时整体句退化为状态计数句） |
| `project.progress.basis` + `coverage.progress_denominator_set` | 分母口径描述串（如"checks（不含 deferred）"；覆盖范围串见 coverage） | 摘要脚注、元信息、§11.3 分母集合声明 | 说明串（如"无可计数依据"） |
| `project.status_counts`（按 `completed` / `in-progress` / `not-started` / `unknown` / `deferred` 键取） | 完成度分布计数 | 各章计数句、状态分布表 | 各桶整数（缺键即 0） |
| `project.counts.work_items`（另有 `items` / `leaves` / `milestones` 等口径） | 参与统计的条目总数 | 计数句、覆盖声明 | 整数 |
| `project.schedule_state` | 排期总判断枚举（`on-track` / `behind` / `unknown-schedule`） | 各章进度判断句 | `unknown-schedule` |
| `project.delay_days_max`（里程碑侧用 `milestones.delay_days_max`） | 最大逾期天数 | 概览判断句、里程碑汇总、进度叙述 | `null` |
| `project.counts.delayed`（明细见 `project.delayed_items[]`） | 逾期条目数 | 概览摘要表、进度叙述、甘特图说结论 | 整数（可为 0） |
| `project.current_phase` | 当前所处阶段名 | 概览判断句、进度叙述 | `null` |
| `project.progress_bar`（条目/分组各有 `progress_bar`，里程碑达成率用 `milestones.achieved_bar`） | 引擎渲染的定宽字符进度条串（`█`/`░`，10 格） | 概览摘要、达成率表（**字段非空则必出、为空则不出**，见 3.1） | `null` → 不画进度条 |
| `milestones.counts.{achieved,at_risk,pending,unknown_schedule,total}` | 里程碑达成 / 逾期或风险 / 待达成 / 无计划日期 / 总数（叙述句可直接照抄 `milestones.narrative`） | 概览摘要表、里程碑汇总表 | 整数（无里程碑时全 0） |
| `milestones.achieved_pct` + `achieved_numerator` / `achieved_denominator`（算式串 `achieved_formula` 逐字照抄） | 里程碑达成率及其分子分母（分母不含 `unknown-schedule`） | 里程碑汇总表、概览摘要 | `null` |
| `groups[].{id,name,status,progress_pct,progress_formula,progress_bar,planned_start,planned_end,schedule_status,delay_days}` | 分组（阶段 / 主题）聚合进度（算式串自带分子分母） | 功能分解阶段聚合行、任务进展分阶段进度表 | `progress_pct=null` |
| `items[].{id,name,type,parent,status,schedule_status,progress_pct,progress_formula,progress_bar,planned_start,planned_end,actual_start,actual_end,delay_days,anchor_date,evidence}` | 条目级进度（`type` 区分 feature / work-item / phase / milestone，`parent` 承载层级） | 特性清单表、工作项进度表、里程碑跟踪表 | `progress_pct=null`、`delay_days=null` |
| `items[].evidence` | 该条目进度/状态的依据串（出处） | 表格「依据」列 | 说明串 |
| `thresholds` | 本次运行生效的判定阈值（材料过弱 / 里程碑视图独立成图 / 甘特拆分下限） | **只**在 `## 元信息 · 进度数据来源` 登记（见第 7 节） | 必有（引擎常量） |

- **调用与落盘**：调用命令、输入参数、输出文件位置登记在 `## 元信息 · 进度数据来源`（见第 7 节），并按 [consistency-rules.md](consistency-rules.md) §7.1 在 `## 元信息 · 统计口径` 为每个引用字段登记一行（「指标定义」列写字段名，「采集命令」列写引擎调用命令）。
- **字段名不进报告正文**：字段名是内部标识，只允许出现在本 `references/` 与 `## 元信息`；面向读者的五个章节里出现的是**数值本身**（读者用语纪律见 [reporting-playbook.md](reporting-playbook.md) §1.7）。

### 1.2 引用纪律（五条，违反即缺陷）

1. **指名可查**：报告中每个进度数字都能在进度数据里指名到一个字段；指不出来的数字一律删除或回引擎补算。
2. **原样引用**：数值**原样落笔**，不二次四舍五入、不改精度、不换算单位（引擎给 `62` 就写 `62%`，给 `61.5` 就写 `61.5%`）。
3. **零算术**：呈现层不做加减乘除、不做日期先后比较、不做天数差；需要新的聚合口径就**回引擎加输出字段**，不在报告里现场算。
4. **同源同值**：同一实体的进度在任何章节都引用**同一个字段**，落笔字面量完全相同（第 5 节门禁）。
5. **诚实空值优先**：字段为 `null` 时走第 6 节降级终态，**绝不**代之以 `0%`、"约一半"或任何占位数字。

---

## 2. 五章节进度呈现位总表（本规范的骨架）

每一行都是**必做项**：该章节没有对应的进度呈现要素即视为骨架不完整（落盘检查单设门禁）。

| 章节 | 进度呈现位（固定位置） | 形态 | 引用字段 | 缺失时（字段 `null`） |
|------|------------------------|------|----------|----------------------|
| `## 项目概览` | 章节末固定小节 `### 整体进度摘要` | ① 整体完成度句 ② 一句进度判断 ③ 进度概览表（4 行）④ 进度条（引擎给 `progress_bar` 则必出、未给则不出） | `project.*`（含 `milestones.*`） | 保留小节，完成度写 `-（无可计数依据）`，判断句改"无排期依据"式，概览表只留可计数行 |
| `## 需求与特性` | ① 开篇量化句 ② 特性清单表新增**进度%** 列 | 一句 + 表格列 | `project.status_counts`（量化句）、`items[type=feature].progress_pct`（列） | 量化句只报状态计数；进度列整列写 `-（无可计数依据）` |
| `## 功能分解` | WBS 图说结论句 + 固定小节 `### 工作项进度`（含**阶段聚合行**） | 表格（工作项级 + 阶段级两段）+ 图说一句 | `items[type=work-item/phase]`、`groups[]` | 表保留，进度列 `-（无可计数依据）`；图说结论改状态计数句 |
| `## 项目里程碑` | ① 里程碑进度汇总表（达成率 / 已达成 / 逾期 / 待达成 / 最大逾期天数）② 跟踪表新增**达成进度**、**延期天数**列 ③ 达成叙述带百分比 | 汇总表 + 跟踪表列 + 一句叙述 | `milestones.*`（counts / achieved_* / delay_days_max）、`items[type=milestone].delay_days` | 无里程碑材料时按 [degradation.md](degradation.md) 第 4 节整节退化为声明，**不出汇总表**（不写 0% 达成率） |
| `## 任务进展` | 甘特图 + 固定小节 `### 进度叙述`（整体完成度 / 分阶段进度表 / 完成度分布 / 逾期条目数） | 三段叙述 + 分阶段进度表 | `project.*` + `groups[]` | 甘特不出图时（degradation 第 5 节）本小节仍保留，只报状态计数与声明句 |

- **进度呈现位不额外造图**：进度概览表、工作项进度表、里程碑汇总表、分阶段进度表都是 **Markdown 表格**，不新增 PlantUML 图（图内进度编码沿用既有四张图的图形编码规范）。
- **`### 整体进度摘要` / `### 工作项进度` / `### 进度叙述` 三个小节标题是骨架契约**，与 `### 人员与分工` 同级同性质：材料缺失时**保留标题**、章节体退化为声明，不删小节。

---

## 3. 逐章节呈现模板（可直接套用；`<…>` 落盘时替换为数值）

> **模板中的 `<project.xxx>` / `<milestones.xxx>` 等只是本文档的取值标注**（路径以引擎输出 schema 为准），落盘时替换为纯数值，**字段名不得进报告正文**。

### 3.1 `## 项目概览` · `### 整体进度摘要`（当前最大缺口）

````markdown
### 整体进度摘要
**整体完成度：<project.progress.formula（自带分子/分母 = 百分比%）>（截至 <baseline>）**
<进度判断句：由 project.schedule_state 按 §4.2 映射；behind 时追加"最长逾期 <project.delay_days_max> 天"；current_phase 非空时追加"当前处于 <project.current_phase>"）>

| 进度视角 | 当前值 |
|----------|--------|
| 整体完成度 | <project.progress.formula（自带分子/分母 = 百分比%）>（口径：<project.progress.basis>）|
| 工作项分布 | 已完成 <status_counts.completed> / 进行中 <status_counts.in-progress> / 未开始 <status_counts.not-started>（共 <project.counts.work_items>）|
| 里程碑达成 | <milestones.achieved_formula>（逾期 <milestones.counts.at_risk> 个，待达成 <milestones.counts.pending> 个）|
| 逾期情况 | 逾期条目 <project.counts.delayed> 项，最长逾期 <project.delay_days_max> 天 |

<进度条（引擎输出 project.progress_bar 时**必出**、未输出则整行不写）：`<project.progress_bar>` <project.progress.progress_pct>%>
````

- 摘要**放在章节末**（背景 → 目标 → 范围 → 进度摘要），让读者读完"项目是什么"立刻看到"做到哪了"。
- **进度条的呈现是确定性的、不是「可选」**：引擎输出了 `project.progress_bar`（或对应条目/分组/达成率的 `progress_bar` / `achieved_bar`）⇒ **必须**原样嵌入；引擎未输出该字段 ⇒ **一律不呈现**（只写 `NN%`）。**不得**在报告里按百分比自行摆格子（那是计算），也不得在字段存在时凭喜好省略。
- 表格四行是固定视角；某行的字段全为 `null` 时该行值写 `-（无可计数依据）`，行不删（缺失即可见信息）。

### 3.2 `## 需求与特性` · 开篇量化句 + 进度列

````markdown
## 需求与特性
<开篇量化句：共 <特性口径条目总数> 项特性，已完成 <status_counts.completed> 项、进行中 <status_counts.in-progress> 项、未开始 <status_counts.not-started> 项；特性维度完成度 <feature_numerator>/<feature_denominator> = <feature_pct>%（截至 <baseline>）。>

| 特性 | 来源 | 状态 | 进度% | 负责人 |
|------|------|------|-------|--------|
| <items[].name> | <items[].evidence> | <status 按 §4.2 映射> | <items[].progress_pct>% | <结构 D 规范名 / 未记录> |
````

- 「进度%」列固定在「状态」列之后；`progress_pct` 为 `null` 的行写 `-（无可计数依据）`——**不写 0%**，也不因无进度就删列。
- 状态列仍是三态读者用语（§4.2 映射），**进度列不替代状态列**：状态回答"处于哪一档"，进度回答"到什么程度"。
- 特性维度完成度取引擎在特性口径上的汇总字段（`type=feature` 条目/分组的聚合）；无该口径时整句退化为状态计数句。

### 3.3 `## 功能分解` · `### 工作项进度`（含阶段聚合）

````markdown
### 工作项进度
**阶段级聚合**

| 阶段 | 状态 | 进度% | 已完成/共计 | 逾期天数 |
|------|------|-------|-------------|----------|
| <groups[].name> | <status 映射> | <groups[].progress_pct>% | <groups[].progress_numerator>/<groups[].progress_denominator> | <groups[].delay_days> |

**工作项级**

| ID | 工作项 | 所属阶段 | 状态 | 进度% | 计划起止 | 逾期天数 | 依据 |
|----|--------|----------|------|-------|----------|----------|------|
| <items[].id> | <items[].name> | <groups[].name> | <status 映射> | <items[].progress_pct>% | <items[].planned_start> ~ <items[].planned_end> | <items[].delay_days> | <items[].evidence> |
````

- 本小节紧随 WBS 图说、位于 `### 人员与分工` **之前**（读者顺序：看结构 → 看进度 → 看谁负责）。
- WBS **图说的结论句必须带进度**：`<整体或本图范围的完成度句> + <逾期条目数句>`，数字与本表同字段同值。
- 阶段聚合行的分子分母原样引用 `groups[]`；阶段进度的**聚合口径由引擎实现**（等权/加权、是否排除未量化项），呈现层只在表下补一句口径说明串（取 `groups[].aggregation` 的口径信息或元信息口径行）。

### 3.4 `## 项目里程碑` · 进度汇总表 + 跟踪表进度列

````markdown
## 项目里程碑
**里程碑进度汇总**

| 指标 | 当前值 |
|------|--------|
| 达成率 | <milestones.achieved_formula（自带分子/分母 = 百分比%）> |
| 已达成 / 逾期 / 待达成 | <milestones.counts.achieved> / <milestones.counts.at_risk> / <milestones.counts.pending>（共 <milestones.counts.total>，另有无计划日期 <milestones.counts.unknown_schedule>）|
| 最大逾期天数 | <milestones.delay_days_max> 天 |

| 编号 | 里程碑 | 锚定 | 状态 | 达成进度 | 延期天数 | 负责人 | 依据 |
|------|--------|------|------|----------|----------|--------|------|
| <Mn> | <name> | <items[].anchor_date> | <status 映射> | <items[].progress_pct>%（引擎给 `progress_bar` 则必带格串、未给则只写 `NN%`） | <items[].delay_days> | <规范名 / 未记录> | <items[].evidence> |

<达成叙述：共 <milestones.counts.total> 个里程碑，已达成 <milestones.counts.achieved> 个（达成率 <milestones.achieved_formula>），逾期 <milestones.counts.at_risk> 个（最长 <milestones.delay_days_max> 天），待达成 <milestones.counts.pending> 个<，无计划日期 <milestones.counts.unknown_schedule> 个（无法判定延期）>。>
````

- 「达成进度」列取 `items[].progress_pct`（进度条格串取引擎 `progress_bar`，无该字段则只写 `NN%`），`null` 写 `-（无可计数依据）`；「延期天数」列取 `items[].delay_days`，字段为 `null` 的行写 `-`；**报告里不出现任何日期相减、任何格数换算**——数值来自引擎。
- 汇总表在跟踪表**之前**（先给结论、再给明细），用户明确要求的"里程碑/目标描述里加百分比、进度表格"由这张表承载。
- 里程碑材料完全缺失时按 [degradation.md](degradation.md) 第 4 节：**不出汇总表**（写"达成率 0%"会把"没有里程碑"伪装成"一个都没达成"），只保留声明句与已检索来源。

### 3.5 `## 任务进展` · `### 进度叙述`

````markdown
### 进度叙述
**整体**：截至 <baseline>，整体完成度 <project.progress.formula>（口径：<project.progress.basis>）；<project.schedule_state 映射句>；当前处于 <project.current_phase>。

| 阶段 | 起止 | 状态 | 进度% | 逾期天数 |
|------|------|------|-------|----------|
| <groups[].name> | <groups[].planned_start> ~ <groups[].planned_end> | <status 映射> | <groups[].progress_pct>% | <groups[].delay_days> |

**完成度分布**：已完成 <status_counts.completed> 项、进行中 <status_counts.in-progress> 项、未开始 <status_counts.not-started> 项<、状态未知 <status_counts.unknown> 项><、本轮延后 <status_counts.deferred> 项>（共 <project.counts.work_items>）。
**逾期**：逾期条目 <project.counts.delayed> 项，最长逾期 <project.delay_days_max> 天。<无逾期时写：基准日左侧无未完成条目。>
````

- 本小节紧随甘特图说；甘特图说的结论句与本小节数字**同字段同值**。
- 分阶段进度表与《功能分解》的阶段聚合表引用**同一批 `groups[]` 字段**，两处数值必须逐字相同（第 5 节门禁）。

---

## 4. 进度叙述规范（文字里的百分比怎么写）

### 4.1 百分比写法（与既有 CG-4 一致）

- 固定形态 `<分子>/<分母> = <百分比>%`，三个值分别取 `*_numerator` / `*_denominator` / `*_pct`——呈现层**只拼字符串，不做除法**。
- 分母口径以 `project.progress.basis` / `coverage.progress_denominator_set` 串补在括注或表格同格内（如"（口径：分解树覆盖的 38 项特性，不含已剔除 2 项）"）；分母集合与分解树覆盖范围的一致性声明见 [consistency-rules.md](consistency-rules.md) §11.3，其数值同样引用引擎字段。
- **精度原样**：引擎给整数写整数、给一位小数写一位小数；同一字段在各章精度必须相同（同源同字面量）。
- 天数写 `逾期 <delay_days> 天`；逾期短语**只在引擎给出逾期枚举**（`schedule_state = behind`、里程碑 `status = at-risk` 且 `delay_days` 非空）时出现，天数原样引用。

### 4.2 枚举 → 读者用语固定映射（纯查表，无阈值判断）

状态词与进度判断句**不由百分比推导**（那是判断/计算），一律由引擎输出的枚举查下表得到：

| 引擎枚举值 | 报告正文固定措辞 |
|------------|------------------|
| `status = completed` | 已完成 |
| `status = in_progress` | 进行中 |
| `status = not_started` | 未开始 |
| `status = unknown` | 状态未知（材料无状态信号） |
| `status = deferred` | 本轮延后 |
| `status = achieved`（里程碑） | 已达成 |
| `status = pending`（里程碑） | 待达成 |
| `status = at-risk`（里程碑） | 逾期 / 有风险（逾期类追加 `逾期 <delay_days> 天`） |
| `schedule_state = on-track` | 进度贴合计划 |
| `schedule_state = behind` | 落后于计划（追加"最长逾期 `<delay_days_max>` 天"） |
| `schedule_state = ahead` | 快于计划 |
| `schedule_state = unknown-schedule` | 无排期依据，进度未与计划比对 |

- 状态词与百分比**搭配写法**：`<状态词>（<分子>/<分母> = <百分比>%）`，如"进行中（12/20 = 60%）"；进度为 `null` 时写"进行中（进度未量化）"。
- **不得**用百分比自行改写状态词（如把 100% 写成"已完成"而引擎 `status` 仍是 `in_progress`）——状态只认 `status` 字段；两者矛盾时回引擎，不在报告里调和。

### 4.3 禁用写法清单（出现即缺陷）

| 禁用 | 原因 | 改成 |
|------|------|------|
| `约 45%` / `大概一半` / `过半` / `九成` | 模糊修饰=文档内二次判断 | 原样引用 `<pct>%` |
| 裸 `<pct>%`（无分子分母） | 违反 CG-4 | `<分子>/<分母> = <pct>%`（**示例**：`1106/1241 = 89.1%`——数值随项目而变，一律照抄引擎算式串） |
| `0%`（用于"没数据"） | 把"无依据"伪装成"零进展" | `-（无可计数依据）` |
| `逾期约一周` / 自己算的天数 | 报告内做日期算术 | `逾期 <delay_days> 天` |
| `进度过半，预计下月完成` | 无字段支撑的预测 | 只写引擎给出的字段；预测需材料依据并标 `（推断）` |
| 字段名进正文（`progress_pct`、`delay_days`） | 内部标识渗入（§1.7） | 只写数值 |

---

## 5. 跨章节进度口径一致（必须同值同源）

同一实体的进度在不同章节多次出现，**必须引用引擎同一字段、落笔同一字面量**。清单如下：

| 实体 / 指标 | 出现章节 | 唯一字段来源 |
|-------------|----------|--------------|
| 项目整体完成度 | 项目概览摘要、任务进展叙述、甘特图说结论 | `project.progress.progress_pct`（分子分母见 `formula` 串） |
| 完成度分布计数 | 项目概览摘要、需求与特性开篇句、任务进展叙述 | `project.status_counts` |
| 特性 X 的进度 | 需求与特性表、（该特性作为工作项时）功能分解表 | `items[id=X].progress_pct` |
| 阶段 P 的进度 | 功能分解阶段聚合行、任务进展分阶段表、WBS/甘特图说 | `groups[id=P].progress_pct` |
| 里程碑达成率 | 项目概览摘要、里程碑汇总表、达成叙述 | `milestones.achieved_pct` / `achieved_formula` |
| 逾期条目数 / 最大逾期天数 | 项目概览摘要、任务进展叙述、甘特图说 | `project.counts.delayed` / `project.delay_days_max` |
| 单条目逾期天数 | 里程碑跟踪表、工作项进度表 | `items[].delay_days` |
| 基准日 | 各章"截至"、图题、元信息 | `baseline`（与 `## 元信息 · 生成日期` 同值，见 [consistency-rules.md](consistency-rules.md) §0） |

**三条纪律**：

1. **同值**：同一指标在各章的数字字面量完全相同（含精度与分子分母）。
2. **同源**：不允许某一章"另算一个更好看的口径"；需要第二种口径必须另起字段并在两处并列说明差异（口径登记见第 7 节）。
3. **不得人工调平**：发现两处不一致，**回引擎重取并重新替换全部呈现位**，禁止手改其中一处使其"看起来一致"。

**门禁执行方式**：本条为落盘门禁「跨章节进度口径一致」（[reporting-playbook.md](reporting-playbook.md) §5、§7 各一条）。**校验由脚本承担**——因为所有进度数字都来自引擎同一字段，脚本只需比对报告中同一指标的多处引用字面量是否相同、以及是否与引擎输出一致；**本文档不给核对算法**，人工不做算术复核，不一致即 FAIL、不得放行。

---

## 6. 无进度数据时的诚实降级（与 [degradation.md](degradation.md) 协同）

引擎输出 `progress_pct = null`、`schedule_state = unknown-schedule`、`delay_days = null` 时，各章节的进度呈现位**保留、内容诚实降级**——这与 degradation.md 第 3 节「五类禁造物」的合法终态 `-（无可计数依据）` 完全一致，不新增终态、不放宽禁造门禁。

| 呈现位 | `progress_pct = null` 时 | `schedule_state = unknown-schedule` 时 |
|--------|--------------------------|----------------------------------------|
| 概览 `### 整体进度摘要` | 完成度行写 `-（无可计数依据）`；分布行照常（状态计数与进度无关） | 判断句写"无排期依据，进度未与计划比对"；逾期行写 `-` |
| 概览进度条 | 不呈现（引擎不输出 `progress_bar`） | 同左 |
| 特性表「进度%」列 | 整列 `-（无可计数依据）`（列不删） | 不影响 |
| 功能分解阶段/工作项表「进度%」列 | 同上；表下补一句"本项目无可计数进度依据，仅报状态" | 「逾期天数」列全 `-` |
| 里程碑汇总表 | 无里程碑材料 → 整表不出（degradation 第 4 节）；有里程碑但无达成/逾期依据 → 达成率写 `-（无可计数依据）` | 「最大逾期天数」写 `-` |
| 任务进展 `### 进度叙述` | 整体句改为"进度未量化，仅报状态计数：已完成 <counts.completed> 项 / 进行中 <counts.in_progress> 项 / 未开始 <counts.not_started> 项"；甘特条不写完成百分比 | 阶段表「逾期天数」全 `-`；不写"贴合计划"或"落后" |

**降级三条纪律**（与 degradation.md 一致，不冲突）：

1. **不造数**：`null` 一律落 `-（无可计数依据）`，**不写 0%**、不写"约"、不用状态计数反推百分比。
2. **缺失可见**：每处进度降级都要落到 degradation.md 第 2 节的三个声明位之一——章节内 `> 材料声明：`、图内 `caption`/图说首句、`## 元信息 · 材料缺口`；`### 材料缺口` 表里"进度百分比"一行必须在场。
3. **状态不受连带降级**：进度无依据**不等于**状态无依据。`status` 仍照常呈现（`unknown` 才是状态无依据的终态），`未知` 与 `not-started` 不得混用。

---

## 7. `## 元信息 · 进度数据来源`（固定小节）

进度数字来自引擎，因此**引擎调用必须可复核**。`## 元信息` 内新增固定小节：

````markdown
### 进度数据来源
- 基准日 D0：<baseline>（与生成日期一致）
- 引擎调用：`python3 ${SKILL_HOME}/scripts/progress-engine.py --db data/project.db --baseline <baseline> --out data/engine-out.json`
- 本次生效阈值：<照抄引擎输出 `thresholds`（材料过弱下限、里程碑视图独立成图下限、甘特拆分下限）——阈值只存放在引擎里，此处只登记本次取值供读者复核；报告正文不出现这些数字>
- 分母口径：<project.progress.basis> + <coverage.progress_denominator_set>（与分解树覆盖范围一致，见「分解树覆盖」）
- 未量化条目：<progress_pct 为 null 的条目数> 项（已在各章以 `-（无可计数依据）` 呈现）
- 字段 → 呈现位对照：<project.progress.progress_pct → 项目概览摘要/任务进展叙述；groups[].progress_pct → 功能分解阶段行/任务进展阶段表；…>
````

- 每个引用字段还须按 [consistency-rules.md](consistency-rules.md) §7.1 在 `## 元信息 · 统计口径` 表登记一行（口径 ID、指标定义=字段名、采集命令=引擎调用、范围、采集日），满足 CG-9。
- 本小节是**内部标识的合法落点**：字段名、脚本名只出现在这里与技能内部文档。

---

## 8. 落笔检查（进度维度，落盘前必过）

- [ ] 五个章节**各自**的进度呈现位齐全（§2 总表逐行核对）：概览 `### 整体进度摘要`、特性表进度列 + 开篇量化句、功能分解 `### 工作项进度`（含阶段聚合行）、里程碑进度汇总表 + 跟踪表「达成进度」「延期天数」列、任务进展 `### 进度叙述`
- [ ] 报告中每一个进度数字都能指名到进度数据的一个字段（`## 元信息 · 进度数据来源` 有字段 → 呈现位对照）
- [ ] 报告正文与本 `references/` 文档中**无任何进度/日期计算**：无除法算式描述、无日期先后判定、无天数差算法（数字一律"取引擎字段"）
- [ ] 所有百分比为 `分子/分母 = xx.x%` 形态且分母口径已给出；精度与引擎输出一致（无二次舍入）
- [ ] 状态词与进度判断句均由 §4.2 枚举映射得出，未由百分比自行推导；`status` 与百分比无矛盾
- [ ] §4.3 禁用写法零出现（无"约/大概/过半/九成"、无裸百分比、无用 0% 表示无数据、无自算天数、无字段名渗入正文）
- [ ] **跨章节进度口径一致**（§5 清单逐行）：同一指标各处同值同源同精度；不一致已回引擎重取，未人工调平
- [ ] `null` 类字段已按 §6 降级为 `-（无可计数依据）`，并落到三个声明位之一；`### 材料缺口` 含"进度百分比"一行
- [ ] 进度条仅在引擎输出 `progress_bar` 时呈现，且为原样引用（未自行按百分比绘制）
- [ ] `## 元信息` 含 `### 进度数据来源` 小节，且各引用字段已在 `## 元信息 · 统计口径` 登记（CG-9）
- [ ] 基准日在各章"截至"表述、图题与元信息中同值（CG-8）
