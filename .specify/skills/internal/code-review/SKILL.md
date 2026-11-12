---
name: code-review
description: |
  Command-line code review workflow built around git-delta. Covers the full four-phase closed loop — pre-submission (author self-check, PR-size guard), review execution (structured P0–P6 dimension checks in a tests-first order, delta-rendered side-by-side diffs), feedback & iteration (six-level severity taxonomy: blocking/important/suggestion/nitpick/question/praise, convergence rules), and merge & knowledge precipitation (merge gate, metrics). Deterministic work (rendering diffs, recording notes, aggregating reports, merge-gate verdicts) is delegated to `${SKILL_HOME}/scripts/git-delta-review.sh`; judgment work (reading code, writing review comments) stays with the human/LLM reviewer. Use this when the user mentions ["code review", "review diff", "review PR", "review MR", "代码审查", "代码评审", "审查代码", "review 代码", "git-delta", "delta diff", "side-by-side diff", "PR review", "MR 审查", "合并前审查", "review 工作流", "code review workflow", "审查意见", "review comments", "合入门禁", "merge gate"]
skill_id: "<SKILL:.specify/skills/internal/code-review/SKILL.md>"
classification: internal
---

# code-review

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.


## Overview

以 **git-delta 为核心渲染工具** 的命令行 Code Review 工作流，覆盖 **提交前 → 审查中 → 反馈后 → 合入后** 四阶段闭环。核心理念：**git-delta 负责"看得舒服"，脚本负责"记得下来"，Markdown 负责"传得出去"；审查判断由人/LLM 完成**。

分工边界：

- **脚本（确定性）**：`diff` 渲染、`review` 逐文件流程、`note` 意见落盘、`report` 汇总与合入门禁判定、`base` 基准解析、`triage` 适用性判定、`start` 记录创建与轮转、`receipt` 覆盖率回执与段裁决 — 全部封装在 `${SKILL_HOME}/scripts/git-delta-review.sh`。
- **Reviewer（判断性）**：按 P0–P6 维度读代码、写意见、做合入决策 — 方法论见 [`${SKILL_HOME}/references/review-workflow.md`](./references/review-workflow.md)。
- **与 `review-sdd-process` 的关系（不同判定对象，由命令组合）**：本技能判定一次**已提交代码 delta** 的可核验缺陷；`review-sdd-process` 判定产出该特性的 **SDD 过程**。`/speckit.review` 按**固定顺序**组合四个段——过程段 → 产物段 → 实现段 → **代码段**——本技能就是其中的**第四段**，位置由组合内容的 owner `.specify/shared/workflow/acceptance-hardening.md` § Review Composition 定义，本节只声明自己的位次与判定对象。各段各自保留自己的严重度词汇，既不互相折算，也不互相冒充：本技能的六级词汇（由 § Workflow 的 `### Phase 3 — 反馈与迭代` 定义，本节不复述）不因组合而改名、不参与任何映射表、不折算为别家级别；本技能也不因组合而改变自己的判定对象、方法论或记录形态。

## Workflow

> 完整方法论（PR 模板、自检清单、表达原则、反模式、度量指标）见 [`references/review-workflow.md`](./references/review-workflow.md)；delta 安装与 git 配置见 [`references/delta-setup.md`](./references/delta-setup.md)。以下只保留执行骨架。

### Phase 0 — 路由与环境确认

1. 确认角色：**Author**（提交前自检，走 Phase 1）还是 **Reviewer**（审查执行，走 Phase 2–4）。两者都要时按顺序执行。
2. 确认对比基准：默认 `main..HEAD`，可用 `--since/--head` 或 `GIT_BASE/GIT_HEAD` 环境变量覆盖。
3. 确认渲染模式（一条规则、两个条件）：**渲染器可用 且 stdout 是交互终端（TTY）** → 渲染模式，记录标注 `renderer: delta`；其余一切情形（含渲染器存在但由 agent / 非交互 / 重定向输出调用）→ 文本模式，记录标注 `renderer: text`。渲染器缺失不阻断代码段：模式标注加上覆盖率回执就是证据，安装指引见 `references/delta-setup.md`（本技能不自动安装渲染器）。`base` / `triage` / `start` / `note` / `receipt` / `report` 在无渲染器的环境里都能运行。

### Phase 1 — 提交前准备（Author）

> 目标：让 Reviewer 不需要猜。

1. **粒度守门**：运行 `${SKILL_HOME}/scripts/git-delta-review.sh diff --stat`。脚本内置 size guard——变更 >400 行警告拆分，>800 行强烈警告。同时核对单一职责（一个 PR 只做一件事）。
2. **上下文准备**：按 `references/review-workflow.md` §2.2 的 PR 描述模板（What/Why/How/Testing/Risk）补全说明。
3. **自检清单**：按 `references/review-workflow.md` §2.3 逐项过（编译测试通过、无调试残留、无敏感信息、diff 已自审等）。"自审一遍自己的 diff"用 `${SKILL_HOME}/scripts/git-delta-review.sh diff --worktree`（未提交改动，HEAD vs 工作区）或 `diff --side-by-side --since <base>`（已提交改动）。

### Phase 2 — 审查执行（Reviewer）

> 目标：知道看什么、按什么顺序看。

1. **建立全局认知**：`diff --files` 看变更文件与增删行数；读 PR 描述理解意图。
2. **结构化审查**：`review --since <base>` 启动逐文件流程（未提交改动用 `review --worktree`）。脚本默认**测试文件优先**（测试即规格说明），逐文件渲染 delta side-by-side diff；`--focus <path>` 聚焦单模块，`--no-tests-first` 关闭排序。
3. **按 P0–P6 维度检查**（正确性 → 安全性 → 设计 → 可维护性 → 性能 → 风格 → 测试，检查项见 `references/review-workflow.md` §3.1），边看边定级。
4. **记录意见**：
   - 交互模式：每个文件后按提示 `c` 录入意见（选级别/行号/内容），可多条。
   - **Agent/CI 非交互模式**：`note -s <severity> -f <file> [-l <line>] -c <comment>` 逐条写入。LLM 审查时必须先完整阅读 diff 再写意见，禁止凭文件名臆测。
5. **时间管理**：单次 Review 不超过 60 分钟；>400 行分次聚焦审查（`--focus`）；规模参考见 `references/review-workflow.md` §3.3。

### Phase 3 — 反馈与迭代

> 目标：对事不对人、快速收敛。

1. **意见分级**（六级，脚本强制校验）：`blocking` 🔴 必须修改 / `important` 🟠 强烈建议 / `suggestion` 🟢 可选优化 / `nitpick` ⚪ 纯风格 / `question` ❓ 需要解释 / `praise` 👍 值得肯定。表达原则见 `references/review-workflow.md` §4.2。
2. **收敛判定**：`report --summary` 输出按级别汇总 + 合入门禁——存在 `blocking` 则不可合入；存在 `important` 需逐条回应。收敛条件与防无限循环规则见 `references/review-workflow.md` §4.3。
3. **迭代**：Author 修改后重跑 Phase 2（聚焦已改文件），Reviewer 仅针对未解决项复审。

### Phase 4 — 合入与沉淀

> 目标：Review 不是终点而是起点。

1. **合入前检查**：`report --summary` 门禁通过 + CI 全绿 + 无未决讨论线程（完整清单见 `references/review-workflow.md` §5.1）。
2. **归档报告**：`.specify/review/<branch>-<ts>.md` 为 Markdown，可直接粘贴到 PR 描述/评论区或随仓库提交。
3. **知识沉淀**：同一问题被提出超过 2 次 → 转化为 Linter 规则或 Checklist 条目，而非依赖人每次发现（沉淀形式见 `references/review-workflow.md` §5.2）。

### 非交互路径（Agent / CI：五步，不是四步）

代码段有一条完全非交互的路径，五步各由一个确定性子命令承担，均不需要终端、不需要应答任何提示：

1. `base --spec <feature-dir>` — 解析评审区间（`base=` / `head=` / `base_source=`）；无档可解时记 `not-evaluated` 并退出 2，绝不猜基准。
2. `start --spec <feature-dir>` — 创建代码段记录，并先把上一份记录归档为 `code-review-<YYYYMMDDTHHMMSSZ>.md`；第二次运行起这是必经一步，省掉它就是把记录交给 agent 手写。
3. `note -s <severity> -f <file> [-l <line>] -c <comment> --review-file <record>` — 逐条落盘意见。
4. `receipt --review-file <record>` — 写出覆盖率回执与段裁决；随后用 `report --summary --file <record>` 取合入门禁判决。在组合评审（`/speckit.review`）中本步**强制**：记录缺少回执块即判输入错误，MUST NOT 以散文计数替代。
5. `capture --review-file <record> --triage <value> [--unit <custom:owner/name>]` — 客户采集：把本次评审的**发现指针**落进客户项目自己的反馈通道（本特性对前序闭合面的唯一授权修订，见下）。

> **修订记录（四步 → 五步，C-10）**：理由 —— 采集所需的全部输入（记录路径、适用性取值、按严重度计数）只在第 4 步之后才齐备，且采集挂在同一条确定性路径里，「发现进入客户通道」才是机械可核对的事实；代价 —— 前序特性的一处闭合枚举（本节步骤枚举）被改写一次，其余闭合面一字不动。

**采集触发条件（合取，二者同时成立）**：① 本次运行所在仓经帽子判据判为客户项目（判据 owner：`.specify/shared/definitions/dogfooding-definitions.md` § 2.1；框架帽（含 vendored 框架源的客户仓）不采集，以 `skipped` 行披露帽子依据，不混入五值闭集）；② 代码段适用性为 `run`。一次合格运行恰好采集一次、至多一条条目，绝不按意见、按文件或按严重度各写一条。

**条目形态（指针）**：一条客户条目只含封闭字段集 —— 代码段记录路径、本次适用性取值、六项按严重度计数（逐项抄自 `report --summary --format json`，含零值）、本次运行标识（记录头日期戳，经 `REVIEW_RUN_TIMESTAMP` 可确定性覆写）、所属客户单元。条目 MUST NOT 含意见正文、逐文件清单或文件计数。

**披露闭集与零条目规则**：每次运行恰好一行采集结论，状态符取自五值闭集 `client-channel-armed` / `client-channel-unarmed` / `client-unit-ambiguous` / `no-capture-object` / `counts-unavailable`，后接具体细节，并与本次适用性取值同屏可见。未采集的任何情形存储零条目 —— 不写空条目、不以 0 填充、不以「本次无发现」替代具名原因。三条不变量：幂等（`(unit, run)` 键交给反馈引擎答重复，非错误）、非阻断（采集失败恒不阻断评审，本步恒退出 0）、不越权（不改记录、不改回执字段块、不触发任何传输）。

适用性由 `triage` 判定，取值封闭为 `run` / `not-applicable` / `not-evaluated`：空 delta 在回执之前就答为 `not-applicable`，绝不会被一块 0/0/0 的回执报成一次干净的评审。

## Strict Requirements

- **级别词汇表固定**：只允许 `blocking/important/suggestion/nitpick/question/praise`，脚本会拒绝其他值——不要发明新级别。
- **意见必须落到具体位置**：`-f <file> -l <line>`，全局性意见才允许省略 `-f`（记为 `(global)`）。
- **不绕过门禁**：合入门禁的唯一判决来源是脚本的 `report --summary --file <code-review.md>`——当前记录含 `blocking` 条目时它以退出码 1 拒绝，此时不得给出"可以合入"的结论；省略 `--file` 的"目录内最新文件"选取只是历史模式（会自标 implicit），组合路径一律显式给记录路径。
- **大变更不硬审**：size guard 触发 >800 行警告时，先建议拆分，再逐模块 `--focus` 审查；未聚焦到的文件在回执里记为带理由跳过，跳过合法但不计为覆盖信用。
- **渲染模式是一条两条件规则**：渲染器可用 **且** stdout 是交互终端（TTY）→ 渲染模式，记录标注 `renderer: delta`；其余一切情形（含渲染器存在但由 agent / 非交互 / 重定向输出调用）→ 文本模式，记录标注 `renderer: text`。选择只看这两个条件，不看渲染器是否存在本身。

- **渲染器缺失条款已被替代（替代并说明理由）**：原「渲染器缺失即停」条款已由本特性**替代**：替代的证据形态是覆盖率回执（`receipt` 子命令与记录内的回执块），替代理由是真正的底线是"不冒充已读"，而不是"必须存在某个渲染器"——回执把"读全"变成可机械核对的断言（文件集相等 + 逐文件裁决 + 缺口非零退出）。渲染器仍不自动安装：缺失时按 `references/delta-setup.md` 的安装表给出指引，代码段照常以文本模式完成。

- **禁止声称未做的事（封闭四短语）**：文本模式运行时，记录与任何结论中禁止出现下列任一表述：`已完成可视化评审`、`rendered review complete`、`visual review performed`、`side-by-side review done`。该清单由 `requirements.md` SC-003 拥有且是闭合的：新增一类表述须先改该条。

- **回执是「已读全 diff」的唯一证据形态**：覆盖率回执是唯一证据；diff 概览、读过变更文件列表、变更行数不大、工具输出存在本身都不得替代它，也不得单独被引作"这次评审做完了"的证据。

## Feedback boundary（反馈边界：只记框架摩擦）

代码段的结论与反馈条目是两件事，判断对象不同、落点也不同：

- **只有框架自身的摩擦可以投递为反馈条目**：渲染器缺失、基准歧义、回执缺口、非交互路径不足，都属于在使用 Spec Kit 自身的模板、命令、技能、脚本时受阻——这才是 feedback entry 的合法内容。
- **代码缺陷 MUST NOT 作为反馈条目投递**：代码段的 `blocking` / `important` / `suggestion` / `nitpick` / `question` / `praise` 意见说的是**本特性代码**的缺陷，它留在记录文件 `<feature-dir>/code-review.md` 里，那里才有它的级别、文件与行号。把它抄进反馈库是违反本条分类义务的行为，不是可以商量的口味问题。反馈机制本身（红线、存储、引擎、阈值协议）仍由 `.specify/shared/workflow/feedback-step.md` 拥有，本条只规定这条边界。
- 同一条分类义务写在两个表面——`.specify/templates/commands/review.md` 与本技能正文——因此「把代码缺陷当反馈投递」是可被检出的违规，而不是口味问题。

### 本技能自己的收尾记录（嵌套执行时的单元普查）

`/speckit.review` 组合运行时，一次运行的单元普查为**四个单元**：命令单元 `/speckit.review`、被委派的过程技能单元 `skill:review-sdd-process`、被委派的产物／实现段载体技能单元 `skill:review-feature-quality`、被委派的代码技能单元 `skill:code-review`。四者共享同一个 run id、各自 `unit_id` 不同，这正是反馈引擎既有的 `(unit_id, run_id)` 键：没有任何一个单元去重、合并或截断另一个，因此四条记录并存是设计结果，不是重复。普查数量随「可运行时抵达的段载体」走，而不是反过来把某个载体折进邻居以维持旧计数；某段记为 `not-applicable` 或 `not-evaluated` 时它照样完成自己的收尾记录——非结论是关于该段的结论，不是少了一个单元。

本技能的义务说全：本技能在 `## Wrap-up` 里以 `skill:code-review` 作为自己的单元身份、以本次运行的 shared run id 完成**自己的收尾记录**；命令侧 MUST NOT 抑制本技能的收尾，MUST NOT 代写本技能运行判定，也 MUST NOT 事后补记；本技能同样不替另一个单元记录，不对另一个单元的条目做修改。

## Expression face protection（表达面保护，以及回执与覆盖率的区分）

表达类交付物的评审面仍按声明的读者基准判定；该面及其判据由表达类评审面的 owner 声明（本技能不复述、也不另开一条 wiring 引用）。代码段是**附加段**（additional segment），位次是固定顺序中的**第四段**——过程段 → 产物段 → 实现段 → 代码段，之后是 Acceptance Reality Check；该顺序的 owner 是 `.specify/shared/workflow/acceptance-hardening.md` § Review Composition，本技能只声明自己位次第 4。它回答的是"这段已提交的代码 delta 里有没有可验证的缺陷"，判的是另一个对象。本特性没有代码 delta 时，代码段按 `triage` 记为 `not-applicable` 并写明依据——它不替代、也不短路读者基准判定，也不替代产物段或实现段，读者的过程评审结论照旧成立。

覆盖率回执的计数对象必须说清楚，因为两个不同的问题共用了"coverage"这个词：

- 回执统计的是**已评审文件**（reviewed files）：变更文件集里带裁决的那一份占比，连同带理由跳过的数量与缺口数量。它从来不是测试覆盖率（never test coverage），也从来不是编译覆盖率（never compile coverage），更不是行覆盖率。
- 回执不得被引作读者基准判定的证据（never evidence for the reader-baseline judgement）：读者基准问的是"表达能否被目标读者读懂"，回执问的是"这份 delta 有没有被逐文件看过"——不是同一个问题的两个度量，谁也不能为另一方作证。
- 反向同样成立：FR-027 禁止的是把编译/测试/覆盖率结果当作表达类评审面的判定对象，它禁止的是**那个对象**，因此 never forbids the receipt——本回执由 FR-014 要求，是"不冒充已读"的证据形态。两个方向都写下来，是为了让任何一方都不能被引作另一方的依据。

不变量保持不变，本特性不做新增：反馈条目仍是一条一件地落在 `.specify/memory/feedback/`（`scope: local`，一条只属于一个单元的一次运行），零自动传输，反馈目标仍是框架本身；本特性不新增 intake 存储、不新增第二套反馈聚合目录、不新增反馈 id 族，也没有任何上传路径。

## Resource ID

- Canonical ID: `<SKILL:.specify/skills/internal/code-review/SKILL.md>`
- Canonical Path: `.specify/skills/internal/code-review/SKILL.md`

## Path Conventions

This Skill follows the canonical `${SKILL_HOME}` / `${SKILL_WORKDIR}` path conventions:

- Use `${SKILL_HOME}/<relative-path>` for every Skill-owned resource reference (scripts, references, assets, sub-directory files).
- Use `${SKILL_WORKDIR}/<relative-path>` for every runtime/user-facing path this Skill reads from or writes to (inputs in the user's project, outputs delivered to the user). Review 记录统一写入 `${SKILL_WORKDIR}/.specify/review/`（可用 `REVIEW_DIR` 覆盖）。
- Never conflate the two; never embed agent-specific install paths.

## Resources

### Scripts (`${SKILL_HOME}/scripts/`)
- `git-delta-review.sh` — 单脚本、多子命令的确定性实体：`diff`（delta 渲染 + size guard；`--worktree` 支持未提交改动）、`review`（交互式逐文件，测试优先，同支持 `--worktree`）、`note`（非交互意见落盘，无需 delta）、`report`（列表/最新/按级汇总 + 合入门禁判决，`--summary --file <record>` 退出 0 允许 / 1 拒绝 / 2 输入错误）、`base`（评审区间解析）、`triage`（适用性三值判定）、`start`（记录创建与轮转）、`receipt`（覆盖率回执与段裁决，退出 0 完整 / 1 覆盖缺口 / 2 不可评估）。

### References (`${SKILL_HOME}/references/`)
- `review-workflow.md` — 四阶段方法论全本：提交粒度规则、PR 描述模板、自检清单、P0–P6 审查维度、审查顺序、反馈分级与表达原则、迭代收敛规则、合入策略、知识沉淀、度量指标、角色矩阵、反模式对策。
- `delta-setup.md` — git-delta 安装（brew/apt/cargo/预编译包）、git 全局配置（pager/side-by-side/line-numbers/navigate/diff3）、容器集成与故障排查。

### Assets (`${SKILL_HOME}/assets/`)
- No assets currently.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:code-review" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:code-review" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:code-review" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
