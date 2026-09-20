# Self-Improvement Workflow（自我提升标准路径）

> **Single source of truth** for the execution order of a Spec Kit Self-Improvement
> Loop. Concepts are owned by `shared/definitions/self-improvement-definitions.md`;
> policy by `shared/guidelines/self-improvement.md`; reusable structure by
> `shared/patterns/self-improvement-pattern.md`. Embedding units reference this file and do
> not copy its steps.

## Entry Contract

Inputs:

- `subject_id` and canonical owner path;
- initiating actor and signal source;
- completed execution window;
- requested direction, if any;
- candidate comparison signal;
- mutation and verification capabilities available in the current runtime.

No completed execution or no canonical owner means no Self-Improvement loop. Route a user-led
edit to Assisted Improvement, or record the observation for later.

## Standard Flow

### SI-0 — Resolve Identity, Origin, and Boundary

1. Verify the target satisfies the Execution Subject definition.
2. Resolve the canonical owner; classify mirrors and runtime artifacts as read-only evidence.
3. Classify origin:
   - own completed run initiated review → `self`;
   - user/other subject/reviewer initiated direction → `assisted`.
4. Declare mutation boundary, external authorities, destructive surfaces, and attempt limit.

If identity or origin is ambiguous, ask one targeted question before mutation. A delegated
`improve-*` executor does not change `self` origin when the subject supplied the initiating
own-run signal.

### SI-1 — Observe Without Mutating

Collect only evidence from the completed window. Use the canonical Feedback step for a
qualifying framework unit, but treat the entry as one sensor. Do not edit the subject while
observing; do not turn unrelated project/system findings into local candidates.

### SI-2 — Qualify and Freeze Evidence

Execute `shared/workflow/evidence-step.md` Step A/B. Reuse fresh evidence or collect available
lanes, classify every finding by the canonical evidence states, and freeze the candidate list.

Outcomes:

- no qualified candidate → close as no-op; keep observations;
- local candidate → continue;
- cross-subject/systemic candidate → escalate to Assisted Improvement (`/better-harness`,
  `/speckit.review`, or the owning improve flow), without broad local mutation.

### SI-3 — Diagnose and Select the Better-Harness Dimension

For each frozen candidate:

1. locate the causal contract, route, script, definition, or missing sensor;
2. name the affected Better-Harness dimension(s) by reference;
3. select the improvement track after evidence triage;
4. choose the smallest intervention that can change the expected signal.

Do not create new candidates during diagnosis. Newly discovered issues start a future loop.

### SI-4 — Route to the Canonical Improver

| Subject | Improver |
|---------|----------|
| Agent Template/Instance/config | `improve-agent` |
| Skill | `improve-skills` |
| Tool record | `improve-tools` |
| Team definition | `improve-team` |

The improver receives: origin (`self|assisted`), subject ID, frozen findings, canonical owner,
mutation boundary, expected signal, and attempt limit. Non-subject artifacts route to their
normal assisted flow (`improve-docs`, direct owner workflow, or system review).

### SI-5 — Plan and Apply the Intervention

Apply `shared/guidelines/confirmation-gates.md` before writes. Reversible, authorized local
edits may execute and be reported; destructive, external, authority-expanding, or uncertain
changes stop for confirmation.

Edit only the canonical owner. Regenerate mirrors through their owning mechanism. Keep the
intervention minimal, preserve unaffected content, and stop when the bounded attempt limit is
reached.

### SI-6 — Validate the Change

Run structural contracts and relevant tests. For behavior-changing changes, run a pressure
scenario; use an independent verifier when required by the guideline. Record failures and
residual risk rather than tuning indefinitely.

A passing check supports only: **intervention applied; outcome pending**.

### SI-7 — Record the Intervention

Execute `shared/workflow/evidence-step.md` Step E. `intervention.json` ties the change to a
baseline finding and expected signal. Reuse existing run reports, logs, history, and memory;
do not create a parallel self-improvement database.

### SI-8 — Compare on a Later Run

After the next comparable execution, run evidence comparison:

- expected signal improved → mark outcome supported and distill reusable learning;
- unchanged → retain evidence and reassess once within the attempt limit;
- regressed → retain evidence, revert or route a bounded corrective intervention;
- no comparable data → keep `Unobserved`; make no outcome claim.

### SI-9 — Close or Escalate

Close with origin, subject, intervention, current validation, outcome state, residual risk, and
next comparison point. Escalate to Assisted Improvement when authority, scope, evidence,
independence, or attempt limits block safe closure.

The embedding unit’s canonical `## Feedback` step still runs at its normal wrap-up position.
Self-Improvement MUST NOT replace, duplicate, or auto-submit Feedback.

## Create-Flow Integration

A create flow performs a **capability setup**, not an improvement run:

1. classify whether the produced artifact is an Execution Subject;
2. if yes, install a compact Self-Improvement Contract referencing this workflow;
3. declare the matching `improve-*` route and evidence sources;
4. validate that the contract does not grant new authority;
5. if no, state that the output is a non-subject Harness asset and keep its normal assisted
   improvement route.

## Improve-Flow Integration

Every `improve-*` flow starts SI-0 before its native workflow:

- default to `assisted` unless an own-run signal from the same subject is demonstrated;
- reuse the flow’s existing evidence and intervention steps rather than duplicating them;
- preserve the flow’s domain-specific diagnosis and validation;
- report “outcome pending” until SI-8 completes.

## Failure and Degradation

| Blocker | Required response |
|---------|-------------------|
| No canonical owner | Stop mutation; resolve ownership |
| Only `Unobserved` evidence | Record only; await a real run |
| No authorized mutation route | Degrade to Assisted Improvement |
| Independent verifier unavailable when required | Apply no autonomy/safety expansion; report pending |
| Tests fail | Stop, retain evidence, report regression |
| Attempt limit reached | Stop automatic iteration; request assisted review |
| Feedback engine unavailable | Continue with available run evidence; never fabricate feedback |

## Completion Report

Report:

- mode: `self` or `assisted` and why;
- subject identity and canonical owner;
- frozen findings and Better-Harness dimension(s);
- intervention and validation performed;
- outcome state: pending / supported / unchanged / regressed / unobserved;
- intervention ledger path and next comparison point;
- residual risks or assisted escalation.
