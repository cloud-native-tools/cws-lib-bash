---
preset_id: capability-arena
name: 能力竞技场持续优化团队
pattern: continuous
summary: 对技能/命令/子代理等能力单元做真实运行验证的竞技场:同题竞技或多角度变体探索 → 双轮裁判加权评分 → 对比保留最优 → 改进回流,驱动能力单元持续变强。
when_to_use: 需要验证并持续优化能力单元(技能/命令/子代理)的实际效果——多个同类单元周期性同题竞技定排位,或对单一目标沿正交角度做变体探索收敛最优;而不是凭感觉改、改完不实测。
signals:
  - 竞技场
  - 竞技
  - 打擂
  - 排位
  - 重绘
  - 同题竞技
  - 裁判
  - 评审团
  - 锦标赛
  - 技能验证
  - 命令验证
  - 代理验证
  - 效果验证
  - 实测验证
  - 多角度优化
  - 变体
  - 淘汰
  - 打分
  - 评分
  - 收敛
  - 持续优化
  - arena
  - tournament arena
  - skill arena
  - capability arena
  - rank skills
  - compare skills
  - shootout
  - judge panel
  - redraw
  - real-run
  - variants
  - optimize
  - converge
inputs:
  - name: arena_targets
    required: true
    description: 参赛能力单元清单(≥1,须同类可比——技能 vs 技能、命令 vs 命令、子代理 vs 子代理,如 draw-echarts / draw-d3js);=1 时进入变体模式,沿 variant_angles 生成候选
  - name: task_source
    required: true
    description: 竞技任务来源(题库目录/选题规则/固定 benchmark);每周期由它抽取或轮转同一道题,保证可比
  - name: quality_dimensions
    required: false
    description: 裁判评分维度与权重(和为 1.0);缺省由 goal 推导后与用户确认
  - name: variant_angles
    required: false
    description: 变体模式的正交优化角度清单(如 布局向/风格向/语义分解向);缺省按目标质量结构切分后与用户确认
  - name: redraw_rounds
    required: false
    description: 败方修订轮数,默认 1——末位按裁判意见修订后重出一次,重出分计入档案但不推翻本轮排位
  - name: convergence
    required: false
    description: 收敛休止条件(threshold 达标 / regression_limit 连续无提升);触发即休止交付,机制不空转
  - name: cadence
    required: false
    description: 运营节奏(如每周/每两周一个竞技周期),默认 weekly
members:
  - role: team-supervisor
    stage: optimizer
    type: Meta
    lifecycle: persistent
    responsibility: 每周期选题、声明候选集(竞技/变体)、派发执行与评审、汇总双轮裁判结果定排位、维护跨周期 STATE.md 排位档案与 run-log;判定收敛休止;触发能力改进回流
  - role: arena-dispatcher
    stage: executor
    type: Worker
    lifecycle: temporary
    responsibility: 对每个候选(参赛单元或变体)真实运行同一道题,产物按候选分目录落 run workspace;记录成功/失败,失败视为该候选本周期 correctness 扣分而非弃权
  - role: judge-panel
    stage: evaluator
    type: Worker
    lifecycle: temporary
    responsibility: 双轮裁判——第一轮按 quality_dimensions 独立盲评逐件打分;第二轮交叉对比并处理异议,产出最终排序与逐件意见(供修订与回流);强制输出 [DIM]_SCORE / WEIGHTED_TOTAL / SUGGESTIONS
  - role: variant-designer
    stage: optimizer
    type: Meta
    lifecycle: temporary
    responsibility: 变体模式专属——沿 variant_angles 的正交角度为同一目标生成 M 个候选改动;只改能力单元定义(技能指南/命令模板/代理配置),绝不手改被评分的产物
  - role: capability-improver
    stage: optimizer
    type: Meta
    lifecycle: temporary
    responsibility: 把裁判意见转写为败方/弱项能力单元的具体改进建议(对接 improve-skills / improve-agent / 命令模板修订流程);不直接改能力源文件,改进落真实路径须人批准
config:
  summary:
    enabled: true
    every: 5
    interactive: false
  maturity: L1
  cadence: weekly
  redraw_rounds: 1
  variants: 3
  convergence:
    threshold: 0.85
    regression_limit: 2
provenance: 由 skills-arena(2026-08-07 viz-skill-arena 真实运行,反馈批次 20260807T051529Z)与 artifact-optimizer(draw-plantuml-optimizer 5 轮真实 run 报告)合并泛化——竞技壳(同题/双轮裁判/排位档案/败方修订)+ 变体机制(正交角度/加权评分/精英保留/收敛条件),优化目标从技能推广到技能/命令/子代理一切可真实运行的能力单元。
---

## Goal Skeleton

长期运营一个能力竞技场:`<arena_targets>`(技能/命令/子代理,同类可比)每个周期(`<cadence>`)在来自 `<task_source>` 的同一道题上真实运行竞技;
单一目标时沿 `<variant_angles>` 正交角度生成变体候选同题探索。经双轮裁判按 `<quality_dimensions>` 加权评分定排位;
末位按裁判意见修订 `<redraw_rounds>` 轮;裁判发现回流为能力单元改进建议。排位档案跨周期累积;
`<convergence>` 触发(达标或连续无提升)即休止交付——机制既不因单次结果停止,也不无收益空转。

## Static Structure

| Role | Stage | Type | Lifecycle | Responsibility |
|------|-------|------|-----------|----------------|
| team-supervisor | optimizer | Meta | persistent | 选题、候选集声明、派发、排位裁决、状态脊柱、收敛判定、改进回流触发 |
| arena-dispatcher | executor | Worker | temporary | 逐候选真实运行同题,产物分目录,失败显式记录 |
| judge-panel | evaluator | Worker | temporary | 双轮裁判:独立盲评 → 交叉对比定排序,强制输出格式 |
| variant-designer | optimizer | Meta | temporary | 变体模式:正交角度候选改动,只改单元定义 |
| capability-improver | optimizer | Meta | temporary | 裁判意见 → 能力单元改进建议 + 败方修订 |

两种候选集形态,同一竞技骨架:**竞技模式**(≥2 个同类能力单元同题对比)与**变体模式**(1 个目标 × M 个正交角度候选)。

## Dynamic Structure

每一个周期(cycle):

```
READ      supervisor 读 constraints.md + budget + kill-switch;从 STATE.md 取上期排位与待办改进;检查 convergence 是否已触发
SELECT    从 task_source 抽题(轮转或固定打擂题);声明本周期形态(竞技/变体)与候选集
GENERATE  变体模式:variant-designer 沿正交角度产出 M 个候选单元改动(角度互不重叠)
EXECUTE   arena-dispatcher 逐候选真实运行同一道题 → 产物按候选分目录落 run workspace;失败计 correctness 扣分
JUDGE     judge-panel 第一轮独立盲评逐件打分;第二轮交叉对比、处理异议 → 最终排序 + 逐件意见(强制输出格式)
REVISE    capability-improver 把末位/弱项意见转写为修订;重出 redraw_rounds 轮,重出分入档案(不推翻本轮排位)
DECIDE    supervisor 对比保留最优(精英保留);达标或连续 regression_limit 周期无提升 → 休止并交付结论
REPORT    本周期排位、得分、修订对比、改进建议清单写入 runs/<ts>-report.md;STATE.md 更新排位档案
SUMMARIZE 按 summary 配置触发 goal 总结(每 N 周期)
```

## Instantiation

1. 确认 `arena_targets` 同类可比:技能 vs 技能、命令 vs 命令、子代理 vs 子代理——跨类同题竞技没有裁判基准;=1 时与用户确认 `variant_angles`(角度必须正交)。
2. 与用户确认 `quality_dimensions` 及权重(和为 1.0)——裁判维度不清的竞技场只会产出噪声排位。
3. 确认 `task_source` 可稳定供题;题库枯竭即机制空转,需在 constraints.md 写入补题责任。
4. 落 `.specify/teams/<slug>/team.md`,frontmatter 加 `preset: capability-arena`;`config` 填 cadence/redraw_rounds/variants/convergence;连续团队三件套(constraints.md / STATE.md / run-log.jsonl)初始化。
5. 按 `create-mode.md` schema 写入 `## Self-Improvement Contract`，本团队的运行报告/裁判反馈只作证据，能力单元改动仍路由到对应 `improve-*`。
6. 竞技产物与评分转储一律写 `.specify/teams/.work/<slug>/`;只有排位档案、报告与经批准的单元改进落真实路径。
7. 变体模式下,先以一个周期实测校准 `convergence.threshold`,避免阈值过高每次空转到休止。

## Constraints & Hard Rules

- **同类可比是参赛前提**:每周期所有候选必须是同类能力单元(技能/命令/子代理各自成赛),且执行同一道题;题目不一致或跨类的分数不可比,排位无效。
- **优化单元定义,不优化被评产物**:变体与修订必须落在能力单元的定义上(技能指南/命令模板/代理配置),产物每周期由真实运行重新生成。手改被评分产物、再回灌单元,等于闭环从未闭合。
- **每周期重载最新单元定义**:arena-dispatcher 不得复用上周期缓存的单元内容。
- **双轮裁判不可并省**:只有独立盲评会锚定先入之见;只有交叉对比会漏掉维度间矛盾。两轮都跑。
- **裁判输出格式强制**:`[DIM]_SCORE` / `WEIGHTED_TOTAL` / `SUGGESTIONS` 缺项即视为该候选无效评分;维度权重和必须为 1.0。
- **变体角度正交**:两个候选提出同类改动时,supervisor 应重切角度而非并行浪费。
- **重出不翻案**:重出分只入档案用于趋势观察;本周期排位以正赛为准,否则激励变成"先摆烂后重出"。
- **改进回流须经人批准**:capability-improver 只产出建议与修订草案;能力单元源文件的真实改动走 improve-skills / improve-agent 的正常批准路径,竞技场不直接写能力源文件。
- **失败显式记录**:候选执行失败计 correctness 扣分并公示,不得静默弃权或剔除。
- **convergence 是硬休止**:达标或连续 regression_limit 周期无提升即休止交付,不得无限重试。

## Known Pitfalls

- 裁判维度权重和不为 1.0 → 跨周期排位不可比。
- 题库枯竭后继续"打擂"→ 周期空转、STATE 漂移;补题责任必须写进 constraints。
- 把重出当成第二正赛 → 排位被翻案噪声淹没(见硬规则"重出不翻案")。
- 参赛单元清单长期不变 → 竞技场退化为自嗨;周期性评估是否增补新单元。
- 把"手改产物"当成优化——最常见且最隐蔽的失效模式(见硬规则"优化单元定义")。
- 运行/构建后端不稳(如远端渲染服务)导致评分噪声——配置自动回退到本地后端,并把失败显式计入 correctness 维度。
- 阈值定得过高导致每次都空转到休止上限——先用一个周期实测校准 threshold。
