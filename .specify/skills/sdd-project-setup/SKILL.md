---
name: sdd-project-setup
description: SDD 项目框架 bootstrap 手册（可独立运行）——把目标项目（本地或远端）安装或刷新到 `.specify/` 基线：机制盘点（deterministic absent/degraded/partial/complete）、specify CLI 安装（python 解析阶梯 + 三源 pip 回退；Python 全缺绝不自动安装、报错退出）、specify init / instructions 刷新、constitution 与首批内容（feature/docs/goal/agents/team 按需），随后把周期性调协、强化、验证、记录回收与候选清单 handoff 给 sdd-house-keeping。当用户说「初始化 spec-kit」「项目接入 SDD」「框架就绪检查」「调协项目框架」「sdd-project-setup」，或 sdd-loop-driver 的 preflight 发现目标项目无 .specify/ 或机制退化时加载本手册；项目已初始化且本次只需维护时，直接加载 sdd-house-keeping。
skill_id: "<SKILL:.specify/skills/sdd-project-setup/SKILL.md>"
classification: external
---

> **分类注解**：本 skill 依**依赖轴**判定为 external——自身零 spec-kit 运行时依赖、任何宿主 agent 可直接加载；其内容编排 spec-kit 框架的安装与首批内容建设（语义耦合在此显式声明），该耦合只体现在它指挥宿主 agent 在目标项目执行 `specify init` / 少量 `/speckit.*` bootstrap 命令，不构成本 skill 的运行时依赖。**三技能软协同**：本 skill = 一次性 bootstrap（init/refresh + constitution + 首次 feature/docs/goal/agents/team）；`sdd-house-keeping` = bootstrap 之后的周期性调协、强化、验证、记录回收与候选清单；`sdd-loop-driver` = SDD 开发阶段循环。三者各自可独立运行，互不强依赖。

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.

## What This Skill Does

把「让一个项目进入 spec-kit 框架的可用基线」固化为 **bootstrap 程序**：先做确定性盘点定缺口，再安装/刷新，随后完成 constitution 与首批内容，最后把周期性维护 handoff 给 `sdd-house-keeping`。本 skill **不执行**周期性 reconcile/strengthen/verify/report，也不执行任何破坏性清理；这些归 house-keeping 的 H1–H5。

bootstrap 对象是**双层框架**：**物理机制**（`.specify/` 目录/脚本/链接）与**逻辑框架**（instructions / feature / docs 为必选层，goal / agent / team 按需层）。只把目录铺齐而逻辑资产缺位，不算 bootstrap 完成。两层各有确定性盘点：`.specify/scripts/mechanism-inventory.py` 与 `.specify/scripts/logical-framework.py`。

**幂等契约**：本技能对同一项目可多次执行——每次执行先 S1 盘点定缺口，S2/S2.5 只执行缺口项；稳定态（机制 complete 且首批内容在位）上的重复执行零结构写动作、零内容重建；`specify` 在位即跳过安装。收敛语义见 `references/setup-recipes.md`。

## When to Load

- 目标项目尚未初始化，或 `.specify/` 退化、constitution 缺失，需要 install/refresh + 首批内容。
- 由 `sdd-loop-driver` 委派：其 preflight ⑤ 发现 `.specify/` 缺失或宪法不在位（缺失=`install`，退化=`refresh`）。
- **不适用**：目标项目已初始化且只需周期性维护/记录回收 → 直接加载 `sdd-house-keeping`；SDD 开发阶段 → `sdd-loop-driver`。

### S0 入口缺省解析

入口可以只给一句意图（如「初始化 spec-kit」）；目标解析遵循共享契约 `.specify/shared/workflow/target-resolution.md`。**setup 不依赖 `.specify/`**：未给目标 → **当前项目**（git root；非 git 取会话 cwd），显式目标优先，拒绝 basename `.specify`，**不向上搜索 `.specify/`**；目标没有 `.specify/` 时由本 skill 创建/刷新。下表只保留本 skill 自己的 mode/tool 缺省：

| 入口缺省 | 解析规则 |
|----------|----------|
| 模式 | 入口未给 → 按本次 S1 分级：absent=`install`、degraded/partial=`refresh`、complete=`bootstrap-content-check` |
| 目标 AI 工具 | 入口未给 → `all`（一次性为 claude/copilot/opencode/qoder 全部 agent init） |

## The Loop (S0–S2 + HANDOFF)

```text
S0 ENTRY     一遍性入口：目标、模式、目标工具
S1 ASSESS    双盘点：.specify/scripts/mechanism-inventory.py 扫物理机制 → absent/partial/
             degraded/complete + provenance；.specify/scripts/logical-framework.py 扫逻辑
             框架 → required/recommended/conditional 三层判定
S2 INSTALL   （全部在执行侧=目标项目所在环境运行；编排侧本地宿主无需
             speckit，不误触发安装链——拓扑真源见
             .specify/shared/workflow/execution-topology.md）
             CLI 层（先于项目层）：python 解析阶梯（项目 .venv → PATH 首个 →
             系统最新；全缺报错退出、绝不自动安装 Python）→ specify 缺失则
             clean reinstall + 三源 pip 回退 + specify check 验证 →
             项目层：absent → specify init（推荐 --ai all 一次覆盖全 agent）；
             partial/degraded → /speckit.instructions 刷新（recover 模式）
S2.4 MIGRATE （按需）旧版 workspace 收尾：S2 之后、S2.5 之前判定版本混杂态
             （机制盘点 partial/degraded 且 provenance 显示旧版残留，或
             `.specify/source.json` 落后于已安装 CLI）→ MUST 经 `/speckit.migrate`
             先 dry-run 后 apply 完成一次性收敛；干净 workspace → 具名跳过。
             命令流 owner：`.specify/templates/commands/migrate.md` + `docs/reference/commands/migrate.md`
             （本技能只决定调用时机，不复述其步骤与四值退出码）
S2.5 BOOTSTRAP 首批内容（只补缺失项，不做完整维护）：
             /speckit.constitution（缺失时）→ /speckit.feature（注册表缺失时
             种子）→ /speckit.docs（docs 树缺失时）→ /speckit.goal（缺失时定义
             3–5 个目标）→ /speckit.agents / /speckit.team（用户明确需要时）
HANDOFF      调用 sdd-house-keeping H0–H4（同一目标/模式）完成首次维护；
             house-keeping 不可用时返回 bootstrap-complete / maintenance-pending，
             不冒充 ready；候选清单由 house-keeping H5 产出
```

**Dispatch carrier**：未给远程三元组 → **本地**，目标=当前项目，派发 MUST 缺省使用 **fork 承载**（同族 `qodercli` 子进程经 `.specify/skills/sdd-loop-driver/scripts/stage-runner.sh`）；异构 agent MUST 使用 **subprocess 承载**（该 agent 自身 CLI 的独立子进程）；宿主内建 in-process subagent 路径 **BANNED**、MUST NOT 被呈现为一个选项。远程三元组给全 → `ssh <alias>` → `su - <run-user>` → `cd <project-dir>`，经 run-agent 驱动 subagent CLI；CLI 缺省取 execution-config defaults（`cli: qodercli`）。完整判据见 `.specify/shared/workflow/execution-topology.md` § Carrier decision。**SSH 传输 owner 是 `ssh-utils`**：选项、引号、stdin 推送与退出码由其 `.specify/scripts/ssh-exec.py` 承载（固定 `-o RemoteCommand=none`），本技能只声明拓扑形态。

**S2.5 carrier**：本地每个 S2.5 命令按 fork / subprocess 两类进程承载派发（in-process 路径 BANNED）；远端每个 S2.5 命令经 run-agent 在 `<project-dir>` 下执行（`ssh <alias>` → `su - <run-user>` → `cd <project-dir>`），CLI 缺省 qodercli；SSH 传输细则见 `ssh-utils`。

**Instruction-chain budget gate**: S2 的 `/speckit.instructions` 刷新若报告 `BUDGET ... over`，本 skill 不实现 R3；把超预算章节与生成器报告交给 `sdd-house-keeping` H2 的 Budget convergence（owner 细节见其 `maintenance-recipes.md` § Budget）。

**S2.4 migrate gate（按需，不静默跳过）**：调用前先读命令自己的 dry-run 计划并呈现；apply 属破坏性收敛，按目标项目治理（宪法与确认门）取得同意后执行；migrate 的 outcome/退出码四值由命令模板拥有，本 skill 逐字转发、不重判。判定为干净时 MUST 在报告里具名 `migrate: not-required`，MUST NOT 以沉默代替结论。远端目标同规（经 run-agent 在 `<project-dir>` 下执行）。

## Hard Requirements

1. **盘点先于处置**：S2/S2.5 的任何动作之前必须先跑 S1 的**两个**盘点脚本（物理机制 + 逻辑框架）——禁止凭印象判定项目状态。
2. **完成标准是 bootstrap + 首次维护**：`.specify/` 存在 ≠ 就绪；**就绪是三态判定而非二态**——只有 bootstrap 完成**且** house-keeping H4 三条件（五族前置检查全 ok + 物理矩阵 complete 且逻辑矩阵 required 层无未声明缺口 + 符号链接完好）同时成立，才可声明「ready」。house-keeping 不可用时只能返回 `bootstrap-complete / maintenance-pending`，不得冒充 ready。
3. **按缺口 bootstrap、不整建**：S2.5 只执行 S1 判定缺失的项；不存在的机制不预建（tools/register 等低频机制按项目需要，缺≠错）。
4. **声明式缺口**：S2/S2.5 的每一项在产出中登记（执行/已存在/跳过+理由）；未处理项交给 house-keeping H5 的未处理清单——静默省略视为违规。
5. **建议而非强制**：候选工作清单由 house-keeping H5 产出；它是提示，不携带任何「必须调用 sdd-loop-driver」的语义。
6. **幂等收敛**：S2/S2.5 的每一动作 MUST 幂等——同一稳定态上重复执行不产生新的写动作；每项动作执行前 MUST 以本次 S1 盘点结果为缺口凭据，禁止凭上次执行的记忆跳过或重做。
7. **运行时与 CLI 就绪先于 init**：S2 执行 specify init 前 MUST 完成 CLI 层——python 解析阶梯三级全缺 → **报错退出，绝不自动安装 Python**；CLI 安装链三源全败 → 报告缺口并停止；两者都不得静默跳过 init 或手工伪造 `.specify/`。
8. **预算超限交给 house-keeping**：S2 刷新报告的 `BUDGET ... over` 不由 setup 实现 R3；原样交给 house-keeping H2，不得静默转述告警或删除项目内容。
9. **本地 fork 承载**：入口未给环境信息时，目标解析与执行都按本地拓扑；治理命令的派发 MUST 缺省使用 **fork 承载**（同族 `qodercli` 子进程经 `.specify/skills/sdd-loop-driver/scripts/stage-runner.sh`），异构 agent MUST 使用 **subprocess 承载**（该 agent 自身 CLI 的独立子进程）；宿主内建 in-process subagent 路径 **BANNED**，MUST NOT 被呈现为一个选项。
10. **目标项目治理优先（本地与远端同规）**：bootstrap 任何目标项目之前，MUST 先读取目标项目既有的宪法（`.specify/constitution.md`）与指令（`.specify/instructions.md` 及其兼容符号链接），并在全部动作中遵守其原则、目录规范、命名规则与临时目录纪律；MUST NOT 覆盖、绕过或删改这些治理内容。目标项目尚无治理文档时，按框架模板生成（constitution / instructions），MUST NOT 凭空自造规则。
11. **目录创建限于规范落点**：bootstrap 的目录创建 MUST 限于框架既有落点（`specify init` 产物、`.specify/.tmp/`、目标项目治理文档声明的目录）；MUST NOT 在目标仓库内创建 ad-hoc 目录或临时根；临时数据按目标项目纪律（无则框架 `temp-directory-discipline`）落位，并在首次写入前确认 `.gitignore` 覆盖。
12. **Bootstrap 后 handoff**：S2.5 完成后，周期性调协、强化、验证、记录回收与候选清单 MUST handoff 给 `sdd-house-keeping`；本 skill MUST NOT 复制其 H1–H5 执行细则。目标项目已初始化且本次只需维护时，直接加载 `sdd-house-keeping`，不重跑 `specify init`。
13. **无破坏性动作**：本 skill MUST NOT 执行 `/speckit.sanitize`、retention apply 或任何删除/归档；破坏性门归 house-keeping 调用的 sanitize。setup 只做可逆的安装/刷新/内容初始化。
14. **不做 SDD 阶段推进**：本技能不做任何 SDD 阶段推进；requirements → … → review 归 `sdd-loop-driver`；S2.5 只调用 bootstrap 内容类命令（constitution/feature/docs/goal/agents/team）。
15. **远端命令经 ssh-utils 承载**：任何远端执行 MUST 使用 `ssh-utils` 的 `.specify/scripts/ssh-exec.py`（或等价地带 `-o RemoteCommand=none` 的形态）；MUST NOT 手写裸 `ssh <alias> "..."`——目标主机可能在 ssh_config 预置 `RemoteCommand`，与命令行冲突。传输失败先跑 `ssh-exec.py --check` 诊断。

## Discipline Defaults

- Bootstrap 的可逆动作直接执行并附执行报告；访谈式问题自行裁决并记录假设（产出附「假设与裁决」节）。
- **不执行破坏性动作**：sanitize/retention 的破坏性门归 house-keeping；setup 不确认、不绕过、不代执行。
- 远端形态时既有脏文件不提交不还原（与 sdd-loop-driver 同一纪律）。
- 不 push（除非入口显式授权）。

## References

- `.specify/shared/workflow/target-resolution.md` — 三技能共享的目标解析唯一契约（显式目标 > git root > cwd；拒绝 `.specify` 根；不向上搜索）。
- `.specify/shared/workflow/execution-topology.md` — 执行拓扑真源：编排侧/执行侧两侧角色划分、speckit 安装归属（只在执行侧）。
- `.specify/scripts/mechanism-inventory.py` — 物理机制盘点（只读）。
- `.specify/scripts/logical-framework.py` — 逻辑框架盘点（只读；S1 跑一次）。
- `references/setup-recipes.md` — bootstrap 侧执行细则：机制矩阵、逻辑矩阵、S1/S2 命令、S2.5 首批内容、handoff 与幂等语义。
- `ssh-utils`（外部技能） — 远端 SSH 传输 owner：`-o RemoteCommand=none`、引号、stdin 脚本推送、su 包装与退出码；setup 的远端命令一律经其 `.specify/scripts/ssh-exec.py`。
- `sdd-house-keeping`（外部技能） — bootstrap 之后的周期性维护 owner：H1 盘点、H2 调协（含 `/speckit.sanitize --lane retention`）、H3 强化、H4 验证、H5 报告。
- `sdd-loop-driver`（外部技能） — SDD 开发阶段循环 owner；候选清单仅建议。

## Subagent Delegation（子代理委派说明——2026-10-16 裁定）

本手册是**编排者**：bootstrap 动作的执行主体按**执行拓扑**选择承载形态（承接技能可选——本技能独立运行时不强制）：

- **盘点**：`.specify/scripts/mechanism-inventory.py` 与 `.specify/scripts/logical-framework.py` 由编排者直接运行（只读脚本，无需子代理）；远端盘点经 `ssh + su` 形态执行。
- **本地拓扑（默认）**：盘点脚本由编排者直接运行（只读，无需子代理）；`specify init` / bootstrap 内容命令的派发 MUST 用 **fork 承载**（同族 `qodercli` 子进程经 `.specify/skills/sdd-loop-driver/scripts/stage-runner.sh`）或 **subprocess 承载**（异构 agent 自身 CLI 的独立子进程）；宿主内建 in-process subagent 路径 **BANNED**，MUST NOT 被呈现为一个选项。
- **远端拓扑**：bootstrap 命令经 **run-agent**（`.specify/skills/internal/run-agent/SKILL.md`）以拓扑声明派发外部子代理，`ssh + su` 进入执行侧。
- **职责切分线**：bootstrap（install/refresh + 首批内容 + handoff）= 本技能；周期性维护（reconcile/strengthen/verify/report）= `sdd-house-keeping`；SDD 阶段循环 = `sdd-loop-driver`；创建/派发/修正 = create-agent / run-agent / improve-agent。

## Boundary

- 只做 bootstrap：install/refresh + constitution + 首次 feature/docs/goal/agents/team + handoff；**不做**完整 reconcile、强化、验证、记录回收或候选清单。
- 不执行任何破坏性动作；不调用 `/speckit.sanitize`、不调用 retention apply。
- 不推进任何 SDD 开发阶段；bootstrap 内容命令仅限 constitution/feature/docs/goal/agents/team。
- 目标项目已是 complete：仍可执行 S1 检查与 S2.5 缺失项；稳定态零写，随后 handoff 给 house-keeping 做 H1–H5。
- 执行侧未安装 `specify` CLI：S2 CLI 层在该环境自动安装；**Python 三级全缺则报错退出，绝不自动安装 Python**。
- 编排侧（本地宿主 agent）**不需要 speckit 框架**；python 解析 / CLI 安装 / specify init 只发生在执行侧。
- 本手册不绑定特定项目族：路径、别名、用户、工具名全部入口参数化。

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:sdd-project-setup" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:sdd-project-setup" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:sdd-project-setup" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
