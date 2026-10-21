---
name: sanitize-materials
description: Framework material hygiene governance for the Spec Kit workspace — scan framework-owned materials (parked ideas, drafts, indexes, mirrors, compatibility links, the docs tree) for stale residue and redundancy, run deterministic correctness checks (dead references, index consistency, symlinks, mirror drift, init migration residue), persist findings in a ledger with pending state, and after explicit user confirmation clean up per the two-level criteria (destructive delete/archive behind a single front-loaded batch confirmation, reversible repairs auto-execute), closing with a three-element execution report. Also the wrap-up step after a cross-generation `specify init` migration. Never evaluates, modifies, or reports user source code, product scripts, or test cases. Internal Spec Kit skill; it depends on the .specify/ structure. Use this when the user mentions ["sanitize", "资料卫生", "过期残留", "清理过期资料", "框架资料清理", "stale residue", "死引用", "dead reference", "镜像漂移", "mirror drift", "台账清理", "索引不一致", "init 迁移收尾", "迁移残留", "speckit.sanitize"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/sanitize-materials/SKILL.md>"
---

# sanitize-materials

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

Canonical extraction source: `.specify/templates/commands/sanitize.md` § Outline, § Stage 1–7
(Preflight / Collect / Judge / Present / Confirm / Apply / Wrap-up), and § Behavior Rules.
Content moved here verbatim in substance; the command keeps entry + lifecycle only.

**Division of labor**: the engine `.specify/scripts/python/sanitize-utils.py` owns the
mechanics; this skill owns when/why/how each engine action is invoked. Finding schema,
merge semantics, and gate criteria defer to engine output and `--help`.

## Input Contract

Parameters are parsed by the command from `$ARGUMENTS` (protocol owned by the command
template); their semantics govern how this skill runs:

- `--roots <csv>` — restrict scanning to a subset of material root kinds. A partial scan
  **never auto-resolves**: pending findings on unscanned roots keep their state (findings
  contract C-14; design authority named under Stores below).
- `check` — check-only mode: stops after Present, never enters Confirm/Apply.
- Trigger: manual, on demand only.
- Glossary: apply the project glossary protocol (`.specify/memory/glossary.md` +
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

**Migration wrap-up lane (init 迁移收尾)**: after a cross-generation `specify init`,
this skill is the sanctioned wrap-up step — the engine's migration-residue checks detect
pre-layering leftovers (legacy skill directories, the old git-workflow state files, the
old tools-registry directory, flat duplicates of nested internal skills) and the
symlink-form check covers `.<agent>/skills` links. Residue dispositions are
`archive` (apply's delete refuses non-empty directories; content-bearing residue follows
archive-not-delete) — each finding's summary names its migration owner (git-utils
bootstrap / `.specify/shared/definitions/tool-definitions.md` § Terminology). User-authored
skills are never candidates.

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

Merge the destructive items (delete / archive) into ONE cleanup plan written to
`.specify/memory/sanitize/cleanup-plan.json` (`confirmed: false`) and present it to the
user **in a single batch**. Deletion and move/archive are the destructive bucket — wait
for user confirmation before any execution (the engine refuses apply with
`confirmed != true` at exit 2, zero execution).

> Gate probe: gate-sanitize-destructive-cleanup — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).

### Stage 6 — Apply

After the user releases the plan: first complete the reversible repairs (repair items'
content modifications — the agent edits the materials directly), set the plan
`confirmed: true`, then run `--action apply`. The engine mechanically executes
delete/archive (archives land under `.specify/archive/` preserving relative layout) and
status updates (pending→resolved).

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

## Behavior Rules (red lines)

- **Scope red line (范围红线)**: never evaluate, modify, or report user source code,
  product scripts, or test cases; finding targets are limited to framework-owned
  materials (a reference-existence check only decides whether the target exists — it is
  not an evaluation of user code).
- **Check zero-modify (检查零修改)**: Collect/Judge never modify any inspected material
  body; writes go only to the ledger and the plan file.
- **Confirmation red line (确认红线)**: no deletion or movement ever happens before the
  user confirms the cleanup plan.
- **Evidence red line (证据红线)**: semantic verdicts' `evidenceRefs` must cite concrete
  commit hashes / paths; insufficient-evidence candidates get no verdict and are never
  entered into the ledger.
- Manual on-demand trigger only; `check` stops at Present and never enters Confirm.
- Ledger accumulation semantics: on repeat runs, new findings merge in; undisposed
  findings keep their state; externally repaired materials not re-detected auto-resolve
  (the engine's merge state machine owns the details).

## Boundaries

- **Two-level criteria governance** (destructive/irreversible → front-loaded
  confirmation; reversible → auto-execute + execution report) is owned by
  `.specify/shared/guidelines/confirmation-gates.md` — this skill applies it at Stage 5/6;
  never copy or restate its rule text here.
- **Delegate items are recommendations only** — this skill never executes another
  command's work; hand off per the Stage 4 triage list.
- **Command-lifecycle surfaces stay in the command template**: `$ARGUMENTS` parsing (User
  Input Protocol), the Glossary entry step, the command's own Feedback / Documentation
  wrap-up sections, and Handoffs.
- Sub-setting via `--roots` trades coverage for speed only; it never silently resolves
  pending findings outside the scanned roots.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:sanitize-materials" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:sanitize-materials" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:sanitize-materials" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
