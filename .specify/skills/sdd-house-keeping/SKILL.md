---
name: sdd-house-keeping
description: This skill can run periodic house-keeping on a target SDD project, including record-retention cleanup via the target project's /speckit.sanitize. Use this when the user mentions ["sdd-house-keeping", "项目管家", "house keeping", "定期维护", "清理并核对目标项目", "记录回收", "retention cleanup", "sanitize records"].
skill_id: "<SKILL:.specify/skills/sdd-house-keeping/SKILL.md>"
classification: external
---

> **分类注解**：本 skill 依**依赖轴**判定为 external——自身零 spec-kit 运行时依赖，任何宿主 agent 可直接加载；其内容编排目标项目的治理与维护命令（语义耦合在此显式声明），该耦合只体现在它指挥宿主 agent 在目标项目执行 `/speckit.*`，不构成本 skill 的运行时依赖。**与 sdd-project-setup 是软协同**：setup 负责一次性 bootstrap，本 skill 负责 bootstrap 之后的周期性维护；本 skill 不安装/初始化项目，setup 也不依赖本 skill 才能完成 bootstrap。**与 sdd-loop-driver 是软协同**：loop-driver 负责 SDD 开发阶段推进，本 skill 不推进任何阶段。

## What This Skill Does

把一个已经初始化的目标项目维持在框架预期的最佳状态：先做确定性盘点定缺口，再按固定次序调协治理/文档/特性/指令，随后按需强化，最后验证并产出候选工作清单。周期维护的核心增量是**记录消费回收**：调用目标项目的 `/speckit.sanitize --lane retention`，把 exec-quant / feedback / session 原始记录按「消费 → 回执 → 回收」处理；没有回执不删除，open feedback 与 unsettled run-determination 永不回收。

本 skill 不重写任何 owner 的内部流程：sanitize 的七个阶段、docs 的 R0–R6、history 的增量 manifest、feature 的注册表 reconcile、instructions 的 R1/R2、confirmation-gates 的两级判据都由各自 owner 承载。本 skill 只负责**何时、按什么次序、以什么模式**调用它们，并汇总结果。

**三段循环对照**：`sdd-project-setup` = S0–S2 + HANDOFF（bootstrap）；本 skill = H0–H5（周期维护）；`sdd-loop-driver` = U0–U6（SDD 阶段循环）。

## When to Load

- 用户说「项目管家」「house keeping」「定期维护」「清理并核对目标项目」「记录回收」「sdd-house-keeping」。
- `sdd-project-setup` 完成 bootstrap（init/refresh + constitution）后 handoff。
- 目标项目已有 `.specify/`，且用户希望检查框架就绪、清理陈旧资料、回收已消费记录或刷新文档/特性/指令。
- 不适用于：全新项目安装（→ `sdd-project-setup`）、SDD 开发阶段推进（→ `sdd-loop-driver`）。

## The Loop (H0–H5)

```text
H0 ENTRY     解析目标项目、模式、工具；拒绝误解析；记录绝对路径
H1 ASSESS    双盘点（物理机制 + 逻辑框架），只读，产出本次缺口凭据
H2 RECONCILE 按固定次序、只处理缺口：
             /speckit.sanitize（materials；cleanup 模式再跑 retention）
             → /speckit.feature → /speckit.instructions（含预算收敛）
             → /speckit.docs
H3 STRENGTHEN 按依赖次序、按需：
             /speckit.history → /speckit.docs 深化 → /speckit.research
             → /speckit.feature 生成
H4 VERIFY    五族前置检查（本地仅④⑤）+ 双矩阵复扫 + 符号链接 + hook health
H5 REPORT    候选工作清单 + 运行报告（写入宿主工作目录）
```

### H0 — Entry

- **目标项目**：遵循共享契约 `.specify/shared/workflow/target-resolution.md`。**本 skill 强依赖 `.specify/`**：显式目标优先；未给 → 从会话 cwd **向上搜索**最近的合法 `.specify/` 根（显式本地路径则从其向上搜索）；项目根必须包含 `.specify/`（至少含 `.specify/memory/`、`.specify/scripts/`、`.specify/templates/` 之一）；解析为绝对路径；**拒绝 basename 为 `.specify` 的根**；目标是框架源仓且未显式指定时先警告。**找不到 `.specify/` → 拒绝执行**，提示运行 `sdd-project-setup`（install）或 `specify init <project-dir>`，可按需 handoff setup。远端先跑 execution-side target-root probe。
- **模式**：未给 → `check`（只盘点/报告，不执行破坏性回收）；用户明确要求清理 → `cleanup`。
- **命令面**：不假设目标项目的 `/speckit.*` 副本存在；H2 前探测命令副本，缺失时按 `.specify/skills/internal/<name>/SKILL.md` 直接加载 owner 技能，不假设 slash 命令可用。
- 目标项目必须已有 `.specify/` 与 constitution；缺失 → 停止并 handoff `sdd-project-setup`（bootstrap 是 setup 的职责）。

### H1 — Assess

运行两个只读盘点脚本（本 skill 自带）：

```bash
python3 ${SKILL_HOME}/scripts/mechanism-inventory.py --project <project-dir> --json
python3 ${SKILL_HOME}/scripts/logical-framework.py --project <project-dir> --json
```

物理矩阵回答 `.specify/` 装没装，逻辑矩阵回答 instructions/features/docs 必选层与 goal/glossary/register/knowledge 推荐层、agents/teams 条件层配没配。两层都跑完才算 H1 完成；缺口凭据永远是**本次** H1，不是上次运行的记忆。

### H2 — Reconcile

固定次序，执行 **H1 缺口 OR owner 自检报告的漂移**；每项登记 `executed / existing / skipped + reason`。未处理项进入 H5 的未处理清单，静默省略视为违规。H1 只回答“目录/资产在不在”，不替代 owner 的漂移检查（sanitize 残留、feature 注册表漂移、instructions 预算/过期、docs 漂移都由各自 owner 判定）。

**远端 H2/H3 执行形态**：所有 `/speckit.*` 命令在 `<project-dir>` 下、经 run-agent 驱动 subagent CLI 执行——`ssh <alias>` → `su - <run-user>` → `cd <project-dir>`；CLI 缺省 qodercli。本地则由编排者/原生子代理在当前项目执行。

1. `/speckit.sanitize` — `check` 模式同时跑 materials check（`/speckit.sanitize check`）与 retention check（`/speckit.sanitize --lane retention check`），两份摘要一起报告；`cleanup` 模式跑 `/speckit.sanitize --lane all`，一个调用内呈现 materials 与 retention 两个计划，破坏性确认仍由 sanitize 既有门处理，**不新增第二道门**。**本 skill 不直接调用 `sanitize-utils.py apply` 或 `record-retention.py apply`。**
   - 目标项目缺 `record-retention.py`（旧框架）：只跑 materials lane，报告 `retention=not_evaluated — 需升级 spec-kit`，不删除；缺 `sanitize-utils.py`：回交 setup 做刷新。
   - `/speckit.*` 副本缺失时按 `.specify/skills/internal/<name>/SKILL.md` 加载 owner 技能，不假设命令面存在。
2. `/speckit.feature` — 注册表缺失 **或** owner 自检报告与仓库实况漂移时 reconcile。
3. `/speckit.instructions` — compat 链接断、instructions 过期、partial/degraded，**或** 生成器报告 `BUDGET ... over` 时执行；预算收敛的 R3 细则见 `./references/maintenance-recipes.md` § Budget。
4. `/speckit.docs` — docs 树与代码/特性/指令漂移时委托 `create-docs` 收敛（漂移由 docs owner 判定，不由 H1 代替）。

constitution 缺失不在本步 bootstrap；交回 `sdd-project-setup`。

### H3 — Strengthen

按依赖次序、按需逐项；已就绪且无退化则声明跳过：

1. `/speckit.history` — 增量蒸馏当前工具的会话历史。
2. `/speckit.docs` — 吸收 history 新素材，深化文档。
3. `/speckit.research` — 调研结论缺失或过期时补调研。
4. `/speckit.feature` — 注册表稀疏或调研揭示缺口时生成特性条目。

`/speckit.goal`、`/speckit.agents`、`/speckit.team` 的**首次定义**归 `sdd-project-setup`。若 H1 显示它们缺失（bootstrap gap），本 skill MUST NOT 静默跳过：记录 `bootstrap-gap: goal|agents|team` 并回交 setup，除非用户明确要求本 skill 维护；首次定义仍归 setup。

### H4 — Verify

- 五族前置检查：本地拓扑只适用 ④ LLM 配置与 ⑤ framework 可用性，①–③ 记 `n/a`；远端五族全查。权威表在 `.specify/skills/internal/run-agent/references/dispatch-preflight.md`，本 skill 引用不复写。
- 物理矩阵复扫达 `complete`（或 partial 且缺口已声明）；逻辑矩阵 required 层无未声明缺口。
- 兼容符号链接悬空扫描为空。
- Hook health：本地 `python3 ${SKILL_HOME}/scripts/hook-health.py --project <project-dir> [--fix] --json`；远端经 `ssh <alias> "su - <run-user> -c 'cd <project-dir> && python3 - --project <project-dir> [--fix] --json'" < ${SKILL_HOME}/scripts/hook-health.py`（或 scp 后执行）——必须在目标侧运行，不能拿 `<project-dir>` 在编排侧跑。`0` 干净/已修，`10` 未解决风险（进未处理清单），`2` 参数错误。`check` 模式只读，不带 `--fix`。

### H5 — Report

产出两件东西：

1. **候选工作清单**（建议而非强制）：未完成 feature、大规模反馈改进、SPECKIT TODO 事项。它是本 skill 的**唯一候选清单所有者**；setup 不再产出 `sdd-candidates-*.yaml`。
2. **运行报告**：写到宿主工作目录 `sdd-housekeeping-<project-slug>-<UTC-ts>.yaml`。字段、`check|cleanup` 的可空字段与 `sanitize_retention` 计数口径见 `./references/maintenance-recipes.md` § H5；本文件不复写 schema。

不在目标项目创建 ad-hoc 目录；不借用 `.specify/state/`；运行报告只落宿主工作目录。

## Hard Requirements

1. **目标项目治理优先**：执行任何命令前先读目标项目的 `.specify/memory/constitution.md` 与 `.specify/instructions.md`；遵守其目录/命名/临时目录纪律；MUST NOT 覆盖、绕过或删改治理内容；MUST NOT 在目标仓库内创建 ad-hoc 目录或临时根。目标项目尚无治理文档时交回 setup，不凭空自造。
2. **盘点先于处置**：H2/H3 的任何动作之前必须先完成 H1 的**两个**盘点；禁止凭印象判定项目状态。
3. **按缺口调协、不整建**：只执行 H1 判定缺失的项；不存在的机制不预建；未处理项必须出现在未处理清单。
4. **幂等收敛**：稳定态上重复执行零结构写、零内容重建；每项动作前以本次 H1 为凭据，禁止凭上次运行的记忆跳过或重做。
5. **sanitize 是唯一的破坏性门**：`check` 默认只扫描；`cleanup` 必须显式请求。破坏性回收/删除由 sanitize 既有确认门保护；本 skill MUST NOT 新增第二道确认门，也 MUST NOT 绕过 sanitize 直接执行 apply。
6. **记录回收红线**：没有 retention receipt 不删除；open feedback、unsettled run-determination、不可解析 exec-quant、无 promotion/ephemeral 决策的 session 笔记永不回收；默认宽限 30 天；目标路径 git 脏时拒绝 apply（非 git 项目需显式 `--allow-unversioned`）。
7. **本地原生承载**：本地拓扑由编排者或宿主原生子代理执行；MUST NOT 在本地启动 `qodercli` / `claude -p` 等外部 agent CLI。远端拓扑经 `run-agent` 外部 CLI 派发。
8. **不推进 SDD 阶段**：requirements → … → review 归 `sdd-loop-driver`；本 skill 只做治理、维护、强化与报告。
9. **进度可见**：长任务按 `.specify/shared/guidelines/progress-reporting.md` 的 15 分钟四要素节奏汇报；派发子代理时把该义务注入载荷。
10. **参数化、零机器路径**：目标路径、别名、运行用户全部入口参数；MUST NOT 嵌入用户名、主机名、家目录或项目族路径。

## Discipline Defaults

- 可逆动作直接执行并附执行报告；破坏性动作只经 sanitize 既有门。
- 远端形态既有脏文件不提交、不还原。
- 不 push（除非入口显式授权）。
- 访谈式问题自行裁决并记录假设；与目标项目治理冲突时以目标治理为准并报告。
- 候选清单是提示，不携带「必须调用 sdd-loop-driver」的语义。

## References

- `.specify/shared/workflow/target-resolution.md` — 三技能共享的目标解析唯一契约。
- `./references/maintenance-recipes.md` — H2 触发条件、H3 依赖、预算收敛、H4 验证、H5 报告 schema、幂等/重入语义。
- `./scripts/mechanism-inventory.py` — 物理机制盘点（只读）。
- `./scripts/logical-framework.py` — 逻辑框架盘点（只读；`--json` / `--strict`）。
- `./scripts/hook-health.py` — 宿主 hook 体检（`--fix` 仅在非 check 模式）。
- `.specify/shared/workflow/execution-topology.md` — 编排侧/执行侧划分与安装归属。
- `.specify/shared/guidelines/confirmation-gates.md` — 破坏性确认的唯一判据 owner。
- `.specify/shared/guidelines/progress-reporting.md` — 长任务进度汇报 owner。
- `.specify/shared/definitions/framework-map.md` — 目录与落点注册。
- Bootstrap owner: `sdd-project-setup`（init/refresh/constitution/首次 goal/agents/team）。
- SDD stage owner: `sdd-loop-driver`。

## Subagent Delegation

- **Carrier decision**（owner：`.specify/shared/workflow/execution-topology.md` § Carrier decision）：
  - **未给远程三元组 → 本地**：目标=当前项目；H1–H5 由编排者或宿主**原生子代理**执行；MUST NOT 启动 `qodercli` / `claude -p`。
  - **远程三元组给全 → 远端**：`ssh <alias>` → `su - <run-user>` → `cd <project-dir>`；H1 盘点在目标侧执行，H2/H3 的 `/speckit.*` 经 run-agent 驱动，H4 hook-health 在目标侧执行；CLI 缺省取 execution-config defaults（`cli: qodercli`），可按 agent/inline 覆盖。
  - **部分远程信息 → 问一个澄清问题**，不猜、不静默回退本地。
- **盘点与验证**：本地由编排者直接运行只读脚本；远端经 `ssh + su` 在 `<project-dir>` 下执行。
- **本地拓扑**：`/speckit.*` 由编排者亲自执行，或交给当前宿主 agent 的**原生子代理**。
- **远端拓扑**：治理命令经 `run-agent` 以拓扑声明派发外部子代理；前置检查与失败处置随其 `dispatch-preflight.md`。
- 职责切分：本 skill = 周期性维护（assess/reconcile/strengthen/verify/report）；setup = bootstrap；loop-driver = SDD 阶段循环；create-agent/run-agent/improve-agent = 代理的创建/派发/修正。

## Boundary

- 不安装、不 init、不 bootstrap constitution；这些归 `sdd-project-setup`。
- 不推进任何 SDD 开发阶段；不创建/修改 feature 的 requirements/plan/tasks。
- 不重写 sanitize/docs/history/feature/instructions 的 owner 流程；只调用并把结果汇总。
- 不新增调度器/守护进程；周期由用户或宿主循环触发。
- 不自动上送任何数据；反馈投递仍是人工路径。
- 不评估用户源码/产品脚本/测试；发现目标限于框架自有资料与记录存储。

## Self-Improvement Contract

This skill is an Execution Subject. Own-run observations (execution friction, missed gaps, wrong target resolution, duplicated owner logic) route through `improve-skills` against the canonical runtime directory `.specify/skills/sdd-house-keeping/` (framework source: `.specify/skills/sdd-house-keeping/`); the mutation route is `improve-skills`, validation is the skill-conformance suite plus the create-skills RED-GREEN pressure test, and the later comparison signal is the next run's observed behavior. The canonical workflow is owned by `.specify/shared/workflow/self-improvement-workflow.md`; this section does not restate it. Creation is capability evidence only, never evidence of improvement.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:sdd-house-keeping" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:sdd-house-keeping" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:sdd-house-keeping" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
