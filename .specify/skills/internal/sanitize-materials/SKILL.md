---
name: sanitize-materials
description: Framework material hygiene governance for the Spec Kit workspace — scan framework-owned materials (parked ideas, drafts, indexes, mirrors, compatibility links, the docs tree) for stale residue and redundancy, run deterministic correctness checks (dead references, index consistency, symlinks, mirror drift, init migration residue), persist findings in a ledger with pending state, and after explicit user confirmation clean up per the two-level criteria (destructive delete/archive behind a single front-loaded batch confirmation, reversible repairs auto-execute), closing with a three-element execution report. Also the wrap-up step after a cross-generation `specify init` migration, the record-retention lane for consumed exec-quant / feedback / session records (consume → receipt → retire; no receipt means no deletion; 30-day grace), the renumber lane that repairs sequence-number collisions left by concurrent/parallel lines (duplicate-only, spec directories / register IDs / REC-OI prefix-follow / feature-local T-CHK, single front-loaded confirmation, verification by re-scan), and the layout lane that converges a legacy anchor layout (`.specify/memory/` anchors, `.specify/features/<NNN>.md` details) to the current one (anchors at the `.specify/` root, details as `<NNN>-<slug>.md`) through a rename-only migration engine that refuses existing targets and never deletes. Never evaluates, modifies, or reports user source code, product scripts, or test cases. Internal Spec Kit skill; it depends on the .specify/ structure. Use this when the user mentions ["sanitize", "资料卫生", "过期残留", "清理过期资料", "框架资料清理", "stale residue", "死引用", "dead reference", "镜像漂移", "mirror drift", "台账清理", "索引不一致", "init 迁移收尾", "迁移残留", "记录回收", "retention", "consume-then-retire", "序号重排", "编号冲突", "duplicate number", "renumber", "speckit.sanitize"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/sanitize-materials/SKILL.md>"
---

# sanitize-materials

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.


## Goal

Framework material hygiene for the Spec Kit workspace: detect stale residue and
redundancy across framework-owned materials (parked ideas / drafts / indexes / mirrors /
compatibility links / docs tree), run correctness checks (dead references / index
consistency / links / mirror drift), persist findings with pending state, and after user
confirmation clean up per the two-level criteria, update statuses, and issue an execution
report. User code, product scripts, and test cases are out of scope entirely.

Owning command: `/speckit.sanitize`. The command template keeps entry, parameter parsing,
and the command-lifecycle wrap-up surfaces; this skill carries the entire executable
seven-stage flow.

The skill also owns a **record-retention lane** (`--lane retention`): a separate
consume → receipt → retire lifecycle for the per-run record stores. It is not part of the
prose-hygiene findings ledger; it uses its own plan, receipts and retirement ledger under
`.specify/memory/retention/`. A raw record is deleted only when a durable receipt covers
it and the 30-day grace period has elapsed.

A third **renumber lane** (`--lane renumber`) repairs sequence-number collisions: when
concurrent or parallel lines each allocate the "next" number from the same base, a merge
can leave two artifacts owning one number. It is duplicate-only, confirmation-gated, and
records its plans and ledgers under `.specify/memory/renumber/`.

Canonical extraction source: `.specify/templates/commands/sanitize.md` § Outline, § Stage 1–7
(Preflight / Collect / Judge / Present / Confirm / Apply / Wrap-up), and § Behavior Rules.
Content moved here verbatim in substance; the command keeps entry + lifecycle only.

**Division of labor**: the engine `.specify/scripts/python/sanitize-utils.py` owns the
mechanics; this skill owns when/why/how each engine action is invoked. Finding schema,
merge semantics, and gate criteria defer to engine output and `--help`.

## Input Contract

Parameters are parsed by the command from `$ARGUMENTS` (protocol owned by the command
template); their semantics govern how this skill runs:

- `--lane materials|retention|renumber|layout|all` — select the lane. `materials` (default) is the
  existing seven-stage prose-hygiene flow; `retention` runs only the record-retention
  lane (R1–R5 below); `renumber` runs only the sequence-number lane (N1–N5 below);
  `layout` runs only the anchor-layout convergence lane (L1–L4 below); `all` runs
  materials first, then retention, then renumber, then layout.
- `--roots <csv>` — restrict scanning to a subset of material root kinds. A partial scan
  **never auto-resolves**: pending findings on unscanned roots keep their state (findings
  contract C-14; design authority named under Stores below).
- `check` — check-only mode: stops after Present (materials) or after Scan/Present
  (retention, renumber), never enters Confirm/Apply.
- Renumber pass-through flags (N4/N5 only): `--groups <csv>` applies a selected subset,
  `--adopt-ambiguous-refs` accepts the user-stated reading that every ambiguous mention
  refers to the kept definition, `--reason <path>` records a dismissal's adjudication
  pointer.
- Trigger: manual, on demand only.
- Glossary: apply the project glossary protocol (`.specify/glossary.md` +
  `.specify/shared/workflow/glossary.md`) before acting — the entry step stays with the command.

## Engine Invocation Contract

Four actions of `.specify/scripts/python/sanitize-utils.py`; always run with
`--workspace-root .` and `--format json` (the engine always emits a JSON envelope):

```bash
# Stage 2 — deterministic checks + semantic candidate discovery
python3 .specify/scripts/python/sanitize-utils.py --action collect --workspace-root . --format json

# Stage 3 — record agent verdicts into the ledger
python3 .specify/scripts/python/sanitize-utils.py --action record --file <verdicts.json> --workspace-root . --format json

# Stage 4 — re-inspect the ledger digest at any time
python3 .specify/scripts/python/sanitize-utils.py --action status --workspace-root . --format json

# Stage 6 — mechanically execute the confirmed cleanup plan
python3 .specify/scripts/python/sanitize-utils.py --action apply --plan .specify/memory/sanitize/cleanup-plan.json --workspace-root . --format json
```

**Exit-code semantics (non-negotiable)**:

- `0` — success.
- `1` — CLI/usage error or unexpected failure (`ok: false` envelope). Report it; never
  retry blindly.
- `2` — verification/gate refusal with **zero side effects**. In particular: **apply with
  `confirmed != true` is refused with exit 2 and executes nothing.** Never attempt apply
  against an unconfirmed plan, never work around the refusal, never edit the engine to
  relax it — the user's confirmation is the only key that turns this lock. Schema
  violations (record/apply input failing contract validation) refuse the same way.

**Digest-first envelope**: every engine output (collect / record / status) is a count
digest plus target-path lists — never paste raw evidence full text into the conversation
(contract C-18, summary-first discipline).

`**Stores**: findings persist in `.specify/memory/sanitize/findings.json`; the cleanup
plan lives at `.specify/memory/sanitize/cleanup-plan.json`. Physical layout and the
cross-run merge state machine are owned by the sanitize findings contract in the
framework spec set (enforced by the engine) — point at it, never restate it.

**Retention lane engine**: the lane uses a sibling engine, not the four prose actions
above. Always run it with `--workspace-root .` and `--format json`:

```bash
# R2 — read-only inventory (eligible / blocked / too-young; no bodies)
python3 .specify/scripts/python/record-retention.py --action scan --workspace-root . --format json

# R3 — write monthly summaries + per-entry receipts
python3 .specify/scripts/python/record-retention.py --action distill --workspace-root . --promotions <promotions.json> --format json

# R4 — write a retention plan (confirmed: false)
python3 .specify/scripts/python/record-retention.py --action plan --workspace-root . --format json

# R5 — execute the confirmed plan
python3 .specify/scripts/python/record-retention.py --action apply --plan <plan.json> --workspace-root . --format json
```

The retention engine never writes the sanitize findings ledger. Its stores are
`.specify/memory/retention/{summaries,receipts,plans,ledger}/`.

**Renumber lane engine**: a third sibling engine, with the same `--workspace-root .`
and `--format json` discipline:

```bash
# N2 — read-only collision inventory (per family, no bodies)
python3 .specify/scripts/python/renumber-utils.py --action scan --workspace-root . --format json

# N3 — write a duplicate-only plan (confirmed: false) with the reference inventory
python3 .specify/scripts/python/renumber-utils.py --action plan --workspace-root . --format json

# N5 — execute the confirmed plan (optionally a subset: --groups <csv>)
python3 .specify/scripts/python/renumber-utils.py --action apply --plan <plan.json> --workspace-root . --format json

# dismissal of an adjudicated overlap / status digest
python3 .specify/scripts/python/renumber-utils.py --action dismiss --group <id> --reason <path> --workspace-root . --format json
python3 .specify/scripts/python/renumber-utils.py --action status --workspace-root . --format json
```

Exit codes follow the same ladder: `0` success, `1` usage/IO, `2` refusal with zero
side effects (unconfirmed plan, stale mapping, dirty target, branch-name conflict,
non-git workspace). The engine writes only `plans/`, `dismissals/` and `ledger/` under
`.specify/memory/renumber/`; it never writes the materials ledger.

## Workflow (seven stages)

### Stage 1 — Preflight

Probe that `python3` and the engine script
`.specify/scripts/python/sanitize-utils.py` are available; if missing, give an actionable
hint (engine three-state probe convention) and stop. A non-git environment still runs —
semantic staleness detection auto-degrades (the engine emits a note).

### Stage 2 — Collect

Run `--action collect`. Deterministic checks (dead references / index consistency /
symlinks / mirror drift / init migration residue) are judged by the engine directly and
entered into the ledger; the output also carries semantic candidates (time-sensitive
declaration materials + an evidence pack). Present a ledger digest to the user (counts
and the pending target list, summary-first — never paste raw evidence full text).

**Migration wrap-up lane (init 迁移收尾)**: after a cross-generation `specify init`, the
one-shot closeout main entry is `/speckit.migrate`; this lane stays as the periodic
recheck fallback — a successful migrate never requires a sanitize run to reach the
post-migration expected state. The lane's checkers and dispositions are unchanged: the
engine's migration-residue checks detect pre-layering leftovers (legacy skill directories,
the old git-workflow state files, the old tools-registry directory, flat duplicates of
nested internal skills) and the symlink-form check covers `.<agent>/skills` links. Residue
dispositions are `archive` (apply's delete refuses non-empty directories; content-bearing
residue follows archive-not-delete) — each finding's summary names its migration owner
(git-utils bootstrap / `.specify/shared/definitions/tool-definitions.md` § Terminology).
User-authored skills are never candidates.

### Stage 3 — Judge

For each `semanticCandidates` entry from collect, decide stale / redundant. **Judge only
from the evidence the candidate carries** — the `evidencePack` (gitLog summary lines +
`pathExistence` mapping) and the `claims` phrases. Never read the material body in full
(targeted excerpts only under the escalation-ladder exception). Decision rules:

- A declaration ("not landed / pending") contradicted by gitLog evidence (a merge commit
  later than the declared date touching the referenced path) → `stale-residue`;
- The declared content is already fully merged into other live material → `redundant`;
- Evidence insufficient to decide → **insufficient evidence, no verdict** (count it in the
  run summary; never fabricate).

Write the verdicts to a temporary file and record them via the engine (`--action record
--file <verdicts.json>`). Verdicts file schema: `{"findings": [...]}`; finding fields
follow the contract `sanitize-findings.md` (stable ID = sha1(category|target)[:12];
`evidenceRefs` must cite concrete commit hashes / paths).

### Stage 4 — Present

Present the findings report: per finding, category / severity / evidence references /
disposition recommendation (with reversibility marking). **Delegate triage** (delegate
items are not executed here, only recommended):

- docs content editing and structural convergence → `/speckit.docs`;
- symlink / instruction file regeneration → `/speckit.instructions`;
- mirror drift convergence → `sync-mirrors.py --write` / `regen-command-copies.py`;
- SDD process quality → `/speckit.review`.

The ledger digest can be re-inspected at any time (`--action status`). Pending items may
remain in the ledger for the next run to converge.

### Stage 5 — Confirm (destructive front-loaded confirmation)

Classify the plan by reversibility first (owner: `.specify/shared/guidelines/confirmation-gates.md`
§ 可逆动作例外):

- `repair` / `dismiss` / `archive` are reversible: `archive` moves the object under
  `.specify/archive/` with a recovery path; `repair` / `dismiss` change state or content
  in place. In `--auto-reversible` mode execute them without confirmation (write the
  auto plan with `confirmed: true`, run apply, and report per the execution-report rule).
- `delete` is a true deletion (no archive copy; recovery is git history only) and stays
  in the destructive bucket. Merge only the `delete` items into ONE cleanup plan written
  to `.specify/memory/sanitize/cleanup-plan.json` (`confirmed: false`) and present it to
  the user **in a single batch**; wait
  for user confirmation before any execution (the engine refuses apply with
  `confirmed != true` at exit 2, zero execution).

When `--auto-reversible` is not given, keep the original single-batch behaviour for the
whole plan.

#### Archive admission gate (spec retirement)

An item that would retire or archive a spec directory under `.specify/specs/` — or mark
its feature row as an archive pointer — MUST pass the single admission owner before it
enters the cleanup plan:

```bash
python3 .specify/scripts/python/seal-utils.py --action archive-gate --spec-dir .specify/specs/<target> --json
```

Exit `0` → admitted; the item may enter the plan. Exit `1` (refused) or Exit `2`
(input/environment error) → keep the item out of the plan and refuse it by name: surface
the engine's `reason` and verdict, and point the user back to `/speckit.seal`. An engine
that cannot be executed is an error, never a pass — "not queried" never means "allowed".
The criterion is owned by the seal engine (C-030); this skill queries it and never
re-implements it.

> Gate probe: gate-sanitize-destructive-cleanup — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).

### Stage 6 — Apply

`--auto-reversible` path: first complete the reversible repairs (repair items' content
modifications — the agent edits the materials directly), apply the auto plan
(`repair` / `dismiss` / `archive` items) with `confirmed: true`, and report each change
with its archive path. Then, if true `delete` items remain, present the single-batch
delete plan and apply it only after the user releases it.

Without `--auto-reversible`: after the user releases the plan, first complete the
reversible repairs, set the plan `confirmed: true`, then run `--action apply`. The engine
mechanically executes delete/archive (archives land under `.specify/archive/` preserving
relative layout) and status updates (pending→resolved).

After execution, present the three-element execution report: what executed; changed
artifacts (per-item locatable); modification path (git history recovers deleted items /
the archive's new location).

User veto → keep only the pending findings and report truthfully: zero deletion, zero
movement. Mid-execution failure → report the failure point, the reason, and any
intermediate artifacts produced; never silently skip.

### Stage 7 — Wrap-up

Run the standard wrap-up: this skill's Feedback step (below); the docs-sync evaluation
per `.specify/shared/workflow/docs-step.md` stays with the command template. When the destructive
gate fired and the user has made a decision, record the observation facts (non-blocking)
per the gate observation protocol:

```bash
python3 .specify/scripts/python/feedback-utils.py --action record \
  --unit-id "/speckit.sanitize" --unit-type command \
  --lifecycle-point "gate-sanitize-destructive-cleanup" --run-id "gate:gate-sanitize-destructive-cleanup:<UTC ts>" \
  --review "<观察事实,正文 MUST 含字面标记 confirm-gate>" --points-file "<要点文件>"
```

## Retention lane (R1–R5)

Runs when `--lane retention` or `--lane all`; `--lane materials` keeps the seven-stage
flow above unchanged.

### R1 — Preflight

Probe `python3` and `.specify/scripts/python/record-retention.py`; if missing, give an
actionable hint and stop.

### R2 — Scan

Run `--action scan`. Present the per-store digest (`total` / `eligible` / `too_young` /
`blocked` / `with_receipt`) and the blocked reasons (`open`, `unsettled`,
`needs-promotion`, `no-carrier`, `unreadable`, `invalid-record`). Never paste record
bodies. `check` stops here.

### R3 — Distill / promote

Run `--action distill`. It writes one summary per month for exec-quant and
run-determination, and one receipt per covered entry. Feedback entries need
`disposition ∈ {processed, ignored}` plus a carrier (`disposition_reason`,
`introspection_ref`, or a consume-log row); entries without a carrier stay blocked.

Session topic notes need a promotion decision before a receipt can be written: promote
durable content with `memory-record` (knowledge) or `/speckit.history` (history), or mark
the note `ephemeral` with a reason. Write the decisions to a promotions file and rerun
`distill --promotions <file>`. A note without a decision stays `needs-promotion` and is
never deleted. An open feedback entry and a run-determination record without `settled_at`
are reported as backlog, never settled or deleted by this lane.

### R4 — Plan / present

Run `--action plan`. Present the plan: per-store counts, the oldest candidate, the grace
boundary, and the blocked backlog. The plan is written with `confirmed: false`.
Destructive confirmation uses the same single front-loaded batch as Stage 5; the
retention lane adds no second gate.

### R5 — Apply

After the user releases the plan: set `confirmed: true`, then run `--action apply`. The
engine re-checks every receipt, grace, entry state and git cleanliness. It refuses when
target paths are dirty or the workspace is not a git repository; a non-git workspace
needs the explicit `--allow-unversioned` override. It deletes only covered raw records,
writes one retirement ledger per batch, and asserts `remaining + retired = original`.

Report the three-element execution report: removed entries per store, the ledger path,
and the modification path (git history recovers deleted records; receipts, summaries and
ledger remain). A failed item is reported; there is no rollback.

## Renumber lane (N1–N5)

Runs when `--lane renumber` or `--lane all`. Four number families, all detected by the
engine — never by eyeballing file contents:

| Family | Token | Collision | Action |
|---|---|---|---|
| spec-number | `.specify/specs/` directory matching `^\d{3}-` | two directories share one 3-digit prefix | directory rename + references |
| register | register.md **ID column**: `REC-<prefix>-NN`, `OI-<prefix>-NN`, `OI-N`, `T-NNN` | one token defined by two rows | later definition renumbered |
| rec-follow | `REC-<prefix>-NN` / `OI-<prefix>-NN` owned by a renamed spec | dependent on a spec-number group | prefix follows the rename |
| local | `T\d{3}[A-Za-z]?` / `CHK\d{3}` definitions inside one file | duplicate definitions in one file | later definition renumbered |

Range cells (`D1–D9`), non-numeric codes (`goal.*`, `S3b`, `c7`, `G1`, `D-A`) and
letter-suffix spec prefixes (`065a-`) have no machine allocation rule: they are reported,
never renumbered. Single-letter labels (for example T1) fall in the same class.

### N1 — Preflight

Probe `python3` and `.specify/scripts/python/renumber-utils.py`; require a git workspace.
A directory rename outside git loses its history, so there is no unversioned override.

### N2 — Scan

Run `--action scan`. Present the per-family digest — proposed / needs-decision /
dismissed — plus `info` notes. A `needs-decision` group carries ambiguous references: a
duplicated identifier cannot say which definition a mention means, so the lane never
guesses. Present counts and target lists, never material bodies.

### N3 — Plan / present

Run `--action plan`. The plan (`confirmed: false`) carries, per group: group id, the kept
owner with its evidence (features row / first register row / git-added / lexicographic),
old → new token, the full reference inventory (file × hit count), guards (branch names,
ambiguous-reference count) and cross-group dependencies. Next-free allocation counts
archived spec numbers and never reuses a freed number.

### N4 — Confirm

Renumbering moves directories and rewrites references. Under the confirmation-gates
owner it is reversible when the workspace is git-clean and the plan is duplicate-only
with no ambiguous references: in `--auto-reversible` mode run `--action plan
--auto-confirm`; the engine re-checks those preconditions itself, writes
`confirmed: true` only when they all hold, and returns `autoConfirmed: true`; N5 then
applies and the ledger records the batch. When any
precondition fails (dirty targets, ambiguous references, mixed groups) the engine leaves
`confirmed: false` and the plan joins the same single front-loaded batch as the cleanup
plan — no second gate. Drop unwanted groups here; `--groups <csv>` at apply time selects
a subset, and unapplied groups stay pending so later runs converge on them.
`--adopt-ambiguous-refs` exists for one stated reading only: the user confirms that every
ambiguous mention refers to the kept definition.

> Gate probe: gate-sanitize-destructive-cleanup — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).

### N5 — Apply

Set `confirmed: true`, then run `--action apply --plan <file>`. The engine re-checks the
mapping (old still duplicated, new still free), the git-clean state of every target and
the branch guard, executes the renames and rewrites, re-scans, and writes one ledger per
batch. A group still detected afterwards is reported as unresolved; there is no rollback.

Branch renames are **reported** (`git branch -m …`), never executed — rewriting a ref can
be irreversible once pushed. An adjudicated overlap is recorded with `--action dismiss`
and never re-proposed (`--reopen` restores it); the dismissal persists the reason path.

## Layout lane (L1–L4)

Runs when `--lane layout` or `--lane all`. The anchor layout — `features.md`, `constitution.md`,
`glossary.md`, `register.md`, `tools.md` at the `.specify/` root and feature details at
`.specify/features/<NNN>-<slug>.md` — is the convergence target for older projects. The mechanism is owned by
`.specify/scripts/python/anchor-layout-migrate.py` (deterministic; archive-first, and the script never rewrites project
documents).

- **L1 detect** — `python3 .specify/scripts/python/anchor-layout-migrate.py --action check --json`; exit 0
  clean, 1 findings (the plan).
- **L2 present** — the plan's moves, placeholder replacements, merges, dedupes, every refused structural
  target (never overwritten), and the reference paths the project must update. Decision gate: functional ×
  autonomous → fix + disclose (`.specify/shared/guidelines/confirmation-gates.md` § Decision gate).
- **L3 apply** — `--action apply --archive-root <root>`: the five anchors converge to the `.specify/` root;
  a placeholder is replaced by the legacy real content; a real/real pair is merged (registry table union or
  append marker) with both originals archived; `.specify/features/<NNN>.md` becomes
  `.specify/features/<NNN>-<slug>.md`. Every original is copied into the archive before the target changes;
  a move whose target already exists is reported `skipped` and left in place (never forced).
- **L4 verify** — `--action check` clean; report the reference-update list and every merge/archive location
  (the project's own documents carry the old paths; the script reports them, the lane does not rewrite them).

## Behavior Rules (red lines)

- **Scope red line (范围红线)**: never evaluate, modify, or report user source code,
  product scripts, or test cases; finding targets are limited to framework-owned
  materials (a reference-existence check only decides whether the target exists — it is
  not an evaluation of user code).
- **Check zero-modify (检查零修改)**: Collect/Judge never modify any inspected material
  body; writes go only to the ledger and the plan file.
- **Confirmation red line (确认红线)**: no deletion or movement ever happens before the
  user confirms the plan — the cleanup plan for delete/archive, the renumber plan for
  directory renames and reference rewrites.
- **Evidence red line (证据红线)**: semantic verdicts' `evidenceRefs` must cite concrete
  commit hashes / paths; insufficient-evidence candidates get no verdict and are never
  entered into the ledger.
- **Receipt red line (回执红线)**: a raw record is deleted only when a retention receipt
  covers it. No receipt means no deletion; distill first.
- **Open/unsettled red line**: open feedback, unsettled run-determination records,
  unreadable exec-quant records and session notes without a promotion/ephemeral decision
  are never retired; they remain in the blocked backlog.
- **Grace red line**: the default grace period is 30 days after the receipt; the plan and
  apply re-check it. Deleting a younger record is a defect, not a shortcut.
- **Git-clean red line**: apply refuses dirty target paths; a non-git workspace needs the
  explicit `--allow-unversioned` override. Do not bypass this by staging or reverting
  unrelated work.
- **Lane separation**: the retention lane never writes the sanitize findings ledger or
  merges its candidates into it; receipts/summaries/ledger live under
  `.specify/memory/retention/`. The renumber lane writes only its own store under
  `.specify/memory/renumber/`.
- **Duplicate-only red line (只消解重复)**: the renumber lane repairs collisions only. It
  never reuses a freed number, never compacts gaps, and never re-labels an identifier
  that collides with nothing.
- **Git-ref red line (git 引用只报告)**: branch renames are printed as commands, never
  executed; apply refuses when a branch name would keep resolving to the old prefix.
- **Dated-record red line (历史记录不改写)**: `.specify/history/`, archives,
  `test-evidence/` logs and date-named files keep the old identity by design; their hits
  are reported as `excluded_hits`, which are not a failure. A recorded pre-rename name
  that is cited later stays a dated record, exactly as a merge-time renumber does.
- **Sanctioned writer (唯一例外)**: register.md and features.md stay hand-maintained
  single-owner files; this lane is the one sanctioned exception, and only for repairing a
  duplicate — it never registers a new number and never edits a row's identity.
- Manual on-demand trigger only; `check` stops at Present and never enters Confirm.
- Ledger accumulation semantics: on repeat runs, new findings merge in; undisposed
  findings keep their state; externally repaired materials not re-detected auto-resolve
  (the engine's merge state machine owns the details).

## Boundaries

- **Two-level criteria governance** (destructive/irreversible → front-loaded
  confirmation; reversible → auto-execute + execution report) is owned by
  `.specify/shared/guidelines/confirmation-gates.md` — this skill applies it at Stage 5/6
  and in the retention lane's R4/R5; never copy or restate its rule text here.
- **Retention store ownership**: `.specify/memory/retention/` is owned by
  `record-retention.py`; summaries, receipts, plans and ledgers are append-only durable
  evidence and are never deleted by the retention lane itself.
- **Renumber store ownership**: `.specify/memory/renumber/` is owned by
  `renumber-utils.py`; plans, dismissals and ledgers are one file per entry (timestamped)
  so concurrent writers never share a path, and there is no mutable index to merge.
- **Number-family owners**: spec numbering rules and pitfalls belong to
  `.specify/skills/internal/create-requirements/SKILL.md` § 2; the feature index's
  single-cell duty belongs to `.specify/shared/workflow/feature-integration.md`; the ID
  register's registration duty belongs to `.specify/instructions.md` § ID Register. This
  lane points at them and never restates their tables.
- **Delegate items are recommendations only** — this skill never executes another
  command's work; hand off per the Stage 4 triage list.
- **Command-lifecycle surfaces stay in the command template**: `$ARGUMENTS` parsing (User
  Input Protocol), the Glossary entry step, the command's own Feedback / Documentation
  wrap-up sections, and Handoffs.
- Sub-setting via `--roots` trades coverage for speed only; it never silently resolves
  pending findings outside the scanned roots.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:sanitize-materials" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:sanitize-materials" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:sanitize-materials" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
