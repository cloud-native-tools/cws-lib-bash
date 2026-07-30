# 参考文档索引

> 本文件是 draw-plantuml 技能所有参考文档的汇总入口。SKILL.md 中的工作流步骤通过本文件索引到具体的参考文档。

---

## 目录结构

```
references/
├── index.md           ← 本文件（汇总索引）
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
| 1 | [01-choose-diagram-type.md](howto/01-choose-diagram-type.md) | Step 2 | 选择图表类型——快速匹配表、按开发阶段/系统类型推荐、常见组合模式 |
| 2 | [02-class-diagram.md](howto/02-class-diagram.md) | Step 3/6 | 类图——类定义、6 种关系类型、GRASP 设计原则 |
| 3 | [03-component-diagram.md](howto/03-component-diagram.md) | Step 3/6 | 组件图——分层架构、微服务模式、接口和依赖建模 |
| 4 | [04-deployment-diagram.md](howto/04-deployment-diagram.md) | Step 3/6 | 部署图——物理拓扑、Kubernetes、云服务、节点间通信 |
| 5 | [05-sequence-diagram.md](howto/05-sequence-diagram.md) | Step 3/6 | 时序图——消息类型、组合片段（alt/loop/par）、激活条、交互流程 |
| 6 | [06-package-diagram.md](howto/06-package-diagram.md) | Step 3/6 | 包图——模块组织、命名空间层次、分层架构、依赖管理 |
| 7 | [07-usecase-diagram.md](howto/07-usecase-diagram.md) | Step 3/6 | 用例图——角色、用例、系统边界、include/extend/generalization |
| 8 | [08-activity-diagram.md](howto/08-activity-diagram.md) | Step 3/6 | 活动图——业务流程建模、泳道、fork/join 并发、决策节点 |
| 9 | [09-state-machine-diagram.md](howto/09-state-machine-diagram.md) | Step 3/6 | 状态机图——对象生命周期、状态转换、事件/守卫/动作、组合状态 |
| 10 | [10-layout-planning.md](howto/10-layout-planning.md) | Step 4 | 布局规划——多区域复杂布局、布局故障排除、CJK 渲染问题 |
| 11 | [11-code-generation.md](howto/11-code-generation.md) | Step 6 | 代码生成——草拟流程、标签与注释规则（≤10 字符 + note）、配套文字准备 |
| 12 | [12-rendering-and-output.md](howto/12-rendering-and-output.md) | Step 8 | 渲染、匹配验证与输出——SVG/PNG 渲染、HTML 组装、质量检查清单 |
| 13 | [13-wbs-diagram.md](howto/13-wbs-diagram.md) | 专项 | WBS 工作分解结构——层级分解、左右方向、无框节点、算术记法、`<style>` 配色 |
| 14 | [14-gantt-diagram.md](howto/14-gantt-diagram.md) | 专项 | 甘特图——任务/工期/依赖、里程碑、完成度、颜色、分隔符、工作日历、今日标记、时间刻度 |
| 15 | [15-mindmap-diagram.md](howto/15-mindmap-diagram.md) | 专项 | 思维导图——OrgMode/Markdown/算术三套写法、左右分支、无框节点、`<style>` 与命名样式类 |
| 16 | [16-json-diagram.md](howto/16-json-diagram.md) | 专项 | JSON 数据可视化——对象/数组/嵌套渲染、`#highlight` 路径高亮、`jsonDiagram` `<style>` |
| 17 | [17-yaml-diagram.md](howto/17-yaml-diagram.md) | 专项 | YAML 显示效果——嵌套映射/列表渲染、`# highlight` 路径高亮、`yamlDiagram` `<style>` |
| 18 | [18-er-diagram.md](howto/18-er-diagram.md) | 专项 | ER 实体关系图——`entity` 属性/主外键、乌鸦脚基数、复合主键、域分组、正交路由 |
| 19 | [19-salt-diagram.md](howto/19-salt-diagram.md) | 专项 | Salt UI 线框图——按钮/输入/复选/单选/下拉控件、列布局、分组框、导航树、表格、菜单/页签 |

> **专项图表（非 UML）**：13–17、19 覆盖 WBS/甘特图/思维导图/JSON/YAML/Salt 六种非 UML 图表，使用各自原生语法，无需 Graphviz；18 为 ER 图（`@startuml` + `entity` 乌鸦脚语法，遵循 UML 样式规范，走 Graphviz 布局）。

---

## 最佳实践与优化指南（`guide/`）

按方面组织的绘图质量提升指南。在工作流中按需阅读。

| 文档 | 对应步骤 | 方面 | 内容说明 |
|------|---------|------|---------|
| [diagram-principles.md](guide/diagram-principles.md) | Step 1–7（所有图通用） | 通用原则 | **图表类型无关的核心原则**：四步执行顺序（UML语义→视觉语义→布局→美化）、UML 语义先行（选对图类型/元素种类/关系类型/构造型/接口）、视觉语义（角色即位置/数量表拓扑/关联同色/文字即负担）、**元素标签最小化规则（去重优先）** |
| [large-diagram-playbook.md](guide/large-diagram-playbook.md) | Step 4/5/7 | 大图美化 | **第0步 先做 UML 语义分析（图类型/元素种类/关系类型/构造型/接口）再绘图** + 复杂大图五步技术栈——「×N」语义折叠、弱化管线/突出语义色、字号层级、正交路由+隐藏边控宽高比消交叉、长文本移入 legend；含大图专用自检清单 |
| [style.md](guide/style.md) | Step 7 | 样式 | 基础 skinparam 模板、色彩模式选择（单色/彩色）、关键路径着色、条件样式（actor）、SVG/PNG 双策略说明、配置项说明、样式校验要点 |
| [layout.md](guide/layout.md) | Step 4/5 | 布局 | 语义驱动布局、布局优化（方向控制/隐藏连线/分组/间距/宽高比）、按图表类型的布局速查、常见布局问题排查、Graphviz 引擎行为规律、PlantUML Server 限制（PNG 硬上限/CJK 字体）、三方权衡分析、版本演进转折点 |
| [content.md](guide/content.md) | Step 5/6 | 内容 | 单一职责/C4 分层/元素数量控制/标签精简 ≤10 字符 + 富文本注释、注释策略、别名与标签规范、协作与维护规范、质量自检清单 |
| [syntax-reference.md](guide/syntax-reference.md) | Step 6 | 语法 | PlantUML 语法参考——覆盖全部 7 种图表类型的完整语法、元素类型、关系表示法、skinparam、常见模式、10 条实用技巧 |

---

## 官方文档与参考手册（`document/`）

UML 理论、PlantUML 语法参考、官方文档和建模方法论的原始参考材料。按需加载以深入理解设计原则和语法细节。

| 文档 | 内容说明 |
|------|---------|
| [01-uml-overview.md](document/01-uml-overview.md) | UML 概述——图表类型分类、建模原则、UML 在软件工程中的角色 |
| [02-class-diagram.md](document/02-class-diagram.md) | 类图理论——类的结构、关系类型（泛化/实现/关联/聚合/组合/依赖）、多重性 |
| [03-sequence-diagram.md](document/03-sequence-diagram.md) | 时序图理论——参与者、生命线、消息类型、组合片段、交互使用 |
| [04-usecase-diagram.md](document/04-usecase-diagram.md) | 用例图理论——角色、用例、系统边界、include/extend 关系 |
| [05-activity-diagram.md](document/05-activity-diagram.md) | 活动图理论——活动、转移、决策、并行、泳道 |
| [06-state-machine-diagram.md](document/06-state-machine-diagram.md) | 状态机图理论——状态、转换、事件、守卫、动作、组合状态 |
| [07-plantuml-guide.md](document/07-plantuml-guide.md) | PlantUML 使用指南——基础语法、工具选型、环境配置 |
| [08-modeling-methodology.md](document/08-modeling-methodology.md) | 建模方法论——面向对象设计原则、SOLID、GRASP 模式 |
| [09-grasp-principles.md](document/09-grasp-principles.md) | GRASP 设计模式——信息专家、创建者、控制器、低耦合、高内聚等 |
| [10-architecture-diagram.md](document/10-architecture-diagram.md) | 架构图设计——架构视图、C4 模型、视图视角 |
| [00-plantuml-overview.md](document/00-plantuml-overview.md) | PlantUML 官方文档——支持的图表类型、时序图详细语法、类图/活动图/组件图基本语法、布局引擎选项、输出格式 |
| [11-wbs-diagram.md](document/11-wbs-diagram.md) | WBS 官方文档缓存——OrgMode/算术语法、方向、无框节点、多行、颜色与 `<style>` |
| [12-gantt-diagram.md](document/12-gantt-diagram.md) | 甘特图官方文档缓存——任务/依赖/里程碑/日历/着色/刻度/资源等完整语法 |
| [13-mindmap-diagram.md](document/13-mindmap-diagram.md) | 思维导图官方文档缓存——OrgMode/Markdown/算术语法、左右分支、无框、`<style>` |
| [14-json-diagram.md](document/14-json-diagram.md) | JSON 可视化官方文档缓存——数据类型渲染、`#highlight`、`jsonDiagram` `<style>`、混合图 |
| [15-yaml-diagram.md](document/15-yaml-diagram.md) | YAML 可视化官方文档缓存——嵌套/列表渲染、`# highlight`、`yamlDiagram` `<style>` |

---

## 快速查找

| 需求 | 查看文档 |
|------|---------|
| 如何分析用户输入 | [howto/00-semantic-analysis.md](howto/00-semantic-analysis.md) |
| 该选哪种 UML 图 | [howto/01-choose-diagram-type.md](howto/01-choose-diagram-type.md) |
| 某种图怎么画 | [howto/02–09](howto/) 对应图表类型 |
| 专项图怎么画（WBS/甘特/思维导图/JSON/YAML） | [howto/13–17](howto/) 对应专项图表 |
| ER 图 / Salt 线框图怎么画 | [howto/18-er-diagram.md](howto/18-er-diagram.md)、[howto/19-salt-diagram.md](howto/19-salt-diagram.md) |
| 布局怎么规划 | [howto/10-layout-planning.md](howto/10-layout-planning.md) + [guide/layout.md](guide/layout.md) §一 |
| 标签和注释怎么写 | [howto/11-code-generation.md](howto/11-code-generation.md) §二 + [guide/content.md](guide/content.md) §1.5 |
| 样式怎么配 | [guide/style.md](guide/style.md) |
| 怎么渲染和验证 | [howto/12-rendering-and-output.md](howto/12-rendering-and-output.md) |
| 布局出问题怎么排查 | [howto/10-layout-planning.md](howto/10-layout-planning.md) §三 + [guide/layout.md](guide/layout.md) §四 |
| 复杂大图太乱/太大怎么美化 | [guide/large-diagram-playbook.md](guide/large-diagram-playbook.md) |
| 某个语法怎么写 | [guide/syntax-reference.md](guide/syntax-reference.md) + [document/00-plantuml-overview.md](document/00-plantuml-overview.md) |
| UML 理论基础 | [document/](document/) 目录下 01–10 的理论文档 |
