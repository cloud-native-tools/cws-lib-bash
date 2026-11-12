# Feature Integration Protocol

This document defines the standard feature tracking integration used by SDD lifecycle commands.

## Core Protocol

Every SDD lifecycle command (`/speckit.requirements`, `/speckit.plan`, `/speckit.tasks`, `/speckit.implement`, `/speckit.checklist`, `/speckit.review`, `/speckit.seal`) automatically integrates with the feature tracking system:

1. **Detect feature context**:
   - If `.specify/features.md` exists, detect the current feature directory (format: `.specify/specs/[REQUIREMENTS_KEY]/`)
   - Extract the feature ID from the directory name

2. **Update feature entry** in `.specify/features.md`:
   - Apply the command-specific status transition (see Status State Machine below)
   - Keep the specification path unchanged
   - Update the "Last Updated" date
   - Automatically stage the changes for git commit

3. **Feature list re-validation** (mandatory for plan, tasks, implement phases):
   - Check whether the current work introduces new Features or deprecates/merges existing ones
   - Ensure functional/non-functional Feature classification remains consistent
   - If changes are discovered, synchronously update:
     - `.specify/features/<ID>.md`
     - `.specify/features.md`
   - Record "key changes / notes" in the Feature detail

## Status State Machine

Each command owns exactly one transition:

| Command | Transition | Notes |
|---------|-----------|-------|
| `/speckit.requirements` | (none) → `Draft` or keep existing | Initializes Feature Linkage; binding deferred to `/speckit.clarify` Mode A |
| `/speckit.plan` | `Draft → Planned` | MUST NOT land `Implemented` |
| `/speckit.tasks` | Maintain `Planned` | Status unchanged |
| `/speckit.implement` | `Planned → Implemented` | Requires Pre-Status-Flip Gate |
| `/speckit.checklist` | `Implemented → Ready for Review` | Conditional initiator — applies only when the checklist runs after `/speckit.implement`: after implement it initiates the transition and cites the same owner criterion; before implement it initiates nothing, MUST NOT error for the absence of a code-segment conclusion, and MUST NOT manufacture one. Criteria are owned by `.specify/templates/feature-details-template.md` § Canonical Status State Machine and are not restated here |
| `/speckit.review` | `Implemented → Ready for Review` | Unconditional initiator. Criteria are owned by `.specify/templates/feature-details-template.md` § Canonical Status State Machine and are not restated here; this gate is a property of the transition, not of this one command |
| `/speckit.seal` | `Ready for Review → Sealed` | Unconditional initiator once its conjunctive conditions hold. Criteria are owned by `.specify/shared/workflow/acceptance-hardening.md` § Feature Status and are not restated here; `Sealed` is the terminal status for new work |

`Ready for Review → Completed` is **closed for new work**: `Completed` survives only as a legacy record value
for rows written before `Sealed` existed (no retroactive rewrite, no downgrade), and new work reaches its
terminal status through `/speckit.seal` (`Ready for Review → Sealed`). A legacy `Completed` row does not
thereby earn archive admission — admission is queried from `seal-utils.py --action archive-gate`.

## Pre-Status-Flip Gate (implement phase only)

Before advancing to `Implemented`:

1. Convert deferred tasks: `[ ]` → `[~]` with `<!-- deferred: <reason> -->` comment
2. Zero open-task check: `grep -cE '^\- \[ \]' tasks.md` must return 0
3. Verification log completeness: every `SC-NNN` has a status row
4. Deferred task registry: `deferred_tasks=` in `verification.md` lists all `[~]` IDs
5. Closure verdict: run `python3 .specify/scripts/python/closure-acceptance-check.py --spec-dir <spec-dir>` before
   the flip. It is the single source of the verdict, the closed reason set and the `final_path` counts; the
   schema owner of all three is `.specify/shared/workflow/acceptance-hardening.md` § Closure Verdict, and this gate
   calls that judgement instead of restating a condition. It MUST NOT be re-decided by a model judgement,
   another script, or an ad-hoc grep over the artifacts. On `block`, record the emitted reasons in
   `verification.md`, land `Blocked`, and MUST NOT write `Implemented`. Exit `2` is an input defect in the
   artifacts: repair and re-run, and never read it as `accept`
6. Only if ALL checks pass: advance status
7. Void DoD rows and Completion Gate items: a DoD row OR a `## Completion Gate` item whose premise is measurably
   false is **void**, not unmet. It does not block the flip, but it MUST carry cited measurement, an inline annotation
   on the `DoD Status` line (or on the gate item), and prominent surfacing in the wrap-up report. Record the correction
   where the false premise lives (see `.specify/templates/tasks-template.md` DoD Status). Never report the Definition of Done as
   plainly "met" while a void row is folded silently into it

## Feature Binding Rules (clarify checkpoint)

`/speckit.requirements` initializes `Related Feature` with `Need clarification`; `/speckit.clarify` Mode A applies these rules to scan, bind, or create:

1. **Scan for existing Feature**:
   - Search by context: Scan `.specify/features/*.md` and `.specify/features.md`
   - Search by ID: Check `SPECIFY_FEATURE` env, git branch name, numeric prefix in BRANCH_NAME
   - **Binding-precedent heuristic**: for each candidate Feature, check its sibling specs (prior spec directories already bound to it, e.g. via its detail file's Related Files/history). A Feature whose siblings repeatedly absorbed similar work is strong evidence for **bind**; a candidate with no topical siblings is evidence for **create**. Surface the precedent when recommending bind-vs-create.

2. **Bind or Create**:
   - If matching Feature found → bind to that Feature ID, do NOT create new
   - If NO match → create new Feature from `.specify/templates/feature-details-template.md`, add row to index

3. **Integration responsibilities**:
   - Ensure corresponding Feature entry exists
   - Update `.specify/features.md`: set Status to the transition owned by `/speckit.requirements` (§ Status State Machine — the requirements phase lands `Draft`, never `Planned`), update Spec Path, refresh date
   - The index is **hand-maintained**: no script regenerates it, so the `Total Features` header and the rows MUST be edited together in the same pass — a header edited alone, or rows edited without it, leaves the file self-inconsistent while still looking well-formed
   - Never create duplicate Feature IDs

## Feature Continuous Evolution

- Before generating/updating a spec, the Feature list MUST be reviewed
- A new SPEC may introduce a new Feature or make existing ones obsolete
- Functional/non-functional classification consistency MUST be preserved
- Feature changes must record source evidence as "key changes / notes"
