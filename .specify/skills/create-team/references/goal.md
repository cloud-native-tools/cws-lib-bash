# Team Goal — 团队目标（操作规范）

**Owner**: the team domain (`create-team` / `/speckit.team`). This file is the single source of truth for the **team-side goal operations** — how a team establishes, carries, and deliberately revises the goal it serves. The **Goal concept itself** (project-level first-class entity at `.specify/goal/<goal-slug>/`, Goal vs Requirement boundary, criteria authority, singularity, and the `goal_slug` Goal–Team binding) is defined once in `.specify/shared/definitions/goal-definitions.md` — this file defers to it and MUST NOT re-define the concept. `improve-team` and other team skills link here for operations, there for the concept. It is the goal-side companion to [`conceptual-model.md`](conceptual-model.md).

## 定义

一个 **team** 由三部分组成：**goal**（总体最终目标）+ **static structure**（Role × Stage × Type 花名册）+ **dynamic structure**（协作模式）。**goal 是北极星，静态与动态结构仅为达成它而存在**——无论它们是什么，都必须围绕 goal 组织与运行。

## 四条性质

1. **北极星，不是任务清单**：goal 描述期望的**最终结果**，不是步骤。角色/阶段与协作模式都**由 goal 推导且服从于 goal**。
2. **具体且可验证**：写到「进展可被判断」——尽量带显式成功标准/质量维度与可度量目标（分数阈值、测试通过、覆盖率）。**evaluator 阶段**与 **iteration/continuous 的 `threshold`/质量维度**正是对着 goal 度量进展；**无法评估的 goal 无法驱动循环**。
3. **区别于 `description`**：`description` 是一句话标签；**goal 是整个团队围绕组织的操作性目标**。一个 team **只有一个** goal。
4. **可刻意修改，但不会漂移**：goal 在一次运行中固定，不因重构结构而作为副作用改动；但可经 `modify` 刻意重定义（见下）。

## create 模式：goal 优先

定义团队时**必须先确立 goal**，再据此推导结构：

1. **Establish the goal（第一步）**——从 `$ARGUMENTS`/对话/仓库上下文提取 goal；缺失则询问；与用户确认。写成可验证形式（含成功标准/阈值）。
2. **Derive structure from the goal**——由 goal 决定需要哪些角色/阶段（静态）与哪种协作模式（动态）。
3. 若 **goal 主题为「优化」**，进一步按 [`optimization-goals.md`](optimization-goals.md) 区分**一次性 / 持续**，并为持续优化选择**淘汰 / 渐进**策略。

## 持久化:引用优先,内联可选

一个具体 goal 的**内容**(目标叙述 + 成功判据)的单一事实源是它在 `.specify/goal/<goal-slug>/goal.md` 的**定义**,由 `/speckit.goal` 撰写。团队侧只声明它服务于哪个 goal,不复制其内容:

- frontmatter 以 **`goal_slug`** 声明所引用的 goal(**引用,不是副本**);同一 `goal_slug` 的多个团队解析到同一份定义。
- 内联的 **`goal`** 字段与 **`## Goal`** 小节仍为合法,用于可读性与存量兼容(字段顺序:`slug, name, description, goal, goal_slug, territory, pattern, members, config, created, updated`;先写 `## Goal`,静态与动态小节围绕它组织)。**当定义存在时以定义为权威**;内联与定义不一致会被显式报出供人裁决,不静默降级。
- 未声明 `goal_slug` 的存量团队仍以内联 `goal` 正常工作,MUST NOT 要求先迁移。

## modify 模式:改内容去定义,改结构在团队

- 修改某个 goal 的**内容**(重写目标或判据)是对**定义**的编辑,经 `/speckit.goal`(`modify` / `criteria` / `status`),不在 `team.md` 里就地改。
- 因 goal 变更而**重对齐花名册与协作模式**仍是团队侧的 `modify`(`improve-team`)。详见 [`../../improve-team/references/goal-editing.md`](../../improve-team/references/goal-editing.md)。

## Target(目标切片):提议形流程,授权只经 /speckit.goal

Target 是 goal 之下的 run 级可指派范围切片——概念(身份文法、三态生命周期、与判据轴的边界)定义一次于 `.specify/shared/definitions/goal-definitions.md` 的 Target Decomposition([[STR-004]]),此处只规范团队侧的操作纪律,不复述概念:

- **提议 → 批准(ratify)两段式**:团队或某次 run 认为需要新切片、或某切片已完成/应放弃时,只**提议**——在 run 报告与台账证据中写明理由;实际的新增(`targets <slug> --add`)与状态迁移(`targets <slug> --set done|dropped|open --id <T-nnn>`)MUST 经 `/speckit.goal` 由人批准执行。**派生流程 MUST NOT 写 `goal.md`**——包括 `## Targets` 节,它只由引擎渲染。
- **分解提议(goal-based 创建,042)**:分解路径产出**分解提议集**——每条候选为成果形语句(GD-2)、从属同一目标、自身独立成立者另立 goal;呈现前每条经 `targets <slug> --check` 干跑通过(校验器与 `--add` 同源),批准为一次**合并批准**(propose→ratify 决策语义不变),随后逐条 `--add`;exit-2 拒绝原样上报、修订重检或显式放弃,不绕过引擎。对 `goal.md` 零写入的红线覆盖提议全程(过程细节见 [`create-mode.md`](create-mode.md) → *Goal-based create branch*)。
- **复用基线**:既有 open Target 是分解提议的复用基线——直接复用、不推倒重建,语义重复的语句不重复授权;done/dropped 条目保留展示、不复用身份、不被顺带重开(重开仅 `/speckit.goal targets --set open`,由人发起)。提议集为空时直接进入成组建队,不强制新增。
- **run 指派是消费不是授权**:`/speckit.team run <team-slug> --target T-<nnn>` 只挑选一个已授权的 `open` 切片聚焦执行;悬空/终态/跨 goal 引用在 preview 即被拦截,终态引用走复核二分而非执行旁路。
- **focus_target(默认聚焦,042)**:goal-based 创建产出的 team.md 可在 frontmatter(`goal_slug` 之后)声明 `focus_target: T-<nnn>`——该团队**默认聚焦**的 Target。它是 run 级 `--target` 的**预填**:解析顺序恒为 显式 `--target` > `focus_target` > 无;未显式指定时 run 解析到它并在执行前披露中以 `(团队默认)` 呈现来源。它**不是写域声明**(写域是 `territory`)、不是 Goal–Team 绑定变更、不参与 goal 身份解析、不改 summary 交付目录。创建时 MUST 校验其引用绑定 goal 下既存的 `open` Target;对应 Target 转终态后 run 被五查拦截,经 improve-team 重聚焦或 `/speckit.goal` 重开,无终态执行旁路。
- **归属落痕**:被指派 run 产生的新台账条目由团队主管写入可选 `target_ref`(局部形),供总结侧折叠出切片轴;归属与证据不一致时列为待批准项,两侧都不自动翻转(见 [`summary-mapping.md`](summary-mapping.md) §6.5)。
