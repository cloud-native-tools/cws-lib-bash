# Glossary Protocol (Correction · Enrichment · Conflict)

**Feature 031 — Glossary Mechanism.** This file is the single source of truth for how
`/speckit.*` commands use the project glossary at `.specify/memory/glossary.md`. Commands
embed a lightweight `## Glossary` step that points here (modeled on the `## Feedback` step).

The glossary is a **documentation/prompt-framework** artifact (Constitution Principle IX):
correction and conflict *judgment* are AI-agent behaviors interpreted from this doc; the
`scripts/python/glossary-utils.py` engine performs only deterministic file operations and
structural conflict detection.

The glossary is loaded as **ambient context** for every command via the Documentation Map
in `.specify/instructions.md` — no command needs to load it explicitly.

---

## 1. Input correction & anchoring (voice-first)

When interpreting user input, consult the glossary and map any recorded **variant** to its
**canonical** term. This primarily repairs errors from voice/dictated input (homophones,
easily-confused words).

- When a correction is applied, **surface it** so it is traceable and the user can override
  it — e.g. `note: interpreted 『speck it』as canonical 『Spec Kit』 (glossary)`.
- The correction is an **interpretation aid only** — never destructively rewrite the user's
  literal input.
- If a variant is **ambiguous** (maps to more than one canonical term) or unrecognized, do
  **not** guess — defer to the user.

## 2. Progressive enrichment (at checkpoints)

At each workflow wrap-up checkpoint (`requirements`, `plan`, `tasks`, `implement`), detect
newly-appearing **project-specific** terms and propose them as `origin=auto`,
`status=proposed`.

- **Common everyday words MUST NOT be recorded** — only domain/project terms.
- Route every proposal through the conflict check (§3) before writing.
- Programmatic writes go through the engine:
  `python3 .specify/scripts/python/glossary-utils.py --action add --canonical "<T>" --meaning "<M>" --origin auto --status proposed`.

## 3. Conflict detection & confirmation

Before writing any proposed or manually-entered term, run conflict detection:

```bash
python3 .specify/scripts/python/glossary-utils.py --action detect-conflict --canonical "<T>" --variants "<csv>"
```

The engine reports **structural** collisions (identical canonical; a variant already bound to
a different canonical). Additionally apply prompt-side judgment for **phonetic/near-duplicate**
and **same-term/different-meaning** clashes.

- On any detected or plausible conflict, **present it** (candidate, colliding entries, kind)
  and obtain an **explicit user resolution** (`keep-existing` / `replace` / `merge-variant` /
  `add-distinct` / `defer`) **before writing**.
- **No conflicting change may be written without user confirmation.** The engine enforces this:
  `add` refuses a conflicting write unless `--confirmed-resolution <choice>` is supplied.

## 4. Manual edits & user precedence (以用户输入为准)

- Users may edit `.specify/memory/glossary.md` directly at any time; it is human-readable.
- `origin=user` entries are **authoritative**: automatic proposals MUST NOT overwrite them
  without explicit user confirmation. The engine refuses an `auto` write over a `user` entry
  unless `--confirmed-resolution` is given.
- User-authored entries are **preserved across regenerations** — instruction generation
  creates the glossary only if absent and never discards existing content.

## 5. Scope

There is exactly **one project-wide glossary** (no per-feature glossaries), shared across all
features and commands.
