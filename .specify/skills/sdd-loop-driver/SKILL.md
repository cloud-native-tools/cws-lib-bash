---
name: sdd-loop-driver
description: 无人值守 SDD 循环驱动手册——以一条一遍性提示词驱动主代理完成「登录环境 → 本地用宿主原生子代理 / 远端用 qodercli 为子代理 → 按阶段推进 SDD 完整流程（requirements → clarify → plan → tasks → checklist → analyze → implement → review）→ 合并 main」的完整闭环，全程循环自推进、零用户提醒。当用户说「使用SDD开发模式推动 <项目>」「无人值守推进」「sdd-loop-driver」「需要使用一个循环来完成这项工作，而不是每次由我提醒你重试或继续」时加载本手册。执行细节（断点探测 / 阶段化 prompt 文件 / runner 与派生 / 后台执行+统一监听 / 收尾纪律）全部由本手册承接，入口只声明目标与起点。当以本技能名给出功能/改进描述时，视为 SDD 目标（目标项目可为本技能自身所在仓库），先做 U0/U1 并走阶段链，不得就地改代码或切换为技能维护路径。
skill_id: "<SKILL:.specify/skills/sdd-loop-driver/SKILL.md>"
classification: external
---

> **分类注解**：本 skill 依**依赖轴**判定为 external——自身零 spec-kit 依赖、任何宿主 agent 可直接加载；内容编排 spec-kit 的 SDD 流程（语义耦合显式声明：指挥子代理执行 `/speckit.*`），不构成运行时依赖。

## What This Skill Does

把经多项目验证的「无人值守 SDD 驱动」固化为可执行手册：宿主 agent（无需安装 spec-kit）对每条项目线执行「断点探测 → 阶段派发 → 统一监听 → 独立校验 → 续环」，直到 review 完成并合并收尾。自迭代、独立校验、卡死处置三条硬需求内置于本手册；监听语义（等待/监控/轮询）的唯一权威落点是 `references/watch-model.md`。

**触发语义与路由**：以本技能名加载并给出功能/改进描述 = SDD 目标，目标项目可为任意仓库（含本技能自身仓库）；改进本技能也必须走 U0/U1 → 阶段链。仅入口显式声明「只做技能维护、不走 SDD」时，才允许 improve-skills/create-skills 维护路径。**主导流程唯一**：**加载后的第一个动作**是写出 U0 入口声明与阶段计划，在此之前不加载其他技能、不编辑文件、不派发 subagent。

**质量门完整**：checklist/analyze/review 在无人值守循环中一律必经、不可省略（编排见 dispatch-recipes.md Recipe 4）。与 sdd-project-setup / sdd-house-keeping **非强绑定、各自可独立运行**：框架 bootstrap 归 setup，周期性维护/记录回收归 house-keeping，阶段循环归本技能；候选清单仅建议，需确认后启动。

## Driver Topology（驱动拓扑——义务真源：run-agent 派发治理）

- **加载本手册的宿主 agent 就是驱动者**：U0–U6（探测/派发/轮询/校验/续环/收尾）由加载者在自己的会话亲自执行，不得委托任何 subagent；**自检**：若处于 subagent 上下文且被赋予「代为驱动循环」的任务，按显式异常行上报并停在前置阶段——嵌套驱动永不是合法形态。
- **流程不可替换**：不得用 improve-skills/create-skills 等维护路径替代 U0–U6（Hard Requirement 7）。
- **派发治理义务上收**：子代理提示词不引用/加载驱动技能、不含循环逻辑；义务全文与派发前拦截见 `.specify/skills/internal/run-agent/SKILL.md` 派发治理节与 subagent-definitions § Dispatch-Time Governance Obligation。
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
| 执行拓扑 | 未给 ssh 别名/run-user/远端路径 → **本地**（宿主原生子代理；阶段派发 MUST NOT 启动 qodercli，analyze 验证波例外见 `references/dispatch-recipes.md` § 本地原生拓扑）；给全 → 远端（外部 CLI）；只给 host 或三元组不完整 → 问一个澄清问题，不猜 |
| 终态权威文档 | 入口描述 + 现有 `docs/` + 宪法；写入 U0 状态脊 |
| 断点 | U1 自动探测，禁止猜测 |
| 特性切片 | 入口描述；未给则按权威文档推导，不自动选题 |

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

```text
U0 ENTRY     一遍性入口：目标、线、断点（或"探测"）、终态权威文档
U1 PROBE     每线：断点探测（git 分支 + 近期提交 + specs 目录 + 终态文档）判定续跑阶段
U2 DISPATCH  本地：原生子代理逐阶段派发（同步返回）；远端：写 prompt + runner 后台派发（配方见 references/dispatch-recipes.md）
U3 WATCH     远端统一监听：单次调用内长轮询信号（退出记录/哨兵/PID/心跳）至终止判定或窗口到期；窗口到期只返回 RUNNING 并立即以递增 --iter 重入，只有阶段 deadline 产生 TIMEOUT（本地原生调用即等待，不轮询；见 references/watch-model.md）
U4 VERIFY    独立校验：哨兵（必要）+ 产物核验 + 纪律抽查 + Wrap-up 记账核验（充分）→ 通过才续环
U5 STALL     超时/重试上限/预算触顶 → 停线、状态脊落盘、出上送件（绝不静默等待）
U6 LEAVE     全线收束：逐线合并收尾（git 状态判定 + 工作树归档清扫，缺省本地合并）+ 一份收尾汇总
```

多条线并行 = 多个独立循环实例：一线一连接、一线一状态脊。首次派发前登记环境级 Line Registry（`.specify/scripts/line-registry.py --action register`），事件携带 `(line_id, run_id)` 信封，U6 后 `deregister`；无标识消息经 `resolve-message` 判定，禁止进程扫描推断。

U0 的产物是入口声明（目标/拓扑/权威/切片/断点）与阶段计划；未产出前不得进入 U2，更不得直接编辑目标仓库。

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
3. **卡死处置**：达重试上限（缺省 2 次）或阶段超时（缺省 90 分钟）→ 停环、落状态脊、出上送件四要素（发现了什么 / 为何吃重 / 已产生的中间产物逐项可定位 / 可选处置）。
4. **状态脊**：每线状态文件在 U2 派发前、U3 终止判定时、U4 校验后、U5 停线时先写后动；续环与重入只认状态脊，不依赖会话记忆。
5. **驱动者生命周期**：U3 是当前运行内的有界等待（外部 CLI 用窗口；本地原生以一次同步调用为界，见 `references/watch-model.md`），驱动者必须存活到全线收束或显式停线上送；独立 `sleep` 回合与「挂监视器后等通知/恢复」均不合法——除非宿主已被探针证明能自动恢复同一运行。确须结束时，唯一合法路径是把状态脊写为 stalled/reentry-required 并显式上报。
6. **驱动拓扑**：加载者即驱动者，亲自执行 U0–U6；阶段子代理只收三段骨架提示词；本地拓扑的阶段派发用宿主原生子代理（MUST NOT 启动 qodercli），远端才用外部 CLI；反嵌套义务真源在 run-agent 派发治理，本手册于 U2 派发前自检。
7. **流程不可替换**：U0/U1 与阶段计划写出前禁止直接编辑目标仓库；禁止用 improve-skills/create-skills 等维护路径替代 SDD 阶段链（目标为本仓库时同样适用）。唯一例外：入口显式声明「只做技能维护、不走 SDD」。
8. **快照只读**：`.specify/scripts/loop-state.py` 的 snapshot 只读——MUST NOT 写状态脊、四件套、Registry 或工作树（唯一写路径是显式 `--out`，且落在 state dir / repo 内一律拒绝），MUST NOT 杀进程、删证据或移除 worktree；`stop` 在 065a 只是建议。字段面与检测读法 owner 是 `references/state-awareness.md`。
9. **监听签名唯一**：每个监听窗口的 Shell 调用 MUST 在命令文本中携带字面量迭代标识——watcher 用 `--iter "<run_id>-w<NN>"`，hook 长读传第 6 个参数——`NN` 逐窗口递增，连续两次监听命令不得字节相同。令牌必须写成字面量，不能用 `$(date +%s)`/`$$`/`$RANDOM` 之类运行时展开：宿主（Qoder）在执行前比较签名，同参数连续调用会被判为重复并误报卡死。规则 owner 与重入续号：`references/watch-model.md` §3.2。
10. **目标项目治理优先（本地与远端同规）**：对目标仓库的任何写动作或目录创建之前，MUST 先读取并遵守目标项目的治理文档——宪法（constitution）与指令（instructions），包括其中的原则、目录规范、命名规则与临时目录纪律；与目标项目既有文档冲突时以目标项目为准。经 ssh 的远端目标同规——远端目录创建同样受目标项目治理约束。目标项目尚无治理框架时委托 sdd-project-setup，不得以本技能的缺省形态替代目标治理。文件清单与兼容符号链接见 References。
11. **运行期目录唯一**：目标仓 `.specify/` 命名空间是本技能唯一合法落点。临时数据（worktree、cache、tmp）走 `<repo>/.specify/.tmp/sdd-loop/{worktrees,cache,tmp}/<line_id>`，由 `.specify/.gitignore` 的 `.tmp/` 规则覆盖、工作项结束时清理；长期状态（状态脊）走 `<repo>/.specify/state/<line_id>.md`，按 line 一文一件、不随工作项清理（入口显式 `--state-dir` 时以入口为准）。布局 owner：`.specify/scripts/line-registry.py` 与 `references/dispatch-recipes.md`；Line Registry 仍缺省在 `$XDG_STATE_HOME/spec-kit/lines/` 或 `~/.local/state/spec-kit/lines/`（环境级，仓库外）。这两类落点由本技能独占；MUST NOT 使用 `.spec-kit/` 或任何其它仓库内 ad-hoc 目录（`tmp/`、`scratch/`、`state/`、`work/` 等）。首次写入前必须完成忽略状态确认（`git check-ignore -q .specify/.tmp`；缺失则先补规则）；目标项目自己的目录治理文档存在时，以目标项目为准。
12. **嵌套运行是一条写线、且不主张合并权**：被团队席位调用时（§ Invoked-from-Team Entry），本次运行作为**一条写线**注册到既有 line registry 与 worktree-per-write-line（`.specify/scripts/line-registry.py`）；领域重叠由该机制串行化或拒绝，MUST NOT 新建第二套 registry / ownership 模型 / integration queue。运行止于 review 并交回 handoff：MUST NOT merge、MUST NOT push——集成归外层按其确认门处置。

## Discipline Defaults

阶段提示词骨架第二段把默认纪律写进每次派发（全文见 references/stage-prompts.md）：直接执行不要确认、访谈式问题自行裁决并记录假设、只提交本特性产物、既有脏文件不提交不还原、不要 push（除非明确授权）。

## Efficiency Optimizations（运行效率优化）

七项优化（owner：`references/efficiency-model.md`）：

1. **快车道**：仅入口 `fast-lane=opt-in` 时在 tasks 后按七项机械判据裁决；失效即回退完整链。
2. **两槽位测试预算**：每线仅 implement 起点与 review 后两次全量，其余用定向集留证。
3. **Plan 只小修**：`PLAN-EDIT:` 声明；实质改动按两分支处置。
4. **进度与脱离**：runner 默认 stream-json + live log；本地与远端均脱离，`--once` 只核验不重派。
5. **大特性拆分门**：plan 入口 >30 FR 或 tasks U4 >40 任务判 `split-required`。
6. **确定性预检**：requirements/plan/tasks 的 U4 先跑 `pre-analyze-check.py`。
7. **跨特性重叠预检**：clarify U4 跑 `overlap-check.py`，先裁决归属再派发 plan。

新增脚本与领域细则见 `references/efficiency-model.md` §5–§7 与 References。

## Task Decomposition & Team Coordination（任务拆解与配合）

驱动者在 `plan` / `implement` / `review` 阶段缺省进入**任务拆解层**：从阶段权威产物派生有界 Work Package，先过确定性门，再按图调度（只读并发、写包独占）、独立校验、确定性集成；阶段哨兵与 U4 不变。运行时 owner 是 `references/decomposition-model.md`（§1–§21）；设计权威是 070 的 contracts 与 data-model，本节只给入口与指针，不复述规则。

- **入口**：每阶段的决策写入 plan fence（状态脊）——`decomposed` / `single-package` / `disabled` / `fallback`；plan fence 是唯一决策记录，ledger `plan` 事件按 `plan_hash` 引用它。
- **何时拆解**：`auto` 仅在门返回 `admit`、至少两个包且 WG-13 收益测试成立时拆解；否则 `single-package`（`reason=not-beneficial`）。不可表示、门在唯一一次修复后仍拒绝、或拆解层不可用（exit 2）→ `fallback`，具名原因，且绝不运行部分包集。
- **门**：`.specify/scripts/wp-gate.py --check plan|preflight|retry`——确定性、stdlib-only、不派发、不写脊；拒绝码与退出码以 §12 和 `contracts/wp-gate.md` 为准。
- **调度**：§13——依赖验证后才就绪、写包独占、只读并发受 `slot_cap` 限制、失败隔离、重入不重派。
- **独立校验**：§15——每包一个全新上下文 verifier；verdict 缺失/不可读/歧义即 fail；包 verdict 永远不替代阶段 U4。
- **集成与收尾**：§16——按声明顺序确定性集成，冲突或缺失输出即停，单一 closing commit，阶段哨兵由 integrator 发出；U4 在集成后原样运行。
- **团队形状**：`.specify/templates/stage-team-preset.md` + 运行域 adapter（§17）；每 stage / attempt / run 都不持久化 `team.md`，`create-team` / `run-team` 不变。
- **报表**：`.specify/scripts/wp-report.py`（§18）；缺失来源一律 `not_evaluated`，绝不以 0 或估计替代。
- **退出开关**：U0 声明 `decomposition: auto|off`、`decomposition_stages`、`decomposition_slot_cap`（缺省 2）；阶段 attempt 可带 `decomposition_override`。优先级：feature `off`（硬退出）> 阶段 override > 阶段表 > 内置缺省（`plan`/`implement`/`review`=auto，其余 off）。
- **边界**：只新增 U4 之前的步骤；不改阶段命令内部、哨兵字面量、U4、阶段链、watcher 判定/退出码、卡死处置、快车道、两槽位测试预算、plan 小修约束，以及 064 的 registry/ownership/worktree/integration 语义、067 的 part brief/test economics、068 的反馈通道。包执行者绝不派发、绝不写脊、绝不加载本手册；不新增服务/守护进程或第二个 registry、ownership 模型、integration queue、ledger。

## References

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
- **目标项目治理文档**（运行时读取，经 ssh 同样适用）：目标项目的 `constitution`（`.specify/memory/constitution.md`）与 `instructions`（`.specify/instructions.md`，含 `AGENTS.md` / `QODER.md` / `CLAUDE.md` 兼容符号链接）；两者不随本技能分发，缺失时按 Hard Requirement 10 处置。

## Boundary

- 合并/push 维持确认门控破坏性分类：缺省本地合并；push 须经入口显式授权。
- 阶段命令为不透明单元：不改各 `/speckit.*` 命令内部流程。
- 不绑定特定项目族或工作区命名规则：别名、用户、路径、CLI、断点阶段全部入口参数化。
- 同仓多写线：worktree-per-write-line + Ownership Manifest + 确定性集成队列；规则见 `references/dispatch-recipes.md` Recipe 7 与 `references/stage-prompts.md` Concurrency Isolation。worktree 仅在合并成功后移除。
- 目标项目未安装 spec-kit（无 `.specify/`）时：**委托 sdd-project-setup** 做 bootstrap（本技能不执行初始化）；bootstrap 返回 `maintenance-pending` 时，再**委托 sdd-house-keeping H1–H4** 做首次维护，取得 ready 凭证后重入循环。

## Subagent Create & Dispatch Delegation（子代理创建与派发委派）

本手册是**编排者**：它不自带派发机制，而是委派两个承接技能完成驱动子代理的任务（2026-10-16 委派化裁定）：

- **实例创建 → create-agent**（`.specify/skills/internal/create-agent/SKILL.md`）：从 `agents/sdd-executor.agent.md` 按职责实例化阶段执行实例（一实例一职责）；产出=`.specify/agents/instances/<slug>.agent.md`。
- **阶段派发 → run-agent**（`.specify/skills/internal/run-agent/SKILL.md`）：本地拓扑的阶段派发用宿主原生子代理（MUST NOT 启动 qodercli），远端拓扑用外部 CLI；远端进入形态为 `ssh <alias>` → `su - <run-user>` → `cd <project-dir>`，CLI 缺省取 execution-config defaults（`cli: qodercli`），可按 agent/inline 覆盖；以拓扑声明 + 实例引用发起执行；前置检查与失败处置见其 `references/dispatch-preflight.md`。
- **编排本体在本手册**：阶段序列（U0–U6）、状态脊、哨兵与独立校验、卡死处置、收尾合并不由承接技能承担（职责切分见 agent-definitions § Driving Subagents via the Three Layers）。
- **阶段子代理预算**：默认 `run-turn-budget` 120；大 implement 阶段按 ≤8 任务/段拆分，细则见 `references/dispatch-recipes.md` § 阶段子代理预算与分段。

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

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:sdd-loop-driver" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:sdd-loop-driver" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:sdd-loop-driver" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
