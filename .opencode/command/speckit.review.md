<!-- AUTO-GENERATED from templates/commands/review.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
> **Concurrency obligation（执行义务，按指针抵达）**: this command is an execution body — consider concurrency first, default to it when the class and capability allow, and, when serial, name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This template restates none of their rules.

## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters guiding review focus.

## Composition — four segments in one fixed order, plus one check that is not a segment

`/speckit.review` runs exactly four segments in a fixed order — process → artifact → implementation → code — and then one deterministic check, the Acceptance Reality Check, which is not a segment. There is no parallel mode, no single merged report, and no parameter — `$ARGUMENTS` included — that selects one segment over another: the order is a property of this template, so no delegated skill may reverse or skip another.

What each part's content is — every segment's judgment object and boundary sentence, the artifact segment's denominator rule, the check's clause and the running unit census — is owned by `.specify/shared/workflow/acceptance-hardening.md` § Review Composition. This section declares the four headings and the five per-segment field names below, and restates none of that content.

Every segment runs on every invocation. No execution class or expression class exempts the process segment, no `$ARGUMENTS` value exempts it, an absent code delta does not exempt it, and no earlier segment's outcome exempts it. The same holds for the artifact and the implementation segments: an empty artifact set or an empty delta changes a segment's verdict, never its presence.

The four conclusions are never merged: not into one severity system, not into one score, not through a mapping table or a conversion. Each segment's vocabulary belongs to its own skill, and this run stores no combined value anywhere.

## Delegation

Each segment is delegated to its existing skill by runtime path. This template orchestrates and points: it inlines no skill's methodology — no dimension list, no severity definition, no coverage-receipt field list, no finding-form field list.

All four segments are described by the same five fields, in this order: `Skill`, `Judgment object`, `Severity vocabulary`, `Inputs`, `Outputs`.

### Segment 1 — process segment (`review-sdd-process`)

- **Skill**: `review-sdd-process` — runtime path `.specify/skills/internal/review-sdd-process/SKILL.md`.
- **Judgment object**: the SDD process that produced the feature — process and tooling quality, never the feature's business merits, never the artifacts' content, never the code it produced. Judging the artifacts is segment 2's work and judging the code is segment 4's.
- **Severity vocabulary**: `P0`/`P1`/`P2`, owned by the process skill; this template cites the family and defines none of its levels.
- **Inputs**: the feature's artifact chain under `REQUIREMENTS_DIR` (plus `FEATURE_ID`, `FEATURE_NAME`, `AVAILABLE_DOCS`), resolved by the frontmatter `scripts:` prerequisite run (`.specify/scripts/bash/check-prerequisites.sh --json --require-spec --include-spec --include-plan --include-tasks`) from repo root; `$ARGUMENTS` guide review focus (wired by `## User Input` above). Timing: run after `/speckit.implement` completes.
- **Outputs**: the review report written to `REQUIREMENTS_DIR/review.md` (review-template structure, self-contained) — and, if this segment aborts before writing it, the minimal report this command authors instead (see `## Failure propagation`). Plus the closing summary — `REQUIREMENTS_KEY`, feature name, commit SHA, report path, finding counts (by severity and by category), top 3 recommendations — which is a presentation, not a carrier (see `## Output and placement`).

### Segment 2 — artifact segment (`review-feature-quality` § Segment A)

- **Skill**: `review-feature-quality` — runtime path `.specify/skills/internal/review-feature-quality/SKILL.md` § Segment A — Artifact Review.
- **Judgment object**: the slice's stage artifacts, taken as the **expected** set its stage rules and its `plan.md` § Project Structure require — for a slice closing the standard spec stage that product is `requirements.md`, `plan.md`, `tasks.md`, `contracts/`, `data-model.md`, `quickstart.md` and `verification.md` — judged for completeness, internal consistency, traceability (requirement → task → success criterion → evidence), dependency and premise ownership, and acceptance honesty.
- **Severity vocabulary**: `P0`/`P1`/`P2`, the same family, owned by `.specify/skills/internal/review-sdd-process/SKILL.md` § Severity Vocabulary; this segment emits the three tokens and defines no level of its own.
- **Inputs**: the artifact set under `REQUIREMENTS_DIR`, the `tasks.md` row set, the `verification.md` status rows and the bound feature detail's claimed status, all resolved for this run by `.specify/scripts/bash/check-prerequisites.sh --json --require-spec --include-spec --include-plan --include-tasks`.
- **Outputs**: the report slot `### 2.2 Artifact Review Segment` of `review.md` — the coverage line, one verdict row per expected member and the findings — plus this segment's contribution to the run's conclusion.

The denominator is the **expected** set, never the artifacts that happen to exist this time. The derivation rule is stated once, at `.specify/shared/workflow/acceptance-hardening.md` § Review Composition, and a restatement of it here would be a second definition, which is a defect. The coverage line is written `checked / expected` with the missing members named beside it. A required artifact that is missing from disk is a finding and it counts as uncovered — both, because a member reported but left out of the denominator under-reports the gap. The dimension set and the finding form, including the rule that a finding carries its `line`, belong to this segment's method at `.specify/skills/internal/review-feature-quality/SKILL.md` § Segment A.

### Segment 3 — implementation segment (`review-feature-quality` § Segment B)

- **Skill**: `review-feature-quality` — runtime path `.specify/skills/internal/review-feature-quality/SKILL.md` § Segment B — Implementation Review.
- **Judgment object**: this slice's implementation as the range `base..head` — the committed delta judged against `requirements.md` and `tasks.md` for correctness, scope and regression. `base` and `head` resolution has exactly one route, `.specify/skills/internal/code-review/scripts/git-delta-review.sh`, whose `base` step owns the ordered resolution tiers and the closed trunk order; this segment implements no second base resolution and invents no branch-name default of its own.
- **Severity vocabulary**: `P0`/`P1`/`P2`, the same family, from the same owner `.specify/skills/internal/review-sdd-process/SKILL.md` § Severity Vocabulary; the six-level code family is a different family, and no conversion, mapping table or unified score exists between the two.
- **Inputs**: the resolved `base..head` range, `requirements.md`, `tasks.md`, the feature's smoke record and the bound feature detail's claimed status.
- **Outputs**: the report slot `### 2.3 Implementation Review Segment` of `review.md` — the base/head pair, the smoke triple (the smoke command verbatim, its exit code, and the evidence path holding the output), the scope-and-regression verdict and the findings — plus this segment's contribution to the run's conclusion.

The segment runs or verifies the feature's smoke test and records all three of the command, the exit code and the evidence path; two of three is a claim that the smoke ran, not a verdict over it. Its conclusion is its own: it is not answered from the code segment's record and not from the process segment's report. That boundary, and the no-substitution rule that carries it, are owned by `.specify/shared/workflow/acceptance-hardening.md` § Review Composition; this template cites them rather than restating them.

### Segment 4 — code segment (`code-review`)

- **Skill**: `code-review` — runtime path `.specify/skills/internal/code-review/SKILL.md`.
- **Judgment object**: verifiable defects in this feature slice's committed code delta. The five-phase method, the per-file walk and the severity definitions all live in the skill body; this template owns only the order and the hand-off. This is the fourth and last segment of the fixed order.
- **Severity vocabulary**: the skill's own levels, from `blocking` to `praise`. They are defined there and are never relabelled, weighted or converted here.
- **Inputs**: the resolved `base..head` range and the code-path verdict of the skill's deterministic script — see `## Review object` and `## Applicability triage`.
- **Outputs**: the code segment record `REQUIREMENTS_DIR/code-review.md`, written only when the triage value is `run`, and it MUST carry the coverage receipt block produced by `receipt --review-file <record>`; a missing receipt block is an input error, never a prose-filled count. Plus this run's archive path when a previous record was rotated. The report's code subsection carries that record's verdict and paths, never its opinions (see `## Output and placement`).

**Client capture (optional fifth step).** When the triage value is `run` and the run's repository is judged a client project, the code segment's non-interactive path ends with a fifth deterministic step — `capture --review-file <record> --triage run [--unit <value>]` — which posts exactly one pointer-shaped entry to the client project's own feedback channel (record path, applicability value, six per-severity counts copied from `report --summary --format json`, run identifier, owning unit). This template accepts an optional `--client-unit custom:<owner>/<name>` argument and passes it through to that step: it disambiguates the owning client unit and adds no command surface of its own. A malformed value (anything not matching `custom:<owner>/<name>`) yields one named skip line naming the expected syntax, zero entries, and does not block or alter the review. The run's human-facing conclusion carries exactly one capture outcome line whose state token is drawn from the closed five-value set — `client-channel-armed` / `client-channel-unarmed` / `client-unit-ambiguous` / `no-capture-object` / `counts-unavailable` — visible together with the triage value; in a framework-hat repository capture does not run and the conclusion names the hat verdict as its basis instead, never one of the five tokens. The report's code subsection (`### 2.1`) gains no capture field: the disclosure is presentation, not a carrier.

## The Acceptance Reality Check

The Acceptance Reality Check is **not a fifth segment** and is **not delegated**: it runs one deterministic program and reports that program's verdict, so there is no judgement for a skill to own. It carries no `Skill` field, no severity vocabulary and no judgment object of its own, and no model judgement may substitute for it.

Run it from repo root against the bound feature's spec directory:

```bash
python3 .specify/scripts/python/closure-acceptance-check.py --spec-dir <spec-dir> --json
```

Copy the `final_path` record it returns into the carrier slot `### 2.4 Acceptance Reality Check` of `review.md`, verbatim and in full, all seven keys on one line: pass [ARC_PASS] · blocked [ARC_BLOCKED] · deferred [ARC_DEFERRED] · partial [ARC_PARTIAL] · fail [ARC_FAIL] · unknown [ARC_UNKNOWN] · total [ARC_TOTAL]. The record is copied and never recomputed — this template re-counts no bucket from `verification.md`, narrows the record to no summary, and re-derives no part of it.

The key set just enumerated and the checker's two verdict values are machine facts with a single owner: `.specify/shared/declarations/facts/arc-verdict-mapping.yaml#/statement`. The enumeration above is the copy slot this template renders — written out because a slot cannot exist without its name — and it is not a second owner of the set.

Then compare the copied record against the feature's **claimed** status. The checker's verdict is a closed two-value set — `accept` and `block` — and `block` is a **non-pass**: it refuses the transition on its own, whatever the claim reads, and it is never carried beside an `accept` as a caveat. Two conditions refuse the transition and either one alone suffices: the verdict is `block`, or the claim is `Implemented` or `Ready for Review` while the record's `pass` bucket reads zero — in the second case the check emits the fixed item `F-ACCEPTANCE` at `P0`. The refusal names the condition that failed — the checker's own named reason codes when the verdict is `block` — not merely that the transition was refused, and it leaves the claimed status unchanged: `Implemented` stays `Implemented` and `Ready for Review` stays `Ready for Review`, because a refusal is not a downgrade. A user waiver of a transition condition does not lift this refusal — it is recorded as residual risk in `review.md`, and the item still fires.

## Review object

The code segment judges this feature slice's committed code delta, reviewed as the range `base..head`, which is recorded so any later reader can recompute it with `git diff base..head`. Base and head resolution belong to the skill's deterministic script — `.specify/skills/internal/code-review/scripts/git-delta-review.sh`, whose `base` step owns the ordered resolution tiers, the closed trunk order and the run-start-fixed head. The command passes a caller's explicit values through and invents no branch-name default of its own. This section owns the range's **resolution** only: the implementation segment judges the same range against `requirements.md` and `tasks.md`, and each of the two reads its own subject on it.

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

An empty delta is triaged before the coverage receipt runs. When base and head point at the same commit and zero files changed, the triage is `not-applicable` with the basis "no committed code delta" before any receipt is produced — an empty changed set never reaches the receipt and is never reported as a clean review of nothing. The artifact and implementation segments are untouched by this triage value: they judge their own subjects, and one segment's applicability settles nothing about another's.

## Failure propagation

A process-segment abort or error does not suppress the code segment, the implementation segment or the artifact segment: the four judgment objects are independent, and no segment's preconditions include another's success. In that state:

- the process segment is recorded as `not-evaluated`, with its reason;
- every segment's conclusion is presented independently, and the run is not presented as a completed review;
- if the abort happened before `review.md` was written, the command itself authors a minimal process report from `.specify/templates/review-template.md` carrying only the code-segment subsection (`### 2.1`) and the abort reason, so the verifiable carrier stays the single `review.md` and its author is the command rather than the process skill.

## Output and placement

**Two artifacts.** The process report stays at `REQUIREMENTS_DIR/review.md`, with the structure owned by `.specify/templates/review-template.md`; the code segment record is the separate file `REQUIREMENTS_DIR/code-review.md`. Neither file overwrites the other, and the two never share one severity summary table. The artifact, implementation and Acceptance Reality Check verdicts live in `review.md`'s slots `### 2.2`, `### 2.3` and `### 2.4`: they add no third file and no second carrier.

**Record existence follows the triage value.** Only `run` writes `code-review.md`. The values `not-applicable` and `not-evaluated` create no record file — not even an empty one — and their verdict and reason live in the report's code subsection.

**Rotation.** `review.md` and `code-review.md` both follow the rotation rule owned by `.specify/shared/workflow/acceptance-hardening.md` § Review Composition § Records and rotation: the existing record is archived as `<record>-<slice>.md` before the new one is written, and the report's code subsection records this run's record path and archive path (`none` on a first run).

**Where the conclusions land.** Both segment conclusions appear on two verifiable carriers: the report's code subsection (`### 2.1`) and the bound feature detail's existing `## Latest Review` review-record entry. The record is not added to any downstream available-documents list (`AVAILABLE_DOCS`) and is not read as plan or tasks input; the feature side reaches it through that existing entry, with no new structured field and no second count copy. The closing summary (console and handoff output) MAY restate both conclusions, but it is a presentation, not an artifact: it is not a third verifiable carrier, it carries no content obligation of its own, and where it disagrees with the two carriers the carriers govern.

**Code finding form.** A code-segment finding keeps its existing locating form — severity plus file and optional line — inside `code-review.md`. It is never coined as a `REC-…` identifier and never registered in the register; that family stays with framework-targeted recommendations.

**Unchanged surfaces.** The frontmatter `scripts:` prerequisite block, the compiled `## Wrap-up` face and `## Handoffs` are unchanged by this composition. `## Handoffs` keeps its recommendation-registration obligation in its current form.

## Status Transition — the gate this run judges

This run judges exactly one status transition, `Implemented → Ready for Review`, and states no criterion of its own. The criteria — four conjunctive conditions; the third an existence test over the current `code-review.md`, the fourth refusing any `final`-path criterion whose status is not passing without an explicit user waiver for the criterion it names — are owned by `.specify/templates/feature-details-template.md` § Canonical Status State Machine. This template cites that section, names the fourth condition only by that pointer, and carries no second wording of any of the four.

**One checkpoint.** The transition is judged once, after the process, artifact and implementation segments have finished and after the code segment completes, with both artifacts on disk (`review.md`, and `code-review.md` when the triage value is `run`). The Acceptance Reality Check's copied record is an input of the same judgement, so its run precedes the flip. Because the code segment's conclusion is one of the conditions' inputs, the status MUST NOT flip before that segment completes; an early flip is a violation even when the process segment already passed.

**A waiver is an explicit user ruling, or there is none.** A user-authored waiver artifact, or the user's own ruling in the session, is a waiver; a driver's or an orchestrator's confirmation is an agent's confirmation and is never a user ruling, and the absence of objection is not a waiver either. The command never downgrades, merges or excludes a `blocking` entry in this judgement, and it never infers a waiver.

**The unattended disposition is halt-and-report.** Without an explicit user ruling the command stops before the transition, reports the block, and records `blocking-unresolved` as the named refusal literal in the report's code subsection (`### 2.1`) and in the conclusion it returns. A refusal names the condition that failed — not merely that the transition was refused — leaves the status at `Implemented`, and never presents the run as a completed review.

**A non-conclusion is disclosed, not blocking.** A code segment recorded `not-applicable` or `not-evaluated` does not block the transition; the verdict and its reason land on the two verifiable carriers named in `## Output and placement`. The closing summary may restate them and carries no obligation of its own.

**`important` items do not block, and each one is answered.** An `important` item never blocks the transition, and the run requires each one to be answered; the remaining severity levels never block it. The two vocabularies are never merged (see `## Composition`): no numeric conversion, no mapping matrix and no unified score exists between them, and nothing in this run stores one.

## Feedback boundary — friction only, four units, one unchanged closing set

**Only framework friction may be posted.** A feedback entry records friction of the framework itself — a missing renderer, an ambiguous base, an insufficient non-interactive path, a receipt gap. A code defect found by the code segment MUST NOT be posted as a feedback entry: it stays in `code-review.md`, where its severity, file and line are meaningful, and this run posts nothing about it. The classification duty is written on two surfaces — this template and `.specify/skills/internal/code-review/SKILL.md` — so posting a code defect as feedback is a detectable violation of a written rule rather than a matter of taste. Entries land in the project-local store `.specify/memory/feedback/`; this composition adds no other destination.

**Four units, four records.** The unit census of one composed run is four units, not three and not two: this command (`/speckit.review`), the delegated process skill (`skill:review-sdd-process`), the carrier skill of the two middle segments (`skill:review-feature-quality`) and the delegated code skill (`skill:code-review`). All four share the run id and differ in `unit_id` — the key the feedback engine already uses — so none dedups, merges or truncates another. Each unit completes its own closing record: this command MUST NOT suppress any skill's wrap-up, MUST NOT write a skill's run determination on its behalf, and MUST NOT back-fill one after the fact. The count is a consequence, not a preference — every runtime-reachable segment carrier is a unit, so adding a carrier adds a unit rather than folding it into a neighbour to keep the number still.

**The closing step set is unchanged.** The six steps of the compiled `## Wrap-up` face below — run determination, execution quantification, feedback record, threshold notice, token reflection, docs-sync evaluation — stay exactly as published. This composition adds no closing step, no side channel and no second record type; every rule it states lives here, outside the generated face, and the face itself is not edited.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "/speckit.review" --unit-type command --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "/speckit.review" --unit-type command`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "/speckit.review" --unit-type command --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Docs Sync Eval — `.specify/shared/workflow/docs-step.md` § "Evaluation procedure (the embedded step points here)"
7. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"

## Handoffs

**Before**: Run after `/speckit.implement` for complete artifact chain.

**After**: Register every `REC-…` id coined in the report in `.specify/register.md` **in the same commit** as the report, using the register's existing pointer-row form (id → one-line meaning → report anchor → status). The register owns the row form; this command owns the registration obligation. Then apply improvements to the spec-kit sources (`.specify/templates/`, `commands/`, `.specify/scripts/`); optionally iterate requirements/plan.