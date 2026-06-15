<!-- Sync Impact Report
- Version change: 1.1.0 -> 1.2.0.1
- Bump type: MINOR (new principle added, existing principles renumbered)
- Added principles: "I. Universal Generality" — maximum reusability, zero customization logic
- Modified principles: All existing principles renumbered (I→II, II→III, III→IV, IV→V, V→VI, VI→VII, VII→VIII)
- Added sections: None
- Removed sections: None
- Templates requiring updates:
  - /.specify/templates/plan-template.md (✅ no action — reads principles dynamically)
  - /.specify/templates/requirements-template.md (✅ no action — no hardcoded principle refs)
  - /.specify/templates/tasks-template.md (✅ no action — reads principle from constitution dynamically)
- Follow-up TODOs: None
-->
# CWS-Lib-Bash Constitution

## Core Principles

### I. Universal Generality
This library exists to provide maximum universality. All scripts and functions
MUST be general-purpose utilities with zero project-specific or
environment-specific customization logic.

Functions MUST:
- Solve generic, reusable problems — not encode any single project's workflow.
- Accept all environment-specific values via parameters or environment variables;
  NEVER hardcode paths, hostnames, credentials, project names, or platform URLs.
- Avoid assumptions about the caller's directory layout, deployment target,
  or organizational conventions beyond POSIX/GNU norms.
- Be immediately usable by any Bash user without modification or forking.

When evaluating whether code belongs in this library, apply this test:
"Would a developer on a completely unrelated project find this function useful
as-is?" If not, the code does not belong here.

Rationale: the library's value is proportional to its generality; every
piece of baked-in customization narrows the audience and creates maintenance
debt that benefits only one consumer.

### II. Library-First Design
Every significant feature MUST begin as a cohesive, reusable library (module/package).
Libraries MUST:
- Be organized by technology domain in `scripts/<domain>.sh` (e.g., `docker.sh`, `network.sh`).
- Be self-contained and independently testable.
- Have a single, clearly documented responsibility.
- Avoid being mere organizational/wrapper shells without real behavior.

Rationale: encourages reuse, clear boundaries, and easier testing.

### III. CLI & Text I/O Interface
Each library SHOULD expose command-line accessible functions.
CLIs MUST:
- Be executable via `./bin/cws_bash_run` for core operations.
- Accept input via arguments or stdin.
- Write normal results to stdout and errors to stderr.
- Prefer plain text or JSON for machine consumption.

Rationale: standardizes integration, observability, and automation.

### IV. Test-First Development
Implementation MUST follow a Test-Driven Development style for core logic:
- Write or update tests in `test/` BEFORE implementing new behavior.
- Ensure tests FAIL first (Red), then implement to make them PASS (Green).
- Refactor only with all tests passing (Refactor).

At minimum:
- Pure functions/utilities MUST have unit tests.
- Critical flows MUST have automated regression coverage.

Rationale: reduces regressions and clarifies intent.

### V. Integration & Contract Testing
Integration/contract tests SHOULD cover:
- Cross-service communication and external APIs.
- System state changes (e.g., file creation, network config).
- Critical end-to-end user journeys.

Rationale: validates real-world behavior beyond unit tests.

### VI. Observability, Versioning & Simplicity
All components MUST be observable and versioned:
- Use `log` function for structured logs (info, warn, error).
- Prefer Semantic Versioning (MAJOR.MINOR.PATCH).
- Document any breaking changes and migration notes.
- Keep designs as simple as possible; avoid speculative features (YAGNI).

Rationale: makes systems debuggable, upgradable, and maintainable.

### VII. Continuous Integration & Quality Gates
Changes MUST be safe to merge:
- `shellcheck` MUST pass for all scripts.
- Unit tests (`cws_bash_test`) MUST pass in CI.
- New behavior MUST be reflected in specs/plan/tasks/docs where applicable.

Rationale: ensures consistent quality and predictable releases.

### VIII. Feature-Centric Development
Feature is the long-lived core framework of the project:
- The Feature list MUST be the "Single Source of Truth".
- Every step in spec → plan → tasks → implement MUST re-evaluate Feature additions/merges/splits/removals.
- Feature changes MUST be traceable to specific spec/plan evidence and recorded in Feature details.

Rationale: centers project evolution on Features to ensure long-term consistency and maintainability.

## Bash Coding Standards

### Naming & Style
- Functions MUST use `snake_case` with domain prefix (e.g., `network_test_connectivity`).
- Variables MUST be `local`, use braces `${var}`, and handle defaults `${var:-}`.
- Code MUST follow Google Shell Style Guide where applicable.

### Error Handling & Dependencies
- Functions MUST use standard return codes (`${RETURN_SUCCESS:-0}` / `${RETURN_FAILURE:-1}`).
- Dependencies MUST be checked using `have <cmd>` at the start.
- Parameters MUST be validated immediately.

### Compatibility
- Scripts MUST support both Linux and macOS.
- Platform differences MUST be handled via `is_linux()` / `is_macos()` helpers.

## Contribution Guidelines

- All changes MUST be submitted via Pull Request.
- PRs MUST pass all static analysis and tests.
- Commits SHOULD follow Conventional Commits format.

## Governance

### Amendment Process
This Constitution supersedes all other development practices. Amendments require a Pull Request with documentation updates and approval from maintainers.

### Versioning
This project follows Semantic Versioning.
- MAJOR: Backward incompatible governance/principle removals or redefinitions.
- MINOR: New principle/section added or materially expanded guidance.
- PATCH: Clarifications, wording, typo fixes, non-semantic refinements.

### Compliance
All Pull Requests must be reviewed against these principles. Code that violates these principles MUST NOT be merged until corrected.

**Version**: 1.2.0.1 | **Ratified**: 2025-12-04 | **Last Amended**: 2026-06-15
