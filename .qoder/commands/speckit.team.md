---
description: 团队操作统一入口：按意图路由创建、修改或运行代理团队
---
<!-- AUTO-GENERATED from templates/commands/team.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). If empty, execute the **Default Behavior (No Arguments)** defined below. If non-empty but intent is ambiguous or unsupported, report capabilities and request the missing intent (do NOT guess silently).

## Outline

`/speckit.team` is the **single entry point** for every **team** operation — the multi-agent analogue of `/speckit.agents`. It recognizes intent, then routes to the owning team skill. It delegates to skills and does **NOT** render templates inline. It MUST NOT serve single-agent authoring (that is `/speckit.agents`), and single-agent commands MUST NOT serve team operations.

What a **team** is — the **goal** (north star, not a task list; concrete, verifiable, distinct from `description`, deliberately revisable never drifting; it decides which roles/stages are needed and which collaboration pattern fits), the static structure (Role × Stage × Type roster), the dynamic structure (the four collaboration patterns and their priorities), and the persistence layout — is defined once in the owning skill's Conceptual Model: `.specify/skills/internal/create-team/references/conceptual-model.md` (goal concept and Goal–Team binding: `references/goal.md` + `.specify/shared/definitions/goal-definitions.md`; optimization-goal classification: `.specify/skills/internal/create-team/references/optimization-goals.md`; continuous operating discipline: `references/operating-loops.md`). Reference, do not restate.

### Modes → Capability Routing

`/speckit.team` exposes **exactly three modes**:

| Mode | Recognized intent | Delegates to skill |
|------|-------------------|--------------------|
| **create** | "创建团队", "组织一个团队", "组建团队", "new team", "build a team" | `create-team` |
| **modify** | "修改团队", "调整团队", "优化 team", "improve/adjust team" | `improve-team` |
| **run** | "运行团队", "执行团队", "run/execute team", "跑一遍"(可选 `--target T-<nnn>` 指定目标切片) | `run-team` |

**Routing flow**:

1. **Recognize intent** from `$ARGUMENTS` and conversation/repo context: classify as `create`, `modify`, or `run`.
2. **create** → `create-team`: establish the goal first (check the **Goal-Based Create** branch below first), then derive the roster (static) + pattern config (dynamic) from it — preset matching runs `python3 .specify/skills/internal/create-team/scripts/match-team-preset.py`, pattern selection follows the decision tree in `.specify/skills/internal/create-team/references/patterns.md`. The full create-mode procedure (derive, 直接落盘 `.specify/teams/<slug>/team.md` without a blocking wait per `.specify/shared/guidelines/confirmation-gates.md`, then present the definition and the modify path, and close per the execution-report convention — `.specify/shared/guidelines/confirmation-gates.md` § 执行报告) is the skill's create-mode procedure: `.specify/skills/internal/create-team/references/create-mode.md`.
3. **modify** → `improve-team`: targeted, evidence-based, structure-preserving edits to any of the team's three parts — the **goal** (redefining it is a first-class edit that realigns both structures), the **static structure**, or the **dynamic structure**. Re-persist and bump `updated`.
4. **run** → `run-team`: the run flow (load → five-check preview via the goal-utils engine → goal restatement → structure render → present & execute → report) is the skill's procedure — `.specify/skills/internal/run-team/SKILL.md`; inputs are the team slug and the optional `--target`, outputs are the run report and ledger entries.
5. **Empty arguments** → execute **Default Behavior (No Arguments)** below.
6. **Non-empty but ambiguous / unsupported** → report capabilities and request the missing intent (see "Ambiguous or Unsupported Intent" below).
7. **modify / run targeting a team that does not exist** under `.specify/teams/` → report **"team not found"** and offer to `create` it.

### Default Behavior (No Arguments)

When `$ARGUMENTS` is empty, the command MUST execute the following sequence instead of routing to a mode:

1. **List all existing teams** — scan `.specify/teams/*/team.md` and present a summary table with each team's `slug`, `name`, `goal`, and `pattern`. If no teams exist, state "No teams found" explicitly.
2. **Give contextual suggestions** — based on the current conversation, recent repo activity, and the listed teams, recommend the most relevant next action. Examples:
   - A team whose goal aligns with the current task → suggest `run <slug>`.
   - A team whose structure seems outdated relative to recent changes → suggest `modify <slug>`.
   - No teams exist or no team fits the current need → suggest `create` with a proposed goal derived from context.
   Suggestions MUST be grounded in observable context (conversation history, repo state, team definitions), NOT fabricated.
3. **Show capability summary** — briefly list the three modes (create / modify / run) so the user knows what operations are available.

This behavior is informational and non-destructive: it MUST NOT create, modify, or run any team without explicit user instruction.

### Ambiguous or Unsupported Intent

When intent cannot be resolved from non-empty arguments, the command MUST report the recognized capabilities and request the missing intent. It MUST NOT guess silently or fail without a message. Report this capability listing:

- **create** — establish the team's **goal**, then author a new team (static + dynamic structure) organized around it and persist it → `create-team`
- **modify** — adjust/optimize an existing team — reshape its structure, or **redefine its goal** and realign the structure to the new goal → `improve-team`
- **run** — restate the **goal**, render the team's structure, and execute it directly (preview is disclosure, not a gate) → `run-team`

### Goal-Based Create — deterministic entry (create path)

When a token in `$ARGUMENTS` exactly matches an archived `<goal-slug>` under `.specify/goal/`, the create path enters the **goal-based branch** directly. The entry is deterministic and engine-driven — recognition runs `python3 .specify/scripts/python/goal-utils.py list --json` and exact-matches the token (or a path to its `goal.md`); it MUST NOT be asserted from memory or semantics, and the branch decision is disclosed in the run output rather than gated on confirmation. Two rejections stop without writing: a **dangling reference** (user-named but absent from `list`) errors with the verbatim prefix `goal 未定义:` and points to `/speckit.goal create`; a **terminal goal** (`achieved`/`abandoned`) is reported and refused. Everything after entry — loading via `parse_goal` (objective, criteria incl. the `None provided.` missing state, status, targets, history), the four-element analysis, the decomposition proposal with batch approval, territory discipline, and team derivation/落盘 — is the skill's branch procedure: `.specify/skills/internal/create-team/references/create-mode.md` → *Goal-based create branch*.

### Run Mode

The **run** mode delegates entirely to the `run-team` skill — `.specify/skills/internal/run-team/SKILL.md` — which owns the procedure (five-check preview via the goal-utils engine as the single point of truth, goal restatement, static/dynamic structure render, present & execute, pattern orchestration, run report) and its `--target` invariants and output discipline. The preview is disclosure, and the team executes directly once presented (可逆动作自动执行,判据:`.specify/shared/guidelines/confirmation-gates.md`); **continuous** loops are the exception and keep their tiered gates (`.specify/skills/internal/create-team/references/operating-loops.md`, `.specify/templates/teams/project-cluster.md`).

- **Inputs**: `run <team-slug> [--target <T-<nnn> | <goal-slug>.T-<nnn>>]` (local form canonical; qualified form accepted only when its `<goal-slug>` equals the bound goal).
- **Outputs**: run report at `.specify/teams/<slug>/runs/<UTC-timestamp>-report.md` (with `## Verification` and, on target-assigned runs, the `**Target 指派**` field) and ledger entries carrying `"target_ref"`.

**`--target` invariants**: Goal–Team binding, identity resolution, and the summary delivery directory are unchanged by `--target` — it is this run's focus slice, not a rebinding or a write-domain declaration.

### Persistence

Canonical store: the team **directory** `.specify/teams/<slug>/` — definition at `team.md`, run reports under `runs/`; no per-tool symlink. The persisted schema (frontmatter, `## Goal` authored first, `## Static Structure`, `## Dynamic Structure`) is owned by `create-team` (`references/create-mode.md`).

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "/speckit.team" --unit-type command --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "/speckit.team" --unit-type command`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "/speckit.team" --unit-type command --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Docs Sync Eval — `.specify/shared/workflow/docs-step.md` § "Evaluation procedure (the embedded step points here)"

## Handoffs

**Before**: Optional `/speckit.agents` to author or refine the single agents that will become team members.

**After**: Run `/speckit.instructions` to sync discoverability of newly created teams and team skills.