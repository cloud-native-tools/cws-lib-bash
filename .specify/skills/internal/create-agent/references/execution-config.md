# Execution Config Schema (`configs/<slug>.yaml`)

**Schema authority** for subagent dispatch configuration. This file owns the field-level
schema; the *runtime* behavior is owned by the deterministic engine
`.specify/scripts/python/execution-config.py` (actions `resolve` / `validate` / `list-configs`). The
CLI capability values are owned **only** by `CAPABILITY_MATRIX` in that engine — this
document references it and never copies its table.

## Layers and precedence

| Layer | Location | Tracked |
|-------|----------|---------|
| `defaults` | `.specify/agents/execution/configs/_defaults.yaml` (seeded by `specify init` from `.specify/templates/execution-config-defaults.yaml`) | yes |
| `agent-config` | `.specify/agents/execution/configs/<slug>.yaml` | yes |
| `inline` | `--mode / --cli / --model / --reasoning-effort / --context-window / --extra-flags / --log-dir / --quantification-method` at dispatch time | n/a |

Precedence: **defaults < agent-config < inline**. A missing key inherits the lower layer.
The effective config always contains the eight keys `mode / cli / model /
reasoning_effort / context_window / extra_flags / log_dir / quantification`; a cleared or
absent value field is `null` and produces no CLI flag and no `source_chain` entry.

## Fields

| Key | Layers | Kind | Rule |
|-----|--------|------|------|
| `agent` | agent-config only | identity | must equal the requested `<slug>` |
| `mode` | all | topology identity | `native` \| `virtual` \| `external`; no `auto` value |
| `cli` | all | topology identity | a CLI name declared by `CAPABILITY_MATRIX`; external requires one |
| `model` | all | override | string |
| `reasoning_effort` | all | override | string |
| `context_window` | all | override | positive integer |
| `extra_flags` | all | override | one line; `shlex`-tokenizable; no managed flags (`-m`, `--model`, `--reasoning-effort`, `--context-window`, incl. `=` forms) |
| `log_dir` | all | override | must resolve inside `.specify/agents/execution/logs` |
| `quantification.method` | all | method selector | `auto` \| `declared` \| `qoder-settings` \| `none` |

## Clear sentinels

For the five value fields (`model`, `reasoning_effort`, `context_window`, `extra_flags`,
`log_dir`), the value `""` or `auto` clears the lower-layer value. `quantification.method=auto`
is a **method value**, not a clear sentinel.

## Identity vs override: coverage, conflict, and the defaults skip

- `mode` and `cli` are **topology identity** fields; the other five are **overrides**.
- **Coverage**: an override value replaces the lower layer's value (that is normal layering).
- **Conflict**: agent-config and inline both declare `mode` (or both declare `cli`) with
  different values → the dispatch is rejected at parse time with the conflicting field named.
- An explicit `cli` combined with an effectively `native`/`virtual` mode is rejected
  (`cli` applies to external dispatch only). An explicit `mode: native|virtual` combined with
  any non-clear override is rejected with a direction to `external`. Override-triggered
  `external` takes priority over a participating defaults layer's `mode: native|virtual`.
- The defaults layer's `cli` is a **default value**, not a declaration. When agent-config or
  inline selects a different CLI, the **whole defaults layer is skipped** (all keys,
  including `mode`, `cli`, and `quantification.method`) and recorded in `skipped_layers`; no
  qoder default may leak into another CLI's effective config, `cli_args`, or record.
- An explicit `mode: external` with no effective `cli` is rejected.

## Quantification methods

Registered methods: `auto / declared / qoder-settings / none`. `auto` resolves in this fixed
order (the engine is the exact authority; E5 in the feature data model holds the order):

1. external + any non-clear override at agent/inline → `declared`
2. external + no explicit override + `cli=qodercli` → `qoder-settings`
3. native/virtual + qoder host → `qoder-settings`
4. otherwise → `none` with a warning

`declared` requires effective model + reasoning_effort + context_window (whether requested
explicitly or produced by auto); `qoder-settings` requires qoder support; incompatible
combinations exit 2 with no downgrade. The capability matrix constrains the **resolved**
method only — `auto` is never rejected merely for not appearing in a per-CLI method list.

## CLI capability

Supported CLI names, per-CLI external support, accepted flags, and available quantification
methods are declared **only** in `CAPABILITY_MATRIX` inside `.specify/scripts/python/execution-config.py`.
Read the code (or run `resolve` on a candidate config) for the current values; do not
reproduce the table in a document or an agent definition.

## Defaults layer and init seeding

- Content owner: `.specify/templates/execution-config-defaults.yaml` (packaged with the CLI).
- `specify init` seeds `.specify/agents/execution/configs/_defaults.yaml` **only when the
  file is absent**; an existing file (including a user-edited one) is never overwritten.
- A missing defaults layer makes `resolve` exit 2 with the path and the `specify init` repair.

## Config snapshot and per-dispatch quantification

Every successful `resolve` writes `.specify/agents/execution/logs/config-snapshots/<config_id>.json`
(workspace-relative POSIX path in the output). The snapshot carries `config_id`,
`resolved_at`, the effective config, `source_chain`, `skipped_layers`, `requires_external`,
`cli_args`, and `log_dir`. `config_id` is the first 16 hex chars of the SHA-256 of the
canonical JSON form of `effective` (sorted keys, compact separators, UTF-8).

After an **external** dispatch, `exec-quant.py --action collect-dispatch --unit-id
agent:<slug> --run-id <label> --snapshot <snapshot> --config-id <config_id>` writes one
record per `(agent:<slug>, dispatch label)`. It recomputes the id from `snapshot.effective`
and requires it to equal both the snapshot's id and `--config-id`; a mismatch is a visible
non-blocking failure (exit 1, no record). A same-id re-resolve overwrites the snapshot, so
collect before another same-id resolve when elapsed fallback matters.

## Validation and the write-then-validate obligation

After writing or editing `configs/<slug>.yaml`, run:

```bash
python3 .specify/scripts/python/execution-config.py --action validate --agent <slug> --workspace-root <project-dir>
```

A non-zero exit (2) is a failed write: report the engine's field/support-set errors and do not
report success. `--action list-configs` discovers all agent configs and reports invalid
entries without aborting.

The YAML subset is deliberately minimal: comments, `key: value`, and one nested
`quantification:` level. Tabs, lists, deeper nesting, duplicate keys, unknown keys, invalid
types/enums, `context_window` ≤ 0 or non-integer, `log_dir` outside the logs tree, and
managed flags inside `extra_flags` are all rejected with the file and field named.
