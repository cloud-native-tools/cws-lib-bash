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

### III. Documentation-First
Documentation is a first-class deliverable and MUST take priority over test coverage:
- The project MUST maintain sufficiently detailed and accurate documentation so it can
  serve as reliable context for AI agents / large language models, supplying project
  knowledge and background information.
- Documentation MUST NOT record implementation details; implementation details belong in
  the code itself.
- Documents MUST stay focused and reasonably sized; when a document becomes too complex it
  MUST be split into smaller, cohesive documents.
- Documents MUST cross-reference one another so that basic navigation can be accomplished
  purely through internal links.
- Markdown documents MUST maintain basic metadata (e.g. title, purpose/summary, status,
  last-updated date, and related links).

Rationale: As agent capabilities grow, high-quality documentation becomes the primary
knowledge context that lets LLMs understand a project accurately and reason effectively;
it therefore ranks above testing in the principle hierarchy.

### IV. Test-First Development
Implementation MUST follow a Test-Driven Development style for core logic:
- Write or update tests BEFORE implementing new behavior.
- Ensure tests FAIL first (Red), then implement to make them PASS (Green).
- Refactor only with all tests passing (Refactor).

At minimum:
- Pure functions/utilities MUST have unit tests.
- Critical flows MUST have automated regression coverage.

Rationale: reduces regressions and clarifies intent.

### V. Integration & Contract Testing
Integration/contract tests SHOULD cover:
- Cross-service communication and external APIs.
- Shared schemas or data contracts.
- Critical end-to-end user journeys.

When real dependencies are hard to run locally, abstract them behind interfaces
and document follow-up contract tests in the plan/tasks.

Rationale: validates real-world behavior beyond unit tests.

### VI. Observability, Versioning & Simplicity
All components MUST be observable and versioned:
- Use structured logs for important events and errors.
- Prefer semantic versioning (MAJOR.MINOR.PATCH).
- Document any breaking changes and migration notes.
- Keep designs as simple as possible; avoid speculative features (YAGNI).

Rationale: makes systems debuggable, upgradable, and maintainable.

### VII. Continuous Integration & Quality Gates
Changes MUST be safe to merge:
- Linting, formatting, and basic tests MUST pass in CI.
- A minimal smoke test or example run SHOULD be provided for new features.
- New behavior MUST be reflected in specs/plan/tasks/docs where applicable.

Rationale: ensures consistent quality and predictable releases.

### VIII. Feature-Centric Development
Feature is the long-term core framework of the project:
- The Feature list MUST remain the "single source of truth" for the project.
- Every phase of spec → plan → tasks → implement MUST review Feature additions/merges/splits/deletions.
- Feature changes MUST be traceable to corresponding spec/plan evidence and recorded in the Feature detail.

Rationale: Keep project evolution Feature-centric to ensure long-term consistency and maintainability.

### IX. Better-Harness Orientation
The project is a *harness* for AI agent work — an environment in which an agent can
understand the task, execute on supported and repeatable paths, validate its changes,
deliver safely, and carry lessons forward. Improvement work MUST be oriented toward
making that harness better:
- Locate and motivate improvements against the five Agent Work Loop dimensions
  (Task Understanding, Controlled Execution, Change Validation, Reliable Delivery,
  Learning Capture); the canonical goal model is `.specify/shared/guidelines/better-harness.md`
  — reference it, do not restate it.
- Evidence discipline governs improvement claims: a configured asset proves at most that a
  mechanism exists (configured ≠ used); unobserved evidence MUST NOT be treated as a defect
  or a conclusion; "improved" MUST only be claimed from comparable before/after evidence.
- This principle adds orientation, not machinery: it MUST NOT justify new scoring systems,
  maturity reports, or tracking/recording engines.

Rationale: Like Dogfooding, Better Harness is a core mindset of the agent era — agents
change code fast, but the workflow around them (fuzzy goals, improvised steps, unproven
"it works", bypassed safeguards, lost lessons) is usually the weak point. Naming the goal
lets every improvement answer "which part of the harness does this strengthen?".

### X. Non-Destructive Remediation
Problems MUST be fixed at their root cause, never by destroying the artifact that
exhibits them:
- Deleting files, code, or data MUST NOT be used as a shortcut to make an immediate
  problem disappear; a "fix" that works by destruction proves the approach is wrong,
  not that the problem is solved.
- When an obstacle is encountered, the underlying cause MUST be identified and repaired;
  bypassing safety checks or removing the surface that exposes the problem is forbidden.
- When a destructive operation is genuinely required (deletion, force-overwrite, reset),
  it MUST be explicitly confirmed with the user before execution.

Rationale: destructive shortcuts destroy information and trust, and usually recreate the
same problem elsewhere; mandatory confirmation keeps irreversible actions under human control.

### XI. Complete & Correct Options, or None
Presenting options that are incomplete or incorrect is WORSE than presenting no options:
- Any option set offered to the user (choices, plans, recommendations) MUST be verified
  correct and MUST cover the realistic decision space.
- When correctness or completeness cannot be ensured, the open question MUST be presented
  directly instead of a partial or speculative option list.
- A known-imperfect option MUST be labeled with its gap rather than presented as solid.

Rationale: wrong or partial options mislead decisions more than no guidance at all — they
manufacture false confidence and foreclose alternatives the user never saw.

### XII. One Source of Truth (Authority & Reference Discipline)
Every fact — a concept's meaning, a normative rule, a threshold, an enumerated list, a
configuration value, a count — MUST have exactly one authoritative definition point (its
**owner**), and every other location MUST reach it by reference:
- The full discipline — owner declaration, the owner-selection order (code, then a
  machine-generated artifact, then an authored document), when a duplicate is legitimate,
  and the disagreement procedure — is defined once in
  `.specify/shared/guidelines/one-source-of-truth.md`; consumers MUST reference it, do not
  restate it.
- **Reference, not copy**: a consuming location cites the owner's path, plus a section anchor
  when the fact is one section of a larger owner, and MUST NOT restate the owner's table,
  threshold literal, or enumeration.
- **Repair direction**: on a disagreement the owner is authoritative and every diverging
  location is stale. The repair MUST convert the copy into a reference rather than re-word it
  to agree — correcting a copy is an instance fix, removing its ability to diverge is the
  mechanism fix.
- Only three duplicates are legitimate: a machine-regenerated copy, a literal pinned in a test
  so that it fails when the owner changes, and a dated record never cited as current reality.
  Any other repetition of a fact MUST be converted into a reference.
- This principle adds a way of writing, not machinery: it MUST NOT be used to justify a
  duplicate-fact scanner, an authority registry, or any other new scoring or tracking system.

Rationale: a fact restated in several places is not merely redundant — the copies disagree
silently, and a reader cannot tell which one is current. Correcting a copy leaves the copy, so
the drift returns; only removing its ability to diverge ends it.

### XIII. User-Facing Comprehension (No Jargon, With Context)
Every message a flow sends to a human MUST be readable by someone who did not take part in the
run, which bounds both its vocabulary and the context it carries:
- The discipline — the permitted-jargon whitelist, the forbidden-jargon blacklist, the context
  floor and ceiling, their adjudication order, and the reproducible verdict questions — is
  defined once in `.specify/shared/guidelines/user-facing-comprehension.md`; consumers MUST
  reference it, do not restate it.
- Jargon MUST be bounded rather than banned: a term may stand unexplained only where a closed
  whitelist condition holds, and anything outside that whitelist counts as a violation.
  Internal identifiers and engine call forms MUST NOT reach a reader who has a user-facing
  path available, and an abbreviation first used in a message MUST be annotated in place.
- Context MUST be bounded in the same breath: each message carries the facts a reader needs in
  order to act without opening another artifact, and reaches everything else by path
  reference. Restating an artifact the reader could open themselves MUST NOT be counted as
  supplying context.
- Judgement MUST be reproducible rather than a matter of taste: two independent reviewers
  applying the criteria to one message MUST reach the same verdict, and a disagreement is a
  defect in the criteria, not a difference of opinion.
- This principle adds a way of writing, not machinery: it MUST NOT be used to justify a jargon
  linter, a wording scorer, a maturity report, or any other new tracking system.

Rationale: an unreadable prompt does not fail loudly. A reader who has to decode a term guesses
and then acts confidently on the wrong meaning, and a reader who has to page away for context
answers a different question — both look like a completed flow while the decision goes wrong.

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
