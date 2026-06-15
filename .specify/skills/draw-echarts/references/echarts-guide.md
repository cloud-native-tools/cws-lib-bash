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
