# State Awareness — 快照入口、中断形态与恢复动作（owner reference）

> **所有权边界（先读这一段）**
>
> - 本文件是 `FR-043` 要求的状态感知 **owner reference**：拥有快照入口与调用形态、六类检测表、probe 契约、watchbeat 读取契约、§Stage Artifact Map 与 §恢复动作建议。
> - **`loop_state` 派生映射（FR-004 的八条优先级）的唯一 owner 是 `.specify/specs/065a-state-awareness/requirements.md` FR-004（parent `#FR-004`）**。§Derived Mapping 只做镜像与指针，不拥有该表；本文件任何位置都不得声称拥有它。
> - watch 判定（状态机、信号优先级、退出码 10–16）的唯一 owner 是 `references/watch-model.md`；本文件只描述聚合器**消费**其输出的方式。
> - `提交齐备` 谓词与候选动作的先后次序，owner 是 `.specify/specs/065a-state-awareness/contracts/interruption-and-action.md` C-46（`IA-14`）；§恢复动作建议 只记录引擎落地读法。
> - 运行时机器权威是 `.specify/scripts/loop-state.py`（`STAGE_ARTIFACTS` / `DERIVED_MAPPING` / 动作阶梯），本文件是它的人类可读镜像；契约测试逐项钉住两侧一致（`C-50`、`FR-004` 三向比对）。
> - 运行时镜像 `.specify/skills/sdd-loop-driver/references/state-awareness.md` 由 `.specify/scripts/python/sync-mirrors.py` 生成，**MUST NOT 手改**。

---

## 入口与调用形态

入口：`.specify/scripts/loop-state.py`（Python ≥ 3.8，仅标准库，无常驻进程、无网络轮询）。一次调用输出一个 `schema_version=1` 的 JSON 信封；**只读**——唯一的写路径是显式 `--out`。

| 形态 | 命令 | 用途 |
|------|------|------|
| 快照 | `loop-state.py --action snapshot --line-id <line> [--stage <stage>] [--state-dir …] [--spec-dir …] [--repo …] [--spine …] [--watch-script …] [--out …]` | 读本地证据，聚合 `loop_state` / 中断形态 / 恢复动作 |
| 远端探针 | `loop-state.py --action snapshot --line-id <line> --probe <file>` | 只消费调用方采集的 probe JSON；不读本地证据、不调本地 watcher |
| 自测 | `loop-state.py --self-test` | 自建临时夹具跑内建用例；末行 `SELF-TEST: N passed, M failed` |
| 拒绝态 | `--action recover` / `--action check-spine` | 065a 只回结构化拒绝信封（exit 1，`owner` 分别为 065c / 065b） |

路径解析顺序（owner：`contracts/loop-state-cli.md` C-4 与 R-02）：显式参数 → Registry 条目 → 环境约定 → `null`。解析不出的路径保持 `null`，不猜、不回退到 cwd。

## 证据读取契约

聚合器消费五类证据源：状态脊、Line Registry、四件套（`pid-*` / `status-*` / `log-*.log` / `heartbeat-*.log`）、watchbeat 标记（`watchbeat-*`）与阶段产物 + git 提交。

**四件套信封**：空格分隔的 `key=value`（首见优先，镜像 `watch-target.sh` 的读法）。阈值 `start-grace` / `deadline-grace` / `heartbeat-max-age` 的缺省值 owner 是 `.specify/scripts/watch-target.sh --help` 的 `Defaults:` 行，本引擎不内置第二套数字；发现失败时 `thresholds.value_state=unknown`，依赖该阈值的判定不触发。`retry_limit` 缺省值 owner 是 `references/stage-prompts.md` § Stall Handling。

**证据源 vs 必需输入**：证据源不可读 → 记 `status=missing`、值用 `null`，仍以退出码 `0` 完成求值；必需输入（`--line-id`、显式 `--probe` 文件）缺失 / 不可解析 → 退出码 `2`，不进入求值。

**完成哨兵**：日志**最后非空行** `== <STAGE>-DONE` 才算完成证据。更早出现的哨兵字样（其后仍有非空行，例如 `ANOMALY: …`）不构成完成证据；`false_completion` 与 `artifacts-without-completion` 是同一条判据互斥的两侧。哨兵谓词的 owner 是 FR-004，本节只记录读法。

**stale 归属**：`run=` 与当前尝试不符、文件 mtime 早于 `stage_started_at`、或既无 `run=` 也无 `line=` 且无 meta 佐证的裸信封 → 列入 `stale_signals[]` 并从本次求值排除。被排除的信号不参与 `loop_state`、产物与动作求值；**065a 不因单纯 stale 改变候选动作**（物理隔离与 stale-unisolated 停线由 065c 承接）。

### watchbeat 读取契约

watchbeat 是**驱动侧写入、本引擎只读消费**的观察标记，字段为空格信封：

| 字段 | 语义 | 缺失时 |
|------|------|--------|
| `run=` | 写入时的尝试标识 | 不作为归属证据；仅当当前尝试已知时用于 `run-mismatch` |
| `stage=` | 阶段名 | 按 `null` 处理，不推断 |
| `window=` | 该标记自身的观察窗口（秒） | **不判“过期”分支**，只保留“标记缺失”分支 |
| `at=` | 写入时刻（epoch 秒） | 新鲜度记 `fresh=null` |
| `event=` | 事件名（如 `watch-window`） | 原样透传 |

新鲜度 = `now - at <= window + deadline-grace`；`deadline-grace` 不可得时不判过期。age 类派生数字**不输出**（信封只给原始 `at` / `mtime_ns`）。写入义务归 065b：本引擎 MUST NOT 创建、刷新或修复该标记。

## 八类中断形态

每条形态含 `form` / `detail` / `evidence[]` / `detector`；不同根因各自成条，同一根因的多个文件合并为一条并在 `evidence[]` 列全部指针。`heartbeat-stalled` 与 `lifecycle-spine-violation` 在本切片只保留词表与 `missing` / `unknown` 语义。

| 形态 | 归属 | 触发判据（读法） |
|------|------|------------------|
| `unwatched` | 065a 检测 | 阶段运行中且无终态证据时：watchbeat 标记缺失（缺失分支）或年龄 > `window=` + deadline-grace（过期分支）；已写出末行哨兵时不触发 |
| `dead-no-exit-record` | 065a 检测 | 无退出记录，`pid` 记录存在且进程已死 / start token 不符；绝不据此判 `DONE` |
| `deadline-overrun-live` | 065a 检测 | `stage_deadline_epoch` 可读、`now ≥ deadline + grace`、进程仍存活、且无退出记录与末行哨兵；处置指向继续观察 |
| `artifacts-without-completion` | 065a 检测 | 产物映射可建立、必需产物齐备、且无末行哨兵（无论退出记录/退出码） |
| `stale-signal` | 065a 检测 | 命中 run 不符 / mtime 早于 `stage_started_at` / 无信封 legacy 三类之一；被列入的信号从本次求值排除 |
| `remote-unreachable` | 065a 检测 | `--probe` 形状 (b) 证明远端不可达；证据指针指向 probe 文件 |
| `heartbeat-stalled` | 065b 保留 | 本切片只保留词表与 `missing` / `unknown` 语义，不检测 |
| `lifecycle-spine-violation` | 065b 保留 | 同上 |

未派发（`not-dispatched`）不是中断形态：它是 `loop_state=UNKNOWN` 的一个 reason，`interruptions[]` 保持为空，四件套 / watchbeat / artifacts / commits 全部记 `na`。

## Stage Artifact Map

本表镜像 `.specify/scripts/loop-state.py` 的 `STAGE_ARTIFACTS`，逐项一致由契约测试钉住。路径相对解析后的 `spec_dir`；`owned_paths[]` 是**条件产物**：存在才进入提交路径集合，缺失不判不完整。

| 阶段 | `artifacts[]` | `owned_paths[]` | `commit_required` | `no_change_allowed` |
|------|---------------|-----------------|-------------------|---------------------|
| `requirements` | `requirements.md` | — | true | false |
| `clarify` | `requirements.md` | — | true | true |
| `plan` | `plan.md`, `data-model.md`, `contracts/`, `quickstart.md`, `feature-ref.md` | `research.md` | true | false |
| `tasks` | `tasks.md` | — | true | false |
| `checklist` | `checklists/` | — | true | false |
| `analyze` | — | — | false | true |
| `implement` | — | — | true | false |
| `review` | `review.md` | — | true | false |

读表要点：

- **产物完整性**只由“文件存在且非空”判定；目录类产物要求目录存在且至少含一个非空文件；`checklist` 另要求自 `stage_base_commit` 起新增/改动的 checklist 文件。
- `stage_base_commit` 缺失或不可解析 → `artifacts.complete=null`、`value_state=unknown`，**不判不完整**、不计入 `false_completion`；`commits.value_state=unknown` 且不回退 HEAD 猜测。
- `analyze` 无必需文件产物 → `complete=true`（vacuous truth），`commit_required=false`，`commits.status=na`。
- `implement` 以**代码/测试路径**的提交证据表达完整性（`src/`、`skills/`、`.specify/scripts/`、`tests/`、`.specify/templates/`、`agents/`），仅文档提交不算；`artifacts.status=na`。
- `stage` 未知时映射不可建立：spec 路径可读 → `status=present`/`value_state=unknown`，否则 `status=missing`/`value_state=na`；不拿别的阶段顶替。

## Derived Mapping

**本节的映射表唯一 owner 是 `requirements.md` FR-004（parent `#FR-004`）。** 下表只镜像该条的八条优先级子句，逐项一致由契约测试比对；本文件不拥有、不改写、不解释该表。

| 子句 | `loop_state`（子句内判定次序） |
|------|--------------------------------|
| `1` | `STALLED`, `REENTRY_REQUIRED` |
| `2` | `ANOMALY`, `FAILED`, `DONE`, `INCOMPLETE` |
| `3` | `DONE`, `INCOMPLETE` |
| `4` | `DEAD` |
| `5` | `TIMEOUT` |
| `6` | `NO_SIGNAL` |
| `7` | `RUNNING` |
| `8` | `UNKNOWN` |

消费约束（来自 FR-004，不在此重述判据）：

- 存在活动 watch target 时 `loop_state` 与 watcher 判定**逐字一致**且 `verdict_source=watcher`；聚合器 MUST NOT 改写、降级或升级该判定。
- 无 watch target 时 `verdict_source=derived`，按上表子句次序取首个命中项；与状态脊 `last_verdict` 冲突只报嵌套 `spine.consistent=false`，不得静默择一。
- 子句 2–3 的“产物齐备”用文件侧完整性（目录/非空），子句 5 的 TIMEOUT 在活进程下仍判 `TIMEOUT`，处置按动作表落到 `watch`。

## Probe 契约

`--probe <file>` 是**必需输入**：文件不可读、JSON 不可解析、形状不符一律退出码 `2`。提供 `--probe` 时 MUST NOT 读取本地状态脊 / 四件套 / 产物 / git 证据，MUST NOT 调用本地 watcher；与 `--spine` / `--state-dir` / `--spec-dir` / `--repo` / `--watch-script` 同时出现一律退出码 `2`（互斥）。

| 形状 | 必需键 | 输出 |
|------|--------|------|
| (a) 快照信封 | `schema_version=1`、`watch_verdict`、`evidence` | 逐字消费 probe 的 `spine` / `registry` / `watch_verdict` / `evidence`；本地只重算 `interruptions` / `recovery_action` / `false_completion` / `missing_artifacts` / `spine.consistent`；`loop_state` 在 `watch_verdict.present=true` 时取 probe verdict，否则走 derived；`evidence_source=probe` |
| (b) 最小可达性 | `schema_version=1`、`reachable=false`、`reason` | `loop_state=STALLED`、`loop_state_reason=remote-unreachable`、`interruptions[]` 含 `remote-unreachable`、动作 `stop`；全部信号与 artifacts / commits 记 `missing`，`watch_verdict.detail=probe-unreachable` |

拒绝路径（均退出码 `2`）：不可解析、`schema_version≠1`、形状 (b) 的 `reachable=true`（无可求值证据）、probe 的 `line_id` 与 `--line-id` 不一致、缺 `schema_version`、两种形状都不匹配、以及与本地路径参数并用。未知字段一律忽略。

probe 模式下不执行本地 git 证据计算，因此 `uncommitted_artifacts=[]` 是“本次未计算”，不是“已全部提交”；`paths.state_dir` / `spec_dir` / `repo` / `spine` 全为 `null`，只有 `paths.probe` 指向输入文件。

## 恢复动作建议

`recovery_action` 是封闭集 `none / watch / verify / resume / retry / stop` 中的恰好一个，对相同输入可复现。**候选行号与先后次序的 owner 是 `contracts/interruption-and-action.md` C-46**；本表只记录引擎的落地读法（含 C-46 明文要求的“行 8–10 不重判 STALLED / REENTRY_REQUIRED”，以及 C-47 对 `resume` / `retry` / `stop` 三类候选的上限改写）。

| C-46 行 | 触发面 | 动作 | `reason` |
|---------|--------|------|----------|
| 1 | `not-dispatched` | `none` | `not-dispatched` |
| 2 | 远端不可达（probe 形状 b） | `stop` | `remote-unreachable` |
| 3 | `loop_state=UNKNOWN`（非未派发） | `stop` | `evidence-gap` |
| 4 | `unwatched` ∨ `deadline-overrun-live` ∨ `RUNNING` ∨ 活进程 `TIMEOUT` | `watch` | `deadline-overrun-live` / `unwatched` / `running` |
| 5 | `DONE` ∧ `commit_required=false`（含 `commits.status=na`） | `verify` | `done-complete` |
| 6 | `DONE` ∧ `commits.value_state=unknown` | `verify` | `commit-baseline-unknown` |
| 7 | `DONE` ∧ 产物齐备 ∧ 提交齐备 | `verify` | `done-complete` |
| 11 | `STALLED` ∨ `REENTRY_REQUIRED` | `stop` | `stalled-handoff` |
| 8 | 产物齐备 ∧ 末行非 `ANOMALY:` ∧（末行哨兵 ∨ salvage 完整记录） | `resume` | `salvage-accepted` / `artifacts-uncommitted` |
| 9 | 产物齐备 ∧ 无末行哨兵 ∧ 无完整 salvage | `retry` | `salvage-not-recorded` |
| 10 | `false_completion=true` | `retry` | `false-completion` |
| 12 | 其余终态（`INCOMPLETE/ANOMALY/FAILED/DEAD/TIMEOUT/NO_SIGNAL`） | `retry` | `terminal-retry` |
| 13 | 兜底（终态与产物/提交证据相互矛盾） | `stop` | `evidence-gap` |

门与上限：

- **C-47 尝试上限**：`attempt` 已知且 `attempt ≥ retry_limit` 时，候选为 `resume` / `retry` / `stop` 的一律改写为 `stop`（`reason=attempts-exhausted`）——按 C-47 字面清单执行，已是 `stop` 的候选同样改标，其原 `reason` 让位于上限事实。`watch` / `none` / `verify` 不受此限。`attempt` 未知时 MUST NOT 给 `resume`：降级 `retry`，`recovery_decision.blocked_by` 记 `attempt-unknown`。
- **C-48 salvage 门**：仅当状态脊同时具备 `salvage=accepted`、非空 `salvage_evidence`、非空 `salvage_at` 才算“完整记录”；否则按未记录处理，候选不得为 `resume`。本切片不写 salvage 记录（065c 承接）。
- **C-49 只建议**：`stop` 在 065a 只是建议——不杀进程、不删证据、不移除 worktree；活进程的 `TIMEOUT` 优先落 `watch`，停线只能在最终快照与用户显式决定之后发生。
- `recovery_decision` 始终内嵌 `action` / `reason` / `preconditions[]` / `blocked_by[]`，且 `action` / `reason` 与顶层 `recovery_action` / `recovery_reason` 相等。`blocked_by` 非空时必须能解释“为什么没采用更高优先级动作”。

## 退出码与只读边界

- 退出码封闭集：`0` 求值成功（任何 `loop_state` 都是数据，不编码为退出码）、`1` 拒绝 / 校验失败（含未实现动作的信封）、`2` 参数错误或必需输入不可读不可解析。
- watcher 的判定码 `10–16` 是**数据**：只写入 `watch_verdict.exit_code`，本入口不复用、不重定义。
- 快照不写状态脊、四件套、Registry 或工作树，也不改 mtime；`--out` 是唯一写路径，目标与父目录先 `realpath` 再与解析后的 state dir / repo 比较（比较先于创建临时文件），落在其内以退出码 `2` 拒绝且不留文件；写入走同目录临时文件 + 原子替换，内容与 stdout 信封相同。

## 引用关系

- 判定表的运行入口与参数/退出码契约：`.specify/specs/065a-state-awareness/contracts/loop-state-cli.md`。
- 中断形态与恢复动作条款：`.specify/specs/065a-state-awareness/contracts/interruption-and-action.md`。
- 产物映射与提交证据条款：`.specify/specs/065a-state-awareness/contracts/stage-artifact-map.md`。
- 信封字段与不变量：`.specify/specs/065a-state-awareness/contracts/snapshot-envelope.md`。
- watch 判定语义：`references/watch-model.md`（owner）。派发与阶段 prompt：`references/stage-prompts.md`。U4 核验清单与 plan-owned 集合：`references/stage-prompts.md` § Independent Verification、`references/efficiency-model.md` §3.1。
- `SKILL.md` 与其它 references MUST 引用本文件的章节，不复制上表。
