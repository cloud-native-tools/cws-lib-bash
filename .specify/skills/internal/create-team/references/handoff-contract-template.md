# Handoff Contract — Template and Rules (`handoff.md`)

**Owner**: the `create-team` skill authors this shape; the artifact's contract clauses are
`contracts/handoff-contract.md` C-53…C-70 in `.specify/specs/094-goal-team-parallel/`.
**Location**: `<spec-dir>/handoff.md` — one per spec, a fixed relative path, no variant
names and no second location (C-53; ruling N-3 of `tasks.md` puts this template beside
`create-mode.md` and `conceptual-model.md`).

## Production and consumption

- **Produced by the `tasks` stage only**, after `goal-utils.py handoff-decision --tasks
  <spec-dir>/tasks.md` returns `handoff` (C-68). The `plan` stage MUST NOT produce one —
  the task table does not exist yet (Clarifications Q4).
- **Consumed by `implement`** (C-68). A spec whose decision returned `direct` MUST NOT
  carry this file; an unexpected one is reported (`handoff-without-handoff-decision`) and
  is never consumed as authority (C-69).
- **Refused at creation when a key does not resolve**: `goal_slug` and `team_slug` are
  validated against `.specify/anchoring/<goal_slug>/goal.md` and
  `.specify/teams/<team_slug>/team.md` through the engine; an unresolvable key exits 2
  with `handoff-dangling-key` naming the key (C-58). The reverse `handoff_ref` is written
  on both definitions by the engine's binding action, never by this file alone (C-59).
- **`implement` refuses to start** a handoff-mode run when the contract is `abandoned` or
  when either key no longer resolves; it MUST NOT repair the contract itself (C-70).

## The shape (handoff/v1)

Instantiate the block below verbatim. Every section is mandatory; an **empty section is
the single line `None.`**, never omitted (C-54). Keep the keys and their order.

```markdown
---
contract: handoff/v1
state: active
goal_slug: <goal-slug>
team_slug: <team-slug>
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
supersedes: null
---

## Status

State: read from the frontmatter `state` field — `active` → `fulfilled` or
`active` → `abandoned`; a terminal handoff is retained, never deleted (C-55).
This contract hands the construction of the referenced task ranges to the referenced
crew; design authority stays on the spec side (C-64).

## Goal

Cite by `goal_slug` only: <goal-slug>. Never restate the goal's objective or criteria —
the definition is authoritative (C-56).

## Targets

The goal's `T-NNN` ids the crew may advance (cite, never restate their statements):

- T-NNN — <one-line id citation only>

## Task Reference

Reference the task table by id ranges or an explicit id list (for example `T001–T010`).
Never copy task rows: a line beginning with `- [ ] T` in this contract is the refused
defect `task-copy-in-handoff` (C-57).

## Territory

The paths the crew may write, relative to the spec directory (expanded into the bound
teams' `territory.write` by `improve-team`, C-61):

- write: `<spec-dir>/<path>`

The following MUST stay forbidden to every seat that carries the expansion (C-62):
`requirements.md`, `tasks.md`, `verification.md`, `handoff.md`.

## Acceptance Criteria

Cite the success criteria by id (`SC-NNN`) from `requirements.md`; never restate them.

## Writeback

One record per completed task at `<spec-dir>/writeback/<T-NNN>.yaml` carrying `task`,
`outcome` (`done` | `blocked` | `deferred`), `run_id`, `evidence` (path or command plus
exit code), and `at` (C-65). A missing record is `not-written-back`, never inferred from
a commit message or a summary (C-66).

## Crew

Cite by `team_slug` only: <team-slug>. Never restate the team's roster or its goal
content.
```

## Rules that the shape cannot express

- **Two-terminal-state machine**: `active` transitions only to `fulfilled` or
  `abandoned`; a terminal contract is retained in place, never deleted (C-55). The
  `active → fulfilled` transition is recorded by the spec side after the writeback is
  verified (C-64).
- **Design face ownership**: the crew never holds `write` on `handoff.md`; amendments are
  a spec-side edit plus an engine re-expansion (C-64). `tasks.md` and `verification.md`
  remain spec-side writes; the crew's delivery is the writeback set plus patches inside
  its territory, and it MUST NOT mark a task complete in the task table (C-67).
- **Territory expansion**: on activation `## Territory` is expanded into the
  `territory.write` of **every** team bound to that `goal_slug` as an explicit,
  disclosed `improve-team` modification — one record per team, never an optimizer guess
  (C-61). Granted entries stay inside the spec directory and MUST NOT name
  `.specify/anchoring/**` or `.specify/teams/**` (C-63).
- **No task rows, no goal prose**: `## Goal` and `## Crew` cite identities; `## Targets`
  and `## Task Reference` cite ids. Copying task rows or restating goal content is a
  defect, not a richer contract (C-56/C-57).
