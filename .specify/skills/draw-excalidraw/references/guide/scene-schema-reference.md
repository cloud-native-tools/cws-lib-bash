# `.excalidraw` 场景 JSON 元素参考

> 权威来源：官方 JSON Schema（https://docs.excalidraw.com/docs/codebase/json-schema）。
> 本文是 Agent 生成场景所需的最小子集 + 实测模板。渲染服务会经 `restore(refreshDimensions)`
> 补齐缺省字段并重算文本度量，因此**只需写对语义字段，样式细节可省**。

## 顶层结构

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "draw-excalidraw",
  "elements": [],
  "appState": { "viewBackgroundColor": "#ffffff", "gridSize": null },
  "files": {}
}
```

## 通用字段（所有元素）

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | ✅ | 字符串，语义化命名 |
| `type` | ✅ | `rectangle` / `ellipse` / `diamond` / `line` / `arrow` / `text` / `frame` / `image` |
| `x` `y` | ✅ | 左上角坐标（画布向右向下为正） |
| `width` `height` | ✅ | 尺寸 |
| `strokeColor` | 建议 | 描边/文字颜色，见色板 |
| `backgroundColor` | 建议 | 填充色；无填充用 `"transparent"` |
| `fillStyle` | 建议 | `"solid"`（实色，推荐）/ `"hachure"`（斜线）/ `"cross-hatch"`（交叉线） |
| `strokeWidth` | 可选 | `1` / `2`（默认）/ `4` |
| `strokeStyle` | 可选 | `"solid"` / `"dashed"` / `"dotted"` |
| `roughness` | 可选 | `0` 工整 / `1` 手绘（默认）/ `2` 狂草 |
| `opacity` | 可选 | 0–100 |
| `angle` | 可选 | 弧度，默认 0 |
| `seed` | 建议 | 任意整数（手绘随机种子） |
| `version` | 建议 | 给 `1` |
| `groupIds` | 可选 | `[]`；组合元素时填共同组 id |
| `frameId` | 可选 | 所属 frame 的 id |
| `roundness` | 可选 | 容器 `{ "type": 3 }`；线/箭头 `{ "type": 2 }`；尖锐则 `null` |
| `boundElements` | 容器必填 | 绑定的文本/箭头清单（见下） |
| `isDeleted` | 可选 | 恒 `false` |
| `updated` | 可选 | 时间戳，给 `1` 即可 |
| `link` `locked` | 可选 | `null` / `false` |

## 容器元素（rectangle / ellipse / diamond）

```json
{"id":"box-a","type":"rectangle","x":100,"y":100,"width":220,"height":90,
 "strokeColor":"#1e1e1e","backgroundColor":"#a5d8ff","fillStyle":"solid",
 "strokeWidth":2,"roughness":1,"opacity":100,"angle":0,"seed":11,"version":1,
 "groupIds":[],"frameId":null,"roundness":{"type":3},"isDeleted":false,
 "updated":1,"link":null,"locked":false,
 "boundElements":[{"id":"text-a","type":"text"},{"id":"arrow-1","type":"arrow"}]}
```

## 文本元素

独立文本（容器外标注/标题）：

```json
{"id":"text-a","type":"text","x":150,"y":132,"width":120,"height":25,
 "text":"网关","fontSize":20,"fontFamily":1,"textAlign":"center","verticalAlign":"top",
 "containerId":null,"originalText":"网关","lineHeight":1.25,
 "strokeColor":"#1e1e1e","backgroundColor":"transparent","fillStyle":"solid",
 "strokeWidth":2,"roughness":1,"opacity":100,"angle":0,"seed":12,"version":1,
 "groupIds":[],"frameId":null,"roundness":null,"boundElements":[],"isDeleted":false,
 "updated":1,"link":null,"locked":false}
```

容器绑定文本（推荐，自动居中）：`containerId` 填容器 id，`textAlign:"center"`、`verticalAlign:"middle"`，x/y 粗略即可（渲染端重算），同时容器 `boundElements` 登记 `{"id":"<text id>","type":"text"}`。

| `fontFamily` | 字体风格 |
|---|---|
| `1` | Excalifont 手绘体（默认；CJK 回落系统字体） |
| `2` | Helvetica/Nunito 无衬线 |
| `3` | Cascadia 等宽（代码） |

`fontSize` 常用 16（正文）/ 20（节点标题）/ 28（图标题）。

## 箭头 / 直线

```json
{"id":"arrow-1","type":"arrow","x":320,"y":145,"width":180,"height":0,
 "points":[[0,0],[180,0]],
 "startBinding":{"elementId":"box-a","focus":0,"gap":4},
 "endBinding":{"elementId":"box-b","focus":0,"gap":4},
 "startArrowhead":null,"endArrowhead":"arrow","lastCommittedPoint":null,
 "strokeColor":"#e03131","backgroundColor":"transparent","fillStyle":"solid",
 "strokeWidth":2,"strokeStyle":"solid","roughness":1,"opacity":100,"angle":0,
 "seed":13,"version":1,"groupIds":[],"frameId":null,"roundness":{"type":2},
 "boundElements":[],"isDeleted":false,"updated":1,"link":null,"locked":false}
```

- `points` 相对起点的折点序列，第一点恒 `[0,0]`。绘制只依赖 `points`；`width/height` 是折点包围盒尺寸（影响选区与导出裁切），取 `max|x|`/`max|y|` 量级即可，无需精确。
- `endArrowhead`：`"arrow"`（默认）/ `"bar"` / `"dot"` / `"triangle"` / `null`；`startArrowhead` 同理（双向箭头两端都设）。
- 绑定时同步更新两端容器的 `boundElements`；自由箭头（不绑定）两个 binding 给 `null`。
- `type: "line"` 同结构但无箭头语义（binding 恒 null）。

## frame（可选分组）

```json
{"id":"frame-1","type":"frame","x":60,"y":60,"width":560,"height":400,
 "name":"子系统 A","seed":14,"version":1}
```

成员元素设 `"frameId":"frame-1"`。frame 有标题栏，适合强分组；弱分组（纯背景色块）用垫底的大 rectangle 更美观。

## 标准色板（Excalidraw 官方）

| 用途 | 色值 |
|------|------|
| 描边/文字 | `#1e1e1e` 黑 · `#e03131` 红 · `#2f9e44` 绿 · `#1971c2` 蓝 · `#f08c00` 橙 · `#6741d9` 紫 |
| 填充背景 | `#ffc9c9` 红浅 · `#b2f2bb` 绿浅 · `#a5d8ff` 蓝浅 · `#ffec99` 黄浅 · `#eebefa` 紫浅 · `#99e9f2` 青浅 |
| 画布背景 | `#ffffff`（默认） |

同子系统同色系；跨系统关系用对比色箭头突出。

## 完整最小示例

两节点一箭头（可直接渲染）：见技能实测样例 `references/howto/03-scene-json-generation.md` 的骨架 + 上述模板组合；也可用渲染服务 `/mermaid-to-scene` 从 `flowchart LR; A-->B` 生成参照物。

## 强弱实现（接收 draw-diagram weight_plan）

语义层（draw-diagram）决定「什么该更显眼」，本技能决定「怎么画粗」。字段事实：`strokeWidth` 在场景 JSON 中接受**任意数值**（UI 预设 1/2/4 只是按钮档位）；深浅走 `strokeColor`（色板见上）。tier → strokeWidth 的映射表与钳位/深浅通道理由**不在此复述**——唯一 owner 见 [SKILL.md「SDS 实现与强弱落地」](../../SKILL.md) 与 [../sds-realization.md §3](../sds-realization.md)。全图单一线宽判不合格。
