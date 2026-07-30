# Requirements Guidelines

This document contains the detailed specification quality validation logic and guidelines for `/speckit.requirements`.

## Specification Quality Validation

After writing the initial spec, validate it against these quality criteria:

### Create Spec Quality Checklist

Generate a checklist file at `FEATURE_DIR/checklists/requirements.md`:

```markdown
# Specification Quality Checklist: [FEATURE NAME]

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: [DATE]
**Feature**: [Link to spec.md]

## Content Quality

- [ ] No implementation details (languages, frameworks, APIs)
- [ ] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [ ] All mandatory sections completed

## Requirement Completeness

- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous
- [ ] Success criteria are measurable
- [ ] Success criteria are technology-agnostic (no implementation details)
- [ ] All acceptance scenarios are defined
- [ ] Edge cases are identified
- [ ] Scope is clearly bounded
- [ ] Dependencies and assumptions identified

## Feature Readiness

- [ ] All functional requirements have clear acceptance criteria
- [ ] User scenarios cover primary flows
- [ ] Feature meets measurable outcomes defined in Success Criteria
- [ ] No implementation details leak into specification

## Notes

- Items marked incomplete require spec updates before `/speckit.clarify` or `/speckit.plan`
```

### Validation Process

1. Review the spec against each checklist item
2. Document specific issues found (quote relevant spec sections)
3. Treat `Feature ID: Need clarification` as pending (requires `/speckit.clarify`)

### Handle Validation Results

- **All items pass**: Mark checklist complete and proceed
- **Items fail (excluding [NEEDS CLARIFICATION])**:
  1. List failing items and specific issues
  2. Update spec to address each issue
  3. Re-run validation (max 3 iterations)
  4. If still failing, document remaining issues and warn user

- **[NEEDS CLARIFICATION] markers remain**:
  1. Extract all markers from the spec
  2. **LIMIT CHECK**: Keep only 3 most critical (by scope/security/UX impact)
  3. Present options to user in table format:

     ```markdown
     ## Question [N]: [Topic]
     
     **Context**: [Quote relevant spec section]
     **What we need to know**: [Specific question]
     
     **Suggested Answers**:
     
     | Option | Answer | Implications |
     |--------|--------|--------------|
     | A      | [First answer] | [Implications] |
     | B      | [Second answer] | [Implications] |
     | C      | [Third answer] | [Implications] |
     | Custom | Provide your own | [How to provide] |
     
     **Your choice**: _[Wait for user response]_
     ```

  4. Number questions sequentially (Q1, Q2, Q3 — max 3 total)
  5. Present all questions together before waiting
  6. Update spec after user responds — record each accepted answer under `## Clarifications` > `### Session YYYY-MM-DD` (same convention as /speckit.clarify), never as loose bullets outside a session heading
  7. Re-run validation after all resolved

## General Guidelines

### Quick Rules

- Focus on **WHAT** users need and **WHY**
- Avoid HOW to implement (no tech stack, APIs, code structure)
- Written for business stakeholders, not developers
- DO NOT create checklists embedded in the spec (separate command)

### Section Requirements

- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant; remove entirely if not applicable

### For AI Generation

1. **Make informed guesses**: Use context, industry standards, common patterns
   - **Conceptual/philosophy inputs** (idea essays, methodology write-ups): first distill them into concrete deliverable slices — typically "what the system itself must embody" vs "what its consumers receive" — before drafting user stories; this cuts clarification rounds
2. **Document assumptions**: Record defaults in the Assumptions section
3. **Limit clarifications**: Maximum 3 [NEEDS CLARIFICATION] markers for critical decisions only
4. **Prioritize clarifications**: scope > security/privacy > user experience > technical details
5. **Think like a tester**: Every vague requirement should fail "testable and unambiguous"

**Examples of reasonable defaults (don't ask about these)**:
- Data retention: Industry-standard for the domain
- Performance: Standard web/mobile expectations unless specified
- Error handling: User-friendly messages with appropriate fallbacks
- Authentication: Standard session-based or OAuth2 for web apps
- Integration patterns: RESTful APIs unless specified

### Success Criteria Guidelines

Success criteria must be:
1. **Measurable**: Include specific metrics (time, percentage, count, rate)
2. **Technology-agnostic**: No frameworks, languages, databases, or tools
3. **User-focused**: Outcomes from user/business perspective
4. **Verifiable**: Can be tested without knowing implementation details

**Good examples**:
- "Users can complete checkout in under 3 minutes"
- "System supports 10,000 concurrent users"
- "95% of searches return results in under 1 second"

**Bad examples** (implementation-focused):
- "API response time is under 200ms" → use "Users see results instantly"
- "Database can handle 1000 TPS" → use user-facing metric
- "React components render efficiently" → framework-specific
