# Stage Prompts — 阶段提示词骨架、校验与运行程序（sdd-loop-driver）

> 本文件是每阶段派发提示词与阶段判定程序的自包含手册。全部文本可直接进入派发提示词；对框架文档的引用仅为溯源注解（运行时不解析）。占位符全部入口参数化——机制零硬编码。

## Stage Prompt Skeleton（三段骨架，每阶段一次）

每阶段把以下三段完整指令写入提示词文件（`prompt-<line>-<stage>.md`），阶段名替换 `<STAGE>`。

**红线（反嵌套拓扑）**：提示词是子代理的**全部输入**，三段骨架之外不得夹带驱动机制本身——反嵌套义务真源已上收 run-agent 派发治理（不引用驱动/循环技能、不指示加载技能、不含循环逻辑；派发前拦截），本行保留提醒并引用、不复述义务全文（analyze C-28）。

### 第①段：背景与权威文档

```text
你在推进 <project> 的无人值守 SDD 特性开发，当前阶段：<STAGE>。
- 项目终态权威文档：<target-state-doc>（所有取舍以它为准）
- 项目宪法：<project>/.specify/memory/constitution.md（合规底线）
- 上一阶段完成提交：<prev-stage-commit-hash>（续作基线）
- 当前断点判定：<breakpoint-verdict>（从状态脊恢复时必填）
- 状态脊：STATE_SPINE_PATH=<state_spine_path>（U0 入口声明；缺失即快速失败）
- 证据目录：EVIDENCE_DIR=<spec-dir>/test-evidence
- 状态脊写入模式：SPINE_WRITE_MODE=direct|transport
```

### 第②段：执行要求（默认纪律，每次派发原样携带）

```text
- 直接执行不要确认；访谈式问题自行裁决并记录假设（假设记录位置：spec 文件的 Assumptions 节或提交说明）。
- 只提交本特性产物。
- 仓库既有脏文件不提交不还原。
- 不要 push（除非明确授权）——远程推送属破坏性操作。
- 只推进当前阶段；下一阶段由主代理派发，不要自行越阶段。
```

> 上列前四条为 G5 默认纪律的**逐字纪律行**（对齐框架 fast-fail 与 confirmation-gates 两份判据文件的英文真源；执行侧以本文件的行文为准，不解析框架文档）。

### 第③段：完成尾标与回传契约

```text
- 完成时，你输出的最后一行必须是且仅是完成哨兵：大写阶段名 + -DONE（例如 PLAN-DONE）。
- 若本阶段无法完成（阻塞、发现规格矛盾、环境缺失），最后一行输出显式异常行：`ANOMALY: <一句话事实>`。
- 最后一行既不是完成哨兵也不是显式异常行 = 卡死信号，主代理将按卡死程序处置。
- 对齐说明：本回传契约与快速失败纪律（fast-fail）的子代理派发注入义务一致——异常必须显式回传，静默是不被接受的输出。
```

## U3 统一监听与驱动者生命周期（Watch Protocol）

监听规则本体见 `watch-model.md`；本段只规定驱动者的行为。

- **合法等待**：在有界长轮询窗口内等待（一次工具调用跑 `watch-target.sh --window N`），终止判定或窗口到期即返回；`RUNNING` → 立即重入下一窗口，**不在 agent 侧 sleep、不按固定 cadence 空转**。
- **非法等待**：独立 `sleep N` 回合；挂起监视器后结束驱动者会话「等待通知/恢复」——在会话式宿主（subagent 结束即停摆）中这意味着循环静默死亡，直接违反 Hard Requirement 1 与 5。唯一例外：宿主已被探针证明通知会自动恢复**同一运行**（`watch-model.md` §6）；此时原生通知只能作唤醒补充，每次唤醒仍做一次快照判定。
- **终止判定去向**：`DONE` / `INCOMPLETE` → U4；`ANOMALY` / `FAILED` / `DEAD` / `TIMEOUT` / `NO_SIGNAL` → U5；`RUNNING` → 重入。
- **窗口到期 ≠ 阶段超时**：只有状态脊中的 `stage_deadline_epoch` 触发 `TIMEOUT`；单窗口到期只产生 `RUNNING`。watcher 不杀进程，处置属 U5。
- **TIMEOUT 不等于可杀**：收到 `TIMEOUT` 后先跑一次 `--once` 最终快照；若 status/sentinel 已出现，按 U4/U5 重新路由；若 `pid=alive` + `heartbeat=fresh` 仍无终态，优先延长/继续观察，不得仅凭 TIMEOUT 停线或杀进程。停线/TERM 必须经用户显式决定，停止前再快照并保留 worktree/status/log。watcher 的 `--deadline-grace` 缺省 120s；宿主工具超时设为 `window + deadline-grace + 30s`。
- **完成需正证据**：进程消失、日志静默、`pgrep` 零匹配都**不是**完成；哨兵/退出记录是必要正证据，U4 仍须独立校验。
- 驱动者必须存活到全线收束（U6）或显式停线（U5）。
- 驱动者确须提前结束（预算耗尽、会话上限）时，唯一合法路径：状态脊写为 `stalled` / `reentry-required`（当前阶段、已试次数、证据指针齐备）+ 向用户显式上报——**静默等待与静默退出都是不被接受的输出**。
- **重入是常态路径**：任何新会话从状态脊读取断点判定与已试次数，先跑一次 `watch-target.sh --once` 快照核对（远端阶段可能已自行完成——终止判定在即按 U4/U5 续环），再决定派发、校验或恢复窗口。
- **Hook 事件是补充，不是判定**：Qoder CLI 的 `Stop` hook 写 done JSON/FIFO 只缩短等待（`--hook-done`/`--hook-fifo`）；DONE 仍要求退出记录 + 哨兵，U4 仍校验产物与纪律。API 崩溃时 Stop 不触发，status/exit 记录必须独立兜底；模型与 SSH 形态见 `watch-model.md` §11–§12。

## Independent Verification（独立校验程序，U4）

阶段完成判定由**独立校验步骤**执行——校验者不是该阶段的执行子代理（由主代理自身核验，或另行派发一个校验子代理）。三条件同时成立才判完成：

1. **哨兵（必要条件）**：本次阶段输出的最后一行是 `<STAGE>-DONE`。日志正文中出现的历史回显不算——只认本次输出末尾。
2. **产物核验（充分条件之一）**：`git log` 出现该阶段的新增提交；该阶段的 spec 产物文件存在（requirements 阶段 → requirements.md；plan 阶段 → plan.md；tasks 阶段 → tasks.md；checklist 阶段 → checklists/ 目录新增清单文件；analyze 阶段 → findings 报告正文输出于本次阶段日志——只读命令不产新提交，哨兵 + 报告正文即产物，git log 新增提交对该阶段不作要求；implement 阶段 → 代码提交与测试；review 阶段 → review 产物）。
3. **纪律合规抽查（充分条件之二）**：第②段的执行要求未被违反——脏文件未被提交/还原、无未授权 push、假设已记录。

**伪完成判未完成**：尾标在而产物缺 = 未完成，循环不派发下一阶段。**U3 返回 `DONE` 只是候选**，三条件同时成立才放行；`INCOMPLETE`（退出 rc=0 但哨兵缺失）按伪完成判未完成。校验结论含逐项证据指针，可被第二位复核者独立复现。

## Deterministic Gates（确定性门，U4 / 派发前）

> Owner of the gate rules is `references/efficiency-model.md` §5–§7. These
> commands run inside U4; a failing gate blocks the next dispatch and its
> result is recorded in the state spine.

| 时点 | 命令 | 失败处置 |
|------|------|----------|
| clarify U4（plan 派发前） | `python3 <skill-dir>/scripts/overlap-check.py --spec-dir <spec-dir> --repo <repo>` | `overlap` → 先做归属裁决并写入两条线状态脊，重跑至 `clear`；不得派发 plan |
| requirements U4（plan 派发前） | `python3 <skill-dir>/scripts/decomposition-check.py --mode plan --requirements <spec-dir>/requirements.md` | `split-required` → 写拆分记录（§5.3），按切片重新走 requirements；不得派发 plan |
| requirements U4 | `python3 <skill-dir>/scripts/pre-analyze-check.py --spec-dir <spec-dir> --stage requirements --repo <repo>` | `fail` → 修复制品后重跑；连续两轮失败按 stall 处置 |
| plan U4（tasks 派发前） | `python3 <skill-dir>/scripts/pre-analyze-check.py --spec-dir <spec-dir> --stage plan --repo <repo>` | 同上 |
| tasks U4（analyze 派发前） | `python3 <skill-dir>/scripts/decomposition-check.py --mode tasks --requirements <spec-dir>/requirements.md --tasks <spec-dir>/tasks.md`，随后 `python3 <skill-dir>/scripts/pre-analyze-check.py --spec-dir <spec-dir> --stage tasks --repo <repo>` | `split-required` 或 `fail` → 不得派发 analyze |

- 预检失败是**阶段门失败**，不是 analyze 的替代：修复后仍必须派发 analyze 并满足其 CRITICAL/HIGH 判据。
- `--strict` 把 `missing-path` advisory 升级为阻挡；`--waive CHECK:path:line` 只做逐行豁免，理由写入状态脊。
- 上表的命令、退出码与摘要写入该阶段 E3 `stage-status` 的 `sufficiency`/`evidence_ptr`，并在状态脊记录 `gates` 摘要。

## Fast Lane Conditional Blocks（快车道条件块）

> Owner of the fast-lane rules is `references/efficiency-model.md` §1. These
> blocks are copied verbatim into the dispatched prompt only when the line's E1
> admission record says `decision=fast-lane`. A full-chain run receives none of
> them; a missing checklist artifact is then a missing required gate.

### implement block（快车道录取时）

```text
FAST LANE: this line was admitted before checklist (E1 record in the state
spine; entry literal fast-lane=opt-in). The checklist stage is intentionally
skipped: checklist=skipped(fast-lane). Do not treat the absent checklist
artifact as a missing required gate. analyze and review remain mandatory and
unchanged. Any reversion trigger (new engine/skill/dependency/security surface,
task-count drift) must be reported with the explicit anomaly line; the driver
then reverts to the full chain, re-dispatches checklist, and re-runs analyze if
it had already passed.
```

### review block（快车道录取时）

```text
FAST LANE: checklist=skipped(fast-lane) (E1 admission record in the state
spine). Review behavior, evidence obligations and finding severities are
unchanged. Do not waive a missing required validation because checklist was
skipped; only the checklist quality-list step is absent.
```

### 发布纪律

- 驱动在派发 `implement` / `review` 提示词时，从状态脊读取 E1 记录并附上对应块与准入证据指针；无 E1 记录或 `decision=full-chain` 时 MUST NOT 附块。
- 收尾汇总必须携带 `checklist=skipped(fast-lane)` 或等价可见标记；回退过的线同时携带 `reversion` 触发与证据。

## Test Budget Blocks（测试预算块，全部阶段）

> Owner of the two-slot rules is `references/efficiency-model.md` §2. These
> blocks are copied into the dispatched prompt according to the stage; the
> session state is always `STATE_SPINE_PATH` (never a second ledger file).

### implement block（implement 起点）

```text
TEST BUDGET: before the first task, run exactly one full suite:
  bash .specify/scripts/bash/run-tests.sh --names-out <spec-dir>/baseline-failed.txt
Write the E2 baseline row into the state-spine fence at STATE_SPINE_PATH
(seq=1, slot=baseline, stage=implement, selection_basis=full-suite, command,
rc, passed/failed, failed_names_path, evidence_ptr; merge_source/merged_at=na
when written directly). 禁止第二次全量（Do not run a second full suite in
implement); any additional full run is forbidden unless it is recorded as
out-of-slot-exception with a reason and evidence. Intermediate verification uses the targeted set
targeted-set-v1 (efficiency-model §2.3) and leaves an E3 stage-status row in
EVIDENCE_DIR.
```

### 中间阶段与 review block（clarify / plan / tasks / checklist / analyze / review）

```text
TEST BUDGET: run only the targeted set selected by targeted-set-v1 with
stage_base=<stage-base>; record command, selection_basis, selected_paths[],
sufficiency, rc, passed/failed, new_failures[] and baseline in an E3
stage-status row (EVIDENCE_DIR). Docs-only stages record status=not-run-docs-only
with the six reduced fields. An empty set with executable changes is recorded
as empty-selection-escalated (expand or escalate explicitly). A checklist stage
skipped by the fast lane records not-applicable-skipped-stage and is excluded
from the completeness denominator.
```

### closure block（驱动侧，review 后、合并前）

```text
TEST BUDGET CLOSURE: after review passes and before merge, run the closure full
suite:
  bash .specify/scripts/bash/run-tests.sh --names-out <spec-dir>/final-failed.txt
Compare by name: comm -13 baseline-failed.txt final-failed.txt. Append the E2
closure row to the SAME state spine (baseline_compare must be the name-level
diff; never a count comparison), then audit:
  python3 <skill-dir>/scripts/audit-test-budget.py --spine "$STATE_SPINE" \
    --spec-dir <spec-dir> --stage-check closure
The summary must report baseline:1 closure:1 plus stages=N complete=N; any new
failure is fixed or explicitly attributed. A fix rerun of the same suite is an
in-slot-rerun (trigger + evidence), not a third slot.
```

### closure-repair 重入 block

```text
TEST BUDGET: this re-entry repairs closure findings and carries
baseline_slot=skip(closure-repair). Do not consume the baseline slot again and
do not run any other full suite; use targeted-set-v1 for intermediate tests.
```

## Plan Constraint Block（plan 完成后的只小修块）

> Owner of the plan constraint rules is `references/efficiency-model.md` §3.
> The block is copied into the `tasks` / `analyze` / `implement` / `review`
> prompts whenever the state spine says `plan_constraint=active`. On re-entry
> the driver restores `active` and `activated_at` from the spine before
> dispatching; a missing value is a fast-fail at dispatch, never a silent
> "constraint absent".

```text
PLAN CONSTRAINT: plan_constraint=active since <activated_at>
(plan_commit=<plan_commit>; approved_baseline_commit=<latest anchor>). Any
change to a plan-owned artifact (plan.md, data-model.md, contracts/,
quickstart.md, research.md, feature-ref.md) must be a minor fix only —
typo/wording, broken link/reference repair, formatting, line-level consistency.
Declare every touch before the done sentinel in the return:
  PLAN-EDIT: <path> — <reason>；分类=minor|substantive
For a substantive change (scope, architecture, data-model/contract semantics,
FR/SC content, task breakdown, new capability/security surface), stop and
return exactly one explicit anomaly line:
  ANOMALY: <one-line fact>
together with the proposed change and its substantive reason. Never rewrite the
plan silently and never re-run the plan stage yourself.
```

## Progress & Detach Blocks（进度与脱离）

> Owner of the stream/detach rules is `references/efficiency-model.md` §4.

### 派发块（每个阶段）

```text
PROGRESS & DETACH: this stage runs under stage-runner.sh with
--output-format stream-json by default. The raw stream (raw-<line>-<stage>.jsonl)
and the derived live log (log-<line>-<stage>.log) are evidence; only a terminal
result may leave the sentinel as the last non-empty line. The dispatch record
carries detached=yes|no; detached=no is recorded as an unprotected run with a
risk reason. Progress growth and raw bytes never decide completion.
```

### 重入块（新会话接管时）

```text
REENTRY: before dispatching or resuming, run watch-target.sh --once against the
recorded pid/status/log/heartbeat. A completed stage is verified, never
redispatched. Wait only inside the long-poll window; do not add an independent
sleep turn and do not start any resident service.
```

## Stall Handling & State Spine（卡死处置与状态脊，U5）

### 缺省值（入口参数可覆盖）

- 阶段超时缺省 **90 分钟**（单阶段数十分钟量级的实测基础；入口可覆盖）。
- 同阶段重试上限缺省 **2 次**（两振停滞先例；入口可覆盖）。
- 预算（budget）与节奏（cadence）：预算降级沿用 on_80pct report-only / on_100pct halt 形态；cadence 仅指**回退形态（间隔轮询）**的检查频率，缺省长轮询窗口不使用固定 cadence（见 `watch-model.md` §4–§5）。

### 处置程序

1. 终止判定 → 处置：
   - `ANOMALY` / `FAILED` / `DEAD` / `NO_SIGNAL` → 重试（重试前修复可归因原因：环境、提示词、断点判定、启动路径），计一次已试次数；
   - `INCOMPLETE` → 按**伪完成**重试（核对哨兵/产物/日志），计一次已试次数；
   - `TIMEOUT` → 先 `--once` 最终快照；若 status/sentinel 已出现则按 U4/U5 重新路由；活进程优先延长/继续观察；只有最终无终态且用户显式决定时才按重试/停线处置；
   - `RUNNING`（窗口到期）→ 不是失败，不计重试，立即重入下一监听窗口。
2. 达重试上限或预算触顶 → **停环**：该线停止推进。
3. 状态脊落盘：当前阶段、已试次数、断点判定、**watcher 最近判定快照（verdict / pid / heartbeat / rc / reason）**、证据指针（日志路径/提交号/status 路径）、卡死状态 = stalled。
4. 出上送件，四要素齐备：
   - **发现了什么**：异常事实一句话（哪条线、哪个阶段、什么信号——含 watcher verdict 与 reason）；
   - **为何吃重**：根因归类（环境/规格矛盾/子代理能力/预算）；
   - **已产生的中间产物逐项可定位**：已完成的阶段与提交号清单、状态脊路径、日志/status/pid 路径；
   - **可选处置**：给用户的 2–3 个下一步选项（如：修环境后重入 / 调整断点 / 放弃该线）。
5. **绝不静默等待，绝不静默修平异常后继续**——异常要么被处置并留痕，要么停下上报；静默是不被接受的输出。

### 状态脊（Line State，先写状态后派发）

每线一份状态文件（随线命名，落主代理侧工作目录），字段：U0 入口声明（目标/拓扑/权威/切片/断点解析）/ line label / 当前阶段 / 已试次数 / 断点判定 / 最近证据指针 / 卡死状态（running / retrying / stalled / done），以及监听字段：`stage_started_at` / `stage_deadline_epoch` / pid·status·log·heartbeat 路径 / `last_verdict` / `verdict_at` / 最近信号快照（pid / heartbeat / rc / reason）。

- **程序**：U0 入口声明时、U2 派发前、U3 收到终止判定时、U4 校验后、U5 停线时**先写状态、后做动作**——续环与重入只读状态脊，零上下文可接手；循环 MUST NOT 依赖会话记忆。
- **重入**：任何新会话接手该线时，从状态脊读取断点判定与已试次数，先跑一次 `watch-target.sh --once` 快照；终止判定在即按 U4/U5 续环，否则从对应阶段续跑或恢复监听窗口。

## Line Registration, Envelope & Message Ingress（线路登记、归属与消息入口，064）

### U0.5 线路登记（首次派发前）

状态脊头字段先写 `line_id` / `run_id`，再向环境级 Registry 注册：

```bash
python3 <skill-dir>/scripts/line-registry.py --action register --line-id <line> --run-id <run> \
  --project-dir <project> --repo-root <repo> --state active [--write-line ...] --format json
```

- 注册失败 = 该线启动失败：显式上送（路径 + 原因），不得静默继续或改用项目内路径。
- 单线运行同样注册并携带信封；不得因归属机制改变 U0–U6、阶段链、哨兵校验与卡死处置。
- 收尾（U6）后 `--action deregister --line-id <line> --reason <reason>`；`state=closed`、`closed_at` 必填。

### 归属信封（每个事件）

- status / pid / heartbeat 行尾携带 `line=<id> run=<id> stage=<stage> event=<type>`；
- 日志旁路 `log-<line>-<stage>.log.meta.jsonl`（append-only，单写者）承载 `log-start` / `log-terminal`，终止条含 `sentinel_seen` 与 `exit`；
- 提示词旁路 `prompt-<line>-<stage>.md.meta.json` 在派发前写入；
- **日志正文零改动**：哨兵字面量与「最后非空行」判定不变；不得在哨兵后追加信封。

### 消息入口程序（驱动侧）

每次收到用户消息，先调用确定性入口，再决定路由：

```bash
python3 <skill-dir>/scripts/line-registry.py --action resolve-message --message "<message>" [--clarified]
```

判定与动作（封闭集：`route | clarify | ambiguous-stop | no-active | no-match`）：

| 结果 | 驱动动作 |
|------|----------|
| `route` | 将消息交给 `target_line_id`；不改动其他线路 |
| `clarify` | 原样向用户提出 `question`（恰好一个），附候选清单；等待期间其他线路继续推进 |
| `ambiguous-stop` | 列出候选并停止路由；**不得再问第二个问题**，不得猜 |
| `no-active` | 明确报告无活动线路并请求目标 |
| `no-match` | 报告标识与候选不匹配；不回落到猜测 |

- 可识别标识：显式 `line_id` token，或唯一匹配的 project/repo 路径或分支名。
- **禁止**使用 `ps`/`pgrep`/进程名/cwd/环境态推断；入口澄清只阻塞该条消息，不暂停/改变其他 line 的子代理与监听。

### 事件归属消费规则

- `own`：`(line_id, run_id)` 与当前监听目标一致——唯一可参与判定、进度与 Registry 状态的事件类别。
- `foreign`：`line_id` 不同——不得转发、不得计入、不得改变当前线路状态。
- `stale-run`：同线旧 `run_id`——不得作为当前尝试的证据。
- `unattributed`：信封缺失或不可解析——显式报告归属缺口，不得当作完成/失败证据。
- `legacy`：watcher 未提供归属参数时的 058 兼容行为（无过滤）；新派发 MUST 提供归属参数。`legacy` 仅允许用于单活动线 / 058 兼容调用；多活动线 MUST NOT 以 legacy 调用绕过归属过滤（先由 `resolve-message` 定线，再带参数监听）。

## Concurrency Isolation（并发隔离，多线并行）

多线并行时每条线是独立循环实例：**一线一连接（检查时独立发起）、一线一状态脊**；任一线的失败不阻塞其他线。

### 并发隔离声明（每次派发提示词携带）

同一项目上有多条线或既有未提交内容时，第②段执行要求追加：

```text
- 并发隔离：以下路径/文件为本线隔离项——不读、不改、不提交：<isolated-paths>
- 审后提交边界：本线只做阶段产物提交，审后由主会话统一提交本线收尾件。
```

### 写线工作区声明（064）

写线派发前，提示词与状态脊 MUST 携带以下声明（缺一项不得派发）：

```text
- worktree：<worktree_path>（本线唯一写工作区）
- branch：line/<line_id>（base_sha：<base_sha>）
- owned_paths：<...>；read_only_paths：<...>；forbidden_paths：<...>
- resources：ports=<start-end>；cache_dir=<...>；tmp_dir=<...>
```

- 一个 worktree 同时只有一个写 line；阶段子代理**不得切换分支**、创建/删除 worktree，或改写其他 line 的 worktree。
- 不得写入另一活动 line 的 `read_only_paths` / `forbidden_paths`；不得写共享可写运行时路径（feedback / session / knowledge / exec-quant 各写本线 worktree）。
- 阶段提交只允许阶段产物路径；运行时记录不提交，由集成者一次归档。
- U6 时未合并/未提交的 worktree MUST 保留并上送（`worktree_retained=true`）；移除只由集成序列在合并成功后执行。
- 端口/缓存/临时目录按 Registry 分配使用；不得启动全局服务。

### 窄读法授权（Narrow-Read Authorization）

被隔离项确需追加操作时，**只有显式授权才能放行**：

```text
- 窄读法授权：本线本次允许对 <isolated-path> 执行 <bounded-operation>，范围仅限此操作，一次性有效。
```

- 授权是**显式、逐项、有界**的——不存在隐式放行；「顺便看一下」不是授权。
- 每次授权记录进该线状态脊（何时、何项、何界），供收尾汇总审计。

## CLI Capability Profiles（U2/U4/U5，064）

CLI 行为知识的唯一落点是 `references/cli/`（schema owner：`references/cli/index.md`）；本节只规定驱动侧的查阅/观测程序，不复述档案内容。

### U2 派发前（只读查阅）

- 只读查阅目标 CLI 档案，据此选择超时形态与 detach 形态；**不改档**。
- 派发记录写入状态脊：`profile_id`、`profile_version`、`observed_cli_version`。
- 输出模式的吞吐默认（stream-json）由 063 拥有；档案只记录缓冲/事件事实，**不改写**该默认。
- 匹配且无新事实 → **零反馈**。

### U4 独立校验（比对）

比对以下事实与档案：输出模式/事件形状、哨兵来源、status/exit 字段、runner rc 与 watcher 判定、日志/session 位置、**缓冲**/可见性。

### U5 停线处置（比对）

比对以下事实与档案：已知**缺陷**、**超时**上限、**detach**/退出/孤儿行为。

### 观测事件与写序

观测事件 = (a) 与 `known` 不符；(b) `unknown` 获得已验证值；(c) 新版本/平台行为首次出现。

处置顺序 MUST 为：

1. 状态脊追加 `cli_observations` 段（观测事实 / 对照的档案条目 / 影响）；
2. 更新档案 `## Provenance`；
3. 经既有 feedback 引擎记录 **恰好一条** `cli-profile:<cli>` 反馈。

- 一次观测事件恰好一条反馈；**每个事件各一条**（同一次派发内的多个独立事件不得合并或遗漏）；
- 无新事实 → **零反馈**；
- `feedback_id` 可在反馈落库后回填 provenance；
- 档案更新不回溯改变 U2 记录的形态；若冲突使当前阶段无法安全完成，走既有 U5 停线/重试程序，不得以改档代替行为修复。
- `known` 条目带观测日期、CLI 版本与证据指针；`unknown` 不填猜测值；版本/平台不一致视为新观测。

## Reattach & Lifecycle（重接线与生命周期，064）

### 重接线程序（主会话恢复后）

**唯一恢复源 = Registry + 状态脊 + 四件套证据**；不得依赖会话记忆、对话历史或宽泛进程扫描。

1. `lease-acquire`：取得该 line 的 driver lease；活持有者 exit 3 → 不夺取；过期 lease 先验证证据再 `lease-break`；`suspected-alive` 需显式 `--override`。
2. `verify-identity`：校验 runner/cli start token；cwd 在平台暴露时校验（Linux `/proc/<pid>/cwd`，macOS 记 `unsupported`）；branch 由 worktree `git rev-parse --abbrev-ref HEAD` 复核。
3. **先做一次 `watch-target.sh --once` 快照**，再决定去向：
   - `identity=ok` + `RUNNING` → 恢复监听，**零重复派发**；
   - `identity=ok` + `DONE` → 进既有 U4 独立校验 → U5/U6；
   - `identity=dead/mismatch` → 既有 U5 卡死/重试程序，保留 worktree 与证据；
   - `identity=remote-unreachable` → `stalled`（reason=`remote-unreachable`）+ 重试连通性，不判 dead、不重派。
4. 每 ≤ `ttl/3` 续租 lease；U2/U3/U4/U5 各续租一次。

### 重复启动与 orphan/stale

- 派发前 `reserve`（`(line_id, stage)` 原子 `O_CREAT|O_EXCL`）：已有活动 reservation 时，同 `run_id` 且 PID 身份有效 → attach；否则拒绝，绝不启动第二个同阶段进程。
- orphan：进程存活但无有效驱动/Registry/状态脊，或 Registry 缺失 → 显式标记并上送；只用线自有证据与已登记 PID，禁止宽泛进程扫描；处置留痕，不静默认领或终止。
- stale：PID 死亡/复用、cwd/branch 不符、证据超期 → 显式标记；清理是显式动作；远端 ssh 不可达记 `stalled`，不记 stale/dead。

### U6 收尾（生命周期）

- U6 在 `integration_result`（merged|failed）记录之后执行；只读线阶段完成直接 U6；写线集成前显式放弃以 `last_event=abandoned` 关闭。
- U6 注销 Registry（`closed` + `closed_at`）、释放 reservation 与 lease、按保留策略归档证据；不得留下 `active` 残留。
- worktree 的移除只由集成序列在合并成功后执行；未合并（failed/放弃）时保留并置 `worktree_retained=true`。

## Variants（已验证变体）

### 本地拓扑（本地简报先行）

项目在本机时：runner 直接以本地项目为工作目录（无 ssh/su 层）；**需求上下文先写成简报文件**（如 `/tmp/<topic>-sdd-brief.md`），子代理提示词只说「先完整阅读简报，再执行 /speckit.requirements」——文件承载的上下文比内联进提示词更稳（不失真、可复查、可复用）。

### 构建固化变体（按角色分线）

同一主机上按角色分两条线并行：一个系统用户（如 `su agent`）在宿主侧项目固化基础设施，另一个系统用户（如 `su develop`）在 `/cws_work` 项目固化 build 配置。两线仅经入口参数（执行身份、路径、目标差异）区分——机制零新增分支、零角色名硬编码。

## Boundary

- 本文件不改变各阶段命令自身的内部流程——它只规定**派发什么、怎么判定完成**。
- 撰写底稿注解：三段骨架与校验程序撰写时取材于 shared 层 `unattended-loop-pattern.md` 底稿；运行时零依赖。
