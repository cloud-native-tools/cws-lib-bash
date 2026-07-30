# 布局规划指南

> 在编写 PlantUML 代码之前，分析组件间的语义关系以确定它们的自然位置。本指南是 [SKILL.md Step 4](../../SKILL.md) 的详细参考。

---

## 一、语义驱动布局基础

布局规划的基础是"语义驱动布局"——组件间的关系自带空间含义。完整的组件角色分类、语义→布局映射表和位置草图绘制方法，参见 [layout.md §一 语义驱动布局](../guide/layout.md)。

核心思路：
1. **识别组件角色**：Hub（中心端）、Edge（节点端）、Peer（对等端）、Entry（入口）、Sink（汇聚端）、External（外部）
2. **映射关系到布局**：1:many → 中心在上节点在下；对等 → 并排；链式 → 按流向；层次 → 父上子下
3. **先画位置草图**：用文本画粗略位置图，标注每个组件的角色和大致位置，然后按草图编写代码

---

## 二、多区域复杂布局

对于包含多个分组区域、水平流向、角色和丰富注释的图表，应用以下技巧：

### 2.1 虚线边框分组区域

使用 `rectangle "Zone Title" as zone_alias #line.dashed { ... }` 创建带虚线边框的视觉分区，将相关组件分组。

### 2.2 水平流向

在图表顶部使用 `left to right direction` 实现从左到右的流向布局（常见于管道型、数据流型和 DevOps 架构图）。

### 2.3 角色外置声明

在所有 `rectangle` 或容器块之外声明 `actor` 元素，使其作为独立的人形图标通过箭头连接到区域。

### 2.4 彩色强调文本

当区域标题或组件名需要彩色文本（如红色强调）时，在标签内使用 PlantUML 标记如 `<color:red>text</color>` 或 `<font color=red>text</font>`。注意**必须省略** `skinparam monochrome true`（见 [style.md](../guide/style.md)），否则颜色会被去除。

### 2.5 全面注释覆盖

复刻参考图时，包含所有文字注释——缺失注释会显著降低正确性。使用 `note top/bottom/left/right of <element>` 添加多行说明文字，使用**箭头标签**（`: short text`）添加简短连线标注。计算源图注释数量并验证输出匹配。

### 2.6 反馈/回流箭头

管道图通常有反馈循环（与主流向相反的箭头）。使用虚线箭头和描述性标签表示：`elementB ..> elementA : feedback label`。

---

## 三、布局故障排除

实践中发现的常见布局陷阱及解决方案：

### 3.1 `left to right direction` 模式下的方向箭头

使用 `left to right direction` 时，主流向使用普通 `-->`（自动走右）。**不要**使用 `-right->`，因为它会被重新解释并可能导致垂直布局。垂直于主流向的连接使用 `.down.>` 和 `.up.>`（带方向提示的点线样式）。

### 3.2 角色与区域的交互

当角色连接到虚线边框区域矩形**内部**的元素时，区域会扩展以视觉包含角色，导致布局变形。解决方案：
- 将角色连接到区域容器本身（`developer ..> zone1`）而非内部元素
- 或使用 `together {}` 单独分组角色，用 `.down.>` / `.up.>` 进行垂直定位

### 3.3 CJK 字体渲染

PlantUML 服务器通常缺少 CJK 字体，导致中文字符零宽度渲染。包含中文文字的图表：
- 使用配套脚本 `scripts/svg-to-png-cjk.cjs` 通过 Playwright 使用系统 CJK 字体渲染 PNG
- 在纯 CJK 标签周围添加填充空格：`"  业务系统  "` 给服务器合理的宽度度量
- 渲染管道：PlantUML 服务器 → SVG → 后处理（移除 textLength）→ Playwright → PNG

### 3.4 `note over` 仅限时序图

在组件/矩形图中，使用 `note top of X`、`note bottom of X`、`note right of X`、`note left of X` 替代 `note over X,Y`。

### 3.5 区域内的注释

附加在区域内元素上的注释会导致区域扩展以容纳注释。当源布局显示区域内注释时，这通常是期望行为。需提前规划注释位置以匹配源图。

### 3.6 默认方向下的角色定位

在默认（从上到下）方向中使用 `-right->` 实现水平流向时，角色通过 `.down.>` 和 `.up.>` 自然定位在管道上下方。这通常比 `left to right direction`（角色容易聚集）提供更好的角色分布。权衡：默认方向需要在每条主流箭头上显式使用 `-right->`。

### 3.7 嵌套 `rectangle` 中的 `together {}` 可能失效

当 `together {}` 放在嵌套 `rectangle` 块内时可能不生效，元素无法对齐。将 `together {}` 移到 rectangle 容器外部。

### 3.8 LTR 模式下 `.down.>` 方向不可预测

在 `left to right direction` 模式下，`.down.>` 可能产生右向或斜向箭头而非垂直向下。需测试实际效果或切换到默认方向模式进行垂直连接。

### 3.9 三方权衡

对于同时需要区域边框 + 角色定位 + 完整注释的复杂图表，参见 [layout.md §七](../guide/layout.md)。当前最优策略（70/100）：默认方向 + 无区域边框 + actor→元素 + 完整注释。

---

## 四、扩展阅读

- **基础布局规则与示例**：[layout.md §一 语义驱动布局](../guide/layout.md)
- **布局优化技巧**（方向控制、隐藏连线、分组、间距）：[layout.md §二 布局优化](../guide/layout.md)
- **引擎行为根因分析**：[layout.md §五–八](../guide/layout.md) — Graphviz 布局引擎行为规律、PlantUML Server 限制和三方权衡的详细分析
- **按图表类型的布局速查**：[layout.md §三](../guide/layout.md)
