# Routing Matrix & Exclusivity Registry（draw-diagram 前门路由权威）

> 证据源：竞技场结论账本 `${SKILL_WORKDIR}/.specify/memory/knowledge/visualization-skill-selection.md`
> （viz-skill-arena 各轮 cycle 的冠军与匹配结论）。本文件只登记**路由判据**；引擎语法与渲染细节归各 draw-* 技能。

## 0. 能力轴层（Capability Axes —— 剪枝层，veto-only）

> **轴②「渲染位置」暂缓登记。** 渲染方式正在另一条流程中重新裁定（远端渲染优先以减少本地依赖、
> 并统一出图口径；含「各引擎是否共用同一远端渲染服务」这一未决架构问题）。在其定案前，本文件
> **不登记轴②取值**——登记一个已知处于争议中的取值，会让路由据错误前提选引擎。轴①③④ 不受影响，
> 照常生效；轴② 定案后由该流程补入本节。

### 0.1 轴定义

| # | 轴 | 判据问法 |
|---|----|---------|
| ① | 动态图表能力 | 产物是否可交互、可随数据刷新？ |
| ③ | 版面自由度 | 能否绘制自由版面（布局由调用方而非渲染器决定）？ |
| ④ | 语义强度与绘图约束 | 语义元模型多强、引擎施加的绘图约束多强（二者正相关）？ |

### 0.2 六引擎 × 三轴取值（18 格）

行序为字母序，无等级含义。每格 = **取值 — 一句依据**。`draw-diagram` 是前门、不渲染，
**不占轴值行**；它的角色是据轴剪枝后选引擎。

| 引擎 | ① 动态图表能力 | ③ 版面自由度 | ④ 语义强度 / 绘图约束 |
|------|---------------|-------------|----------------------|
| `draw-d3js` | **具备** — 数据绑定与事件层由脚本直接承担，可交互、可随数据刷新 | **可** — 绝对坐标 SVG 控制，无布局引擎干预，版面完全由调用方决定 | **最弱 / 最弱** — 无元模型：画布即几何，语义须调用方自建，引擎不施加任何语义约束 |
| `draw-drawio` | **不具** — 产物是静态 mxGraph 几何 XML 及其渲染/导出图；viewer 仅平移缩放，不随数据刷新 | **可** — 调用方自算的 `x/y/width/height` 被原样保留，几何即产物；布局与走线 pass 均为**显式可选**（`--layout`、`postLayout=elk`、`routing=libavoid`），默认不改调用方坐标 | **弱 / 弱（含非语义负担）** — mxGraph 核心是几何图元、形状库只是外观模板；坐标自算是负担而非语义约束 |
| `draw-echarts` | **具备** — option/series 全量重绘即数据驱动刷新，toolbox 与图表联动为原生交互 | **受限（非自由）** — 版面须落在坐标系/系列目录内；约束类型 = **枚举式系列目录**（坐标系语义外的自由版面只能退化为 graphic 元件） | **中 / 中** — series + option 树承载「数据→图形」映射，约束随系列目录枚举 |
| `draw-excalidraw` | **不具** — 场景 JSON 是静态手绘元素；React 组件可交互编辑，但不随数据刷新 | **可** — 场景元素自由摆放，几何任意 | **最弱 / 最弱** — 手绘元素无关系语义，引擎不做语义校验 |
| `draw-mermaid` | **不具** — 文本→单帧渲染，重绘即重新生成，无数据绑定与交互层 | **不可** — 文本生图：文本须遵循语法、语法自身即携带语义，布局归渲染器；约束类型 = **文本语法** | **中 / 中** — 每个图类型一套语法，语法关键字即语义声明，约束随语法 |
| `draw-plantuml` | **不具** — 远端单帧输出（SVG/PNG），无交互与数据刷新通道 | **不可** — 语义元模型决定版面并自动布局；约束类型 = **语义元模型**（最强） | **最强 / 最强** — UML/专有标签原生元模型（component/entity/relation 有类型），声明即受语义约束 |

### 0.3 交互规则（固定执行语义）

1. **轴层是剪枝层（veto-only）**：只回答「某引擎能否满足本诉求」，**不提名引擎、不产生默认、不排序候选**。轴取值本身永远不足以选中一家引擎。
2. **固定执行序**：`§0 轴剪枝` → `§1 独占登记` → `§2 图类矩阵（默认 + 替代）` → `§3 tie-break` → `§4 红线`。
3. **轴取值 MUST NOT 推翻独占命中**：独占登记是「只有一家能画」的能力上界断言，轴取值是可行性谓词。命中 §1 即定引擎（例：命中「可编辑白板」= excalidraw，不得因「标准工程观感」改判 drawio）。
4. **冲突不静默**：被独占命中的引擎同时被轴剪枝判为不可行（例：「甘特图 + 自由版面」——甘特独占 plantuml，而 plantuml 无自由版面）是**诉求自身矛盾**，MUST 升级为 §3 既有的一轮 `AskUserQuestion`（并列呈现独占依据与轴冲突），MUST NOT 静默改路。
5. **剪枝可位移 §2 默认**：若 §2 某行默认引擎被轴剪枝剔除，顺次取该行**未被剪枝**的替代；替代耗尽 → 按第 4 条升级。轴剪枝先于 §2 生效。
6. **轴取值只在 §3 内部当最终排序判据**（竞争双方同为非独占候选时），判据文本单点拥有在 §0.4，§3 只引用不复制。

### 0.4 `draw-drawio` ↔ `draw-excalidraw` 可判优先序

二者同处「自由版面」，是三轴唯一的同轴正面竞争。**判据有序、每步可判、无「皆可/视情况/取决于」出口**：

1. **引擎身份 / 产物格式显式点名** → 按其点名（`drawio`/`draw.io`/`.drawio`/`mxGraph` → drawio；`excalidraw`/`.excalidraw`/手绘/白板/sketch/hand-drawn/whiteboard → excalidraw）。
2. **命中 §1 独占** → 按独占（「可编辑白板产物 / 手绘美学 / mermaid→手绘桥接」= excalidraw），不再比较。
3. **显式审美诉求** → 要手绘/白板观感 → excalidraw；要标准工程制图观感 → drawio。
4. **交付链路** → 需官方 CLI 无头/批量导出（svg/png/pdf）或静态 viewer / iframe 嵌入 → drawio；需 React 组件嵌入 → excalidraw。
5. **缺省（无任何区分信号）** → **draw-drawio**。

**主判据（tie-break 维度）= 观感**：标准工程制图 vs 手绘白板。**次判据 = 交付链路成熟度**：官方 CLI 无头导出（drawio）vs 需 Playwright/headless（excalidraw），并延伸出嵌入形态（viewer/iframe vs React 组件）与产物形态（`.drawio` XML vs `.excalidraw` JSON）。**缺省归 drawio 的理由**：无标记诉求的缺省形态是标准工程图 + 可交付导出物；手绘白板是审美选择，必须被显式表达。继续可编辑性两家都具备，故不构成区分点——`excalidraw` 的独占已由 §1「可编辑白板产物」这一**更窄的诉求**承担。

## 1. 独占登记（Exclusivity Registry —— 只有一家能画）

命中即定引擎，跳过比较：

| 图种 / 产物诉求 | 唯一引擎 | 独占理由 |
|----------------|---------|---------|
| WBS、甘特图、Salt UI 线框图、JSON 可视化、YAML 显示效果图、ER 实体关系（crow's foot） | **draw-plantuml** | 原生 `@start` 族标签与 entity 语法，其余引擎无等价表达 |
| 可编辑白板产物（`.excalidraw` 拖回继续编辑）、手绘美学、mermaid→手绘桥接 | **draw-excalidraw** | 场景 JSON 是唯一可继续编辑的白板源文件 |
| ECharts 仪表板嵌入、标准数据系列图且要 toolbox/联动交互 | **draw-echarts** | ECharts 生态与系列目录原生支持 |
| 既有图像的像素级复刻、超出目录的 bespoke D3 交互 | **draw-d3js** | 绝对坐标 SVG 控制，无布局引擎干预 |
| 仓库原生声明式文本图（GitHub/CI 免工具链直渲、diff 友好） | **draw-mermaid** | 平台原生 mermaid 渲染，文本即产物 |
| `.drawio`/mxGraph 可编辑图形产物、官方 CLI 无头导出（`drawio -x -f svg/png/pdf`）、免文本语法中介的原生几何/形状库工程制图 | **draw-drawio** | 唯一「图形源可编辑（非文本重生成）+ 官方 CLI 导出链路 + 标准工程形状库」三者同时成立的引擎（mermaid-cli 产出位图、excalidraw 无官方 CLI） |

## 2. 图类矩阵（默认引擎 + 替代切换）

| 图类 / 意图 | 默认引擎 | 替代（artifact_intent 命中即切换） | 证据 |
|------------|---------|----------------------------------|------|
| 部署/架构拓扑**复刻**（像素级、散点布局、等高分区、单色） | **draw-d3js** | echarts（interactive-html）、excalidraw（editable-whiteboard） | cycle 3 冠军 R2 0.95 |
| UML 语义架构图（component/deployment/sequence/class/package） | **draw-plantuml** | d3js（仅复刻形态） | cycle 1-2 冠军 |
| 自由版面架构/拓扑**新建**（要可继续编辑） | **draw-excalidraw** | d3js（像素自定义）、drawio（标准工程观感）、plantuml（UML 严格） | cycle 3 R2 0.94 |
| 标准工程观感**新建**（工程制图 / 形状库 / 交付物需 CLI 导出或 PDF） | **draw-drawio** | plantuml（UML 严格语义）、excalidraw（手绘白板）、d3js（像素自定义） | 新增引擎（S1f 引导），待竞技场复评 |
| 流程图 / 状态机 / 简单时序（text-first、进仓库维护） | **draw-mermaid** | plantuml（UML 严格语义） | 可维护性优先 |
| 数据可视化（柱/线/饼/散点/力导向/树图/热力） | **draw-echarts** | d3js（bespoke 交互） | 系列目录覆盖 |
| 思维导图 | **draw-plantuml**（原生） | mermaid（repo-text）、excalidraw（editable） | 三引擎皆可，按产物形态 |

## 3. Tie-break 顺序（artifact_intent 优先）

1. `editable-whiteboard` → draw-excalidraw
2. `interactive-dashboard` → draw-echarts
3. `repo-text` → draw-mermaid
4. `pixel-reproduction` → draw-d3js
5. `uml-strict` / `static-embed` → draw-plantuml

6. `standard-engineering`（标准工程观感 / `.drawio` 可编辑产物 / 需 CLI 导出）→ draw-drawio
7. `react-embed`（需 React 组件嵌入、或产物要拖回继续手绘编辑）→ draw-excalidraw
8. 与 artifact_intent 无关的「同为自由版面」竞争 → 依 §0.4 有序判据；判据无信号时缺省 draw-drawio

并列仍不可决 → 一轮 AskUserQuestion（≤4 问）附推荐项；推荐项 = 矩阵默认引擎。

## 4. 反路由红线（MUST NOT）

- 不得因"某引擎也会画"而绕过独占登记（如用 mermaid 画甘特替代 plantuml 原生甘特）
- 不得把复刻请求路由到自动布局引擎（mermaid/plantuml）——等高分区与散点版面会被布局算法改写（cycle 3 证据：mermaid 0.755）
- 不得为凑"全面性"让下层技能承接非其独特的图种；路由责任在前门
- 不得把要求**自由版面**的诉求路由到 `draw-mermaid` / `draw-plantuml`（前者版面受文本语法约束、后者受语义元模型约束，自由版面不可表达）
- 不得把要求**动态图表**（可交互 / 随数据刷新）的诉求路由到静态单帧引擎（`drawio` / `excalidraw` / `mermaid` / `plantuml`）——动态图表能力只属 `draw-d3js` / `draw-echarts`
- 不得把需要**坐标系语义外自由几何**的诉求压给 `draw-echarts`（系列目录是枚举式约束，超出即无承载）
- 不得以「轴取值命中」为理由改写或跳过独占登记（轴层 veto-only，见 §0.3 规则 3）
