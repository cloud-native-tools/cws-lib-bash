# 批评和自我批评 (Critique and Self-Critique) — 改进提案的证伪纪律

本文件是改进流程头部**批评步骤**的唯一真源(single source of truth):证伪尝试(Falsification Attempt)的输出形态、可采纳判据、拒绝形态、判定处置、自我批评半侧规则、失效模式→规则映射、与相邻机制的边界都只在此定义。流程落点是 `.specify/shared/workflow/self-improvement-workflow.md` SI-3C;消费者 MUST 以路径引用本文件,MUST NOT 复述其规则——复述即第二定义点,会各自漂移。导览面见 `docs/concepts/critique-and-self-critique.md`。

**本纪律防的失效是「未经批评的改进」**:提案基于散文描述进入执行,从未与可判定的事实对质。三种实测形态(均在本仓发生,锚点见 § 失效模式与规则映射):**盲目改进**(前提读自散文,实现抵达时才被证伪)、**反复改进**(目标与判据被反复重切,重切本身从未被批评)、**越改越差**(已分流未执行的修复并不静止,错误主张反而扩散)。目的取自用户原话:通过更辩证的思索避免这三种形态。

## 在流程中的位置

- 批评步骤跑在 improve 流程的头部:SI-3 诊断产出拟议干预之后、SI-4 路由派发之前。**未经批评的提案 MUST NOT 进入派发**——提案在路由那一刻才算「被提出」,批评必须发生在那之前。
- 提案 = 任何一处拟落地的改动,**包括对改进流程自身判据、目标与既有裁定的重切**:重切本身即一条提案,同样受批评(这是反「反复改进」的落点)。
- 批评步骤消费 SI-2 冻结的候选与 SI-3 的诊断结论;它不产生新候选,不重新给证据定级(那归 SI-2 与 `.specify/shared/workflow/evidence-step.md`)。

## 输出形态:每个提案一条证伪尝试

对每条提案,批评步骤 MUST 产出**一条证伪尝试**:点名一个具体、可执行的测量或检查,它运行后能表明两件事之一——

1. **(a) 前提为假**:提案所依赖的前提不成立;或
2. **(b) 改动使事情变糟**:改动使其对象可测地更差。

每条 MUST **可判定**:点名文件、grep、测试或测量,使第二位复核者执行后得出同一 verdict。这与 `.specify/shared/guidelines/user-facing-comprehension.md` § 机械判据是同一可复现标准,与 `.specify/shared/guidelines/fast-fail.md` § 判据同样覆盖机器给出的绿 是同一证据标准——两处均以路径引用,不复述。

**代码优先规则**:前提关乎「系统实际如何行为」时,证伪尝试 MUST 指向决定该行为的代码或配置,MUST NOT 指向描述它的散文(与 `.specify/shared/guidelines/one-source-of-truth.md` 的 owner 选择序同向:code 先于文档)。两起盲目改进实测的共同根因即裁定读自散文描述而非决定它的代码。

**形态先例**:证伪尝试与 Derivation Step 的 `falsification` 字段(真源 `.specify/shared/definitions/derivation-definitions.md`)**同构而对象不同**(改进提案 vs 推导步骤),属房内有既形态,不是第二套词汇。

### 可采纳判据(封闭集,四条全满足)

1. **可执行**——点名一位复核者能直接运行的路径/命令/测试/测量;
2. **可判定**——结果二值:证伪,或未证伪;
3. **有界**——一次定向检查即可完成,不是开放式全量审计;
4. **指向**——瞄准 (a) 该提案的前提或 (b) 该改动的回归,不是一般性观感。

### 拒绝形态(封闭清单,命中即拒)

- 「考虑是否…」「注意…风险」「可能影响…」——无指向的关切陈述;
- 一般性风险清单、利弊叙事——不可执行,无 verdict;
- 需要通读整份散文才能执行的条目——散文裁决正是本纪律要防的根因;
- 「等实现之后再看」——证伪尝试 MUST 在派发前可运行;只能在派发后运行的属 SI-6 验证,不属批评。

## 判定与处置

- 证伪尝试在**派发前执行**;执行按 Program-First(`.specify/shared/guidelines/token-efficiency.md`):grep/测试/引擎输出作判定,模型不代程序重读散文。
- **前提被证伪 ⇒ 提案 void**:MUST NOT 派发,MUST NOT 绕开被证伪的前提改写后重派。void 不折算为「未达成」——该区分与门控前提衰变的 void/unmet 处置同构(真源 `.specify/shared/workflow/feature-integration.md` § Pre-Status-Flip Gate),引用不复述。
- **未被证伪 ⇒ 判定随提案同行**:尝试本体与 verdict 记在提案已有的载体里(SI-4 派发载荷、SI-7 intervention 记录)。**MUST NOT 为批评新建台账、注册表或存储**——与 SI-7 "do not create a parallel self-improvement database" 及 fast-fail § 点名拒绝的四类机制同向。
- **交接判据**:未携已执行证伪尝试的提案,接收方(improver)MUST 拒收;尝试之缺失本身就是可判定的拒收条件。这是「已分流未执行」死信的拦截规则(见映射表 · 越改越差)。
- **仪表自检**:提案以改进流程自身仪表的输出为证据时,其证伪尝试 MUST 含一条对该仪表覆盖面的定向检查(计数是否被静默截断);手法沿用反空真哨兵(定义归 `.specify/shared/guidelines/fast-fail.md` 所引真源),不重新发明。

## 自我批评半侧

流程 MUST 批评自己的既有产出,形态与批评外部提案完全相同:

1. **列继承前提**:提案依赖的、由本流程此前产出的裁定/判据/干预(改点(Change Point)记录与 intervention.json 等,各自形态归其真源)逐项列出;
2. **每条继承前提一条证伪尝试**:点名能表明该记录已不成立的可执行检查;代码优先规则同样适用;
3. **自我证伪即断链**:继承前提被证伪时,引用它的提案 MUST 停止推进,处置按 § 判定与处置;停下来之后怎么走,由 `.specify/shared/guidelines/fast-fail.md` 的纠正/裁定二值判据决定——本纪律不重定义它;
4. **同作者委派**:提案与批评出自同一会话/作者时,证伪尝试的执行 MUST 按 `.specify/shared/workflow/objective-analysis-gate.md` 委派给新鲜上下文的只读子代理;本纪律不复述其触发条件与门规则。

## 失效模式与规则映射

| 失效模式 | 对策规则 | 实证锚点(实测于本仓) |
|---------|---------|---------|
| **盲目改进**:前提读自散文,实现抵达时才被证伪,各耗一次派发 | 代码优先规则 + 派发前执行 | `.specify/scripts/python/trigger-utils.py:289-301` `shape_telemetry_row` 返回封闭七键字典,承载不了「未解决红状态」;`.specify/scripts/python/memory-utils.py:28` `SCOPES` 封闭、`slugify`(:53)剥除 `/`、`action_reindex`(:436)非递归 glob——「session 专用子目录」裁定无引擎路径可达 |
| **反复改进**:判据与目标一轮内被反复重切,核心术语三迁 | 重切本身即提案(§ 在流程中的位置)+ 自我批评半侧第 1–2 条 | `.specify/goal/session-driven-self-improvement/goal.md` § History:2026-10-05 单轮留下 4 次判据变更 + 2 次 objective 变更;核心术语经 断言 → 判断逻辑 → 运行判定 三迁 |
| **越改越差**:已分流未执行的修复反而扩散;流程自身仪表静默少报 | 交接判据(缺失即拒收)+ 仪表自检 | F-A02:2026-09-11 `.specify/memory/feedback/consume-log.md` 分流给 improve-skills 后从未执行,同一错误主张自 `.specify/skills/internal/create-agent/SKILL.md:122,127` 扩散进 `.specify/templates/commands/agents.md:25`(现行渲染器 `src/specify_cli/__init__.py:618` 明写 "Real files only (no symlinks)");`.specify/scripts/python/feedback-utils.py:1883` `--limit` 缺省 5,而 `.specify/templates/commands/feedback.md:46` 的 inventory 调用未传 `--limit 0`,open 条目被静默截断 |

## 边界(本纪律不做什么)

- **不新增用户确认流程**:批评步骤的「停」只发生在证据判定上(前提被证伪 ⇒ void),不产生任何面向用户的确认提示,不向 `.specify/shared/guidelines/confirmation-gates.md` 的治理保留清单增行,不触及其判据。
- **不替代 Fast Fail 的纠正/裁定二值**:本纪律裁**派发前**的提案资格;fast-fail 裁**执行中**的异常分流。同一前提若在执行中才被发现为假,仍按 fast-fail 处置。二者时点相邻、互不重叠。
- **不另立继承前提的复测义务**:行动前对继承前提的复测义务归 `.specify/templates/instructions-template.md` § "Fact, Correctness & Logic Checks (Input Sanity)";本纪律只规定该复测在 improve 流程头部的**形态**(证伪尝试)与**时点**(派发前),不放宽也不收紧其升级规则。
- **不是第二个 feedback 存储**:判定记在提案已有载体,不建新存储、不加 probe;`.specify/shared/workflow/feedback-step.md` § Positioning & Red Lines 不受影响。
- **不重定义证据状态**:候选资格与 evidenceState 归类归 SI-2 与 evidence-step;本纪律只回答「提案经一次证伪后是否仍值得落地」。
- **不新增引擎**:MUST NOT 引入批评引擎、评分器、成熟度报告或跟踪台账;判定由 agent 按上述判据执行,可执行部分交既有确定性程序(Program-First)。

## 消费者清单

| 消费者 | 引用方式 |
|--------|---------|
| `.specify/shared/workflow/self-improvement-workflow.md` SI-3C | 流程落点:短规范步骤 + 指向本文件,不复述规则 |
| `improve-*` 技能族(SI-4 接收方) | 交接判据:派发载荷缺已执行的证伪尝试即拒收 |
| `docs/concepts/critique-and-self-critique.md` | 导览面:定位与失效模式概览,一切细节以路径引用本文件 |
| 改进判据/目标的重切提案 | 重切本身即提案:携对被重切记录的证伪尝试进入批评 |
