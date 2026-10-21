# UML 时序图

> 时序图展示对象之间按时间顺序的消息交换，强调交互的时间维度。

## 核心元素

### 对象与生命线（Lifeline）

对象以矩形框表示，其下方的垂直虚线为生命线，表示对象的存在时间。对象命名有三种方式：
- `对象:类`（如 `order:Order`）
- `:类`（匿名对象）
- `对象`（省略类名）

### 激活条（Activation Bar）

生命线上的窄矩形条，表示对象正在执行某个操作的时间段。

### 消息类型

| 消息类型 | 含义 | PlantUML 语法 |
|---------|------|---------------|
| 同步消息 | 发送方等待返回 | `A -> B: msg` |
| 异步消息 | 发送方不等待返回 | `A ->> B: msg` |
| 返回消息 | 同步调用的返回 | `B --> A: result` |
| 回调消息 | 异步回调 | `B -->> A: callback` |
| 自关联消息 | 对象调用自身方法 | `A -> A: self` |

### 组合片段（Combined Fragment）

| 类型 | 关键字 | 说明 |
|------|--------|------|
| 选择 | `alt` | if-else 分支 |
| 选项 | `opt` | 可选执行（if without else） |
| 循环 | `loop` | 重复执行 |
| 并行 | `par` | 并发执行 |
| 中断 | `break` | 跳出循环 |
| 引用 | `ref` | 引用其他交互片段 |

## PlantUML 语法详解

### 基本时序图

```plantuml
@startuml
actor User
participant "Web App" as Web
participant "API Server" as API
database "Database" as DB

User -> Web: 点击下单
Web -> API: POST /orders
API -> DB: 保存订单
DB --> API: 返回订单ID
API --> Web: 201 Created
Web --> User: 显示下单成功
@enduml
```

### 激活条与嵌套调用

```plantuml
@startuml
actor User

User -> OrderService: createOrder()
activate OrderService

OrderService -> StockService: checkStock()
activate StockService
StockService --> OrderService: available
deactivate StockService

OrderService -> PaymentService: processPayment()
activate PaymentService
PaymentService --> OrderService: success
deactivate PaymentService

OrderService --> User: orderCreated
deactivate OrderService
@enduml
```

### alt 条件分支

```plantuml
@startuml
participant Client
participant Server

Client -> Server: 查询数据

alt 数据存在
    Server --> Client: 返回数据
else 数据不存在
    Server --> Client: 返回404
end
@enduml
```

### loop 循环

```plantuml
@startuml
participant Scheduler
participant Worker

loop 每10秒
    Scheduler -> Worker: 心跳检测
    Worker --> Scheduler: 响应
end
@enduml
```

### opt 可选片段

```plantuml
@startuml
participant User
participant System

User -> System: 登录

opt 首次登录
    System -> System: 初始化用户偏好
end

System --> User: 登录成功
@enduml
```

### par 并行执行

```plantuml
@startuml
participant Client
participant ServiceA
participant ServiceB

Client -> ServiceA: 请求A
activate ServiceA

par 并行调用
    ServiceA -> ServiceB: 异步调用B
else
    ServiceA -> ServiceA: 本地处理
end

ServiceA --> Client: 返回结果
deactivate ServiceA
@enduml
```

### ref 引用

```plantuml
@startuml
actor User
participant System

User -> System: 请求操作

ref over System
  用户认证流程
end ref

System --> User: 操作结果
@enduml
```

## 完整实战示例：电商下单流程

```plantuml
@startuml
actor "买家" as Buyer
participant "前端" as UI
participant "订单服务" as Order
participant "库存服务" as Stock
participant "支付服务" as Pay
database "数据库" as DB

Buyer -> UI: 提交订单
UI -> Order: createOrder(items)
activate Order

Order -> Stock: lockStock(items)
activate Stock

alt 库存充足
    Stock --> Order: locked
    deactivate Stock
    
    Order -> DB: saveOrder(PENDING)
    DB --> Order: orderId
    
    Order --> UI: 订单创建成功
    UI --> Buyer: 跳转支付页
    
    Buyer -> UI: 确认支付
    UI -> Pay: pay(orderId, amount)
    activate Pay
    Pay --> UI: 支付成功
    deactivate Pay
    
    UI -> Order: confirmPaid(orderId)
    Order -> Stock: deductStock(items)
    Order -> DB: updateOrder(PAID)
    Order --> UI: 支付确认
    
else 库存不足
    Stock --> Order: insufficient
    deactivate Stock
    Order --> UI: 库存不足
    UI --> Buyer: 提示库存不足
end

deactivate Order
@enduml
```

## 绘制注意事项

1. **划清边界**：明确交互场景的范围，不要无限延伸
2. **对象排列**：交互频繁的对象尽量靠拢；初始化交互的对象放最左端
3. **消息粒度**：关注核心交互，省略不重要的细节
4. **编号可选**：复杂图可为消息加编号以便引用
5. **异步标注**：明确区分同步调用和异步消息

## 适用场景

- 设计 API 调用流程和微服务交互
- 分析复杂业务逻辑的执行顺序
- 调试分布式系统交互问题
- 技术方案评审中的时序分析
