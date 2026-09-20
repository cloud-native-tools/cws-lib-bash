# Team Definition & Persistence (create mode)

Detailed guide for `/speckit.team create`. The `SKILL.md` contract keeps the skeleton; this reference holds the full procedure, schema, and persistence rules.

---

## Goal-first procedure

Produce a team from a user **goal** and (unless one-shot) persist it as `.specify/teams/<slug>/team.md`. The goal is the team's north star — **establish it first, then derive both structures from it** (goal concept: `references/goal.md`).

1. **Establish the goal (first)** — extract the goal from `$ARGUMENTS`/conversation/repo context, ask if missing (elicitation is fine; a blocking confirmation of the final goal is not); write it in a **verifiable** form (success criteria / threshold). When the goal is missing or too vague to derive a roster and pattern from, elicit it via the interview pattern (`.specify/shared/patterns/interview-pattern.md`) instead of one flat question — ask the settled-prerequisite decisions in a round as **open** questions carrying their context (no option menus, no recommended answers: the goal is the user's to state), write each answer into the goal statement before the next round, and stop at the user's confirmation that the goal is stable (访谈退出门为固有交互,保留). If no live user is available, say the goal is unestablished and stop; never invent one. Goal semantics — the project-level Goal concept, one-goal-per-team singularity, criteria authority, and the `goal_slug` binding — are defined once in `.specify/shared/definitions/goal-definitions.md`. If the goal's theme is **optimization**, classify it (one-time vs continuous) and pick a strategy (elimination vs progressive) per `references/optimization-goals.md`.
2. **Match against team presets (before deriving anything)** — run `${SKILL_HOME}/scripts/match-team-preset.py --goal "<goal text>"` and act on the returned `confidence`: `high` → present the top preset (goal skeleton + roster + pattern) and **recommend reuse**; `medium` → present the top 2 candidates alongside the from-scratch option; `low`/`none` → say no preset matched and continue to step 3. Presets are known-good shapes distilled from teams that actually ran — reusing one is what keeps a vague goal from producing an arbitrary team. Never instantiate a preset silently, and never let it override an explicit user instruction. See `references/team-presets.md`.
3. **Select the pattern** via the Pattern Selection decision tree (`references/patterns.md`) — independent → parallel; sequenced → serial; iterative-quality → iteration; long-lived operation → continuous — **derived from the goal**. On preset reuse, the preset supplies the pattern; still verify it fits.
4. **Build the roster (static structure)** — a Role × Stage × Type matrix. If the user did not supply members, **propose** them from the goal: prefer existing agents under `.specify/agents/{templates,instances}/`, otherwise temporary stage/worker templates from `templates/`. An **iteration or continuous team MUST include exactly one Team Supervisor** (Meta role). **Judge each member's `type` explicitly by its operating object** — operates on business artifacts/information → `Worker`; operates on other agents/skills/agent-defining configuration → `Meta`. Do **not** derive Type from Stage: an evaluator scoring a business artifact (repo state, rendered output, a document) is a `Worker`, not Meta. The implication runs **one way only**: a member that must **write** team config / agent definitions / skill definitions MUST be `Meta` (necessary); but holding an evaluator / optimizer / "continuous improvement" role does **not** by itself make it Meta (not sufficient) — an agent that iteratively improves a *business artifact* is still a `Worker`. Decide each member's Type from **what it writes to**, never from its role name (see `references/conceptual-model.md` → Type criterion + "Meta and write authority"). Roster rows carry **responsibility** (stage, territory, `blockedBy`, reporting duty); the referenced agent carries **capacity** — never fork a capacity artifact to express a new seat (`references/capacity-vs-responsibility.md`).
5. **Build the pattern config (dynamic structure)** — parallelism + territories (parallel), DAG `blockedBy` edges + per-handoff verification + file-path-only handoff (serial), quality dimensions + threshold + max_iterations + regression_limit (iteration), or the operating config — maturity + cadence + budget + constraints + independent verifier + state spine (continuous; see `references/operating-loops.md`).
6. **直接落盘并呈现** — persist the `Team` **directly** to `.specify/teams/<slug>/team.md` using the schema below (skip persistence only for an explicit one-shot run;不设阻塞式停等), including the schema’s compact `## Self-Improvement Contract`; then present the persisted **goal** + roster + pattern with the modification path (`/speckit.team` modify / `improve-team`) per the execution-report convention. When a preset was reused, record `preset: <preset_id>` in the frontmatter and apply the preset's `## Instantiation` steps (including any `constraints.md` / `STATE.md` bootstrap).

---

## Goal-based create branch

When the user's input names an **already-defined goal**, create runs through this branch instead of re-eliciting the goal as free text. Concept anchor: `.specify/shared/definitions/goal-definitions.md` (Goal / Target / binding — linked, never restated).

1. **Recognize (deterministic, zero semantic guessing)** — run `python3 scripts/python/goal-utils.py list --json` for the archive slug set; a token that **exactly matches** a slug (or a path to its `goal.md`) enters the branch directly (the verdict is disclosed in the output, not gated). Near-misses (case/hyphen variants) are **not** hits; no match → continue with the free-text procedure above, unchanged. The verdict comes from the engine enumeration, never from agent memory.
2. **Load and restate** — read the definition via `parse_goal` (`scripts/python/goal-utils.py`): objective, criteria (including the `None provided.` missing state), status, targets, history; restate to the user (non-blocking presentation).
   - **Dangling reference** (user names a slug absent from `list`): error with the verbatim prefix `goal 未定义:`, pointing to `/speckit.goal create`; zero artifacts, zero writes — MUST NOT silently degrade to inline goal creation.
   - **Terminal goal** (`achieved`/`abandoned`): report the terminal state explicitly and refuse to create. Both rejections stop without needing confirmation — they are stops, not writes.
3. **Four-element analysis (advisory, not a gate)** — present before any derivation, each element with rationale: **维度** (the plane the goal's object lives on), **判据覆盖** (criteria listed, or the missing state declared — never invented), **既有 Target** (open/done/dropped inventory — the reuse baseline), **可达成性** (single-team short-term achievable vs broad-needs-decomposition, conclusion + basis). The conclusion is a recommendation: the user adjudicates single-team vs decomposition; forcing single-team on a broad goal is not blocked, but the adjudication is recorded in the presentation and execution report.
4. **Decomposition proposal & batch approval (decomposition path)** — when the analysis says broad and the user adjudicates decomposition:
   - **Drafting discipline** — each candidate is an outcome-form statement (GD-2 slice scale) subordinate to the same goal; a candidate that stands alone as an independent end-state is directed to **another goal** (GD-3 litmus) and leaves the proposal set; MUST NOT restate the goal's success criteria or any spec's SC-xxx. The set is **unordered** — no dependency edges, no numbering semantics; identities are issued monotonically by the engine at landing time.
   - **Dry-run validation** — before presentation, run `python3 scripts/python/goal-utils.py targets <slug> --check "<candidate>"` per statement (zero writes; same-source validators as `--add`). Every statement MUST pass (exit 0) before it is presented; rejected entries are rewritten and rechecked or dropped.
   - **Presentation** — one `分解提议` section presents the full set: each statement + its rationale + the `--check` verdict.
   - **Approval & landing** — one **merged ratification** (full set presented once → single user adjudication; propose→ratify decision semantics unchanged) covers the whole set; then execute `targets <slug> --add` **per statement**. Each verdict is respected immediately: an exit-2 rejection is reported verbatim → revise and re-run `--check` before resubmitting, or explicitly abandon; never bypass the engine, never hand-write `## Targets`.
   - **Reuse baseline** — existing Targets are the baseline: `open` entries are reused directly (they become the group-creation objects); semantically duplicate statements are never re-authorized; `done`/`dropped` entries are shown but their identities are never reused and they are never reopened in passing (reopen only via `/speckit.goal targets --set open`, human-initiated). Proposals only fill gaps; an empty proposal set goes straight to group creation.
   - **Mid-abort** — landed entries are kept (they are legal authorizations), the rest are dropped; a re-run reuses the baseline with zero duplicate authorization.
5. **Single-team path (adjudicated)** — derive roster + pattern with the loaded goal narrative as input through the existing machinery (step 2 preset matching + step 3 pattern tree of the procedure above); derivation reasons MUST enter the pre-execution presentation; a strong preset match recommends reuse.
6. **Group creation path (N teams : 1 Goal)** — after decomposition approval (or when the reuse baseline already holds), create one team per open Target:
   - every team declares the **same `goal_slug`**; `focus_target: T-<nnn>` points at that team's slice (**inserted after `goal_slug`** in the frontmatter order below); before landing, the field MUST exist in the bound goal's `## Targets` and be `open`, otherwise creation is refused;
   - roster + pattern derive from the **Target statement** through the existing machinery (`match-team-preset.py --goal "<statement>"` + pattern tree); derivation reasons enter the pre-execution presentation;
   - team slug derives as `<goal-slug>-t<nnn>` (lowercase, zero-padded three digits, e.g. `log-split-t003`), checked for uniqueness against `.specify/teams/`; collisions are auto-rewritten and echoed (rename afterwards via modify if desired — never blocks landing);
   - **territory discipline** — present a pairwise-disjoint territory proposal based on the slices; before landing run `python3 skills/create-team/scripts/verify-territory-disjoint.py --input <proposals.json> --json` (proposed ∪ existing same-`goal_slug` teams): `exit 0` → land; `exit 4` → disclose the contested/undeclared parties, re-divide and re-run, or hand off to `/speckit.goal coordinate` — never silently land a known overlap. When other teams already exist under the goal, the single-team path MUST run the same verify;
   - the **pre-persist disclosure (non-blocking)** presents in one place: the branch verdict, the analysis conclusion, the path decision, the proposal set or reuse statement, and the territory division (with the verify verdict) — then team.md lands directly and is presented with its modification path. Existing teams under the same `goal_slug` (scan `.specify/teams/*/team.md` frontmatter) MUST be detected and offered for reuse or handed to `/speckit.goal coordinate` — never duplicate silently.
7. **Landing invariants** — frontmatter declares `goal_slug` (reference, not a content copy); an inline `goal` field, if kept, is readability rendering only — the definition is authoritative, and any mismatch is surfaced for human adjudication, never forked into a second authoritative narrative. The branch writes `team.md` only; it performs **zero writes to `goal.md`** (`## Targets` / `## History` are rendered only by the `/speckit.goal` engine).

---

## Persisted `team.md` schema

Each persistent team owns a **directory** `.specify/teams/<slug>/` (no per-tool symlink — framework-internal). The definition is stored at `.specify/teams/<slug>/team.md`; per-run reports accumulate under `.specify/teams/<slug>/runs/`:

```markdown
---
name: <display name>
slug: <kebab-slug>
description: <one-line label>
goal: <overall final objective + success criteria / threshold>
goal_slug: <kebab-slug>        # optional — the GOAL's identity; distinct from `slug` (the team's identity). See references/summary-mapping.md
focus_target: T-<nnn>         # optional (042) — the team's default focus Target under the bound goal;
                               #   a PREFILL of run-level --target: explicit --target always overrides, a run without
                               #   --target resolves to it (disclosed as "(团队默认)"). NOT a write-scope claim, NOT a
                               #   Goal–Team binding change. Written by goal-based create and modify (improve-team);
                               # at creation it MUST reference an existing OPEN Target of the bound goal.
territory:                     # optional — TEAM-level coverage; all four patterns. Lifts member Territory Division one level up
  write:                       #   paths this team may create/modify (glob / brace / relative all normalised before compare)
    - <path-or-glob>
  read:                        #   paths this team may read (read overlap between teams is allowed)
    - <path-or-glob>
  forbidden:                   #   shared paths this team MUST NOT modify
    - <path-or-glob>
  non_path:                    #   coverage that is not file-shaped (framework itself, runtime, …); listed for arbitration, never intersected
    - { type: <dimension>, target: <free text> }
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
  # optimization goals: optimization_target (single target path), or co_targets
  # (coordinated multi-target optimization — list of target paths + the layering
  # principle stating which kind of content belongs to which target; see
  # references/optimization-goals.md)
  summary:                     # optional — omit the block entirely and summary is still ENABLED (opt-out)
    enabled: true
    every: 5                   # refresh once per N phase boundaries; continuous default 5, bounded patterns 1
    delivery_dir: .specify/goal/<goal-slug>/summary/   # derived from goal_slug, never from the team slug
    interactive: false         # team-triggered refresh is automated → invoke the skill non-interactively
---

## Goal
<the team's overall final objective + success criteria; authored FIRST — the static and dynamic sections are organized to serve it. See references/goal.md>

## Static Structure
<Role × Stage × Type matrix table for this team's roster>

## Dynamic Structure
<pattern description, parallelism/DAG/loop settings, and the execution flow diagram.
 For iteration/continuous patterns this section MUST end with an explicit Loop Card
 (WHEN→SEE→DO→CHECK→STOP→LEAVE table): WHEN = trigger/cadence, SEE = state read first
 (STATE.md/constraints), DO = the bounded unit per cycle, CHECK = concrete verification
 (evaluator command/criterion), STOP = termination condition + hard caps
 (threshold/max_iterations/budget/kill-switch), LEAVE = what is persisted/handed off
 (runs report, STATE update, escalations). A loop whose CHECK or STOP cannot be
 stated concretely is not ready to persist.>

## Self-Improvement Contract

- Subject: this persisted team definition; member executions are evidence.
- Observe: completed run reports and Post-Run Critique.
- Improve: follow `.specify/shared/workflow/self-improvement-workflow.md`; route through `improve-team`.
- Boundary: preserve team authority, maturity gates, budget, kill-switch, and verifier independence.
- Verify: validate now and wait for a comparable later run before claiming improvement.
```

### Schema notes

- `slug` MUST be unique within `.specify/teams/`; it also names the team directory `.specify/teams/<slug>/`.
- `goal_slug` identifies the **goal**, not the team — it is deliberately a different axis from `slug` (the team slug). Two teams that declare the same `goal_slug` are pursuing one goal and share one summary; a team that omits it falls back to its own `slug` as an *inferred* goal identity. It MUST NOT be derived from the goal prose, so rewriting the goal text never relocates the summary. See `references/summary-mapping.md`.
- `territory` is the **team-level** coverage declaration and applies to all four patterns (the member-level Territory Division lifted one level up). An absent key means **undeclared** — never conflated with an empty scope. Path entries are normalised (brace-expanded, canonicalised) before comparison. Among teams sharing one `goal_slug`, no two `write` scopes may intersect (read overlap is allowed); a write intersection is a **contested area** that must be resolved to a single owner or a forbidden-write entry. The refresh only **detects and proposes** a re-division — a human ratifies it and the agreed scopes are written back into each `team.md`, never into the goal directory.
- `config.summary` tunes the periodic summary refresh (enable/disable, cadence, delivery directory, interactivity). Omitting the block leaves the summary **enabled** with the pattern's default cadence — `continuous` defaults to every 5th cycle, never every cycle.
- `members` MUST resolve to `.specify/agents/{templates,instances}/<slug>.agent.md` (instance wins on filename collision) or a temporary stage/worker template; unresolved members are surfaced as broken references.
- `config` MUST match `pattern`.
- Every persisted team MUST contain `## Self-Improvement Contract` exactly once. A one-shot team MUST NOT claim subject identity.
