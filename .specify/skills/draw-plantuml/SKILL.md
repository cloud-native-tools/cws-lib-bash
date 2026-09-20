---
name: draw-plantuml
description: |
  Draw system architecture diagrams with PlantUML, render to SVG/PNG via PlantUML server, and output as HTML with rendered images.
  Use standard UML semantics (Component, Deployment, Sequence, Class/Package) to describe system architecture.
  Also supports six non-UML specialty diagrams with native @start tags: WBS (工作分解结构), Gantt (甘特图), MindMap (思维导图), JSON 数据可视化, YAML 显示效果图, Salt UI 线框图;
  plus ER 实体关系图 (@startuml + entity, crow's foot) for database design.
  Use when the user mentions "架构图", "architecture diagram", "UML图", "plantuml", "系统架构图", "画架构", "设计图", "组件图", "部署图", "时序图", "类图", "包图", "系统设计",
  "流程图", "状态图", "活动图", "用例图", "状态机图", "模块图", "交互图",
  "sequence diagram", "class diagram", "component diagram", "deployment diagram",
  "activity diagram", "state diagram", "use case diagram", "package diagram",
  "工作分解结构", "WBS", "甘特图", "gantt", "项目计划图", "进度图", "思维导图", "mindmap", "脑图",
  "JSON可视化", "JSON数据图", "json diagram", "YAML可视化", "YAML显示", "yaml diagram", "配置可视化", "数据结构图",
  "ER图", "实体关系图", "数据库设计", "数据建模", "表结构", "ERD", "entity relationship", "crow's foot",
  "UI原型", "线框图", "wireframe", "界面原型", "salt", "界面草图",
  "复刻图", "图片重绘", "图片转UML", "replicate diagram", "redraw", "image to UML"
skill_id: "<SKILL:.specify/skills/draw-plantuml/SKILL.md>"
---

# 架构图绘制技能

使用 PlantUML 语法和标准 UML 语义绘制系统架构图，通过 PlantUML 服务器渲染为 SVG/PNG，并输出为包含渲染图表和说明文字的完整 HTML 文档。

## 核心原则

- **UML 语义，而非随意方框**：UML 类图表必须遵循标准 UML 图表类型，使用正确的 UML 元素和关系
- **架构优先的叙事**：图和文字互补——文字解释*为什么*，图展示*什么*
- **统一样式**：使用 `skinparam` / `<style>` 保持统一样式，UML 图每张核心元素 ≤7 个（硬上限 ≤15）
- **语义视觉强弱分层**：结构权重 > 流权重——**大模块边框 > 小模块边框 > 模块间流线**；**粗细+深浅编码权重（注意力吸引），色相编码语义路径**；禁止全图统一线宽/统一边框粗细（默认档位表与经渲染验证的写法见 [style.md §十一](references/guide/style.md)）。**受委派时"什么该更显眼"由 SDS `weight_plan` 决定（语义层），本技能只负责"怎么画粗"**——见「SDS 实现与强弱落地」与 [references/sds-realization.md](references/sds-realization.md)
- **远端渲染优先**：默认只使用 PlantUML 服务器渲染（`render-plantuml.sh` 默认 `PLANTUML_BACKEND=server`），**不下载、不配置本地渲染工具链**（plantuml.jar / graphviz / 字体）；远端不可用时，必须先询问用户是否改用本地渲染（`PLANTUML_BACKEND=local`），**未获用户确认不得本地渲染**
- **专项图表遵循其原生语义**：WBS/甘特图/思维导图/JSON/YAML/Salt 六类非 UML 图表使用各自的原生语法（`@startwbs`/`@startgantt`/`@startmindmap`/`@startjson`/`@startyaml`/`@startsalt`）与原生配色，不套用 UML 的 skinparam 单色规则；ER 图虽被官方归为非 UML，但用 `@startuml` + `entity` 语法、走 Graphviz 布局，按 UML 图同套 skinparam 规范处理

### 方法论总纲（贯穿全流程，先「对」与「达意」再「好看」）

下述四支柱是本技能所有优化手段的固化总纲，**单一事实来源为 [guide/diagram-principles.md](references/guide/diagram-principles.md)**（图表类型无关，适用于任意图；大图专项另见 [guide/large-diagram-playbook.md](references/guide/large-diagram-playbook.md)）。工作流各步都服从它：

1. **上下文驱动**：UML 脱离程序上下文无意义——先吃透文档/代码/描述、产出带出处的上下文摘要，保证程序整体正确、不臆造（principles §4.1）。
2. **减法与拆分**：信息量大时优先整洁美观而非面面俱到，每图突出**一个核心点**；单图表达不下则按架构接缝**拆为图集**（概览图 + 下钻子图，图间层次与交叉引用，每图自足，图集共享稳定词汇）（principles §4.2/§4.3）。
3. **UML 语义 + 视觉语义**：先选对图类型/元素种类/关系/构造型/接口（§1）；再按人类视角规划视觉语义——角色即位置、一对多用「单代表+多重性」、关联即同色、分组即框选（§2）。
4. **文字修饰 + 收尾美化**：元素上只留简洁标题、详解外置到布局安全的 note、字号层级跨图统一（§3）；最后做对齐/着色/线条与大图专项美化（playbook）。

## SDS 实现与强弱落地

**输入契约**：经 draw-diagram 前门委派时，输入是 **SDS（Semantic Drawing Spec）文件路径**——逻辑模型 + 几何（canvas、每图元 `box{x,y,w,h}`、zone box、relation anchor）+ `weight_plan` 档位 + typography 层级；schema、档位语义与偏离规则属语义层（[../draw-diagram/references/semantic-model.md](../draw-diagram/references/semantic-model.md)）。本技能**只做实现，不改语义**：不得增删/重命名元素与关系、不得改写 zone 成员与 `layout`（equal-height/stack/grid/free）语义、不得"优化"复刻版面；仅 SDS 缺项时按本技能默认流程补，并在回报中声明补了什么。

**强弱实现**：SDS 只给相对档位，绝对线宽由本引擎落实（下表值经 PlantUML server 实测）——**T1** 大模块/分区边界 `skinparam rectangle<<zone>> { BorderThickness 3 }`（stroke-width 37.5 @scale4）、**T2** 小模块/子容器边界 `rectangle<<sub>>`/`package` `BorderThickness 2`（25）、**T3** 数据流 `skinparam ArrowThickness 1.2`（15）、**T4** 注释保持基线不加粗 + `noteFontColor` 压浅。档位常量用 `!define` 宏承载、再由 stereotype 作用域 skinparam 引用（渲染脚本 `strip_style` 会删除与注入键同名的**扁平 skinparam 行**，宏行与作用域块不在剥离集合内）；虚线分区用块内 `BorderStyle dashed`——**内联 `#line.dashed` 尾缀会把粗细重置回基线**。**复刻类 SDS 携带源图实测权重时，以该实测值覆盖上述默认档**，不得回落。关键路径只在 T3 内用**色相**抬升、`[thickness=2]` 封顶（≤T2）。

**几何**：PlantUML 走 graphviz **自动布局，没有绝对坐标通道**，只能逼近 SDS 几何——`skinparam rectangle<<zone>> { MinimumWidth N }` 逼近 zone 宽/拉平多 zone 等宽、`-[hidden]down-` 锁秩、`-[hidden]right-` 拉同排（不改秩）、`<<ph>>` 透明占位节点撑高、方向关键字 + `nodesep`/`ranksep` 控宽高比。**SDS 中无法兑现的项（精确 x/y、等高/等宽分区、列错位 stagger、relation anchor/gap）必须量化声明**（偏离维度 + 实测幅度 + 引擎原因）；未声明的偏离按 semantic-fidelity 扣分，已声明的计入引擎实现质量。

→ 落地配方、实测数据、量测自检（measure 量具）与偏离声明模板：[references/sds-realization.md](references/sds-realization.md)

## 工作流

按以下 8 个步骤顺序执行；每步都服从上面的「方法论总纲」四支柱。每步核心说明如下，详细操作阅读对应参考文档。

### Step 1: 语义解析 + 吃透上下文（上下文驱动）

分析用户输入以理解绘制意图；通过补充推断或交互式提问（`AskUserQuestion`，最多一轮 ≤4 个问题）确认意图。**面对文档/代码等丰富上下文时，先产出一份带出处的上下文摘要**（组件、关系、核心流程、关键决策），后续绘图与自检都对着它，保证程序整体正确、不臆造。

→ [00-semantic-analysis.md](references/howto/00-semantic-analysis.md)；上下文驱动见 [diagram-principles.md §4.1](references/guide/diagram-principles.md)

### Step 2: 选图类型 + 定「单图 or 图集」（减法与拆分）

从 8 种标准 UML 图表类型中选最合适的一或多种，每图聚焦**单一视角/一个核心点**。**信息量大或多面时做减法与拆分**：优先整洁美观而非面面俱到；单图表达不下则按架构接缝（分层/控制面数据面/静态行为/请求制品流/系统节点边界）**拆为图集**——一张概览/索引图在顶 + 下钻子图，图间体现层次与交叉引用（`▶ 见 图N`），每图自足，图集共享稳定词汇（编号/颜色/构造型跨图同义）。**若任务/需求清单点名了多类图（如"5 类图"），逐项核对每类图都有独立图表交付——note/文字摘要顺带出现不算完成该类图**（需求清单覆盖检查见 [01-choose-diagram-type.md](references/howto/01-choose-diagram-type.md)）。

→ [01-choose-diagram-type.md](references/howto/01-choose-diagram-type.md)；减法与拆分见 [diagram-principles.md §4.2/§4.3](references/guide/diagram-principles.md)

### Step 3: 选元素 + 关系（UML 语义正确）

选正确的 UML 元素种类（组件/节点/制品/数据库/接口/类/状态…）与关系类型（依赖/关联/实现/通信路径/控制信号/«deploy»«manifest»…）、构造型与多重性；为对外契约补 `interface` 与端口。**元素种类本身即语义，勿一律用 rectangle/component。**

→ [references/howto/](references/howto/)（02–09）；UML 语义先行见 [diagram-principles.md §1](references/guide/diagram-principles.md)

### Step 4: 规划布局 + 视觉语义（人类视角）

**受 draw-diagram 委派时，本步不重做语义决策**：角色即位置、分区/等高/错位、方向与宽高比、强弱档位分配都由 SDS 的 geometry + `weight_plan` 给定（见「SDS 实现与强弱落地」）；本步只做**逼近实现**——把 SDS 几何翻成 stereotype 作用域 skinparam + 隐藏边秩脚手架 + 透明占位节点，并**量化声明**无法兑现项（[references/sds-realization.md](references/sds-realization.md)）。

无 SDS 输入（用户直接调用本技能）时，编码前自行规划空间语义：
- **视觉语义**：角色即位置（枢纽居中偏上、节点沿边/底，Hub/Edge/Entry/Sink）；一对多用**单代表元素 + 多重性标注**（`collections`/堆叠阴影/«×N»），不画 N 份兄弟盒；关联即同色（同子系统同色相族）；分组即框选（宏观逻辑分区用可见具名 frame、同类细分组用不可见 frame）。
- **方向/宽高比决策**：数「最宽层宽 B」与「主流深 D」选方向（宽浅 `top to bottom`、深窄长链 `left to right`）；`C≈round(sqrt(N×1.3))` 估列数摆近正方形网格（嵌套图每个 frame 内同理）；单层兄弟 ≤6，超出下沉/拆 frame。
- **强弱计划（语义视觉权重）**：编码前把每个 frame/元素/边族分配到权重档——默认三档：大区边框（最粗最深）> 子模块边框 > 流线（最细最浅）；关键路径在流线档内**用色相不用粗细**抬升，且粗细不得超过子模块边框档（档位→元素关键字映射与 `<style>` 写法见 [style.md §十一](references/guide/style.md)）。

→ [10-layout-planning.md](references/howto/10-layout-planning.md)、[layout.md §一/§2.1/§2.5](references/guide/layout.md)；视觉语义见 [diagram-principles.md §2](references/guide/diagram-principles.md)

### Step 5: 生成 PlantUML 代码

按所选图类型操作指南与语法编写代码：`@startuml`/`@enduml` 包裹，先声明元素再声明关系，用方向关键字与分组（`together`/隐藏边）控制布局。

→ [11-code-generation.md](references/howto/11-code-generation.md)、[syntax-reference.md](references/guide/syntax-reference.md)

### Step 6: 文字修饰（独立一步）

单独治理图元文字：**元素上只留很简洁的标题**（先去重——已被 interface/stereotype/嵌套表达的删掉）；**详细清晰的说明外置到 `note`**（用完整语言，非碎片；布局安全否则省——深层嵌套成员的 note 常被引擎甩到页边，改折叠进父级 note 或 legend）；**字号统一为 16px**（`skinparam defaultFontSize 16`，渲染脚本自动注入，UML 与专项图同值；跨图集一致，禁止 per-kind 差异化字号），**禁用零散内联 `<size:>`/`**bold**`**（字号/粗细不一的头号成因）。

→ [diagram-principles.md §3](references/guide/diagram-principles.md)、[content.md](references/guide/content.md)

### Step 7: 应用样式 + 大图专项（对齐·着色·线条）

应用统一 skinparam/色彩模式，确保视觉一致；**并按强弱计划落地权重档**：边框粗细/深浅按档递减（大区 > 子模块 > 叶元素），流线默认细浅、关键路径色相抬升且粗细 ≤ 子模块档。**大图（节点多/尺寸大）套用大图技术栈**：×N 语义折叠、弱化管线突出语义色、正交路由 + 隐藏边控宽高比消交叉、连线治理、隐藏脚手架的能与不能、legend 作单一细节仓；只用 SVG 交付大图。

→ [style.md](references/guide/style.md)、[large-diagram-playbook.md](references/guide/large-diagram-playbook.md)；受委派时档位落地与几何逼近配方见 [sds-realization.md](references/sds-realization.md)

### Step 8: 渲染、匹配与微调

用渲染脚本渲染 SVG/PNG（**默认远端渲染**——脚本默认 `PLANTUML_BACKEND=server`；禁止自行下载/配置本地渲染工具；远端不可用时脚本会提示，必须先询问用户是否接受本地渲染，获确认后以 `PLANTUML_BACKEND=local` 重试）；读取生成图片与用户要求比对，发现差异微调代码重渲；**强弱自检：大区边框须明显粗且深于子模块边框、子模块边框粗且深于流线（SVG 中 `stroke-width` 至少三档可辨），全图单一线宽即判不合格**；图集则逐图检查自足性、交叉引用与跨图一致（配色/字号/编号/页脚）；最终组装为 HTML 文档输出。

→ [12-rendering-and-output.md](references/howto/12-rendering-and-output.md)

## 专项图表（非 UML）

除 8 种标准 UML 图表外，本技能还支持 7 种专项图表。其中 WBS/甘特图/思维导图/JSON/YAML/Salt 六种不遵循 UML 语义，各自有独立语法与原生配色；ER 图用 `@startuml` + `entity` 乌鸦脚语法，遵循 UML 样式规范。当用户意图属于以下场景时，在 Step 2 直接选用对应专项图表，并阅读其操作指南：

| 专项图表 | 适用场景 | 起止标记 | 操作指南 |
|---------|---------|---------|---------|
| **WBS 工作分解结构** | 项目/交付物层级分解 | `@startwbs`/`@endwbs` | [13-wbs-diagram.md](references/howto/13-wbs-diagram.md) |
| **甘特图 Gantt** | 项目进度、任务依赖、里程碑 | `@startgantt`/`@endgantt` | [14-gantt-diagram.md](references/howto/14-gantt-diagram.md) |
| **思维导图 MindMap** | 知识梳理、发散规划 | `@startmindmap`/`@endmindmap` | [15-mindmap-diagram.md](references/howto/15-mindmap-diagram.md) |
| **JSON 数据可视化** | 展示 JSON 数据结构 | `@startjson`/`@endjson` | [16-json-diagram.md](references/howto/16-json-diagram.md) |
| **YAML 显示效果图** | 展示 YAML 配置结构 | `@startyaml`/`@endyaml` | [17-yaml-diagram.md](references/howto/17-yaml-diagram.md) |
| **ER 实体关系图** | 数据库表结构、数据建模、表间基数 | `@startuml`（`entity` 语法） | [18-er-diagram.md](references/howto/18-er-diagram.md) |
| **Salt UI 线框图** | 界面原型、表单/窗口线框 | `@startsalt`/`@endsalt` | [19-salt-diagram.md](references/howto/19-salt-diagram.md) |

> 专项图表的渲染同样走 Step 8 的渲染脚本；除 ER 图外均无需 Graphviz（`dot`）即可渲染（ER 走 Graphviz 布局，**仅限用户确认后的本地渲染**才需要本机 `dot`）。样式与美观要点见各操作指南的「布局与美观技巧」小节。
>
> **WBS / 甘特图交付前必做量测自检**：这两类图的"清晰度、版面、日期定位"都不能靠肉眼判断，用 [measure-svg-layout.py](scripts/measure-svg-layout.py) 量三条判据——**正文有效字号 ≥12px**（`= font-size × 显示宽度 ÷ viewBox 宽`；放大 zoom 无效）、**长宽比 1.2~1.8:1**、**标签不越过时间轴右边界**（不能用 `viewBox 宽 − 最右元素 x`，该值结构性 ≈0）；判断某个写法（依赖箭头、资源分配、标题字号）有没有改写排期，用 `--compare` 做 A/B 并看 `scheduleChanged`。详见 [13-wbs-diagram.md](references/howto/13-wbs-diagram.md)、[14-gantt-diagram.md](references/howto/14-gantt-diagram.md)。

## 输出要求

- **交付契约（必读；规则 owner 在前门）**：[../draw-diagram/references/delivery-contract.md](../draw-diagram/references/delivery-contract.md) —— D1/D2 交付形态、D3–D5 面向用户的文字规则（**图内标签与 HTML 正文同规**）、D6 交付前自检。**条文与示例只存在于契约，本节不复写。**以下各条是本引擎的**机械落地**，与契约冲突时以契约为准。
- 输出为单个 HTML 文档，包含渲染的图表（渲染图为主体；原始 PlantUML 文本不嵌入正文，仅放入可折叠的「复现性附录」`<details>` 块，默认收起）
- 图表通过 [render-plantuml.sh](scripts/render-plantuml.sh) 渲染，同时产出 PNG 与 SVG（**默认远端渲染**：脚本默认 `PLANTUML_BACKEND=server`；本地渲染必须先在用户确认后以 `PLANTUML_BACKEND=local` 显式启用）
- **HTML 附复现性附录**：本图渲染命令（render-plantuml.sh 调用 + CJK 补跑脚本，一律 `${SKILL_HOME}` 相对路径、禁止写死绝对路径）、依赖说明（后端/CJK/本地工具链，含离线 fallback）与可折叠的 puml 源码——**附录源码必须与磁盘实际渲染的 `.puml` 逐字节一致**（含渲染脚本注入的样式块，直接从磁盘复制），保证"这张图怎么重新生成"可复现（详见 [12-rendering-and-output.md §4.4](references/howto/12-rendering-and-output.md)）
- **默认优先选用 PNG 格式**引用/嵌入图片（最美观，且在 Preview / Markdown 预览中可直接查看）；仅当图表过宽/过大触及 PNG 4096px 上限或需任意无损缩放时改用 SVG
- **嵌入 Markdown 文档时（最佳实践）**：默认看 PNG、细节不够可开 SVG 无损放大，**SVG/PNG 必须同时产出**。⚠️ Markdown 图片 `![]()` 与内联 HTML `<a>` 走**不同的路径解析管线**（有的渲染器会代理/改写 Markdown 图片 URL 却透传 HTML `href`），混用会导致两条路径不一致——故 **PNG 与 SVG 引用须用同一机制**：首选**全内联 HTML**（`<a href=x.svg target=_blank rel=noopener><img src=x.png></a>`，点图即开 SVG 新标签），渲染器会剥 HTML 时回退**全纯 Markdown**（同标签打开）。→ 见 [12-rendering-and-output.md §4.3](references/howto/12-rendering-and-output.md)
- PNG/SVG 与 HTML 保存在同一目录，HTML 通过相对路径引用图片
- PlantUML 源文件（`.puml`）保存以供未来编辑
- 每张图至少包含标题、渲染图片和简要说明

## 参考文档

所有参考文档（操作指南、最佳实践、官方文档）的完整索引和说明，参见 [references/index.md](references/index.md)。

**实战沉淀（务必阅读）**：竞技评审与重绘中固化的经验教训，见 [best-practices/best-practices.md](best-practices/best-practices.md)（最佳实践）与 [best-practices/pitfalls.md](best-practices/pitfalls.md)（陷阱）——绘制前对照最佳实践，绘制后自查陷阱清单。

## Evaluation Form(绘制评价单)

**定位与边界。** 本节是交付 PlantUML 产物后的 Evaluation Form(绘制评价单)，承载用户对本次已交付图表结果的评价；它不是 `## Feedback`，也不替代或改变该节的 agent 自省。`## Feedback` 保持其既有的「不向用户征询」规则，本节只处理用户主动给出的绘制评价。

**触发与一次性征询。** 仅在本技能已交付 PlantUML 产物及必要使用说明后，随该次交付附上一句非阻塞征询：`已交付 PlantUML 图；如愿意，请评价它是否准确、清晰且适合用途，或说明希望调整之处。` 不得等待回复、重复询问或因沉默降低交付结果。

**无评价。** 用户没有给出评价即视为本次绘制满意；不创建评价条目、不调用反馈引擎，也不在后续回合追问。

**有评价。** 用户一旦主动给出评价，保留其原意，将 review 内容标为 `## Evaluation Form`，并从评价中提取至少一条评价要点；随后以本节的 probe 记录（不是以 `wrap-up` probe 记录）：

```bash
python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
  --unit-id "skill:draw-plantuml" --unit-type skill \
  --lifecycle-point evaluation-form \
  --run-id "<drawing-run-id>:evaluation-form" --feature "<feature-key-if-any>" \
  --review-file "<evaluation-form-review-file>" \
  --points-file "<evaluation-form-points-file>"
```

这会经 `skill-draw-plantuml-evaluation-form` probe 把评价条目写入 `.specify/memory/feedback/`。不得把本节记录与同次运行的 `## Feedback` 自省共用 `run_id`，也不得把用户评价改写为 agent 自评。

**处置、回用与传递边界。** 该条目进入既有的 `record→threshold→package→manual→mark-submitted` 链路，并由既有 feedback 处置流程持续标记为 `processed` 或 `ignored`；`processed` 时在 `disposition_reason` 中保留可执行结论。后续执行本技能前，查询本技能已处置的评价单并将适用结论用于 PlantUML 图表实现与交付验收：

```bash
python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action list \
  --unit-id "skill:draw-plantuml" --disposition processed --contains "Evaluation Form"
```

本节绝不自动发送任何内容。若记录结果的既有 threshold 机制要求提示，只能按既有协议给出一次非阻塞的手动打包/提交提示；本节自身的评价征询始终只有交付时的一次。

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:draw-plantuml" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
