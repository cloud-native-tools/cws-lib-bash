# SDS 实现（draw-echarts 语法层）

> **边界**：SDS（Semantic Drawing Spec：逻辑模型 + Geometry + weight_plan + typography 层级）的 schema 与语义决策 owner 是 draw-diagram 技能（[semantic-model.md](../../draw-diagram/references/semantic-model.md)）。本文件只覆盖**语法层**：如何把 SDS 的几何与强弱在 ECharts 中精确兑现，以及固定坐标复刻管线与渲染质量实践。技法出处：cycle3 竞技复盘（dated record：[cycle3-reproduction-lessons.md](cycle3-reproduction-lessons.md)，仅作历史依据，现行规范以本文件为准）。

## 1. 输入契约与偏离策略

- 输入 = SDS 文件路径（file-path-only handoff）。元素、关系、分区、盒位、档位分配一律**照单兑现，不得改写语义**——发现 SDS 可疑时回报前门仲裁，不静默"优化"。
- ECharts（`graph layout:'none'`、`graphic` 绝对坐标）是**绝对坐标引擎**：MUST 精确实现 SDS 几何与权重，**预期零偏离**。
- 确实无法兑现的项（如真正的部署层次、时序图的时序轴）：逼近 + 按 Deviation Declaration 规则**量化声明**（偏离维度 + 幅度 + 原因）。已声明的偏离计入语法实现质量；未声明的偏离按 semantic-fidelity 扣分。

## 2. 几何兑现：SDS box → ECharts 坐标换算

| SDS 几何项 | ECharts 兑现 |
|-----------|-------------|
| `canvas {w,h}` | 图表容器尺寸 = canvas px；同时写入 config `meta.canvasWidth/Height`（`check-layout.mjs` 读取） |
| 图元 `box {x,y,w,h}`（左上角原点） | `graph` 节点 x/y 是**盒中心**：`{ x: box.x + w/2, y: box.y + h/2, symbolSize: [w, h] }` |
| zone `box` | `graphic` rect：`{ left: box.x, top: box.y, width: box.w, height: box.h, z: 0 }`（graphic 同为左上角原点，直映） |
| relation `anchor: edge-midpoint, gap` | 端点 = 源/目标盒的边中点坐标，按 `gap` px 沿线内缩；箭头落点必须在目标盒**边中点**，不落盒角、不落盒底 |
| 节点形状 | 精确复刻用 per-node `path://` 圆角矩形（radius 10，按实测 w/h 生成路径）；一般场景 `symbol: 'roundRect'` + `symbolSize: [w,h]` 亦可 |

`layout:'none'` 为 SDS 驱动交付的唯一合法布局；force/circular 只属于无 SDS 的关系视图。

## 3. Bounds-fit 角锚点（消除死白）

固定坐标 graph 的包围盒由数据点自动拟合，导出视口与内容错位会产生底部/侧边死白（cycle3 实测 ~15% 底部空带）。技法：加入 **4 个隐形 1×1 角锚点节点**，坐标 `(0,0) (W,0) (0,H) (W,H)`（W/H = canvas 尺寸），样式 `itemStyle.opacity: 0`、`label.show: false`、不参与 tooltip/legend。效果：graph 包围盒 ≡ canvas，导出视口按内容包围盒裁切即与 SDS 画布恒等（bounds-fit identity）。**此 4 锚点是必需项，不得删除**。

## 4. 边线 lines-series 压节点（精确落点）

graph 内建 `links` 的边由引擎路由，箭头落点与层叠不可控（cycle3 缺陷：无箭头、落点进盒底）。精确复刻时把边改画为**独立 `lines` series，`z` 高于节点 series**：

```javascript
series: [
  { type: 'graph', layout: 'none', z: 2, data: nodes /* 含 4 角锚点 */ },
  { type: 'lines', z: 3, coordinateSystem: undefined /* 像素坐标 */,
    polyline: true,                    // 正交/多段路由
    symbol: ['none', 'arrow'], symbolSize: [8, 8],
    lineStyle: { width: 1.6, opacity: 1, curveness: 0 },
    data: [{ coords: [[x1,y1],[xm,ym],[x2,y2]] }] }   // 显式折点，末点 = 目标盒边中点 - gap
]
```

- 每条有向边必有可见实心三角箭头，方向沿线指向目标盒；
- 所有边 `lineStyle.opacity: 1`（半透明是已修复缺陷，不得回归）；
- 简单直线边可留在 graph `links`（`edgeSymbol: ['none','arrow']`），精确落点/正交路由走 `lines` series。

## 5. 固定坐标复刻管线（测量 → config JSON → render.mjs）

1. **目标像素测量**（语义层职责）：复刻类 SDS 由 draw-diagram 从源图测量产出 canvas、每图元盒位、每角色实测线宽；语法层只消费测量值。仅当无 SDS 直接调用复刻需求时，本层才自行测量（量像素，不目测）。
2. **config JSON**（唯一权威）：全部节点坐标/尺寸/分区/边折点落进 `*.config.json`（含 `meta.canvasWidth/Height` 与栅格规则）；`*.config.js` 包装由 `node scripts/sync-config.mjs <file>.config.json` 生成（禁止手工双写；`scripts/` 相对技能根目录）；交付前 `node scripts/check-layout.mjs <config>` 查越界/重叠。
3. **render.mjs 确定性导出**：为交付物写一个小 Node 导出脚本（`render.mjs`，随交付物存放，非本技能 scripts/ 固定资产）：ECharts SSR（`echarts.init(null, null, { renderer: 'svg', ssr: true })`）或 headless chromium（`--screenshot=render.png --window-size=<canvas w,h>`）；导出时 `animation: false`、`toolbox: { show: false }`、固定 `pixelRatio` → 同 config 必得同图（确定性）。PNG 随 HTML 一并交付作渲染证明。

## 6. Tier 映射理据与复刻覆盖规则

- **理据**（映射表 owner = SKILL.md「SDS 实现与强弱落地」，此处不重述数值）：SDS 相对档位落为绝对 px 时，保持相邻档 ≥0.4px 的可辨步长（1× DPI 下肉眼可分），同时把边界类压在"重框"阈值以下——T1/T2 走盒边框（`graphic` rect `lineWidth` / `itemStyle.borderWidth`），T3/T4 走线宽（`lineStyle.width`）；相对序严格单调递减即合格。色相只编码语义路径，永不编码权重；关键路径仅色相抬升、粗细封顶 ≤ T2，不得反压结构。typography 同构：zone-title > element-label > annotation，相对层级由 SDS 声明，绝对字号本层按 canvas 比例选定（复刻按源图实测）。
- **复刻覆盖规则**：`fidelity_intent=reproduction` 的 SDS 携带**源图实测的每角色线宽**，实测值即规范，1:1 覆盖 SKILL.md 默认映射；默认映射只适用于新建类请求、或 SDS 仅给出相对档位而无实测值时。实测值与默认档位冲突时：**实测 > 默认**，且不得把实测值"归整"到默认档位。
- 全图单一线宽/单一边框粗细判不合格（语义层验收维度）。

## 7. 渲染质量清单（cycle3 固化，交付前逐项过）

- [ ] 每条有向边有可见箭头，落点在目标盒边中点、方向沿线（不进盒底、不落盒角）
- [ ] 导出图（render.png）**无任何 UI chrome**：toolbox saveAsImage 按钮隐藏或导出期关闭
- [ ] 无死白：导出视口 = 内容包围盒；4 角锚点在位
- [ ] 无投影：`shadowBlur`/`shadowColor`/`shadowOffset` 全禁用，干净单线描边
- [ ] 所有边 `lineStyle.opacity: 1`
- [ ] SDS 元素/边/分区全量在位、标签正确（覆盖检查归前门，本层不自减）
- [ ] config JSON 为唯一权威、js 包装生成、`check-layout.mjs` 通过
