# D3.js v7 Quick Reference Guide

This guide provides a concise reference for D3.js v7 syntax, patterns, and common chart recipes. Use it when writing D3.js visualization code.

## Data-Join Pattern (Core Concept)

The fundamental D3 pattern for bindingdata to DOM elements:

```javascript
// Select → Data → Enter → Append → Attr
const bars = svg.selectAll("rect")
  .data(data)
  .join("rect")  // v7 simplified: handles enter+update+exit
    .attr("x", d => xScale(d.category))
    .attr("y", d => yScale(d.value))
    .attr("width", xScale.bandwidth())
    .attr("height", d => height - yScale(d.value))
    .attr("fill", d => colorScale(d.category));
```

## Standard Margin Convention

```javascript
const margin = { top: 40, right: 30, bottom: 50, left: 60 };
const width = 800 - margin.left - margin.right;
const height = 500 - margin.top - margin.bottom;

const svg = d3.select("#chart")
  .append("svg")
    .attr("viewBox", `0 0 ${width + margin.left + margin.right} ${height + margin.top + margin.bottom}`)
    .attr("preserveAspectRatio", "xMidYMid meet")
  .append("g")
    .attr("transform", `translate(${margin.left},${margin.top})`);
```

## Scales

### Linear Scale (Quantitative)
```javascript
const yScale = d3.scaleLinear()
  .domain([0, d3.max(data, d => d.value)])  // data range
  .range([height, 0])                        // pixel range (inverted for y)
  .nice();                                   // round domain to nice values
```

### Band Scale (Categorical / Ordinal)
```javascript
const xScale = d3.scaleBand()
  .domain(data.map(d => d.category))
  .range([0, width])
  .padding(0.2);  // gap between bars
```

### Time Scale
```javascript
const xScale = d3.scaleTime()
  .domain(d3.extent(data, d => d.date))
  .range([0, width]);
```

### Color Scales
```javascript
// Categorical (up to 10 categories)
const color = d3.scaleOrdinal(d3.schemeTableau10);

// Sequential (continuous)
const color = d3.scaleSequential(d3.interpolateBlues)
  .domain([0, d3.max(data, d => d.value)]);

// Diverging
const color = d3.scaleDiverging(d3.interpolateRdBu)
  .domain([min, mid, max]);
```

### Other Useful Scales
```javascript
// Square root (for bubble/area sizing)
const rScale = d3.scaleSqrt()
  .domain([0, d3.max(data, d => d.population)])
  .range([2, 30]);

// Log scale
const yScale = d3.scaleLog()
  .domain([1, 1000000])
  .range([height, 0]);

// Ordinal position
const yScale = d3.scalePoint()
  .domain(categories)
  .range([0, height])
  .padding(0.5);
```

## Axes

```javascript
// Bottom axis (x)
svg.append("g")
  .attr("transform", `translate(0,${height})`)
  .call(d3.axisBottom(xScale))
  .selectAll("text")
    .attr("transform", "rotate(-45)")
    .style("text-anchor", "end");

// Left axis (y)
svg.append("g")
  .call(d3.axisLeft(yScale)
    .ticks(5)
    .tickFormat(d3.format(",.0f")));

// Axis label
svg.append("text")
  .attr("x", width / 2)
  .attr("y", height + margin.bottom - 5)
  .attr("text-anchor", "middle")
  .text("X Axis Label");
```

**Rotated tick labels**: when rotating tick labels (`rotate(-32)` / `rotate(-45)`), reserve extra bottom margin (`margin.bottom` ≈ 70–100px) so long labels do not clip. If rotated labels still collide with narrow cells, shorten the displayed label and show the full name in a tooltip.

## Common Chart Recipes

### Bar Chart
```javascript
svg.selectAll("rect")
  .data(data)
  .join("rect")
    .attr("x", d => xScale(d.name))
    .attr("y", d => yScale(d.value))
    .attr("width", xScale.bandwidth())
    .attr("height", d => height - yScale(d.value))
    .attr("fill", "steelblue");
```

### Line Chart
```javascript
const line = d3.line()
  .x(d => xScale(d.date))
  .y(d => yScale(d.value))
  .curve(d3.curveMonotoneX);  // smooth interpolation

svg.append("path")
  .datum(data)
  .attr("fill", "none")
  .attr("stroke", "steelblue")
  .attr("stroke-width", 2)
  .attr("d", line);
```

### Area Chart
```javascript
const area = d3.area()
  .x(d => xScale(d.date))
  .y0(height)
  .y1(d => yScale(d.value))
  .curve(d3.curveMonotoneX);

svg.append("path")
  .datum(data)
  .attr("fill", "steelblue")
  .attr("fill-opacity", 0.3)
  .attr("stroke", "steelblue")
  .attr("d", area);
```

### Scatter Plot
```javascript
svg.selectAll("circle")
  .data(data)
  .join("circle")
    .attr("cx", d => xScale(d.x))
    .attr("cy", d => yScale(d.y))
    .attr("r", d => rScale(d.size))
    .attr("fill", d => colorScale(d.category))
    .attr("opacity", 0.7);
```

### Pie / Donut Chart
```javascript
const pie = d3.pie().value(d => d.value).sort(null);
const arc = d3.arc().innerRadius(0).outerRadius(radius);
// For donut: .innerRadius(radius * 0.5)

const g = svg.append("g")
  .attr("transform", `translate(${width/2},${height/2})`);

g.selectAll("path")
  .data(pie(data))
  .join("path")
    .attr("d", arc)
    .attr("fill", d => colorScale(d.data.name))
    .attr("stroke", "white");
```

### Force-Directed Graph

**Reproducibility rule**: a bare simulation starts from random positions — each reload gives a different layout. For reproducible output use fixed coordinates or a grouped force layout (below).

**SDS 在场时**：几何由 SDS 逐 box 给定 → 必走 Option B（预设固定坐标，不启用仿真），本节仿真配方只用于 standalone、无 SDS 的探索型请求（见 [sds-realization.md](sds-realization.md) §3.2）。

```javascript
// Option A: grouped force layout (stable regions per group, deterministic anchors)
const groupX = { 0: 200, 1: 600, 2: 1000 };   // per-group anchor x
const groupY = { 0: 250, 1: 250, 2: 250 };    // per-group anchor y
const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(100))
  .force("charge", d3.forceManyBody().strength(-300))
  .force("x", d => d3.forceX(groupX[d.group]).strength(0.5))
  .force("y", d => d3.forceY(groupY[d.group]).strength(0.5))
  .force("center", d3.forceCenter(width / 2, height / 2));

// Option B: fixed/preset coordinates (fully reproducible, no tick simulation)
// Each node carries x/y; compute link endpoints from them; keep d3.drag for manual
// adjustment. Prefer this for dense graphs (>15–20 nodes) or architecture diagrams.

const link = svg.selectAll("line")
  .data(links).join("line")
    .attr("stroke", d => typeColor(d.type))   // color edges by relation type
    .attr("stroke-opacity", 0.6);

const node = svg.selectAll("circle")
  .data(nodes).join("circle")
    .attr("r", 8).attr("fill", d => colorScale(d.group))
    .call(d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended));

simulation.on("tick", () => {
  link.attr("x1", d => d.source.x).attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
  node.attr("cx", d => d.x).attr("cy", d => d.y);
});
```

**Edge labels in dense graphs**: do not keep every label permanently visible — show labels on hover, or only for a curated set of key edges:

```javascript
// Hover-only edge labels: keep labels hidden, reveal the hovered link's label
link.on("mouseover", (event, d) => {
  linkLabel.filter(l => l === d).style("visibility", "visible");
})
.on("mouseout", (event, d) => {
  linkLabel.filter(l => l === d).style("visibility", "hidden");
});
```

**Always-on toggle**: hover-only labels lose information in static output (screenshots, PDFs). Expose a「常显边标签」checkbox so the same figure can be exported/printed with all labels visible:

```javascript
// Default hover-only; the checkbox makes labels permanently visible.
let edgeLabelsAlwaysOn = false;
d3.select("#edge-labels-toggle").on("change", (event) => {
  edgeLabelsAlwaysOn = event.target.checked;
  linkLabel.style("visibility", edgeLabelsAlwaysOn ? "visible" : "hidden");
});
link.on("mouseover", (event, d) => {
  if (!edgeLabelsAlwaysOn) linkLabel.filter(l => l === d).style("visibility", "visible");
})
.on("mouseout", (event, d) => {
  if (!edgeLabelsAlwaysOn) linkLabel.filter(l => l === d).style("visibility", "hidden");
});
```

**Bilingual node labels**: in architecture graphs, render a short English name plus a Chinese subtitle (≤ ~12 chars) below it; English-only short names reduce readability for mixed-language reviewers:

```javascript
// Node label group: name (bold) + subtitle (small, dim) beneath it
const g = node.append("g");
g.append("text").attr("class", "node-name").attr("dy", "-0.2em").text(d => d.name);
g.append("text").attr("class", "node-sub").attr("dy", "1.1em").text(d => d.sub);
```

**Cross-panel orthogonal routing**: when panels/zones partition the layout, snap cross-panel edges to unified anchor ports on the panel border and route them as orthogonal polylines (elbow routing) instead of straight diagonals:

```javascript
// Orthogonal (elbow) route between source (x1,y1) and target (x2,y2), snapping
// to panel-border ports (px,py). curveStepAfter produces the elbow segments.
const route = d3.line().x(d => d.x).y(d => d.y).curve(d3.curveStepAfter);
// waypoints: [{x:x1,y:y1}, {x:px,y:y1}, {x:px,y:py}, {x:x2,y:py}, {x:x2,y:y2}]
// Collapse redundant waypoints when consecutive points share x or y.
// Port rule: each panel exposes named exit/entry ports on its border (e.g.
// envd.out → gateway.in), and cross-panel edges use port coordinates instead of
// node centers, so a panel can be moved without rewriting every edge.
```

**Fixed-coordinate validation**: record the partition/grid rule in the data file header (e.g. "panel A: x∈[40,360], y∈[40,300]; node slots on a 24px grid") and run the overlap / panel-bounds check before render. Snippet (`validateCoords`) plus the SDS box-conformance check (`validateAgainstSDS`) live in [sds-realization.md](sds-realization.md) §4 — the fixed-coordinate pipeline has a single owner there.

**Dense-graph guidance**: for >15–20 nodes or dense links, prefer fixed hand-placed coordinates or the grouped force layout; keep edge label text short (≤ ~8–10 chars); every node must be a real component of the modeled system (do NOT mix pseudo-nodes like "queues"/"budgets"/"states" into the node set — move them to annotation text or a distinct non-node layer); give infrastructure nodes (storage, external services, registries) their own group + legend color; the legend must pair color swatches with group names.

### Treemap
```javascript
const root = d3.hierarchy(data)
  .sum(d => d.value)
  .sort((a, b) => b.value - a.value);

d3.treemap()
  .size([width, height])
  .padding(2)(root);

svg.selectAll("rect")
  .data(root.leaves())
  .join("rect")
    .attr("x", d => d.x0)
    .attr("y", d => d.y0)
    .attr("width", d => d.x1 - d.x0)
    .attr("height", d => d.y1 - d.y0)
    .attr("fill", d => colorScale(d.parent.data.name));
```

### Tree Layout (Layered / Resource Model)

Use for hierarchical layered models (e.g. resource model: platform → subsystem → component). `d3.stratify` converts flat parent/child rows into a hierarchy.

```javascript
// Rows: [{ id, parent }, ...]; root row has parent null
const root = d3.stratify()
  .id(d => d.id)
  .parentId(d => d.parent)(rows);

d3.tree().size([width, height - 60])(root);   // or d3.cluster() for tidy leaves

const link = svg.selectAll("path")
  .data(root.links())
  .join("path")
    .attr("d", d3.linkHorizontal()
      .x(d => d.y).y(d => d.x))
    .attr("fill", "none")
    .attr("stroke", "#999");

const node = svg.selectAll("g")
  .data(root.descendants())
  .join("g")
    .attr("transform", d => `translate(${d.y},${d.x})`);
node.append("circle")
  .attr("r", 5)
  .attr("fill", d => d.children ? "#4e79a7" : "#59a14f");
node.append("text")
  .attr("x", 8).attr("dy", "0.32em")
  .text(d => d.data.name);
```

### Heatmap / Dependency Matrix

```javascript
svg.selectAll("rect")
  .data(data)
  .join("rect")
    .attr("x", d => xScale(d.col))
    .attr("y", d => yScale(d.row))
    .attr("width", xScale.bandwidth())
    .attr("height", yScale.bandwidth())
    .attr("fill", d => colorScale(d.value));
```

**Direction convention must be visible by default** (e.g. row = depends-on, column = dependency): add permanent axis captions like "依赖方（行）→" / "被依赖方（列）→", and restate the direction in hover tooltips.

**Rotated column headers**: reserve header height proportional to the longest label when rotating (e.g. -32°/-45°); if labels collide with narrow cells, shorten the displayed name and show the full name in the tooltip.

**Strength scale semantics**: when cells hold author-assigned strengths (e.g. 0–4), define the scale in the data file header AND in a figure caption/legend — e.g. `0=无依赖, 1=弱关联(低频/可选), 2=一般(异步/事件), 3=强(同步调用/数据流), 4=强同步依赖(核心链路)`. Subjective values without a documented scale are not reviewable or reproducible.

**Wide matrices (>~10–13 columns)**: rotated headers collide with narrow cells — group columns by subsystem with group header rows and fold/collapse sections, or paginate into multiple views with a switcher; keep the full matrix reachable via tooltip or a "show all" toggle.

**Semantic fit**: a heatmap shows dependency *intensity* only — it is not a topology or deployment view. If a deployment architecture is requested, render a fixed-coordinate component layout or a namespace-grouped view instead.

### State Machine Diagram (Hand-Drawn, Fixed Layout)

Reference pattern for state machines: hand-placed coordinates (fully reproducible), state boxes with name + subtitle, quadratic Bezier edges with arrow markers, animated dashed edges for automatic transitions, a distinct style for manual/exception transitions, edge labels at the curve midpoint, a sidebar legend, and per-state tooltips.

```javascript
// States with fixed coordinates (reproducible)
const states = [
  { id: "idle",     name: "IDLE",     sub: "待机 · 零资源", x: 190, y: 330, color: "#64748b" },
  { id: "starting", name: "STARTING", sub: "初始化中",      x: 460, y: 150, color: "#f59e0b" },
  { id: "running",  name: "RUNNING",  sub: "运行态",        x: 740, y: 150, color: "#10b981" },
  { id: "failed",   name: "FAILED",   sub: "失败 · 人工介入", x: 740, y: 520, color: "#ef4444" }
];
// Edges as quadratic Bezier with control points; manual: true = exception path
const edges = [
  { id: "e1", x1: 206, y1: 330, x2: 460, y2: 150, ctrl: [330, 200], label: "start", manual: false },
  { id: "e2", x1: 460, y1: 150, x2: 740, y2: 150, ctrl: [600, 100], label: "ready",  manual: false },
  { id: "e3", x1: 740, y1: 150, x2: 740, y2: 520, ctrl: [820, 330], label: "crash",  manual: true  }
];

// Arrow marker
const marker = svg.append("defs").append("marker")
  .attr("id", "arr").attr("viewBox", "0 -5 10 10").attr("refX", 9).attr("refY", 0)
  .attr("markerWidth", 6.5).attr("markerHeight", 6.5).attr("orient", "auto")
  .append("path").attr("d", "M0,-5L10,0L0,5").attr("fill", "#4b5563");

// Edges: d = M x1,y1 Q cx,cy x2,y2 ; automatic edges animate the dash
svg.selectAll("path.edge")
  .data(edges).join("path")
    .attr("d", d => `M${d.x1},${d.y1} Q${d.ctrl[0]},${d.ctrl[1]} ${d.x2},${d.y2}`)
    .attr("stroke", d => d.manual ? "#ef4444" : "#4b5563")
    .attr("stroke-dasharray", d => d.manual ? "2 5" : "7 4")
    .attr("marker-end", "url(#arr)");
// CSS: @keyframes dashmove { to { stroke-dashoffset: -24; } }
//      path.edge:not(.manual) { animation: dashmove 0.9s linear infinite; }

// Edge labels at Bezier midpoint t=0.5: x = (x1 + 2*cx + x2)/4, y = (y1 + 2*cy + y2)/4 - 6
svg.selectAll("text.edge-label")
  .data(edges).join("text")
    .attr("x", d => (d.x1 + 2 * d.ctrl[0] + d.x2) / 4)
    .attr("y", d => (d.y1 + 2 * d.ctrl[1] + d.y2) / 4 - 6)
    .text(d => d.label);

// State boxes: rounded rect (rx 10) + name + subtitle; on hover highlight the
// connected edges and show a tooltip with the state description.

// Sidebar legend pattern: color dots + state semantics list, lifecycle verb chips,
// and an edge-type legend (animated dashed arrow = automatic, red arrow = manual).
// Start/end pseudo states [*]: filled circles drawn OUTSIDE the state data —
// they are annotations, never data states.
```

**Inference annotation**: transitions/states inferred by the author (absent from the source description — e.g. a manual recovery path such as FAILED→SUSPENDED cold-boot rebuild, or a direct-delete path) get a distinct style AND an explicit label such as 「描述未定义，推断路径」, so readers do not mistake them for source-described semantics. The sidebar legend must also list recovery paths explicitly (e.g. 冷启重建: FAILED → SUSPENDED → BOOTING) instead of leaving them implicit in a per-state tooltip — edges are many and curved, and a single tooltip desc is easy to miss in static output.

### Sequence Diagram (Hand-Drawn SVG)

D3 can draw sequence diagrams directly with SVG primitives — no layout library needed. Place lifelines at fixed x positions; draw messages as horizontal arrows at increasing y; activation bars as rects.

```javascript
const lifelines = [
  { id: "client", name: "Client",  x: 120 },
  { id: "api",    name: "API",     x: 360 },
  { id: "worker", name: "Worker",  x: 620 }
];
const messages = [
  { from: "client", to: "api",    y: 120, label: "Create()",      ret: false },
  { from: "api",    to: "worker", y: 170, label: "Resume()",      ret: false },
  { from: "worker", to: "api",    y: 220, label: "ack",           ret: true  },
  { from: "api",    to: "client", y: 270, label: "202 Accepted",  ret: true  }
];

// Lifelines: header box + vertical dashed line
lifelines.forEach(l => {
  svg.append("rect").attr("x", l.x - 40).attr("y", 30).attr("width", 80).attr("height", 26);
  svg.append("text").attr("x", l.x).attr("y", 47).attr("text-anchor", "middle").text(l.name);
  svg.append("line").attr("x1", l.x).attr("y1", 56).attr("x2", l.x).attr("y2", height - 30)
     .attr("stroke", "#bbb").attr("stroke-dasharray", "4 3");
});

// Messages: solid arrow = call, dashed arrow = return; label above the line
messages.forEach(m => {
  const x1 = lifelines.find(l => l.id === m.from).x;
  const x2 = lifelines.find(l => l.id === m.to).x;
  svg.append("line")
    .attr("x1", x1).attr("y1", m.y).attr("x2", x2).attr("y2", m.y)
    .attr("stroke", m.ret ? "#999" : "#333")
    .attr("stroke-dasharray", m.ret ? "5 3" : null)
    .attr("marker-end", m.ret ? "url(#arr-ret)" : "url(#arr-call)");
  svg.append("text")
    .attr("x", (x1 + x2) / 2).attr("y", m.y - 6)
    .attr("text-anchor", "middle").attr("font-size", "11px")
    .text(m.label);
});
```

Keep the actor list and message list as plain data at the top of the script so the diagram stays easy to maintain.

## Interactivity

### Tooltip
```javascript
const tooltip = d3.select("body").append("div")
  .attr("class", "tooltip")
  .style("position", "absolute")
  .style("visibility", "hidden")
  .style("background", "rgba(0,0,0,0.8)")
  .style("color", "white")
  .style("padding", "8px 12px")
  .style("border-radius", "4px")
  .style("font-size", "12px");

// Attach to elements
selection
  .on("mouseover", (event, d) => {
    tooltip.style("visibility", "visible")
      .html(`<strong>${d.name}</strong><br/>Value: ${d.value}`);
  })
  .on("mousemove", (event) => {
    tooltip.style("top", (event.pageY - 10) + "px")
      .style("left", (event.pageX + 10) + "px");
  })
  .on("mouseout", () => {
    tooltip.style("visibility", "hidden");
  });
```

### Transitions
```javascript
selection.transition()
  .duration(750)
  .ease(d3.easeCubicOut)
  .attr("y", d => yScale(d.value))
  .attr("height", d => height - yScale(d.value));
```

### Zoom & Pan
```javascript
const zoom = d3.zoom()
  .scaleExtent([0.5, 5])
  .on("zoom", (event) => {
    g.attr("transform", event.transform);
  });

svg.call(zoom);
```

### Export SVG / PNG

For figures meant to be embedded in reports/docs, add「导出 SVG / 导出 PNG」buttons. SVG export = serialize a cloned node; PNG export = rasterize the SVG onto a Canvas.

```javascript
function exportSVG(filename = "chart.svg") {
  const svgNode = document.querySelector("#chart svg");
  const clone = svgNode.cloneNode(true);
  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.setAttribute("width", svgNode.viewBox.baseVal.width);
  clone.setAttribute("height", svgNode.viewBox.baseVal.height);
  // Inline critical presentation (font-size / fill on text, marker defs) into the
  // clone when the document <style> block does not serialize with the SVG.
  const blob = new Blob([new XMLSerializer().serializeToString(clone)],
                        { type: "image/svg+xml;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob); a.download = filename; a.click();
  URL.revokeObjectURL(a.href);
}

function exportPNG(filename = "chart.png", scale = 2) {
  const svgNode = document.querySelector("#chart svg");
  const img = new Image();
  img.onload = () => {
    const canvas = document.createElement("canvas");
    canvas.width = svgNode.viewBox.baseVal.width * scale;
    canvas.height = svgNode.viewBox.baseVal.height * scale;
    canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
    const a = document.createElement("a");
    a.href = canvas.toDataURL("image/png"); a.download = filename; a.click();
  };
  img.src = "data:image/svg+xml;charset=utf-8," +
    encodeURIComponent(new XMLSerializer().serializeToString(svgNode));
}
```

Caveats: the export is a static snapshot — hover/tooltip states are not captured; external CSS/fonts may need inlining for full fidelity; PNG export requires the SVG to be rasterizable (no external images).

## Data Utilities

```javascript
// Parse CSV string
const data = d3.csvParse(csvString, d => ({
  name: d.name,
  value: +d.value,  // convert to number
  date: new Date(d.date)
}));

// Statistical helpers
d3.min(data, d => d.value)
d3.max(data, d => d.value)
d3.extent(data, d => d.value)  // [min, max]
d3.mean(data, d => d.value)
d3.sum(data, d => d.value)

// Grouping
const grouped = d3.group(data, d => d.category);
const rolled = d3.rollup(data, v => d3.sum(v, d => d.value), d => d.category);

// Number formatting
d3.format(",.0f")(1234567)   // "1,234,567"
d3.format(".1%")(0.1234)     // "12.3%"
d3.format("$.2f")(1234.5)    // "$1234.50"

// Time formatting
d3.timeFormat("%Y-%m-%d")(new Date())   // "2024-01-15"
d3.timeParse("%Y-%m-%d")("2024-01-15") // Date object
```

## Responsive Pattern

```javascript
// Option 1: viewBox (preferred)
const svg = d3.select("#chart").append("svg")
  .attr("viewBox", `0 0 ${totalWidth} ${totalHeight}`)
  .attr("preserveAspectRatio", "xMidYMid meet")
  .style("width", "100%")
  .style("height", "auto");

// Option 2: Resize listener
function render() {
  const containerWidth = document.getElementById("chart").clientWidth;
  // recalculate dimensions and redraw
}
window.addEventListener("resize", render);
render();
```

## Reproduction Appendix (复现附录)

Split-mode deliverables (data in `data-*.js`) MUST include an appendix in the HTML: a visible collapsible footer (plus a header comment block) stating:
- the file renders by opening it — no build step (CDN mode needs network; vendored mode works offline);
- which data file/array drives which part of the figure (nodes / links / rels / cells);
- the source description version/date the data is based on;
- the coordinate grid/partition rule if fixed coordinates are used (see [sds-realization.md](sds-realization.md) §4).
Single-file mode should include the same appendix with the data location pointing at the inline `const data` blocks. See [assets/template.html](../assets/template.html) for the boilerplate.

## Color Palettes Reference

| Palette | Usage | Code |
|---------|-------|------|
| Category10 | Categorical (≤10) | `d3.schemeCategory10` |
| Tableau10 | Categorical (≤10, colorblind-friendly) | `d3.schemeTableau10` |
| Blues | Sequential (light→dark) | `d3.interpolateBlues` |
| Viridis | Sequential (perceptually uniform) | `d3.interpolateViridis` |
| RdBu | Diverging (red↔blue) | `d3.interpolateRdBu` |
| RdYlGn | Diverging (red↔green) | `d3.interpolateRdYlGn` |

## 强弱实现（接收 draw-diagram weight_plan）

档位→绝对线宽的**规范表**在 [SKILL.md](../SKILL.md) §「SDS 实现与强弱落地 · 强弱实现」；映射理由、stroke 深浅阶梯、typography 绝对字号与关键路径色相纪律在 [sds-realization.md](sds-realization.md) §2（本文不复述数值，避免二处漂移）。D3 写法只有一条：把 SDS 的 `tier` 挂在数据上，一次 join 落地。

```javascript
// TIER_PX / TIER_INK 取自 SKILL.md 强弱表 + sds-realization.md §2.2 深浅阶梯
zoneSel.attr("stroke-width", d => TIER_PX[d.tier]).attr("stroke", d => TIER_INK[d.tier]);
flowSel.attr("stroke-width", d => TIER_PX[d.tier])
       .attr("stroke", d => d.keyPath ? KEY_HUE : TIER_INK[d.tier]);   // 关键路径只换色相，粗细封顶 = T2
```

复刻型 SDS（`fidelity_intent: reproduction`）用源图实测线宽覆盖默认表：[sds-realization.md](sds-realization.md) §5。全图单一线宽判不合格。
