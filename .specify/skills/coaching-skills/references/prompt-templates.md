# Coaching Prompt Templates

Fill-in shapes for one coaching run. The skill body owns the rules; this file owns the
skeletons, the derivation method and the phase boundaries.

## Execution Expectation Template

Path: `.specify/memory/coaching/<run-id>/expectation.md`. Write it **before any
dispatch action**; the `dispatched-at` field of `observation.md` § Dispatch is the
ordering evidence.

```markdown
## Run header
- run-id: <YYYYMMDDTHHMMSSZ-trainee-slug>
- chain: <caller> → <trainee> → <subject>   (direct run: <caller> → <trainee>)
- trainee: <resolved Trainee name and path>
- subject: <subject reference verbatim from `<work>`; its resolved path belongs to
  `observation.md`, never retro-filled here>
- started-at: <ISO-8601 UTC>

## Trainee
- identifier (verbatim):
- resolved-path:
- executor-kind: skill | command   (decided by scanning both lists; `/` is not a discriminator)
- layer: external | internal   (skill Trainees; `n/a` for a command)
- subject-resolution: self (Trainee is the subject) | delegated to the Trainee (meta-skill)
- failure-semantics: <extracted from the Trainee's own text or the command template>

## Outcome Correctness
<!-- `OC-1` MUST name the primary deliverable: an artifact path, or a checkable
conclusion (decision, report, verdict statement) for a Trainee that produces no
artifact. The acceptance and allowed-deviation columns accept only `pass|fail` or
`tolerance=<number><unit> severity=<low|medium|high>`; undecidable wording such as
"roughly matches" or "reasonable" is invalid in either column. -->
| id | object | acceptance | allowed-deviation | derivation |
|---|---|---|---|---|
| OC-1 | <primary deliverable> | <closed form> | <closed form> | <Trainee file#section> |
| OC-2 | <check item or verdict statement> | <closed form> | <closed form> | <Trainee file#section> |

## Process Efficiency
<!-- Every row derives from the Trainee text. `steps` is an order of magnitude
(`~5-8`), `tool-calls` is a profile (which tools, how many rounds), `retries` is the
allowed redundancy budget, and `critical-path` names the step sequence that must not
be skipped. `derivation` is a Trainee anchor or `validation-gap`; a validation-gap
row carries no invented numbers. `validation-gap` is the expectation-side unknown
marker and must not be swapped with `observation-gap`, which belongs to the
observation record only. -->
| id | steps | tool-calls | retries | critical-path | derivation |
|---|---|---|---|---|---|
| PE-1 | ~<order of magnitude> | <tools and rounds> | <allowed retries> | <named step sequence> | <Trainee file#section> |
| PE-2 | validation-gap | validation-gap | validation-gap | validation-gap | validation-gap |

## Assumptions
- <what this expectation takes for granted>

## Unknowns
- <what cannot be derived from the Trainee text and will be checked after execution>

## Forbidden Side Effects
- No Trainee tool, script or command is executed in this phase.
- No write inside the Trainee directory.
- No network or external call.
- No claim marker is created; the claim protocol belongs to `../data-model.md` §
  Optimization claim and to the optimization step only.

## Trainee Failure Semantics
- <which failure stops the run, which continues, and what the Trainee promises to
  report; extracted from the Trainee's own text>
```

## Derivation Method

Produce the expectation by the mental-simulation procedure carried over from the
pre-rename skill:

1. Build the simulation contract: **Initial State**, **Rules**, **Known Constraints**,
   **Assumptions**, **Unknowns**, plus the side effects forbidden for this phase.
2. Run the mental trace step by step. For each Trainee step record the expected
   action, the state delta and a consistency check against the critical path.
3. Run the **Logic Implementation Audit**. Separate **Natural Language Logic**
   (judgement steps executed by reasoning: trade-offs, quality review, intent) from
   **Programmatic Logic** (deterministic script calls). Take each script's contract
   as given (input → output) and audit its invocation timing, preconditions and
   downstream consumption instead of simulating its internals.
4. Record the audit result in `expectation.md`: which Trainee steps are judgement,
   which are deterministic calls, and which side effects are forbidden for this
   phase.
5. Extract the Trainee's own failure semantics here; the compare phase reuses them to
   decide continue-vs-stop.

## Zero Side Effects of the Expectation Phase

The expectation phase MUST NOT:

1. execute any Trainee tool, script, or command;
2. write inside the Trainee's directory;
3. make network or external calls;
4. create the run's claim marker — that belongs to the optimization step.

Reading the Trainee's `SKILL.md` and the reference files it needs is permitted and is
the only allowed interaction.

## Observation Record Template

Path: `.specify/memory/coaching/<run-id>/observation.md`. Write it after the single
dispatch and before `deviations.md`: it records what actually happened, never what the
expectation predicted.

```markdown
## Run header
- run-id: <YYYYMMDDTHHMMSSZ-trainee-slug>
- chain: <caller> → <trainee> → <subject>
- trainee: <resolved Trainee name and path>
- subject-resolved-path: <as reported by the Trainee; `unresolved` is a legitimate value
  and MUST be paired with a deviation>
- subject-evidence: <read-only post-run probe of the subject — changed file list, or
  `none-observed` when the subject is byte-identical; recorded as `file-evidence` steps>
- observation-window: <first observed step at> .. <last observed step at>

## Dispatch
- mode: native | run-agent-fallback | run-skills-explicit-path
- dispatched-at: <ISO-8601 UTC; later than the expectation.md mtime>
- payload-ref: <path or hash of the rendered payload>
- returned: completed | partial | failed | timeout | refused
- anomaly-line: <the subagent's anomaly line, verbatim>
- failure-coordinates: <step id, error, completed portion; omit only when returned is completed>

## Steps
| step | trigger/instruction | action | tool-call | state-change | artefact | elapsed | source | consistency |
|---|---|---|---|---|---|---|---|---|
| S1 | <Trainee instruction> | <what the subagent did> | <tool + key argument, or —> | <state delta> | <path, or —> | <duration> | host-event | on-critical-path: yes; vs-expected-steps: within |
| S2 | <Trainee instruction> | <the step no channel carried> | — | — | — | — | observation-gap | on-critical-path: yes; vs-expected-steps: beyond |

## Gaps
- gap-count: <number of gap rows>
- step ids: <S-ids, comma-separated>
- <plain prose: which steps carried no observation channel and what information is missing>

## Result
- state: completed | partial | failed
- failure-coordinates: <step id, error, completed portion; omit only when completed>
```

Rules for the record:

- Section order is fixed: `## Run header` → `## Dispatch` → `## Steps` → `## Gaps` →
  `## Result`. Exactly one dispatch block: a second one is a contract violation even when
  the first dispatch failed.
- `consistency` is an observation-only judgement with two closed sub-fields:
  `on-critical-path: yes|no` and `vs-expected-steps: within|beyond`. It MUST NOT execute
  the Trainee's verification logic — verifying the Trainee's output is the Trainee's job,
  not an observation side effect.
- Every step row carries a `source`: `host-event` when the host reported the step,
  `self-report` when only the subagent's structured return described it, `file-evidence`
  when a read-only filesystem probe of the subject supplies the fact (never an inference),
  and `observation-gap` when no channel carried it. When two channels describe one step
  and disagree at field level, the `host-event` value wins.
- The gap marker `observation-gap` appears only on step rows. `## Gaps` describes the gaps
  in plain prose and does not repeat the marker; it reports the count (`gap-count`) and
  the affected step ids. An unobservable step is never omitted and never reconstructed
  from the expectation.
- A failed, timed-out, or refused dispatch keeps its coordinates: which step, which error,
  which part completed. Gaps never mask a failure and the record never narrates an
  incomplete run as completed.
- If no observation could be collected at all, the file still exists, `## Gaps` states the
  total absence, and `## Result` says so plainly; downstream `deviations.md` and
  `improvement-plan.md` carry `evidence: none` and the run stays `partial`.

## Deviations Template

Path: `.specify/memory/coaching/<run-id>/deviations.md`. Both dimension sections are
required:

```markdown
## Outcome Correctness
| id | expectation | observed | dimension | severity | evidence |
|---|---|---|---|---|---|
| D-1 | <OC id and its expectation> | <what the observation record carries> | result-deviation | <low\|medium\|high> | S2 / checklist.md |

## Process Efficiency
| id | expectation | observed | dimension | severity | evidence |
|---|---|---|---|---|---|
| D-2 | <PE id and its expectation> | <observed step count and tool profile> | process-deviation | <low\|medium\|high> | S1-S4 |

## Readings
- coach reading of `<work>`: <one line>
- Trainee actual reading: <one line>
- material divergence: <what separates the two readings beyond normal execution noise>
```

Rules for the deviations: every finding cites a step id and/or an artifact path from
`observation.md`; the dimension column uses only `result-deviation` or
`process-deviation`; a partially completed flow separates the two classes. When the
observation carries no evidence, each row is marked `evidence: none` instead of being
dropped.

## Improvement Plan Template

Path: `.specify/memory/coaching/<run-id>/improvement-plan.md`. Entries are
priority-ordered and concrete:

```markdown
## Improvements
1. `I-1` — target: `<Trainee file>` § `<section>`; tweak: `<one concrete change>`; cites:
   `D-1`.
2. `I-2` — target: `<Trainee file>` § `<section>`; tweak: `<one concrete change>`; cites:
   `evidence: none`.

## Run Status
- run: success | partial | failed
- optimization: applied | skipped | unavailable | failed
```

Rules for the plan: each entry names a concrete Trainee file and section plus one concrete
tweak — generic advice is invalid. Each entry cites `D-*` findings or is marked
`evidence: none`; the plan is still produced when the observation is empty. Both status
values are recorded once, in `## Run Status`, and the combination rule is owned by
`../data-model.md` § RunStatus — consult it, do not restate it here.
