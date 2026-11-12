# SDD Routing Definitions — 授权路由与 SDD 调用分类

**Owner（唯一所有者）**: 本文件 `.specify/shared/definitions/sdd-routing-definitions.md` 是「一次变更何时走 SDD、何时直接修改、何时必须裁定」这条路由规则的唯一所有者。它拥有**四项事实**，且只有本文件可以把它们写出来：

| # | 事实 | 本文件落点 |
|---|------|-----------|
| F-1 | 五项声明输入的封闭取值域 | § Inputs |
| F-2 | 三值裁决表（`sdd` / `direct` / `adjudicate`） | § Verdict table |
| F-3 | 固定优先级 | § Precedence |
| F-4 | 理由码词表（封闭） | § Reason codes |

**引用纪律**: 其他任何位置——命令模板、技能、驱动入口、裁决记录形状、契约、测试——MUST 以「路径 + 章节锚」引用本文件，MUST NOT 复制上表任一项，MUST NOT 以表格 / YAML / JSON / 代码常量的形式再声明一份「输入 → 裁决」的映射；仓库中 MUST NOT 出现第二份路由数据文件或常量表。判据与两份合法重复的唯一真源是 `.specify/shared/guidelines/one-source-of-truth.md`。

**机读面**: 唯一的读取者是只读 stdlib 引擎 `.specify/scripts/python/sdd-route.py`（动作 `route` / `authorize` / `golden`）。它在运行时解析本文件，MUST NOT 自带第二份取值域、裁决表、优先级或理由码；引擎的接口与退出码归 `contracts/routing-decision.md` C-28 所有。

**字面量登记处**: `[[STR-001]]` … `[[STR-011]]` 的取值与语义 owner 是合并后的父规格 `.specify/specs/074-goal-team-sdd-unification/requirements.md` § Shared Strings（原切片登记处为其被合并前的投影）；本文件以 `[[STR-NNN]]` 引用其语义，不另立第二张字面量表。

**不在本文件（只给指针，不复述）**:

| 主题 | 所有者 |
|------|--------|
| 复杂度层级名、判定信号与思考深度处方 | `.specify/shared/guidelines/task-complexity-rubric.md` |
| 质量门与确认门集合 | `.specify/shared/guidelines/confirmation-gates.md` 与宪法质量原则 |
| Goal / Target 的身份、状态机与绑定 | `.specify/shared/definitions/goal-definitions.md` |
| 驱动的阶段名册、状态脊、哨兵、U0–U6 | `.specify/skills/sdd-loop-driver/SKILL.md` |
| 反嵌套义务与其派发前探针 | `.specify/shared/definitions/subagent-definitions.md` § Dispatch-Time Governance Obligation；`.specify/skills/internal/run-agent/SKILL.md` |
| 中立元数据键集（`[[STR-001]]` 的取值域与缺省） | `src/specify_cli/__init__.py` `NEUTRAL_AGENT_METADATA_KEYS` |
| `team.md` frontmatter schema（`[[STR-011]]` 块映射） | `.specify/skills/internal/create-team/references/create-mode.md` § Persisted `team.md` schema |

## Hierarchy

控制层级只有一条，且有唯一一条边界：

1. **Goal** 是最高层：它陈述一个目标与可验证的成功判据（身份与状态机归 `.specify/shared/definitions/goal-definitions.md`）。
2. **Team** 绑定一个 Goal，编排 Agent 成员；Team 不重写 Goal，只把 Goal 拆成成员职责。
3. **Agent** 执行一条职责（duty）；职责是路由与授权的计量单位——一次裁决对应一条职责，而不是一个文件或一次提交。
4. **SDD 运行**（`sdd-loop-driver`）是从属执行路径：它由**已获有效授权的 Agent** 启动，为一条职责产出 SDD 工件链，并在 review 完成后交回 handoff。

**边界**: 下层不得改写上层的定义。**一次 SDD 运行 MUST NOT 创建/重绑/改范围/终止共享档案中的既有定义**——需要改变既有定义的动作 MUST 返回给上层执行者（Goal 侧归 `/speckit.goal`，Team 侧归 `/speckit.team` 的既有写线），而不是在运行内就地改写。层级不新增结构字段、不新增强制绑定。

**平行线 carve-out（追加）**: 上句治理的是**共享档案中已有的定义**，不是禁止运行拥有定义。一次运行——SDD 运行与命令运行同规——MAY 创建归本次运行所有的定义并写入两条档案层：goal 档案 `.specify/anchoring/<slug>/goal.md`、team 档案 `.specify/teams/<slug>/team.md`；归属由绑定记录回答，其构成与取值域归 `.specify/shared/definitions/goal-definitions.md` § The Binding Record，team 侧归 `.specify/skills/internal/create-team/references/conceptual-model.md` § The Team Definition and the Binding Model——本段只是路由层的 carve-out，不复述任何 value domain。哪些命令运行 MAY 创建定义由声明层与 goal 引擎的 `command-family` 动作判定，本段不设第二份清单。

## Direct modification

**直接修改** = 执行一次变更而**不产生 SDD 工件链**：不建立工件链、不经过驱动的阶段与哨兵、不产出 handoff。

它与 SDD 运行只在这一件事上不同，**不是减免**：

- 直接修改仍受**全部适用的质量门与确认门**约束——门禁集合按路径引用 `.specify/shared/guidelines/confirmation-gates.md` 与宪法质量原则，本文件不复述其中任何一条；
- 直接修改仍留下可复核的执行证据（改了什么、按什么判据、谁做的）；
- 「改动看起来很小」不是走直接修改的理由：理由只有一项——裁决值（F-2），由声明的五项输入推出，不由改动规模、文件数量或作者身份推出。

两者的区分因此是可判定的：SDD 运行留下工件链与 handoff，直接修改不留下；而**是否应当**走其中一条，由本文件的三值裁决表回答，不由调用方自行判断。

## Invocation kinds

一个 Agent 在启动一项工作前，只有**四种**调用类型可选，且四者的身份不得混用：

| # | 调用类型 | 入口 | 是否 SDD 调用 |
|---|----------|------|---------------|
| 1 | **SDD 开发流程**（development flow） | `sdd-loop-driver` | 是——且只有它是 |
| 2 | **框架引导**（bootstrap） | `sdd-project-setup` | 否 |
| 3 | **周期性维护**（house-keeping） | `sdd-house-keeping` | 否 |
| 4 | **直接修改**（direct modification） | 无技能、无驱动 | 否 |

规则：

- **引导与维护不同于开发流程**：`sdd-project-setup` 与 `sdd-house-keeping` 是框架的引导与维护路径，它们各自有既定职责，MUST NOT 被读作「轻量的 SDD 运行」，也 MUST NOT 取代开发流程。
- **只有驱动构成 SDD 调用**：在嵌套入口契约下（`.specify/skills/sdd-loop-driver/references/nested-invocation.md`），只有 `sdd-loop-driver` 的调用算作一次 SDD 调用。
- **无 `.specify/` 结构的目标项目走引导路径**：当一次被分流为 SDD 的变更落到尚无 `.specify/` 结构的目标项目时，路由是**引导路径**（`sdd-project-setup`），MUST NOT 把 SDD 分流降级为直接修改——降级会让该变更永久失去工件链与 handoff，而这两件正是它被分流为 SDD 的原因。
- **引导与维护派发子代理时适用同一有效授权谓词**：当 `sdd-project-setup` 或 `sdd-house-keeping` 派发子代理时，该派发与一次 SDD 调用适用**同一个**有效授权谓词——同一个键 `[[STR-001]]` 的两个半边（Agent 定义能力 AND 席位策略，席位侧载体为 `[[STR-011]]` 块映射），按 (team, seat) 解析，可执行形态是 `python3 .specify/scripts/python/sdd-route.py --action authorize`。谓词不是第二个谓词，其义务位点归 `.specify/shared/definitions/subagent-definitions.md` § Dispatch-Time Governance Obligation。

## Inputs

本裁决只消费下列五项**声明输入**（F-1）。第 3 列是本文件对引擎暴露的取值域机读面：引擎按 `/` 切分该格、去反引号，得到该输入的有序成员列。域外取值一律判 `ambiguous`（见 § Precedence），MUST NOT 就近换一个合法值继续。

| 输入（CLI 标志） | 含义 | 封闭取值域（`/` 分隔，机读） | 纪律 |
|---|---|---|---|
| `change_nature`（`--nature`） | 变更性质：能力与契约是被新增或改变，还是被保持 | `feature` / `maintenance` / `definition-class` | 三值封闭，只允许声明其中一个值。`feature` = 新增或改变一项能力或契约；`maintenance` = 保持既有全部能力与契约；`definition-class` = 目标路径落在 `requirements.md` FR-008 谓词列出的根之内，其**成员资格由该路径谓词派生**，本文件不复述那份路径清单，且不因此新增第六项输入。 |
| `traceability`（`--traceability`） | 是否需要持久可追溯（审计链、跨会话可复核） | `required` / `not-required` | 二值封闭，只允许声明其中一个值。 |
| `blast_radius`（`--blast-radius`） | 影响半径 | `local` / `cross-cutting` / `local-bounded-definition-correction` | 三值封闭，只允许声明其中一个值。第三值是**有界修正**的独立取值，MUST 随附非空理由（见 § Definition-class default），它与 `local` 不同义、不可互换。 |
| `reversibility`（`--reversibility`） | 可逆性 | `reversible` / `hard` | 二值封闭，只允许声明其中一个值。`hard` 覆盖「不可逆或其反向代价高」这一整类，不另设第三个值。 |
| `complexity`（`--complexity`） | Task Complexity Rubric 的层级 | `trivial` / `standard` / `complex` / `high-stakes` | 四值封闭，只允许声明这四个层级名之一。层级名、判定信号与思考深度处方的 owner 是 `.specify/shared/guidelines/task-complexity-rubric.md`：本文件 MUST NOT 复述其信号、表或处方，层级改名经这条引用抵达本裁决。 |

**禁用输入**：本裁决 MUST NOT 消费实现介质（implementation medium）、扩展名（extension）、语言（language）、工件数（artifact count）或作者身份（author identity）；这五项不是输入，也不是任何输入的替身，不得据其中任一项推断任何取值。目标路径的唯一读法是 `requirements.md` FR-008 的路径谓词：引擎消费的是调用方**声明**的 `change_nature`，谓词在声明侧执行，因此引擎既不读目标路径、也不复制那份路径清单。

**机读面（层级分档）**：上表 `complexity` 行的四名按 rubric 自身的分档二分——高 = `complex` / `high-stakes`；低 = `trivial` / `standard`。分档不改写层级名，只声明哪两名属于「高」这一侧。

**机读面（取值语义 / value semantics）**：下列具名句柄指向 § Inputs 已经声明的取值，**不复述任何取值域**——它只给引擎一个可引用的名字，使条件判定不必自己写死取值字面量；改域时这一块随上表一起改（同一文件、同一处）。

- `definition_class` = `definition-class`
- `feature_nature` = `feature`
- `traceability_required` = `required`
- `traceability_not_required` = `not-required`
- `plain_local` = `local`
- `cross_cutting` = `cross-cutting`
- `bounded_correction` = `local-bounded-definition-correction`
- `definition_class_default` = `cross-cutting`
- `reversal_hard` = `hard`
- `reversal_reversible` = `reversible`

## Definition-class default

`definition-class` 变更**默认跨切面**：它落盘的表面定义着其他表面的行为，所以默认值是 `change_nature` 这个取值的属性，不是调用方另传的类别标志，也不是引擎的临场判断（C-20）。

- **有界修正是唯一逃逸口**：调用方必须声明独立的半径取值 `local-bounded-definition-correction` 并随附**非空理由**。声明普通 `local` 而指望被当作等价物不成立——`local` 对 `definition-class` 不被接受为等价，此时有效半径取默认值 `cross-cutting`。
- **理由缺失或为空是缺项，不是默许**：条件 `input-missing` 命中，理由码取 `adjudicate-missing-input`（见 § Reason codes），MUST NOT 补一个推定的理由后继续。
- **逃逸口只在定义面上成立**：`local-bounded-definition-correction` 与其它变更性质同时声明时，它不构成本地半径，有效半径取 `cross-cutting`；唯一例外是 § Conflict set 里的冲突组合，那一条按裁定处理。
- **有效半径（effective blast radius）**是记录里随 `inputs` 一起落盘的派生值：声明 `definition-class` 取值时，有界修正 + 非空理由 → 该有界值，否则 → 默认值；其余变更性质下沿用声明值，唯独有界修正取值按上一条取 `cross-cutting`。推导所用的取值句柄见 § Inputs 的「机读面（取值语义）」。

## Verdict table

三值裁决表（F-2）。第 2 列是机读事实：`any` = 该行任一条件成立即命中，`all` = 该行全部条件成立才命中；第 3 列是条件 id，本文件与引擎之间唯一的机读接口——引擎对每个 id 各有一份判定，但 MUST NOT 携带 id 到裁决的映射（那份映射就是本表）。

| 裁决 | 组合方式 | 条件 id（机读） | 命中含义 |
|---|---|---|---|
| `sdd` | `any` | `nature-feature` / `traceability-required` / `blast-cross-cutting` / `reversal-hard` / `complexity-high` | 走 SDD 开发流程。五个条件逐条对应 FR-009：变更新增或改变能力/契约、需要持久可追溯、有效半径跨切面、不可逆或难以反向、层级为高。任一成立即足。 |
| `direct` | `all` | `nature-preserves` / `traceability-not-required` / `blast-local` / `reversal-reversible` / `complexity-low` / `bounded-correction-recorded` | 走直接修改。六条必须**同时**成立（FR-010）：变更保持既有全部能力与契约、无需持久可追溯、有效半径为本地（`definition-class` 上则是有界修正取值）、可逆、层级为低；第六条在 `definition-class` 上要求有界修正已附理由，其余变更性质下自动成立。单条不成立即移出本裁决。 |
| `adjudicate` | `any` | `input-missing` / `input-ambiguous` / `input-conflicting` | 必须裁定（FR-011）：任一必需输入缺失、任一声明值落在封闭域之外、或命中 § Conflict set 的组合。 |

## Precedence

固定优先级（F-3）：`adjudicate` 先于 `sdd`，`sdd` 先于 `direct`。次序不因输入、调用方、改动规模或历史裁决而变化。

- **裁定先判**：缺项、域外取值、冲突组合都先于任何分支推理——它们若成立，后面的条件算得再准也不改变裁决。
- **只有非裁定分支里**，§ Definition-class default 的跨切面默认才生效。
- **MUST NOT 静默默认 `direct`**：`direct` 只在 § Verdict table 六条全部成立时返回；任何一条不成立都不会落到它，也不会落到一个「差不多」的值上。
- **每个裁决带一个理由码**：取自 § Reason codes 的封闭词表，且 MUST 同时携带五项输入原值与全部命中条件 id，使同一输入求值两次得到逐字节相同的输出（SC-002）。
- **「全部命中条件」含被吸收的那些**：记录的 `triggered_conditions` 是三个分支一起算出的**全部**命中条件 id。一个 `sdd` 裁决旁边出现属于 `direct` 分支的条件 id 是预期的——它表示那条边际条件当时也成立，只是被更高优先级的裁决吸收了；反过来，`adjudicate` 裁决旁边出现 `sdd` 或 `direct` 的条件 id 同理。

**机读面（优先级 / precedence，1 最高）**：`adjudicate` > `sdd` > `direct`

## Conflict set

冲突条件是**封闭枚举**，不是自由判断（C-24）：只有下表声明的组合算冲突，其余任何输入组合要么一致（恰有一个分支成立），要么不冲突，因此 `sdd` 分支的分类规则始终可达。

| # | 冲突组合（机读） | 为何冲突 |
|---|---|---|
| 1 | `change_nature=feature` & `blast_radius=local-bounded-definition-correction` | 一次新增或改变能力/契约的变更不可能同时是一条「有界定义修正」：两个声明互相取消对方的前提，任选其一都是替调用方做决定。 |

组合格的机读形态是 `输入=取值` 项以 & 符号连接的一行；命中任何一行即条件 `input-conflicting`。多条冲突以外的多条件同时命中，裁决按 § Precedence 走，理由码按 § Reason codes 的行序取首条。

## Reason codes

理由码词表（F-4）——封闭，且**行序即取码次序**：同一裁决下多条条件同时命中时，取本表中行号最小的那条。第 5 列说明读者该用它判断什么，不是触发条件的第二份定义。理由码自带裁决前缀（`adjudicate-` / `sdd-` / `direct-`），因此一个理由码本身就说清了它是哪一种裁决，而不必回查第 3 列。

| # | 理由码 | 归属裁决 | 条件 id | 读者用它判断什么 |
|---|---|---|---|---|
| 1 | `adjudicate-missing-input` | `adjudicate` | `input-missing` | 哪一项输入缺失（含 `definition-class` 上缺失的有界修正理由） |
| 2 | `adjudicate-ambiguous-value` | `adjudicate` | `input-ambiguous` | 哪个声明值落在封闭取值域之外 |
| 3 | `adjudicate-conflicting-inputs` | `adjudicate` | `input-conflicting` | 命中了 § Conflict set 的哪一条组合 |
| 4 | `sdd-capability-or-contract-change` | `sdd` | `nature-feature` | 变更新增或改变了能力/契约 |
| 5 | `sdd-traceability-required` | `sdd` | `traceability-required` | 需要持久可追溯 |
| 6 | `sdd-cross-cutting-radius` | `sdd` | `blast-cross-cutting` | 有效半径跨切面（含 `definition-class` 的默认） |
| 7 | `sdd-hard-reversal` | `sdd` | `reversal-hard` | 不可逆或难以反向 |
| 8 | `sdd-complexity-high` | `sdd` | `complexity-high` | 层级为高 |
| 9 | `direct-conditions-all-hold` | `direct` | — | 六条全部成立，走直接修改 |

条件 id 为 `—` 的行表示该裁决没有被更细的条件 id 细分（`direct` 的六条本身就是 § Verdict table 那一行），它在归属裁决胜出时即命中。

**理由码不是错误码**：`adjudicate-missing-input` / `adjudicate-ambiguous-value` / `adjudicate-conflicting-inputs` 都是**已产出的裁决**，进程退出码仍为 `0`；退出码阶梯（`0` 产出裁决 / `2` 输入错误，无第三值）归 `contracts/routing-decision.md` C-28。

## User override

用户的显式指示**覆盖**裁决。覆盖不是丢弃：它记为一条**裁定**，而裁定同样是裁决记录，因此四个必填面一个都不能少（FR-012 / C-25）：

- 用户指令**原文**——逐字，不改写、不摘要、不转述；
- **被覆盖的裁决**——引擎算出的那个值保留在记录里，MUST NOT 因为它被覆盖就抹掉；
- **理由码**——FR-011 要求每个裁决都带一个，裁定不例外；
- 作出覆盖的单元与时间，按 § Verdict record 的 `actor` / `recorded_at`。

引擎 MUST NOT 反向覆盖用户：`route` 产出的是**覆盖之前**的裁决，记录里的 `override` 成员留给调用方写入这条裁定；两者并存，谁覆盖谁在记录里可读。

## Per-duty application

裁决的计量单位是**一条成员职责**（duty），不是一个文件、一次提交或一次会话（FR-013 / C-26）：

- **写入前一次**：每条职责在它第一次写可追溯文件**之前**适用一次裁决。**写入型变更** = 写任何被追踪的文件（源码、配置、定义、文档）；只读分析不写被追踪文件，不需要裁决。
- **复用到输入变化为止**：同一职责内的后续写入沿用同一条裁决，不重算、不改写理由码。
- **输入一变即重判**：旧裁决保留在记录中（不删除、不覆盖），新裁决取代其效力；读者因此能看到「什么时候、因为哪一项输入变化换过判」。

## Verdict record

裁决记录的字段面归 `.specify/specs/074-goal-team-sdd-unification/slices/074a-authorized-routing/data-model.md` E4，本文件不复述字段表；本文件固定两件事，二者都是本切片可判定的面（C-27）：

- **载体**：本切片的裁决记录落在 **Agent 执行证据**里。嵌套运行的 handoff 与调用方的结果**按稳定路径引用同一条记录**，不复算——外层读到的就是该职责实际据以行动的那条裁决。
- **时间戳由记录侧承载、引擎不自造**：引擎 MUST NOT 读时钟（同一输入两次求值必须逐字节一致，C-24）。`recorded_at` 缺省为 `null`，由调用方以 `--recorded-at` 传入，或在写入证据时补齐；引擎只把它原样放进载荷。

## Golden case table

黄金用例（F-2 / F-4 的逐行可判定面）。**行集的唯一落点是本表**：测试代码、独立数据文件、任何第二个表都 MUST NOT 复制这些行——`--action golden` 在运行时解析本表并逐行判定，判定结果同时给出实际裁决与实际理由码，因此表与实现之间不可能悄悄漂移。

表头是机读契约：每个输入占一列（列名即 § Inputs 的输入标识），`rationale` 列承载有界修正要求的非空理由，最后三列依次是期望裁决、期望理由码与所覆盖的需求面。单元格缺值写 `—`，它就是「该输入缺失」，不是空字符串。

| case id | change_nature | traceability | blast_radius | reversibility | complexity | rationale | 期望裁决 | 期望理由码 | 覆盖的需求面 |
|---|---|---|---|---|---|---|---|---|---|
| G1-feature-scale | feature | required | cross-cutting | hard | standard | — | sdd | sdd-capability-or-contract-change | FR-009：功能规模的变更 |
| G2-bounded-maintenance | maintenance | not-required | local | reversible | standard | — | direct | direct-conditions-all-hold | FR-010：六条全部成立的有界维护 |
| G3-cross-cutting | maintenance | not-required | cross-cutting | reversible | trivial | — | sdd | sdd-cross-cutting-radius | FR-009：有效半径跨切面 |
| G4-irreversible | maintenance | not-required | local | hard | standard | — | sdd | sdd-hard-reversal | FR-009：不可逆或难以反向 |
| G5-ambiguous-value | maintenance | not-required | local | reversible | deep | — | adjudicate | adjudicate-ambiguous-value | FR-011：域外取值（ambiguous） |
| G6-conflicting | feature | not-required | local-bounded-definition-correction | reversible | trivial | 只收紧一处定义措辞 | adjudicate | adjudicate-conflicting-inputs | FR-011 / C-24：冲突组合（conflicting） |
| G7-bounded-definition-correction | definition-class | not-required | local-bounded-definition-correction | reversible | trivial | 只收紧一处定义措辞，语义不变 | direct | direct-conditions-all-hold | FR-008 / FR-010：满足其余全部条件的有界定义修正 |
| G8-missing-input | maintenance | not-required | local | reversible | — | — | adjudicate | adjudicate-missing-input | FR-011：缺项（未声明复杂度层级） |
| G9-definition-class-default | definition-class | not-required | local | reversible | standard | — | sdd | sdd-cross-cutting-radius | FR-008 / FR-010：definition-class 默认跨切面，声明 local 不被接受为等价 |
| G10-complexity-high | maintenance | not-required | local | reversible | high-stakes | — | sdd | sdd-complexity-high | FR-009：层级为高 |
| G11-traceability | maintenance | required | local | reversible | standard | — | sdd | sdd-traceability-required | FR-009：需要持久可追溯 |
| G12-bounded-without-rationale | definition-class | not-required | local-bounded-definition-correction | reversible | trivial | — | adjudicate | adjudicate-missing-input | C-20：有界修正必须随附非空理由 |
| G13-all-sdd-conditions | feature | required | cross-cutting | hard | high-stakes | — | sdd | sdd-capability-or-contract-change | FR-009 / C-24：五条全部命中，取码次序取首条且携带全部命中条件 |
| G14-ambiguous-beats-conflict | feature | not-required | local-bounded-definition-correction | maybe | standard | 只收紧一处定义措辞 | adjudicate | adjudicate-ambiguous-value | C-24：多条件同时命中时按声明次序取码（ambiguous 先于 conflicting） |

七类必备覆盖与行号对应：feature-scale = G1；bounded maintenance = G2；cross-cutting = G3；irreversible = G4；ambiguous = G5、G14；conflicting = G6、G14；满足其余全部条件的有界定义修正 = G7。G8 / G12 补上「缺项」这一裁定形态，G9 / G10 / G11 / G13 把默认值与其余分类条件各钉一行。

**判定语不是错误**：某行判定与期望不符时，`--action golden` 在载荷里把它报为 `match: false`，退出码仍为 `0`——一个不匹配是**已产出的判定**，不是引擎故障；把它读成故障会让「表漂移」和「引擎坏了」这两件事无法区分。
