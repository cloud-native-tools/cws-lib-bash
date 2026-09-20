---
description: 基于设计产物生成依赖有序的 tasks.md 任务清单
---
<!-- AUTO-GENERATED from templates/commands/tasks.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Detect input type and apply:
- **Background info** → integrate as context constraints
- **Task outline** → use as primary organizational structure
- **Additional task entries** → parse, standardize, merge into appropriate phases

If empty, generate a complete `tasks.md` from available design artifacts.

## Glossary

Consult the project glossary (`.specify/memory/glossary.md`, ambient via the Documentation Map) and apply the protocol in `.specify/shared/workflow/glossary.md`:

- **Before acting on the user input**, map any recorded homophone/confusable variant to its canonical term (correcting voice/dictated input); surface each correction so the user can override it, and defer to the user on ambiguous variants.
- **At wrap-up**, propose any new project-specific terms (`origin=auto`, `status=proposed`), excluding common words; run conflict detection; non-conflicting new terms MUST be written directly and merged into the wrap-up report (non-blocking); only writes that conflict with or overwrite an existing user entry MUST still pause for user confirmation. User-authored entries are authoritative.

## Outline

1. **Setup**: Run `.specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse REQUIREMENTS_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Load design documents**: Read from REQUIREMENTS_DIR:
   - **Required**: plan.md (tech stack, libraries, structure), requirements.md (user stories with priorities)
   - **Optional**: data-model.md (entities), contracts/ (API endpoints), research.md (decisions), quickstart.md (test scenarios)
   - Note: Not all projects have all documents. Generate tasks based on what's available.

3. **Generate task list workflow**:
   - **Analyze $ARGUMENTS input type**: Determine if input contains background context, task outline, or additional task items
   - Load plan.md and extract tech stack, libraries, project structure
   - Load requirements.md and extract user stories with their priorities (P1, P2, P3, etc.)
   - If data-model.md exists: Extract entities and map to user stories
   - If contracts/ exists: Map endpoints to user stories
   - If research.md exists: Extract decisions for setup tasks
   - **Integrate $ARGUMENTS content**: 
     - For background info: Apply as contextual constraints in task generation
     - For task outlines: Use as primary organizational structure
     - For additional tasks: Parse, standardize, and merge into appropriate phases
   - Generate tasks organized by user story (see Task Generation Rules below)
   - Generate dependency graph showing user story completion order
   - Create parallel execution examples per user story
   - Validate task completeness (each user story has all needed tasks, independently testable)
   - Validate story-label placement mechanically: every task row inside a User Story phase carries exactly one `[US*]` label, and NON-story phases (Setup / Foundational / Polish) carry ZERO `[US` markers — placeholder labels like `[US-none]` are format violations (enforced by the structural validator in step 5; do not rely on remembering the rule)

4. **Generate tasks.md**: Use `.specify/templates/tasks-template.md` as structure, fill with:
   - Correct feature name from plan.md
   - Phase 1: Setup tasks (project initialization)
   - Phase 2: Foundational tasks (blocking prerequisites for all user stories)
   - Phase 3+: One phase per user story (in priority order from requirements.md)
   - Each phase includes: story goal, independent test criteria, tests (if requested), implementation tasks
   - Final Phase: Polish & cross-cutting concerns
   - All tasks must follow the strict checklist format (see Task Generation Rules below)
   - Clear file paths for each task
   - Dependencies section showing story completion order
   - Parallel execution examples per story
   - Implementation strategy section (MVP first, incremental delivery)

5. **Mechanical structural validation (program-first — see `.specify/shared/guidelines/token-efficiency.md`)**: run `python3 .specify/scripts/python/validate-tasks.py <path-to-generated-tasks.md>` on the written file (also valid on rerun against an existing tasks.md). The validator owns the fixed structural rules — task-row single-line contract, ID uniqueness, `blockedBy` resolvability, `[P]` parallel safety (two parallel tasks naming the same file), story-label placement, and the DoD format rule (`## Definition of Done` uses ONLY the `- DoD-N:` prefix; no line in that section may match `^\- \[[ xX~]\]` checkbox syntax) — never hand-roll these checks per run. Fix every ERROR (including rewriting any checkbox-formatted DoD items with the `- DoD-N:` prefix) and re-run until exit 0; resolve or explicitly justify each WARN in the report.

6. **Report**: Output path to generated tasks.md and summary:
   - Total task count
   - Task count per user story
   - Parallel opportunities identified
   - Independent test criteria for each story
   - Suggested MVP scope (typically just User Story 1)
   - Format validation: Confirm ALL tasks follow the checklist format (checkbox, ID, labels, file paths)
   - Structural validator status: final `validate-tasks.py` verdict (exit code, error/warning counts, justification for any remaining WARN)

Context for task generation: 
- Design documents from REQUIREMENTS_DIR: {AVAILABLE_DOCS}
- User input analysis result: {ARGUMENTS_ANALYSIS_RESULT}
- Input type handling strategy: {INPUT_HANDLING_STRATEGY}

The tasks.md should be immediately executable - each task must be specific enough that an LLM can complete it without additional context. When $ARGUMENTS contains additional task items, ensure they are properly integrated with correct formatting, sequential IDs, and appropriate story labels.

## Feature Integration

Apply [Feature Integration Protocol](.specify/shared/workflow/feature-integration.md). This command maintains status from planning phase. Additionally, **the tasks phase MUST review the Feature list** — task breakdown may expose new Features or invalidate old ones. Update `.specify/memory/features.md` and detail files synchronously if changes are discovered.

## Task Generation Rules

**CRITICAL**: Tasks MUST be organized by user story to enable independent implementation and testing.

**Tests are Constitution-driven (NOT a fixed default)**: Before generating tasks, detect test-mandating principles **deterministically** (token-efficiency program-first — see `.specify/shared/guidelines/token-efficiency.md`): run `grep -nE 'MUST|MANDATORY|NON-NEGOTIABLE|Test-First|TDD|Contract-Driven' .specify/memory/constitution.md` and consume only the matched principle headings/lines — do NOT read the whole constitution into context for this keyword check.

- **Tests default ON** if any such principle exists, OR if the feature specification / `$ARGUMENTS` explicitly requests TDD. In ON mode you MUST emit test tasks (contract, unit, integration as applicable) per user story BEFORE the corresponding implementation tasks. If the constitution defines distinct testing layers (e.g. Layer-1 generator unit tests + Layer-2 build/smoke validation), emit tasks for EVERY layer it mandates.
  - **Migration/regression exception**: tests that port or guard *existing* behavior (migrated suites, regression nets) can only go green after the consumer code they exercise has been updated — place such a test task AFTER its implementation task with an explicit `[blockedBy: T<impl>]` tag. Only new-behavior contract tests are strictly red-first. This resolves the otherwise-contradictory "tests precede implementation" vs "Task ID sequential in execution order" pairing for migration scenarios.
- **Tests default OFF** only when no test-mandating principle is found AND the spec is silent on TDD.

At the top of the generated `tasks.md`, you MUST print a one-line banner declaring which mode was chosen and cite the constitution principle (or absence thereof) that drove the decision. Example:

```text
**Tests Mode**: ON (Constitution Principle IV "Test-First Development" is NON-NEGOTIABLE; Layer-1 unit + Layer-2 validation required)
```

or

```text
**Tests Mode**: OFF (constitution.md declares no test-mandating principle; spec did not request TDD)
```

**Template-only / doc-feature gate**: if the constitution (or plan.md's Constitution Check) carries a *template-only features* principle (e.g. a Principle VII-style rule that template/prompt/doc artifacts are governed by structural contract tests rather than runtime tests), cite THAT gate in the banner and emit **structural contract tests** (content/heading/mirror-parity assertions on the artifact) — not unit/integration tests, which have nothing to run against. Do not re-derive this from feature history each run.

### Environment Prerequisites (probe at generation time)

When any generated task depends on an external environment (docker daemon, network-pullable images, a live cluster, special hardware):

1. **Probe availability now**: check each required environment during task generation (e.g. `docker info`, a registry pull check) instead of letting `/speckit.implement` discover the gap mid-run. Probe results are NEVER cached across sessions or runs — re-probe on every generation and every rerun.
2. **Single landing point**: record every probe conclusion exactly ONCE, in the generated tasks.md's `## Environment Prerequisites` section (see `.specify/templates/tasks-template.md`). Per-phase prerequisites and `[~]` task notes MUST reference that section instead of restating verdicts — two hand-synced copies of the same conclusion drift apart.
3. **Pre-validate named targets**: any concrete build/smoke target named in a task MUST have a locally satisfiable dependency chain (base images pullable, toolchain present). If unsatisfiable, either substitute a satisfiable target up front or pre-flag the task `[~]`-eligible in Notes with the substitution guidance.
4. **Cross-artifact drift check**: after probing, grep this feature's sibling artifacts for environment assertions; any stale claim contradicting the fresh probe result MUST be corrected or flagged in the same run, so artifacts never disagree about the environment.

### Rerun contract (tasks.md already exists)

Regenerating over an existing tasks.md is destructive; a rerun is a **validate-and-amend** pass instead. Keep existing task IDs stable — never renumber (dependency graphs, feature records, and run history cite those IDs); drive incremental corrections from the step-5 structural validator and fresh premise/environment re-measurement; and append genuinely new work as new IDs at the end, mirroring `/speckit.implement`'s "Append tasks, never renumber" precedent. Regenerate from scratch only on explicit user request.

### Premise verification (all task rows)

Factual premises embedded in ANY task row — file existence, counts, "fill/extend existing file X", "diff against pre-change output" — are governed by the **Inherited premises** bullet of `.specify/instructions.md` § "Fact, Correctness & Logic Checks (Input Sanity)": they are hypotheses to re-measure at generation time, for every task type, not only rows that author tests. A row whose premise is a count carries the reproducible re-derivation command. The Pin Hygiene rules below are the test-authoring specialization of this same duty.

### Pin Hygiene (test-authoring rule)

Tasks that author or modify tests MUST follow pin-hygiene so the project's own next increment does not break its own contracts:

1. **Version pins use floor semantics**: assert `parsed >= (MAJOR, MINOR)`, never `startswith("X.Y")` — a later legitimate bump must not fail an unrelated contract.
2. **Surface-file lists must be real**: every file path listed in a test fixture/surface list MUST be existence-checked at authoring time (or the list derived from the tree); a phantom entry turns the whole test into a permanent FileNotFoundError.
3. **Counts are contracts, not conveniences**: hard-code a count only when the count itself is the contract (then update it in the same task that changes the population); otherwise derive it with `len(...)` from a glob.

### Checklist Format (REQUIRED)

Every task MUST strictly follow this format:

```text
- [ ] [TaskID] [P?] [Story?] Description with file path
```

**One line per task (mechanical-validation contract)**: the ENTIRE task row — checkbox, ID, labels, description, and file path — MUST stay on a single line. Format validators and downstream tooling inspect only the row's first line; wrapping the description or the file path onto a continuation line makes the path invisible to the gate and forces manual re-verification.

**Format Components**:

1. **Checkbox**: ALWAYS start with `- [ ]` (markdown checkbox)
2. **Task ID**: Sequential number (T001, T002, T003...) in execution order
3. **[P] marker**: Include ONLY if task is parallelizable (different files, no dependencies on incomplete tasks)
4. **[Story] label**: REQUIRED for user story phase tasks only
   - Format: [US1], [US2], [US3], etc. (maps to user stories from requirements.md)
   - Setup phase: NO story label
   - Foundational phase: NO story label  
   - User Story phases: MUST have story label
   - Polish phase: NO story label
5. **Description**: Clear action with exact file path
6. **[blockedBy: Txxx,Tyyy] tag**: REQUIRED whenever a task depends on specific earlier tasks (derived from plan/data-model/contract dependencies). Use the tag, not prose ("depends on T012") — `/speckit.implement` orders execution topologically from these tags and refuses to start a task whose blockers are not `[X]`. Omit the tag when only phase order applies.

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

1. **From User Stories (requirements.md)** - PRIMARY ORGANIZATION:
   - Each user story (P1, P2, P3...) gets its own phase
   - Map all related components to their story:
     - Models needed for that story
     - Services needed for that story
     - Endpoints/UI needed for that story
     - If tests requested: Tests specific to that story
   - Mark story dependencies (most stories should be independent)

2. **From Contracts**:
   - Map each contract/endpoint → to the user story it serves
   - If tests requested: Each contract → contract test task [P] before implementation in that story's phase
   - Prefer one test file per contract document rather than per story: when multiple stories append to a single shared test file, [P] parallel markers become invalid and stories serialize on that file
   - **When one test file is legitimately claimed by verification tasks in more than one phase** (one contract document whose clauses span several stories, so a single test file is correct), the two rules above are not sufficient: partition that file's clause ranges across the verification rows so each row names the clauses it is responsible for turning green, or assign the file to a single phase and have later rows reference it read-only. Otherwise two rows demand the same file be "all green" at different times and the pair is unsatisfiable in the prescribed order — the executor is left either ticking a row against a partially-green file or overriding the schedule. Add a self-check that flags any test path appearing in two verification rows with different green points.

3. **From Data Model**:
   - Map each entity to the user story(ies) that need it
   - If entity serves multiple stories: Put in earliest story or Setup phase
   - Relationships → service layer tasks in appropriate story phase

4. **From Setup/Infrastructure**:
   - Shared infrastructure → Setup phase (Phase 1)
   - Foundational/blocking tasks → Foundational phase (Phase 2)
   - Story-specific setup → within that story's phase

### Phase Structure

- **Phase 1**: Setup (project initialization)
- **Phase 2**: Foundational (blocking prerequisites - MUST complete before user stories)
- **Phase 3+**: User Stories in priority order (P1, P2, P3...)
  - Within each story: Tests (if requested) → Models → Services → Endpoints → Integration
  - Each phase should be a complete, independently testable increment
- **Final Phase**: Polish & Cross-Cutting Concerns

**Asset-migration phase shape (porting/vendoring an external code subset)**: when a spec copies an external codebase subset in as a hosted asset, split the copy from its acceptance: the **physical copy + static dependency-closure check** is Foundational (Phase 2 — it blocks everything), while **governance artifacts** (provenance ledger, license, ported regression tests, mirrors) belong to the user story that owns the asset. Two standard acceptance actions for the copy task: (1) grep-assert every import resolves to the runtime's builtins or inside the subset; (2) **actually resolve all entry modules with the runtime** (e.g. `node -e "await import(...)"` per entry) — checklist-driven copying misses transitive dependencies that only real module resolution exposes.

**Doc-feature phase shape (template-only / documentation / prompt-framework specs)**: when the spec's deliverables are templates, docs, prompts, or skills rather than runtime code, "Models → Services → Endpoints" does not apply — do not force it. Switch the within-story order to the doc-feature taxonomy:
1. **author-section** — write/edit the template or document section itself
2. **mirror-parity** — every row of plan.md's *Mirror Obligations* table MUST be covered by an explicit write task and an explicit verify task: rows that share one fan-out command (e.g. a single `sync-mirrors.py --write`) MAY share the write task (one per phase, not one per row), but each verify task MUST enumerate the rows it covers (`diff -q` for mirrors; grep-for-the-edit for regenerated per-tool copies). Mirror pairs are first-class tasks, never implicit side-effects of the authoring task.
3. **render-verify** — actually render/execute the artifact (render the diagram, run the template through its consumer) and inspect the output
4. **refresh-verify** — re-run the artifact's refresh/regeneration path to confirm repeatability
The app-shaped examples in the tasks template are illustrative, not mandatory; pick the taxonomy that matches the spec's actual deliverables.

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.tasks" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Artifact Commit

At wrap-up, **before** the Feedback and Documentation steps, commit the artifact this command produced — and only that artifact, staged by explicit path. Follow the canonical convention in `.specify/shared/workflow/artifact-commit-step.md`: run the deletion-surface audit first, use a single-line message per `.specify/templates/commit-template.md`, never `git add -A`, and never fold another command's uncommitted artifacts into this commit (report that as an upstream deviation instead). A read-only run that produced no artifact skips this step and says so in one line rather than creating an empty commit. Committing here does not advance the feature's lifecycle status and does not push.

## Handoffs

**Before running this command**:

- Run `/speckit.plan` to produce a plan and design artifacts.

**After running this command**:

- Optionally run `/speckit.analyze` to check cross-artifact consistency before implementation.
- Optionally run `/speckit.checklist` to create quality gates.
- Then run `/speckit.implement` to execute the tasks phase-by-phase.