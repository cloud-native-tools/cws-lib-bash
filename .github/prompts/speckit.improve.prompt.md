<!-- AUTO-GENERATED from templates/commands/improve.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions.

**Resolve the improvement target first.** An improvement needs an Execution Subject — a repeatedly-invoked artifact with one canonical editable definition (criteria owner: `.specify/shared/definitions/self-improvement-definitions.md` § Execution Subject). From `$ARGUMENTS` resolve exactly **one** target and carry its subject kind through the whole run:

| Target form in `$ARGUMENTS` | Subject kind |
|---|---|
| `/speckit.<command>` | command template |
| `skill:<name>` | Skill |
| an agent artifact (role slug or `.specify/agents/...` path) | agent |
| a tool record (name / alias / `tool_id` under `.specify/memory/tools/`) | tool record |
| a team (slug or `.specify/teams/<slug>/team.md`) | team definition |
| `custom:<owner>/<name>` | host-project custom unit |

`$ARGUMENTS` may also carry scope narrowing — the aspect or concern to prioritize (e.g. one axis of the run determination, a recurring failure, a specific friction the user names). If `$ARGUMENTS` is empty, resolve the target from the current conversation when it is unambiguous (e.g. the run just discussed) and state that resolution; otherwise ask **one** targeted question listing the accepted forms above — do not guess a subject silently. A `custom:<owner>/<name>` target routes by what the artifact actually is after resolution; when no route below fits it, it is a non-subject artifact and follows its normal assisted flow (SI-4's closing sentence). If the stated target resolves to no durable artifact with a canonical owner (e.g. "this session" as a whole), it is not an Execution Subject: per the workflow's Entry Contract no improvement loop runs — report that, record the observation for later (e.g. `/speckit.todo` Park Mode), and stop without mutating anything.

## Glossary

Consult the project glossary (`.specify/memory/glossary.md`) and apply the protocol in `.specify/shared/workflow/glossary.md`: correct recorded homophone/confusable variants before acting; propose new terms at wrap-up with user confirmation.

## Outline

`/speckit.improve` is the **active trigger** of the self-improvement flow: a thin entry-plus-delegation shell. The loop's steps are owned by `.specify/shared/workflow/self-improvement-workflow.md` — referenced below, never copied — and every implementation detail lives on the skill/engine side. This command records which surfaces to call, how to call them, and what each call receives and returns. Three segments:

**why（当前问题是什么）→ what（哪些方面需要提升）→ how（如何提升）**

### Step 1 — why: read the target's run-determination history

```bash
python3 .specify/scripts/python/run-determination.py --action history --target "<unit-id>" --json
```

Optional narrowers: `--limit <n>` (most recent rows; 0 = all), `--unsettled` (only records still awaiting settlement — the engine's own filter for rows whose `settled_at` is null).

- **Consumes**: the resolved target unit id — the engine's `--target` vocabulary is the same unit-id space as the table above.
- **Returns**: a counts block plus one bounded projection row per past record — each axis's `verdict`, `reason` and `signal`, the settlement state (`settled_at`), and `provenance.declared_by_caller`; never a record body, never a raw measurement. The output shape is owned by the engine (`.specify/scripts/python/run-determination.py`): parse what it emits, do not assume fields.
- **Two MUSTs, binding on this step**:
  1. **Measured vs caller-declared stays visible.** `provenance.declared_by_caller` names the inputs the caller supplied at determination time (an `elapsed_ms` or `proxy_paths` entry there marks the corresponding figure as a caller declaration, not a tool-session measurement); the record's `measurement.source` — visible only in the record body, which may be opened solely per the escalation ladder in `.specify/shared/guidelines/token-efficiency.md` with a recorded reason — carries the source hierarchy. Present every figure with its provenance; never present both kinds as measurements.
  2. **`not_evaluated` is not fine.** An axis whose `reason` is non-null was not validly evaluated: report it as **not evaluated**（未评估）, never as fine, ok, or zero. An empty history likewise proves nothing about past runs (the engine's honesty boundary) — say so explicitly when no records exist.
- **Corroboration (session-history lane)**: `python3 .specify/scripts/python/memory-utils.py --action recall --scope session --query "<topic>" --limit <n>` — returns index rows (id, title, summary, tags, score, path), no bodies; open a body only per the escalation ladder. Suggested queries: the command/skill name, `run-determination`, the user's stated concern.
- A non-zero engine exit is a verdict — report it and stop this segment; do not argue around it (the exit-code table is owned by the engine's `EXIT_*` constants).

### Step 2 — what: qualify and freeze evidence

Execute SI-2 per `.specify/shared/workflow/self-improvement-workflow.md` (referenced, not copied):

- Start from the history projection's change-point block of the past records (finding axes plus the `clean` flag — bounded by design; the projection never returns finding bodies) plus the user's stated concern. A clean history is a valid outcome, not an error: report it and weigh whether the run's own concern still justifies continuing.
- Evidence read surface (LLM-investigation conclusions, lane 3):
  - `python3 .specify/scripts/python/evidence-utils.py --action latest --target "<unit-id>"` — returns `runId`, `path`, `created`, `ageDays`, `stale` plus a freshness warning; a `stale` run is reported and **not consumed silently**.
  - `python3 .specify/scripts/python/evidence-utils.py --action list --target "<unit-id>" --limit <n>` — index entries for past runs.
  - From a fresh run, consume only the per-finding projection — `evidence[] | {id, lane, evidenceState, summary, signals}` and the top-level `findingsDigest` — never `findings.json` wholesale, never the `lanes/*` raw files.
  - When no fresh run exists, collect via `python3 .specify/scripts/python/evidence-utils.py --action collect --target "<unit-id>" --lanes <lanes>`; whether to collect is SI-2's call, and the collection contract is `.specify/shared/workflow/evidence-step.md` Step A/B.
- Red lines are inherited by reference from `.specify/shared/workflow/evidence-step.md` § Positioning & Red Lines: `Unobserved` evidence is recorded only, never turned into a defect; count signals route, they never conclude.
- **Freeze the candidate list** once evidence states are classified. Outcomes: no qualified candidate → close as no-op and keep the observations; local candidate → continue to Step 3; cross-subject or systemic candidate → escalate per SI-2 without broad local mutation.

### Step 3 — how: diagnose, critique, route, apply, validate, record

Run the workflow's steps **by reference** — `.specify/shared/workflow/self-improvement-workflow.md`:

1. **SI-3 diagnosis** per frozen candidate: locate the causal contract or missing sensor, name the affected Better-Harness dimension by reference to `.specify/shared/guidelines/better-harness.md`, choose the smallest intervention that can change the expected signal.
2. **SI-3C critique before dispatch**: every proposal carries one falsification attempt, executed before routing. Output form, acceptability criteria and verdict handling are owned by `.specify/shared/guidelines/critique-and-self-critique.md` (referenced, never restated). A falsified premise voids the proposal — it is never dispatched; a proposal without an executed attempt is rejected by the receiving improver.
3. **SI-4 route** via the dispatch table below.
4. **SI-5 apply** — edit only the canonical owner; regenerate mirrors through their owning mechanism. The write classification and the closing report follow `.specify/shared/guidelines/confirmation-gates.md`: reversible local edits execute per plan and are reported afterwards in one consolidated wrap-up（执行报告：执行内容 / 产出工件 / 修改途径）; the destructive, external, authority-expanding and doubtful cases follow that taxonomy and the workflow's own SI-5 clause.
5. **SI-6 validate** — structural contracts and relevant tests; a passing check supports only **intervention applied; outcome pending**.
6. **SI-7 record** — `.specify/shared/workflow/evidence-step.md` Step E: write `intervention.json` beside the baseline evidence run (targetFinding / change / baselineRunId / expectedSignal). No parallel self-improvement store is created; critique verdicts ride the proposal's existing carrier, and the ledger is the only intervention record.
7. **SI-8 compare on the next comparable run; SI-9 close or escalate** — outcome states and the completion report are the workflow's.

### SI-4 dispatch table

Every routed improver receives the same payload — origin (`self|assisted`), the subject ID, the frozen findings, the canonical owner path, the mutation boundary, the expected signal, and the attempt limit — plus the extra input its own contract requires, and returns its own report. Per-improver specifics live in each `SKILL.md` (paths below), not here. Report **outcome pending** until SI-8 (the workflow's Improve-Flow Integration).

| Subject kind | Route to | Contract-required extra input | Returns |
|---|---|---|---|
| agent | `improve-agent` — `.specify/skills/internal/improve-agent/SKILL.md` | the artifact's **layer** (`template` / `instance` / `execution`) stated explicitly — the skill asks rather than infers | a targeted update of the one agent artifact plus an evidence-cited change report with regenerate/retest recommendations |
| Skill | `improve-skills` — `.specify/skills/improve-skills/SKILL.md` | the skill identifier; user-stated requirements ride along as highest-priority input | a focused Skill update plus a driving-evidence report; shape and red-line gates run inside the skill; the Step-E ledger when findings evidence was consumed |
| tool record | `improve-tools` — `.specify/skills/internal/improve-tools/SKILL.md` | the record identifier (name / alias / `tool_id`) | a field-level record edit with a before → after report; the skill never invokes the tool to "test" an improvement |
| team definition | `improve-team` — `.specify/skills/internal/improve-team/SKILL.md` | the team slug; runs-lane evidence is its recommended lane | an updated `team.md` (bumped `updated` date) plus a change report; recommends a validating run |

**Pending row — command subjects.** A command template **is** an Execution Subject, but **no improver exists** for that subject kind yet (conclusion and its five-criteria evidence: the run-determination contract § 13.1). Until one is authorized, degrade to **Assisted Improvement** per the workflow § Failure and Degradation: edit `.specify/templates/commands/<name>.md` in the framework source, regenerate the per-tool copies with `python3 .specify/scripts/python/regen-command-copies.py`, then run SI-6 validation — per-tool copies are generated mirrors, never hand-edited. In a client project (no framework source), a command-subject finding routes through the feedback flow (`/speckit.feedback`) to the upstream instead of editing generated copies. Decider for closing this pending: the **user**, via a `/speckit.team` modify that authorizes a named `skills/` directory for it. This command does not pre-create that directory or its name.

**Delegation — the orchestrating skill.** The three segments execute in `.specify/skills/internal/self-improvement/SKILL.md` (skill `self-improvement`; installed at `.specify/skills/internal/self-improvement/SKILL.md` after the package sync). Dispatch it with the resolved subject (kind, id, canonical owner, origin, mutation boundary, expected signal, attempt limit) plus the Step-1 history projection and the Step-2 frozen candidates when this command has already produced them — the skill runs any segment it did not receive, on the same surfaces recorded above. It returns the grounded why digest, the frozen what list, and the routed how dispatch (per-improver payloads plus the command-subject pending row above) with the wrap-up report. The Steps above remain the record of which engine surfaces each segment calls; execution detail is the skill's.

## Behavior Rules

- **Projections only.** Every store read consumes the engine's projection or index (Summary-First: `.specify/shared/guidelines/token-efficiency.md`); a machine-managed data file is never injected wholesale.
- **Non-zero engine exits are verdicts** — report and stop the affected segment; do not argue around them.
- **The command does not mutate a subject itself.** Edits happen only through the routed improver or the workflow's declared assisted/degrade path.
- **No new machinery.** No second store, no ledger beyond SI-7's `intervention.json`, and no aggregate score over the axes — the engine defines none, and this command must not invent one.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "/speckit.improve" --unit-type command --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "/speckit.improve" --unit-type command`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "/speckit.improve" --unit-type command --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Docs Sync Eval — `.specify/shared/workflow/docs-step.md` § "Evaluation procedure (the embedded step points here)"

## Handoffs

**Before**: none — any Spec Kit project whose `.specify/` assets carry the run-determination engine. Determination records are produced at each qualifying run's wrap-up (wiring owned by `.specify/shared/workflow/feedback-step.md`); a fresh project starts with an empty history and Step 1 says so.

**After**: the routed improver's own report (outcome pending), then SI-8 comparison on the next comparable run; `/speckit.review` for a cross-artifact review; a client project's findings about framework assets route through `/speckit.feedback`.