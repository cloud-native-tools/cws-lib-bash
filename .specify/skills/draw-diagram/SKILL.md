---
name: draw-diagram
description: |
  Unified front door and single home of every diagram engine: builds a semantic logical-diagram model (elements, relations, zones, layout/style/artifact/fidelity intent), then renders it through the best-fit engine layer carried inside this skill (d3js / drawio / echarts / excalidraw / mermaid / plantuml) via the routing matrix and exclusivity registry. Formerly six separate draw-* skills, merged with content preserved; the inheritance is re-verifiable via references/merge-provenance.md.
  统一绘图入口:先语义建模,再由本技能内置的引擎层渲染;六个引擎的语法、渲染与坑位归 references/types/<engine>/ 各自承载。
  Use when the user mentions "画图", "绘图", "画个图", "出图", "draw a diagram", "diagram", "图表",
  "架构图", "拓扑图", "流程图", "时序图", "状态图", "类图", "ER图", "甘特", "WBS", "思维导图", "线框图",
  "数据可视化", "复刻图", "图片重绘", or asks to draw/replicate any diagram — including a request that
  names an engine outright: "D3", "d3.js", "data visualization", "交互式图表", "interactive chart",
  "柱状图", "折线图", "散点图", "饼图", "力导向图", "树图", "热力图", "bar chart", "line chart",
  "pie chart", "force graph", "treemap", "heatmap", "面积图", "area chart", "气泡图", "bubble chart",
  "甜甜圈图", "donut chart", "数据仪表板", "dashboard", "SVG图表", "svg chart", "数据图形", "drawio",
  "draw.io", ".drawio", "mxgraph", "mxGraphModel", "mxGraph XML", "ECharts", "Apache ECharts",
  "数据图表", "雷达图", "仪表盘", "漏斗图", "K线图", "桑基图", "旭日图", "关系图", "状态机",
  "state machine", "gauge", "funnel", "sankey", "仪表板", "堆叠图", "stacked chart", "环形图",
  "平行坐标", "箱线图", "boxplot", "excalidraw", "手绘风格图", "手绘图", "手绘风", "白板图", "白板",
  "手绘架构图", "手绘流程图", "sketch style diagram", "hand-drawn diagram", "whiteboard diagram",
  "画个手绘风格的", "用 excalidraw 画", "excalidraw 场景", ".excalidraw 文件", "mermaid 转手绘",
  "mermaid 转 excalidraw", "生成 excalidraw", "excalidraw 渲染", "excalidraw 出图", "mermaid",
  "Mermaid图", "mermaid diagram", "architecture diagram", "UML图", "系统架构图", "画架构", "设计图",
  "组件图", "部署图", "包图", "系统设计", "活动图", "用例图", "状态机图", "模块图", "交互图",
  "sequence diagram", "class diagram", "component diagram", "deployment diagram", "activity diagram",
  "state diagram", "use case diagram", "package diagram", "工作分解结构", "甘特图", "gantt",
  "项目计划图", "进度图", "mindmap", "脑图", "实体关系图", "数据库设计", "数据建模", "表结构", "ERD",
  "entity relationship", "crow's foot", "C4", "C4图", "C4模型", "context diagram",
  "container diagram", "UI原型", "wireframe", "界面原型", "界面草图", "图片转图", "replicate diagram",
  "redraw", "image to diagram", "plantuml", "JSON可视化", "JSON数据图", "json diagram", "YAML可视化",
  "YAML显示", "yaml diagram", "配置可视化", "数据结构图", "salt", "图片转UML", "image to UML".
skill_id: "<SKILL:.specify/skills/draw-diagram/SKILL.md>"
classification: external
---

# 统一绘图入口（draw-diagram）

语义建模在先、引擎选择在后：把任何绘图请求转换为逻辑图模型（LDM），再交由唯一最合适的**内置引擎层**
渲染。**前门层不渲染任何图**，也不维护任何引擎细节；引擎细节全部归 `references/types/<engine>/` 自有。

## Goal

- 用户只面对一个绘图入口；引擎差异由路由矩阵吸收
- 六个引擎层各自强调**独特能力**（独占图种、产物形态），不再追求全面性
- 产物可对照 LDM 验收（元素/关系/分组/产物形态覆盖）

## Dispatch Contract

前门层不维护任何引擎细节：语法、渲染脚本、scene/schema、skinparam、坑位全部归各引擎层自有
（command names、options、return shapes come from the engine layer）。前门只持有：语义建模、
路由（含独占登记）、分派、覆盖验收。**两层各自编辑、互不复制**——这条边界不因两层现在同处一个
技能而消失：引擎层的文档不得上抄路由判据，前门不得下抄引擎语法。

**例外——共享渲染后端（环境特定）**：六引擎共用的渲染服务（`xuanji-render.aliyun-inc.com:9696-9701`）
是**跨引擎共享基础设施**，不属于任何单一引擎层，因此其**可用性 preflight 与自部署回退**由前门统一持有
（见 Step 2.5 + [./references/self-deploy-render-service.md](./references/self-deploy-render-service.md)）。
前门仍**不渲染**——它只在分派前确认后端可达、不可达时按既定流程提示/中断/可选自部署；各引擎的渲染请求语法仍归引擎层自有。

## Engine Layers（六个内置引擎层）

| 引擎层 | 入口文档（L4） | 独占长处 |
|--------|----------------|----------|
| `d3js` | [./references/types/d3js/d3js.md](./references/types/d3js/d3js.md) | 绝对坐标 SVG、像素级复刻、bespoke 交互 |
| `drawio` | [./references/types/drawio/drawio.md](./references/types/drawio/drawio.md) | `.drawio`/mxGraph 可编辑产物、CLI 无头导出 |
| `echarts` | [./references/types/echarts/echarts.md](./references/types/echarts/echarts.md) | 数据系列目录、toolbox/联动交互仪表板 |
| `excalidraw` | [./references/types/excalidraw/excalidraw.md](./references/types/excalidraw/excalidraw.md) | 手绘美学、可拖回继续编辑的场景 JSON |
| `mermaid` | [./references/types/mermaid/mermaid.md](./references/types/mermaid/mermaid.md) | 仓库原生声明式文本图、diff 友好 |
| `plantuml` | [./references/types/plantuml/plantuml.md](./references/types/plantuml/plantuml.md) | 严格 UML 语义、WBS/甘特/Salt/JSON/YAML/ER |

选型判据（独占登记、图类矩阵、tie-break）见 [./references/routing-matrix.md](./references/routing-matrix.md)；
每个引擎层内部自带 `references/`（L5）、`.specify/scripts/`、`assets/`，其相对路径与自定位脚本按引擎层根目录解释。

## Workflow

### Step 1:  intake 与语义建模

1. 吃透上下文（文档/代码/目标图）：先产出**带出处的上下文摘要**（组件、关系、分区、核心流程），LDM 只从摘要与用户意图构建，**不臆造元素**
2. 构建 LDM（schema 与覆盖检查定义见 [./references/semantic-model.md](./references/semantic-model.md)）：
   `diagram_class / elements / relations / zones / layout_intent / style_intent / weight_plan / artifact_intent / fidelity_intent / interactivity_intent / editability_intent`；
   含多层结构的图**必须填 `weight_plan`**（语义视觉强弱：大模块边界 > 小模块边界 > 数据流；前门决定「什么该更显眼」，引擎决定「怎么画粗」）；
   `interactivity_intent` 按**交互语义规约**落为 level + forms（形式分类、档位与默认值见 [./references/semantic-model.md](./references/semantic-model.md) § 交互语义与验收），要求交互时 `artifact_intent` 同步取 `interactive-html`
3. 产出**几何层**（语义决策，语法层实现）：canvas 尺寸、每图元 `box{x,y,w,h}`、分区盒与布局语义（equal-height/stack/grid/free）、关系锚点与间隙；复刻类从源图测量（像素或比例），新建类先规划网格再落坐标（schema 见 semantic-model.md Geometry）
4. 复刻类请求（给了现有图/文档要求重画）：`fidelity_intent=reproduction`——保留源结构与版面语义（含源图实测的每角色线宽，覆盖默认档位），不得"顺手优化"布局

### Step 2: 路由

1. **独占登记优先**（有些图只有一家能画）：[./references/routing-matrix.md](./references/routing-matrix.md) §1 命中即定引擎，不再比较
2. 否则按 §2 图类矩阵取默认引擎，再按 §3 tie-break（artifact_intent）切换
3. 仍歧义 → 一轮 `AskUserQuestion`（≤4 问）附推荐项；不得静默猜
4. **Preflight**：选定引擎的入口文档存在（`references/types/<engine>/<engine>.md`）；缺失即响亮失败并列出可用引擎，不得即兴自渲染

### Step 2.5: 共享渲染后端 preflight 与自部署回退（环境特定）

> **⚠️ 环境特定信息**：六个引擎共用一个自部署的多引擎渲染服务，消费方契约名为 `xuanji-render.aliyun-inc.com`
> （一引擎一专用端口 **9696-9701**：plantuml 9696 / mermaid 9697 / excalidraw 9698 / drawio 9699 /
> echarts 9700 / d3 9701，**无网关 / 无聚合 / 无代理**）。**并非所有执行环境都能访问 `xuanji-render.aliyun-inc.com`**——
> 它依赖该执行环境的内网 DNS / `/etc/hosts` 映射与 docker 主机。完整契约 + 自部署步骤见附件
> [./references/self-deploy-render-service.md](./references/self-deploy-render-service.md)。**委派引擎渲染（Step 3）前先过此 preflight**
> （**纯 HTML 交互交付不经此后端**——解耦语义 owner 是 [./references/delivery-contract.md](./references/delivery-contract.md) § D7.2，本节不复述）：

1. **探测可用性**：`curl -sf --max-time 5 http://xuanji-render.aliyun-inc.com:9697/healthz`（任一 Node 引擎端口的 `/healthz` 即代表后端可用）。
   **可用** → 一切按既定流程执行，进入 Step 3 委派，**不做任何部署动作**。
2. **不可用**（DNS 不解析 / 超时 / 非 200）→ **提示用户并中断**本次渲染委派；**不得**静默降级、**不得**即兴用本地工具（mermaid-cli / plantuml.jar 等）自渲染绕过。提示须说明：该地址是环境特定、当前不可达、本次无法走既定渲染后端。
3. 该提示的**末尾**必须附一个选项：**「要不要考虑自部署?」**
4. 用户选择自部署 → 按 [self-deploy-render-service.md](./references/self-deploy-render-service.md) **先分析当时的运行环境**（docker / podman / k8s / 裸机进程能力 + registry/镜像工厂可达性），据此**选择部署形态**：**docker 容器化为最优默认**，但**不假定 docker 一定可用**——按环境给出可选备选（podman rootless / Kubernetes / 裸机 systemd 进程）连同推荐项**交用户拍板**；选定后给出**具体要执行的步骤**，并在执行前**再次向用户确认是否执行自部署操作**，确认后才动手。
5. 自部署完成后 → 把 `xuanji-render.aliyun-inc.com → 自部署服务 IP` 的映射写入**执行环境**的 `/etc/hosts`；此后再次执行绘图时**直接从第 1 步 preflight 命中可用后端开始，不再重复部署步骤**。

### Step 3: 分派到引擎层

- 读选定引擎的入口文档 `references/types/<engine>/<engine>.md`，按其自身流程渲染；传入 **SDS 文件路径**（SDS = Semantic Drawing Spec，即 LDM + Geometry 的落盘形态，schema 见 [./references/semantic-model.md](./references/semantic-model.md)）+ 目标/输出要求 + **交付契约**（[./references/delivery-contract.md](./references/delivery-contract.md)：HTML 包装、源文件与图片保留、面向用户的文字规则、交互式网页交付 § D7（interactivity_intent ≠ none 时适用））；尽量 file-path-only handoff。**`weight_plan` 随 SDS 一并传递**，由引擎层按其「强弱实现」小节落地（各引擎线宽/边框语法归引擎层自有）；**`interactivity_intent` 同随 SDS 传递**，由引擎层按其「交互实现」小节落地（当前 d3js / echarts 设有该节；`level: none` 时无交互义务）
- 引擎层的 `.specify/scripts/` 按其文档给定的调用形式执行：`${SKILL_HOME}` 指本技能根目录，故引擎脚本路径形如 `${SKILL_HOME}/references/types/<engine>/scripts/<script>`
- 前门层不渲染、不手改引擎产物、不改引擎脚本（score = f(target) 纪律在引擎层各自生效）
- **只加载选定引擎那一层**：不得为了「参考」而把其它引擎层的文档读进上下文

### Step 4: 验收与回报

1. 对照 LDM 做覆盖检查：元素与标签、关系集合（含方向）、分组边界、产物形态、**强弱层级（weight_plan 在产物中可辨：边框按档递减、流线最细、关键路径仅色相抬升）**、**交互（interactivity_intent.level ≠ none 时逐声明 form 复现一次「输入 → 可见变化」，判据见 semantic-model.md § 交互语义与验收；level = none 零交互义务）**
2. **对照交付契约做验收**（[./references/delivery-contract.md](./references/delivery-contract.md) 的 D6 自检表，逐项核对）：D1/D2 交付形态在盘、D3–D5 面向用户的文字规则成立（图内文字与 HTML 正文同规）。**条文与示例只在契约里，本节不复写**；任一项不过 = 不覆盖
3. 不覆盖 → 带 delta 说明重渲染一次（上限 1 次）；仍不覆盖 → 如实回报产物与缺口
4. 回报：产物路径（HTML + 源文件 + 图片）、**选定引擎层** + 路由理由（命中独占/矩阵行/tie-break）、LDM 摘要

> **Fast Fail 实例指针**:本文件中"即停 / 即中止 / 不得静默降级"一类规则是快速失败纪律的既有**实例**;其判据与两份清单的唯一真源是 `.specify/shared/guidelines/fast-fail.md`(本文件引用它,MUST NOT 复述它)。

## 逐级披露（Progressive Disclosure —— 五层）

一次绘图请求按下面五层推进；**每层只读它需要的那一层**，不越层取内容、不把下层内容上抄。
两层同处一个技能**不改变**这条纪律：内置化改的是层的**载体**（从各自注册的技能目录改为
`references/types/<engine>/` 子树），不是层的**边界**，因此按需加载与 token 效率照旧成立。

| 层 | 承载面 | 这一层做什么 |
|----|--------|-------------|
| **L1** | `.specify/skills/draw-diagram/SKILL.md`（本文件） | 分析语义逻辑，构建 LDM 与几何层，产出**整体逻辑图表设计**（Step 1） |
| **L2** | `.specify/skills/draw-diagram/references/*.md` | 选型与判据分析：路由矩阵 / 独占登记 / tie-break / 能力轴（Step 2）、LDM/SDS schema 与覆盖检查、**交付契约**（交付形态 + 面向用户的文字规则） |
| **L3** | 分派决策本身 | 选定后读入对应引擎层入口文档，传 SDS 路径 + `weight_plan` + 交付契约（Step 3） |
| **L4** | `references/types/<engine>/<engine>.md` | 针对**自身图表类型**做引擎侧逻辑设计：「SDS 实现与强弱落地」小节把语义档位落实为本引擎的绝对线宽/字号，并声明几何兑现义务 |
| **L5** | `references/types/<engine>/references/*.md` | 各层面完善并输出最终图表：语法/格式、渲染与导出、引擎指南与坑位 |

**当前落地状态（如实记录，不粉饰）**：

- L1–L5 五层均已在盘：六个引擎层于 2026-10-12 由原 `draw-{d3js,drawio,echarts,excalidraw,mermaid,plantuml}`
  六个独立技能整体内置而来，内容无损、形式按本技能惯例重表达，各引擎层的 `references/`、`.specify/scripts/`、
  `assets/`、`best-practices/` 子树原样保留（其内部相对链接与自定位脚本随子树整体迁移，未打断）。
- 跨引擎**同名的 47 个 `.md` 文件经哈希比对无一内容相同**，全部已分化——实测口径（勿凭文件名判定重复）：
  `12-gantt-diagram.md` 在 mermaid 是 73 行、在 plantuml 是 1708 行；`layout.md` 是 69 行 vs 471 行；
  `content.md` 是 61 行 vs 345 行。因此它们**不是可去重的副本，而是同一主题的两份引擎专属实现**，
  各留在自己引擎层的 `references/{howto,guide,document}/` 内。
- 其中确有一部分是引擎无关的语义内核（如 GRASP 原则、建模方法论），**须逐文件 diff 才能分离**，
  不得按文件名批量搬移或合并；该分离与上移仍是**待办**，未完成前语义专章须到对应引擎层就地查阅，
  **不得据同名文件各自演化**（One Source Of Truth 风险已登记）。
- 本次内置的**能力继承与无损证据已落盘且可复核**：`references/merge-provenance.md`（逐引擎能力继承表）
  + `references/merge-provenance/<engine>.baseline.txt`（冻结事实基线），复核命令见该记录首行。

## Document Map

| 问题 | 读哪里 |
|------|--------|
| 独占登记 / 图类矩阵 / tie-break | [./references/routing-matrix.md](./references/routing-matrix.md) |
| LDM schema 与覆盖检查 | [./references/semantic-model.md](./references/semantic-model.md) |
| **交付形态**（HTML 包装、源文件与渲染图保留）**与面向用户的文字规则** | [./references/delivery-contract.md](./references/delivery-contract.md) |
| 共享渲染后端可用性 preflight / 自部署（**环境特定**：xuanji-render.aliyun-inc.com:9696-9701） | [./references/self-deploy-render-service.md](./references/self-deploy-render-service.md) |
| 语义视觉强弱（weight_plan 档位与验收） | [./references/semantic-model.md](./references/semantic-model.md) `weight_plan`；引擎落地见各引擎层「强弱实现」小节 |
| 可交互图表（交互形式分类/档位/验收判据；交互交付形态） | [./references/semantic-model.md](./references/semantic-model.md) § 交互语义与验收；交付侧 [./references/delivery-contract.md](./references/delivery-contract.md) § D7；引擎落地见 d3js / echarts「交互实现」小节 |
| 引擎语法、渲染、坑位、脚本 | `references/types/<engine>/`（入口 `<engine>.md`，详见其 `references/`） |
| 六引擎的能力继承与无损证据 | [./references/merge-provenance.md](./references/merge-provenance.md) |
| 路由证据（竞技场结论） | `${SKILL_WORKDIR}/.specify/memory/knowledge/visualization-skill-selection.md` |

## Boundary Between the Two Internal Layers

- 公共部分（intake 摘要纪律、语义建模、路由、验收）只在前门层维护一份
- 引擎层的入口文档与正文强调独特能力与独占图种；"什么请求该用哪个引擎"由前门路由回答，引擎层不自行声明路由判据
- 新增引擎时：先补 routing-matrix 独占/矩阵行，再在 `references/types/<new-engine>/` 建引擎层，并在 Engine Layers 表与本文件 description 补触发词
- 引擎层不得再声明自己的 `## Feedback` / `## Evaluation Form` / `skill_id`：这些是**技能级**生命周期面，
  合并后只有本技能一份（见下两节），引擎维度的信号由评价单与反馈条目内的**引擎名**承载

## Self-Improvement Contract

- Canonical owner: `.specify/skills/draw-diagram/`（镜像 `.specify/skills/draw-diagram/` 由 sync-mirrors 生成，不手改）
- Own-run observation: 每次分派的路由命中（独占/矩阵/tie-break/问用户）、验收覆盖结果、重渲染次数
- Mutation route: `improve-skills`（路由错配、矩阵缺口、LDM 字段不足、引擎层语法/坑位均走此路由修订本技能）
- Validation route: 路由判定用 arena 账本历史案例回放；纪律类修订按 create-skills 压力测试法 RED-GREEN；
  **合并无损性**用 `references/merge-provenance.md` 首行的复核命令（退出 0 = 六引擎能力与事实仍在本技能内）
- Comparison signal: 同类请求的"问用户次数 ↓、重渲染次数 ↓、验收一次通过率 ↑"
- Escalation boundary: 引擎渲染缺陷不再外移到独立技能——记入 `skill:draw-diagram` 反馈单元，
  并在条目中**点名引擎层**（如 `engine: plantuml`），以便处置时定位到 `references/types/<engine>/`

## Evaluation Form(绘制评价单)

**定位与边界。** 本节是交付结果后的 Evaluation Form(绘制评价单)，专门承载用户对本次**已交付的渲染结果**的评价；它不是 `## Feedback`，也不替代或改变该节的 agent 自省。`## Feedback` 保持其既有的「不向用户征询」规则，本节只处理用户主动给出的绘制评价。合并前六个引擎技能各有一份本节，现统一为此一份，**引擎维度改由条目内的引擎名承载**（见下）。

**运行模式门。** 若 `${SKILL_WORKDIR}/.specify/` 不存在（standalone 模式）：本节保留交付时的一次性非阻塞征询与「无评价即满意」规则，但**跳过全部反馈引擎读写**——不执行下方 probe 记录与 `--action list` 查询，用户评价仅保留在当次运行报告中，不创建反馈条目；Spec Kit 项目模式（`${SKILL_WORKDIR}/.specify/` 存在）按本节原文执行。

**触发与一次性征询。** 仅在 Step 4 已验收并回报实际交付的产物路径、选定引擎层、路由理由和 LDM 摘要之后，随该次交付附上一句非阻塞征询：`已交付渲染结果（引擎:<engine>）；如愿意，请评价这张结果是否准确、清晰且适合用途，或说明希望调整之处。` 不得在路由、渲染开始或中间结果时征询；不得等待回复、重复询问或因沉默降低交付结果。

**无评价。** 用户没有给出评价即视为本次绘制满意；不创建评价条目、不调用反馈引擎，也不在后续回合追问。

**有评价。** 用户一旦主动给出评价，保留其原意，将 review 内容标为 `## Evaluation Form`，**在 review 首行记明 `engine: <engine>`**（这是原六份分引擎评价单合并后唯一保留引擎维度的位置，缺失即无法把结论回用到对应引擎层），并从评价中提取至少一条评价要点；随后以本节的 probe 记录（不是以 `wrap-up` probe 记录）：

```bash
python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
  --unit-id "skill:draw-diagram" --unit-type skill \
  --lifecycle-point evaluation-form \
  --run-id "<drawing-run-id>:evaluation-form" --feature "<feature-key-if-any>" \
  --review-file "<evaluation-form-review-file>" \
  --points-file "<evaluation-form-points-file>"
```

这会经 `skill-draw-diagram-evaluation-form` probe 把评价条目写入 `.specify/memory/feedback/`。不得把本节记录与同次运行的 `## Feedback` 自省共用 `run_id`，也不得把用户评价改写为 agent 自评。

**处置、回用与传递边界。** 该条目进入既有的 `record→threshold→package→manual→mark-submitted` 链路，并由既有 feedback 处置流程持续标记为 `processed` 或 `ignored`；`processed` 时在 `disposition_reason` 中保留可执行结论。后续执行本技能前，查询本技能已处置的评价单并将适用结论用于语义建模、路由或验收（**含按引擎名筛选**）：

```bash
python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action list \
  --unit-id "skill:draw-diagram" --disposition processed --contains "Evaluation Form"
```

本节绝不自动发送任何内容。若记录结果的既有 threshold 机制要求提示，只能按既有协议给出一次非阻塞的手动打包/提交提示；本节自身的评价征询始终只有交付时的一次。

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:draw-diagram" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:draw-diagram" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:draw-diagram" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
