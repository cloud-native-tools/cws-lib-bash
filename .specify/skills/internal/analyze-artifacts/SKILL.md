---
name: analyze-artifacts
description: Perform a strictly read-only cross-artifact consistency and quality analysis across requirements.md, plan.md, tasks.md and the feature registry, then emit one compact findings report — duplication, ambiguity, underspecification, constitution conflicts, coverage gaps, inconsistencies and feature-linkage drift, with severities validated by an independent fresh-context subagent wave and a rerun delta when a prior report exists. Use this when the user mentions ["analyze artifacts", "consistency analysis", "cross-artifact", "drift detection", "一致性分析", "跨产物分析", "需求漂移", "coverage gap", "任务覆盖缺口", "constitution alignment", "feature linkage drift", "rerun delta", "findings report"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/analyze-artifacts/SKILL.md>"
---

# analyze-artifacts

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.


## Goal

Reach a verdict on whether a feature's artifact set is internally consistent and ready to
implement — before implementation starts. The output is one **compact findings report**
(≤50 rows) whose CRITICAL/HIGH severities survive an independent validation wave, plus the
coverage/linkage summaries that make the absence of findings itself an evidenced claim.

The skill is **strictly read-only on artifacts**: it modifies no artifact. (The single
sanctioned exception is the wrap-up engine entries — Run Determination / Exec Quant /
Feedback Record — local bookkeeping, not an artifact modification.)

Canonical extraction source: `.specify/templates/commands/analyze.md` § Execution Steps 1–7,
Operating Principles, and the do-not-flag list. The command template keeps entry +
delegation only.

## Rounds

- **Round 1** adjudicates the full severity set (`CRITICAL`/`HIGH`/`MEDIUM`/`LOW`).
- **Round 2** (a rerun after fixes) re-adjudicates the round-1 findings **and** the full severity set,
  or declares itself **C/H-only** in the report. A C/H-only round 2 MUST enumerate every open
  `MEDIUM`/`LOW` round-1 finding as a **residue row** in the findings JSONL — `status` plus a
  disposition (`fixed` / `deferred` / `rejected`, with the reason) — and a round-2 pass without that
  residue list is incomplete: it MUST NOT be read as closing the gate. Prose residue in a notes file
  is not a gate input.

### Incremental re-check protocol（增量复检协议）

A round after the first defaults to an **incremental re-check**; the full re-run is the fallback, not the default:

- **Re-check scope**: round N+1 re-checks exactly (i) the loci repaired in round N and (ii) their one-hop neighbors (a repaired FR/contract clause pulls the artifact sections that cite it).
- **Reuse is declared, never silent**: every untouched domain is reused and named in the round record with its content hash (path set + hash). An unnamed reuse is an incomplete record.
- **Validator independence is never downgraded**: every CRITICAL/HIGH of the incremental round still needs a fresh-context, read-only validator; reuse applies to detection domains, never to validation.
- **Deterministic gates always full-run** as the backstop; a gate that goes red for a reason a repaired locus cannot explain escalates to a full re-run.
- **Full re-run is mandatory** when any of: more than half of the declared domains were touched; the repairs changed contract surfaces across all three artifact classes; the finding taxonomy or a clause-id map changed; or an incremental round still leaves an open CRITICAL/HIGH.
- **Round record fields**: touched-loci set · reused domains (path + hash) · per carried finding disposition (`fixed` / `deferred` / `rejected` with reason). The residue rules above apply unchanged.

### Domain and output budget（域与输出预算）

The dispatch layer splits the analysis into file-disjoint domains; this skill owns the sizing and output rules it must follow:

- **Size by expected finding volume**: a domain carries at most ~15 files and ~10 expected findings. A domain expected to exceed either bound MUST be pre-split by file path before dispatch — a domain that fails on output limit and is then re-split is a dispatch defect, and its partial findings are never accepted.
- **Bounded worker output**: a worker returns findings as structured records only (id / category / claim / severity / locations / evidence) in the findings JSONL; narrative duplicated from the artifacts does not belong in worker output.
- **Incomplete unit rule**: a worker that returns an output-limit error, a truncated findings set, or a read-domain mismatch is an incomplete unit — re-dispatch its files (split further), never synthesize around a silence.


## Input Contract

- **Prerequisite**: `/speckit.tasks` has produced a complete `tasks.md`. Abort with a
  clear message if a required artifact is missing (tell the user which command to run).
- **Argument**: free text is **supplemental analysis focus areas**, not standalone
  instructions.
- **Constitution authority**: `.specify/constitution.md` is non-negotiable in this
  scope. A constitution conflict is automatically **CRITICAL** and is resolved by adjusting
  spec/plan/tasks — never by diluting, reinterpreting, or silently ignoring the principle.
  If a principle itself must change, that happens in a separate explicit constitution
  update **outside** this skill. This precedence also governs the validation pass: a
  validator verdict MAY narrow a constitution finding's evidence boundary but MUST NOT
  lower its severity.

## Workflow

### 1. Initialize the analysis context

Run the command's declared prerequisite script once from repo root; parse JSON for
`REQUIREMENTS_DIR` and `AVAILABLE_DOCS`; derive absolute `SPEC` / `PLAN` / `TASKS` paths.
Abort if a required file is missing. Then derive feature-lookup context (best effort, no
write): `REQUIREMENTS_KEY` = basename of the requirements dir; `FEATURE_INDEX` =
`.specify/features.md` (if present); `FEATURE_DETAILS_DIR` =
`.specify/features/` (if present) — the index rows live in `features.md`, the
matching detail file at `features/<NNN>-<slug>.md`, and the install-shipped sample at
`features/*.md`.

Identify the most likely bound feature in this order: (1) explicit references inside
`requirements.md` (Feature ID/Name sections, metadata block); (2) `REQUIREMENTS_KEY` /
branch-naming hints (numeric prefix, shared slug); (3) string similarity against
`features.md` rows. **Feature files absent → continue the analysis and report the absence
as a governance gap**, not a hard failure.

### 2. Load artifacts (progressive disclosure)

Load only the minimal necessary context — never the whole artifacts:

| Source | Load |
|--------|------|
| `requirements.md` | Overview/Context, functional + non-functional requirements, user stories, edge cases, feature metadata (ID / Name / linkage statements) |
| `plan.md` | Architecture/stack choices, data-model references, phases, technical constraints |
| `tasks.md` | Task IDs, descriptions, phase grouping, `[P]` markers, referenced file paths |
| `checklists/*.md` | Item text, checked state (`- [ ]` / `- [X]`), and tags — `[Gap]` in particular |
| feature registry | Index rows (ID, Name, Description, Status, Details link, Last Updated); the matching detail file; its spec-linkage fields |
| constitution | `.specify/constitution.md` for principle validation |

### 3. Coverage accounting (fixed read-only step)

Run the clause/FR coverage accountant once and surface its verdict in the report:

```
python3 .specify/scripts/python/account-clause-coverage.py --spec <spec-dir>
```

This step MUST NOT pass `--freeze` — freezing the baseline is `/speckit.tasks`'s duty
(C-6), and the analyze side only consumes it. The run's `[fr-uncovered]` lane feeds the
report's coverage summary. `status: baseline-missing` MUST appear as a phase-visible
problem together with its remedy (re-run `/speckit.tasks` to freeze
`coverage-baseline.txt`), never silently skipped. A feature without a contract set MUST
record an explicit skip with its reason.

### 4. Build semantic models

Internal representations only — raw artifacts never appear in the output:

- **Requirements inventory** — each functional/non-functional requirement with a stable
  slug key derived from the imperative phrase (e.g. "User can upload file" →
  `user-can-upload-file`).
- **User story / action inventory** — discrete user actions with acceptance criteria.
- **Task coverage mapping** — each task mapped to one or more requirements or stories
  (inference by keyword, or explicit ID/keyphrase references).
- **Constitution rule set** — principle names plus their MUST/SHOULD normative statements.
- **Feature linkage model** — candidate `feature_id` / `feature_name` with confidence
  (high/medium/low), requirement↔feature intent mapping, and consistency signals (ID/name
  match, terminology match, status/path coherence).

### 5. Detection passes

Eight passes (A duplication · B ambiguity · C underspecification · D constitution alignment
· E coverage gaps · F inconsistency · G feature relevance & accuracy · I decision tension
records) plus one checklist pass (H), the same-author delegation rule, the stale-copy decision
test, and the do-not-flag noise floor:
[`./references/detection-and-severity.md`](./references/detection-and-severity.md).

**F — cross-clause contradictions.** Two clauses that impose mutually exclusive criteria on
the same object MUST be reported as one `inconsistency` finding naming both clauses and the
shared object — for example, one clause requires an artifact's whole-file hash to remain
unchanged while another requires a section of that same file to be rewritten, or two clauses
classify the same predicate into different closed sets. Neither clause may be accepted as the
settled reading while its opposite stands.

**H — checklist accountability.** Every unchecked `[Gap]` item under
`REQUIREMENTS_DIR/checklists/*.md` MUST be raised as a finding or carry an explicit
disposition marker in the gate report. The marker form is machine-checkable; free prose
MUST NOT satisfy it:

- `CHK005 disposition: raised-as-finding H-01`
- `CHK005 disposition: covered-by <artifact § anchor>`

The report MUST make the count `unchecked + unraised + undispositioned = 0` observable;
a non-zero count blocks the analyze gate.

Limit to **50 findings**; aggregate the remainder in an overflow summary.

### 6. Severity assignment

Four severities (CRITICAL / HIGH / MEDIUM / LOW) with the general heuristic plus
feature-specific rules, and the propagation-surface cap that governs them:
[`./references/detection-and-severity.md`](./references/detection-and-severity.md).

### 7. Validate CRITICAL/HIGH findings

Every CRITICAL and HIGH finding MUST be confirmed by an independent read-only validation
subagent before it is reported — fresh context, one verdict each
(`confirm` / `reject` / `downgrade`) plus both evidence-boundary fields, disjoint from the
detectors, with the downgrade rate reported as a metric:
[`./references/validation-and-report.md`](./references/validation-and-report.md).

### 8. Produce the report

One compact Markdown report — findings table, coverage/feature/linkage summaries, systemic
observations, metrics, and the rerun delta when a prior report exists:
[`./references/validation-and-report.md`](./references/validation-and-report.md).

### 9. Next actions & remediation

- CRITICAL issues → resolve before `/speckit.implement`.
- LOW/MEDIUM only → proceed with suggestions.
- Offer concrete remediation edits for the top N issues. **Do not apply them
  automatically** — the user must approve, and any follow-up editing command is invoked
  by the user.

## Operating Principles

- **Read-only**: never modify files.
- **Self-authored artifacts are not self-auditable**: when this session produced them,
  delegate detection as well as validation (§5's same-author delegation; owner
  `.specify/shared/workflow/objective-analysis-gate.md`).
- **Actionable findings only**; ≤50 rows; summarize overflow.
- **Constitution violations are always CRITICAL** and are never a `downgrade` candidate.
- **Feature checks are evidence-based**; lower the confidence when evidence is weak.
- **Zero findings is a claim that carries evidence** — see the zero-finding floor.
- **Deterministic**: a rerun without changes produces consistent results; a rerun after
  remediation additionally reports its delta.

## Boundaries

- **Remediation is not this skill.** It produces findings and offers edits; applying them
  belongs to `/speckit.requirements`, `/speckit.plan`, or `/speckit.tasks`.
- **Evidence collection is not this skill.** The detection here is artifact-consistency
  analysis over the spec chain; the framework's evidence layer (running the evidence
  engine over session/project/assets/runs/feedback lanes to produce `findings.json`) is a
  different, consumer-neutral capability and does not interpret its own output.
- **Code review is not this skill.** Reviewing a diff or a PR is a different capability;
  this one reviews the spec chain.
- **Feedback is not this skill.** `/speckit.feedback` targets the Spec Kit framework
  itself across accumulated unit-run entries; this skill analyzes the current feature's
  spec chain. The boundary is owned by
  `.specify/shared/workflow/feedback-step.md` § *Mechanism boundary*.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:analyze-artifacts" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:analyze-artifacts" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:analyze-artifacts" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
