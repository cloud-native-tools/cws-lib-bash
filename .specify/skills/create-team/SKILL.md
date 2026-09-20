---
name: create-team
description: Create and run an agent team — organize multiple agents into a collaborative structure (parallel dispatch, serial chain, self-iterating iteration loop, or long-lived continuous operating loop), persist it as a reusable team, and execute it directly after a disclosed preview (reversible actions auto-execute per the confirmation-gates policy; continuous loops keep their tiered gates). Use when the user mentions ["创建团队", "组织一个团队", "组建团队", "运行团队", "执行团队", "编排", "并行", "串行", "团队", "闭环", "迭代", "运营", "持续", "new team", "build a team", "run team", "pipeline", "parallel", "chain", "iteration", "continuous", "team loop", "多agent协作", "agent协同"]
skill_id: "<SKILL:.specify/skills/create-team/SKILL.md>"
---

# create-team

## Goal

Create and run an **agent team**: organize multiple Agents into a **collaborative structure** (parallel dispatch, serial chain, self-iterating iteration loop, or long-lived continuous operating loop), persist it as a reusable `.specify/teams/<slug>/team.md`, and **execute** it directly after a disclosed preview — 可逆动作自动执行(判据:`.specify/shared/guidelines/confirmation-gates.md`),持续循环类保留其分级门控。This skill owns both **defining** a team and **running** it, and is the single source of truth for the multi-agent Conceptual Model (see `references/conceptual-model.md`).

## Conceptual Model

The multi-agent Conceptual Model (Role × Stage × Type + Team/Loop, the Team Supervisor Meta role, and the static/dynamic structure split) is defined authoritatively in `references/conceptual-model.md`. Read it before defining or running a team; do not re-define it elsewhere.

The capacity vs. responsibility boundary — which template set defines an agent's capacity and which defines its team-scoped responsibility — is `references/capacity-vs-responsibility.md`.

The **goal** concept is defined authoritatively in `references/goal.md`. When a goal's theme is **optimization**, classify it per `references/optimization-goals.md`.

## Team Definition & Persistence (create mode)

Produce a team from a user **goal** and persist it as `.specify/teams/<slug>/team.md`. Establish the goal first, then derive both structures from it. Full procedure, schema, and persistence rules: [`references/create-mode.md`](references/create-mode.md).

**Goal-based branch (before step 1)**: when a token in the input exactly matches an archived goal slug — verified deterministically via `python3 scripts/python/goal-utils.py list --json`, never guessed — offer to enter the **goal-based create branch**: load the definition via `parse_goal`, present the four-element analysis (维度 / 判据覆盖 / 既有 Target / 可达成性 — advisory, the user adjudicates), then derive the team from the loaded goal. Dangling references stop with the verbatim prefix `goal 未定义:`; terminal goals (`achieved`/`abandoned`) are rejected. Full branch procedure: [`references/create-mode.md`](references/create-mode.md) → *Goal-based create branch*.

1. **Establish the goal** — extract/establish a verifiable goal from `$ARGUMENTS`/context.
2. **Match presets** — run `${SKILL_HOME}/scripts/match-team-preset.py --goal "<text>"` and act on its `confidence`.
3. **Select the pattern** — derive from the goal via the decision tree in [`references/patterns.md`](references/patterns.md).
4. **Build the roster** — a Role × Stage × Type matrix; judge `Type` by operating object (`references/conceptual-model.md`).
5. **Build the pattern config** — parallelism/territories, DAG/blockedBy, iteration thresholds, or continuous operating config.
6. **直接落盘并呈现** — **直接写入** `team.md`(不设阻塞式停等),随后呈现 goal + roster + pattern 与修改途径(`/speckit.team` modify / `improve-team`),按执行报告约定收尾。

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
## Result Summary ## Deliverables ## Execution Detail ## Run Workspace ## Summary
Summary: produced | skipped(cadence) | skipped(budget) | declined(no-material); Overlap: none | contested(<n>) | undecidable(<team,…>)
First activation: declare the summary mechanism has activated and the cadence now in force (首次激活需声明).
```

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
- **Every run writes a dated report** to `.specify/teams/<slug>/runs/<UTC-timestamp>-report.md` per the Report contract
- **Every persisted team contains `## Self-Improvement Contract` exactly once**; one-shot teams do not claim subject identity

## Resources

| Path | Contents |
|------|----------|
| `${SKILL_HOME}/references/` | `conceptual-model.md`, `capacity-vs-responsibility.md`, `goal.md`, `optimization-goals.md`, `operating-loops.md`, `team-presets.md`, `summary-mapping.md`, `create-mode.md`, `patterns.md`, `execution-guide.md` |
| `${SKILL_HOME}/templates/` | team-supervisor role template, the three EEI stage templates, the parallel/serial/triad orchestration templates, `agent-workflow-schema.md` |
| `${SKILL_HOME}/templates/teams/` | Predefined team shapes: `capability-arena.md` (skill/command/subagent 竞技场), `project-cluster.md` (跨项目协作集群) |
| `${SKILL_HOME}/scripts/match-team-preset.py` | Deterministic preset matcher — returns ranked JSON with a `confidence` verdict |

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

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:create-team" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
