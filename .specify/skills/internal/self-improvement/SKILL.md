---
name: self-improvement
description: Execute the self-improvement loop (SI-0…SI-9) for one resolved Execution Subject — the delegated runnable carrier of /speckit.improve. Internal Spec Kit skill; it depends on the .specify/ structure. Use this when the user mentions ["self improvement", "improve loop", "自我提升", "运行判定", "改点", "why what how", "执行改进循环", "improvement dispatch", "improve history"]
skill_id: "<SKILL:.specify/skills/internal/self-improvement/SKILL.md>"
classification: internal
---

# self-improvement

## Goal

Execute the Self-Improvement Loop — **why（当前问题是什么）→ what（哪些方面需要提升）→ how（如何提升）** — for exactly **one** resolved Execution Subject. This skill is the runnable carrier delegated by `/speckit.improve`; the command resolves the subject and stays a thin entry-plus-delegation shell. Goal anchor (Constitution Principle XIII): the Better-Harness goal model in `.specify/shared/guidelines/better-harness.md`.

**Orchestration, not restatement.** This skill names which engine calls to make and carries the loop's routing; every step body, value domain, reason set and red line is owned elsewhere and reached by path — if this text and an owner disagree, the owner wins:

| Owned fact | Owner (referenced, never copied) |
|---|---|
| Execution Subject criteria | `.specify/shared/definitions/self-improvement-definitions.md` § Execution Subject |
| SI-0…SI-9 step bodies, outcomes, completion report | `.specify/shared/workflow/self-improvement-workflow.md` |
| evidence lanes, Step A/B/E, red lines | `.specify/shared/workflow/evidence-step.md` |
| 批评和自我批评 · 证伪尝试 rules | `.specify/shared/guidelines/critique-and-self-critique.md` |
| 改点 identity and boundaries | `.specify/memory/glossary.md` → `改点`; `.specify/shared/workflow/self-improvement-workflow.md` SI-7 |
| write classification and closing report | `.specify/shared/guidelines/confirmation-gates.md` |
| Summary-First / escalation ladder | `.specify/shared/guidelines/token-efficiency.md` |

## Runtime Mode

Internal skill — it depends on the `.specify/` structure. If `${SKILL_WORKDIR}/.specify/` does not exist, the engines and owner files this skill orchestrates are absent: report that the loop cannot run here and stop; do not approximate the flow from memory.

## Input Contract

From the delegating command (`/speckit.improve`) or an equivalent caller:

- **Resolved subject** — exactly one Execution Subject: kind, id, canonical owner path, origin (`self|assisted`), mutation boundary, expected signal, attempt limit. SI-0 resolves identity, origin and boundary; if any is missing or ambiguous, return one targeted question instead of guessing.
- **Step-1 history projection** (optional) — the why segment's engine output, when the caller already ran it.
- **Step-2 frozen candidates** (optional) — the what segment's frozen list, when the caller already ran it.
- **User-stated concern / scope narrowing** — rides along and grounds both digests.

A segment the caller did not pre-compute is executed by this skill on the same surfaces the command records (Segments below). A target that is not an Execution Subject (workflow Entry Contract) ends the run: report, record the observation for later, stop without mutating anything.

## Output Contract

1. **Grounded why digest** — Segment 1.
2. **Frozen what list** — Segment 2 (frozen stays frozen: candidates are neither added nor dropped afterwards — red-line owner: `.specify/shared/workflow/evidence-step.md`).
3. **Routed how dispatch** — per-improver payloads, Segment 3.
4. **Wrap-up report** — mode and why, subject identity and canonical owner, frozen findings and dimension(s), intervention and validation, outcome state, ledger path and next comparison point, residual risks (the list is owned by workflow § Completion Report).

## Workflow

### Segment 1 — why: the subject's run-determination history

1. Read the target's past 运行判定 records: `python3 .specify/scripts/python/run-determination.py --action history --target "<unit-id>" --json` (the `--limit` / `--unsettled` narrowers are the engine's own). The output shape is owned by the engine (`.specify/scripts/python/run-determination.py`): parse what it emits, do not assume fields.
2. Digest under the two MUSTs, binding on every why digest:
   - **Measured vs caller-declared stays visible.** `provenance.declared_by_caller` names the inputs the caller declared at determination time; present every figure with its provenance — never present both kinds as measurements.
   - **`not_evaluated` is not fine.** An axis whose `reason` is non-null was not validly evaluated: report it as not evaluated（未评估）, never as fine, ok, or zero. An empty history proves nothing about past runs (the engine's honesty boundary) — say so explicitly when no records exist.
3. Corroborate through the session-history lane: `python3 .specify/scripts/python/memory-utils.py --action recall --scope session --query "<topic>" --limit <n>` — index rows only; open a body only per the escalation ladder in `.specify/shared/guidelines/token-efficiency.md` with a recorded reason.
4. A non-zero engine exit is a verdict — report it and stop this segment; do not argue around it (exit codes owned by the engine).
5. A clean history is a valid outcome, not an error: report it, then weigh whether the run's own concern still justifies continuing (SI-2's call, workflow).

### Segment 2 — what: qualify and freeze evidence

1. Execute SI-2 per `.specify/shared/workflow/evidence-step.md` Step A/B (referenced, not copied) — reuse fresh evidence or collect:
   - `python3 .specify/scripts/python/evidence-utils.py --action latest --target "<unit-id>"` — a `stale` run is reported and **not consumed silently**;
   - `--action list --target "<unit-id>" --limit <n>` — index entries for past runs;
   - `--action collect --target "<unit-id>" --lanes <lanes>` — when SI-2 decides to collect (the collection contract is evidence-step Step A/B).
2. From a fresh run consume only the per-finding projection and the top-level findings digest — never `findings.json` wholesale, never the raw lane files (Summary-First owner: `.specify/shared/guidelines/token-efficiency.md`).
3. Red lines are inherited by reference from `.specify/shared/workflow/evidence-step.md` § Positioning & Red Lines: `Unobserved` evidence is recorded only, never turned into a defect; count signals route, they never conclude.
4. **Freeze the candidate list** once evidence states are classified. Outcomes are SI-2's (workflow): no qualified candidate → close as no-op and keep the observations; local candidate → Segment 3; cross-subject or systemic candidate → escalate per SI-2 without broad local mutation.

### Segment 3 — how: diagnose, critique, route, apply, validate, record

Run the workflow's steps by reference — `.specify/shared/workflow/self-improvement-workflow.md`:

1. **SI-3 diagnosis** per frozen candidate: locate the causal contract or missing sensor, name the affected Better-Harness dimension by reference to `.specify/shared/guidelines/better-harness.md`, choose the smallest intervention that can change the expected signal. Newly discovered issues start a future loop — no new candidates here.
2. **SI-3C critique — the mandatory gate at the head of dispatch.** Every proposal leaving this segment carries **one executed 证伪尝试 (falsification attempt)**; output form, acceptability criteria and verdict handling are owned by `.specify/shared/guidelines/critique-and-self-critique.md` (referenced, never restated). A falsified premise voids the proposal — never dispatched, never rewritten around the falsified premise and re-dispatched. A proposal without an executed attempt is rejected by the receiving improver (the owner's handover criterion). When the proposal and the critique share an author, the attempt's execution is delegated per `.specify/shared/workflow/objective-analysis-gate.md`. Critique verdicts ride the proposal's existing carrier — no new ledger, registry or store.
3. **SI-4 route** per the workflow's SI-4 table. Each payload assembles the subject fields this skill already holds (Input Contract) plus the frozen candidate and the executed critique verdict, plus the contract-required extra input read from the routed improver's own `SKILL.md` at run time. A command-subject finding has no improver yet — that pending row and its degrade path are owned by `.specify/templates/commands/improve.md` (workflow § Failure and Degradation). The skill does not mutate a subject itself: edits happen only through the routed improver or the workflow's declared assisted/degrade path.
4. **SI-5 apply** per workflow SI-5: edit only the canonical owner; regenerate mirrors through their owning mechanism; the write classification and the closing report follow `.specify/shared/guidelines/confirmation-gates.md` — reversible local edits execute per plan and are reported afterwards in one consolidated wrap-up; the destructive, external, authority-expanding and doubtful cases follow that taxonomy's front-loaded path.
5. **SI-6 validate**: structural contracts and relevant tests. A passing check supports only **intervention applied; outcome pending**.
6. **SI-7 record**: `.specify/shared/workflow/evidence-step.md` Step E — write the intervention ledger beside the baseline evidence run. The ledger is the only intervention record; no parallel self-improvement store is created.
7. **SI-8 / SI-9**: compare on the next comparable run (`evidence-utils.py --action compare`); close or escalate per the workflow — outcome states and the completion report are the workflow's.

## Constraints

1. **Projections only.** Every store read consumes the engine's projection or index; a machine-managed data file is never injected wholesale (Summary-First owner: `.specify/shared/guidelines/token-efficiency.md`).
2. **Non-zero engine exits are verdicts** — report and stop the affected segment; never argued around.
3. **No proposal leaves Segment 3 without an executed 证伪尝试.** The absence is itself the receiving improver's rejection condition.
4. **The skill does not mutate a subject itself.** Mutations go through the routed improver or the workflow's declared assisted/degrade path only.
5. **No new machinery.** No second store, no ledger beyond Step E's, and no aggregate score over the axes — the engine defines none.
6. **Attempt limit is hard.** Reaching it stops automatic iteration; request assisted review (workflow § Failure and Degradation).
7. **Owners outrank this file.** A discrepancy against an owner is reported, never resolved by silent rewording here.

## Self-Improvement Routing

Start every run with SI-0 from `.specify/shared/workflow/self-improvement-workflow.md`; default to `assisted` unless an own-run signal from the same subject is demonstrated. This skill is the loop's carrier, not its own improver: a Skill subject routes to the skill improver per SI-4 — including this skill itself. Report **outcome pending** until SI-8; never call a change "improved" before comparison.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:self-improvement" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:self-improvement" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:self-improvement" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
