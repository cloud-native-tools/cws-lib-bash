# Canonical `## Evidence` Step (evidence-step)

所有"证据驱动优化"类消费单元(improve-skills / improve-agent / improve-team 及未来消费者)的标准证据步骤**单一事实源**。各消费单元只引用本文件,不复制定义;修订本文件即修订全部消费者。与 `feedback-step.md`(自省记录)对偶:feedback-step 写反馈,evidence-step 读证据。证据层与其全部消费单元共同服务于宪法原则 XIII 声明的 **Better Harness 目标**——目标模型(五维 Agent Work Loop、前馈/反馈回路、改进轨道)单一事实源见 `.specify/shared/guidelines/better-harness.md`;本文件的红线即该目标模型的证据纪律载体。

## Positioning & Red Lines

1. **证据层对消费者中立**:证据由 `evidence-utils.py` 采集并规范化为 findings.json(合同见 `skills/collect-evidence/references/evidence-contract.md`);证据层不含严重度、修复方案、优先级等观点字段——那些属于消费层。
2. **Unobserved 红线**:`Unobserved` 状态的证据只可记录,**禁止**当作缺陷去修、禁止推断为结论。未观察 ≠ 不存在,也 ≠ 存在。
3. **计数只路由**:资产/会话/运行的计数信号只用于路由检查方向,**不得**直接生成优化点或候选。
4. **候选冻结**:Step B 分拣完成后候选清单即冻结,后续步骤**不得**增删候选——防止"想修什么就把什么说成证据"。
5. **evidenceState 七态语义不可重定义**:`Present / Wired / Exercised / Outcome-supported / Missing / Unobserved / Not applicable`(定义见 `skills/collect-evidence/references/evidence-discipline.md`);消费方只能自定义**响应方式**,不能裁剪或重定义状态语义。

## Canonical block (steps for the embedding unit)

### Step A — 证据采集或复用

```bash
# 复用 7 天内证据(超龄有 warning,不得静默使用超龄证据):
python3 .specify/scripts/python/evidence-utils.py --action latest --target <unit-id>
# 无可复用证据时采集:
python3 .specify/scripts/python/evidence-utils.py --action collect --target <unit-id> --lanes all
```

`<unit-id>` 词汇与 feedback 一致:`skill:<name>`、`/speckit.<cmd>` 或 `project`。采集不可用的泳道以 `unavailable` 显式呈现,消费流程照常进行,不得视为错误。

### Step B — 证据审读与候选分拣(完成后冻结)

按 evidenceState 分拣 findings.json 的证据条目:

| 状态 | 分拣去向 |
|------|---------|
| `Exercised` / `Outcome-supported` 的**负向**证据 | 缺陷候选(可修) |
| `Missing` | 机制缺失候选(可建) |
| `Present` / `Wired` 但从未 `Exercised` | "配而未用"候选(先查路由/触发词,再考虑裁撤) |
| `Unobserved` | 只记录,禁止当缺陷修(红线 2) |
| `Not applicable` | 跳过 |

候选清单在本步结束时**冻结**;计数信号不得直接生成候选(红线 3/4)。

### Step C/D — 根因分析与定向修改(各消费单元自有)

沿用消费单元既有流程(失败模式分类法、结构分析法、Refinement Map 等);最小变更与双镜像纪律不变。

### Step E — 干预台账

每次定向修改后,向基线证据运行目录写 `intervention.json`:

```json
{
  "targetFinding": "<基线 findings 中的证据条目 id>",
  "change": "<定向修改描述(脱敏)>",
  "baselineRunId": "<基线 runId>",
  "expectedSignal": { "signalKey": "<信号键>", "direction": "improve|reduce" }
}
```

下一轮同目标 Step A 之后运行 `--action compare`:预期信号改善 → 干预标 `Outcome-supported`;无可比数据 → 保持 `Unobserved`。**禁止**在缺乏前后证据对比时宣称"已修复"。

## Notes for embedders

- 本步骤插入消费单元的证据输入位置(通常替代原"从历史回忆执行效果"类步骤),不改变该单元的收尾 Feedback 步骤。
- 引用方式:在 SKILL.md 相应步骤写"按 `.specify/shared/workflow/evidence-step.md` 执行 Step A/B(+E)",零复制定义。
- Node 环境缺失时 session/project/assets 三泳道降级,runs/feedback 泳道(纯 Python)仍可用——消费流程按可用泳道进行,边界如实申明。
- `.specify/memory/evidence/` 不进入 feedback 打包(package)范围。
