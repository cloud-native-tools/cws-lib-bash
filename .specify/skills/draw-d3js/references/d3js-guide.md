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
```javascript
const simulation = d3.forceSimulation(nodes)
  .force("link", d3.forceLink(links).id(d => d.id).distance(100))
  .force("charge", d3.forceManyBody().strength(-300))
  .force("center", d3.forceCenter(width / 2, height / 2));

const link = svg.selectAll("line")
  .data(links).join("line")
    .attr("stroke", "#999").attr("stroke-opacity", 0.6);

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

### Heatmap
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

## Color Palettes Reference

| Palette | Usage | Code |
|---------|-------|------|
| Category10 | Categorical (≤10) | `d3.schemeCategory10` |
| Tableau10 | Categorical (≤10, colorblind-friendly) | `d3.schemeTableau10` |
| Blues | Sequential (light→dark) | `d3.interpolateBlues` |
| Viridis | Sequential (perceptually uniform) | `d3.interpolateViridis` |
| RdBu | Diverging (red↔blue) | `d3.interpolateRdBu` |
| RdYlGn | Diverging (red↔green) | `d3.interpolateRdYlGn` |
