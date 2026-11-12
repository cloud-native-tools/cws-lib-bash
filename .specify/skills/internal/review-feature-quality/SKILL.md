---
name: review-feature-quality
description: Own the method of the two middle segments of `/speckit.review` — the artifact segment (Segment A) judges a slice's expected artifact set for completeness, internal consistency, traceability from requirement to task to success criterion to evidence, dependency and premise ownership, and acceptance honesty; the implementation segment (Segment B) judges the same slice's `base..head` delta against `requirements.md` and `tasks.md` for correctness, scope and regression and records the smoke command, exit code and evidence path. The expected-set denominator, the finding field set with its required `line`, the dimension lists and the `checked / expected` coverage-line shape live here, with the per-dimension detail in `references/artifact-and-implementation-review.md`. The skill owns no severity family: it emits the `P0`/`P1`/`P2` tokens owned by `review-sdd-process` and defines no level, and the composition that places it second and third is owned by `.specify/shared/workflow/acceptance-hardening.md` § Review Composition. Use this when the user mentions ["artifact review", "产物审查", "产物评审", "implementation review", "实现审查", "实现评审", "review artifacts", "review implementation", "expected artifact set", "期望产物集", "traceability review", "可追溯性审查", "/speckit.review"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/review-feature-quality/SKILL.md>"
---

# review-feature-quality

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.


## Goal

Carry the **method** of `/speckit.review`'s two middle segments — the artifact segment and the
implementation segment — and nothing else. The composition that places them second and third in one
fixed order, the boundary sentences between the four segments, the expected-artifact derivation rule
and the Acceptance Reality Check's clause are **not** stated here: they are owned by
`.specify/shared/workflow/acceptance-hardening.md` § Review Composition, which this skill cites and never
restates.

This skill is the methodology carrier for those two segments, so the dimension sets below are the
**only** statement of what each segment looks at. Per-dimension detail — the checklists, the coverage
line shape and the smoke record's fields — lives in
`references/artifact-and-implementation-review.md` and is reached from here by path.

## Input Contract

- **When**: inside a `/speckit.review` run, after the process segment has finished and before the code
  segment starts. Both segments read the same slice; neither needs the other's conclusion.
- **Subject**: for Segment A, the slice's stage artifacts under `REQUIREMENTS_DIR`; for Segment B, this
  slice's committed `base..head` delta. The two subjects are disjoint — an artifact is not a diff and a
  diff is not an artifact.
- **Arguments**: none of this skill's own. `$ARGUMENTS` guides review focus and is transported by the
  command; it selects, reorders and skips no segment.
- **Composition**: `.specify/shared/workflow/acceptance-hardening.md` § Review Composition. This skill states no
  order of its own.

## Segment A — Artifact Review

The second segment of the fixed order. It answers one question — does the slice's artifact set meet
what its stage requires? — and no other.

- **Skill**: `.specify/skills/internal/review-feature-quality/SKILL.md` § Segment A — Artifact Review
  (this section), with the per-dimension detail in
  `references/artifact-and-implementation-review.md` § A.
- **Judgment object**: the slice's **stage artifacts**, taken as the **expected set** its stage rules
  and its `plan.md` § Project Structure require. For a slice closing the standard spec stage that
  derivation's product is `requirements.md`, `plan.md`, `tasks.md`, `contracts/`, `data-model.md`,
  `quickstart.md` and `verification.md`; a slice whose stage rules add or drop a member has a
  different product, which is exactly why the set is derived per slice instead of being a constant
  list.
- **Severity vocabulary**: `P0`/`P1`/`P2` — the family owned by
  `.specify/skills/internal/review-sdd-process/SKILL.md` § Severity Vocabulary. This segment emits those three
  tokens as a consumer and defines no level of its own; the meanings are written once, in the report
  template's severity table, and are not repeated here.
- **Inputs**: the artifact set under `REQUIREMENTS_DIR`, the slice's `tasks.md` row set and its
  `verification.md` status rows, the feature detail's claimed status, and the pointer targets the
  plan/tasks tables name as evidence.
- **Outputs**: the report slot `### 2.2 Artifact Review Segment` of `review.md` — the coverage line,
  one verdict row per expected member, and the findings — plus this segment's contribution to the
  run's console conclusion. The slot's **shape** is owned by `.specify/templates/review-template.md`; this
  section owns its content.

### The denominator is the expected set

The denominator is the **expected set**, never the artifacts that happen to be on disk. The
derivation rule — the union of what the slice's stage rules require and what its `plan.md`
§ Project Structure lists — has exactly one statement: `.specify/shared/workflow/acceptance-hardening.md`
§ Review Composition. A second statement of it, this file included, is a second definition and is a
defect. What this section states is only the consequence a run has to enact:

- the coverage line is written `checked / expected`, and the members it counts as missing are named
  next to it;
- a required artifact that is missing from disk is a finding and counts as uncovered — both, not
  either. A member reported but left out of the denominator under-reports the gap; a member counted
  but left unnamed tells a reader a number moved without saying what is absent;
- "not present" can therefore never render as full coverage.

### The five dimensions

The dimension set is fixed and complete: a segment that judged fewer of them would answer a narrower
question than the one it owes.

1. **Completeness** — every member of the expected set exists, and each existing member carries the
   sections its own template requires.
2. **Internal consistency** — no two artifacts state the same fact differently. A threshold, a count,
   an enumeration, a path or a status literal appears with one spelling in one place and every other
   place points at it.
3. **Traceability** — every requirement reaches at least one task row, every task row reaches a
   success criterion or an evidence artifact, and every success criterion reaches the evidence that
   moves it. A link whose far end has no target is the finding; a criterion whose only support is its
   own restatement is a broken link too.
4. **Dependency and premise ownership** — a dependency or premise a row inherits names its owner, its
   carrier and its status, and a row that borrows a fact records where that fact is stated instead of
   restating it.
5. **Acceptance honesty** — a status claim, a coverage number and a red-first record say what the
   evidence supports and no more. A criterion reported as passing without the measurement that
   produced that reading is a `P0` by construction, and so is a red-first claim with no recorded red
   run.

### The finding form

Every finding carries three locating fields:

- **severity** — one token of the family cited above;
- **artifact path** — the member of the expected set the finding is about, repo-relative;
- **line** — the line number in that artifact.

`line` is **required whenever the artifact is line-addressable**, and a markdown artifact is: so is a
row-shaped artifact with a computable row number. An omission MUST name why in the finding itself,
because a reader cannot tell "this defect has no line" from "the line was not recorded". The field set
has no conditional member and no second escape: a finding that drops the line on a line-addressable
artifact without a stated reason is malformed, not terse.

## Segment B — Implementation Review

The third segment of the fixed order. It answers one question — does this slice's delta do what
`requirements.md` and `tasks.md` say? — and no other.

- **Skill**: `.specify/skills/internal/review-feature-quality/SKILL.md` § Segment B — Implementation
  Review (this section), with the per-dimension detail in
  `references/artifact-and-implementation-review.md` § B.
- **Judgment object**: this slice's implementation as the range `base..head` — the committed delta
  judged against `requirements.md` and `tasks.md` for correctness, scope and regression. `base` and
  `head` resolution has exactly one route, `.specify/skills/internal/code-review/scripts/git-delta-review.sh`,
  whose `base` step owns the ordered resolution tiers, the closed trunk order and the run-start-fixed
  head. This segment implements no second base resolution and invents no branch-name default.
- **Severity vocabulary**: `P0`/`P1`/`P2` — the same family, from the same owner
  (`.specify/skills/internal/review-sdd-process/SKILL.md` § Severity Vocabulary). This segment defines no level
  either, and the two families present in a composed run never map onto each other.
- **Inputs**: the resolved `base..head` range, `requirements.md`, `tasks.md`, the feature's smoke
  record, and the closure checker's `final_path` record when the run has one.
- **Outputs**: the report slot `### 2.3 Implementation Review Segment` of `review.md` — the base/head
  pair, the smoke triple, the scope-and-regression verdict and the findings — plus this segment's
  contribution to the run's console conclusion.

### The three judgments

1. **Correctness** — the delta does what the requirements say, and the acceptance evidence it claims
   is the evidence this delta produced.
2. **Scope** — the delta contains no work that no requirement and no task row asks for, and no task
   row it claims is closed is closed by a fragment of itself.
3. **Regression** — nothing the feature already delivered stops working. A behaviour an earlier
   criterion measured is re-measured rather than assumed unchanged.

### The smoke record

The segment runs or verifies the feature's smoke test and records three things, all three: the
**command** verbatim, the **exit code** it returned, and the **evidence path** holding its output. A
record missing any of the three is a claim that the smoke was run, not a verdict over it. A smoke that
cannot be made deterministic on a local fixture is a finding against the feature — "needs a real
cluster" or "needs real network" is not an exemption for this segment.

### The `final_path` record is quoted, never judged

The closure checker's `final_path` record is the Acceptance Reality Check's input, and the hard
condition on it stays the implement gate's. This segment at most quotes it: it re-counts no bucket,
re-derives no total and never overrules the checker. An implementation that satisfies every
requirement still does not move that record, and the record does not move this segment's verdict.

## Boundaries

- **One segment, one question.** Segment A judges the artifacts, Segment B judges the delta. Neither
  answers the other's question, and the code segment answers neither of them: the code segment's
  object is the committed code delta under its own six-level vocabulary, so a clean code record says
  nothing about whether the artifacts are complete or whether the requirement was delivered.
- **The composition is not stated here.** What `/speckit.review` runs, in what order, and what each
  part may answer belong to `.specify/shared/workflow/acceptance-hardening.md` § Review Composition. This skill
  carries two segments' method and cites that section; it re-derives no order and no boundary
  sentence.
- **No severity family is owned here.** `P0`/`P1`/`P2` belongs to
  `.specify/skills/internal/review-sdd-process/SKILL.md`; the six-level code family belongs to
  `.specify/skills/internal/code-review/SKILL.md`. This skill is a consumer of the first, a stranger to the
  second, and it maps, converts, weights and scores neither.
- **The process skill stays single.** `review-sdd-process` keeps exactly one judgment object. This
  skill adds none to that body, does not live under its `references/`, and is not reached through it.
- **The Acceptance Reality Check is not a segment of this skill.** It runs one deterministic program
  and delegates nothing; no dimension set, no severity token and no finding form of this skill applies
  to it.
- **Remediation is not this skill.** It produces verdicts and findings; repairing an artifact or the
  delta is a follow-up run's work.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:review-feature-quality" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:review-feature-quality" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:review-feature-quality" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
