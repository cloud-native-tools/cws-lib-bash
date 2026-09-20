---
name: draw-mermaid
description: |
  Draw system architecture diagrams with Mermaid, render to SVG/PNG via the mermaid.ink render server or local mermaid-cli, and output as HTML with rendered images.
  Use standard UML semantics (Sequence, Class, State, ER, Flowchart-based Component/Deployment/Package) to describe system architecture — a Mermaid counterpart for every PlantUML diagram type that has a native match.
  Also supports native specialty diagrams: Gantt (甘特图), MindMap (思维导图, also covers PlantUML WBS 工作分解结构), ER 实体关系图 (erDiagram, crow's foot), C4 架构图 (C4Context/C4Container/C4Component/C4Dynamic/C4Deployment), plus flowchart-based approximations for Use Case / JSON / YAML / Salt 线框图.
  Use when the user mentions "mermaid", "Mermaid图", "mermaid diagram", "架构图", "architecture diagram", "UML图", "系统架构图", "画架构", "设计图", "组件图", "部署图", "时序图", "类图", "包图", "系统设计",
  "流程图", "状态图", "活动图", "用例图", "状态机图", "模块图", "交互图",
  "sequence diagram", "class diagram", "component diagram", "deployment diagram",
  "activity diagram", "state diagram", "use case diagram", "package diagram",
  "工作分解结构", "WBS", "甘特图", "gantt", "项目计划图", "进度图", "思维导图", "mindmap", "脑图",
  "ER图", "实体关系图", "数据库设计", "数据建模", "表结构", "ERD", "entity relationship", "crow's foot",
  "C4", "C4图", "C4模型", "context diagram", "container diagram",
  "UI原型", "线框图", "wireframe", "界面原型", "界面草图",
  "复刻图", "图片重绘", "图片转图", "replicate diagram", "redraw", "image to diagram"
skill_id: "<SKILL:.specify/skills/draw-mermaid/SKILL.md>"
---

# 架构图绘制技能（Mermaid）

使用 Mermaid 语法和标准 UML 语义绘制系统架构图，通过 mermaid.ink 渲染服务器或本地 mermaid-cli 渲染为 SVG/PNG，并输出为包含渲染图表和说明文字的完整 HTML 文档。

## 核心原则

- **引擎独有能力（路由选中本引擎的理由）**：仓库原生声明式文本图——`.mmd` 文本即产物、diff 友好、可版本管理，GitHub/GitLab/CI 等平台原生免工具链直渲；代价是布局自动（dagre），受 SDS 委派时几何只能逼近并声明偏离（见「SDS 实现与强弱落地」）
- **UML 语义，而非随意方框**：UML 类图表必须遵循标准 UML 图表类型，使用正确的 UML 元素和关系（Mermaid 的 classDiagram / sequenceDiagram / stateDiagram-v2 / erDiagram / flowchart 各司其职）
- **架构优先的叙事**：图和文字互补——文字解释*为什么*，图展示*什么*
- **统一样式**：用 `%%{init: {themeVariables}}%%` / `classDef` 保持统一样式，UML 图每张核心元素 ≤7 个（硬上限 ≤15）
- **远端渲染优先**：默认只使用 mermaid.ink 渲染服务器（`render-mermaid.sh` 默认 `MERMAID_BACKEND=server`），**不下载、不配置本地渲染工具链**（mermaid-cli / Chrome / puppeteer）；远端不可用时，必须先询问用户是否改用本地渲染（`MERMAID_BACKEND=local`），**未获用户确认不得本地渲染**
- **专项图表遵循其原生语义**：Gantt / MindMap（含 WBS）/ ER / C4 使用各自原生语法与原生配色，不套用 flowchart 的通用样式规则；Use Case / JSON / YAML / Salt 在 Mermaid 无原生图表类型，用 flowchart 语义化近似并明示近似关系

### 方法论总纲（贯穿全流程，先「对」与「达意」再「好看」）

下述四支柱是本技能所有优化手段的固化总纲，**单一事实来源为 [guide/diagram-principles.md](references/guide/diagram-principles.md)**（图表类型无关，适用于任意图；大图专项另见 [guide/large-diagram-playbook.md](references/guide/large-diagram-playbook.md)）。工作流各步都服从它：

1. **上下文驱动**：UML 脱离程序上下文无意义——先吃透文档/代码/描述、产出带出处的上下文摘要，保证程序整体正确、不臆造（principles §4.1）。
2. **减法与拆分**：信息量大时优先整洁美观而非面面俱到，每图突出**一个核心点**；单图表达不下则按架构接缝**拆为图集**（概览图 + 下钻子图，图间层次与交叉引用，每图自足，图集共享稳定词汇）（principles §4.2/§4.3）。
3. **UML 语义 + 视觉语义**：先选对图类型/元素种类/关系/构造型/接口（§1）；再按人类视角规划视觉语义——角色即位置、一对多用「单代表+多重性」、关联即同色、分组即框选（§2）。
4. **文字修饰 + 收尾美化**：元素上只留简洁标题、详细说明外置到布局安全的注释（flowchart 的 `:::注释节点`/link 注释、sequence 的 note、class 的 note）、字号层级跨图统一（§3）；最后做对齐/着色/线条与大图专项美化（playbook）。

## SDS 实现与强弱落地

**输入契约**：受 [draw-diagram](../draw-diagram/SKILL.md) 委派时，输入是 **SDS 文件路径**（Semantic Drawing Spec：逻辑模型 + Geometry（canvas / 每图元 box{x,y,w,h} / 分区盒 / 关系锚点）+ weight_plan 档位 + typography 层级）。SDS schema 与 Deviation Declaration 规则的 owner 是 [../draw-diagram/references/semantic-model.md](../draw-diagram/references/semantic-model.md)。**MUST NOT 改写语义**：元素/关系/分区集合、布局语义、weight_plan 档位一律以 SDS 为冻结输入——本技能只负责引擎语法、SDS 实现/逼近、渲染质量。无 SDS（用户直调）时按下方工作流自行补齐同等模型。

### 强弱实现（tier → stroke-width）

SDS 的相对档位（T1>T2>T3>T4）由本层经 `linkStyle` / `classDef` / `style` 落实为绝对线宽；**复刻类 SDS（fidelity_intent=reproduction）携带的源图实测线宽优先，覆盖下表默认值**：

| 档位 | SDS 语义角色 | Mermaid 载体与语法 | 默认线宽 |
|------|-------------|------------------|---------|
| T1 | 大模块/顶层分区边界 | 顶层 subgraph（cluster）边框：`style <zoneId> stroke-width:3px`（配深色 stroke） | 3px |
| T2 | 小模块/组件边界 | 嵌套 subgraph 与组件节点边框：`classDef module stroke-width:2px` | 2px |
| T3 | 数据流/依赖连线 | 流线：`linkStyle <idx|default> stroke-width:1.5px` | 1.5px |
| T4 | 注释/副标题 | 注释节点与弱虚线：`classDef note stroke-width:1px`（配 `-.->`） | 1px |

关键路径（weight_plan.key_paths）仅以色相抬升、线宽封顶 = T2；全图单一线宽判不合格（验收判据 owner：semantic-model.md）。

### 几何逼近与偏离声明

Mermaid 为**自动布局引擎**（dagre，无绝对坐标 API）→ SDS Geometry 只能**逼近**：ghost spacer 锚点（等高/顶对齐分区）、`~~~` 行锁链（行序/rank 控制）、invisible links（列对齐）。无法兑现项（精确 x/y、等高分区、锚点位置等）MUST 在**结果清单中量化声明**（偏离维度 + 幅度 + 原因）——未声明的偏离按 semantic-fidelity 扣分，已声明的计入语法实现质量、不算语义缺陷。

→ 逼近技术细节（含 wrappingWidth 陷阱、curve:linear、版本 pin、本地 bundle 渲染回退）、档位映射依据与偏离声明模板：[references/sds-realization.md](references/sds-realization.md)

## PlantUML ↔ Mermaid 图表类型对照

本技能以**复刻 PlantUML 图表能力**为目标：PlantUML 有的图表类型，Mermaid 有的类型直接对应（✓），语义可映射的用 Mermaid 最接近的原生类型承接（≈），Mermaid 无任何匹配类型的才标记「不匹配」（✗）并在正文说明替代建议。

| PlantUML 类型 | Mermaid 对应 | 匹配度 | 说明 |
|---------------|-------------|--------|------|
| Class 类图（`@startuml`） | `classDiagram` | ✓ | 类、属性、方法、6 种关系（`<|--` `*--` `o--` `-->` `..>` `..|>`）、多重性 |
| Sequence 时序图 | `sequenceDiagram` | ✓ | participant/actor、消息箭头、activate、note、alt/loop/par/opt 片段、autonumber |
| Activity 活动图 | `flowchart` | ✓ | 活动节点 + 菱形决策 + fork/join（subgraph 泳道）；状态驱动流程用 `stateDiagram-v2` 亦可 |
| State 状态机图 | `stateDiagram-v2` | ✓ | `[*]` 初终态、转换/守卫/动作、复合状态、fork/join、并发 `--` |
| Gantt 甘特图（`@startgantt`） | `gantt` | ✓ | section、任务/里程碑、依赖、完成度、todayMarker、axisFormat |
| MindMap 思维导图（`@startmindmap`） | `mindmap` | ✓ | 根/分支/节点形状（square/cloud/bang）、无框节点 |
| WBS 工作分解结构（`@startwbs`） | `mindmap`（树形） | ≈ | WBS 即树 → mindmap 承接；需要左右展开+算术记法的，用 `flowchart LR` 近似 |
| ER 实体关系图（entity） | `erDiagram` | ✓ | 实体、属性、PK/FK、乌鸦脚基数（`||--o{` 等） |
| C4（`C4_Context` 等宏） | `C4Context` / `C4Container` / `C4Component` / `C4Dynamic` / `C4Deployment` | ✓ | Mermaid v10.9+ 原生 C4 系列 |
| Use Case 用例图 | `flowchart`（语义近似） | ≈ | Mermaid 无原生用例图；用「角色节点 + 用例椭圆 + 系统边界 subgraph」近似 |
| Component 组件图 | `flowchart`（subgraph 边界）或 `C4Component` | ≈ | 无原生组件图；分层组件用 flowchart subgraph，组件级 C4 用 C4Component |
| Deployment 部署图 | `flowchart`（subgraph 节点）或 `C4Deployment` | ≈ | 无原生部署图；节点/容器用 subgraph 分层近似 |
| Package 包图 | `flowchart`（subgraph）或 `classDiagram`（namespace） | ≈ | 包间依赖用 flowchart；类在包内的组织用 classDiagram namespace |
| Object 对象图 | `classDiagram`（实例标注） | ≈ | 无原生对象图；类图实例 + 关系近似 |
| JSON 数据可视化（`@startjson`） | `flowchart`（结构树近似） | ≈ | Mermaid 无原生 JSON 图；对象树用 flowchart 层级 + 类型标注近似 |
| YAML 显示效果图（`@startyaml`） | `flowchart`（结构树近似） | ≈ | 同上 |
| Salt UI 线框图（`@startsalt`） | `flowchart`（界面结构近似） | ≈ | 无原生线框图；控件/区块布局用 flowchart 近似 |
| Network 网络图（nwdiag） | `flowchart`（子网 subgraph 近似） | ≈ | 无原生网络图 |
| Timing 时序波形图（`@startuml timing`） | `xychart-beta`（时间线近似）或 `timeline`（仅历史时间线语义） | ✗ | Mermaid 无等价时序波形类型；`timeline` 是时间线叙事图，语义不同 |
| Composite Structure / Profile / Archimate / Ditaa / EBNF / Regex | — | ✗ | Mermaid 无匹配类型；如需请说明用 flowchart 手动建模或改用其他工具 |

> **Mermaid 独有而 PlantUML 无的类型**（按需选用）：`pie`、`quadrantChart`、`requirementDiagram`、`gitGraph`、`journey`、`timeline`、`sankey-beta`、`xychart-beta`、`packet-beta`、`kanban`。详见 [howto/01-choose-diagram-type.md](references/howto/01-choose-diagram-type.md)。

## 工作流

按以下 8 个步骤顺序执行；每步都服从上面的「方法论总纲」四支柱。每步核心说明如下，详细操作阅读对应参考文档。

### Step 1: 语义解析 + 吃透上下文（上下文驱动）

**受 draw-diagram 委派时本步跳过**：SDS 即语义输入（逻辑模型/几何/强弱已在语义层定案），不得重新建模或就语义再问用户（仅语法/渲染事项可确认）。以下适用于无 SDS 的直调场景：

分析用户输入以理解绘制意图；通过补充推断或交互式提问（`AskUserQuestion`，最多一轮 ≤4 个问题）确认意图。**面对文档/代码等丰富上下文时，先产出一份带出处的上下文摘要**（组件、关系、核心流程、关键决策），后续绘图与自检都对着它，保证程序整体正确、不臆造。

→ [00-semantic-analysis.md](references/howto/00-semantic-analysis.md)；上下文驱动见 [diagram-principles.md §4.1](references/guide/diagram-principles.md)

### Step 2: 选图类型 + 定「单图 or 图集」（减法与拆分）

按上方 **PlantUML ↔ Mermaid 类型对照表** 从 Mermaid 支持的类型中选最合适的一或多种，每图聚焦**单一视角/一个核心点**。**信息量大或多面时做减法与拆分**：优先整洁美观而非面面俱到；单图表达不下则按架构接缝（分层/控制面数据面/静态行为/请求制品流/系统节点边界）**拆为图集**——一张概览/索引图在顶 + 下钻子图，图间体现层次与交叉引用（`▶ 见 图N`），每图自足，图集共享稳定词汇（编号/颜色/构造型跨图同义）。

→ [01-choose-diagram-type.md](references/howto/01-choose-diagram-type.md)；减法与拆分见 [diagram-principles.md §4.2/§4.3](references/guide/diagram-principles.md)

### Step 3: 选元素 + 关系（UML 语义正确）

选正确的 Mermaid 图类型与元素（classDiagram 的类/关系、sequenceDiagram 的参与者/消息、stateDiagram-v2 的状态/转换、erDiagram 的实体/基数、flowchart 的节点形状/边型），为对外契约补接口与端口语义。**元素种类本身即语义，勿一律用 flowchart 矩形。**

→ [references/howto/](references/howto/)（02–09）；UML 语义先行见 [diagram-principles.md §1](references/guide/diagram-principles.md)

### Step 4: 几何落地（SDS 优先，规划仅作回退）

- **有 SDS（受委派）**：几何是语义层已定案的决策（谁和谁同区、谁居中、分区等高、方向/宽高比、锚点）——**不得重新规划**，按「SDS 实现与强弱落地」小节以脚手架逼近（ghost spacer 锚点、`~~~` 行锁链、invisible links），并对无法兑现项做量化偏离声明。
- **无 SDS（直调回退）**：编码前先补空间语义——角色即位置（枢纽居中偏上、节点沿边/底）；一对多用**单代表元素 + 多重性标注**（`collections`/`«×N»`）；关联即同色；分组即框选（`subgraph` 具名边界）。方向/宽高比：数「最宽层宽 B」与「主流深 D」选 `TD`/`LR`，`C≈round(sqrt(N×1.3))` 估列数，单层兄弟 ≤6。

→ [sds-realization.md](references/sds-realization.md)；回退规划见 [10-layout-planning.md](references/howto/10-layout-planning.md)、[layout.md §一/§2.1/§2.5](references/guide/layout.md)、[diagram-principles.md §2](references/guide/diagram-principles.md)

### Step 5: 生成 Mermaid 代码

按所选图类型操作指南与语法编写代码：首行写图类型声明（`classDiagram` / `sequenceDiagram` / `stateDiagram-v2` / `erDiagram` / `gantt` / `mindmap` / `flowchart TD` 等），样式指令 `%%{init: {...}}%%` 置于首行之前，先声明元素再声明关系，用方向关键字与 `subgraph` 控制布局。源文件保存为 `.mmd`。

→ [11-code-generation.md](references/howto/11-code-generation.md)、[syntax-reference.md](references/guide/syntax-reference.md)

### Step 6: 文字修饰（独立一步）

单独治理图元文字：**元素上只留很简洁的标题**（先去重——已被类型/嵌套表达的删掉）；**详细清晰的说明外置到布局安全的注释**（flowchart 用 `A -->|说明| B` 边标签或 `:::note` 节点、sequence 用 `note right/left of`、class 用 `note for`）；**字号层级用 `%%{init: {themeVariables: {fontSize, ...}}}%%` 统一设定**（标题>容器>组件>note>legend>箭头>stereotype），图内与跨图集一致，**禁用零散内联字号与加粗**（字号/粗细不一的头号成因）。

→ [diagram-principles.md §3](references/guide/diagram-principles.md)、[content.md](references/guide/content.md)

### Step 7: 应用样式 + 大图专项（对齐·着色·线条）

用 `%%{init: {themeVariables}}%%` / `classDef` / `style` 应用统一主题与色彩模式，确保视觉一致。**大图（节点多/尺寸大）套用大图技术栈**：×N 语义折叠、弱化管线突出语义色、subgraph 分层控宽高比消交叉、连线治理、legend 作单一细节仓；只用 SVG 交付大图。

→ [style.md](references/guide/style.md)、[large-diagram-playbook.md](references/guide/large-diagram-playbook.md)

### Step 8: 渲染、匹配与微调

用渲染脚本渲染 SVG/PNG（**默认远端渲染**——脚本默认 `MERMAID_BACKEND=server`；禁止自行下载/配置本地渲染工具；远端不可用时脚本会提示，必须先询问用户是否接受本地渲染，获确认后以 `MERMAID_BACKEND=local` 重试）；读取生成图片与用户要求比对，发现差异微调代码重渲；图集则逐图检查自足性、交叉引用与跨图一致（配色/字号/编号/页脚）；最终组装为 HTML 文档输出。

→ [12-rendering-and-output.md](references/howto/12-rendering-and-output.md)

## 专项图表（非 UML）

除 8 类 UML 图（含近似）外，本技能还支持 6 种专项图表。Gantt/MindMap/ER/C4 有原生语法与原生配色；Use Case/JSON/YAML/Salt 为 flowchart 语义近似（在下方表格中标注「近似」）。当用户意图属于以下场景时，在 Step 2 直接选用对应专项图表，并阅读其操作指南：

| 专项图表 | 适用场景 | Mermaid 类型 | 操作指南 |
|---------|---------|-------------|---------|
| **甘特图 Gantt** | 项目进度、任务依赖、里程碑 | `gantt` | [14-gantt-diagram.md](references/howto/14-gantt-diagram.md) |
| **思维导图 MindMap** | 知识梳理、发散规划 | `mindmap` | [15-mindmap-diagram.md](references/howto/15-mindmap-diagram.md) |
| **WBS 工作分解结构** | 项目/交付物层级分解 | `mindmap`（树形，≈） | [13-wbs-diagram.md](references/howto/13-wbs-diagram.md) |
| **ER 实体关系图** | 数据库表结构、数据建模、表间基数 | `erDiagram` | [18-er-diagram.md](references/howto/18-er-diagram.md) |
| **C4 架构图** | 上下文/容器/组件/动态/部署视图 | `C4Context` 等五类 | [20-c4-diagram.md](references/howto/20-c4-diagram.md) |
| **Use Case / JSON / YAML / Salt** | 用例视图、数据结构展示、UI 线框 | `flowchart`（近似） | [07-usecase-diagram.md](references/howto/07-usecase-diagram.md) / [16-json-diagram.md](references/howto/16-json-diagram.md) / [17-yaml-diagram.md](references/howto/17-yaml-diagram.md) / [19-salt-diagram.md](references/howto/19-salt-diagram.md) |

> 专项图表的渲染同样走 Step 8 的渲染脚本（`render-mermaid.sh`），服务器后端（mermaid.ink）与本地后端（mermaid-cli）对全部类型一视同仁，无需 Graphviz。
>
> **WBS / 甘特图交付前必做量测自检**：这两类图的"清晰度、版面、日期定位"都不能靠肉眼判断，用 [measure-svg-layout.py](scripts/measure-svg-layout.py) 量三条判据——**正文有效字号 ≥12px**（`= font-size × 显示宽度 ÷ viewBox 宽`；放大 zoom 无效）、**长宽比 1.2~1.8:1**、**标签不越过时间轴右边界**；判断某个写法（依赖箭头、资源分配、标题字号）有没有改写排期，用 `--compare` 做 A/B 并看 `scheduleChanged`。详见 [13-wbs-diagram.md](references/howto/13-wbs-diagram.md)、[14-gantt-diagram.md](references/howto/14-gantt-diagram.md)。

## 输出要求

- **交付契约（必读；规则 owner 在前门）**：[../draw-diagram/references/delivery-contract.md](../draw-diagram/references/delivery-contract.md) —— D1/D2 交付形态、D3–D5 面向用户的文字规则（**图内标签与 HTML 正文同规**）、D6 交付前自检。**条文与示例只存在于契约，本节不复写。**以下各条是本引擎的**机械落地**，与契约冲突时以契约为准。
- 输出为单个 HTML 文档，包含渲染的图表；**每图附「可复现信息」折叠块**（内嵌 `.mmd` 源码 + 渲染命令，`<details>` 块，见 [12-rendering-and-output.md §4.4](references/howto/12-rendering-and-output.md)），不依赖外部渲染服务在线即可复现
- 图表通过 [render-mermaid.sh](scripts/render-mermaid.sh) 渲染，同时产出 PNG 与 SVG（**默认远端渲染**：脚本默认 `MERMAID_BACKEND=server`；本地渲染必须先在用户确认后以 `MERMAID_BACKEND=local` 显式启用）
- **默认优先选用 PNG 格式**引用/嵌入图片（最美观，且在 Preview / Markdown 预览中可直接查看）；仅当图表过宽/过大或需任意无损缩放时改用 SVG
- **密集图（组件/部署/时序）交付前量有效字号**：`measure-svg-layout.py <x.svg> --display-width <目标显示宽>`，正文 <12px 时上调 `fontSize`（时序图用 sequence 的 `actorFontSize`/`messageFontSize`/`noteFontSize`）重渲，或 HTML 改引 SVG 宽幅显示——**放大 zoom 无效**（画布同比放大）
- **嵌入 Markdown 文档时（最佳实践）**：默认看 PNG、细节不够可开 SVG 无损放大，**SVG/PNG 必须同时产出**。⚠️ Markdown 图片 `![]()` 与内联 HTML `<a>` 走**不同的路径解析管线**（有的渲染器会代理/改写 Markdown 图片 URL 却透传 HTML `href`），混用会导致两条路径不一致——故 **PNG 与 SVG 引用须用同一机制**：首选**全内联 HTML**（`<a href=x.svg target=_blank rel=noopener><img src=x.png></a>`，点图即开 SVG 新标签），渲染器会剥 HTML 时回退**全纯 Markdown**（同标签打开）。→ 见 [12-rendering-and-output.md §4.3](references/howto/12-rendering-and-output.md)
- PNG/SVG 与 HTML 保存在同一目录，HTML 通过相对路径引用图片
- Mermaid 源文件（`.mmd`）保存以供未来编辑
- 每张图至少包含标题、渲染图片和简要说明

## 参考文档

所有参考文档（操作指南、最佳实践、官方文档）的完整索引和说明，参见 [references/index.md](references/index.md)。

**实战沉淀（务必阅读）**：竞技评审与重绘中固化的经验教训，见 [best-practices/best-practices.md](best-practices/best-practices.md)（最佳实践）与 [best-practices/pitfalls.md](best-practices/pitfalls.md)（陷阱）——绘制前对照最佳实践，绘制后自查陷阱清单。

## Evaluation Form(绘制评价单)

**定位与边界。** 本节是交付 Mermaid 产物后的 Evaluation Form(绘制评价单)，承载用户对本次已交付图表结果的评价；它不是 `## Feedback`，也不替代或改变该节的 agent 自省。`## Feedback` 保持其既有的「不向用户征询」规则，本节只处理用户主动给出的绘制评价。

**触发与一次性征询。** 仅在本技能已交付 Mermaid 产物及必要使用说明后，随该次交付附上一句非阻塞征询：`已交付 Mermaid 图；如愿意，请评价它是否准确、清晰且适合用途，或说明希望调整之处。` 不得等待回复、重复询问或因沉默降低交付结果。

**无评价。** 用户没有给出评价即视为本次绘制满意；不创建评价条目、不调用反馈引擎，也不在后续回合追问。

**有评价。** 用户一旦主动给出评价，保留其原意，将 review 内容标为 `## Evaluation Form`，并从评价中提取至少一条评价要点；随后以本节的 probe 记录（不是以 `wrap-up` probe 记录）：

```bash
python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
  --unit-id "skill:draw-mermaid" --unit-type skill \
  --lifecycle-point evaluation-form \
  --run-id "<drawing-run-id>:evaluation-form" --feature "<feature-key-if-any>" \
  --review-file "<evaluation-form-review-file>" \
  --points-file "<evaluation-form-points-file>"
```

这会经 `skill-draw-mermaid-evaluation-form` probe 把评价条目写入 `.specify/memory/feedback/`。不得把本节记录与同次运行的 `## Feedback` 自省共用 `run_id`，也不得把用户评价改写为 agent 自评。

**处置、回用与传递边界。** 该条目进入既有的 `record→threshold→package→manual→mark-submitted` 链路，并由既有 feedback 处置流程持续标记为 `processed` 或 `ignored`；`processed` 时在 `disposition_reason` 中保留可执行结论。后续执行本技能前，查询本技能已处置的评价单并将适用结论用于 Mermaid 图表实现与交付验收：

```bash
python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action list \
  --unit-id "skill:draw-mermaid" --disposition processed --contains "Evaluation Form"
```

本节绝不自动发送任何内容。若记录结果的既有 threshold 机制要求提示，只能按既有协议给出一次非阻塞的手动打包/提交提示；本节自身的评价征询始终只有交付时的一次。

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:draw-mermaid" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
