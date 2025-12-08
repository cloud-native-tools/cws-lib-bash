<!-- Sync Impact Report
- Version change: 0.0.0 -> 1.0.0
- Modified principles: Defined initial principles based on project documentation.
- Added sections: Core Principles, Governance.
- Templates requiring updates: /.specify/templates/plan-template.md (✅ updated)
-->
# CWS-Lib-Bash Constitution

## Core Principles

### I. Modular & Domain-Driven
Functions MUST be organized by technology domain in `scripts/<domain>.sh`. Each module should be self-contained where possible, focusing on a specific tool or technology (e.g., `docker.sh`, `git.sh`).

### II. Consistent Naming & Style
Functions MUST use `snake_case` with domain prefix (e.g., `network_test_connectivity`). Variables MUST be `local`, use braces `${var}`, and handle defaults `${var:-}`.

### III. Robust Error Handling
Functions MUST use standard return codes (`${RETURN_SUCCESS:-0}` / `${RETURN_FAILURE:-1}`). Dependencies MUST be checked using `have <cmd>` at the start. Parameters MUST be validated.

### IV. Unified Logging
All informational and error output MUST use the `log` function with appropriate levels (`info`, `notice`, `warn`, `error`, `fatal`). Direct `echo` to stdout/stderr should be avoided for status messages.

### V. Cross-Platform Compatibility
Scripts MUST support both Linux and macOS. Platform-specific logic MUST be handled using `is_linux()` or `is_macos()` helpers.

### VI. Standardized Execution
All commands MUST be executable via `./bin/cws_bash_run <function> [args]`. The environment MUST be loadable via `source ./bin/cws_bash_env`.

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

**Version**: 1.0.0 | **Ratified**: 2025-12-04 | **Last Amended**: 2025-12-04
