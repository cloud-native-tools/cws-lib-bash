---
name: memory-recall
description: Retrieve relevant prior memory before or during a Spec Kit task, using a lightweight local file index (no vectors). Searches short-term working notes in .specify/memory/session/ and long-term knowledge in .specify/memory/knowledge/ by keyword, tag, source, feature, and date, then injects the most relevant entries into context. Pairs with memory-record. Triggers include "回忆", "查找记忆", "recall memory", "what do we know about", "prior decisions".
skill_id: "<SKILL:.specify/skills/memory-recall/SKILL.md>"
---

# memory-recall

## Overview
Search the project memory store and surface the most relevant entries so the current Spec Kit task can build on past decisions, preferences, and working state. This is the *retrieval* half of the memory system; `memory-record` is the capture half. Retrieval uses a plain local JSON index and keyword/tag scoring — there is no vector store.

## When to use
- At the start of a `/speckit.*` command or skill run, to load relevant context before acting.
- Mid-task, when you need prior decisions or conventions on a specific subject.
- When the user asks what is already known/decided about a topic.

## Workflow
1. Derive a compact query from the task: key terms, the feature key (if any), and useful tags.
2. Choose a scope:
   - `session` — recent working context only.
   - `knowledge` — durable, cross-session knowledge only.
   - `all` — both (default when unsure).
3. Run the shared engine from the project root:
   ```bash
   python3 "${SKILL_WORKDIR}/.specify/scripts/python/memory-utils.py" \
     --action recall \
     --scope <session|knowledge|all> \
     --query "<key terms>" \
     --tags "<optional,tags>" \
     --feature "<optional-feature-key>" \
     --since "<optional YYYY-MM-DD>" \
     --limit 5
   ```
   Use `--format json` when you need to parse results programmatically; the default text output is human-readable.
4. Read the returned entry paths for full content when a summary is not enough, then fold the relevant points into your working context.
5. If nothing relevant is found, proceed without memory and rely on the current spec/plan.

## Related actions
- `--action list --scope <session|knowledge|all> --limit N` — browse the most recent entries without a query.
- `--action prune --scope session --max-entries N` / `--max-age-days D` — keep short-term memory bounded.
- `--action reindex --scope all` — rebuild `index.json` from files if an index is lost or stale.

## Path Conventions
- Engine (shared project script): `${SKILL_WORKDIR}/.specify/scripts/python/memory-utils.py`.
- Memory store (read from): `${SKILL_WORKDIR}/.specify/memory/session/` and `${SKILL_WORKDIR}/.specify/memory/knowledge/`.

## Resource ID
- Canonical ID: `<SKILL:.specify/skills/memory-recall/SKILL.md>`
- Canonical Path: `.specify/skills/memory-recall/SKILL.md`

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:memory-recall" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
