# Observer Lifecycle — 派发简报、引擎调用与缺口/失败语义

Owner split（`contracts/observer-lifecycle.contract.md` C-12）：`SKILL.md` § SDD Observer 拥有生命周期条款与状态脊记录节形状；本文件拥有派发简报模板、引擎调用循环与缺口/失败语义。本文件不含循环逻辑，也不引用任何驱动技能。

## Dispatch brief template

编排者从线自身的事实填充每个 `<...>` 槽位；简报以 fast-fail 注入子句（拥有者字面量，逐字节相等）作为独立段落开头。

```text
<!-- fast-fail-clause:begin -->
fast-fail-clause(快速失败注入子句)——执行中发现与已记录预期不符的状态时:
- 先问一个问题:解决它需要**纠正**还是**裁定**?纠正 = 恰有一种与已记录意图一致的读法、改动局部可逆、未证伪任何下游前提、未越过本动作声明的范围。
- 纠正 ⇒ 就地修完,并在回传中披露。裁定(须在两种以上读法间选择,或须发明工件未记录的意图)⇒ **停在本层、回抛编排者,MUST NOT 就地修平后继续**。
- 回传 MUST 含一条显式异常行:有异常则逐条以**行首** `ANOMALY:` 列出;无异常则明写 `未发现异常`。缺该行即回传不完整,沉默 MUST NOT 被读作干净。
- 判据、两份封闭清单与上送件形态的唯一真源:`.specify/shared/guidelines/fast-fail.md`。
<!-- fast-fail-clause:end -->

## Assignment
- line: <line_id>（run: <run_id>）
- spec: <NNN-slug>；journal: <spec dir>/journal.md（只经 .specify/scripts/python/journal-utils.py 追加，不手写）
- spine: <state spine path>；state dir: <runner state dir>
- execution label: <line_id>--<run_stamp>--observer（既有三段约定）；triplet 目录: <label>=<triplet dir>
- window: 既有派发 turn budget 与阶段 deadline（不新建定时器）

## Concurrency obligation
- 按 .specify/shared/definitions/subagent-definitions.md § The Concurrency Obligation 做一次性评估；类表 .specify/shared/declarations/facts/concurrency-class.yaml；串行理由码 .specify/shared/declarations/facts/serial-reason.yaml；读数字段 .specify/shared/declarations/facts/effective-concurrency.yaml。
- 单写者义务：同一线同一时刻至多一个未结算执行；上一个 `.status` 未结算时不得派发下一个；观测职责内部串行。

## Read domain
- 状态脊（观察者记录节 + 两条窄语法）、阶段日志与完成哨兵、checkpoint 文件、git 历史、正证据四件套（pid / status / log / heartbeat）、exec 记录与 meta 信封。
- 排除：编排者会话上下文与阶段提示词正文（不是观测输入）。

## Write surface
- journal（经 .specify/scripts/python/journal-utils.py）；自身执行产物（既有 `.specify/agents/execution/logs/` 布局的 triplet）。
- 写状态脊、阶段产物、feature 注册表或 glossary 均为越界缺陷。

## Forbidden
- 不评价、不建议、不推断；journal 行不得承载评价、建议、因果推断、严重级或推荐。
- 不发出用户可见的汇报、提问或审批请求；不引用或加载驱动/循环技能；不承载或启动 SDD 运行。
- 内部 subagent 串行使用，宿主 in-process 并发路径 BANNED。

## Return contract
- 回传 MUST 含一条显式异常行：无异常明写 `未发现异常`，有异常逐条以行首 `ANOMALY:` 列出；缺该行即回传不完整。
```

## Engine invocation loop and actions

- journal 只由引擎写：每次追加是一次 `journal-utils.py --action append` 调用，携带完整身份（`--spec-dir`、`--spine`、`--state-dir`、`--repo`、`--line-id`、`--run-id`、`--execution-label`）。
- 一次执行内：每个观测轮次追加一次；载体无变化的轮次不追加（引擎的幂等身份）；窗口正常结束时传 `--settle`；线终态收束时传 `--final`，它追加 `line-terminal` 与 `observer-settle`，并以一条 `observer-gap` 关闭仍开着的窗口。
- 退出码：`0` 追加成功或检查干净；`1` 检查发现或输入拒绝；`2` 身份不符（陈旧或外来的执行 label 永不追加）；`3` 并发写者被拒（不写入任何内容）。
- `--action check` 严格只读，MUST NOT 重写 journal。

## Gap semantics

- 缺口是两次执行之间未被覆盖的窗口，绝不以推断内容填充：窗口起点 = 上一条已写入条目的 `observed_at`（无条目时取状态脊记录节的 `started_at`）；窗口终点 = 新执行首条条目的 `observed_at`。
- 每个未覆盖窗口恰好一条 `observer-gap` 行：`event_at` = 窗口起点，`observed_at` = 窗口终点；`--final` 追加以同一方式关闭开着的窗口。
- 重启追加同一 journal，并按上述规则为每个缺口产生恰好一条行。

## Failure semantics

- 启动失败：状态脊观察者记录节写 `state: failed` + 一行原因，由既有收束报告披露；启动失败不产生 journal。
- 运行中掉线：失败执行的 `.status` 保持 unsettled / failed；driver 在下一阶段边界从同一实例重启；journal 获得一条 `observer-gap`，不产生任何伪造行。
- 收束执行失败：状态脊写 `state: failed` + 原因，收束报告点名未闭合窗口的起止；journal MUST NOT 被改写以伪造闭合。
- 非阻塞：任何阶段推进、checkpoint、审查或合并都不依赖 observer；披露是唯一的收束义务，observer 不发出用户可见的汇报、提问或审批请求。
