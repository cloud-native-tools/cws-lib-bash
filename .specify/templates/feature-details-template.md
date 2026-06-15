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
| Planned | Implemented | `/speckit.implement` | `tasks.md` has zero `[ ]` rows (all tasks are `[X]` closed or `[~]` deferred) AND `verification.log` records a `SC-NNN_status=pass|deferred` row for every Success Criterion in `requirements.md`. |
| Implemented | Ready for Review | `/speckit.review` (or human) | All deferred (`[~]`) tasks are resolved or explicitly waived, and review evidence has been produced. |
| Ready for Review | Completed | Human / governance | Final acceptance. |

**Critical contract**: `/speckit.plan` MUST land status `Planned` (not `Implemented`). `/speckit.implement` MUST advance `Planned → Implemented` only when the DoD above is satisfied; if any task is `[~]` deferred, append a ` (deferred: T<comma-list>)` suffix to the `Last Updated` cell in `features.md` so the deferral is visible at the index level.

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
