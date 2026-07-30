# Better Harness — 改进机制的目标锚点 (Improvement North Star)

Spec Kit 全部改进机制共同服务的目标的**单一事实源**：feedback 机制（`workflow/feedback-step.md`）、证据层（`workflow/evidence-step.md` + `collect-evidence`）、`create-*` / `improve-*` 技能族、memory / history / review，各自解决不同环节的问题，但都指向同一件事——**让项目成为对 AI agent 更好的执行环境（a better harness）**。各流程只引用本文件，不复制定义；修订本文件即修订全部消费者的目标表述。

> 理念来源：概念体系改编自开源项目 **Better Harness**（Harness 定义、Feedforward/Feedback 回路、Agent Work Loop 五维模型、证据状态纪律）。Spec Kit 早已隐式采用其证据纪律（七态 evidenceState、"配置≠使用"红线）；本文件将隐式目标显式化。

## Harness 是什么，"Better" 是什么

**Harness（执行环境）**：包裹任务的环境，使 agent 能够完成一个**有界、可恢复的工作循环**：

```text
理解上下文 → 做出有界修改 → 选择正确的验证 → 解读失败 → 修复 →
重新验证 → 知道剩余风险是否需要人工评审
```

**Better**：让 agent 的工作变得 **repeatable（可重复）、verifiable（可验证）、recoverable（可恢复）、auditable（可审计）**。好的 harness 不等于"文档多、CI 文件多"——只有当这些工件连接到可执行的反馈和机械化的护栏时才算数。

**术语消歧（重要）**：feedback 红线中"never the LLM, the agent CLI/harness"的 *harness* 指 **host（agent CLI 运行时**，如 Claude Code / Qoder CLI**）**；本文件的 *Harness* 指**项目层的执行环境资产**——Spec Kit 装入项目的 `.specify/` 工件层（宪法、规格、命令、技能、脚本、记忆）正是这一层的组成部分。两者不可混用：改进目标针对后者，feedback 红线保护前者不被越界评价。

## Feedforward 与 Feedback 回路

一个健康的 harness 同时具备行动**前**的引导与行动**后**的传感：

| 回路侧 | 含义 | Spec Kit 中的对应资产 |
|--------|------|----------------------|
| **Feedforward guides**（前馈引导） | agent 行动前就位的目标、边界与路径 | constitution、specs / plans / tasks、instructions（AGENTS.md）、glossary、skills / agents / teams / tools 定义、checklists |
| **Feedback sensors**（反馈传感） | agent 行动后观察结果、帮助自我纠正的信号 | tests / verification.log、`/speckit.analyze`、`/speckit.review`、feedback entries、evidence 泳道（session / project / assets / runs / feedback） |

改进工作应问：**摩擦发生在前馈缺失，还是反馈缺失？** 前者补引导资产，后者补传感信号。

## Agent Work Loop 五维目标模型 → Spec Kit 机制映射

评估与改进 harness 时，按交付的五个相连环节定位问题与改进项：

| 维度 | 它回答的问题 | Spec Kit 中的支撑机制 |
|------|-------------|----------------------|
| **Task Understanding**（任务理解） | agent 是否知道目标和"完成"的含义？ | constitution、`/speckit.requirements` / `clarify`、feature index、glossary、instructions |
| **Controlled Execution**（可控执行） | 工作是否在受支持、可重复的路径上？ | `/speckit.plan` / `tasks` / `implement`、skills、tools 定义（行为规则）、scripts、teams 编排 |
| **Change Validation**（改动验证） | 是否有证据证明变更确实有效？ | Test-First（原则 IV）、`/speckit.checklist`、`/speckit.analyze`、verification.log |
| **Reliable Delivery**（可靠交付） | 速度是否绕过了质量检查或验收？ | workflow gates（原则 VII）、`/speckit.review`、git-workflow 技能、Pre-Status-Flip Gate |
| **Learning Capture**（经验沉淀） | 下一个任务是否从本次受益？ | memory（session / knowledge）、history、**feedback 机制**、`improve-*` 技能族 |

**消费方式**：改进单元在描述"这次改进强化了什么"时，引用维度名而非另造分类；跨维度的系统性问题属于 `/speckit.review` 的全局视角。

## 证据纪律（改进断言的红线）

改进断言必须诚实于证据边界——这是本目标模型自带的纪律，与 `workflow/evidence-step.md` 的红线同源：

1. **配置 ≠ 使用**：配置好的资产（一个技能、一条规则、一个 hook）最多证明**机制存在**（`Present` / `Wired`）；只有关联到实际任务的证据才能证明它**被使用**（`Exercised`）或**改善了结果**（`Outcome-supported`）。
2. **七态 evidenceState 不可重定义**：`Present / Wired / Exercised / Outcome-supported / Missing / Unobserved / Not applicable`（定义见 `.specify/skills/collect-evidence/references/evidence-discipline.md`）。
3. **Unobserved 红线**：未观察 ≠ 不存在，也 ≠ 存在；只可记录，禁止当缺陷修、禁止推断为结论。
4. **"已改进"须有前后对比**：通过一次当前检查只证明干预被执行过；只有可比的后续结果才能证明循环变好了（对应 `evidence-step.md` Step E 的 `intervention.json` + `--action compare` 机制）。

## 改进轨道（从证据选择策略）

按目标资产的现状选择改进策略，三条轨道对应 Spec Kit 的既有工具：

| 轨道 | 适用情形 | Spec Kit 中的执行者 |
|------|---------|-------------------|
| **Bootstrap（0 → 1）** | 基础的导航、验证或风险路径缺失 | `create-skills` / `create-agent` / `create-team` / `create-tools`、`/speckit.constitution` / `instructions` |
| **Operationalize（1 → 60）** | 机制存在但未接入日常工作（`Present`/`Wired` 而从未 `Exercised`） | 修触发词 / 路由 / 嵌入约定（feedback-step、evidence-step 的嵌入规范）、`improve-*` 的"配而未用"候选处理 |
| **Optimize（60 → 100）** | 机制在用，且有 ≥2 次可比运行证据支撑定向优化 | `improve-skills` / `improve-agent` / `improve-team` / `improve-tools` 的证据驱动定向修改 |

轨道选择发生在证据分拣（evidence-step Step B）**之后**：先看证据说资产处于什么状态，再选轨道，不得反过来"想建什么就说缺什么"。

## 边界（本文件不做什么）

- **只加方向，不加机制**：本目标锚点不引入评分系统、成熟度报告、新记录引擎或运行时评估平台——Spec Kit 是文档/提示框架（宪法原则 IX），Better Harness 在这里是**目标取向**，不是新增 runtime。
- **不改变 feedback 红线**：feedback 的 target 仍然是 Spec Kit 框架本身，仍然是用户数据、零自动传输（`workflow/feedback-step.md` § Positioning & Red Lines 不受影响）。
- **不替代各单元的自有流程**：improve-* 的失败模式分类法、结构分析法、Refinement Map 等保持不变；本文件只回答"为什么做、朝哪个维度做"。

## 消费者清单

| 消费者 | 引用方式 |
|--------|---------|
| 宪法原则 XIII（Better-Harness Orientation） | 治理层声明，指向本文件为目标模型的单一事实源 |
| `workflow/feedback-step.md` | Goal anchor 段：feedback 强化 Learning Capture 维度 |
| `workflow/evidence-step.md` | 定位段：证据层是本目标模型的证据规则载体 |
| `improve-skills` / `improve-agent` / `improve-team` / `improve-tools` | `## Goal` 中一句目标锚点声明（各自强化的维度） |
| `/speckit.review` | 全局报告可按五维组织系统性发现（可选） |
