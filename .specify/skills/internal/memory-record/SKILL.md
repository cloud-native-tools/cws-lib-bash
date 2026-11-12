---
name: memory-record
description: Persist a durable, structured record of a Spec Kit conversation into project memory (memory-as-files). Use when a /speckit.* command or skill produces a decision, user preference, review outcome, or working-state note worth remembering. Records short-term working context to .specify/memory/session/ and long-term distilled knowledge to .specify/memory/knowledge/. Only records conversations driven by a Spec Kit command or skill. Triggers include "记住", "记录记忆", "save to memory", "remember this", "record decision".
skill_id: "<SKILL:.specify/skills/internal/memory-record/SKILL.md>"
classification: internal
---

# memory-record

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.


## Overview
Write one memory entry as a Markdown file (plus a local JSON index update) into the project memory directory, so future Spec Kit sessions can recall it. This skill is the *capture* half of the memory system; `memory-recall` is the retrieval half.

Spec Kit is scaffolding, not a runtime — it cannot intercept raw model turns. This skill is how the agent, while executing a `/speckit.*` command or another skill, deliberately persists what matters from that interaction.

## When to use
Invoke during or right after a `/speckit.*` command or skill run when the interaction produced something worth keeping:
- A decision and its rationale (e.g. "chose JWT over sessions").
- A durable user preference or project convention not yet in the constitution.
- Review feedback that should shape future work.
- The in-flight working state of a long run (what was just done / the next step).

A non-derivable takeaway from the run is a recording obligation, not an optional nicety — see `.specify/shared/guidelines/knowledge-promotion.md` § 1.

## What NOT to store
Do not store anything derivable from project state: code, architecture, file layouts, git history, or content already captured in `constitution.md`, `features.md`, `features/<ID>.md`, or `tools.md`. Memory is only for **non-derivable** context. Keep entries short and high-signal.

The recording obligation and the repeated-emphasis promotion trigger are owned by `.specify/shared/guidelines/knowledge-promotion.md`; this skill owns the write mechanics.

## Choosing scope
The scope domain is a machine fact, not this skill's: the closed set `--scope` accepts (and the order
`--scope all` expands in) is owned by `.specify/shared/declarations/facts/memory-types.yaml#/statement` and read
by `.specify/scripts/python/memory-utils.py`. What follows is the **judgement** for picking one member — which
scope a given takeaway belongs in — and it is the only thing owned here.

- `session` — short-term / working memory for the current effort (progress, in-flight state, ephemeral context). Append-only; safe to prune later.
- `knowledge` — long-term / distilled memory that stays useful across sessions (stable preferences, conventions, lasting decisions). Upserted by title slug, so re-recording the same subject updates it.

For a user emphasis, use `session` with tags `user-emphasis,key:<ascii-slug>` so the second occurrence can be counted; the promotion trigger is owned by `.specify/shared/guidelines/knowledge-promotion.md` § 2.

## Workflow
1. Confirm the trigger is a Spec Kit command or skill. Determine the correct `--source`:
   - `/speckit.<command>` for command-driven work (e.g. `/speckit.plan`).
   - `skill:<skill-name>` for skill-driven work (e.g. `skill:study-code`).
   The engine rejects any other source, so this is a hard boundary — never fabricate a source to force a write.
2. Distill the takeaway into a concise title and a few lines of content.
3. Pick the scope — one member of the set `.specify/shared/declarations/facts/memory-types.yaml#/statement`
   owns — using the judgement above.
   - For a user emphasis, first check prior occurrences with `memory-utils.py --action recall --scope all --tags "key:<ascii-slug>" --format json`. If this is the second occurrence, follow `.specify/shared/guidelines/knowledge-promotion.md` § 2 — do not stop after recording.
4. Run the shared engine from the project root:
   ```bash
   python3 "${SKILL_WORKDIR}/.specify/scripts/python/memory-utils.py" \
     --action record \
     --scope <the chosen scope> \
     --source "</speckit.command|skill:name>" \
     --title "<concise title>" \
     --tags "<comma,separated,tags>" \
     --feature "<feature-key-if-any>" \
     --content "<the distilled note>"
   ```
   For multi-line content, prefer `--content-file <path>` or pipe via stdin.
5. Report the returned entry path to the user.

## Path Conventions
- Engine (shared project script): `${SKILL_WORKDIR}/.specify/scripts/python/memory-utils.py`.
- Memory store (runtime output): `${SKILL_WORKDIR}/.specify/memory/session/` and `${SKILL_WORKDIR}/.specify/memory/knowledge/`.
- The engine creates these directories on first write and maintains an `index.json` per scope.

## Resource ID
- Canonical ID: `<SKILL:.specify/skills/internal/memory-record/SKILL.md>`
- Canonical Path: `.specify/skills/internal/memory-record/SKILL.md`

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:memory-record" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:memory-record" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:memory-record" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
