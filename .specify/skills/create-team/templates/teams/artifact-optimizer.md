---
preset_id: artifact-optimizer
name: 产物质量锦标赛优化团队
pattern: iteration
summary: 对一个可评分的产物（图表/文档/代码风格）做多变体并行优化 + 加权评分 + 淘汰择优的收敛式迭代团队。
when_to_use: 有一个明确的被优化目标（一份指南/模板/规则）和一个可重复渲染或构建的基准产物，希望通过多轮打分收敛到质量阈值后停止。
signals:
  - 优化
  - 提升质量
  - 打分
  - 评分
  - 迭代
  - 收敛
  - 变体
  - 淘汰
  - 锦标赛
  - 美观
  - optimize
  - improve quality
  - score
  - iterate
  - converge
  - variants
  - tournament
inputs:
  - name: optimization_target
    required: true
    description: 被优化的对象路径（指南/模板/规则集）——迭代真正修改的东西
  - name: benchmark
    required: true
    description: 基准输入；每代由它重新生成被评分的产物
  - name: build_command
    required: true
    description: 从 target + benchmark 生成产物的可重复命令
  - name: quality_dimensions
    required: false
    description: 评分维度与权重（和为 1.0）；缺省由 goal 推导后与用户确认
  - name: threshold
    required: false
    description: 达标阈值，默认 0.85
members:
  - role: team-supervisor
    stage: optimizer
    type: Meta
    lifecycle: temporary
    responsibility: 每代派发变体优化器；收集评分并做精英保留式淘汰选择；判定收敛/继续/回退；维护决策日志
  - role: variant-optimizer
    stage: optimizer
    type: Meta     # 按操作对象判定：optimization_target 为 skill/agent 配置（如 skill 指南）→ Meta；若 target 是纯业务文档 → 改为 Worker
    lifecycle: temporary
    responsibility: 从一个固定角度（angle）提出对 optimization_target 的候选改动；每代 M 个实例并行、角度互不重叠；只改 target，绝不手改被评分产物
  - role: renderer
    stage: executor
    type: Worker
    lifecycle: temporary
    responsibility: 每代重载最新 target，用 build_command 从 benchmark 重新生成候选产物到 run workspace；报告成功/失败
  - role: scorer
    stage: evaluator
    type: Worker   # 评分对象是渲染出的业务产物 → 业务层评估者（Type 按操作对象判定）
    lifecycle: temporary
    responsibility: 按 quality_dimensions 对候选产物加权打分，输出强制格式的 `[DIM]_SCORE` / `WEIGHTED_TOTAL` / `SUGGESTIONS`
config:
  strategy: elimination
  variants: 3
  threshold: 0.85
  max_iterations: 5
  regression_limit: 2
provenance: 从 .specify/teams/draw-plantuml-optimizer/ 蒸馏（5 轮真实 run 报告；优化 skills/draw-plantuml 的绘图指南，基准图 docs/diagrams/05-detailed.puml）
---

## Goal Skeleton

持续提升 `<optimization_target>` 的产出质量。以 `<benchmark>` 为基准输入、`<build_command>` 为可重复生成方式，
令加权评分（`<quality_dimensions>`）达到 ≥ `<threshold>` 即视为本轮达标；最多 `<max_iterations>` 代，
连续 `<regression_limit>` 代无提升则中止。每轮可复现、可复盘，多轮 re-run 累积改进。

## Static Structure

| Role | Stage | Type | Lifecycle | Responsibility |
|------|-------|------|-----------|----------------|
| team-supervisor | optimizer | Meta | temporary | 派发、淘汰择优、收敛判定 |
| variant-optimizer × M | optimizer | Meta | temporary | 每实例一个固定角度的候选改动（角度不重叠） |
| renderer | executor | Worker | temporary | 重载最新 target，从 benchmark 重建候选产物 |
| scorer | evaluator | Worker | temporary | 加权打分，强制输出格式（评分对象是业务产物 → Worker） |

角度（`angle`）按被优化对象的质量结构切分，实例之间必须正交；示例（图表域）：布局向 / 风格向 / 语义分解向。

## Dynamic Structure

每一代：

```
COORDINATE  supervisor 下发本代 M 个 angle + 上代评分反馈
EXECUTE     M 个 variant-optimizer 并行产出候选 target 改动
            → renderer 逐个"重载最新 target + 从 benchmark 重建"产物
EVALUATE    scorer 对每个候选产物加权打分
DECIDE      supervisor 淘汰择优（精英保留）；达标 → 收敛交付并停止
            未达标且未触 max_iterations / regression_limit → 进入下一代
IMPROVE     胜出改动合入 optimization_target，作为下一代的基线
```

## Instantiation

1. 确认 `optimization_target` 与 `benchmark` 是两个不同的东西：target 是被改的，benchmark 是不动的输入。
2. 与用户确认 `quality_dimensions` 及权重（必须和为 1.0），并把它写进 goal——不可评分的 goal 驱动不了循环。
3. 验证 `build_command` 可重复执行且失败可见（渲染/构建失败必须计为 correctness 维度扣分，而不是静默跳过）。
4. 落 `.specify/teams/<slug>/team.md`，frontmatter 加 `preset: artifact-optimizer`；`config` 填 strategy/variants/threshold/max_iterations/regression_limit。
5. 每代候选产物、评分转储一律写 `.specify/teams/.work/<slug>/`；只有最终胜出的 target 改动落真实路径。

## Constraints & Hard Rules

- **优化 target，不优化产物**：迭代必须修改 `optimization_target`，产物每代由 `build_command` 从 benchmark 重新生成。手改被评分产物、最后再批量回灌 target，等于闭环从未闭合。
- **每代重载最新 target**：renderer 不得复用上一代缓存的 target 内容。
- **max_iterations 是硬性上限**，必须显式设置;`regression_limit` 触发即中止而非无限重试。
- **scorer 输出格式强制**：`[DIM]_SCORE` / `WEIGHTED_TOTAL` / `SUGGESTIONS` 缺项即视为该候选无效评分。
- **变体角度正交**：两个 variant-optimizer 提出同类改动时，supervisor 应重切角度而非并行浪费。

## Known Pitfalls

- 把"手改产物"当成优化——最常见且最隐蔽的失效模式（见上方硬规则第一条）。
- 权重和不为 1.0 导致加权总分不可比。
- 构建后端不稳（如远端渲染服务）导致评分噪声——配置自动回退到本地后端，并把失败显式计入正确性维度。
- 阈值定得过高导致每次都跑满 max_iterations：先用一代实测校准 threshold。
