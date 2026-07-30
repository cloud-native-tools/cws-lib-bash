# 代码生成与配套文字指南

> 根据所选图表类型的操作指南和最佳实践，编写具体的 PlantUML 代码并准备配套文字说明。本指南是 [SKILL.md Step 6](../../SKILL.md) 的详细参考。

---

## 一、代码草拟流程

### 1.1 识别关键元素

从用户描述中识别关键元素：
- **参与者/节点/组件/类**：系统中的实体
- **角色**：与系统交互的外部实体（用户、外部系统）
- **状态**：对象生命周期中的关键状态

### 1.2 定义关系

确定元素之间的关系类型：
- 依赖、关联、实现、继承（结构图）
- 消息、调用、返回（时序图）
- 状态转换、事件触发（状态机图）
- 控制流、数据流（活动图）

### 1.3 编写 PlantUML 代码

1. 用 `@startuml` / `@enduml` 包裹整个图表
2. 先声明所有元素，再声明关系（代码结构清晰）
3. 每张图聚焦单一主题，核心元素 ≤7 个（可接受 ≤12，硬上限 15）；过大则拆分为多张图
4. 应用布局技术：方向关键字（`-right->`、`-down->`）、分组关联元素（`together{}`）、隐藏连线（`-[hidden]->`）

### 1.4 代码结构示例

```plantuml
' ✓ 好：先声明核心元素，再描述关系
participant OrderService
participant PaymentService
participant InventoryService

OrderService -> PaymentService : 发起支付
PaymentService -> InventoryService : 扣减库存
```

```plantuml
' ✗ 差：边定义边画关系，阅读混乱
participant OrderService
OrderService -> PaymentService : 发起支付
participant InventoryService
PaymentService -> InventoryService : 扣减库存
```

---

## 二、标签与注释规则

### 2.1 核心规则：标签 ≤10 字符 + note 补充

元素名称和关系标签不得超过 10 个字符——适用于所有 UML 图类型，无例外。当短标签无法充分表达元素用途时，**必须**附加 `note` 元素补充详细说明。

```plantuml
' ✗ 差：元素标签过长，导致框体过宽
component [用户订单管理服务主模块] as OrderMain

' ✓ 好：简短标签 + note 补充说明
component [订单服务] as Order

note right of Order
  包含订单创建、取消、
  退款、状态查询等子模块
end note
```

### 2.2 注释位置语法

| 场景 | 语法 | 说明 |
|------|------|------|
| 元素旁注释 | `note right of X` / `note left of` / `note top of` / `note bottom of` | 定位在元素指定方向 |
| 多行注释 | `note right of X` ... `end note` | 多段说明文字 |
| 浮动注释 | `note "text" as N` + `N .. X` | 独立放置，用虚线连接 |
| 关系线注释 | `note on link` ... `end note` | 附加在箭头连线上 |
| 简短箭头标签 | `A -> B : 简短文字` | ≤10 字符，直接在箭头上 |

> **注意**：在组件/矩形图中使用 `note top/bottom/right/left of X`，不要使用 `note over X,Y`（仅限时序图）。

### 2.3 详细注释模式和示例

详细的注释写作模式、常见反模式和 note 语法速查，参见 [content.md §1.5 标签精简与富文本注释补充](../guide/content.md) 和 [§二–三 注释策略](../guide/content.md)。

---

## 三、布局技术应用

编写代码时应用以下布局技术（详细说明参见 [layout.md §二 布局优化](../guide/layout.md)）：

- **方向控制**：用 `-right->`/`-down->` 等方向关键字明确连线走向
- **隐藏连线**：用 `-[hidden]->` 创建不可见连接，间接调整元素位置
- **分组绑定**：用 `together{}` 将关联元素紧密排列
- **间距调整**：用 `skinparam nodesep`/`ranksep` 控制元素间距
- **线型区分**：实线 `-->`（数据流）、虚线 `..>`（控制信号）、粗线 `==>`（关键路径）

按图表类型的推荐方向和布局重点，参见 [layout.md §三 按图表类型的布局速查](../guide/layout.md)。

---

## 四、配套文字准备

对每张图，准备以下说明内容（将包含在最终 HTML 中）：

| 内容项 | 说明 |
|--------|------|
| **图表标题** | 将成为 HTML 中的 H2/H3 标题 |
| **上下文** | 1-2 句话说明此图代表什么以及为何选择此类型 |
| **PlantUML 源代码** | 保存为 `.puml` 文件供参考和渲染 |
| **说明** | 每个关键元素和关系的要点 |
| **设计理由** | 为何选择此结构/交互模式（如适用） |

文字说明应引用图表中的具体元素，避免泛泛描述。文字和图互补——文字解释*为什么*，图展示*什么*。

---

## 五、PlantUML 语法参考

完整的 PlantUML 语法细节（元素类型、关系表示法、样式、模式、按图表类型的快速语法参考表），参见 [syntax-reference.md](../guide/syntax-reference.md)。

各图表类型的详细操作指南（关键元素、完整示例、建模步骤、最佳实践），参见 [references/howto/](./) 目录中 02–09 的对应文档。
