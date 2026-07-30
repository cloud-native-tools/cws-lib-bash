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
| Core | `profile.d/` | Numbered `NN_*.sh` loaded at init: vars, aliases, logging, formatting, file/network/storage/process utilities |
| Domains | `scripts/` | Numbered `NNN_<domain>.sh` grouped by technology: packages (0xx), system (01x), network (03x), toolchains (11x), containers/k8s (2xx), AI tooling (31x) |
| Tests | `test/` | Bash test scripts run via `cws_bash_test` |

## Key conventions

- Functions: `snake_case` with domain prefix (e.g. `git_switch`, `docker_*`).
- Numeric file prefixes define load order and domain grouping.
- Return codes via `${RETURN_SUCCESS}` / `${RETURN_FAILURE}`; logging via `log`.
- Cross-platform: Linux and macOS supported by feature detection in core.

## Decisions

No ADRs recorded yet — see [docs/decisions/index.md](docs/decisions/index.md).
