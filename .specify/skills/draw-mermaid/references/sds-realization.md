# SDS 实现与逼近（Mermaid 语法层）

> 本文件是 draw-mermaid **语法层**的 SDS 落地 owner：Mermaid 专属的几何逼近脚手架、weight_plan 档位 → stroke-width 映射依据、偏离声明模板、渲染复现与回退链。SDS schema、weight_plan 档位语义、Deviation Declaration 规则的 owner 是 [../../draw-diagram/references/semantic-model.md](../../draw-diagram/references/semantic-model.md)——本文件不复述语义，只定义「怎么用 Mermaid 画出来」。输入契约与档位速查表见 [../SKILL.md](../SKILL.md) 「SDS 实现与强弱落地」。

## 1. 定位：自动布局引擎 = 逼近 + 声明

Mermaid flowchart 把布局交给 dagre：无绝对坐标 API、节点尺寸由文本反推、分区盒 content-hugging。按 semantic-model.md 的 Deviation Declaration 规则，mermaid 属**自动布局引擎**——以脚手架**逼近** SDS Geometry 是合法实现方式，但无法兑现项 MUST 量化声明（模板见 §5）；未声明的偏离按 semantic-fidelity 扣分，已声明的偏离计入本引擎语法实现质量、不算语义层缺陷。

## 2. 几何逼近技术（脚手架）

### 2.1 Ghost spacer 锚点（等高/顶对齐分区）

近似 SDS zones 的 `equal-height` / 顶对齐语义：在**每个** subgraph 内部的顶部与底部各放不可见锚点/占位节点（每 subgraph ≥2 个），用 `~~~` 串成贯穿链，强制各分区达到相近的纵向伸展：

```
subgraph ZA[用户网络]
  direction TB
  za_top[" "] ~~~ za1 ~~~ za2 ~~~ za_bot[" "]
end
style za_top fill:none,stroke:none,color:transparent
style za_bot fill:none,stroke:none,color:transparent
```

各分区标题须落在同一水平阅读线上；仅靠 content-hugging 会出现「某区塌成小盒、浮动在中部」的结构性失败（cycle3 证据，见 §7）。flowchart 逼近不了显式列高时可评估 `block-beta`。

### 2.2 `~~~` 行锁链（行序 / rank 控制）

`A ~~~ B` 是不可见连线：锁行序（谁在上一行）、把兄弟节点锁进同一 rank、固定叙事顺序。dagre 同时尊重**声明顺序**——源码里先声明的先摆，行锁链 + 声明顺序是本层仅有的两个 rank 控制手段。

### 2.3 Invisible links 列对齐

跨行放垂直 `~~~` 链可把不同行的节点拉进同列，近似 SDS 的 columns/grid 版面；配合 `%%{init: {flowchart: {nodeSpacing: 50, rankSpacing: 60}}}%%` 逼近 SDS 的 relation `gap`（只能逼近量级，不能精确到 px）。

### 2.4 wrappingWidth 陷阱

`flowchart.wrappingWidth`（默认 200px）会**静默折行**长标签 → 节点宽高被引擎改写 → 直接破坏 SDS box 近似与列宽规划。对策：`%%{init: {flowchart: {wrappingWidth: 1000}}}%%` 放开自动折行，换行点改由源码显式 `\n` 声明（可控、可 diff），不让引擎替你做几何决策。

### 2.5 curve: linear

SDS 的 relation anchor（edge-midpoint 直线）与 mermaid 默认贝塞尔曲线不符；复刻类 SDS 的源图多为直线 + 实心箭头。`%%{init: {flowchart: {curve: 'linear'}}}%%` 出直线折线，并核对 link 样式（`stroke-width` 按 §4 档位）与填充箭头，写入后**验证生效**（init 指令位置错误会被静默忽略）。

## 3. 渲染复现与回退链

- **版本 pin**：dagre 布局行为随 mermaid 版本漂移——同一脚手架在不同版本可能排出不同版面，使偏离声明失效。复刻/验收关键图必须固定版本（记录 mermaid.ink API 版本，或用固定版本的本地 mmdc），并把版本写入产物「可复现信息」块。
- **回退链（remote-first）**：远端 mermaid.ink（默认，`MERMAID_BACKEND=server`）→ 自建 mermaid.ink 兼容服务器（[../server/README.md](../server/README.md)，**本地 bundle**：镜像内置 mermaid + Chromium + Noto CJK 字体，渲染不依赖外网下载）→ 本地 mmdc（`MERMAID_BACKEND=local`，**必须先获用户确认**，脚本有 consent gate，绝不静默回退）。本地 bundle 保证远端不可用时布局引擎不变，偏离声明无需因后端切换重做；切换后端后仍应抽查版面未漂移。

## 4. weight_plan 档位 → stroke-width 映射依据

档位表（T1–T4 语义角色、默认相对线宽 3.0/2.0/1.5/1.0、关键路径封顶规则）的 owner 是 semantic-model.md；此处只记**映射为绝对 px 的依据与语法**：

1. **等比落 px**：相对层级 3.0 > 2.0 > 1.5 > 1.0 直接映射 3px > 2px > 1.5px > 1px——mermaid stroke-width 支持小数 px；1px 以下在 PNG 光栅（2x 导出）中不可辨，3px 以上分区框开始压过内容区，故 1–3px 是可用带宽，默认档位恰好占满。
2. **载体分工**：T1 用 `style <zoneSubgraphId> stroke:#333,stroke-width:3px`（顶层 cluster 边框，配最深 stroke 色）；T2 用 `classDef module stroke-width:2px` 挂到嵌套 subgraph / 组件节点；T3 用 `linkStyle default stroke-width:1.5px`（或按边索引逐条 `linkStyle 0,1,2`）；T4 用 `classDef note stroke-width:1px` 挂注释节点、配 `-.->` 虚线弱化。
3. **源实测覆盖**：复刻类 SDS 携带源图每角色实测线宽时，直接取实测值作绝对线宽，默认表让位（复刻不改版）。
4. **关键路径**：只以色相抬升（暖色/高饱和 stroke），线宽封顶 = T2，不得反压 T1 结构边界。
5. **typography 同构**：zone-title > element-label > annotation 的相对字号由 SDS 声明，绝对字号用 `%%{init: {themeVariables: {fontSize, ...}}}%%` 分层落实（模板见 [guide/style.md](guide/style.md)，不复述）。
6. **交付自检**：渲染产物中 T1/T2/T3 必须肉眼可辨地递减；全图单一线宽 = 不合格（验收判据 owner：semantic-model.md）。

## 5. 偏离声明模板

结果清单（委派回报 / HTML 输出说明区）MUST 内嵌下表；只写实测或可估的偏离，**不编造精度**：

```markdown
## Deviation Declaration（mermaid / dagre 自动布局）
| # | 偏离维度 | SDS 要求 | 实际渲染 | 幅度 | 原因 |
|---|---------|---------|---------|------|------|
| 1 | 精确坐标 | 元素 A box{x:240,y:80} | dagre 排至约 (256,96) | Δx≈16px, Δy≈16px | 无绝对坐标 API，仅 rank/序控制 |
| 2 | 分区等高 | 3 zones equal-height 顶对齐 | 中区短约 12px | ≈4% 高度 | content-hugging；已用 ghost spacer 逼近仍非精确 |
| 3 | 连线锚点 | edge-midpoint 直线 | linear 直线，锚点含节点 padding 偏移 | ≤6px | dagre 锚点自算，不可指定 |
```

声明纪律（owner：semantic-model.md Deviation Declaration）：未声明偏离 → semantic-fidelity 扣分；已声明偏离 → 计入语法实现质量，不计为语义层缺陷。

## 6. 渲染质量实践（保留项，与 SDS 无关仍生效）

- 无衬线字体：`%%{init: {'theme': 'default', 'themeVariables': {'fontFamily': 'Arial, Helvetica, sans-serif'}}}%%`（复刻类常要求；CJK 用渲染脚本默认 Noto 栈）。
- 导出分辨率 ≥2x（PNG_SCALE=2 / SVG_SCALE=3，脚本已默认），保证线宽档位差在光栅中可辨。
- PNG + SVG 双产出、HTML 全内联引用、可复现信息块：见 [howto/12-rendering-and-output.md](howto/12-rendering-and-output.md)。
- 有效字号/宽高比量测：`../scripts/measure-svg-layout.py`（判据见 SKILL.md「输出要求」）。
- 大图与样式专项：[guide/large-diagram-playbook.md](guide/large-diagram-playbook.md)、[guide/style.md](guide/style.md)。

## 7. 历史记录

[cycle3-reproduction-lessons.md](cycle3-reproduction-lessons.md) 是 Cycle 3 竞技评审的**dated 原始记录**（不作现行规范引用）；其脚手架修复项（等高锚点、`~~~` 行锁、sans-serif、2x 导出、版本 pin、curve:linear）已泛化为本文件 §2–§4、§6 的现行技术。
