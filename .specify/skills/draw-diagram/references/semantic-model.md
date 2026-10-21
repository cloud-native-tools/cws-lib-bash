# Logical Diagram Model（LDM）schema 与覆盖检查

> 前门与下层之间的交接契约：委派传 LDM + 目标/输出要求；验收按覆盖检查执行。

## Schema

```yaml
diagram_class: topology | uml-component | uml-deployment | uml-sequence | uml-class
               | flowchart | state | er | gantt | wbs | mindmap | dataviz | wireframe | freeform
elements:            # 节点/组件/步骤
  - { id, label, kind: node|service|data|actor|step, zone? }
relations:           # 有向边
  - { from, to, kind: depends|flows|calls|contains, label?, }
zones:               # 分区/分组/泳道
  - { id, label, members: [id], layout: equal-height|stack|grid|free }
layout_intent:   scattered | columns | hierarchical | cycle | grid | free
auto_layout_intent:   # auto-layout 引擎降级意图（无法兑现精确 x/y 时的逼近依据；可选，建议 geometry 类 SDS 填写）
  fallback_rank_order: { <zone-id>: [label] }   # 每 zone 内元素的降级秩序（rank 逼近顺序）
  routing_intent: straight-segments            # 直线段优先，禁止 zigzag elbow
  equal_height_priority: low | medium | high   # 分区等高优先于元素精确位置
style_intent:    monochrome | hand-drawn | theme-color | brand
weight_plan:     # 语义视觉强弱（注意力层级）：大模块边界 > 小模块边界 > 数据流
  tiers:         # 粗细+深浅编码权重；色相只编码语义路径，不编码权重
    - { t: T1, targets: zone-borders }        # 大区/顶层分区边界：最粗最深
    - { t: T2, targets: submodule-and-leaf-borders }   # 子模块/组件/叶元素边界
    - { t: T3, targets: flows }               # 数据流/依赖连线：最细最浅
    - { t: T4, targets: annotations }         # 注释/副标题：最浅
  key_paths: [relation-id]   # 关键路径在 T3 内用色相抬升；粗细封顶 = T2，不得反压结构
artifact_intent: static-embed | interactive-html | editable-whiteboard | repo-text | pixel-reproduction
fidelity_intent: reproduction | fresh        # 复刻既有图 vs 新建
interactivity_intent:    # 交互语义规约（不是备注字段）——形式分类/档位/默认值/验收判据 owner：本文件 § 交互语义与验收
  level: none | basic | rich
  forms: [hover | click | filter | expand-collapse | zoom-pan | brush | linked-highlight | dashboard]   # 可多选；level=none 时为空
editability_intent:   none | whiteboard-edit | text-edit
```

## 构建纪律

1. **带出处摘要先行**：富上下文（文档/代码/目标图）先产出摘要（组件、关系、分区、核心流程，逐条标出处），LDM 只从摘要 + 用户意图构建
2. **不臆造**：摘要没有的元素/关系不得进入 LDM；目标图看不清的结构标 `uncertain` 并在委派时声明
3. **复刻不改版**：`fidelity_intent=reproduction` 时 zones 的 layout 与 elements 的相对位置语义照抄源图（如 equal-height 分区、stagger 列），不得"优化"
4. **产物意图显式**：用户没说的 artifact_intent 按 tie-break 默认并在回报中声明假设
5. **强弱计划必做**：含多层结构的图（zones 非空或元素 >15）必须填 `weight_plan`——委派前把每个 zone/子容器/叶元素/边族分配到 T1–T4；**前门只决定「什么该更显眼」，引擎技能决定「怎么画粗」**（各引擎「强弱实现」小节）；全图单一线宽/单一边框粗细判不合格

## 交互语义与验收（interactivity_intent —— 可交互图表的前门规约）

`interactivity_intent` 把「图表随用户输入做出调整」落为**可验收的语义规约**。本节拥有**形式分类、
档位、默认值、验收判据**；交付形态（JS 资产策略 / 与共享渲染后端的解耦 / 浏览器验收）归
[delivery-contract.md](delivery-contract.md) § D7；各 form 在引擎内的实现归引擎层「交互实现」小节
（当前 d3js / echarts 设有）。三层互不复制。

### 形式分类（forms，8 类；粒度以「一次输入 → 一次可见变化」可判定为准）

| form | 用户输入 | 图的可见变化（判定点） |
|------|---------|----------------------|
| `hover` | 指针悬停图元 | 出现提示/高亮，移开消失 |
| `click` | 点击图元或图例项 | 选中态/详情出现，或可见集合开关 |
| `filter` | 操作筛选控件（图例/下拉/输入） | 可见元素或数据集合随之增减 |
| `expand-collapse` | 折叠/展开操作 | 分区/子树可见性切换（布局收拢或重排） |
| `zoom-pan` | 滚轮/捏合/拖拽画布 | 同一数据的视口缩放或平移 |
| `brush` | 框选范围 | 范围内图元高亮或筛选生效 |
| `linked-highlight` | 在任一面板交互 | 其他面板出现对应高亮/筛选 |
| `dashboard` | 工具栏/跨图操作 | 多图作为整体响应同一输入（toolbox/联动） |

### 档位（level）

| 档位 | 判据 |
|------|------|
| `none` | `forms` 为空：静态交付，零交互义务（用户未表达交互诉求时的默认值；既有静态路径不变式） |
| `basic` | `forms` 恰含 `hover` 或 `click` 之一（单形式最小交互） |
| `rich` | `forms` ≥ 2，或含任一「改图类」形式（`filter` / `expand-collapse` / `brush` / `linked-highlight` / `dashboard`） |

### 默认值（用户没说全时按此取值，并在回报中声明假设——构建纪律 4 同规）

- 用户**未表达交互诉求** → `level: none`，不默认添加交互。
- 用户要求**可交互**但未点名形式 → `level: rich` + `forms: [hover, click, filter]`，`artifact_intent` 同步取 `interactive-html`；回报声明假设。
- 用户点名**仪表板/联动** → `forms` 含 `dashboard`；点名任意具体形式 → `forms` 照抄点名，未点名的维度不添加。
- 边界：**动画/动图/视频不是交互形式**——forms 分类里没有它们的位置，不得作为任何 form 的实现。

### 验收判据（Step 4 / 覆盖检查「交互」维度的判定规则）

1. **逐 form 复现**：每个声明 form 复现一次「输入 → 可见变化」即通过；任一声明 form 无法复现 → 该维度不覆盖。
2. **动画不算交互**：过渡/动效只是反馈的形态；无输入驱动的自动播放不满足任何 form。
3. **控件在而无效不算实现**：事件未绑定、状态未更新、点了没反应 = 未实现。
4. **代码证据口径**：无法亲自操作的验收环境（无头/静态检查），以「事件绑定 → 状态更新 → 渲染更新」闭合链路的代码证据替代逐项复现，并在回报中注明所用口径。
5. **未声明的交互不构成缺陷**；已交付的交互须在说明中列出（交付契约 § D7.3）。
6. `level: none`：零交互义务，不因缺交互判不覆盖。

## 覆盖检查（Step 4 验收）

| 维度 | 通过判据 |
|------|---------|
| 元素 | 数量与标签集合一致（`uncertain` 项已声明） |
| 关系 | 边集合一致且方向一致（hub-spoke 的扇出数一致） |
| 分组 | zone 成员与边界语义一致（equal-height 等 layout 语义保留） |
| 产物形态 | 与 artifact_intent 匹配（可编辑/交互/文本/静态） |
| 强弱 | `weight_plan` 层级在产物中可辨：边框粗细/深浅按 T1>T2>T3 递减、流线最细最浅；关键路径仅色相抬升且粗细 ≤ T2；全图单一线宽判不合格 |
| 风格 | 与 style_intent 匹配（monochrome 复刻不得引入彩色主题） |
| 交互 | `level ≠ none` 时逐声明 form 可复现一次「输入 → 可见变化」（判据见 § 交互语义与验收）；`level = none` 零交互义务 |

## Geometry（几何层 —— 语义层产出，语法层实现）

```yaml
canvas: { w: <px>, h: <px> }          # SDS 声明的画布尺寸
elements:
  - { id, box: { x, y, w, h } }       # 每图元目标位置与大小(px, 左上角原点)
zones:
  - { id, box: { x, y, w, h }, layout: equal-height|stack|grid|free }
relations:
  - { from, to, anchor: edge-midpoint|corner|auto, gap: <px> }
```

纪律：
1. 几何是**语义决策**（谁和谁同区、谁居中、分区等高、列错位），不是引擎语法——由 draw-diagram 产出
2. 复刻类请求：几何从源图测量得来（像素测量或比例估算），照抄源版面语义
3. 新建类请求：先规划网格（列宽/行高/间距/枢纽居中/上下游排布），再落坐标；文本宽度按 CJK≈fontSize×字数、ASCII≈fontSize×0.6×字数 预留

## Visual Weights / weight_plan（视觉权重语义 —— "应该画多显眼"，不是"怎么画"）

有序档位表（与 SKILL.md `weight_plan` 术语对齐；多层结构图必填）：

| 档位 | 语义角色 | 默认相对线宽 |
|------|---------|-------------|
| T1 | 大模块/分区边界（结构强弱关系的"强"） | 3.0 |
| T2 | 小模块/组件/叶元素边界；关键路径仅色相抬升、线宽 ≤ T2 | 2.0 |
| T3 | 数据流/依赖连线（"弱"） | 1.5 |
| T4 | 注释/副标题 | 1.0 |

1. 语义层只声明**档位与相对层级**（如"组件边界应比数据流线更显眼，以突出结构强弱关系"→ T1>T3）
2. 语法层在各引擎「强弱实现」小节把相对层级落实为绝对线宽/颜色/虚实（"如何画粗线且画好粗线"）
3. typography 层级同构：zone-title > element-label > annotation（相对字号由语义层声明，绝对字号由语法层落实）

## Deviation Declaration（语法层偏离声明规则）

1. 绝对坐标引擎（d3js / echarts layout:'none' / excalidraw 场景 JSON / drawio mxGraph 几何）：MUST 精确实现 SDS 几何与权重，预期零偏离
2. 自动布局引擎（mermaid / plantuml）：以脚手架/skinparam **逼近** SDS 几何；无法兑现项（如精确 x/y、等高分区）MUST 在结果清单中**量化声明**（偏离维度 + 幅度 + 原因）
3. 未声明的偏离 → 按 semantic-fidelity 扣分；已声明的偏离 → 计入该引擎语法实现质量，不计为语义层缺陷
4. **超界判据**：声明偏离超出 SDS 给定 bound（如 ±150px）时——SDS 含 `auto_layout_intent` 而引擎未利用 → 计**语法层**缺陷；SDS 缺该意图 → 计**语义层**缺陷（建模方漏声明降级秩序）

任一维度不通过 → 带 delta 说明再委派一次（上限 1 次）；仍不通过 → 如实回报产物与缺口，不粉饰。
