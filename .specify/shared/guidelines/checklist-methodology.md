# Checklist Methodology

This document contains detailed examples, anti-examples, and methodology guidance for the `/speckit.checklist` command.

## Core Concept: "Unit Tests for English"

Checklists are **UNIT TESTS FOR REQUIREMENTS WRITING** — they validate the quality, clarity, and completeness of requirements in a given domain.

**NOT for verification/testing**:
- NOT "Verify the button clicks correctly"
- NOT "Test error handling works"
- NOT "Confirm the API returns 200"
- NOT checking if code/implementation matches the plan/specifications

**FOR requirements quality validation**:
- "Are visual hierarchy requirements defined for all card types?" [Completeness]
- "Is 'prominent display' quantified with specific sizing/positioning?" [Clarity]
- "Are hover state requirements consistent across all interactive elements?" [Consistency]
- "Are accessibility requirements defined for keyboard navigation?" [Coverage]
- "Do the requirements define what happens when logo image fails to load?" [Edge Cases]

## Category Structure

Group items by requirement quality dimensions:
- **Requirement Completeness** — Are all necessary requirements documented?
- **Requirement Clarity** — Are requirements specific and unambiguous?
- **Requirement Consistency** — Do requirements align without conflicts?
- **Acceptance Criteria Quality** — Are success criteria measurable?
- **Scenario Coverage** — Are all flows/cases addressed?
- **Edge Case Coverage** — Are boundary conditions defined?
- **Non-Functional Requirements** — Performance, Security, Accessibility — are they specified?
- **Dependencies & Assumptions** — Are they documented and validated?
- **Ambiguities & Conflicts** — What needs clarification?

## How To Write Checklist Items

### Item Structure Pattern

Each item should follow:
- Question format asking about requirement quality
- Focus on what's WRITTEN (or not written) in the requirements (What)
- Include quality dimension in brackets [Completeness/Clarity/Consistency/etc.]
- Reference requirement section using `[Req §...]` (e.g., `[Req §FR-001]`)
- Use `[Gap]` marker when checking for missing requirements

### Examples by Quality Dimension

**Completeness**:
- "Are error handling requirements defined for all API failure modes? [Gap]"
- "Are accessibility requirements specified for all interactive elements? [Completeness]"
- "Are mobile breakpoint requirements defined for responsive layouts? [Gap]"

**Clarity**:
- "Is 'fast loading' quantified with specific timing thresholds? [Clarity, Req §NFR-2]"
- "Are 'related episodes' selection criteria explicitly defined? [Clarity, Req §FR-5]"
- "Is 'prominent' defined with measurable visual properties? [Ambiguity, Req §FR-4]"

**Consistency**:
- "Do navigation requirements align across all pages? [Consistency, Req §FR-10]"
- "Are card component requirements consistent between landing and detail pages? [Consistency]"

**Coverage**:
- "Are requirements defined for zero-state scenarios (no episodes)? [Coverage, Edge Case]"
- "Are concurrent user interaction scenarios addressed? [Coverage, Gap]"
- "Are requirements specified for partial data loading failures? [Coverage, Exception Flow]"

**Measurability**:
- "Are visual hierarchy requirements measurable/testable? [Acceptance Criteria, Req §FR-1]"
- "Can 'balanced visual weight' be objectively verified? [Measurability, Req §FR-2]"

### Scenario Classification & Coverage

Check if requirements exist for: Primary, Alternate, Exception/Error, Recovery, Non-Functional scenarios.
- For each scenario class: "Are [scenario type] requirements complete, clear, and consistent?"
- If scenario class missing: "Are [scenario type] requirements intentionally excluded or missing? [Gap]"
- Include resilience/rollback when state mutation occurs

### Traceability Requirements

- MINIMUM: ≥80% of items MUST include at least one traceability reference
- Each item should reference: requirement section `[Req §X]`, or use markers: `[Gap]`, `[Ambiguity]`, `[Conflict]`, `[Assumption]`
- When citing specification artifacts, MUST ask whether the spec decision is traceable to a requirement
- If no ID system exists: "Is a requirement & acceptance criteria ID scheme established? [Traceability]"

### Surface & Resolve Issues

Ask questions about the requirements themselves:
- Ambiguities: "Is the term 'fast' quantified with specific metrics? [Ambiguity, Req §NFR-1]"
- Conflicts: "Do navigation requirements conflict between §FR-10 and §FR-10a? [Conflict]"
- Assumptions: "Is the assumption of 'always available podcast API' validated? [Assumption]"
- Dependencies: "Are external podcast API requirements documented? [Dependency, Gap]"

## Content Consolidation Rules

- Soft cap: If raw candidate items > 40, prioritize by risk/impact
- Merge near-duplicates checking the same requirement aspect
- If >5 low-impact edge cases, create one item: "Are edge cases X, Y, Z addressed in requirements? [Coverage]"

## Prohibited Patterns (makes it an implementation test)

- Any item starting with "Verify", "Test", "Confirm", "Check" + implementation behavior
- References to code execution, user actions, system behavior
- "Displays correctly", "works properly", "functions as expected"
- "Click", "navigate", "render", "load", "execute"
- Test cases, test plans, QA procedures
- Implementation details (frameworks, APIs, algorithms)
- Converting design decisions into requirements without justification

## Required Patterns (tests requirements quality)

- "Are [requirement type] defined/specified/documented for [scenario]?"
- "Is [vague term] quantified/clarified with specific criteria?"
- "Are requirements consistent between [section A] and [section B]?"
- "Can [requirement] be objectively measured/verified?"
- "Are [edge cases/scenarios] addressed in requirements?"
- "Do the requirements define [missing aspect]?"

## Example Checklist Types

### UX Requirements Quality (`ux.md`)

- "Are visual hierarchy requirements defined with measurable criteria? [Clarity, Req §FR-1]"
- "Is the number and positioning of UI elements explicitly specified? [Completeness, Req §FR-1]"
- "Are interaction state requirements (hover, focus, active) consistently defined? [Consistency]"
- "Are accessibility requirements specified for all interactive elements? [Coverage, Gap]"
- "Is fallback behavior defined when images fail to load? [Edge Case, Gap]"
- "Can 'prominent display' be objectively measured? [Measurability, Req §FR-4]"

### API Requirements Quality (`api.md`)

- "Are error response formats specified for all failure scenarios? [Completeness]"
- "Are rate limiting requirements quantified with specific thresholds? [Clarity]"
- "Are authentication requirements consistent across all endpoints? [Consistency]"
- "Are retry/timeout requirements defined for external dependencies? [Coverage, Gap]"
- "Is versioning strategy documented in requirements? [Gap]"

### Performance Requirements Quality (`performance.md`)

- "Are performance requirements quantified with specific metrics? [Clarity]"
- "Are performance targets defined for all critical user journeys? [Coverage]"
- "Are performance requirements under different load conditions specified? [Completeness]"
- "Can performance requirements be objectively measured? [Measurability]"
- "Are degradation requirements defined for high-load scenarios? [Edge Case, Gap]"

### Security Requirements Quality (`security.md`)

- "Are authentication requirements specified for all protected resources? [Coverage]"
- "Are data protection requirements defined for sensitive information? [Completeness]"
- "Is the threat model documented and requirements aligned to it? [Traceability]"
- "Are security requirements consistent with compliance obligations? [Consistency]"
- "Are security failure/breach response requirements defined? [Gap, Exception Flow]"

## Anti-Examples: What NOT To Do

**WRONG — These test implementation, not requirements:**

```markdown
- [ ] CHK001 - Verify landing page displays 3 episode cards [Req §FR-001]
- [ ] CHK002 - Test hover states work correctly on desktop [Req §FR-003]
- [ ] CHK003 - Confirm logo click navigates to home page [Req §FR-010]
- [ ] CHK004 - Check that related episodes section shows 3-5 items [Req §FR-005]
```

**CORRECT — These test requirements quality:**

```markdown
- [ ] CHK001 - Are the number and layout of featured episodes explicitly specified? [Completeness, Req §FR-001]
- [ ] CHK002 - Are hover state requirements consistently defined for all interactive elements? [Consistency, Req §FR-003]
- [ ] CHK003 - Are navigation requirements clear for all clickable brand elements? [Clarity, Req §FR-010]
- [ ] CHK004 - Is the selection criteria for related episodes documented? [Gap, Req §FR-005]
- [ ] CHK005 - Are loading state requirements defined for asynchronous episode data? [Gap]
- [ ] CHK006 - Can "visual hierarchy" requirements be objectively measured? [Measurability, Req §FR-001]
```

**Key Differences:**
- Wrong: Tests if the system works correctly → Correct: Tests if the requirements are written correctly
- Wrong: Verification of behavior → Correct: Validation of requirement quality
- Wrong: "Does it do X?" → Correct: "Is X clearly specified?"
