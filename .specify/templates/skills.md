# Skills System Guide

> **Note**: This file is shipped by Spec Kit and created by `/speckit.instructions` only when absent — your local edits are preserved. It is an explanation document, **not** a registry: nothing here needs to be updated when skills are added or removed.

## Where skills live

Skills ship in two layers, each one directory per skill — `SKILL.md` (YAML frontmatter `name` / `description` + body) plus optional `references/`, `scripts/`, `assets/`:

- **External skills** (for consuming projects and their agents): installed flat at `.specify/skills/<name>/`.
- **Internal skills** (Spec Kit workflow machinery): installed nested at `.specify/skills/internal/<name>/`; by default not agent-visible — `/speckit.*` workflows consume them via explicit paths only. **Named exception**: `run-skills` is registered to agents so it can be invoked directly — it is the entry point for running unregistered skills, and an entry point must itself be reachable (see its SKILL.md for resolution and runtime-mode gating). On hosts whose discovery cannot surface internal skills, the same capability stays reachable via `/speckit.skills`' run intent (explicit-path loading).
- `.github/skills` is a compatibility symlink to `.specify/skills/` for tools that discover skills there.

## Discovery — no registration table

Supported AI agent CLIs discover skills natively (directory scan / skill loaders); Spec Kit maintains **no skill registry** in `instructions.md`. A skill exists iff its directory contains a valid `SKILL.md`. A one-level scan of `.specify/skills/` therefore sees external skills only; internal skills are not part of that one-level face (hosts that scan deeper, or the per-agent `skills` symlinks that expose the whole tree, may surface them — the default consumption path stays explicit path references, with `run-skills` as the named exception above). To enumerate installed external skills:

```bash
ls .specify/skills/                       # external skill directories (one level)
head -n 8 .specify/skills/*/SKILL.md      # frontmatter name/description per external skill
```

## Creating & improving

- **Create**: the `create-skills` skill (also powers `/speckit.skills`). Name-collision checks scan existing skill directories and their frontmatter `name` fields — not a registry.
- **Improve**: the `improve-skills` skill, driven by execution feedback and failure cases.
- Generic CLI skills (non–Spec Kit) are loaded by the host agent as-is; Spec-Kit-specific blocks (e.g. the engine-backed `## Feedback` step) follow `.specify/shared/workflow/runtime-mode.md` gating.

## Mirrors (Spec Kit development repositories only)

In repositories that develop skills upstream, canonical sources live in the two root layers `skills/external/<name>/` and `skills/internal/<name>/`, mirrored to `.specify/skills/` by `scripts/python/sync-mirrors.py` (external flat, internal nested). Edit the canonical source, never the mirror; run the sync engine after every change.
