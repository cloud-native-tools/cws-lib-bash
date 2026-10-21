# D3.js Data Visualization Skill

Create interactive data visualizations using D3.js (Data-Driven Documents), output as a self-contained HTML file that can be opened directly in any modern browser.

## SDS 实现与强弱落地

本技能是 draw-* 家族的**语法层**：语义层 `draw-diagram` 拥有 SDS（Semantic Drawing Spec = 逻辑模型 + 几何 + `weight_plan` 档位 + typography 层级），本技能只拥有 **D3 语法、SDS 实现、渲染质量实践、偏离逼近**。

1. **输入契约**：受委派时调用方传入 **SDS 文件路径**（+ 目标/输出要求）——读 SDS，不重推 SDS。**MUST NOT 改写语义**：几何（canvas / 每图元 `box{x,y,w,h}` / 分区盒 / 关系锚点）、`weight_plan` 档位归属、分区布局语义均由语义层决定。仅无 SDS 的直接调用（standalone）才在本地规划版面。
2. **强弱实现**（SDS 相对档位 → D3 绝对 stroke-width；本表为规范值，理由与深浅/字号阶梯见 references/sds-realization.md §2）：

   | 档位 | 语义角色（SDS 声明） | D3 绝对线宽 |
   |------|----------------------|-------------|
   | T1 | 大模块/分区边界 | 2.5px |
   | T2 | 小模块/组件边界（关键路径粗细封顶 = T2，只抬色相） | 2.0px |
   | T3 | 数据流/依赖连线 | 1.6px |
   | T4 | 注释/副标题 | 1.2px |

   **复刻型 SDS**（`fidelity_intent: reproduction`）携带**源图实测线宽/字号/色值**，实测值**覆盖**上表默认——照抄实测，不得归一化回默认档位。
3. **几何**：d3js 是**绝对坐标引擎** → **MUST 精确兑现 SDS 的每个 box，预期零偏离**（不启力导向重排、不用 margin 约定平移已声明坐标）；运行时不可避免项（字体度量致文本溢出）先在 box 内近似，再量化声明。
4. 像素测量管线、viewBox 对齐、固定坐标 data-join、锚点计算、校验三关（`validateCoords` + `validateAgainstSDS` + 复刻型的渲染读回 ↔ 源图差量）、偏离策略：[references/sds-realization.md](references/sds-realization.md)。

## 交互实现（interactivity_intent → D3 交互）

语义层在 SDS 中声明**要什么交互**（`interactivity_intent.level` + `forms`；形式分类、档位、默认值与逐 form 验收判据 owner：[semantic-model.md](../../semantic-model.md) § 交互语义与验收，此处不复写）。本节只拥有**怎么实现**：form → D3 配方、产物形态、实现义务。MUST NOT 增删或改判声明的 forms；`level: none` 时零交互义务（不顺手加交互，与 Core Principle 4 一致）。

### 形式 → D3 配方（引擎语法，本节 owner）

| form | D3 实现配方族 |
|------|--------------|
| `hover` | `selection.on('mouseover'/'mousemove'/'mouseout')` 驱动 tooltip 元素或高亮 class |
| `click` | 点击选中态（class toggle / 详情面板）；图例项点击 → 该系列 data-join 重绘 |
| `filter` | 筛选控件（checkbox/select）→ 更新绑定数据 → `enter/update/exit` 重绘 |
| `expand-collapse` | 分区容器显隐切换或子树重算，折叠状态持久在状态对象中 |
| `zoom-pan` | `d3.zoom()` 绑定 svg，作用于 viewBox / `<g>` transform |
| `brush` | `d3.brush()` → 范围内图元高亮，或作为筛选条件驱动重绘 |
| `linked-highlight` | 多面板共享状态对象，一处事件更新其他面板的 class/筛选 |
| `dashboard` | 多 SVG 共享筛选状态 + 上述形式的组合 |

### 义务与产物形态

1. **链路闭合**：每个声明 form 必须事件绑定 → 状态更新 → 渲染更新三环齐全；缺环 = 该 form 未实现（验收判据见 semantic-model § 交互语义与验收，"控件在而无效不算实现"）。
2. **库加载按交付契约 § D7.1 三选一并声明**：single-file 模式默认 CDN（`https://d3js.org/d3.v7.min.js`）须在复现性附录声明「首开需联网」；离线交付走 split/vendored 模式（既有 Core Principle 2 的两种输出模式即该表两种策略的本引擎实现）。
3. **过渡不是交互**：`d3.transition` 等动效只作反馈增强，不作为任何 form 的达标形态（无输入驱动的自动播放不满足判据）。
4. **既有交互长处与声明 forms 并存**：常显边标签开关、`?clean=1` 静态快照、导出 SVG/PNG 等既有能力照常提供；声明之内的 forms 一个都不能少，声明之外的不作为验收点。
5. **交付说明**：列出实际具备的交互与触发方式（使用说明不属于交付契约 D4 禁止的图例式解说；其余文字规则 D3–D5 照常适用）。

## Core Principles

### 1. Data-Driven Design
Every visualization must start from data. Choose the chart type that best reveals patterns, trends, or relationships in the user's data. Avoid decorative elements that don't serve the data story.

### 2. Self-Contained Output
Default output is a **single HTML file** with all D3.js code and styles inline, so it works by simply opening in a browser. Two output modes are supported:

- **Single-file mode (default)**: all code, styles, and data inline; D3.js v7 loaded from CDN (`https://d3js.org/d3.v7.min.js`). Best for quick sharing and portability.
- **Split mode (for maintainability / offline reproducibility)**: keep data in a separate local `data.js` or `data.json` next to the HTML, and optionally vendor D3.js locally (download `d3.v7.min.js` beside the HTML and reference it by relative path). Choose split mode when the dataset is large, the chart will be edited repeatedly, or the output must render without CDN access. State the chosen mode in the deliverable explanation.

### 3. D3.js Best Practices
Use D3.js v7 (latest stable). Follow the data-join pattern (`enter/update/exit`), use proper scales and axes, implement responsive SVG with `viewBox`. See [d3js-guide.md](references/d3js-guide.md) for syntax and patterns.

### 4. Progressive Enhancement
Start with a clean, functional visualization. Add interactivity (tooltips, transitions, zoom) only when it serves the user's needs or when explicitly requested.

### 5. Engine-Unique Capability（本引擎独占，语法层全权）
- **像素级复刻**：绝对坐标 SVG 控制、无布局引擎干预 → 源图 1:1 重现（实测坐标 / 线宽 / dash / 字号 / 单色调色板）。管线见 [references/sds-realization.md](references/sds-realization.md) §3.4、§5。
- **bespoke 交互**：超出标准图表目录的自定义交互——常显边标签开关、`?clean=1` 静态快照、拖拽微调、分区折叠、导出 SVG/PNG。
- 图型选择与语义判定不归本技能：见 § SDS 实现与强弱落地（由 `draw-diagram` 的 SDS 决定）。

## Workflow

This skill creates D3.js data visualizations based on user-provided data and requirements. Follow the steps below in order.

### Step 1: Understand Data & Requirements

Analyze the user's input to determine:

1. **Data structure**: What format is the data in? (CSV, JSON, array, table, markdown table, etc.)
2. **Data dimensions**: How many variables? Categorical vs quantitative? Time-series?
3. **Visualization goal**: What story should the chart tell? (comparison, trend, distribution, relationship, composition, hierarchy)
4. **Interactivity needs**: Static or interactive? Tooltips, zoom, filter, animation?
5. **Multi-chart needs**: Does the user need multiple perspectives? 有 SDS 时图型集合与画布/分区几何照 SDS 执行；仅 standalone 时本地规划 dashboard 版面。

Data format handling:
- If data is in a markdown table or plain text table, parse it into a JSON array
- If data has Chinese headers, preserve them as labels
- If data volume is large (>100 rows), consider aggregation or sampling before visualization

If critical information is missing, ask **one targeted question**.

### Step 2: Choose Chart Type

> **SDS 在场时不重选图型**：`diagram_class`、需要的图型集合与覆盖判定已由语义层（draw-diagram）决定并写入 SDS；本步骤退化为"该图型对应哪段 D3 配方"的查表。下表是 **standalone（无 SDS）直接调用**时的决策索引，同时也是本引擎的能力清单。

Match data characteristics and goals to the appropriate D3.js chart type:

| Goal | Data Type | Recommended Charts |
|------|-----------|--------------------|
| 比较 (Comparison) | Categorical | Bar Chart, Grouped Bar, Lollipop |
| 趋势 (Trend) | Time-series | Line Chart, Area Chart, Multi-line |
| 分布 (Distribution) | Quantitative | Histogram, Box Plot, Violin |
| 关系 (Relationship) | Two+ quantitative | Scatter Plot, Bubble Chart |
| 组成 (Composition) | Part-to-whole | Pie/Donut Chart, Stacked Bar, Treemap |
| 层次 (Hierarchy) | Tree/nested | Tree Layout, Sunburst, Circle Packing |
| 网络 (Network) | Nodes + Links | Force-Directed Graph, Sankey |
| 地理 (Geographic) | Geo-referenced | Choropleth Map, Bubble Map |
| 热度 (Intensity) | Matrix/grid | Heatmap, Calendar Heatmap |
| 时序 (Sequence) | Interactions over time | Sequence Diagram (hand-drawn SVG, no layout library needed) |
| 分层 (Layered model) | Hierarchical resource/domain layers | Tree Layout, Sunburst, Circle Packing |

If multiple perspectives are needed, create multiple visualizations in the same HTML document.

**Multi-chart coverage check**（有 SDS：覆盖判定归前门的 LDM 验收，本技能只逐张兑现；以下为 standalone 自查）: when the request names a fixed set of diagrams (e.g. "5 类图"), enumerate them up front and map each one to a concrete chart type before writing code, then deliver the complete set. Missing requested diagram types are deliverable defects, not rendering details — a heatmap cannot stand in for a missing sequence diagram or a missing layered-model view.

**Semantic fit**（图类适配判定归前门路由；受委派时按 SDS 的 `diagram_class` 实现，不在此改判）: a heatmap / dependency matrix encodes dependency *intensity* only; it does NOT show topology, deployment layout, or namespace grouping. If the requested diagram is a deployment/architecture view, render a topology or grouped view (fixed-coordinate component layout, zone-grouped force graph, namespace-grouped view) instead of overloading a heatmap with metadata columns (kind/replica/port).

### Step 3: Write D3.js Code

Based on the chosen chart type and data:

1. **Prepare data**: Parse/transform user data into D3-friendly format
2. **Set up SVG**: Define dimensions, margins, and responsive viewBox（SDS 几何图：viewBox 与 SDS canvas **1:1**，**不套 margin 平移**——见 [references/sds-realization.md](references/sds-realization.md) §3.1）
3. **Create scales**: Map data domains to visual ranges (x, y, color, size)
4. **Draw axes**: Add labeled axes with proper tick formatting
5. **Binddata & draw elements**: Use the data-join pattern to render visual marks
6. **Add labels & legend**: Title, axis labels, legend for color/size encodings
7. **Add interactivity** (if requested): Tooltips, transitions, hover effects

For D3.js syntax, scale types, layouts, and common patterns, reference [d3js-guide.md](references/d3js-guide.md).

#### Dense Graph & Architecture Diagram Guidance

When the visualization is a component/architecture graph (nodes + links), apply these rules.

> **决策 vs 实现**：有 SDS 时——「哪些是节点、谁属哪个分区、坐标在哪、谁是关键路径、哪条是推断路径」全部是语义层的决定（SDS `elements` / `zones` / geometry / `weight_plan`），本技能只做 D3 实现与渲染质量，**不得在此重做这些判定**。无 SDS 的 standalone 调用下，标〔决策〕的条目由本技能自行判定并在交付说明中记录策略。

- **Layout reproducibility**〔有 SDS：固定坐标是契约，不选策略；以下为 standalone 选项〕: a bare `d3.forceSimulation` starts from random positions — every reload yields a different layout. For reproducible output either (a) assign fixed/preset coordinates (`x`/`y` on each node) and pin or skip the simulation, (b) constrain the simulation with per-group `forceX`/`forceY` so each group occupies a stable region, or (c) seed node positions deterministically. State the layout strategy in the deliverable explanation.
- **Dense-graph threshold**〔决策 / standalone 判据〕: with roughly >15–20 nodes or dense link sets, a free-running force layout tends to cross and overlap. Prefer fixed hand-placed coordinates (readable + reproducible) or a grouped force layout over a pure simulation.
- **Edge labels**〔实现〕: do NOT keep every edge label permanently visible at full opacity in dense graphs — labels overlap nodes and other links. Show labels on hover (per-link label or tooltip), or display labels only for a curated set of key edges. Keep edge label text short (≤ ~8–10 chars) and color edges by type/relation for extra disambiguation.
- **Node semantics**〔决策归语义层 elements〕: every node must be a real component of the modeled system. Non-component concepts (queues, budgets, behaviors, states) are NOT nodes — move them into annotation text, a description panel, or a visually distinct non-node annotation layer. Mixing pseudo-nodes into the node set misleads readers about the architecture.
- **Group semantics**〔决策归语义层 zones〕: assign groups by semantic role. Infrastructure nodes (storage systems, external services, registries) usually are not part of a subsystem — give them their own group and their own legend color instead of folding them into a subsystem group.
- **Legend**〔实现〕: always pair color swatches (colored dots/rects) with group names in the legend; a text-only legend is insufficient to decode a colored graph.
- **Bilingual node labels**〔实现〕: in architecture graphs, give each node a short English name (e.g. access / gateway) plus a Chinese subtitle (职责说明, ≤ ~12 chars) below it when the audience is mixed-language; English-only short names reduce readability for Chinese reviewers.
- **Edge-label visibility toggle**〔实现〕: default edge labels to hidden (hover reveals), but provide an explicit「常显边标签」toggle (checkbox/button) so the same figure can be printed/exported with labels permanently visible for doc embedding. Hover-only labels with no way to show them statically lose information in static output (screenshots, PDFs).
- **Cross-panel edges**〔实现；锚点位置取自 SDS `relations.anchor`〕: when the layout uses panels/zones, route cross-panel edges through unified anchor exit/entry ports on panel borders, or use orthogonal (elbow) routing, instead of long straight diagonals that cut through unrelated panels — long cross-panel lines read as clutter in static output.
- **Fixed-coordinate hygiene**〔实现〕: with hand-placed coordinates, record the partition/grid rule in the data file header (e.g. "panel A: x∈[40,360], y∈[40,300]; node slots on a 24px grid") and run the overlap / panel-bounds + SDS 逐 box 一致性校验 before render, so later node additions do not silently overlap. Snippets (`validateCoords` / `validateAgainstSDS`): [references/sds-realization.md](references/sds-realization.md) §4.
- **Inference annotation**〔判定归语义层摘要纪律；区别样式与图注落地归本技能〕: when the diagram includes transitions/states/relations inferred by the author (not stated in the source description) — e.g. a manual recovery path or a direct-delete path — mark them with a distinct style AND a「描述未定义，推断路径」annotation (footnote, legend entry, or edge label); never present inferred semantics as source-described. Similarly, annotate deliberately omitted domain parts instead of omitting silently.

**Data provenance**: when the visualization encodes an external description (architecture doc, spec, requirement), record the source file/version/date in the data file header or a page note (e.g. `// 依据: docs/architecture.md v2.3 (2026-08-01)`). This keeps the figure auditable against its source and surfaces narrative drift between the description and the diagram.

### Step 4: Assemble HTML Document

Package everything into a self-contained HTML file with this structure:

```html
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[Visualization Title]</title>
  <script src="https://d3js.org/d3.v7.min.js"></script>
  <style>
    /* Inline styles for the visualization */
  </style>
</head>
<body>
  <div id="chart"></div>
  <script>
    // D3.js visualization code
  </script>
</body>
</html>
```

Key requirements:
- D3.js loaded from CDN: `https://d3js.org/d3.v7.min.js` (single-file mode) or vendored locally (split mode)
- All CSS inline in `<style>` block
- All JavaScript inline in `<script>` block
- Data embedded inline in single-file mode; in split mode, data lives in a separate local `data.js`/`data.json` referenced by relative path
- A **reproduction appendix** (visible collapsible footer section plus a header comment block): state that the file opens and renders directly with no build step (CDN mode needs network; split/vendored mode works offline), which data files/arrays drive which part of the figure (nodes / links / rels / cells), and the source description version/date the data is based on. Mandatory in split mode — the data is external and maintainers need the entry points.
- **Export capability**: include「导出 SVG / 导出 PNG」buttons (SVG serialization + Canvas conversion) whenever the figure targets embedding into reports or docs. Reusable snippet: [d3js-guide.md](references/d3js-guide.md).
- Responsive design: use `viewBox` or resize listener

Heatmap / dependency-matrix specifics:
- Make the direction convention **visible by default**: annotate rows and columns (e.g. 行 = 依赖方 / 列 = 被依赖方, with an arrow caption), not only in tooltips. Hover tooltips should restate the direction explicitly.
- Rotated column headers (e.g. -32°/-45°) need enough reserved header height — scale it to the longest label. If labels are long, shorten the displayed name and show the full name in the tooltip.
- **Strength scale semantics**: when cells encode an author-assigned strength (e.g. 0–4), define the scale in the data file header AND in a figure caption/legend (e.g. `0=无依赖, 1=弱关联(低频/可选), 2=一般(异步/事件), 3=强(同步调用/数据流), 4=强同步依赖(核心链路)`). Subjective values without a documented scale are not reviewable or reproducible.
- **Wide matrices (>~10–13 columns)**: rotated headers start colliding with narrow cells — group columns by subsystem with group header rows and fold/collapse sections, or paginate into multiple views with a switcher, instead of shrinking cells further.

For multi-chart dashboards:
- Use CSS Grid or Flexbox for layout
- Each chart in its own `<div>` with unique ID
- Share color scales across charts for visual consistency
- Add a page title and optional description section

### Step 5: Save & Verify

1. Save the HTML file to the user's specified path (or suggest a reasonable default like `./output/visualization.html`)
2. Verify the file can be opened in a browser
3. Provide a brief explanation of:
   - What the visualization shows
   - How to interact with it (if interactive)
   - How to modify the data (where in the code to update values)
   - How to reproduce/embed: the file opens directly in a browser and renders with no build step (CDN mode needs network; split/vendored mode works offline); when review embedding matters, optionally attach a headless-browser-exported PNG snapshot of the figure — that snapshot's window height (content height **plus** a margin) and the clipping judgement are owned by the delivery contract's D6「渲染证据几何」row ([../draw-diagram/references/delivery-contract.md](../../delivery-contract.md)); the margin value is not restated here, and a non-blank PNG alone is **not** render evidence

## Output Requirements

- **Delivery contract (read first; rules owned by the front door)**: [../draw-diagram/references/delivery-contract.md](../../delivery-contract.md) — D1/D2 delivery form, D3–D5 user-facing text rules (**in-chart labels and the HTML prose obey the same rules**), D6 pre-delivery self-check. **The rule text and its examples live only in the contract; they are not restated here.** The items below are this engine's **mechanics**; the contract wins on conflict.
- Output as a **single `.html` file** by default (self-contained; D3.js v7 via CDN). Split mode is allowed when maintainability or offline reproducibility requires it: local `data.js`/`data.json` and/or a vendored local D3.js, all referenced by relative paths
- D3.js version: v7 (via `https://d3js.org/d3.v7.min.js` or vendored locally)
- SVG-based rendering (not Canvas, unless specifically requested for performance)
- Responsive: works on both desktop and mobile viewports
- Clean, readable code with comments explaining key sections
- Default language: follow user's preferred language for labels and titles
- Color palette: use `d3.schemeCategory10` or `d3.schemeTableau10` by default; honor user preferences
- Deliverables encoding an external description annotate the source version/date (data header or page note)
- Inferred diagram semantics (states/transitions/relations not present in the source) are annotated「描述未定义，推断路径」, never presented as source-described
- Figures targeting doc embedding include「导出 SVG/PNG」buttons

## Reference Documents

### Guides (`references/`)

| Document | Content |
|----------|---------|  
| [sds-realization.md](references/sds-realization.md) | **SDS 实现技术所有者**：输入契约与不可改写边界、档位线宽/深浅/字号落地理由、像素测量管线、viewBox 与 canvas 1:1、固定坐标 data-join、锚点计算、`validateCoords` + `validateAgainstSDS` + 复刻型渲染读回差量（§4 关三）、复刻型实测覆盖、偏离策略 |
| [d3js-guide.md](references/d3js-guide.md) | D3.js v7 quick reference: scales, axes, shapes, layouts, transitions, data-join pattern, and common chart recipes (incl. dense/reproducible force graphs, state machine, hand-drawn sequence diagram, tree/layered model, heatmap direction conventions) |
| [d3js-official-docs.md](references/d3js-official-docs.md) | D3.js official documentation: core concepts, module architecture, data-join philosophy. Load on-demand for deeper understanding |
| [cycle3-reproduction-lessons.md](references/cycle3-reproduction-lessons.md) | Dated record（cycle 3 R1，复刻竞技场）：当次重绘的强制修正与不可动不变量；通用化的质量实践已收入 sds-realization.md §5，本文件不作为当前规范引用 |

### Best Practices (`best-practices/`)

**实战沉淀（务必阅读）**：竞技评审与重绘中固化的经验教训，见 [best-practices.md](best-practices/best-practices.md)（最佳实践）与 [pitfalls.md](best-practices/pitfalls.md)（陷阱）——绘制前对照最佳实践，绘制后自查陷阱清单。

### Assets (`assets/`)

| Asset | Purpose |
|-------|---------|  
| [template.html](assets/template.html) | Base HTML template with D3.js CDN, responsive setup, and standard margin convention |

## Quality Checklist

Before delivering the final HTML file, verify:

**总则（复刻优先）**：`fidelity_intent=reproduction` 时，源图忠实度**高于本清单**。某条与源图冲突
（源图没有图例色块、源图的边标签是常显的等）→ 该条 MUST 显式标 **N/A**，并写明该语义在源图里由谁
承载（如面板标题、`<title>` 属性、tooltip）；MUST NOT 为了凑满清单而偏离源图。既未兑现又未标 N/A
的条目按缺项计。

- [ ] 受委派时读了调用方给的 SDS，没有重推语义（元素/分区/档位归属未改写）
- [ ] SDS 几何逐 box 兑现、零偏离（`validateAgainstSDS` 无 delta；未启力导向重排；未套 margin 平移）
- [ ] 线宽按档位落地且单调递减（T1>T2>T3>T4，非全图单一线宽）；关键路径只抬色相、粗细 ≤ T2
- [ ] 复刻型用源图实测线宽/字号/色值覆盖默认档位（未"归一化"回默认）
- [ ] 不可避免的运行时偏离已在 box 内近似并量化声明（维度 + 幅度 + 原因）
- [ ] HTML file opens correctly in a browser without errors
- [ ] Browser console shows no JavaScript errors
- [ ] D3.js v7 is present (CDN link or vendored local file) and correct
- [ ] No external dependencies beyond D3.js; split-mode data files are local and relative
- [ ] SVG has proper `viewBox` or responsive sizing
- [ ] Axes have readable labels and proper formatting
- [ ] Colors are distinguishable and accessible (avoid red/green only)
- [ ] Data values render correctly (spot-check at least 2 data points)
- [ ] Code has comments explaining data format and key logic
- [ ] Title and labels match the user's language preference
- [ ] Interactive elements (if any) provide visual feedback
- [ ] Multi-chart layout (if applicable) is balanced and aligned
- [ ] All requested diagram types are delivered (multi-chart coverage check)
- [ ] Graph nodes are all real components — no pseudo-nodes mixed into the node set
- [ ] Graph layout is reproducible (fixed/preset coordinates or grouped/seeded forces)
- [ ] Graph legend pairs color swatches with group names
- [ ] Heatmap/dependency matrix shows its direction convention by default
- [ ] Dense-graph edge labels are not all permanently visible (hover or curated set)
- [ ] Reproduction appendix (data maintenance + render notes) is included in the HTML output
- [ ] Dependency-matrix strength scale is defined (data header + caption) when cells are author-assigned
- [ ] Wide matrices (>~10–13 cols) are grouped/folded or paginated rather than squeezed
- [ ] Dense-graph edge labels have an always-on toggle (not hover-only)
- [ ] Inferred transitions/paths are annotated「描述未定义，推断路径」
- [ ] Data provenance (source description version + date) is recorded for architecture figures
- [ ] Fixed-coordinate graphs record the grid/partition rule and pass an overlap/bounds check
- [ ] Cross-panel edges use anchored or orthogonal routing
- [ ] Export SVG/PNG is available when the figure targets doc embedding
