---
name: sdd-project-setup
description: SDD 项目框架调协手册（可独立运行）——把目标项目（本地或远端）以调协模式推进到 spec-kit 框架预期的最佳状态：机制盘点（确定性脚本分级 absent/degraded/partial/complete）、specify CLI 安装（python 解析阶梯 + 三源 pip 回退；Python 全缺绝不自动安装、报错退出）、specify init / instructions 刷新、调协序列（constitution → sanitize → feature → instructions → docs，按需逐项）、强化序列（history → docs → research → feature → goal——会话历史蒸馏补料、深度调研、特性列表生成、定义 3–5 个项目目标）、五族前置检查与兼容符号链接验证，最后产出候选工作清单（未完成 feature / 大改进 feedback / TODO 事项——建议而非强制地供 sdd-loop-driver 等下游选用；两技能互不强依赖）。当用户说「初始化 spec-kit」「项目接入 SDD」「框架就绪检查」「调协项目框架」「sdd-project-setup」，或 sdd-loop-driver 的 preflight 发现目标项目无 .specify/ 或机制退化时加载本手册。
skill_id: "<SKILL:.specify/skills/sdd-project-setup/SKILL.md>"
classification: external
---

> **分类注解**：本 skill 依**依赖轴**判定为 external——自身零 spec-kit 运行时依赖、任何宿主 agent 可直接加载；其内容编排 spec-kit 框架的安装与激活流程（语义耦合在此显式声明），该耦合只体现在它指挥宿主 agent 在目标项目执行 `specify init` / `/speckit.*` 治理命令，不构成本 skill 的运行时依赖。**与 sdd-loop-driver 的关系是软协同而非强绑定**：两技能各自可独立运行；本技能调协完成后**建议**（非强制）下一步可用 sdd-loop-driver 推进开发——handoff 的是一份候选工作清单，是否调用由用户或上游流程决定。

## What This Skill Does

spec-kit 本地 fork（master）在上游 SDD 之上扩充了大量机制——feature 注册表（37/41 真实项目采用）、feedback 库、memory-as-files、glossary、ID register、evidence、probe 体系等。这些机制只有被正确安装、激活、验证后才能兑现价值。本手册把「让一个项目达到 spec-kit 框架预期的最佳状态」固化为**调协模式**五步程序：先盘点定缺口，再按需调协，最终验证；调协完成后产出候选工作清单供下一步 SDD 开发选用（可选 handoff sdd-loop-driver，非强制）。

调协分两层：**基础调协**（机制盘点/安装/修复/验证，S1–S4）让框架就绪；**强化序列**（机制就绪后的增值建设，S3+，按需逐项）用框架内容类命令把项目从「机制可用」推进到「知识与规划在位」——history 蒸馏会话历史为文档与知识库补料、research 深度调研、feature 生成特性列表、goal 定义 3–5 个项目目标。

**幂等契约**：本技能对同一项目可多次执行——每次执行先 S1 盘点定缺口，S2/S3/S3+ 只执行缺口项；**稳定态（机制 complete 且无内容缺口）上的重复执行零结构写动作、零内容重建**，仅刷新 S5 候选清单；CLI 层同样收敛——python 按阶梯选用、`specify` 在位即跳过安装。收敛语义与逐命令重入行为见 setup-recipes.md「幂等与重入语义」。

## When to Load

- 入口话术声明**目标与模式**：目标项目（本地路径，或 ssh 别名+运行用户+项目目录——远端形态参数与 sdd-loop-driver 一致）、模式（`install` 全新安装 / `refresh` 刷新既有 / `verify` 只读核查）、目标 AI 工具（qoder/claude/codex/opencode/hermes/copilot，或 `all`——按脚本惯例一次性为 claude/copilot/opencode/qoder 全部 agent init，默认推荐）。
- 由 sdd-loop-driver 委派时（其 U1 发现 `.specify/` 缺失或宪法不在位）：模式由委派上下文决定——缺失=`install`，退化=`refresh`。

## The Loop (S0–S5)

```text
S0 ENTRY     一遍性入口：目标、模式、目标工具
S1 ASSESS    机制盘点：.specify/scripts/mechanism-inventory.py 扫描 .specify/ → 状态分级
             （absent / partial / degraded / complete）+ 框架版本 provenance
S2 INSTALL   （全部在执行侧=目标项目所在环境运行；编排侧本地宿主无需
             speckit，不误触发安装链——拓扑真源见
             .specify/shared/workflow/execution-topology.md）
             CLI 层（先于项目层）：python 解析阶梯（项目 .venv → PATH 首个 →
             系统最新；全缺报错退出、绝不自动安装 Python）→ specify 缺失则
             clean reinstall + 三源 pip 回退 + specify check 验证 →
             项目层：absent → specify init（推荐 --ai all 一次覆盖全 agent）；
             partial/degraded → /speckit.instructions 刷新（recover 模式）
S3 RECONCILE 基础调协（按 S1 缺口按需逐项，惯常次序）：
             /speckit.constitution → /speckit.sanitize → /speckit.feature →
             /speckit.instructions → /speckit.docs
S3+ STRENGTHEN 强化序列（机制就绪后的增值建设，按需逐项，细则见
             setup-recipes.md）：/speckit.history → /speckit.docs 深化 →
             /speckit.research → /speckit.feature 特性生成 →
             /speckit.goal（定义 3–5 个项目目标）
S4 VERIFY    五族前置检查（SSH/运行用户/CLI/LLM 配置/spec-kit 可用性）+
             机制完备度矩阵复扫 + 兼容符号链接核验 → 全绿才算调协完成
S5 SUGGEST   产出候选工作清单（三个内部来源：未完成 feature / 大规模改进
             feedback / speckit TODO 事项）→ 建议（非强制）下一步可用
             sdd-loop-driver 推进开发
```

**Instruction-chain budget gate**: `/speckit.instructions` 的 `BUDGET` 报告是 S3 的收敛条件之一；超预算处理见 `references/setup-recipes.md` § S3.4（先走 owner 的 R1/R2，仍超则执行 R3 project-filled 章节外迁；无法收敛列 pending）。

## Hard Requirements

1. **盘点先于处置**：S2/S3 的任何动作之前必须先跑 S1 脚本盘点——禁止凭印象判定项目状态（archive-not-delete；本仓 fleet 实测中 4/41 为退化安装、2/41 缺特性注册表，肉眼不可判）。
2. **就绪是三态判定而非二态**：`.specify/` 存在 ≠ 就绪；S4 三条件（五族前置检查全 ok + 机制矩阵达 complete 或缺口已声明 + 符号链接完好）同时成立才判调协完成。
3. **调协按需、不整建**：S3 只执行 S1 判定缺失的项，每项一个治理命令，命中即停；不存在的机制不预建（tools/register 等低频机制按项目需要，缺≠错）。
4. **声明式缺口**：S3 调协的每一项在产出中登记（执行/已存在/跳过+理由）；未被处理的项必须出现在「未处理清单」——静默省略视为违规。
5. **建议而非强制**：S5 的候选工作清单是提示（有哪些可做的事），不携带任何「必须调用 sdd-loop-driver」的语义；调用与否由用户或上游流程决定。
6. **幂等收敛**：S2/S3/S3+ 的每一动作 MUST 幂等——同一稳定态上重复执行不产生新的写动作；每项动作执行前 MUST 以本次 S1 盘点结果为缺口凭据，禁止凭上次执行的记忆跳过或重做（幂等与重入语义见 setup-recipes.md）。
7. **运行时与 CLI 就绪先于 init**：S2 执行 specify init 前 MUST 完成 S2 的 CLI 层——python 解析阶梯三级全缺 → **报错退出，绝不自动安装 Python**；CLI 安装链三源全败 → 报告缺口并停止；两者都不得静默跳过 init 或手工伪造 `.specify/`。
8. **指令体积预算收敛**：S3 的 `/speckit.instructions` 之后 MUST 读取生成器的 `BUDGET` 报告；`over` 时 MUST 先走 owner 的 R1/R2，仍超且存在可迁移 project-filled 章节时 MUST 按 `references/setup-recipes.md` § S3.4 执行 R3 回退；未回到预算内且无可迁移章节时 MUST 作为 pending 上报（上调预算/拆分章节），不得静默转述告警或删除项目内容。

## Discipline Defaults

- 直接执行不要确认；访谈式问题自行裁决并记录假设（产出附「假设与裁决」节）。
- 远端形态时既有脏文件不提交不还原（与 sdd-loop-driver 同一纪律）。
- 本技能**不做任何 SDD 阶段推进**（requirements 等开发阶段归 sdd-loop-driver）；调协与强化的 /speckit.* 调用仅限治理与建设类（constitution/sanitize/feature/instructions/docs/history/research/goal）。
- 不 push（除非入口显式授权）。

## References

- `.specify/shared/workflow/execution-topology.md` — 执行拓扑真源：编排侧/执行侧两侧角色划分、speckit 安装归属（只在执行侧）、本地退化形态、误读反模式清单。
- `references/setup-recipes.md` — 五步执行细则：机制矩阵维度定义、状态分级判据、CLI 安装链（python 解析阶梯 / 三源 pip 回退 / specify check 验证）、init/refresh 命令形态（本地与远端，含 `--ai all` 全 agent 一次性 init）、S3 调协序列触发条件、五族前置检查引用（权威落点 run-agent dispatch-preflight.md）、符号链接核验、S5 候选工作清单 schema 与三个内部来源、与 sdd-loop-driver 的软协同契约。

## Subagent Delegation（子代理委派说明——2026-10-16 裁定）

本手册是**编排者**：调协动作的执行主体按需委派承接技能（可选形态——本技能独立运行时不强制）：

- **盘点与验证的执行**：`.specify/scripts/mechanism-inventory.py` 由编排者直接运行（只读脚本，无需子代理）；远端盘点经 `ssh + su` 形态执行（占位约定同 `.specify/shared/workflow/external-dispatch-recipes.md`）。
- **S2/S3 治理命令的派发**：`specify init` / `/speckit.*` 治理命令如需以子代理承载，经 **run-agent**（`.specify/skills/internal/run-agent/SKILL.md`）以拓扑声明派发——前置检查与失败处置链随其 `references/dispatch-preflight.md`；独立运行时编排者亦可亲自执行治理命令（等价路径）。
- **职责切分线**：框架调协（install/reconcile/strengthen/verify/候选清单）= 本技能；SDD 完整阶段循环 = sdd-loop-driver；创建/派发/修正 = create-agent / run-agent / improve-agent（见 `.specify/shared/definitions/agent-definitions.md` § Driving Subagents via the Three Layers）。

## Boundary

- 目标项目已是 complete 且 verify 模式：出候选清单即止，不做任何写动作。
- sdd-loop-driver 的 SDD 循环、阶段派发、状态脊、收尾纪律不在本技能范围——那是另一个可独立运行技能的职责；S5 只是建议，不强制调用。
- 执行侧（目标项目所在环境）未安装 `specify` CLI：S2 CLI 层在该环境自动安装（python 解析阶梯 + 三源 pip 回退；**Python 三级全缺则报错退出，绝不自动安装 Python**）。安装失败且目标项目已有 .specify/：允许走 /speckit.instructions 恢复路径；两者都缺时报告缺口并停止。
- 编排侧（本地宿主 agent）**不需要 speckit 框架**：技能与子代理通常运行在不同环境——技能驱动 ssh 登录远端开发机启动子代理执行 /speckit.* 命令；python 解析 / CLI 安装 / specify init 只发生在执行侧，编排侧缺 specify 不构成缺口、不得误触发安装链（拓扑真源见 `.specify/shared/workflow/execution-topology.md`）。
- 本手册不绑定特定项目族：路径、别名、用户、工具名全部入口参数化。

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:sdd-project-setup" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:sdd-project-setup" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:sdd-project-setup" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
