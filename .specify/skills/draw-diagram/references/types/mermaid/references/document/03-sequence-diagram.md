# 时序图理论（03）

## 1. 参与者与生命线

- **参与者（participant/actor）**：交互对象（服务、模块、人、外部系统）；
- **生命线**：参与者下方的竖线（时间轴向下）；
- Mermaid：`participant A as 显示名`、`actor`（人形）。

## 2. 消息类型

| 类型 | Mermaid | 语义 |
|------|---------|------|
| 同步消息 | `->>` | 调用方等待返回 |
| 返回消息 | `-->>` | 被调方返回 |
| 异步消息 | `--)` | 不等待 |
| 创建/失联 | `-x` | 终止/销毁 |
| 自调用 | `A->>A` | 内部调用 |

## 3. 组合片段（UML 语义）

| 片段 | Mermaid | 语义 |
|------|---------|------|
| alt | `alt ... else ... end` | 条件分支 |
| opt | `opt ... end` | 可选 |
| loop | `loop ... end` | 循环 |
| par | `par ... and ... end` | 并行 |
| break | `break ... end` | 中断 |
| critical | `critical ... end` | 关键区（必须成功） |
| ref | 无原生 | 用 `Note` + 文字说明 |

## 4. 交互使用（Interaction Use）

UML 的 `ref`（引用另一张时序图）在 Mermaid 无原生支持：
- 方案：`Note over A: ▶ 见图N（XX 时序）` 交叉引用；
- 图集组织（diagram-principles §4.3）。

## 5. 激活与生命周期

- activate/deactivate 表达调用栈（同步调用的生命周期）；
- 自递归、嵌套调用逐层激活；
- 过长的激活（异常场景）用 `break` 表达退出。

## 6. Mermaid 表达要点

- 消息标签 = 动作 + 关键参数（`POST /orders`），≤10 字符；
- 场景拆分：单图消息 ≤20 条；
- `autonumber` 编号便于评审引用；
- 完整语法见 howto/05。
