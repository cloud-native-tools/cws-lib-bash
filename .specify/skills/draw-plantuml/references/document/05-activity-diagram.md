# UML 活动图

> 活动图展示业务流程、工作流或算法的控制流和数据流，支持并发与多角色协作。

## 概述

活动图是 UML 中的行为图，本质上是增强版流程图，着重表现从一个活动到另一个活动的控制流。它的独特优势在于能够表示并发活动和多角色泳道。

**优点**：描述并发行为、识别问题领域中的关键对象
**局限性**：不能直接展示对象协作、可能导致类职责混乱

## 核心元素

| 元素 | 说明 | PlantUML 语法 |
|------|------|--------------|
| 开始节点 | 流程起点（实心黑圆） | `start` |
| 结束节点 | 流程终点（双环圆） | `stop` |
| 活动（Action） | 一个具体操作步骤 | `:动作名;` |
| 控制流 | 连接活动的有向箭头（实线） | `->` 或 `-> 标注;` |
| 对象流 | 活动与对象的依赖（虚线） | `-[dashed]->` |
| 决策（Decision） | 条件分支（菱形） | `if ... then ... else ... endif` |
| 合并（Merge） | 任一分支到达即继续 | `endif` |
| 分叉（Fork） | 开启并行分支 | `fork` |
| 汇合（Join） | 所有分支到达才继续 | `end fork` |
| 泳道（Swimlane） | 划分不同对象的职责 | `\|泳道名\|` |

## PlantUML 语法详解

### 条件判断

```plantuml
@startuml
start
:归还图书;
if (是否超期) then (超期)
    :支付罚金;
else (未超期)
endif
stop
@enduml
```

### 并行处理

`end fork`：所有分支完成才继续（类似 CountDownLatch.await）
`end merge`：任一分支完成即继续

```plantuml
@startuml
start
fork
  :行为 1;
fork again
  :行为 2;
fork again
  :行为 3;
end fork
:所有完成后的操作;
stop
@enduml
```

### 泳道

```plantuml
@startuml
|客户|
start
:提交申请;
|审批人|
:审核申请;
if (通过?) then (是)
    |系统|
    :执行操作;
else (否)
    |客户|
    :收到拒绝通知;
endif
stop
@enduml
```

### 对象流

```plantuml
@startuml
start
:创建订单;
-[dashed]-> 订单对象;
:__订单__]
-[dashed]-> 传递给支付;
:处理支付;
stop
@enduml
```

### 连接器与中断

```plantuml
@startuml
start
:操作A;
if (条件) then (满足)
    :正常流程;
else (异常)
    (A)
    detach
    (A)
    :异常处理;
    stop
endif
stop
@enduml
```

## 完整实战示例：电商订单处理

```plantuml
@startuml
|会员|
start
:选择商品加入购物车;
|系统|
:产生订单;
fork
    :核对信用卡;
    if (余额) then (充足)
        :付款;
    else (不足)
        (A)
        note right: 连接器
    endif
fork again
    :核对库存数量;
    if (库存) then (充足)
        :发送商品;
    else (不足)
        (A)
        detach
        (A)
        :取消订单;
        :其他流程;
        stop
    endif
end fork
stop
@enduml
```

## 活动图 vs 流程图

| 类型 | 特点 |
|------|------|
| 基础流程图 | 简单顺序步骤，无并发 |
| 活动图 | UML 规范，支持并发、泳道、对象流 |
| 业务流程图 | 带泳道的流程图，表述多角色业务流程 |
| 任务流程图 | 无泳道，表述单一任务步骤 |

## 适用场景关键词

当需要表达以下内容时使用活动图：
- "业务流程"、"审批流程"、"工作流"
- "算法步骤"、"并发处理"、"多角色协作流程"
- 任何需要展示并行执行或泳道分工的场景

## 建模最佳实践

1. 明确活动的粒度——每个活动是一个有意义的完整操作
2. 涉及多参与者时使用泳道明确职责
3. 在分支处清晰标注判断条件
4. 区分控制流（实线）和对象流（虚线）
5. 过于复杂时考虑拆分为多个子活动图
