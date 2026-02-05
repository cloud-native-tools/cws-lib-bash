<!--
  Do NOT remove placeholder tokens. Each [TOKEN] must be replaced when generating a concrete review report.
-->

# Specification-Driven Development (SDD) Process Review Report: [REQUIREMENT NAME]

**Feature ID**: [FEATURE_ID]  
**Branch / Spec Key**: [REQUIREMENTS_KEY]  
**Spec Path**: .specify/specs/[REQUIREMENTS_KEY]/requirements.md  
**Plan Path**: .specify/specs/[REQUIREMENTS_KEY]/plan.md  
**Tasks Path**: .specify/specs/[REQUIREMENTS_KEY]/tasks.md  
**Review Date**: [REVIEW_DATE]  
**Reviewer (Agent)**: [REVIEWER_NAME]

---

## 1. Scope & Overall Assessment

- **Artifacts Reviewed**: [PROCESS_ARTIFACTS_REVIEWED]
- **Overall Process Health**: [PROCESS_HEALTH_SUMMARY]
- **Primary Strengths**:
  - [PROCESS_STRENGTH_1]
  - [PROCESS_STRENGTH_2]
- **Primary Gaps**:
  - [PROCESS_GAP_1]
  - [PROCESS_GAP_2]

## 2. Spec Quality Review (`requirements.md`)

### 2.1 Clarity & Testability

- **User Scenarios Coverage**: [SPEC_USER_SCENARIOS_COVERAGE]
- **Requirements Testability**: [SPEC_REQUIREMENTS_TESTABILITY]
- **Success Criteria Measurability**: [SPEC_SUCCESS_CRITERIA_MEASURABILITY]
- **Assumptions & Scope Boundaries**: [SPEC_ASSUMPTIONS_SCOPE]

### 2.2 Gaps & Observations

- **Strengths**:
  - [SPEC_STRENGTH_1]
  - [SPEC_STRENGTH_2]
- **Process Gaps / Ambiguities**:
  - [SPEC_GAP_1]
  - [SPEC_GAP_2]

## 3. Plan Quality Review (`plan.md`)

### 3.1 Traceability & Coherence

- **Plan aligns to spec requirements**: [PLAN_TRACEABILITY]
- **Risk identification & mitigation**: [PLAN_RISK_MANAGEMENT]
- **Sequencing & dependency clarity**: [PLAN_SEQUENCING_CLARITY]

### 3.2 Gaps & Observations

- **Strengths**:
  - [PLAN_STRENGTH_1]
  - [PLAN_STRENGTH_2]
- **Process Gaps / Ambiguities**:
  - [PLAN_GAP_1]
  - [PLAN_GAP_2]

## 4. Tasks Quality Review (`tasks.md`)

### 4.1 Coverage & Granularity

- **Coverage of spec/plan**: [TASKS_COVERAGE]
- **Granularity & ownership clarity**: [TASKS_GRANULARITY]
- **Validation / QA tasks included**: [TASKS_VALIDATION_COVERAGE]

### 4.2 Gaps & Observations

- **Strengths**:
  - [TASKS_STRENGTH_1]
  - [TASKS_STRENGTH_2]
- **Process Gaps / Ambiguities**:
  - [TASKS_GAP_1]
  - [TASKS_GAP_2]

## 5. Cross-Artifact Traceability

- **Spec → Plan traceability**: [TRACE_SPEC_TO_PLAN]
- **Plan → Tasks traceability**: [TRACE_PLAN_TO_TASKS]
- **Inconsistencies / missing links**: [TRACE_GAPS]

## 6. speckit / SDD Improvement Suggestions

- **Template Improvements**:
  - [IMPROVE_TEMPLATE_1]
  - [IMPROVE_TEMPLATE_2]
- **Prompt / Command Improvements**:
  - [IMPROVE_PROMPT_1]
  - [IMPROVE_PROMPT_2]
- **Automation / Checks**:
  - [IMPROVE_AUTOMATION_1]
  - [IMPROVE_AUTOMATION_2]
- **Workflow Practices**:
  - [IMPROVE_PROCESS_1]
  - [IMPROVE_PROCESS_2]

## 7. Follow-ups

- **Recommended process experiments**: [PROCESS_EXPERIMENTS]
- **Next review trigger**: [PROCESS_NEXT_REVIEW_TRIGGER]

## 8. Links & Artifacts

- **Specification**: .specify/specs/[REQUIREMENTS_KEY]/requirements.md
- **Plan**: .specify/specs/[REQUIREMENTS_KEY]/plan.md
- **Tasks**: .specify/specs/[REQUIREMENTS_KEY]/tasks.md
- **Data Model** (if any): .specify/specs/[REQUIREMENTS_KEY]/data-model.md
- **Contracts** (if any): .specify/specs/[REQUIREMENTS_KEY]/contracts/
- **Research** (if any): .specify/specs/[REQUIREMENTS_KEY]/research.md
- **Quickstart** (if any): .specify/specs/[REQUIREMENTS_KEY]/quickstart.md

---

## 9. Conclusion & Next Steps

- **Priority of recommendations (P0/P1/P2)**: [RECOMMENDATION_PRIORITY]
- **Proposed owner(s)**: [RECOMMENDATION_OWNERS]
- **Expected impact**: [RECOMMENDATION_IMPACT]

## 10. Feedback

Please share the contents of this document with the spec-kit framework developers.

---

## Placeholder Glossary

| Token | Meaning / Source |
|-------|------------------|
| [FEATURE_ID] | Sequential three-digit feature identifier (e.g., 001) |
| [FEATURE_NAME] | Short human-readable name of the feature |
| [REQUIREMENTS_KEY] | Combined ID + slug used as spec directory name (e.g., 001-create-taskify) |
| [REVIEW_DATE] | ISO date when this review was generated (YYYY-MM-DD) |
| [REVIEWER_NAME] | Name/label of the reviewing agent or persona |
| [PROCESS_*] | Process-level observations and summaries |
| [SPEC_*] | Spec quality observations derived from `.specify/specs/[REQUIREMENTS_KEY]/requirements.md` |
| [PLAN_*] | Plan quality observations derived from `.specify/specs/[REQUIREMENTS_KEY]/plan.md` |
| [TASKS_*] | Task quality observations derived from `.specify/specs/[REQUIREMENTS_KEY]/tasks.md` |
| [TRACE_*] | Cross-artifact traceability observations |
| [IMPROVE_*] | Suggestions for improving speckit/SDD templates, prompts, checks, and workflow |
| [RECOMMENDATION_*] | Summary-level conclusion fields for priority, owners, and impact |

## Replacement Rules

1. No placeholder token may remain in a committed review report.  
2. Dates must be valid ISO format.  
3. Keep lists dense; remove unused trailing placeholder lines.  
4. Preserve this heading structure for all review reports for consistency.  
5. When regenerating a review, either overwrite the existing `review.md` or archive the previous version according to project conventions.

<!-- End of review template -->
