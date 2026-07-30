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
- **专项图表遵循其原生语义**：WBS/甘特图/思维导图/JSON/YAML/Salt 六类非 UML 图表使用各自的原生语法（`@startwbs`/`@startgantt`/`@startmindmap`/`@startjson`/`@startyaml`/`@startsalt`）与原生配色，不套用 UML 的 skinparam 单色规则；ER 图虽被官方归为非 UML，但用 `@startuml` + `entity` 语法、走 Graphviz 布局，按 UML 图同套 skinparam 规范处理

### 方法论总纲（贯穿全流程，先「对」与「达意」再「好看」）

下述四支柱是本技能所有优化手段的固化总纲，**单一事实来源为 [guide/diagram-principles.md](references/guide/diagram-principles.md)**（图表类型无关，适用于任意图；大图专项另见 [guide/large-diagram-playbook.md](references/guide/large-diagram-playbook.md)）。工作流各步都服从它：

1. **上下文驱动**：UML 脱离程序上下文无意义——先吃透文档/代码/描述、产出带出处的上下文摘要，保证程序整体正确、不臆造（principles §4.1）。
2. **减法与拆分**：信息量大时优先整洁美观而非面面俱到，每图突出**一个核心点**；单图表达不下则按架构接缝**拆为图集**（概览图 + 下钻子图，图间层次与交叉引用，每图自足，图集共享稳定词汇）（principles §4.2/§4.3）。
3. **UML 语义 + 视觉语义**：先选对图类型/元素种类/关系/构造型/接口（§1）；再按人类视角规划视觉语义——角色即位置、一对多用「单代表+多重性」、关联即同色、分组即框选（§2）。
4. **文字修饰 + 收尾美化**：元素上只留简洁标题、详解外置到布局安全的 note、字号层级跨图统一（§3）；最后做对齐/着色/线条与大图专项美化（playbook）。

## 工作流

按以下 8 个步骤顺序执行；每步都服从上面的「方法论总纲」四支柱。每步核心说明如下，详细操作阅读对应参考文档。

### Step 1: 语义解析 + 吃透上下文（上下文驱动）

分析用户输入以理解绘制意图；通过补充推断或交互式提问（`AskUserQuestion`，最多一轮 ≤4 个问题）确认意图。**面对文档/代码等丰富上下文时，先产出一份带出处的上下文摘要**（组件、关系、核心流程、关键决策），后续绘图与自检都对着它，保证程序整体正确、不臆造。

→ [00-semantic-analysis.md](references/howto/00-semantic-analysis.md)；上下文驱动见 [diagram-principles.md §4.1](references/guide/diagram-principles.md)

### Step 2: 选图类型 + 定「单图 or 图集」（减法与拆分）

从 8 种标准 UML 图表类型中选最合适的一或多种，每图聚焦**单一视角/一个核心点**。**信息量大或多面时做减法与拆分**：优先整洁美观而非面面俱到；单图表达不下则按架构接缝（分层/控制面数据面/静态行为/请求制品流/系统节点边界）**拆为图集**——一张概览/索引图在顶 + 下钻子图，图间体现层次与交叉引用（`▶ 见 图N`），每图自足，图集共享稳定词汇（编号/颜色/构造型跨图同义）。

→ [01-choose-diagram-type.md](references/howto/01-choose-diagram-type.md)；减法与拆分见 [diagram-principles.md §4.2/§4.3](references/guide/diagram-principles.md)

### Step 3: 选元素 + 关系（UML 语义正确）

选正确的 UML 元素种类（组件/节点/制品/数据库/接口/类/状态…）与关系类型（依赖/关联/实现/通信路径/控制信号/«deploy»«manifest»…）、构造型与多重性；为对外契约补 `interface` 与端口。**元素种类本身即语义，勿一律用 rectangle/component。**

→ [references/howto/](references/howto/)（02–09）；UML 语义先行见 [diagram-principles.md §1](references/guide/diagram-principles.md)

### Step 4: 规划布局 + 视觉语义（人类视角）

编码前先规划空间语义：
- **视觉语义**：角色即位置（枢纽居中偏上、节点沿边/底，Hub/Edge/Entry/Sink）；一对多用**单代表元素 + 多重性标注**（`collections`/堆叠阴影/«×N»），不画 N 份兄弟盒；关联即同色（同子系统同色相族）；分组即框选（宏观逻辑分区用可见具名 frame、同类细分组用不可见 frame）。
- **方向/宽高比决策**：数「最宽层宽 B」与「主流深 D」选方向（宽浅 `top to bottom`、深窄长链 `left to right`）；`C≈round(sqrt(N×1.3))` 估列数摆近正方形网格（嵌套图每个 frame 内同理）；单层兄弟 ≤6，超出下沉/拆 frame。

→ [10-layout-planning.md](references/howto/10-layout-planning.md)、[layout.md §一/§2.1/§2.5](references/guide/layout.md)；视觉语义见 [diagram-principles.md §2](references/guide/diagram-principles.md)

### Step 5: 生成 PlantUML 代码

按所选图类型操作指南与语法编写代码：`@startuml`/`@enduml` 包裹，先声明元素再声明关系，用方向关键字与分组（`together`/隐藏边）控制布局。

→ [11-code-generation.md](references/howto/11-code-generation.md)、[syntax-reference.md](references/guide/syntax-reference.md)

### Step 6: 文字修饰（独立一步）

单独治理图元文字：**元素上只留很简洁的标题**（先去重——已被 interface/stereotype/嵌套表达的删掉）；**详细清晰的说明外置到 `note`**（用完整语言，非碎片；布局安全否则省——深层嵌套成员的 note 常被引擎甩到页边，改折叠进父级 note 或 legend）；**字号层级用 per-kind skinparam 统一设定**（标题>容器>组件>note>legend>箭头>stereotype），图内与跨图集一致，**禁用零散内联 `<size:>`/`**bold**`**（字号/粗细不一的头号成因）。

→ [diagram-principles.md §3](references/guide/diagram-principles.md)、[content.md](references/guide/content.md)

### Step 7: 应用样式 + 大图专项（对齐·着色·线条）

应用统一 skinparam/色彩模式，确保视觉一致。**大图（节点多/尺寸大）套用大图技术栈**：×N 语义折叠、弱化管线突出语义色、正交路由 + 隐藏边控宽高比消交叉、连线治理、隐藏脚手架的能与不能、legend 作单一细节仓；只用 SVG 交付大图。

→ [style.md](references/guide/style.md)、[large-diagram-playbook.md](references/guide/large-diagram-playbook.md)

### Step 8: 渲染、匹配与微调

用渲染脚本渲染 SVG/PNG；读取生成图片与用户要求比对，发现差异微调代码重渲；图集则逐图检查自足性、交叉引用与跨图一致（配色/字号/编号/页脚）；最终组装为 HTML 文档输出。

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

> 专项图表的渲染同样走 Step 8 的渲染脚本；除 ER 图外均无需 Graphviz（`dot`）即可渲染（ER 走 Graphviz 布局，本地 jar 渲染时须有 `dot`）。样式与美观要点见各操作指南的「布局与美观技巧」小节。

## 输出要求

- 输出为单个 HTML 文档，包含渲染的图表（不嵌入原始 PlantUML 文本）
- 图表通过 [render-plantuml.sh](scripts/render-plantuml.sh) 渲染，同时产出 PNG 与 SVG
- **默认优先选用 PNG 格式**引用/嵌入图片（最美观，且在 Preview / Markdown 预览中可直接查看）；仅当图表过宽/过大触及 PNG 4096px 上限或需任意无损缩放时改用 SVG
- **嵌入 Markdown 文档时（最佳实践）**：默认看 PNG、细节不够可开 SVG 无损放大，**SVG/PNG 必须同时产出**。⚠️ Markdown 图片 `![]()` 与内联 HTML `<a>` 走**不同的路径解析管线**（有的渲染器会代理/改写 Markdown 图片 URL 却透传 HTML `href`），混用会导致两条路径不一致——故 **PNG 与 SVG 引用须用同一机制**：首选**全内联 HTML**（`<a href=x.svg target=_blank rel=noopener><img src=x.png></a>`，点图即开 SVG 新标签），渲染器会剥 HTML 时回退**全纯 Markdown**（同标签打开）。→ 见 [12-rendering-and-output.md §4.3](references/howto/12-rendering-and-output.md)
- PNG/SVG 与 HTML 保存在同一目录，HTML 通过相对路径引用图片
- PlantUML 源文件（`.puml`）保存以供未来编辑
- 每张图至少包含标题、渲染图片和简要说明

## 参考文档

所有参考文档（操作指南、最佳实践、官方文档）的完整索引和说明，参见 [references/index.md](references/index.md)。

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At the end of a substantial run of this skill, perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this run reached a meaningful wrap-up. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against this skill's declared purpose and produce a short review plus ≥1 concrete, skill-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this skill's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id`; if a parent flow already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "skill:draw-plantuml" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
