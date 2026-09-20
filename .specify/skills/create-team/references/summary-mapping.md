# 团队 → 项目管理概念映射(summary 机制的单一事实源)

> **定位**:本文件是 `036-team-summary` 机制中「团队词汇 → `summarize-project` 项目管理实体」映射的**单一事实源**(FR-001)。表单生成器 `scripts/build-summary-input.py` 按本文件实现;报告与契约引用本文件而不各自重述。
>
> **边界**:`summarize-project` 保持不变(只读呈现工具、输入面仍是表单),适配责任全在团队侧(FR-024)。字段定义与约束的权威是该技能的 `schema/project.sql`(DDL),本文件不复写 schema。

## 0. 双索引:产物落在哪一侧

| 索引 | 路径 | 内容 | 回答的问题 |
|------|------|------|-----------|
| **team 索引** | `.specify/teams/<team-slug>/` | 运行信息(事实源):`runs/` / `STATE.md` / `run-log.jsonl` / `items.jsonl` / `constraints.md` | 这个团队在怎么运行 |
| **goal 索引** | `.specify/goal/<goal-slug>/summary/` | **唯一的完整总结**(派生物、自包含交付目录) | 这个目标推进到哪里 |

团队目录 MUST NOT 承载完整总结产物(FR-017)。总结步骤期间团队目录 MUST 保持字节不变(FR-020)。

## 1. 聚合范围

映射的对象是**一个 goal**,而非一个团队。设该 goal 下有 N 个团队(N ≥ 1,即声明了同一 `goal_slug` 的全部团队),下表来源在这 N 个团队上取并集,`project` 与 `milestones` 取自 goal 本身。

某团队本次未参与刷新 MUST NOT 导致其此前贡献的工作项从总结中消失(FR-032)——每次刷新都从该 goal 下全部团队的台账重新折叠。

## 2. 七实体来源表(FR-007:每个实体要么有来源,要么有显式缺席降级)

| 实体 | 团队侧来源 | 缺席降级 |
|------|-----------|---------|
| `project` | **goal 级**:`project_name` ← 解析出的 goal 身份;`project_desc` ← 该 goal 的**定义** `.specify/goal/<goal-slug>/goal.md` 的目标叙述(定义存在时),无定义时回退到团队内联 goal 正文;`baseline_date` ← 本次触发运行/cycle 的时间戳(FR-005,不依赖被调技能读系统时钟);`repos` 恒为空(不 opt-in 扫仓) | 不可缺席(R 档) |
| `people` | N 个团队名册行的**并集**;`owner_id` ← 名册 agent slug;`owner_name` ← 所引用 agent 定义的 frontmatter `name`(解析顺序见 §5);`owner_role` ← 名册 `role`。同一 agent slug 出现在多个团队 → 归并为一人 | 解析不到定义 → `owner_name` 记 `未记录`,不臆造(FR-004) |
| `phases` | N 个团队各自的阶段单位,**按团队命名空间化**(见 §3) | 无阶段材料 → 该团队单一阶段并声明 |
| `work_items` | N 个团队 `items.jsonl` 台账的**并集**(权威结构面,见 §6) | 全部团队台账为空且 `runs/` 亦无交付物 → 拒绝出总结(`declined(no-material)`) |
| `milestones` | **goal 级,只一套**:定义存在时逐条映射该 goal **定义**的成功判据(`source` 指向 `goal.md`);无定义时回退到解析内联 goal 正文的判据(FR-013);`anchor_item_id` 锚到对应工作项(FR-003) | 定义判据为空(`None provided.`)或内联无判据 → 该组为空并显式声明,依赖 `work_items` 满足 R 档组级约束 |
| `features` | N 个团队产出的能力/交付物类目并集 | 无类目材料 → 空,《需求与特性》按既有降级只留声明 |
| `sources` | 每个团队每组信息一条声明,`source_kind: user-form`,`source_ref` 指向该团队的 tracked 工件路径 | 不可缺席(否则条目 `source` 无法推断) |

### 2.1 `coverage` 块 MUST 恒定产出

`coverage` 只在表单显式提供时才有值;而落盘门禁 **CG-COVERAGE** 规定「报告含 `@startwbs` 却无覆盖完整性声明 → FAIL」,功能分解图又是无条件出图项。因此生成器 MUST 每次都产出该块:

| 字段 | 团队侧口径 |
|------|-----------|
| `candidate_total` | 台账中出现过的全部 `item_id` 去重计数 |
| `excluded` | `excluded_reason` 非空的条目数(如 iteration 被淘汰变体) |
| `granularity_truncated` | 已完成/已归档且在呈现层被聚合为计数的条目数(FR-029) |
| `unattributed` | 有交付物证据但无法归属到任何阶段的条目数 |
| `source_label` | `团队条目台账 items.jsonl` |

闭合等式由引擎产出(`coverage.closure_equation`),报告照抄,团队侧不做减法。

## 3. 四种协作模式的阶段 / 工作项语义(FR-002)

| 模式 | `phases` 单位 | `work_items` 单位 |
|------|--------------|------------------|
| `continuous` | cycle | `STATE.md` 被跟踪条目(经台账) |
| `iteration` | generation(代) | 每代变体任务 + 被采纳的改进项 |
| `serial` | stage | 各 stage 的交付物 |
| `parallel` | 派发批次 | 各 territory(领地) |

**阶段 MUST 按团队命名空间化**:`phase_id` 形如 `<team-slug>.PH-<nnnn>`、`phase_name` 形如 `<team-slug> · <单位>`。同一 goal 下的团队可能模式不同、阶段单位不同,混为一条有序序列会断言一个并不存在的顺序。

## 4. 状态归一(FR-006)

| 团队侧信号 | 归一状态 |
|-----------|---------|
| 条目已解决 / 已归档 / 已采纳落地 | `completed` |
| 条目在本阶段被处理中,或 L2+ 已提交变更待验证 | `in-progress` |
| 有计划完成日且已越过、仍未完成 | `delayed` |
| 已入台账但尚未被任何阶段处理 | `not-started` |
| **无任何状态信号** | `unknown` — MUST NOT 记 `not-started`,MUST NOT 记 `0%` |

**被调引擎已兜住的三条**(团队侧只需不伪造输入,不重复实现):

- 无勾选比、无明写百分比 → `project.progress.progress_pct = null` 并附 `reason`,**不写 0%**。
- 无排期材料 → `gantt.bar_count = 0`、`has_planned_dates = false`,**甘特不出图**。
- 阶段聚合**排除** `unknown` 条目,既不拖累也不虚增完成率。

**成熟度锚定**:状态语义按条目发生时的成熟度(`maturity_at_event`)解释。L1(report-only)期间的条目 MUST NOT 因团队升级到 L2/L3 而被追溯改写为「已行动」。

## 5. 人员称名解析顺序

1. `.specify/agents/instances/<slug>.agent.md` 的 frontmatter `name`(Agent Instance,项目创建)
2. `.specify/agents/templates/<slug>.agent.md` 的 frontmatter `name`(Agent Template,init 安装)

同名时 **instance 优先**。旧平铺路径 `.specify/agents/<slug>.agent.md` 已废弃,MUST NOT 使用。运行中的子代理属第三层 **Agent Execution**,其运行日志不得作为出处(见 §7)。

## 6. Item Ledger — `.specify/teams/<team-slug>/items.jsonl`

tracked、append-only、JSON Lines。每行一个**条目状态事件**。只由团队主管写入(FR-021);子代理 MUST NOT 写入。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `item_id` | string | 是 | 条目身份,文法见 §6.2。重命名时不变(FR-026) |
| `title` | string | 是 | 条目标题(可含中文;**不**作为身份键) |
| `phase_ref` | string | 是 | 所属阶段 ID,对应模式的阶段单位 |
| `state` | enum | 是 | `completed` / `in-progress` / `delayed` / `not-started` / `unknown` |
| `provenance` | string | 是 | tracked 工件路径(可带 `#anchor` / `:line`)。无出处则本行非法(FR-010/FR-011) |
| `ts` | string | 是 | 事件时间戳(ISO-8601 UTC),同时是基线日期来源 |
| `identity` | enum | 是 | `explicit`(团队发放) / `inferred`(历史回填,FR-027) |
| `supersedes` | string | 否 | 被本行归并的推断身份 ID,用于两态交接 |
| `excluded_reason` | string | 否 | 计入被排除口径的理由;非空即不计入延期/未完成 |
| `maturity_at_event` | string | 否 | 事件发生时的成熟度(L1/L2/L3),锚定状态语义 |
| `target_ref` | string | 否 | 归属的 Target 身份(038)。**局部形** `T-\d{3}`,goal 由团队绑定隐含;缺省 = 归属 goal 整体。见 §6.5 |

示例行:

```json
{"item_id":"TI-0007","title":"P7 sync-mirrors 单入口","phase_ref":"PH-0002","state":"completed","provenance":".specify/teams/demo/runs/20260730T094500Z-report.md#deliverables","ts":"2026-07-30T09:45:00Z","identity":"explicit","maturity_at_event":"L1"}
```

### 6.1 不变式

- **IL-1**:append-only。既有行 MUST NOT 被改写或删除;状态推进以追加新行表达。
- **IL-2**:同一 `item_id` 的**最后一行**(按 `ts`,同 `ts` 按文件顺序)决定其当前状态。
- **IL-3**:`provenance` MUST 指向 tracked 路径。`.specify/teams/.work/**`、`.specify/agents/execution/logs/**` 以及仓库外路径(如 `${TMPDIR}/spec-kit-dispatch/**`)一律非法。
- **IL-4**:`identity: explicit` 的行其 `item_id` MUST 匹配 `TI-<nnnn>`;`inferred` MUST 匹配 `TIX-<8hex>`。
- **IL-5**:`supersedes` 非空时,被指向的 ID MUST 在本台账中出现过,且折叠后 MUST 只产生一条记录。

### 6.2 身份文法(受 DDL 硬约束)

`entity_ids.entity_id` 的 DDL CHECK 为 `GLOB '[A-Za-z0-9]*' AND NOT GLOB '*[^A-Za-z0-9_.-]*'`——首字符字母或数字,其余仅 `[A-Za-z0-9_.-]`。越界(含空格、含中文)会以**退出码 3** 被拒。

| 实体 | 文法 | 发放者 |
|------|------|--------|
| 工作项(显式) | `TI-<nnnn>`,零填充四位,团队内单调递增 | 团队主管,写台账时发放 |
| 工作项(推断) | `TIX-<8hex>`,`sha256(title + "\u0000" + phase_ref)` 前 8 位小写十六进制 | 生成器,回填历史条目时确定性计算 |
| 阶段 | `PH-<nnnn>` | 生成器,按阶段单位序号 |
| 里程碑 | `MS-<nnnn>` | 生成器,按 goal 判据序号 |
| 人员 | 名册 agent slug 原文 | 既有(已合法) |

**中文标题 MUST NOT 直接作为 ID**;推断身份必须先经上述哈希。

**聚合下的唯一性(重要)**:N 个团队的台账装载进**同一个** `project.db`,而 `entity_ids` 是**全局** ID 命名空间(跨实体唯一,由触发器强制)。团队内单调递增的 `TI-<nnnn>` 因此会跨团队撞号(实测:两个团队各自的 `TI-0001` 同时入库 → 退出码 3,`item_id='TI-0001' 在本实体内重复`)。生成器 MUST 在折叠时为工作项与阶段 ID 加团队命名空间前缀(`<team-slug>.TI-0007` / `<team-slug>.PH-0002`;`.` 属允许字符),使聚合后仍全局唯一;该前缀同时承载归属(FR-033)。**此约束只作用于聚合层——团队台账内部仍写不带前缀的 `TI-<nnnn>`**,以免团队侧发放逻辑依赖 goal 拓扑。

### 6.3 两态交接(FR-027)

1. 历史条目(团队开始发放显式 ID 之前)以 `TIX-<8hex>` 回填,`identity: inferred`,并在表单 `inferred_fields` 留痕(`inferred_from` 非空,由 DDL 强制)。
2. 同一条目其后获得显式 ID 时,追加一行 `identity: explicit` + `supersedes: TIX-<hex>`。
3. 折叠时以显式 ID 为权威并合并其历史事件为**一条**记录,MUST NOT 同时呈现两条。
4. 推断身份时代发生重命名 → 哈希改变,旧 ID 按「本次未见」处理并进入材料缺口声明,不静默消失。

### 6.4 `STATE.md` 交叉引用

维护 `STATE.md` 的团队 MUST 在其被跟踪条目上内联 `[TI-nnnn]` 标记,供人交叉引用。台账仍是机器解析面;该标记不对 `STATE.md` 的散文形态施加 schema。

### 6.5 `target_ref` 归属折叠(038)

可选 [[STR-003]] 把条目归属到绑定 goal 的一个 Target(目标切片,概念见 `.specify/shared/definitions/goal-definitions.md` Target Decomposition,授权面是 `/speckit.goal targets`):

- **归属**:行携带合法局部形且该身份存在于绑定 goal 的 `## Targets` 节 → 计入该 Target 的归属集合;末行定态语义(IL-2)不变——同一 `item_id` 以最后事件为准。
- **降级**:指向不存在身份(或限定形等非法形态)→ 按 goal 整体降级计入,表单 `targets.invalid_refs` 计数并显式声明;MUST NOT 臆造 Target(FR-014)。
- **缺省**:无 `target_ref` → 归属 goal 整体(`targets.unattributed_to_target` 计数);存量行语义不变。
- **正交性**:团队命名空间前缀(`<team-slug>.TI-nnnn`,§6.2)照常加;`target_ref` 仍为局部形,二者互不影响。
- **表单产出**:goal 定义存在 `## Targets` 节 → 表单新增 `targets:` 块——每 Target 的 `authored_status` / `attributed_items` / `completed_items` / `pending_approval`、按 authored 终态计的 `coverage`(n/m)、`unattributed_to_target`、`invalid_refs`。切片轴与判据轴**分列**,MUST NOT 由 Target 完成度推导 goal `achieved`(SC-005)。authored 与证据不一致(open/全完成 或 done/未完成)→ `pending_approval: true` 并列为待批准/复核项,两侧均不自动翻转(FR-015)。
- **无节 goal**:表单 MUST 不含 `targets:` 块,既有输出逐字节不变(SC-002)。

## 7. 出处纪律(FR-010 / FR-011)

- 每个状态与进度数值 MUST 携带 `source`,指向一个具体的 tracked 团队工件路径;无出处的数值 MUST 被拒绝,而非以默认值落库。
- **可采纳**:`.specify/teams/<slug>/{team.md,STATE.md,run-log.jsonl,items.jsonl}`、`runs/**`,以及 tracked 的 `.specify/agents/execution/configs/**` 与 `.specify/agents/execution/scripts/**`。
- **不可采纳**:`.specify/teams/.work/**`(运行中间物,git-ignored)、`.specify/agents/execution/logs/**`(运行时日志,git-ignored,含外部派发可见性三元组 `.live.log` / `.jsonl` / `.status`)、以及任何仓库外路径。
- 只存在于不可采纳位置的数值 MUST 降级为 `unknown`,MUST NOT 从缓存或记忆回填——出处必须在读取时可验证。

## 7.1 写入面与不变性的边界(FR-020 / FR-021)

不变性约束的对象是**总结步骤**,不是团队的全部运行。二者必须分清,否则会得出"团队永远不能写 `STATE.md`"这种错误结论。

| 阶段 | 允许写入 | 说明 |
|------|---------|------|
| **总结步骤**(SUMMARIZE) | **白名单**:仅 `.specify/goal/<goal-slug>/summary/**` 与反馈存量 | 纯派生步骤。此期间**六组** MUST 保持字节不变:① `.specify/goal/<goal-slug>/goal.md`(被撰写的定义——刷新写到它即为写入面违规,而非"顺带更新")、② `.specify/teams/**`、③ 被监控目标、④ `summarize-project` 技能自身文件、⑤ `.specify/agents/**`、⑥ `.specify/project/**`(`manage-project` 时代的既有产物,其下已不再有任何 goal 内容) |
| **团队正常 cycle 写入**(ACT / CRITIQUE / REPORT 等) | `STATE.md`、`items.jsonl`、`run-log.jsonl`、`runs/<ts>-report.md`、结果清单 | 不受上表限制。团队主管在这些相里按 FR-026 发放条目 ID、追加台账事件、写运行报告(含总结状态行) |

- **只有团队主管写 tracked 工件**:`team.md` / `STATE.md` / `run-log.jsonl` / `items.jsonl` / `runs/` 与 tracked 的总结产物一律只由团队主管(orchestrator)写入。**子代理 MUST NOT 写入任何 tracked 工件**——子代理在隔离上下文中运行,并发写会竞争,半写会损坏持久记录;它们只往 git-ignored 的运行工作区写结果清单,由主管汇总(FR-021)。
- 运行报告的**总结状态行**由主管在写报告时落盘,属于"正常 cycle 写入",不违反总结步骤的不变性。

## 8. 人工批注由被调技能保留

上一版总结中的 `## 附注` 节由被调技能的既有刷新行为原样保留,团队侧 **MUST NOT** 重复实现(FR-018)。

## 10. goal 索引的机制细节(FR-030 … FR-036)

### 10.1 goal 身份解析

1. `team.md` frontmatter 声明了 `goal_slug` → 取其值,身份类型 `explicit`。
2. 未声明 → 取该团队自身的 `slug`,身份类型 `inferred`,并在派生数据的 `inferred_fields` 与报告元信息中标记为推断(FR-034)。

`goal_slug` MUST 同时满足 §6.2 的 DDL 字面量文法与路径片段安全(不含 `/`、不为 `.` / `..`)。

> 042 note: team.md 的可选字段 `focus_target`(默认聚焦 Target)**不参与**本节两级身份解析——它只是 run 级 `--target` 的预填,不构成第三级,也不影响 summary 归属与交付目录。

**不变式**:
- **GI-1**:取值 MUST NOT 由 goal 正文派生。改写 goal 正文不改变它,故不迁移交付目录(FR-019);正文变更本身记入元信息。
- **GI-2**:一个团队在任一时刻只属于一个 goal。改绑时原 goal 目录保留其历史贡献并标注其已不再参与,新 goal 目录自改绑时点起接收新贡献。
- **GI-3**:推断身份升为显式身份时归并到显式 goal 目录并保留历史,不留两份并列总结。
- **GI-4**:两团队声明同一 `goal_slug` 但 goal 正文实质不同时,**以显式声明为准**(声明即同一 goal),正文差异记入元信息供人裁决——机制不自行判定"其实不是同一目标"。

### 10.2 聚合与归属

- 触发刷新的团队只是**触发者**;刷新范围恒为该 goal 下的**全部**团队。团队从不单独出总结。
- 某团队本次未参与刷新 MUST NOT 使其历史贡献消失——每次都从全部团队台账重新折叠(FR-032)。
- 归属由两处冗余承载且都不得丢:工作项 ID 的 `<team-slug>.` 前缀,以及 `source` 出处路径的 `.specify/teams/<team-slug>/` 前缀(FR-033)。
- 归属以 **team slug** 呈现,不以代理 id / 结果清单路径等内部标识符呈现(FR-022)。

### 10.3 与既有产物共存

`.specify/project/` 已存在 `manage-project` 时代的历史产物(`project.md` 与 wbs / gantt / milestones 图表)。`goal/` 子树平级新增,MUST NOT 覆盖或迁移既有内容(FR-036)。被调技能对 SpecKit 项目的默认交付目录 `.specify/project/summary/` 亦为平级,互不冲突。

### 10.4 并发刷新串行化(FR-035)

同一 goal 下多个团队邻近触发时:

- 刷新以交付目录级互斥锁(`data/.refresh.lock`)**串行化为一次成功刷新**;让位的那次以 `skipped(serialized)` 退出并由调用方在其运行报告中记录状态行,MUST NOT 静默 no-op。
- 写入是**原子**的(临时文件 + 同目录替换):刷新要么完整落盘,要么保留上一版总结。半写的交付目录是被禁止的状态(WS-13)。
- 让位的刷新 MUST NOT 改动既有产物。
- 陈旧锁(超过阈值)按被遗弃处理并回收,避免死掉的运行永久堵住该 goal。

## 9. 调用方式

被调技能默认有四道逐层交互确认门禁;团队触发是自动流程,故 MUST 以**非交互模式**调用,并在报告 `## 元信息` 标注该事实。装载用 `--load`(每次从台账重建)而非 `--update`:累积状态的权威在团队台账,不在派生数据库,故「删除交付目录后重跑得同一份总结」成立。
> Gate probe: gate-create-team-noninteractive-call — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).
