# Goal Definitions Reference

Canonical definition of the **Goal** concept in Spec Kit, its boundary against **Requirement**, the criteria authority rule, the singularity rule, the **Target** decomposition, and the Goal–Team binding. This file is the single source of truth for the Goal concept; other documents (`/speckit.team`, `skills/create-team`, the glossary) link here rather than re-defining it. It sits alongside the other concept anchors: `tool-definitions.md`, `agent-definitions.md`, `subagent-definitions.md`.

## What a Goal Is

A **Goal** is a **project-level, first-class concept**: an **authored fact source** (never a derived artifact) that states a desired end state and how to tell it has been reached. Its **object is unrestricted**: a Goal may describe any desired outcome in any dimension — it is not limited to what the project's code implements (see Goal Dimensions below). It is persisted under `.specify/goal/<goal-slug>/` and is composed of exactly three parts:

1. **Goal narrative** — the desired end **outcome** (north star). Outcome, not steps: a Goal MUST NOT be written as a task list or an implementation plan.
2. **Verifiable success criteria** — thresholds / satisfaction conditions that an evaluator (a program or a scoring agent) can measure progress against.
3. **Lifecycle state** — `active` / `achieved` / `abandoned`. Terminal Goals are retained, never deleted (see Goal Archive).

A Goal MAY additionally carry a **Target decomposition** (see Target Decomposition below). Like timestamps, Targets are an **annex** around the concept — never a fourth composition part.

Two operating properties follow:

- **Measured by degree**: a Goal is *pursued*; its verification is progress-shaped (percentage, threshold attainment, evaluator scores) — not a per-clause pass/fail.
- **Modified deliberately**: changing a Goal is a strategic act — the change is recorded and history is preserved; silent drift is prohibited.

### Goal Dimensions (illustrative, not a closed taxonomy)

Goals and Requirements live on **different planes** (decided 2026-08-04): a Requirement describes what the **current project's source code or configuration** must implement (a feature); a Goal may target **any dimension** of desired outcome, including ones no Requirement could ever express. Illustrative dimensions:

| Dimension | Example Goal | Why it is not a Requirement |
|-----------|--------------|-----------------------------|
| **Framework / harness itself** | "I want the spec-kit framework this project uses to stay continuously updated" | Its object is the toolchain, not this project's code — no FR on this repo can implement it |
| **Codebase-wide convention convergence** | "I want all project source code to be standard-idiomatic Golang" | A cross-cutting end state pursued by degree across the whole codebase, not a per-feature clause |
| **Delivered-capability outcome** | "I want feature X to run on platform Y" | An outcome about a capability in a target environment; Requirements specify the implementation, the Goal states the environmental end state being pursued |

Boundary note: when a dimension-2-style desire is frozen into a **binding rule** enforced by gates, it belongs to the **Constitution** (a governance principle); when it binds one deliverable as a testable clause, it is a **Requirement**; when it is a desired end state pursued and measured **by degree**, it is a **Goal**. The same sentence can move between the three homes only by deliberately changing its nature.

## Goal vs Requirement

**Goal** and **Requirement** are independent, parallel first-class concepts on **different planes** — **there is no necessary hierarchy between them** (decided 2026-08-04). A Requirement's object is fixed: this project's source code / configuration and the feature they implement. A Goal's object is free: any dimension of desired outcome.

| Dimension | Goal (目标) | Requirement (需求) |
|-----------|------------|--------------------|
| Object (作用对象) | Unrestricted — framework/harness, codebase conventions, delivered-capability outcomes, … (any dimension) | The project's source code / configuration — what feature they must implement |
| Essence | Desired end state + attainment criteria | Binding clauses on a deliverable |
| Question answered | *why / whither* — toward what, to what degree | *what / how-correct* — what MUST hold, what counts as done right |
| Home | `.specify/goal/<goal-slug>/` (authored fact source) | `.specify/specs/<ID>-<slug>/requirements.md` (bound to one Feature) |
| Shape | Singular narrative + criteria per Goal | Enumerated clauses (FR-xxx / SC-xxx) |
| Verification | By degree — progress, thresholds, evaluator scoring | Binary — per-clause pass/fail against tests and acceptance scenarios |
| Change discipline | Deliberate modification with recorded history (no silent drift) | Clarification/revision flow (Clarifications sessions, re-gated spec) |
| Failure semantics | Not yet attained → keep iterating / adjust strategy / deliberately re-scope | Not satisfied → implementation non-conforming, delivery blocked |
| Anti-pattern | Written as a task list / implementation steps | Written as an untestable aspiration |

**No structural link (decided)**: a requirements spec carries **no** Goal field — `requirements.md` does not reference a `goal-slug`, and a Goal never enumerates the FRs "under" it. When work on a Feature happens to advance a Goal, that connection surfaces **observationally** — in evaluation results, team summaries, and run reports — never as a mandatory field in either artifact. Neither concept derives from, contains, or validates the other.

**Litmus tests** (when writing a sentence, decide where it belongs):

1. **Deletion test** — deleting it loses *direction* → Goal; loses a *contract* → Requirement.
2. **Verification test** — verifying it needs scoring/progress → Goal criterion; needs a pass/fail check → Requirement clause.
3. **Change test** — changing it is a strategic decision with history → Goal; a clarification + spec revision → Requirement.
4. **Subject test** — the sentence's subject is an executing subject ("the team reaches …") → Goal; a system/deliverable ("the system MUST …") → Requirement.
5. **Object test** — it constrains what this project's source/config implements → Requirement; its object lies beyond the implementation surface (the framework itself, codebase-wide convergence, runtime/platform outcomes) → Goal.

## Criteria Authority Boundary

Success-shaped statements exist in both worlds; their authority is disjoint (decided 2026-08-04):

- **SC-xxx** (Success Criteria in a requirements spec) serve **only their own Feature** — they measure that Feature's delivery and nothing broader.
- **Goal success criteria** are **cross-feature** — they measure the end state regardless of which Features contributed.
- Criteria MUST NOT be copied between the two stores. Cross-feature aggregation happens at the **evaluation/summary layer** (evaluators, team summaries), with each side citing its own source — never by restating one store's criteria inside the other.

## Singularity Rule

One Goal = one objective (decided 2026-08-04):

- **Per Goal definition**: a Goal MUST NOT bundle several objectives into one composite definition — split them into separate `goal-slug`s, each with its own directory and lifecycle.
- **Per executing subject**: a team binds to exactly **one** Goal at a time (see Binding below). A team that "pursues two goals" is either two teams or a Goal that needs deliberate re-scoping.
- The **project** may hold multiple `active` Goals concurrently — each is its own `goal-slug`, each advanced by its own team(s).
- Decomposing one objective into **Targets** (see Target Decomposition below) does not breach singularity: Targets are slices of the same objective, never additional objectives.

## Target Decomposition (目标切片)

A **Target** is a **sub-outcome under exactly one Goal**: an independently advanceable, completion-judgeable **scope slice** of the same end state (decided 2026-08-11; operational surface specified by requirement `038-goal-target`). Targets give the Goal — a large, slow-moving concept — a **run-sized control point**: a team run can be pointed at one Target without touching the Goal–Team binding, the Goal's identity, or the summary delivery directory.

```
Goal (authored end state)  1 ── N  Target (run-assignable scope slice)  1 ── N  runs / work items (TI-xxxx)
```

Four defining properties:

1. **An annex, never a fourth part.** The decomposition is optional: a Goal without Targets is fully valid and behaves exactly as if the mechanism did not exist. Adding Targets changes neither the narrative, nor the criteria, nor the lifecycle.
2. **Outcome-shaped, recursively.** GD-2 applies at Target scale: each Target states a sub-**outcome** ("log component split complete"), never a step. The Target set is an **unordered set** — identity ordinals carry no execution-order semantics; an ordered target list is an implementation plan wearing a goal's clothes.
3. **Subordinate, not independent.** GD-3 litmus at this boundary: a Target must be a slice of its parent objective. A candidate that would stand as a meaningful end state of its own is a separate Goal — split it, do not nest it.
4. **A tree, not a graph.** A Target belongs to exactly one Goal; 1 Goal : N Targets; N runs : 1 Target. Cross-goal Targets do not exist, and Targets carry no dependency edges between them.

**Identity.** Local form `T-<nnn>` — issued monotonically within the goal, never reused. Qualified form `<goal-slug>.T-<nnn>`, dot-namespaced after the `<team-slug>.TI-<nnnn>` precedent and legal under the shared identity grammar (which admits `.` but not `#` or `/`). Lifecycle is exactly `open` / `done` / `dropped`; terminal Targets are retained with their state, never deleted.

**Two progress axes — never conflate.** Success criteria measure **end-state attainment** and remain the sole authority for `achieved`. Targets measure **scope coverage** (n of m slices done). All Targets complete does NOT make a Goal achieved; criteria are never derived from Targets, and Targets never restate criteria (the criteria authority rule extends to Target statements). At the summary layer, milestones (`MS-<nnnn>`) remain criteria projections; completed Targets MAY additionally feed milestone entries under a distinct source marker — a presentation-layer concern owned by the summary mapping, not by this definition.

**Write model — authored lifecycle, derived progress.**

- *Authored*: a Target's statement and its deliberate lifecycle live inside the Goal's definition file (a `## Targets` section; exact layout owned by the implementing feature) and are written **only via `/speckit.goal`** — the sole-authoring-entry rule is unchanged. Teams and runs may **propose** Targets or completions; a human ratifies through `/speckit.goal` (propose → ratify, as in `coordinate`).
- *Derived*: per-Target execution progress is folded from team ledgers (`items.jsonl` rows carrying a `target_ref`) at summary time and is never written back into `goal.md`. When authored state and evidence disagree (state `open`, yet every attributed item is complete), the discrepancy is surfaced for ratification — never auto-flipped.

**Run assignment.** A team run MAY name one Target under the team's **bound** Goal. The reference is validated — a dangling or terminal Target is reported, never silently accepted — and a run that names no Target runs against the Goal broadly, exactly the pre-Target behavior. Work items attribute to the Target through the ledger's `target_ref`.

## Storage & Goal Archive

```
.specify/goal/
└── <goal-slug>/     # one Goal definition — narrative + criteria + lifecycle state
```

- **Goal Archive** = the whole `.specify/goal/` tree: the materialized "current & historical goal list" of the project. Terminal (`achieved` / `abandoned`) Goals stay archived — never deleted.
- This document fixes only the **location and semantics**; the file layout inside `<goal-slug>/` is owned by the feature that implements Goal management.

## Goal–Team Binding

- A team references its Goal by **one-way identity**: the team declares a `goal_slug`; the binding is **N teams : 1 Goal**. The team side stores the identity only — never a copy of the Goal content.
- **Team Goal** therefore means *the reference* — which project-level Goal this team serves. Team evaluators measure progress against the referenced Goal's criteria.
- **Migration fallback**: teams created before Goal management exist may still carry an inline goal in `team.md`; wherever a Goal definition exists, the definition is authoritative and the inline copy is legacy.
- **Run-level Target assignment**: the binding axis stays team ↔ Goal and stays static. The run-sized variable is the **Target**: a run may select one Target **inside the bound Goal** — this never rebinds the team, never alters goal-identity resolution, and never relocates the summary delivery directory. See Target Decomposition.

## Terminology Boundaries

| Term | Meaning | Where defined |
|------|---------|---------------|
| **Goal** (this document) | Project-level authored end-state definition (narrative + criteria + lifecycle) | here; store `.specify/goal/<goal-slug>/` |
| **Goal Archive** | The `.specify/goal/` tree — current & historical Goals, terminal ones retained | here |
| **Goal–Team Binding** | One-way `goal_slug` reference, N teams : 1 Goal, identity-only | here |
| **Team Goal** | A team's reference to the project-level Goal it serves | here; declared in `.specify/teams/<slug>/team.md` |
| **Requirement** | Feature-bound spec of testable clauses (FR/SC) driving plan → tasks → implement → verification | `.specify/specs/<ID>-<slug>/requirements.md`; `/speckit.requirements` |
| **Feature** | Long-lived capability entry in the feature index | `.specify/memory/features.md` |
| **Success Criteria (SC-xxx)** | Per-feature measurable outcomes — authority limited to their Feature | requirements spec of that Feature |
| **Team** | Multi-agent structure organized around (exactly one) Goal | `/speckit.team`, `skills/create-team` |
| **Target** (this document) | Run-assignable sub-outcome (scope slice) under exactly one Goal — an annex to the definition, unordered, authored via `/speckit.goal` | here; persisted in `.specify/goal/<goal-slug>/goal.md` (`## Targets`) |
| **`target_ref`** | A ledger work item's attribution to a Target (`T-<nnn>`) | `items.jsonl` contract (`skills/create-team`, summary mapping) |
| **"target" elsewhere** | `optimization_target` / `co_targets` (the artifact an iteration loop mutates), a territory entry's `target` field, the `--target` flags of the evidence/interview engines — all **unrelated** to Goal Targets | their owning docs; glossary disambiguation |
