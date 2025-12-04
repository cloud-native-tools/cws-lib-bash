<!--
  SOURCE TEMPLATE (development path): templates/feature-template.md
  INSTALLED TEMPLATE (runtime path): .specify/templates/feature-template.md
  Do NOT remove placeholder tokens. Each [TOKEN] must be replaced during feature instantiation.
  This template is derived from an actual feature detail file and generalized.
-->

# Feature Detail: [FEATURE_NAME]

**Feature ID**: [FEATURE_ID]  
**Name**: [FEATURE_NAME]  
**Description**: [FEATURE_DESCRIPTION]  
**Status**: [FEATURE_STATUS]  
**Spec Path**: .specify/specs/[FEATURE_ID]-[FEATURE_SLUG]/spec.md  
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

- Specification: .specify/specs/[FEATURE_ID]-[FEATURE_SLUG]/spec.md
- Feature Index: memory/feature-index.md
- Feature Detail: memory/features/[FEATURE_ID].md
- Quality Checklist: .specify/specs/[FEATURE_ID]-[FEATURE_SLUG]/checklists/requirements.md

## Status Tracking

- **Draft**: [STATUS_DRAFT_CRITERIA]
- **Planned**: [STATUS_PLANNED_CRITERIA]
- **Implemented**: [STATUS_IMPLEMENTED_CRITERIA]
- **Ready for Review**: [STATUS_READY_FOR_REVIEW_CRITERIA]
- **Completed**: [STATUS_COMPLETED_CRITERIA]

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
- [ ] Spec path exists or will be created
- [ ] Status is valid and criteria defined
- [ ] Overview gives clear value proposition
- [ ] Key Changes list distinct, actionable items
- [ ] Implementation Notes capture constraints/assumptions
- [ ] Dates in YYYY-MM-DD format

<!-- End of template -->
