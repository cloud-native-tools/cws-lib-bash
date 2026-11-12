# 不言自明（Self-explanatory）— 概念定义

> **Owner 声明**：本文件是“不言自明（Self-explanatory）”概念的单一真源。实践方法见 `.specify/shared/guidelines/self-explanatory.md`；Constitution 与 instructions 只持有指针或摘要，不复制本定义。
>
> **命名史**：本概念最初以“望文生义”引入；2026-11-04 按用户决定，中文规范名改为“不言自明”，英文规范名为“Self-explanatory”。旧名只作为历史记录保留，后续引用一律使用新名。
>
> **Status**: confirmed at exit gate — 2026-11-04. Ledger: `.specify/memory/session/interview-wangwenshengyi.md`.

## 1. 概念

不言自明是一条**以人为本**的原则：名称、路径与结构应当从**用户视角**一次性传达系统的关键信息。人类用户应当能够直接看到这些信息，或者通过一个简单的命令取得更详细的信息，而不必先打开文件、阅读实现或询问维护者。

它防住的失效是：结构本身不携带用户需要的信息，用户只能靠记忆、额外文档或逐项打开实体来恢复系统状态，因而无法在入口处完成筛选、排序和判断。

> **边界**：本概念的判据是“人从名称、路径或结构能否直接得到信息”，不是“程序能否在不携带上下文的情况下理解”。程序视角的可读性不是本概念的判据。

## 2. 用户视角的信息可达性

- **上限（ceiling）**：用户可以直接看到所需信息。
- **下限（floor）**：用户可以通过一个简单命令取得所需信息。
- 只要下限满足，就足以支持一次改造；上限是优先方向，不是每次改造的硬门槛。

## 3. 适用面

本概念**先确定原则，不预先固定实施面**。哪些名称或结构值得改造，按项目、用户和工作流具体分析；不同项目、不同用户的标准不同，不存在普适的实施清单。应用可由用户主动触发，或在优化流程中提示触发。

本概念**不是无缘由的预防性优化措施**：只有在存在具体的用户信息需求（用户要在入口处完成某项筛选、排序或判断）时才适用；不能指出具体目的时，不应用本概念。

## 4. 与既有原则的关系

- 与 Constitution X（Documentation Naming & Location Conventions）最接近，是对其“path is semantic / names carry meaning”的**具现化**。
- 依赖 Constitution XVIII（Grounded Naming）：名称首先由既有权威来源决定，不能为了“不言自明”绕过命名来源规则。
- **核心判断条件**：面对一个具体结构，如果本概念能触发“把用户需要的信息维度提升为名称、路径或结构层级”的改造判断，说明它已进入框架并产生效力；不能触发则说明 Constitution X 的效力不足。goal 的 `<status>/<slug>` 布局只是本概念的一个示例，不是对所有项目强制实施的普适布局。
- <!-- 092 handoff: D6 → 082 / 083 -->
  与 `.specify/shared/definitions/mechanism-policy-definitions.md` 的相邻边界与**判据优先级**：一段内容先按那份文件的判据定侧（机制侧 / 运行环境侧），再在本概念下决定**这一侧内部**的名称、路径是否承载信息维度。定侧在前、命名在后；同时可读时先定侧，命名只在已定的侧内生效。

## 5. 权威归属与强制力

- 定义由 **shared 层**拥有：框架源为本文件 `.specify/shared/definitions/self-explanatory-definitions.md`；运行时镜像为 `.specify/shared/definitions/self-explanatory-definitions.md`。
- **Constitution 与 instructions 是输出机制**：在客户项目中，它们把 shared 层的定义投射到该项目的 harness 配置中，只持有指针或摘要，不复制定义文本；在 framework hat 下，自优化的输出目标由执行流程决定（见 `.specify/shared/workflow/best-practice-optimization.md` §2、§6）。
- 输出与应用映射见 `.specify/shared/workflow/best-practice-optimization.md`。
- 强制力为 **SHOULD**，以**最佳实践条目**的方式嵌入框架自主的优化流程。

## 6. 被编码属性的真源与投影

- 当名称或路径编码了某个属性（例如 goal 的 status），该属性的权威值仍在原有真源中：`goal.md` 的 YAML frontmatter `status` 是 One Source of Truth。
- 名称或路径是**投影**，不是第二真源；不得通过独立编辑路径来改变状态。
- 投影由 `/speckit.sanitize` 等调协机制维护，采用**最终一致**：不要求实时性，但调协后必须与真源一致。

## 7. 维度增加顺序

当确实要增加一个信息维度时，按以下优先级决定：

1. **用户明确要求**；
2. **框架自身规则**；
3. **每次最多只增加一个维度**（小步快跑、及时止损）。

该顺序是概念层的约束；具体操作步骤见 `.specify/shared/guidelines/self-explanatory.md`。
