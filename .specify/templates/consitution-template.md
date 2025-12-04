# [PROJECT_NAME] Constitution
<!--
This is a PRESET template containing a set of generic project principles
and workflow guidelines. It is intended as a starting point only.

When adopting this constitution for a specific project, you MUST review,
add, remove, or modify principles and sections to match the actual
context, risk profile, and organizational policies of your project.
Do not assume this template is sufficient without customization.
-->

## Core Principles

### I. Library-First Design
Every significant feature MUST begin as a cohesive, reusable library (module/package).
Libraries MUST:
- Be self-contained and independently testable.
- Have a single, clearly documented responsibility.
- Avoid being mere organizational/wrapper shells without real behavior.

Rationale: encourages reuse, clear boundaries, and easier testing.

### II. CLI & Text I/O Interface
Each library SHOULD expose a command-line interface (CLI) for core operations.
CLIs MUST:
- Accept input via stdin/arguments/files using plain text or JSON.
- Write normal results to stdout and errors to stderr.
- Prefer JSON for machine consumption and human-readable text for operators.

Rationale: standardizes integration, observability, and automation.

### III. Test-First Development (NON-NEGOTIABLE)
Implementation MUST follow a Test-Driven Development style for core logic:
- Write or update tests BEFORE implementing new behavior.
- Ensure tests FAIL first (Red), then implement to make them PASS (Green).
- Refactor only with all tests passing (Refactor).

At minimum:
- Pure functions/utilities MUST have unit tests.
- Critical flows MUST have automated regression coverage.

Rationale: reduces regressions and clarifies intent.

### IV. Integration & Contract Testing
Integration/contract tests SHOULD cover:
- Cross-service communication and external APIs.
- Shared schemas or data contracts.
- Critical end-to-end user journeys.

When real dependencies are hard to run locally, abstract them behind interfaces
and document follow-up contract tests in the plan/tasks.

Rationale: validates real-world behavior beyond unit tests.

### V. Observability, Versioning & Simplicity
All components MUST be observable and versioned:
- Use structured logs for important events and errors.
- Prefer semantic versioning (MAJOR.MINOR.PATCH).
- Document any breaking changes and migration notes.
- Keep designs as simple as possible; avoid speculative features (YAGNI).

Rationale: makes systems debuggable, upgradable, and maintainable.

### VI. Continuous Integration & Quality Gates
Changes MUST be safe to merge:
- Linting, formatting, and basic tests MUST pass in CI.
- A minimal smoke test or example run SHOULD be provided for new features.
- New behavior MUST be reflected in specs/plan/tasks/docs where applicable.

Rationale: ensures consistent quality and predictable releases.

## [SECTION_2_NAME]
<!-- Example: Additional Constraints, Security Requirements, Performance Standards, etc. -->

[SECTION_2_CONTENT]
<!-- Example: Technology stack requirements, compliance standards, deployment policies, etc. -->

## [SECTION_3_NAME]
<!-- Example: Development Workflow, Review Process, Quality Gates, etc. -->

[SECTION_3_CONTENT]
<!-- Example: Code review requirements, testing gates, deployment approval process, etc. -->

## Governance
<!-- Projects SHOULD refine this to match their org/governance needs. -->

[GOVERNANCE_RULES]
<!-- Example: Constitution supersedes other guidelines; Amendments require proposal,
review, and version bump; All PRs MUST check compliance with core principles. -->

**Version**: [CONSTITUTION_VERSION] | **Ratified**: [RATIFICATION_DATE] | **Last Amended**: [LAST_AMENDED_DATE]
<!-- Example: Version: 1.0.0 | Ratified: 2025-01-01 | Last Amended: 2025-01-01 -->
