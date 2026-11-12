# Best-Practice-Based Optimization Workflow

> **Owner**：shared 层。本工作流拥有**优化编排与输出映射**；它不定义任何单项最佳实践。
>
> **单项最佳实践 owner 示例**：`.specify/shared/definitions/self-explanatory-definitions.md`（概念）+ `.specify/shared/guidelines/self-explanatory.md`（实践）。
>
> **Status**: confirmed at exit gate — 2026-11-04. 最终文件名按同族约定取定。

## 1. 目的与适用范围

本工作流定义一次 `/speckit.*` 执行（尤其是 `/speckit.improve`）如何：

1. 分析上下文；
2. 查找最佳实践文档；
3. 选择并应用最佳实践；
4. 把结果输出到正确的目标制品。

它同时适用于 **spec-kit 自身**与**客户项目**；由“两顶帽子”决定目标。

## 2. 两顶帽子（Two Hats）

- **Framework hat（框架自身）**：工作流作用在 spec-kit 自身；`.specify/shared/*` 是源，自优化的输出落到框架自己的治理或运行目标（例如框架自身的 `.specify/constitution.md`、`.specify/instructions.md`，或执行流程解析出的其他目标）。
- **Client hat（客户项目）**：工作流作用在用户项目；`/speckit.constitution` 输出到客户项目的 `.specify/constitution.md`，`/speckit.instructions` 输出到客户项目的 `.specify/instructions.md`。
- **先定帽子，再定目标**：同一个命令可以在两种帽子下运行；不得把框架源内容写进客户项目运行时而当作源修改，也不得把客户运行时修改当作框架源修改。
- 拓扑与路径解析规则的 owner 是 `.specify/shared/definitions/dogfooding-definitions.md` §2.1；本节只引用，不重述。

## 3. 触发与上下文分析

- **每次调用 `/speckit.improve` 都必须参考本工作流**。
- 其他 `/speckit.*` 命令在输出或集成最佳实践时应用本工作流。
- 第一步分析上下文：识别用户的信息或优化需求、当前执行流程、以及当前帽子。
- 第二步查找最佳实践文档：在 shared 层的最佳实践目录中定位候选条目（见 §4）。

## 4. 最佳实践目录与条目形态

- 一项最佳实践**可以是一个目录条目，也可以是一份独立文档**，取决于内容多少。
- “不言自明”的条目是两份独立文档：
  - 概念 owner：`.specify/shared/definitions/self-explanatory-definitions.md`
  - 实践 owner：`.specify/shared/guidelines/self-explanatory.md`
- 查找时以条目声明的 owner 路径为准；工作流不复制条目的定义或阈值。
- 新增最佳实践时，在本节登记条目，或登记其独立文档路径与 owner。

## 5. 选择与应用

- 每个优化任务选择一个最佳实践；应用时以该实践的指南为准。
- 任务层与实现层的粒度区分由所选最佳实践的指南定义。例如“不言自明”的任务层约束见 `.specify/shared/definitions/self-explanatory-definitions.md` §7，实现层的调协过程见其 `.specify/shared/guidelines/self-explanatory.md` §9。
- 应用前必须确认具体目的；没有具体用户信息或优化需求时，不做预防性改造。目的性约束的 owner 是所选最佳实践。
- 既有结构按 reconcile 模式逐步迁移；改名类改造先评估引用面、工作量与向前兼容性。

## 6. 输出映射

| 命令或流程 | Client hat 目标 | Framework hat 目标 |
|------------|-----------------|--------------------|
| `/speckit.constitution` | 客户项目的 `.specify/constitution.md` | 由框架自身的执行流程解析 |
| `/speckit.instructions` | 客户项目的 `.specify/instructions.md` | 由框架自身的执行流程解析 |
| `/speckit.improve` 及其他 `/speckit.*` | 该命令自己的目标制品 | 该命令在框架自身执行时的目标制品 |

- 目标**不全局硬编码**；按当前执行流程与帽子解析。
- 自优化可以落在框架源（`.specify/shared/*`），也可以落在框架运行时；由对应执行流程决定。

## 7. 输出形态

- 目标制品承载**摘要 + 指针**，不复制 shared 层的完整定义；shared 层仍是唯一 owner（见 `.specify/shared/guidelines/one-source-of-truth.md`）。
- 摘要必须自足到让读者能行动，并指明 owner 路径。
- 如果目标制品没有指针机制，可以承载简短摘要，但必须指明 owner。

## 8. 边界

- 本工作流不定义任何概念或实践；单项最佳实践由其 definitions / guidelines 拥有。
- 本工作流负责“何时查找、如何选择、输出到哪里”，不负责替代单项实践的判据。
- 自优化同样受本工作流约束；具体输出目标由执行流程决定。
