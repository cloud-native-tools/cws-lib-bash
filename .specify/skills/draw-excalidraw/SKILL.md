---
name: draw-excalidraw
description: |
  Draw hand-drawn-style diagrams with Excalidraw scene JSON, render to SVG/PNG via a self-hosted Excalidraw render service, and output as HTML with rendered images.
  Excalidraw 是手绘风格（白板风）绘图：架构图、流程图、拓扑图、思维导图、时序示意、ER 图等自由画布图表；标准流程图/时序图/类图也可走 Mermaid 桥接自动布局。
  Use when the user mentions "excalidraw", "手绘风格图", "手绘图", "手绘风", "白板图", "白板", "手绘架构图", "手绘流程图", "sketch style diagram", "hand-drawn diagram", "whiteboard diagram",
  "画个手绘风格的", "用 excalidraw 画", "excalidraw 场景", ".excalidraw 文件", "mermaid 转手绘", "mermaid 转 excalidraw", "生成 excalidraw", "excalidraw 渲染", "excalidraw 出图"
skill_id: "<SKILL:.specify/skills/draw-excalidraw/SKILL.md>"
---

# 手绘风格图表绘制技能（Excalidraw）

使用 Excalidraw 场景 JSON（`.excalidraw` 明文格式）绘制手绘风格图表，通过**自部署的 Excalidraw 渲染服务**渲染为 SVG/PNG，并输出为包含渲染图表和说明文字的完整 HTML 文档。与 draw-plantuml 同构：源文件 → 远端渲染服务 → SVG/PNG → HTML。

## 核心原则

- **绝对坐标 = 几何实现**：Excalidraw 没有自动布局引擎，场景 JSON 坐标即最终坐标。谁在哪、多大、谁和谁同区由 **SDS geometry**（draw-diagram 产出）决定；本技能按 SDS box **零偏离**落实，仅在无 SDS 的直接调用时才自规划网格（fallback，宁可稀疏不可拥挤）
- **两条生成路径，按图选型**：标准结构图（流程图/时序/类/ER/状态）优先走 **Mermaid 桥接**（布局自动、成功率最高）；自由布局图（架构图/拓扑/脑图/版面自定义）走**场景 JSON 直出**。**带 SDS geometry 委派时必须直出**——桥接自动布局兑不了 SDS 坐标
- **远端渲染优先**：默认只使用渲染服务（`render-excalidraw.sh` 默认 `EXCALIDRAW_BACKEND=server`）；服务不可用时必须先询问用户（修正 `EXCALIDRAW_SERVER` 地址，或经确认后以 `EXCALIDRAW_BACKEND=local` 本机临时起服务），**未获用户确认不得静默切换**
- **渲染后必回看**：读取渲染出的 PNG 与用户要求比对（重叠/错位/溢出/漏元素），发现问题改场景 JSON 重渲——坐标是算出来的，必须用眼睛验收
- **手绘美学（风格默认，复刻时被覆盖）**：`style_intent=hand-drawn`（或直接调用无声明）时 `roughness: 1`、Excalidraw 标准色板、容器圆角、箭头微弯；复刻场景触发**复刻覆盖**（`roughness: 0`、直角、crisp），见 [sds-realization.md §4](references/sds-realization.md)

## SDS 实现与强弱落地

本技能是绘图技能族的**语法层**：只拥有 Excalidraw 引擎语法（场景 JSON）、SDS 实现、渲染质量实践与偏离逼近。语义层——逻辑模型、geometry（canvas/box/anchor）、weight_plan 档位、typography 层级——归 draw-diagram，schema 见 [../draw-diagram/references/semantic-model.md](../draw-diagram/references/semantic-model.md)，此处不复述。

**输入契约**：draw-diagram 委派传入 **SDS 文件路径**。**MUST NOT 改写语义**——不增删元素/关系、不挪 box、不改档位次序；兑不了（如 label 装不进 box）→ 量化回报，不擅自修。无 SDS 的直接调用按 [sds-realization.md §5](references/sds-realization.md) 兜底自规划并声明假设。

**强弱实现**（tier → 绝对 `strokeWidth`；相对线宽语义见 owner）：

| 档位（语义角色） | strokeWidth | 落实要点 |
|------|------|------|
| T1 大模块/分区边界 | 3 | solid，最深笔画色 |
| T2 小模块/组件边界 | 2 | solid |
| T3 数据流/关系箭头 | 1.5→2 | Excalidraw 最小可读笔画钳位；T2>T3 层级转移到深浅通道——流线用更浅颜色 |
| T4 注释/副标题 | 1 | 独立 text / 细线 |

- zone 边界：`strokeStyle: "dashed"` + `roughness: 0`（crisp 复刻）；`roughness: 1` 仅当 `style_intent=hand-drawn`
- 关键路径仅色相抬升，线宽封顶 = T2；typography 落实：zone/图标题 28 > 元素标签 20 > 注释 16

**几何**：场景 JSON 是**绝对坐标**引擎 → **MUST 精确兑现 SDS box**（x/y/w/h、zone box、relation anchor+gap 照抄），容器绑定文本按 SDS box 居中（复刻场景写精确居中坐标——渲染器不自动重居中）。**预期零偏离**，不适用"逼近声明"豁免；未声明偏离按 semantic-fidelity 扣分。

**细节**：几何映射表、场景 JSON 约定（containerId/箭头绑定/seed/scale 钉住）、映射理由、复刻覆盖规则、无 SDS 兜底 → [references/sds-realization.md](references/sds-realization.md)

## 工作流

按以下 7 个步骤顺序执行：

### Step 1: 语义解析 + 吃透上下文（直接调用时）

draw-diagram 委派时语义与几何以 **SDS 为准**——本步仅核对 SDS 与输出要求，**不重建语义**。直接调用（无 SDS）时：分析用户输入理解绘制意图；必要时用 `AskUserQuestion` 确认（最多一轮 ≤4 问）。面对文档/代码等丰富上下文，先产出带出处的上下文摘要（组件、关系、核心流程），后续绘图对着它，不臆造。

→ [00-semantic-analysis.md](references/howto/00-semantic-analysis.md)

### Step 2: 选图类型 + 选生成路径

从图表类型决定生成路径：

| 场景 | 路径 | 依据 |
|------|------|------|
| 流程图、时序图、类图、ER 图、状态图、甘特 | **Mermaid 桥接** | 官方转换器自动布局+文本绑定，LLM 写 Mermaid 成功率高 |
| 架构图、拓扑图、思维导图、分区/分层示意、任何需要自定义版面的图 | **场景 JSON 直出** | Mermaid 表达不了自由版面 |
| **带 SDS geometry 的委派** | **场景 JSON 直出**（强制） | 桥接自动布局兑不了 SDS 坐标 |

→ [01-path-selection.md](references/howto/01-path-selection.md)

### Step 3: 实现 SDS 几何（场景 JSON 路径必做）

版面语义由 SDS geometry 决定，本步只**实现给定盒子**：SDS box → 元素 `x/y/w/h` 1:1、zone box → 垫底矩形/frame、relation anchor → 箭头绑定与折点路由；文本宽度估算只用于校验 label 装得进 SDS box（装不下 → 量化回报，不擅自改盒）。无 SDS 的直接调用按兜底网格法自规划并声明假设。

→ [sds-realization.md](references/sds-realization.md)

### Step 4: 生成场景 JSON / Mermaid 代码

场景 JSON 路径：按元素规范写 `.excalidraw` 文件——先容器后文本再箭头；文本优先用**容器绑定**（`containerId`，渲染服务会自动按真实字体度量重算尺寸并居中）；箭头写全两端 binding。Mermaid 路径：写标准 Mermaid 语法即可。

→ [03-scene-json-generation.md](references/howto/03-scene-json-generation.md)、[scene-schema-reference.md](references/guide/scene-schema-reference.md)

### Step 5: 渲染

用 [render-excalidraw.sh](scripts/render-excalidraw.sh) 渲染，同时产出 PNG 与 SVG（默认远端：`EXCALIDRAW_BACKEND=server` + `EXCALIDRAW_SERVER`；服务不可达时脚本给出指引，须先询问用户）。Mermaid 桥接路径先把 Mermaid 转成场景（`/mermaid-to-scene`）存为 `.excalidraw`，再走同一渲染脚本——保证两条路径交付物一致且源文件可编辑。

→ [04-rendering-and-output.md](references/howto/04-rendering-and-output.md)

### Step 6: 回看比对与微调

读取渲染 PNG 检查：元素齐全？文本溢出容器？箭头穿元素？布局失衡？weight_plan 层级可辨（边框按档递减、流线最细浅）？微调只修**渲染缺陷**（溢出/穿越/重叠/错位），不得挪动 SDS box 与语义；缺陷根源在 SDS 本身（如 box 装不下 label）→ 量化回报语义层/用户。Mermaid 路径不满意版面时，可转为场景 JSON 路径手动微调（转换结果就是可编辑场景）。

### Step 7: 组装 HTML 输出

按输出要求组装 HTML（渲染图为主体，场景 JSON 源码放可折叠「复现性附录」）。HTML 由 Agent 组装，渲染脚本只产 PNG/SVG。

→ [04-rendering-and-output.md §HTML 组装](references/howto/04-rendering-and-output.md)

## 输出要求

- **交付契约（必读；规则 owner 在前门）**：[../draw-diagram/references/delivery-contract.md](../draw-diagram/references/delivery-contract.md) —— D1/D2 交付形态、D3–D5 面向用户的文字规则（**图内标签与 HTML 正文同规**）、D6 交付前自检。**条文与示例只存在于契约，本节不复写。**以下各条是本引擎的**机械落地**，与契约冲突时以契约为准。
- 输出为单个 HTML 文档：渲染图为主体；原始场景 JSON 不嵌入正文，仅放入可折叠「复现性附录」`<details>` 块（默认收起），附录内容必须与磁盘实际渲染的 `.excalidraw` 逐字节一致
- 图表通过 [render-excalidraw.sh](scripts/render-excalidraw.sh) 渲染，同时产出 PNG 与 SVG
- **默认优先选用 PNG** 引用/嵌入图片；仅当图表过大需无损缩放时用 SVG
- **嵌入 Markdown 文档时**：PNG 与 SVG 引用须用同一机制——首选全内联 HTML（`<a href=x.svg target=_blank rel=noopener><img src=x.png></a>`），渲染器剥 HTML 时回退全纯 Markdown
- PNG/SVG 与 HTML 同目录，HTML 相对路径引用图片
- `.excalidraw` 源文件必须保存（用户可直接拖入 excalidraw.com 或自部署白板继续编辑）
- 每张图至少包含标题、渲染图片和简要说明

## 渲染服务部署

渲染服务（[scripts/server/](scripts/server/)）是本技能的配套后端，部署方式（本机 Node 直跑 / Docker / 远端服务器）与 API 详见 [server-deployment.md](references/guide/server-deployment.md)。首次使用且服务未部署时，先读该文档与用户确认部署方式。

## 参考文档

完整索引见 [references/index.md](references/index.md)。SDS 实现（几何映射、强弱落地、复刻覆盖、无 SDS 兜底）见 [references/sds-realization.md](references/sds-realization.md)。

**实战沉淀（务必阅读）**：[best-practices/best-practices.md](best-practices/best-practices.md)（最佳实践）与 [best-practices/pitfalls.md](best-practices/pitfalls.md)（陷阱）——绘制前对照最佳实践，绘制后自查陷阱清单。

## Evaluation Form(绘制评价单)

**定位与边界。** 本节是交付 Excalidraw 产物后的 Evaluation Form(绘制评价单)，承载用户对本次已交付绘图结果的评价；它不是 `## Feedback`，也不替代或改变该节的 agent 自省。`## Feedback` 保持其既有的「不向用户征询」规则，本节只处理用户主动给出的绘制评价。

**触发与一次性征询。** 仅在本技能已交付 Excalidraw 产物及必要使用说明后，随该次交付附上一句非阻塞征询：`已交付 Excalidraw 图；如愿意，请评价它是否准确、清晰且适合用途，或说明希望调整之处。` 不得等待回复、重复询问或因沉默降低交付结果。

**无评价。** 用户没有给出评价即视为本次绘制满意；不创建评价条目、不调用反馈引擎，也不在后续回合追问。

**有评价。** 用户一旦主动给出评价，保留其原意，将 review 内容标为 `## Evaluation Form`，并从评价中提取至少一条评价要点；随后以本节的 probe 记录（不是以 `wrap-up` probe 记录）：

```bash
python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
  --unit-id "skill:draw-excalidraw" --unit-type skill \
  --lifecycle-point evaluation-form \
  --run-id "<drawing-run-id>:evaluation-form" --feature "<feature-key-if-any>" \
  --review-file "<evaluation-form-review-file>" \
  --points-file "<evaluation-form-points-file>"
```

这会经 `skill-draw-excalidraw-evaluation-form` probe 把评价条目写入 `.specify/memory/feedback/`。不得把本节记录与同次运行的 `## Feedback` 自省共用 `run_id`，也不得把用户评价改写为 agent 自评。

**处置、回用与传递边界。** 该条目进入既有的 `record→threshold→package→manual→mark-submitted` 链路，并由既有 feedback 处置流程持续标记为 `processed` 或 `ignored`；`processed` 时在 `disposition_reason` 中保留可执行结论。后续执行本技能前，查询本技能已处置的评价单并将适用结论用于 Excalidraw 绘制与交付验收：

```bash
python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action list \
  --unit-id "skill:draw-excalidraw" --disposition processed --contains "Evaluation Form"
```

本节绝不自动发送任何内容。若记录结果的既有 threshold 机制要求提示，只能按既有协议给出一次非阻塞的手动打包/提交提示；本节自身的评价征询始终只有交付时的一次。

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:draw-excalidraw" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
