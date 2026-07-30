---
preset_id: process-monitor
name: 过程监控团队
pattern: continuous
summary: 对一个正在进行的过程（需求实现、迁移、发布准备）做只读的周期性监控，每 cycle 产出进度判定、问题清单、遗漏清单与建议。
when_to_use: 有一个跨多天推进的过程需要盯着，希望定期拿到"进度到哪了 / 哪里偏了 / 漏了什么 / 该做什么"，且监控本身绝不能改动被监控对象。
signals:
  - 监控
  - 盯着
  - 跟踪进度
  - 巡检进度
  - 持续观察
  - 只读
  - 定期报告
  - 每天
  - 每小时
  - monitor
  - track progress
  - watch
  - periodic report
  - read-only
  - cadence
inputs:
  - name: target
    required: true
    description: 被监控对象的标识（如 requirement key / 迁移计划路径）；缺省时按序推断活跃对象，推断不出则询问，绝不猜测
  - name: baseline
    required: false
    description: 附加监控基准文档（设计方案、外部计划）；提供时并入证据源
  - name: cadence
    required: false
    description: 监控周期，默认 2h
members:
  - role: team-supervisor
    stage: optimizer
    type: Meta
    lifecycle: persistent
    responsibility: 每 cycle 解析 target 的工件链与状态，判定阶段进度并附证据路径；产出问题/遗漏/建议三清单；维护 STATE.md 与 run-log.jsonl；对被监控对象零写入
  - role: quality-checker
    stage: evaluator
    type: Meta     # 复核对象是 supervisor 结论的证据形态（agent 产出的元属性）→ Meta；若改为直接核查业务工件则为 Worker
    lifecycle: persistent
    responsibility: 作为独立核查者，对 supervisor 的进度判定与 High-Priority 问题做定向复核（L1 不派遣，晋级 L2 后启用）；默认 REJECT 无证据结论
config:
  maturity: L1
  cadence: 2h
  verifier: independent
  max_attempts_per_item: 3
  write_policy: read-only-on-target
  quality_dimensions:
    - name: progress-accuracy
      weight: 0.30
    - name: deviation-detection
      weight: 0.25
    - name: gap-detection
      weight: 0.25
    - name: suggestion-actionability
      weight: 0.20
  threshold: 0.8
  budget:
    max_cycles_per_day: 6
    max_tokens_per_day: 100000
    max_subagents_per_cycle: 0
    on_80pct: report-only
    on_100pct: halt
  kill_switch: loop-pause-all
provenance: 从 .specify/teams/requirement-implement-monitor/ 蒸馏（4 个已记录 cycle 的真实 run 报告；监控任意在实现中的 spec，前身 bh-port-monitor）
---

## Goal Skeleton

对 `<target>` 提供只读的过程监控：跟踪其从起草到收官的整体推进。每 `<cadence>` 一个 cycle 产出四项：
①阶段进度判定（工件链 + 任务勾选/DoD，附证据路径）②问题/偏离清单（约束违反、范围蔓延、工件失同步）
③遗漏项清单 ④可操作建议。成功标准：四项产出齐全；High-Priority 误报率 < 20%（累计复盘）；
本 loop 对监控对象零写入（仅写本团队目录）。

## Static Structure

| Role | Stage | Type | Lifecycle | Responsibility |
|------|-------|------|-----------|----------------|
| team-supervisor | optimizer | Meta | persistent | 进度判定、三清单产出、状态脊维护 |
| quality-checker | evaluator | Meta | persistent | 独立复核（L2+ 启用），无证据结论默认 REJECT |

监控目标**参数化**：团队定义本身不绑定任何具体对象，`target` 由每次 run 的输入决定。

## Dynamic Structure

每个 cycle：

```
1. 读 constraints.md + budget + kill-switch；预算触顶按 on_80pct / on_100pct 降级或中止
2. 解析 target（缺省时推断：会话上下文中的对象 → 存在未完成项的最新对象 → 询问用户）
3. 收集证据：工件链存在性与新鲜度、任务勾选状态、DoD 条目、baseline 对照
4. 判定阶段进度（每条判定必须附证据路径）
5. 产出问题/偏离清单、遗漏清单、可操作建议（指向具体文件与动作）
6. L2+：quality-checker 对 High-Priority 结论独立复核，无证据即 REJECT
7. 写 cycle 报告到 runs/；更新 STATE.md（跨周期状态）与 run-log.jsonl（append-only）
8. Post-Run Critique：记录本轮误报，用于累计误报率统计
```

## Instantiation

1. 确认 `target` 的推断顺序，并在 goal 中写清"团队不绑定具体对象、由 run 输入决定"。
2. 落 `.specify/teams/<slug>/team.md`，frontmatter 加 `preset: process-monitor`。
3. 生成 `constraints.md`（首条即"对监控对象零写入"）、初始 `STATE.md`、空 `run-log.jsonl`。
4. 从 `maturity: L1` 起步；L1 不派遣 subAgent，先积累若干 cycle 的误报率数据再考虑晋级。
5. 明确 cadence 与每日 cycle 上限，避免监控本身消耗超过被监控过程。

## Constraints & Hard Rules

- **对被监控对象零写入**：只写本团队目录（`runs/`、`STATE.md`、`run-log.jsonl`）与 run workspace。任何"顺手修一下"都越界。
- **每条判定必须附证据路径**：无证据的进度结论、无证据的问题结论一律不得进报告。
- **绝不猜测监控目标**：推断不出就询问用户。
- **必须从 L1 起步**，并在 cycle 开始时读 constraints + budget + kill-switch。
- **状态脊是跨周期唯一记忆**：cycle 之间不依赖会话上下文。

## Known Pitfalls

- 把"读到的最新一次改动"当成整体进度——需对照完整工件链与 DoD，而非单点信号。
- High-Priority 误报堆积导致报告被忽视——必须做 Post-Run Critique 并统计误报率。
- 监控目标漂移：run 之间悄悄换了对象却沿用旧 STATE——每 cycle 在报告头部显式声明本轮 target。
- cadence 过密导致预算被监控本身吃掉——先用较宽的周期跑稳再收紧。
