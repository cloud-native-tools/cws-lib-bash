# 如何画状态机图 (State Machine Diagram)

> 状态机图描述单个对象在其生命周期中响应事件所经历的状态序列，展示对象"有哪些状态，在什么条件下如何变化"。是订单系统、审批流程、协议设计等场景的核心建模工具。

## 状态机图的用途

状态机图回答的是"这个对象有哪些状态，什么事件触发状态变化，变化时做什么"：
- 消除复杂的 if-else/switch 状态判断逻辑
- 为订单、审批、工单等有明确生命周期的对象建模
- 设计通信协议的状态握手和传输过程
- UI 组件状态设计（按钮的 enabled/disabled/loading）
- 工作流引擎的状态流转规则

## 核心概念

### 有限状态机（FSM）五要素

| 要素 | PlantUML 语法 | 说明 |
|------|-------------|------|
| **状态 (State)** | `state 状态名` 或直接写状态名 | 对象在某个时刻的条件 |
| **事件 (Event)** | 箭头上的文本 | 触发状态转换的外部/内部刺激 |
| **转换 (Transition)** | `-->` | 从一个状态到另一个状态的变化 |
| **守卫条件 (Guard)** | `[条件]` | 转换发生的前置条件 |
| **动作 (Action)** | `/动作` | 转换时执行的操作 |

完整转换语法：`状态A --> 状态B : 事件 [守卫条件] / 动作`

### 状态类型

| 类型 | 表示 | 说明 |
|------|------|------|
| 初始状态 | `[*]` | 黑色实心圆，状态机的唯一入口 |
| 终止状态 | `[*]` | 双环圆，状态机结束（可有多个） |
| 简单状态 | 圆角矩形 | 没有子状态的基本状态 |
| 组合状态 | 包含子状态的大状态 | 层次化组织相关状态 |
| 并发状态 | `--` 分隔的并行区域 | 多个子状态机同时运行 |

### 状态内部行为

```plantuml
@startuml
state 待支付 {
  [*] --> 已创建
  已创建 : entry / 启动支付计时器(30min)
  已创建 : do / 等待支付
  已创建 : exit / 停止计时器
}
@enduml
```

- **entry**：进入状态时执行的动作
- **do**：在状态驻留期间持续执行的活动
- **exit**：离开状态时执行的动作

## PlantUML 语法

### 基本状态机

```plantuml
@startuml
[*] --> 未提交
未提交 --> 部门经理审批中 : 提交申请
部门经理审批中 --> HR审批中 : 审批通过
部门经理审批中 --> 已拒绝 : 审批拒绝
HR审批中 --> 审批完成 : 审批通过
HR审批中 --> 已拒绝 : 审批拒绝
审批完成 --> [*]
已拒绝 --> [*]
@enduml
```

### 含守卫条件的状态机

```plantuml
@startuml
[*] --> New
New --> Runnable : start()
Runnable --> Running : 获取CPU时间片
Running --> Runnable : yield() / 时间片用完
Running --> Blocked : wait() / IO阻塞
Blocked --> Runnable : notify() / IO完成
Running --> Terminated : run()结束
Terminated --> [*]
@enduml
```

### 组合状态（层次化）

```plantuml
@startuml
[*] --> Active

state Active {
  [*] --> Idle
  Idle --> Processing : 接收请求
  Processing --> Idle : 处理完成
  Processing --> Error : 处理异常
  Error --> Idle : 重试
}

Active --> Shutdown : 关闭命令
Shutdown --> [*]
@enduml
```

### 并发状态（正交区域）

两个独立的子状态机同时运行，用 `--` 分隔：

```plantuml
@startuml
[*] --> Active

state Active {
  state "网络模块" as Net {
    [*] --> Connected
    Connected --> Disconnected : 网络断开
    Disconnected --> Connected : 重新连接
  }
  --
  state "业务模块" as Biz {
    [*] --> Idle
    Idle --> Working : 收到任务
    Working --> Idle : 任务完成
  }
}

Active --> [*] : 退出
@enduml
```

## 完整 PlantUML 示例

### 订单状态机（经典案例）

```plantuml
@startuml
' Semantic: Entry=[*], Hub=买家已付款, Edge=退款中/卖家已发货, Sink=交易成功/已关闭

skinparam state {
  BackgroundColor LightBlue
  BorderColor DarkBlue
}
skinparam nodesep 30
skinparam ranksep 40

[*] --> 等待买家付款 : 下单

' 隐藏连线控制状态排列顺序
等待买家付款 -[hidden]r-> 买家已付款

' == 正常路径 ==
等待买家付款 --> 买家已付款 : 付款成功
买家已付款 --> 卖家已发货 : 卖家发货
卖家已发货 --> 交易成功 : 买家确认收货
卖家已发货 --> 交易成功 : 自动确认收货(超时7天)

' == 取消路径 ==
等待买家付款 --> 已关闭 : 超时未付款 / 买家取消

' == 退款路径 ==
买家已付款 --> 退款中 : 买家申请退款
卖家已发货 --> 退款中 : 买家申请退款
退款中 --> 买家已付款 : 卖家拒绝退款
退款中 --> 退款成功 : 退款完成

' == 售后路径 ==
交易成功 --> 售后维权 : 买家发起售后
售后维权 --> 交易成功 : 维权关闭

' == 终止状态 ==
交易成功 --> [*]
已关闭 --> [*]
退款成功 --> [*]
@enduml
```

### Java 线程状态机

```plantuml
@startuml
[*] --> NEW : Thread创建

NEW --> RUNNABLE : start()

state RUNNABLE {
  [*] --> READY
  READY --> RUNNING : 获取CPU时间片
  RUNNING --> READY : yield() / 时间片用完
}

RUNNABLE --> BLOCKED : 等待synchronized锁
BLOCKED --> RUNNABLE : 获取到锁

RUNNABLE --> WAITING : wait() / join() / park()
WAITING --> RUNNABLE : notify() / unpark()

RUNNABLE --> TIMED_WAITING : sleep(n) / wait(n)
TIMED_WAITING --> RUNNABLE : 超时 / notify()

RUNNABLE --> TERMINATED : run()执行完毕 / 异常退出
TERMINATED --> [*]
@enduml
```

## 状态机图的编程实现

### 方式一：枚举状态机（简单场景）

```java
public enum State {
    PENDING {
        @Override
        State transition(String event) {
            if ("PAY".equals(event)) return PAID;
            if ("CANCEL".equals(event)) return CANCELLED;
            return this; // 保持当前状态
        }
    },
    PAID {
        @Override
        State transition(String event) {
            if ("SHIP".equals(event)) return SHIPPED;
            if ("REFUND".equals(event)) return REFUNDING;
            return this;
        }
    },
    // ...
    ;
    abstract State transition(String event);
}
```

### 方式二：状态模式（GoF 设计模式）

将每个状态封装为独立类，符合开闭原则，类数量随状态增长。

### 方式三：COLA StateMachine（推荐）

阿里开源的轻量级状态机框架：

```java
StateMachineBuilder<States, Events, Context> builder =
    StateMachineBuilderFactory.create();

builder.externalTransition()
    .from(States.PENDING)
    .to(States.PAID)
    .on(Events.PAY_SUCCESS)
    .when(checkBalance())
    .perform(createPayment());

StateMachine<States, Events, Context> machine = builder.build("order");
States target = machine.fireEvent(States.PENDING, Events.PAY_SUCCESS, context);
```

## 状态机图建模步骤

1. **确定建模对象**：哪些对象有复杂的生命周期？（订单、审批、连接、工单）
2. **列举所有状态**：穷尽对象可能处于的所有关键状态
3. **识别初始和终止状态**：对象的起点在哪？哪些是终点？
4. **定义转换路径**：每个状态在什么事件下切换到哪个状态
5. **添加守卫条件**：同一事件在不同条件下是否走向不同状态？
6. **标注动作**：状态转换时或状态驻留时需要执行什么动作？
7. **检查完整性**：所有状态是否都能从初始状态到达？是否都能到达终止状态？有没有死锁？

## 语义布局分析

> 状态机图的语义角色映射：

| 语义角色 | 含义 | 典型状态 |
|---------|------|---------|
| **Entry (入口)** | 初始状态 | `[*]` (初始伪状态) |
| **Hub (中心)** | 核心稳定态（停留最久） | 已付款、进行中、Active |
| **Edge (边缘)** | 过渡态（短暂停留） | 处理中、验证中、Pending |
| **Sink (汇聚)** | 终止状态 | `[*]` (终止伪状态)、已完成、已取消 |
| **Peer (对等)** | 并行子状态 | 复合状态内的正交区域 |

**位置草图**：
```
[Entry: [*]]
     ↓
[Edge: 等待中]
     ↓
[Hub: 已付款]  ←→  [Edge: 退款中]
     ↓                    ↓
[Edge: 已发货]      [Sink: 已退款]
     ↓
[Sink: 已完成]  →  [Sink: [*]]
```

**布局技巧**：
- 使用隐藏连线控制状态位置：`待付款 -[hidden]r-> 已付款` 强制左右排列
- `..>` 用于内部转换（entry/do/exit），`-->` 用于外部状态转换
- 按路径分组箭头：正常路径、取消路径、退款路径

**布局优化要点**：
- **语义驱动布局**：初始态（Entry）在左上/上方，核心稳定态（Hub）居中，终止态（Sink）在右下/下方
- **隐藏连线**：`stateA -[hidden]r-> stateB` 强制状态水平/垂直排列，控制状态机的整体走向
- **虚线区分转换类型**：`..>` 用于内部转换（entry/do/exit），`-->` 用于外部状态转换
- **按路径分组**：将转换按业务路径分组注释（正常路径、异常路径、回退路径），代码结构映射状态语义
- **复合状态**：使用 `state "名称" { ... }` 表示嵌套状态，等价于 `together{}` 的分组效果
- **间距**：`skinparam nodesep 30`、`skinparam ranksep 40` 适合状态机的紧凑布局

## 最佳实践

- **只对有复杂生命周期的对象建模**：简单 CRUD 对象不需要状态机（如"已读/未读"用 boolean 就够了）
- **状态要穷尽**：覆盖对象的所有可能状态，包括异常状态
- **转换要有明确的触发事件**：每个箭头都要标注是什么事件触发了这次转换
- **使用守卫条件而非拆分状态**：同事件不同结果用 `[条件]`，而非创建多个几乎相同的状态
- **使用组合状态避免状态爆炸**：当子状态过多时将相关状态封装为组合状态
- **验证终止性**：确保不存在死锁（无法到达终止状态）和活锁（无限循环）
- **区分 Entry/Do/Exit**：进入时初始化、驻留时持续监控、离开时清理
- **事件要幂等**：同一事件多次触发，状态机行为应保持一致

## 状态机图与活动图的区别

| 维度 | 状态机图 | 活动图 |
|------|---------|--------|
| 关注点 | 一个对象的**状态变化** | 一个业务流程的**步骤顺序** |
| 核心元素 | 状态（State）、转换（Transition） | 活动（Action）、控制流 |
| 驱动方式 | 事件驱动（被动等待事件） | 流程驱动（步骤自动推进） |
| 典型问题 | "订单支付后变成什么状态？" | "下单流程需要经过哪些步骤？" |
| 受众 | 开发者、领域专家 | 业务分析师、产品经理 |
