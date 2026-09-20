# Team Presets: predefined team shapes

**Owner**: the team domain (`create-team` / `/speckit.team`). This file defines the preset mechanism; the presets themselves live in `../templates/teams/`.

## Why presets exist

Without them, every `create` run derives a roster and a pattern purely from a free-form user sentence. User goals are usually vague ("帮我组个团队盯着这些仓库"), so the derived team is arbitrary and often does not match what the user pictured — the divergence only surfaces after a run. A preset is a **known-good team shape distilled from a team that actually ran**: goal skeleton, roster with pre-assigned responsibilities, pattern config with tuned thresholds, and the constraints that made it work.

Presets do **not** replace the goal-first flow. They are offered as a **match** during step 2 of team creation; instantiation proceeds directly with the match disclosed (users adjust afterwards via modify — no blocking confirmation).

## Preset file contract

Each preset is one file `../templates/teams/<preset-id>.md` with YAML frontmatter plus a body:

```yaml
---
preset_id: <kebab-id>              # unique; also the file basename
name: <display name>
pattern: parallel | serial | iteration | continuous
summary: <one line — what team shape this is>
when_to_use: <the situation this shape fits>
signals:                            # matcher input: user-intent phrases (zh + en)
  - <phrase>
inputs:                             # what the user must supply to instantiate
  - name: <param>
    required: true | false
    description: <what it is>
members:                            # roster skeleton — responsibilities, not capacities
  - role: <role>
    stage: executor | evaluator | optimizer
    type: Worker | Meta
    lifecycle: persistent | temporary
    responsibility: <the seat's accountability>
config: { }                         # pattern config skeleton with tuned defaults
provenance: <the real team/session this was distilled from>
---
```

Body sections (all mandatory):

- `## Goal Skeleton` — a fill-in-the-blank verifiable goal.
- `## Static Structure` — the Role × Stage × Type roster table.
- `## Dynamic Structure` — the execution flow of one run/cycle.
- `## Instantiation` — how to turn the preset into `.specify/teams/<slug>/team.md`, with every substitution listed.
- `## Constraints & Hard Rules` — the non-negotiable rules that made the original team safe.
- `## Known Pitfalls` — failures observed in the original runs, so an instance does not rediscover them.

## Matching protocol

1. Run `${SKILL_HOME}/scripts/match-team-preset.py --goal "<the user's goal text>"`. It scores every preset's `signals` + `pattern` keywords against the goal and returns JSON (`matches[]` with `preset_id`, `score`, `confidence`, `reasons`).
2. Act on `confidence` — **the script scores, the agent decides**:
   - `high` — present the top preset with its goal skeleton, roster and pattern, **recommend reusing it, and proceed with reuse**; the user can adapt or start from scratch afterwards via modify (no blocking choice point).
   - `medium` — present the top 2 candidates alongside the from-scratch option, without recommending.
   - `low` / `none` — say no preset matched and proceed with the normal goal-first derivation.
3. Never instantiate a preset silently, and never let a preset override an explicit user instruction — a preset is a starting point, and every field stays editable afterwards via `/speckit.team` modify / `improve-team`.
4. On reuse, fill the preset's `inputs`, apply `## Instantiation`, then persist through the ordinary `team.md` schema. Record `preset: <preset_id>` in the persisted frontmatter so later `modify` runs know the origin.

## Adding a preset

Only distil a preset from a team that has **actually run** (its `runs/` reports are the evidence). Write the file per the contract above, keep `signals` specific enough not to shadow other presets, and state `provenance`. A hypothetical shape is not a preset.

## Retiring or renaming a preset

A preset is referenced from more places than its own file. When one is dissolved, merged, or renamed, work this checklist (distilled from the 2026-08-20 four-to-two consolidation):

1. **Register the removal** — add every deleted preset file to `_OBSOLETE_SKILL_FILES` in `src/specify_cli/__init__.py` (OBSOLETE-ASSET-REGISTRY markers) and extend `tests/contract/test_cleanup_obsolete_assets.py`. Init's additive copytree never deletes; an unregistered removal leaves dead presets in every upgraded workspace.
2. **Sweep live instances** — `.specify/teams/*/team.md` frontmatter `preset:` fields referencing the old id: repoint to the successor preset (with a dated note) or drop it with a `## Lineage` note; bump `updated`. A dangling `preset:` reference is silent rot — nothing validates it.
3. **Update coupling surfaces** — `SKILL.md` Resources table, `templates/commands/team.md` (then regenerate per-tool copies via `regen-command-copies.py`), the governance-kept table in `.specify/shared/guidelines/confirmation-gates.md`, `GOVERNANCE_PATH_PATTERNS` in `scripts/python/scan-confirmation-gates.py`, and `tests/contract/test_confirmation_gates_sweep.py`.
4. **Sync and prune mirrors** — run `sync-mirrors.py --write`, then delete the stale mirror copies under `.specify/skills/create-team/templates/teams/` by hand; mirror sync never deletes.
5. **Do not rewrite history** — specs, `docs/notes/`, and team `runs/` keep the old names; they are point-in-time records.
6. **Re-validate matching** — run `match-team-preset.py` against the surviving presets' canonical use-case phrasings; a consolidation that merges two presets must not leave either intent unmatched (check `confidence` for both lineages).
