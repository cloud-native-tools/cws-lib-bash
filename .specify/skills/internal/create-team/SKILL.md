---
name: create-team
description: Create and run an agent team — organize multiple agents into a collaborative structure (parallel dispatch, serial chain, self-iterating iteration loop, or long-lived continuous operating loop), persist it as a reusable team, and execute it directly after a disclosed preview (reversible actions auto-execute per the confirmation-gates policy; continuous loops keep their tiered gates). Use when the user mentions ["创建团队", "组织一个团队", "组建团队", "运行团队", "执行团队", "编排", "并行", "串行", "团队", "闭环", "迭代", "运营", "持续", "new team", "build a team", "run team", "pipeline", "parallel", "chain", "iteration", "continuous", "team loop", "多agent协作", "agent协同"]
skill_id: "<SKILL:.specify/skills/internal/create-team/SKILL.md>"
classification: internal
---

# create-team

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.


## Goal

Create and run an **agent team**: organize multiple Agents into a **collaborative structure** (parallel dispatch, serial chain, self-iterating iteration loop, or long-lived continuous operating loop), persist it as a reusable `.specify/teams/<slug>/team.md`, and **execute** it directly after a disclosed preview — 可逆动作自动执行(判据:`.specify/shared/guidelines/confirmation-gates.md`),持续循环类保留其分级门控。This skill owns both **defining** a team and **running** it, and is the single source of truth for the multi-agent Conceptual Model (see `references/conceptual-model.md`).

## Conceptual Model

The multi-agent Conceptual Model (Role × Stage × Type + Team/Loop, the Team Supervisor Meta role, and the static/dynamic structure split) is defined authoritatively in `references/conceptual-model.md`. Read it before defining or running a team; do not re-define it elsewhere.

The capacity vs. responsibility boundary — which template set defines an agent's capacity and which defines its team-scoped responsibility — is `references/capacity-vs-responsibility.md`.

The **goal** concept is defined authoritatively in `references/goal.md`. When a goal's theme is **optimization**, classify it per `references/optimization-goals.md`.

## Command Family Gate (which commands may create a goal/team)

Whether the invoking command run may own a goal/team is decided by the declared class axis, never by a per-command list kept here (contract C-74): ask the engine with `python3 .specify/scripts/python/goal-utils.py command-family --command <stem> --json` and read `in_family` from its answer. The action resolves the class through `flow-class-check.py --action lookup --unit-id /speckit.<stem>` and reports `source: ledger` = in family, `source: default` = not in family; a degraded lookup exits 2 and is never read as a family membership. This skill carries no second whitelist.

## Handoff Contract (designer → construction crew, 094)

Complex work is handed to a crew through `<spec-dir>/handoff.md`, whose shape and rules are authored once in [`references/handoff-contract-template.md`](references/handoff-contract-template.md) — cite it, never restate it.

- **Production** — the `tasks` stage produces the contract only after `python3 .specify/scripts/python/goal-utils.py handoff-decision --tasks <spec-dir>/tasks.md --json` returns `handoff`; `plan` never produces one and `implement` consumes it (C-68).
- **Key discipline** — `goal_slug` and `team_slug` are validated against `.specify/anchoring/<goal_slug>/goal.md` and `.specify/teams/<team_slug>/team.md` through the engine; an unresolvable key is refused at creation with `handoff-dangling-key` (exit 2) naming the key, and the reverse `handoff_ref` on both definitions is written by the engine's binding action — never by the contract file alone (C-58/C-59).
- **Territory** — on activation the contract's `## Territory` expands into the `territory.write` of every team bound to that `goal_slug` as an explicit `improve-team` modification, one record per team; `requirements.md`, `tasks.md`, `verification.md` and `handoff.md` stay in `territory.forbidden`, and the refusal is mechanical via [`.specify/scripts/territory-check.py`](.specify/scripts/territory-check.py) (C-61/C-62).
- **Writeback** — the crew delivers one record per completed task under `<spec-dir>/writeback/<T-NNN>.yaml`; the task table stays spec-side (C-65/C-67).

## Team Definition & Persistence (create mode)

Produce a team from a user **goal** and persist it as `.specify/teams/<slug>/team.md`. Establish the goal first, then derive both structures from it. Full procedure, schema, and persistence rules: [`references/create-mode.md`](references/create-mode.md).

**Goal-based branch (before step 1)**: when a token in the input exactly matches an archived goal slug — verified deterministically via `python3 .specify/scripts/python/goal-utils.py list --json`, never guessed — offer to enter the **goal-based create branch**: load the definition via `parse_goal`, present the four-element analysis (维度 / 判据覆盖 / 既有 Target / 可达成性 — advisory, the user adjudicates), then derive the team from the loaded goal. Dangling references stop with the verbatim prefix `goal 未定义:`; terminal goals (`achieved`/`abandoned`) are rejected. Full branch procedure: [`references/create-mode.md`](references/create-mode.md) → *Goal-based create branch*.

1. **Establish the goal** — extract/establish a verifiable goal from `$ARGUMENTS`/context.
2. **Match presets** — run `${SKILL_HOME}/scripts/match-team-preset.py --goal "<text>"` and act on its `confidence`.
3. **Select the pattern** — derive from the goal via the decision tree in [`references/patterns.md`](references/patterns.md).
4. **Build the roster** — a Role × Stage × Type matrix; judge `Type` by operating object (`references/conceptual-model.md`). Member resolution: prefer existing agents under `.specify/agents/{templates,instances}/`; for a seat with no persistent definition, perform **seat instantiation (席位实例化)** — delegate to `create-agent` (kind: instance) to instantiate the seat from its stage frame, resolving ALL frame placeholders and setting `team-scope: <team-slug>` (the framework-only seat-provenance key; no `capacity-scope` for stage-frame seats); a same-slug collision with an existing persistent definition MUST be disclosed and that seat halted, never silently overwritten.
5. **Build the pattern config** — parallelism/territories, DAG/blockedBy, iteration thresholds, or continuous operating config.
6. **直接落盘并呈现** — **直接写入** `team.md`(不设阻塞式停等),随后呈现 goal + roster + pattern 与修改途径(`/speckit.team` modify / `improve-team`),按执行报告约定收尾。
   > **Reporter-seat obligation (087)**: the persisted roster MUST carry the reporting seat — a `members[]` row whose `role` is the literal `reporter`, written as `reporting-territory` (read list + the one write list for its stream artifact) plus `reporting-cadence` — unless the runtime-omission condition of [`references/create-mode.md`](references/create-mode.md) § Schema notes (RS-05) holds, in which case `config.reporting-reason` records which of the two accepted values applies. The seat is a roster row, never a parallel `reporter:` block. Before presenting, run the seat guard: `python3 ${SKILL_HOME}/scripts/validate-roster.py .specify/teams/<slug>/team.md` — exit `0` = satisfied (seat present or reason recorded), exit `1` = one named defect on one line (fix it before presenting), exit `2` = input error (disclose it). Rule source: [`references/create-mode.md`](references/create-mode.md) § Schema notes; the procedure is a step of create, not a separate command.
7. **渲染触发** — `team.md` 与席位实例落盘后,直接执行 `specify render-agents --ai <当前宿主工具>` 使席位到达宿主注册面(渲染模式工具:qoder/claude/copilot/opencode);stats 摘要(rendered/backups/unmapped)进执行报告;渲染触发失败 MUST 披露原因并作为流程异常上送,不得静默跳过。存量团队经一次 modify 即可让席位上注册面。

**Member class and stated concurrency capability (成员类别与并发能力声明)**: every `members[]` row MUST carry a **class** drawn from `.specify/shared/declarations/facts/concurrency-class.yaml` (a pointer — the class table is never copied here), and the team MUST state **how many of its members can run concurrently**; that statement MUST be derivable from the member classes and the slot cap read at execution time (`.specify/shared/declarations/facts/concurrency-slot-and-reserve.yaml`), never asserted independently. The team MUST NOT be instantiated with more concurrent members than the statement supports: the roster step reads each member's dispatch-capability verdict (the capability judgement reads the existing `capability-tools` frontmatter key — no new key is introduced) and **reports the reduction** when it applies. Per-seat **territories are judged at binding time** — intersecting or undeclared territories are red before any run (`references/conceptual-model.md` § Seat territories judged at binding time).

`goal_slug` identifies the **goal**, not the team slug; it is a different axis from `slug` (the team's identity). See `references/goal.md` and `references/summary-mapping.md`.

## Execution (run mode)

`/speckit.team run <slug>` loads a persisted team and executes it via the **preview → execute** sequence(预览即披露,呈现后直接执行;continuous 循环保留分级门控)。Full run discipline and shared protocols: [`references/execution-guide.md`](references/execution-guide.md).

1. **Load** the team from `.specify/teams/<slug>/team.md`.
2. **Restate the Goal** so execution is judged against it.
3. **Render Static Structure** — roster as a Role × Stage × Type matrix.
4. **Render Dynamic Structure** — pattern, settings, and execution flow.
5. **Present & execute** — present goal + structures, then orchestrate per pattern directly(presentation is disclosure, not a blocking gate;事后修改经 modify / improve-team)。
6. **Write the run report** — after every run, write a dated report to `.specify/teams/<slug>/runs/` per the Report contract below.

## Run Workspace, Reports & Output Discipline

Keep four file classes strictly separated: team definition, run reports, deliverables, and run intermediates. Token efficiency (see `.specify/shared/guidelines/token-efficiency.md`): agent prompts and handoffs carry digests/paths, never whole machine-managed data files. Full layout and protocols: [`references/execution-guide.md`](references/execution-guide.md).

### Report contract

After **every** run, write `.specify/teams/<slug>/runs/<UTC-timestamp>-report.md`:

```markdown
# Team Run Report: <name>
- **Team**: <slug> · **Goal**: <goal> · **Pattern**: <pattern> · **Outcome**: <outcome>
## Result Summary ## Deliverables ## Verification ## Execution Detail ## Run Workspace ## Summary
Summary: produced | skipped(cadence) | skipped(budget) | declined(no-material); Overlap: none | contested(<n>) | undecidable(<team,…>)
First activation: declare the summary mechanism has activated and the cadence now in force (首次激活需声明).
## Nested SDD Runs
```

`## Execution Detail` MUST 内含派发映射表 —— 每个被派发的执行体一行,列恰为 `label` | `role` | `dispatch_duty` | `workspace` | `parent`。`role` 取值恰为 `subagent` / `superagent`(`dual-role` 从不出现在该列);`dispatch_duty` 取值恰为 `granted` / `not-granted`。列与行形态由本节拥有;角色语义与值域归 `.specify/shared/definitions/superagent-definitions.md` § The Relative Role / § Role Edges(按指针)。不得为此新增顶层段 —— 映射表是 `## Execution Detail` 的必备内容。

### Verification(必填段,本节为该口径的唯一真源)

`## Verification` 是**必填**段:run 报告的验证结论 MUST 是**可复算的口径**,不是散文自评 —— 有界 pattern(parallel / serial / iteration)与 continuous 一律适用,continuous 的独立验证者纪律(`references/operating-loops.md` §6)叠加在本节之上,不替代它。三条口径:

1. **回归数字注明口径** — 每个测试 / 检查数字 MUST 标明是**全量**还是**过滤子集**,子集 MUST 附过滤表达式(如 `-k <expr>`);子集数字 MUST NOT 当作整体基线陈述。
2. **仓库存在长期既存失败时** — 独立验证的最小充分形式是「**同口径** A/B 失败集求差 + 差集逐项归因」:A、B 两侧用同一条命令、同一过滤口径跑,只对**失败集差集**逐项归因,不对两侧的绝对数字作比较。worktree A/B 的差集项 MUST 先排除 **git-ignored 残留**归因 —— worktree 不复制 git-ignored 文件,运行工作区、构建产物、本地缓存一类路径在两侧天然不对称,由此产生的差异不是本次改动造成的,把它记成改动效果就是假阳。
3. **One-Source-Of-Truth 类验收** — MUST 先从**落盘产物**提取实际出现的短语,再以这些短语为查询集反向计数;MUST NOT 以「我以为写了的短语」为查询集 —— 那样复写检查必然假阴(查询集与被查集不同源)。机械判据见 `.specify/shared/guidelines/one-source-of-truth.md` § Reference, don't copy。

Stage 级批量判定的实读证据下限由 `references/patterns.md` § Serial Chain → Substance floor 持有,不在此复述。

### Nested SDD Runs section（必填段,本节为该段的唯一真源）

每个 run 报告 MUST 在既有必填段之后**末尾追加**一个嵌套段,标题字面量逐字为 `## Nested SDD Runs`(不得改写、不得改变标题层级、不得并入其它段)。该段对**每次运行**强制 —— 有界 pattern(parallel / serial / iteration)与 continuous 一律适用,与该次运行是否真的发生过嵌套 SDD 调用无关。既有必填段的名称、次序与内容义务逐字不变;MUST NOT 省略该段,省略即判违约。

- **每次调用一行**: 一行恰好五个字段 —— `outcome`、`artifact paths`、`evidence paths`、`routing-verdict reference`、`anomalies`。`outcome` 取自三值封闭集 `completed` / `blocked` / `failed`;第四值、自由文本或空值一律非法。
- **无嵌套调用**: MUST 在段内显式声明「本次无嵌套 SDD 调用」,不是省略整段 —— 即便正确内容本是 none,省略仍是违约。
- **路径以路径携带**: artifact / evidence 只写路径,段内 MUST NOT 内联工件正文;`blocked` / `failed` 的嵌套运行 MUST NOT 改写成成功语气 —— 它们原样上抛。
- **routing-verdict reference**: 指向 `074a` 在 Agent 执行证据里记录的那条裁决(`.specify/scripts/python/sdd-route.py` 是该记录的产生者),段内只承载**引用**:MUST NOT 复制输入集、裁决表或理由码词表,MUST NOT 重算。记录不可定位时记 `missing`,外层 MUST NOT 重算或补写。
- **handoff 字段集按引用读取**: 封闭字段集归 `.specify/skills/sdd-loop-driver/references/nested-invocation.md`;交接未携带的字段按缺失记录,MUST NOT 用调用方叙述补齐;交接缺 integration identity 即为 incomplete handoff,外层 MUST NOT 据此报成功。
- **与 `## Verification` 并列**: 嵌套段是 `## Verification` 的**同级段**,不是替代 —— 嵌套运行自己的验证证据不解除外层运行的验证义务,外层运行的验证标准照旧适用。
- **写者唯一**: 团队 supervisor 是该段与本次运行全部 tracked 工件的**唯一写者**;嵌套运行不写任何 tracked 工件 —— 不改报告、不写 goal archive、不写 spec 目录 —— 它的产出只是回传的 handoff,由 supervisor 消费。
- **归因边界**: 报告期 supervisor 追加**至多一条**、携带既有 Target 引用的台账条目 —— 声明了 Target 时**恰一条**,未声明时**零条**;复用既有归因字段 `target_ref`(字段、文法与缺省归 `references/summary-mapping.md` § 6.5)。未声明 Target 的运行 MUST NOT 臆造占位 Target,其台账行不带归因字段(既有 Goal 整体形态)。本段对 Goal 面只是消费者:MUST NOT 新增 Goal 字段、MUST NOT 建立 Goal → requirements spec 的结构链接、MUST NOT 写 Goal 定义文件;解析出的 Goal 字段集在运行前后完全一致。

## Pattern Selection (Decision Tree)

Select from four collaboration patterns, each with a distinct priority: **parallel** = 效率优先, **serial** = 质量优先, **iteration** = 目标收敛, **continuous** = 长期运营. The goal decides which fits. Decision tree and detailed pattern guides: [`references/patterns.md`](references/patterns.md).

---

## § Parallel Dispatch Pattern

**Priority: 效率优先 (throughput-first).** Dispatch multiple independent agents concurrently; correctness rests on conflict-free territories. Refresh the goal summary after cross-verification and Result Aggregation complete. Details: [`references/patterns.md § Parallel`](references/patterns.md#parallel-dispatch-pattern).

---

## § Serial Chain Pattern

**Priority: 质量优先 (quality-first).** Orchestrate agents in a DAG-based pipeline; a simple verification guards every handoff. Refresh the goal summary after each stage handoff verification passes. Details: [`references/patterns.md § Serial`](references/patterns.md#serial-chain-pattern).

---

## § Iteration Pattern

**Priority: 目标收敛 (converge to the goal).** A Team Supervisor (Meta) dispatches Workers, scores output, and iterates until threshold or cap. Refresh the goal summary after each generation's DECIDE phase completes. Details: [`references/patterns.md § Iteration`](references/patterns.md#iteration-pattern).

---

## § Continuous Operating Loop Pattern

**Priority: 长期运营 (operate the team long-term).** A long-lived loop that runs on a cadence; full operating discipline is in `references/operating-loops.md`. One `run` executes exactly one cycle.

### Per-Cycle Loop

1. READ `constraints.md` + budget + kill-switch
2. BUDGET check spend
3. TRIAGE discover & prioritize source work
4. ACT per maturity (L1 report-only; L2+ minimal change)
5. VERIFY independent verifier (L2+)
6. SCORE against quality dimensions
7. CRITIQUE append Post-Run Critique
8. REPORT write `runs/<ts>-report.md`
9. SUMMARIZE refresh the goal summary when the gates allow

---

## Summary Refresh (all patterns)

Every run refreshes a **goal-level summary** by driving `summarize-project` non-interactively (`--load`). Concept mapping and provenance rules live in `references/summary-mapping.md`.

### Trigger boundaries

| Pattern | Boundary |
|---------|----------|
| `continuous` | end of every Nth cycle — phase 9 SUMMARIZE, after REPORT |
| `iteration` | after each generation's DECIDE phase |
| `serial` | after each stage handoff verification passes |
| `parallel` | after cross-verification and Result Aggregation complete |
| all | **terminal summary** on goal met / converged / halt / manual stop (unless budget already exceeded) |

### Gate order (hard sequence)

Evaluate in order; the first blocking gate determines the recorded status. **Budget outranks cadence**; the summary is the **first step dropped** under budget pressure; two boundaries in rapid succession **coalesce** into one refresh.

1. **Budget** — at report-only tier or kill-switch set → skip, record `skipped(budget)`.
2. **Cadence** — not at an Nth boundary → skip, record `skipped(cadence)`.
3. **Material** — no item ledger and no run reports in the goal → decline, record `declined(no-material)`.
4. **Overlap detection** — detect write-scope overlap across teams sharing this `goal_slug`; record contested areas; do not rewrite any `team.md`.
5. Otherwise → refresh, record `produced`.

### Status line (mandatory in every run report)

```
Summary: produced | skipped(cadence) | skipped(budget) | declined(no-material)
Overlap: none | contested(<n>) | undecidable(<team,…>)
```

Exactly one status MUST appear. `produced` names the delivery directory; `skipped(budget)` names the blocking tier; `declined(no-material)` MUST NOT appear alongside any chart.

### Enablement

`config.summary` is opt-out: a team without the block is **still ENABLED** at the pattern's default cadence. The `continuous` default is every 5th cycle — **never every cycle**. Bounded patterns default to every boundary. Invoke the refresh non-interactively and record that fact in the report metadata.

## Shared Protocols

All patterns share file-path-only handoffs, progress tracking, structured result manifests from sub-agents, and model selection guidance. Details: [`references/execution-guide.md`](references/execution-guide.md).

## Hard Constraints

- **Territory validation MUST pass** before parallel dispatch
- **DAG validation (no cycles)** before serial chain starts; a **simple per-handoff verification** guards every serial step
- **Max iterations MUST be set** for iteration loops (default: 5, max: 10)
- **Continuous loops MUST start at maturity L1**, read `constraints.md` + budget + kill-switch at cycle start, honor the budget circuit-breaker (80% → report-only, 100%/kill-switch → halt), and use an **independent verifier** (default REJECT) at L2+ — see `references/operating-loops.md`
- **File-path-only handoff** — never paste content between agents
- **Context isolation** — each agent invocation is a fresh subagent; the continuous **verifier MUST be a separate sub-agent** from the implementer
- **Idempotent execution** — stages/iterations/cycles can be re-run safely
- **Run intermediates confined** to `.specify/teams/.work/<slug>/` (git-ignored); only declared final deliverables (standard output) persist to real target paths — never the team directory. Every team additionally keeps the tracked item ledger `items.jsonl`, and continuous teams also keep tracked `constraints.md` / `STATE.md` / `run-log.jsonl`, in the team directory. The summary delivery directory is **not** in the team directory — it belongs to the goal index `.specify/goal/<goal-slug>/summary/`
- **Every run writes a dated report** to `.specify/teams/<slug>/runs/<UTC-timestamp>-report.md` per the Report contract, including its mandatory `## Verification` section (口径见上,不复述)
- **Every persisted team contains `## Self-Improvement Contract` exactly once**; one-shot teams do not claim subject identity

## Resources

| Path | Contents |
|------|----------|
| `${SKILL_HOME}/references/` | `conceptual-model.md`, `capacity-vs-responsibility.md`, `goal.md`, `optimization-goals.md`, `operating-loops.md`, `team-presets.md`, `summary-mapping.md`, `create-mode.md`, `patterns.md`, `execution-guide.md`, `handoff-contract-template.md` |
| `${SKILL_HOME}/templates/` | team-supervisor role template, the three EEI stage templates, the parallel/serial/triad orchestration templates, `agent-workflow-schema.md` |
| `${SKILL_HOME}/templates/teams/` | Predefined team shapes: `capability-arena.md` (skill/command/subagent 竞技场), `project-cluster.md` (跨项目协作集群) |
| `${SKILL_HOME}/scripts/match-team-preset.py` | Deterministic preset matcher — returns ranked JSON with a `confidence` verdict |
| `${SKILL_HOME}/scripts/territory-check.py` | Territory refusal surface — may a crew seat write this path? (094 handoff contract) |

## Agent-Specific Configuration

### Step 1: Identify Executing Agent

| Agent | Detection Signals |
|-------|-------------------|
| **Claude Code** | Tools include `Agent`, `Edit`, `Bash`, `Read`; `.claude/` directory exists |
| **GitHub Copilot** | Running in VS Code Copilot Chat context |
| **Qoder CLI** | `.qoder/` directory exists; `AGENTS.md` instructions loaded |
| **opencode** | `.opencode/` directory exists |

### Step 2: Load Agent-Specific Guidance

Check if a guide exists at:

```
${SKILL_HOME}/references/<agent-slug>-guide.md
```

If the guide exists, apply agent-specific tool mappings for orchestration (e.g., Claude Code uses `Agent` tool, Copilot uses `@workspace` delegation).

### Step 3: Capture Execution Feedback

If you encounter an agent-specific obstacle, generate feedback at:

```
.specify/memory/feedback/create-team-<agent-slug>-<YYYY-MM-DDTHH-MM-SS>.md
```

```markdown
# Agent Execution Feedback

**Source**: create-team
**Agent**: <agent-slug>
**Timestamp**: <ISO-8601>
**Outcome**: <success | success-with-workaround | partial-failure | full-failure>

## Obstacle
[Description of the agent-specific issue encountered]

## Workaround Applied
[What was done to work around the issue, if anything]

## Suggested Improvement
[Specific change to the skill or reference document that would prevent this issue]
```

Only generate feedback when a genuine agent-specific obstacle was encountered.

## Self-Improvement Integration

A persisted `team.md` is an Execution Subject; a one-shot team and individual member executions are not separate team subjects. Persistent definitions MUST include a compact `## Self-Improvement Contract` referencing `.specify/shared/workflow/self-improvement-workflow.md`: team run reports/Post-Run Critique are own-run evidence, `improve-team` is the improvement route, behavior/autonomy changes require an independent verifier, and later comparable runs decide outcome. This composes with—not replaces—the continuous operating loop, its maturity gates, budget, and kill-switch. This `create-team` Skill routes its own qualified run evidence through `improve-skills`.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:create-team" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:create-team" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:create-team" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
