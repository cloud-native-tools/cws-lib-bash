---
name: sdd-loop-driver
description: 无人值守 SDD 循环驱动手册——以一条一遍性提示词驱动主代理完成「登录环境 → 本地用 fork 承载（同族 qodercli 子进程经 .specify/scripts/stage-runner.sh）/ 远端用外部 CLI 为子代理 → 按阶段推进 SDD 完整流程（阶段序列与完成哨兵由 `.specify/shared/declarations/facts/driver-stage-sequence.yaml#/statement` 与 `.specify/shared/declarations/facts/driver-completion-sentinels.yaml#/statement` 单一拥有，本手册不复述取值）→ 合并 main」的完整闭环，全程循环自推进、零用户提醒。当用户说「使用SDD开发模式推动 <项目>」「无人值守推进」「sdd-loop-driver」「需要使用一个循环来完成这项工作，而不是每次由我提醒你重试或继续」时加载本手册。执行细节（断点探测 / 阶段化 prompt 文件 / runner 与派生 / 后台执行+统一监听 / 收尾纪律）全部由本手册承接，入口只声明目标与起点。当以本技能名给出功能/改进描述时，视为 SDD 目标（目标项目可为本技能自身所在仓库），先做 U0/U1 并走阶段链，不得就地改代码或切换为技能维护路径。
skill_id: "<SKILL:.specify/skills/sdd-loop-driver/SKILL.md>"
classification: external
---

> **分类注解**：本 skill 依**依赖轴**判定为 external——自身零 spec-kit 依赖、任何宿主 agent 可直接加载；内容编排 spec-kit 的 SDD 流程（语义耦合显式声明：指挥子代理执行 `/speckit.*`），不构成运行时依赖。

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.

## What This Skill Does

把经多项目验证的「无人值守 SDD 驱动」固化为可执行手册：宿主 agent（无需安装 spec-kit）对每条项目线执行「断点探测 → 阶段派发 → 统一监听 → 独立校验 → 续环」，直到 review 完成并合并收尾。自迭代、独立校验、卡死处置三条硬需求内置于本手册；监听语义（等待/监控/轮询）的唯一权威落点是 `references/watch-model.md`。

**触发语义与路由**：以本技能名加载并给出功能/改进描述 = SDD 目标，目标项目可为任意仓库（含本技能自身仓库）；改进本技能也必须走 U0/U1 → 阶段链。仅入口显式声明「只做技能维护、不走 SDD」时，才允许 improve-skills/create-skills 维护路径。**主导流程唯一**：**加载后的第一个动作**是写出 U0 入口声明与阶段计划，在此之前不加载其他技能、不编辑文件、不派发 subagent。

**质量门完整**：checklist/analyze/review 在无人值守循环中一律必经、不可省略（编排见 dispatch-recipes.md Recipe 4）。与 sdd-project-setup / sdd-house-keeping **非强绑定、各自可独立运行**：框架 bootstrap 归 setup，周期性维护/记录回收归 house-keeping，阶段循环归本技能；候选清单仅建议，需确认后启动。

## Driver Topology（驱动拓扑——义务真源：run-agent 派发治理）

- **加载本手册的宿主 agent 就是驱动者**：U0–U6（探测/派发/轮询/校验/续环/收尾）由加载者在自己的会话亲自执行，不得委托任何 subagent；**自检**：若处于 subagent 上下文且被赋予「代为驱动循环」的任务，按显式异常行上报并停在前置阶段——嵌套驱动永不是合法形态。
- **流程不可替换**：不得用 improve-skills/create-skills 等维护路径替代 U0–U6（Hard Requirement 7）。
- **派发治理义务上收**：子代理提示词不引用/加载驱动技能、不含循环逻辑；义务全文与派发前拦截见 `.specify/skills/internal/run-agent/SKILL.md` 派发治理节与 subagent-definitions § Dispatch-Time Governance Obligation。
- **角色面按指针（根 super agent）**：驱动者是根 super agent；阶段派发载荷携带 `role_edge` 七字段（形态见 `references/stage-prompts.md` § 归属信封）；角色、角色边与协议归 `.specify/shared/definitions/superagent-definitions.md`。执行仍由既有派发前自检与 U4 承担 —— 不新增门禁，阶段序列与哨兵不变。
- **两侧环境模型**：spec-kit 只要求存在于执行侧（目标项目）；编排侧宿主无需安装，缺之不构成缺口（真源：`.specify/shared/workflow/execution-topology.md`）。

## When to Load

- 入口只声明**目标与起点**：目标项目（含登录别名/用户/路径）、断点（可省略，自动探测）、终态权威文档、特性切片（入口声明或按权威文档推导——不自动选题）。
- 宿主无 `.specify/` 也可运行；仅当子代理要在目标项目执行 `/speckit.*` 时目标项目才需具备 `.specify/`。
- 不适用于：需逐轮拍板的探索式会话；单命令进程内长跑。

### U0 入口解析（缺省 + 强制自检）

入口可以只给功能描述；缺省按下表解析，**不得因参数不全而切换流程**：

| 入口缺省 | 解析规则 |
|----------|----------|
| 目标项目 | 遵循 `.specify/shared/workflow/target-resolution.md`：**强依赖 `.specify/`**，未给路径且未给 host/ssh 别名 → 从会话 cwd **向上搜索**最近的合法 `.specify/` 根（显式本地路径则从其向上搜索）；找不到 → 拒绝执行并 handoff `sdd-project-setup` / 提示 `specify init`；显式目标优先；拒绝 basename `.specify`；远端先跑 execution-side target-root probe |
| 执行拓扑 | 未给 ssh 别名/run-user/远端路径 → **本地**（承载为 **fork**：同族 `qodercli` 子进程经 `.specify/scripts/stage-runner.sh`；异构 agent 用 **subprocess** 承载——该 agent 自身 CLI 的独立子进程；宿主内建 in-process subagent 路径 **BANNED**，不作为并发承载，见 `references/dispatch-recipes.md` § 本地原生拓扑）；给全 → 远端（外部 CLI）；只给 host 或三元组不完整 → 问一个澄清问题，不猜 |
| 终态权威文档 | 入口描述 + 现有 `docs/` + 宪法；写入 U0 状态脊 |
| 断点 | U1 自动探测，禁止猜测 |
| 特性切片 | 入口描述；未给则按权威文档推导，不自动选题 |
| 并发度 | 缺省 **24**；U0 在状态脊写 `agent_concurrency_requested` / `agent_concurrency_effective` / `agent_concurrency_reason` / `verifier_reserve`；每阶段按 effective 与 ready packages 重算，降级必须具名 |
| 写隔离 | 缺省 `write_isolation=shared-tree`；团队运行（一个绑定 goal 的 team）可声明 `worktree`，写 agent 各占 child line + 独立 worktree |

**Goal/Team（binding model）**：goal 与 team 都是**档案层**里的定义——goal 档案 `.specify/anchoring/<slug>/goal.md`、team 档案 `.specify/teams/<slug>/team.md`——归属由定义内的绑定记录回答（构成与取值域归 `.specify/shared/definitions/goal-definitions.md` § The Binding Record，team 侧归 `.specify/skills/internal/create-team/references/conceptual-model.md` § The Team Definition and the Binding Model）；两者都不落任何 spec 子目录。**创建时机不在本手册复述**：读 `.specify/shared/declarations/facts/goal-team-handoff-threshold.yaml` 的声明值——直接执行的运行不创建，交接的运行在 `tasks` U4 后创建 goal 与 team；命令运行由命令模板声明其创建时刻。状态脊字段名为 `goal_slug` / `team_slug` / `origin_spec_dir`，写入 MUST 只落新键；历史状态脊里的 `temp_goal_slug` / `temp_team_slug` / `temp_scope_spec_dir` 只经 goal 引擎的一次性迁移别名读取（引擎读旧键、写新键；别名在 094 之后的首个 minor 版本移除），MUST NOT 被静默丢弃，无法解析时按 `legacy-key-dangling` 失败。

**U0.5 自检（进入 U2 前必须通过）**：

1. 目标、拓扑、权威、切片、断点已写入状态脊？
2. 正准备直接编辑目标仓库？→ **停**：这是流程绕过，不是 U2 派发。
3. 正准备加载 improve-skills/create-skills？→ 除非入口声明「只做技能维护」，否则**停**并回 U1。
4. 阶段计划（下一阶段 + 派发形态）已写出？否 → 先写再派发。

### 常见误路由（入口 → 正确路由）

- 本技能名 + 功能/改进描述 → SDD 阶段链（目标可为本仓库）；禁止直接改代码或改走 improve-skills。
- 本技能名 + 明确「只改技能文档/不走 SDD」→ 技能维护路径；不得强制派发阶段。
- 纯提问/咨询 → 回答并停；不自动启动循环。

### Invoked-from-Team Entry（团队内调用入口）

除独立入口外，本手册支持**被团队席位调用**的入口形态：一个已获有效授权的成员席位，为其一条职责启动**恰好一次**有界嵌套运行。该形态**接受的输入恰为六项、且集合封闭**——多出的事实不得被静默忽略，缺任一项即拒绝：

| 事实 | 含义 |
|------|------|
| `goal_ref` | 绑定的 Goal 引用（必填） |
| `target_ref` | 可选的 Target 引用；缺省 = 对绑定 Goal 整体运行 |
| `team_slug` | 发起调用的团队 slug（授权坐标之一） |
| `seat_slug` | 发起调用的席位 slug（授权坐标之一） |
| `scope` | 授权的工件 / 领域范围 |
| `verdict_ref` | 路由裁决记录的引用（其裁决必须是 SDD 值） |

**U0 之前完成校验**：六项事实在写出 U0 入口声明**之前**全部校验；任一不通过即**拒绝启动并点名失败条件**，不把职责改写到能通过的形状，也不进入 U0。有效授权谓词（Agent 定义能力 AND 席位策略，按 (team, seat) 解析）的可执行形态是 `python3 .specify/scripts/python/sdd-route.py --action authorize`——提示词改词修不好一次拒绝。

**止于 review，不主张合并权**：嵌套运行在驱动既有 review 修复循环收束后结束，交回结构化 handoff；它**不进入 merge 步**，也不主张属于**外层**的合并权——集成由外层按其既有确认门处置。

校验表、handoff schema、写线登记、失败与卡死交回、消费方义务的**唯一落点**是 `references/nested-invocation.md`；本节只声明入口形态与上述三条边界，不复述其表。独立入口（本文件其余各节的形态与骨架）逐字不变——本入口是**追加**，不是替换。

## The Loop (U0–U6)

**Stage chain (test-pinned literal; owner: `.specify/shared/declarations/facts/driver-stage-sequence.yaml#/statement`)**: requirements → clarify → plan → tasks → checklist → analyze → implement → review

```text
U0 ENTRY     一遍性入口：目标、线、断点（或"探测"）、终态权威文档
U1 PROBE     每线：断点探测（git 分支 + 近期提交 + specs 目录 + 终态文档）判定续跑阶段
U2 DISPATCH  本地：fork 承载逐阶段派发（同族 qodercli 子进程经 .specify/scripts/stage-runner.sh；异构 agent 用 subprocess 承载）；远端：写 prompt + runner 后台派发（配方见 references/dispatch-recipes.md）
U3 WATCH     统一监听：单次调用内长轮询信号（退出记录/哨兵/PID/心跳）至终止判定或窗口到期；fork 子进程与远端 runner 同规；窗口到期只返回 RUNNING 并立即以递增 --iter 重入，只有阶段 deadline 产生 TIMEOUT（见 references/watch-model.md）
U4 VERIFY    独立校验：哨兵（必要）+ 产物核验 + 纪律抽查 + Wrap-up 记账核验（充分）→ 通过才续环
U5 STALL     超时/重试上限/预算触顶 → 停线、状态脊落盘、出上送件（绝不静默等待）
U6 LEAVE     全线收束：逐线合并收尾（closure/merge 步在**特性线闭合**处跑 `.specify/scripts/python/closure-acceptance-check.py`，`block` 把该线标 `blocked`——线不是也不得再是 `completed`；**split 线**——存在 `merge.status=merged` 的合并清单或分片目录——在合并收尾前 MUST 经 `/speckit.seal` 完成 merge-back、分片归档与终态判定，seal 的终态记录即该线终态；非 split 线沿用 review 门判定）+ 工作树归档清扫，缺省本地合并 + 一份收尾汇总
```

多条线并行 = 多个独立循环实例：一线一连接、一线一状态脊。首次派发前登记环境级 Line Registry（`.specify/scripts/line-registry.py --action register`），事件携带 `(line_id, run_id)` 信封，U6 后 `deregister`；无标识消息经 `resolve-message` 判定，禁止进程扫描推断。

U0 的产物是入口声明（目标/拓扑/权威/切片/断点）与阶段计划；未产出前不得进入 U2，更不得直接编辑目标仓库。

**Split closure（U6 子步，无人值守同规）**：U6 收尾前先判定本线是否 split 线——判定输入 = 该 spec 的合并清单（`merge.status=merged` 且 `slices[]` 非空）或父 spec 下已存在的分片目录；命中即 MUST 派发**一次**有界 `/speckit.seal` 执行（技能 `seal-artifact`；承载与阶段派发同规，见 `references/dispatch-recipes.md` Recipe 8），按引擎顺序完成 merge-plan → merge-apply（未合并时）→ archive-plan → archive-apply → seal 判定。完成判据：`seal.md` 回执存在、归档清单与引用台账齐备、终态裁决**逐字**回报；`Sealed` 与「具名阻断」都是合法终态，驱动 MUST NOT 改写、降级或重判；seal 以拒绝/错误退出时按其输出逐条上送，MUST NOT 绕过引擎改写状态面。该子步不改阶段链（seal 是收尾动作，不是阶段）、不改哨兵判定与 U4 规则；非 split 线不派发、不写任何 seal 产物。

**Qoder Desktop host adapter**: when the driver itself runs inside the Qoder
Desktop app, every headless `qodercli` child must be launched through the
desktop adapter that unsets the four `QODER_AGENT_SDK_*` / `QODER_SDK_*`
variables, otherwise `-p` exits immediately with `sdk_invalid_args`. Wrapper,
variable list and observed 1.1.76 facts: `references/cli/qodercli.md`
§ "Qoder Desktop Host Adapter"; dispatch form: `references/dispatch-recipes.md`
§ Recipe 5 "Qoder 桌面宿主变体".

### Hook completion backstop（Qoder CLI）

Hook 只是提前完成信号（`--settings` 注入、写 done/FIFO、`hook=observed`），完成仍由退出记录 + 哨兵判定；SSH 长读与故障矩阵见 `references/watch-model.md` §12–§13。

## Hard Requirements

1. **自迭代**：U4 通过后立即派发下一阶段（U2），不等用户任何形式的「继续」。
2. **独立校验**：阶段完成判定不由执行者自报——校验者不是该阶段执行子代理；哨兵在而产物缺 = 伪完成，判未完成；阶段 Wrap-up 记账缺失（且未返回 `WRAPUP-DEFERRED`）同样按伪完成判未完成（记账核验归 `references/stage-prompts.md` § Independent Verification）。
3. **卡死处置**：达重试上限（缺省 3 次）或阶段超时（缺省 180 分钟）→ 停环、落状态脊、出上送件四要素（发现了什么 / 为何吃重 / 已产生的中间产物逐项可定位 / 可选处置）。
4. **状态脊**：每线状态文件在 U2 派发前、U3 终止判定时、U4 校验后、U5 停线时先写后动；续环与重入只认状态脊，不依赖会话记忆。
5. **驱动者生命周期**：U3 是当前运行内的有界等待（进程承载用窗口——fork 子进程与远端 runner 同规；见 `references/watch-model.md`），驱动者必须存活到全线收束或显式停线上送；独立 `sleep` 回合与「挂监视器后等通知/恢复」均不合法——除非宿主已被探针证明能自动恢复同一运行。确须结束时，唯一合法路径是把状态脊写为 stalled/reentry-required 并显式上报。
6. **驱动拓扑**：加载者即驱动者，亲自执行 U0–U6；阶段子代理只收三段骨架提示词；本地拓扑的阶段派发用 **fork 承载**（同族 `qodercli` 子进程经 `.specify/scripts/stage-runner.sh`）或 **subprocess 承载**（异构 agent 自身 CLI 的独立子进程），宿主内建 in-process subagent 路径 **BANNED**、不作为并发承载；远端用外部 CLI；反嵌套义务真源在 run-agent 派发治理，本手册于 U2 派发前自检。
7. **流程不可替换**：U0/U1 与阶段计划写出前禁止直接编辑目标仓库；禁止用 improve-skills/create-skills 等维护路径替代 SDD 阶段链（目标为本仓库时同样适用）。唯一例外：入口显式声明「只做技能维护、不走 SDD」。
8. **快照只读**：`.specify/scripts/loop-state.py` 的 snapshot 只读——MUST NOT 写状态脊、四件套、Registry 或工作树（唯一写路径是显式 `--out`，且落在 state dir / repo 内一律拒绝），MUST NOT 杀进程、删证据或移除 worktree；`stop` 在 065a 只是建议。字段面与检测读法 owner 是 `references/state-awareness.md`。
9. **监听签名唯一**：每个监听窗口的 Shell 调用 MUST 在命令文本中携带字面量迭代标识——watcher 用 `--iter "<run_id>-w<NN>"`，hook 长读传第 6 个参数——`NN` 逐窗口递增，连续两次监听命令不得字节相同。令牌必须写成字面量，不能用 `$(date +%s)`/`$$`/`$RANDOM` 之类运行时展开：宿主（Qoder）在执行前比较签名，同参数连续调用会被判为重复并误报卡死。规则 owner 与重入续号：`references/watch-model.md` §3.2。
10. **目标项目治理优先（本地与远端同规）**：对目标仓库的任何写动作或目录创建之前，MUST 先读取并遵守目标项目的治理文档——宪法（constitution）与指令（instructions），包括其中的原则、目录规范、命名规则与临时目录纪律；与目标项目既有文档冲突时以目标项目为准。经 ssh 的远端目标同规——远端目录创建同样受目标项目治理约束。目标项目尚无治理框架时委托 sdd-project-setup，不得以本技能的缺省形态替代目标治理。文件清单与兼容符号链接见 References。
11. **运行期目录唯一**：目标仓 `.specify/` 命名空间是本技能唯一合法落点。临时数据（worktree、cache、tmp）走 `<repo>/.specify/.tmp/sdd-loop/{worktrees,cache,tmp}/<line_id>`，由 `.specify/.gitignore` 的 `.tmp/` 规则覆盖、工作项结束时清理；长期状态（状态脊）走 `<repo>/.specify/state/<line_id>.md`，按 line 一文一件、不随工作项清理（入口显式 `--state-dir` 时以入口为准）。布局 owner：`.specify/scripts/line-registry.py` 与 `references/dispatch-recipes.md`；Line Registry 仍缺省在 `$XDG_STATE_HOME/spec-kit/lines/` 或 `~/.local/state/spec-kit/lines/`（环境级，仓库外）。这两类落点由本技能独占；MUST NOT 使用 `.spec-kit/` 或任何其它仓库内 ad-hoc 目录（`tmp/`、`scratch/`、`state/`、`work/` 等）。首次写入前必须完成忽略状态确认（`git check-ignore -q .specify/.tmp`；缺失则先补规则）；目标项目自己的目录治理文档存在时，以目标项目为准。
12. **嵌套运行是一条写线、且不主张合并权**：被团队席位调用时（§ Invoked-from-Team Entry），本次运行作为**一条写线**注册到既有 line registry 与 worktree-per-write-line（`.specify/scripts/line-registry.py`）；领域重叠由该机制串行化或拒绝，MUST NOT 新建第二套 registry / ownership 模型 / integration queue。运行止于 review 并交回 handoff：MUST NOT merge、MUST NOT push——集成归外层按其确认门处置。
13. **类别感知（只换算子与槽位内容）**：阶段派发载荷 MUST 携带类别**四元组**（`flow_class=` / `source=` / `marker=` / `error=`；值域、缺键处置与派发纪律归 `references/stage-prompts.md` § 类别四元组的派发纪律），fork 承载（本地同族 `qodercli` 子进程）与远端 CLI 同规，subprocess 承载（异构 agent）同规；缺任一键即**派发构造缺陷**，U4 不放行。U4 对表达类 MUST 校验门禁证据——算子结果齐备、证据文件存在且非空、载荷与当场解析一致、`stage-status` 在行（校验程序归 `references/stage-prompts.md` § Independent Verification）；载荷 `error` 位非 `-`（即 `owner-unavailable`）时 MUST 走 `owner-unavailable` 分支——记降级观测、保持既有门禁集，MUST NOT 按表达类校验。预算槽位装什么归 `references/efficiency-model.md` §2.8（`selection_basis=docs-gate-full`），时点与槽位数不变。驱动 MUST NOT 因类别改变阶段序列、哨兵字面量、watcher 判定与退出码、卡死处置、快车道判据或 analyze / review 调用率（两者保持 100%）；任何以「本线属表达类」为由跳过或缩短阶段的请求被拒。类别只改变两件事：用哪套算子证明同一不变量、预算槽位里装什么。

14. **方向审计（Direction audit）**：每个检查点 MUST 包含五问方向审计（owner：`references/checkpoint-protocol.md` § Direction audit）；驱动 MUST 按 T0/T1/T2 分层重载方向契约与 Hard Requirements（T0 每检查点、T1 每阶段边界/轮次上限/压缩后、T2 仅在派发形态不清或处置卡死时），审计判定只有 `on-track` / `correction-applied` / `decision-needed` 三值，结论是陈述、MUST NOT 以征求用户「继续」收尾（HR1）。
## Discipline Defaults

阶段提示词骨架第二段把默认纪律写进每次派发（全文见 references/stage-prompts.md）：直接执行不要确认、访谈式问题自行裁决并记录假设、只提交本特性产物、既有脏文件不提交不还原、不要 push（除非明确授权）。

## Efficiency Optimizations（运行效率优化）

七项优化（owner：`references/efficiency-model.md`）：

1. **快车道**：仅入口 `fast-lane=opt-in` 时在 tasks 后按七项机械判据裁决；失效即回退完整链。
2. **两槽位测试预算**：每线仅 implement 起点与 review 后两次全量，其余用定向集留证。
3. **Plan 只小修**：`PLAN-EDIT:` 声明；实质改动按两分支处置。
4. **进度与脱离**：runner 默认 stream-json + live log；本地与远端均脱离，`--once` 只核验不重派。
5. **大特性拆分门**：plan 入口 >120 FR 或 tasks U4 >160 任务判 `split-required`。
6. **确定性预检**：requirements/plan/tasks 的 U4 先跑 `pre-analyze-check.py`。
7. **跨特性重叠预检**：clarify U4 跑 `overlap-check.py`，先裁决归属再派发 plan。

新增脚本与领域细则见 `references/efficiency-model.md` §5–§7 与 References。

## Task Decomposition & Team Coordination（任务拆解与配合）

驱动者在 `plan` / `implement` / `review` 阶段缺省进入**任务拆解层**：从阶段权威产物派生有界 Work Package，先过确定性门，再按图调度（只读并发、写包独占）、独立校验、确定性集成；阶段哨兵与 U4 不变。运行时 owner 是 `references/decomposition-model.md`（§1–§21）；设计权威是 070 的 contracts 与 data-model，本节只给入口与指针，不复述规则。

- **入口**：每阶段的决策写入 plan fence（状态脊）——`decomposed` / `single-package` / `disabled` / `fallback`；plan fence 是唯一决策记录，ledger `plan` 事件按 `plan_hash` 引用它。
- **何时拆解**：`auto` 仅在门返回 `admit`、至少两个包且 WG-13 收益测试成立时拆解；否则 `single-package`（`reason=not-beneficial`）。不可表示、门在唯一一次修复后仍拒绝、或拆解层不可用（exit 2）→ `fallback`，具名原因，且绝不运行部分包集。
- **门**：`.specify/scripts/wp-gate.py --check plan|preflight|retry`——确定性、stdlib-only、不派发、不写脊；拒绝码与退出码以 §12 和 `contracts/wp-gate.md` 为准。
- **调度**：§13——依赖验证后才就绪、写包独占、只读并发受 `slot_cap` 限制、失败隔离、重入不重派。
- **先划分后派发（C-073）**：协调者 MUST 先产出包集再派发——每个包命名其范围、输入与输出路径；派发临时包（ad hoc packages）即 `unpartitioned`。协调者自身工具集缺派发能力时，该包集仍是可用的交付物（后到的可派发执行者无需重新推导）。
- **真实执行形态（C-074）**：协调者 MUST 报告实际达成的执行形态，即使它是串行——「划分就绪、执行串行」是具名披露（附理由码），MUST NOT 沉默；不得把串行运行呈现为并发。
- **能力裁决与槽位上限逐次下传（C-071）**：每次派发 MUST 携带当次读出的能力裁决与槽位上限；一次派发 MUST NOT 继承上一次派发的读数；本规则只加派发载荷，不改任何步骤顺序。
- **逐阶段覆盖与逐单元读数（C-069/C-070）**：每个循环阶段 MUST 声明自己的拆解覆盖，MUST NOT 继承上一阶段的覆盖；读数按**推进单元**记录——driver 按阶段/包、`sdd-house-keeping` 按条目、`sdd-project-setup` 按步骤，MUST NOT 写成「每轮」。
- **独立校验**：§15——每包一个全新上下文 verifier；verdict 缺失/不可读/歧义即 fail；包 verdict 永远不替代阶段 U4。
- **集成与收尾**：§16——按声明顺序确定性集成，冲突或缺失输出即停，单一 closing commit，阶段哨兵由 integrator 发出；U4 在集成后原样运行。
- **团队形状**：`.specify/templates/stage-team-preset.md` + 运行域 adapter（§17）；每 stage / attempt / run 都不持久化 `team.md`，`create-team` / `run-team` 不变。
- **Checkpoint 协议（085）**：每阶段 U4 后、下一阶段派发前执行四步 checkpoint（产物核验 / Goal 进度 / 至多一条 team 配置提案 / 下一阶段并发与 roster），写 `<spec-dir>/checkpoints/<NN>-<stage>.md`；owner `references/checkpoint-protocol.md`，本节只给指针。
- **报表**：`.specify/scripts/wp-report.py`（§18）；缺失来源一律 `not_evaluated`，绝不以 0 或估计替代。
- **退出开关**：U0 声明 `decomposition: auto|off`、`decomposition_stages`、`decomposition_slot_cap`（缺省值读 `.specify/shared/declarations/facts/concurrency-slot-and-reserve.yaml` 的 `slot_cap_default`——本手册不写数字；状态脊三键是该 fact 的运行期投影）；阶段 attempt 可带 `decomposition_override`。优先级：feature `off`（硬退出）> 阶段 override > 阶段表 > `.specify/shared/declarations/facts/decomposition-coverage.yaml`（`decomposition-coverage`，内置缺省的唯一 owner——本手册不复述各阶段取值）。
- **analyze 缺省并发（FR-034）**：`analyze` 阶段按 `decomposition-coverage.yaml` 的 `analyze: on` 默认以 **N 个并发 SDD Analysis Worker**（`agents/sdd-analysis-worker.agent.md`）执行，N 取自阶段团队配置 / 状态脊 `agent_concurrency_requested`，本手册不固化数字；串行 analyze（N=1）只在 `serial-reason.yaml` 的封闭词表给出具名理由码时成立。三件事与并发同时成立，缺任一项判红：(a) 每个 Worker 的**读域**在派发前声明为**文件级**路径集，同一路径出现在两个并发 Worker 的读域里（读域相交）即**派发前判红**；(b) N 份 findings 按确定性规则归并——先按声明的读域次序分节，节内按 finding id 字典序，跨 Worker 重复 id 按「先声明先得」破平并保留指向被抑制副本的指针，MUST NOT 依赖返回时刻；(c) 记录 `requested` / `effective` / `effective_reason` 三元组（effective 取逐 Worker 派发/返回区间最大重叠数）＋ 每 Worker 的 `executor_id` 与其 verdict 的 `verifier_id`；(d) **增量复检的派发义务**：第 N+1 轮按 `.specify/skills/internal/analyze-artifacts/SKILL.md` § Rounds 的 Incremental re-check protocol 派发——载荷 MUST 携带 touched-loci 集与 reused-domain 哈希清单，未触碰域的复用 MUST 落盘具名；验证者仍逐条 fresh-context，复用只作用于检测域；确定性门全量复跑兜底；该 owner 拥有回退到全量重检的全部判据；(e) **域与输出预算**：域按预期发现量在派发前预切（上限归 analyze-artifacts § Domain and output budget 所有），输出预算随派发载荷下传；worker 返回 output-limit / 截断 findings / 读域不匹配即未完成单元，按文件重切重派，MUST NOT 整域重试或以部分 findings 合成。承载形态见 `references/dispatch-recipes.md` § 本地原生拓扑（fork / subprocess 两类进程承载，in-process 路径 BANNED）。
- **implement 并发切包**：implement 阶段 MUST 按 **~10 任务/包（每包 ≤16）** 切分，并发上限 = 运行期槽位上限（读 `concurrency-slot-and-reserve.yaml` 的 `slot_cap_default` 并与天花板取 min；本手册不写数字；依赖与写域由 decomposition §13 调度）；多个写包时声明 `write_isolation=worktree`，写 agent 各占 child line + 独立 worktree，集成按 §16 交给既有 integration queue 串行合入。禁止把 60+ 任务压在一个执行子代理里。
- **边界**：只新增 U4 之前的步骤；不改阶段命令内部、哨兵字面量、U4、阶段链、watcher 判定/退出码、卡死处置、快车道、两槽位测试预算、plan 小修约束，以及 064 的 registry/ownership/worktree/integration 语义、067 的 part brief/test economics、068 的反馈通道。包执行者绝不派发、绝不写脊、绝不加载本手册；不新增服务/守护进程或第二个 registry、ownership 模型、integration queue、ledger。

## References

- **框架声明层（本手册引用的两条取值）**——阶段序列 `.specify/shared/declarations/facts/driver-stage-sequence.yaml#/statement`、完成哨兵 `.specify/shared/declarations/facts/driver-completion-sentinels.yaml#/statement`：两条取值由声明单一拥有，引擎经 `.specify/scripts/loop-state.py` 的共享读取入口读取，本手册与 `references/` 各文件只引用路径，不复述取值。
- `references/dispatch-recipes.md` — 五大执行机制、阶段链与哨兵、hook/SSH 窗口、线路登记。
- `references/watch-model.md` — 统一监听模型：信号源、判定状态机、窗口/期限、多线 manifest、hook/SSH 与故障矩阵。
- `references/state-awareness.md` — 状态感知快照 owner：入口与调用形态、六类检测与两类保留形态、§Derived Mapping（镜像 FR-004）、§Stage Artifact Map、probe 契约、动作建议与 watchbeat 读法；本手册与其它 references 只引用其章节，不复述整表。
- `references/stage-prompts.md` — 三段骨架、独立校验、Line/Envelope/Ingress、重接线、变体、并发隔离、卡死处置。
- `references/nested-invocation.md` — 团队内调用入口的完整契约：入口校验表、handoff schema（字段集封闭、三值 outcome、集成身份四事实）、写线登记、失败与卡死交回、消费方义务。
- `.specify/scripts/loop-state.py` — 只读快照引擎（`snapshot` / `--probe` / `--self-test`；`recover`、`check-spine` 返回结构化拒绝），字段面与退出码契约见 `references/state-awareness.md`。
- `.specify/scripts/watch-target.sh` — 长轮询 watcher 参考实现（快照、归属过滤、hook、lease、逐窗口 `--iter` 迭代标识）。
- `.specify/scripts/hook-stop.sh` / `watch-hook.sh` — Stop hook 模板与远端同身份长读。
- `.specify/scripts/line-registry.py` — 环境级 Registry、原子写/同线锁、信封分类、消息入口、集成队列。
- `.specify/scripts/decomposition-check.py` / `pre-analyze-check.py` / `overlap-check.py` — 三个确定性门（owner：efficiency-model §5–§7）。
- `references/observer-lifecycle.md` — 观察者派发简报模板、引擎调用循环、缺口与失败语义；生命周期条款与记录节形状的 owner 是本文件 § SDD Observer。
- **目标项目治理文档**（运行时读取，经 ssh 同样适用）：目标项目的 `constitution`（`.specify/constitution.md`）与 `instructions`（`.specify/instructions.md`，含 `AGENTS.md` / `QODER.md` / `CLAUDE.md` 兼容符号链接）；两者不随本技能分发，缺失时按 Hard Requirement 10 处置。

## Boundary

- 合并/push 维持确认门控破坏性分类：缺省本地合并；push 须经入口显式授权。
- 阶段命令为不透明单元：不改各 `/speckit.*` 命令内部流程。
- 不绑定特定项目族或工作区命名规则：别名、用户、路径、CLI、断点阶段全部入口参数化。
- 同仓多写线：worktree-per-write-line + Ownership Manifest + 确定性集成队列；规则见 `references/dispatch-recipes.md` Recipe 7 与 `references/stage-prompts.md` Concurrency Isolation。worktree 仅在合并成功后移除。
- 目标项目未安装 spec-kit（无 `.specify/`）时：**委托 sdd-project-setup** 做 bootstrap（本技能不执行初始化）；bootstrap 返回 `maintenance-pending` 时，再**委托 sdd-house-keeping H1–H4** 做首次维护，取得 ready 凭证后重入循环。

## Subagent Create & Dispatch Delegation（子代理创建与派发委派）

本手册是**编排者**：它不自带派发机制，而是委派两个承接技能完成驱动子代理的任务（2026-10-16 委派化裁定）：

- **实例创建 → create-agent**（`.specify/skills/internal/create-agent/SKILL.md`）：从 `agents/sdd-<stage>-<role>.agent.md` 角色族（如 `sdd-requirement-analyzer`、`sdd-plan-coordinator`、`sdd-plan-executor`）按职责实例化阶段执行实例（一实例一职责）；产出=`.specify/agents/instances/<slug>.agent.md`。
- **阶段派发 → run-agent**（`.specify/skills/internal/run-agent/SKILL.md`）：本地拓扑的阶段派发用 **fork 承载**（同族 `qodercli` 子进程经 `.specify/scripts/stage-runner.sh`）或 **subprocess 承载**（异构 agent 自身 CLI 的独立子进程），宿主内建 in-process subagent 路径 **BANNED**、不作为并发承载；远端拓扑用外部 CLI；远端进入形态为 `ssh <alias>` → `su - <run-user>` → `cd <project-dir>`，CLI 缺省取 execution-config defaults（`cli: qodercli`），可按 agent/inline 覆盖；以拓扑声明 + 实例引用发起执行；前置检查与失败处置见其 `references/dispatch-preflight.md`。
- **编排本体在本手册**：阶段序列（U0–U6）、状态脊、哨兵与独立校验、卡死处置、收尾合并不由承接技能承担（职责切分见 agent-definitions § Driving Subagents via the Three Layers）。
- **阶段子代理预算**：统一 `run-turn-budget` 500（owner：阶段执行角色族 `agents/sdd-<stage>-<role>.agent.md`；2026-11-06 统一）；大 implement 阶段按 **~10 任务/包（每包 ≤16）** 切分、并发上限取运行期槽位上限（读 slot fact，本手册不写数字）；多个写包用 `write_isolation=worktree`（child line + 独立 worktree），集成队列串行合入；细则见 `references/dispatch-recipes.md` § 阶段子代理预算与分段。

## Feedback & Probe Points（反馈与探针采集点）

本技能频繁驱动完整 SDD 流程，是 speckit 框架摩擦的最佳观察者——框架级观察 MUST 有落点，MUST NOT 随收尾汇总蒸发。三个采集点（本技能不加新采集机器——状态脊、收尾汇总与既有引擎就是载体，IX）：

1. **每线观察点（U4/U6）**：独立校验与收尾时，把观察到的 **speckit 框架级摩擦**记入该线状态脊的「框架观察」段——结构化三要素：现象 / 框架位置（哪个阶段命令、模板、命令面）/ 对驱动的影响。范围限框架本身（阶段命令行为、模板缺口、哨兵与校验误报）；目标项目的业务问题不属此类。
2. **收尾落库点（U6）**：收尾汇总携带「框架反馈候选」清单（自各线「框架观察」段聚合）。宿主具备规格库结构时逐条经 `feedback-utils.py --action record --unit-id "skill:sdd-loop-driver" --unit-type skill` 落库；standalone 时随汇总交付用户——**不自动上送**。
3. **skill 收尾点（run 结束）**：执行编译 `## Wrap-up` 节的五步引擎链（run determination → exec quant → feedback record → threshold notice → token reflection），按单执行。

## CLI Capability Profiles

`references/cli/` 是 CLI 行为知识的**唯一落点**；`references/cli/index.md` 是 schema 与观测程序的 owner。

- **派发前（U2）只读查档**：按目标 CLI 档案选择超时/脱离形态，派发记录写 `profile_id` / `profile_version` / `observed_cli_version`；匹配且无新事实不产生反馈。
- **U4/U5 观测后更新**：实际行为与 `known` 不符、`unknown` 获得已验证值、或新版本/平台行为首次出现时，先写状态脊 `cli_observations`，再更新档案 provenance，再记录恰好一条 `cli-profile:<cli>` 反馈；无新事实零反馈。
- **派发资格**：仍由 `CAPABILITY_MATRIX`（`.specify/scripts/python/execution-config.py`）**唯一**拥有；档案只记录观测，冲突时资格以矩阵为准。
- 档案更新不得改变哨兵、watcher 判定/退出码、确认门、阶段 deadline 或测试预算；当前阶段使用 U2 记录的形态。

## SDD Observer（观察者：启动、记录节与收束）

观察者是每条 driver 驱动的 SDD 线上的第三方记录者：它只记录载体上发生了什么，不参与推进、不评价、不建议、不推断。机制总量 = 一个专用实例、一份线级 journal（路径 `.specify/specs/<NNN-slug>/journal.md`）、若干有界执行窗口；不引入调度器、守护进程、第二注册表或第二状态面。派发简报、引擎调用与缺口/失败语义的 owner 是 `references/observer-lifecycle.md`；本节拥有生命周期条款与状态脊记录节的形状。

### 入口开关与启动时点

- U0 入口声明接受 `observer: on|off`，缺省 `on`。`off` 由 driver 写入状态脊观察者记录节（`state: disabled` + 原因），并在既有 U6 收束报告中披露——关闭是「已记录的未观测」，MUST NOT 表现为静默缺失。
- 启动时点：line 已登记且状态脊已建立之后、首个阶段的 U2 派发之前（首个阶段提示词发出前）。机械判据恰为：状态脊存在 + line 已登记 + U2 尚未派发。启动步骤属于 driver，MUST NOT 下放到任一 stage 命令内部。
- 启动尝试与结果（`started` / `failed` / `disabled`）由 driver 写入状态脊观察者记录节；失败附一行原因。

### 专用实例与身份

- 每条线恰好一个 Observer Instance（实例层），identity 由 `line_id` 与 spec key 派生；实例 slug 为 `sdd-observer-<line_id>`。一条线一个实例、多次执行复用；不同线 MUST NOT 共享实例或 journal。
- 实例由 driver 的启动步骤经既有 `create-agent` 委派创建；任一 stage 命令 MUST NOT 自行创建 observer 实例。
- observer MUST NOT 注册为写线（不属 `root` / `coordinator` / `agent-write` 封闭写角色集）、不占工作树、不进入集成队列。

### 状态脊观察者记录节（本节拥有形状）

driver 以追加式小节写入状态脊；小节只追加、latest wins，observer 自身 MUST NOT 写状态脊。键与顺序恰为：

```text
  ## Observer Record — <YYYY-MM-DDTHH:MM:SSZ>
  - state: started | failed | disabled | closed
  - line_id: <value>
  - run_id: <value>
  - spec: <NNN-slug>
  - instance: <instance slug>
  - execution_label: <label or ->
  - started_at: <UTC ISO-8601 or ->
  - reason: <one line or ->
```

### 有界执行与重启

- observer Execution 经既有 `run-agent` 派发落地；承载 MUST 是 external 模态的 fork（同族子进程经 `stage-runner.sh`）或 subprocess（异构 agent 自身 CLI 的子进程）；native 与 virtual 模态 MUST NOT 承载。执行 label 走既有三段约定 `<line_id>--<run_stamp>--observer`，可见性经既有 triplet 目录呈现（driver 以既有 `--sub-flow <label>=<triplet-dir>` 语义传入监督投影）。
- 每次执行是有界窗口：边界取既有派发 turn budget 与阶段 deadline，不引入新定时器。同一线同一时刻至多一个未结算执行：上一个 `.status` 未结算时 driver MUST NOT 派发下一个；journal 引擎以单写者 flock 拒绝第二个并发 writer。
- 执行在线终止前结束（失败、停滞、窗口到期）时，driver MAY 在下一阶段边界从同一实例再次启动；重启追加同一 journal，并由引擎为未覆盖窗口写一条 `observer-gap`。重启 MUST NOT 改变任何阶段的重试次数、超时判定或完成哨兵判定。

### 线终态收束

- 最后一个声明阶段之后、外层收尾之前，driver 启动一次终态收束执行：经 `journal-utils.py --action append --final` 追加 `line-terminal` 与 `observer-settle`，并为仍开着的窗口写一条起止具名的 `observer-gap`。`state: closed` 由 driver 在收束执行结算后写入观察者记录节。
- 收束执行无法启动或失败时：driver 在观察者记录节记录 `state: failed` + 原因，U6 收束报告点名未闭合窗口的起止；journal MUST NOT 被改写成假闭合。

### 非阻塞（披露是唯一的收束义务）

- observer 的存在、缺失、健康、结论与 journal 内容 MUST NOT 成为任何阶段推进（U4）、checkpoint、review 或合并的门。
- 失败只做两件事：写入状态脊观察者记录节，并在既有 U6 收束报告披露。披露是唯一的收束义务；observer 不发出用户可见的汇报、提问或审批请求。
- observer 的可见性只经既有 supervision 投影呈现，MUST NOT 新增字段、行或小节。

### 适用范围

- 适用于 driver 驱动的 SDD 线，含团队内调用的嵌套运行：一条线一个 observer、一份 journal。嵌套运行拥有自己的 observer，内层 observer MUST NOT 观察外层团队运行。
- 非 SDD 的 `/speckit.*` 命令运行与不承载 SDD 线的 team 运行 MUST NOT 产生 observer 或 journal。

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:sdd-loop-driver" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:sdd-loop-driver" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:sdd-loop-driver" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
