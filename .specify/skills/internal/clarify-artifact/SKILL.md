---
name: clarify-artifact
description: Identify underspecified areas in the current feature's phase artifact and encode ratified answers back into that same file — pre-plan `requirements.md`, post-plan `plan.md`, or post-tasks `tasks.md` — via a fail-fast writability probe, a per-mode taxonomy coverage scan, and a bounded loop of closed multiple-choice questions (options table plus a Recommended pick), and also own the Scope Revision Protocol for when the user re-scopes the feature after downstream artifacts already exist (amend upstream in place, regenerate downstream by hand, residual-reference sweep). Use this when the user mentions ["clarify", "clarification", "resolve ambiguities", "ambiguous", "underspecified", "re-clarify", "clarify the plan", "clarify requirements", "scope revision", "user re-scoped", "澄清", "消歧", "解决歧义", "欠指定", "澄清需求", "修订范围", "范围变更"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/clarify-artifact/SKILL.md>"
---

# clarify-artifact

## Goal

Detect and reduce ambiguity or missing decision points in the current phase's primary
artifact and record clarifications directly in that file. One run targets exactly one
phase artifact and leaves it self-consistent, or — when the user has re-scoped the
feature — executes the Scope Revision Protocol instead of a clarification run.

Owning command: `/speckit.clarify`. Canonical extraction source:
`.specify/templates/commands/clarify.md` § Phase 0 (Phase Detection & Context Setup), § Taxonomy
& Coverage Scan, § Question Generation & Interactive Loop, § Report, § Behavior Rules,
and § Scope Revision Protocol. Content moved here verbatim in substance; the command
template keeps entry, wiring, and lifecycle delegation only.

## Input Contract

- **Prerequisite**: `requirements.md` exists in the feature's requirements dir. If no
  `requirements.md` exists at all → abort and instruct `/speckit.requirements` first.
- **Arguments**: process `$ARGUMENTS` as command parameters — either explicit decisions
  to integrate, or an explicit target artifact naming a mode override (below). They are
  never standalone instructions.
- **Script**: run the command's declared prerequisite script — the `{SCRIPT}` slot,
  `.specify/scripts/bash/check-prerequisites.sh --json --paths-only` — from repo root once; parse
  JSON for `REPO_ROOT`, `BRANCH`, `REQUIREMENT_ID`, `REQUIREMENTS_DIR`, `FEATURE_SPEC`,
  `IMPL_PLAN`, `TASKS`.

## Workflow

### 1. Phase Detection & Context Setup

**Determine current phase** by file existence in `REQUIREMENTS_DIR`:

| Phase | Trigger | Target File | Handoff |
|-------|---------|-------------|---------|
| A: Post-Requirements | `plan.md` NOT exist | `requirements.md` | `/speckit.plan` |
| B: Post-Plan | `plan.md` exists, `tasks.md` NOT exist | `plan.md` | `/speckit.tasks` |
| C: Post-Tasks | `tasks.md` exists | `tasks.md` | `/speckit.implement` |

If no `requirements.md` at all → abort, instruct `/speckit.requirements` first.
Log: `**Mode: [A/B/C] — clarifying [target]**`

**Mode override**: when `$ARGUMENTS` explicitly names an upstream artifact (e.g.
"re-clarify the requirements" while `plan.md` already exists), clarify THAT artifact
instead of the phase-detected one, cascade accepted answers into the derived artifacts,
and log the deviation from the default mode. The default table applies only when the
user gives no explicit target.

**Writability probe (fail fast)**: before generating any questions, verify the target
file is writable (touch-test or write-bit stat on the target and its directory). If
unwritable (e.g. root-owned spec dir), STOP immediately with an actionable message
(owning path + fix command such as `sudo chown -R $USER <dir>`) — do NOT run the
question loop first and lose the integration work at the final write. If the user
chooses to proceed read-only, batch all integrations into ONE write attempt at the end
instead of the per-answer saves the mode's integration rules call for.

**Load common context (summary-first — see
`.specify/shared/guidelines/token-efficiency.md`)**: project `.specify/memory/features.md`
via `grep -E '^\| [0-9]{3}'` index rows; read `research.md` (if exists); pull
`.specify/memory/constitution.md`, `README.md`, and `docs/` content only as targeted
excerpts when a candidate question actually requires them — never wholesale.

**Load mode-specific context** (see taxonomy reference).

### 2. Taxonomy & Coverage Scan

For the active mode's detailed taxonomy categories and integration rules, load:
`.specify/shared/constants/clarify-taxonomy.md`

Each mode has its own taxonomy. For each category, mark status (Clear / Partial /
Missing). Add candidate questions for Partial/Missing categories unless clarification
would not materially change implementation.

**Same-author detection delegation**: this scan usually runs on an artifact the same
agent just wrote — the ordinary case is a `requirements → clarify` chain without a
break — so the scan inherits the author's own reading, and an ambiguity unnoticed while
writing is unlikely to be noticed while scanning. When that condition holds, delegate
the coverage scan to fresh-context read-only subagents. Apply the canonical gate in
`.specify/shared/workflow/objective-analysis-gate.md` (single source of truth; do not
restate its rules here). This skill has no severity tiers, so the local analogue of the
propagation-surface cap is the materiality filter above: do not raise a question whose
answer changes no **downstream artifact**.

If spec contains `Feature ID: Need clarification` or `Feature Name: Need clarification`,
treat Feature Linkage as high-priority.

### 3. Question Generation & Interactive Loop

This loop is **clarification (澄清), not interviewing (采访)** — a distinction worth
keeping straight because both ask the user questions. Here the answer space is **already
bounded** by the target artifact and the mode's taxonomy, so questions are **closed**:
an options table plus a **Recommended** pick that the user ratifies or corrects. That is
why this skill may propose answers at all.

From `.specify/shared/patterns/interview-pattern.md` it borrows only the **context
discipline** (every question states why it arises and what the answer will change) and
the **fact-vs-decision split** (never ask the user for anything the repo can answer). It
deliberately does **not** adopt that pattern's open-question rule — presenting options is
correct when the possibilities really are known.

The **no-jargon half** of that borrowing is not restated here either: which terms may
stand unexplained, which internal forms must never reach the user, what each question
must carry for a reader who opens it alone, and how the option table's consequence
previews are worded are all defined once in
`.specify/shared/guidelines/user-facing-comprehension.md` (this skill covers surface
class ⑤); its condition sets MUST NOT be copied into this skill.

**Escalation**: when the coverage scan shows the answer space is not actually bounded —
the decisions *branch*, answers keep unlocking questions nobody anticipated, or the cap
is reached with critical ambiguities still open — stop and recommend `/speckit.interview`
on the same target artifact (open questions, unbounded rounds, durable ledger). Do not
silently exceed the cap, do not fabricate the remainder, and do not force an options
table onto a decision whose options you are guessing.

1. **Integrate user-provided decisions first**: when `$ARGUMENTS` contains explicit
   decisions (not open questions — e.g. a naming choice, a chosen option), integrate them
   into the target artifact BEFORE generating the question queue; the queue then covers
   only residual ambiguities. When residuals are few and independent, group them into one
   prompt instead of a per-question loop.

2. **Generate prioritized queue** (max 5 questions internally). Constraints:
   - Filter via Research: Skip questions answered by `research.md`
   - Maximum 10 total across session
   - Each must be answerable with multiple-choice (2–5 options) OR ≤5-word short answer
   - Only include questions whose answers materially impact downstream artifacts
   - Balance category coverage; favor high-impact unresolved categories

3. **Questioning loop** — order-dependent questions singly; mutually independent ones
   MAY batch:
   - **Batching rule**: ask a question alone when its framing depends on an earlier
     answer (the later options change with the earlier choice); when questions are
     mutually independent — neither answer alters the other's option set — they MAY be
     presented as one batch, consistent with step 1's rule for residuals. Default to
     single when unsure.
   - Multiple-choice: table format (Option | Description | Consequence), state
     **Recommended** option with reasoning
   - **Consequence preview (per option)**: every option MUST carry a one-line preview of
     what choosing it changes in the target artifact — sections or requirement IDs
     added/rewritten, obligations triggered — so the user chooses between outcomes, not
     labels. Where an option carries a known cost or semantic tension, name it in that
     preview; the active mode's integration rules (taxonomy reference) then bind that
     cost into the artifact rather than leaving it as a recorded answer only. When the
     questioning surface exposes a per-option preview/detail field, put the consequence
     there; otherwise make it the third table column.
   - Short-answer: state **Suggested** answer with reasoning
   - User replies: "yes"/"recommended" → use suggestion; otherwise validate answer
   - Stop when: all critical ambiguities resolved, user signals "done", or 5 questions
     reached

4. **Integration** — use the active mode's rules from the taxonomy reference.

5. **Validation** (after each write):
   - One bullet per accepted answer in `## Clarifications` > `### Session YYYY-MM-DD`
   - No lingering vague placeholders remain
   - Markdown structure valid; terminology consistent

6. **Final Write**: Save the target file.

### 4. Report

- Operating mode (A/B/C) and target file path
- Questions asked & answered count
- Sections touched
- Coverage summary table (Resolved / Deferred / Clear / Outstanding)

If no meaningful ambiguities were found at any point: report
`No critical ambiguities detected.` and suggest proceeding.

## Behavior Rules

- Never exceed 5 total questions
- Respect early termination signals ("stop", "done", "proceed")
- Do not modify upstream artifacts in later modes (B won't edit `requirements.md`;
  C won't edit `plan.md`)
- Fast-fail rules inside this workflow (the writability probe's immediate STOP, no
  silent degradation) are instances of the discipline owned by
  `.specify/shared/guidelines/fast-fail.md` — reference it, never restate it.

### Scope Revision Protocol (user re-scopes AFTER plan/tasks exist)

The rules above govern *clarification* runs. When the USER explicitly changes the
feature's scope or core concept after downstream artifacts exist, that is a **revision**,
not a clarification — follow this protocol instead of forcing new specs or re-running
scaffolding:

1. **Amend upstream in place**: update `requirements.md` first, recording the user
   directive verbatim under `## Clarifications` (dated session entry). Never re-run
   creation scripts — they overwrite history.
2. **Regenerate downstream by hand**: rewrite plan/data-model/contracts/quickstart/tasks
   to match; delete artifacts the revision obsoletes (use alias-proof `\rm -f`).
3. **Residual-reference sweep (exit gate)**: grep all spec artifacts for terms belonging
   to the dropped design; zero hits (outside "removed/dropped" annotations) before
   reporting completion.
4. **Re-validate**: re-run the spec quality checklist and update the Feature entry notes
   with the revision rationale.

## Boundaries

- **Unbounded interviewing is not this skill.** When the answer space is not bounded by
  the artifact (branching decisions, unanticipated question unlock), route to
  `/speckit.interview` — that is the escalation in §3, not a licence to exceed the cap.
- **Revision scaffolding is not this skill.** The Scope Revision Protocol amends
  artifacts in place; creating a fresh feature or regenerating artifacts via the
  creation commands belongs to `/speckit.requirements` and downstream commands.
- **Command-level wiring stays with `/speckit.clarify`.** The command frontmatter
  (`scripts:` slot), the User Input Protocol, and the wrap-up lifecycle (Artifact
  Commit, Feedback, Documentation, Handoffs, next-command suggestions) are owned by the
  command template, not absorbed here.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:clarify-artifact" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:clarify-artifact" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:clarify-artifact" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
