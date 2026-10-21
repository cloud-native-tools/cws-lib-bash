---
name: implement-feature
description: Execute the current feature's implementation end to end — verify project setup, parse tasks.md into a topological execution order, implement phase by phase with TDD and evidence-backed closure (IDENTIFY→RUN→READ→VERIFY→CLAIM), re-validate the Completion Gate against the current tree, and land phase-boundary commits; also owns mid-run scope revision handling and the optional long-run self-iterating loop. Use this when the user mentions ["implement the feature", "implement tasks", "run implementation", "implement all tasks", "按 tasks.md 实现", "实现任务", "开始实现", "继续实现", "执行实现", "全部任务实现", "long-run mode", "run to completion", "跑到完成", "长跑模式"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/implement-feature/SKILL.md>"
---

# implement-feature

## Goal

Turn the current feature's `tasks.md` into a **completed, verified, committed
implementation**: every task `[X]` (or honestly `[~]`), the Completion Gate re-validated
against the current tree, and each phase boundary committed. This skill owns the
executable core of `/speckit.implement` — steps 1–9, mid-run scope revision, the long-run
loop, and the commit discipline — while the command template keeps entry, the `scripts:`
block, user-input handling, and the wrap-up lifecycle (Feature Integration / Feedback /
Documentation / Handoffs).

Canonical extraction source: `.specify/templates/commands/implement.md` § Outline (steps 1–9), §
Mid-Run User Directives, § Optional: Long-Run Mode, the Fast Fail instance pointer, and §
Optional: Git Commit. Content moved here verbatim in substance.

## Input Contract

- **Feature artifacts**: `REQUIREMENTS_DIR` and `AVAILABLE_DOCS` come from the command's
  `{SCRIPT}` prerequisite run (its `scripts:` entry resolves to
  `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`); all paths
  must be absolute. `tasks.md` and `plan.md` are REQUIRED inputs (step 3).
- **User parameters**: arrive already processed by the command's User Input Protocol —
  treated as command parameters, never as standalone instructions.
- **Long-run activation**: only an explicit user request ("run to completion" /
  "long-run mode") turns on Long-Run Mode below; it is never self-activated.
- **Multi-agent runs**: tasks may be claimed across agents via the `[>]` marker protocol
  (step 5).

## Workflow (steps 1–9)

### Step 0 — Baseline pre-flight (re-capture frozen values)

Before any other workflow step, re-capture every frozen baseline this feature
carries. The set is derived from the spec directory by glob —
`<spec-dir>/baseline-*` and `<spec-dir>/notes/baseline-*` — plus the coverage
baseline file (`<spec-dir>/coverage-baseline.txt`, [[STR-002]]); it is
directory-derived, never a hand-written count. For each captured value that
differs from the frozen file, the new value MUST be written into the row that
cites it, and every difference MUST be classified — BEFORE any drift verdict is
issued — using `git log` provenance into exactly one of: `upstream repair`,
`inherited`, `attributable to this feature`, or `undecidable`. `undecidable`
MUST be reported explicitly; you MUST NOT guess between the three attributed
classes. A missing baseline file is handled as a first capture with its
provenance recorded — never as zero drift.

### Step 1 — Prerequisites and paths

Run `{SCRIPT}` from repo root; parse `REQUIREMENTS_DIR` and `AVAILABLE_DOCS`. All paths
must be absolute.

### Step 2 — Checklist exemption gate

If `REQUIREMENTS_DIR/checklists/` exists, check checklist status first:

- Count total/completed/incomplete items per checklist.
- **Third branch — recheck answered**: an item whose subject a later stage resolved and
  recorded in `checklists/recheck-<date>-<topic>.md` (the append-only C-8 shape) counts
  as answered — not incomplete, no waiver needed. Subtract it before counting; the gate
  fires only for genuinely unresolved items.
- If genuinely unresolved items remain: STOP, show table, ask **"Proceed anyway? (yes/no)"**.
  > Gate probe: gate-implement-checklist-waiver — after the user decision, record firing
  > evidence per `.specify/shared/guidelines/confirmation-gates.md` §门控观察协议
  > (non-blocking).
- If user proceeds: require a waiver recorded in `REQUIREMENTS_DIR/waivers.md` carrying
  all four parts — `Scope`, `Basis`, `Disposition`, `Closed`. `Closed` MUST state what
  solved the item (which upstream artifact edit closed it). A waiver missing any part is
  non-compliant and MUST NOT be treated as closed evidence.
- If all complete (or answered): proceed automatically.

### Step 3 — Load context (summary-first)

Preload ONLY `tasks.md` (REQUIRED) and `plan.md` (REQUIRED); open `data-model.md`,
`contracts/`, `research.md`, `quickstart.md` on demand as targeted excerpts when the
current task needs them — artifacts authored in the same session may be consumed from
conversation context after an existence check. The summary-first discipline is owned by
`.specify/shared/guidelines/token-efficiency.md` (read it; do not restate it).

### Step 4 — Project Setup Verification

- Create/verify ignore files based on detected tech stack — the per-technology patterns
  are owned by `.specify/shared/constants/ignore-patterns.md` (consult it; never guess patterns).
- Verify the ignore rules ADMIT every output artifact this run is expected to write
  (reports, logs, per-session subdirectory files) — a whitelist that misses a nested path
  surfaces as a silent loss at report-writing time, so check it here with `git check-ignore`
  on a representative expected path.
- **Writability pre-probe (fail fast)**: walk every directory named in plan.md's Source
  Code tree and Mirror Obligations rows and write-bit-probe each (touch-test); report ALL
  unwritable paths up front — and distinguish the failure class first: **ENOENT (path does
  not exist)** means the plan likely references a retired/renamed location (fix the plan
  reference, never chown); **EACCES (permission denied, e.g. root-owned container dirs)**
  carries the `sudo chown -R $USER <dir>` remedy — do NOT let a phase discover an
  unwritable target mid-run.

### Step 5 — Parse tasks.md

- Extract phases, dependencies, task details (ID, description, file paths, parallel
  markers `[P]`, `[blockedBy: ...]` tags), execution flow.
- **Topological order**: a task with a `[blockedBy: Txxx,...]` tag MUST NOT start until
  every listed blocker is `[X]`; among unblocked tasks follow phase order.
- **Multi-agent claim**: in multi-agent runs, claim a task by flipping `[ ]`→`[>]` before
  working it; never work a task another agent holds at `[>]`.
- **Task premises are hypotheses**: the factual premises a task row inherits from upstream
  artifacts (counts, file existence, ordering feasibility) fall under the **Inherited
  premises** bullet of `.specify/instructions.md` § "Fact, Correctness & Logic Checks
  (Input Sanity)" — re-measure before acting, and write a premise falsified by execution
  back into the task row / upstream artifact instead of silently working around it.

### Step 6 — Implement feature

Phase-by-phase; complete each before next. Respect dependencies; parallel tasks `[P]` can
run together.

**Mechanical write gate**: if `.specify/gate.yaml` exists, run
`python3 .specify/scripts/python/gate-check.py <planned-write-paths>` before each phase's
edits. Exit 2 (DENY) → do NOT write, report the rule and escalate; exit 1 (CONFIRM) → ask
the user before writing; exit 3 (gate unreadable) → surface the problem, do not silently
proceed. The gate verdict is mechanical — never argue around it in prose. **Make the
verdict observable**: echo it (paths checked, exit code, any CONFIRM/DENY rows) in that
phase's FIRST progress report. A gate whose invocation depends on the agent remembering it
each phase is a gate that gets skipped on the phase where it matters, and nothing in the
run's output distinguishes "gate ran and allowed" from "gate never ran" — so step 7 treats
a phase with no recorded verdict as unclosed. (`gate-check.py` stays an invocation
instruction here — its rule model is owned by the script itself.)

**TDD with failure attribution first**: test tasks before implementation tasks. When a
test goes red, decide whether the defect is in the subject under test or in the assertion
itself (fragile text heuristics, wrong expected form) BEFORE changing anything, and state
in the progress report which side was fixed and why — mechanically "fixing the subject" to
satisfy a wrong assertion corrupts correct work. Two further axes before spending a retry:

- **assertion contradicts an already-clarified requirement** (the spec decided X and the
  assertion demands not-X → fix the assertion and cite the clarification);
- **external provenance** (a parallel session's in-progress work, or a script resolving
  the wrong repo root because it was invoked from a mirror copy instead of the canonical
  one → attribute it externally, scope the acceptance to what you own, and record that
  evidence instead of consuming the 3-strike budget).

**Validate every project-side regen/build command** (fail-open EXIT=0 insufficient —
verify output artifacts). **Evidence form must match artifact class**: generated
executables/scripts get a full syntax scan (e.g. `bash -n` for shell) before ANY green
claim — green unit tests do not catch breakage only reachable when the artifact runs; and
*builds* is not *launches* — an artifact whose contract is to be runnable MUST actually be
run at least once.

**Batch regens**: when several source edits feed the same derived-artifact set, land the
edits first (per logical group or phase), then run ONE regeneration + one gate pass for
the batch — a separate regen per source edit multiplies the run's most expensive step while
adding no signal.

**Shell hygiene (alias-proof)**: destructive/mirror file operations MUST use alias-proof
forms (`\rm -f`, `\cp -f`, or `command rm/cp`) and MUST verify the result afterwards (`ls`
/ `diff -q`) — interactive aliases (`rm -i`, `cp -i`) silently swallow non-interactive
deletes/copies while appearing to succeed. **Bulk content substitution**: zero residual of
the OLD form proves nothing — the verification MUST assert the NEW form is present and
correct (inspect the resulting literals, not just absence counts) and include one
behavioral execution, because paths built from fragments (`root / f"{x}/{y}"`) are
invisible to any text search. **Mutation-drill restore**: when a drill deliberately breaks
a subject to prove a guard goes red, restore it by EXACT reverse substitution and
`assert count == 1` on the restored literal, then prove recovery by re-running the case
AND confirming that file's `git diff` is empty — MUST NOT read a `cp` exit code as proof
of restore, because an interactive `cp -i` alias no-ops while still returning success.

**Exit-code traps**: in an `&&` chain, never place a command whose legitimate result is a
zero count or an empty match (`grep -c`, `grep -q`, `comm`, `diff -q`, `test -d`) before a
command that MUST run — `grep -c` exits 1 on zero matches, so the chain aborts silently
and everything after it (including a `git commit`) never happens while the check itself
reports success. Use `;`, or append `|| true`, and confirm the chain's tail actually
executed.

**Test runs**: prefer the canonical runner `.specify/scripts/bash/run-tests.sh` (resolves the
pytest interpreter once, pipe-safe) for baseline and regression tasks instead of ad-hoc
`python -m pytest | tail` pipelines whose exit codes mask interpreter failures.
**Baseline captures names, not just counts**: record the baseline with
`--names-out <spec-dir>/baseline-failed.txt` and re-run regression the same way, so
zero-new-failures is proven by `comm -13 baseline current` instead of count archaeology.

**Pinned rendering conditions for CLI baselines**: when the baseline snapshots CLI
help/table output, capture it under fixed rendering conditions (e.g.
`env -u COLUMNS <cmd>` or explicit `COLUMNS=N <cmd>`) and record the condition in the
baseline file's header note — Click switches render paths depending on COLUMNS, and an
unanchored baseline produces refactor-unrelated false diffs that need a live control
experiment to attribute.

**Assert suite collection, not just totals**: when a task expects a specific suite to
run, verify that suite's collection count (`pytest --collect-only -q <path>`) is non-zero
/ matches intent — pytest only collects `test_*.py` by default, so suites named otherwise
(e.g. `contract_*.py`) are silently skipped while the total pass count stays green.

**Runnable-runner probe**: a baseline whose collection fails (e.g.
`No module named pytest`, venv interpreter missing) is a probe FAILURE, not an empty
baseline — resolve the
interpreter first, then capture the baseline. Before adding files to a directory, grep the
test suite for brittle count assertions on that directory (e.g. `test_*_has_ten_*`,
hard-coded `len(...) == N`) and update them in the same task.

**Commit discipline**: wrap-up metadata fix-ups (verification stamps, mirror syncs) go
into NEW commits — never `--amend` an already-created commit.

**Command/template edits**: after editing anything under `.specify/templates/commands/`, regenerate
every per-tool copy and the `.specify` mirror with
`python3 .specify/scripts/python/regen-command-copies.py` (verify with `--check`) — never hand-sync
the 5 tool dirs.

### Step 7 — Progress tracking

- Report after each completed task.
- Halt on non-parallel task failure; for `[P]` continue successful, report failed.
- Mark completed: `[X]`. Deferred: `[~]` with `<!-- deferred: <reason> -->` — the reason
  domain covers BOTH a resource unavailable this round AND an exhaustive requirement that
  cannot be completed this round; a `[~]` is an honest non-green, not a state to hide.
  Never leave deferred work as `[ ]`. When a `[~]` makes the Completion Gate (step 8) fail,
  that fail is an EXPECTED outcome — it MUST NOT be turned green by rewriting the task
  description or relaxing the gate criteria (the task-side disposition forms are owned by
  `.specify/templates/commands/tasks.md`).
- **Evidence-backed closure — Gate Function (IDENTIFY→RUN→READ→VERIFY→CLAIM)**: only mark
  `[X]` for work you have actually executed and verified. Before every completion claim:
  IDENTIFY the command that proves the work (test id, build, grep, diff of the named target
  file) → RUN it now → READ its actual output → VERIFY it proves the claim → only then
  CLAIM, pasting the fresh output (or its decisive excerpt) in the same message as the
  claim. Claims phrased as "should pass" / "应该没问题" / predictions of untested behavior
  are BANNED — stale output from an earlier turn does not count. Do NOT close a task whose
  named file was not changed.
- **Order-independent comparison for reorder-prone artifacts**: when an artifact can be
  reordered (generated from an unordered scan/traversal) or a requirement declares "keep X
  unchanged", a positional diff or a raw count is NOT acceptable evidence — parse both
  sides into semantic keys (identifying tuples / keyed maps) and compare them
  order-independently as sets. Paired inverse value changes in a positional diff are
  usually a reordering artifact, not a regression: confirm on the semantic keys before
  "fixing" anything.
- **Front-loading closure**: when a task's substance was already landed earlier (e.g. a
  later-story file written ahead of its phase), close it by re-verifying its assertion set
  against the current tree and recording that evidence in the progress report — never
  re-perform the work theatrically (revert-then-rewrite), and never tick silently without
  evidence.
- **Doc/example evidence**: tasks that add command examples, usage snippets, or feedback
  records are only `[X]` when the example was actually executed (or its engine invoked)
  and the output observed. Feedback-record unit ids MUST match the engine's accepted
  format (`/speckit.<cmd>` or `skill:<name>`) — a record written with a free-form unit id
  is silently dropped by consolidation queries.

### Step 8 — Completion validation

All tasks `[X]` or `[~]` (no `[ ]` remaining). Features match spec. Tests pass.

- **Completion Gate re-validation**: if tasks.md contains a `## Completion Gate` section,
  do NOT trust the all-tasks-done state — re-validate every gate item against the current
  tree (running its stated check), and treat any failing item as an open task. Track
  consecutive gate rejections: after **3** consecutive failed re-validations without a
  newly closed item, STOP and escalate to the user instead of retrying. This counter has
  **run scope** — it resets to zero at the start of every run (it is never a cross-run
  total), and its current value is written into `verification.md` so a resumed run reads
  the real count instead of inheriting a stale one.
- **Gate-premise decay** (named action): when a premise a gate item or DoD row rests on —
  a frozen SHA, a line number, a count — is falsified by measurement, re-reference the
  premise, measure the new form **more strictly, never more loosely**, and annotate the
  falsified premise inline on that row; a gate item or DoD row whose premise is measurably
  false is **void**, not unmet, and the void rule with its surfacing duty is owned by
  `.specify/shared/workflow/feature-integration.md` § Pre-Status-Flip Gate (which binds
  `## Completion Gate` items exactly as it binds DoD rows).
- **Commit gate**: commit after each task or logical group; in multi-phase runs the
  **phase boundary** is the default commit unit — commit only after that phase's name-level
  regression diff (`comm -13 baseline current`) is empty, so every increment is
  independently bisectable; count-only regression claims are not acceptable evidence.
- **Legitimate-transient exception** (owner:
  `docs/reference/history/00-cross-cutting-lessons.md` §二十二): when an existing guard
  goes red purely because of task ORDERING — a discipline truth-source lands in one phase
  while its reachability pointer lands in the next — the red is a legitimate transient,
  not a regression. Do NOT commit a known-red increment; combine the two phases into ONE
  commit unit whose criterion is that the MERGED `comm -13 baseline current` is empty, and
  attribute it explicitly as an ordering transient (neither a subject defect nor an
  assertion defect).
- **Approval routing**: phase-boundary commits are pre-authorized by default in
  multi-phase runs; single-phase runs keep the explicit approval point.
  - **Multi-phase runs (the long-run shape — 任务多、相位多)**: when tasks.md parses
    into more than one phase, every phase-boundary commit is pre-authorized — commit
    WITHOUT presenting an approval question, provided the same safety gates hold as
    for any commit (deletion-surface audit reconciled; that phase's name-level
    regression diff `comm -13 baseline current` empty). Do NOT open a run-start
    question about how phase commits should be authorized (e.g. "长跑的相位边界提交
    如何授权？") — for this shape, pre-authorization IS the rule, not a recommendation
    to offer; only a user who explicitly demands per-phase confirmation gets asked per
    phase.
  - **Explicit pre-authorization (any shape)**: a user statement like "直接提交" /
    long-run mode activation pre-authorizes the run the same way.
  - **Single-phase runs**: present the phase's commit command and wait for the user's
    go-ahead (ONE explicit approval point).
  A run MUST NOT end with the feature entirely uncommitted while commit commands were
  never presented: if every approval point was declined or skipped, the wrap-up MUST
  prominently list the pending uncommitted state and the exact commit command(s) as the
  final actionable item.
- **Deletion-surface audit (mechanical, before every phase commit)**: run
  `git diff --cached --diff-filter=D --name-only` (and the same for the unstaged tree
  before staging) — every listed deletion MUST reconcile against a task row or a
  user-confirmed cleanup plan; an unreconciled deletion aborts the commit for human review
  (`git add -A` silently carries working-tree destruction into otherwise-green commits —
  this audit is the backstop).
- The spec dir MUST NOT be left *entirely* uncommitted when validation completes — an
  uncommitted implementation leaves no per-task audit trail and breaks
  `/speckit.review`'s git-based history reconstruction. Do not report the Definition of
  Done as "met" while the whole feature is uncommitted.

### Step 9 — Pre-Status-Flip Gate and Verification Log

Apply the full gate protocol from `.specify/shared/workflow/feature-integration.md` §
Pre-Status-Flip Gate. Populate `REQUIREMENTS_DIR/verification.md` from
`.specify/templates/verification-log-template.md` — that template OWNS the
`SC-NNN_status` vocabulary, so draw every status from the set it declares and MUST NOT
narrow it to a subset (a gate or DoD row reading `pass|deferred` silently forbids an
honest `partial`).

> Gate probe: gate-implement-evidence-binding — after populating the evidence
> records, run the binding check per the template's declared rules: every sample
> recorded `pass` MUST have a complete evidence row whose archived artifact
> exists, is non-empty, and whose computed SHA-256 equals the recorded hash;
> missing/empty/mismatch is RED naming the sample id and the reason — the failure
> MUST NOT be downgraded to "self-disclosed and continue". A `pass` without a
> complete evidence row is `unverified` and MUST NOT be cited as passing evidence
> anywhere downstream. Record firing evidence per
> `.specify/shared/guidelines/confirmation-gates.md` § 门控观察协议 (non-blocking;
> via the feedback engine `--lifecycle-point`).

### Mid-Run User Directives (scope changes DURING implement)

When the user changes scope or adds a design constraint while the implementation run is
in progress, do NOT improvise: apply the Scope Revision Protocol from
`.specify/templates/commands/clarify.md` adapted to implement:

1. **Upstream first**: amend `requirements.md` (FR/SC/entities/edge cases) and record the
   directive verbatim under `## Clarifications` (dated, append-only — never replace
   existing rows), then cascade to plan/contracts as needed.
2. **Append tasks, never renumber**: new work lands as new `T0NN` rows appended to
   `tasks.md` (marked to the relevant story or Polish); existing IDs and history stay
   intact.
3. **Re-verify the touched surface**: re-run the affected contract/integration batch plus
   mirror checks before continuing the phase sequence.
4. **Leave a trace**: note the directive and its landing (FRs, tasks, commits) in
   `verification.md` `notes=`.

### Optional: Long-Run Mode (self-iterating until Completion Gate green)

Activated ONLY when the user explicitly requests it (e.g. "run to completion", "long-run
mode"). Turns the single pass into a bounded loop driven by a state file — works on all
supported agent tools as pure prompt flow (no Stop-hook required).

1. **State file**: create `REQUIREMENTS_DIR/implement-loop.local.md` (git-ignored) with
   frontmatter: `iteration: 0`, `max_iterations: <user-set, default 5>`,
   `stagnation_strikes: 0`, `last_closed_count: <current [X] count>`.
2. **Loop**: at what would normally be wrap-up, if open (`[ ]`/`[>]`) tasks remain AND the
   state file exists: increment `iteration`, re-read tasks.md, and re-enter task selection
   (step 5) instead of ending.
3. **Completion promise**: the loop ends successfully ONLY when the Completion Gate
   (step 8) re-validates green — not when tasks merely look done.
4. **Hard caps (all mechanical, no judgment)**:
   - `iteration >= max_iterations` → STOP, report remaining open tasks.
   - **Stagnation two-strike**: at each iteration boundary compare closed-task count to
     `last_closed_count`; no new closure → `stagnation_strikes += 1`, else reset to 0. Two
     consecutive strikes → STOP and escalate (something is structurally blocked; more
     iterations won't fix it).
5. **Exit**: on any stop (success, cap, stagnation, user interrupt), delete the state file
   and report: iterations used, tasks closed per iteration, gate status, and remaining
   open/deferred tasks.

## Fast Fail instance pointer

本 skill 中"即停 / 即中止 / 不得静默降级"一类规则是快速失败纪律的既有**实例**;其判据与两份清单的唯一真源是 `.specify/shared/guidelines/fast-fail.md`(本 skill 引用它,MUST NOT 复述它)。

## Optional: Git Commit (fallback)

Fallback for runs whose phase-boundary commits were declined or skipped (see the Commit
gate's approval routing in step 8). After implementation, generate commit command using
`.specify/templates/commit-template.md`:

- Collect: BRANCH, REQUIREMENTS_KEY, FEATURE_TITLE, TYPE, SCOPE, SUBJECT
- Display `git add -A && git commit -m "{msg}"` — only execute on explicit user approval

## Boundaries

- **Entry & lifecycle stay in the command template** `/speckit.implement`: the
  AUTO-GENERATED header, the `scripts:` block, the User Input Protocol, Glossary, Feature
  Integration transition (`Planned → Implemented`), `## Feedback`, `## Documentation`,
  `## Handoffs` and next-command suggestions are command surfaces, not skill content.
- **Feature status flip** happens through the command's Feature Integration step after
  this skill's Pre-Status-Flip Gate passes; the gate protocol itself is owned by
  `.specify/shared/workflow/feature-integration.md` (pointer, never restatement).
- **Task-side disposition forms** (how a `[~]` is recorded and dispositioned on the task
  side) are owned by `.specify/templates/commands/tasks.md` — this skill only consumes and updates
  `tasks.md` rows per the rules above.
- **Standalone scope clarification** (a clarify pass outside a running implementation)
  belongs to `/speckit.clarify`; only the mid-run adaptation above lives here.
- **The mechanical write-gate engine stays an invocation instruction**: this skill carries
  when/how to run `gate-check.py` and what each exit code obligates; the gate's rule model
  is owned by the script and `.specify/gate.yaml`, never restated here.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:implement-feature" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:implement-feature" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:implement-feature" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
