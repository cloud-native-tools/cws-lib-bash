# Apache ECharts v5 Quick Reference Guide

This guide provides a concise reference for ECharts v5 configuration patterns, chart recipes, and common components. Use it when building ECharts visualizations.

## Option Structure (Core Concept)

ECharts uses a single `option` object to configure the entire chart:

```javascript
const option = {
  title: { ... },       // Chart title
  tooltip: { ... },     // Hover tooltip
  legend: { ... },      // Legend component
  toolbox: { ... },     // Utility tools (save, zoom, etc.)
  xAxis: { ... },       // X-axis configuration
  yAxis: { ... },       // Y-axis configuration
  series: [ ... ],      // Data series (the actual charts)
  dataset: { ... },     // Optional: shared data source
  dataZoom: [ ... ],    // Optional: zoom/scroll controls
  grid: { ... },        // Optional: chart area positioning
  color: [ ... ]        // Optional: custom color palette
};
chart.setOption(option);
```

## Initialization Pattern

```javascript
// Basic initialization
const chart = echarts.init(document.getElementById('chart'));

// With dark theme
const chart = echarts.init(document.getElementById('chart'), 'dark');

// With SVG renderer (for small data, better text rendering)
const chart = echarts.init(document.getElementById('chart'), null, { renderer: 'svg' });

// Responsive resize
window.addEventListener('resize', () => chart.resize());
```

## Common Components

### Title
```javascript
title: {
  text: 'Main Title',
  subtext: 'Subtitle text',
  left: 'center',           // 'left' | 'center' | 'right' | pixel | percentage
  textStyle: { fontSize: 18, fontWeight: 'bold' }
}
```

### Tooltip
```javascript
// For axis-based charts (bar, line)
tooltip: {
  trigger: 'axis',
  axisPointer: { type: 'shadow' }  // 'line' | 'shadow' | 'cross'
}

// For item-based charts (pie, scatter)
tooltip: {
  trigger: 'item',
  formatter: '{b}: {c} ({d}%)'  // {a}=series name, {b}=category, {c}=value, {d}=percent
}

// Custom formatter function
tooltip: {
  trigger: 'axis',
  formatter: function(params) {
    return params.map(p => `${p.marker} ${p.seriesName}: ${p.value}`).join('<br>');
  }
}
```

### Legend
```javascript
legend: {
  data: ['Series1', 'Series2'],  // auto-detected if omitted
  orient: 'horizontal',          // 'horizontal' | 'vertical'
  left: 'center',
  top: 'bottom'
}
```

### Toolbox
```javascript
toolbox: {
  feature: {
    saveAsImage: { title: '保存为图片' },
    dataView: { title: '数据视图', readOnly: false },
    magicType: { type: ['line', 'bar', 'stack'] },  // type switching
    restore: { title: '还原' },
    dataZoom: { title: { zoom: '缩放', back: '还原' } }
  }
}
```

### DataZoom (Scroll/Zoom)
```javascript
dataZoom: [
  { type: 'slider', start: 0, end: 100 },       // slider bar below chart
  { type: 'inside', start: 0, end: 100 }        // mouse wheel/touch zoom
]
```

### Grid (Chart Area)
```javascript
grid: {
  left: '3%', right: '4%', bottom: '3%',
  containLabel: true   // include axis labels in grid area
}
```

## Axis Configuration

### Category Axis
```javascript
xAxis: {
  type: 'category',
  data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
  axisLabel: { rotate: 45 },        // rotate labels for long text
  boundaryGap: true                  // gap at edges (true for bar, false for line)
}
```

### Value Axis
```javascript
yAxis: {
  type: 'value',
  name: 'Sales (万元)',
  nameLocation: 'middle',
  nameGap: 50,
  min: 0,
  max: 'dataMax',
  splitLine: { show: true }
}
```

### Time Axis
```javascript
xAxis: {
  type: 'time',
  axisLabel: {
    formatter: '{yyyy}-{MM}-{dd}'
  }
}
```

### Log Axis
```javascript
yAxis: {
  type: 'log',
  logBase: 10
}
```

## Dataset (Recommended for Tabular Data)

### Array Format
```javascript
dataset: {
  source: [
    ['product', '2022', '2023', '2024'],
    ['Product A', 43.3, 85.8, 93.7],
    ['Product B', 83.1, 73.4, 55.1],
    ['Product C', 86.4, 65.2, 82.5]
  ]
},
xAxis: { type: 'category' },
yAxis: {},
series: [{ type: 'bar' }, { type: 'bar' }, { type: 'bar' }]
```

### Object Array Format
```javascript
dataset: {
  dimensions: ['product', '2022', '2023', '2024'],
  source: [
    { product: 'A', '2022': 43.3, '2023': 85.8, '2024': 93.7 },
    { product: 'B', '2022': 83.1, '2023': 73.4, '2024': 55.1 }
  ]
}
```

### Encode Mapping
```javascript
series: [{
  type: 'scatter',
  encode: {
    x: 'income',      // map 'income' dimension to x-axis
    y: 'life',        // map 'life' dimension to y-axis
    tooltip: [0, 1, 2]
  }
}]
```

## Common Chart Recipes

### Bar Chart
```javascript
option = {
  title: { text: '销售对比' },
  tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
  xAxis: { type: 'category', data: ['Q1', 'Q2', 'Q3', 'Q4'] },
  yAxis: { type: 'value' },
  series: [{
    type: 'bar',
    data: [120, 200, 150, 80],
    itemStyle: { borderRadius: [4, 4, 0, 0] }
  }]
};
```

### Stacked Bar Chart
```javascript
series: [
  { name: '产品A', type: 'bar', stack: 'total', data: [320, 302, 301, 334] },
  { name: '产品B', type: 'bar', stack: 'total', data: [120, 132, 101, 134] },
  { name: '产品C', type: 'bar', stack: 'total', data: [220, 182, 191, 234] }
]
```

### Line Chart
```javascript
option = {
  title: { text: '趋势分析' },
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: ['Jan', 'Feb', 'Mar', 'Apr', 'May'] },
  yAxis: { type: 'value' },
  series: [{
    type: 'line',
    data: [820, 932, 901, 934, 1290],
    smooth: true,           // smooth curve
    areaStyle: {}           // fill area below line (remove for plain line)
  }]
};
```

### Multi-Line Chart
```javascript
series: [
  { name: '2022', type: 'line', data: [120, 132, 101, 134, 90] },
  { name: '2023', type: 'line', data: [220, 182, 191, 234, 290] },
  { name: '2024', type: 'line', data: [150, 232, 201, 154, 190] }
]
```

### Pie Chart
```javascript
option = {
  title: { text: '访问来源', left: 'center' },
  tooltip: { trigger: 'item' },
  legend: { orient: 'vertical', left: 'left' },
  series: [{
    type: 'pie',
    radius: '60%',          // '60%' for pie, ['40%', '70%'] for donut
    data: [
      { value: 1048, name: '搜索引擎' },
      { value: 735, name: '直接访问' },
      { value: 580, name: '邮件营销' },
      { value: 484, name: '联盟广告' },
      { value: 300, name: '视频广告' }
    ],
    emphasis: {
      itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.3)' }
    }
  }]
};
```

### Donut Chart
```javascript
series: [{
  type: 'pie',
  radius: ['40%', '70%'],     // inner radius, outer radius
  avoidLabelOverlap: false,
  label: { show: false, position: 'center' },
  emphasis: {
    label: { show: true, fontSize: 20, fontWeight: 'bold' }
  },
  data: [...]
}]
```

### Scatter Plot
```javascript
option = {
  xAxis: { type: 'value', name: 'Height (cm)' },
  yAxis: { type: 'value', name: 'Weight (kg)' },
  tooltip: { trigger: 'item' },
  series: [{
    type: 'scatter',
    symbolSize: 10,
    data: [[161, 51], [167, 59], [159, 49], [157, 63], [155, 53]],
    itemStyle: { opacity: 0.7 }
  }]
};
```

### Radar Chart
```javascript
option = {
  radar: {
    indicator: [
      { name: '销售', max: 100 },
      { name: '管理', max: 100 },
      { name: '技术', max: 100 },
      { name: '客服', max: 100 },
      { name: '研发', max: 100 }
    ]
  },
  series: [{
    type: 'radar',
    data: [
      { value: [80, 90, 70, 85, 95], name: 'Team A' },
      { value: [60, 70, 80, 75, 65], name: 'Team B' }
    ]
  }]
};
```

### Gauge Chart
```javascript
option = {
  series: [{
    type: 'gauge',
    progress: { show: true, width: 18 },
    axisLine: { lineStyle: { width: 18 } },
    detail: { valueAnimation: true, formatter: '{value}%' },
    data: [{ value: 72, name: '完成率' }]
  }]
};
```

### Heatmap
```javascript
option = {
  tooltip: { position: 'top' },
  xAxis: { type: 'category', data: hours },
  yAxis: { type: 'category', data: days },
  visualMap: {
    min: 0, max: 10,
    calculable: true,
    orient: 'horizontal', left: 'center', bottom: '5%'
  },
  series: [{
    type: 'heatmap',
    data: [[0, 0, 5], [0, 1, 1], ...],  // [x, y, value]
    label: { show: true }
  }]
};
```

### Treemap
```javascript
option = {
  series: [{
    type: 'treemap',
    data: [
      { name: 'Category A', value: 100, children: [
        { name: 'A-1', value: 60 },
        { name: 'A-2', value: 40 }
      ]},
      { name: 'Category B', value: 80 }
    ]
  }]
};
```

### Sankey Diagram
```javascript
option = {
  series: [{
    type: 'sankey',
    data: [
      { name: 'Source A' }, { name: 'Source B' },
      { name: 'Target X' }, { name: 'Target Y' }
    ],
    links: [
      { source: 'Source A', target: 'Target X', value: 5 },
      { source: 'Source A', target: 'Target Y', value: 3 },
      { source: 'Source B', target: 'Target X', value: 8 }
    ]
  }]
};
```

### Funnel Chart
```javascript
option = {
  series: [{
    type: 'funnel',
    left: '10%', width: '80%',
    data: [
      { value: 100, name: '展示' },
      { value: 80, name: '点击' },
      { value: 60, name: '访问' },
      { value: 40, name: '咨询' },
      { value: 20, name: '订单' }
    ]
  }]
};
```

### Candlestick (K-Line)
```javascript
option = {
  xAxis: { type: 'category', data: dates },
  yAxis: { type: 'value' },
  series: [{
    type: 'candlestick',
    data: [
      [20, 34, 10, 38],   // [open, close, lowest, highest]
      [40, 35, 30, 50],
      [31, 38, 33, 44]
    ]
  }]
};
```

### Graph — Force-Directed Relationship View (关系视图)

Force layout is for **relationship exploration**, not architecture diagrams: nodes overlap freely and there is no subsystem boundary or containment semantics. Keep edge labels hidden by default in dense graphs and reveal them on hover.

```javascript
option = {
  tooltip: { trigger: 'item' },
  legend: { data: ['服务', '依赖'] },        // category legend (auto-detected if omitted)
  series: [{
    type: 'graph',
    layout: 'force',                        // 'force' | 'circular' | 'none' (fixed x/y)
    roam: true,
    label: { show: true, position: 'right' },
    // Edge labels: hidden by default, hover-only — avoids occlusion in dense force layouts
    edgeLabel: { show: false },
    emphasis: { edgeLabel: { show: true }, scale: true },
    // Label overlap avoidance where supported
    labelLayout: { hideOverlap: true },
    data: [
      { name: 'Node A', category: 0 },
      { name: 'Node B', category: 0 },
      { name: 'Node C', category: 1 }
    ],
    links: [
      { source: 'Node A', target: 'Node B' },
      { source: 'Node B', target: 'Node C' }
    ],
    categories: [
      { name: '服务', itemStyle: { color: '#5470c6' } },
      { name: '依赖', itemStyle: { color: '#91cc75' } }
    ],
    lineStyle: { opacity: 0.6, width: 1, curveness: 0.2 },
    force: { repulsion: 120, edgeLength: [60, 120] }
  }]
};
```

If the user asks for always-on edge labels in a dense graph, enable `labelLayout: { hideOverlap: true }` on the series and keep `emphasis.edgeLabel` for hover detail.

### Graph — Component / Architecture View (组件/架构视图)

For component views with subsystem boundaries and stable layout, use a **fixed layout** plus background partition zones. Never present a force graph as an architecture diagram.

```javascript
option = {
  // Background partition zones: draw subsystem rectangles behind the series (z: 0)
  graphic: [
    { type: 'rect', left: '4%', top: '6%', width: '44%', height: '40%', z: 0,
      style: { fill: 'rgba(84,112,198,0.08)', stroke: '#5470c6', lineWidth: 1 } },
    { type: 'text', left: '5%', top: '7%', z: 0,
      style: { text: 'Subsystem A', fill: '#5470c6', font: '12px sans-serif' } },
    { type: 'rect', left: '52%', top: '6%', width: '44%', height: '40%', z: 0,
      style: { fill: 'rgba(145,204,117,0.08)', stroke: '#91cc75', lineWidth: 1 } }
  ],
  series: [{
    type: 'graph',
    layout: 'none',                        // fixed positions (x/y in px or %)
    data: [
      { name: 'api-gateway', x: 120, y: 90, category: 0 },
      { name: 'order-svc', x: 320, y: 160, category: 0 },
      { name: 'data-store', x: 300, y: 280, category: 1 }
    ],
    categories: [
      { name: 'Subsystem A', itemStyle: { color: '#5470c6' } },
      { name: 'Subsystem B', itemStyle: { color: '#91cc75' } }
    ],
    label: { show: true, position: 'bottom' },
    edgeLabel: { show: false },
    emphasis: { edgeLabel: { show: true } },
    lineStyle: { opacity: 0.6, curveness: 0.2 }
  }]
};
```

Alternatives: `layout: 'circular'` for ring topologies; `markArea` on a background `scatter`/`custom` series when axis-based partitioning fits better. When fixed positioning is not feasible, deliver the graph as a labeled "关系视图 / relationship view" and state the substitution tradeoff explicitly.

When the view mixes an old (migrated) architecture layer with the current implementation, label partitions with evolution terms instead of a bare "旧" category — e.g. partition titles "子系统A（已迁移）" / "子系统B（演进）", or a legend split "活跃关系 / 演进关系" — and keep migrated nodes visually consistent with their own partition. Never present a migration overlay as if all nodes were current.

### Graph — State Machine (状态机)

Model a state machine with graph `categories` so nodes are colored by state class and the legend matches. **`[*]` start/end pseudo-nodes must carry a visible label** (`[*]` or localized 开始/结束) — never an empty label (an empty-string label formatter renders them as unidentifiable empty circles). **Distinguish inferred/completed edges and manual-intervention edges from source-described edges** (dashed gray / red dashed vs solid, see "Inferred vs Source-Described Transitions" below).

```javascript
option = {
  tooltip: { trigger: 'item' },
  legend: { data: ['稳态', '迁移', '异常态', '伪节点'] },
  series: [{
    type: 'graph',
    layout: 'none',                        // or 'force' with roam for exploration
    data: [
      { name: '开始', category: 3, symbolSize: 10 },   // [*] start pseudo-node
      { name: 'RUNNING', category: 0, symbolSize: 40 },
      { name: 'CRASHED', category: 2, symbolSize: 40 },
      { name: 'DELETE', category: 2, symbolSize: 30 }, // explicit manual-intervention target
      { name: '结束', category: 3, symbolSize: 10 }    // [*] end pseudo-node
    ],
    links: [
      { source: '开始', target: 'RUNNING' },
      { source: 'RUNNING', target: 'CRASHED', lineStyle: { color: '#ee6666' } },          // source-described
      { source: 'RUNNING', target: 'DELETE', lineStyle: { type: 'dashed', color: '#999999' } },  // inferred (源描述未详述)
      { source: 'CRASHED', target: 'DELETE', lineStyle: { type: 'dashed', color: '#ee6666' } }   // manual intervention (人工介入)
    ],
    categories: [
      { name: '稳态', itemStyle: { color: '#91cc75' } },      // steady
      { name: '迁移', itemStyle: { color: '#fac858' } },      // transition
      { name: '异常态', itemStyle: { color: '#ee6666' } },    // exception
      { name: '伪节点', itemStyle: { color: '#999999', borderColor: '#666666', borderWidth: 1 } }
    ],
    label: { show: true },
    edgeLabel: { show: false },
    emphasis: { edgeLabel: { show: true } }
  }],
  // Explicit omission annotation: document intentionally excluded states instead of
  // silently omitting them (fidelity discipline)
  title: {
    text: '服务状态机',
    subtext: '注: PAUSED 态架构未定义, 本图不含 · 虚线边为补全/人工介入（非源描述原文）'
  }
};
```

**State-box variant (roundRect nodes + colored transition edges)** — the high-reuse shape for dense state machines where states read better as boxes than circles:

```javascript
series: [{
  type: 'graph',
  layout: 'none',                          // hand-placed coordinates: states on a left→right timeline
  data: [
    // roundRect state boxes; width carries the label, height stays uniform
    { name: 'PENDING',   x: 80,  y: 140, symbol: 'roundRect', symbolSize: [92, 40], category: 0 },
    { name: 'RUNNING',   x: 260, y: 140, symbol: 'roundRect', symbolSize: [92, 40], category: 0 },
    { name: 'SUSPENDED', x: 260, y: 260, symbol: 'roundRect', symbolSize: [92, 40], category: 1 },
    { name: 'FAILED',    x: 440, y: 260, symbol: 'roundRect', symbolSize: [92, 40], category: 2 },
    { name: 'DONE',      x: 440, y: 140, symbol: 'roundRect', symbolSize: [92, 40], category: 3 }
  ],
  links: [
    // edges colored BY TRANSITION CATEGORY — the legend then explains edge meaning, not just nodes
    { source: 'PENDING',   target: 'RUNNING',   category: 0 },
    { source: 'RUNNING',   target: 'DONE',      category: 0 },
    { source: 'RUNNING',   target: 'SUSPENDED', category: 1 },
    { source: 'SUSPENDED', target: 'RUNNING',   category: 1 },
    { source: 'RUNNING',   target: 'FAILED',    category: 2 },
    { source: 'SUSPENDED', target: 'FAILED',    category: 2 }
  ],
  categories: [
    { name: '正向流转', itemStyle: { color: '#91cc75' }, lineStyle: { color: '#91cc75' } },
    { name: '挂起/恢复', itemStyle: { color: '#fac858' }, lineStyle: { color: '#fac858' } },
    { name: '失败',     itemStyle: { color: '#ee6666' }, lineStyle: { color: '#ee6666' } },
    { name: '完成',     itemStyle: { color: '#73c0de' }, lineStyle: { color: '#73c0de' } }
  ],
  label: { show: true, color: '#fff' },     // label inside the box
  edgeLabel: { show: false },
  emphasis: { edgeLabel: { show: true } },  // transition names on hover, not always-on
  lineStyle: { curveness: 0.15 },
  edgeSymbol: ['none', 'arrow'], edgeSymbolSize: 8
}]
```

Rules of this variant: `symbolSize: [w, h]` must fit the longest state name (measure, do not guess — overflow clips silently); keep one height for all boxes so the timeline reads; `categories[].lineStyle.color` is what makes edges legend-explainable — coloring edges only via per-link `lineStyle` loses the legend.

**Always-on vs hover edge labels — the one switch.** The default discipline is `edgeLabel.show: false` + `emphasis.edgeLabel.show: true` (hover-only). When the user explicitly wants always-on labels, flip exactly one place:

```javascript
// Always-on (dense graphs: pair with labelLayout.hideOverlap to survive occlusion)
edgeLabel: { show: true, fontSize: 10 },
labelLayout: { hideOverlap: true },
emphasis: { edgeLabel: { show: true } }     // keep hover emphasis as-is
```

Never achieve "labels visible" by removing the emphasis block or by duplicating labels into `links[].name` tooltips — the switch is `edgeLabel.show` alone.

## Styling

### Color Palette
```javascript
// Global palette
color: ['#5470c6', '#91cc75', '#fac858', '#ee6666', '#73c0de', '#3ba272', '#fc8452', '#9a60b4', '#ea7ccc']

// ECharts default dark theme colors
color: ['#dd6b66', '#759aa0', '#e69d87', '#8dc1a9', '#ea7e53', '#eedd78', '#73a373', '#73b9bc', '#7289ab']
```

### Item Style
```javascript
series: [{
  type: 'bar',
  itemStyle: {
    color: '#5470c6',
    borderRadius: [4, 4, 0, 0],
    shadowBlur: 4,
    shadowColor: 'rgba(0,0,0,0.2)'
  },
  emphasis: {
    itemStyle: { color: '#3ba272' }
  }
}]
```

### Gradient Colors
```javascript
itemStyle: {
  color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: '#83bff6' },
    { offset: 0.5, color: '#188df0' },
    { offset: 1, color: '#188df0' }
  ])
}
```

## Tips & Patterns

### Multiple Charts in One Page
```javascript
const chart1 = echarts.init(document.getElementById('chart1'));
const chart2 = echarts.init(document.getElementById('chart2'));
chart1.setOption(option1);
chart2.setOption(option2);
window.addEventListener('resize', () => { chart1.resize(); chart2.resize(); });
```

For multi-chart pages, keep shared context (task title, dataset notes) in the page-level header/footer once; avoid duplicating identical titles/legends/footnotes across charts.

### Pinned Version & Offline Fallback

Always pin the ECharts version (e.g. `echarts@5.6.0`), never a floating `echarts@5` tag. For offline-critical deliverables, the local copy must be REAL: place `vendor/echarts.min.js` (download + verify with `scripts/vendor-echarts.sh <dir>`), then use an **offline-first loader**: vendored copy first, pinned CDN fallback. **Never use `document.write`** for the loader (deprecated, blocking, CSP-hostile) — use a dynamic script with `onerror`:

```html
<script>
  // Offline-first: vendored copy is primary; CDN is the fallback.
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
```

Record the pinned version in a code comment; add SRI (`integrity` + `crossorigin`) attributes where practical. Never ship a loader that references `vendor/echarts.min.js` unless the file actually exists — an empty `vendor/` stub renders a blank canvas offline.

### Static Snapshot Export (渲染证明)

For offline-critical or review-facing deliverables, export a static PNG/SVG of each chart and deliver it alongside the HTML so reviewers can verify the visual result without a browser or network:

```javascript
// In-page export (after setOption + animation settle):
const url = chart.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#1a2332' });
// Save the data URL as <name>.png; or use toolbox saveAsImage.
```

Or capture a headless screenshot when a browser is available:

```bash
chromium --headless --screenshot=out.png --window-size=1440,900 <file>.html
```

Verify the exported image is not a blank canvas (check file size / open it) before delivering.

### External Data / Config Separation (Regeneration)

For complex or regenerable deliverables, keep data and the `option` in a separate `config.json` (single canonical format) so regeneration edits only the config, not the page scaffold. The HTML loads a `config.js` wrapper (defines `window.CHART_CONFIG`) which is **generated** from the canonical JSON — never hand-sync two copies (they drift):

```bash
# canonical: foo.config.json  ->  generated wrapper: foo.config.js
node scripts/sync-config.mjs foo.config.json
node scripts/sync-config.mjs --check foo.config.json   # fails when the pair drifted
```

```html
<script src="foo.config.js"></script>   <!-- defines window.CHART_CONFIG = {...} (generated) -->
<script>
  const chart = echarts.init(document.getElementById('chart'));
  chart.setOption(window.CHART_CONFIG);
</script>
```

Keep single-file inline output for simple one-off charts.

### Inferred vs Source-Described Transitions (推断边 vs 源描述边)

When the source description does not specify a transition (e.g. "RUNNING 直接 Delete 未详述") and the model completes it — or when a transition only exists through human action (e.g. operator Delete/恢复 on a CRASHED state described in prose but absent from the state graph) — **draw the edge explicitly but make its provenance visible**:

```javascript
links: [
  // source-described transition: solid, category color
  { source: 'RUNNING', target: 'SUSPENDING', lineStyle: { color: '#ffd93d' } },
  // inferred/completed by the model: dashed gray
  { source: 'RUNNING', target: 'DELETE', lineStyle: { type: 'dashed', color: '#999999' } },
  // manual intervention (human action): red dashed
  { source: 'CRASHED', target: 'DELETE', lineStyle: { type: 'dashed', color: '#ee6666' } }
]
```

Add the distinction to the legend or a prominent in-chart footnote (`title.subtext` / `graphic` text), not only in a page footer. Footnote example: "虚线边为按模型补全/人工介入，非源描述原文".

### Design Tokens for Multi-Chart Deliverables (设计令牌)

When a deliverable contains multiple charts (especially with a shared dark theme), do NOT scatter hex colors across each config — define ONE design-token object and reference it from every chart:

```javascript
// shared-design-tokens.js — loaded before every chart config
window.DESIGN_TOKENS = {
  theme: 'dark',
  background: '#0f1923',
  panel: '#1a2332',
  palette: ['#4ecdc4', '#ffd93d', '#ff6b6b', '#95a5a6', '#5b8ff9', '#61ddbb', '#e8a33d', '#8fa3b8'],
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif',
  edge: { described: '#8fa3b8', inferred: '#999999', manual: '#ff6b6b' }
};
```

Each chart config then uses `window.DESIGN_TOKENS.palette[0]` etc. — one edit point keeps all charts visually consistent.

### Fixed-Layout Hygiene (坐标栅格纪律)

For `layout: 'none'` graphs with hand-written coordinates: record the canvas size and grid rules in the config `meta` (e.g. `meta.canvasWidth`, `meta.canvasHeight`), and run the overlap/bounds check before delivery:

```bash
node scripts/check-layout.mjs foo.config.json        # OUT_OF_BOUNDS / OVERLAP / ZONE_OUT_OF_BOUNDS
node scripts/verify-deliverable.mjs foo.html          # includes the layout check
```

Rules of thumb: keep node spacing ≥ 1.5× the largest neighbor size; keep partition zones inside the canvas with a margin; record the canvas width explicitly (the checker defaults to 1200×800 when `meta.canvasWidth/Height` is absent — an absent width is itself a finding).

### Label Overlap Avoidance

- Scatter/graph node labels: `labelLayout: { hideOverlap: true }`
- Graph edge labels: default hidden (`edgeLabel: { show: false }`), hover-only via `emphasis.edgeLabel: { show: true }` — do not render all edge labels by default in dense graphs
- Pie labels: `avoidLabelOverlap: true` (default)

### Dynamic Data Update
```javascript
// Update with new data (merges with existing option)
chart.setOption({ series: [{ data: newData }] });
```

### Loading Animation
```javascript
chart.showLoading();
// ... fetch data ...
chart.hideLoading();
chart.setOption(option);
```

### Event Handling
```javascript
chart.on('click', function(params) {
  console.log(params.name, params.value);
});
```

## 强弱实现（接收 draw-diagram weight_plan）

语义层（draw-diagram）决定「什么该更显眼」，本技能决定「怎么画粗」。tier → 绝对值映射表的 owner 是 SKILL.md「SDS 实现与强弱落地 → 强弱落地」小节（此处不重述数值）；映射理据、复刻覆盖规则与兑现管线见 [sds-realization.md](sds-realization.md)。graph/lines/sankey 等 series 同规则：边界类走 `itemStyle.borderWidth` / `graphic` rect `lineWidth`，流线类走 `lineStyle.width`，关键路径仅色相抬升、**粗细封顶 = T2**；全图单一线宽判不合格。
