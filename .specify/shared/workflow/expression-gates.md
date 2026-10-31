# Expression Gates — 文档型门禁算子集

**Owner（唯一所有者）**: 本文件 `.specify/shared/workflow/expression-gates.md` 是「文档型门禁」的唯一所有者。
它拥有：**封闭六面清单（face id + owner_pointer）、逐阶段算子表、阻断级别、读者声明形态、证据等级与 as-of 语法、三项基线协议、算子去重、阶段不变量、调用点表、调用时机与降级**。

**面数 = 6**（封闭集）。新增面须由后续特性修订本 owner，MUST NOT 由消费方就地扩面；六面之外 MUST NOT 出现第七面。

除「证据分级与 as-of」一面由本文件新增并自持判据外，其余五面的判据句归各自 `owner_pointer`。本文件只登记指针与「在哪一阶段、由哪个入口、以什么阻断级别」执行，**不复述**这些 owner 的判据正文；命令模板与技能 MUST NOT 复制本文件的面表、算子表或调用点表。

**机器键与取值**: 类别键 `flow_class`（[[STR-003]]）、两取值 `execution` / `expression` 的判据与台账唯一所有者是 `.specify/shared/definitions/flow-class-definitions.md`；本文件只登记「读取**动作**」与「归口」，不登记任何单元的类别取值。

## 六面（封闭集）

每面登记且仅登记一个 face id 与一个 `owner_pointer`（路径，必要时带 `§` 章节锚；owner 是整文件纪律文档时不加锚）。同一面出现第二个 face id 或第二个 owner_pointer 即第二副本，按缺陷处理。

| 面（中文） | face id | owner_pointer |
| --- | --- | --- |
| 需求清晰度 | requirements-clarity | `.specify/scripts/python/validate-requirements.py` + `.specify/shared/guidelines/requirements-guidelines.md` § Specification Quality Validation |
| 读者/目的/边界 | reader-purpose | `.specify/shared/guidelines/user-facing-comprehension.md` § 基准读者与覆盖协议 |
| 证据分级与 as-of | evidence-asof | `.specify/shared/workflow/expression-gates.md` § 证据分级与 as-of |
| 结构/链接/构建 | structure-links-build | `.specify/skills/create-docs/SKILL.md` § Desired-State Baseline + `.specify/skills/create-docs/scripts/docs-utils.py` |
| 事实一致性 | fact-consistency | `.specify/shared/guidelines/one-source-of-truth.md`（整文件即判据，无单章节锚） |
| 评审 | review | `.specify/skills/internal/review-sdd-process/SKILL.md` § Workflow + `.specify/templates/review-template.md` |

## 阶段算子表

八个阶段各至少一行：阶段、算子 id、执行算子（可执行入口或点名的既有流程）、对应面、阻断级别。任一阶段无算子即失败；算子行不得是空表头行。
`算子 id` 是稳定标识（`G-…`，全表唯一），供分类 owner 映射表的 `强制门禁引用` 列以 `gate:<算子 id>` 引用；id 变更即引用失效，两者 MUST 同步修订。

| 阶段 | 算子 id | 执行算子 | 对应面 | 阻断级别 |
| --- | --- | --- | --- | --- |
| requirements | `G-req-clarity` | `validate-requirements.py --spec-dir <spec dir>`（五项结构检查）+ `pre-analyze-check.py --stage requirements` | requirements-clarity | blocking |
| requirements | `G-req-evidence` | 证据三件套语法预检（`doc-consistency-check.py --faces evidence`） | evidence-asof | blocking |
| clarify | `G-clarify-clarity` | `pre-analyze-check.py --stage requirements`（仅在需求变更后重跑一次） | requirements-clarity | blocking |
| clarify | `G-clarify-reader` | 读者声明与阅读场景补齐（`doc-consistency-check.py --faces reader`） | reader-purpose | blocking |
| plan | `G-plan-fact` | `pre-analyze-check.py --stage plan`（事实唯一性与悬空引用一次比对） | fact-consistency | blocking |
| plan | `G-plan-structure` | 结构面复核（`docs-utils.py --action validate`，判据为零新增违规） | structure-links-build | blocking |
| tasks | `G-tasks-fact` | `pre-analyze-check.py --stage tasks`（计数判定，委派） | fact-consistency | blocking |
| tasks | `G-tasks-evidence` | 证据等级与 as-of 复核（`doc-consistency-check.py --faces evidence`） | evidence-asof | blocking |
| checklist | `G-checklist-reader` | 读者声明复核（`doc-consistency-check.py --faces reader`） | reader-purpose | blocking |
| checklist | `G-checklist-duplicate` | 跨文件手写副本（`doc-consistency-check.py --faces duplicate`） | fact-consistency | blocking |
| analyze | `G-analyze-fact` | `/speckit.analyze`（调用率 100%） | fact-consistency | blocking |
| analyze | `G-analyze-review` | 评审基线确认（`/speckit.review`，按读者基准判定） | review | blocking |
| implement | `G-implement-structure` | 结构/链接/构建（`docs-utils.py --action validate`，零新增） | structure-links-build | blocking |
| implement | `G-implement-reader` | 自然度与读者适配抽样（人工或受委托的评审代理） | reader-purpose | advisory |
| review | `G-review-review` | `/speckit.review`（调用率 100%，按读者基准判定） | review | blocking |
| review | `G-review-fact` | 事实一致性复核（`doc-consistency-check.py --action verify`） | fact-consistency | blocking |

## 阻断级别

- 六面中每一面 MUST 至少有一个 `blocking` 算子；该底线的作用对象是六面全集（`/speckit.docs` 调用点及其文档型特性路径）。
- 需求清晰度、事实一致性、评审三面 MUST 各至少一个 `blocking` 算子。
- 读者声明缺失 MUST 阻断：`reader-declaration-missing` 是 blocking，不是 warning。
- 不得把既有 P0/P1 判定降为 advisory；不得把表达类读作更宽松的通道。本门禁集只决定「用哪套算子证明同一不变量」，不新增、不放宽判定阈值。
- `skill:humanize` 调用点只执行 062 域最小算子集（见 § 调用点表），它不继承六面的阻断底线；那是另一条调用点行，六面表的行集合不适用于该行，也不因该行降低六面的阻断级别。

## 读者声明

- 文档型交付物 MUST 在其**前 40 个非空行**内声明两行：`**Readers**: <目标读者>` 与 `**Reading scenario**: <阅读场景与要做的决定>`。
- 两行任一缺失，或值为空，即 `reader-declaration-missing`（阻断）。
- 读者判定 MUST 沿用 `.specify/shared/guidelines/user-facing-comprehension.md` § 基准读者与覆盖协议 定义的基准读者；MUST NOT 新建第二套读者定义，本地覆盖按该 owner 的协议声明。

## 证据分级与 as-of

本面是本文件新增并自持判据的一面；对象是**文档断言**。

- 证据等级取封闭三值：`实测` / `推断` / `引用`。`as-of` 取 `YYYY-MM-DD`。
- **来源必填**：`实测` / `推断` 的 `source` 是可复算命令或退出状态，`引用` 的 `source` 是引文出处（URL / 文档路径 + 章节）。缺失或空值即 `source-missing`（阻断）。
- 三件套成组：一条事实性断言只要出现等级或 `as-of` 任一，等级、`as-of`、`source` 三项 MUST 同时到位。
- 行形态（机器可读，`doc-consistency-check.py` 的 `evidence` 面据此执行）：
  - 标记：一行只有出现标记 `证据：` 时才被视为带标注的断言行；无标记的行不进入本面语法判定。
  - 等级：标记后的第一个 token（到 `，` 或 `（` 或行尾）；不在封闭三值内 → `grade-invalid`。
  - `as-of`：写作 `as-of <YYYY-MM-DD>`；格式不符 → `as-of-malformed`；早于该文件最后一次提交日期 → `as-of-stale`。
  - 来源：写作 `source: <文本>`；缺失或空值 → `source-missing`；只有等级或只有 `as-of` → `grade-asof-unpaired`。
- 对象边界：本面描述**文档断言**。`.specify/shared/workflow/evidence-step.md` 的七态描述机制证据，`.specify/shared/guidelines/single-run-evidence.md` 描述一次执行的记录留存——两者的取值域 MUST NOT 被本面重定义、收窄或并入。

## 结构/链接/构建只是必要条件

- 结构、链接、构建通过 MUST NOT 被援引为内容正确性的证据；它们只是必要条件。
- 结构面判据 MUST 写成「零新增违规」：既有基线（2026-10-24 实测 `violations = 3` —— `broken-link` 2 + `note-frontmatter` 1）不因本特性被继承为失败，也不因本特性被顺手修复。
- 站点层不存在时，构建算子记为 `not-applicable`（显式），不得记为通过。

## 事实一致性

- 同一事实 MUST 只有一个所有者并以引用表达；≥ 2 处手写即缺陷。
- 修复方向 MUST 是改为对唯一 owner 的引用；不是把多处措辞改到一致。MUST NOT 靠改措辞使多处一致。
- 派生计数 MUST 由制品导出；手工计数 MUST 由既有计数判定（`pre-analyze-check.py`）报出，本门禁集 MUST NOT 自建第二套计数规则。
- 机械检测下限（本门禁集承认的让步）：归一化后完全相等且长度 ≥ 24 字符，或相似度 ≥ 0.90 且长度 ≥ 40 字符。低于下限的近副本不被机械报出，仍由评审面按事实唯一性判定；该下限 MUST NOT 被读作判据放宽。

## 评审

- 表达类的评审 MUST 保留，且 MUST 按声明的读者基准判定：判定者是人工评审者或受委托的评审代理，判定对象是读者能否理解并与外部事实相符。
- MUST NOT 复用代码评审的判定对象（编译、测试、覆盖率）；MUST NOT 由分类免除。
- 评审面 MUST 至少一条 blocking 算子，且在 analyze 与 review 两个阶段都在场。

## 三项基线

表达类特性 MUST 在开工前冻结三项实测基线（门禁调用次数、人工确认次数、requirements→analyze 墙钟），收尾逐项对照；基线缺失即不可验收。

| 量 | 既有通道（来源命令） |
| --- | --- |
| 门禁调用次数 | `exec-quant.py --action list-records --since <ISO> --format json`，按声明的门禁单元集过滤计数 |
| 人工确认次数 | 门控观察记录（`feedback-utils.py --action record --lifecycle-point gate-*` → `--action list`）+ clarify 提问轮次 |
| requirements→analyze 墙钟 | `git log --diff-filter=A --format='%h %as' -- <requirements.md>` 的首次提交 author date → `/speckit.analyze` 的运行判定记录时间戳 |

- 冻结点：开工前 = `requirements.md` 的首次提交。起点 MUST 用 `--diff-filter=A` 取该文件的**新增提交**；MUST NOT 用 `git log -1`（取最近一次触及，不是首次提交，且不输出提交哈希）。仪器口径与 `not-evaluated` 降级归 069b 契约 C-1。
- 任一量无来源时记 `null` + `reason`，MUST NOT 记 0、MUST NOT 记达成。
- 单阶段确认 ≤ 3 次；超出即回看阶段产物，而不是继续追加确认。
- 三项值 MUST 来自上表的既有通道，MUST NOT 新增采集器。

## 算子去重

- 同一算子在**同一次产物变更**上 MUST 只跑一次：需求未变更时，clarify 后不重跑需求面全量校验；plan / tasks 的结构检查由 `pre-analyze-check.py` 一次承担。
- 表达类 MUST NOT 继承代码型算子（测试执行、编译、覆盖率）；确因该特性产出代码或站点时按产出物补回，并在基线记录中说明。
- 去重 MUST NOT 减少面数与阻断级别。

## 阶段不变量

- 阶段完整性由既有阶段记录判定，类别 MUST NOT 参与该判定。
- `analyze` 与 `review` 的调用率 MUST 为 100%。
- 任何以「本流程属表达类」为由跳过、缩短或改判阶段的请求 MUST 被拒绝——该规则无例外。

## 与复杂度轴正交

- 复杂度轴（复杂命令 / 简单命令）决定有没有 wrap-up 面，其 owner 是 `.specify/shared/workflow/feedback-step.md`；该文件只需一行指针指向分类 owner，MUST NOT 在该文件中复制判据或台账。
- 本门禁集选择算子，复杂度轴决定是否有 wrap-up 面；两轴互相推导的禁令与判据归 `.specify/shared/definitions/flow-class-definitions.md` § 与复杂度轴正交，本文件只引用该节，不复述其判据句。

## 调用点表

本表是「入口 → 阶段 → 算子」的唯一登记处。命令模板与技能 MUST NOT 复制本表，只可出现 owner 指针与各自被允许的调用形态；新增调用点属契约变更，MUST NOT 由模板或技能自行扩面。

| 调用点 | 时点 | 类别读取 | 执行算子 | 阻断 |
| --- | --- | --- | --- | --- |
| `/speckit.docs`（W1） | `## Outline` 内、目标声明协调与分派之前 | `flow-class-check.py --action lookup --unit-id "/speckit.docs"` | 六面全集：`requirements-clarity`（需求清晰度）· `reader-purpose`（读者/目的/边界）· `evidence-asof`（证据分级与 as-of）· `structure-links-build`（结构/链接/构建）· `fact-consistency`（事实一致性）· `review`（评审）；其中读者、证据与事实三面由 `doc-consistency-check.py --action verify` 执行，计数面委派 `pre-analyze-check.py` | 每面 ≥ 1 blocking |
| `skill:create-docs`（W3） | Reconcile Loop 的 R6 verify 与 Authoring Flow 的 R6 验证（两处） | 沿用调用方已解析结果；无调用方（standalone）时不新读 | 读者/目的 + 证据/as-of + 事实一致性 → `doc-consistency-check.py --action verify`（对受触文档）；结构/链接/构建 → `docs-utils.py --action validate` | blocking：发现即报告并阻止「收敛完成」结论 |
| `/speckit.humanize`（W2） | `## Outline` 内、委派技能之前 | 不读取（只给 owner 指针） | 无（模板不执行算子） | 不适用（本行只声明指针与归口） |
| `skill:humanize`（W4） | Stage 6 保真自检之前（读取一次）→ Stage 6 + Stage 7 | `flow-class-check.py --action lookup --unit-id "/speckit.humanize"`（该流程唯一的类别读取） | 062 域最小集，不按六面登记：`062-stage6-fidelity` · `062-stage6-entailment` · `062-stage5-audience-report` · `062-reviewer-report` | `062-stage6-fidelity` 与 `062-stage6-entailment` blocking；其余为 062 既有报告义务 |

### 特性线阶段命令（`spec:` 键）

**类条件追加**：特性线（一条 spec 目录）的类别经 `spec:<spec 目录名>` 键解析，声明载体与判据归 `.specify/shared/definitions/flow-class-definitions.md` § 特性线声明面（`spec:` 键）。本表只登记「哪个阶段命令在哪一时点读一次类别、随后按哪张表执行」，**不复制**算子 id、面名或阻断级别——那些只有 § 阶段算子表 一处。

| 阶段命令 | 读取时点 | 类别读取 | 执行算子 | 阻断 |
| --- | --- | --- | --- | --- |
| `/speckit.requirements` | 声明行写入之后、`validate-requirements.py` 之前 | `flow-class-check.py --action lookup --unit-id "spec:<spec 目录名>"` | § 阶段算子表 requirements 行 | blocking |
| `/speckit.clarify` | 阶段入口 | `flow-class-check.py --action lookup --unit-id "spec:<spec 目录名>"` | § 阶段算子表 clarify 行 | blocking |
| `/speckit.plan` | 阶段入口 | `flow-class-check.py --action lookup --unit-id "spec:<spec 目录名>"` | § 阶段算子表 plan 行 | blocking |
| `/speckit.tasks` | 阶段入口 | `flow-class-check.py --action lookup --unit-id "spec:<spec 目录名>"` | § 阶段算子表 tasks 行 | blocking |
| `/speckit.checklist` | 阶段入口 | `flow-class-check.py --action lookup --unit-id "spec:<spec 目录名>"` | § 阶段算子表 checklist 行 | blocking |
| `/speckit.analyze` | 阶段入口 | `flow-class-check.py --action lookup --unit-id "spec:<spec 目录名>"` | § 阶段算子表 analyze 行 | blocking |
| `/speckit.implement` | 阶段入口 | `flow-class-check.py --action lookup --unit-id "spec:<spec 目录名>"` | § 阶段算子表 implement 行 | blocking |

- **一次读取**：同一次阶段运行只读一次，结果复用于本阶段全部算子调用；命令与其委托技能在同一产物变更上重叠时复用调用方结果，技能 MUST NOT 再读一次；跨阶段不缓存、跨线不复用。
- **两分支**：解析为表达类 → 执行本阶段在 § 阶段算子表 登记的行；其余情形（含未声明按默认、含 `owner-unavailable` 降级）→ 既有门禁集逐字不变。MUST NOT 存在第三个分支。
- **作者输入错误不属降级**：解析以退出码 1 报作者输入错误（取值越界或声明行形态不合规）时，阶段停下并以阶段协议的异常行收尾；MUST NOT 按「既有门禁集逐字不变」继续，也 MUST NOT 记作 `owner-unavailable`。

## 调用时机与降级

- 读取先于判定：lookup MUST 先于该入口的任何门禁判定执行，且同一次运行只执行一次（同一产物变更不重复读取）。`/speckit.docs` 的读取在命令模板分派前；`/speckit.humanize` 的读取在其委派技能的 Stage 6 之前——命令模板本身不读取。
- 降级一律可见：`source: default` → 原样显示固定标记（[[STR-004]]，未声明·按默认）；owner 不可解析或引擎缺席（文件不存在 / 退出码 2）→ 显示 `owner-unavailable`，并保持既有门禁不变；MUST NOT 中断流程、MUST NOT 静默切换门禁集、MUST NOT 把降级当作通过。
- 技能被独立调用（无命令调用方）时，仍按其调用点行执行读取；owner 或引擎缺席时按默认类处理并带同一标记或 `owner-unavailable`。
- 命令与技能在同一个产物变更上重叠时，以一次执行为准并复用其输出，MUST NOT 造成算子重复执行。
- 接线 MUST NOT 改变判定阈值、阶段集合或 P0/P1 定义——它只决定「用哪套算子证明同一不变量」。

## 与首批成员的关系

- `/speckit.docs` 与 `/speckit.humanize` 的既有门禁 MUST NOT 被本门禁集削弱；只补强、不削弱。
- 补强形态封闭为各自入口的最小接线：命令模板与技能只出现 lookup 调用与 owner 指针，不出现算子表副本、不改写既有行为；`/speckit.humanize` 的命令模板保持 Simple（零脚本调用），读取落在其技能的 Stage 6。
- 本切片 MUST NOT 新增 `/speckit.*` 命令；062 的保真底线、默认零写入与报告契约原样保留。

## 不在本文件（只给指针）

| 主题 | 所有者 |
| --- | --- |
| 分类判据、两取值、判定依据、逐流程台账、类中立清单、命名空间 | `.specify/shared/definitions/flow-class-definitions.md` |
| 复杂度轴（决定 wrap-up 面有无） | `.specify/shared/workflow/feedback-step.md`（只加一行指针，MUST NOT 复制判据） |
| 类别解析的可执行入口（行为与退出码归该文件） | `.specify/scripts/python/flow-class-check.py` |
| 事实一致性检查器（读者 / 证据 / 副本 / 计数四面） | `.specify/scripts/python/doc-consistency-check.py` |
