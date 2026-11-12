---
name: coaching-skills
description: |
  Coach a Skill or a slash-command (the Trainee) through one real work item: state the expected outcome and process efficiency first, dispatch exactly one subagent to execute the Trainee's own SKILL.md (or the resolved command template), observe what actually happens, then report the deviations and a micro-adjustment plan. Use this when the user mentions ["教练", "陪练", "观察执行", "预期 vs 实际", "执行偏差", "微调建议", "coaching"], or invokes it as `coaching-skills <trainee> [<work>]`.
skill_id: "<SKILL:.specify/skills/coaching-skills/SKILL.md>"
classification: external
---

# coaching-skills

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.

## Goal

Coach one Trainee — a Skill or a slash-command — through one real work item: state the
execution expectation first (outcome correctness and process efficiency), dispatch
exactly one subagent to execute the Trainee's own `SKILL.md` (or its resolved command
template), observe what actually happens, compare the two, and hand a micro-adjustment
plan to the existing `improve-skills` entry. The Trainee's real work is the primary
result; optimizing the Trainee is secondary.

## Inputs

Invocation: `coaching-skills <trainee> [<work>]`.

- **One required positional parameter**: the Trainee reference. **`<work>` is
  OPTIONAL** — many skills and commands run without arguments (e.g. `/speckit.status`);
  an empty value dispatches the no-argument form and is never a missing parameter.
- **`Trainee`**: the Trainee reference — a Skill or a command surface. Skill-reference
  forms, normalization order, disambiguation rules and failure semantics are owned by
  `.specify/shared/definitions/skill-reference-definitions.md` — reach them there, and report
  the raw and the normalized identifier plus the decision class. A leading `/` is only
  the surface form (both kinds carry it) and is **never** an instruction to invoke the
  Trainee directly instead of running this loop; the kind is decided by scanning both
  lists in § Trainee Resolution.
- **Meta-skill Trainees are in scope.** When the Trainee itself operates on other
  skills (`improve-skills`, `merge-skills`, `create-skills`, `run-skills`), `<work>` is
  normally a skill-engineering request ("optimize skill X", "merge A into B"); its
  primary artifact is the changed target-skill file set or the Trainee's run report.
  Such a request MUST NOT be reclassified as "not a real work item", and the coach
  MUST NOT execute the Trainee's steps itself in its place.
- `<work>` enters the run and the dispatch payload **verbatim** (an empty value stays
  empty and is recorded as no-argument execution); never rewrite, summarize,
  re-scope it, or fill it on the user's behalf.
- A missing **Trainee** parameter fails closed and names it; an empty `<work>` is
  legal. Missing-argument handling is a plain one-sentence clarification, then stop.
  It is not a confirmation step.

## Trainee Resolution

**First decide what kind of executor the Trainee names — resolve it by scanning both
lists, never by syntax.** A leading `/` is NOT a discriminator: skills
(`/improve-skills`, `/coaching-skills`) and command surfaces (`/speckit.status`) both
carry it.

- **Scan both lists** with the leading `/` stripped: (a) the **Skill** set through the
  position ladder below (directory name or frontmatter `name`); (b) the **Command** set
  through the canonical templates `.specify/templates/commands/<name>.md` (a `speckit.` prefix
  also maps to `<name>.md`), then their generated per-tool copies as aliases.
- Exactly one hit decides the executor kind: a **Skill** (decision class `skill`
  internal/external/installed) or a **Command** (decision class `command`; the template
  body is its execution contract).
- **Two hits of different kinds fail closed naming both candidates** — a skill and a
  command sharing the normalized name are ambiguous and the user disambiguates; two hits
  inside the skill ladder fail closed the same way; zero hits name the raw form and the
  searched coordinates of both lists. Never pick the nearest.
- The recursion guard (§ below) applies to whichever branch resolved.

Scan coordinates, aliases and the full failure table:
[`references/trainee-resolution.md`](./references/trainee-resolution.md).

Reuse the `run-skills` position ladder, with no second resolution rule: canonical
internal → canonical external → installed internal → installed external.

- Normalize the `Trainee` reference first, by the owner document cited under § Inputs
  (the order and the failure semantics live there, not here); report the raw identifier, the
  normalized identifier and the decision class in the run output.
- A source hit and its installed mirror hit are one hit for the same skill; only two
  distinct layers carrying the same name are two hits.
- Two hits: fail closed naming both candidate paths; never pick the nearest.
- Zero hits: fail closed naming the raw and normalized identifier and the searched coordinates.
- Reject before the expectation phase when the resolved executor is unreadable: a skill
  directory without a readable `SKILL.md`, or a command without a readable template,
  or either with invalid frontmatter.
- Reject a target that resolves to `coaching-skills` itself: recursion depth is 1 and
  no dispatch happens.
- When the host can only load by explicit path, use the `run-skills` explicit-path
  mode and record it in the DispatchRecord `mode`.
- Read the Trainee's `SKILL.md` and the reference files it needs; change nothing and
  trigger no Trainee side effect in this phase.

## Nested (chain) runs

A meta-skill Trainee may itself target the skill actually changed (`caller → Trainee →
subject`). The four duties — the Trainee resolves the subject, expectation and verdict
target the subject, the write lock follows the subject, and depth is one dispatch edge per
perspective with claim-before-dispatch plus the subject guards — are owned in full by
[`references/nested-runs.md`](./references/nested-runs.md); this body states the branch
only and never a second copy.

## Preflight

Run these checks in order before writing any artifact:

1. the Trainee parameter is present and resolves to exactly one executor — a command
   template or a skill hit — with valid frontmatter and a target other than this skill;
2. `<work>` is optional: an empty value is legal (no-argument execution) and is never
   treated as a missing parameter;
3. when the Trainee is a meta-skill, `<work>` names an identifiable subject to operate
   on; if it is empty, ask one targeted clarification and stop (never pick the subject);
4. the run directory does not already exist (see § Run Identity).

Any failure stops the run before the expectation phase and names what failed and
where it was searched. A run that passes preflight proceeds to write the expectation;
nothing else is a precondition.

## Run Identity

- `run-id`: `YYYYMMDDTHHMMSSZ-<trainee-slug>` — a UTC timestamp plus the lowercase
  kebab slug of the resolved Trainee name. For a command Trainee the slug is the
  command name's kebab form (`/speckit.status` → `speckit-status`).
- Run directory: `.specify/memory/coaching/<run-id>/`, created before the expectation
  is written.
- If the directory already exists the run fails closed naming the existing path;
  MUST NOT append a suffix and MUST NOT reuse the directory.
- All four artifacts live inside the run directory; no artifact path escapes it.

## Artifacts and Order

Exactly four files, in this order:

1. `expectation.md`
2. `observation.md`
3. `deviations.md`
4. `improvement-plan.md`

- `expectation.md` MUST land on disk before the first action of the dispatched
  subagent. The DispatchRecord field `dispatched-at` is the ordering evidence.
- Observation, deviations and improvement plan follow in that order; a missing file
  fails the run regardless of how good the others are.
- The two closed status values are recorded once, in `improvement-plan.md` § Run
  Status.

## Execution First

- The primary success condition is: the Trainee's real work completed and its primary
  artifact exists — an artifact path or checkable conclusion for a skill; the command's
  output or invocation record for a command.
- Optimization MUST NOT be a precondition of execution and MUST NOT shorten, redirect,
  or simplify the execution to collect optimization material.
- The coach MUST NOT run any Trainee step in parallel with the subagent.

## Single Dispatch

- Dispatch exactly one subagent per run. A failed, timed-out, or refused dispatch is
  recorded as such and never retried inside the same run.
- After a failed dispatch, continue into `deviations.md` and `improvement-plan.md` —
  continue means exactly that and nothing more.
- The coach never executes Trainee steps itself and never injects side effects into
  the subagent's work.

## Dispatch Payload

The payload is a closed field set; anything not listed below is forbidden.

| Field | Content | Rule |
|-------|---------|------|
| `trainee` | resolved identifier, resolved path, executor kind (`skill` or `command`), and the layer for a skill | the exact path this run resolved; no alternatives offered |
| `workdir` | the project root the Trainee must treat as `${SKILL_WORKDIR}` | a subagent does not inherit this conversation's cwd; omitting it leaves every `.specify/...` reference ambiguous |
| `work` | `<work>` verbatim | byte-for-byte the second positional parameter; an empty value IS the no-argument form, never a missing parameter |
| `instruction` | for a skill: "Follow the Trainee's own `SKILL.md` as the highest execution guidance"; for a command: "Execute the resolved command template exactly; `<work>` (possibly empty) is its argument set — an empty `<work>` is the no-argument form" | never replaced by a coach-authored procedure |
| `return-contract` | step-by-step actions, tool calls, state changes, artifacts, elapsed time, terminal state — plus, when the Trainee is a meta-skill: `subject {ref, path}`, the subject's changed files, and the claim taken or skipped | powers `self-report` when host events are unavailable |
| `anomaly-line` | "State one explicit anomaly line on return; state `none` when there is none" | silence is not read as clean |
| `fast-fail-clause` | the dispatcher's anomaly discipline | injected at dispatch time; a subagent does not inherit this conversation |
| `confirmation-relay` | "If the Trainee flow reaches a destructive step **or needs a targeted clarification**, stop and report it back instead of approving or guessing" | the answer comes from the user; the subagent never self-approves and never substitutes a guess |
| `reporting-cadence` | the tick value in force for this run, plus the attribution pair (structure slug + run stamp) the subordinate's own lines must carry | the value is the resolved profile's cadence; the subordinate reports its own progress on it and the coach reports the subordinate's state on it |

The payload MUST NOT contain:

1. the expectation file, any `OC-*` / `PE-*` row, or a summary of them;
2. the coach's deviation guesses or conclusions about `<work>`;
3. a coach-authored simplification or reordering of the Trainee flow;
4. any artifact path inside the run directory — the subagent writes Trainee outputs,
   not coach records;
5. the coach's own status lines or its expected subordinate-state conclusions — the
   subordinate is never told what its state will be judged as.

Exactly one payload is dispatched per run. A failed dispatch is not re-sent with a
modified payload; the failure is recorded instead.

On return, the anomaly line is written into the DispatchRecord unchanged. Self-reported
steps become `self-report` rows, and anything the self-report does not cover becomes an
`observation-gap` row rather than an inferred one. The Trainee's own reported state at
return is recorded verbatim as a `self-report` row: when the coach's report cites that
state it cites `self-report`, and it MUST NOT infer the state from host events or from
the silence of the Trainee's output. A return that claims completion
without the Trainee's primary artifact is recorded as `partial`, not `completed`.

The transport — `native` host subagent tool, `run-agent-fallback`, or
`run-skills-explicit-path` mode — is recorded in the DispatchRecord `mode` field, and the
rendered payload is stored or referenced by `payload-ref`. The payload's raw text never
enters the coach's user-facing report.

## Sub-flow Report

The Trainee dispatch is the sub-flow this run reports. On the tick in force for the run,
the coach reports that one dispatch — not an empty set, and not merely the coach's own
progress — with its **identity** (the dispatch's label), its **state** and the **age** of
its last observed activity. The state and the age come from the Trainee's own reported
state at return once it is available, and from the artifact triplet the dispatch already
declares before that; the coach cites `self-report` rather than inferring.

An omission is a defect, not a sampling decision: a dispatch this run made and did not
report on a tick is named by its label, and a failure or a stall crossing is reported
before the next tick rather than waiting for the clock.

**This section demonstrates the duty; it does not define it.** Scope, cadence, the stall
threshold and the transition classes are owned by
`.specify/shared/guidelines/reporting-obligations.md` — reach them there. This skill MUST NOT
restate any of them, because a restatement would make the shipped example a second
definition of the obligation. The label convention is owned by
`.specify/shared/definitions/subagent-definitions.md` § External Dispatch Visibility Contract.

## Compare

Write `deviations.md` by comparing the expectation with the observation on both
dimensions: `## Outcome Correctness` and `## Process Efficiency`.

- Every finding cites concrete evidence from `observation.md`: a step id and/or an
  artifact path.
- Classify every finding `result-deviation` or `process-deviation`; a partially
  completed Trainee flow separates the two classes.
- State where the coach's reading of `<work>` and the Trainee's actual
  reading/execution materially diverged beyond normal execution noise.

## Improvement Plan

Write `improvement-plan.md` with entries ordered by priority.

- Each entry names a concrete Trainee file and section plus one concrete tweak;
  generic advice ("improve clarity", "be more careful") is invalid.
- Each entry cites `D-*` findings, or is marked `evidence: none` when no execution
  evidence exists.
- When observation is empty the plan is still produced; it is never dropped for lack
  of evidence.

## Optimization

- Apply the plan through the existing `improve-skills` entry, passing the Trainee
  target and the deviation evidence. Do not rewrite Trainee files directly and do not
  change that entry's contract.
- Claim protocol: the sole owner is `data-model.md` § Optimization claim. Apply that
  section's single timing (after the execution loop and the plan are written, before
  `improve-skills` is invoked), its atomic creation, its conflict rule and its
  release/leftover semantics exactly as written there. This skill states no second
  version and never decides a claim by scanning run directories or by any
  read-then-write sequence.
- A claim conflict fails the step closed: record `optimization: failed` and name the
  conflicting run-id, as the owner's conflict rule prescribes.
- A rejection by `improve-skills` is recorded as `optimization: failed` (or
  `unavailable` when the entry cannot be resolved); never retry in a loop.

## Run Status

Record both values once, in `improvement-plan.md` § Run Status:

- `run:` one of `success`, `partial`, `failed`.
- `optimization:` one of `applied`, `skipped`, `unavailable`, `failed`.

Report optimization beside the execution verdict, never inside it: an unavailable,
skipped, or failed optimization never turns a completed Trainee execution into `failed`.
The verdict ladder itself is owned by `data-model.md` § RunStatus — consult
it instead of restating it here. The run report restates both values and names the
four artifact paths.

## Degradation Ladder

- Host events available: steps carry `host-event`.
- Host events unavailable but the subagent's structured return is available: steps
  carry `self-report`.
- Neither: the step is a row marked `observation-gap`, counted in the gap list, never
  invented.
- No observation at all: the plan still exists, every entry is `evidence: none`, and
  the run closes `run: partial` per `data-model.md` § RunStatus.

## Boundaries

- Dispatch mechanism: the **fork carrier** is first for same-family agents (a separate `qodercli`
  child process through `.specify/skills/sdd-loop-driver/scripts/stage-runner.sh` — prompt via
  stdin, stream-json output, sentinel-judged completion); heterogeneous agents use the
  **subprocess carrier** (an independent child process of the agent's own CLI). `run-agent` only
  resolves and relays; `run-skills` only resolves and executes the Trainee and carries no dispatch
  duty. The host-internal in-process subagent path is **BANNED** as a carrier — neither a default
  nor a degradation option. No second mechanism is introduced; the mode used is recorded in the
  DispatchRecord.
- Governance: this skill stays `classification: external`. Relaying a destructive
  step that belongs to the Trainee's own flow is a governance-kept relay: state the
  step to the user, obtain the answer, then dispatch; the subagent never
  self-approves.
- Dual independent context: the coach forms the expectation from its own reading of
  `<work>`. The dispatch payload carries `<work>` verbatim, the Trainee target, and
  the instruction to execute per the Trainee's own `SKILL.md`; it never carries the
  expectation, deviation guesses, or the coach's conclusions. The coach never
  pre-digests `<work>`; divergence is a reportable finding, not something to
  eliminate.

## Resources

- Expectation skeleton, derivation method and the zero-side-effect declaration:
  [`./references/prompt-templates.md`](./references/prompt-templates.md).
- Observation, deviation and improvement-plan templates: the same file.
- Optimization claim protocol and run-status ladder: [`./data-model.md`](./data-model.md).

## Resource ID
- Canonical ID: `<SKILL:.specify/skills/coaching-skills/SKILL.md>`
- Canonical Path: `.specify/skills/coaching-skills/SKILL.md`

## Available Tools & Resources

### Scripts (`./scripts/`)
- No scripts required.

### References (`./references/`)
- `./references/prompt-templates.md` — execution-expectation skeleton, derivation
  method, zero-side-effect declaration, and the later run-record templates.

### Assets (`./assets/`)
- No assets required.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:coaching-skills" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:coaching-skills" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:coaching-skills" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
