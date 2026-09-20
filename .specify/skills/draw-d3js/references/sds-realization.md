# SDS 实现（draw-d3js 语法层技术）

> 本文是 draw-d3js 作为**语法层**实现 SDS 的技术所有者：像素测量、viewBox、固定坐标 data-join、
> 坐标校验、档位线宽/深浅/字号的 D3 落地、偏离逼近。
>
> **不属于本文的事实（只引用，不复制）**：SDS schema、`weight_plan` 相对档位表、几何构建纪律、
> Deviation Declaration 规则的语义所有者是 `draw-diagram`（`../../draw-diagram/references/semantic-model.md`；
> standalone 安装下该同级技能可能不存在，此时以调用方传入的 SDS 文件为准）。
> tier→绝对线宽的**规范表**在 [SKILL.md](../SKILL.md) §「SDS 实现与强弱落地 · 强弱实现」——本文只给
> 理由、代码与例外规则，不复述数值表。

## 1. 输入契约与不可改写边界

| 项 | 归属 | 本技能的动作 |
|----|------|-------------|
| 逻辑模型（elements / relations / zones / diagram_class） | 语义层 | 读取，不增删元素、不改分组归属 |
| 几何（canvas、`box{x,y,w,h}`、分区盒、关系锚点与 gap） | 语义层 | 逐 box 精确落坐标（§3），零偏离 |
| `weight_plan` 档位归属（谁 T1、谁 T3） | 语义层 | 不改档位归属，只把档位落为绝对线宽（§2） |
| typography 相对层级（zone-title > element-label > annotation） | 语义层 | 落为绝对字号（§2.3） |
| 引擎语法、渲染质量、交互、导出 | **本技能** | 全权决定 |
| 复刻型的源图实测值 | 语义层测量并写入 SDS | **覆盖**本技能默认（§5） |

改写语义的典型错误：为"好看"把力导向打开重排节点、把等高分区改成自适应高度、把注释升格为节点、
把 T3 流线加粗到超过 T2、给关键路径加粗而不是只抬色相。

## 2. 强弱落地（怎么画粗，且把粗线画好）

### 2.1 档位→绝对线宽的理由

规范数值见 SKILL.md 的强弱表；这里记录**为什么这样映射**，便于后续调参不破坏判据：

1. **压缩顶端**：SDS 的相对档位是"注意力层级"，不是像素指令。大分区边界的**周长**远大于叶元素，
   线宽 × 周长 = 视觉墨量；若按相对值等比放大（T1 3.0px 起），大区边框会变成粗黑框压住内容。
   因此 D3 落地把顶端压到 2.5px：结构仍然最强，但不吃版面。
2. **保住可辨间距**：相邻档位差 ≥ ~0.4px——这是 1× 屏幕渲染与 2× PNG 导出后仍能被人眼稳定区分的最小间隔；
   差值 < ~0.3px 时两档读起来一样，等价于 SDS 判不合格的"全图单一线宽"。
3. **T4 设地板**：注释档不低于 ~1.2px。1px 以下的描边被反锯齿渲染成灰雾，导出 PNG / 打印后直接消失。
4. **保序即合格**：SDS 要的是**层级可辨**（单调递减 + 间距可辨），不是等比复刻相对数值。

### 2.2 深浅通道与色相纪律

线宽之外的第二通道是 stroke 深浅（单色复刻的默认阶梯，自上而下变浅）：

| 档位 | 默认 stroke 色 | 备选（主题图） |
|------|----------------|----------------|
| T1 | `#37474F` | `stroke-opacity: 1.0` |
| T2 | `#607D8B` | `0.85` |
| T3 | `#90A4AE` | `0.7` |
| T4 | `#A3B1BA` | `0.55` |

- **色相只编码语义**（路径类型/分组），**永不编码权重**：给 T3 流线上红色不会让它"变重"，只会误导读者。
- **关键路径**：按 SDS 规则只抬色相，`stroke-width` 封顶 = T2，不得反压结构层级。
- D3 写法：把档位挂在数据上，一次 join 落地，避免逐元素硬编码：

```javascript
// SDS 的 tier 随元素数据传入；线宽表 = SKILL.md 强弱表（此处不重复数值）
zoneSel.attr("stroke-width", d => TIER_PX[d.tier]).attr("stroke", d => TIER_INK[d.tier]);
flowSel.attr("stroke-width", d => TIER_PX[d.tier])
       .attr("stroke", d => d.keyPath ? KEY_HUE : TIER_INK[d.tier]);   // 关键路径只换色相
```

### 2.3 typography 落地

SDS 声明相对层级，语法层给绝对字号（默认阶梯）：zone-title 16px / element-label 13px / annotation 11px。

- **zone-title 用 `font-weight: normal`（或 500），不用 bold**：同字号加粗会让分区标题的视觉权重超过
  T1 边框本身，且与多数复刻目标的实测字重不符（cycle3 mandatory fix #1）。
- 文本溢出预算：CJK ≈ fontSize × 字数，ASCII ≈ fontSize × 0.6 × 字数；渲染后用
  `node.getComputedTextLength()` / `getBBox()` **实测**，超出所属 box 时按 §6 处理，不得擅自加宽 box。
- 双语标签（英文短名 + 中文职责副标题 ≤ ~12 字）时，副标题走 annotation 档字号与 T4 深浅。

## 3. 几何落地（绝对坐标管线）

d3js 是绝对坐标引擎：SDS 的 box 直接就是 SVG 用户坐标，**1:1、无缩放、无平移**。

### 3.1 viewBox 与 SDS canvas 对齐

```javascript
// canvas 来自 SDS；viewBox 与 canvas 严格 1:1，preserveAspectRatio 保证等比适配容器
const svg = d3.select("#chart").append("svg")
  .attr("viewBox", `0 0 ${sds.canvas.w} ${sds.canvas.h}`)   // 复刻例：源图 2000×1257 → "0 0 2000 1257"
  .attr("preserveAspectRatio", "xMidYMid meet")
  .style("width", "100%").style("height", "auto");
```

**不要**在 SDS 几何图上套用 margin 约定（`translate(margin.left, margin.top)`）——那会把每个已声明
box 整体平移，等于改写几何。margin 约定只用于坐标轴图表（bar/line/scatter 等 dataviz 形态）。

### 3.2 固定坐标 data-join（禁用力导向）

```javascript
// SDS elements/zones/relations → PANELS/NODES/EDGES，每条自带 box（x,y,w,h）
const panel = svg.selectAll(".zone").data(PANELS).join("rect").attr("class", "zone")
  .attr("x", d => d.box.x).attr("y", d => d.box.y)
  .attr("width", d => d.box.w).attr("height", d => d.box.h)
  .attr("fill", "none").attr("stroke-dasharray", d => d.dash ?? "6 4");

const node = svg.selectAll(".node").data(NODES).join("g").attr("class", "node")
  .attr("transform", d => `translate(${d.box.x},${d.box.y})`);
node.append("rect").attr("width", d => d.box.w).attr("height", d => d.box.h);
node.append("text").attr("x", d => d.box.w / 2).attr("y", d => d.box.h / 2)
    .attr("text-anchor", "middle").attr("dominant-baseline", "middle").text(d => d.label);
```

- 裸 `d3.forceSimulation` 起始位置随机、每次刷新布局不同，**与 SDS 几何契约直接冲突**：受委派绘制
  SDS 图时不启用仿真（无 tick、无随机种子问题）。`d3.drag` 可保留供人工微调，但落盘坐标仍以 SDS 为准。
- d3js-guide 的力导向配方（分组力导 / 预设坐标）只在 standalone、无 SDS 的探索型请求下使用。

### 3.3 关系锚点与间隙

```javascript
// anchor: edge-midpoint（默认）= 中心连线与目标 box 边框的交点；gap = 端点内缩像素
function edgePoint(from, to, gap = 0) {
  const cx = from.box.x + from.box.w / 2, cy = from.box.y + from.box.h / 2;
  const tx = to.box.x + to.box.w / 2,   ty = to.box.y + to.box.h / 2;
  const dx = tx - cx, dy = ty - cy;
  const sx = Math.abs(dx) * to.box.h > Math.abs(dy) * to.box.w   // 命中左右边还是上下边
    ? (to.box.w / 2) / Math.abs(dx || 1e-6)
    : (to.box.h / 2) / Math.abs(dy || 1e-6);
  return { x: tx - dx * sx - Math.sign(dx) * gap, y: ty - dy * sx - Math.sign(dy) * gap };
}
```

- `anchor: corner` → 取最近角点；`auto` → 取 Δ 较大的轴走 edge-midpoint（避免斜穿）。
- 跨分区边：走分区边框上的统一出入口锚点或正交（elbow）路由，别用长对角线切穿无关键区
  （`d3.line().curve(d3.curveStepAfter)` + 端口坐标；片段见 d3js-guide「Force-Directed Graph」）。
- 箭头 marker 尺寸随档位缩放（`markerWidth`/`markerHeight` 按 stroke-width 比例），否则 T3 细线的箭头
  会比 T1 边框更抢眼，破坏层级。

### 3.4 复刻型的像素测量管线

源图（PNG/截图/既有 SVG）给定时，几何从**测量**得来（语义层负责测量并写入 SDS；本节是测量技术）：

1. **画布**：1:1 缩放下读源图像素尺寸 → 直接作为 `viewBox`（如 2000×1257），不要缩放到"整千"。
2. **分区与节点盒**：逐个量左上角 (x,y) 与宽高 (w,h)；分区等高/列错位等版面语义照抄，不做"优化"。
3. **描边与虚线**：量每个角色的 stroke-width、dash 长度与间隙、色值（灰阶取样）→ 这些实测值就是
   §5 的覆盖权重，写回 SDS 的 `weight_plan`。
4. **字体**：量 zone-title / label / annotation 三档字号与字重（regular vs bold 必须实测，见 §2.3）。
5. **取数手段**：图像编辑器/截图工具的坐标读数，或无头浏览器里对既有 SVG 跑
   `el.getBoundingClientRect()` / `getBBox()`；比例估算时记录估算依据与不确定项（标 `uncertain`）。
6. **数据分离**：把 `PANELS/NODES/EDGES` 抽成 `<script type="application/json">` 块或外置 `data-*.js`，
   让校验器无需解析 JS 即可点数（cycle3 mandatory fix #2）；渲染逻辑从该块读取。

## 4. 坐标校验（渲染前跑，绿了才交付）

两道关：**内部一致性**（重叠/越界）与 **SDS 一致性**（逐 box 偏差）。

```javascript
// 关一：手工/实测坐标的重叠与分区越界检查；分区栅格规则记在数据文件头
// （例："panel A: x∈[40,360], y∈[40,300]; node slots on a 24px grid"）
function validateCoords(nodes, panels, minGap = 8) {
  const problems = [];
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      if (Math.abs(nodes[i].x - nodes[j].x) < minGap && Math.abs(nodes[i].y - nodes[j].y) < minGap)
        problems.push(`overlap: ${nodes[i].id} ↔ ${nodes[j].id}`);
    }
    const p = panels.find(pan => nodes[i].x >= pan.x0 && nodes[i].x <= pan.x1
                              && nodes[i].y >= pan.y0 && nodes[i].y <= pan.y1);
    if (nodes[i].panel && !p) problems.push(`out-of-bounds: ${nodes[i].id}`);
  }
  if (problems.length) console.warn("[coords]", problems.join("; "));
  return problems;
}

// 关二：SDS 一致性——绝对坐标引擎预期零偏离，容差只吸收浮点/取整
function validateAgainstSDS(rendered, sds, tol = 1) {
  const deltas = [];
  for (const e of sds.elements) {
    const r = rendered.find(x => x.id === e.id);
    if (!r) { deltas.push(`missing: ${e.id}`); continue; }
    for (const k of ["x", "y", "w", "h"])
      if (Math.abs(r.box[k] - e.box[k]) > tol)
        deltas.push(`${e.id}.${k}: sds=${e.box[k]} got=${r.box[k]}`);
  }
  if (deltas.length) console.warn("[sds]", deltas.join("; "));
  return deltas;   // 非空 → 修实现，不改 SDS；确实无法兑现 → 按 §6 量化声明
}
```

清点校验同样属于这一关：元素/边/分区**数量**与 SDS 一致（复刻例：21 nodes / 5 edges / 3 zones）。

## 5. 复刻型 SDS：源实测覆盖规则

**规则**：`fidelity_intent: reproduction` 时，SDS 携带从源图实测的线宽、字号、色值、dash 与几何；
这些实测值**覆盖**本技能的默认档位表与默认阶梯。默认表只服务于新建型（`fresh`）请求。

- 实测 T1 边框是 4px 就画 4px，**不要**"归一化"到默认值；实测 zone-title 是 regular 就不要加粗。
- 单色（monochrome）复刻不得引入彩色主题；`style_intent` 由 SDS 声明。
- 覆盖关系写进交付说明（哪些值来自实测、哪些用了默认），让验收方能区分。

**cycle3 质量实践**（generalized；原始记录见 [cycle3-reproduction-lessons.md](cycle3-reproduction-lessons.md)，
dated record，不作为当前规范引用）：

1. zone-title 字重 normal/500，不用 bold（§2.3）。
2. 数据抽离为可校验的 JSON 块（§3.4 步 6）。
3. 每分区一行角色注解（如 用户网络=入口、阿里云=托管云服务）作为标题下的弱副标题——**仅当**它不改变
   布局、不与组件重叠时才加；加了就要用 annotation 档字号/深浅。
4. `?clean=1` 静态快照里用 `<title>` 属性承载节点/边元数据：打印嵌入不带可见 HUD 也不丢信息。
5. 不可动的复刻不变量：像素实测的固定坐标与 viewBox、全部元素/箭头/分区在位、单色调色板与实测
   线宽/dash——**不得**切换为力导向布局。

## 6. 偏离策略（绝对坐标引擎）

1. **默认零偏离**：d3js 属绝对坐标引擎，MUST 精确兑现 SDS 几何与权重；预期偏离为零
   （规则所有者：semantic-model.md「Deviation Declaration」条 1）。因此本技能**不使用**自动布局引擎那套
   "脚手架逼近 + 声明无法兑现项"的路径——没有兑现不了的坐标。
2. **唯一合法的偏离来源是运行时事实**（SDS 无法预知）：浏览器字体度量让标签比实测 box 更宽、CJK 字形
   回退、导出栅格化取整。处理顺序：
   - 先在 box **内部**近似：字号降一档 / 折两行 / 截断展示名并把全名放进 `<title>` 或 tooltip；
   - 仍放不下 → 在交付说明里**量化声明**（偏离维度 + 幅度 + 原因，例：`node-07 label 超宽 6px，字号 13→12`）；
   - **绝不**为容纳文本而移动或放大 box——那是改写语义几何。
3. **未声明的偏离按 semantic-fidelity 扣分**；已声明的偏离计入语法实现质量，不算语义层缺陷。
4. 自查：交付前跑 §4 两道关 + 浏览器控制台无报错 + 导出 PNG 目视比对（复刻型与源图并排看）。
