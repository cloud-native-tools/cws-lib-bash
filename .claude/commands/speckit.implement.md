## User Input

```text
$ARGUMENTS
```

You **MUST** analyze the user input in `$ARGUMENTS`, infer the user's intent, and use that intent to supplement missing context and guide the implementation process.

The user input may include:

1. Special requests that require extra care or custom handling during the implementation workflow.
2. Supplemental information that provides additional context or reference material.
3. Specific implementation constraints, priorities, or scope adjustments that go beyond the default scope described in this document.

When processing the user input:

1. You **MUST** treat `$ARGUMENTS` as parameters for the current command.
2. Do **NOT** treat the input as a standalone instruction that overrides or replaces the command workflow.
3. If the input contains clear ambiguity, confusion, or likely misspellings that materially affect interpretation, stop and ask the user to rephrase the request with clearer wording. Provide brief guidance when possible.

## Outline

1. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root and parse REQUIREMENTS_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Check checklists status** (if REQUIREMENTS_DIR/checklists/ exists):
   - Scan all checklist files in the checklists/ directory
   - For each checklist, count:
     - Total items: All lines matching `- [ ]` or `- [X]` or `- [x]`
     - Completed items: Lines matching `- [X]` or `- [x]`
     - Incomplete items: Lines matching `- [ ]`
   - Create a status table:

     ```text
     | Checklist | Total | Completed | Incomplete | Status |
     |-----------|-------|-----------|------------|--------|
     | ux.md     | 12    | 12        | 0          | ✓ PASS |
     | test.md   | 8     | 5         | 3          | ✗ FAIL |
     | security.md | 6   | 6         | 0          | ✓ PASS |
     ```

   - Calculate overall status:
     - **PASS**: All checklists have 0 incomplete items
     - **FAIL**: One or more checklists have incomplete items

   - **If any checklist is incomplete**:
     - Display the table with incomplete item counts
     - **STOP** and ask: "Some checklists are incomplete. Do you want to proceed with implementation anyway? (yes/no)"
     - Wait for user response before continuing
     - If user says "no" or "wait" or "stop", halt execution
     - If user says "yes" or "proceed" or "continue":
       1. **Require a waiver comment** (short risk-acceptance note) before proceeding
       2. Record the waiver in `REQUIREMENTS_DIR/waivers.md` (create if missing) with:
          - Date (ISO)
          - Checklist summary table
          - Waiver comment
       3. Proceed to step 3

   - **If all checklists are complete**:
     - Display the table showing all checklists passed
     - Automatically proceed to step 3

3. Load and analyze the implementation context:
   - **REQUIRED**: Read tasks.md for the complete task list and execution plan
   - **REQUIRED**: Read plan.md for tech stack, architecture, and file structure
   - **IF EXISTS**: Read data-model.md for entities and relationships
   - **IF EXISTS**: Read contracts/ for API specifications and test requirements
   - **IF EXISTS**: Read research.md for technical decisions and constraints
   - **IF EXISTS**: Read quickstart.md for integration scenarios

4. **Project Setup Verification**:
   - **REQUIRED**: Create/verify ignore files based on actual project setup:

   **Detection & Creation Logic**:
   - Check if the following command succeeds to determine if the repository is a git repo (create/verify .gitignore if so):

     ```sh
     git rev-parse --git-dir 2>/dev/null
     ```

   - **If the repository IS a git repo**, also verify the commit identity is set BEFORE staging any files (catching this here avoids the common "all work staged, commit fails" trap at the end of the run):

     ```sh
     git config --get user.email
     git config --get user.name
     ```

     If either is empty, HALT the run and prompt the user to set them (e.g. `git config --global user.email "you@example.com"` / `git config --global user.name "Your Name"`, or repo-local equivalents). Do NOT continue to file edits until the identity is set — at that point the working tree is still clean and recoverable.

   - Check if Dockerfile* exists or Docker in plan.md → create/verify .dockerignore
   - Check if .eslintrc* exists → create/verify .eslintignore
   - Check if eslint.config.* exists → ensure the config's `ignores` entries cover required patterns
   - Check if .prettierrc* exists → create/verify .prettierignore
   - Check if .npmrc or package.json exists → create/verify .npmignore (if publishing)
   - Check if terraform files (*.tf) exist → create/verify .terraformignore
   - Check if .helmignore needed (helm charts present) → create/verify .helmignore

   **If ignore file already exists**: Verify it contains essential patterns, append missing critical patterns only
   **If ignore file missing**: Create with full pattern set for detected technology

   **Common Patterns by Technology** (from plan.md tech stack):
   - **Node.js/JavaScript/TypeScript**: `node_modules/`, `dist/`, `build/`, `*.log`, `.env*`
   - **Python**: `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `dist/`, `*.egg-info/`
   - **Java**: `target/`, `*.class`, `*.jar`, `.gradle/`, `build/`
   - **C#/.NET**: `bin/`, `obj/`, `*.user`, `*.suo`, `packages/`
   - **Go**: `*.exe`, `*.test`, `vendor/`, `*.out`
   - **Ruby**: `.bundle/`, `log/`, `tmp/`, `*.gem`, `vendor/bundle/`
   - **PHP**: `vendor/`, `*.log`, `*.cache`, `*.env`
   - **Rust**: `target/`, `debug/`, `release/`, `*.rs.bk`, `*.rlib`, `*.prof*`, `.idea/`, `*.log`, `.env*`
   - **Kotlin**: `build/`, `out/`, `.gradle/`, `.idea/`, `*.class`, `*.jar`, `*.iml`, `*.log`, `.env*`
   - **C++**: `build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.so`, `*.a`, `*.exe`, `*.dll`, `.idea/`, `*.log`, `.env*`
   - **C**: `build/`, `bin/`, `obj/`, `out/`, `*.o`, `*.a`, `*.so`, `*.exe`, `Makefile`, `config.log`, `.idea/`, `*.log`, `.env*`
   - **Swift**: `.build/`, `DerivedData/`, `*.swiftpm/`, `Packages/`
   - **R**: `.Rproj.user/`, `.Rhistory`, `.RData`, `.Ruserdata`, `*.Rproj`, `packrat/`, `renv/`
   - **Universal**: `.DS_Store`, `Thumbs.db`, `*.tmp`, `*.swp`, `.vscode/`, `.idea/`

   **Tool-Specific Patterns**:
   - **Docker**: `node_modules/`, `.git/`, `Dockerfile*`, `.dockerignore`, `*.log*`, `.env*`, `coverage/`
   - **ESLint**: `node_modules/`, `dist/`, `build/`, `coverage/`, `*.min.js`
   - **Prettier**: `node_modules/`, `dist/`, `build/`, `coverage/`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`
   - **Terraform**: `.terraform/`, `*.tfstate*`, `*.tfvars`, `.terraform.lock.hcl`
   - **Kubernetes/k8s**: `*.secret.yaml`, `secrets/`, `.kube/`, `kubeconfig*`, `*.key`, `*.crt`

5. Parse tasks.md structure and extract:
   - **Task phases**: Setup, Tests, Core, Integration, Polish
   - **Task dependencies**: Sequential vs parallel execution rules
   - **Task details**: ID, description, file paths, parallel markers [P]
   - **Execution flow**: Order and dependency requirements

6. Implement feature following the task plan:
   - **Phase-by-phase implementation**: Complete each phase before moving to the next
   - **Respect dependencies**: Run sequential tasks in order, parallel tasks [P] can run together  
   - **Follow TDD approach**: Implement test tasks before their corresponding implementation tasks
   - **File-based coordination**: Tasks affecting the same files must run sequentially
   - **Validation checkpoints**: Verify each phase completion before proceeding

7. Implementation rules:
   - **Setup first**: Initialize project structure, dependencies, configuration
   - **Tests before code**: If you need to write tests for contracts, entities, and integration scenarios
   - **Core development**: Implement models, services, CLI commands, endpoints
   - **Integration work**: Database connections, middleware, logging, external services
   - **Polish and validation**: Unit tests, performance optimization, documentation
   - **Validate every project-side regen / build / codegen command**: Whenever a task invokes a project wrapper (e.g. `cws_py_cmd …`, `make generate`, `bazel build //…`, `npm run codegen`, `pnpm build`), a fail-open EXIT=0 from the dispatcher is NOT sufficient evidence of success — wrapper dispatchers commonly print `command not found` / `module not found` / `cmdline not registered` while still exiting 0. After each such invocation you MUST verify success by ONE of the following:
     1. Run with strict shell semantics: prefix the command with `set -euo pipefail;` (bash) or wrap in a check that asserts `$?` is 0 AND stderr does NOT contain the substrings `not found`, `No module named`, `cmdline ` (project-specific markers should be added per-project).
     2. Inspect a known output artefact's mtime before and after; fail the task if no expected file was modified.
     3. Re-read a canonical generated file (e.g. a regenerated `Dockerfile`, `openapi.yaml`, or generated source) and grep for a sentinel that only appears when regeneration actually ran.
     If verification fails, HALT the run, mark the task as `[ ]` (still open), and surface a clear error pointing to the suspected dispatcher / missing dependency. Do NOT mark the task `[X]`.

8. Progress tracking and error handling:
   - Report progress after each completed task
   - Halt execution if any non-parallel task fails
   - For parallel tasks [P], continue with successful tasks, report failed ones
   - Provide clear error messages with context for debugging
   - Suggest next steps if implementation cannot proceed
   - **IMPORTANT** For completed tasks, mark the task as `[X]` in `tasks.md`.
   - **Deferred tasks are first-class**: if a task cannot be executed in this run because it requires a resource the runtime does not have (real docker daemon, external system access, multi-day backfill, manual sign-off), DO NOT silently leave it `[ ]`. Mark it `[~]` and add a one-line `<!-- deferred: <reason> -->` HTML comment on the row. Also append its ID to `deferred_tasks=` in `verification.log`. The run summary at the end MUST contain a `## Deferred Tasks` block listing every `[~]` row and its reason.
   - Failure ≠ deferral: a task that genuinely tried and errored stays `[ ]` and the run halts (unless [P]); only intentional handoffs become `[~]`.

9. Completion validation:
   - Verify all required tasks are closed: every task is either `[X]` (done) or `[~]` (deferred, see § Deferred Tasks). NO `[ ]` rows may remain. If any `[ ]` remains, the run is NOT complete.
   - Check that implemented features match the original specification
   - Validate that tests pass and coverage meets requirements
   - Confirm the implementation follows the technical plan
   - Report final status with summary of completed work

10. **Pre-Status-Flip Gate** (MANDATORY before advancing Feature status to Implemented):

    This gate enforces the Status State Machine contract. Execute these checks IN ORDER before any status transition:

    1. **Convert deferred tasks**: For every `[ ]` task that was intentionally skipped (requires resources unavailable in this run), convert it to `[~]` with an inline `<!-- deferred: <reason> -->` comment. Do NOT leave deferred work as `[ ]`.
    2. **Zero open-task check**: Run `grep -cE '^\- \[ \]' tasks.md`. If the result is NOT 0, the gate FAILS — refuse to advance status. Either complete the remaining tasks or convert them to `[~]` with justification.
    3. **Verification log completeness**: Confirm that `verification.log` has a `SC-NNN_status=` row for EVERY Success Criterion declared in `requirements.md`. Each status must be one of: `pass`, `fail`, `partial`, `deferred`, `unknown`. If any SC row is missing, add it before advancing.
    4. **Deferred task registry**: If any tasks are `[~]`, verify that `deferred_tasks=` in `verification.log` lists their IDs (comma-separated) and `deferred_reason_summary=` is filled.
    5. **Only if ALL checks pass**: Advance the feature status `Planned → Implemented` per the Feature Integration section below.

11. **Populate the Verification Log** (`REQUIREMENTS_DIR/verification.log`):
    - If the file does not exist, instantiate it from `.specify/templates/verification-log-template.md`.
    - **Seeding (at run start)**: Copy the template, replace `[REQUIREMENTS_KEY]` with the actual key, then enumerate EVERY `SC-NNN` declared in `requirements.md` and emit empty `SC-NNN_status=` / `SC-NNN_value=` / `SC-NNN_note=` rows. This ensures no SC is accidentally omitted.
    - Record the baseline block ONCE at the start of the run (capture `baseline_commit` from `git rev-parse HEAD` before any edits, plus any metric counters needed to evaluate Success Criteria from `requirements.md`).
    - At the end of the run, populate the post-change block, set one `SC-NNN_status=` row per Success Criterion, and list deferred task IDs in `deferred_tasks=`.
    - Do NOT invent a new ad-hoc format — use the template's keys verbatim so `/speckit.review` and CI can parse the result mechanically.

## Feature Integration

The `/speckit.implement` command automatically integrates with the feature tracking system:

- If a `.specify/memory/features.md` file exists, the command will:
  - Detect the current feature directory (format: `.specify/specs/[REQUIREMENTS_KEY]/`)
  - Extract the feature ID from the directory name
  - Update the corresponding feature entry in `.specify/memory/features.md`:
    - Advance status `Planned → Implemented` per the canonical state machine in `.specify/templates/feature-details-template.md` § "Canonical Status State Machine". This transition is the responsibility of `/speckit.implement`, NOT `/speckit.plan`.
    - DoD for the transition: `tasks.md` has zero `[ ]` rows (every task is `[X]` or `[~]`) AND every Success Criterion in `requirements.md` has a `SC-NNN_status=pass|deferred` row in `verification.log`.
    - If ANY task is `[~]` deferred, append ` (deferred: T<comma-list>)` to the row's `Last Updated` cell to keep the deferral visible at index level.
    - Keep the specification path unchanged
    - Update the "Last Updated" date
  - Automatically stage the changes to `.specify/memory/features.md` for git commit

In addition, the **implement phase must re-validate the Feature list**:

- Implementation results may introduce new Features, weaken/replace existing Features, or require Feature deletion.
- Ensure functional/non-functional Feature categorization remains consistent.
- If there are changes, the following must be updated synchronously:
  - `.specify/memory/features/<ID>.md`
  - `.specify/memory/features.md`
- Record the "key changes/notes" brought by implementation in Feature details.

This integration ensures that all feature implementation activities are properly tracked and linked to their corresponding entries in the project's feature index.

Note: This command assumes a complete task breakdown exists in tasks.md. If tasks are incomplete or missing, suggest running `/speckit.tasks` first to regenerate the task list.

## Handoffs

**Before running this command**:

- Run `/speckit.tasks` to ensure a complete, ordered `tasks.md` exists.
- If checklists exist under `checklists/`, complete them or explicitly decide to proceed with known risks.

**After running this command**:

- Run `/speckit.review` to evaluate SDD process quality and propose workflow improvements.
- Optionally run `/speckit.analyze` to catch any spec/plan/tasks drift introduced during implementation.

## Optional: Generate a Git Commit Command

After implementation and validation are complete, generate a directly executable commit command:

```sh
git add -A && git commit -m "{msg}"
```

### Commit Message Generation (based on template)

1. **Load the commit message template**:
   - Preferred: `.specify/templates/commit-template.md`
   - Fallback: `.specify/templates/commit-template.md`

2. **Collect the context needed to render the template** (reuse the previously resolved REQUIREMENTS_DIR when available):
   - `[BRANCH]`: `git rev-parse --abbrev-ref HEAD`
   - `[REQUIREMENTS_KEY]`: Derive from the `REQUIREMENTS_DIR` directory name (e.g., `.specify/specs/NNN-short-name/` → `NNN-short-name`)
   - `[FEATURE_TITLE]`: Prefer reading the title or Feature name from `REQUIREMENTS_DIR/requirements.md`
   - `[TYPE]`: Choose based on the primary nature of the current change (feat/fix/docs/test/chore)
   - `[SCOPE]`: Prefer `[REQUIREMENTS_KEY]`, otherwise derive from `[BRANCH]`
   - `[SUBJECT]`: One-line summary, must be semantically consistent with spec documents and implementation content

3. **Render `{msg}` using the template** and generate the full command:
   - `git add -A && git commit -m "{msg}"`

### Interaction Requirements (must execute)

1. Display the generated `{msg}` and full command verbatim to the user.
2. Clearly prompt the user:
   - Execute the commit now? (yes/no)
   - If you want to rewrite the message, reply with the desired message first, then the command will be regenerated.
3. **Only execute the command when the user explicitly replies yes/proceed/continue**; otherwise stop at the prompt and display stage.