---
name: create-tasks
description: Fill the feature's design artifacts into a dependency-ordered, immediately executable `tasks.md` — load plan/requirements plus optional design docs, organize tasks by user story under the strict checklist format, decide the Constitution-driven tests mode (ON / OFF / template-only gate) and print its banner, probe environment prerequisites, re-measure every embedded premise with real pasted output, place runtime-evidence notes at their fixed landing points, and run the structural validator to exit 0. Also owns the rerun validate-and-amend contract over an existing tasks.md. Use this when the user mentions ["generate tasks", "task breakdown", "create tasks", "tasks.md", "task list", "user story tasks", "parallel tasks", "task phases", "任务拆解", "任务分解", "生成任务清单", "生成 tasks.md", "任务列表", "拆分任务"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/create-tasks/SKILL.md>"
---

# create-tasks

## Goal

Turn the feature's design artifacts into an **actionable, dependency-ordered `tasks.md`** — tasks organized by user story so each story is independently implementable and testable, every row in the strict checklist format, tests decided by the Constitution rather than a fixed default, and every structural rule machine-checked by the validator before the report. The generated tasks.md must be immediately executable: each task specific enough that an LLM can complete it without additional context.

This skill owns the executable core of `/speckit.tasks` — Outline steps 1–6 and the Task
Generation Rules — while the command template keeps entry, the `scripts:` block, the User
Input Protocol, the Glossary protocol step, and the wrap-up lifecycle (Feedback /
Documentation / Artifact Commit / Handoffs).

Canonical extraction source: `.specify/templates/commands/tasks.md` § Outline (steps 1–6) and §
Task Generation Rules. Content moved here verbatim in substance; the structural validator
(`.specify/scripts/python/validate-tasks.py`) and the structure template
(`.specify/templates/tasks-template.md`) are already externalized and stay
invocation/pointer references.

## Input Contract

- **Upstream artifacts**: `REQUIREMENTS_DIR` must contain plan.md (tech stack, libraries,
  structure) and requirements.md (user stories with priorities) — produced by the upstream
  `/speckit.plan` run. Their absence fails the run before generation starts (the command's
  Handoffs surface the prerequisite command).
- **Optional design docs**: data-model.md (entities), contracts/ (API endpoints),
  research.md (decisions), quickstart.md (test scenarios). Not all projects have all
  documents — generate tasks based on what's available.
- **Setup variables**: REQUIREMENTS_DIR and AVAILABLE_DOCS come from the command's
  `{SCRIPT}` prerequisite run (its `scripts:` entry resolves to
  `.specify/scripts/bash/check-prerequisites.sh --json`, run from repo root); all paths must be
  absolute.
- **User input**: arrives already processed by the command's User Input Protocol; this
  skill still classifies content type per Workflow step 3 — background info, task outline,
  or additional task entries — and applies the matching integration strategy.

## Workflow (Outline steps 1–6)

### Step 1 — Setup

Run `{SCRIPT}` from repo root and parse REQUIREMENTS_DIR and AVAILABLE_DOCS list. All
paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g
'I'\''m Groot' (or double-quote if possible: "I'm Groot").

### Step 2 — Load design documents

Read from REQUIREMENTS_DIR:

- **Required**: plan.md (tech stack, libraries, structure), requirements.md (user stories
  with priorities)
- **Optional**: data-model.md (entities), contracts/ (API endpoints), research.md
  (decisions), quickstart.md (test scenarios)
- Note: Not all projects have all documents. Generate tasks based on what's available.

### Step 3 — Generate task list workflow

- **Analyze `$ARGUMENTS` input type**: determine if input contains background context,
  task outline, or additional task items.
- Load plan.md and extract tech stack, libraries, project structure
- Load requirements.md and extract user stories with their priorities (P1, P2, P3, etc.)
- If data-model.md exists: extract entities and map to user stories
- If contracts/ exists: map endpoints to user stories
- If research.md exists: extract decisions for setup tasks
- **Integrate `$ARGUMENTS` content**:
  - For background info: apply as contextual constraints in task generation
  - For task outlines: use as primary organizational structure
  - For additional tasks: parse, standardize, and merge into appropriate phases
- Generate tasks organized by user story (see Task Generation Rules below)
- Generate dependency graph showing user story completion order
- Create parallel execution examples per user story
- Validate task completeness (each user story has all needed tasks, independently
  testable)
- Validate story-label placement mechanically: every task row inside a User Story phase
  carries exactly one `[US*]` label, and NON-story phases (Setup / Foundational / Polish)
  carry ZERO `[US` markers — placeholder labels like `[US-none]` are format violations
  (enforced by the structural validator in step 5; do not rely on remembering the rule)

### Step 4 — Generate tasks.md

Use `.specify/templates/tasks-template.md` as structure, fill with:

- Correct feature name from plan.md
- Phase 1: Setup tasks (project initialization)
- Phase 2: Foundational tasks (blocking prerequisites for all user stories)
- Phase 3+: One phase per user story (in priority order from requirements.md)
- Each phase includes: story goal, independent test criteria, tests (if requested),
  implementation tasks
- Final Phase: Polish & cross-cutting concerns
- All tasks must follow the strict checklist format (see Task Generation Rules below)
- Clear file paths for each task
- Dependencies section showing story completion order
- Parallel execution examples per story
- Implementation strategy section (MVP first, incremental delivery)

### Step 5 — Mechanical structural validation (program-first)

Program-first — see `.specify/shared/guidelines/token-efficiency.md`. Run
`python3 .specify/scripts/python/validate-tasks.py <path-to-generated-tasks.md>` on the
written file (also valid on rerun against an existing tasks.md). The validator owns the
fixed structural rules — task-row single-line contract, ID uniqueness, `blockedBy`
resolvability, `[P]` parallel safety (two parallel tasks **writing** the same file; a task
that only points at a file is not a write target), story-label placement, and the DoD
format rule (`## Definition of Done` uses ONLY the `- DoD-N:` prefix; no line in that
section may match `^\- \[[ xX~]\]` checkbox syntax) — never hand-roll these checks per
run. Fix every ERROR (including rewriting any checkbox-formatted DoD items with the
`- DoD-N:` prefix) and re-run until exit 0; resolve or explicitly justify each WARN in the
report. Adjudicate every `parallel-safe` WARN **by the rows' actual write targets** — the
machine classifies pointer targets heuristically, so the verdict is yours: two rows that
only read or cite the same file are not a conflict, and two rows that both write it are,
whatever the prose says. MUST NOT silence a WARN by deleting the referenced path from a
row's text — that removes the evidence of the conflict without removing the conflict, and
leaves the row without the file path the format rule requires.

### Step 6 — Report

Output path to generated tasks.md and summary:

- Total task count
- Task count per user story
- Parallel opportunities identified
- Independent test criteria for each story
- Suggested MVP scope (typically just User Story 1)
- Format validation: confirm ALL tasks follow the checklist format (checkbox, ID, labels,
  file paths)
- Structural validator status: final `validate-tasks.py` verdict (exit code,
  error/warning counts, justification for any remaining WARN)

Context for task generation:

- Design documents from REQUIREMENTS_DIR: {AVAILABLE_DOCS}
- User input analysis result: {ARGUMENTS_ANALYSIS_RESULT}
- Input type handling strategy: {INPUT_HANDLING_STRATEGY}

The tasks.md should be immediately executable — each task must be specific enough that an
LLM can complete it without additional context. When `$ARGUMENTS` contains additional task
items, ensure they are properly integrated with correct formatting, sequential IDs, and
appropriate story labels.

## Task Generation Rules

**CRITICAL**: Tasks MUST be organized by user story to enable independent implementation
and testing.

### Tests Are Constitution-Driven (NOT a Fixed Default)

**Tests are Constitution-driven (NOT a fixed default)**: before generating tasks, detect
test-mandating principles **deterministically** (token-efficiency program-first — see
`.specify/shared/guidelines/token-efficiency.md`): run
`grep -nE 'MUST|MANDATORY|NON-NEGOTIABLE|Test-First|TDD|Contract-Driven' .specify/memory/constitution.md`
and consume only the matched principle headings/lines — do NOT read the whole constitution
into context for this keyword check.

- **Tests default ON** if any such principle exists, OR if the feature specification /
  `$ARGUMENTS` explicitly requests TDD. In ON mode you MUST emit test tasks (contract,
  unit, integration as applicable) per user story BEFORE the corresponding implementation
  tasks. If the constitution defines distinct testing layers (e.g. Layer-1 generator unit
  tests + Layer-2 build/smoke validation), emit tasks for EVERY layer it mandates.
  - **Migration/regression exception**: tests that port or guard *existing* behavior
    (migrated suites, regression nets) can only go green after the consumer code they
    exercise has been updated — place such a test task AFTER its implementation task with
    an explicit `[blockedBy: T<impl>]` tag. Only new-behavior contract tests are strictly
    red-first. This resolves the otherwise-contradictory "tests precede implementation" vs
    "Task ID sequential in execution order" pairing for migration scenarios.
- **Tests default OFF** only when no test-mandating principle is found AND the spec is
  silent on TDD.

At the top of the generated `tasks.md`, you MUST print a one-line banner declaring which
mode was chosen and cite the constitution principle (or absence thereof) that drove the
decision. Example:

```text
**Tests Mode**: ON (Constitution Principle IV "Test-First Development" is NON-NEGOTIABLE; Layer-1 unit + Layer-2 validation required)
```

or

```text
**Tests Mode**: OFF (constitution.md declares no test-mandating principle; spec did not request TDD)
```

**Template-only / doc-feature gate**: if the constitution (or plan.md's Constitution
Check) carries a *template-only features* principle (e.g. a Principle VII-style rule that
template/prompt/doc artifacts are governed by structural contract tests rather than
runtime tests), cite THAT gate in the banner and emit **structural contract tests**
(content/heading/mirror-parity assertions on the artifact) — not unit/integration tests,
which have nothing to run against. Do not re-derive this from feature history each run.

### Environment Prerequisites (probe at generation time)

When any generated task depends on an external environment (docker daemon,
network-pullable images, a live cluster, special hardware):

1. **Probe availability now**: check each required environment during task generation
   (e.g. `docker info`, a registry pull check) instead of letting `/speckit.implement`
   discover the gap mid-run. Probe results are NEVER cached across sessions or runs —
   re-probe on every generation and every rerun.
2. **Single landing point**: record every probe conclusion exactly ONCE, in the generated
   tasks.md's `## Environment Prerequisites` section (see
   `.specify/templates/tasks-template.md`). The "reference instead of restating" duty is
   OPEN over carriers: per-phase prerequisites, `[~]` task notes, assumption rows,
   decision rows, and ANY free-prose row that states or implies an environment verdict —
   all MUST reference that section instead of restating verdicts. No carrier is exempt
   by being unlisted; the list cannot be closed, so a verdict sitting in an unlisted
   carrier is still a restatement. Two hand-synced copies of the same conclusion drift
   apart.
3. **Pre-validate named targets**: any concrete build/smoke target named in a task MUST
   have a locally satisfiable dependency chain (base images pullable, toolchain present).
   If unsatisfiable, either substitute a satisfiable target up front or pre-flag the task
   `[~]`-eligible in Notes with the substitution guidance.
4. **Cross-artifact drift check**: after probing, grep this feature's sibling artifacts
   for environment assertions; any stale claim contradicting the fresh probe result MUST
   be corrected or flagged in the same run, so artifacts never disagree about the
   environment.

### Rerun contract (tasks.md already exists)

Regenerating over an existing tasks.md is destructive; a rerun is a **validate-and-amend**
pass instead. Keep existing task IDs stable — never renumber (dependency graphs, feature
records, and run history cite those IDs); drive incremental corrections from the step-5
structural validator and fresh premise/environment re-measurement; and append genuinely
new work as new IDs at the end, mirroring `/speckit.implement`'s "Append tasks, never
renumber" precedent. Regenerate from scratch only on explicit user request.

### Premise verification (all task rows)

Factual premises embedded in ANY task row — file existence, counts, "fill/extend existing
file X", "diff against pre-change output" — are governed by the **Inherited premises**
bullet of `.specify/instructions.md` § "Fact, Correctness & Logic Checks (Input Sanity)":
they are hypotheses to re-measure at generation time, for every task type, not only rows
that author tests. A row whose premise is a count carries the reproducible re-derivation
command. **That command MUST be actually run at generation time, with its real output
pasted next to the count it yields** — a printed re-derivation command that was never
executed is a claim, not a measurement, and it is exactly the route by which a wrong
number enters `tasks.md` and is then inherited as fact by every downstream row. **When a
more naive form of the same measurement would return a different answer, write the trap
form down too**: name the naive variant alongside the number it yields, so a reader can
tell the measurement was taken deliberately rather than by luck. Two recurring trap
shapes: counting the *lines* that match a pattern when the unit is an *occurrence* (a
wrapped row makes the two disagree — the same defect step 5's row-format rule reports),
and comparing *positions* in an artifact a generator is free to reorder (a paired +1/−1
positional delta is a reordering, not a regression). The Pin Hygiene rules below are the
test-authoring specialization of this same duty.

### Pin Hygiene (test-authoring rule)

Tasks that author or modify tests MUST follow pin-hygiene so the project's own next
increment does not break its own contracts:

1. **Version pins use floor semantics**: assert `parsed >= (MAJOR, MINOR)`, never
   `startswith("X.Y")` — a later legitimate bump must not fail an unrelated contract.
2. **Surface-file lists must be real**: every file path listed in a test fixture/surface
   list MUST be existence-checked at authoring time (or the list derived from the tree); a
   phantom entry turns the whole test into a permanent FileNotFoundError.
3. **Counts are contracts, not conveniences**: hard-code a count only when the count
   itself is the contract (then update it in the same task that changes the population);
   otherwise derive it with `len(...)` from a glob.

### Checklist Format (REQUIRED)

Every task MUST strictly follow this format:

```text
- [ ] [TaskID] [P?] [Story?] Description with file path
```

**One line per task (mechanical-validation contract)**: the ENTIRE task row — checkbox,
ID, labels, description, and file path — MUST stay on a single line. Format validators and
downstream tooling inspect only the row's first line; wrapping the description or the file
path onto a continuation line makes the path invisible to the gate and forces manual
re-verification.

**Format Components**:

1. **Checkbox**: ALWAYS start with `- [ ]` (markdown checkbox)
2. **Task ID**: sequential number (T001, T002, T003...) in execution order
3. **[P] marker**: include ONLY if task is parallelizable (different files, no
   dependencies on incomplete tasks)
4. **[Story] label**: REQUIRED for user story phase tasks only
   - Format: [US1], [US2], [US3], etc. (maps to user stories from requirements.md)
   - Setup phase: NO story label
   - Foundational phase: NO story label
   - User Story phases: MUST have story label
   - Polish phase: NO story label
5. **Description**: clear action with exact file path
6. **[blockedBy: Txxx,Tyyy] tag**: REQUIRED whenever a task depends on specific earlier
   tasks (derived from plan/data-model/contract dependencies). Use the tag, not prose
   ("depends on T012") — `/speckit.implement` orders execution topologically from these
   tags and refuses to start a task whose blockers are not `[X]`. Omit the tag when only
   phase order applies.

**Examples**:

- ✅ CORRECT: `- [ ] T001 Create project structure per implementation plan`
- ✅ CORRECT: `- [ ] T005 [P] Implement authentication middleware in src/middleware/auth.py`
- ✅ CORRECT: `- [ ] T012 [P] [US1] Create User model in src/models/user.py`
- ✅ CORRECT: `- [ ] T014 [US1] Implement UserService in src/services/user_service.py`
- ❌ WRONG: `- [ ] Create User model` (missing ID and Story label)
- ❌ WRONG: `T001 [US1] Create model` (missing checkbox)
- ❌ WRONG: `- [ ] [US1] Create User model` (missing Task ID)
- ❌ WRONG: `- [ ] T001 [US1] Create model` (missing file path)

### Task Organization

1. **From User Stories (requirements.md)** — PRIMARY ORGANIZATION:
   - Each user story (P1, P2, P3...) gets its own phase
   - Map all related components to their story:
     - Models needed for that story
     - Services needed for that story
     - Endpoints/UI needed for that story
     - If tests requested: tests specific to that story
   - Mark story dependencies (most stories should be independent)

2. **From Contracts**:
   - Map each contract/endpoint → to the user story it serves
   - If tests requested: each contract → contract test task [P] before implementation in
     that story's phase
   - Prefer one test file per contract document rather than per story: when multiple
     stories append to a single shared test file, [P] parallel markers become invalid and
     stories serialize on that file
   - **When one test file is legitimately claimed by verification tasks in more than one
     phase** (one contract document whose clauses span several stories, so a single test
     file is correct), the two rules above are not sufficient: partition that file's
     clause ranges across the verification rows so each row names the clauses it is
     responsible for turning green, or assign the file to a single phase and have later
     rows reference it read-only. Otherwise two rows demand the same file be "all green"
     at different times and the pair is unsatisfiable in the prescribed order — the
     executor is left either ticking a row against a partially-green file or overriding
     the schedule. Declare the partition with the `[green: <contract>#<clause>]`
     attribution tag (defined in `.specify/templates/tasks-template.md` § Format) and let
     the validator judge it: its `green-path-divergence` check flags any test path
     appearing in two verification rows with different green points, so this is one
     machine criterion and MUST NOT also be carried as a second, hand-run one.

3. **From Data Model**:
   - Map each entity to the user story(ies) that need it
   - If entity serves multiple stories: put in earliest story or Setup phase
   - Relationships → service layer tasks in appropriate story phase

4. **From Setup/Infrastructure**:
   - Shared infrastructure → Setup phase (Phase 1)
   - Foundational/blocking tasks → Foundational phase (Phase 2)
   - Story-specific setup → within that story's phase

### Phase Structure

- **Phase 1**: Setup (project initialization)
- **Phase 2**: Foundational (blocking prerequisites — MUST complete before user stories)
- **Phase 3+**: User Stories in priority order (P1, P2, P3...)
  - Within each story: Tests (if requested) → Models → Services → Endpoints → Integration
  - Each phase should be a complete, independently testable increment
- **Final Phase**: Polish & Cross-Cutting Concerns

**Runtime-evidence landing points (Setup / Foundational rows — fixed, never re-invented
per run)**: run-time evidence produced by a Setup or Foundational row lands at a fixed
path. Without a written landing point each tasks round imitates a neighbouring spec and
each implement round has to guess where the previous phase put the file:

- **Failing-test baseline name list** — its path, its capture flag, and its name-level
  comparison form are owned by `/speckit.implement` step 6's `**Test runs**` bullet
  (`.specify/templates/commands/implement.md`). MUST NOT be restated, re-derived, or given a second
  path here; a Setup/Foundational row that captures or consumes that baseline points at
  that owner.
- `<spec-dir>/notes/red-first-evidence.md` — for every test that MUST go red before its
  subject exists: the command, its real output, and its exit status. When the note binds
  a claim to a gate, it MUST quote the gate row verbatim — id + name + check command;
  a bare gate id alone MUST NOT be used, so a later renumbering produces a visible
  mismatch rather than a silently dangling reference. Forward-applicable only:
  pre-existing note instances (e.g. 062's) are out of scope and MUST NOT be
  retro-edited.
- `<spec-dir>/notes/quickstart-run.md` — the real output of actually running this
  feature's `quickstart.md` scenario, its teardown steps included.
- `<spec-dir>/notes/pre-change-measurements.md` — the pre-change side of every "diff
  against pre-change output" premise: the measured value, the command that produced it,
  and the capture date.
- `<spec-dir>/coverage-baseline.txt` — for a feature with a contract set, freeze it with
  `python3 .specify/scripts/python/account-clause-coverage.py <spec-dir> --freeze > <spec-dir>/coverage-baseline.txt`
  (the accountant's own default path is `coverage-baseline.txt`); the timing is the same
  re-freeze timing stated below (first full-tree accounting per feature, not first
  all-green). A feature without a contract set MUST skip with an explicit stated reason —
  MUST NOT fabricate an empty baseline.

Create `notes/` in Phase 1 (Setup) so that Phase 2 (Foundational) rows already have
somewhere to write. **Re-freeze timing**: these files are frozen measurements, so they
inherit the never-cache rule the Environment Prerequisites probes above already state —
re-capture on every generation and every rerun of this command (the producer-side
obligation, retained). The implement-side re-capture is not this command's duty to
describe: it is owned by `/speckit.implement`'s baseline pre-flight (its Step 0 in
`.specify/skills/internal/implement-feature/SKILL.md` — the implement-side consumer step),
which re-captures every frozen baseline before any workflow step and classifies every
difference. A row whose re-capture yields a different value carries the new value; MUST
NOT keep citing the stale frozen one.

**Special phase shapes**: two cases override the default "Models → Services → Endpoints"
within-story order — **asset-migration** (porting/vendoring an external code subset: split
the physical copy + dependency-closure check from the story-owned governance artifacts) and
**doc-feature** (template-only / documentation / prompt-framework specs: author-section →
mirror-parity → render-verify → refresh-verify taxonomy). Full rules live in
[references/phase-shapes.md](references/phase-shapes.md) — consult it whenever the spec's
deliverables match either case. The app-shaped examples in the tasks template are
illustrative, not mandatory; pick the taxonomy that matches the spec's actual
deliverables.

## Feature Integration

Apply the Feature Integration Protocol (`.specify/shared/workflow/feature-integration.md`
— canonical convention; do not restate it here). This phase maintains feature status from
the planning phase. Additionally, **the tasks phase MUST review the Feature list** — task
breakdown may expose new Features or invalidate old ones. Update
`.specify/memory/features.md` and detail files synchronously if changes are discovered.

## Boundaries

- **Entry & lifecycle stay in the command template** `/speckit.tasks`: the AUTO-GENERATED
  header, the `scripts:` block, the User Input Protocol section, the Glossary protocol
  step, `## Feedback`, `## Documentation`, `## Artifact Commit`, and `## Handoffs`
  (before/after command sequencing and next-command suggestions) are command surfaces, not
  skill content.
- **Externalized assets stay pointers** (per the S0 ruling): the structural validator
  `.specify/scripts/python/validate-tasks.py` and the structure template
  `.specify/templates/tasks-template.md` are invoked and referenced, never re-implemented
  or copied — the validator owns the fixed structural checks, the template owns the
  section layout (Format, Environment Prerequisites, the `[green: <contract>#<clause>]`
  tag definition). This skill's duty is to invoke the validator and adjudicate its
  findings, never to hand-roll the checks per run.
- **Shared conventions stay pointers**: the token-efficiency discipline
  (`.specify/shared/guidelines/token-efficiency.md`), the Feature Integration Protocol,
  `/speckit.implement`'s `**Test runs**` baseline owner
  (`.specify/templates/commands/implement.md`), and the Input Sanity section of
  `.specify/instructions.md` are referenced by path, never restated here.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:create-tasks" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:create-tasks" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:create-tasks" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
