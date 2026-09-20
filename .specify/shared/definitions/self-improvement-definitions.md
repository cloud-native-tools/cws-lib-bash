# Self-Improvement Definitions（自我提升概念权威）

> **Single source of truth** for the meanings and boundaries of Self-Improvement,
> Assisted Improvement, Execution Subject, and Self-Improvement Loop in Spec Kit.
> Canonical at `shared/definitions/self-improvement-definitions.md`, mirrored to
> `.specify/shared/definitions/`. This file owns concepts only; normative gates live in
> `shared/guidelines/self-improvement.md`, reusable structure in
> `shared/patterns/self-improvement-pattern.md`, and execution order in
> `shared/workflow/self-improvement-workflow.md`.

## Execution Subject（执行主体）

An **Execution Subject** is a durable, identifiable behavioral artifact that:

1. can be invoked repeatedly;
2. owns or references an execution contract;
3. produces observable run evidence;
4. has one canonical editable definition; and
5. can route a durable change to that definition for a later execution.

The concept is about a durable identity, not an autonomous process. A subject may use a
separate agent execution to observe, improve, or verify it and still remain the subject of
the loop.

| Artifact | Execution-subject boundary |
|----------|----------------------------|
| **Agent** | Agent Template or Agent Instance is a subject; an Agent Execution is evidence from one run, not an editable subject. Layer meanings remain owned by `agent-definitions.md`. |
| **Skill** | The canonical Skill directory is a subject; installed mirrors are projections, not independent subjects. |
| **Tool** | The Tool record is a subject because it governs repeated invocations; the external binary/function/webhook is not owned by Spec Kit. Tool meaning remains owned by `tool-definitions.md`. |
| **Team** | The persisted team definition is a subject; member executions and run reports are evidence, not separate team definitions. |
| **Document / site output** | Not an execution subject unless it independently satisfies all five criteria above. It may be an improvement target or Harness asset. |

## Self-Improvement（自我提升）

**Self-Improvement** is an evidence-driven improvement loop whose **initiating signal and
target share the same durable subject identity**. The subject observes outcomes from its
own completed executions, qualifies a change against its own contract, routes the change
to its canonical definition, validates the intervention, and waits for a comparable later
run before claiming outcome improvement.

“Self” identifies ownership of the signal and target. It does **not** mean:

- rewriting a definition during the execution governed by that definition;
- bypassing confirmation, ownership, review, or independent verification;
- treating self-reflection as proof;
- granting an LLM, agent runtime, or generated artifact new authority.

A subject is **self-improvement-capable** when its definition declares an observation
source, trigger, editable boundary, improvement route, validation route, and comparison
signal. Capability does not imply automatic mutation.

## Assisted Improvement（他者辅助提升）

**Assisted Improvement** is an improvement loop whose initiating direction or target
judgment is supplied by a different actor: a user, another agent/team, a reviewer, an
administrator, or an explicit improve command/skill.

The distinction is based on **who owns the initiating decision**, not who edits the file:

| Situation | Classification |
|-----------|----------------|
| A Skill records friction from its own run and dispatches `improve-skills` against itself | Self-Improvement; `improve-skills` is the delegated improver |
| A user asks to change that Skill | Assisted Improvement |
| A review agent detects a defect in another agent definition | Assisted Improvement |
| A team’s own run critique triggers `improve-team` for that same team | Self-Improvement |
| A maintainer periodically reviews every team | Assisted Improvement |

User corrections always count as assisted input and outrank subject-originated preference,
subject to framework red lines.

## Self-Improvement Loop（自我提升闭环）

A **Self-Improvement Loop** is the bounded connection of existing Spec Kit mechanisms:

```text
own run → observation → evidence qualification → targeted intervention
        → change validation → later comparable run → outcome comparison → learning
```

The loop is not a new daemon, score store, or mutation engine. It composes:

- Better Harness as the goal model (`shared/guidelines/better-harness.md`);
- Feedback as an optional reflection sensor (`shared/workflow/feedback-step.md`);
- Evidence as the qualification and comparison layer (`shared/workflow/evidence-step.md`);
- the relevant `improve-*` skill as the change executor;
- existing tests, review, memory, history, and run reports as evidence sources.

## Observation, Intervention, and Outcome

- **Observation**: a scoped fact from a run, user correction, test, report, or feedback entry.
- **Improvement candidate**: an observation that passes evidence qualification; it is not yet a change.
- **Intervention**: the targeted change recorded against a baseline finding.
- **Change validation**: proof that the edited artifact is structurally and behaviorally valid now.
- **Outcome validation**: a later comparable run showing the expected signal improved.

Change validation MUST NOT be called outcome validation. “Implemented” may be reported after
current checks pass; “improved” requires a before/after comparison.

## Relationship Boundaries

- **Feedback is a sensor, not authority.** Its target and transmission red lines remain owned
  by `workflow/feedback-step.md`; recording feedback never authorizes a mutation.
- **Better Harness is the north star, not the loop engine.** It says what becomes better;
  Self-Improvement says who initiated and closed the loop.
- **Dogfooding is a context, not a synonym.** Dogfooding can generate first-hand signals for
  Self-Improvement, but self-use without an intervention/comparison loop is not Self-Improvement.
- **Reconcile is convergence, not learning.** A reconcile run may apply an intervention, but
  repeating desired-state convergence alone does not prove improvement.
- **Continuous operation is scheduling, not identity.** A continuous team may host repeated
  Self-Improvement cycles; cadence alone does not make a loop self-improving.
