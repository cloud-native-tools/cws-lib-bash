---
name: sdd-loop-driver
description: 无人值守 SDD 循环驱动手册——以一条一遍性提示词驱动主代理完成「登录环境 → 以 qodercli 为子代理 → 按阶段推进 SDD 完整流程（requirements → clarify → plan → tasks → checklist → analyze → implement → review）→ 合并 main」的完整闭环，全程循环自推进、零用户提醒。当用户说「使用SDD开发模式推动 <项目>」「无人值守推进」「sdd-loop-driver」「需要使用一个循环来完成这项工作，而不是每次由我提醒你重试或继续」时加载本手册。执行细节（断点探测 / 阶段化 prompt 文件 / runner 与派生 / 后台执行+统一监听 / 收尾纪律）全部由本手册承接，入口只声明目标与起点。当以本技能名给出功能/改进描述时，视为 SDD 目标（目标项目可为本技能自身所在仓库），先做 U0/U1 并走阶段链，不得就地改代码或切换为技能维护路径。
skill_id: "<SKILL:.specify/skills/sdd-loop-driver/SKILL.md>"
classification: external
---

> **分类注解**：本 skill 依**依赖轴**判定为 external——自身零 spec-kit 依赖、任何宿主 agent 可直接加载；内容编排 spec-kit 的 SDD 流程（语义耦合显式声明：指挥子代理执行 `/speckit.*`），不构成运行时依赖。

## What This Skill Does

把经多项目验证的「无人值守 SDD 驱动」固化为可执行手册：宿主 agent（无需安装 spec-kit）对每条项目线执行「断点探测 → 阶段派发 → 统一监听 → 独立校验 → 续环」，直到 review 完成并合并收尾。自迭代、独立校验、卡死处置三条硬需求内置于本手册；监听语义（等待/监控/轮询）的唯一权威落点是 `references/watch-model.md`。

**触发语义与路由**：以本技能名加载并给出功能/改进描述 = SDD 目标，目标项目可为任意仓库（含本技能自身仓库）；改进本技能也必须走 U0/U1 → 阶段链。仅入口显式声明「只做技能维护、不走 SDD」时，才允许 improve-skills/create-skills 维护路径。**主导流程唯一**：**加载后的第一个动作**是写出 U0 入口声明与阶段计划，在此之前不加载其他技能、不编辑文件、不派发 subagent。

**质量门完整**：checklist/analyze/review 在无人值守循环中一律必经、不可省略（编排见 dispatch-recipes.md Recipe 4）。与 sdd-project-setup **非强绑定、各自可独立运行**：框架调协归它，阶段循环归本技能；候选清单仅建议，需确认后启动。

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
| 目标项目 | 当前工作目录含 `.specify/` → 当前仓库；否则问一个澄清问题，不猜 |
| 执行拓扑 | 未给 ssh 别名/run-user/远端路径 → 本地；给全 → 远端 |
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

## The Loop (U0–U6)

```text
U0 ENTRY     一遍性入口：目标、线、断点（或"探测"）、终态权威文档
U1 PROBE     每线：断点探测（git 分支 + 近期提交 + specs 目录 + 终态文档）判定续跑阶段
U2 DISPATCH  写阶段提示词文件 + runner，后台派发（配方见 references/dispatch-recipes.md）
U3 WATCH     统一监听：单次调用内长轮询信号（退出记录/哨兵/PID/心跳）至终止判定或窗口到期；窗口到期只返回 RUNNING 并立即重入，只有阶段 deadline 产生 TIMEOUT（见 references/watch-model.md）
U4 VERIFY    独立校验：哨兵（必要）+ 产物核验 + 纪律抽查（充分）→ 通过才续环
U5 STALL     超时/重试上限/预算触顶 → 停线、状态脊落盘、出上送件（绝不静默等待）
U6 LEAVE     全线收束：逐线合并收尾（git 状态判定 + 工作树归档清扫，缺省本地合并）+ 一份收尾汇总
```

多条线并行 = 多个独立循环实例：一线一连接、一线一状态脊。首次派发前登记环境级 Line Registry（`.specify/scripts/line-registry.py --action register`），事件携带 `(line_id, run_id)` 信封，U6 后 `deregister`；无标识消息经 `resolve-message` 判定，禁止进程扫描推断。

U0 的产物是入口声明（目标/拓扑/权威/切片/断点）与阶段计划；未产出前不得进入 U2，更不得直接编辑目标仓库。

### Hook completion backstop（Qoder CLI）

Hook 只是提前完成信号（`--settings` 注入、写 done/FIFO、`hook=observed`），完成仍由退出记录 + 哨兵判定；SSH 长读与故障矩阵见 `references/watch-model.md` §12–§13。

## Hard Requirements

1. **自迭代**：U4 通过后立即派发下一阶段（U2），不等用户任何形式的「继续」。
2. **独立校验**：阶段完成判定不由执行者自报——校验者不是该阶段执行子代理；哨兵在而产物缺 = 伪完成，判未完成。
3. **卡死处置**：达重试上限（缺省 2 次）或阶段超时（缺省 90 分钟）→ 停环、落状态脊、出上送件四要素（发现了什么 / 为何吃重 / 已产生的中间产物逐项可定位 / 可选处置）。
4. **状态脊**：每线状态文件在 U2 派发前、U3 终止判定时、U4 校验后、U5 停线时先写后动；续环与重入只认状态脊，不依赖会话记忆。
5. **驱动者生命周期**：U3 是当前运行内的有界等待（窗口见 `references/watch-model.md`），驱动者必须存活到全线收束或显式停线上送；独立 `sleep` 回合与「挂监视器后等通知/恢复」均不合法——除非宿主已被探针证明能自动恢复同一运行。确须结束时，唯一合法路径是把状态脊写为 stalled/reentry-required 并显式上报。
6. **驱动拓扑**：加载者即驱动者，亲自执行 U0–U6；阶段子代理只收三段骨架提示词；反嵌套义务真源在 run-agent 派发治理，本手册于 U2 派发前自检。
7. **流程不可替换**：U0/U1 与阶段计划写出前禁止直接编辑目标仓库；禁止用 improve-skills/create-skills 等维护路径替代 SDD 阶段链（目标为本仓库时同样适用）。唯一例外：入口显式声明「只做技能维护、不走 SDD」。

## Discipline Defaults

阶段提示词骨架第二段把默认纪律写进每次派发（全文见 references/stage-prompts.md）：直接执行不要确认、访谈式问题自行裁决并记录假设、只提交本特性产物、既有脏文件不提交不还原、不要 push（除非明确授权）。

## Efficiency Optimizations（运行效率优化）

七项优化（owner：`references/efficiency-model.md`）：

1. **快车道**：仅入口 `fast-lane=opt-in` 时在 tasks 后按七项机械判据裁决；录取跳过 checklist、保留 analyze/review，判据失效即回退完整链。
2. **两槽位测试预算**：每线仅 implement 起点 baseline 与 review 后 closure 两次全量；中间与 review 用定向集留证据；槽外全量必须显式例外。
3. **Plan 只小修**：plan 后下游只允许小修并须 `PLAN-EDIT:` 声明；实质改动按两分支处置；requirements 门内变更按最新锚点 re-baseline。
4. **进度与脱离**：runner 默认 stream-json，raw + 派生 live log；本地与远端均 nohup 脱离，`--once` 重入只核验不重派。
5. **大特性拆分门**：plan 入口 >30 FR 或 tasks U4 >40 任务判 `split-required`，拆分后逐切片推进。
6. **确定性预检**：requirements/plan/tasks 的 U4 先跑 `pre-analyze-check.py`（重复/悬空 ID、blockedBy、计数漂移、死路径），在 analyze 前修复。
7. **跨特性重叠预检**：clarify U4 运行 `overlap-check.py`，共享交付路径重叠先做归属裁决再派发 plan。

新增脚本与领域细则见 `references/efficiency-model.md` §5–§7 与 References。

## References

- `references/dispatch-recipes.md` — 五大执行机制：断点探测、阶段化 prompt、runner 与派生、统一监听、收尾；阶段链与哨兵；hook/SSH 窗口；线路登记与消息入口。
- `references/watch-model.md` — 统一监听模型：信号源、判定状态机、窗口与阶段期限、`pgrep -c` 零匹配陷阱、多线 manifest、宿主适配与自测；归属层与重接线快照（§11）；hook 事件补充、SSH 远程读法与故障矩阵（§12–§13）。
- `references/stage-prompts.md` — 三段骨架、独立校验、Line/Envelope/Ingress、重接线/orphan/U6、变体、并发隔离与窄读法授权、卡死处置与状态脊。
- `.specify/scripts/watch-target.sh` — 长轮询 watcher 参考实现（单目标/多目标、快照与自测、归属过滤、hook、`--raw-stream`、lease 续租）。
- `.specify/scripts/hook-stop.sh` / `watch-hook.sh` — Stop hook 模板（原子写 done JSON + FIFO）与远端同身份长读（`HOOK_TIMEOUT`）。
- `.specify/scripts/line-registry.py` — Python 3 stdlib-only 引擎：环境级 Registry、原子写/同线锁、信封分类、消息入口、所有权/集成队列、lease/reservation/身份校验。
- `.specify/scripts/decomposition-check.py` / `pre-analyze-check.py` / `overlap-check.py` — 三个确定性门：大特性拆分、跨产物预检、跨特性重叠（规则 owner：efficiency-model §5–§7）。

## Boundary

- 合并/push 维持确认门控破坏性分类：缺省本地合并；push 须经入口显式授权。
- 阶段命令为不透明单元：不改各 `/speckit.*` 命令内部流程。
- 不绑定特定项目族或工作区命名规则：别名、用户、路径、CLI、断点阶段全部入口参数化。
- 同仓多写线：worktree-per-write-line + Ownership Manifest + 确定性集成队列；规则见 `references/dispatch-recipes.md` Recipe 7 与 `references/stage-prompts.md` Concurrency Isolation。worktree 仅在合并成功后移除。
- 目标项目未安装 spec-kit（无 `.specify/`）时：**委托 sdd-project-setup** 处置（本技能不执行初始化），处置完成并取得就绪凭证后重入循环。

## Subagent Create & Dispatch Delegation（子代理创建与派发委派）

本手册是**编排者**：它不自带派发机制，而是委派两个承接技能完成驱动子代理的任务（2026-10-16 委派化裁定）：

- **实例创建 → create-agent**（`.specify/skills/internal/create-agent/SKILL.md`）：从 `agents/sdd-executor.agent.md` 按职责实例化阶段执行实例（一实例一职责）；产出=`.specify/agents/instances/<slug>.agent.md`。
- **阶段派发 → run-agent**（`.specify/skills/internal/run-agent/SKILL.md`）：以 Execution 拓扑声明（本地/远端）+ 实例引用发起执行；产出=执行结果或可见性三元组；前置检查与失败处置见其 `references/dispatch-preflight.md`。
- **编排本体在本手册**：阶段序列（U0–U6）、状态脊、哨兵与独立校验、卡死处置、收尾合并不由承接技能承担（职责切分见 agent-definitions § Driving Subagents via the Three Layers）。

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
