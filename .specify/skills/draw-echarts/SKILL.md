---
name: draw-echarts
description: |
  Use Apache ECharts to create data visualizations and output as standalone HTML documents.
  Use when the user mentions "ECharts", "echarts", "Apache ECharts", "数据图表", "图表",
  "柱状图", "折线图", "饼图", "散点图", "雷达图", "热力图", "仪表盘", "漏斗图",
  "K线图", "桑基图", "树图", "旭日图", "关系图", "gauge", "funnel", "sankey",
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
The output must be a **single HTML file** with all ECharts configuration and styles inline. No external dependencies beyond the ECharts CDN link. The file should work by simply opening in a browser.

### 3. ECharts Best Practices
Use ECharts v5.x (latest stable via CDN). Leverage built-in features: responsive resize, tooltip, legend, toolbox (save as image, data view). Use `dataset` for data management when data is tabular. See [echarts-guide.md](references/echarts-guide.md) for configuration patterns.

### 4. Rich Interactivity by Default
ECharts provides built-in interactivity (tooltip, legend toggle, zoom, data highlight). Enable these features by default. Add custom interactions only when explicitly requested.

## Workflow

This skill creates ECharts data visualizations based on user-provided data and requirements. Follow the steps below in order.

### Step 1: Understand Data & Requirements

Analyze the user's input to determine:

1. **Data structure**: What format is the data in? (Array, table, JSON, CSV, markdown table, etc.)
2. **Data dimensions**: How many variables? Categorical vs quantitative? Time-series?
3. **Visualization goal**: What story should the chart tell? (comparison, trend, distribution, relationship, composition, hierarchy, flow)
4. **Special needs**: Theme preference (light/dark)? Animation? Custom tooltip? Toolbox features?
5. **Multi-chart needs**: Does the user need multiple charts on one page? If so, plan grid layout.

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

If multiple chart types are needed, create multiple charts in the same HTML document or use ECharts `toolbox` for type switching.

### Step 3: Build ECharts Option

Based on the chosen chart type and data:

1. **Prepare data**: Format data as `dataset.source` (preferred for tabular data) or inline `series.data`
2. **Configure axes**: Set up `xAxis` and `yAxis` with proper types (`category`, `value`, `time`, `log`)
3. **Define series**: Specify chart type, data mapping (`encode` or direct data), and visual styling
4. **Add components**: title, tooltip, legend, toolbox, dataZoom as needed
5. **Apply styling**: Colors, itemStyle, emphasis effects, animation settings
6. **Responsive setup**: Add `window.resize` listener to call `chart.resize()`

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
  <script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
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
- ECharts loaded from CDN: `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js`
- All CSS inline in `<style>` block
- All JavaScript inline in `<script>` block
- Data embedded directly in the script (no external file loading)
- Responsive: use `window.addEventListener('resize', () => chart.resize())`
- Use [template.html](assets/template.html) as the starting point

For multi-chart dashboards:
- Use CSS Grid for layout (e.g., `grid-template-columns: 1fr 1fr`)
- Each chart in its own container `<div>` with unique ID and fixed height
- Initialize separate ECharts instances for each container
- Single resize listener calls `.resize()` on all chart instances
- Add a page title and optional summary section

For dark theme:
- Use `echarts.init(dom, 'dark')` for built-in dark mode
- Set `body { background: #1a1a2e; }` to match

### Step 5: Save & Verify

1. Save the HTML file to the user's specified path (or suggest a reasonable default like `./output/chart.html`)
2. Verify the file can be opened in a browser
3. Provide a brief explanation of:
   - What the visualization shows
   - How to interact with it (tooltip, legend toggle, zoom, toolbox)
   - How to modify the data (where in the code to update values)

## Output Requirements

- Output as a **single `.html` file** (self-contained, no external dependencies except ECharts CDN)
- ECharts version: v5.x (via `https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js`)
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
| [echarts-guide.md](references/echarts-guide.md) | ECharts v5 quick reference: option structure, chart types, components, dataset, styling, and common chart recipes |
| [echarts-official-docs.md](references/echarts-official-docs.md) | ECharts official documentation: container sizing, themes, dataset patterns, encode mapping. Load on-demand for deeper understanding |

### Assets (`assets/`)

| Asset | Purpose |
|-------|---------|  
| [template.html](assets/template.html) | Base HTML template with ECharts CDN, responsive setup, and standard initialization pattern |

## Quality Checklist

Before delivering the final HTML file, verify:
- [ ] HTML file opens correctly in a browser without errors
- [ ] Browser console shows no JavaScript errors
- [ ] ECharts CDN link is present and correct
- [ ] No external file dependencies (all data is inline)
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
