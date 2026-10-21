# 选择图表类型（01）

## 1. PlantUML ↔ Mermaid 类型对照（本技能核心）

| PlantUML 类型 | Mermaid 对应 | 匹配 | 备注 |
|---------------|-------------|------|------|
| Class | `classDiagram` | ✓ | 6 种关系、namespace、构造型 |
| Sequence | `sequenceDiagram` | ✓ | alt/loop/par、note、activate |
| Activity | `flowchart` | ✓ | 决策菱形 + fork 语义；状态驱动用 stateDiagram-v2 |
| State | `stateDiagram-v2` | ✓ | 初终态、守卫、复合、fork/join |
| Gantt | `gantt` | ✓ | section/依赖/里程碑/完成度 |
| MindMap | `mindmap` | ✓ | 缩进树 |
| WBS | `mindmap` | ≈ | 树形承接；需要左右展开用 flowchart LR |
| ER (entity) | `erDiagram` | ✓ | 乌鸦脚基数 |
| C4 宏 | `C4Context` 等 | ✓ | v10.9+ |
| Use Case | `flowchart` | ≈ | 角色 + 用例椭圆 + 系统边界 subgraph |
| Component | `flowchart` / `C4Component` | ≈ | subgraph 边界 |
| Deployment | `flowchart` / `C4Deployment` | ≈ | 节点 subgraph 分层 |
| Package | `flowchart` / classDiagram namespace | ≈ | 包依赖 / 类组织 |
| Object | classDiagram 实例 | ≈ | 实例 + 关系 |
| JSON | `flowchart` | ≈ | 结构树近似 |
| YAML | `flowchart` | ≈ | 结构树近似 |
| Salt | `flowchart` | ≈ | 界面结构近似 |
| Network (nwdiag) | `flowchart` | ≈ | 子网 subgraph |
| Timing | `xychart-beta` / `timeline` | ✗ | 语义不同，明确告知用户 |
| Composite/Profile/Archimate/Ditaa/EBNF/Regex | — | ✗ | 无匹配，说明替代方案 |

**规则**：优先 ✓（原生），其次 ≈（语义最接近的原生类型），✗ 必须向用户说明「Mermaid 无此类型」并给替代建议——不要静默用 flowchart 硬画。

## 2. 快速匹配表（按用户意图）

| 用户说 | 选 |
|--------|----|
| 系统长什么样、模块怎么分 | flowchart / C4Container |
| 谁调用谁、顺序 | sequenceDiagram |
| 类/对象结构 | classDiagram |
| 业务怎么流转 | flowchart（活动语义） |
| 对象状态变化 | stateDiagram-v2 |
| 数据库表 | erDiagram |
| 项目进度 | gantt |
| 任务分解 | mindmap（WBS） |
| 想法发散 | mindmap |
| 部署在哪、网络拓扑 | flowchart（Deployment 语义） |

## 3. 按开发阶段推荐

| 阶段 | 常用图 |
|------|--------|
| 需求分析 | flowchart（用例近似）、sequenceDiagram（场景） |
| 概要设计 | C4Context / C4Container、flowchart 组件图 |
| 详细设计 | classDiagram、sequenceDiagram、stateDiagram-v2、erDiagram |
| 实现/代码走查 | classDiagram、flowchart |
| 测试设计 | stateDiagram-v2、flowchart（覆盖路径） |
| 交付/汇报 | C4 系列、gantt（进度） |

## 4. 常见组合模式

- **架构图集**：C4Context（总览）→ C4Container（系统拆分）→ C4Component（关键系统下钻）+ sequenceDiagram（关键交互）→ C4Deployment（部署）；
- **业务分析**：flowchart 用例近似（范围）+ flowchart 活动图（流程）+ stateDiagram-v2（订单状态机）；
- **数据设计**：erDiagram（表结构）+ classDiagram（领域模型）。

**需求点名图表集合时**（如「5 类图：组件/部署/时序/状态机/资源分层」）：Step 2 先产出**覆盖清单**（需求点名类型 → 图号 → Mermaid 类型映射），交付前逐项打勾核对——缺图先补再交付，不得以「语义相近的其他图」替代点名类型；图集索引（`▶ 见图N`）与覆盖清单一一对应，便于评审核对。

## 5. Mermaid 独有类型速览（PlantUML 无）

按需选用：`pie`、`quadrantChart`、`requirementDiagram`、`gitGraph`、`journey`、`timeline`、`sankey-beta`、`xychart-beta`、`packet-beta`、`kanban`、`block`。语法见 guide/syntax-reference.md §9。
