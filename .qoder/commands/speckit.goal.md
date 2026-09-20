---
description: 创建、查看、修改项目目标，并协调共享该目标的团队
---
<!-- AUTO-GENERATED from templates/commands/goal.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions.

## Positioning

`/speckit.goal` is the **sole authoring entry** for project-level goal definitions. It owns create, view, modify, migrate, and coordinate. No skill, script, or other command may write into the goal archive.

A **Goal** is a project-level authored fact source. Its concept — composition, lifecycle, boundary against Requirement, criteria authority, singularity, and the team binding — is defined once in `.specify/shared/definitions/goal-definitions.md`. **Link to that document; never restate it here.** This command owns only the *operations*.

Deterministic rules (identity grammar, three-part structure, lifecycle table, change history, archive enumeration) live in `.specify/scripts/python/goal-utils.py`. Call the engine; do not re-derive its judgments in prose.

## Glossary

Consult `.specify/memory/glossary.md` and apply `.specify/shared/workflow/glossary.md`: map recorded homophone/confusable variants to canonical terms before acting, surfacing each correction. At wrap-up propose new project-specific terms (`origin=auto`, `status=proposed`); non-conflicting terms are written directly and merged into the wrap-up report (non-blocking) — only conflicts/overwrites of user entries still pause.

## Modes

Mode is inferred from `$ARGUMENTS`; the inferred mode is disclosed with every run, and execution proceeds directly (可逆动作自动执行,判据:`.specify/shared/guidelines/confirmation-gates.md`). Ambiguous input resolves to `view`, which is read-only.

| Mode | Purpose | Writes |
|------|---------|--------|
| `create` | archive a new goal definition | `.specify/goal/<goal-slug>/goal.md` |
| `view` | list the archive, or show one goal | nothing |
| `modify` | change objective, criteria, lifecycle state, or Targets | the same definition file |
| `targets` | add / list / transition the goal's Targets (run-assignable scope slices) | the same definition file |
| `migrate` | derive a definition from a team's inline goal and switch that team to a reference | new `goal.md` + that `team.md` |
| `coordinate` | propose a territory re-division across teams sharing one goal | nothing until ratified, then each `team.md` |

`targets` is a modify-intent route: Target authorization, listing, and state transitions all land through this single authoring entry — no other surface writes the `## Targets` section. Concept: link `.specify/shared/definitions/goal-definitions.md` (Target Decomposition), never restate.

## Outline

1. **Resolve context**: run `.specify/scripts/bash/check-prerequisites.sh --json --paths-only` for `REPO_ROOT`. The archive is `REPO_ROOT/.specify/goal/`.

2. **Determine the mode** from `$ARGUMENTS`; state it back to the user.

3. **Preview → execute.** Before any write, show: the mode, the target path, and the exact content to be written (or the diff for a modify) — then write directly (preview is disclosure, not a blocking gate; 事后修改经 `/speckit.goal` modify). `view` stays read-only.

4. **Execute via the engine** — never hand-write a definition file:

   ```bash
   python3 .specify/scripts/python/goal-utils.py create <goal-slug> \
     --objective "<desired end outcome>" \
     --criterion "<verifiable condition>" --criterion "<...>" --json
   python3 .specify/scripts/python/goal-utils.py list    # archive listing (no `view` action)
   python3 .specify/scripts/python/goal-utils.py validate <goal-slug>
   python3 .specify/scripts/python/goal-utils.py status <goal-slug> --set achieved
   python3 .specify/scripts/python/goal-utils.py criteria <goal-slug> --criterion "<new>"
   python3 .specify/scripts/python/goal-utils.py targets <goal-slug> --add "<sub-outcome statement>"
   python3 .specify/scripts/python/goal-utils.py targets <goal-slug> --check "<sub-outcome statement>"
   python3 .specify/scripts/python/goal-utils.py targets <goal-slug> --list
   python3 .specify/scripts/python/goal-utils.py targets <goal-slug> --set done --id T-001
   ```

   Exit codes: `0` ok · `2` input error (rejection) · `3` not found · `4` validation failed. A non-zero exit is a **verdict**: report it, never argue around it.

   `targets` notes: the engine renders the `## Targets` section (never hand-edit it); statements pass the same GD-2/GD-3 shape check at slice scale and must not restate a success criterion; terminal goals are read-only; terminal Target identities are never reused. A terminal-state Target reported by a run is a **review bifurcation**: verify by hand — if genuinely done, stop; if evidence contradicts, reopen via `targets <slug> --set open --id <T-nnn>` and re-issue the run. There is no terminal-execution bypass.

5. **Interview for `create`** — collect exactly four things, and nothing else. Ask them per the interview pattern (`.specify/shared/patterns/interview-pattern.md`): **open** questions carrying their context, no option menus and no recommended answers (the objective and its slices are the user's to state, not yours to propose), facts looked up rather than asked, each answer written through before the next round.
   - the **objective**: the desired end *outcome*. If the user describes steps, say so and ask for the outcome instead (the engine rejects task lists as GD-2).
   - **success criteria**: zero or more verifiable conditions. Zero is legal — the archive records `None provided.` and consumers declare the absence rather than inventing criteria. Verifiable ≠ machine-checkable: a criterion whose measurement route is **manual/human review** (a named reviewer judging the end state, recorded by degree) is an equally legitimate form — concept: `.specify/shared/definitions/goal-definitions.md` (verifiable success criteria), link, never restate. Say so out loud when asking, so the user does not withhold a real criterion because no program can measure it.
   - the **identity**: a slug that is also the directory name. Reuse `goal_slug` semantics; do not invent a second identifier.
   - **Targets** (optional annex — concept: Target Decomposition in `.specify/shared/definitions/goal-definitions.md`, link, never restate): zero or more sub-outcome statements under the confirmed objective. Zero is legal — a goal without Targets is fully valid and this item may be skipped entirely. Each statement must be outcome-shaped at slice scale (GD-2), a slice of this objective rather than an independent end state (GD-3), and must not restate a success criterion. Collect only statements the user states — in this mode you never draft slices on their behalf.

   If the objective bundles several objectives the engine rejects it as GD-3 — help the user split it into separate goals, each with its own directory and lifecycle.

   **Execution order**: write the definition first (`create`), then land each collected Target statement through the engine — `targets <goal-slug> --check "<statement>"` for the dry-run verdict, `targets <goal-slug> --add "<statement>"` to authorize; never hand-write the `## Targets` section. A rejected statement is a verdict: report it, let the user reword or drop it, and continue with the rest — the already-created goal is never rolled back for a rejected slice.

6. **`migrate <team-slug>`**: read that team's inline goal, derive a definition whose objective and criteria are semantically equivalent, create it, then set the team's `goal_slug` to the new identity. **Never** delete the team's inline goal — retention is the user's choice, and migration is per-team and optional.

7. **`coordinate <goal-slug>`**: the mechanism detects overlap and **proposes** a re-division with its rationale. It writes nothing. On the user's ratification, write the agreed territory back into each affected `team.md` — never into the goal directory.

## Boundaries

- The definition is **authored**. No derived flow may write `goal.md`; the summary refresh writes only `<goal-slug>/summary/**`.
- The goal's object is **unrestricted** — the framework itself, codebase-wide convention convergence, runtime outcomes. Never reject a goal because no functional requirement in this project implements it.
- Criteria are **measured by degree**, not per-clause pass/fail. Never render a criterion as a binary checkbox.
- Criteria are **cross-feature** and disjoint from any requirements spec's `SC-xxx`. Never copy criteria in either direction.
- `requirements.md` carries no goal field and a goal never enumerates functional requirements. The two sit on different planes with no hierarchy.
- A team serves exactly one goal at a time.
- Terminal goals (`achieved` / `abandoned`) stay archived. Deletion is not a lifecycle transition.

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.goal" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Documentation

At the same wrap-up point, apply the docs-sync evaluation per `.specify/shared/workflow/docs-step.md` and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up.

## Handoffs

**Before**: none — a goal may be archived at any time, with or without teams.

**After**: bind a team by declaring `goal_slug` in its `team.md` (see `/speckit.team`). Once two or more teams share a goal, run `coordinate` to keep their territories disjoint.