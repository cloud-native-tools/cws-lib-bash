# Continuous 运营循环 — Operating Discipline（操作规范）

**Owner**: the team domain (`create-team` / `/speckit.team`). 本文是 **`continuous`（长期运营型）** 协作模式的**单一真相源**。它是 [`conceptual-model.md`](conceptual-model.md) 四模式表里 `continuous` 一行的展开，也是 [`optimization-goals.md`](optimization-goals.md) 中「持续优化」的运营落地。`iteration`（收敛型）无需本文纪律。

## 0. iteration vs continuous —— 何时用本模式

| | **iteration**（收敛型） | **continuous**（运营型 — 本文） |
|---|---|---|
| 目标语义 | 一次性：把某物从 A 提升到 B，**达标即止** | 持续：**长期维持/不断改进**某质量或**按节奏处理源源不断的工作** |
| 生命周期 | bounded：跑到 `threshold`/`max_iterations` 即交付并结束 | unbounded：按 **cadence** 长期运行，每次运行是一个有界 cycle |
| 停止条件 | 达标 / 上限 / 连续回退 | **本运行**受预算/断路器/kill-switch 约束；**整体**由人决定何时退役 |
| 风险面 | 单次、可回滚 | 反复、可能无人值守 → 必须有护栏 |

**判定**：goal 含「持续 / 不断 / 长期维持 / 每天/每次 / keep running / keep improving」，或工作是**源源不断到达**的（CI 失败、新 PR、新 issue、依赖更新）→ `continuous`；否则 `iteration`。

> 核心信条（源自 Loop Engineering）：**不要跳过报告阶段。** 运营循环的价值不在于一开始就自动改东西，而在于先低风险地校准判断，再逐级授予自动权限。

## 概念消歧：continuous 运营循环 vs reconcile 调谐模式

本模式与 [`shared/patterns/reconcile-pattern.md`](../../../shared/patterns/reconcile-pattern.md) 的**调谐模式（reconcile）**极易混淆——二者都是「反复运行 + LLM 判断 + 写状态文件」的循环。根本区别在于**处理对象 + 终止语义**：

| 维度 | reconcile（调谐模式） | continuous 运营循环（本文） |
|------|----------------------|----------------------------|
| 处理对象 | 一个持久制品空间（目录树/配置/注册表/知识库），有可描述的理想形态 | 源源不断到达的工作流（CI 失败、新 PR、issue、依赖更新）或要长期维持的质量指标 |
| 范式 | 声明式：desired vs current → diff → 收敛到一致 | 命令式/运营式：按 cadence 长期处理，无终态「done」 |
| 单次调用的终止 | 收敛到一致即结束（R0–R6 在一次调用内闭环） | 一次 run 只跑一个有界 cycle（§10 步骤 1–8），整体生命周期无界 |
| 外层重复的驱动 | 用户/按需触发（想收敛时才调） | cadence/cron 调度，可能无人值守 |
| 护栏重心 | 容忍带（防抖动）+ 只归档不删除（防数据丢失）+ 分级确认 | 成熟度 L1→L2→L3 + 预算/断路器/kill-switch + 独立验证者 + 尝试上限 |
| 人的位置 | 每次调用人都在场，通过分级门禁确认破坏性动作 | L3 可无人值守，仅在越界点停下 → 所以才需要 kill-switch/预算 |
| 组织结构 | 一个 skill/agent 应用的设计模式（扇出可选） | 一个多角色团队（supervisor/worker/独立验证者） |
| 状态文件语义 | snapshot/plan/audit/residual —— 描述一次调用的收敛事务 | STATE.md 脊柱 + run-log + post-run critique —— 跨 run 记忆与晋级证据 |

**嵌套关系（不是竞品）**：reconcile 是「一次调用内把制品空间收敛到一致」的**收敛引擎**；运营循环是「决定何时、以多大自治度去动手」的**跨调用调度 + 治理外壳**。一个 continuous 团队的 cycle 里，TRIAGE→ACT 若处理的工作恰好是「保持某制品空间 X 收敛」，其内部完全可以调用一次 reconcile 循环——**运营循环可以包住调谐环，反之不行**。

**判定口诀**：有可描述的制品理想形态要反复收敛 → reconcile；有源源不断的工作、或要按节奏长期改进的指标 → continuous 运营循环。

**容易张冠李戴的近义概念**：
- 「容忍带」（reconcile，跳过表面差异）≠「quality threshold/打分」（运营循环，cycle 验收）
- 「audit log/residual report」（reconcile，每次调用）≠「STATE.md + post-run critique」（运营循环，跨 run 晋级证据）
- 「分级确认门禁」（人在场）≠「成熟度 + kill-switch」（可无人值守）
- 「只归档不删除」（reconcile）≠「路径黑名单/约束文件」（运营循环）

## 1. 成熟度级别 L1 → L2 → L3（不可跳级）

每个 continuous 团队都在某个**成熟度级别**运行，`config.maturity` 记录当前级别。**必须从 L1 起步**，达标后才逐级晋升。

| 级别 | 含义 | 允许的动作 | 必备护栏 |
|------|------|-----------|----------|
| **L1 — 报告态** | 只发现 + 分诊 + 打分 + 写状态，**不改任何交付物** | 读、评、写 `STATE.md` 与 run report | 状态脊柱 + 预算 |
| **L2 — 辅助态** | 对**小而明确**的项做最小改动，**独立验证者**把关，产出草稿供人审 | L1 + 最小改动（每项 ≤ `max_attempts`）+ 独立验证 | L1 + 约束文件 + 独立验证者 + worktree/工作区隔离 + 尝试上限 |
| **L3 — 无人值守** | 可无人运行，仅在越界处停下等人 | L2 + 在允许范围内自动落地 | L2 + 完整黑名单 + 明确的**人工交接点** + kill-switch + 已验证的指标 |

### 晋级门控（L1→L2 举例，L2→L3 同理从严）

`improve-team` 才能执行晋级/降级（改 `config.maturity`），且必须有证据：

1. 连续 **≥ 2 个 cadence 周期**在 L1 运行，High-Priority 误报率 **< 20%**（读 `STATE.md` 的 Post-Run Critique 累计）。
2. 独立验证者 + 工作区隔离已在**人工触发**的改动上验证可用。
3. 约束文件（路径黑名单、构建/测试命令、尝试上限）已写全。
4. 无未解决的越界/预算事件。

> 反面教材（`why-we-killed-ci-sweeper`）：直接上自动修复、验证者与实现者同会话、无分支白名单、无预算 → 48h 烧掉 8M tokens、11 个 PR 里 1 个破坏生产配置。**这四条恰好是 L1 门控 + 独立验证者 + 约束文件 + 预算断路器要防的。**

## 2. Cadence（运行节奏）

`config.cadence` 声明重复节奏，例如 `1d`（每日）、`2h`（活跃期加密）、`cron: 0 8 * * 1-5`（仅工作日晨间）。高频节奏（如 `5-15m` 的 PR/CI 类）**必须**在「无可执行工作」时秒级早退（见 §4）。运营型团队的一次 `run` 只跑**一个 cycle**；重复由外部调度（人工 `/speckit.team run`、cron、CI）驱动。

## 3. 约束文件（每个 cycle 开头读取，绑定）

continuous 团队在 `.specify/teams/<slug>/constraints.md` 维护一份**绑定约束**，Team Supervisor 在**每个 cycle 最开始**读取并执行。缺失时套用下方默认最小集。约束至少覆盖：

- **路径黑名单**：绝不改 `.env`/`.env.*`、`auth/`、`payments/`、`secrets/`、`credentials/`、以及项目声明的核心/基础设施文件。
- **推送 / 合并门控**：绝不未经人工批准自动合并到主干；先开草稿 PR。
- **尝试上限**：每个待办项 **最多 3 次**修复尝试，超过即升级给人（机械执行：把每次尝试记入工作区账本，重试前校验计数）。
- **改动纪律**：一次 cycle **只修一个问题**；绝不顺手重构无关代码；绝不为了让门禁变绿而禁用测试。
- **沟通**：动手前先在报告/状态里说明将做什么；不擅自关闭 issue/PR。

## 4. 预算守卫 + 断路器 + Kill-switch

`config.budget` 声明每日/每 cycle 上限。Team Supervisor 在 cycle **开始与结束**各检查一次：

```yaml
budget:
  max_cycles_per_day: <n>
  max_tokens_per_day: <n>
  max_subagents_per_cycle: <n>
  on_80pct: report-only     # ≥80% 日预算 → 本 cycle 降为仅报告，不派 worker、不改动
  on_100pct: halt           # ≥100% 或 kill-switch → 立即退出，一行说明写入 STATE.md
kill_switch: <flag/label>   # 例如 loop-pause-all
```

规则：
- **无可执行工作** → 以极小开销早退（不派子代理），并在 run-log 记 `no-op`。
- 花费 **≥ 75%** 日预算 → 进入**精简档**（report-only 的前置降档）：跳过高成本核验项（如全量测试实测、逐文件 diff 复扫），只保留轻量观察（状态文件、日志尾部、计数对账）；每个被跳过的检项必须在 run report 中显式标注 `skipped(budget)` 并把对应结论记为 Unobserved，不得静默省略。
- 花费 **≥ 80%** 日预算 → 切 **report-only**（等价临时降到 L1）。
- 花费 **≥ 100%** 或 kill-switch 生效 → **立即退出**，在 `STATE.md` 留一行说明。
- **用户显式解除断路器**：用户可在确认门显式 override 预算断路器（人工授权优先于 loop 自律护栏），但必须双留痕（run report + STATE.md：授权人、时点、实际消耗），且授权仅对**当前 cycle** 有效——下一 cycle 断路器自动恢复。
- 绝不超过 `max_subagents_per_cycle`。

## 5. 状态脊柱（跨运行记忆）

continuous 团队在 `.specify/teams/<slug>/STATE.md` 维护**跨 cycle 的持久记忆**（区别于每次一份的 `runs/<ts>-report.md`）。每个 cycle 必须更新它，并**剪枝**已解决项：

```markdown
# Team State — <slug>
Last cycle: <ISO-8601>   Maturity: L1|L2|L3   Cadence: <...>

## High Priority (团队正在处理或等待人工)
- [ ] <一行描述> — 动作/状态；尝试计数 n/max

## Watch List (监控，暂不动作)
- <一行描述>

## Recent Noise (本 cycle 看过但判定不值得动作)
- <一行描述>

## Post-Run Critique (每 cycle 追加，用于晋级判据)
- <cycle 时间>: 误报=<n>；噪声项；下一轮的一个改进
```

**增量锚点**：当监控对象是一个（可能属于另一 session 的）工作树时，每 cycle 在 STATE.md 固化一行观测锚点——`Anchor: HEAD=<sha> statusHash=<sha256(git status --porcelain)>`。下一 cycle 先比对锚点：未变化即可跳过全量重扫（记 no-op 或轻量确认）；变化则以 `git diff <旧HEAD>` 做增量审读,而非全量基线盘点。

## 6. 独立验证者（Maker/Checker，L2+ 强制）

这是把 `iteration` 的 evaluator 按 Loop Engineering 强化后的形态。L2 及以上，任何交付物改动都要经过**独立验证者**：

- **独立**：验证者是**独立子代理**，**绝不**与实现者（executor）同一会话/同一角色实例。
- **默认 REJECT**：立场是「除非证据充分，否则拒绝」。
- **实跑校验**：亲自运行测试/门禁，**不信任**实现者「测试通过」的声称；给出命令 + 结果片段。
- **裁决三态**：`APPROVE | REJECT | ESCALATE_HUMAN`（无法运行测试/中高风险 → 升级给人）。
- **范围核查**：只改相关文件、无黑名单路径、无无关改动、无「作弊」（禁用测试/注释断言）。

映射：`executor`(Worker) 提改动 → `evaluator`(Meta，独立验证者) 裁决 → `optimizer`(Meta) 仅在继续时给改进方向。实现者**不得**自评为完成。

## 7. Post-Run Critique + Run-Log

- **每 cycle 结束**：在 `STATE.md` 的 Post-Run Critique 追加一条（误报、重复项、被降级/丢弃项、下一轮的一个改进）——这是晋级门控的证据来源。
- **Run-Log**：向 `.specify/teams/<slug>/run-log.jsonl` 追加一行结构化记录，便于观测与预算核算：

```json
{"cycle":"<ISO8601>","maturity":"L1","items_found":<n>,"resolved":<n>,"false_positives":<n>,"actions_taken":<n>,"escalations":<n>,"tokens_estimate":<n>,"outcome":"no-op|report-only|fix-proposed|escalated|halted"}
```

`resolved`（本 cycle 关闭的既有项）与 `false_positives`（本 cycle 判定为误报的项）是 L1→L2 晋级门控的核心判据——逐 cycle 机读记录后，误报率可直接从 run-log 聚合，无需回读 Critique 散文。

- **完整 run report** 仍按 create-team 的 Report 契约写入 `runs/<UTC-timestamp>-report.md`（每 cycle 一份）。

## 8. 团队目录布局（continuous 扩展）

`iteration`/`parallel`/`serial` 团队目录只含 `team.md` + `runs/`。**`continuous` 团队额外持有以下 tracked 运营脊柱文件**（durable，非运行中间产物）：

```
.specify/teams/<slug>/
├── team.md            # 定义（含 continuous config）
├── constraints.md     # §3 绑定约束（每 cycle 读取）
├── STATE.md           # §5 跨运行状态脊柱
├── run-log.jsonl      # §7 结构化运行日志（append-only）
└── runs/              # 每 cycle 一份完整 report
```

运行中间产物一律仍进 git-ignored 的 `.specify/teams/.work/<slug>/`。

## 9. continuous 的 config 骨架（写入 team.md frontmatter）

```yaml
pattern: continuous
config:
  maturity: L1                     # 必须从 L1 起步（§1）
  cadence: 1d                      # §2
  verifier: independent            # §6，L2+ 强制
  max_attempts_per_item: 3         # §3
  quality_dimensions: [...]        # Σ 权重 = 1.0
  threshold: 0.8                   # 每 cycle 交付/接受阈值（L2+）
  budget: { max_cycles_per_day: 1, max_tokens_per_day: 100000, max_subagents_per_cycle: 0, on_80pct: report-only, on_100pct: halt }
  kill_switch: loop-pause-all
  constraints_file: .specify/teams/<slug>/constraints.md
  state_spine: .specify/teams/<slug>/STATE.md
  run_log: .specify/teams/<slug>/run-log.jsonl
```

> L1 起步时 `max_subagents_per_cycle: 0`（仅报告，不派 worker）；晋到 L2 时由 `improve-team` 上调并补齐 `constraints.md` 与独立验证者。

## 10. 每个 cycle 的执行流程（run 时 Supervisor 遵循）

```
1. READ    读取 constraints.md + budget + kill-switch；若 kill-switch/100% → 立即退出
2. BUDGET  核算今日已花；≥80% → 本 cycle 转 report-only
3. TRIAGE  发现 & 分诊源工作（CI/PR/issue/质量差距）；无可执行项 → 早退(no-op)
4. ACT     L1: 仅写 STATE；L2+: 对小而明确项做最小改动（每项 ≤ max_attempts）
5. VERIFY  L2+: 独立验证者裁决（默认 REJECT，实跑测试）
6. SCORE   按 quality_dimensions 打分（对着 goal 度量）
7. CRITIQUE STATE.md 追加 Post-Run Critique；run-log.jsonl 追加一行
8. REPORT  写 runs/<UTC-timestamp>-report.md；更新 STATE.md 的 Last cycle + 剪枝
```

## 11. 失败模式（一等公民）

| 失败 | 缓解 |
|------|------|
| 直接上 L2/L3 自动修复 | 强制 L1 起步 + 晋级门控（§1）|
| 验证者与实现者同会话 → 放水 | 独立子代理 + 默认 REJECT + 实跑（§6）|
| 无预算 → 失控烧 token | budget + 断路器 + kill-switch（§4）|
| 分诊制造噪声 | STATE 加 Noise 段；收紧规则；用误报率做晋级判据 |
| 状态文件无限膨胀 | 每 cycle 剪枝已解决/关闭项（§5）|
| 无关重构 / 为过门禁禁用测试 | 约束文件「一次一改、绝不禁测」（§3）|
| 反复处理同一 flaky 项 | `max_attempts_per_item` + 超限升级给人（§3）|
