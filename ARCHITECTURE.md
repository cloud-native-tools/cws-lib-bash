# Architecture

One-page summary. Details live in [docs/concepts/](docs/concepts/index.md);
decisions in [docs/decisions/](docs/decisions/index.md).

## Overview

cws-lib-bash is a function library: sourcing it injects namespaced Bash
functions into the shell. There is no daemon or build step — the runtime is
the user's shell session.

## Layers

| Layer | Location | Role |
|-------|----------|------|
| Entrypoints | `bin/` | `cws_bash_setup` (install), `cws_bash_env` (load into shell), `cws_bash_run` (one-shot call), `cws_bash_test` (test runner) |
| Core | `profile.d/` | Numbered `NN_*.sh` loaded at init: vars, probes (`02_probe.sh`), aliases, logging, formatting, file/network/storage/process utilities |
| Domains | `scripts/` | Numbered `NNN_<domain>.sh` grouped by technology: packages (0xx), system (01x), network (03x), toolchains (11x), containers/k8s (2xx), AI tooling (31x) |
| Tests | `test/` | Bash test scripts run via `cws_bash_test` |

## Key conventions

- Functions: `snake_case` with domain prefix (e.g. `git_switch`, `docker_*`).
- Numeric file prefixes define load order and domain grouping.
- Detection is centralized in the probe layer: `is_*` answers "is the system/environment X" (properties), `has_*` answers "is capability X present" (commands). `has_cmd <name>` owns command-presence testing and `cmd_path <name>` owns path resolution; new code calls a predicate instead of inlining a `command -v` test. Both degrade to `type`/`hash`/`which` when the `command` builtin itself is unusable. Shell state and project capability stay separate: `is_venv` (a venv is activated) vs `has_venv` (the project ships a usable `.venv`, resolved by `venv_python`). Predicates print nothing and return `${RETURN_SUCCESS}`/`${RETURN_FAILURE}`.
- Return codes via `${RETURN_SUCCESS}` / `${RETURN_FAILURE}`; logging via `log`.
- Cross-platform: Linux and macOS supported by feature detection in core.

## Decisions

No ADRs recorded yet — see [docs/decisions/index.md](docs/decisions/index.md).
