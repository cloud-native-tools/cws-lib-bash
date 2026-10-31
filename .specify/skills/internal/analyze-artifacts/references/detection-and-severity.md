# Detection passes, severity, and the noise floor

Owns §4 (detection), §5 (severity) and the do-not-flag list of the analysis skill. Extracted
from `.specify/templates/commands/analyze.md`; content preserved, form re-expressed.

## Same-author detection delegation (applies before any pass)

When the artifacts under analysis were produced by **the agent now running this skill, in the
current session** — the ordinary case for a `requirements → clarify → plan → tasks` chain run
without a break — self-review is weak evidence, and detection MUST be delegated to
fresh-context read-only subagents rather than left to the validation wave.

The delegation wave uses the same carrier rule as §5.5: **workers, never sessions** — the native
subagent tool when the runtime exposes one, the external read-only CLI (`qodercli -p` /
`claude -p`) when the executing agent is itself a non-nesting subagent, and the marked direct
re-read only as the fallback. Host session-creation APIs (`create_chat_session`, `fork_chat_session`, or equivalent) are **PROHIBITED**; owner: `.specify/shared/definitions/subagent-definitions.md` § Mode Selection.

Apply the canonical gate in `.specify/shared/workflow/objective-analysis-gate.md` (single
source of truth; do not restate its rules). **Local parameters for this skill**: the
propagation-surface cap is **MEDIUM** (used when no downstream artifact inherits the
finding), and the fallback marker is `(detected: direct read, subagent unavailable)`.

**Scope split.** The analysis divides the artifact set into three disjoint scopes — an
application of the owner's rule 1 to this artifact set, not a restatement of it:

- (a) **spec ↔ plan ↔ research consistency** — duplication, ambiguity, underspecification,
  count and cross-reference drift;
- (b) **plan ↔ contracts ↔ data-model ↔ tasks coverage** — every requirement reaches a task,
  every task maps back, every claimed mapping is true;
- (c) **feature linkage + registry + constitution alignment**.

**Stale-copy decision test.** When a finding's claim is that a fact is duplicated or stale,
apply the One-Source-of-Truth decision test *before* reporting it: is the second copy one of
the legitimate kinds that discipline allows, or a drifting copy that must be converted into a
reference? The conditions that separate the two are owned by
`.specify/shared/guidelines/one-source-of-truth.md` — read it; do not restate them. **A copy
that qualifies as legitimate is not a finding.**

## The eight passes

Focus on high-signal findings. **Limit to 50 findings total**; aggregate the remainder in an
overflow summary.

### A. Duplication
- Near-duplicate requirements → mark the lower-quality one for consolidation.

### B. Ambiguity
- Vague adjectives (*fast*, *scalable*, *secure*) lacking measurable criteria.
- Unresolved placeholders (`TODO`, `TKTK`, `???`).

### C. Underspecification
- Requirements missing a measurable outcome.
- Tasks referencing undefined components.

### D. Constitution alignment
- Any element conflicting with a MUST principle.
- Missing mandated sections or quality gates.

### E. Coverage gaps
- Requirements with zero tasks; tasks with no requirement.
- Non-functional requirements not reflected in tasks.

### F. Inconsistency
- Terminology drift across files.
- Data entities present in `plan.md` but absent in the spec (or vice versa).
- Task-ordering contradictions.
- **Stability / containment claims**: a requirement, success criterion, DoD item, or task that
  asserts a machine-produced surface changes only within an enumerated set, or that anything
  "unaffected" stays identical, is checked against `.specify/shared/guidelines/closed-set-claims.md`
  — read that owner; do not restate its criteria. Report a claim that lacks the baseline referent,
  the comparison unit, or a mechanically derivable allowed-delta set, and report a derivation that
  omits the fan-out of the edited shared sources onto generated artifacts.

### G. Feature relevance & accuracy
- Missing feature binding when the requirement implies feature capability.
- Incorrect or stale feature metadata.
- Index/detail divergence, or requirement↔feature inconsistency.
- **Stage-recording duties**: derive the latest stage actually reached from the artifacts
  present in `REQUIREMENTS_DIR`, then check the bound feature's index row and detail file
  against the recording duties owned by `.specify/shared/workflow/feature-integration.md`
  § Core Protocol (steps 2–3) — read that owner; do not re-derive its list.
  Judge the two duties **separately**: a status that is lawfully held (including a terminal
  status that MUST NOT regress — rule owner:
  `.specify/templates/feature-details-template.md` § Extension slice rule) never waives the
  stage record, so a correct status beside a stale date or note is **still a finding**.

### I. Decision Tension records

Judged object: **exactly one artifact** — the `plan.md` under the `REQUIREMENTS_DIR` resolved by
the prerequisite script. The `requirements.md` in the same directory is a mapping reference and
is never a second judged object. The channel MUST NOT open any other feature directory's
`plan.md`: a plan outside `REQUIREMENTS_DIR` will produce no finding at all. In-scope historical
plans written before this channel existed are NOT exempt — a missing section is reported, and
the remedy is to add it.

Record shape, admissibility criteria, rejection forms and the load-bearing threshold are owned by
`.specify/shared/guidelines/decision-tension.md` — read that owner; do not restate its tables here.

Three defect classes, each **HIGH**, plus the two record-level validator labels — the section anchor
and the identifier shape — which carry the same severity, so the table below covers all six labels
the program can print and no finding can be dropped between the program and this mapping. The value
domain is HIGH or 0 — there is **no advisory or downgrade tier**, and the detector MUST NOT be asked
to decide whether the plan holds a load-bearing decision: a missing record is judged fail-closed.

| Defect class | Validator label(s) | Severity |
|--------------|--------------------|----------|
| No record — the `## Decision Tensions` section is absent, or present with a bare `N/A` carrying no one-line justification per load-bearing trigger | `dtr-section-missing` | HIGH |
| Misplaced section — the section is present but is not the direct successor of `## Constitution Check` followed by `## Project Structure`, so the record no longer sits beside the gate it defends | `dtr-anchor` | HIGH |
| Incomplete record — a field label missing or blank, a single-pole `binding_constraints`, an empty `expected_sacrifice` or the literal `none` | `dtr-record-incomplete`, `dtr-rejected-form` | HIGH |
| Record identifier malformed, duplicated or skipped — the sub-section heading does not begin with `T-NNN`, or the identifiers are not unique and increasing in document order | `dtr-tension-id` | HIGH |
| Unmappable cost — `expected_sacrifice` does not resolve to a declared measurement source | `expected-sacrifice-unmapped` | HIGH |

When `requirements.md` has no measurement-source section, branch mechanically on the record
count: one or more records fail mapping one by one; a compliant `N/A` with zero records produces
zero findings.

Severity: the propagation-surface criterion owned by
`.specify/shared/workflow/objective-analysis-gate.md` — no new severity level, score or maturity
verdict. Every finding names its propagation surface as its FIRST field, namely the plan flowing
into tasks and implementation (`计划 → 任务 / 实现`).

Deterministic verdicts: every mechanically decidable part — field presence, enumerated values,
reference resolution — is printed by `.specify/scripts/python/validate-decision-tensions.py`, whose
`--json` `checks` array carries the per-label counts. Consume that verdict; MUST NOT re-score the
record semantically, and MUST NOT turn a label count into a percentage or a maturity score.

## Severity assignment

### General heuristic

| Severity | Assign when |
|----------|-------------|
| **CRITICAL** | Violates a constitution MUST; a core spec artifact is missing; a requirement with zero coverage blocks baseline functionality |
| **HIGH** | Duplicate or conflicting requirement; ambiguous security/performance attribute; untestable acceptance criterion |
| **MEDIUM** | Terminology drift; missing non-functional task coverage; underspecified edge case; weak/low-confidence feature mapping |
| **LOW** | Style/wording improvements; minor redundancy not affecting execution order |

### Feature-specific severities

| Severity | Assign when |
|----------|-------------|
| **CRITICAL** | A requirement bound to an incorrect feature, causing scope misdirection; or constitution-mandated feature governance is violated |
| **HIGH** | A requirement references a feature ID/name that does not exist, or conflicts with the feature index/detail |
| **MEDIUM** | A requirement is likely feature-related but binding confidence is low due to incomplete metadata |
| **LOW** | Cosmetic naming drift where the semantic intent still matches |

### Propagation surface governs the cap

A finding's **`propagation_surface`** names the downstream artifact(s) that inherit it, or the
literal `none` when nothing downstream inherits it. Severity is **derived from that field**,
not chosen independently — owner: `.specify/shared/workflow/objective-analysis-gate.md`
rule 3. A row whose surface is `none` is capped at MEDIUM.

**Containment claims.** Severity follows the artifact that depends on the claim: a claim backing
a success criterion, DoD item, or verification gate is an untestable acceptance criterion → **HIGH**
(its propagation surface is that criterion, so the `none` cap does not apply); a narrative-only
claim is capped at MEDIUM by the same rule.

## DO-NOT-FLAG list (noise control — do not report these at any severity)

- Style/wording preferences already consistent within the project's own conventions.
- Intentional template placeholders (`[REQUIREMENT NAME]`, `TXXX`, sample tasks marked as
  samples).
- Deferred `[~]` tasks whose recorded reason **cites an evidence file** in the requirement's
  directory (probe, baseline, or verification record) — they are deliberate, not gaps. The
  exemption is **evidence-bound**: an uncited reason does not qualify, and a task merely
  *eligible* for deferral (pre-marked as deferrable but not actually deferred) is NOT exempt
  without that citation — treat it as a coverage question and let the evidence file decide.
- Cross-references into `.specify/` mirrors that duplicate canonical paths by design.
- Pre-existing baseline test failures already recorded in the feature's baseline file.
- A class-level allowed-delta set pinned by a drift-guard test, or a containment claim that names
  its baseline referent and per-class comparison unit — legitimate forms under
  `.specify/shared/guidelines/closed-set-claims.md`, not findings.
