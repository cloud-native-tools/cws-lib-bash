---
description: 批判性评审当前特性的 SDD 过程，出具改进导向报告
---
<!-- AUTO-GENERATED from templates/commands/review.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters guiding review focus.

## Composition — two segments, one fixed order

`/speckit.review` runs exactly two segments in a fixed order. There is no parallel mode, no single merged report, and no parameter — `$ARGUMENTS` included — that selects one segment over the other: the order is a property of this template, so neither delegated skill may reverse or skip the other.

The process segment runs on every invocation. No execution class or expression class exempts it, no `$ARGUMENTS` value exempts it, an absent code delta does not exempt it, and no earlier segment's outcome exempts it.

The two conclusions are never merged: not into one severity system, not into one score, not through a mapping table or a conversion. Each segment's vocabulary belongs to its own skill, and this run stores no combined value anywhere.

## Delegation

Each segment is delegated to its existing skill by runtime path. This template orchestrates and points: it inlines neither skill's methodology — no process-review dimension list, no code-review dimension list, no severity definitions, no coverage-receipt field list.

### Segment 1 — process segment (`review-sdd-process`)

- **Skill**: `review-sdd-process` — runtime path `.specify/skills/internal/review-sdd-process/SKILL.md`.
- **Judgment object**: the SDD process that produced the feature — process and tooling quality, never the feature's business merits, never the code it produced. Judging the code is segment 2's work, not this one's.
- **Severity vocabulary**: `P0`/`P1`/`P2`, owned by the process skill; this template cites the family and defines none of its levels.
- **Inputs**: the feature's artifact chain under `REQUIREMENTS_DIR` (plus `FEATURE_ID`, `FEATURE_NAME`, `AVAILABLE_DOCS`), resolved by the frontmatter `scripts:` prerequisite run (`.specify/scripts/bash/check-prerequisites.sh --json --require-spec --include-spec --include-plan --include-tasks`) from repo root; `$ARGUMENTS` guide review focus (wired by `## User Input` above). Timing: run after `/speckit.implement` completes.
- **Outputs**: the review report written to `REQUIREMENTS_DIR/review.md` (review-template structure, self-contained) — and, if this segment aborts before writing it, the minimal report this command authors instead (see `## Failure propagation`). Plus the closing summary — `REQUIREMENTS_KEY`, feature name, commit SHA, report path, finding counts (by severity and by category), top 3 recommendations — which is a presentation, not a carrier (see `## Output and placement`).

### Segment 2 — code segment (`code-review`)

- **Skill**: `code-review` — runtime path `.specify/skills/internal/code-review/SKILL.md`.
- **Judgment object**: verifiable defects in this feature slice's committed code delta. The five-phase method, the per-file walk and the severity definitions all live in the skill body; this template owns only the order and the hand-off.
- **Severity vocabulary**: the skill's own levels, from `blocking` to `praise`. They are defined there and are never relabelled, weighted or converted here.
- **Inputs**: the resolved `base..head` range and the code-path verdict of the skill's deterministic script — see `## Review object` and `## Applicability triage`.
- **Outputs**: the code segment record `REQUIREMENTS_DIR/code-review.md`, written only when the triage value is `run`; plus this run's archive path when a previous record was rotated. The report's code subsection carries that record's verdict and paths, never its opinions (see `## Output and placement`).

**Client capture (optional fifth step).** When the triage value is `run` and the run's repository is judged a client project, the code segment's non-interactive path ends with a fifth deterministic step — `capture --review-file <record> --triage run [--unit <value>]` — which posts exactly one pointer-shaped entry to the client project's own feedback channel (record path, applicability value, six per-severity counts copied from `report --summary --format json`, run identifier, owning unit). This template accepts an optional `--client-unit custom:<owner>/<name>` argument and passes it through to that step: it disambiguates the owning client unit and adds no command surface of its own. A malformed value (anything not matching `custom:<owner>/<name>`) yields one named skip line naming the expected syntax, zero entries, and does not block or alter the review. The run's human-facing conclusion carries exactly one capture outcome line whose state token is drawn from the closed five-value set — `client-channel-armed` / `client-channel-unarmed` / `client-unit-ambiguous` / `no-capture-object` / `counts-unavailable` — visible together with the triage value; in a framework-hat repository capture does not run and the conclusion names the hat verdict as its basis instead, never one of the five tokens. The report's code subsection (`### 2.1`) gains no capture field: the disclosure is presentation, not a carrier.

## Review object

The code segment judges this feature slice's committed code delta, reviewed as the range `base..head`, which is recorded so any later reader can recompute it with `git diff base..head`. Base and head resolution belong to the skill's deterministic script — `.specify/skills/internal/code-review/scripts/git-delta-review.sh`, whose `base` step owns the ordered resolution tiers, the closed trunk order and the run-start-fixed head. The command passes a caller's explicit values through and invents no branch-name default of its own.

Uncommitted working-tree changes are not part of that object: when they exist the run discloses the unreviewed scope in both the report's code subsection and this run's record, and issues no pass conclusion over it.

## Applicability triage

Before the code segment starts, the command resolves its applicability to exactly one of three values, a closed set:

| Value | When it applies | What it obliges |
|-------|-----------------|-----------------|
| `run` | this feature has a committed code delta containing at least one code path | the code segment runs and the record is written |
| `not-applicable` | the feature produces no code deliverable, or has no committed code delta | a basis naming one of those two facts |
| `not-evaluated` | the environment or the base resolution prevents evaluation | a reason, with the reproducible command that failed |

There is no fourth state: an unspecified value, an empty value, or a silently dropped segment is a violation. A `pass` verdict can never be attached to a non-`run` triage.

What counts as a code path is not decided here. The predicate has exactly one owner — the skill's deterministic script `.specify/skills/internal/code-review/scripts/git-delta-review.sh`, whose closed default code-path set is overridden by an explicit `--code-paths`. This template cites that verdict and carries no second path list: two lists drift, and a drift turns one repository state into two different triage values.

An empty delta is triaged before the coverage receipt runs. When base and head point at the same commit and zero files changed, the triage is `not-applicable` with the basis "no committed code delta" before any receipt is produced — an empty changed set never reaches the receipt and is never reported as a clean review of nothing.

## Failure propagation

A process-segment abort or error does not suppress the code segment: the two judgment objects are independent, and the code segment's preconditions do not include the process segment's success. In that state:

- the process segment is recorded as `not-evaluated`, with its reason;
- both segment conclusions are presented independently, and the run is not presented as a completed review;
- if the abort happened before `review.md` was written, the command itself authors a minimal process report from `.specify/templates/review-template.md` carrying only the code-segment subsection (`### 2.1`) and the abort reason, so the verifiable carrier stays the single `review.md` and its author is the command rather than the process skill.

## Output and placement

**Two artifacts.** The process report stays at `REQUIREMENTS_DIR/review.md`, with the structure owned by `.specify/templates/review-template.md`; the code segment record is the separate file `REQUIREMENTS_DIR/code-review.md`. Neither file overwrites the other, and the two never share one severity summary table.

**Record existence follows the triage value.** Only `run` writes `code-review.md`. The values `not-applicable` and `not-evaluated` create no record file — not even an empty one — and their verdict and reason live in the report's code subsection.

**Rotation.** When a run finds an existing `code-review.md`, it first archives that file inside the same directory as `code-review-<YYYYMMDDTHHMMSSZ>.md` (UTC, second resolution) and then writes the new record. An existing archive path is never overwritten: two runs inside one second either wait for the next second or exit `2` with the reason. `code-review.md` therefore always denotes the latest run, and every earlier run survives as its own archive file. The report's code subsection records the path written this run and this run's archive path — `none` on a first run, the archive's actual path afterwards.

**Where the conclusions land.** Both segment conclusions appear on two verifiable carriers: the report's code subsection (`### 2.1`) and the bound feature detail's existing `## Latest Review` review-record entry. The record is not added to any downstream available-documents list (`AVAILABLE_DOCS`) and is not read as plan or tasks input; the feature side reaches it through that existing entry, with no new structured field and no second count copy. The closing summary (console and handoff output) MAY restate both conclusions, but it is a presentation, not an artifact: it is not a third verifiable carrier, it carries no content obligation of its own, and where it disagrees with the two carriers the carriers govern.

**Code finding form.** A code-segment finding keeps its existing locating form — severity plus file and optional line — inside `code-review.md`. It is never coined as a `REC-…` identifier and never registered in the register; that family stays with framework-targeted recommendations.

**Unchanged surfaces.** The frontmatter `scripts:` prerequisite block, the compiled `## Wrap-up` face and `## Handoffs` are unchanged by this composition. `## Handoffs` keeps its recommendation-registration obligation in its current form.

## Status Transition — the gate this run judges

This run judges exactly one status transition, `Implemented → Ready for Review`, and states no criterion of its own. The criteria — three conjunctive conditions, the third an existence test over the current `code-review.md` — are owned by `.specify/templates/feature-details-template.md` § Canonical Status State Machine. This template cites that section and carries no second wording of it.

**One checkpoint.** The transition is judged once, after the process segment and the code segment have both finished and both artifacts are on disk (`review.md`, and `code-review.md` when the triage value is `run`). Because the code segment's conclusion is one of the conditions' inputs, the status MUST NOT flip before that segment completes; an early flip is a violation even when the process segment already passed.

**A waiver is an explicit user ruling, or there is none.** A user-authored waiver artifact, or the user's own ruling in the session, is a waiver; a driver's or an orchestrator's confirmation is an agent's confirmation and is never a user ruling, and the absence of objection is not a waiver either. The command never downgrades, merges or excludes a `blocking` entry in this judgement, and it never infers a waiver.

**The unattended disposition is halt-and-report.** Without an explicit user ruling the command stops before the transition, reports the block, and records `blocking-unresolved` as the named refusal literal in the report's code subsection (`### 2.1`) and in the conclusion it returns. A refusal names the condition that failed — not merely that the transition was refused — leaves the status at `Implemented`, and never presents the run as a completed review.

**A non-conclusion is disclosed, not blocking.** A code segment recorded `not-applicable` or `not-evaluated` does not block the transition; the verdict and its reason land on the two verifiable carriers named in `## Output and placement`. The closing summary may restate them and carries no obligation of its own.

**`important` items do not block, and each one is answered.** An `important` item never blocks the transition, and the run requires each one to be answered; the remaining severity levels never block it. The two vocabularies are never merged (see `## Composition`): no numeric conversion, no mapping matrix and no unified score exists between them, and nothing in this run stores one.

## Feedback boundary — friction only, three units, one unchanged closing set

**Only framework friction may be posted.** A feedback entry records friction of the framework itself — a missing renderer, an ambiguous base, an insufficient non-interactive path, a receipt gap. A code defect found by the code segment MUST NOT be posted as a feedback entry: it stays in `code-review.md`, where its severity, file and line are meaningful, and this run posts nothing about it. The classification duty is written on two surfaces — this template and `.specify/skills/internal/code-review/SKILL.md` — so posting a code defect as feedback is a detectable violation of a written rule rather than a matter of taste. Entries land in the project-local store `.specify/memory/feedback/`; this composition adds no other destination.

**Three units, three records.** The unit census of one run is three, not two: this command (`/speckit.review`), the delegated process skill (`skill:review-sdd-process`) and the delegated code skill (`skill:code-review`). All three share the run id and differ in `unit_id` — the key the feedback engine already uses — so none dedups, merges or truncates another. Each unit completes its own closing record: this command MUST NOT suppress either skill's wrap-up, MUST NOT write a skill's run determination on its behalf, and MUST NOT back-fill one after the fact. The command side adds its own record and leaves both skills' records intact.

**The closing step set is unchanged.** The six steps of the compiled `## Wrap-up` face below — run determination, execution quantification, feedback record, threshold notice, token reflection, docs-sync evaluation — stay exactly as published. This composition adds no closing step, no side channel and no second record type; every rule it states lives here, outside the generated face, and the face itself is not edited.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "/speckit.review" --unit-type command --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "/speckit.review" --unit-type command`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "/speckit.review" --unit-type command --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Docs Sync Eval — `.specify/shared/workflow/docs-step.md` § "Evaluation procedure (the embedded step points here)"

## Handoffs

**Before**: Run after `/speckit.implement` for complete artifact chain.

**After**: Register every `REC-…` id coined in the report in `.specify/memory/register.md` **in the same commit** as the report, using the register's existing pointer-row form (id → one-line meaning → report anchor → status). The register owns the row form; this command owns the registration obligation. Then apply improvements to the spec-kit sources (`.specify/templates/`, `commands/`, `.specify/scripts/`); optionally iterate requirements/plan.