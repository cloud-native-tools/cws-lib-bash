# UML 状态机图

> 状态机图展示对象在其生命周期中响应事件的状态变化，适合描述状态流转逻辑。

## 核心概念

### 有限状态机（FSM）要素

- **状态（State）**：对象在某个时刻的条件或情况
- **事件（Event）**：导致状态转换的触发器（调用事件、信号事件、时间事件、变化事件）
- **转换（Transition）**：从一个状态到另一个状态的变化
- **守卫条件（Guard）**：转换发生的前置条件，用 `[条件]` 表示
- **动作（Action）**：转换时执行的操作，用 `/ 动作` 表示

### 状态类型

| 类型 | 说明 | PlantUML |
|------|------|----------|
| 初始状态 | 状态机入口（实心黑圆） | `[*] -->` |
| 终止状态 | 状态机结束（双环圆） | `--> [*]` |
| 简单状态 | 无子状态（圆角矩形） | `state 名称` |
| 组合状态 | 含有子状态 | `state 名称 { ... }` |
| 并发状态 | 正交区域 | `--` 分隔符 |

## PlantUML 语法详解

### 基本状态机

```plantuml
@startuml
[*] --> 未提交
未提交 --> 审批中 : 提交申请
审批中 --> 已通过 : 审批通过
审批中 --> 已拒绝 : 审批拒绝
已通过 --> [*]
已拒绝 --> [*]
@enduml
```

### 守卫条件与动作

```plantuml
@startuml
[*] --> Idle
Idle --> Processing : request [isValid] / log()
Processing --> Done : complete
Processing --> Error : exception / notify()
Error --> Idle : retry
Done --> [*]
@enduml
```

### 组合状态（子状态）

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

```plantuml
@startuml
[*] --> Active

state Active {
    state "网络模块" as Network {
        [*] --> Connected
        Connected --> Disconnected : 网络断开
        Disconnected --> Connected : 重新连接
    }
    --
    state "业务模块" as Business {
        [*] --> Idle
        Idle --> Working : 收到任务
        Working --> Idle : 任务完成
    }
}

Active --> [*] : 退出
@enduml
```

### 注释

```plantuml
@startuml
[*] --> 待支付

note right of 待支付
  用户下单后进入待支付状态
  需要在30分钟内完成支付
end note

待支付 --> 已支付 : 支付成功
已支付 --> [*]
@enduml
```

## 完整实战示例：电商订单状态机

```plantuml
@startuml
[*] --> 待支付 : 下单

state 待支付 {
    [*] --> 已创建
    已创建 --> 已取消 : 用户取消
}

待支付 --> 待发货 : 支付成功
待支付 --> 已关闭 : 超时未支付

待发货 --> 已发货 : 商家发货
待发货 --> 退款中 : 用户申请退款

已发货 --> 已收货 : 用户确认收货
已发货 --> 退款中 : 用户申请退款

退款中 --> 已退款 : 商家同意退款
退款中 --> 已发货 : 商家拒绝退款

已收货 --> 已完成 : 评价完成
已收货 --> 售后中 : 用户申请售后

售后中 --> 已完成 : 售后完成
已完成 --> [*]
已关闭 --> [*]
已退款 --> [*]

note right of 待发货
  支付成功后等待商家发货
  商家需在48小时内发货
end note
@enduml
```

## 状态机编程实现

### 方式一：枚举（简单场景）

每个枚举值实现转换逻辑，适用于状态少、逻辑简单的场景。

### 方式二：状态模式（GoF）

将每个状态封装为独立类，符合开闭原则，但类数量较多。

### 方式三：COLA StateMachine（推荐）

阿里开源轻量级框架，无状态、线程安全、流式 API：

```java
StateMachineBuilder<States, Events, Context> builder = 
    StateMachineBuilderFactory.create();

builder.externalTransition()
    .from(States.PENDING).to(States.PAID)
    .on(Events.PAY_SUCCESS)
    .when(checkCondition())
    .perform(doAction());

StateMachine<States, Events, Context> stateMachine = builder.build(ID);
States target = stateMachine.fireEvent(States.PENDING, Events.PAY_SUCCESS, ctx);
```

### 方式四：Spring State Machine

Spring 官方框架，支持层级状态、并行状态、持久化，适合复杂场景。

## 注意事项

1. **状态爆炸**：状态过多时使用组合状态（层级）简化
2. **事件幂等**：同一事件多次触发应保持幂等性
3. **持久化**：长期运行的状态机需考虑状态持久化
4. **异常路径**：不仅建模正常流程，也要覆盖异常和恢复

## 适用场景关键词

当需要表达以下内容时使用状态机图：
- "状态流转"、"生命周期"、"订单状态"
- "工作流状态"、"协议状态"、"UI组件状态"
- 任何对象在其生命周期中有明确状态变化的场景
