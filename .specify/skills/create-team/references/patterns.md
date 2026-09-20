# Collaboration Patterns

Detailed reference for the four team collaboration patterns. The `SKILL.md` contract keeps the priority, summary boundary, and a pointer to this file.

---

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

## Parallel Dispatch Pattern

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

**Dispatch modality**: choose each member's execution mode per `.specify/shared/definitions/subagent-definitions.md` — **native** subagent when the runtime supports it, **virtual** (simulated in-session) when the tool has no subagent capability, **external** CLI process for long-running/parallel/isolated work. External dispatch MUST go through `scripts/dispatch.sh` (stream-json → compact filter → `.live.log`/`.jsonl`/`.status` triplet); silent `cli -p … > log 2>&1` dispatch is prohibited — a buffered log yields zero progress signal and defeats stall detection.

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

### Summary Boundary

After cross-verification and **Result Aggregation** complete, refresh the goal summary subject to the gate order in `SKILL.md` `## Summary Refresh`, and record the `Summary:` status line in the run report.

### Worktree Isolation (optional, config `isolation: worktree`)

Territory validation gives *logical* isolation; worktrees add *physical* isolation for teams whose members write real project files (not just report manifests). Enable by setting `isolation: worktree` in the team's `config`.

- **Dispatch**: each writing member runs in its own git worktree (dispatch the agent with worktree isolation; the runtime creates a branch per member from the default branch HEAD). Read-only members (evaluators, analysts) do NOT need worktrees.
- **Merge protocol**: the Lead — never a member — reviews each member branch (diff against base), then merges sequentially into the integration branch; territory validation still applies, so merges are conflict-free by construction. A conflict at merge time means territory validation was wrong — stop and repartition rather than resolving ad hoc.
- **Dirty-tree refusal**: never delete a worktree with uncommitted changes; surface it to the user (it may be salvageable work). Cleanup only after the branch is merged or explicitly discarded.
- **When to skip**: single-writer teams, report-only (L1) teams, and teams whose members write only into `.specify/teams/.work/<slug>/` gain nothing from worktrees — keep the default shared-tree dispatch.

### Monitoring

Monitor each agent's output manifest at `.specify/teams/.work/<slug>/parallel-result-<agent-id>.md`. For externally dispatched members, additionally watch `<label>.live.log` growth (bytes/lines) as the liveness signal — stalled growth counts toward the stall thresholds below.

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

## Serial Chain Pattern

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
4. VALIDATE: Check outputs exist; run the stage's quality_gate
5. VERIFY HANDOFF: run a simple verification that this step's output is
   consistent with its predecessor's (the quality-first per-handoff gate) —
   on fail, apply Failure Recovery before unlocking downstream stages
6. RECORD: Update progress file
7. UNLOCK: Mark downstream stages as unblocked
```

> **Per-handoff verification is mandatory** in the serial pattern — it is what makes this the quality-first form. Keep it lightweight (a targeted check that the handoff artifact satisfies the downstream stage's `inputs_from` contract), not a full re-evaluation.

### Summary Boundary

After each stage's **handoff verification passes**, refresh the goal summary subject to the gate order in `SKILL.md` `## Summary Refresh`, and record the `Summary:` status line in the run report. Two stage handoffs completing in rapid succession coalesce into one refresh.

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

## Iteration Pattern

> **iteration** reaches a goal **through iteration**, carrying the **convergence** meaning: it runs, scores, and iterates until the goal's threshold is met or a cap is hit, **then stops and delivers**. For a long-lived loop that keeps operating on a cadence, use **Continuous Operating Loop Pattern** instead.

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

**Mid-run requirement additions.** If the user adds requirements while a run is underway, the cutoff is **task-set finalization**: before the task set is finalized (during INIT / the first COORDINATE), merge the addition **and write it back to `team.md`** (e.g. extend `config.test_environment`) so the task set stays fixed across iterations; after finalization, take the addition as input to the **next run or `improve-team`** instead of mutating the task set mid-loop — otherwise scores stop being comparable across iterations.

**Per-run focus (optional).** A run MAY declare a focus (e.g. "功能全面覆盖" / coverage-first) that temporarily extends the task set or shifts per-dimension scoring emphasis for that run only. The Team Supervisor MUST record in the run report exactly how the focus changed the task set and the scoring basis — focused-run scores are not comparable with other runs' scores unless that delta is recorded; `team.md` itself stays unchanged.

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
> 5. When the target's content is a **workflow/mechanism** (a protocol, review process, self-feedback loop), the scored deliverable is **a record of actually executing that mechanism once** — the executor follows the protocol for real and produces either concrete evidenced changes or an explicit no-findings statement. A static reading of the mechanism text is not an evaluable artifact.
>
> **Anti-pattern (do not do this):** optimizing the scored artifact directly (e.g. hand-editing the output diagram/file) and only distilling changes back into the target in batch at the end. That measures the *artifact*, not the *target* — the improvement loop for the target never actually closes. This applies to **both** the elimination and progressive strategies in `references/optimization-goals.md`.

### Summary Boundary

After each generation's **DECIDE** phase completes, refresh the goal summary subject to the gate order in `SKILL.md` `## Summary Refresh`, and record the `Summary:` status line in the run report. A converged or capped run also produces the terminal summary.

### Convergence Detection

| Condition | Check | Action |
|-----------|-------|--------|
| **Quality Met** | weighted_total >= threshold | Accept — deliver best output |
| **Max Iterations** | iteration >= max_iterations | Stop — report best with warning |
| **Diminishing Returns** | consecutive_regressions >= regression_limit | Halt — restore best, warn user |

> **Delivery pre-check — score pass ≠ deliverable.** A passing `weighted_total` measures the quality dimensions, not structural integrity the dimensions don't cover (e.g. a new file never registered in its routing/index, dangling internal references). Before adopting, the Team Supervisor runs a structural-integrity check on the winning deliverable; on findings, append a **lightweight convergence round** scoped to only those structural fixes (not a full iteration), then adopt.

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

## Continuous Operating Loop Pattern

**Priority: 长期运营 (operate the team long-term).** A **continuous** team is not "run once and finish" — it is a **long-lived operating loop** that runs on a **cadence** to keep handling a stream of incoming work or to keep maintaining/improving a quality over time. Where `iteration` converges then stops, `continuous` keeps running, cycle after cycle, and must be engineered to run **continuously and smoothly, without going out of control**. Its full operating discipline is the single source of truth in `references/operating-loops.md`; this section is the orchestration summary.

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
9. SUMMARIZE refresh the GOAL's summary when the gates allow (budget → cadence → material);
             record the outcome as a `Summary:` status line in this cycle's report.
             Runs AFTER REPORT because the report is one of its provenance sources.
             See SKILL.md `## Summary Refresh`.
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
| Goal met / converged / halted / stopped by a human | Produce one **terminal summary** before wrapping up, unless the budget is already exceeded |
