---
name: draw-echarts
description: |
  Use Apache ECharts to create data visualizations and output as standalone HTML documents.
  Use when the user mentions "ECharts", "echarts", "Apache ECharts", "数据图表", "图表",
  "柱状图", "折线图", "饼图", "散点图", "雷达图", "热力图", "仪表盘", "漏斗图",
  "K线图", "桑基图", "树图", "旭日图", "关系图", "状态机", "state machine",
  "gauge", "funnel", "sankey",
  "数据可视化", "data visualization", "仪表板", "dashboard", "堆叠图",
  "stacked chart", "环形图", "平行坐标", "箱线图", "boxplot"
skill_id: "<SKILL:.specify/skills/draw-echarts/SKILL.md>"
---

# Apache ECharts Data Visualization Skill

Create data visualizations using Apache ECharts, output as a self-contained HTML file that can be opened directly in any modern browser.

## Core Principles

### 1. Configuration-Driven Design
ECharts uses a declarative `option` object to configure charts. Every visualization starts from understanding the data and mapping it to the appropriate `option` structure. Focus on clear data-to-visual mappings.

### 2. Self-Contained Output
The output must be a **single HTML file** with all ECharts configuration and styles inline. No external dependencies beyond the pinned ECharts script. The file should work by simply opening in a browser.

**Version pinning & offline reproducibility**: always load a **pinned** ECharts version (e.g. `echarts@5.6.0`), never a floating `echarts@5` tag — floating tags break reproducibility (CDN behavior, ECharts changes). For **offline-critical or long-lived deliverables, the local copy must be REAL**: place `vendor/echarts.min.js` into the deliverable (use `scripts/vendor-echarts.sh <dir>` which downloads and verifies the file) — never ship a loader that references a file you did not actually place, and never ship an empty `vendor/` stub (it renders a blank canvas offline). The HTML loader references the vendored copy first and falls back to the pinned CDN via a dynamic `onerror` loader — **no `document.write`** (deprecated, blocking, CSP-hostile). For complex, regenerable deliverables, separate data and the `option` config into a `config.json` (single canonical format) with a generated `config.js` wrapper (see `scripts/sync-config.mjs`), so regeneration only edits the config (see Step 4).

### 3. ECharts Best Practices
Use a pinned ECharts 5.x version (e.g. `echarts@5.6.0`). Leverage built-in features: responsive resize, tooltip, legend, toolbox (save as image, data view). Use `dataset` for data management when data is tabular. See [echarts-guide.md](references/echarts-guide.md) for configuration patterns, including graph/state-machine recipes and label-overlap avoidance.

### 4. Rich Interactivity by Default
ECharts provides built-in interactivity (tooltip, legend toggle, zoom, data highlight). Enable these features by default. Add custom interactions only when explicitly requested.

## SDS 实现与强弱落地

**Input contract**：受 draw-diagram 委派时，输入 = SDS（Semantic Drawing Spec）文件路径 —— 逻辑模型 + 几何（canvas、每图元 `box{x,y,w,h}`、zone 盒、relation 锚点）+ weight_plan 档位 + typography 层级；schema owner：[semantic-model.md](../draw-diagram/references/semantic-model.md)。本技能 **MUST NOT 改写语义**（元素、关系、分区、布局/档位决策）——语法层只拥有：引擎语法、SDS 实现、渲染质量实践、偏离逼近。

### 强弱落地（tier → 绝对值；owner = 本节）

| SDS 档位 | ECharts 绝对值 |
|----------|----------------|
| T1 大模块/分区边界 | zone `graphic` rect `lineWidth: 2.5`；按 `style_intent` 可用虚线 |
| T2 小模块/组件边界 | 节点 `itemStyle.borderWidth: 2.0` |
| T3 数据流 | 边 `lineStyle.width: 1.6` |
| T4 注释 | `lineStyle.width: 1.2` |

关键路径仅色相抬升、线宽封顶 ≤ T2；色相只编码语义、永不编码权重。**复刻覆盖**：`fidelity_intent=reproduction` 的 SDS 携带源图实测线宽，覆盖上表默认值（规则细节见 [sds-realization.md](references/sds-realization.md)）。全图单一线宽/单一边框粗细判不合格。

### 几何落地

`graph` + `layout:'none'` + 4 个隐形 1×1 角锚点节点 + 固定坐标 `*.config.json` 精确兑现 SDS 盒位（SDS box 左上角原点；graph 节点 x/y 为盒中心 → 需换算）。ECharts 是绝对坐标引擎：**预期零偏离**；确实无法兑现的项 MUST 按 Deviation Declaration 规则（semantic-model.md）逼近并量化声明。

映射理据、固定坐标复刻管线（目标像素测量 → config JSON → render.mjs 确定性导出）、bounds-fit 角锚点与边线 lines-series-压节点技巧、渲染质量清单：[references/sds-realization.md](references/sds-realization.md)。

## Workflow

This skill creates ECharts data visualizations based on user-provided data and requirements. Follow the steps below in order.

**SDS gate**：若输入是 draw-diagram 委派的 SDS 路径，Step 1–2 的语义推导（数据理解、图类/布局选择）已由 SDS 承载——不得重推或改写；直接从 Step 3 开始，按「SDS 实现与强弱落地」+ [references/sds-realization.md](references/sds-realization.md) 兑现。Step 4–5（HTML 组装、验证交付）始终适用。无 SDS 的直接调用按下列步骤全流程执行。

### Step 1: Understand Data & Requirements

Analyze the user's input to determine:

1. **Data structure**: What format is the data in? (Array, table, JSON, CSV, markdown table, etc.)
2. **Data dimensions**: How many variables? Categorical vs quantitative? Time-series?
3. **Visualization goal**: What story should the chart tell? (comparison, trend, distribution, relationship, composition, hierarchy, flow)
4. **Special needs**: Theme preference (light/dark)? Animation? Custom tooltip? Toolbox features?
5. **Multi-chart needs**: Does the user need multiple charts on one page? If so, plan grid layout.
6. **Delivery list**: If the task implies multiple views (e.g. an architecture overview, a state machine, a relationship view, a deployment view), enumerate the **full required view list up front** and keep it for coverage checking at delivery time. Every required view must be either delivered or explicitly waived with a stated reason (see "Coverage Discipline" in Step 2).

Data format handling:
- If data is in a markdown table or plain text table, parse it into ECharts-compatible format
- Prefer `dataset.source` for tabular data with multiple series
- If data has Chinese headers, preserve them for axis labels and legend
- If data volume is large (>50 rows), enable `dataZoom` for scrollable exploration

If critical information is missing, ask **one targeted question**.

### Step 2: Choose Chart Type

Match data characteristics and goals to the appropriate ECharts chart type:

| Goal | Data Type | Recommended Charts (type value) |
|------|-----------|---------------------------------|
| 比较 (Comparison) | Categorical | `bar`, `bar` (horizontal) |
| 趋势 (Trend) | Time-series | `line`, `line` (area) |
| 占比 (Composition) | Part-to-whole | `pie`, `treemap`, `sunburst` |
| 分布 (Distribution) | Quantitative | `scatter`, `boxplot`, `heatmap` |
| 关系 (Relationship) | Two+ quantitative | `scatter`, `graph` |
| 层次 (Hierarchy) | Tree/nested | `tree`, `treemap`, `sunburst` |
| 网络 (Network) | Nodes + Links | `graph`, `sankey` |
| 多维 (Multi-dim) | Multiple attributes | `radar`, `parallel` |
| 指标 (KPI) | Single value | `gauge` |
| 流程 (Funnel) | Stage conversion | `funnel` |
| 金融 (Finance) | OHLC data | `candlestick` |

### Graph / Network & State Machine Views

- **布局选择是语义决策，本节只保留引擎事实。** SDS 在场时，`layout_intent`、zones、每图元盒位由 SDS 承载（谁和谁同区、谁居中、分区等高都是语义层决定），语法层照 [references/sds-realization.md](references/sds-realization.md) 精确兑现，不得在此重新决策；无 SDS 的直接调用才在本层选择。引擎事实：力导向 `graph` 节点自由重叠、无子系统边界与从属语义——是关系视图而非架构图；边界/包含类视图的 ECharts 形态是固定布局（`layout:'none'` + 显式 `x`/`y`，环形拓扑可 `circular`）+ `graphic` rect 分区背景层；仅表达关系时把产物明确标注为「关系视图 / relationship view」，不得冒充架构图。
- **Edge labels occlude in dense graphs.** Do not render all edge labels by default in force layouts with many edges. Default `edgeLabel` to hidden and reveal on hover via `emphasis.edgeLabel: { show: true }`, and/or enable `labelLayout: { hideOverlap: true }` avoidance. Provide a global toggle only when the user explicitly asks for always-on labels.
- **State machines (`graph` with `categories`):** give `[*]` start/end pseudo-nodes a **visible label** (`[*]`, or localized 开始/结束) — never an empty label — and style nodes by state class (steady/transition/exception states) through `categories[].itemStyle` so node fill/border matches the legend and the edge colors.
- **Inferred vs source-described edges (推断边 vs 源描述边):** when the source description does not specify a transition (e.g. "RUNNING 直接 Delete 未详述") and the model completes it, distinguish the inference from described facts visually — recommended: **dashed gray** (`lineStyle: { type: 'dashed', color: '#999' }`) for inferred/completed edges, **solid** colored edges for source-described transitions, **red dashed** for manual-intervention actions (e.g. operator Delete/恢复 on a CRASHED state that only appears in prose, not in the state graph). Add the distinction to the legend or a prominent in-chart footnote (`title.subtext` / `graphic`), not only in a page footer.
- **Correction / arbitration annotation (校正/仲裁标注):** when the model must arbitrate a conflict in the source description (e.g. old vs current architecture, two interpretations of a data path), do not silently correct: (1) present both readings with the chosen one marked and a timestamp where the description contains old and new sections; (2) label partition titles with evolution terms (e.g. "子系统A（已迁移）", "子系统B（演进）") or use a legend split "活跃关系 / 演进关系" instead of a bare "旧" category; (3) cite the correction basis (the source reference/出处) in the delivery notes so the arbitration is reproducible.
- **Explicit omission annotation:** when the model deliberately excludes part of the domain (undefined states, out-of-scope components, unavailable data), annotate the omission on the chart (e.g. `title.subtext`, `graphic` text footnote, or a page note: "PAUSED 态架构未定义故不含") — never omit silently.

### Scope Boundary: When ECharts Is Not the Right Tool

ECharts is a data-viz library, not a diagramming tool. **Deployment diagrams, sequence diagrams, and UML class diagrams** are outside its natural expression — this capability boundary is an ECharts syntax fact; the *routing decision* itself belongs to the draw-diagram front door (routing matrix + exclusivity registry). For such views:
- Recommend the sibling diagram skills (draw-plantuml, draw-mermaid) to the user; or
- If ECharts must render the view anyway, deliver an approximate view (e.g. a `graph` for deployment topology) and **declare the deviation quantitatively** (dimension + magnitude + reason) per the Deviation Declaration rule in [semantic-model.md](../draw-diagram/references/semantic-model.md), documenting what the view shows and what it cannot show (deployment layers, containment, temporal order).

Never silently substitute one view type for another.

### Coverage Discipline (多视图交付清单)

When the task requires a fixed set of views, keep the delivery list from Step 1 and check it **before delivering**: each required view is either delivered, or explicitly waived with a stated reason (out of scope, substituted by another view with tradeoff noted, or better served by a sibling skill). Do not discover missing views at delivery time.

If multiple chart types are needed, create multiple charts in the same HTML document or use ECharts `toolbox` for type switching.

### Step 3: Build ECharts Option

Based on the chosen chart type and data:

1. **Prepare data**: Format data as `dataset.source` (preferred for tabular data) or inline `series.data`
2. **Configure axes**: Set up `xAxis` and `yAxis` with proper types (`category`, `value`, `time`, `log`)
3. **Define series**: Specify chart type, data mapping (`encode` or direct data), and visual styling
4. **Add components**: title, tooltip, legend, toolbox, dataZoom as needed
5. **Apply styling**: Colors, itemStyle, emphasis effects, animation settings
6. **Shared design tokens**: for multi-chart deliverables (especially with a shared dark theme), define ONE design-token object (palette, theme, background, panel color, fonts, edge-style semantics) and reference it from every chart config — do not scatter hex colors per config (cross-chart consistency, single edit point)
7. **Responsive setup**: Add `window.resize` listener to call `chart.resize()`
8. **Annotate omissions**: If the model deliberately omits part of the domain (undefined states, out-of-scope items), add an explicit annotation (`title.subtext`, `graphic` footnote, or page note) — never omit silently

For ECharts configuration patterns, chart recipes, and component options, reference [echarts-guide.md](references/echarts-guide.md).

### Step 4: Assemble HTML Document

Package everything into a self-contained HTML file using the base template structure:

```html
<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[Chart Title]</title>
  <script>
    // ECharts loader: vendored local copy first (offline-capable), pinned CDN fallback.
    // The local copy MUST exist — run: bash scripts/vendor-echarts.sh <deliverable-dir>
    // Never use document.write for this loader.
    (function () {
      var s = document.createElement('script');
      s.src = 'vendor/echarts.min.js';
      s.async = false;
      s.onerror = function () {
        var c = document.createElement('script');
        c.src = 'https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js';
        c.async = false;
        document.head.appendChild(c);
      };
      document.head.appendChild(s);
    })();
  </script>
  <style>
    /* Inline styles */
  </style>
</head>
<body>
  <div id="chart" style="width: 100%; height: 500px;"></div>
  <script>
    // ECharts initialization and configuration
  </script>
</body>
</html>
```

Key requirements:
- ECharts loaded from **pinned** CDN: `https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js` (never a floating `echarts@5` tag); keep the version in a code comment. Where practical, add `integrity`/`crossorigin` (SRI) attributes for the pinned script
- **Offline-critical deliverables MUST ship a real `vendor/echarts.min.js`** (download + verify with `scripts/vendor-echarts.sh <dir>`); the loader references the local copy first and only falls back to CDN — no `document.write`
- For quick online-only charts, the CDN-primary order is acceptable, but never reference `vendor/` unless the file actually exists (an empty `vendor/` stub renders a blank canvas offline)
- All CSS inline in `<style>` block
- All JavaScript inline in `<script>` block
- Data embedded directly in the script (no external file loading) — **except** complex/regenerable deliverables, where data and the `option` config live in a separate `config.json` (canonical) with a generated `config.js` wrapper so regeneration edits only the config file, not the page scaffold
- Responsive: use `window.addEventListener('resize', () => chart.resize())`
- Use [template.html](assets/template.html) as the starting point

For external-config deliverables:
- Keep ONE canonical format (`*.config.json`); generate the `*.config.js` wrapper with `node scripts/sync-config.mjs <file>.config.json` — never hand-sync two copies (they drift)
- Before delivery, run `node scripts/verify-deliverable.mjs <file>.html` for structural checks (vendor presence, loader, config sync, layout)

For multi-chart dashboards:
- Use CSS Grid for layout (e.g., `grid-template-columns: 1fr 1fr`)
- Each chart in its own container `<div>` with unique ID and fixed height
- Initialize separate ECharts instances for each container
- Single resize listener calls `.resize()` on all chart instances
- Add a page title and optional summary section
- **Avoid redundant information**: put shared context (task title, dataset notes, version footnote) in the page-level header/footer once; keep per-chart titles, legends, and footnotes minimal and non-duplicative

For dark theme:
- Use `echarts.init(dom, 'dark')` for built-in dark mode
- Set `body { background: #1a1a2e; }` to match

### Step 5: Save & Verify

1. Save the HTML file to the user's specified path (or suggest a reasonable default like `./output/chart.html`)
2. **Structural verification (program-first, no browser needed)**: run `node scripts/verify-deliverable.mjs <file>.html` — it checks (a) any referenced `vendor/echarts.min.js` actually exists and is non-empty, (b) the ECharts loader does not use `document.write`, (c) `*.config.js`/`*.config.json` pairs are in sync, (d) fixed-layout graph coordinates have no out-of-bounds nodes or overlaps (canvas size from config `meta.canvasWidth/Height`). Fix all reported problems before delivery
3. **Local open verification (渲染证明)**: open the HTML in a browser and confirm the chart actually renders (canvas is not blank, no console errors). For offline-critical deliverables, re-open with network disabled (or `file://` with no CDN access) to prove the vendored copy renders. If a headless browser is available, capture a screenshot, e.g. `chromium --headless --screenshot=out.png --window-size=1440,900 <file>.html`; verify the PNG is not a blank canvas
4. **Static snapshot export**: for offline-critical or review-facing deliverables, export a static PNG/SVG of each chart (toolbox "保存为图片", or `chart.getDataURL({ type: 'png', pixelRatio: 2 })`, or the headless screenshot) and deliver it **alongside the HTML** as render evidence — reviewers without a browser or network can verify the actual visual result offline
5. Provide a brief explanation of:
   - What the visualization shows
   - How to interact with it (tooltip, legend toggle, zoom, toolbox)
   - How to modify the data (where in the code to update values)
   - For arbitration/correction cases: the correction basis (source reference/出处) and the timestamped readings, so the interpretation is reproducible

## Output Requirements

- **Delivery contract (read first; rules owned by the front door)**: [../draw-diagram/references/delivery-contract.md](../draw-diagram/references/delivery-contract.md) — D1/D2 delivery form, D3–D5 user-facing text rules (**in-chart labels and the HTML prose obey the same rules**), D6 pre-delivery self-check. **The rule text and its examples live only in the contract; they are not restated here.** The items below are this engine's **mechanics**; the contract wins on conflict.
- Output as a **single `.html` file** (self-contained, no external dependencies except the pinned ECharts script; offline-critical output ships a REAL local `vendor/echarts.min.js`, never an empty stub)
- **Offline-critical / review-facing deliverables**: `vendor/echarts.min.js` present and non-empty (verified by `scripts/vendor-echarts.sh` / `scripts/verify-deliverable.mjs`) AND a static PNG/SVG snapshot of each chart delivered alongside the HTML as render evidence
- ECharts version: **pinned 5.x** (e.g. `https://cdn.jsdelivr.net/npm/echarts@5.6.0/dist/echarts.min.js`), never a floating `@5` tag
- Canvas-based rendering by default (use SVG renderer only if requested)
- Responsive: works on both desktop and mobile viewports
- Clean, readable code with comments explaining key sections
- Default language: follow user's preferred language for labels and titles
- Built-in interactivity: tooltip, legend toggle enabled by default
- Toolbox: include save-as-image feature by default

## Reference Documents

### Guides (`references/`)

| Document | Content |
|----------|---------|  
| [sds-realization.md](references/sds-realization.md) | SDS 实现（语法层）：SDS box→ECharts 坐标换算、bounds-fit 角锚点、边线 lines-series-压节点、固定坐标复刻管线（测量 → config JSON → render.mjs 确定性导出）、tier 映射理据与复刻覆盖规则、cycle3 渲染质量清单 |
| [echarts-guide.md](references/echarts-guide.md) | ECharts v5 quick reference: option structure, chart types, components, dataset, styling, common chart recipes, plus graph/state-machine/component-view recipes, label-overlap avoidance, and pinned-version/offline fallback patterns |
| [echarts-official-docs.md](references/echarts-official-docs.md) | ECharts official documentation: container sizing, themes, dataset patterns, encode mapping. Load on-demand for deeper understanding |

### Best Practices (`best-practices/`)

**实战沉淀（务必阅读）**：竞技评审与重绘中固化的经验教训，见 [best-practices.md](best-practices/best-practices.md)（最佳实践）与 [pitfalls.md](best-practices/pitfalls.md)（陷阱）——绘制前对照最佳实践，绘制后自查陷阱清单。

### Assets (`assets/`)

| Asset | Purpose |
|-------|---------|  
| [template.html](assets/template.html) | Base HTML template with offline-first ECharts loader (vendored copy + CDN fallback, no `document.write`), responsive setup, and standard initialization pattern |

### Scripts (`scripts/`)

| Script | Purpose |
|--------|---------|
| [vendor-echarts.sh](scripts/vendor-echarts.sh) | Download a pinned `echarts.min.js` into the deliverable's `vendor/` and verify it (non-empty, version marker, JS syntax) — makes offline rendering real, not a stub |
| [sync-config.mjs](scripts/sync-config.mjs) | Generate the `*.config.js` wrapper from the canonical `*.config.json` (or reverse); `--check` mode fails when the pair drifted — no more hand-syncing two copies |
| [check-layout.mjs](scripts/check-layout.mjs) | Coordinate hygiene for fixed-layout graph configs: out-of-bounds nodes/zones and pairwise node overlaps (canvas size from `meta.canvasWidth/Height`) |
| [verify-deliverable.mjs](scripts/verify-deliverable.mjs) | Pre-delivery structural checks per HTML: vendor file presence, no `document.write` loader, config js/json sync, layout checks (program-first; the visual check is Step 5) |

## Quality Checklist

Before delivering the final HTML file, verify:
- [ ] HTML file opens correctly in a browser without errors
- [ ] Browser console shows no JavaScript errors
- [ ] **Local open verification passed**: chart actually renders (canvas non-blank); for offline-critical output, re-opened with network disabled and still renders
- [ ] `scripts/verify-deliverable.mjs` reports no problems (vendor presence, no `document.write`, config sync, layout)
- [ ] **Offline-critical**: `vendor/echarts.min.js` exists and is non-empty (real file, not an empty stub); static PNG/SVG snapshot of each chart delivered alongside the HTML
- [ ] ECharts CDN link is present and correct (pinned version)
- [ ] No external file dependencies (all data is inline) — or config is external with a single canonical format + generated wrapper (no hand-synced js/json pair)
- [ ] Chart container has proper width and height
- [ ] Tooltip displays correctly on hover
- [ ] Legend is present (for multi-series charts) and toggleable
- [ ] Colors are distinguishable and accessible (avoid red/green only)
- [ ] Data values render correctly (spot-check at least 2 data points)
- [ ] Code has comments explaining data format and key options
- [ ] Title and labels match the user's language preference
- [ ] `window.resize` listener is registered for responsive behavior
- [ ] Toolbox with save-as-image is enabled
- [ ] Multi-chart layout (if applicable) is balanced and aligned
- [ ] Multi-chart deliverables share one design-token object (palette/theme/background), not scattered hex colors
- [ ] ECharts version is pinned (no floating `@5` tag); offline-critical output has a real vendored copy
- [ ] All required views from the delivery list are covered, or explicitly waived with a stated reason
- [ ] Dense graph edge labels are not all visible by default (hover-only or `labelLayout` avoidance)
- [ ] State machine `[*]` pseudo-nodes carry a visible label; node colors match the legend categories
- [ ] Inferred/completed edges (model 补全) are visually distinguished from source-described edges (dashed vs solid); manual-intervention edges are explicit (red dashed) and not only in `desc`/tooltip
- [ ] Fixed-layout graph coordinates are recorded (canvas size/grid rules in config `meta`) and pass the overlap/bounds check
- [ ] Corrections/arbitrations of the source description carry a cited basis (出处) in the delivery notes; old vs new readings are labeled with evolution terms ("已迁移"/"演进") rather than a bare "旧" category
- [ ] Deliberately omitted domain parts (undefined states, out-of-scope items) are annotated explicitly
- [ ] Substituted view types (e.g. a relationship view standing in for a deployment diagram) are documented with their tradeoff

## Evaluation Form(绘制评价单)

**定位与边界。** 本节是交付 ECharts 产物后的 Evaluation Form(绘制评价单)，承载用户对本次已交付可视化结果的评价；它不是 `## Feedback`，也不替代或改变该节的 agent 自省。`## Feedback` 保持其既有的「不向用户征询」规则，本节只处理用户主动给出的绘制评价。

**触发与一次性征询。** 仅在本技能已交付 ECharts 产物及必要使用说明后，随该次交付附上一句非阻塞征询：`已交付 ECharts 图表；如愿意，请评价它是否准确、清晰且适合用途，或说明希望调整之处。` 不得等待回复、重复询问或因沉默降低交付结果。

**无评价。** 用户没有给出评价即视为本次绘制满意；不创建评价条目、不调用反馈引擎，也不在后续回合追问。

**有评价。** 用户一旦主动给出评价，保留其原意，将 review 内容标为 `## Evaluation Form`，并从评价中提取至少一条评价要点；随后以本节的 probe 记录（不是以 `wrap-up` probe 记录）：

```bash
python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
  --unit-id "skill:draw-echarts" --unit-type skill \
  --lifecycle-point evaluation-form \
  --run-id "<drawing-run-id>:evaluation-form" --feature "<feature-key-if-any>" \
  --review-file "<evaluation-form-review-file>" \
  --points-file "<evaluation-form-points-file>"
```

这会经 `skill-draw-echarts-evaluation-form` probe 把评价条目写入 `.specify/memory/feedback/`。不得把本节记录与同次运行的 `## Feedback` 自省共用 `run_id`，也不得把用户评价改写为 agent 自评。

**处置、回用与传递边界。** 该条目进入既有的 `record→threshold→package→manual→mark-submitted` 链路，并由既有 feedback 处置流程持续标记为 `processed` 或 `ignored`；`processed` 时在 `disposition_reason` 中保留可执行结论。后续执行本技能前，查询本技能已处置的评价单并将适用结论用于 ECharts 图表实现与交付验收：

```bash
python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action list \
  --unit-id "skill:draw-echarts" --disposition processed --contains "Evaluation Form"
```

本节绝不自动发送任何内容。若记录结果的既有 threshold 机制要求提示，只能按既有协议给出一次非阻塞的手动打包/提交提示；本节自身的评价征询始终只有交付时的一次。

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:draw-echarts" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
