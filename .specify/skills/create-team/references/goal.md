# Team Goal — 团队目标（操作规范）

**Owner**: the team domain (`create-team` / `/speckit.team`). This file is the **single source of truth** for the team **goal** concept. `improve-team` and other team skills MUST link here rather than re-defining it. It is the goal-side companion to [`conceptual-model.md`](conceptual-model.md).

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

## 持久化

持久化的 `.specify/teams/<slug>/team.md`（团队目录，运行报告累积在同目录 `runs/` 下）：

- frontmatter 含 **`goal`** 字段（顺序：`slug, name, description, goal, pattern, members, config, created, updated`）；
- 含 **`## Goal`** 小节（总体最终目标 + 成功标准），**先写 `## Goal`**，静态与动态小节都围绕它组织。

## modify 模式：goal 可修改

`modify`（`improve-team`）可把 goal 作为**一等可修改对象**重定义；goal 变更时必须**重新对齐**花名册与协作模式。详见 [`../../improve-team/references/goal-editing.md`](../../improve-team/references/goal-editing.md)。
