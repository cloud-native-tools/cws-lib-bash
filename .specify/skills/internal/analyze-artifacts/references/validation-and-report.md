# Finding validation and report format

Owns §5.5 (independent validation wave), §6 (report) and §7 (next actions) of the analysis
skill. Extracted from `.specify/templates/commands/analyze.md`; content preserved, form re-expressed.

## 5.5 Finding validation (independent subagent pass)

Before reporting, **every CRITICAL and HIGH finding MUST be confirmed by an independent
read-only validation subagent.**

- **Propagation-surface intake.** A row whose `propagation_surface` is `none` is capped at
  MEDIUM by the propagation-surface rule, so it MUST NOT be dispatched to this wave as
  CRITICAL/HIGH — MEDIUM/LOW skip validation. A `none` row that nonetheless arrives marked
  CRITICAL/HIGH is a **severity-derivation error**: re-tier it against its propagation
  surface rather than spend a validator confirming a cap violation.
- **Fresh context.** The validator receives **only** the finding (id, category, claim,
  severity) and its evidence location(s) — never the detection reasoning, never the other
  findings.
- **Task.** Re-read the cited artifacts and return one verdict — `confirm` (evidence supports
  the claim), `reject` (not supported — state why), or `downgrade` (real but overstated —
  propose a severity) — **plus both evidence-boundary fields**: `evidence_supported` (what
  the cited artifacts actually substantiate, with locations) and `evidence_not_supported`
  (what the claim asserts beyond that, or what the validator could not observe). A verdict
  returned without both fields is **incomplete** — ask for them again rather than reporting
  the severity alone.
- **Constitution carve-out.** `downgrade` never applies to a constitution finding: severity
  precedence is owned by the Operating Constraints § Constitution Authority, not by this
  pass. When a validator confirms a principle conflict but proposes a lower severity, **keep
  CRITICAL** and adopt only its evidence-boundary fields as the row's scope note.
- **Batching.** Validate in **one parallel dispatch wave**. A validator MUST NOT validate a
  finding it produced; when detection was also delegated under the same-author rule, the
  detection agents and the validators MUST be **disjoint sets** (owner:
  `.specify/shared/workflow/objective-analysis-gate.md` rule 5) — a detector validating its
  own finding is the self-review this pass exists to remove.
- **Downgrade rate is a reported metric.** State how many findings were sent, `confirm`ed,
  `downgrade`d, and `reject`ed. A wave that downgrades most of what it receives is evidence
  that detection over-rated severity — that observation belongs in the report's remediation
  advice (tighten the propagation-surface requirement), **not** absorbed silently, and a large
  downgrade count MUST NOT be presented as though the detection pass had been accurate.
- **Report handling.** Only `confirm`ed findings keep CRITICAL/HIGH in the main table;
  `downgrade`d rows get the new severity with a `(validated: downgraded)` note; `reject`ed
  rows move to a separate **Unvalidated Findings** appendix (never silently dropped). Every
  validated row carries the validator's `evidence_supported` / `evidence_not_supported`
  boundary **verbatim** — a downgrade that drops the boundary discards the very reason it was
  downgraded. MEDIUM/LOW skip validation.
- **Zero-finding floor.** "No findings" is itself a verdict and MUST carry evidence. When the
  passes yield no CRITICAL/HIGH, do not simply skip the wave — re-read a sample of the
  coverage mapping (**every** requirement whose coverage rests on a single task row, plus a
  sample of the remaining rows) and record the sample size and its outcome in the Coverage
  Summary. When the run yields zero findings at **any** severity, the report MUST state which
  detection passes ran and what was sampled to confirm the absence.
- **Subagent-unavailable fallback.** If the validation subagent dispatch fails twice in a row
  (upstream error), a direct evidence re-read by the analyzing agent MAY substitute; the
  report row MUST then carry `(validated: direct re-read, subagent unavailable)` so the
  weaker evidence path is visible to the reader.

## 6. Compact analysis report

Output a Markdown report. **No file writes.**

| ID | Category | propagation_surface | Severity | Location(s) | Summary | Recommendation |
|----|----------|---------------------|----------|-------------|---------|----------------|

One row per finding.

- **IDs** are stable across reruns and always prefixed by the **category initial** (e.g.
  `C-01`, `H-02`). The analysis scope is recorded in the **Category** column, and an ID MUST
  NOT carry a scope-letter prefix or scope numbering — a scope-lettered ID cannot be matched
  between two runs, which is exactly what the rerun delta depends on.
- **`propagation_surface`** names the downstream artifact(s) that inherit the finding, or the
  literal `none`.
- **Severity** is derived from that field and sits to its right.

Also include: **Coverage Summary Table**, **Feature Linkage Summary Table**, **Constitution
Alignment Issues**, **Unmapped Tasks**, **Systemic Observations**, and **Metrics** (Total
Reqs, Tasks, Coverage %, Feature Linkage %, Ambiguity/Duplication/Inconsistency/Critical
counts).

**Systemic Observations** (report-skeleton slot). Aggregate several MEDIUM findings that point
at the same weak surface into one cluster-level observation here, **without raising any single
row's severity** — a cluster is a pattern across rows, not a licence to re-tier one of them.
This is where cluster-level signal lands instead of being lost or smuggled into an inflated
per-row severity.

**Rerun delta** (post-remediation runs). When a prior analysis of the same requirement is
available (an earlier report in context, or one the user supplied), the report MUST separate
the two directions of change instead of presenting one flat list:

- **Resolved Since Last Run** — prior finding IDs, each with the evidence that closed it
  (artifact + location), not merely an assertion that it is gone.
- **New Since Last Run** — finding IDs absent from the prior report, **including ones the
  remediation itself introduced**.
- Findings unchanged from the prior run stay in the main table marked `(carried over)`.

The headline verdict MUST NOT read as "ready to implement" on the strength of a fully cleared
prior set while any new or carried-over CRITICAL/HIGH finding remains open — **a cleared
backlog and a clean rerun are different claims**, and the report states both separately.

## 7. Next actions & remediation

- CRITICAL issues → resolve before `/speckit.implement`.
- LOW/MEDIUM only → proceed with suggestions.
- Offer: *"Would you like concrete remediation edits for top N issues?"* — **do not apply
  automatically.**

> **Fast Fail 实例指针**：本技能中"即停 / 即中止 / 不得静默降级"一类规则是快速失败纪律的既有**实例**；其判据与两份清单的唯一真源是 `.specify/shared/guidelines/fast-fail.md`（本文件引用它，MUST NOT 复述它）。
