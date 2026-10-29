<!--
  Do NOT remove placeholder tokens. Each [TOKEN] must be replaced during feature instantiation.
  This template is derived from an actual feature detail file and generalized.
-->

# Feature Detail: [FEATURE_NAME]

**Feature ID**: [FEATURE_ID]  
**Name**: [FEATURE_NAME]  
**Description**: [FEATURE_DESCRIPTION]  
**Status**: [FEATURE_STATUS]  
**Created**: [FEATURE_CREATED_DATE]  
**Last Updated**: [FEATURE_LAST_UPDATED_DATE]

## Overview

[FEATURE_OVERVIEW]

## Latest Review

[FEATURE_LATEST_REVIEW_SUMMARY]

## Key Changes

1. [KEY_CHANGE_1]
2. [KEY_CHANGE_2]
3. [KEY_CHANGE_3]
4. [KEY_CHANGE_4]
5. [KEY_CHANGE_5]

<!-- Add or remove items as needed; keep numbered list contiguous -->

## Implementation Notes

- [IMPLEMENTATION_NOTE_1]
- [IMPLEMENTATION_NOTE_2]
- [IMPLEMENTATION_NOTE_3]
- [IMPLEMENTATION_NOTE_4]
- [IMPLEMENTATION_NOTE_5]

<!-- Add additional notes if required -->

## Future Evolution Suggestions

- [FUTURE_SUGGESTION_1]
- [FUTURE_SUGGESTION_2]
- [FUTURE_SUGGESTION_3]

## Related Files

- Feature Index: .specify/memory/features.md
- Feature Detail: .specify/memory/features/[FEATURE_ID].md

## Status Tracking

- **Draft**: [STATUS_DRAFT_CRITERIA]
- **Planned**: [STATUS_PLANNED_CRITERIA]
- **Implemented**: [STATUS_IMPLEMENTED_CRITERIA]
- **Ready for Review**: [STATUS_READY_FOR_REVIEW_CRITERIA]
- **Completed**: [STATUS_COMPLETED_CRITERIA]

### Canonical Status State Machine (single source of truth)

This is the authoritative transition table cited by `/speckit.feature`, `/speckit.plan`, `/speckit.tasks`, and `/speckit.implement`. Those commands MUST NOT paraphrase the rules — they MUST point at this section.

| From | To | Owner Command | Trigger / Definition of Done |
|------|------|----------------|------------------------------|
| (n/a) | Draft | `/speckit.feature` | Feature row first added to `.specify/memory/features.md`. |
| Draft | Planned | `/speckit.plan` | `plan.md`, `data-model.md`, `contracts/`, and `quickstart.md` exist for the requirement bound to this feature; Constitution Check has no unjustified Fail rows. |
| Planned | Implemented | `/speckit.implement` | `tasks.md` has zero `[ ]` rows (all tasks are `[X]` closed or `[~]` deferred) AND `verification.md` records a `SC-NNN_status=` row for every Success Criterion in `requirements.md`, drawn from the status vocabulary owned by `.specify/templates/verification-log-template.md` (MUST NOT be narrowed to a subset of it — an honest `partial` is a legal status, not a DoD failure). |
| Implemented | Ready for Review | `/speckit.review` (or human) | Three conjunctive conditions, all required: every deferred (`[~]`) task is resolved or explicitly waived; review evidence has been produced; and the current code-segment record (`code-review.md`) contains no `blocking` entry. Stated in full in **the gate below**, which owns them — this cell is their summary. |
| Ready for Review | Completed | Human / governance | Final acceptance. |

**Critical contract**: `/speckit.plan` MUST land status `Planned` (not `Implemented`). `/speckit.implement` MUST advance `Planned → Implemented` only when the DoD above is satisfied; if any task is `[~]` deferred, append a ` (deferred: T<comma-list>)` suffix to the `Last Updated` cell in `features.md` so the deferral is visible at the index level.

**Extension slice rule**: when a later requirement plans an extension of a Feature whose status is already `Implemented`, the status is NOT regressed (`Implemented → Planned` is not a legal transition). Instead: keep the status, record the extension's planning in the Feature detail (Latest Review / Key Changes) and in the `features.md` Last Updated cell, and let the extension's own `/speckit.implement` run re-assert `Implemented` with updated evidence when it closes.

**The `Implemented → Ready for Review` gate.** This block owns the transition's criteria. Every other artifact that touches this transition — `/speckit.review`, `/speckit.checklist`, the process report's code subsection, the `## Latest Review` review-record entry above — reaches them here by reference and carries no second wording of them.

1. **Three conjunctive conditions, all required**: every deferred (`[~]`) task is resolved or explicitly waived; review evidence has been produced; and the current code-segment record contains no `blocking` entry.
2. **The third condition is an existence test over the current record.** It reads `code-review.md` — the record the latest code-segment run wrote — and asks one question: does that file contain at least one `blocking` entry? One such heading blocks the transition. A later run that writes a record carrying zero `blocking` entries no longer blocks, and that is the whole mechanism: there is no clearing action and no cleared state, so no artifact explains how an entry becomes cleared and no run is ever asked to mark one. Archived records (`code-review-<YYYYMMDDTHHMMSSZ>.md`) are never counted — they are history, not this gate's input.
3. **The six-level vocabulary is read directly.** The severity words are `blocking`, `important`, `suggestion`, `nitpick`, `question` and `praise`, owned by `skills/internal/code-review/SKILL.md`. The gate reads those words as written. Relabelling them as `P0`/`P1`/`P2`, converting between the two families, or consulting a mapping matrix before judging is forbidden: the process family (`P0`/`P1`/`P2`) has its own owner, and no conversion, no mapping table and no unified score exists between the two.
4. **`important` does not block, but each `important` item must be answered.** With only `important` items open and no `blocking` entry, the transition is allowed, and each `important` item must be answered — agreement or disagreement, with a reason. `suggestion`, `nitpick`, `question` and `praise` never block and require no answer; none of the four is a transition condition.
5. **A waiver exists only as an explicit user ruling.** A user-authored waiver artifact, or the user's own ruling in the session, is a waiver; a driver's or an orchestrator's confirmation is an agent's confirmation and is never a user ruling, and the absence of objection is not a waiver either. The agent never downgrades, merges or excludes a `blocking` entry inside this judgement. When a waiver exists it is written onto both verifiable carriers — the process report's code subsection and this feature detail's `## Latest Review` review-record entry.
6. **The unattended disposition is halt-and-report.** Without an explicit user ruling the run stops before the transition, reports the block, and records `blocking-unresolved` as the named refusal literal in the process report's code subsection and in the conclusion the command returns. A run must never leave the status at `Implemented` while presenting itself as a completed review.
7. **A refusal names the failed condition and leaves the status at `Implemented`.** The reason states which of the three conditions failed — a `blocking` entry in the current code-segment record, missing review evidence, or deferred tasks not yet resolved or waived — not merely that the transition was refused. It is written onto both verifiable carriers.
8. **`not-applicable` and `not-evaluated` do not block, and are disclosed.** A code segment with either verdict does not block the transition; each is disclosed on both verifiable carriers — the process report's code subsection (`### 2.1`) and the review-record entry above. The closing summary may restate it and carries no obligation of its own; it is a presentation, not a third carrier.
9. **One checkpoint, after both segments.** The transition is judged once, after the process segment and the code segment have both finished and both artifacts (`review.md` and, when the code segment ran, `code-review.md`) are on disk. Because the code segment's conclusion is one of the conditions' inputs, the status must not flip before that segment completes; an early flip is a violation even when the process segment already passed.

## Placeholder Glossary

| Token | Meaning / Source |
|-------|------------------|
| [FEATURE_ID] | Sequential three-digit feature identifier (e.g., 001) |
| [FEATURE_NAME] | Short human-readable name (2-5 words) |
| [FEATURE_SLUG] | Kebab-case combination of ID + normalized name (e.g., 001-feature-mechanism-redesign) |
| [FEATURE_DESCRIPTION] | One-line summary in natural language |
| [FEATURE_STATUS] | Draft | Planned | Implemented | Ready for Review | Completed |
| [FEATURE_CREATED_DATE] | ISO date when first created (YYYY-MM-DD) |
| [FEATURE_LAST_UPDATED_DATE] | ISO date of last modification (YYYY-MM-DD) |
| [FEATURE_OVERVIEW] | Paragraph explaining motivation and context |
| [FEATURE_LATEST_REVIEW_SUMMARY] | Summary of the most recent end-to-end feature review |
| [KEY_CHANGE_N] | Discrete planned change (prefer 3–7 items) |
| [IMPLEMENTATION_NOTE_N] | Constraint, assumption, or technical nuance |
| [FUTURE_SUGGESTION_N] | Suggested follow-up enhancements or experiments for this feature |
| [STATUS_*_CRITERIA] | Definition of Done for each status |

## Replacement Rules

1. No placeholder token may remain after instantiation.  
2. Dates must be valid ISO format.  
3. Keep lists dense; remove unused trailing placeholder lines.  
4. Preserve this heading structure; do not add unrelated sections.  
5. Always update `Feature Index` after creating or modifying a feature detail file.

## Validation Checklist (To be removed after instantiation)

- [ ] All tokens replaced
- [ ] Status is valid and criteria defined
- [ ] Overview gives clear value proposition
- [ ] Key Changes list distinct, actionable items
- [ ] Implementation Notes capture constraints/assumptions
- [ ] Dates in YYYY-MM-DD format

## Related Specifications/Requirements

- Specification: .specify/specs/[REQUIREMENTS_KEY]/requirements.md
  Quality Checklist: .specify/specs/[REQUIREMENTS_KEY]/checklists/requirements.md
- Specification: .specify/specs/[REQUIREMENTS_KEY]/requirements.md
  Quality Checklist: .specify/specs/[REQUIREMENTS_KEY]/checklists/requirements.md

<!-- End of template -->
