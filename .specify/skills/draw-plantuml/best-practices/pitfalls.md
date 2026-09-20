# draw-plantuml 陷阱（Pitfalls）

> 从 viz-skill-arena 竞技 cycle（Substrate 架构图，2026-08-07）中 R1 评审实测发现的坑。每条含「现象 → 后果 → 规避」。最佳实践见 [best-practices.md](best-practices.md)。

## 1. 状态机只以 note 摘要出现

**现象**：状态机以序列图底部文字 note（`[*]→SUSPENDED→…→[*]`）代替独立 state 图。
**后果**：需求「状态机图」未交付，状态语义表达不完整；R1 裁判点名「建议补独立 stateDiagram」。
**规避**：状态机一律用独立 `state` 图交付，人工介入态（CRASHED）显式标注。

## 2. 每个组件都挂 note（信息密度爆炸）

**现象**：部署图/组件图每个组件框都挂多行 note（职责、端口、机制细节全写）。
**后果**：整体拥挤、可读性差，视觉分被扣。
**规避**：note 精简为「端口 + 职责」两行；仍拥挤则拆子图。

## 3. component 嵌套表达分组

**现象**：用 component 嵌套（component inside component）表达 namespace/节点分组。
**后果**：分组语义弱、结构不直观（R1 实测点名）。
**规避**：改用 `package` / `rectangle` 显式分组并加分组标签。

## 4. 序列图关键路径无视觉引导

**现象**：group/alt/opt 区块颜色与 activate 层次对比度一般，关键路径（Resume 工作流）与普通路径无区分。
**后果**：读者难以跟踪主流程，视觉引导弱。
**规避**：关键路径加高亮色块。

## 5. HTML 不附渲染命令与源码

**现象**：交付 HTML 只引用渲染后的图片，无 `.puml` 源码、无 `render-plantuml.sh` 调用说明。
**后果**：无法复现、无法重渲，reproducibility 降分。
**规避**：HTML 内嵌 puml 全文 + 渲染命令。

## 6. 跨层连线不规划（长线交叉）

**现象**：组件排列顺序随意，枢纽组件与周边组件的连线横穿整图。
**后果**：长连线交叉密集，布局凌乱。
**规避**：组件按「入口 → 枢纽 → 出口」排列；跨层边经枢纽汇聚。

## 7. 数据/状态存储无独立图

**现象**：双层资源模型（CRD ↔ 状态库）信息只散落在组件图 note 中，无独立分层图。
**后果**：需求「资源模型图」未真正交付，信息组织被评散乱。
**规避**：声明层（CRD/etcd）↔ 动态层（Valkey）用独立 package 分层图交付。

## 8. HTML 附录源码与磁盘 .puml 不一致

**现象**：HTML 复现性附录的 puml 源码是手抄/简化版——缺 shadowing/roundCorner/dpi/scale/defaultFontName，却多出 actorStyle awesome。
**后果**：按 HTML 重渲无法复现实际产物，reproducibility 降分。
**规避**：附录源码直接从磁盘 `.puml`（含渲染脚本注入的样式块）复制，逐字节一致（见 best-practices §6 与 [12-rendering-and-output.md §4.4](../references/howto/12-rendering-and-output.md)）。

## 9. 图内口径与 HTML 文字矛盾

**现象**：HTML 叙述「XX 以 DaemonSet 形态运行」，图内却是普通节点内组件；或旧组件形态画成当前活跃层。
**后果**：读者/评审判定架构理解错误，可信度受损。
**规避**：图与文同一口径；旧架构/时间点显式标注（见 best-practices §9）。

## 10. legend 色块换后端后未复验

**现象**：`<back:#…>` 色块与 CJK 字体渲染依赖渲染服务；换服务器/改用本地 jar 后图例色块空白或中文豆腐块。
**后果**：图例契约失效，颜色语义丢失。
**规避**：换渲染后端后重渲，肉眼复验图例色块与 CJK 字体（见 [style.md §十](../references/guide/style.md)）。

## 11. SVG 未固定长宽比导致拉伸变形（人工确认的严重缺陷）

**现象**：PlantUML 服务器输出的 SVG 根元素为 `preserveAspectRatio="none"` 且无 width/height——浏览器新窗口打开时按容器拉伸，图形变形，用户端无法正确显示。
**后果**：最终用户打开 SVG 时图形扭曲，绘制效果失效（人工检视确认的 P0 级显示问题）。
**规避**：渲染后必须执行 `fix_svg_aspect`（`render-plantuml.sh` 内置）——从 viewBox 推算等比 width/height（长边 ≤2400px）并改 `preserveAspectRatio="xMidYMid meet"`；验证时检查 SVG 根元素三属性齐备（见 [12-rendering-and-output.md §二-3](../references/howto/12-rendering-and-output.md)）。

## 12. 字号不统一（per-kind 默认值各异 + 块内覆盖残留）

**现象**：不同图表字号看起来不一致——源 `.puml` 常带 `skinparam component { FontSize 14 }` / `package { FontSize 15 }` 等块内覆盖；且 PlantUML 各元素字号参数（`packageTitleFontSize`/`legendFontSize`/`sequenceMessageFontSize` 等）默认值各异，**不跟随 `defaultFontSize`**，导致 package 标题/图例/序列图 group 标题仍用旧字号。
**后果**：跨图、跨图集字号不统一，视觉杂乱；用户端观感不一致。
**规避**：渲染脚本已统一处理——`strip_style` 删除块内 `FontSize N` 覆盖行，注入块显式设置全部元素字号参数为 16（`defaultFontSize`/`titleFontSize`/`captionFontSize`/`noteFontSize`/`stereotypeFontSize`/`legendFontSize`/`packageTitleFontSize`/`sequenceMessageFontSize`/`sequenceActorFontSize`/`sequenceGroupTitleFontSize`）。验证：SVG 中 `font-size` 应只有单一值（16×12.5=200）。

## 13. 全图统一线宽（边框与流线无强弱分层）

**现象**：zone 框、子模块框、叶元素框与流线全部同粗细同深浅（典型：脚本旧基线统一 2px + 关键路径 2px 彩线），结构层级与数据流在视觉上同档竞争。
**后果**：注意力无落点——读者无法先抓「有哪些大块」再读交互，整图显杂乱；07 号组件图 v2 初版被用户纠正「强弱模糊、线段和边框没有进行强弱的区分看起来很杂乱」。
**规避**：编码前先做强弱计划（[style.md §十一](../references/guide/style.md)）：大区 `rectangle` 3px 最深 > 子模块 `package` 2px 中 > 叶元素 1px 浅 > 流线 1px 最浅；关键路径只用色相抬升、`[thickness=2]` 封顶。渲染后 `grep -oE 'stroke-width:[0-9.]+' <out>.svg | sort -u` 须 ≥3 档。注意：**嵌套 `<style>` 选择器（`package { package { … } }`）实测不生效**，必须用扁平选择器 + 元素关键字分档。
