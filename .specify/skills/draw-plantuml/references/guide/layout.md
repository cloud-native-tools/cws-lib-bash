# PlantUML 布局指南

通过语义驱动布局、方向控制、分组和间距调整等技巧，使生成的 UML 图布局清晰、层次分明。同时包含 Graphviz 引擎行为规律和 PlantUML Server 限制的深度分析。

> **定位**：本文件是绘图**布局优化指南**，与 [style.md](./style.md)（统一样式配置）和 [content.md](./content.md)（内容组织与标签规则）互补。在 Step 4 规划布局和 Step 5 阅读最佳实践时**必须参照本指南**。

---

## 一、语义驱动布局

> **先分析语义，再动手布局。** 组件间的关系自带空间含义：1:N 的中心/边缘关系自然映射为"中心在上、边缘在下"；对等关系自然映射为"并排放置"。

### 1.1 组件角色分类

绘图前先将每个组件分类：

| 角色 | 说明 | 默认位置 | 典型元素 |
|------|------|---------|---------|
| **中心端 (Hub)** | 被多个组件连接的核心 | 中上方 | API Server、消息队列 |
| **节点端 (Edge)** | 1:N 连接中心的端点 | 中心下方 | kubelet、Agent、Worker |
| **对等端 (Peer)** | 同级、同功能的组件 | 并排 | Scheduler + Controller Manager |
| **入口 (Entry)** | 外部流量进入点 | 左侧或顶部 | Ingress、Gateway、LB |
| **汇聚端 (Sink)** | 数据终点、存储 | 右侧或底部 | DB、PV、Registry |
| **外部 (External)** | 系统边界之外 | 框架外侧 | Users、外部 API |

### 1.2 语义→布局映射

| 语义关系 | 布局规则 | PlantUML 实现 |
|---------|---------|--------------|
| 1:N (hub-spoke) | 中心在上，节点在下 | Hub 放入上层 frame，Edge 放入下层 node |
| 对等 (peer) | 并排同层 | `together {}` 包裹 |
| 链式 (chain) | 按流向排列 | 默认箭头 `-->` |
| 层次 (hierarchy) | 父上子下 | 嵌套 frame/node 容器 |

### 1.3 实践：先画位置草图

在写 PlantUML 之前，用文本画一张位置草图，标注每个组件的角色和大致位置。然后按草图的空间关系编写 PlantUML 代码——声明顺序应从上到下、从左到右，与位置草图一致。

---

## 二、布局优化

> 80% 的可读性问题源于元素位置混乱，**布局控制优先于样式美化**。

### 2.1 方向控制

用方向关键字明确连接线走向，避免自动布局导致的交叉：

```plantuml
' 强制方向指令（适用于所有关系线）
A -right-> B : 向右
A -down-> C : 向下
A -left-> D : 向左

' 缩写形式同样有效
A -r-> B
A -d-> C
A -l-> D
```

**核心原则**：
- 时序图：核心服务置左，辅助系统置右，**数据流从左到右**
- 组件图/部署图：主要依赖从上到下（配合 `top to bottom direction`）
- 活动图：主干流程垂直向下，分支水平展开

#### 方向决策规则（先算再选）

**在写代码前，先数两个量**，据此选方向——目标是让**元素多的那一维铺在屏幕更宽的水平方向**：

- **B（最宽层宽度）** = 同一层级并排兄弟节点的最大数量
- **D（主流深度）** = 从入口到汇聚端串起来的最长层数（最长链长度）

| 条件 | 结论 | 指令 |
|------|------|------|
| B ≥ D（宽而浅，兄弟多） | 保持默认自上而下，主流向纵向 | `top to bottom direction` |
| D ≥ 2·B（深而窄，长链） | 默认方向会又高又窄 → 把长链横过来 | `left to right direction` |
| B、D 接近（方形结构） | 默认自上而下即可，无需强改 | `top to bottom direction` |

> **反直觉提醒**：嵌套架构图里"层多"（深）往往被误当作"该用 TB"。恰恰相反——**深链用 LR 摊平、宽扇出用 TB**，才能贴近 16:9。改方向后务必重渲染核对（LTR 下方向提示会被重解释，见 §五 行为 1）。

### 2.2 隐藏连接线引导布局

通过 `-[hidden]->` 创建不可见连接，间接调整元素相对位置：

```plantuml
' 使 ServiceB 位于 ServiceA 右侧，但不显示连线
ServiceA -[hidden]right-> ServiceB

' 利用隐藏线构建网格布局
A -[hidden]-> B
A -[hidden]-> C
B -[hidden]-> D
```

### 2.3 分组与逻辑分区

#### `together{}` 绑定关联元素

```plantuml
' 认证模块紧密排列，不被自动布局分散
together {
  participant AuthService
  participant TokenService
  participant SessionStore
}
```

#### 泳道分区（活动图）

```plantuml
|前端|
:用户点击登录;
|API网关|
:验证Token;
|后端服务|
:处理业务逻辑;
```

#### 包/框架分区（组件图/部署图）

```plantuml
package "表示层" {
  [Web UI]
  [Mobile App]
}
package "业务层" {
  [Order Service]
  [User Service]
}
```

### 2.4 布线简化

#### 正交布线（直角转折）

```plantuml
' 仅保留直角转折，大幅减少视觉干扰
skinparam linetype ortho
```

> **注意**：`linetype ortho` 在复杂图中可能导致连线重叠，建议元素 >10 时测试效果再决定是否启用。

#### 间距调整

```plantuml
' 增大水平间距，避免元素重叠
skinparam nodesep 40

' 增大垂直间距，改善层次感
skinparam ranksep 60
```

**推荐参数**：
| 图表复杂度 | nodesep | ranksep |
|-----------|---------|---------|
| 简单（≤5元素） | 默认 | 默认 |
| 中等（6-10元素） | 30-40 | 40-60 |
| 复杂（11-15元素） | 40-60 | 60-80 |

### 2.5 宽高比控制（宽嵌套架构的核心）

理想宽高比（宽/高）落在 **4:3 (≈1.33) 至 16:9 (≈1.78)** 之间，便于在文档和屏幕中阅读。对 ~40 元素的宽嵌套架构图，这是决定成败的第一优先项。

#### 步骤一：估算列数与行数，先在纸上摆成近方形网格

PlantUML 默认框「含间距」约 **160px 宽 × 100px 高**（宽高比约 1.6:1）。因此像素宽高比 ≈ **(列数 C / 行数 R) × 1.6**。反推目标区间：

- 想要 16:9 (1.78)：C/R ≈ **1.1**
- 想要 4:3 (1.33)：C/R ≈ **0.83**

**结论：让框排成"接近正方形的网格"（C ≈ R，略偏宽），像素比就自然落在 4:3–16:9。** 别让某一维远大于另一维。

**列数速算公式**：`C ≈ round( sqrt(N × 1.3) )`，`R ≈ ceil(N / C)`。

| 元素数 N | 建议列数 C | 建议行数 R | 说明 |
|---------|-----------|-----------|------|
| ~12 | 4 | 3 | 单层网格即可 |
| ~20 | 5 | 4 | 分 2 个嵌套 frame |
| ~40 | 7 | 6 | 分 3–4 个嵌套 frame，每 frame 内再排小网格 |

> 对嵌套图，把公式用在**每个 frame 内部**：单个 frame 内元素也排成近方形小网格，避免 frame 内出现单列长条。

#### 步骤二：按估算结果匹配对策

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 极端竖长（比值 < 1.0） | 同类节点全部纵向堆叠，C 太小 | 用 `together{}` 把同级节点并排，增大 C；或对长链改 `left to right direction` |
| 极端竖长 | ranksep 过大 | 降低 `skinparam ranksep`（复杂图取 60，不要更高） |
| 极端横宽（比值 > 2.0） | 所有元素挤在同一层，C 太大 | 引入嵌套层次（frame/package/node）把宽扇出折成多行；降低 `nodesep` |
| 极端横宽 | 每层放了太多兄弟（C > 8） | 单层兄弟数控制在 **≤6**，超出的下沉为子层或拆 frame |
| 宽高失衡 | 方向指令与内容不匹配 | 见 §2.1 方向决策规则，按 B/D 重选方向 |

#### 步骤三：防止「一条长边把整张画布撑变形」

单条边会沿其方向单独顶开画布，是宽嵌套图变形的最隐蔽元凶。逐条排查：

| 长边类型 | 撑变形的方式 | 对策 |
|---------|-------------|------|
| **长标签边** | 标签文字宽度直接撑开该行/该列间距 | 标签压到 ≤10 字符，详情移入 `note`（见 content.md） |
| **跨多层直连边**（如顶层直接连到底层） | Graphviz 为容纳这条边，把中间所有层撑高/撑宽 | 让两端落在相邻层；或对该边用 `-[hidden]-` 只做布局、真实关系另画短边；必要时改走 `note` 说明 |
| **回边 / 反馈边**（下层指回上层） | 拉长主流方向，占满整条高度 | 保留但用虚线 `..>` 弱化；或用 `-[hidden]-` 不参与主流排序 |
| **跨 frame 长边** | 把两个 frame 强行拉远 | 相关 frame 相邻声明；跨 frame 边尽量少，用 1 条汇总边代替多条平行边 |

> **要点**：宽高比问题≠全局问题，往往是**一两条极端边**造成的。渲染后先找"最长的那条边/最宽的那个标签"，单独修它，通常一步到位。

**部署图专用技巧**：
- 多个 Worker Node / Pod 副本使用 `together{}` 水平排列，避免逐个垂直堆叠
- 搭配 `skinparam nodesep 30` 和 `skinparam ranksep 50` 在紧凑与可读性之间取得平衡
- Control Plane 和 Worker Node 分属不同 `frame`，自然形成上下两层而非单列

### 2.6 隐藏连线强制布局

当自动布局不满足语义要求时，使用 `-[hidden]->` 创建不可见连线来强制元素位置：

```plantuml
' 强制 API Server 在 Node 上方（hub 在 edge 上方）
api -[hidden]d-> node1

' 强制 PV 在 Registry 上方（对齐右侧 sink）
pv -[hidden]d-> reg

' 强制入口在左侧
users -[hidden]r-> ingress
```

**使用原则**：
- 先写所有隐藏连线（布局骨架），再写实际连线（语义关系）
- 隐藏连线的方向 (`r/d/l/u`) 决定元素相对位置
- 连接到容器别名（如 `n1`）而非容器内部元素（如 `kl1`），效果更稳定

### 2.7 虚线区分连线语义

通过线型区分不同语义的连线，降低视觉噪音：

| 线型 | PlantUML 语法 | 适用场景 |
|------|-------------|---------|
| **实线** | `-->` | 数据流、强依赖、请求响应 |
| **虚线** | `..>` | 控制信号、周期性检查、watch/report |
| **粗线** | `==>` | 关键路径、主数据流 |

```plantuml
' 数据流（实线）
service --> pod : ClusterIP

' 控制信号（虚线）
kubelet ..> apiserver : report

' 关键路径（粗线，按需使用）
users ==> ingress : HTTPS
```

---

## 三、按图表类型的布局速查

| 图表类型 | 推荐方向 | 布局重点 |
|---------|---------|---------|
| **组件图** | `top to bottom direction` | 按层分组（表示层/业务层/数据层），依赖从上到下 |
| **部署图** | `top to bottom direction` | 物理拓扑从外到内，网络层次从上到下；同级节点（如多个 Worker Node）用 `together{}` 并排，配合 `nodesep`/`ranksep` 控制间距，避免极端竖长比例 |
| **时序图** | 默认（左→右排列参与者） | `together{}` 将关联参与者分组，`order` 控制排列 |
| **类图** | `top to bottom direction` | 继承从上到下，组合/聚合水平排列 |
| **活动图** | 默认（上→下） | 泳道划分职责域，主干垂直、分支水平 |
| **状态机图** | 默认 | 初始状态在顶部，终止状态在底部 |
| **用例图** | `left to right direction` | Actor 在左，系统边界在右 |
| **包图** | `top to bottom direction` | 高层包在上，底层包在下 |

### 3.1 专项图表（非 UML）的布局要点

WBS / 甘特图 / 思维导图 / JSON / YAML 的布局由各自数据结构自动决定，**无法**用 `-[hidden]->`、`together{}` 等 UML 手段摆位。可控手段集中在**结构组织**与**方向/刻度**：

| 图表类型 | 布局重点 |
|---------|---------|
| **WBS / 思维导图** | 默认所有分支同侧展开会变得又高又窄；用 `<`/`>`（WBS）或 `left side`/`+`/`-`（思维导图）把约一半分支挂到另一侧，让根节点两侧均衡，得到接近正方形的紧凑长宽比。层级控制在 3~4 层，节点文字短，末端要点用 `_` 无框弱化。 |
| **甘特图** | 用 `-- 阶段 --` 分隔符把设计/开发/测试/上线切成区块；按时间跨度选 `printscale`（≤3 周 daily、1~4 月 weekly、半年以上 monthly/quarterly，可加 `zoom N`）让图宽适中；`today` 竖线 + 完成百分比呈现进度；横向很宽时优先输出 SVG（PNG 有 4096px 上限）。 |
| **JSON / YAML** | 结构越深，树向右铺得越开；保持结构平衡、压平不必要的中间层，超过 4~5 层考虑拆成多张图；用 `#highlight` / `# highlight` 聚焦关键路径引导视线；容易变宽，优先输出 SVG。 |

---

## 四、常见布局问题排查

| 现象 | 可能原因 | 解决方案 |
|------|---------|---------|
| 连线大量交叉 | 未指定方向 | 添加 `-right->`/`-down->` 方向指令 |
| 元素位置跳跃 | 自动布局分散 | 用 `together{}` 或 `-[hidden]->` 固定位置 |
| 图表过宽/过高 | 方向与内容不匹配，或单层兄弟过多 | 按 §2.1 方向决策规则重选方向，按 §2.5 把框排成近方形网格 |
| 一条边撑得画布很长 | 长标签边 / 跨多层直连边 | 见 §2.5 步骤三：压短标签、拆分跨层边或改 `-[hidden]-` |
| 图表过宽/过高 | 方向指令冲突 | 检查是否有互相矛盾的方向声明 |
| 文字重叠 | 间距不足 | 增大 `nodesep`/`ranksep` |
| 分组内元素跑出 | package/rectangle 内容过多 | 拆分为子图或减少分组内元素 |
| 正交线重叠 | `linetype ortho` 冲突 | 尝试移除 ortho 或调整元素顺序 |

---

## 五、Graphviz 布局引擎行为

> 以下行为均通过实际渲染对比验证。这些知识解释了 [10-layout-planning.md](../howto/10-layout-planning.md) 中布局故障排除指南背后的原因。按需加载，不必每次运行都读。

| # | 行为 | 影响 | 验证方法 |
|---|------|------|---------|
| 1 | `-right->` 在 `left to right direction` 下被 Graphviz 重新解释，可能产生垂直布局而非水平 | LTR 模式下主流向混乱 | 将 `-right->` 替换为 `-->`，布局从垂直恢复为水平 |
| 2 | Actor 连接 zone 内部元素时，zone 会扩展以视觉包含整个 actor 路径 | Zone 边界膨胀，布局变形 | 断开 actor→内部元素连接后 zone 恢复正常大小 |
| 3 | `together {}` 在嵌套 `rectangle` 内部可能不生效 | 分组元素无法对齐 | 将 `together {}` 移到 rectangle 外部后元素正确对齐 |
| 4 | `.down.>` 在 LTR 模式下方向不可预测，可能产生右向或斜向箭头而非垂直向下 | 垂直辅助连线位置错误 | 在 LTR 模式下测试 `.down.>`，对比默认方向模式下的结果 |
| 5 | 默认方向（top-to-bottom）+ `-right->` 时 Actor 分布优于 LTR 模式 | Actor 位置更分散、更自然 | 同一图表切换方向模式后观察 actor 从聚集变为分散 |
| 6 | `note` 附加在 zone 内元素上会扩展 zone 边界 | Zone 面积增大 2~3 倍 | 在添加 note 前后对比 zone 面积 |

### 行为 1 详解：`-right->` 在 LTR 模式下的重解释

```
' ❌ LTR 模式下使用 -right-> → 可能产生垂直布局
left to right direction
A -right-> B    ' Graphviz 重新解释此方向提示

' ✅ LTR 模式下使用 --> → 自动走右
left to right direction
A --> B         ' 主流向正确
```

**根因**：LTR 模式下 Graphviz 已经将"右"作为默认流向，额外的 `-right->` 方向提示被引擎视为冗余约束并可能重新解释为其他方向。

**对策**：LTR 模式下主流用 `-->`，垂直辅助连线用 `.down.>` / `.up.>`。

### 行为 2 详解：Actor-Zone 膨胀

```
' ❌ Actor 连接到 zone 内部元素 → zone 膨胀
rectangle "CI/CD Zone" as zone1 {
  component [Build] as build
}
actor "Developer" as dev
dev ..> build    ' zone1 扩展以包含 dev 的路径

' ✅ 方案A: 连接到 zone 容器本身
dev ..> zone1    ' zone1 不膨胀，但 dev 位置可能聚集

' ✅ 方案B: together 分组 + 垂直定位
together {
  actor "Developer" as dev
}
dev .down.> build   ' 需要测试实际效果
```

### 行为 3 详解：嵌套 rectangle 中 together 失效

```
' ❌ together 在嵌套 rectangle 内可能不生效
rectangle "Zone" {
  together {
    component [A]
    component [B]
  }
}

' ✅ 将 together 移到 rectangle 外部
together {
  component [A]
  component [B]
}
rectangle "Zone" {
  [A]
  [B]
}
```

---

## 六、PlantUML Server 限制

| 限制 | 影响 | 规避方式 |
|------|------|---------|
| **PNG 4096×4096 硬上限** | 大图被截断或返回全白 PNG | `render-plantuml.sh` 自适应计算 scale/dpi，目标 ≤ 4095 |
| **无 CJK 字体** | 中文字符零宽度渲染（textLength ≈ 4px） | `svg-to-png-cjk.cjs` 通过 Playwright 浏览器渲染 |
| **textLength 计算错误** | CJK 文字被压缩到几像素宽度 | 后处理移除 SVG 中的 `textLength` 和 `lengthAdjust` 属性 |
| **`note over X,Y` 仅限时序图** | 矩形图/组件图中报语法错误 | 使用 `note top/bottom/right/left of X` 替代 |

### CJK 渲染问题详解

**根因链**：
```
.puml → Graphviz → SVG（textLength 由字体 metrics 计算）
                         ↓
              server 无 CJK 字体 → fallback 字体返回近零宽度
                         ↓
              textLength ≈ 4px（应 ≈ 56px/4字）
                         ↓
              浏览器按 textLength 压缩文字 → 中文不可读
```

**五步修复管道**（`svg-to-png-cjk.cjs` 实现）：

| 步骤 | 操作 | 原因 |
|------|------|------|
| 1 | `sed` 移除 `textLength` 和 `lengthAdjust` 属性 | 错误的 textLength 强制浏览器压缩文字 |
| 2 | viewBox 宽度 ×2.5，高度 ×1.5 | CJK 文本正确渲染后宽度远超 server 预留 |
| 3 | 包装 HTML + CJK 字体栈 CSS | 通过 `!important` 覆盖 SVG 内嵌字体声明 |
| 4 | Playwright headless Chromium screenshot | 利用系统 CJK 字体正确计算排版 |
| 5 | JavaScript 计算所有 SVG 元素 bounding box → clip | 去除 viewBox 扩展后的空白区域 |

**CJK 字体栈**（覆盖主流平台）：
```css
svg text {
  font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei",
               "Noto Sans CJK SC", "WenQuanYi Micro Hei",
               Arial, Helvetica, sans-serif !important;
}
```

---

## 七、复杂图表的根本性三方权衡

通过 16 个版本的迭代验证，发现 PlantUML 中存在一个**根本性的三方权衡**：

```
          Zone 边框（虚线分组区域）
          /      \
         /        \
   Actor 分布 ---- 注释完整性
```

**三者无法在 PlantUML 中同时完美实现**：

| 策略 | Zone 边框 | Actor 分布 | 注释完整 | 典型得分 |
|------|----------|-----------|---------|---------|
| LTR + zones + actor→zone | ✅ 有 | ❌ 聚集 | ❌ 不全 | ~51/100 |
| LTR + zones + actor→内部 | ⚠️ 膨胀 | ⚠️ 受限 | ❌ 不全 | N/A |
| 默认方向 + zones + actor→内部 | ⚠️ 膨胀 | ⚠️ 混乱 | ✅ 全 | N/A |
| **默认方向 + 无zone + actor→元素** | ❌ 无 | ✅ 好 | ✅ 全 | **~70/100** |
| LTR + 无zone + actor→元素 | ❌ 无 | ⚠️ 一般 | ❌ 不全 | ~52/100 |

### 当前最优策略（70/100）

当需要同时处理多区域分组、Actor 定位和丰富注释时：

1. **使用默认方向**（top-to-bottom）+ `-right->` 实现水平主流向
2. **不使用 zone 虚线边框**，改用 `note` 标签或 `package` 替代视觉分组
3. **Actor 通过 `.down.>` / `.up.>` 精确定位**在管道上下方
4. **包含全部注释**，短标签用箭头标签 (`: text`)，长说明用 `note` 元素

### 何时可以突破权衡

如果图表**不需要**同时满足三个条件，可以适当放松：
- **不需要 zone 边框** → 可以用 LTR + actor→元素，actor 分布尚可
- **不需要 actor** → 可以用 LTR + zones，zone 边框完整
- **不需要丰富注释** → 任何策略都能工作

> **理论上限**（估计 ~85/100）：如果 PlantUML/Graphviz 未来支持"Actor 穿越 zone 边界而不影响布局"的特性，可以同时实现三者。目前受引擎限制无法突破。

---

## 八、版本演进关键转折点

以下转折点对理解引擎行为最有价值：

| 版本 | 转折 | 关键发现 |
|------|------|---------|
| v1→v2 | 全英文标签 → 中文化 | 发现 CJK 零宽度渲染问题 |
| v3 | 修复 `-right->` → `-->` | 发现 LTR 模式下方向提示被重解释 |
| v4→v5 | 无zone → 有zone | 发现 actor→内部元素导致 zone 膨胀 |
| v7 | LTR → 默认方向 | Actor 分布显著改善 |
| v10 | 回退到 LTR + zones | 评分从 59 退步到 51（actor 聚集 + 注释不全） |
| v12 | 回退到默认方向 + 无zone | 70/100 — 最完整的注释覆盖和最佳 actor 分布 |

---

## 扩展阅读

- **统一样式配置**：参见 [style.md](./style.md)
- **内容组织与标签规则**：参见 [content.md](./content.md)
- **PlantUML 语法参考**：参见 [syntax-reference.md](./syntax-reference.md)
- **布局规划操作指南**：参见 [10-layout-planning.md](../howto/10-layout-planning.md)
