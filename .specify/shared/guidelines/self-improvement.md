# Self-Improvement Guidelines（自我提升治理规则）

> **Single source of truth** for the normative eligibility, evidence, authority,
> safety, and claim rules of Self-Improvement in Spec Kit. Terms are owned by
> `shared/definitions/self-improvement-definitions.md`; this file does not redefine them.
> All normative language follows RFC 2119.

## Eligibility Gate

A durable artifact MAY declare Self-Improvement capability only when it qualifies as an
Execution Subject under `shared/definitions/self-improvement-definitions.md`.

- Agent Templates/Instances, Skills, Tool records, and persisted Teams MAY qualify.
- One live Agent Execution, a run report, a generated document, a static site, and other
  one-shot outputs MUST NOT claim subject identity merely because an agent produced them.
- The canonical owner MUST be resolvable before a loop starts. A mirror, generated copy, or
  compatibility path MUST NOT become the edit target.

## Required Subject Contract

A self-improvement-capable subject MUST expose or reference all of these fields:

1. **Identity** — the stable subject ID and canonical editable owner;
2. **Observation** — which own-run evidence sources may trigger review;
3. **Qualification** — how evidence is classified and candidates are frozen;
4. **Mutation boundary** — which files/fields the subject may propose changing;
5. **Improvement route** — the matching `improve-*` executor or equivalent owner-approved path;
6. **Validation** — current-change checks and an independent verifier where required;
7. **Comparison** — the later signal that can support an improvement claim;
8. **Escalation** — what stops, waits for a user, or degrades to Assisted Improvement.

The contract MAY be a compact section that points to the canonical workflow. It MUST NOT
copy the workflow steps, evidence-state meanings, or confirmation policy.

## Evidence Rules

- A subject MUST observe completed executions; it MUST NOT rewrite its governing definition
  mid-run and then evaluate the remainder as if the contract were unchanged.
- Candidate qualification MUST follow `shared/workflow/evidence-step.md` Step A/B. Negative
  `Exercised`/`Outcome-supported` evidence and `Missing` mechanisms may become candidates;
  `Unobserved` MUST NOT.
- Direct user correction is valid assisted evidence. It does not need repeated occurrence,
  but the resulting edit still requires change validation.
- Self-reflection and Feedback entries are observations, not proof. A subjective statement
  such as “this felt better” MUST NOT become an outcome claim without a comparable signal.
- Candidate lists freeze before diagnosis and mutation. New findings start a later loop.

## Authority and Mutation Rules

- Self-Improvement MUST edit only the canonical owner defined by the One Source of Truth
  discipline (`shared/guidelines/one-source-of-truth.md`). Mirrors are regenerated.
- A subject MAY initiate its own loop but SHOULD delegate mutation to the matching
  `improve-agent`, `improve-skills`, `improve-tools`, or `improve-team` executor. Delegation
  preserves self-originated classification because the subject still owns the initiating signal.
- The improver MUST NOT broaden scope beyond the frozen candidates.
- Changes MUST be minimal and reversible. A large rewrite requires evidence that the current
  structure is itself causal; “cleaner” is not evidence.
- Self-Improvement MUST NOT grant itself new permissions, widen write territory, weaken a
  safety rule, change external authority, or enable unattended execution without Assisted
  Improvement and the applicable user/governance decision.

## Confirmation and Independence

All actions follow `shared/guidelines/confirmation-gates.md`:

- reversible local edits may execute and then be reported;
- destructive actions, external writes, authority expansion, and uncertain actions stop for
  confirmation;
- existing governance-kept gates remain in force.

Behavior-changing interventions SHOULD use a verifier execution independent of the execution
that authored the change. Independence is REQUIRED for unattended continuous teams, safety
boundaries, permission changes, and promotion to a higher autonomy/maturity tier.

## Validation and Claims

- **Change validation** MUST run in the intervention cycle: structural contracts, relevant
  tests, reference integrity, and a pressure test for behavior-changing instructions.
- Every evidence-driven intervention MUST write `intervention.json` per
  `shared/workflow/evidence-step.md` Step E.
- **Outcome validation** occurs only on a later comparable run through `--action compare` or
  an equivalent documented comparison.
- Before comparison, report “intervention applied; outcome pending”, never “self-improved”,
  “fixed”, or “better”.
- A failed comparison MUST retain the evidence, revert or revise through a new bounded loop,
  and MUST NOT silently tune until a favorable result appears.

## Feedback and Better-Harness Integration

- Better Harness (`shared/guidelines/better-harness.md`) owns the improvement goal and dimension
  vocabulary. Every intervention names the affected dimension(s) by reference.
- Feedback (`shared/workflow/feedback-step.md`) remains optional user data targeting the Spec
  Kit framework. It may supply a signal when the subject is a matching framework unit, but
  MUST NOT become a general artifact-mutation bus.
- Memory/history may preserve reusable learning; they MUST NOT replace evidence or create a
  second authoritative contract.
- `/better-harness` and `/speckit.review` provide system-level assisted review. A local subject
  MUST escalate cross-subject or cross-dimension findings instead of self-modifying broadly.

## Anti-Churn and Efficiency

- Repeated clean runs do not justify edits. No candidate means no mutation.
- Deterministic detection, deduplication, schema checks, mirror checks, and comparisons MUST
  be scripted per `shared/guidelines/token-efficiency.md`.
- Evidence consumption is summary-first. Raw logs and stores are loaded only through the
  escalation rules in that guideline.
- A subject MUST impose a bounded attempt/cycle limit; on exhaustion it reports residual risk
  and degrades to Assisted Improvement.

## Non-Subject Artifacts

Create/improve flows for documentation and presentation assets participate in Better Harness
but do not confer Self-Improvement identity on those outputs. `create-docs`, `create-pages`,
and `improve-docs` remain Assisted Improvement paths unless the created artifact independently
meets the Execution Subject definition.
