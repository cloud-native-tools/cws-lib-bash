<!--
  SOURCE TEMPLATE (development path): templates/review-template.md
  INSTALLED TEMPLATE (runtime path): .specify/templates/review-template.md
  Do NOT remove placeholder tokens. Each [TOKEN] must be replaced when generating a concrete review report.
-->

# Feature Review Report: [FEATURE_NAME]

**Feature ID**: [FEATURE_ID]  
**Branch / Spec Key**: [FEATURE_KEY]  
**Spec Path**: .specify/specs/[FEATURE_KEY]/spec.md  
**Plan Path**: .specify/specs/[FEATURE_KEY]/plan.md  
**Tasks Path**: .specify/specs/[FEATURE_KEY]/tasks.md  
**Review Date**: [REVIEW_DATE]  
**Reviewer (Agent)**: [REVIEWER_NAME]

---

## 1. Summary

- **Problem & Goal**: [SUMMARY_PROBLEM_GOAL]
- **Primary Users / Actors**: [SUMMARY_ACTORS]
- **Key Capabilities Delivered**: [SUMMARY_CAPABILITIES]
- **Overall Outcome**: [SUMMARY_OUTCOME]

## 2. Spec Review (`spec.md`)

### 2.1 Coverage & Clarity

- **User Scenarios Coverage**: [SPEC_USER_SCENARIOS_COVERAGE]
- **Functional Requirements Clarity**: [SPEC_FUNCTIONAL_REQUIREMENTS_CLARITY]
- **Success Criteria Measurability**: [SPEC_SUCCESS_CRITERIA_MEASURABILITY]
- **Non-functional Requirements**: [SPEC_NON_FUNCTIONAL_SUMMARY]

### 2.2 Gaps & Observations

- **Strengths**:
  - [SPEC_STRENGTH_1]
  - [SPEC_STRENGTH_2]
- **Gaps / Ambiguities**:
  - [SPEC_GAP_1]
  - [SPEC_GAP_2]

## 3. Plan Review (`plan.md`)

### 3.1 Alignment with Spec

- **Architecture matches spec intent**: [PLAN_ARCH_ALIGNMENT]
- **Data model supports key scenarios**: [PLAN_DATA_MODEL_ALIGNMENT]
- **Contracts / Interfaces cover user flows**: [PLAN_CONTRACT_ALIGNMENT]

### 3.2 Design Decisions

- **Key Decisions**:
  - [PLAN_DECISION_1]
  - [PLAN_DECISION_2]
- **Notable Trade-offs / Risks**:
  - [PLAN_RISK_1]
  - [PLAN_RISK_2]

## 4. Tasks & Implementation Review (`tasks.md` + implementation)

### 4.1 Task Breakdown

- **Phases & Ordering**: [TASKS_PHASE_SUMMARY]
- **Parallelization Strategy**: [TASKS_PARALLELIZATION_SUMMARY]
- **Coverage of Spec Requirements**: [TASKS_COVERAGE_SUMMARY]

### 4.2 Execution Observations

- **Completed vs Deferred / Skipped Tasks**:
  - [TASKS_COMPLETION_OVERVIEW]
- **Notable Implementation Notes**:
  - [TASKS_IMPLEMENTATION_NOTE_1]
  - [TASKS_IMPLEMENTATION_NOTE_2]

## 5. End-to-End Assessment

- **Does the implemented feature satisfy the spec?**: [ASSESSMENT_SPEC_FIT]
- **Are there known gaps or follow-ups needed?**: [ASSESSMENT_KNOWN_GAPS]
- **Impact on other areas / integrations**: [ASSESSMENT_INTEGRATIONS_IMPACT]

## 6. Future Evolution Suggestions

- [REVIEW_FUTURE_SUGGESTION_1]
- [REVIEW_FUTURE_SUGGESTION_2]
- [REVIEW_FUTURE_SUGGESTION_3]

## 7. Links & Artifacts

- **Specification**: .specify/specs/[FEATURE_KEY]/spec.md
- **Plan**: .specify/specs/[FEATURE_KEY]/plan.md
- **Tasks**: .specify/specs/[FEATURE_KEY]/tasks.md
- **Data Model** (if any): .specify/specs/[FEATURE_KEY]/data-model.md
- **Contracts** (if any): .specify/specs/[FEATURE_KEY]/contracts/
- **Quickstart** (if any): .specify/specs/[FEATURE_KEY]/quickstart.md

---

## Placeholder Glossary

| Token | Meaning / Source |
|-------|------------------|
| [FEATURE_ID] | Sequential three-digit feature identifier (e.g., 001) |
| [FEATURE_NAME] | Short human-readable name of the feature |
| [FEATURE_KEY] | Combined ID + slug used as spec directory name (e.g., 001-create-taskify) |
| [REVIEW_DATE] | ISO date when this review was generated (YYYY-MM-DD) |
| [REVIEWER_NAME] | Name/label of the reviewing agent or persona |
| [SUMMARY_*] | High-level summary bullets for the review |
| [SPEC_*] | Observations derived from `.specify/specs/[FEATURE_KEY]/spec.md` |
| [PLAN_*] | Observations derived from `.specify/specs/[FEATURE_KEY]/plan.md` |
| [TASKS_*] | Observations derived from `.specify/specs/[FEATURE_KEY]/tasks.md` and execution results |
| [ASSESSMENT_*] | End-to-end assessment statements for this feature |
| [REVIEW_FUTURE_SUGGESTION_N] | Concrete, review-driven evolution suggestions for this feature |

## Replacement Rules

1. No placeholder token may remain in a committed review report.  
2. Dates must be valid ISO format.  
3. Keep lists dense; remove unused trailing placeholder lines.  
4. Preserve this heading structure for all review reports for consistency.  
5. When regenerating a review, either overwrite the existing `review.md` or archive the previous version according to project conventions.

<!-- End of review template -->
