---
name: draw-diagram
description: |
  Unified front door for every diagram request: builds a semantic logical-diagram model (elements, relations, zones, layout/style/artifact/fidelity intent) and delegates rendering to the single best-fit draw-* specialist (d3js / drawio / echarts / excalidraw / mermaid / plantuml) via the routing matrix and exclusivity registry. This skill renders nothing itself.
  统一绘图前门:先语义建模,再委派给最合适的 draw-* 专项技能;本技能不渲染。
  Use when the user mentions "画图", "绘图", "画个图", "出图", "draw a diagram", "diagram", "图表",
  "架构图", "拓扑图", "流程图", "时序图", "状态图", "类图", "ER图", "甘特", "WBS", "思维导图", "线框图",
  "数据可视化", "复刻图", "图片重绘", or asks to draw/replicate any diagram without naming a specific engine.
skill_id: "<SKILL:.specify/skills/draw-diagram/SKILL.md>"
---

# 统一绘图前门（draw-diagram）

语义建模在先、引擎选择在后：把任何绘图请求转换为逻辑图模型（LDM），再委派给唯一最合适的
draw-* 专项技能渲染。**本技能不渲染任何图**，也不维护任何引擎细节。

## Goal

- 用户只面对一个绘图入口；引擎差异由路由矩阵吸收
- draw-* 下层技能各自强调**独特能力**（独占图种、产物形态），不再追求全面性
- 委派产物可对照 LDM 验收（元素/关系/分组/产物形态覆盖）

## Delegation Contract

本技能不维护任何下层细节：语法、渲染脚本、scene/schema、skinparam、坑位全部归各 draw-*
技能自有（command names、options、return shapes come from the delegated skill）。
前门只持有：语义建模、路由（含独占登记）、委派、覆盖验收。两层各自编辑、互不复制。

**例外——共享渲染后端（环境特定）**：六引擎共用的渲染服务（`xuanji-render.aliyun-inc.com:9696-9701`）
是**跨引擎共享基础设施**，不属于任何单一 draw-* 下层，因此其**可用性 preflight 与自部署回退**由前门统一持有
（见 Step 2.5 + [./references/self-deploy-render-service.md](./references/self-deploy-render-service.md)）。
前门仍**不渲染**——它只在委派前确认后端可达、不可达时按既定流程提示/中断/可选自部署；各引擎的渲染请求语法仍归下层自有。

## Workflow

### Step 1:  intake 与语义建模

1. 吃透上下文（文档/代码/目标图）：先产出**带出处的上下文摘要**（组件、关系、分区、核心流程），LDM 只从摘要与用户意图构建，**不臆造元素**
2. 构建 LDM（schema 与覆盖检查定义见 [./references/semantic-model.md](./references/semantic-model.md)）：
   `diagram_class / elements / relations / zones / layout_intent / style_intent / weight_plan / artifact_intent / fidelity_intent / interactivity_intent / editability_intent`；
   含多层结构的图**必须填 `weight_plan`**（语义视觉强弱：大模块边界 > 小模块边界 > 数据流；前门决定「什么该更显眼」，引擎决定「怎么画粗」）
3. 产出**几何层**（语义决策，语法层实现）：canvas 尺寸、每图元 `box{x,y,w,h}`、分区盒与布局语义（equal-height/stack/grid/free）、关系锚点与间隙；复刻类从源图测量（像素或比例），新建类先规划网格再落坐标（schema 见 semantic-model.md Geometry）
4. 复刻类请求（给了现有图/文档要求重画）：`fidelity_intent=reproduction`——保留源结构与版面语义（含源图实测的每角色线宽，覆盖默认档位），不得"顺手优化"布局

### Step 2: 路由

1. **独占登记优先**（有些图只有一家能画）：[./references/routing-matrix.md](./references/routing-matrix.md) §1 命中即定引擎，不再比较
2. 否则按 §2 图类矩阵取默认引擎，再按 §3 tie-break（artifact_intent）切换
3. 仍歧义 → 一轮 `AskUserQuestion`（≤4 问）附推荐项；不得静默猜
4. **Preflight**：选定引擎的技能目录存在（canonical `skills/<engine>/` 或已安装镜像）；缺失即响亮失败并列出可用引擎，不得即兴自渲染

### Step 2.5: 共享渲染后端 preflight 与自部署回退（环境特定）

> **⚠️ 环境特定信息**：六个引擎共用一个自部署的多引擎渲染服务，消费方契约名为 `xuanji-render.aliyun-inc.com`
> （一引擎一专用端口 **9696-9701**：plantuml 9696 / mermaid 9697 / excalidraw 9698 / drawio 9699 /
> echarts 9700 / d3 9701，**无网关 / 无聚合 / 无代理**）。**并非所有执行环境都能访问 `xuanji-render.aliyun-inc.com`**——
> 它依赖该执行环境的内网 DNS / `/etc/hosts` 映射与 docker 主机。完整契约 + 自部署步骤见附件
> [./references/self-deploy-render-service.md](./references/self-deploy-render-service.md)。**委派引擎渲染（Step 3）前先过此 preflight**：

1. **探测可用性**：`curl -sf --max-time 5 http://xuanji-render.aliyun-inc.com:9697/healthz`（任一 Node 引擎端口的 `/healthz` 即代表后端可用）。
   **可用** → 一切按既定流程执行，进入 Step 3 委派，**不做任何部署动作**。
2. **不可用**（DNS 不解析 / 超时 / 非 200）→ **提示用户并中断**本次渲染委派；**不得**静默降级、**不得**即兴用本地工具（mermaid-cli / plantuml.jar 等）自渲染绕过。提示须说明：该地址是环境特定、当前不可达、本次无法走既定渲染后端。
3. 该提示的**末尾**必须附一个选项：**「要不要考虑自部署?」**
4. 用户选择自部署 → 按 [self-deploy-render-service.md](./references/self-deploy-render-service.md) **先分析当时的运行环境**（docker / podman / k8s / 裸机进程能力 + registry/镜像工厂可达性），据此**选择部署形态**：**docker 容器化为最优默认**，但**不假定 docker 一定可用**——按环境给出可选备选（podman rootless / Kubernetes / 裸机 systemd 进程）连同推荐项**交用户拍板**；选定后给出**具体要执行的步骤**，并在执行前**再次向用户确认是否执行自部署操作**，确认后才动手。
5. 自部署完成后 → 把 `xuanji-render.aliyun-inc.com → 自部署服务 IP` 的映射写入**执行环境**的 `/etc/hosts`；此后再次执行绘图时**直接从第 1 步 preflight 命中可用后端开始，不再重复部署步骤**。

### Step 3: 委派

- 以 Skill 调用委派选定 draw-* 技能，传入 LDM + 目标/输出要求 + **交付契约**（[./references/delivery-contract.md](./references/delivery-contract.md)：HTML 包装、源文件与图片保留、面向用户的文字规则）；尽量 file-path-only handoff。**`weight_plan` 随 LDM 一并传递**，由被委派技能按其「强弱实现」小节落地（各引擎线宽/边框语法归下层自有）
- 前门不渲染、不手改引擎产物、不改引擎源码（score = f(target) 纪律在下层各自生效）

### Step 4: 验收与回报

1. 对照 LDM 做覆盖检查：元素与标签、关系集合（含方向）、分组边界、产物形态、**强弱层级（weight_plan 在产物中可辨：边框按档递减、流线最细、关键路径仅色相抬升）**
2. **对照交付契约做验收**（[./references/delivery-contract.md](./references/delivery-contract.md) 的 D6 自检表，逐项核对）：D1/D2 交付形态在盘、D3–D5 面向用户的文字规则成立（图内文字与 HTML 正文同规）。**条文与示例只在契约里，本节不复写**；任一项不过 = 不覆盖
3. 不覆盖 → 带 delta 说明再委派一次（上限 1 次）；仍不覆盖 → 如实回报产物与缺口
4. 回报：产物路径（HTML + 源文件 + 图片）、选定引擎 + 路由理由（命中独占/矩阵行/tie-break）、LDM 摘要

## 逐级披露（Progressive Disclosure —— 五层）

一次绘图请求按下面五层推进；**每层只读它需要的那一层**，不越层取内容、不把下层内容上抄。

| 层 | 承载面 | 这一层做什么 |
|----|--------|-------------|
| **L1** | `skills/draw-diagram/SKILL.md`（本文件） | 分析语义逻辑，构建 LDM 与几何层，产出**整体逻辑图表设计**（Step 1） |
| **L2** | `skills/draw-diagram/references/*.md` | 选型与判据分析：路由矩阵 / 独占登记 / tie-break / 能力轴（Step 2）、LDM schema 与覆盖检查、**交付契约**（交付形态 + 面向用户的文字规则） |
| **L3** | 委派动作本身 | 选定后以 Skill 调用委派对应 `skills/draw-*` 引擎，传 SDS 路径 + `weight_plan` + 交付契约（Step 3） |
| **L4** | `skills/draw-*/SKILL.md` | 针对**自身图表类型**做引擎侧逻辑设计：「SDS 实现与强弱落地」小节把语义档位落实为本引擎的绝对线宽/字号，并声明几何兑现义务 |
| **L5** | `skills/draw-*/references/*.md` | 各层面完善并输出最终图表：语法/格式、渲染与导出、引擎指南与坑位 |

**当前落地状态（如实记录，不粉饰）**：

- L1、L3 已就位；L2 今日有 `routing-matrix.md`（选型判据）、`semantic-model.md`（LDM/SDS schema 与覆盖检查）、`delivery-contract.md`（交付形态与文字规则）三个文件——**选型、建模、交付三条判据链齐全**，但语义分析 / 图类选择 / 版面规划 / 样式配色 / 内容措辞 / 类专属约定的**专章尚未从下层上移**。
- 这些专章目前仍**分散存放在 `draw-mermaid`、`draw-plantuml`、`draw-excalidraw` 的 `references/{howto,guide,document}/` 内**。实测口径（勿凭文件名判定重复）：跨 specialist **同名的 47 个 `.md` 文件，无一内容相同，全部已分化**——例如 `12-gantt-diagram.md` 在 mermaid 是 73 行、在 plantuml 是 1708 行，`layout.md` 是 69 行 vs 471 行，`content.md` 是 61 行 vs 345 行。所以它们**不是可直接去重的副本，而是同一主题的两份引擎专属实现**；其中确有一部分是引擎无关的语义内核（如 GRASP 原则、建模方法论），但**须逐文件 diff 才能分离**，不得按文件名批量搬移或合并。
- 该分离与上移是已知的**结构重构**待办（原估 14 新文件 + 2 合并，须按上述实测口径重估），未在本轮执行；在其完成前，L2 的选型/建模/交付三条判据链不受影响（三个文件自足），但语义专章须到上述下层目录就地查阅，**不得据同名文件各自演化**（One Source Of Truth 风险已登记）。

## Document Map

| 问题 | 读哪里 |
|------|--------|
| 独占登记 / 图类矩阵 / tie-break | [./references/routing-matrix.md](./references/routing-matrix.md) |
| LDM schema 与覆盖检查 | [./references/semantic-model.md](./references/semantic-model.md) |
| **交付形态**（HTML 包装、源文件与渲染图保留）**与面向用户的文字规则** | [./references/delivery-contract.md](./references/delivery-contract.md) |
| 共享渲染后端可用性 preflight / 自部署（**环境特定**：xuanji-render.aliyun-inc.com:9696-9701） | [./references/self-deploy-render-service.md](./references/self-deploy-render-service.md) |
| 语义视觉强弱（weight_plan 档位与验收） | [./references/semantic-model.md](./references/semantic-model.md) `weight_plan`；引擎落地见各 draw-* 「强弱实现」小节 |
| 引擎语法、渲染、坑位 | 被委派 draw-* 技能自有 SKILL.md 与 references |
| 路由证据（竞技场结论） | `${SKILL_WORKDIR}/.specify/memory/knowledge/visualization-skill-selection.md` |

## Boundary with Lower Layers

- 公共部分（intake 摘要纪律、语义建模、路由、验收）只在本技能维护一份
- 下层 draw-* 的 description 与正文强调独特能力与独占图种；"什么请求该用我"由前门路由回答
- 新增引擎时：先补 routing-matrix 独占/矩阵行，再建下层技能

## Self-Improvement Contract

- Canonical owner: `skills/draw-diagram/`（镜像 `.specify/skills/draw-diagram/` 由 sync-mirrors 生成，不手改）
- Own-run observation: 每次委派的路由命中（独占/矩阵/tie-break/问用户）、验收覆盖结果、再委派次数
- Mutation route: `improve-skills`（路由错配、矩阵缺口、LDM 字段不足均走此路由修订本技能）
- Validation route: 路由判定用 arena 账本历史案例回放；纪律类修订按 create-skills 压力测试法 RED-GREEN
- Comparison signal: 同类请求的"问用户次数 ↓、再委派次数 ↓、验收一次通过率 ↑"
- Escalation boundary: 引擎渲染缺陷不归本技能——记入对应 draw-* 的反馈单元

## Evaluation Form(绘制评价单)

**定位与边界。** 本节是交付结果后的 Evaluation Form(绘制评价单)，专门承载用户对本次**已交付的委派结果**的评价；它不是 `## Feedback`，也不替代或改变该节的 agent 自省。`## Feedback` 保持其既有的「不向用户征询」规则，本节只处理用户主动给出的绘制评价。

**触发与一次性征询。** 仅在 Step 4 已验收并回报委派引擎实际交付的产物路径、路由理由和 LDM 摘要之后，随该次交付附上一句非阻塞征询：`已交付委派结果；如愿意，请评价这张结果是否准确、清晰且适合用途，或说明希望调整之处。` 不得在路由、委派开始或中间结果时征询；不得等待回复、重复询问或因沉默降低交付结果。

**无评价。** 用户没有给出评价即视为本次绘制满意；不创建评价条目、不调用反馈引擎，也不在后续回合追问。

**有评价。** 用户一旦主动给出评价，保留其原意，将 review 内容标为 `## Evaluation Form`，并从评价中提取至少一条评价要点；随后以本节的 probe 记录（不是以 `wrap-up` probe 记录）：

```bash
python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
  --unit-id "skill:draw-diagram" --unit-type skill \
  --lifecycle-point evaluation-form \
  --run-id "<drawing-run-id>:evaluation-form" --feature "<feature-key-if-any>" \
  --review-file "<evaluation-form-review-file>" \
  --points-file "<evaluation-form-points-file>"
```

这会经 `skill-draw-diagram-evaluation-form` probe 把评价条目写入 `.specify/memory/feedback/`。不得把本节记录与同次运行的 `## Feedback` 自省共用 `run_id`，也不得把用户评价改写为 agent 自评。

**处置、回用与传递边界。** 该条目进入既有的 `record→threshold→package→manual→mark-submitted` 链路，并由既有 feedback 处置流程持续标记为 `processed` 或 `ignored`；`processed` 时在 `disposition_reason` 中保留可执行结论。后续执行本技能前，查询本技能已处置的评价单并将适用结论用于语义建模、路由或验收：

```bash
python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action list \
  --unit-id "skill:draw-diagram" --disposition processed --contains "Evaluation Form"
```

本节绝不自动发送任何内容。若记录结果的既有 threshold 机制要求提示，只能按既有协议给出一次非阻塞的手动打包/提交提示；本节自身的评价征询始终只有交付时的一次。

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:draw-diagram" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
