<!-- AUTO-GENERATED from templates/commands/derive.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat it as command parameters, not as a standalone instruction that replaces this workflow.

`$ARGUMENTS` may carry: a **topic** (the domain question to derive an architecture for), a **source list** (titles, authors, URLs — handed in by the user, a colleague, or another model), and optional parameters `--max-steps <N>` (derivation step budget) and `--force` (re-scaffold an existing archive, which discards its content).

A source list is **input to be verified, not a set of facts to inherit**. Handed-in lists routinely contain dead links and community-retitled articles; both are recorded as evidence by Stage 3 rather than silently trusted or silently dropped.

## Glossary

Consult the project glossary (`.specify/memory/glossary.md`) and apply the protocol in `.specify/shared/workflow/glossary.md`: correct recorded homophone/confusable variants before acting; propose new terms at wrap-up with user confirmation.

## Outline

本命令是推导能力的执行入口。**概念真源** = `.specify/shared/definitions/derivation-definitions.md` — 六套记录 schema(Source / Reasoning Move / Criterion / Derivation Step / Decision Point / Architecture Element)、四级溯源等级、链完整性规则 C1–C7、自审集 A1–A16、封闭禁用论证字面量集、能力降级规则均在该文件定义。本模板**引用而不复述**其规则;二者不一致时以概念真源为准。引擎 = `.specify/scripts/python/derive-utils.py`(动作与退出码以其 `--help` 为准)。

方法的核心区别:读来源不是为了知道它**主张什么**,而是为了知道它**怎么从前提走到结论**。产物是一条可被独立读者重放核查的推导链,以及每个元素都回指链上某一步的架构。

### Stage 1 — Preflight

探测 `python3`、引擎 `.specify/scripts/python/derive-utils.py`、以及**线上能力**(宿主是否暴露 WebSearch / WebFetch 一类工具)。

- 引擎缺失 → 给出 actionable 提示后停止(引擎三态探测惯例)。
- **线上能力缺失 → 进入降级路径**(见 Stage 3 的降级条款),不静默跳过核实。

### Stage 2 — Resolve Topic & Load the Move Library

解析 `<topic-slug>`(身份文法见概念真源)。脚手架推导档案:

```bash
python3 .specify/scripts/python/derive-utils.py --action init --slug <topic-slug> --workspace-root . --format json
```

档案已存在时引擎拒绝覆盖 —— 就地增补既有档案,仅在用户明确要求重新脚手架时才加 `--force`。

脚手架后立即填写档案的 `## Agent Identity` 块(agent 类型与版本、模型名/版本——宿主未暴露时如实写 `unavailable`、run-id、UTC 时间戳、topic)。该块是本次运行所有 `agent-prior` 准则的**署名锚点**:决策断言因被记录且有署名而有效,不因缺乏外部证据而无效。

随后读取**算子库投影**(摘要优先:消费投影而非整读库文件;阈值定义见 `.specify/shared/guidelines/token-efficiency.md`):

```bash
python3 .specify/scripts/python/derive-utils.py --action moves-list --workspace-root . --format json
```

已有算子是本次运行的起点:优先复用与增锚,只有 genuinely new 的推理形状才新增。

### Stage 3 — Ground the Sources Online

对每个来源执行线上核实,按概念真源 §Dead-Link Protocol 的固定次序降级:直连抓取 → 存档可用性查询 → 按标题+作者做一次归属搜索。引擎产出**不可编造的证据痕迹**:

```bash
python3 .specify/scripts/python/derive-utils.py --action probe-links --file <urls.json> --workspace-root . --format json
```

**探活是佐证,不是落地路径本身。** 若 `probe-links` 对某 URL 返回 `access: unknown`(典型成因:宿主经 SOCKS 代理出网而 stdlib `urllib` 无法穿越,引擎会在输出里给出 `proxyWarning`),那**不是**该来源已死的证据 —— 改用宿主自身的抓取/检索工具落地该来源,并把**那条工具产出的证据**写进 `verification`。探活不可用绝不构成跳过核实的理由;拿不到任何证据时,诚实的等级是 `unverified`。

随后由 agent 读实际文本并判定**溯源等级**(引擎供给证据,等级是判断):`primary` / `authoritative-secondary` 可锚定推导步骤;`community` / `unverified` 只能作 `leads` 线索。两条硬规则:

- **等级由内容决定,不因被救回而升级** —— 存档快照救回作者本人页面仍是 `primary`,救回清单体文章仍是 `community`。
- **`verification` 必须是具体证据**(HTTP 状态、快照地址、确立归属的那条搜索结果)。裸断言被引擎拒绝;拿不出具体证据时,诚实的等级是 `unverified`。

`title_mismatch` 由引擎按归一化字符串比较计算,**不由 agent 断言**;为真时双标题都留痕,且引用该来源的每一步都引用 `resolved_title`。每个 `unverified` 来源都写入 `## Unverifiable Sources` 并附理由 —— 静默丢弃会让一个死链变成链上看不见的洞。

**降级条款(线上能力缺失)**:MUST NOT 编造核实。全部来源标 `unverified`、理由 `no-online-capability`,全数进 `## Unverifiable Sources`,**任何推导步骤都不得锚定**,运行在建链前停止并如实报告降级 —— 产出诚实的空结果,而不是自信的未核实结果。

### Stage 4 — Extract Reasoning Moves

从已核实来源中提取思维算子。这一步是语义工作,不可脚本化:读懂来源的实际论证,把它的**推理形状**写成带命名槽位的形式(槽位是它能跨领域复用的原因),并写明它防住的失败模式、适用条件**与过度使用护栏**、以及展示这一论证方式的来源锚点。

抽取的是**方法不是结论**:若一条候选把领域名词换掉就失效,它是该来源的主张,应作为 `premises` 引用而不是算子。

经引擎入库(算子库的唯一写入者;按归一化 `inference_form` 做**两级**去重——精确与槽位同构,近重复时拒绝写入并在 `payload.duplicates[]` 返回既有 `move_id`,本次运行转为增锚而非分叉;拒绝是**成功路径**,退出码 0):

```bash
python3 .specify/scripts/python/derive-utils.py --action moves-add --file <moves.json> --workspace-root . --format json
```

`<moves.json>` 形态为 `{"moves": [...]}`,每条 MUST 给出 `name` / `inferenceForm` / `prevents` / `appliesWhen` / `anchor` / `intent`;`intent` 取值封闭为 `new` / `reuse` / `reinforce` / `supersede`,后三者 MUST 同时给出 `existingMoveId`。schema 任一处不合法 → 退出码 2 且**零写入**(全有或全无)。

锚点 MUST 用**跨主题限定形式** `<topic-slug>.S-<nnn>`(库是项目级的,来源是主题级的);裸 `S-<nnn>` 会被拒绝,因为 `moves-add` 不携带 topic、无从限定,而写进库的裸形式会在下一次 `validate` 触发 `anchor-form` 违例。

产物还 MUST 在 `## Reasoning Moves Applied` 记下**本次运行的处置日志**,两列表 `| move_id | disposition |`,disposition 取 `moves-add` 返回的运行相对值(`new` / `reused` / `reinforced`)。这张表是跨运行复用度的量测点(第二次运行同一主题时 `reused` + `reinforced` 应大于 0),`stats` 就读它。**它不是库行的复写**:两列日志不携带库的任何字段,故不需要 `<!-- projection of moves.md#M-nnn -->` 标记;只有真的把库的七列拼进产物时才需要标记,而与库中同 ID 但文本不同的复写行会被拒绝。

### Stage 5 — Build the Derivation Chain

逐步推导,每步一个 `### D-<k>` 块:`premises`(已核实来源 + **更早**的步骤)/ `leads`(可选线索)/ `move`(**恰好一个**)/ `derivation`(槽位已实例化的推理)/ `conclusion`(一句可证伪陈述)/ `falsification`(什么观察能推翻它)/ `confidence`(`derived` / `provisional` / `contested`)/ `contested-with`。

链完整性规则 C1–C7 由概念真源定义、由引擎执行。三条最容易被绕过的:

- **禁用论证(C3)**:`derivation` 与 `conclusion` 里不得出现封闭禁用集的任何字面量。真的需要陈述业内普遍做法时,引用一个**已核实来源**去说这件事 —— 那就把一句空洞论证变成了一个有锚点的前提。
- **矛盾不静默择一(C5)**:两个来源的算子推出冲突结论时,标 `contested`、双向 `contested-with`、写出**判别性问题**,残余进 `## Open Questions`。不确定性向前传播:消费 `contested` 前提的步骤至多 `provisional`,`derived` 步骤不得建立在 `contested` 之上。
- **前提耗尽不等于可以编造(C6)**:下一步所需前提无已核实来源可提供时,以终止条件 (b) 收尾,缺口进 `## Open Questions`(含 `why-undetermined` 与 `discriminator`)。步骤数受 `--max-steps` 预算约束,触顶如实报告。

在 `## Termination` 写明 `- condition: a|b` 与 `- steps: <n> / <budget>`。

### Stage 5.5 — Record Criteria & Decision Points

链推导出**结构**(架构必须包含什么、为什么);产品级**选型**(哪个图存储、哪个向量引擎、哪个模型族)由决策点记录,不埋在散文里。这一步实现「枚举 → 过滤 → 排序 → 选中」的可审计版本:

1. **采集准则** `## Criteria`(每行一条,单元格单行):从 handed-in 约束、项目宪法、以及 agent 自身先验中采集排序根据。`kind` = `constraint`(硬过滤,违反即淘汰)| `preference`(排序权重,违反扣分不淘汰);`provenance` = `source`(**真值断言**——owner 列必须引用已核实的 `S-<nnn>`)| `declared`(利益方声明——owner 写明声明者)| `agent-prior`(**决策断言**——owner 写 `Agent Identity <run-id>`,即本次运行的 agent+LLM 署名)。每条准则 MUST 给出 `defeater`(什么观察或重新声明能推翻它)。
2. **建决策点** `## Decision Points`(每个 `### DP-<k>` 块字段单行):`question` / `candidates`(每个候选挂 `[S-<nnn>]` 或标 `[ungrounded]`,`;` 分隔)/ `filters`(引用 D-k / C-nnn 说明剪掉了谁、凭什么)/ `ranking`(**每条排序判断引用 ≥1 个 C-nnn** —— 无准则引用的排序是穿着真值断言外衣的偏好,A15 拒绝)/ `selected`(MUST 出自 candidates)/ `alternates`(**≤2 个**,即 top-1..3 输出契约,每个附切换触发器引用 Q-k 或 C-nnn)。

类别纪律(A16 背书项):**真值断言挂来源,决策断言挂署名**。`agent-prior` 准则不得措辞成经验事实(那是 C3 禁用字面量的变体);`source` 准则不得被拉伸到来源文本之外。被记录且署名的偏好选择是**终局的决策**,不因"缺外部证据"降为 provisional——它由重新声明修订,不由引用修订;只有结构层未被来源支撑的部分才走 D 步 `provisional` + Open Question 通道。

### Stage 6 — Compose the Derived Architecture

每个 `### A-<k> <name>` 块:`statement` / `derived-from`(**强制、≥1、全部可解析**)/ `confidence`(按其步骤的**最小值**继承)/ `open-questions`。内嵌产品级选型的元素 MAY 加 `decisions: DP-<k>` 引用决策点而不复述其内容。

缺 `derived-from` 是硬失败,引擎拒绝整个文件 —— 不可溯源的元素是穿着架构外衣的偏好。未定点进 `## Open Questions`(`question` / `why-undetermined` / `would-resolve` / `discriminator`),`Q ↔ A` 链接双向可解析,被阻塞的元素降级为 `provisional` 或 `contested`。**绝不用听起来合理的猜测填空** —— 那正是本命令存在的理由所要防的失败模式。

### Stage 7 — Self-Audit

```bash
python3 .specify/scripts/python/derive-utils.py --action validate --slug <topic-slug> --workspace-root . --format json
```

引擎程序化判定 A1–A10 与 A12/A13/A15,并把结果写入产物的 `## Self-Audit` 表。输出中的 `semanticChecksPending` 列出**必须由 agent 显式背书**的三项:

- **A11** — 本次运行确实联网核实了(每个来源至少一次检索或抓取,且记入 `verification`)。
- **A14** — 产物陈述的是来源的**思维方式**,不是其内容摘要。这是本命令存在的理由;一份 A14 不成立的产物即使结构全绿也没有价值。
- **A16** — 决策断言已署名、未被洗成真值断言:`agent-prior` 准则不以经验事实口吻措辞,`source` 准则未超出来源文本,每条 DP 排序确实被其引用的准则支撑。

`validate` **零写入**:A1–A10 与 A12/A13/A15 这 13 行的 `result` 由引擎**派生**,产物里的值 MUST 与 `payload.audit.engine` 逐字相等(不等即 `audit-result-diverges`),但引擎不会替你写。故自审是**两趟**:第一趟取 `payload.audit.engine` 与 `payload.audit.semantic` 的派生值 → 由 agent 誊写进产物的 `## Self-Audit` 表(A11/A14/A16 的 `result` 取 `attested` / `not-attested` / `pending`,其 `method` 列 MUST 是一句可核查的话,不能写 `engine` 或 `n/a`)→ 第二趟重跑 `validate` 收敛到零 error。「誊写引擎给出的值」与「自己判一个值填进去」是两件事:前者是记录,后者是 C-20 禁止的手写。

退出码 4 表示存在结构性违规。**任一引擎检查为红的运行 MUST 如实报告失败与定位,MUST NOT 把 `## Derived Architecture` 当作已推导结果呈现。**

计数与分布:

```bash
python3 .specify/scripts/python/derive-utils.py --action stats --slug <topic-slug> --workspace-root . --format json
```

### Stage 8 — Report

产物均为可逆写入(新档案文件 + 算子库追加),故全程自动执行,收尾出具三要素执行报告(判据见 `.specify/shared/guidelines/confirmation-gates.md`):

1. **执行内容** — 主题、来源数与分级分布、复用/新增算子数、链步数与终止条件、准则数与决策点数(含署名 agent 标识)、架构元素数、未决问题数、自审结果(含 A11/A14/A16 背书)。
2. **变更工件** — 逐项可定位:`.specify/derive/<topic-slug>/derive.md`、`.specify/derive/moves.md`(新增/增锚的 `M-<nnn>`)。
3. **修改途径** — 两者均 git 跟踪,可经 git 历史回退;算子库为累积存储,`superseded` 行保留不删。

失败或中途停止时如实报告失败点、原因与已产生的中间产物,不静默跳过。

### Stage 9 — Wrap-up

标准 Feedback 与 Documentation 收尾步骤(见下)。

## Behavior Rules

- **联网核实是硬要求,不是优化项**:没有线上核实的来源一律 `unverified`,一律不得锚定推导步骤。
- **等级判断归 agent,证据归引擎**:引擎供给 HTTP 状态、快照地址、归属检索命中;等级、算子抽取、判别性问题命名、终止条件 (a)/(b) 是语义判断。
- **真值断言挂来源,决策断言挂署名**:排序与选型可以基于 agent 先验,但 MUST 以 `agent-prior` 准则记录并署名到 `## Agent Identity`;无署名的偏好诉诸(「业界通用」类字面量)仍被 C3 禁止——修复路径是转换成准则或挂来源,不是删除判断。
- **算子库只经 `moves-add` 写入**:手工编辑会被 `validate` 检出(行形、ID 单调性、重复 ID、槽位同构重复),不静默接受。
- **引用不复述**:schema、等级集、C1–C7、A1–A16、禁用字面量集一律以 `.specify/shared/definitions/derivation-definitions.md` 为准。
- **不触碰用户源码**:本命令只写 `.specify/derive/` 下的档案与算子库。
- **产物不预判领域**:分发文件中的示例一律槽位化合成,handed-in 语料只作为本次运行的输入,不写入框架文件。

## Boundary: /speckit.derive vs /speckit.research

| | `/speckit.research` | `/speckit.derive` |
|---|---|---|
| 对象 | 一个**特性**的未决技术问题 | 一个**主题**(领域级问题) |
| 产出 | 决策与理由 + 引用 | 推导链 + 每个元素可溯源的架构 |
| 落点 | `.specify/specs/<key>/research.md` | `.specify/derive/<topic-slug>/derive.md` |
| 生命期 | 绑定单个特性 | 跨特性复用 |
| 抽取的是 | 结论层(选哪个、为什么) | 方法层(怎么从前提走到结论) |

依赖方向单向:`/speckit.plan` MAY 按身份引用架构元素 `A-<k>` 而不重新论证;本命令 MUST NOT 引用 plan。

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.derive" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether this run produced information needing entry into the documentation space (a new derivation archive worth a concept note, a decision that belongs in an ADR, a newly coined term for the glossary), and conclude with exactly one of `需记录(目标文档 + 要点)` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Handoffs

**Before**: 无强制前置(手动按需运行)。 handed-in 来源清单可来自任何渠道;若某特性的 `research.md` 已积累引用,可作为起点一并 handed-in。

**After**: `/speckit.plan` 按身份引用架构元素 `A-<k>` 编码实现方案;`/speckit.clarify` 处理 `## Open Questions` 中阻塞架构元素的未决问题,解决后重跑本命令延长推导链。