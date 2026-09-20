---
name: memory-record
description: Persist a durable, structured record of a Spec Kit conversation into project memory (memory-as-files). Use when a /speckit.* command or skill produces a decision, user preference, review outcome, or working-state note worth remembering. Records short-term working context to .specify/memory/session/ and long-term distilled knowledge to .specify/memory/knowledge/. Only records conversations driven by a Spec Kit command or skill. Triggers include "记住", "记录记忆", "save to memory", "remember this", "record decision".
skill_id: "<SKILL:.specify/skills/memory-record/SKILL.md>"
---

# memory-record

## Overview
Write one memory entry as a Markdown file (plus a local JSON index update) into the project memory directory, so future Spec Kit sessions can recall it. This skill is the *capture* half of the memory system; `memory-recall` is the retrieval half.

Spec Kit is scaffolding, not a runtime — it cannot intercept raw model turns. This skill is how the agent, while executing a `/speckit.*` command or another skill, deliberately persists what matters from that interaction.

## When to use
Invoke during or right after a `/speckit.*` command or skill run when the interaction produced something worth keeping:
- A decision and its rationale (e.g. "chose JWT over sessions").
- A durable user preference or project convention not yet in the constitution.
- Review feedback that should shape future work.
- The in-flight working state of a long run (what was just done / the next step).

## What NOT to store
Do not store anything derivable from project state: code, architecture, file layouts, git history, or content already captured in `constitution.md`, `features.md`, `features/<ID>.md`, or `tools.md`. Memory is only for **non-derivable** context. Keep entries short and high-signal.

## Choosing scope
- `session` — short-term / working memory for the current effort (progress, in-flight state, ephemeral context). Append-only; safe to prune later.
- `knowledge` — long-term / distilled memory that stays useful across sessions (stable preferences, conventions, lasting decisions). Upserted by title slug, so re-recording the same subject updates it.

## Workflow
1. Confirm the trigger is a Spec Kit command or skill. Determine the correct `--source`:
   - `/speckit.<command>` for command-driven work (e.g. `/speckit.plan`).
   - `skill:<skill-name>` for skill-driven work (e.g. `skill:study-project`).
   The engine rejects any other source, so this is a hard boundary — never fabricate a source to force a write.
2. Distill the takeaway into a concise title and a few lines of content.
3. Pick the scope (`session` vs `knowledge`) using the guidance above.
4. Run the shared engine from the project root:
   ```bash
   python3 "${SKILL_WORKDIR}/.specify/scripts/python/memory-utils.py" \
     --action record \
     --scope <session|knowledge> \
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
- Canonical ID: `<SKILL:.specify/skills/memory-record/SKILL.md>`
- Canonical Path: `.specify/skills/memory-record/SKILL.md`

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:memory-record" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
