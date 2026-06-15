# Apache ECharts 官方文档

> 来源: https://echarts.apache.org/zh/index.html
> 文档地址: https://echarts.apache.org/handbook/zh/get-started/
> 获取时间: 2026-05-12

---

## 使用手册目录

### 入门篇

- 快速上手
- 获取 ECharts
- 在项目中引入 ECharts
- 寻求帮助

### 版本说明

- ECharts 6 特性介绍
- v5 升级 v6 指南
- 5.0 新特性
- v4 升级 v5 指南
- 5.2 / 5.3 / 5.4 / 5.5 / 5.6 更新

### 概念篇

- 图表容器及大小
- 样式
- 数据集
- 数据转换
- 坐标轴
- 视觉映射
- 图例
- 事件与行为

### 实战篇

- 基础柱状图
- 堆叠柱状图
- 更多图表类型...

---

## 快速上手

### 获取 Apache ECharts

Apache ECharts 支持多种下载方式。以从 jsDelivr CDN 上获取为例：

在 https://www.jsdelivr.com/package/npm/echarts 选择 `dist/echarts.js`，点击并保存为 `echarts.js` 文件。

### 引入 Apache ECharts

在保存 `echarts.js` 的目录新建一个 `index.html` 文件：

```html
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <!-- 引入刚刚下载的 ECharts 文件 -->
    <script src="echarts.js"></script>
  </head>
</html>
```

### 绘制一个简单的图表

在绘图前需要为 ECharts 准备一个定义了高宽的 DOM 容器：

```html
<body>
  <!-- 为 ECharts 准备一个定义了宽高的 DOM -->
  <div id="main" style="width: 600px;height:400px;"></div>
</body>
```

完整代码：

```html
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>ECharts</title>
    <!-- 引入刚刚下载的 ECharts 文件 -->
    <script src="echarts.js"></script>
  </head>
  <body>
    <!-- 为 ECharts 准备一个定义了宽高的 DOM -->
    <div id="main" style="width: 600px;height:400px;"></div>
    <script type="text/javascript">
      // 基于准备好的dom，初始化echarts实例
      var myChart = echarts.init(document.getElementById('main'));

      // 指定图表的配置项和数据
      var option = {
        title: {
          text: 'ECharts 入门示例'
        },
        tooltip: {},
        legend: {
          data: ['销量']
        },
        xAxis: {
          data: ['衬衫', '羊毛衫', '雪纺衫', '裤子', '高跟鞋', '袜子']
        },
        yAxis: {},
        series: [
          {
            name: '销量',
            type: 'bar',
            data: [5, 20, 36, 10, 10, 20]
          }
        ]
      };

      // 使用刚指定的配置项和数据显示图表。
      myChart.setOption(option);
    </script>
  </body>
</html>
```

---

## 图表容器及大小

### 初始化

#### 在 HTML 中定义有宽度和高度的父容器（推荐）

通常需要在 HTML 中先定义一个 `<div>` 节点，并且通过 CSS 使得该节点具有宽度和高度。初始化的时候，传入该节点，图表的大小默认即为该节点的大小。

```html
<div id="main" style="width: 600px;height:400px;"></div>
<script type="text/javascript">
  var myChart = echarts.init(document.getElementById('main'));
</script>
```

#### 指定图表的大小

如果图表容器不存在宽度和高度，也可以在初始化的时候指定大小：

```html
<div id="main"></div>
<script type="text/javascript">
  var myChart = echarts.init(document.getElementById('main'), null, {
    width: 600,
    height: 400
  });
</script>
```

### 响应容器大小的变化

#### 监听图表容器的大小并改变图表大小

可以监听页面的 `resize` 事件获取浏览器大小改变的事件，然后调用 `echartsInstance.resize` 改变图表的大小：

```html
<style>
  #main, html, body {
    width: 100%;
  }
  #main {
    height: 400px;
  }
</style>
<div id="main"></div>
<script type="text/javascript">
  var myChart = echarts.init(document.getElementById('main'));
  window.addEventListener('resize', function() {
    myChart.resize();
  });
</script>
```

> 提示：可以借助浏览器的 `ResizeObserver` API 来实现更细粒度的监听。

#### 为图表设置特定的大小

```js
myChart.resize({
  width: 800,
  height: 400
});
```

### 容器节点被销毁以及被重建时

在图表容器被销毁之后，调用 `echartsInstance.dispose` 销毁实例，在图表容器重新被添加后再次调用 `echarts.init` 初始化。

> 提示：在容器节点被销毁时，总是应调用 `echartsInstance.dispose` 以销毁实例释放资源，避免内存泄漏。

---

## ECharts 中的样式简介

### 颜色主题（Theme）

最简单的更改全局样式的方式是直接采用颜色主题。ECharts5 除了默认主题外，还内置了 `'dark'` 主题：

```js
var chart = echarts.init(dom, 'dark');
```

其他主题需要自己加载：

```js
// JSON 格式主题
fetch('theme/vintage.json')
  .then(r => r.json())
  .then(theme => {
    echarts.registerTheme('vintage', theme);
    var chart = echarts.init(dom, 'vintage');
  })
```

### 调色盘

调色盘可以在 option 中设置，给定一组颜色，图形、系列会自动从其中选择颜色：

```js
option = {
  // 全局调色盘
  color: [
    '#c23531', '#2f4554', '#61a0a8', '#d48265',
    '#91c7ae', '#749f83', '#ca8622', '#bda29a',
    '#6e7074', '#546570', '#c4ccd3'
  ],
  series: [
    {
      type: 'bar',
      // 此系列自己的调色盘
      color: ['#dd6b66', '#759aa0', '#e69d87', '#8dc1a9', '#ea7e53']
    }
  ]
};
```

### 直接的样式设置

ECharts 的 option 中，很多地方可以设置 `itemStyle`、`lineStyle`、`areaStyle`、`label` 等，直接设置图形元素的颜色、线宽、点的大小、标签的文字等。

### 高亮的样式：emphasis

在鼠标悬浮到图形元素上时，通过 `emphasis` 属性来定制高亮样式：

```js
option = {
  series: {
    type: 'scatter',
    // 普通样式
    itemStyle: {
      color: 'red'
    },
    label: {
      show: true,
      formatter: 'This is a normal label.'
    },
    // 高亮样式
    emphasis: {
      itemStyle: {
        color: 'blue'
      },
      label: {
        show: true,
        formatter: 'This is a emphasis label.'
      }
    }
  }
};
```

### 通过 visualMap 组件设定样式

`visualMap` 组件能指定数据到颜色、图形尺寸的映射规则。

---

## 数据集（Dataset）

数据集（dataset）是专门用来管理数据的组件。从 ECharts4 支持数据集开始，更推荐使用数据集来管理数据。

### 在系列中设置数据

```js
option = {
  xAxis: {
    type: 'category',
    data: ['Matcha Latte', 'Milk Tea', 'Cheese Cocoa', 'Walnut Brownie']
  },
  yAxis: {},
  series: [
    { type: 'bar', name: '2015', data: [89.3, 92.1, 94.4, 85.4] },
    { type: 'bar', name: '2016', data: [95.8, 89.4, 91.2, 76.9] },
    { type: 'bar', name: '2017', data: [97.7, 83.1, 92.5, 78.1] }
  ]
};
```

### 在数据集中设置数据

数据设置在数据集中的好处：

1. 能够贴近数据可视化常见思维方式：提供数据 → 指定数据到视觉的映射
2. 数据和其他配置可以被分离开来
3. 数据可以被多个系列或组件复用
4. 支持更多的数据的常用格式

#### 二维数组格式

```js
option = {
  legend: {},
  tooltip: {},
  dataset: {
    source: [
      ['product', '2015', '2016', '2017'],
      ['Matcha Latte', 43.3, 85.8, 93.7],
      ['Milk Tea', 83.1, 73.4, 55.1],
      ['Cheese Cocoa', 86.4, 65.2, 82.5],
      ['Walnut Brownie', 72.4, 53.9, 39.1]
    ]
  },
  xAxis: { type: 'category' },
  yAxis: {},
  series: [{ type: 'bar' }, { type: 'bar' }, { type: 'bar' }]
};
```

#### 对象数组格式

```js
option = {
  legend: {},
  tooltip: {},
  dataset: {
    dimensions: ['product', '2015', '2016', '2017'],
    source: [
      { product: 'Matcha Latte', '2015': 43.3, '2016': 85.8, '2017': 93.7 },
      { product: 'Milk Tea', '2015': 83.1, '2016': 73.4, '2017': 55.1 },
      { product: 'Cheese Cocoa', '2015': 86.4, '2016': 65.2, '2017': 82.5 },
      { product: 'Walnut Brownie', '2015': 72.4, '2016': 53.9, '2017': 39.1 }
    ]
  },
  xAxis: { type: 'category' },
  yAxis: {},
  series: [{ type: 'bar' }, { type: 'bar' }, { type: 'bar' }]
};
```

### 数据到图形的映射

- 指定数据集的列（column）还是行（row）映射为系列：`series.seriesLayoutBy`
- 指定维度映射规则：`series.encode` 和 `visualMap`

#### series.encode 示例

```js
var option = {
  dataset: {
    source: [
      ['score', 'amount', 'product'],
      [89.3, 58212, 'Matcha Latte'],
      [57.1, 78254, 'Milk Tea'],
      [74.4, 41032, 'Cheese Cocoa'],
      [50.1, 12755, 'Cheese Brownie'],
      [89.7, 20145, 'Matcha Cocoa'],
      [68.1, 79146, 'Tea'],
      [19.6, 91852, 'Orange Juice'],
      [10.6, 101852, 'Lemon Juice'],
      [32.7, 20112, 'Walnut Brownie']
    ]
  },
  xAxis: {},
  yAxis: { type: 'category' },
  series: [
    {
      type: 'bar',
      encode: {
        x: 'amount',  // 将 "amount" 列映射到 X 轴
        y: 'product'  // 将 "product" 列映射到 Y 轴
      }
    }
  ]
};
```

#### encode 支持的属性

```js
// 通用属性
encode: {
  tooltip: ['product', 'score'],
  seriesName: [1, 3],
  itemId: 2,
  itemName: 3
}

// 直角坐标系特有
encode: {
  x: [1, 5, 'score'],
  y: 0
}

// 极坐标系特有
encode: {
  radius: 3,
  angle: 2
}

// 地理坐标系特有
encode: {
  lng: 3,
  lat: 2
}
```

### 维度（dimension）

维度类型可以取以下值：

- `'number'`: 默认，普通数据
- `'ordinal'`: 类目/文本数据
- `'time'`: 时间数据
- `'float'`: 浮点数（使用 TypedArray 优化性能）
- `'int'`: 整数（使用 TypedArray 优化性能）

### 多个 dataset 以及引用

```js
var option = {
  dataset: [
    { source: [...] },  // 序号 0
    { source: [...] },  // 序号 1
    { source: [...] }   // 序号 2
  ],
  series: [
    { datasetIndex: 2 },  // 使用序号为 2 的 dataset
    { datasetIndex: 1 }   // 使用序号为 1 的 dataset
  ]
};
```

---

## 支持的图表类型

ECharts 支持以下主要图表类型：

| 图表类型 | type 值 | 说明 |
|---------|---------|------|
| 折线图 | `'line'` | 趋势展示 |
| 柱状图 | `'bar'` | 分类对比 |
| 饼图 | `'pie'` | 占比展示 |
| 散点图 | `'scatter'` | 相关性分析 |
| 涟漪散点图 | `'effectScatter'` | 带动画效果的散点 |
| 雷达图 | `'radar'` | 多维度对比 |
| 树图 | `'tree'` | 层级结构 |
| 矩形树图 | `'treemap'` | 层级占比 |
| 旭日图 | `'sunburst'` | 层级占比（环形） |
| 箱线图 | `'boxplot'` | 统计分布 |
| K线图 | `'candlestick'` | 股票数据 |
| 热力图 | `'heatmap'` | 密度分布 |
| 地图 | `'map'` | 地理数据 |
| 平行坐标 | `'parallel'` | 多维数据 |
| 漏斗图 | `'funnel'` | 流程转化 |
| 仪表盘 | `'gauge'` | 指标展示 |
| 关系图 | `'graph'` | 网络关系 |
| 桑基图 | `'sankey'` | 流量流向 |
| 自定义 | `'custom'` | 自定义渲染 |

---

## 推荐资源

- 官方网站: https://echarts.apache.org/zh/index.html
- 使用手册: https://echarts.apache.org/handbook/zh/get-started/
- 配置项文档: https://echarts.apache.org/zh/option.html
- API 文档: https://echarts.apache.org/zh/api.html
- 示例集: https://echarts.apache.org/examples/zh/index.html
- 主题编辑器: https://echarts.apache.org/zh/theme-builder.html
