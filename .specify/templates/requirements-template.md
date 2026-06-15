# Requirements Specification: [REQUIREMENT NAME]

**Requirement Branch**: `[###-requirement-name]`  
**Created**: [DATE]  
**Status**: Draft  
**Input**: User description: "$ARGUMENTS"

## Related Feature *(mandatory)*

<!--
  ACTION REQUIRED: Keep the default values as "Need clarification" in the initial draft.
  /speckit.clarify must resolve this section to the final Feature binding before planning.
-->

**Feature ID**: Need clarification  
**Feature Name**: Need clarification

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
  
  Assign priorities (P1, P2, P3, etc.) to each story, where P1 is the most critical.
  Think of each story as a standalone slice of functionality that can be:
  - Developed independently
  - Tested independently
  - Deployed independently
  - Demonstrated to users independently
-->

### User Story 1 - [Brief Title] (Priority: P1)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently - e.g., "Can be fully tested by [specific action] and delivers [specific value]"]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]
2. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 2 - [Brief Title] (Priority: P2)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]  
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if requirement involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]

### Measurement Sources & Collection Methods

<!--
  ACTION REQUIRED: For each measurable outcome above, specify:
  - Where the metric data will be collected from (logs, monitoring, user surveys, etc.)
  - How the data will be collected and aggregated
  - What the baseline measurement is (if applicable)
  - How often the metric will be measured
-->

- **SC-001 Source**: [Data source and collection method for SC-001]
- **SC-002 Source**: [Data source and collection method for SC-002]  
- **SC-003 Source**: [Data source and collection method for SC-003]
- **SC-004 Source**: [Data source and collection method for SC-004]

## Shared Strings *(optional, recommended when any string-literal is consumed verbatim by tests, contracts, snippets, or source)*

<!--
  ACTION REQUIRED:
  Use this section as the SINGLE SOURCE OF TRUTH for string literals that must match
  exactly across multiple artefacts (FRs, contracts, snippet bodies, test assertions,
  task descriptions). Downstream artefacts MUST cite by `<string-id>` rather than
  re-typing the text, so a rotation only edits this section.

  Examples of strings that belong here:
    - Error messages asserted by tests
    - Sentinel substrings in stderr / logs
    - Env var names, exit codes treated as contract
    - URL paths or filenames that contracts pin to a specific string

  Omit this section entirely if no such cross-artefact strings exist.
-->

| String ID | Value (verbatim) | Consumed by |
|-----------|------------------|-------------|
| `STR-001` | "[exact string, quoted]" | FR-XXX, contracts/xxx.md C-N, tasks T-NNN, snippet `<path>` |
| `STR-002` | "[exact string, quoted]" | [list of citing artefacts] |

**Citation convention**: When an FR, contract, task, or test references one of these strings, write `[[STR-NNN]]` instead of copy-pasting the literal. CI / `/speckit.analyze` can then verify that every `[[STR-NNN]]` reference resolves to a row in this section.

## Clarifications

<!-- 
This section will be populated by /speckit.clarify command with questions and answers.
Format: - Q: <question> → A: <answer>
-->
