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

At the end of a substantial run of this skill, perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this run reached a meaningful wrap-up. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against this skill's declared purpose and produce a short review plus ≥1 concrete, skill-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this skill's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id`; if a parent flow already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "skill:memory-record" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
