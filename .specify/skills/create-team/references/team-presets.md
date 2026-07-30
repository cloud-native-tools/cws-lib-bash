# Team Presets: predefined team shapes

**Owner**: the team domain (`create-team` / `/speckit.team`). This file defines the preset mechanism; the presets themselves live in `../templates/teams/`.

## Why presets exist

Without them, every `create` run derives a roster and a pattern purely from a free-form user sentence. User goals are usually vague ("帮我组个团队盯着这些仓库"), so the derived team is arbitrary and often does not match what the user pictured — the divergence only surfaces after a run. A preset is a **known-good team shape distilled from a team that actually ran**: goal skeleton, roster with pre-assigned responsibilities, pattern config with tuned thresholds, and the constraints that made it work.

Presets do **not** replace the goal-first flow. They are offered as a **match** during step 2 of team creation, and the user always confirms before instantiation.

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
   - `high` — present the top preset with its goal skeleton, roster and pattern, and **recommend reusing it**. Ask the user to confirm reuse, adapt, or start from scratch.
   - `medium` — present the top 2 candidates alongside the from-scratch option, without recommending.
   - `low` / `none` — say no preset matched and proceed with the normal goal-first derivation.
3. Never instantiate a preset silently, and never let a preset override an explicit user instruction — a preset is a starting point, and every field stays editable at the confirmation gate.
4. On reuse, fill the preset's `inputs`, apply `## Instantiation`, then persist through the ordinary `team.md` schema. Record `preset: <preset_id>` in the persisted frontmatter so later `modify` runs know the origin.

## Adding a preset

Only distil a preset from a team that has **actually run** (its `runs/` reports are the evidence). Write the file per the contract above, keep `signals` specific enough not to shadow other presets, and state `provenance`. A hypothetical shape is not a preset.
