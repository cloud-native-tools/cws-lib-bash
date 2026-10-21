---
name: manage-history
description: Distill the current AI tool's past conversation history for this project into a durable, theme-aggregated knowledge base under `.specify/history/` — decisions with rationale, reusable lessons, open TODOs, key interaction flows, and user↔model disagreement points; incremental by default (a manifest tracks already-distilled sessions), full reprocess on request. Orchestrates the collect-history engines through tool identification, clean-session extraction, five-dimension distillation, theme aggregation, and manifest update, merging new findings into existing theme files without overwriting or duplicating. Use this when the user mentions ["session history", "conversation history", "distill history", "历史蒸馏", "会话历史", "历史知识库", "增量蒸馏", "history knowledge base", "past conversations", "经验沉淀", "history manifest", "distill sessions"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/manage-history/SKILL.md>"
---

# manage-history

## Goal

Distill the **current AI tool's** past conversations **for the current project** into a durable, theme-aggregated knowledge base at `.specify/history/`. The output is mined long-term value — decisions, reusable lessons, open TODOs, key interaction flows, and points of user↔model disagreement — never a verbatim transcript store. Runs are **incremental**: a manifest tracks which sessions were already distilled, so re-runs only process new ones and merge into the existing documents.

This skill owns the executable core of `/speckit.history`: Steps 1–6 (tool identification, clean extraction, five-dimension distillation, theme aggregation, manifest handling) and the Safety Rules, all inline. The per-tool heavy lifting is externalized to the engines — `.specify/scripts/bash/collect-history.sh` (locate / extract / manifest-update) and `.specify/scripts/python/history-utils.py` (pluggable `STORE_RESOLVERS` per tool) — and this skill drives them as invocation instructions. The command template keeps entry, user-input handling, and lifecycle only.

Canonical extraction source: `.specify/templates/commands/history.md` § Steps 1–6 and § Safety Rules. Content moved here verbatim in substance. Long-form reference (owner of the conceptual model): `docs/reference/commands/history.md`.

## Input Contract

- **Precondition**: the current tool has some conversation history for this project — this skill distills the past; it does not create it. No history → Step 1's gate reports and stops.
- **`--full`** — reprocess **all** sessions and regenerate the knowledge base (ignore the incremental manifest). Absent → incremental (manifest-tracked).
- **Theme focus / date range / topic hint** — optional narrowing of which sessions to emphasize during distillation.
- **Scope = ALL history**: the analytical horizon is always the tool's *entire* past conversation record for this project (every session in the store); incrementality is an efficiency device, not a scope cut.
- **Unit of work = concepts/themes**: one or many themes, each aggregating evidence across sessions. A concept may draw on 20 sessions; a session may feed 5 concepts.
- **Engines are invoked, never reimplemented**: `.specify/scripts/bash/collect-history.sh` for locate / extract / manifest-update; `.specify/scripts/python/history-utils.py` owns per-tool session-store resolution.

## Workflow

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

## Safety Rules

1. **Read-only on history**: never modify or delete files under the tool's session store; only read them.
2. **No verbatim dumps**: `.specify/history/` holds distilled value, not raw transcripts.
3. **No silent truncation**: if you cap coverage (e.g. skip trivial sessions or batch-limit), say so in the report.
4. **Unsupported tools stop cleanly**: never guess an unadapted tool's storage format and parse it blindly.

## Boundaries

- **Single-session data operations** (export, naming, archiving one session as a data object) are `/speckit.session`'s job — that command manages session **data** and does not parse content into concepts. This skill always operates on the full corpus and parses content into themes.
- **Memory persistence** (writing distilled knowledge into long-term project memory) is not this skill — the invoking command offers it as a follow-up; this skill writes only `.specify/history/`.
- **Codifying conventions** surfaced by the distillation (constitution / instructions updates) is separate commands' work; this skill only records them in the history documents.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:manage-history" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:manage-history" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:manage-history" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
