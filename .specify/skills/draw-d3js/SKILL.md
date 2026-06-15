---
name: draw-d3js
description: |
  Use D3.js to create interactive data visualizations and output as standalone HTML documents.
  Use when the user mentions "D3", "d3.js", "数据可视化", "data visualization", "交互式图表",
  "interactive chart", "柱状图", "折线图", "散点图", "饼图", "力导向图", "树图", "热力图",
  "bar chart", "line chart", "pie chart", "force graph", "treemap", "heatmap",
  "面积图", "area chart", "气泡图", "bubble chart", "甜甜圈图", "donut chart",
  "数据仪表板", "dashboard", "SVG图表", "svg chart", "数据图形"
skill_id: "<SKILL:.specify/skills/draw-d3js/SKILL.md>"
---

# D3.js Data Visualization Skill

Create interactive data visualizations using D3.js (Data-Driven Documents), output as a self-contained HTML file that can be opened directly in any modern browser.

## Core Principles

### 1. Data-Driven Design
Every visualization must start from data. Choose the chart type that best reveals patterns, trends, or relationships in the user's data. Avoid decorative elements that don't serve the data story.

### 2. Self-Contained Output
The output must be a **single HTML file** with all D3.js code and styles inline. No external dependencies beyond the D3.js CDN link. The file should work by simply opening in a browser.

### 3. D3.js Best Practices
Use D3.js v7 (latest stable). Follow the data-join pattern (`enter/update/exit`), use proper scales and axes, implement responsive SVG with `viewBox`. See [d3js-guide.md](references/d3js-guide.md) for syntax and patterns.

### 4. Progressive Enhancement
Start with a clean, functional visualization. Add interactivity (tooltips, transitions, zoom) only when it serves the user's needs or when explicitly requested.

## Workflow

This skill creates D3.js data visualizations based on user-provided data and requirements. Follow the steps below in order.

### Step 1: Understand Data & Requirements

Analyze the user's input to determine:

1. **Data structure**: What format is the data in? (CSV, JSON, array, table, markdown table, etc.)
2. **Data dimensions**: How many variables? Categorical vs quantitative? Time-series?
3. **Visualization goal**: What story should the chart tell? (comparison, trend, distribution, relationship, composition, hierarchy)
4. **Interactivity needs**: Static or interactive? Tooltips, zoom, filter, animation?
5. **Multi-chart needs**: Does the user need multiple perspectives? If so, plan a dashboard layout.

Data format handling:
- If data is in a markdown table or plain text table, parse it into a JSON array
- If data has Chinese headers, preserve them as labels
- If data volume is large (>100 rows), consider aggregation or sampling before visualization

If critical information is missing, ask **one targeted question**.

### Step 2: Choose Chart Type

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

If multiple perspectives are needed, create multiple visualizations in the same HTML document.

### Step 3: Write D3.js Code

Based on the chosen chart type and data:

1. **Prepare data**: Parse/transform user data into D3-friendly format
2. **Set up SVG**: Define dimensions, margins, and responsive viewBox
3. **Create scales**: Map data domains to visual ranges (x, y, color, size)
4. **Draw axes**: Add labeled axes with proper tick formatting
5. **Binddata & draw elements**: Use the data-join pattern to render visual marks
6. **Add labels & legend**: Title, axis labels, legend for color/size encodings
7. **Add interactivity** (if requested): Tooltips, transitions, hover effects

For D3.js syntax, scale types, layouts, and common patterns, reference [d3js-guide.md](references/d3js-guide.md).

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
- D3.js loaded from CDN: `https://d3js.org/d3.v7.min.js`
- All CSS inline in `<style>` block
- All JavaScript inline in `<script>` block
- Data embedded directly in the script (no external file loading)
- Responsive design: use `viewBox` or resize listener

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

## Output Requirements

- Output as a **single `.html` file** (self-contained, no external dependencies except D3.js CDN)
- D3.js version: v7 (via `https://d3js.org/d3.v7.min.js`)
- SVG-based rendering (not Canvas, unless specifically requested for performance)
- Responsive: works on both desktop and mobile viewports
- Clean, readable code with comments explaining key sections
- Default language: follow user's preferred language for labels and titles
- Color palette: use `d3.schemeCategory10` or `d3.schemeTableau10` by default; honor user preferences

## Reference Documents

### Guides (`references/`)

| Document | Content |
|----------|---------|  
| [d3js-guide.md](references/d3js-guide.md) | D3.js v7 quick reference: scales, axes, shapes, layouts, transitions, data-join pattern, and common chart recipes |
| [d3js-official-docs.md](references/d3js-official-docs.md) | D3.js official documentation: core concepts, module architecture, data-join philosophy. Load on-demand for deeper understanding |

### Assets (`assets/`)

| Asset | Purpose |
|-------|---------|  
| [template.html](assets/template.html) | Base HTML template with D3.js CDN, responsive setup, and standard margin convention |

## Quality Checklist

Before delivering the final HTML file, verify:
- [ ] HTML file opens correctly in a browser without errors
- [ ] Browser console shows no JavaScript errors
- [ ] D3.js v7 CDN link is present and correct
- [ ] No external file dependencies (all data is inline)
- [ ] SVG has proper `viewBox` or responsive sizing
- [ ] Axes have readable labels and proper formatting
- [ ] Colors are distinguishable and accessible (avoid red/green only)
- [ ] Data values render correctly (spot-check at least 2 data points)
- [ ] Code has comments explaining data format and key logic
- [ ] Title and labels match the user's language preference
- [ ] Interactive elements (if any) provide visual feedback
- [ ] Multi-chart layout (if applicable) is balanced and aligned
