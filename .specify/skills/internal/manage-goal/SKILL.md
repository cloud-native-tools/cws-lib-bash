---
name: manage-goal
description: Author and manage project-level goal definitions — the executable core of `/speckit.goal`. Runs the six modes (create / view / modify / targets / migrate / coordinate) through the goal engine: the four-element interview for a new goal (objective, success criteria, identity, Targets), the read/write engine grouping with exit-code verdicts, the single destructive write (`criteria --clear`) behind explicit approval, Target slice authorization with GD-2/GD-3 shape checks, per-team migration from an inline goal, and territory re-division proposals across teams sharing one goal. Every write goes through the engine — the goal archive is engine-write-only. Use this when the user mentions ["goal", "项目目标", "创建目标", "goal definition", "objective", "成功判据", "success criteria", "targets", "目标切片", "migrate goal", "目标迁移", "coordinate", "目标协调", "goal archive", "goal_slug", "goal achieved", "goal abandoned"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/manage-goal/SKILL.md>"
---

# manage-goal

## Goal

Own and execute the operations behind `/speckit.goal` — the **sole authoring entry** for
project-level goal definitions. A **Goal** is a project-level authored fact source; this
skill owns only the *operations* (mode semantics, the four-element interview, execution
ordering, engine invocation). The goal *concept* — composition, lifecycle, boundary
against Requirement, criteria authority, singularity, and the team binding — is defined
once in `.specify/shared/definitions/goal-definitions.md`. **Link to that document; never
restate it.** Deterministic rules (identity grammar, three-part structure, lifecycle
table, change history, archive enumeration) live in `.specify/scripts/python/goal-utils.py`. Call
the engine; do not re-derive its judgments in prose.

**Non-negotiable boundary** (carried verbatim from the command's positioning): no skill,
script, or other command may write into the goal archive **directly** — the goal engine
(`goal-utils.py`) is its sole writing path, whether driven by `/speckit.goal` or carried
as delegated logic behind it.

Canonical extraction source: `.specify/templates/commands/goal.md` § Modes, § Outline 1–7, and
§ Boundaries. Content moved here verbatim in substance; the command template keeps entry,
user-input handling, glossary pre-step, and lifecycle only.

## Input Contract

- **Intent**: one of `create | view | modify | targets | migrate | coordinate`, optionally
  with a goal-slug or team-slug. Mode is inferred from the request and **disclosed with
  every run**.
- **Ambiguous input resolves to `view`** — which is read-only.
- **Reversibility**: execution proceeds directly for reversible actions
  (可逆动作自动执行，判据：`.specify/shared/guidelines/confirmation-gates.md`) — the single
  destructive write, named in step 4, is the exception.

| Mode | Purpose | Writes |
|------|---------|--------|
| `create` | archive a new goal definition | `.specify/goal/<goal-slug>/goal.md` |
| `view` | list the archive, or show one goal | nothing |
| `modify` | change objective, criteria, lifecycle state, or Targets | the same definition file |
| `targets` | add / list / transition the goal's Targets (run-assignable scope slices) | the same definition file |
| `migrate` | derive a definition from a team's inline goal and switch that team to a reference | new `goal.md` + that `team.md` |
| `coordinate` | propose a territory re-division across teams sharing one goal | nothing until ratified, then each `team.md` |

`targets` is a modify-intent route: Target authorization, listing, and state transitions
all land through this single authoring entry — no other surface writes the `## Targets`
section. Concept: link `.specify/shared/definitions/goal-definitions.md` (Target
Decomposition), never restate.

## Workflow

### 1. Resolve context

Run `.specify/scripts/bash/check-prerequisites.sh --json --paths-only` for `REPO_ROOT`.
The archive is `REPO_ROOT/.specify/goal/`.

### 2. Determine the mode

From the request; state it back to the user.

### 3. Preview → execute

Before any write, show: the mode, the target path, and the exact content to be written
(or the diff for a modify) — then write directly (preview is **disclosure, not a blocking
gate**；事后修改经 `/speckit.goal` modify). `view` stays read-only.

### 4. Execute via the engine — never hand-write a definition file

The block below fixes only the **read/write grouping**; every action's full flag set and
defaults are owned by `python3 .specify/scripts/python/goal-utils.py --help` and are not restated
here.

```bash
# 读组 — zero writes
python3 .specify/scripts/python/goal-utils.py list    # archive listing (no `view` action)
python3 .specify/scripts/python/goal-utils.py validate <goal-slug>
python3 .specify/scripts/python/goal-utils.py check-statement "<sub-outcome statement>"
python3 .specify/scripts/python/goal-utils.py targets <goal-slug> --list
python3 .specify/scripts/python/goal-utils.py targets <goal-slug> --check "<sub-outcome statement>"

# 写组 — mutates the one definition file
python3 .specify/scripts/python/goal-utils.py create <goal-slug> --objective "<desired end outcome>"
python3 .specify/scripts/python/goal-utils.py objective <goal-slug> --set "<revised outcome>"
python3 .specify/scripts/python/goal-utils.py criteria <goal-slug> --criterion "<new>"
python3 .specify/scripts/python/goal-utils.py status <goal-slug> --set achieved
python3 .specify/scripts/python/goal-utils.py targets <goal-slug> --add "<sub-outcome statement>"
python3 .specify/scripts/python/goal-utils.py targets <goal-slug> --set done --id T-001
python3 .specify/scripts/python/goal-utils.py migrate <team-slug>
```

Exit codes: `0` ok · `2` input error (rejection) · `3` not found · `4` validation failed.
A non-zero exit is a **verdict**: report it, never argue around it.

**破坏性写入**（桶归属见 `.specify/shared/guidelines/confirmation-gates.md` §破坏性动作清单）：`criteria <goal-slug> --clear` 以空值覆盖既有判据集。引擎对缺参的 `criteria` 调用一律 exit 2——它 MUST NOT 被读成查看入口，也不会静默清空；传 `--clear` 之前 MUST 先取得用户明示批准。其余写入均为可逆动作：直接执行，按执行报告呈现，事后经 `/speckit.goal` modify 修改。

`create` 另接受两个可选附注——`--title`（可读标题，身份仍是 slug）与 `--boundary`（排除项）：仅在用户自行陈述时携带，MUST NOT 为此发问，step 5 的收集集不因它们扩张。概念见 `.specify/shared/definitions/goal-definitions.md`。

`targets` notes:

- the engine renders the `## Targets` section (never hand-edit it);
- statements pass the same GD-2/GD-3 shape check at slice scale and must not restate a
  success criterion;
- terminal goals are read-only; terminal Target identities are never reused;
- a terminal-state Target reported by a run is a **review bifurcation**: verify by hand —
  if genuinely done, stop; if evidence contradicts, reopen via
  `targets <slug> --set open --id <T-nnn>` and re-issue the run. There is no
  terminal-execution bypass.

### 5. Interview for `create` — exactly four things, nothing else

Ask them per the interview pattern (`.specify/shared/patterns/interview-pattern.md`):
**open** questions carrying their context, no option menus and no recommended answers
(the objective and its slices are the user's to state, not yours to propose), facts looked
up rather than asked, each answer written through before the next round.

1. **the objective**: the desired end *outcome*. If the user describes steps, say so and
   ask for the outcome instead (the engine rejects task lists as GD-2).
2. **success criteria**: zero or more verifiable conditions. Zero is legal — the archive
   records `None provided.` and consumers declare the absence rather than inventing
   criteria. Verifiable ≠ machine-checkable: a criterion whose measurement route is
   **manual/human review** (a named reviewer judging the end state, recorded by degree) is
   an equally legitimate form — concept: `.specify/shared/definitions/goal-definitions.md`
   (verifiable success criteria), link, never restate. Say so out loud when asking, so the
   user does not withhold a real criterion because no program can measure it.
3. **the identity**: a slug that is also the directory name. Reuse `goal_slug` semantics;
   do not invent a second identifier.
4. **Targets** (optional annex — concept: Target Decomposition in
   `.specify/shared/definitions/goal-definitions.md`, link, never restate): zero or more
   sub-outcome statements under the confirmed objective. Zero is legal — a goal without
   Targets is fully valid and this item may be skipped entirely. Each statement must be
   outcome-shaped at slice scale (GD-2), a slice of this objective rather than an
   independent end state (GD-3), and must not restate a success criterion. Collect only
   statements the user states — in this mode you never draft slices on their behalf.

If the objective bundles several objectives the engine rejects it as GD-3 — help the user
split it into separate goals, each with its own directory and lifecycle.

**Execution order**: write the definition first (`create`), then land each collected
Target statement through the engine — `targets <goal-slug> --check "<statement>"` for the
dry-run verdict, `targets <goal-slug> --add "<statement>"` to authorize; never hand-write
the `## Targets` section. A rejected statement is a verdict: report it, let the user
reword or drop it, and continue with the rest — the already-created goal is never rolled
back for a rejected slice.

### 6. `migrate <team-slug>`

Read that team's inline goal, derive a definition whose objective and criteria are
semantically equivalent, create it, then set the team's `goal_slug` to the new identity.
**Never** delete the team's inline goal — retention is the user's choice, and migration is
per-team and optional.

### 7. `coordinate <goal-slug>`

The mechanism detects overlap and **proposes** a re-division with its rationale. It writes
nothing. On the user's ratification, write the agreed territory back into each affected
`team.md` — never into the goal directory.

## Boundaries

- **Engine-write-only (non-negotiable)**: the definition is **authored**. No derived flow
  may write `goal.md`; no skill, script, or other command may write into the goal archive
  directly — `goal-utils.py` is its sole writing path. The summary refresh writes only
  `<goal-slug>/summary/**`.
- The goal's object is **unrestricted** — the framework itself, codebase-wide convention
  convergence, runtime outcomes. Never reject a goal because no functional requirement in
  this project implements it.
- Criteria are **measured by degree**, not per-clause pass/fail. Never render a criterion
  as a binary checkbox.
- Criteria are **cross-feature** and disjoint from any requirements spec's `SC-xxx`.
  Never copy criteria in either direction.
- `requirements.md` carries no goal field and a goal never enumerates functional
  requirements. The two sit on different planes with no hierarchy.
- A team serves exactly one goal at a time (binding concept:
  `.specify/shared/definitions/goal-definitions.md` § Goal–Team Binding).
- Terminal goals (`achieved` / `abandoned`) stay archived. Deletion is not a lifecycle
  transition.

## Command-lifecycle surfaces (kept in `/speckit.goal`)

Entry argument handling (`.specify/shared/workflow/user-input-protocol.md`), the glossary
pre-step (`.specify/memory/glossary.md`, protocol `.specify/shared/workflow/glossary.md`),
the `## Feedback` / `## Documentation` steps, and handoffs (team binding via
`/speckit.team`) stay in the command template — they are command lifecycle, not goal
operations.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:manage-goal" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:manage-goal" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:manage-goal" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
