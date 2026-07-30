---
name: improve-team
description: Adjust and optimize an existing agent team — add/remove members, change the collaboration pattern, tune thresholds/parallelism/quality dimensions, or operate a continuous loop (promote/demote maturity L1→L2→L3, tune budget/constraints/cadence/verifier) — with targeted, evidence-based, structure-preserving edits. Use when the user mentions ["调整团队", "优化团队", "优化 team", "修改团队", "升级成熟度", "降级成熟度", "调预算", "improve team", "adjust team", "refine team", "tune team", "promote maturity", "给团队增加", "给团队减少"]
skill_id: "<SKILL:.specify/skills/improve-team/SKILL.md>"
---

# improve-team

## Goal

Adjust and optimize an **existing** agent team. `improve-team` is the team-domain analogue of `improve-agent`, completing the create → improve lifecycle for teams. It loads a persisted team, makes **targeted, evidence-based, structure-preserving** edits (never a broad rewrite), re-persists the team, and reports what changed and why. The multi-agent Conceptual Model it operates against is defined once in `../create-team/references/conceptual-model.md`; the team **goal** concept in `../create-team/references/goal.md`.

Editing a team's **goal** is a first-class modify that **cascades into structure realignment** — follow `references/goal-editing.md`. For a **`continuous`** team, the operating discipline you tune (maturity level, cadence, budget/circuit-breaker, constraints file, independent verifier, state spine) is defined in `../create-team/references/operating-loops.md`.

Goal anchor (Constitution Principle XIII): this skill is a Better-Harness instrument — improving a team strengthens the **Controlled Execution** and **Reliable Delivery** dimensions (sound orchestration, independent verification, bounded autonomy) and closes the **Learning Capture** loop; goal model in `.specify/shared/guidelines/better-harness.md`.

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| target team | yes | Slug/name resolving to `.specify/teams/<slug>/team.md`. |
| improvement direction | yes | What to change: **redefine the goal** (cascades into structure realignment — see `references/goal-editing.md`), add/remove member, change pattern, tune thresholds/parallelism/dimensions, or — for a `continuous` team — **promote/demote maturity** (L1→L2→L3), tune budget/constraints/cadence, or fix verifier independence. |
| evidence | recommended | Normalized findings evidence from the **runs lane** (team run reports, Post-Run Critique notes, cycle logs — all consumed via `evidence-utils.py`, per `.specify/shared/workflow/evidence-step.md`): non-convergence, oscillating scores, territory conflicts, stale member references, budget overruns, false-positive rate, runaway token spend. |

## Behavior

1. **Resolve target** — load `team.md` from `.specify/teams/<slug>/team.md`. If none exists → report **"team not found"** and offer to **create** one (hand off to `create-team` via `/speckit.team create`). Never silently create a team.
2. **Gather evidence (evidence-step A/B)** — execute Step A/B per `.specify/shared/workflow/evidence-step.md`: reuse or collect findings via `evidence-utils.py --action latest|collect --target project --lanes runs,feedback`, then use the **runs-lane** evidence items (per-team run-report counts, critique notes, cycle/escalation signals) to identify convergence/oscillation, territory conflicts, and stale/broken member references before proposing changes. Triage by `evidenceState` and freeze the candidate list; `Unobserved` items are recorded only, never fixed.
3. **Attribute root cause** — map each issue to the responsible part (roster, pattern, config/thresholds, member territories/DAG).
4. **Apply targeted edits** — make the **minimal, evidence-based** change that fixes the issue while **preserving the parts of the team that already work** (SC-005). Do not touch unaffected fields — they must remain byte-identical.
5. **Re-persist** — write the updated `team.md` and **bump the `updated` date**; leave `created` and all unaffected frontmatter/members untouched. Run intermediates stay in the git-ignored workspace `.specify/teams/.work/<slug>/`; if editing a legacy team, repoint any stale `progress_file` there.
6. **Report** — list each change and the evidence that motivated it, and recommend a `run` to validate.

## Refinement Map (examples)

| Symptom | Likely cause | Team edit |
|---------|--------------|-----------|
| Iteration never converges | Threshold too high or conflicting dimensions | Lower threshold / rebalance `quality_dimensions` weights |
| Score oscillates | Ambiguous evaluator criteria | Tighten the evaluator rubric (via the moved stage templates in `create-team/templates/`) |
| Parallel file conflicts | Overlapping territories | Repartition `territories`; move shared files to forbidden-write |
| Serial stage stalls | Broken/missing handoff dependency | Fix `blockedBy` edges / handoff file path |
| Stale member | Agent renamed/deleted | Repoint or remove the member; surface the broken reference |
| Missing a role (e.g. no QA gate) | Roster gap | Add a member (e.g. a `qa-engineer`) without altering existing members |
| Goal drifted / team doing off-target work | Goal stale or never made explicit | Redefine the `goal` (verifiable form) and **realign** roster + pattern to it — see `references/goal-editing.md` |
| Goal changed from one-time to continuous | Requirement shifted to "keep improving" / recurring work | Switch the pattern from `iteration` to `continuous`; add `maturity` (start L1), `cadence`, `budget`, `constraints_file`, independent verifier — see `../create-team/references/operating-loops.md` |
| Continuous loop burns too many tokens / runs away | No budget or circuit-breaker | Add/tighten `budget` (daily cap, `on_80pct: report-only`, `on_100pct: halt`) + `kill_switch` |
| Continuous loop makes bad auto-changes | Jumped past L1, or verifier not independent | Demote `maturity` to L1 (report-only); make the verifier a **separate** sub-agent with a default-REJECT stance |
| Continuous loop ready for more autonomy | ≥2 L1 cycles, <20% false positives, verifier proven, constraints authored | Promote `maturity` L1→L2 (or L2→L3) per operating-loops.md graduation gates |
| Continuous `STATE.md` grows unbounded | Resolved items never pruned | Enforce per-cycle pruning of resolved/closed items in the state spine |

## MUST / MUST NOT

- MUST operate only on an **existing** persisted team; MUST NOT silently create one (on miss, report "team not found" and offer to create).
- MAY **redefine the team's `goal`** as a first-class edit, but only on an explicit goal-change request; MUST NOT change the goal as a side effect of restructuring. When the goal changes, MUST **realign** the roster + pattern to the new goal (see `references/goal-editing.md`).
- MUST make **targeted, evidence-based, structure-preserving** edits — no broad rewrites; unaffected fields stay byte-identical.
- MUST bump the `updated` date on every successful edit.
- MUST NOT modify single agents (that is `improve-agent`'s domain) beyond team-membership references.

## Outputs

- An updated `.specify/teams/<slug>/team.md` (with a bumped `updated` date) and a change report listing each edit and its motivating evidence.

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
     --unit-id "skill:improve-team" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
