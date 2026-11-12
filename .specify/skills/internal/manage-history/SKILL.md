---
name: manage-history
description: Distill the current AI tool's past conversation history for this project into a durable, theme-aggregated knowledge base under `.specify/history/` — decisions with rationale, reusable lessons, open TODOs, key interaction flows, and user↔model disagreement points; incremental by default (a manifest tracks already-distilled sessions), full reprocess on request. Orchestrates the collect-history engines through tool identification, clean-session extraction, five-dimension distillation, theme aggregation, and manifest update, merging new findings into existing theme files without overwriting or duplicating. Use this when the user mentions ["session history", "conversation history", "distill history", "历史蒸馏", "会话历史", "历史知识库", "增量蒸馏", "history knowledge base", "past conversations", "经验沉淀", "history manifest", "distill sessions"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/manage-history/SKILL.md>"
---

# manage-history

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.


## Goal

Distill the **current AI tool's** past conversations **for the current project** into a durable, theme-aggregated knowledge base at `.specify/history/`. The output is mined long-term value — decisions, reusable lessons, open TODOs, key interaction flows, and points of user↔model disagreement — never a verbatim transcript store. Runs are **incremental**: a manifest tracks which sessions were already distilled, so re-runs only process new ones and merge into the existing documents.

This skill owns the executable core of `/speckit.history`: Steps 1–6 (tool identification, clean extraction, five-dimension distillation, theme aggregation, manifest handling) and the Safety Rules, all inline. The per-tool heavy lifting is externalized to the engines — `.specify/scripts/bash/collect-history.sh` (locate / extract / manifest-update) and `.specify/scripts/python/history-utils.py` (pluggable `STORE_RESOLVERS` per tool) — and this skill drives them as invocation instructions. The command template keeps entry, user-input handling, and lifecycle only.

Canonical extraction source: `.specify/templates/commands/history.md` § Steps 1–6 and § Safety Rules. Content moved here verbatim in substance. Long-form reference (owner of the conceptual model): `docs/reference/commands/history.md`.

**The manifest's schema is a machine fact, not this skill's.** Its file name, its three top-level keys (one of which is the per-session map the incremental read addresses) and the per-session entry key are owned by `.specify/shared/declarations/facts/history-manifest-schema.yaml#/statement`, and `.specify/scripts/python/history-utils.py` reads them from there; this skill describes the manifest's *role* (which sessions were already distilled) and reaches its shape by that pointer instead of restating it. The five distillation categories this skill names are **not** a machine fact (no engine reads them) and stay here as prose — their non-migration is recorded in `contracts/migration-batches.contract.md` § Facts outside the roster, not as an exclusion row, because this unit is in scope for the manifest schema.

### 四段形态 (the four-stage form)

`/speckit.history` runs in four stages, in this order and under these names:
**回顾 (review) → 设计（方案） (design) → 用户确认 (user confirm) → 执行 (execute)**. This line is the seam's one
statement of the ladder; `.specify/templates/commands/history.md` enumerates it once as a delegation list, and no other face
restates it.

The four stages are **three insertions plus the existing list**, never a renumbering: **Step 0** (回顾) sits before
Step 1, **Step A** (设计) and **Step B** (用户确认) sit between Step 0 and Step 1, and the execute segment takes
**Step 6's position** — the skill's existing write-and-close chain (Step 4's theme-aggregation writes, Step 5's
manifest update, Step 6's report), with no new number and Step 6's name unmoved. Steps 1–6 keep their numbering and
their text, so the sentence "Steps 1–6" above stays true; a reader meeting "Step A" needs to know only that it is an
insertion before Step 1.

The seam order and the step numbers MUST be read together: Step 0 → Step A → Step B → execute. In the four-stage
form the distillation pipeline (Steps 1–6) runs **inside** the execute segment, because Steps 4–5 write; nothing below
Step B may write, and the pipeline may not run above Step B. That is what the two snapshots bracketing Steps 0 and A
measure.

## Input Contract

- **Precondition**: the current tool has some conversation history for this project — this skill distills the past; it does not create it. No history → Step 1's gate reports and stops.
- **`--full`** — reprocess **all** sessions and regenerate the knowledge base (ignore the incremental manifest). Absent → incremental (manifest-tracked).
- **Theme focus / date range / topic hint** — optional narrowing of which sessions to emphasize during distillation.
- **Scope = ALL history**: the analytical horizon is always the tool's *entire* past conversation record for this project (every session in the store); incrementality is an efficiency device, not a scope cut.
- **Unit of work = concepts/themes**: one or many themes, each aggregating evidence across sessions. A concept may draw on 20 sessions; a session may feed 5 concepts.
- **Engines are invoked, never reimplemented**: `.specify/scripts/bash/collect-history.sh` for locate / extract / manifest-update; `.specify/scripts/python/history-utils.py` owns per-tool session-store resolution.
- **Confirmation granularity** — `group` / `item` / `none-of`; absent input resolves to `group`. The closed domain and
  its semantics are stated at Step B below, not here.

## Workflow

### Step 0: 回顾 (review) — zero write

1. **Snapshot #1, before anything is read.** This snapshot, not any claim this skill makes, is what "review wrote
   nothing" means:
   ```bash
   mkdir -p .specify/.tmp
   { git status --porcelain=v1
     python3 .specify/scripts/python/non-disposable-check.py --roots | cut -d' ' -f1 \
       | while read -r root; do [ -d "$root" ] && find "$root" -type f -print; done \
       | LC_ALL=C sort | while IFS= read -r file; do sha256sum "$file"; done
   } > .specify/.tmp/history-seam-snapshot-before.txt
   ```
   (On a host without `sha256sum`, `shasum -a 256` is the same reading; both snapshots must use one command.)
   The snapshot is the pair (**`git status --porcelain=v1` full text**, **content hashes over the declared root
   set**). Never type the ten directory names here: the set and its count are owned by
   `.specify/shared/declarations/facts/non-disposable-review-surface.yaml#/statement`, read through
   `.specify/scripts/python/declaration_reader.py` (a missing or malformed declaration is exit `2` naming the path — never
   "zero candidates, all green").
2. **Read the review surface** — the declared roots **of the HEAD working tree**; git history (commit / blame /
   old-version diff) is not a review input:
   ```bash
   python3 .specify/scripts/python/non-disposable-check.py --json > .specify/.tmp/history-review.json
   ```
   Exit `0` clean, `1` findings, `2` input error. The semantic face is sharded (`--scope`) and may be delegated to
   parallel subagents; the same tree at any concurrency yields the same entry set by name, so concurrency moves the
   wall clock only.
3. **Report coverage first, then entries** — one row per declared root in declared order (present / count / excluded
   reason), then per entry: `path:line`, class, `detection`, evidence refs, severity, state, proposed disposition.
4. **Nothing is written**: no tracked path, no `.specify/history/` write, no `.specify/memory/sanitize/findings.json`.
   `.specify/.tmp/` is this stage's only scratch and it is git-ignored by `.specify/.gitignore` (`.tmp/`).

### Step A: 设计（方案） (design) — zero write

1. **Propose per entry**: one disposition — a member of the four-value set owned by
   `.specify/shared/definitions/non-disposable-definitions.md` § Disposition Set, cited and never re-listed here — plus the
   paths it would touch, its reversibility, and the **group** it belongs to (a group is one detection class). End
   with exactly one confirmation request; execute nothing.
2. **Write nothing**, with one sanctioned exception: if carrying the plan to Step B needs a file, it lands under
   `.specify/.tmp/` and the execute segment deletes it. No tracked path is written before the confirmation
   (FR-031 / FR-042).
3. **Snapshot #2, after the design** — same command as Step 0, to
   `.specify/.tmp/history-seam-snapshot-after-design.txt`, then compare:
   ```bash
   diff .specify/.tmp/history-seam-snapshot-before.txt \
        .specify/.tmp/history-seam-snapshot-after-design.txt   # MUST print nothing
   ```
   The two snapshots MUST be byte-identical. Any difference is the seam's own violation — stop before Step B and
   report it; never continue and call it a detail.

### Step B: 用户确认 (user confirm)

The confirmation granularity is a **closed three-value** domain:

| value | one confirmation covers |
|---|---|
| `group` (**default**) | every entry of that detection class |
| `item` | one entry |
| `none-of` | nothing implicitly — everything stays proposed and only the named entries are confirmed |

- **Absent input resolves to `group`** — the default is a value, not a reason to ask again.
- **No fourth value**, and no "one confirmation = execute everything": full execution is only ever the sum of
  per-group or per-item confirmations.
- **After a partial confirmation** every unconfirmed entry appears in the report as `unconfirmed`
  (`data-model.md` § Entry State Machine) — not "no design yet", not a disposition value. It MUST NOT be silently
  dropped, MUST NOT be retried automatically next round, and MUST NOT count toward this round's closure.
- Record the confirmed set and the granularity that produced it in the plan/evidence, so the execute segment has
  exactly one reading of what was confirmed.

### Step 1: Identify Tool & Project

1. **Identify the executing agent** following `.specify/shared/workflow/agent-configuration.md` → "Step 1: Identify Executing Agent" (Claude Code / Copilot / Qoder / opencode / Codex / Hermes / …).
2. Run `.specify/scripts/bash/collect-history.sh --json` from repo root. It auto-detects the tool and prints JSON:
   ```json
   {
     "action": "locate", "tool": "<key>", "supported": <bool>,
     "project_path": "<abs path>", "project_name": "<name>",
     "session_store": "<path or null>", "session_count": <int>,
     "output_dir": "<...>/.specify/history",
     "manifest_path": "<...>/.specify/history/.manifest.json",
     "supported_tools": ["claude", "qoder"], "note": "<explanation>"
   }
   ```
   - If the detected `tool` is wrong, re-run with `--tool <key>` (append to the script call).
3. **Gate on support**:
   - If `supported` is `false`: report the detected tool, the `note`/`hint` (where its history would live), and that extraction for this tool is **not yet implemented** (only `supported_tools` are). Explain that support is pluggable via `STORE_RESOLVERS` in `.specify/scripts/python/history-utils.py`, then **stop**.
   - If `session_count` is `0`: report "No history found for this tool/project." and stop.

### Step 2: Extract Clean Sessions

1. Run `.specify/scripts/bash/collect-history.sh --action extract --tool <tool> --json` (add `--full` if the user requested it). This writes a de-noised transcript per session to `.specify/history/.work/<sid>.txt` and returns an inventory:
   ```json
   {
     "total_sessions": <int>, "pending_sessions": <int>, "total_chars": <int>,
     "sessions": [{"sid": "...", "short": "...", "title": "...",
       "first_user": "...", "chars": <int>, "n_user": <int>, "n_asst": <int>,
       "mtime": "...", "processed": <bool>, "work_file": "<path or null>"}]
   }
   ```
2. **Select sessions to distill**: those with `work_file != null` (i.e. `processed=false`, unless `--full`). **Skip trivial/meta sessions**: very small `chars` (heuristic < ~1500) or clearly meta ("how do I get session history", empty-content). Note skipped ones in the final report — never silently drop.
3. If nothing to process (all already in the manifest and no `--full`): report "History is already up to date (N sessions)." and stop.

### Step 3: Distill Each Session (delegate in parallel)

For each selected session, read its `work_file` and extract **only long-term value** along these **five dimensions** (no verbatim retelling):

1. **关键决策与理由 (Decisions & rationale)** — what was decided and why; **explicitly include abandoned alternatives** and why they were dropped.
2. **可复用经验 / 踩坑 (Reusable lessons / pitfalls)** — problems, fixes, general techniques, anti-patterns worth avoiding next time.
3. **未完成 / 待办 (Unfinished / TODO)** — deferred ideas, open questions, follow-ups.
4. **关键交互流程 (Key interaction flow)** — notable multi-step workflows or conventions (else "无").
5. **用户 ↔ 模型的冲突/分歧点 (User↔model conflicts)** — where the user overrode/corrected the model. Format: `用户主张 X;模型原本 Y;最终 Z`.

**Delegation**: for large sessions, spawn parallel subagents (one per session) that each read one `work_file` and return the five-dimension extraction as compact Markdown. Batch to respect the concurrency cap. Small sessions may be read directly. Keep identifiers (file paths, command names, commit hashes) accurate.

### Step 4: Theme Aggregation → `.specify/history/`

Group the distilled sessions into **themes** (derive them from the actual content; do not force a fixed taxonomy). Generate or **update** these files (create `.specify/history/` if missing; if a root-owned dir blocks writes, recreate it as the current user):

- `README.md` — index: theme table (theme · covered sessions · date span), reading order, and a few cross-session "meta-conclusions".
- `00-cross-cutting-lessons.md` — lessons/pitfalls that recur across many sessions.
- `NN-<theme-slug>.md` — one file per theme, organized by the five dimensions above; cross-link related docs with `[[name]]`.

**Merge strategy (incremental)**: if a target file exists, **integrate** new findings into the right sections without overwriting valid prior content or duplicating entries. Add new theme files as needed. Only regenerate wholesale under `--full`.

### Step 5: Update Manifest

Record the sessions distilled this run so future runs skip them:
```bash
.specify/scripts/bash/collect-history.sh --action manifest-update --tool <tool> \
  --sids "<space/comma-separated full sids>" --json
```
(Use the full `sid` values from the inventory, not the `short` form.)

### Step 6: Report

Summarize: tool & project detected, sessions distilled this run vs skipped (with reasons), themes created/updated, and the output location. Remind the user that `.specify/history/.work/` is disposable scratch (git-ignored) and the `.md` docs + `.manifest.json` are the durable output.

### 执行段 — 执行 (execute), at Step 6's position

The execute segment is **the existing Step 4 → Step 5 → Step 6 chain plus the repair writes Step B confirmed**. It
starts only after Step B and only on the **confirmed set**; Steps 1–6 keep their numbers and names.

1. **Pre-flight readings (Capture Rule).** Before the first byte of any write, take the four readings the owner
   page's § Capture Rule names — command and raw output verbatim — and the same four after; both sets land in the
   evidence file's `readings` segment. A "now fixed" claim with no before-reading is a self-report, not evidence.
2. **Group by group, boundary by boundary.** Write one group at a time, in group order, never splitting an entry
   across a boundary, so an interruption stops between groups and never mid-entry. After each group, record one
   evidence file — that is the recovery point.
3. **One evidence file per group, four segments.** The location is `.specify/specs/<spec-dir>/test-evidence/` (this
   feature: `.specify/specs/092-non-disposable/test-evidence/`), one file per run, and the shape is owned by
   `data-model.md` § E-7 — `readings` (before/after detection readings of the same scope), `paths` (changed-path
   list, every rename pair included), `corpus` (the corpus entry ids this group disposes; empty when none),
   `dispositions` (one record per entry, owner page § Disposal Pathways). A file missing one of the four segments
   does not make the repair valid. Evidence MUST NOT go into `.specify/memory/sanitize/findings.json` or into
   `.specify/history/`, and no second evidence store may be created (FR-035).
4. **Disposal channels.** `correct` / `supersede` are reversible with one `git checkout -- <path>`. `archive` is a
   **move** (`git mv` semantics): the disposition record carries the `source → archive` mapping, the superseded text
   stays at the archive path, and `git status --porcelain` shows a rename pair — never a deletion. No disposition
   deletes a file.
5. **No bypass.** Every path the run touches MUST be named in a **confirmed** design row; a path outside them is a
   violation of this segment. A change to an existing spec body, owner document or guard is a confirmed design item
   and carries its before/after readings.
6. **Then the confirmed distillation work.** The pipeline of Steps 1–6 runs here for the sessions it was confirmed to
   process, and it stays this skill's existing capability: `.specify/history/` remains the sole distill storage (this
   feature only reads it) and the incremental manifest is unchanged (FR-043 / FR-044 / FR-059).
7. **Clean up and close.** Delete the `.specify/.tmp/` plan and snapshot scratch, then report the confirmed set, the
   `unconfirmed` count (stated as **not closed**), the per-group evidence paths, the disposition rows, and the
   rename pairs.

## Safety Rules

1. **Read-only on history**: never modify or delete files under the tool's session store; only read them.
2. **No verbatim dumps**: `.specify/history/` holds distilled value, not raw transcripts.
3. **No silent truncation**: if you cap coverage (e.g. skip trivial sessions or batch-limit), say so in the report.
4. **Unsupported tools stop cleanly**: never guess an unadapted tool's storage format and parse it blindly.
5. **The seam writes only after confirmation**: Steps 0 and A leave the working tree byte-identical, the execute segment writes only the confirmed set at group boundaries, and no disposition deletes a file.

## Boundaries

- **Single-session data operations** (export, naming, archiving one session as a data object) are `/speckit.session`'s job — that command manages session **data** and does not parse content into concepts. This skill always operates on the full corpus and parses content into themes.
- **Memory persistence** (writing distilled knowledge into long-term project memory) is not this skill — the invoking command offers it as a follow-up; this skill writes only `.specify/history/` for the distillation face and the confirmed execute-segment paths (repairs plus the spec's `test-evidence/`).
- **Codifying conventions** surfaced by the distillation (constitution / instructions updates) is separate commands' work; this skill only records them in the history documents.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:manage-history" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:manage-history" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:manage-history" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
