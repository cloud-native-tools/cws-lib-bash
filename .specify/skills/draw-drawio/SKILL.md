---
name: draw-drawio
description: |
  Realization engine for draw.io / mxGraph: turns an already-decided diagram semantics into an uncompressed `.drawio` (mxGraph XML) artifact, and can export it to SVG/PNG/PDF through the draw.io Desktop CLI.
  Axis position (a one-line statement only; the values and their justifications are owned by skills/draw-diagram/references/routing-matrix.md §0, which is the authority if the two ever differ): no dynamic-chart capability / free-form layout / weak semantics and weak drawing constraints. Rendering locality (axis ②) is deliberately NOT asserted here: it is being re-decided in a separate flow, and §0 registers no axis-② value yet.
  Trigger on engine-identity terms only — never on generic diagram-class vocabulary; diagram-class intent and engine selection belong to the front door (skills/draw-diagram/SKILL.md).
  Use when the user mentions "drawio", "draw.io", ".drawio", "mxgraph", "mxGraphModel", "mxGraph XML".
skill_id: "<SKILL:.specify/skills/draw-drawio/SKILL.md>"
---

# draw-drawio

## Goal

把**已经定好的**图表语义兑现为 draw.io / mxGraph 产物（`.drawio`，未压缩 mxGraph XML），并按需导出 SVG/PNG/PDF。本技能是 draw.io / mxGraph 的**实现层**：产物格式、XML 结构、渲染与导出。它不做语义判断、不选图类、不选引擎。

## Ownership Boundary（只给指针，不复写）

本技能 MUST NOT 内联任何语义层内容。「这张图该表达什么、该是什么结构、该长什么样、该由哪个引擎画」一律回下列 owner：

| 问题 | Owner（打开它；不要从这里复制） |
|------|--------------------------------|
| 语义模型（实体、层级、结构、关联；SDS/LDM schema） | `skills/draw-diagram/references/semantic-model.md`（**现存**） |
| **引擎选择**——含本引擎与他引擎的取舍、`drawio` ↔ `excalidraw` 可判优先序、独占登记、tie-break、反路由红线 | `skills/draw-diagram/references/routing-matrix.md`（**现存**：§0 能力轴层 / §1 独占 / §2 图类矩阵 / §3 tie-break / §4 红线） |
| 语义分析、图类选择、版面规划、样式配色、内容措辞、类专属约定 | 前门 `skills/draw-diagram/SKILL.md`（**现存**）。这些问题的**专章参考文件**（`references/howto/*`、`references/guide/*`、`references/document/*`）由 stage S1d 规划、**尚未落盘**——今日该 `references/` 树下只有上两行那两个文件。故此处**不预建具体路径**；在专章落盘前一律回前门 `SKILL.md`，不在本技能内自答 |

> **本技能不含任何路由叙事。** 「何时该选我而不选别的引擎」属引擎选择策略，owner 是 `routing-matrix.md`。绕开前门直接调用本技能不在其职责范围内。

## SDS 实现与强弱落地

本技能是绘图技能族的**语法层**：只拥有 draw.io / mxGraph 引擎语法（XML 结构、样式串）、SDS 实现与渲染导出。语义层——逻辑模型、geometry（canvas/box/anchor）、`weight_plan` 档位、typography 层级——归 draw-diagram，schema 见 [../draw-diagram/references/semantic-model.md](../draw-diagram/references/semantic-model.md)，此处不复述。

**输入契约**：draw-diagram 委派传入 **SDS 文件路径**。**MUST NOT 改写语义**——不增删元素/关系、不挪 box、不改档位次序；兑不了（如 label 装不进 box）→ 量化回报，不擅自修。无 SDS 的直接调用属越界（见上「不含路由叙事」），如仍被执行则 MUST 显式声明自规划的假设。

**强弱实现**（tier → `strokeWidth`；相对线宽语义与档位定义 owner = `semantic-model.md`，此处只落实绝对值。`strokeWidth` 缺省为 `1`）：

| 档位（语义角色） | strokeWidth | 落实要点 |
|------|------|------|
| T1 大模块/分区边界 | 3 | 实线；分区用容器（`swimlane`，见 `./references/mxgraph-format.md` §5） |
| T2 小模块/组件边界 | 2 | 实线 |
| T3 数据流/关系箭头 | 1.5 | edge 的 `strokeWidth`；若某渲染路径不接受小数宽度，钳位为 2 并把 T2>T3 的层级转移到**深浅通道**（`strokeColor` 更浅），与 draw-excalidraw 同法 |
| T4 注释/副标题 | 1 | 独立 text 形状或细线 |

- zone 边界虚实：`dashed=1`（缺省 `0` = 实线）；仅当 `style_intent` 要求手绘观感时才用 `sketch=1`——**手绘美学是 draw-excalidraw 的独占**，本引擎默认不启用。
- 关键路径仅色相抬升，线宽封顶 = T2；typography 落实（`fontSize`，缺省 `12`）：zone/图标题 18 > 元素标签 12 > 注释 10。
- **颜色取值不在本文件**：`fillColor` / `strokeColor` / `fontColor` 的**具体色值**是配色决策，owner 是前门的样式指引（尚未落盘）；本技能只负责把档位差落实为可辨的粗细与深浅。

**几何**：mxGraph 是**绝对坐标**引擎（`semantic-model.md` Deviation Declaration 第 1 类）→ **MUST 精确兑现 SDS box**（`x/y/width/height`、zone box、relation anchor+gap 照抄），容器内子元素按 SDS box 换算为**相对父容器**坐标。**预期零偏离**，不适用「逼近声明」豁免；未声明偏离按 semantic-fidelity 扣分。

> **与布局 pass 的硬冲突（MUST 遵守）**：SDS 给了几何就**不得开启会移动 vertex 的 pass**——`postLayout=elk` / `applyLayouts` / CLI `--layout` 都会重排节点位置，一旦启用即等于**推翻 SDS box**，属改写语义。`routing=libavoid` 可用（官方明确「Vertices stay exactly where you placed them」，只整理走线、不动版面）。仅当 SDS **未给几何**、且前门显式授权由引擎排版时，才可启用重布局 pass，并在回报中声明「版面由 pass 生成、非 SDS 兑现」。详见 `./references/render-and-export.md` §3。

**细节**：XML 结构与样式串语法 → [./references/mxgraph-format.md](./references/mxgraph-format.md)；渲染、导出与布局 pass → [./references/render-and-export.md](./references/render-and-export.md)。

> **与其它五家的一处形差（如实记录）**：五个既有引擎各有独立的 `references/sds-realization.md` 承载几何映射表与复刻覆盖规则；本技能暂无该文件，SDS 落地细则全部内联于本节 + 上述两份 references。若本节继续增长，再按 `improve-skills` 拆出同名文件与套件对齐。

## 本技能自有内容

只有两份引擎知识参考，不多不少：

- [`./references/mxgraph-format.md`](./references/mxgraph-format.md) — 产物格式与必备 XML 结构：两种可接受形态、两根结构 cell、`parent` 规则、`mxGeometry as="geometry"`、vertex/edge 属性、标签与元数据载体、样式串语法、最小骨架、生成硬性规则与自检清单。
- [`./references/render-and-export.md`](./references/render-and-export.md) — 渲染与导出：CLI 导出命令与 `--layout` 开关、查看/嵌入路径、**布局与走线的事实**（默认内建 router 无避障；布局 pass 为可选）、分平台二进制定位。

两份都只承载实现细节，不得复写语义层指引。

## 生成契约（摘要 — 详见 `./references/mxgraph-format.md`）

1. **形态二选一**：完整形 `mxfile > diagram > mxGraphModel > root`，或**简化形**只给 `mxGraphModel`（draw.io 打开时自动补齐外层；官方推荐 AI 生成用简化形，需多页时才用完整形）。
2. **两根结构 cell 必备**：`<mxCell id="0"/>`（根容器，无 parent）与 `<mxCell id="1" parent="0"/>`（默认图层）。
3. **vertex 与 edge 都必须带 `parent`**（通常为 `"1"`，或所属 group/layer 的 id）。只有 `id="0"` 可以没有 parent。
4. `vertex="1"` 与 `edge="1"` **互斥**；`id` 在同一 diagram 内唯一，任意字符串皆可。
5. `mxGeometry` 必须带 **`as="geometry"`** 才被识别为该 cell 的几何。
6. **一律未压缩 XML**：绝不生成 `compressed="true"`，绝不生成 Base64/deflate 负载。
7. **绝不输出 XML 注释** `<!-- -->`：官方明令禁止（浪费 token、可能引发解析错误、对图形无语义）。
8. 样式是 cell 上的**字符串属性** `style`，`key=value` 以 `;` 连接，可含裸 token（形状名 / 样式类名）。
9. 标签走 `value`；自定义元数据走 `UserObject` / `object` 的 `label`（此时**嵌套的 mxCell 不带自己的 id**）。
10. edge 只需 `source` / `target`，**不需要手写路径点**；走线由引擎计算。
11. **非矩形形状必须配匹配的 `perimeter=`**（否则连接点计算错位）。已确证的取值只有两个：`rectanglePerimeter`（默认）与 `ellipsePerimeter`（配 `ellipse`）；其余取值目录 owner 是官方 `style-reference.md` §6，本技能不复制、也不按命名长相推断。

> **验证状态（必读）**：以上 11 条**全部来自官方文档**（XSD + 三份官方参考），并已在一份生成产物上通过官方 XSD 校验与 `./references/mxgraph-format.md` §8 自检清单；但本机无 draw.io 环境，**尚未经一次真实导出验证**。详见 `./references/mxgraph-format.md` §9。

## 渲染与导出（摘要 — 详见 `./references/render-and-export.md`）

- **CLI 导出**：`drawio -x -f svg|png|pdf -o <out> <in>`；无图形环境的 Linux 以 `xvfb-run -a` 包裹。这是官方文档确证的既有成熟路径；**本机尚未实测**，且 drawio-desktop 官方 README 无 CLI 章节，故完整开关表仍属未决项。
- **`--layout` 开关**：可在创建后跑一次布局 pass，取值为预设名（`verticalFlow` / `horizontalFlow` / `verticalTree` / `horizontalTree` / `radialTree` / `organic`）或自定义 layout JSON 数组。
- **几何事实**：`.drawio` 格式自身**不做任何布局计算**——vertex 必须携带显式 `x/y/width/height`。但布局与走线 pass 是**可选叠加**的：默认内建 router 很基础（直线或简单直角，**无避障**，连线会直接穿过中间的形状）。
- **三个 pass 的调用面尚未确证**：`routing=libavoid` / `postLayout=elk` / `applyLayouts` 在官方文档中是 **MCP server `create_diagram` 的参数名**；其在 Desktop CLI 上的等价开关**只确证了 `--layout`**。首次真实出图前不得把这三者当作 CLI 开关直接调用——详见 `./references/render-and-export.md` §4 未决项 9。

> **轴②「渲染位置」不在本技能内声明。** 渲染方式（本地 / 远端 / 共享渲染服务）正在另一条流程中重新裁定；本文件与其 references 只登记**引擎能力事实**，不声明本套件采用哪条渲染路径。选路判据的 owner 是 `skills/draw-diagram/references/routing-matrix.md` §0。

## 交付形态（Delivery）

规则 owner = [../draw-diagram/references/delivery-contract.md](../draw-diagram/references/delivery-contract.md)（D1–D6，七技能统一）。本节只写 **draw.io 侧的机械落地**，不复写规则。

**同目录三件套**（缺 HTML 即不合格）：

| 产物 | 说明 |
|------|------|
| `<name>.drawio` | **源文件**，未压缩 mxGraph XML；保留以供未来在 draw.io 中继续编辑 |
| `<name>.svg`（+ 按需 `.png` / `.pdf`） | 经 CLI 导出的**渲染图**，与 HTML 同目录 |
| `<name>.html` | **用户直接双击打开的入口**，相对路径引用同目录的图 |

- **HTML 由 Agent 组装**（本技能不带脚本）：页面主体是 `<img src="<name>.svg">`（相对路径，MUST NOT 写绝对路径），离线可看；`<html lang>` 与页面文字语言跟用户一致。
- **复现性附录**：可折叠 `<details>` 块内放 `.drawio` 源码 + 实际用的导出命令；附录源码 MUST 与磁盘上那份 `.drawio` **逐字节一致**（直接从磁盘复制，不凭记忆重写）。
- **文字规则在本引擎的落点**：图内标签走 `mxCell` 的 `value=`，HTML 说明文字走页面正文——**两者都**受契约 D3–D5 约束（条文与示例见契约，本节不复写）。
- **未导出成功的兜底**：若本机无 draw.io CLI 导致无法导出图片，MUST 如实说明「只交付了 `.drawio` 源文件与一个引用它的 HTML，图需在 draw.io 中打开」，**不得**假装已交付可直接查看的图。

## 参考文档（外部权威源）

本技能不复写 draw.io 的样式目录与形状库——它们的 owner 是官方文档：

- 生成与校验总纲：https://www.drawio.com/docs/reference/diagram-generation/
- 样式与形状完整参考（官方，供 AI 生成用）：https://github.com/jgraph/drawio-mcp/blob/main/shared/style-reference.md
- 规范 XML 生成参考（官方 MCP 各 prompt 的唯一真源）：https://github.com/jgraph/drawio-mcp/blob/main/shared/xml-reference.md
- 结构校验 XSD：https://github.com/jgraph/drawio-mcp/blob/main/shared/mxfile.xsd

## Self-Improvement Contract

- Canonical owner: `skills/draw-drawio/`（镜像 `.specify/skills/draw-drawio/` 由 sync-mirrors 生成，不手改）
- Own-run observation: 每次生成产物的结构自检结果（§自检清单逐项）、导出是否成功、被前门再委派/退回的次数、用户评价单条目
- Mutation route: `improve-skills`（XML 结构错、样式 key 误用、导出命令失效、未决项被新证据消解，均走此路由修订本技能）
- Validation route: 结构类修订用官方 XSD 与 §自检清单校验一份真实产物；纪律类修订按 create-skills 压力测试法 RED-GREEN
- Comparison signal: 同类请求的"产物一次校验通过率 ↑、导出失败次数 ↓、前门退回次数 ↓"
- Escalation boundary: 语义错配与图类误判不归本技能——回 `skills/draw-diagram`（前门）的反馈单元；渲染路径选型（轴②）不归本技能——归另一条渲染流程

## Evaluation Form(绘制评价单)

**定位与边界。** 本节是交付 draw.io / mxGraph 产物后的 Evaluation Form(绘制评价单)，承载用户对本次已交付绘图结果的评价；它不是 `## Feedback`，也不替代或改变该节的 agent 自省。`## Feedback` 保持其既有的「不向用户征询」规则，本节只处理用户主动给出的绘制评价。

**触发与一次性征询。** 仅在本技能已交付 draw.io / mxGraph 产物及必要使用说明后，随该次交付附上一句非阻塞征询：`已交付 draw.io 图；如愿意，请评价它是否准确、清晰且适合用途，或说明希望调整之处。` 不得等待回复、重复询问或因沉默降低交付结果。

**无评价。** 用户没有给出评价即视为本次绘制满意；不创建评价条目、不调用反馈引擎，也不在后续回合追问。

**有评价。** 用户一旦主动给出评价，保留其原意，将 review 内容标为 `## Evaluation Form`，并从评价中提取至少一条评价要点；随后以本节的 probe 记录（不是以 `wrap-up` probe 记录）：

```bash
python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
  --unit-id "skill:draw-drawio" --unit-type skill \
  --lifecycle-point evaluation-form \
  --run-id "<drawing-run-id>:evaluation-form" --feature "<feature-key-if-any>" \
  --review-file "<evaluation-form-review-file>" \
  --points-file "<evaluation-form-points-file>"
```

这会经 `skill-draw-drawio-evaluation-form` probe 把评价条目写入 `.specify/memory/feedback/`。不得把本节记录与同次运行的 `## Feedback` 自省共用 `run_id`，也不得把用户评价改写为 agent 自评。

**处置、回用与传递边界。** 该条目进入既有的 `record→threshold→package→manual→mark-submitted` 链路，并由既有 feedback 处置流程持续标记为 `processed` 或 `ignored`；`processed` 时在 `disposition_reason` 中保留可执行结论。后续执行本技能前，查询本技能已处置的评价单并将适用结论用于 draw.io 绘制与交付验收：

```bash
python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action list \
  --unit-id "skill:draw-drawio" --disposition processed --contains "Evaluation Form"
```

本节绝不自动发送任何内容。若记录结果的既有 threshold 机制要求提示，只能按既有协议给出一次非阻塞的手动打包/提交提示；本节自身的评价征询始终只有交付时的一次。

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:draw-drawio" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
