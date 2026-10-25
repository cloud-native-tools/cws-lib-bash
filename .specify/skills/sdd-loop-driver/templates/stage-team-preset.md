---
preset_id: sdd-stage-team
name: SDD Stage Work-Package Team
pattern: parallel
summary: Run one SDD stage as bounded work packages coordinated by the driver, with independent verification and deterministic integration.
when_to_use: The driver reaches a stage that passes the Work Package decomposition gate and needs coordinated read-only parallelism with serialized writes.
signals:
  - sdd stage work packages
  - subagent task decomposition
  - stage team preset
inputs:
  - name: stage
    required: true
    description: Canonical stage name (plan, implement, review; analyze/clarify only on explicit opt-in).
  - name: wp_graph
    required: true
    description: The admitted Work Package plan (packages, dependencies, pattern, slot cap).
  - name: line
    required: true
    description: Line label and state-spine path for the run.
  - name: slot_cap
    required: false
    description: Read-only concurrency cap; defaults to 2 and is capped by the line's remaining allowance.
members:
  - role: stage-planner
    stage: executor
    type: Worker
    lifecycle: persistent
    responsibility: Derive and own the stage Work Package plan and its acceptance boundaries (the driver itself).
  - role: stage-worker
    stage: executor
    type: Worker
    lifecycle: temporary
    responsibility: Execute exactly one Work Package inside its owned paths, budget, and evidence contract.
  - role: stage-verifier
    stage: evaluator
    type: Worker
    lifecycle: temporary
    responsibility: Independently verify settled Work Packages; never the executor of the package being verified.
  - role: stage-integrator
    stage: executor
    type: Worker
    lifecycle: temporary
    responsibility: Aggregate verified outputs in the declared order, make the single stage-closing commit, and emit the stage sentinel.
config:
  default_pattern: parallel
  pattern_selection: parallel only when every package is read-only and two or more packages are independent; serial when any write package or any dependency edge orders the work; iteration only for a bounded repair_loop with an explicit maximum; continuous is never selected.
  slot_cap_default: 2
  slot_cap_ceiling: "min(4, the line's remaining concurrency allowance owned by Feature 064)"
  write_packages: dispatched alone (effective concurrency 1)
  verification: one fresh-context verifier execution per Work Package
  retry: at most one automatic retry per Work Package; the retry must change scope, budget, or topology
  persistence: run-scoped only; never .specify/teams/<slug>/team.md
provenance: Feature 070 clarify 2026-10-24; shape derived from the measured baseline in the 070 brief and the existing Role × Stage × Type vocabulary, not from a create-team catalog run. First-run provenance is attached when the first decomposed stage closes (its coordination report path is recorded in the spine).
---

# SDD Stage Work-Package Team

## Goal Skeleton

Run exactly one SDD stage as bounded Work Packages: the driver derives and gates the plan, dispatches the ready packages, verifies every package independently, integrates the verified outputs in the declared order, and then runs the unchanged stage sentinel and U4 checks.

## Static Structure

| Seat | Stage | Type | Lifetime | Filled by |
|------|-------|------|----------|-----------|
| `stage-planner` | executor | Worker | persistent | the driver itself |
| `stage-worker` | executor | Worker | temporary | one execution per Work Package |
| `stage-verifier` | evaluator | Worker | temporary | one fresh-context execution per verdict |
| `stage-integrator` | executor | Worker | temporary | one execution per decomposed stage attempt |

The roster defines exactly these four seats. `stage-planner` is the driver itself: it decomposes, invokes the gate, schedules, and writes the spine, and it never dispatches another coordinator. `stage-worker` is filled by one execution per Work Package (a native subagent locally, one detached runner remotely). `stage-verifier` is filled by one fresh-context read-only execution per verdict and never the package executor. `stage-integrator` is filled by one execution per decomposed stage attempt.

## Dynamic Structure

- **Parallel**: independent read-only packages run concurrently up to the resolved slot cap; no write package is present.
- **Serial with read-only layers**: dependencies and write packages order the work; every write package runs alone, while independent ready read-only packages may still overlap under SD-04.
- **Bounded iteration**: a complete `repair_loop` (maximum iterations plus a stop condition) drives a review-repair convergence loop.

The selected pattern is always graph-derived and is not this preset's default: `iteration` when a complete `repair_loop` exists; otherwise `parallel` when every package is read-only and two or more packages are independent; otherwise `serial` when any write package or any dependency edge exists. `continuous` is never selected and never appears as an adapter flow.

## Instantiation

The adapter binds this preset and the package graph into a run-scoped plan fence: it substitutes the stage, the line, the plan hash, the slot cap, the selected pattern, and the package-to-seat mapping. The projection is run-scoped.

Do not create a team directory (`.specify/teams/<slug>/`) and do not persist a team definition: no `.specify/teams/<slug>/team.md` is created per stage, per attempt, or per run. There is no goal binding and no team run report.

The graph-derived pattern, the resolved slot cap, and the per-package seat mapping take precedence over this preset's declared defaults (ST-12).

## Constraints & Hard Rules

- The driver is the sole coordinator; package executors never dispatch another package, never spawn a driver, and never edit the plan.
- A write package is never concurrent with any other package; a package sentinel never satisfies the stage sentinel; the stage sentinel plus the unchanged U4 remain mandatory.
- The plan and ledger are fences in the existing line state spine; there is no second brief, ledger, registry, ownership model, integration queue, or persisted team.
- `create-team` and `run-team`, their templates, presets, and run reports are unchanged. This preset is loaded by explicit path and is not registered in the create-team catalog.

## Known Pitfalls

- Treating a package sentinel (`WP-…-DONE`) as the stage sentinel.
- Running a write package concurrently with any other package.
- Verifying a package with its executor's own context.
- Letting a same-budget retry repeat without a scope, budget, or topology change.
- Letting this preset's default pattern override the graph-derived pattern or the resolved slot cap.
- Persisting a team directory per stage or per attempt.
