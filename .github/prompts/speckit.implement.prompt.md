## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions.

## Glossary

Consult the project glossary (`.specify/memory/glossary.md`, ambient via the Documentation Map) and apply the protocol in `.specify/shared/workflow/glossary.md`:

- **Before acting on the user input**, map any recorded homophone/confusable variant to its canonical term (correcting voice/dictated input); surface each correction so the user can override it, and defer to the user on ambiguous variants.
- **At wrap-up**, propose any new project-specific terms (`origin=auto`, `status=proposed`), excluding common words; run conflict detection and obtain explicit user confirmation before writing. User-authored entries are authoritative.

## Outline

1. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root; parse REQUIREMENTS_DIR and AVAILABLE_DOCS. All paths must be absolute.

2. **Check checklists status** (if `REQUIREMENTS_DIR/checklists/` exists):
   - Count total/completed/incomplete items per checklist
   - If incomplete: STOP, show table, ask "Proceed anyway? (yes/no)"
   - If user proceeds: require waiver comment, record in `REQUIREMENTS_DIR/waivers.md`
   - If all complete: proceed automatically

3. **Load context**: tasks.md (REQUIRED), plan.md (REQUIRED), data-model.md, contracts/, research.md, quickstart.md (IF EXISTS).

4. **Project Setup Verification**: Create/verify ignore files based on detected tech stack. For detailed patterns per technology, see `.specify/shared/constants/ignore-patterns.md`. Also verify the ignore rules ADMIT every output artifact this run is expected to write (reports, logs, per-session subdirectory files) — a whitelist that misses a nested path surfaces as a silent loss at report-writing time, so check it here with `git check-ignore` on a representative expected path. **Writability pre-probe (fail fast)**: walk every directory named in plan.md's Source Code tree and Mirror Obligations rows and write-bit-probe each (touch-test); report ALL unwritable paths (e.g. root-owned container dirs) up front with the `sudo chown -R $USER <dir>` remedy — do NOT let a phase discover an unwritable target mid-run.

5. **Parse tasks.md**: Extract phases, dependencies, task details (ID, description, file paths, parallel markers [P]), execution flow.

6. **Implement feature**:
   - Phase-by-phase; complete each before next
   - Respect dependencies; parallel tasks [P] can run together
   - TDD approach: test tasks before implementation tasks
   - Validate every project-side regen/build command (fail-open EXIT=0 insufficient — verify output artifacts)
   - **Shell hygiene (alias-proof)**: destructive/mirror file operations MUST use alias-proof forms (`\rm -f`, `\cp -f`, or `command rm/cp`) and MUST verify the result afterwards (`ls` / `diff -q`) — interactive aliases (`rm -i`, `cp -i`) silently swallow non-interactive deletes/copies while appearing to succeed
   - **Test runs**: prefer the canonical runner `.specify/scripts/bash/run-tests.sh` (resolves the pytest interpreter once, pipe-safe) for baseline and regression tasks instead of ad-hoc `python -m pytest | tail` pipelines whose exit codes mask interpreter failures. **Baseline captures names, not just counts**: record the baseline with `--names-out <spec-dir>/baseline-failed.txt` and re-run regression the same way, so zero-new-failures is proven by `comm -13 baseline current` instead of count archaeology
   - **Runnable-runner probe**: a baseline whose collection fails (e.g. `No module named pytest`, venv interpreter missing) is a probe FAILURE, not an empty baseline — resolve the interpreter first, then capture the baseline. Before adding files to a directory, grep the test suite for brittle count assertions on that directory (e.g. `test_*_has_ten_*`, hard-coded `len(...) == N`) and update them in the same task
   - **Commit discipline**: wrap-up metadata fix-ups (verification stamps, mirror syncs) go into NEW commits — never `--amend` an already-created commit
   - **Command/template edits**: after editing anything under `.specify/templates/commands/`, regenerate every per-tool copy and the `.specify` mirror with `python3 .specify/scripts/python/regen-command-copies.py` (verify with `--check`) — never hand-sync the 5 tool dirs

7. **Progress tracking**:
   - Report after each completed task
   - Halt on non-parallel task failure; for [P] continue successful, report failed
   - Mark completed: `[X]`. Deferred (resource unavailable): `[~]` with `<!-- deferred: <reason> -->`. Never leave deferred work as `[ ]`.
   - **Evidence-backed closure**: only mark `[X]` for work you have actually executed and verified. Each closure MUST be justified by concrete evidence (a passing test id, a command/grep result, or a diff of the named target file). Do NOT close a task whose named file was not changed.
   - **Front-loading closure**: when a task's substance was already landed earlier (e.g. a later-story file written ahead of its phase), close it by re-verifying its assertion set against the current tree and recording that evidence in the progress report — never re-perform the work theatrically (revert-then-rewrite), and never tick silently without evidence.
   - **Doc/example evidence**: tasks that add command examples, usage snippets, or feedback records are only `[X]` when the example was actually executed (or its engine invoked) and the output observed. Feedback-record unit ids MUST match the engine's accepted format (`/speckit.<cmd>` or `skill:<name>`) — a record written with a free-form unit id is silently dropped by consolidation queries.

8. **Completion validation**: All tasks `[X]` or `[~]` (no `[ ]` remaining). Features match spec. Tests pass. **Commit gate**: commit after each task or logical group; the spec dir MUST NOT be left *entirely* uncommitted when validation completes — an uncommitted implementation leaves no per-task audit trail and breaks `/speckit.review`'s git-based history reconstruction. Do not report the Definition of Done as "met" while the whole feature is uncommitted.

9. **Pre-Status-Flip Gate** and **Verification Log**: Apply the full gate protocol from `.specify/shared/workflow/feature-integration.md` § Pre-Status-Flip Gate. Populate `REQUIREMENTS_DIR/verification.md` from `.specify/templates/verification-log-template.md`.

### Mid-Run User Directives (scope changes DURING implement)

When the user changes scope or adds a design constraint while this command is running, do NOT improvise: apply the Scope Revision Protocol from `.specify/templates/commands/clarify.md` adapted to implement:

1. **Upstream first**: amend `requirements.md` (FR/SC/entities/edge cases) and record the directive verbatim under `## Clarifications` (dated, append-only — never replace existing rows), then cascade to plan/contracts as needed.
2. **Append tasks, never renumber**: new work lands as new `T0NN` rows appended to `tasks.md` (marked to the relevant story or Polish); existing IDs and history stay intact.
3. **Re-verify the touched surface**: re-run the affected contract/integration batch plus mirror checks before continuing the phase sequence.
4. **Leave a trace**: note the directive and its landing (FRs, tasks, commits) in `verification.md` `notes=`.

## Feature Integration

Apply [Feature Integration Protocol](.specify/shared/workflow/feature-integration.md). This command's transition: `Planned → Implemented` (requires gate pass).

## Optional: Git Commit

After implementation, generate commit command using `.specify/templates/commit-template.md`:
- Collect: BRANCH, REQUIREMENTS_KEY, FEATURE_TITLE, TYPE, SCOPE, SUBJECT
- Display `git add -A && git commit -m "{msg}"` — only execute on explicit user approval

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this command reached its wrap-up stage. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against `/speckit.implement`'s declared purpose and produce a short review plus ≥1 concrete, command-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this command's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id` (e.g. the feature key + a run timestamp); if a nested skill/command already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "/speckit.implement" --unit-type command \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Handoffs

**Before**: `/speckit.tasks` to ensure complete tasks.md exists.

**After**: `/speckit.review` for SDD process quality evaluation. Optional `/speckit.analyze` for drift detection.