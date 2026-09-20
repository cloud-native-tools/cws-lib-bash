---
description: 识别特性产物中的欠指定区域，并将澄清答案写回对应阶段文件
---
<!-- AUTO-GENERATED from templates/commands/clarify.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions.

## Outline

Goal: Detect and reduce ambiguity or missing decision points in the current phase's primary artifact and record clarifications directly in that file.

### Phase 0: Phase Detection & Context Setup

1. Run `.specify/scripts/bash/check-prerequisites.sh --json --paths-only` from repo root once; parse JSON for `REPO_ROOT`, `BRANCH`, `REQUIREMENT_ID`, `REQUIREMENTS_DIR`, `FEATURE_SPEC`, `IMPL_PLAN`, `TASKS`.

2. **Determine current phase** by file existence in REQUIREMENTS_DIR:

   | Phase | Trigger | Target File | Handoff |
   |-------|---------|-------------|---------|
   | A: Post-Requirements | `plan.md` NOT exist | `requirements.md` | `/speckit.plan` |
   | B: Post-Plan | `plan.md` exists, `tasks.md` NOT exist | `plan.md` | `/speckit.tasks` |
   | C: Post-Tasks | `tasks.md` exists | `tasks.md` | `/speckit.implement` |

   - If no `requirements.md` at all → abort, instruct `/speckit.requirements` first.
   - Log: `**Mode: [A/B/C] — clarifying [target]**`

   **Mode override**: when `$ARGUMENTS` explicitly names an upstream artifact (e.g. "re-clarify the requirements" while `plan.md` already exists), clarify THAT artifact instead of the phase-detected one, cascade accepted answers into the derived artifacts, and log the deviation from the default mode. The default table applies only when the user gives no explicit target.

3. **Writability probe (fail fast)**: before generating any questions, verify the target file is writable (touch-test or write-bit stat on the target and its directory). If unwritable (e.g. root-owned spec dir), STOP immediately with an actionable message (owning path + fix command such as `sudo chown -R $USER <dir>`) — do NOT run the question loop first and lose the integration work at the final write. If the user chooses to proceed read-only, batch all integrations into ONE write attempt at the end instead of the per-answer saves the mode's integration rules call for.

4. **Load common context (summary-first — see `.specify/shared/guidelines/token-efficiency.md`)**: project `.specify/memory/features.md` via `grep -E '^\| [0-9]{3}'` index rows; read `research.md` (if exists); pull `.specify/memory/constitution.md`, `README.md`, and `docs/` content only as targeted excerpts when a candidate question actually requires them — never wholesale.

5. **Load mode-specific context** (see taxonomy reference).

### Taxonomy & Coverage Scan

For the active mode's detailed taxonomy categories and integration rules, load: `.specify/shared/constants/clarify-taxonomy.md`

Each mode has its own taxonomy. For each category, mark status (Clear / Partial / Missing). Add candidate questions for Partial/Missing categories unless clarification would not materially change implementation.

**Same-author detection delegation**: this scan usually runs on an artifact the same agent just wrote — the ordinary case is a `requirements → clarify` chain without a break — so the scan inherits the author's own reading, and an ambiguity unnoticed while writing is unlikely to be noticed while scanning. When that condition holds, delegate the coverage scan to fresh-context read-only subagents. Apply the canonical gate in `.specify/shared/workflow/objective-analysis-gate.md` (single source of truth; do not restate its rules here). This command has no severity tiers, so the local analogue of the propagation-surface cap is the materiality filter above: do not raise a question whose answer changes no **downstream artifact**.

If spec contains `Feature ID: Need clarification` or `Feature Name: Need clarification`, treat Feature Linkage as high-priority.

### Question Generation & Interactive Loop

This loop is **clarification (澄清), not interviewing (采访)** — a distinction worth keeping straight because both ask the user questions. Here the answer space is **already bounded** by the target artifact and the mode's taxonomy, so questions are **closed**: an options table plus a **Recommended** pick that the user ratifies or corrects. That is why this command may propose answers at all.

From `.specify/shared/patterns/interview-pattern.md` it borrows only the **context discipline** (every question states why it arises and what the answer will change) and the **fact-vs-decision split** (never ask the user for anything the repo can answer). It deliberately does **not** adopt that pattern's open-question rule — presenting options is correct when the possibilities really are known.

The **no-jargon half** of that borrowing is not restated here either: which terms may stand unexplained, which internal forms must never reach the user, what each question must carry for a reader who opens it alone, and how the option table's consequence previews are worded are all defined once in `.specify/shared/guidelines/user-facing-comprehension.md` (this command covers surface class ⑤); its condition sets MUST NOT be copied into this template.

**Escalation**: when the coverage scan shows the answer space is not actually bounded — the decisions *branch*, answers keep unlocking questions nobody anticipated, or the cap is reached with critical ambiguities still open — stop and recommend `/speckit.interview` on the same target artifact (open questions, unbounded rounds, durable ledger). Do not silently exceed the cap, do not fabricate the remainder, and do not force an options table onto a decision whose options you are guessing.

1. **Integrate user-provided decisions first**: when `$ARGUMENTS` contains explicit decisions (not open questions — e.g. a naming choice, a chosen option), integrate them into the target artifact BEFORE generating the question queue; the queue then covers only residual ambiguities. When residuals are few and independent, group them into one prompt instead of a per-question loop.

2. **Generate prioritized queue** (max 5 questions internally). Constraints:
   - Filter via Research: Skip questions answered by `research.md`
   - Maximum 10 total across session
   - Each must be answerable with multiple-choice (2–5 options) OR ≤5-word short answer
   - Only include questions whose answers materially impact downstream artifacts
   - Balance category coverage; favor high-impact unresolved categories

3. **Questioning loop** — order-dependent questions singly; mutually independent ones MAY batch:
   - **Batching rule**: ask a question alone when its framing depends on an earlier answer (the later options change with the earlier choice); when questions are mutually independent — neither answer alters the other's option set — they MAY be presented as one batch, consistent with step 1's rule for residuals. Default to single when unsure.
   - Multiple-choice: table format (Option | Description | Consequence), state **Recommended** option with reasoning
   - **Consequence preview (per option)**: every option MUST carry a one-line preview of what choosing it changes in the target artifact — sections or requirement IDs added/rewritten, obligations triggered — so the user chooses between outcomes, not labels. Where an option carries a known cost or semantic tension, name it in that preview; the active mode's integration rules (taxonomy reference) then bind that cost into the artifact rather than leaving it as a recorded answer only. When the questioning surface exposes a per-option preview/detail field, put the consequence there; otherwise make it the third table column.
   - Short-answer: state **Suggested** answer with reasoning
   - User replies: "yes"/"recommended" → use suggestion; otherwise validate answer
   - Stop when: all critical ambiguities resolved, user signals "done", or 5 questions reached

4. **Integration** — use the active mode's rules from the taxonomy reference.

5. **Validation** (after each write):
   - One bullet per accepted answer in `## Clarifications` > `### Session YYYY-MM-DD`
   - No lingering vague placeholders remain
   - Markdown structure valid; terminology consistent

6. **Final Write**: Save the target file.

### Report

- Operating mode (A/B/C) and target file path
- Questions asked & answered count
- Sections touched
- Coverage summary table (Resolved / Deferred / Clear / Outstanding)
- Suggested next command: A → `/speckit.plan`, B → `/speckit.tasks`, C → `/speckit.implement`

## Behavior Rules

- If no meaningful ambiguities: "No critical ambiguities detected." → suggest proceeding
- Never exceed 5 total questions
- Respect early termination signals ("stop", "done", "proceed")
- Do not modify upstream artifacts in later modes (B won't edit requirements.md; C won't edit plan.md)

### Scope Revision Protocol (user re-scopes AFTER plan/tasks exist)

The rule above governs *clarification* runs. When the USER explicitly changes the feature's scope or core concept after downstream artifacts exist, that is a **revision**, not a clarification — follow this protocol instead of forcing new specs or re-running scaffolding:

1. **Amend upstream in place**: update requirements.md first, recording the user directive verbatim under `## Clarifications` (dated session entry). Never re-run creation scripts — they overwrite history.
2. **Regenerate downstream by hand**: rewrite plan/data-model/contracts/quickstart/tasks to match; delete artifacts the revision obsoletes (use alias-proof `\rm -f`).
3. **Residual-reference sweep (exit gate)**: grep all spec artifacts for terms belonging to the dropped design; zero hits (outside "removed/dropped" annotations) before reporting completion.
4. **Re-validate**: re-run the spec quality checklist and update the Feature entry notes with the revision rationale.

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.clarify" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Artifact Commit

At wrap-up, **before** the Feedback and Documentation steps, commit the artifact this command produced — and only that artifact, staged by explicit path. Follow the canonical convention in `.specify/shared/workflow/artifact-commit-step.md`: run the deletion-surface audit first, use a single-line message per `.specify/templates/commit-template.md`, never `git add -A`, and never fold another command's uncommitted artifacts into this commit (report that as an upstream deviation instead). A read-only run that produced no artifact skips this step and says so in one line rather than creating an empty commit. Committing here does not advance the feature's lifecycle status and does not push.

## Handoffs

**Before**: At minimum `/speckit.requirements` first. Phase auto-detected from file existence.

**After**: Mode A → `/speckit.plan`. Mode B → `/speckit.tasks`. Mode C → `/speckit.implement`.