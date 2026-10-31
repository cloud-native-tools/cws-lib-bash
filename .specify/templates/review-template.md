<!--
  Do NOT remove placeholder tokens. Each [TOKEN] must be replaced when generating a concrete review report.

  This report is SELF-CONTAINED. It is intended to be sent to spec-kit framework maintainers who do not have access to the source repository on their own machine. Therefore:

  - For a `REC-…` target, the **repo-relative path is the PRIMARY form** (it resolves on any checkout); an absolute path is allowed only as a parenthetical supplement.
  - Every finding includes an inline quoted excerpt of the offending text — readers must be able to judge the issue without opening the source file.
  - A target with no repo-relative form MUST be marked `external` with its reason.

  This report is PROBLEM-FIRST. It is NOT a status summary of what the feature does or what each artifact contains. Sections that describe the feature instead of identifying a process gap MUST be deleted.
-->

# Specification-Driven Development (SDD) Process Review Report: [REQUIREMENT_NAME]

> **Audience**: spec-kit framework maintainers.
> **Purpose**: Identify concrete problems and improvement targets in spec-kit templates, command prompts, automation, and workflow as exposed by this feature's SDD lifecycle.
> **Intentionally problem-first**: this report omits long narrative summaries of artifact contents. If a sentence describes the feature instead of identifying a process gap, it does not belong here.

## 0. Portable Project Context (Self-Contained Snapshot)

| Field | Value |
|-------|-------|
| Requirement ID | [REQUIREMENT_ID] |
| Requirement Key | [REQUIREMENTS_KEY] |
| Requirement Name | [REQUIREMENT_NAME] |
| Related Feature | [FEATURE_ID] [FEATURE_NAME] |
| Repository | [REPO_NAME] |
| Repository URL | [REPO_URL] (from `git remote -v`; in a fork `origin` may be the UPSTREAM, so list the remote that actually holds these commits) |
| Reachability of COMMIT_SHA | [PUSHED_TO: <remotes> \| UNRESOLVABLE: `git branch -r --contains HEAD` is empty — cite absolute paths + `git show <sha>:<path>` instead of URLs] |
| Branch | [BRANCH] |
| Commit SHA | [COMMIT_SHA_FULL] (short: [COMMIT_SHA_SHORT]) |
| Repo Root (absolute) | [REPO_ROOT_ABS] |
| Review Date | [REVIEW_DATE] |
| Reviewer (Agent) | [REVIEWER_NAME] |
| Environment | [ENVIRONMENT_SUMMARY] |
| spec-kit Source Snapshot | [SPECKIT_REPO_URL] @ [SPECKIT_COMMIT_OR_VERSION] |

### Artifact Inventory

| Artifact | Lines | Absolute Path | One-line Summary |
|----------|------:|---------------|-------------------|
| [ARTIFACT_NAME] | [LINES] | [ABS_PATH] | [ONE_LINE_SUMMARY] |

(Add one row per artifact actually reviewed. Drop optional artifacts that are absent. Keep summaries to one line each — they exist for orientation, not as a substitute for findings.)

## 1. Process Execution Timeline

Reconstruct what actually happened during this feature's SDD lifecycle. Capture deviations from the prescribed `/speckit.*` flow, ad-hoc artifacts, manual workarounds, and concrete friction moments. Order chronologically. This section is the raw material for Section 3 — keep it factual, not editorial.

| # | Step / Event | Evidence (commit SHA, file, or quoted excerpt) | Deviation from prescribed flow? |
|---|--------------|------------------------------------------------|---------------------------------|
| 1 | [STEP_OR_EVENT] | [EVIDENCE] | [DEVIATION_OR_NONE] |

## 2. Findings Summary

| Severity | Count | Definition |
|----------|------:|------------|
| P0 | [P0_COUNT] | Blocks correct use of spec-kit, or creates silent corruption risk. Fix before next spec. |
| P1 | [P1_COUNT] | Recurring friction across specs. Fix when convenient — currently every spec writer pays the toll. |
| P2 | [P2_COUNT] | Quality-of-life. Compounding gains across many specs. |

| Category | Count |
|----------|------:|
| Template | [CAT_TEMPLATE_COUNT] |
| Command Prompt | [CAT_PROMPT_COUNT] |
| Automation / Scripts | [CAT_AUTOMATION_COUNT] |
| Workflow | [CAT_WORKFLOW_COUNT] |
| Documentation | [CAT_DOCS_COUNT] |

### 2.1 Code Segment (Verdict and Pointers)

> Fill this subsection on every run — including the runs where the code segment is `not-applicable` or `not-evaluated`, and including a process-segment abort. When the process segment aborted before `review.md` existed, this subsection is the whole report: it must be fillable with nothing else present, so it carries no reference to any other section.

| Field | Value | Source |
|-------|-------|--------|
| Base commit | [BASE_SHA] | the resolved diff base |
| Head commit | [HEAD_SHA] | the run-start `HEAD`, fixed for the run even if commits land later |
| Base source | [BASE_SOURCE] | the resolution tier the code segment reported |
| Renderer mode | [RENDERER_MODE] | the code record's header marker (`renderer: text` or `renderer: delta`) |
| Changed / judged / skipped / gap files | [CHANGED_COUNT] / [JUDGED_COUNT] / [SKIPPED_COUNT] / [GAP_COUNT] | copied field by field from the coverage receipt block; never recomputed, re-aggregated, or read off the record's prose |
| Segment verdict | [SEGMENT_VERDICT] | one of the four closed values the `code-review` skill owns (`pass`, `blocked`, `not-applicable`, `not-evaluated`) |
| Gate verdict | [GATE_VERDICT] | the merge-gate verdict source; when it refuses, the named literal `blocking-unresolved` |
| Reason, when one applies | [SEGMENT_REASON] | mandatory for `not-applicable` (a basis) and for `not-evaluated` (a reason); `none` otherwise |
| Uncommitted scope | [UNCOMMITTED_DISCLOSURE] | disclosed, never concluded over; the same sentence lives in [RECORD_PATH] |
| Record | [RECORD_PATH] | written only when the triage value is `run`; otherwise `not written` |
| Archive | [ARCHIVE_PATH] | this run's archive path; `none` on a first run |

This subsection carries the verdict and the pointers only: no opinion body, no per-severity item count. The findings themselves live in [RECORD_PATH] and are read there.

## 3. Findings (Problems & Improvement Targets)

> List **only** problems, friction, ambiguities, and concrete improvement targets. Each finding MUST include an inline quoted excerpt of the offending text and a concrete proposed fix. Order by severity (P0 → P1 → P2), then by category. Drop any finding that lacks evidence — vague complaints are not actionable.

### F1 — [SHORT_FINDING_TITLE]

- **Severity**: [P0 | P1 | P2]
- **Category**: [Template | Command Prompt | Automation | Workflow | Documentation]
- **Location**: [ABS_PATH — preferred; use [REPO_URL]/blob/[COMMIT_SHA_FULL]/relative/path#Lstart-Lend ONLY when §0 records the commit as pushed and the remote is HTTPS-web-accessible]
- **Evidence** (verbatim quote):

  ```
  [QUOTED_EXCERPT — preserve original wording verbatim, including whitespace where significant]
  ```

- **Why it's a problem**: [ONE_OR_TWO_SENTENCE_EXPLANATION]
- **Proposed fix**: [CONCRETE_CHANGE_TO_NAMED_FILE_OR_SECTION]

(Repeat the F[N] block for each finding. Do not invent findings to fill space; quality over quantity.)

## 4. What Worked — Preserve (Brief)

> Keep this section **short**. Bullet-only, no narrative paragraphs. List only the spec-kit mechanics worth preserving so they aren't accidentally regressed in a later refactor.

- [PRESERVE_ITEM_1]
- [PRESERVE_ITEM_2]

## 5. spec-kit / SDD Improvement Recommendations

> Group by target subsystem. Each recommendation MUST name the exact file or section in the spec-kit repo to change and cross-reference the source finding ID(s).
>
> **Target path form**: the **repo-relative path is the PRIMARY form** (`templates/...`, `skills/...`, `scripts/...` — it resolves on any checkout). An absolute path MAY follow only as a parenthetical supplement, e.g. `templates/tasks-template.md (absolute: [SPECKIT_REPO_ROOT]/templates/tasks-template.md)`. A target with no repo-relative form MUST be marked `external` with its reason.

### 5.1 Template Improvements

- **[REC_T1_TITLE]** — Target: `templates/[FILE].md` (absolute supplement: `[SPECKIT_REPO_ROOT]/templates/[FILE].md`). Change: [CONCRETE_CHANGE]. Source: F[N]. Expected impact: [IMPACT].

### 5.2 Command Prompt Improvements

- **[REC_C1_TITLE]** — Target: `templates/commands/[FILE].md` (absolute supplement: `[SPECKIT_REPO_ROOT]/templates/commands/[FILE].md`). Change: [CONCRETE_CHANGE]. Source: F[N]. Expected impact: [IMPACT].

### 5.3 Automation / Script Improvements

- **[REC_A1_TITLE]** — Target: `scripts/bash/[FILE].sh` (or `scripts/python/[FILE].py`; absolute supplement: `[SPECKIT_REPO_ROOT]/scripts/...`). Change: [CONCRETE_CHANGE]. Source: F[N]. Expected impact: [IMPACT].

### 5.4 Workflow Improvements

- **[REC_W1_TITLE]** — Target: `shared/workflow/[FILE].md` (absolute supplement: `[SPECKIT_REPO_ROOT]/shared/workflow/[FILE].md`). Change: [CONCRETE_CHANGE]. Source: F[N]. Expected impact: [IMPACT].

### 5.5 Documentation Improvements

- **[REC_D1_TITLE]** — Target: `docs/[FILE].md` (absolute supplement: `[SPECKIT_REPO_ROOT]/docs/[FILE].md`). Change: [CONCRETE_CHANGE]. Source: F[N]. Expected impact: [IMPACT].

(Drop any sub-section that has no recommendations — do not leave empty headers.)

## 6. Priority Roadmap

| Priority | Recommendation | Target File / Subsystem | Source Finding(s) |
|----------|----------------|--------------------------|-------------------|
| P0 | [REC_TITLE] | [TARGET] | F[N] |
| P1 | [REC_TITLE] | [TARGET] | F[N] |
| P2 | [REC_TITLE] | [TARGET] | F[N] |

## 7. Self-Containment Check

The generator MUST tick every box below before submitting the report. If any box would remain unchecked, fix the report first.

- [ ] Every `REC-…` target is repo-relative (primary), with an absolute path only as a parenthetical supplement; targets with no repo-relative form are marked `external` with a reason.
- [ ] Every finding in Section 3 has a quoted excerpt that lets the reader judge the problem without opening the source file.
- [ ] No bullet says "see attached", "as discussed earlier", or otherwise references context outside this document.
- [ ] No placeholder tokens (`[...]`) remain anywhere in the report.
- [ ] Section 4 is short and bullet-only — no multi-paragraph narrative summaries leaked back in.
- [ ] Section 5 recommendations each cite an exact target file in the spec-kit repo and at least one source finding ID.
- [ ] P0 validation status is stated explicitly. When the review raised zero P0 findings, use the standard wording: "No P0 findings raised; the P0 independent-validation pass is vacuously satisfied." — do not leave the path unmentioned and do not improvise per-run phrasing.

## 8. Feedback

Please share the contents of this document with the spec-kit framework developers.

---

## Placeholder Glossary

| Token | Meaning / Source |
|-------|------------------|
| [REQUIREMENT_ID] | Sequential three-digit requirement identifier from branch name (e.g., 023) |
| [REQUIREMENT_NAME] | Short human-readable name of the requirement/specification |
| [REQUIREMENTS_KEY] | Combined ID + slug used as spec directory name (e.g., 023-cross-platform-build) |
| [FEATURE_ID] | Sequential three-digit feature identifier from `.specify/memory/features.md` (e.g., 021) |
| [FEATURE_NAME] | Short human-readable name of the parent feature |
| [REPO_NAME] | Repository basename (`basename "$(git rev-parse --show-toplevel)"`) |
| [REPO_URL] | Repository origin URL (https form preferred), or `(no remote configured)` |
| [BRANCH] | Current git branch (`git rev-parse --abbrev-ref HEAD`) |
| [COMMIT_SHA_FULL] | Full SHA of HEAD at review time (`git rev-parse HEAD`) |
| [COMMIT_SHA_SHORT] | Abbreviated SHA (`git rev-parse --short HEAD`) |
| [REPO_ROOT_ABS] | Absolute path of repository root (`git rev-parse --show-toplevel`) |
| [REVIEW_DATE] | ISO date when this review was generated (YYYY-MM-DD) |
| [REVIEWER_NAME] | Name/label of the reviewing agent or persona |
| [ENVIRONMENT_SUMMARY] | OS, shell, and key toolchain versions relevant to this feature |
| [SPECKIT_REPO_URL] | URL of the spec-kit repo whose templates/commands/scripts are being reviewed |
| [SPECKIT_COMMIT_OR_VERSION] | spec-kit commit SHA or release version embedded in the project's `.specify/` snapshot, or `unknown` |
| [ARTIFACT_NAME] / [LINES] / [ABS_PATH] / [ONE_LINE_SUMMARY] | Per-row entries in the Artifact Inventory |
| [STEP_OR_EVENT] / [EVIDENCE] / [DEVIATION_OR_NONE] | Per-row entries in the Process Execution Timeline |
| [P0_COUNT] / [P1_COUNT] / [P2_COUNT] | Counts in the severity summary |
| [CAT_*_COUNT] | Counts per finding category |
| F[N] | Stable finding ID (F1, F2, ...) used to cross-reference findings to recommendations |
| [SHORT_FINDING_TITLE] / [QUOTED_EXCERPT] / [ONE_OR_TWO_SENTENCE_EXPLANATION] / [CONCRETE_CHANGE_TO_NAMED_FILE_OR_SECTION] | Per-finding fields |
| [REC_*_TITLE] / [CONCRETE_CHANGE] / [IMPACT] | Per-recommendation fields |
| [BASE_SHA] | The resolved diff base commit id of the code segment (`base..head` interval) |
| [HEAD_SHA] | The head commit id: the run-start `HEAD`, fixed for the whole run |
| [BASE_SOURCE] | Which resolution tier produced the base (explicit, feature-first-commit, or trunk merge base) |
| [RENDERER_MODE] | The code record's header marker: `renderer: text` or `renderer: delta` |
| [CHANGED_COUNT] / [JUDGED_COUNT] / [SKIPPED_COUNT] / [GAP_COUNT] | The four coverage-receipt counts, copied field by field from the receipt block in the code record — never recomputed |
| [SEGMENT_VERDICT] | The code segment's verdict, one of the four closed values owned by the `code-review` skill |
| [GATE_VERDICT] | The merge-gate verdict for the `Implemented → Ready for Review` transition; the refusing literal is `blocking-unresolved` |
| [SEGMENT_REASON] | The mandatory basis of a `not-applicable` result or the mandatory reason of a `not-evaluated` one; `none` otherwise |
| [UNCOMMITTED_DISCLOSURE] | The sentence disclosing unreviewed uncommitted working-tree scope, when any exists; the same sentence appears in the code record |
| [RECORD_PATH] | The code segment record path, `<spec>/code-review.md` |
| [ARCHIVE_PATH] | This run's archive path for the previous record, or `none` on a first run |

## Replacement Rules

1. No placeholder token may remain in a committed review report.
2. Dates must be valid ISO format (YYYY-MM-DD).
3. **REC targets are repo-relative first.** The repo-relative path is the PRIMARY form (it resolves on any checkout); an absolute path is allowed only as a parenthetical supplement. A target with no repo-relative form MUST be marked `external` with its reason. This supersedes 061's machine-local absolute-only form.
4. Findings without a quoted excerpt MUST be dropped — vague complaints are not actionable.
5. Section 4 stays short and bullet-only. The report is for maintainers who want to know what to change, not a status report for project stakeholders.
6. Section 5 recommendations each cite an exact target file in the spec-kit repo and at least one source finding ID from Section 3.
7. Run the Section 7 self-containment check before writing the report. Every box must be tickable.
8. When regenerating a review, overwrite the existing `review.md` (unless project convention says otherwise).

<!-- End of review template -->
