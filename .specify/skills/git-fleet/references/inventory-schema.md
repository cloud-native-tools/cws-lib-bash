# inventory schema

The engine holds no host list and no absolute paths. Everything machine-specific
lives in this file, supplied via `--inventory` or `$GIT_FLEET_INVENTORY`.

## Top level

| Field | Required | Meaning |
|-------|----------|---------|
| `version` | no | Schema version; currently `1`. |
| `envs` | **yes** | Map of environment name → environment spec. Empty ⇒ hard error. |
| `internal_origin_patterns` | no | Substrings identifying *your* git hosts (e.g. a company git domain). Manifest lines are kept only when they contain one of these. Without it, manifest edge collection is skipped entirely. |
| `manifests` | no | Manifest filenames to scan. Default: `go.mod`, `package.json`, `pom.xml`, `Cargo.toml`, `pyproject.toml`. |

## Environment spec

| Field | Required | Meaning |
|-------|----------|---------|
| `roots` | **yes** | Absolute directory roots to scan. **This is the management boundary** — a git repo outside every root is by definition out of scope. |
| `transport` | no | `local` (run the probe here) or `ssh` (run it over ssh). Defaults to `local` when the env is literally named `local`, otherwise `ssh`. Declare it explicitly; the default exists only for brevity. |
| `target` | when `transport: ssh` | The ssh destination. Must already resolve through the caller's ssh config — the engine adds no config file and no credentials. Defaults to the env name. |
| `depth` | no | `find -maxdepth` for repo discovery. Default `4`, which covers `<root>/<org>/<repo>/<submodule>/.git`. |
| `kind` | no | Free-text label carried into the snapshot for reporting only. |
| `availability` | no | Free-text note, e.g. that the host is only reachable on a particular network. Purely documentation: the engine still probes and records `unreachable`. |
| `roots_verified` | no | `false` marks a root that is an unconfirmed guess. The first reachable scan should confirm the path and flip it to `true`. Prevents a wrong guess from quietly looking like an empty machine. |

## Example

```yaml
version: 1

internal_origin_patterns:
  - git.example.com

manifests:
  - go.mod
  - package.json

envs:
  local:
    kind: workstation
    transport: local
    roots:
      - /home/me/project
    depth: 4
    roots_verified: true

  build-host-1:
    kind: linux-remote
    transport: ssh
    target: build-host-1
    roots:
      - /srv/project
      - /data/work
    depth: 4
    roots_verified: true

  laptop-at-home:
    kind: laptop
    transport: ssh
    target: laptop-at-home
    roots:
      - /Users/me/project
    depth: 4
    availability: reachable only on the home network
    roots_verified: false
```

## Validation and refusal

Both `target` and every `roots` entry are interpolated into a remote shell command
line, so both are checked against a character whitelist before use:

- `target` — `[A-Za-z0-9._-]+`
- `roots`, `manifests` — `[A-Za-z0-9._/+-]+`
- `internal_origin_patterns` — `[A-Za-z0-9._/@:-]+`

A violation yields `status: config-error` for that environment, never a relaxed
execution. This is what stops an option-shaped "host name" such as
`-oProxyCommand=...` from reaching `ssh`.

Roots containing spaces are therefore unsupported by design: the probe word-splits
`$ROOTS`, and permitting quoting here would mean accepting arbitrary shell text.

## Scope consequences

Because `roots` is the boundary, adding a directory to `roots` is how a repo enters
management, and removing it is how a repo leaves. There is no per-repo allow/deny
list — that would be a second, redundant source of truth about scope.
