# Watch Model — 统一监听模型（wait / monitor / poll / observe）

> 本文件是 sdd-loop-driver 对「等待、监控、轮询、监听」语义的**唯一权威落点**。SKILL.md、dispatch-recipes.md、stage-prompts.md 只引用本文件，不复述规则。自包含：运行时零框架依赖，全部参数为入口参数。
>
> 适用对象：远程/本地子代理进程、异步脚本、阶段日志、心跳、退出记录，以及多线并行时的批量监听。

## 0. 不变量（Invariants）

1. **驱动者存活（driver liveness）**：U3 的等待必须在驱动者当前运行内完成并交回结果；「挂监视器后结束会话等通知」不是合法形态——除非宿主能证明通知会自动恢复**同一运行**（见 §6）。
2. **完成需正证据（positive evidence）**：进程消失、`pgrep` 零匹配、监听窗口到期都**不是**完成。完成只来自完成哨兵或退出记录；哨兵仍只是必要条件，充分条件由 U4 独立校验补齐。
3. **窗口到期 ≠ 阶段超时（window ≠ deadline）**：单次监听窗口到期只产生 `RUNNING`；只有阶段 deadline（阶段开始 + 阶段超时）才产生 `TIMEOUT`。这条把「监视器误判超时」与「阶段真的超时」分开。
4. **等待不烧回合（no idle turns）**：禁止把 `sleep N` 作为独立工具回合再检查；等待必须收在**单个阻塞调用**内部（长轮询脚本/阻塞 tail/远端等待循环），调用在事件发生或窗口到期时返回。
5. **监听无副作用（read-only watch）**：watcher 只读信号，不 kill 进程、不写项目状态、不改工作树；一切处置属于 U5。
6. **可重入（re-entrant）**：watcher 不持有内存状态，全部信号来自文件/进程；任意新会话凭状态脊 + 一次 `--once` 快照即可接管。

## 1. 词汇（Vocabulary）

| 词 | 含义 | 本模型中的形态 |
|----|------|----------------|
| **Wait（等待）** | 驱动者暂停推进，直到终止事件或窗口到期 | 只允许发生在一次工具调用内部（长轮询）；或经 §6 探针证明可自动恢复的宿主通知 |
| **Monitor（监视）** | 持续采样一个或多个目标的信号并给出判定 | `.specify/scripts/watch-target.sh`（无状态、可重入、只读） |
| **Poll（轮询）** | 周期性重复采样 | **回退形态**：无法阻塞等待时使用；不是缺省 |
| **Observe（观察）** | 读取日志/心跳/退出记录，不做判定 | watcher 内部动作，或 U3 的证据采集 |
| **Watch window（监听窗口）** | 一次阻塞调用的最长持续时间 | `--window`；到期返回 `RUNNING`，驱动者立即重入下一窗口 |
| **Stage deadline（阶段期限）** | 阶段开始时间 + 阶段超时（缺省 90 分钟） | 唯一产生 `TIMEOUT` 的判据；入口可覆盖 |
| **Deadline grace（期限宽限）** | 阶段期限之后继续采样、等待晚完成证据的窗口 | `--deadline-grace`（缺省 120s）；晚到的 status/sentinel 重判为 DONE/FAILED；宽限到期仍无终态才返回 `TIMEOUT` |

## 2. Watch Target 与信号源

一条线 × 一个阶段 = 一个 watch target。信号按下表采集；缺失信号必须降级为显式 `na`/`missing`，不得用零值或猜测填充。

| 信号 | 来源（runner 写入） | 用途 | 缺失时 |
|------|--------------------|------|--------|
| **完成哨兵** | 阶段日志最后一个非空行，精确等于 `<STAGE>-DONE` | 完成的正证据（必要条件） | `sentinel=na`（未配置）或 `no` |
| **退出记录** | `status-<line>-<stage>`：`exit=<rc> at=<epoch> sentinel=<0|1>`，用临时文件 + `mv` 原子写入 | 退出码 + 哨兵布尔值；完成/失败的强信号 | `rc=na`，降级看哨兵与进程状态 |
| **存活** | `pid-<line>-<stage>`：`pid=<pid> start=<start_ticks> at=<epoch>` | `kill -0` + `/proc/<pid>/stat` 僵尸/复用校验 | `pid=missing`，按启动宽限期处理 |
| **心跳** | `heartbeat-<line>-<stage>.log`：每 30s 原子覆盖为 epoch | 证明 **runner 外壳**仍活着；不证明子代理有进展 | `heartbeat=missing`；不作为单独完成/超时判据 |
| **进度** | 派生 live log（`log-<line>-<stage>.log`，最后非空行是哨兵来源）+ raw stream（`raw-<line>-<stage>.jsonl`，经 `--raw-stream` 只报告 `stream=na\|absent\|growing\|idle` 与字节数） | 排障与卡死辅助；raw 增长只是可见性 | `-p` / buffered 模式下日志在退出前静默，属预期；stream 缺失时 `stream=na\|absent` |
| **异常行** | 日志最后一个非空行以 `ANOMALY:` 开头 | 显式失败回传（fast-fail） | 无 |
| **阶段期限** | 状态脊中的 `stage_started_at + stage_timeout` | 唯一的 `TIMEOUT` 判据 | 入口必须提供，否则不得判超时 |
| **Hook 事件** | `Stop`/`SubagentStop` hook 原子写 `hook-event-<stage>.json` + FIFO 行 | **提前完成信号**；只缩短等待，不单独构成判定 | `hook=na`（未配置）或 `none` |

## 3. 判定状态机（Verdict State Machine）

判定按下列顺序短路；先命中者胜。`.specify/scripts/watch-target.sh` 是退出码的代码侧所有者（`--help` 与 `--self-test` 钉住）。

| 判定 | 退出码 | 终止? | 触发条件（按优先级） | 驱动者动作 |
|------|--------|-------|----------------------|------------|
| `ANOMALY` | 11 | 是 | 退出记录存在或进程已死，且日志最后非空行以 `ANOMALY:` 开头 | U5：按重试上限处置；保留异常行 |
| `FAILED` | 12 | 是 | 退出记录 `exit≠0`，无异常行 | U5：先修可归因原因再重试 |
| `INCOMPLETE` | 15 | 是 | **配置了哨兵时**，退出记录 `exit=0` 但哨兵缺失 | **伪完成候选**：U4 判未完成，不派发下一阶段 |
| `DEAD` | 13 | 是 | 有 PID 记录且进程已死/僵尸/PID 复用，且无退出记录 | U5：外壳死亡，查日志尾部后重试/上送 |
| `TIMEOUT` | 14 | 是 | 无更高优先级信号，且 `now ≥ stage deadline`（宽限期已耗尽） | U5：**先做 `--once` 最终快照**；`pid=alive` + `heartbeat=fresh` 时不得仅凭 TIMEOUT 停线或杀进程，优先延长/继续观察；停线须用户显式决定；watcher 不杀进程 |
| `NO_SIGNAL` | 16 | 是 | PID 与退出记录都缺失，且超出启动宽限期 | U5：启动失败/路径错误，先查前置检查与 runner |
| `DONE` | 0 | 是 | 哨兵命中（退出记录 `rc=0` + 哨兵，或日志最后非空行 = 哨兵；进程状态不改变该判定）；未配置哨兵时退出记录 `rc=0` 即 DONE | **U4 独立校验**；哨兵不是充分条件 |
| `RUNNING` | 10 | 否 | 进程存活或仍在启动宽限期内，无终止信号 | 立即重入下一 watch window，不做 agent 侧 sleep |

补充规则：

- **退出码 0 但无哨兵**不是完成（`INCOMPLETE`）；**哨兵在但进程仍活**可先判 `DONE` 进入 U4（哨兵是执行者的完成声明，artifact 校验兜底）。
- **异常行**只在其已是最后一行且（退出记录存在或进程已死）时判 `ANOMALY`；进程仍活时异常行可能是中间输出，返回 `RUNNING` 并带 `anomaly=observed`。
- **心跳 stale + PID alive** 返回 `RUNNING` + `heartbeat=stale`（外壳看门狗退化），不直接判 `STALLED`；阶段期限仍是唯一超时判据。日志增长或 stream 输出可覆盖该警告。
- **窗口到期**永远返回 `RUNNING`，绝不返回 `TIMEOUT`。
- **进度与 raw 增长不参与判定**：live log 行数/增长、raw stream 字节增长都不得单独产生 `DONE` 或 `TIMEOUT`；哨兵仍只认 live log 最后非空行，raw 只作证据面。非终止事件中的哨兵字样不构成完成。
- **降级**：CLI 不支持 stream-json（`progress=degraded reason=cli-lacks-stream`）或派生失败（先 `--finish` 恢复，再 buffered fallback）时，runner 在 status 记录降级与原因；watcher 判定表与退出码零改动，`sentinel=0` 仍按 `INCOMPLETE` 处理。

### 3.1 Deadline grace 与 late completion（2026-10-20 热修）

- **TIMEOUT 是预算判定，不是死亡证明**。子代理可能在 deadline 之后才写出 `exit=0/1` 与哨兵；把 TIMEOUT 当成“可杀/已卡死”会把晚完成误判为故障（实测：postreview-repair 在 deadline 后约 11 分钟自行完成，status 显示 `exit=0 sentinel=1`）。
- watcher 在 deadline 后继续采样 `--deadline-grace` 秒（缺省 120）；期间任何 status / sentinel / 异常行按 §3 重新判定，`DONE`/`FAILED`/`ANOMALY` 优先于 `TIMEOUT`；宽限耗尽仍无终态才返回 `TIMEOUT`，reason 为 `deadline-grace-expired`。
- 宿主工具超时 MUST 设为 `window + deadline-grace + 30s`；否则宿主会先杀掉 watcher，宽限来不及生效。
- 驱动者收到 `TIMEOUT` 后 MUST 先跑 `--once` 最终快照：若 status/sentinel 已出现，按 U4/U5 重新路由，**不得判 stall**；若 `pid=alive` + `heartbeat=fresh` 仍无终态，优先延长/继续窗口。停线或 TERM 必须经用户显式决定，并在停止前再跑一次 `--once`，保留 worktree/status/log 证据。
- **无提交 ≠ 卡死**：长审计/长测试期间可能数十分钟没有 commit；判断依据是 pid/heartbeat/status/session 活动，而不是 commit 间隔。

## 4. 机制阶梯（事件优先）

按顺序选择；只有上一级不可用时才降级。降级必须在状态脊记录原因。

0. **Hook 事件补充（推荐，不改变回退路径）**：runner 注入 `Stop` hook，hook 原子写 `done.json` 并尝试写 FIFO；watcher 在同一窗口内优先 `--hook-done` 检查、再以 `--hook-fifo` 阻塞读（`read -t … <> fifo`，避免无写者时 open 阻塞）。事件到达只产生 `hook=observed`，判定仍由哨兵/退出记录给出。hook 未配置或未触发时，行为与第 1 级完全一致。
1. **长轮询窗口（缺省回退）**：一次工具调用内跑一个远端/本地循环，每 `--interval`（缺省 3s）采样一次，命中终止判定或窗口到期即返回。等待期间**零模型回合、零 token**；事件检测延迟约为一个内部采样间隔。
2. **宿主原生通知/监视器（仅作补充）**：当且仅当宿主能证明「通知会自动恢复同一驱动运行」时，可把原生监视器作为唤醒补充；每次唤醒仍要执行一次快照判定，且**不得在布置监视器后结束驱动者会话**（不变量 1）。宿主能力未经探针证明时，原生监视器只用于可见性，不用于等待。
3. **间隔轮询（回退）**：无法长轮询（宿主无可用阻塞调用、工具超时上限过短、无 shell）时，用有界间隔检查；多线合并为一次检查；退避曲线见 §5。
4. **禁止形态**：
   - 独立 `sleep N` 回合后检查（空等烧回合）；
   - 固定 cadence 作为缺省（应作为回退）；
   - 监视器判定「窗口到期」后直接停线/杀进程；
   - 用 `pgrep` 零匹配、进程消失或日志静默推断完成。

**窗口尺寸**：`--window` ≤ 宿主工具超时上限 − 30s 余量（例如宿主上限 600s → 窗口 300–540s）。窗口到期返回 `RUNNING` 后**立即**发起下一窗口，不在 agent 侧等待。若宿主没有可调工具超时，使用短窗口（60–120s）重复。

**进度面（stream / buffered / degraded）**：stream 模式下 runner 以 `--output-format stream-json` 运行，raw 落盘、派生 live log 增量增长；CLI 不支持时转 buffered 并记 `progress=degraded` + 原因；派生失败先 `--finish` 恢复、再 buffered fallback，皆无则 `sentinel=0`（INCOMPLETE，绝不伪完成）。进度面选择不改变 §3 判定、退出码或窗口语义；`--raw-stream` 的 `stream=` 字段只是可见性证据。

## 5. 主动策略（Proactive Rules）

- **先查后等（check-before-wait）**：每个窗口开始时先做一次零成本快照；已终止则立即返回，不进入 sleep。
- **廉价信号优先**：退出记录 → PID 存活 → 日志尾行 → 心跳 mtime。任一步给出终止判定即短路，避免无谓的远端读取。
- **自适应内部间隔**：远端长轮询 3–5s；本地 1–2s。窗口内不需要向驱动者输出进度；只有终止或窗口到期才输出。
- **批量多线**：一个窗口、一次连接检查全部线（manifest 模式）；任一线终止即返回全部线的快照，驱动者先处置终止线，再为剩余线重入。快线不被慢线阻塞。
- **早发现异常**：退出记录出现即返回，不等窗口到期；进程死亡即返回 `DEAD`；最后一行是哨兵即返回 `DONE`。
- **预算组合**：`min(剩余阶段期限, 窗口上限)` 决定本次窗口；窗口到期后重新计算，不允许越过阶段期限。
- **重入快照**：新会话接手先跑 `--once`；若已终止，直接进 U4/U5，绝不重新派发已完成的阶段（这正是「clarify 12:22 已完成却被误判超时」的防线）。
- **留痕**：只在状态转移（U2 派发 / U3 终态 / U4 校验 / U5 停线）写状态脊；`RUNNING` 窗口不写，避免每窗写盘。

## 6. 宿主适配（Host Adapters）

| 宿主能力 | 合法等待形态 | 说明 |
|----------|--------------|------|
| 有可调超时的阻塞 shell 工具（Qoder CLI / Claude Code 等） | 一次调用跑 `watch-target.sh --window N`，工具超时设为 N+30s | 缺省形态；调用期间零 token |
| 有原生后台任务/监视器，且**通知会自动恢复同一运行** | 原生通知作为唤醒补充 + 每次唤醒做快照 | 必须先用小实验证明自动恢复；否则按下一行 |
| 有原生监视器但通知不会自动恢复运行 | 仅用于可见性；等待仍用阻塞长轮询 | 布置后结束会话 = 循环静默死亡（不变量 1） |
| 无阻塞 shell / 工具超时不可调 | 短窗口间隔轮询（60–120s），批量多线 | 状态脊记录降级原因 |
| 本地拓扑 | 同一脚本去掉 ssh/su 层 | 路径与身份为入口参数 |

远端拓扑的一次窗口：

```bash
# 上传一次（每主机一次即可）
ssh <alias> "cat > /home/<run-user>/watch-target.sh" < <skill-dir>/scripts/watch-target.sh
ssh <alias> "chmod +x /home/<run-user>/watch-target.sh"

# 每个窗口：一次 ssh（与 runner 同一执行身份），命中即返回；工具超时设为 window+deadline-grace+30s
ssh <alias> "su - <run-user> -c 'bash /home/<run-user>/watch-target.sh \
  --label <line> --pid-file /home/<run-user>/pid-<line>-<stage> \
  --status-file /home/<run-user>/status-<line>-<stage> \
  --log /home/<run-user>/log-<line>-<stage>.log \
  --sentinel <STAGE>-DONE --heartbeat /home/<run-user>/heartbeat-<line>-<stage>.log \
  --deadline-epoch <epoch> --window 200 --interval 3 \
  --deadline-grace 120'"
```

## 7. 存活判据的正确性（pgrep 陷阱）

**实测缺陷（必须作为回归用例保留）**：

```bash
count=$(pgrep -c "$pattern") || echo 0
# 零匹配时：pgrep -c 先向 stdout 打印计数 0，再以退出码 1 结束；
# `|| echo 0` 于是追加第二个 0 → 变量是 "0\n0"，不是 0。
# 后续 [ "$count" -eq 0 ] 报 "integer expression expected"，
# 或分支误走，把运行中的阶段判成结束/超时。
```

正确规则：

1. **首选 PID 文件 + `kill -0`**；Linux 上再读 `/proc/<pid>/stat`：状态 `Z` 视为死亡，字段 22（start ticks）与 pidfile 不一致视为 **PID 复用**。
2. 必须用模式匹配时，只取布尔：`pgrep -f "$pattern" >/dev/null 2>&1`。模式要锚定（如 `[q]odercli .*<line>`），避免匹配 watcher/ssh 自己的命令行；注意 `pgrep -f` 仍可能匹配**执行检查的 shell 自身**（pattern 字面量就在其命令行里），所以计数不可信、布尔也可能假阳性——这也是 PID 文件优先的原因。
3. 必须计数时：`count=$(pgrep -fc "$pattern" 2>/dev/null || true); count=${count:-0}`，再用 `case "$count" in ''|*[!0-9]*) count=0;; esac` 归一化；**禁止** `|| echo 0`、禁止把 `pgrep -c` 当存活判据。计数含自匹配偏差，只可用于「至少有一个」的粗判，不可用于精确进程数。
4. **零匹配 ≠ 完成**：零匹配只说明「没有找到」，可能因为进程名变了、权限不足、PID 文件丢失或匹配模式错误；完成必须有哨兵/退出记录正证据。
5. **每次修改监视器都跑反向用例**：零匹配、进程已死、僵尸、PID 复用、退出码 0 无哨兵。`watch-target.sh --self-test` 覆盖这些用例。

## 8. 多线批量（Manifest）

Manifest 每行一个 target，`|` 分隔：

```text
label|pid_file|status_file|log|sentinel|heartbeat|deadline_epoch
```

- 空字段用 `-`；路径不得包含 `|`。
- 一次调用检查全部行；任一行终止即返回所有行的判定，驱动者逐线处置。
- 退出码取终止判定中的最高严重级：`ANOMALY > FAILED > DEAD > INCOMPLETE > TIMEOUT > NO_SIGNAL > DONE`；全部 `RUNNING` 时为 10。
- 一行失败不阻塞其他行（并发隔离在编排层，watcher 只报判定）。

## 9. 与 U3/U4/U5 的接线

- **U2**：状态脊写入 `stage_started_at`、`stage_deadline_epoch`、四件套路径（pid/status/log/heartbeat）与哨兵字面量。
- **U3**：按 §4 选机制；终止判定 → 写状态脊 `last_verdict` + 证据一行 → 进 U4（`DONE`/`INCOMPLETE`）或 U5（其余）。`RUNNING` → 立即重入。
- **U4**：哨兵（必要）+ 产物核验 + 纪律抽查（充分）；`DONE` 只是候选，不是结论。
- **U5**：四要素上送件携带 watcher 的 `verdict` / `pid` / `heartbeat` / `rc` / `reason` / `last_status` 快照，并注明 `grace_expired` 是否发生；收到 `TIMEOUT` 先 `--once` 最终快照，活进程不得仅凭 TIMEOUT 停线/杀进程；绝不静默等待。
- **重入**：先 `--once` 快照，按判定进 U4/U5 或恢复窗口。
- **调用失败不是判定**：一次监听调用没有返回任何 `WATCH` 行（ssh 255、宿主工具超时、网络中断）时，不改变阶段状态——先做 `--once` 快照或连通性检查，再重入新窗口；连续失败按 U5 的环境根因处置。**绝不把连接故障当作阶段失败，也绝不因此杀进程。**
- **重入时的 NO_SIGNAL**：若运行时文件已被清理但日志哨兵/阶段产物仍在，先按 U4 产物路径核对；核对通过即视为已完成，不按启动失败处置。

## 10. 参考实现

`.specify/scripts/watch-target.sh` — 无框架依赖的 bash 长轮询 watcher（可选 hook 事件补充）。

- 单目标与 `--manifest` 多目标；`--once` 快照；`--self-test` 回归用例。
- hook 参数：`--hook-done F`（持久完成记录，先查）与 `--hook-fifo F`（窗口内阻塞读，事件到达即缩短等待）；仅单目标可用。
- 输出为单行 `WATCH label=… verdict=… pid=… heartbeat=… hook=… anomaly=… sentinel=… rc=… elapsed=… reason=… stream=na|absent|growing|idle line=… run=…`；终止判定附带一行 `EVIDENCE …`（提供 `--raw-stream` 时附 `raw=<path> bytes=<n>`）。`stream=` 只作可见性，不参与任何 verdict。
- 只读信号，不 kill、不写项目状态；hook 事件只标记 `hook=observed`，从不由它直接产生 DONE。
- 退出码与判定表由 `--help` / `--self-test` 钉住；本文件的 §3 是语义映射，代码是精确值所有者；自测覆盖 hook-done、hook-fifo、零匹配、僵尸、PID 复用与伪完成。

- watcher 必须与 runner 以**同一执行身份**运行（`kill -0` 的权限前提）；远端拓扑两者都在 `<run-user>` 下。

## 11. 归属层与重接线快照（064）

> 本节只增加消费规则与快照入口；§3 的判定状态机与退出码保持不变。

- **归属参数**：watcher 可选 `--line-id` / `--run-id` / `--meta`；提供 `--line-id` 与 `--run-id` 时执行归属过滤，输出行追加 `line=` / `run=` / `attribution=`（`own|foreign|stale-run|unattributed|legacy`）。
- **消费规则**：只有 `own` 事件参与判定、进度与 Registry 状态；`foreign`/`stale-run`/`unattributed` 只出现在摘要，不改变 verdict、不改变状态、不转发为当前线路进度。
- **兼容规则**：未提供归属参数 → `attribution=legacy`，行为与 058 完全一致；单线新派发 MUST 提供归属参数。`legacy` 仅限单活动线 / 058 兼容调用；多活动线 MUST NOT 以 legacy 调用绕过归属过滤。
- **重接线快照**：新会话先 `--once` 判定（running → 恢复监听；done → U4/U5；dead → U5；远端不可达 → `stalled(remote-unreachable)`），再决定去向；快照不写状态、不杀进程。
- **远端不可达**：一次 watcher 调用没有返回任何 `WATCH` 行（ssh 255/超时）时，不改变阶段状态，不判 DEAD；先做连通性检查并按 `stalled(remote-unreachable)` 处置。
- **lease 续租钩子**：持有 driver lease 时，窗口 ≤ `ttl/3`（缺省 ≤200s）或传 `--lease-renew-cmd`（`--lease-renew-interval` 缺省 60s）在窗口内续租；钩子失败不改变判定。

- 配套脚本：`.specify/scripts/hook-stop.sh`（Stop hook 模板，写 done JSON + 尽力写 FIFO）与 `.specify/scripts/watch-hook.sh`（远端同身份长读，先查 done、再读 FIFO，输出事件或 `HOOK_TIMEOUT`）。

## 12. Hook 事件补充（Qoder CLI Stop / SubagentStop）

Hook 是**提前完成信号**，不替代 U4 的哨兵与产物校验；它解决的是「阶段已完成但 watcher 还在采样」和「stdout 缓冲导致完成不可见」两类延迟。

### 12.1 能力与配置

- Qoder CLI 提供与 Claude Code 兼容的 hooks：`Stop`（主 agent 正常结束）、`SubagentStop`（子代理结束）、`SessionEnd`、`Notification` 等；支持异步/命令/HTTP 等类型。
- 配置位置：`~/.qoder/settings.json`、`<project>/.qoder/settings.json`、`<project>/.qoder/settings.local.json`；**推荐按派发隔离**，在 runner 中用 `--settings <per-dispatch.json>` 注入，避免污染全局配置。
- 先例：本机实测 Stop hook 通过 `--settings` 注入、写 FIFO 后 `read -t` 即时返回；API 崩溃时 Stop 不触发，仍由 status/exit 记录判 FAILED。

### 12.2 runner 侧（本地/远端同构）

```bash
# 1) 每阶段独立 FIFO 与 settings（远端由 run-user 创建）
mkfifo "$dir/hook-done-$line-$stage.fifo"
cat > "$dir/hook-settings-$line-$stage.json" <<'JSON'
{"hooks":{"Stop":[{"hooks":[{"type":"command",
  "command":"/abs/path/hook-stop.sh","timeout":5}]}]}}
JSON
# 2) hook 读取 HOOK_EVENT_DIR / HOOK_STAGE / HOOK_FIFO
HOOK_EVENT_DIR="$dir" HOOK_STAGE="$stage" HOOK_FIFO="$dir/hook-done-$line-$stage.fifo" \
  qodercli -w "$project" --permission-mode auto \
  --settings "$dir/hook-settings-$line-$stage.json" -p "$(cat "$dir/prompt-$line-$stage.md")"
```

- hook 必须先**原子写** `hook-event-<stage>.json`（含 `session_id`、`hook_event_name`、时间戳），再尽力写 FIFO；FIFO 写用 `timeout 5` 包裹，避免无读者时挂住。
- `settings` 与脚本使用绝对路径、`umask 077`；不要改全局 settings。
- 远端 runner 仍用 `nohup`/`setsid` 脱离；hook 与 FIFO 都留在 run-user 侧。

### 12.3 watcher 侧

```bash
.specify/scripts/watch-target.sh --label "$line" \
  --pid-file … --status-file … --log … --sentinel "$STAGE-DONE" --heartbeat … \
  --hook-done "$dir/hook-event-$stage.json" \
  --hook-fifo "$dir/hook-done-$stage.fifo" \
  --deadline-epoch "$deadline" --window 540 --interval 3
```

- `--hook-done` 每轮先查（check-before-wait）；`--hook-fifo` 用 `read -t <interval> <> fifo` 等待，事件到达即进入下一轮判定。
- `hook=observed` 只表示「提前信号已到」；DONE 仍要求退出记录/哨兵，U4 仍要求产物与纪律核验。
- hook 未触发（崩溃、配置错误）时，watcher 的原有 PID/status/sentinel/deadline 路径不变。

### 12.4 远端 SSH 拓扑

```bash
# 每个窗口：一次 ssh（与 runner 同一身份），长读远端 FIFO/done，工具超时 = window + 30s
ssh -o BatchMode=yes -o ConnectTimeout=5 <alias> \
  "su - <run-user> -c 'bash --noprofile --norc -c \
    \"bash /home/<run-user>/watch-hook.sh <stage> <window> <deadline> \
      /home/<run-user>/hook-done-<stage>.fifo \
      /home/<run-user>/hook-event-<stage>.json\"'"
# 事件返回后，仍需在远端跑一次 watch-target.sh --once 取得权威判定
ssh <alias> "su - <run-user> -c 'bash --noprofile --norc -c \
  \"bash /home/<run-user>/watch-target.sh ... --once\"'"
```

- SSH 断开**不杀远端进程**；下一窗口先查 `done.json`，再读 FIFO，丢失连接不丢事件。
- 登录 shell 噪声：远端 watcher 统一 `bash --noprofile --norc` 并重定向 stderr；只解析最后一行/数字，空输出 = `UNKNOWN`，绝不当作 0/完成。
- 多线：线数少时每线一个 SSH 长读；线数多时所有 hook 追加到单一 `hook-events.log`，本地用一条 `ssh ... "tail -F -n 0 hook-events.log"` 流式读取并按 `line/stage` 路由；`done.json` 仍按线持久化。manifest 模式目前不消费 hook 参数（单目标专用）。
- 可选 `type:"http"` hook：远端 POST 到编排侧收集器再由本地 FIFO 唤醒；代价是入站网络、鉴权与监听器，SSH 长读无需入站。

## 13. 观测侧故障矩阵（2026-10-19 复盘）

| 故障 | 根因 | 规则 |
|------|------|------|
| 阶段完成仍判超时，空等 86 分钟 | `pgrep -c` 零匹配先打印 `0` 再以 1 退出，`\|\| echo 0` 追加第二个 0，数值比较失效 | **禁止用 `pgrep` 计数判存活/完成**；PID 文件 + `kill -0` + `/proc/<pid>/stat` start ticks/僵尸检查 |
| 无关 qodercli 会话让 watcher 永不归零 | 按用户级 `pgrep -u agent -x qodercli -c` 计数，计入其他 cwd 的会话 | 每线每阶段独立 PID/status/log/heartbeat；匹配限定「本仓 + 本线」；不使用用户级普查 |
| 阶段退出后 watcher 静默 | 登录 shell 报错文本混入 stdout，整段 `tr -d` 后永不等于 `0` | 远端 `bash --noprofile --norc` + stderr 重定向；只取最后一行/数字；**空输出 = UNKNOWN，继续轮询** |
| 共享 `cws-lib-bash` 被 teardown 删除 | 临时脚本使用通用变量名 `ROOT`，被 `cws_bash_env` 覆盖后 `rm -rf "$ROOT"` | 禁止在 source 环境脚本中使用 `ROOT`/`HOME`/`PATH` 等通用名；`rm -rf` 前 `realpath` + 前缀断言；优先保留备份 |
| 正常完成后 hook 未触发 | API/CLI 崩溃不会产生 Stop 事件 | **hook 只是补充**；status/exit 记录与哨兵必须独立判定；`EXITED_NO_SENTINEL` 回传最后一行、日志尾部、git 状态 |
| 进程消失/日志静默被当作完成 | 观测面只有「没有信号」 | 完成必须来自退出记录或哨兵；`DEAD`/`NO_SIGNAL` 进 U5，不是 DONE |

**双信号硬规则**：正常完成 = 退出记录 `rc=0` **且** 日志最后一行哨兵（或约定的等价正证据）；hook 事件只能缩短等待，不能替代任一信号。U4 的产物/纪律核验仍是最终充分条件。

