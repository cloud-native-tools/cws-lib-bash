# 参考文档索引

> 本文件是 draw-mermaid 技能所有参考文档的汇总入口。SKILL.md 中的工作流步骤通过本文件索引到具体的参考文档。

---

## 目录结构

```
references/
├── index.md           ← 本文件（汇总索引）
├── sds-realization.md ← SDS 实现与逼近（几何脚手架、档位→线宽映射、偏离声明模板）
├── howto/             ← 操作指南（分步指南，对应工作流步骤）
├── guide/             ← 最佳实践与优化指南
└── document/          ← 官方文档与参考手册
```

---

## 操作指南（`howto/`）

按工作流步骤组织的分步指南，提供具体的操作方法和示例。

| # | 文档 | 对应步骤 | 内容说明 |
|---|------|---------|---------|
| 0 | [00-semantic-analysis.md](howto/00-semantic-analysis.md) | Step 1 | 语义分析与意图理解——分类输入类型（直接描述/图片复刻/模糊/代码可视化）、提取内容、差距分析、交互式确认 |
| 1 | [01-choose-diagram-type.md](howto/01-choose-diagram-type.md) | Step 2 | 选择图表类型——**PlantUML ↔ Mermaid 类型对照表**、快速匹配表、按开发阶段/系统类型推荐、常见组合模式、Mermaid 独有类型速览 |
| 2 | [02-class-diagram.md](howto/02-class-diagram.md) | Step 3/6 | 类图——类定义、6 种关系类型、namespace、classDef 样式、GRASP 设计原则 |
| 3 | [03-component-diagram.md](howto/03-component-diagram.md) | Step 3/6 | 组件图——分层架构、微服务模式、接口和依赖建模（flowchart subgraph / C4Component） |
| 4 | [04-deployment-diagram.md](howto/04-deployment-diagram.md) | Step 3/6 | 部署图——物理拓扑、Kubernetes、云服务、节点间通信（flowchart subgraph / C4Deployment） |
| 5 | [05-sequence-diagram.md](howto/05-sequence-diagram.md) | Step 3/6 | 时序图——消息类型、组合片段（alt/loop/par/opt/break）、激活条、交互流程 |
| 6 | [06-package-diagram.md](howto/06-package-diagram.md) | Step 3/6 | 包图——模块组织、命名空间层次、分层架构、依赖管理（flowchart subgraph / classDiagram namespace） |
| 7 | [07-usecase-diagram.md](howto/07-usecase-diagram.md) | Step 3/6 | 用例图（flowchart 近似）——角色、用例、系统边界、include/extend/generalization 语义表达 |
| 8 | [08-activity-diagram.md](howto/08-activity-diagram.md) | Step 3/6 | 活动图——业务流程建模、泳道（subgraph）、fork/join 并发、决策节点 |
| 9 | [09-state-machine-diagram.md](howto/09-state-machine-diagram.md) | Step 3/6 | 状态机图——对象生命周期、状态转换、事件/守卫/动作、组合状态、fork/join、并发 |
| 10 | [10-layout-planning.md](howto/10-layout-planning.md) | Step 4 | 布局规划——方向/宽高比决策、subgraph 分组、布局故障排除、CJK 渲染问题 |
| 11 | [11-code-generation.md](howto/11-code-generation.md) | Step 6 | 代码生成——草拟流程、标签与注释规则（≤10 字符 + 边标签/note）、`%%{init}%%` 指令位置 |
| 12 | [12-rendering-and-output.md](howto/12-rendering-and-output.md) | Step 8 | 渲染、匹配验证与输出——SVG/PNG 渲染（服务器/本地后端）、HTML 组装、质量检查清单 |
| 13 | [13-wbs-diagram.md](howto/13-wbs-diagram.md) | 专项 | WBS 工作分解结构（mindmap 承接）——层级分解、方向、无框节点、状态色 + `\n【责任人】` 信息编码；内联「有效字号」分档规则 |
| 14 | [14-gantt-diagram.md](howto/14-gantt-diagram.md) | 专项 | 甘特图——任务/工期/依赖、里程碑、完成度、颜色、分隔符、工作日历、今日标记、时间刻度；量测自检三判据 |
| 15 | [15-mindmap-diagram.md](howto/15-mindmap-diagram.md) | 专项 | 思维导图——缩进式语法、左右分支、节点形状、`classDef` 样式 |
| 16 | [16-json-diagram.md](howto/16-json-diagram.md) | 专项 | JSON 数据可视化（flowchart 近似）——对象/数组/嵌套层级、类型标注、高亮 |
| 17 | [17-yaml-diagram.md](howto/17-yaml-diagram.md) | 专项 | YAML 显示效果（flowchart 近似）——嵌套映射/列表层级、键值标注 |
| 18 | [18-er-diagram.md](howto/18-er-diagram.md) | 专项 | ER 实体关系图——实体/属性/主外键、乌鸦脚基数、复合主键、域分组 |
| 19 | [19-salt-diagram.md](howto/19-salt-diagram.md) | 专项 | Salt UI 线框图（flowchart 近似）——按钮/输入/复选/单选/下拉控件、分组框、表格 |
| 20 | [20-c4-diagram.md](howto/20-c4-diagram.md) | 专项 | C4 架构图——C4Context/C4Container/C4Component/C4Dynamic/C4Deployment 五视图写法 |

> **专项图表（非 UML）**：13–17、19 覆盖 WBS/甘特图/思维导图/JSON/YAML/Salt 六种非 UML 图表；18 为 ER 图（`erDiagram` 原生）；20 为 C4 系列（`C4Context` 等原生）。其中 WBS/JSON/YAML/Salt 在 Mermaid 无原生类型，使用最接近的类型（mindmap / flowchart）语义近似，文档中已标注。

---

## 最佳实践与优化指南（`guide/`）

按方面组织的绘图质量提升指南。在工作流中按需阅读。

| 文档 | 对应步骤 | 方面 | 内容说明 |
|------|---------|------|---------|
| [diagram-principles.md](guide/diagram-principles.md) | Step 1–7（所有图通用） | 通用原则 | **图表类型无关的核心原则**：四步执行顺序（UML语义→视觉语义→布局→美化）、UML 语义先行（选对图类型/元素种类/关系类型/构造型/接口）、视觉语义（角色即位置/数量表拓扑/关联同色/文字即负担）、**元素标签最小化规则（去重优先）** |
| [large-diagram-playbook.md](guide/large-diagram-playbook.md) | Step 4/5/7 | 大图美化 | **第0步 先做 UML 语义分析（图类型/元素种类/关系类型/构造型/接口）再绘图** + 复杂大图五步技术栈——「×N」语义折叠、弱化管线/突出语义色、字号层级、subgraph 分层控宽高比消交叉、长文本移入 legend；含大图专用自检清单 |
| [style.md](guide/style.md) | Step 7 | 样式 | `%%{init}%%` themeVariables 模板、主题选择（default/neutral/dark/forest/base）、classDef/样式类、关键路径着色、SVG/PNG 双策略说明、样式校验要点 |
| [layout.md](guide/layout.md) | Step 4/5 | 布局 | 语义驱动布局、布局优化（方向控制/隐藏连线/分组/间距/宽高比）、按图表类型的布局速查、常见布局问题排查、Mermaid 布局引擎行为规律、渲染服务限制（URL 长度/CJK 字体） |
| [content.md](guide/content.md) | Step 5/6 | 内容 | 单一职责/C4 分层/元素数量控制/标签精简 ≤10 字符 + 注释、注释策略（边标签/note/legend）、别名与标签规范、协作与维护规范、质量自检清单 |
| [syntax-reference.md](guide/syntax-reference.md) | Step 6 | 语法 | Mermaid 语法参考——覆盖全部 20 类图表类型的完整语法、元素类型、关系表示法、`%%{init}%%` 配置、常见模式、10 条实用技巧 |

---

## 官方文档与参考手册（`document/`）

UML 理论、Mermaid 语法参考、官方文档和建模方法论的原始参考材料。按需加载以深入理解设计原则和语法细节。

| 文档 | 内容说明 |
|------|---------|
| [00-mermaid-overview.md](document/00-mermaid-overview.md) | Mermaid 官方能力总览——图表类型全景、渲染方式（浏览器/mermaid-cli/服务器）、PlantUML 对照起点 |
| [01-uml-overview.md](document/01-uml-overview.md) | UML 概述——图表类型分类、建模原则、UML 在软件工程中的角色 |
| [02-class-diagram.md](document/02-class-diagram.md) | 类图理论——类的结构、关系类型（泛化/实现/关联/聚合/组合/依赖）、多重性 |
| [03-sequence-diagram.md](document/03-sequence-diagram.md) | 时序图理论——参与者、生命线、消息类型、组合片段、交互使用 |
| [04-usecase-diagram.md](document/04-usecase-diagram.md) | 用例图理论——角色、用例、系统边界、include/extend 关系（及 Mermaid 近似方案） |
| [05-activity-diagram.md](document/05-activity-diagram.md) | 活动图理论——活动、转移、决策、并行、泳道 |
| [06-state-machine-diagram.md](document/06-state-machine-diagram.md) | 状态机图理论——状态、转换、事件、守卫、动作、组合状态 |
| [07-mermaid-guide.md](document/07-mermaid-guide.md) | Mermaid 使用指南——基础语法、工具选型（mmdc / mermaid.ink / 编辑器插件）、环境配置 |
| [08-modeling-methodology.md](document/08-modeling-methodology.md) | 建模方法论——面向对象设计原则、SOLID、GRASP 模式 |
| [09-grasp-principles.md](document/09-grasp-principles.md) | GRASP 设计模式——信息专家、创建者、控制器、低耦合、高内聚等 |
| [10-architecture-diagram.md](document/10-architecture-diagram.md) | 架构图设计——架构视图、C4 模型、视图视角 |
| [11-wbs-diagram.md](document/11-wbs-diagram.md) | WBS 理论——工作分解结构定义、分解原则（与 Mermaid mindmap/flowchart 承接） |
| [12-gantt-diagram.md](document/12-gantt-diagram.md) | 甘特图参考——任务/依赖/里程碑/日历/着色/刻度完整语法 |
| [13-mindmap-diagram.md](document/13-mindmap-diagram.md) | 思维导图参考——缩进语法、节点形状、分支方向、样式类 |
| [14-json-diagram.md](document/14-json-diagram.md) | JSON 可视化参考——PlantUML `@startjson` 语义与 flowchart 近似对照 |
| [15-yaml-diagram.md](document/15-yaml-diagram.md) | YAML 可视化参考——PlantUML `@startyaml` 语义与 flowchart 近似对照 |
| [16-er-diagram.md](document/16-er-diagram.md) | ER 图参考——实体/属性/基数/乌鸦脚记法完整语法 |

---

## 快速查找

| 需求 | 查看文档 |
|------|---------|
| 如何分析用户输入 | [howto/00-semantic-analysis.md](howto/00-semantic-analysis.md) |
| PlantUML 图怎么转 Mermaid | [howto/01-choose-diagram-type.md](howto/01-choose-diagram-type.md) 的类型对照表 |
| 该选哪种 UML 图 | [howto/01-choose-diagram-type.md](howto/01-choose-diagram-type.md) |
| 某种图怎么画 | [howto/02–09](howto/) 对应图表类型 |
| 专项图怎么画（WBS/甘特/思维导图/JSON/YAML/ER/C4/Salt） | [howto/13–20](howto/) 对应专项图表 |
| 布局怎么规划 | [howto/10-layout-planning.md](howto/10-layout-planning.md) + [guide/layout.md](guide/layout.md) §一 |
| SDS 怎么实现/逼近（档位线宽、几何脚手架、偏离声明） | [sds-realization.md](sds-realization.md) |
| 标签和注释怎么写 | [howto/11-code-generation.md](howto/11-code-generation.md) §二 + [guide/content.md](guide/content.md) §1.5 |
| 样式怎么配 | [guide/style.md](guide/style.md) |
| 怎么渲染和验证 | [howto/12-rendering-and-output.md](howto/12-rendering-and-output.md) |
| WBS/甘特成图够不够清晰、标签有没有越界、某写法有没有改排期 | `../scripts/measure-svg-layout.py`（量测三判据 + `--compare` A/B）；判据说明见 [howto/14-gantt-diagram.md](howto/14-gantt-diagram.md) 「量测自检」与 [howto/13-wbs-diagram.md](howto/13-wbs-diagram.md) 「尺寸、清晰度与留白」 |
| 布局出问题怎么排查 | [howto/10-layout-planning.md](howto/10-layout-planning.md) §三 + [guide/layout.md](guide/layout.md) §四 |
| 复杂大图太乱/太大怎么美化 | [guide/large-diagram-playbook.md](guide/large-diagram-playbook.md) |
| 某个语法怎么写 | [guide/syntax-reference.md](guide/syntax-reference.md) + [document/00-mermaid-overview.md](document/00-mermaid-overview.md) |
| UML 理论基础 | [document/](document/) 目录下 01–10 的理论文档 |
