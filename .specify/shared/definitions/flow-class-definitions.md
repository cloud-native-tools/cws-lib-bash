# Flow Class Definitions — 执行 / 表达流程分类

**Owner（唯一所有者）**: 本文件 `.specify/shared/definitions/flow-class-definitions.md` 是「执行 / 表达」分类轴的唯一所有者。
它拥有：**判据、两个取值、判定依据（`basis`）、边界例、命名空间、逐流程台账、类中立封闭清单、变更记录、同构映射（8 阶段 × 3 面）、不可同构边界**。
其他任何位置（命令模板、技能、契约、测试、门户文档）MUST 以「路径 + 章节锚」引用本文件，MUST NOT 复制判据句或取值定义，MUST NOT 以表格 / YAML / JSON / 代码常量的形式再声明一份「流程单元 → 类别」的映射；仓库中 MUST NOT 出现第二份分类数据文件。

**机器键**: `flow_class`（[[STR-003]]）。取值只有两个：`execution`（[[STR-001]]）与 `expression`（[[STR-002]]）。
四个共享字面量（`[[STR-001]]` / `[[STR-002]]` / `[[STR-003]]` / `[[STR-004]]`）的登记处是**父规格 069 的 § Shared Strings**——父规格是这些字面量的语义 owner，069a 与 069b 的表是同源投影；本文引用其语义，不另立第二张字面量表。

**覆盖范围**: 框架内全部流程单元——命令模板（`.specify/templates/commands/*.md` → `/speckit.<stem>`）与技能（`skills/{external,internal}/*/SKILL.md` → `skill:<dir-name>`）。
清单规模（实测 2026-10-24：`ls .specify/templates/commands/*.md | wc -l` → 27；`ls skills/{external,internal}/*/SKILL.md | wc -l` → 51）：命令 27 + 技能 51 = **78 行台账**。

**不在本文件**（只给指针，不复述）：

| 主题 | 所有者 |
|------|--------|
| 门禁算子集、文档型六面、阶段算子表、调用点表 | `.specify/shared/workflow/expression-gates.md` |
| 复杂度轴（复杂 / 简单命令，决定有无 wrap-up 面） | `.specify/shared/workflow/feedback-step.md` |
| 读取类别的唯一引擎 | `.specify/scripts/python/flow-class-check.py` |

## 判据

### 唯一问题

分类只回答一个问题：**该流程的主交付物，其验收由什么判定？**
判定 MUST NOT 引入第二个问题——失败是否不可逆、交付物有几件、由谁编写，都不构成第二判别量（主交付物并列时，失败不可逆性只作 tie-break）。

### 判定步骤（两步，必须都写得出答案）

1. **指认主交付物**：该流程验收完成时必须交出去、并被消费者用来做最终判定的那一件产物（多件时取被最终判定实际使用的那件）。
2. **指认判定面**：这件产物的缺陷，最先在哪一面暴露？
   - 机器面——脚本退出码、生成物不可用、下游流程或运行时消费失败、执行行为不符 → `execution`，`basis = behavior-oracle`。
   - 读者面——只有当人读错、或与外部事实不符时才暴露；结构 / 链接 / 构建检查通过不构成充分条件 → `expression`，`basis = reader-oracle`。
   - 两面都必须签字才算完成 → `mixed-oracle`，类别一律取 `execution`（父 069 §Edge Cases 首条；台账一致性的规范条款见 `.specify/specs/069b-isomorphism-migration-metrics/contracts/ledger-reconciler.md` C-7，本文件只留指针），并在台账该行 `notes` 保留父指针。

### 两个取值

- `execution`：主交付物在验收时被机器执行、解析或消费，其缺陷以可观测的行为差异显现（退出码、生成物不可用、下游流程失败、运行时行为不符）。
- `expression`：主交付物交给人阅读，其缺陷只有在读者读错或与外部事实不符时显现；机器结构检查通过只是必要条件。

### 判定依据 `basis`

| 取值 | 含义 |
|------|------|
| `behavior-oracle` | 判定由机器可观测的事实给出：运行行为、生成物可用性、脚本退出码、可对回制品的核验结论 |
| `reader-oracle` | 判定只能由读者给出：读懂与否、是否与外部事实相符 |
| `mixed-oracle` | 两种 oracle 都是最终判定所必需；类别取 `execution`，规范条款归 069b |

`basis` 是台账每行的必选列，也是 `lookup` 输出的一部分；它不是第三个类别，不改写任何取值。

### 不参与判定的因素（介质无关）

以下因素 MUST NOT 参与判定：文件扩展名、自然语言种类、是否含代码块、是否由脚本生成、交付物数量比例、构建 / 结构 / 链接检查是否通过、作者身份。
判定的全部输入是「主交付物 + 判定面」；凡是靠介质或制品形态推出的结论，一律按判据缺陷处理。

### 边界例

- **Markdown 架构文档 → `expression`**：交付物给人读，判据是读者能否理解并与外部事实相符；「它是 Markdown」不参与判定——同内容的纯文本或表格也一样。
- **须生成并编译 SDK 的 OpenAPI 契约 → `execution`**：验收落在「生成物能否编译、SDK 能否按契约调用」这一可观测行为上；它同时可被人阅读，不改变判定。
- **站点构建通过不改变判定**：`/speckit.docs`（文档内容，`expression`）与 `skill:create-pages`（站点构建与发布，`execution`）作用在同一棵文档树上——前者按读者面判定，后者按构建与页面可用性判定；构建绿只证明发布面可用（必要条件），不把文档内容改判为 `execution`。
- **未登记单元 → 默认 `execution` 并在消费点标注**：默认不等于已判定；判定缺席不得被读作表达类（FR-009，消费点标注形态归门禁侧调用点表）。

### 判据缺陷

指认不出唯一主交付物或唯一判定面 → 判为**判据缺陷**：先修判据、再对全部样本重判（FR-006），MUST NOT 就地逐案裁定。
台账与判据冲突时以判据为准，并把冲突本身记为缺陷（FR-005）。

### 不变量指针

类别 MUST NOT 被用作跳过或缩短阶段的开关：阶段集合、门禁数量与 analyze / review 的调用率不因类别改变（规范条款归 `.specify/shared/workflow/expression-gates.md` § 阶段不变量与 requirements FR-012 / FR-013 / FR-014，本文件不复述）。

## 命名空间

- `flow_class` 是本分类的机器键：台账列头、JSON 键、CLI 参数统一用它；裸 `execution` MUST NOT 充当键名。
- `execution` 与既有 **Agent Execution**（Agent 三层分类法第三层，概念见 `.specify/shared/definitions/agent-definitions.md`，词汇表见 `.specify/memory/glossary.md` 的 `Agent Execution` 行）**同词异义**：前者描述「流程主交付物的验收 oracle」，后者描述「Agent 模板 / 实例 / 执行」三层的第三层。
- 读法约束：`execution` 只有在 `flow_class` 语境下（本文件判据、台账列、`lookup` 输出）才读作本分类；出现在 `.specify/agents/execution/`、`execution-config.py` 等既有名称中时 MUST NOT 读作本分类。
- 词汇表侧的同词消歧行（`流程分类 (Flow Class)` / `执行类流程` / `表达类流程`）以本文件为 owner 指针；本文件不复述词汇表的同音 / 易混词列。

## 与复杂度轴正交

复杂度轴（复杂命令 / 简单命令）的 owner 是 `.specify/shared/workflow/feedback-step.md`：它决定**有没有 wrap-up 面**。本分类轴决定**门禁算子集**（owner：`.specify/shared/workflow/expression-gates.md`）。
两轴 MUST NOT 互相推导：由复杂度推类别、或由类别推 wrap-up 面，都是缺陷。可核对的对照：`/speckit.docs` 是复杂命令、`/speckit.humanize` 是简单命令，二者在本台账同为 `expression`。

## 同构映射（8 阶段 × 3 面）

一张表把「代码是以计算机语言写的文档、文档是以人类语言写的代码」落成可逐行核对的对应。行集是八阶段名册（owner：`.specify/skills/sdd-loop-driver/scripts/loop-state.py` 的 `STAGE_ARTIFACTS` 顶层键，声明见 `.specify/specs/066-loop-state-awareness-a/requirements.md` FR-006）；名册变更时映射跟着增删行，**不另立版本**。

legend（三面含义只在此声明一次，24 格不重复）：**结构 = 实体 / 关系 / 边界**——该阶段的产物由哪些实体构成、彼此是什么关系、到哪里为止；**流程 = 阶段与门禁角色**——该阶段在流程中的位置，以及哪个门禁面扮演出口判定；**逻辑 = 证据 / 契约 / 验收 / 版本 / 所有权**——该阶段用什么证明、与谁有契约、由谁验收、版本与所有权如何登记。

每个面格写成 `代码型：… ↔ 文档型：…`：左侧是执行类流程赖以验收的产物或判定面，右侧是表达类流程赖以验收的产物或判定面。`强制门禁` 列写出该行声称被强制的 face id；`强制门禁引用` 列写出与之对应的 `gate:<算子 id>`，算子 id 取自门禁 owner `.specify/shared/workflow/expression-gates.md` § 阶段算子表的 `算子 id` 列；`强制状态` 列取封闭两值。三列都只引用门禁 owner，不复述算子文本。

- `已强制`：该行点名的**每个** `(阶段, face)` 都有一个 `gate:<算子 id>` 引用解析到该 `(阶段, face)` 的 blocking 算子行。
- `已声明未强制`：该阶段此刻没有任何 blocking 算子行——它只是如实标注，不构成通过、不构成豁免，也不构成新增未强制行的许可。

该声明是**引用级可证伪**：引用缺失、写成未知 id、解析到 advisory 算子、解析到别的阶段或别的 face，都各自转红；24 格自由文本是否真的在描述那个门禁，仍由评审面（`C-10`）判定，检查器不声称能判定语义真实性。

| 阶段 | 结构（实体 / 关系 / 边界） | 流程（阶段与门禁角色） | 逻辑（证据 / 契约 / 验收 / 版本 / 所有权） | 强制门禁 | 强制门禁引用 | 强制状态 |
| --- | --- | --- | --- | --- | --- | --- |
| requirements | 代码型：需求清单的机器解析入口与条目边界 ↔ 文档型：需求条目的章节结构与术语边界 | 代码型：validator 五项检查作为阶段出口门禁 ↔ 文档型：读者与目的声明作为澄清入口 | 代码型：FR 编号与验收条款的可复算绑定 ↔ 文档型：断言的证据等级与外部事实来源 | `requirements-clarity`、`evidence-asof` | `gate:G-req-clarity`、`gate:G-req-evidence` | 已强制 |
| clarify | 代码型：写回规格的裁定条目与受影响条款集合 ↔ 文档型：澄清问答的章节归属与术语修订 | 代码型：pre-analyze 复跑作为需求变更后的门禁 ↔ 文档型：读者声明与阅读场景补齐 | 代码型：裁定与 FR 条款的引用闭合 ↔ 文档型：裁定依据的引文出处与 as-of | `requirements-clarity`、`reader-purpose` | `gate:G-clarify-clarity`、`gate:G-clarify-reader` | 已强制 |
| plan | 代码型：设计产物的文件集与契约条款编号 ↔ 文档型：设计叙述的实体与关系模型 | 代码型：pre-analyze 阶段检查作为计划出口 ↔ 文档型：结构与链接构建面复核 | 代码型：契约条款与 FR 的覆盖映射 ↔ 文档型：设计决策的事实唯一性与版本声明 | `fact-consistency`、`structure-links-build` | `gate:G-plan-fact`、`gate:G-plan-structure` | 已强制 |
| tasks | 代码型：任务行的依赖标签与勾选状态 ↔ 文档型：任务叙述的执行顺序与边界 | 代码型：validate-tasks 的计数与认领检查 ↔ 文档型：任务阶段的读者与目的声明 | 代码型：绿点认领与契约条款的一一对应 ↔ 文档型：证据等级与 as-of 的行内标注 | `fact-consistency`、`evidence-asof` | `gate:G-tasks-fact`、`gate:G-tasks-evidence` | 已强制 |
| checklist | 代码型：清单条目的编号与可判定形态 ↔ 文档型：需求质量问题的分类叙述 | 代码型：清单被后续门禁机器消费的入口 ↔ 文档型：读者声明复核与跨文件副本检查 | 代码型：条目到需求条款的覆盖计数 ↔ 文档型：条目依据的引文出处 | `reader-purpose`、`fact-consistency` | `gate:G-checklist-reader`、`gate:G-checklist-duplicate` | 已强制 |
| analyze | 代码型：跨产物检查的输入集合与 finding 结构 ↔ 文档型：一致性结论的章节归属与读者边界 | 代码型：`/speckit.analyze` 作为 100% 调用率的门禁 ↔ 文档型：评审基线确认的读者基准 | 代码型：findings 到产物位置的定位 ↔ 文档型：结论断言的事实来源与版本 | `fact-consistency`、`review` | `gate:G-analyze-fact`、`gate:G-analyze-review` | 已强制 |
| implement | 代码型：代码改动与生成物的文件边界 ↔ 文档型：规格回填的章节与术语边界 | 代码型：构建与结构检查作为实现出口 ↔ 文档型：自然度与读者适配抽样 | 代码型：测试与证据记录的运行结论 ↔ 文档型：回填断言的证据等级与 as-of | `structure-links-build` | `gate:G-implement-structure` | 已强制 |
| review | 代码型：findings 的分级与对象定位 ↔ 文档型：评审报告的组织与读者范围 | 代码型：`/speckit.review` 作为 100% 调用率的门禁 ↔ 文档型：读者基准下的可理解性判定 | 代码型：finding 到阶段记录的逐条对回 ↔ 文档型：结论与外部事实的一致性证据 | `review`、`fact-consistency` | `gate:G-review-review`、`gate:G-review-fact` | 已强制 |

## 不可同构边界

同构映射到此为止：下面四条是两侧**不能互换**的判定面，任一条被跨过，上表的对应关系就不再成立。每条边界 MUST 在门禁设计里有对应处理——`门禁处理` 列同时写出封闭 face id 与处理方式，只列 face id 不算绑定。边界与映射同属本文件，MUST NOT 拆成两份各自漂移。

| 边界 | 不可互换的判定面 | 为什么不能互换 | 门禁处理 |
| --- | --- | --- | --- |
| a | 验收 oracle：执行行为 vs 阅读理解 | 代码型交付物由运行行为判定，文档型交付物由读者理解与外部事实判定；把读者判定换成运行判定，会漏掉「读起来就是错的」这类缺陷 | `review` 面按声明的读者基准判定；`requirements-clarity` 面只校验结构，不替代读者判定 |
| b | 验证算子：测试 vs 构建 / 链接 / 一致性检查 | 测试能证明行为，构建与链接只能证明可用；把构建通过当作内容正确，会把「通过但事实陈旧」判成合格 | `structure-links-build` 面按零新增违规执行，只作必要条件；`fact-consistency` 面负责事实唯一性 |
| c | 失败可见性：运行期偏差 vs 构建通过而事实陈旧的静默失败 | 运行期偏差会以退出码或异常暴露；文档型失败可以在构建全绿时静默存在，只能靠证据与评审面显式暴露 | `evidence-asof` 面强制断言的等级、as-of 与来源三件套；`review` 面复核事实一致性 |
| d | 语义 oracle 缺失：文档没有编译器，意义只能由人判定 | 编译与测试不产生「意义是否正确」的判定；文档型交付物的语义只能由读者与外部事实给出 | `review` 面承担语义判定；`reader-purpose` 面要求声明读者与阅读场景作为判定前提 |

机械下限：24 格两侧成对（缺一侧即缺陷）；`.specify/templates/commands/` 与 `skills/` MUST NOT 出现以「文档即代码」为理由的许可句；上述两张表的单元格 MUST NOT 用介质作为分类理由（扩展名、语言种类、是否含代码块、是否由脚本生成）；门禁 owner 的算子列 MUST NOT 出现代码型算子。强制声明的可证伪粒度是**引用级**：每行 `强制门禁引用` 的 `gate:<算子 id>` 必须解析到门禁 owner 在该 `(阶段, face)` 的 blocking 算子行，缺失 / 未知 / 非 blocking / 错 `(阶段, face)` 都转红；引用级通过 MUST NOT 被读作「24 格自由文本的语义已被证明」。语义判定（一句主张是否真的落地）归评审面，检查器不声称能判定自由文本的可判定性。核对入口：`.specify/scripts/python/flow-class-check.py --action isomorphism`（只读；判据归本文件与门禁 owner）。

## 所有权：归框架，客户项目只为自己新增的流程声明

- 分类所有权归框架；客户项目 MUST NOT 覆盖框架流程的类别。
- 客户项目 MAY 按同一判据为自己新增的流程声明类别：项目 MAY 在自己的知识空间记录类别；该记录框架不读取、不改变门禁（不影响门禁）。本版不提供项目侧声明面、存储或读取点。
- 框架源与客户运行时副本并存时以本文件为准：副本 MUST 由生成 / 刷新产生并带漂移检查，副本不是第二真源。

## 逐流程台账

**台账版本**: 1（2026-10-25）
生效版本由本文件的文档版本与既有 § 变更记录 共同承载；台账**行级不设版本列**，
本声明在 § 逐流程台账 内只出现一次（缺失 → `ledger-version-missing`，重复 → `row-malformed`；规范条款归
`.specify/specs/069b-isomorphism-migration-metrics/contracts/ledger-reconciler.md` C-5）。

一行一个流程单元，首格是单元 id（命令 `/speckit.<stem>`，技能 `skill:<dir-name>`）；列按**表头名**解析，解析器 MUST NOT 猜列。
列头逐字取机器键 `flow_class`；`basis` 取本节上文的三值；`neutral` 只允许留空或 `yes`（`yes` 仅用于 § 类中立清单 中的技能）；`notes` 是该行的判定要点，不复述判据正文。
`mixed-oracle` 行一律取 `execution`（父 069 §Edge Cases 首条；规范条款见 `.specify/specs/069b-isomorphism-migration-metrics/contracts/ledger-reconciler.md` C-7），行内 `notes` 保留父指针。

| unit_id | flow_class | basis | neutral | notes |
| --- | --- | --- | --- | --- |
| /speckit.agents | execution | behavior-oracle |  | 交付代理定义与调度结果；以派发后的行为与 agent 校验判定 |
| /speckit.analyze | execution | behavior-oracle |  | 交付一致性分析结论；可重跑复算并作为门禁裁决 |
| /speckit.checklist | execution | behavior-oracle |  | 交付需求质量清单；条目被后续门禁机器消费 |
| /speckit.clarify | execution | behavior-oracle |  | 交付写回规格的裁定；由 validator 与下游流程读取判定 |
| /speckit.constitution | execution | mixed-oracle |  | 治理文本由读者判、版本推进由引擎判；父 069 §Edge Cases 首条（规范条款见 `.specify/specs/069b-isomorphism-migration-metrics/contracts/ledger-reconciler.md` C-7） |
| /speckit.derive | expression | reader-oracle |  | 交付可重放的推导链；是否可溯源只能由读者判定 |
| /speckit.docs | expression | reader-oracle |  | 首批成员；文档内容由读者与外部事实判定（FR-025） |
| /speckit.feature | execution | behavior-oracle |  | 交付特性注册行与详情；由命令读取与状态机脚本判定 |
| /speckit.feedback | execution | behavior-oracle |  | 交付反馈条目与分流结果；路由与打包结果可判定 |
| /speckit.goal | execution | behavior-oracle |  | 交付目标定义与共用关系；由 goal 引擎校验判定 |
| /speckit.history | execution | behavior-oracle |  | 交付 manifest 与主题知识；增量与去重可机器判定 |
| /speckit.humanize | expression | reader-oracle |  | 首批成员；保真与自然度由读者判定（FR-025） |
| /speckit.implement | execution | mixed-oracle |  | 代码须运行、规格回填须读者核；父 069 §Edge Cases 首条（规范条款见 `.specify/specs/069b-isomorphism-migration-metrics/contracts/ledger-reconciler.md` C-7） |
| /speckit.improve | execution | behavior-oracle |  | 交付改进后的技能 / 代理 / 团队 / 工具；以再运行与校验判定 |
| /speckit.instructions | execution | mixed-oracle |  | 指令文本由读者判、符号链接由脚本判；父 069 §Edge Cases 首条（规范条款见 `.specify/specs/069b-isomorphism-migration-metrics/contracts/ledger-reconciler.md` C-7） |
| /speckit.interview | execution | mixed-oracle |  | 目标产物因对象而异、ledger 由引擎传播且收敛须用户确认；父 069 §Edge Cases 首条（规范条款见 `.specify/specs/069b-isomorphism-migration-metrics/contracts/ledger-reconciler.md` C-7） |
| /speckit.plan | execution | behavior-oracle |  | 交付设计产物；由 pre-analyze 检查与下游 tasks 消费判定 |
| /speckit.requirements | execution | behavior-oracle |  | 交付需求规格；由 validator 与下游流程消费判定 |
| /speckit.research | execution | behavior-oracle |  | 交付研究结论；由 plan 与 pre-analyze 检查消费判定 |
| /speckit.review | execution | behavior-oracle |  | 交付评审结论；findings 逐条对回阶段记录与制品 |
| /speckit.sanitize | execution | behavior-oracle |  | 交付清理结果与残留清单；由脚本复算判定 |
| /speckit.session | execution | behavior-oracle |  | 交付会话导出目录；文件集与清单可校验 |
| /speckit.skills | execution | behavior-oracle |  | 交付技能实体；以再运行与校验判定 |
| /speckit.tasks | execution | behavior-oracle |  | 交付任务清单；由 validate-tasks 与覆盖核对判定 |
| /speckit.team | execution | behavior-oracle |  | 交付团队定义与运行报告；由预检与运行结果判定 |
| /speckit.todo | execution | behavior-oracle |  | 交付 TODO 块与搁置条目；由扫描器判定 |
| /speckit.tools | execution | behavior-oracle |  | 交付 Tool 记录；由校验与调用行为判定 |
| skill:create-docs | expression | reader-oracle |  | 首批成员委派技能；文档内容由读者与外部事实判定 |
| skill:create-pages | execution | behavior-oracle |  | 边界例：站点构建通过只证发布面可用、不改文档内容类别 |
| skill:create-skills | execution | behavior-oracle |  | 交付技能实体；以再运行与校验判定 |
| skill:database-utils | execution | behavior-oracle |  | 交付查询结果；以 SQL 执行行为判定 |
| skill:document-utils | execution | behavior-oracle |  | 交付读写后的文档文件；以产物可打开与可渲染判定 |
| skill:draw-diagram | execution | behavior-oracle |  | 交付图源与渲染产物；以渲染结果与结构判定 |
| skill:git-utils | execution | behavior-oracle |  | 交付平台对象与分支状态；以平台行为判定 |
| skill:humanize | expression | reader-oracle |  | 首批成员执行体；保真与自然度由读者判定（W4 承载唯一读取） |
| skill:improve-docs | expression | reader-oracle |  | 改进后的文档；读者面判定，与 /speckit.docs 同类 |
| skill:improve-skills | execution | behavior-oracle |  | 交付改进后的技能；以再运行判定 |
| skill:merge-skills | execution | behavior-oracle |  | 交付合并后的技能实体；覆盖与再运行可核验 |
| skill:sdd-loop-driver | execution | behavior-oracle |  | 交付阶段推进与证据；由阶段记录与检查器判定 |
| skill:sdd-project-setup | execution | behavior-oracle |  | 交付项目调谐结果；由机制分级脚本判定 |
| skill:think-skills | execution | behavior-oracle |  | 交付执行行为的模拟判定；以与真实运行一致为准 |
| skill:analyze-artifacts | execution | behavior-oracle |  | 交付一致性分析结论；可重跑复算并作为门禁裁决 |
| skill:archive-session | execution | behavior-oracle | yes | 类中立（session）：导出会话产物，无自身交付物 |
| skill:clarify-artifact | execution | behavior-oracle |  | 交付写回制品的裁定；由下游读取与校验判定 |
| skill:code-review | execution | behavior-oracle |  | 交付代码评审结论；判定对象是代码差异的可验证缺陷 |
| skill:collect-evidence | execution | behavior-oracle | yes | 类中立（evidence）：为目标单元采集证据，findings 归属被采集单元 |
| skill:create-agent | execution | behavior-oracle |  | 交付代理定义；以派发后的行为判定 |
| skill:create-checklist | execution | behavior-oracle |  | 交付质量清单；条目被后续门禁消费 |
| skill:create-plan | execution | behavior-oracle |  | 交付设计产物；由 pre-analyze 检查与下游消费判定 |
| skill:create-requirements | execution | behavior-oracle |  | 交付需求规格；由 validator 与下游消费判定 |
| skill:create-tasks | execution | behavior-oracle |  | 交付任务清单；由 validate-tasks 与覆盖核对判定 |
| skill:create-team | execution | behavior-oracle |  | 交付团队定义；由预检与运行结果判定 |
| skill:create-tools | execution | behavior-oracle |  | 交付 Tool 记录；由校验与调用行为判定 |
| skill:derive-architecture | expression | reader-oracle |  | 交付可重放的推导链；是否可溯源只能由读者判定 |
| skill:implement-feature | execution | mixed-oracle |  | 代码须运行、规格回填须读者核；父 069 §Edge Cases 首条（规范条款见 `.specify/specs/069b-isomorphism-migration-metrics/contracts/ledger-reconciler.md` C-7） |
| skill:improve-agent | execution | behavior-oracle |  | 交付改进后的代理；以再运行判定 |
| skill:improve-team | execution | behavior-oracle |  | 交付改进后的团队；以运行与阈值判定 |
| skill:improve-tools | execution | behavior-oracle |  | 交付改进后的 Tool 记录；以校验与调用判定 |
| skill:manage-agents | execution | behavior-oracle |  | 交付多 Agent 接线状态；由接线脚本核验判定 |
| skill:manage-constitution | execution | mixed-oracle |  | 治理文本由读者判、版本与校验由引擎判；父 069 §Edge Cases 首条（规范条款见 `.specify/specs/069b-isomorphism-migration-metrics/contracts/ledger-reconciler.md` C-7） |
| skill:manage-features | execution | behavior-oracle |  | 交付特性注册与详情；由状态机脚本判定 |
| skill:manage-feedback | execution | behavior-oracle | yes | 类中立（feedback）：分流调用方的反馈条目，无自身交付物 |
| skill:manage-goal | execution | behavior-oracle |  | 交付目标定义；由 goal 引擎校验判定 |
| skill:manage-history | execution | behavior-oracle |  | 交付知识库与 manifest；增量与去重可机器判定 |
| skill:manage-instructions | execution | mixed-oracle |  | 指令文本由读者判、符号链接由脚本判；父 069 §Edge Cases 首条（规范条款见 `.specify/specs/069b-isomorphism-migration-metrics/contracts/ledger-reconciler.md` C-7） |
| skill:manage-todo | execution | behavior-oracle |  | 交付 TODO 块与搁置条目；由扫描器判定 |
| skill:memory-recall | execution | behavior-oracle | yes | 类中立（memory）：检索并注入记忆，不产出自己的制品 |
| skill:memory-record | execution | behavior-oracle | yes | 类中立（memory）：记录调用方流程的决策与状态 |
| skill:research-feature | execution | behavior-oracle |  | 交付研究结论；由 plan 与 pre-analyze 检查消费判定 |
| skill:review-sdd-process | execution | behavior-oracle |  | 交付评审结论；findings 逐条对回阶段记录与制品 |
| skill:run-agent | execution | behavior-oracle |  | 交付一次代理运行结果；以运行行为判定 |
| skill:run-interview | execution | mixed-oracle |  | 收敛须用户确认、ledger 由引擎传播；父 069 §Edge Cases 首条（规范条款见 `.specify/specs/069b-isomorphism-migration-metrics/contracts/ledger-reconciler.md` C-7） |
| skill:run-skills | execution | behavior-oracle |  | 交付技能运行结果；以实际执行判定 |
| skill:run-team | execution | behavior-oracle |  | 交付团队运行报告；以运行结果判定 |
| skill:sanitize-materials | execution | behavior-oracle |  | 交付清理结果与残留清单；由脚本复算判定 |
| skill:self-improvement | execution | behavior-oracle |  | 交付改进点与运行记录；由引擎记录判定 |
| skill:study-project | expression | reader-oracle |  | 交付架构分析报告；报告是否读懂由读者判定 |
| skill:summarize-project | expression | reader-oracle |  | 交付项目总结报告；呈现是否可用由读者判定 |

台账完备性以**仓库清单**为准：清单有而台账无 → 缺口，台账有而清单无 → 未登记项，两侧 MUST 双向覆盖、零缺口（对账由 `.specify/scripts/python/flow-class-check.py --action check` 执行）。
同一单元在台账中 MUST 恰好一行；两行同值 → 重复，两行反值 → 双类冲突。

## 类中立清单

类中立是**封闭清单**：登记「承载调用方产物、没有自己的交付物」的共享技能，用来豁免「命令与其委托技能 MUST 同类」这一条约束。
类中立**不改变**该单元自身的类别键（仍是一个二值），也**不豁免任何门禁**——门禁是否执行只由门禁 owner 的调用点表决定。
清单外出现 `neutral: yes` 即缺陷；清单内条目 MUST 存在于技能清单且台账该行为 `neutral: yes`。

| unit_id | category | rationale |
| --- | --- | --- |
| skill:memory-record | memory | 记录调用方流程的决策与状态，条目归属调用方，无独立交付物 |
| skill:memory-recall | memory | 检索并向调用方注入已有记忆，不产出自己的制品 |
| skill:manage-feedback | feedback | 汇总并分流调用方产生的反馈条目，条目归属上报单元 |
| skill:collect-evidence | evidence | 为目标单元采集证据，findings 与边界声明归属被采集单元 |
| skill:archive-session | session | 导出当前会话产物，内容归属被导出的会话 |

## 变更记录

台账每次类别变更 MUST 在此留一行：`date | unit_id | before → after | basis | 依据`。
变更记录是审计痕迹，MUST NOT 被当作当前取值的来源——当前取值只从 § 逐流程台账 读。
空表表示自本版起尚无类别变更。

| date | unit_id | before → after | basis | 依据 |
| --- | --- | --- | --- | --- |

## 消费方指针

- 读取类别：`.specify/scripts/python/flow-class-check.py --action lookup --unit-id <id>`（唯一读取路径；命令模板与技能 MUST NOT 内嵌类别副本）。
- 对账：同引擎 `--action check`（八类 finding 与反空真下限归契约 `contracts/flow-class-ledger.md`）。
- 同构映射与边界核对：同引擎 `--action isomorphism`（只读；判定归本文件 § 同构映射 / § 不可同构边界与门禁 owner）。
- 门禁算子与调用点：`.specify/shared/workflow/expression-gates.md`（本文件不列举面名、算子与调用点）。
