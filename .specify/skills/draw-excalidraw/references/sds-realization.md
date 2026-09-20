# SDS 实现参考（Excalidraw 语法层）

> 本文件拥有「把 Semantic Drawing Spec（SDS）落实为 Excalidraw 场景 JSON」的**实现技术**。SDS schema（逻辑模型 / Geometry / weight_plan / Deviation Declaration）归 [../../draw-diagram/references/semantic-model.md](../../draw-diagram/references/semantic-model.md) 所有，此处不复述。本文的网格/坐标技术**只实现给定盒子，不决定版面语义**——谁和谁同区、谁居中、分区等高是语义层决策。

## 1. SDS 几何 → 场景 JSON（1:1 实现，零偏离）

场景 JSON 是绝对坐标系（px，左上原点），与 SDS geometry 同构，MUST 精确落实：

| SDS 字段 | 场景 JSON 落实 |
|---------|---------------|
| `canvas {w,h}` | 场景无画布尺寸字段；导出尺寸 = 内容包围盒 + `EXCALIDRAW_PADDING`（固定值）。canvas 用作**坐标边界校验**：所有 box 必须落在 canvas 内 |
| `elements[].box {x,y,w,h}` | 容器元素 `x/y/width/height` 照抄 |
| `zones[].box` | 垫底大矩形（浅色 `backgroundColor` + `fillStyle: "solid"`，写在成员之前）或 `frame`；尺寸 = zone box 照抄 |
| `relations[].anchor/gap` | 箭头 `startBinding`/`endBinding`（`focus: 0`，gap 取 SDS 值，缺省 4）+ `points` 折点 |
| weight_plan tiers | 见 §3 强弱映射 |

- 元素书写顺序：**zone 垫底 → 容器 → 绑定文本 → 箭头 → 注释**（同层先写者垫底）。
- **文本宽度校验**：估算式（CJK ≈ fontSize×字数；ASCII ≈ fontSize×0.6×字数；另加左右 padding 2×20）只用于**校验** label 能否装进 SDS box——装不下时量化回报语义层，**不得擅自加宽盒子或改字号层级**。
- 连线路由（纯语法）：正交水平/垂直优先；两端错位用 3–4 个折点绕行，不穿其他元素，必要时回报"需要更大间距"而不是挪盒子；`points` 只写折点（相对箭头起点，首点恒 `[0,0]`）。
- 箭头标签：独立 text 放最长水平段中点上方 20–30px、与箭头同色（T4 档）。
- SDS 的 box 清单同时就是 Step 6 回看的**验收清单**：逐 box 比对位置/尺寸/层级。

## 2. 场景 JSON 落实约定（确定性与绑定）

字段级编写规范见 [howto/03-scene-json-generation.md](howto/03-scene-json-generation.md)。SDS 实现相关的四条约定：

1. **containerId 绑定**：容器文本一律绑定（容器 `boundElements` 登记文本；`textAlign: "center"` + `verticalAlign: "middle"`）——渲染服务按真实字体度量重算尺寸并居中。
2. **复刻给精确居中坐标**：复刻场景下绑定文本坐标 MUST 写精确居中值——实测渲染器**不会**自动重居中（cycle3 R1 教训，见 [cycle3-reproduction-lessons.md](cycle3-reproduction-lessons.md)）。
3. **固定 seed**：所有元素给定固定整数 `seed`（`version: 1`），保证手绘随机纹理跨渲染可复现。
4. **钉住导出 scale**：`EXCALIDRAW_SCALE` 固定（如 2），PNG 像素尺寸 = viewBox × scale，跨导出确定。

渲染服务兜底：默认 `EXCALIDRAW_BACKEND=server` 远端渲染；服务不可达（exit 2）→ **先询问用户**（修正 `EXCALIDRAW_SERVER`，或经确认后 `local` 临时本机起服务），不得静默切换。处置细节见 [howto/04-rendering-and-output.md](howto/04-rendering-and-output.md) 与 [guide/server-deployment.md](guide/server-deployment.md)。

## 3. 强弱映射（tier → strokeWidth）理由

档位表与落实要点见 [SKILL.md「SDS 实现与强弱落地」](../SKILL.md)。理由补充：

- Excalidraw UI 线宽档为 1/2/4，但场景 JSON 接受任意数值：**T1=3** 落在 2 与 4 之间，恰好表达"强于组件边界、不抢全图焦点"。
- **T3 钳位 1.5→2**：Excalidraw 箭头笔画低于 2 时在手绘纹理与导出缩放下丢失细节、视觉上沦为发丝线，破坏 T3>T4 的可读层级；钳位后 T2 与 T3 数值同宽，**T2>T3 层级转移到深浅通道**——组件边界用更深笔画色、流线用更浅颜色（权重 = 粗细 + 深浅双通道；色相只编码语义路径）。
- 关键路径（`key_paths`）仅做**色相抬升**（更醒目颜色），strokeWidth 封顶 = T2，不得反压结构。
- zone 边界 `strokeStyle: "dashed"`：大面积围选的视觉重量由虚线 + 垫底浅色背景承担，避免实线粗框压住图面。
- typography 落实：zone/图标题 28 > 元素标签 20 > 注释 16（与 best-practices 字号三档一致）。

## 4. 复刻覆盖规则（fidelity_intent=reproduction / artifact_intent=pixel-reproduction）

手绘美学是引擎默认，**不是复刻目标的覆盖项**。复刻时逐条覆盖：

1. 全元素 `roughness: 0`——手绘抖动会产生双线/扭曲轮廓，复刻要单线 crisp。
2. zone/容器直角：`roundness: null`（不用圆角手绘角）。
3. zone 边界细虚线（`dashed`，短周期）。
4. 箭头锚定目标盒**边中点**，箭头尖端与边框留 2–4px gap，不贴角。
5. 同列组件盒宽高完全一致（SDS box 已统一，落实时不得漂移）。
6. 钉住导出 scale、固定 seed（§2）。
7. 走**场景 JSON 直出**，不走 Mermaid 桥接——桥接自动布局无法兑现 SDS 坐标，属未声明偏离。

`style_intent=hand-drawn` 与复刻意图冲突时按 SDS 声明执行；SDS 未声明则询问/回报假设，不擅自决定。

## 5. 无 SDS 直接调用时的兜底（自规划，非主路径）

直接调用且用户未给几何要求时，本技能临时承担语义角色自规划版面，并在回报中**声明"自规划版面"假设**（有 SDS 时本节一律不适用）：

1. **定基准尺寸**：普通节点 200×90、宽文本 260×90、小节点 140×60；全图统一 1–2 档。
2. **定间距**：同层兄弟 ≥80、层间 ≥100、分组内边距 ≥40、画布留白 ≥60；宁稀疏不拥挤。
3. **定方向**：深窄链式 → left-to-right；宽浅分层 → top-to-bottom。
4. **算坐标**：第 r 行第 c 列——top-to-bottom：`x = MARGIN + c×(NODE_W+GAP_SIBLING)`，`y = MARGIN + r×(NODE_H+GAP_LEVEL)`；left-to-right 互换 x/y。
5. **角色位置常识**（自规划参考；SDS 场景下属语义层决策）：枢纽居中偏上、入口在左/上、出口在右/下、外部系统靠边；同子系统同色系；一对多用代表元素 + `×N` 标注，不复制盒子。
6. 落 JSON 前先列规划表（元素 × 行/列/尺寸/颜色 + 箭头清单），兼作 Step 6 验收清单。
