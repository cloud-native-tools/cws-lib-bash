<!-- AUTO-GENERATED from templates/commands/implement.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions.

## Glossary

Consult the project glossary (`.specify/memory/glossary.md`, ambient via the Documentation Map) and apply the protocol in `.specify/shared/workflow/glossary.md`:

- **Before acting on the user input**, map any recorded homophone/confusable variant to its canonical term (correcting voice/dictated input); surface each correction so the user can override it, and defer to the user on ambiguous variants.
- **At wrap-up**, propose any new project-specific terms (`origin=auto`, `status=proposed`), excluding common words; run conflict detection; non-conflicting new terms MUST be written directly and merged into the wrap-up report (non-blocking); only writes that conflict with or overwrite an existing user entry MUST still pause for user confirmation. User-authored entries are authoritative.

## Outline

1. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root; parse REQUIREMENTS_DIR and AVAILABLE_DOCS. All paths must be absolute.

2. **Check checklists status** (if `REQUIREMENTS_DIR/checklists/` exists):
   - Count total/completed/incomplete items per checklist
   - If incomplete: STOP, show table, ask "Proceed anyway? (yes/no)"
     > Gate probe: gate-implement-checklist-waiver — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).
   - If user proceeds: require waiver comment, record in `REQUIREMENTS_DIR/waivers.md`
   - If all complete: proceed automatically

3. **Load context (summary-first — see `.specify/shared/guidelines/token-efficiency.md`)**: preload ONLY tasks.md (REQUIRED) and plan.md (REQUIRED); open data-model.md, contracts/, research.md, quickstart.md on demand as targeted excerpts when the current task needs them — artifacts authored in the same session may be consumed from conversation context after an existence check.

4. **Project Setup Verification**: Create/verify ignore files based on detected tech stack. For detailed patterns per technology, see `.specify/shared/constants/ignore-patterns.md`. Also verify the ignore rules ADMIT every output artifact this run is expected to write (reports, logs, per-session subdirectory files) — a whitelist that misses a nested path surfaces as a silent loss at report-writing time, so check it here with `git check-ignore` on a representative expected path. **Writability pre-probe (fail fast)**: walk every directory named in plan.md's Source Code tree and Mirror Obligations rows and write-bit-probe each (touch-test); report ALL unwritable paths up front — and distinguish the failure class first: **ENOENT (path does not exist)** means the plan likely references a retired/renamed location (fix the plan reference, never chown); **EACCES (permission denied, e.g. root-owned container dirs)** carries the `sudo chown -R $USER <dir>` remedy — do NOT let a phase discover an unwritable target mid-run.

5. **Parse tasks.md**: Extract phases, dependencies, task details (ID, description, file paths, parallel markers [P], `[blockedBy: ...]` tags), execution flow. **Topological order**: a task with a `[blockedBy: Txxx,...]` tag MUST NOT start until every listed blocker is `[X]`; among unblocked tasks follow phase order. In multi-agent runs, claim a task by flipping `[ ]`→`[>]` before working it; never work a task another agent holds at `[>]`. **Task premises are hypotheses**: the factual premises a task row inherits from upstream artifacts (counts, file existence, ordering feasibility) fall under the **Inherited premises** bullet of `.specify/instructions.md` § "Fact, Correctness & Logic Checks (Input Sanity)" — re-measure before acting, and write a premise falsified by execution back into the task row / upstream artifact instead of silently working around it.

6. **Implement feature**:
   - Phase-by-phase; complete each before next
   - **Mechanical write gate**: if `.specify/gate.yaml` exists, run `python3 .specify/scripts/python/gate-check.py <planned-write-paths>` before each phase's edits. Exit 2 (DENY) → do NOT write, report the rule and escalate; exit 1 (CONFIRM) → ask the user before writing; exit 3 (gate unreadable) → surface the problem, do not silently proceed. The gate verdict is mechanical — never argue around it in prose. **Make the verdict observable**: echo it (paths checked,
     exit code, any CONFIRM/DENY rows) in that phase's FIRST progress report. A gate whose invocation depends on the agent
     remembering it each phase is a gate that gets skipped on the phase where it matters, and nothing in the run's output
     distinguishes "gate ran and allowed" from "gate never ran" — so step 7 treats a phase with no recorded verdict as unclosed.
   - Respect dependencies; parallel tasks [P] can run together
   - TDD approach: test tasks before implementation tasks. **Failure attribution first**: when a test goes red, decide whether the defect is in the subject under test or in the assertion itself (fragile text heuristics, wrong expected form) BEFORE changing anything, and state in the progress report which side was fixed and why — mechanically "fixing the subject" to satisfy a wrong assertion corrupts correct work. Two further axes before spending a retry: **assertion contradicts an already-clarified requirement** (the spec decided X and the assertion demands not-X → fix the assertion and cite the clarification), and **external provenance** (a parallel session's in-progress work, or a script resolving the wrong repo root because it was invoked from a mirror copy instead of the canonical one → attribute it externally, scope the acceptance to what you own, and record that evidence instead of consuming the 3-strike budget)
   - Validate every project-side regen/build command (fail-open EXIT=0 insufficient — verify output artifacts). **Evidence form must match artifact class**: generated executables/scripts get a full syntax scan (e.g. `bash -n` for shell) before ANY green claim — green unit tests do not catch breakage only reachable when the artifact runs; and *builds* is not *launches* — an artifact whose contract is to be runnable MUST actually be run at least once.
   - **Batch regens**: when several source edits feed the same derived-artifact set, land the edits first (per logical group or phase), then run ONE regeneration + one gate pass for the batch — a separate regen per source edit multiplies the run's most expensive step while adding no signal.
   - **Shell hygiene (alias-proof)**: destructive/mirror file operations MUST use alias-proof forms (`\rm -f`, `\cp -f`, or `command rm/cp`) and MUST verify the result afterwards (`ls` / `diff -q`) — interactive aliases (`rm -i`, `cp -i`) silently swallow non-interactive deletes/copies while appearing to succeed. **Bulk content substitution**: zero residual of the OLD form proves nothing — the verification MUST assert the NEW form is present and correct (inspect the resulting literals, not just absence counts) and include one behavioral execution, because paths built from fragments (`root / f"{x}/{y}"`) are invisible to any text search.
     **Exit-code traps**: in an `&&` chain, never place a command whose legitimate result is a zero count or an empty match
     (`grep -c`, `grep -q`, `comm`, `diff -q`, `test -d`) before a command that MUST run — `grep -c` exits 1 on zero matches, so
     the chain aborts silently and everything after it (including a `git commit`) never happens while the check itself reports
     success. Use `;`, or append `|| true`, and confirm the chain's tail actually executed
   - **Test runs**: prefer the canonical runner `.specify/scripts/bash/run-tests.sh` (resolves the pytest interpreter once, pipe-safe) for baseline and regression tasks instead of ad-hoc `python -m pytest | tail` pipelines whose exit codes mask interpreter failures. **Baseline captures names, not just counts**: record the baseline with `--names-out <spec-dir>/baseline-failed.txt` and re-run regression the same way, so zero-new-failures is proven by `comm -13 baseline current` instead of count archaeology
   - **Pinned rendering conditions for CLI baselines**: when the baseline snapshots CLI help/table output, capture it under fixed rendering conditions (e.g. `env -u COLUMNS <cmd>` or explicit `COLUMNS=N <cmd>`) and record the condition in the baseline file's header note — Click switches render paths depending on COLUMNS, and an unanchored baseline produces refactor-unrelated false diffs that need a live control experiment to attribute
   - **Assert suite collection, not just totals**: when a task expects a specific suite to run, verify that suite's collection count (`pytest --collect-only -q <path>`) is non-zero / matches intent — pytest only collects `test_*.py` by default, so suites named otherwise (e.g. `contract_*.py`) are silently skipped while the total pass count stays green
   - **Runnable-runner probe**: a baseline whose collection fails (e.g. `No module named pytest`, venv interpreter missing) is a probe FAILURE, not an empty baseline — resolve the interpreter first, then capture the baseline. Before adding files to a directory, grep the test suite for brittle count assertions on that directory (e.g. `test_*_has_ten_*`, hard-coded `len(...) == N`) and update them in the same task
   - **Commit discipline**: wrap-up metadata fix-ups (verification stamps, mirror syncs) go into NEW commits — never `--amend` an already-created commit
   - **Command/template edits**: after editing anything under `.specify/templates/commands/`, regenerate every per-tool copy and the `.specify` mirror with `python3 .specify/scripts/python/regen-command-copies.py` (verify with `--check`) — never hand-sync the 5 tool dirs

7. **Progress tracking**:
   - Report after each completed task
   - Halt on non-parallel task failure; for [P] continue successful, report failed
   - Mark completed: `[X]`. Deferred (resource unavailable): `[~]` with `<!-- deferred: <reason> -->`. Never leave deferred work as `[ ]`.
   - **Evidence-backed closure — Gate Function (IDENTIFY→RUN→READ→VERIFY→CLAIM)**: only mark `[X]` for work you have actually executed and verified. Before every completion claim: IDENTIFY the command that proves the work (test id, build, grep, diff of the named target file) → RUN it now → READ its actual output → VERIFY it proves the claim → only then CLAIM, pasting the fresh output (or its decisive excerpt) in the same message as the claim. Claims phrased as "should pass" / "应该没问题" / predictions of untested behavior are BANNED — stale output from an earlier turn does not count. Do NOT close a task whose named file was not changed.
   - **Order-independent comparison for reorder-prone artifacts**: when an artifact can be reordered (generated from an unordered scan/traversal) or a requirement declares "keep X unchanged", a positional diff or a raw count is NOT acceptable evidence — parse both sides into semantic keys (identifying tuples / keyed maps) and compare them order-independently as sets. Paired inverse value changes in a positional diff are usually a reordering artifact, not a regression: confirm on the semantic keys before "fixing" anything.
   - **Front-loading closure**: when a task's substance was already landed earlier (e.g. a later-story file written ahead of its phase), close it by re-verifying its assertion set against the current tree and recording that evidence in the progress report — never re-perform the work theatrically (revert-then-rewrite), and never tick silently without evidence.
   - **Doc/example evidence**: tasks that add command examples, usage snippets, or feedback records are only `[X]` when the example was actually executed (or its engine invoked) and the output observed. Feedback-record unit ids MUST match the engine's accepted format (`/speckit.<cmd>` or `skill:<name>`) — a record written with a free-form unit id is silently dropped by consolidation queries.

8. **Completion validation**: All tasks `[X]` or `[~]` (no `[ ]` remaining). Features match spec. Tests pass. **Completion Gate re-validation**: if tasks.md contains a `## Completion Gate` section, do NOT trust the all-tasks-done state — re-validate every gate item against the current tree (running its stated check), and treat any failing item as an open task. Track consecutive gate rejections: after **3** consecutive failed re-validations without a newly closed item, STOP and escalate to the user instead of retrying. **Commit gate**: commit after each task or logical group; in multi-phase runs the **phase boundary** is the default commit unit — commit only after that phase's name-level regression diff (`comm -13 baseline current`) is empty, so every increment is independently bisectable; count-only regression claims are not acceptable evidence. **Approval routing**: each phase-boundary commit goes through ONE explicit approval point — present the phase's commit command and wait for the user's go-ahead, UNLESS the user pre-authorized commits for this run (e.g. "直接提交" / long-run mode), in which case commit without re-asking. A run MUST NOT end with the feature entirely uncommitted while commit commands were never presented: if every approval point was declined or skipped, the wrap-up MUST prominently list the pending uncommitted state and the exact commit command(s) as the final actionable item. **Deletion-surface audit (mechanical, before every phase commit)**: run `git diff --cached --diff-filter=D --name-only` (and the same for the unstaged tree before staging) — every listed deletion MUST reconcile against a task row or a user-confirmed cleanup plan; an unreconciled deletion aborts the commit for human review (`git add -A` silently carries working-tree destruction into otherwise-green commits — this audit is the backstop). The spec dir MUST NOT be left *entirely* uncommitted when validation completes — an uncommitted implementation leaves no per-task audit trail and breaks `/speckit.review`'s git-based history reconstruction. Do not report the Definition of Done as "met" while the whole feature is uncommitted.

9. **Pre-Status-Flip Gate** and **Verification Log**: Apply the full gate protocol from `.specify/shared/workflow/feature-integration.md` § Pre-Status-Flip Gate. Populate `REQUIREMENTS_DIR/verification.md` from `.specify/templates/verification-log-template.md`.

### Mid-Run User Directives (scope changes DURING implement)

When the user changes scope or adds a design constraint while this command is running, do NOT improvise: apply the Scope Revision Protocol from `.specify/templates/commands/clarify.md` adapted to implement:

1. **Upstream first**: amend `requirements.md` (FR/SC/entities/edge cases) and record the directive verbatim under `## Clarifications` (dated, append-only — never replace existing rows), then cascade to plan/contracts as needed.
2. **Append tasks, never renumber**: new work lands as new `T0NN` rows appended to `tasks.md` (marked to the relevant story or Polish); existing IDs and history stay intact.
3. **Re-verify the touched surface**: re-run the affected contract/integration batch plus mirror checks before continuing the phase sequence.
4. **Leave a trace**: note the directive and its landing (FRs, tasks, commits) in `verification.md` `notes=`.

### Optional: Long-Run Mode (self-iterating until Completion Gate green)

Activated ONLY when the user explicitly requests it (e.g. "run to completion", "long-run mode"). Turns the single pass into a bounded loop driven by a state file — works on all supported agent tools as pure prompt flow (no Stop-hook required).

1. **State file**: create `REQUIREMENTS_DIR/implement-loop.local.md` (git-ignored) with frontmatter: `iteration: 0`, `max_iterations: <user-set, default 5>`, `stagnation_strikes: 0`, `last_closed_count: <current [X] count>`.
2. **Loop**: at what would normally be wrap-up, if open (`[ ]`/`[>]`) tasks remain AND the state file exists: increment `iteration`, re-read tasks.md, and re-enter task selection (step 5) instead of ending.
3. **Completion promise**: the loop ends successfully ONLY when the Completion Gate (step 8) re-validates green — not when tasks merely look done.
4. **Hard caps (all mechanical, no judgment)**:
   - `iteration >= max_iterations` → STOP, report remaining open tasks.
   - **Stagnation two-strike**: at each iteration boundary compare closed-task count to `last_closed_count`; no new closure → `stagnation_strikes += 1`, else reset to 0. Two consecutive strikes → STOP and escalate (something is structurally blocked; more iterations won't fix it).
5. **Exit**: on any stop (success, cap, stagnation, user interrupt), delete the state file and report: iterations used, tasks closed per iteration, gate status, and remaining open/deferred tasks.

## Feature Integration

Apply [Feature Integration Protocol](.specify/shared/workflow/feature-integration.md). This command's transition: `Planned → Implemented` (requires gate pass).

## Optional: Git Commit

Fallback for runs whose phase-boundary commits were declined or skipped (see the Commit gate's approval routing in step 8). After implementation, generate commit command using `.specify/templates/commit-template.md`:
- Collect: BRANCH, REQUIREMENTS_KEY, FEATURE_TITLE, TYPE, SCOPE, SUBJECT
- Display `git add -A && git commit -m "{msg}"` — only execute on explicit user approval

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.implement" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Handoffs

**Before**: `/speckit.tasks` to ensure complete tasks.md exists.

**After**: `/speckit.review` for SDD process quality evaluation. Optional `/speckit.analyze` for drift detection.