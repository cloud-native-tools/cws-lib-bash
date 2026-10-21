# D3.js 官方文档

> 来源: https://d3js.org/
> 获取时间: 2026-05-12

---

## 什么是 D3？

D3（或 D3.js）是一个免费、开源的 JavaScript 数据可视化库。其基于 Web 标准的底层方法在创作动态、数据驱动的图形方面提供了无与伦比的灵活性。十多年来，D3 驱动了开创性和获奖的可视化，成为更高级图表库的基础构建块，并在世界各地培养了一个充满活力的数据从业者社区。

D3 "使该领域进入了前所未有的增长、多样化和创造力"，并"改变了数百万数据可视化在新闻编辑室、网站和个人作品集中的创建方式"——Information is Beautiful 2022 年时间考验奖如此评价。

D3 由 Mike Bostock 于 2011 年创建。Mike 与 Jeff Heer 和 Vadim Ogievetsky 在斯坦福大学共同撰写了 D3 论文。

### D3 是一个底层工具箱

D3 不是传统意义上的图表库。它没有"图表"的概念。当你用 D3 可视化数据时，你组合各种原语：

- CSV 解析器来加载数据
- 时间比例尺用于水平位置（x）
- 线性比例尺用于垂直位置（y）
- 序数比例尺和分类配色方案用于颜色
- 堆叠布局用于排列值
- 面积形状用线性曲线生成 SVG 路径数据
- 坐标轴用于记录位置编码
- 选择集用于创建 SVG 元素

D3 不是单一的庞然大物，而是一套约 30 个独立库（或"模块"）的集合。

### D3 是灵活的

因为 D3 没有总体的"图表"抽象，即使是一个基本图表也可能需要几十行代码。好处是，所有部分都摆在你面前，你可以完全控制发生的事情。

### D3 与 Web 配合

D3 不引入新的图形表示；相反，你直接使用 D3 与 SVG 和 Canvas 等 Web 标准配合。

名称 "D3" 是 data-driven documents 的缩写，其中 documents 指的是表示网页内容的文档对象模型（DOM）标准。

### D3 用于定制可视化

如果你需要最大的表现力来实现定制的可视化，你应该考虑 D3。D3 对于媒体组织（如纽约时报或 The Pudding）很有意义。

### D3 用于动态可视化

D3 最新颖的概念是其数据连接（data join）：给定一组数据和一组 DOM 元素，数据连接允许你对进入、更新和退出的元素应用不同的操作。

---

## 快速入门

### 在线试用 D3

最快的入门方式是在 Observable 上！D3 默认在 notebooks 中作为 Observable 标准库的一部分可用。

### D3 在原生 HTML 中

在原生 HTML 中，你可以从 CDN（如 jsDelivr）加载 D3，或者下载到本地。

#### ESM + CDN

```html
<!DOCTYPE html>
<div id="container"></div>
<script type="module">

import * as d3 from "https://cdn.jsdelivr.net/npm/d3@7/+esm";

// 声明图表尺寸和边距
const width = 640;
const height = 400;
const marginTop = 20;
const marginRight = 20;
const marginBottom = 30;
const marginLeft = 40;

// 声明 x（水平位置）比例尺
const x = d3.scaleUtc()
    .domain([new Date("2023-01-01"), new Date("2024-01-01")])
    .range([marginLeft, width - marginRight]);

// 声明 y（垂直位置）比例尺
const y = d3.scaleLinear()
    .domain([0, 100])
    .range([height - marginBottom, marginTop]);

// 创建 SVG 容器
const svg = d3.create("svg")
    .attr("width", width)
    .attr("height", height);

// 添加 x 轴
svg.append("g")
    .attr("transform", `translate(0,${height - marginBottom})`)
    .call(d3.axisBottom(x));

// 添加 y 轴
svg.append("g")
    .attr("transform", `translate(${marginLeft},0)`)
    .call(d3.axisLeft(y));

// 将 SVG 元素追加到容器
container.append(svg.node());
</script>
```

#### UMD + CDN

```html
<!DOCTYPE html>
<div id="container"></div>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
<script type="module">
// 同样的代码...
container.append(svg.node());
</script>
```

你也可以单独导入和解构各个 D3 模块：

```html
<script type="module">
import {forceSimulation, forceCollide, forceX} from "https://cdn.jsdelivr.net/npm/d3-force@3/+esm";

const nodes = [{}, {}];
const simulation = forceSimulation(nodes)
    .force("x", forceX())
    .force("collide", forceCollide(5))
    .on("tick", () => console.log(nodes[0].x));
</script>
```

### 从 npm 安装

```bash
yarn add d3
# 或
npm install d3
# 或
pnpm add d3
```

然后在你的应用中加载 D3：

```js
import * as d3 from "d3";
```

你也可以按需导入特定符号：

```js
import {select, selectAll} from "d3";
```

或者从 D3 子模块安装和导入：

```js
import {mean, median} from "d3-array";
```

TypeScript 声明可通过 DefinitelyTyped 获取。

### D3 在 React 中

大多数 D3 模块（包括 d3-scale、d3-array、d3-interpolate 和 d3-format）不与 DOM 交互，因此在 React 中使用它们没有区别。

```jsx
import * as d3 from "d3";

export default function LinePlot({
  data,
  width = 640,
  height = 400,
  marginTop = 20,
  marginRight = 20,
  marginBottom = 20,
  marginLeft = 20
}) {
  const x = d3.scaleLinear([0, data.length - 1], [marginLeft, width - marginRight]);
  const y = d3.scaleLinear(d3.extent(data), [height - marginBottom, marginTop]);
  const line = d3.line((d, i) => x(i), y);
  return (
    <svg width={width} height={height}>
      <path fill="none" stroke="currentColor" strokeWidth="1.5" d={line(data)} />
      <g fill="white" stroke="currentColor" strokeWidth="1.5">
        {data.map((d, i) => (<circle key={i} cx={x(i)} cy={y(d)} r="2.5" />))}
      </g>
    </svg>
  );
}
```

对于操作 DOM 的 D3 模块（包括 d3-selection、d3-transition 和 d3-axis），可以使用 ref 和 useEffect hook：

```jsx
import * as d3 from "d3";
import {useRef, useEffect} from "react";

export default function LinePlot({
  data,
  width = 640,
  height = 400,
  marginTop = 20,
  marginRight = 20,
  marginBottom = 30,
  marginLeft = 40
}) {
  const gx = useRef();
  const gy = useRef();
  const x = d3.scaleLinear([0, data.length - 1], [marginLeft, width - marginRight]);
  const y = d3.scaleLinear(d3.extent(data), [height - marginBottom, marginTop]);
  const line = d3.line((d, i) => x(i), y);
  useEffect(() => void d3.select(gx.current).call(d3.axisBottom(x)), [gx, x]);
  useEffect(() => void d3.select(gy.current).call(d3.axisLeft(y)), [gy, y]);
  return (
    <svg width={width} height={height}>
      <g ref={gx} transform={`translate(0,${height - marginBottom})`} />
      <g ref={gy} transform={`translate(${marginLeft},0)`} />
      <path fill="none" stroke="currentColor" strokeWidth="1.5" d={line(data)} />
      <g fill="white" stroke="currentColor" strokeWidth="1.5">
        {data.map((d, i) => (<circle key={i} cx={x(i)} cy={y(d)} r="2.5" />))}
      </g>
    </svg>
  );
}
```

### D3 在 Svelte 中

与 React 一样，你可以专门使用 Svelte 进行渲染，只使用不操作 DOM 的 D3 模块：

```svelte
<script>
  import * as d3 from 'd3';

  export let data;
  export let width = 640;
  export let height = 400;
  export let marginTop = 20;
  export let marginRight = 20;
  export let marginBottom = 20;
  export let marginLeft = 20;

  $: x = d3.scaleLinear([0, data.length - 1], [marginLeft, width - marginRight]);
  $: y = d3.scaleLinear(d3.extent(data), [height - marginBottom, marginTop]);
  $: line = d3.line((d, i) => x(i), y);
</script>

<svg width={width} height={height}>
  <path fill="none" stroke="currentColor" stroke-width="1.5" d={line(data)} />
  <g fill="white" stroke="currentColor" stroke-width="1.5">
    {#each data as d, i}
      <circle key={i} cx={x(i)} cy={y(d)} r="2.5" />
    {/each}
  </g>
</svg>
```

---

## API 模块索引

D3 由以下模块组成，按类别分组：

### 介绍 (Introduction)

- What is D3?
- Getting started
- API index
- Examples

### 可视化 (Visualization)

| 模块 | 说明 |
|------|------|
| d3-axis | 坐标轴 |
| d3-chord | 弦图（Chords, Ribbons） |
| d3-color | 颜色处理 |
| d3-interpolate | 插值（Value, Color, Transform, Zoom） |
| d3-contour | 等高线（Contour polygons, Density estimation） |
| d3-delaunay | Delaunay 三角剖分和 Voronoi 图 |
| d3-force | 力导向图（Simulations, Center, Collide, Link, Many-body, Position） |
| d3-geo | 地理投影（Paths, Projections, Streams, Spherical shapes/math） |
| d3-hierarchy | 层次结构（Hierarchies, Stratify, Tree, Cluster, Partition, Pack, Treemap） |
| d3-path | SVG 路径 |
| d3-polygon | 多边形 |
| d3-quadtree | 四叉树 |
| d3-scale | 比例尺（Linear, Time, Pow, Log, Symlog, Ordinal, Band, Point, Sequential, Diverging, Quantile, Quantize, Threshold） |
| d3-scale-chromatic | 配色方案（Categorical, Cyclical, Diverging, Sequential） |
| d3-selection | 选择集（Selecting, Modifying, Joining data, Events, Control flow, Local variables, Namespaces） |
| d3-shape | 形状（Arcs, Areas, Curves, Lines, Links, Pies, Stacks, Symbols, Radial areas/lines/links） |

### 动画 (Animation)

| 模块 | 说明 |
|------|------|
| d3-ease | 缓动函数 |
| d3-timer | 定时器 |
| d3-transition | 过渡动画（Selecting, Modifying, Timing, Control flow） |

### 交互 (Interaction)

| 模块 | 说明 |
|------|------|
| d3-brush | 刷选 |
| d3-dispatch | 事件调度 |
| d3-drag | 拖拽 |
| d3-zoom | 缩放 |

### 数据 (Data)

| 模块 | 说明 |
|------|------|
| d3-array | 数组操作（Adding, Binning, Bisecting, Blurring, Grouping, Interning, Set operations, Sorting, Summarizing, Ticks, Transforming） |
| d3-dsv | 分隔值（CSV/TSV）解析 |
| d3-fetch | 数据获取 |
| d3-format | 数字格式化 |
| d3-random | 随机数 |
| d3-time | 时间计算 |
| d3-time-format | 时间格式化 |

---

## d3-selection 模块

选择集（Selections）允许对文档对象模型（DOM）进行强大的数据驱动转换：设置属性、样式、属性、HTML 或文本内容等。使用数据连接的进入和退出选择集，你还可以添加或移除元素以对应数据。

主要子章节：

- **Selecting elements** - 查询 DOM 元素
- **Modifying elements** - 修改选中元素的属性
- **Joining data** - 将数据连接到选中元素进行可视化
- **Handling events** - 声明事件监听器进行交互
- **Control flow** - 遍历选中的元素
- **Local variables** - 将状态附加到元素
- **Namespaces** - 处理 XML 命名空间

---

## d3-shape 模块

可视化可以用离散的图形标记表示，如符号、弧形、线条和面积。d3-shape 模块为你提供了各种形状生成器。

与 D3 的其他方面一样，这些形状由数据驱动：每个形状生成器公开访问器，控制输入数据如何映射到视觉表示。

```js
const line = d3.line()
    .x((d) => x(d.date))
    .y((d) => y(d.value));
```

主要子模块：

- **Arcs** - 圆形或环形扇区，如饼图或甜甜圈图
- **Areas** - 由上边界线和基线定义的面积，如面积图
- **Curves** - 在点之间插值以产生连续形状
- **Lines** - 样条线或折线，如折线图
- **Links** - 从源到目标的平滑三次贝塞尔曲线
- **Pies** - 计算饼图或甜甜圈图的角度
- **Stacks** - 堆叠相邻形状，如堆叠柱状图
- **Symbols** - 分类形状编码，如散点图
- **Radial areas** - 类似面积，但在极坐标中
- **Radial lines** - 类似线条，但在极坐标中
- **Radial links** - 类似链接，但在极坐标中

---

## 推荐资源

- 官方网站: https://d3js.org/
- API 文档: https://d3js.org/d3-selection（各模块链接类似）
- 示例集合: https://observablehq.com/@d3/gallery
- Observable Plot（高级姐妹库）: https://observablehq.com/plot/

> 提示: 除非你需要 D3 的底层控制，推荐使用高级姐妹库 Observable Plot。Plot 简洁而富有表现力的 API 让你可以更多地关注分析和可视化数据。
