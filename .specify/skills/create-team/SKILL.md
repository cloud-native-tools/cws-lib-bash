---
name: create-team
description: Create and run an agent team — organize multiple agents into a collaborative structure (parallel dispatch, serial chain, self-iterating iteration loop, or long-lived continuous operating loop), persist it as a reusable team, and execute it behind a preview→confirm gate. Use when the user mentions ["创建团队", "组织一个团队", "组建团队", "运行团队", "执行团队", "编排", "并行", "串行", "团队", "闭环", "迭代", "运营", "持续", "new team", "build a team", "run team", "pipeline", "parallel", "chain", "iteration", "continuous", "team loop", "多agent协作", "agent协同"]
skill_id: "<SKILL:.specify/skills/create-team/SKILL.md>"
---

# create-team

## Goal

Create and run an **agent team**: organize multiple Agents into a **collaborative structure** (static roster + dynamic execution pattern — parallel dispatch, serial chain, self-iterating iteration loop, or long-lived continuous operating loop), persist it as a reusable `.specify/teams/<slug>/team.md`, and **execute** it behind a preview→confirm gate. This skill owns both **defining** a team and **running** it, and is the single source of truth for the multi-agent Conceptual Model (see `references/conceptual-model.md`).

## Conceptual Model

The multi-agent Conceptual Model (Role × Stage × Type + Team/Loop, the Team Supervisor Meta role, and the static/dynamic structure split) is defined once, authoritatively, in `references/conceptual-model.md`. Read it before defining or running a team; do not re-define it elsewhere.

**Which template set defines an agent** — `create-agent/templates/` defines an agent's **capacity** (team-agnostic: tools, skills, professional identity); `create-team/templates/` defines an agent's **responsibility** (team-scoped: stage, territory, handoff, reporting duty). The authoritative boundary, including the no-cross-writing rule and edit routing, is `references/capacity-vs-responsibility.md`. Read it before adding or editing any agent template.

The **goal** — the team's north star that both structures serve — is defined authoritatively in `references/goal.md`. When a goal's theme is **optimization**, `references/optimization-goals.md` gives the one-time-vs-continuous classification and the elimination-vs-progressive strategies. Read `references/goal.md` before defining a team; it is the goal-side companion to the conceptual model.

## Team Definition & Persistence (create mode)

Produce a team from a user **goal** and (unless one-shot) persist it as `.specify/teams/<slug>/team.md`. The goal is the team's north star — **establish it first, then derive both structures from it** (goal concept: `references/goal.md`).

1. **Establish the goal (first)** — extract the goal from `$ARGUMENTS`/conversation/repo context, ask if missing, and confirm it with the user; write it in a **verifiable** form (success criteria / threshold). If the goal's theme is **optimization**, classify it (one-time vs continuous) and pick a strategy (elimination vs progressive) per `references/optimization-goals.md`.
2. **Match against team presets (before deriving anything)** — run `${SKILL_HOME}/scripts/match-team-preset.py --goal "<goal text>"` and act on the returned `confidence`: `high` → present the top preset (goal skeleton + roster + pattern) and **recommend reuse**; `medium` → present the top 2 candidates alongside the from-scratch option; `low`/`none` → say no preset matched and continue to step 3. Presets are known-good shapes distilled from teams that actually ran — reusing one is what keeps a vague goal from producing an arbitrary team. Never instantiate a preset silently, and never let it override an explicit user instruction. See `references/teams.md`.
3. **Select the pattern** via the Pattern Selection decision tree below (independent → parallel; sequenced → serial; iterative-quality → iteration; long-lived operation → continuous) — **derived from the goal**. On preset reuse, the preset supplies the pattern; still confirm it fits.
4. **Build the roster (static structure)** — a Role × Stage × Type matrix. If the user did not supply members, **propose** them from the goal: prefer existing agents under `.specify/agents/`, otherwise temporary stage/worker templates from `templates/`. An **iteration or continuous team MUST include exactly one Team Supervisor** (Meta role). **Judge each member's `type` explicitly by its operating object** — operates on business artifacts/information → `Worker`; operates on other agents/skills/agent-defining configuration → `Meta`. Do **not** derive Type from Stage: an evaluator scoring a business artifact (repo state, rendered output, a document) is a `Worker`, not Meta. The implication runs **one way only**: a member that must **write** team config / agent definitions / skill definitions MUST be `Meta` (necessary); but holding an evaluator / optimizer / "continuous improvement" role does **not** by itself make it Meta (not sufficient) — an agent that iteratively improves a *business artifact* is still a `Worker`. Decide each member's Type from **what it writes to**, never from its role name (see `references/conceptual-model.md` → Type criterion + "Meta and write authority"). Roster rows carry **responsibility** (stage, territory, `blockedBy`, reporting duty); the referenced agent carries **capacity** — never fork a capacity artifact to express a new seat (`references/capacity-vs-responsibility.md`).
5. **Build the pattern config (dynamic structure)** — parallelism + territories (parallel), DAG `blockedBy` edges + per-handoff verification + file-path-only handoff (serial), quality dimensions + threshold + max_iterations + regression_limit (iteration), or the operating config — maturity + cadence + budget + constraints + independent verifier + state spine (continuous; see `references/operating-loops.md`).
6. **Confirm** the proposed **goal** + roster + pattern with the user, then persist the `Team` to `.specify/teams/<slug>/team.md` using the schema below (skip persistence only for an explicit one-shot run). When a preset was reused, record `preset: <preset_id>` in the frontmatter and apply the preset's `## Instantiation` steps (including any `constraints.md` / `STATE.md` bootstrap).

### Persisted `team.md` schema

Each persistent team owns a **directory** `.specify/teams/<slug>/` (no per-tool symlink — framework-internal). The definition is stored at `.specify/teams/<slug>/team.md`; per-run reports accumulate under `.specify/teams/<slug>/runs/` (see Run Workspace, Reports & Output Discipline below):

```markdown
---
name: <display name>
slug: <kebab-slug>
description: <one-line label>
goal: <overall final objective + success criteria / threshold>
pattern: parallel | serial | iteration | continuous
preset: <preset_id>            # optional — set when instantiated from a team preset
created: YYYY-MM-DD
updated: YYYY-MM-DD
members:
  - agent: <slug-or-template-id>
    role: <role>
    lifecycle: persistent | temporary
    # territory: [...]        # parallel
    # blockedBy: [...]        # serial
config:
  # pattern-specific block (parallelism / DAG / loop settings)
---

## Goal
<the team's overall final objective + success criteria; authored FIRST — the static and dynamic sections are organized to serve it. See references/goal.md>

## Static Structure
<Role × Stage × Type matrix table for this team's roster>

## Dynamic Structure
<pattern description, parallelism/DAG/loop settings, and the execution flow diagram>
```

- `slug` MUST be unique within `.specify/teams/`; it also names the team directory `.specify/teams/<slug>/`.
- `members` MUST resolve to `.specify/agents/<slug>.agent.md` or a temporary stage/worker template; unresolved members are surfaced as broken references.
- `config` MUST match `pattern`.

## Execution (run mode)

`/speckit.team run <slug>` loads a persisted team and executes it behind the mandatory **preview → confirm → execute** gate:

1. **Load** the team from `.specify/teams/<slug>/team.md`.
2. **Restate the Goal** — surface the team's `goal` up front, so both structures are read as *means to that end* and execution can be judged against it.
3. **Render Static Structure** — the roster as a Role × Stage × Type matrix (agent, role, Worker/Meta, persistent/temporary).
4. **Render Dynamic Structure** — the `pattern`, its parallelism/DAG/loop settings, and an execution flow diagram (textual/mermaid/PlantUML showing dispatch/handoff/loop edges).
5. **Confirmation gate** — present the **goal** and both structures and require explicit user confirmation. On decline, stop without executing. On confirm, orchestrate per pattern using the engine defined in the pattern sections below, preserving the Hard Constraints (territory validation before parallel dispatch; DAG no-cycle + per-handoff verification before serial; mandatory max-iteration cap for iteration loops; for **continuous** loops read `constraints.md` + budget + kill-switch at cycle start, run exactly one cycle at the declared maturity level starting at L1, and use an independent verifier at L2+; file-path-only handoff; context isolation; idempotent execution). All run-generated intermediate files MUST stay in the run workspace `.specify/teams/.work/<slug>/`; deliverables go only to their declared target paths (see Run Workspace, Reports & Output Discipline).
6. **Write the run Report** — after execution finishes (success, halt, or abort), write a dated report to `.specify/teams/<slug>/runs/` per the Report contract below. This is mandatory for every run.

## Run Workspace, Reports & Output Discipline

Every team run produces files in **four distinct classes**. Keep them strictly separated — this is what makes runs reproducible, the team directory clean, and later skill/command optimization possible.

| Class | Location | Git | What goes here |
|-------|----------|-----|----------------|
| **Team definition** | `.specify/teams/<slug>/team.md` | tracked | The persisted team (frontmatter + Goal/Static/Dynamic sections). |
| **Run reports** | `.specify/teams/<slug>/runs/<UTC-timestamp>-report.md` | tracked, **accumulate** | One report per execution; filename carries the date. |
| **Deliverables (standard output)** | the **declared target path** (a real project path the user/goal specifies) | tracked | The team's actual product — final artifacts only. **Never** the team directory. |
| **Run intermediates** | `.specify/teams/.work/<slug>/` | **git-ignored** | Everything else, any filename: progress files, parallel status manifests, per-iteration candidate renders, evaluator score dumps, team working memory, executor/optimizer scratch, intermediate serial-stage handoff files. |

Rules:

- The team directory `.specify/teams/<slug>/` holds **only** `team.md` and `runs/` — no intermediate files, no deliverables.
- **Only final deliverables** count as standard output and escape to real target paths. Intermediate handoff files between serial stages are run intermediates → `.specify/teams/.work/<slug>/` (file-path-only handoff still works: downstream stages read from the workspace).
- The run workspace is created on demand by the orchestrator at run time; it is transient and safe to delete. Do not rely on it across runs — durable knowledge belongs in the tracked report.

### Report contract

After **every** run, write `.specify/teams/<slug>/runs/<UTC-timestamp>-report.md` (e.g. `20260715T143000Z-report.md`). It MUST record at least:

```markdown
# Team Run Report: <team name>

- **Team**: <slug>
- **Goal**: <the team's goal / success criteria>
- **Started**: <ISO-8601>  **Finished**: <ISO-8601>  **Duration**: <hh:mm:ss>
- **Pattern**: parallel | serial | iteration | continuous
- **Outcome**: <converged / max-reached / regression-halted / completed / aborted>

## Result Summary
<concise summary of the final result against the goal>

## Deliverables
| Artifact | Target path |
|----------|-------------|
<final deliverable paths — real project paths, not the team dir>

## Execution Detail
<full process record: task decomposition / stage or iteration log / scores / decisions / handoffs / problems encountered — enough to later optimize the team, its skills, and commands>

## Run Workspace
- Intermediates: `.specify/teams/.work/<slug>/` (git-ignored; transient)
```

## Pattern Selection (Decision Tree)

The team domain has **four** collaboration patterns, each with a distinct priority: **parallel** = 效率优先 (throughput), **serial** = 质量优先 (quality, with a verified handoff between every step), **iteration** = 目标收敛 (converge then stop), **continuous** = 长期运营 (operate indefinitely on a cadence). Analyze the user's intent and task characteristics to select the right one:

```
1. Is the work long-lived / recurring — running on a cadence to keep handling a
   stream of incoming work (CI failures, new PRs/issues, dependency updates) or
   to keep improving / maintaining a quality over time?
   → YES: Continuous (operating loop) — see references/operating-loops.md; start at maturity L1
   → NO: Continue to Q2

2. Are sub-tasks independent with no shared mutable state? (throughput-first)
   → YES: Parallel Dispatch
   → NO: Continue to Q3

3. Do tasks form a strict sequence (output of A feeds input of B)? (quality-first, verified handoffs)
   → YES: Serial Chain
   → NO: Continue to Q4

4. Does the deliverable need iterative quality improvement that converges to a goal, then stops?
   → YES: Iteration
   → NO: Consider Serial Chain with parallel stages
```

| Scenario | Pattern | Priority | Signals |
|----------|---------|----------|---------|
| Independent tasks, no shared state | Parallel Dispatch | 效率优先 | "并行", "同时", "independent", "parallel", "效率" |
| Sequential phases with dependencies | Serial Chain | 质量优先 | "阶段", "串行", "pipeline", "chain", "依次" |
| Quality-critical, converge then stop | Iteration | 目标收敛 | "团队", "闭环", "自迭代", "迭代", "quality loop", "converge" |
| Long-lived, cadence-driven, unattended-capable | Continuous | 长期运营 | "持续", "长期", "运营", "每天/每次", "keep running", "operating loop" |
| Mix of independent + dependent | Serial Chain with parallel stages | 质量优先 | "先…再分别…" |

---

## § Parallel Dispatch Pattern

**Priority: 效率优先 (throughput-first).** This team form puts **maximum efficiency first** — it runs multiple operations **concurrently** to compress wall-clock time. Dispatch **multiple independent agents** in parallel when the task decomposes into non-overlapping sub-tasks. Correctness rests on conflict-free territories rather than on step-by-step verification.

### When to Use

- Task naturally decomposes into **2+ independent sub-tasks**
- Sub-tasks have **no shared mutable state** (no file overlap)
- Throughput is a priority (wall-clock time reduction)
- Tasks are embarrassingly parallel (separate modules, independent reviews)

### When NOT to Use

- Sub-tasks have **strong sequential dependencies**
- Multiple agents need to **modify the same file**
- Fewer than 2 independent sub-tasks
- Task requires **iterative refinement** on shared artifacts

### Territory Division

Territory division is the **deterministic, conflict-free** assignment of file/directory scopes to each child agent.

**Rules:**

1. **Extract Domains**: Parse task into discrete sub-task domains with clear deliverables.
2. **Map to File Sets**: For each domain, enumerate READ and WRITE file sets.
3. **Zero Write Overlap**: No two agents may have overlapping WRITE sets.
4. **Read Overlap Allowed**: Multiple agents MAY read the same files.
5. **Shared File Prohibition**: Files that multiple agents might WRITE go to a **Forbidden Write List** — only the Lead modifies these after aggregation.

**Territory Manifest:**

```
Territory: agent-<N>
  Task: <one-line brief>
  Write Scope: [files/dirs this agent may create or modify]
  Read Scope: [files/dirs this agent may read]
  Forbidden: [shared files this agent MUST NOT modify]
```

**Validation Checklist:**

- [ ] Every file in any Write Scope appears in exactly ONE agent's Write Scope
- [ ] Forbidden Write List contains all files referenced by 2+ agents' potential writes
- [ ] Each agent has at least one file in its Write Scope
- [ ] No circular dependencies between territories

### Dispatch Protocol

**Key principle**: Issue all sub-agent calls in ONE response block — sequential dispatch defeats the purpose.

Per-Agent Payload:

| Field | Content |
|-------|---------|
| `task_brief` | One-paragraph task with clear deliverable |
| `territory` | Write Scope + Read Scope |
| `forbidden_files` | Files this agent MUST NOT modify |
| `output_convention` | Where to write status + intermediates (`.specify/teams/.work/<slug>/`) vs. final deliverables (declared target path) |
| `model_hint` | Suggested model tier (light / standard / heavy) |

Context Isolation Rules:
- NO conversation history passed to child agents
- NO other agent's task briefs shared
- NO intermediate results from other agents visible
- Child agents receive only their territory manifest

### Monitoring

Monitor each agent's output manifest at `.specify/teams/.work/<slug>/parallel-result-<agent-id>.md`.

**Stall Detection:**

| Condition | Threshold | Action |
|-----------|-----------|--------|
| No manifest created | 60s after dispatch | Alert Lead |
| Manifest stuck at `in-progress` | 120s with no file changes | Flag as stalled |
| Empty output | Manifest exists but deliverables empty | Flag as incomplete |

**Recovery Options**: Wait (extend timeout) | Nudge (re-issue) | Terminate (Lead takes over) | Reassign (fresh agent)

### Result Aggregation

1. Collect each agent's completion manifest
2. Verify deliverables exist at declared paths
3. Flag territory violations
4. Detect contradictory outputs → trigger Lead resolution
5. Generate Final Report

**Final Report:**

```markdown
# Parallel Dispatch Report
## Summary
- Agents dispatched: <N>
- Successful: <count> | Partial: <count> | Failed: <count>

## Agent Results
| Agent | Task | Status | Output Paths | Notes |
|-------|------|--------|--------------|-------|

## Conflicts Detected
[list or "None"]

## Aggregated Deliverable
[final merged output description]
```

---

## § Serial Chain Pattern

**Priority: 质量优先 (quality-first).** This team form puts **quality first**: work advances through an ordered chain where **every step has a strict predecessor dependency**, and **a simple verification guards each handoff** between a step and its predecessor before the next step may start. It runs slower than parallel dispatch, but the per-handoff gate guarantees quality accumulates rather than compounds errors. Orchestrate Agents in a **serial chain** (DAG-based pipeline) where each stage's output feeds into the next stage's input.

### When to Use

- Task has **multiple phases with clear dependencies**
- A **pipeline of specialized roles** must collaborate in sequence
- **Quality gates** between stages ensure standards before proceeding
- Work spans **multiple sessions** and needs persistent progress tracking

### When NOT to Use

- All tasks are **independent** → use Parallel Dispatch
- A single Agent can complete the task alone
- No clear stage boundary exists
- Task is purely **iterative refinement** → use Iteration

### Workflow Definition

**1. Derive Stages from Intent:**
- Stage sequence: distinct phases
- Agent assignments: which role handles each phase
- Dependency graph: which stages depend on which
- Outputs: what each stage produces

**2. Generate AgentWorkflow JSON:**

```json
{
  "workflow_id": "<kebab-case-id>",
  "name": "<Human-readable name>",
  "stages": [
    {
      "stage_id": "...",
      "agent_kind": "...",
      "task": "...",
      "inputs_from": ["..."],
      "outputs": ["..."],
      "blockedBy": ["..."],
      "quality_gate": "..."
    }
  ],
  "handoff_protocol": "file-path-only",
  "progress_file": ".specify/teams/.work/<slug>/progress.md"
}
```

**3. Validate DAG (No Cycles):**
- Build adjacency list from `blockedBy` edges
- Detect cycles using topological sort
- If cycle → report path and ask user to resolve

### Stage Execution Protocol

```
For each stage in topological order:
1. CHECK: All blockedBy stages completed? (read progress file)
2. BUILD CONTEXT: Gather upstream output paths from inputs_from
3. INVOKE: Spawn subagent with agent_kind role
4. VALIDATE: Check outputs exist; run the stage's `quality_gate`
5. VERIFY HANDOFF: run a **simple verification** that this step's output is
   consistent with its predecessor's (the quality-first per-handoff gate) —
   on fail, apply Failure Recovery before unlocking downstream stages
6. RECORD: Update progress file
7. UNLOCK: Mark downstream stages as unblocked
```

> **Per-handoff verification is mandatory** in the serial pattern — it is what makes this the quality-first form. Keep it lightweight (a targeted check that the handoff artifact satisfies the downstream stage's `inputs_from` contract), not a full re-evaluation.

### Failure Recovery

| Strategy | When to Use | Action |
|----------|-------------|--------|
| **halt** | Critical failure | Stop, report, preserve state |
| **retry** | Transient failure | Re-invoke (max 2 retries) |
| **improve** | Quality gate failed | Invoke improve-agent on output |
| **skip** | Optional stage | Mark skipped, continue pipeline |

### Progress Tracking

Write to `.specify/teams/.work/<slug>/progress.md`:

```markdown
# Workflow Progress: <name>
**Workflow ID**: <id>
**Status**: in-progress | completed | failed | halted

## Stage Progress
| Stage | Agent | Status | Started | Completed | Output Path |
|-------|-------|--------|---------|-----------|-------------|

## Handoff Log
- [timestamp] stage_A → stage_B: Passed `<path>`
```

### Cross-Session Resume

1. Check if progress file exists
2. Parse stage table to determine state
3. Present status summary: "Workflow X is N/M complete. Resume?"
4. Continue from first non-completed stage

---

## § Iteration Pattern

> **iteration** reaches a goal **through iteration**, carrying the **convergence** meaning: it runs, scores, and iterates until the goal's threshold is met or a cap is hit, **then stops and delivers**. For a long-lived loop that keeps operating on a cadence, use **§ Continuous Operating Loop Pattern** instead.

**Priority: 目标收敛 (converge to the goal).** Orchestrate a **multi-Agent team** forming a self-iterating closed-loop system with two layers: a **Team Supervisor** (strategy + coordination, the single Meta role) and **Workers** (execution). The former Meta-Coordinator is merged into the Team Supervisor. This is a **bounded** loop — it converges then ends.

### When to Use

- Task requires **continuous quality improvement** through iteration
- Complex deliverables need **multiple specialized roles** collaborating
- **Automated quality gate control** is desired
- Task is too large or multi-faceted for a single Agent

### When NOT to Use

- Simple single-direction tasks with no feedback loop
- No clear quality standard or scoring criteria
- A single Agent can complete the task in one pass
- Purely sequential with no iteration → use Serial Chain
- Tasks are independent with no shared goal → use Parallel Dispatch
- Work is **long-lived / recurring** and must run on a cadence (never "done") → use **Continuous**

### Architecture

```
USER / GOAL
     │
     ▼
TEAM SUPERVISOR (Meta role — Strategy + Coordination Layer)
  • Define quality dimensions & thresholds
  • Decompose tasks; select & dispatch Workers
  • Monitor progress, adapt strategy
  • Score team output (multi-dimensional)
  • Decide: accept / improve / halt
     │
     ▼
WORKER AGENTS (Execution Layer)
  • requirements-analyst, ux-analyst, system-designer
  • module-designer, test-engineer
  • qa-engineer, knowledge-manager
```

### Team Initialization

1. **Define Team Goal**: Goal statement, deliverables, quality expectations
2. **Select Workers**: Choose from preset roles or create custom agents
3. **Configure Team Supervisor**: Task decomposition strategy, dispatch pattern, team roster, quality dimensions + weights, threshold (default: 0.8), max iterations (default: 5), regression limit (default: 2)

### Self-Iteration Loop

```
INITIALIZE:
  iteration = 0, best_score = 0, consecutive_regressions = 0

LOOP (iteration in 1..max_iterations):

  PHASE 1 — COORDINATE:
    Team Supervisor decomposes goal, assigns sub-tasks, selects dispatch strategy

  PHASE 2 — EXECUTE:
    Workers execute assigned sub-tasks, write deliverables
    IF goal optimizes a TARGET (a skill / implementation / config, e.g. config.optimization_target):
      (a) Workers/optimizers mutate ONLY the target (a working copy) — NOT the scored artifact directly
      (b) an executor then REGENERATES the scored deliverable from the source inputs
          BY APPLYING the current target (reload latest target; do not hand-edit the artifact)
      (c) so the score in PHASE 3 reflects the TARGET, not a hand-tuned proxy
    Team Supervisor monitors, handles failures, consolidates results

  PHASE 3 — EVALUATE:
    Team Supervisor scores the regenerated deliverable on each quality dimension
    Compute weighted_total, record in history

  PHASE 4 — DECIDE:
    IF weighted_total >= threshold → STOP (Success)
    IF iteration >= max_iterations → STOP (Max Reached)
    IF consecutive_regressions >= regression_limit → STOP (Regression)
    IF weighted_total > best_score → update best

  PHASE 5 — IMPROVE (if continuing):
    Team Supervisor generates improvement feedback, adjusts strategy,
    and triggers improve-agent on weak areas
```

> **Optimization-target invariant (`score = f(target)`) — mandatory whenever the goal optimizes a reusable target** (a skill, implementation, prompt, or config; e.g. `config.optimization_target`). The loop MUST optimize the **target**, not the scored artifact (the "proxy"):
> 1. Each iteration, optimizers edit **only the target** (a working copy of the skill/impl/config) — **never hand-edit the scored deliverable directly**.
> 2. An executor then **regenerates the deliverable from the source inputs by applying the current target** (reload the latest target each iteration — see the progressive strategy's "重载最新实现" in `references/optimization-goals.md §4`).
> 3. Score the **regenerated** deliverable. This guarantees the score measures the target's quality, closing the loop "improve target → regenerate from target → score → keep best target".
> 4. On success, the **adopted target** is the standard-output deliverable (persist to its real path); the regenerated artifact is a run intermediate.
>
> **Anti-pattern (do not do this):** optimizing the scored artifact directly (e.g. hand-editing the output diagram/file) and only distilling changes back into the target in batch at the end. That measures the *artifact*, not the *target* — the improvement loop for the target never actually closes. This applies to **both** the elimination and progressive strategies in `references/optimization-goals.md`.

### Convergence Detection

| Condition | Check | Action |
|-----------|-------|--------|
| **Quality Met** | weighted_total >= threshold | Accept — deliver best output |
| **Max Iterations** | iteration >= max_iterations | Stop — report best with warning |
| **Diminishing Returns** | consecutive_regressions >= regression_limit | Halt — restore best, warn user |

### Final Report

```markdown
# Iteration Report
## Outcome
**Status**: Converged | Max Reached | Regression Halted
**Final Score**: [weighted_total] / 1.0
**Total Iterations**: [count]

## Score Breakdown
| Dimension | Weight | Final Score | Trend |
|-----------|--------|-------------|-------|

## Iteration History
| Round | Score | Delta | Strategy | Key Changes |
|-------|-------|-------|----------|-------------|

## Deliverables
[File paths of best-scoring iteration's outputs]

## Lessons Learned
[Summary of effective strategies]
```

---

## § Continuous Operating Loop Pattern

**Priority: 长期运营 (operate the team long-term).** A **continuous** team is not "run once and finish" — it is a **long-lived operating loop** that runs on a **cadence** to keep handling a stream of incoming work or to keep maintaining/improving a quality over time. Where `iteration` converges then stops, `continuous` keeps running, cycle after cycle, and must be engineered to run **continuously and smoothly, without going out of control**. Its full operating discipline is the single source of truth in [`references/operating-loops.md`](references/operating-loops.md); this section is the orchestration summary.

### When to Use

- Work **arrives continuously** (CI failures, new PRs/issues, dependency updates) and needs periodic triage/action.
- A quality must be **maintained or improved over the long term**, not just brought to a bar once.
- You want the team to run **unattended-capable** on a schedule, with humans gating only the risky parts.

### When NOT to Use

- The goal is a **one-time** lift to a bar → use **Iteration**.
- No cadence / no recurring source of work → use one of the bounded patterns.
- No budget, constraints, or scoring can be defined — a continuous loop **without guardrails is unsafe**; define them first or stay at Iteration.

### Maturity Levels (start at L1, never skip)

| Level | Does | Guardrails required |
|-------|------|---------------------|
| **L1 — report** | discover + triage + score + write state; **no changes** | state spine + budget |
| **L2 — assisted** | minimal changes to small, well-scoped items; **independent verifier** gates; drafts for human review | L1 + constraints file + independent verifier + workspace isolation + attempt cap |
| **L3 — unattended** | auto-lands within the allowed scope; stops at boundaries for humans | L2 + full denylist + explicit human-handoff points + kill-switch + proven metrics |

Graduation is an `improve-team` action, gated on evidence (≥ 2 cadence cycles at L1 with < 20% high-priority false positives, verifier proven on manual fixes, constraints authored). **Do not skip L1 — the report phase is the calibration phase.**

### Per-Cycle Loop (one `run` = one cycle)

```
1. READ    read constraints.md + budget + kill-switch; kill-switch or ≥100% → exit now
2. BUDGET  sum today's spend; ≥80% daily cap → drop this cycle to report-only
3. TRIAGE  discover & prioritize source work; nothing actionable → early-exit (no-op, <5k tokens)
4. ACT     L1: write STATE only; L2+: minimal change per item (≤ max_attempts_per_item)
5. VERIFY  L2+: independent verifier (separate sub-agent, default REJECT, actually runs tests)
6. SCORE   score against quality_dimensions (measured against the goal)
7. CRITIQUE append a Post-Run Critique line to STATE.md; append one line to run-log.jsonl
8. REPORT  write runs/<UTC-timestamp>-report.md; update STATE.md Last cycle + prune resolved items
```

### Config (frontmatter `config`, continuous only)

```yaml
config:
  maturity: L1                 # start here; only improve-team promotes
  cadence: 1d                  # 1d | 2h | "cron: 0 8 * * 1-5"
  verifier: independent        # maker/checker, default REJECT (L2+)
  max_attempts_per_item: 3
  quality_dimensions: [...]    # Σ weights = 1.0
  threshold: 0.8               # per-cycle acceptance bar (L2+)
  budget: { max_cycles_per_day: 1, max_tokens_per_day: 100000, max_subagents_per_cycle: 0, on_80pct: report-only, on_100pct: halt }
  kill_switch: loop-pause-all
  constraints_file: .specify/teams/<slug>/constraints.md
  state_spine: .specify/teams/<slug>/STATE.md
  run_log: .specify/teams/<slug>/run-log.jsonl
```

### Directory (continuous extends the standard layout)

Beyond `team.md` + `runs/`, a continuous team's directory also holds tracked operating-spine files: `constraints.md` (§3 of operating-loops), `STATE.md` (cross-run memory), `run-log.jsonl` (append-only). Run intermediates still go only to git-ignored `.specify/teams/.work/<slug>/`.

### Stop / Halt (per cycle)

| Condition | Action |
|-----------|--------|
| Nothing actionable | Early-exit `no-op` (<5k tokens) |
| Spend ≥ 80% daily cap | Drop to `report-only` for the rest of the cycle |
| Spend ≥ 100% or kill-switch set | **Halt immediately**; one-line note to STATE.md |
| Item exceeds `max_attempts_per_item` | Escalate to human; stop retrying that item |
| Verifier REJECT / ESCALATE_HUMAN (L2+) | Discard the change; log; do not land |

---

## Shared Protocols

### File Handshake Protocol

All patterns use **file-path-only** communication:
- Agents write deliverables to designated paths
- Downstream agents receive ONLY file paths (not content)
- Never paste file content between agents — saves 50%+ tokens

### Progress Tracking

- Parallel: manifest files at `.specify/teams/.work/<slug>/parallel-result-<agent-id>.md`
- Serial: progress file at `.specify/teams/.work/<slug>/progress.md`
- Iteration: iteration history in the run workspace; final summary in the tracked run report
- Continuous: cross-run `STATE.md` + append-only `run-log.jsonl` in the team directory; per-cycle report under `runs/` (see `references/operating-loops.md`)

### Structured Returns from Loop Sub-Agents

In iteration/continuous loops, every dispatched sub-agent (optimizer, executor/renderer, scorer/evaluator) MUST finish by writing a small **structured result manifest** into the run workspace (e.g. `.specify/teams/.work/<slug>/gen-<N>/<role>-result.md` or `.json`), containing: `status` (done/failed), `output_paths` (file-path-only, no content), per-dimension scores (evaluators), and the single biggest improvement point observed.

- **Sub-agents never write tracked team files.** `runs/<ts>-report.md`, `team.md`, `STATE.md`, and `run-log.jsonl` are written **only by the Team Supervisor (orchestrator)**, which aggregates the manifests. Sub-agents run in isolated contexts — concurrent writes to tracked files race, a sub-agent cannot see sibling variants to aggregate them, and a partial write corrupts the durable record.
- The supervisor **validates each manifest before DECIDE**; a missing or empty manifest counts that variant/cycle as failed (it does not silently score zero-quality work as zero points).
- The scored deliverable path in the manifest is what the supervisor passes to the evaluator — evaluators read the artifact from that path, never from pasted content.

### Model Selection Guidance

| Sub-task Type | Examples | Recommended Tier |
|---------------|----------|-----------------|
| **Deterministic** | Template filling, format conversion | Light (fast, cheap) |
| **Judgment** | Code review, scoring, standard implementation | Standard |
| **Deep Synthesis** | Architecture design, novel algorithms | Heavy (high capability) |

### Hard Constraints

- **Territory validation MUST pass** before parallel dispatch
- **DAG validation (no cycles)** before serial chain starts; a **simple per-handoff verification** guards every serial step
- **Max iterations MUST be set** for iteration loops (default: 5, max: 10)
- **Continuous loops MUST start at maturity L1**, read `constraints.md` + budget + kill-switch at cycle start, honor the budget circuit-breaker (80% → report-only, 100%/kill-switch → halt), and use an **independent verifier** (default REJECT) at L2+ — see `references/operating-loops.md`
- **File-path-only handoff** — never paste content between agents
- **Context isolation** — each agent invocation is a fresh subagent; the continuous **verifier MUST be a separate sub-agent** from the implementer
- **Idempotent execution** — stages/iterations/cycles can be re-run safely
- **Run intermediates confined** to `.specify/teams/.work/<slug>/` (git-ignored); only declared final deliverables (standard output) persist to real target paths — never the team directory. Continuous teams additionally keep tracked `constraints.md` / `STATE.md` / `run-log.jsonl` in the team directory
- **Every run writes a dated report** to `.specify/teams/<slug>/runs/<UTC-timestamp>-report.md` per the Report contract

---

## Resources

| Path | Contents |
|------|----------|
| `${SKILL_HOME}/references/` | `conceptual-model.md` (Role × Stage × Type), `capacity-vs-responsibility.md` (which template set defines what), `goal.md`, `optimization-goals.md`, `operating-loops.md`, `teams.md` (preset mechanism + matching protocol) |
| `${SKILL_HOME}/templates/` | team-supervisor role template, the three EEI stage templates, the parallel/serial/triad orchestration templates, `agent-workflow-schema.md` |
| `${SKILL_HOME}/templates/teams/` | Predefined team shapes: `workspace-cluster.md`, `artifact-optimizer.md`, `process-monitor.md` |
| `${SKILL_HOME}/scripts/match-team-preset.py` | Deterministic preset matcher — scores a goal against every preset's signals and returns ranked JSON with a `confidence` verdict (`--help` for usage) |

## Agent-Specific Configuration

### Step 1: Identify Executing Agent

| Agent | Detection Signals |
|-------|-------------------|
| **Claude Code** | Tools include `Agent`, `Edit`, `Bash`, `Read`; `.claude/` directory exists |
| **GitHub Copilot** | Running in VS Code Copilot Chat context |
| **Qoder CLI** | `.qoder/` directory exists; `AGENTS.md` instructions loaded |
| **opencode** | `.opencode/` directory exists |
| **Qwen Code** | `QWEN.md` instructions loaded; `.qwen/` directory exists |

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

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At the end of a substantial run of this skill, perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this run reached a meaningful wrap-up. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against this skill's declared purpose and produce a short review plus ≥1 concrete, skill-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this skill's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id`; if a parent flow already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "skill:create-team" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
