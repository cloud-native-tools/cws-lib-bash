# Mermaid 官方能力总览（00）

> Mermaid 是一个基于 JavaScript 的图表渲染库：用类 Markdown 文本定义图表，浏览器/CLI/服务器渲染为 SVG/PNG。本技能以「复刻 PlantUML 图表能力」为目标组织用法。

## 1. 图表类型全景（v11）

| 分类 | 类型 |
|------|------|
| 流程图 | flowchart（含 subgraph、样式类、交互） |
| UML | sequenceDiagram、classDiagram、stateDiagram-v2、erDiagram |
| 项目/计划 | gantt、journey、timeline、kanban（实验） |
| 架构 | C4Context、C4Container、C4Component、C4Dynamic、C4Deployment、architecture（实验）、block（实验） |
| 数据 | pie、quadrantChart、xychart-beta、sankey-beta、packet-beta |
| 需求/版本 | requirementDiagram、gitGraph |
| 树 | mindmap |

## 2. 与 PlantUML 的对照起点

- 原生匹配：classDiagram / sequenceDiagram / stateDiagram-v2 / erDiagram / gantt / mindmap / C4 系列；
- 语义映射：activity→flowchart、WBS→mindmap、usecase/component/deployment/package/object→flowchart 或 classDiagram 近似；
- 无匹配：timing（xychart 近似不等效）、composite/profile/archimate/ditaa/ebnf/regex——向用户说明。
- 完整对照表见 SKILL.md「PlantUML ↔ Mermaid 图表类型对照」与 howto/01。

## 3. 渲染方式

| 方式 | 用途 |
|------|------|
| 浏览器（mermaid.js CDN） | 网页内嵌 |
| mermaid-cli（mmdc） | 本地渲染 SVG/PNG/PDF（需 Chrome） |
| mermaid.ink 服务器 | URL 即渲染（本技能服务器后端） |
| 编辑器插件（VS Code Markdown Preview Mermaid） | 预览调试 |

## 4. 本技能使用的工具链

- 渲染：`scripts/render-mermaid.sh`（服务器 mermaid.ink + 本地 mmdc 双后端）；
- 量测：`scripts/measure-svg-layout.py`（WBS/甘特版面三判据）；
- 兜底：`scripts/svg-to-png-cjk.cjs`（SVG→PNG，CJK 字体与内容裁剪）；
- 输出：HTML 文档 + PNG/SVG + `.mmd` 源文件。

## 5. 版本注意

- C4 系列原生支持需 v10.9+；
- `kanban`/`block` 实验性（v11.x）；
- gantt `progress` 任务属性 v11.7+；
- 交付时注明所用 Mermaid 版本（本地 mmdc 默认 npx 拉最新）。
