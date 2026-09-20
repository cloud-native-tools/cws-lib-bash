# Skills System Guide

> **Note**: This file is shipped by Spec Kit and created by `/speckit.instructions` only when absent — your local edits are preserved. It is an explanation document, **not** a registry: nothing here needs to be updated when skills are added or removed.

## Where skills live

- Installed skills: `.specify/skills/` — one directory per skill: `SKILL.md` (YAML frontmatter `name` / `description` + body) plus optional `references/`, `scripts/`, `assets/`.
- `.github/skills` is a compatibility symlink to `.specify/skills/` for tools that discover skills there.

## Discovery — no registration table

Supported AI agent CLIs discover skills natively (directory scan / skill loaders); Spec Kit maintains **no skill registry** in `instructions.md`. A skill exists iff its directory contains a valid `SKILL.md`. To enumerate installed skills:

```bash
ls .specify/skills/                       # skill directories
head -n 8 .specify/skills/*/SKILL.md      # frontmatter name/description per skill
```

## Creating & improving

- **Create**: the `create-skills` skill (also powers `/speckit.skills`). Name-collision checks scan existing skill directories and their frontmatter `name` fields — not a registry.
- **Improve**: the `improve-skills` skill, driven by execution feedback and failure cases.
- Generic CLI skills (non–Spec Kit) are loaded by the host agent as-is; Spec-Kit-specific blocks (e.g. the engine-backed `## Feedback` step) follow `.specify/shared/workflow/runtime-mode.md` gating.

## Mirrors (Spec Kit development repositories only)

In repositories that develop skills upstream, canonical sources live in the root `skills/` directory and are mirrored to `.specify/skills/` by `scripts/python/sync-mirrors.py`. Edit the canonical source, never the mirror; run the sync engine after every change.
