# 如何画包图 (Package Diagram)

> 包图用于将模型元素分组并展示它们之间的依赖关系，是大型系统架构设计中组织层次结构的核心工具。

## 包图的用途

包图回答的是"系统的模块如何组织，它们之间有什么依赖关系"：
- 将大型系统划分为逻辑上内聚的模块（包/命名空间）
- 展示模块之间的依赖方向和耦合程度
- 帮助识别循环依赖和架构异味
- 为分层架构、领域驱动设计（DDD）的有界上下文提供可视化
- 组织类图的宏观结构，避免单张类图包含过多元素

## 关键元素

| 元素 | PlantUML 表示 | 说明 |
|------|-------------|------|
| **包 (Package)** | `package "名称" {}` | 逻辑分组容器，可嵌套 |
| **命名空间** | `package 名称 {}` | 用 `.` 分隔层次，如 `com.example.order` |
| **依赖 (Dependency)** | `A --> B` 或 `A ..> B` | 包 A 依赖包 B（变更会传播） |
| **包含/嵌套** | 大括号嵌套 | 子包属于父包 |

## PlantUML 语法

### 基本包定义

```plantuml
@startuml
package "Domain Layer" {
  package "Order Domain" {
    class Order
    class OrderItem
  }
  package "User Domain" {
    class User
    class UserProfile
  }
}

package "Infrastructure" {
  package "Persistence" {
    class OrderRepository
    class UserRepository
  }
}

"Order Domain" --> "Persistence" : depends on
"User Domain" --> "Persistence"
@enduml
```

### 命名空间风格（Java 包结构）

```plantuml
@startuml
package com.example.order {
  class OrderService
  class Order
}

package com.example.order.repository {
  interface OrderRepository
  class JpaOrderRepository
}

package com.example.payment {
  class PaymentService
}

com.example.order ..> com.example.order.repository
com.example.order --> com.example.payment
JpaOrderRepository ..|> OrderRepository
@enduml
```

### 带颜色和样式的包图

```plantuml
@startuml
skinparam package {
  BackgroundColor #E8F5E9
  BorderColor #388E3C
  FontStyle bold
}

package "Presentation" #E3F2FD {
  [Web UI]
  [Mobile App]
}

package "Application" #FFF3E0 {
  [Order Service]
  [User Service]
}

package "Domain" #F3E5F5 {
  [Order]
  [User]
}

package "Infrastructure" #FCE4EC {
  [Repository]
  [Message Queue]
}

[Web UI] --> [Order Service]
[Order Service] --> [Order]
[Order Service] --> [Repository]
@enduml
```

## 常见架构模式

### 分层架构（Layered Architecture）

```
Presentation  →  Application  →  Domain  →  Infrastructure
（上层依赖下层，下层不依赖上层）
```

```plantuml
@startuml
' 语义角色：Entry=Presentation, Hub=Domain, Edge=Application, Sink=Infrastructure
skinparam linetype ortho
skinparam nodesep 40
skinparam ranksep 60

together {
  package "Presentation Layer" as PL {
    [Controllers]
    [Views]
  }
}

together {
  package "Application Layer" as AL {
    [OrderAppService]
    [UserAppService]
  }
}

together {
  package "Domain Layer" as DL {
    [Order] as OrderEntity
    [User] as UserEntity
    [OrderService] as OrderDomainSvc
  }
}

together {
  package "Infrastructure Layer" as IL {
    [OrderRepository]
    [UserRepository]
    [EmailSender]
  }
}

' 隐藏连线强制分层顺序
PL -[hidden]d-> AL
AL -[hidden]d-> DL
DL -[hidden]d-> IL

' 强依赖（必须）
PL --> AL
AL --> DL

' 弱依赖（可选/基础设施适配）
AL ..> IL : <<optional>>
DL ..> IL : <<adapter>>
@enduml
```

### 领域驱动设计 (DDD) 有界上下文

```plantuml
@startuml
package "Order Context" as Order {
  [Order] as O
  [OrderItem]
  [OrderService]
}

package "Payment Context" as Payment {
  [Payment]
  [PaymentGateway]
}

package "Shipping Context" as Shipping {
  [Shipment]
  [TrackingService]
}

package "Shared Kernel" as Shared {
  [Money]
  [Address]
  [UserId]
}

Order --> Payment : depends on
Order --> Shipping
Order --> Shared
Payment --> Shared
Shipping --> Shared
@enduml
```

### Java 典型项目包结构

```plantuml
@startuml
package "com.example.project" {
  package "controller" {
    [OrderController]
    [UserController]
  }
  package "service" {
    interface [OrderService]
    [OrderServiceImpl]
    [UserService]
  }
  package "repository" {
    interface [OrderRepository]
    [JpaOrderRepository]
  }
  package "domain" {
    [Order]
    [OrderItem]
    [OrderStatus]
  }
  package "dto" {
    [OrderDTO]
    [CreateOrderRequest]
  }
  package "config" {
    [SecurityConfig]
    [SwaggerConfig]
  }
}

[OrderController] --> [OrderService]
[OrderController] --> [OrderDTO]
[OrderServiceImpl] ..|> [OrderService]
[OrderServiceImpl] --> [OrderRepository]
[OrderServiceImpl] --> [Order]
[JpaOrderRepository] ..|> [OrderRepository]
@enduml
```

### 双层资源模型（声明层 ↔ 动态层）

当资源/数据模型横跨两个层次——「声明/配置层」（期望态、模板、配置）与「动态/运行时层」（实例、快照、运行状态）——用**两个 `package` 分层摆放**，跨层箭头表达「实例化 / 引用 / 派生」关系。声明层在上、动态层在下，跨层箭头单向向下（声明驱动动态）；层内关系用细线，避免与跨层主线抢视觉。

```plantuml
@startuml
package "声明层 (Declarative)" as Decl {
  [模板] as Tmpl
  [配置] as Cfg
}
package "动态层 (Runtime)" as Dyn {
  [实例] as Inst
  [快照] as Snap
}

Tmpl ..> Inst : 实例化
Cfg ..> Inst : 引用
Inst ..> Snap : 派生
@enduml
```

**要点**：
- **层名即语义**：声明层放期望态/模板/配置类元素，动态层放运行时实例/状态类元素；两层各自内聚、跨层单向依赖
- **独立成图，别塞注脚**：凡有「配置/模板 ↔ 运行时实例」的二元结构，优先独立成图（或作为图集的一张子图），**不要**把资源模型信息散落在组件图/部署图的 note 里——note 放不下关系，读者也无法在组件图里读模型
- 若两层各有多个子域，层内再套 `package` 子包，保持「上层声明 → 下层动态」的整体秩序

## 包间依赖原则

好的包结构应该遵循以下原则：

### 无环依赖原则 (Acyclic Dependencies Principle)
包之间的依赖关系图中不应存在循环。如果 A→B→C→A 形成循环，这些包必须作为一个整体一起发布和测试。

```plantuml
@startuml
' ✓ 好的：单向依赖
package A
package B
package C
A --> B
B --> C

' ✗ 坏的：循环依赖
' A --> B --> C --> A
@enduml
```

### 稳定依赖原则 (Stable Dependencies Principle)
依赖方向应指向更稳定的包。被依赖越多的包越稳定（不易变更），依赖别人的包应保持灵活。

### 稳定抽象原则 (Stable Abstractions Principle)
稳定程度越高的包抽象程度越高。抽象（接口、抽象类）应该放在稳定的包中，具体实现放在灵活的包中。

## 包图建模步骤

1. **确定顶层包**：按架构层（Presentation/Application/Domain/Infrastructure）或按业务域划分
2. **逐层展开子包**：每个顶层包内是否需要进一步细分
3. **标注依赖方向**：从依赖方指向被依赖方，确保无循环
4. **检查依赖合理性**：上层能依赖下层，下层不应依赖上层；域层不应依赖基础设施层（依赖倒置）
5. **标注关键类/接口**：在包内放置代表性元素说明包的职责

## 语义布局分析

> 包图的语义角色映射：

| 语义角色 | 含义 | 典型包 |
|---------|------|-------|
| **Hub (中心)** | 核心领域包，被最多包依赖 | Domain、Core |
| **Edge (边缘)** | 特性包/有界上下文 | Order、Payment、Shipping |
| **Entry (入口)** | 对外接口/API 包 | API、Controller、Interface |
| **Sink (汇聚)** | 基础设施/持久化包 | Infrastructure、Persistence |
| **Peer (对等)** | 同层级的功能包 | 同一有界上下文内的子包 |

**位置草图**：
```
[Entry: API/Interface]
        ↓ (依赖)
[Hub: Domain/Core]
    ↓           ↓
[Edge: Order]  [Edge: Payment]  (together{})
        ↓
[Sink: Infrastructure]
```

**布局优化要点**：
- **语义驱动布局**：高层包（Entry）在上，核心包（Hub）居中，基础设施包（Sink）在下
- **`together{}`**：同层的功能包并排，如 `together { package "Order"; package "Payment" }`
- **隐藏连线**：`Presentation -[hidden]d-> Application` 强制分层从上到下
- **虚线区分依赖**：`..>` 表示弱依赖（可选），`-->` 表示强依赖（必须）
- **`linetype ortho`**：包图使用正交布线，层级关系更清晰
- **DDD 上下文**：用 `package` 嵌套表示有界上下文边界

## 最佳实践

- **控制包的大小**：一个包内的类应在 10-20 个以内，超过则拆分子包
- **高内聚低耦合**：包内元素应紧密相关，包间耦合应尽可能小
- **依赖方向与架构层次一致**：依赖箭头应指向更稳定、更抽象的包
- **避免循环依赖**：如果发现循环依赖，提取公共接口或拆分包
- **使用分层命名**：`com.example.order.controller` 比 `controllers` 更清晰
- **包图配合类图使用**：包图给出宏观结构，类图给出微观设计

## 包图与组件图的区别

| 维度 | 包图 | 组件图 |
|------|------|-------|
| 关注点 | 代码的组织结构（命名空间、模块） | 运行时的组件/服务结构 |
| 粒度 | 包/模块层级 | 可独立部署的服务/组件 |
| 典型元素 | package、class | component、interface、database |
| 受众 | 开发者 | 架构师、开发者 |
| 典型问题 | "OrderService 应该放在哪个包？" | "Order Service 依赖哪些其他服务？" |
