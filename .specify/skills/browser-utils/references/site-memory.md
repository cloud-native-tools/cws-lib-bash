# Site Memory (浏览器站点记忆)

Per-site persistent memory for browser-utils: every site you operate gets a
memory directory keyed by domain, and a four-state lifecycle drives how tasks
against that site are executed. Managed exclusively by the deterministic engine
`${SKILL_HOME}/scripts/site-memory.py` — never hand-edit `state.json`.

## Layout

```text
${SKILL_HOME}/site/<host[:port]>/
├── state.json              # Site State — the state machine file (engine-only writes)
├── records/<task>.jsonl    # Operation Records — exploration-phase trace, append-only
├── recipe.json             # Request Recipe — optimization-phase distillation
├── validation/<run>.json   # Validation Evidence — one file per validation run
└── notes.md                # optional free-text site quirks (agent-written)
```

The directory is created by `--action init` on first contact with a site. If
`state.json` is missing or corrupted, treat the site as having no memory
(`get-state` returns `state: null`) — re-run `init`; a broken memory never
blocks completing the user's task.

## State machine

```text
exploration ──(records complete)──▶ optimization ──(recipe valid)──▶ validation ──(verdict=pass)──▶ sealed
                                      ▲                                  │                          │
                                      └────────(verdict=fail / drift)────┴──────(rollback)──────────┘
```

- **exploration**: complete the task with page-level operations while recording
  every DOM action and underlying network request — including failures and
  retries — via `--action append-record`.
- **optimization**: distill the trace into `recipe.json` (request-level steps
  first; steps that cannot be request-ified stay `type: "page"` with an explicit
  `reason`), then complete the task in hybrid form.
- **validation**: execute the recipe end-to-end against its `expect` clauses;
  `--action record-validation` persists the evidence and moves the state
  automatically (pass → sealed, fail → optimization).
- **sealed**: run `recipe.json` directly with zero page probing. On a step
  failure (site drift), `transition --to optimization --evidence <proof>` and
  re-distill.

All transitions are gated by the engine (records completeness, recipe validity,
verdict) and logged in `state.json` `history` with an evidence reference. Any
state still completes the user's task in full — state changes *how*, never
*whether*.

## Engine CLI

```bash
python3 ${SKILL_HOME}/scripts/site-memory.py --action <a> [--site host[:port] | --url URL] \
    [--task slug] [--record '<json>' | --file path] [--to state] [--evidence text] \
    --skill-home "${SKILL_HOME}"
```

| Action | Purpose | Exit 1 means |
|--------|---------|--------------|
| `init` | Create/refresh the site dir (idempotent; derives `<host[:port]>` from `--url`) | — |
| `get-state` | Read state + memory summary; `state: null, memory: "absent"` for unknown/corrupt | — |
| `append-record` | Validate + redaction-check + append one record line | redaction or seq violation |
| `validate-records` | Completeness verdict for a task's trace | — |
| `write-recipe` | Schema-validate and store `recipe.json` | — (schema errors exit 2) |
| `record-validation` | Persist evidence, auto-transition by verdict | state move refused (evidence still stored) |
| `transition` | Gated state move; rollbacks require `--evidence` | illegal transition / gate failed |

Output is always a single JSON envelope; exit codes: 0 ok, 1 refused, 2
usage/schema error.

## Recording rules (exploration phase)

- One line per action, `seq` strictly continuing per task file.
- `kind: "dom"` — `action`, `target`, optional `input`/`result`.
- `kind: "network"` — `method`, `url`, `response_shape` (`status` + top-level
  `json_keys`); `headers`/`body_template` optional.
- Failures stay in the trace: `ok: false` plus an `error` message.
- **Redaction is enforced at write time**: cookie/authorization/token headers
  must be placeholders (`<cookie:aliyun>`); dynamic fields in bodies must carry
  their resolution source (`<resolve:page-var:csrfToken>`,
  `<resolve:prev-request:2.requestId>`). Raw values are rejected.

## Distillation rules (optimization phase)

From `records/<task>.jsonl`, keep the network calls the task's outcome actually
depends on and drop pure-rendering noise (static assets, analytics). Each kept
call becomes a request step with `params_template`, `dynamic_fields` (resolution
source per dynamic value), and `expect` (`status` exact, `json_keys` subset
match). Steps that cannot be request-ified (captcha, complex client-side
computation) stay page-level with a `reason`.

## Ownership

Site memory is runtime data owned by the calling project. In the spec-kit
framework repo it is git-ignored, excluded from the wheel, and skipped by
mirror sync; the installed skill creates it on first use and the caller decides
whether to commit it.

The skill itself never ships or archives `site/` content. Management and
archival are the calling project/agent's responsibility:

- **Commit** `site/` to the caller's own repository when the memory should be
  shared across team members or survive machine changes (records are already
  redacted at write time, so committing is safe).
- **Back up** or **git-ignore** it when the memory is personal or disposable —
  losing it only costs a fresh exploration run; no framework function breaks.
- Whatever the choice, the skill's closing report after any run that wrote
  site memory MUST surface this responsibility so the caller decides
  deliberately instead of by default.
