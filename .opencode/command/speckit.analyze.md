<!-- AUTO-GENERATED from templates/commands/analyze.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as supplemental analysis focus areas, not standalone instructions.

## Goal

Identify inconsistencies, duplications, ambiguities, underspecified items, and feature-linkage drift across the core artifacts (`requirements.md`, `plan.md`, `tasks.md`) plus feature memory (`.specify/memory/features.md` and `.specify/memory/features/*.md`) before implementation. This command MUST run only after `/speckit.tasks` has successfully produced a complete `tasks.md`.

## Operating Constraints

**STRICTLY READ-ONLY**: Do **not** modify any files. Output a structured analysis report. (Single sanctioned exception: the wrap-up Feedback step's engine entry — local bookkeeping, not an artifact modification.) Offer an optional remediation plan (user must explicitly approve before any follow-up editing commands would be invoked manually).

**Constitution Authority**: The project constitution (`.specify/memory/constitution.md`) is **non-negotiable** within this analysis scope. Constitution conflicts are automatically CRITICAL and require adjustment of the spec, plan, or tasks—not dilution, reinterpretation, or silent ignoring of the principle. If a principle itself needs to change, that must occur in a separate, explicit constitution update outside `/speckit.analyze`. This precedence also governs the §5.5 validation pass: a validator verdict MAY narrow a Constitution finding's evidence boundary but MUST NOT lower its severity (handling: § 5.5 **Constitution carve-out**).

## Execution Steps

### 1. Initialize Analysis Context

Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` once from repo root and parse JSON for REQUIREMENTS_DIR and AVAILABLE_DOCS. Derive absolute paths:

- SPEC = REQUIREMENTS_DIR/requirements.md
- PLAN = REQUIREMENTS_DIR/plan.md
- TASKS = REQUIREMENTS_DIR/tasks.md

Abort with an error message if any required file is missing (instruct the user to run missing prerequisite command).
For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

Then derive feature lookup context (best effort, no write):

- REQUIREMENTS_KEY = basename(REQUIREMENTS_DIR)
- FEATURE_INDEX = `.specify/memory/features.md` (if present)
- FEATURE_DETAILS_DIR = `.specify/memory/features/` (if present)

Try to identify the most likely bound feature for the current requirement by using, in order:

1. Explicit references in `requirements.md` (e.g., Feature ID/Name sections, metadata block)
2. REQUIREMENTS_KEY / branch naming hints (numeric prefix, shared slug)
3. String similarity against rows in `features.md`

If feature files are absent, continue analysis and report this as a governance gap instead of failing the whole command.

### 2. Load Artifacts (Progressive Disclosure)

Load only the minimal necessary context from each artifact:

**From requirements.md:**

- Overview/Context
- Functional Requirements
- Non-Functional Requirements
- User Stories
- Edge Cases (if present)
- Feature-related metadata (Feature ID/Feature Name/Feature Linkage statements, if present)

**From plan.md:**

- Architecture/stack choices
- Data Model references
- Phases
- Technical constraints

**From tasks.md:**

- Task IDs
- Descriptions
- Phase grouping
- Parallel markers [P]
- Referenced file paths

**From feature registry (if present):**

- `.specify/memory/features.md` index rows (ID, Name, Description, Status, Details link, Last Updated)
- Matching detail file `.specify/memory/features/<ID>.md` for the best candidate feature
- Any spec linkage fields in feature detail (spec paths, key changes, notes)

**From constitution:**

- Load `.specify/memory/constitution.md` for principle validation

### 3. Build Semantic Models

Create internal representations (do not include raw artifacts in output):

- **Requirements inventory**: Each functional + non-functional requirement with a stable key (derive slug based on imperative phrase; e.g., "User can upload file" → `user-can-upload-file`)
- **User story/action inventory**: Discrete user actions with acceptance criteria
- **Task coverage mapping**: Map each task to one or more requirements or stories (inference by keyword / explicit reference patterns like IDs or key phrases)
- **Constitution rule set**: Extract principle names and MUST/SHOULD normative statements
- **Feature linkage model**:
  - Candidate `feature_id`, `feature_name`, confidence (high/medium/low)
  - Requirement ↔ Feature intent mapping (what capability the requirement claims to serve)
  - Consistency signals (ID/name match, terminology match, status/path coherence)

### 4. Detection Passes (Token-Efficient Analysis)

Focus on high-signal findings. Limit to 50 findings total; aggregate remainder in overflow summary.

**Same-author detection delegation**: when the artifacts under analysis were produced by the agent now running this command, in the current session — the ordinary case for a `requirements → clarify → plan → tasks` chain run without a break — self-review is weak evidence, and detection MUST be delegated to fresh-context read-only subagents rather than left to the §5.5 validation wave. Apply the canonical gate in `.specify/shared/workflow/objective-analysis-gate.md` (single source of truth; do not restate its rules here). This command's local parameters: the propagation-surface cap is **MEDIUM** (used when no downstream artifact inherits the finding), and the fallback marker is `(detected: direct read, subagent unavailable)`.

Analyze's split of the artifact set into disjoint scopes — an application of the owner's rule 1 to this artifact set, not a restatement of it: (a) spec ↔ plan ↔ research consistency — duplication, ambiguity, underspecification, count and cross-reference drift; (b) plan ↔ contracts ↔ data-model ↔ tasks coverage — every requirement reaches a task, every task maps back, every claimed mapping is true; (c) feature linkage + registry + constitution alignment.

#### A. Duplication Detection
- Near-duplicate requirements → mark lower-quality for consolidation

#### B. Ambiguity Detection
- Vague adjectives (fast, scalable, secure) lacking measurable criteria
- Unresolved placeholders (TODO, TKTK, ???)

#### C. Underspecification
- Requirements missing measurable outcome
- Tasks referencing undefined components

#### D. Constitution Alignment
- Any element conflicting with MUST principles
- Missing mandated sections/quality gates

#### E. Coverage Gaps
- Requirements with zero tasks; tasks with no requirement
- Non-functional requirements not reflected in tasks

#### F. Inconsistency
- Terminology drift across files
- Data entities in plan but absent in spec (or vice versa)
- Task ordering contradictions

#### G. Feature Relevance & Accuracy
- Missing feature binding when requirement implies feature capability
- Incorrect/stale feature metadata
- Index/detail divergence or requirement-feature inconsistency
- **Stage-recording duties**: derive the latest stage actually reached from the artifacts present in REQUIREMENTS_DIR, then check the bound Feature's index row and detail file against the recording duties owned by `.specify/shared/workflow/feature-integration.md` § Core Protocol (steps 2–3) — read that owner; do not re-derive its list here. Judge the two duties separately: a status that is lawfully held (including a terminal status that MUST NOT regress — rule owner: `.specify/templates/feature-details-template.md` § Extension slice rule) never waives the stage record, so a correct status beside a stale date or note is still a finding.

### 5. Severity Assignment

Use this heuristic to prioritize findings:

- **CRITICAL**: Violates constitution MUST, missing core spec artifact, or requirement with zero coverage that blocks baseline functionality
- **HIGH**: Duplicate or conflicting requirement, ambiguous security/performance attribute, untestable acceptance criterion
- **MEDIUM**: Terminology drift, missing non-functional task coverage, underspecified edge case, weak/low-confidence feature mapping
- **LOW**: Style/wording improvements, minor redundancy not affecting execution order

Feature-specific severity rules:

- **CRITICAL**: Requirement bound to an incorrect feature causing scope misdirection, or constitution-mandated feature governance is violated
- **HIGH**: Requirement references feature ID/name that does not exist or conflicts with feature index/detail
- **MEDIUM**: Requirement likely feature-related but binding confidence is low due to incomplete metadata
- **LOW**: Cosmetic naming drift where semantic intent still matches

### 5.5 Finding Validation (independent subagent pass)

Before reporting, every **CRITICAL** and **HIGH** finding MUST be confirmed by an independent read-only validation subagent:

- **Fresh context**: the validator receives ONLY the finding (id, category, claim, severity) and its evidence location(s) — never the detection reasoning or the other findings.
- **Task**: re-read the cited artifacts and return one verdict — `confirm` (evidence supports the claim), `reject` (claim not supported — state why), or `downgrade` (real but overstated — propose severity) — plus both **evidence-boundary fields**: `evidence_supported` (what the cited artifacts actually substantiate, with locations) and `evidence_not_supported` (what the claim asserts beyond that, or what the validator could not observe). A verdict returned without both fields is incomplete; ask for them again rather than reporting the severity alone.
- **Constitution carve-out**: `downgrade` never applies to a Constitution finding — severity precedence is owned by Operating Constraints § **Constitution Authority**, not by this pass. When a validator confirms a principle conflict but proposes a lower severity, keep CRITICAL and adopt only its evidence-boundary fields as the row's scope note.
- **Batching**: validate findings in one parallel dispatch wave; a validator MUST NOT validate a finding it produced. When detection was also delegated under §4's same-author rule, the detection agents and the validators MUST be disjoint sets (owner: `.specify/shared/workflow/objective-analysis-gate.md` rule 5) — a detector validating its own finding is the self-review this pass exists to remove.
- **Downgrade rate is a reported metric**: state how many findings were sent, `confirm`ed, `downgrade`d, and `reject`ed. A wave that downgrades most of what it receives is evidence that detection over-rated severity, and that observation belongs in the report's remediation advice (tighten §4's propagation-surface requirement) rather than being absorbed silently. Do not present a large downgrade count as though the detection pass had been accurate.
- **Report handling**: only `confirm`ed findings keep CRITICAL/HIGH in the main table; `downgrade`d rows get the new severity with a `(validated: downgraded)` note; `reject`ed rows move to a separate **Unvalidated Findings** appendix (never silently dropped). Every validated row carries the validator's `evidence_supported` / `evidence_not_supported` boundary verbatim — a downgrade that drops the boundary discards the very reason it was downgraded. MEDIUM/LOW skip validation.
- **Zero-finding floor**: "no findings" is itself a verdict and MUST carry evidence. When the passes yield no CRITICAL/HIGH, do not simply skip the wave — re-read a sample of the coverage mapping (every requirement whose coverage rests on a single task row, plus a sample of the remaining rows) and record the sample size and its outcome in the Coverage Summary. When the run yields zero findings at any severity, the report MUST state which detection passes ran and what was sampled to confirm the absence.
- **Subagent-unavailable fallback**: if the validation subagent dispatch fails twice in a row (upstream error), a direct evidence re-read by the analyzing agent MAY substitute; the report row MUST then carry `(validated: direct re-read, subagent unavailable)` so the weaker evidence path is visible to the reader.

**DO-NOT-FLAG list** (noise control — do not report these at any severity):
- Style/wording preferences already consistent within the project's own conventions
- Intentional template placeholders (`[REQUIREMENT NAME]`, `TXXX`, sample tasks marked as samples)
- Deferred `[~]` tasks whose recorded reason cites an evidence file in the requirement's directory (probe, baseline, or verification record) — they are deliberate, not gaps. The exemption is evidence-bound: an uncited reason does not qualify, and a task merely *eligible* for deferral (pre-marked as deferrable but not actually deferred) is NOT exempt without that citation — treat it as a coverage question and let the evidence file decide.
- Cross-references into `.specify/` mirrors that duplicate canonical paths by design
- Pre-existing baseline test failures already recorded in the feature's baseline file

### 6. Produce Compact Analysis Report

Output Markdown report (no file writes):

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|

One row per finding; stable IDs prefixed by category initial.

Also include: **Coverage Summary Table**, **Feature Linkage Summary Table**, **Constitution Alignment Issues**, **Unmapped Tasks**, **Metrics** (Total Reqs, Tasks, Coverage %, Feature Linkage %, Ambiguity/Duplication/Inconsistency/Critical counts).

**Rerun delta (post-remediation runs)**: when a prior analysis of the same requirement is available (an earlier report in context or one supplied by the user), the report MUST separate the two directions of change instead of presenting one flat list:

- **Resolved Since Last Run** — prior finding IDs, each with the evidence that closed it (artifact + location), not merely an assertion that it is gone.
- **New Since Last Run** — finding IDs absent from the prior report, including ones the remediation itself introduced.
- Findings unchanged from the prior run stay in the main table marked `(carried over)`.

The headline verdict MUST NOT read as "ready to implement" on the strength of a fully cleared prior set while any new or carried-over CRITICAL/HIGH finding remains open — a cleared backlog and a clean rerun are different claims and the report states both separately.

### 7. Next Actions & Remediation

- CRITICAL issues: resolve before `/speckit.implement`
- LOW/MEDIUM only: proceed with suggestions
- Offer: "Would you like concrete remediation edits for top N issues?" (do NOT apply automatically)

## Operating Principles

- Read-only: NEVER modify files
- Self-authored artifacts are not self-auditable: when this session produced them, delegate detection as well as validation (§4 **Same-author detection delegation**; owner `.specify/shared/workflow/objective-analysis-gate.md`)
- Focus on actionable findings; limit to 50 rows; summarize overflow
- Prioritize constitution violations (always CRITICAL — never a `downgrade` candidate: §5.5 **Constitution carve-out**)
- Feature checks are evidence-based; lower confidence when evidence is weak
- Report zero issues gracefully (emit success report with coverage statistics) — the absence of findings is itself a claim that carries verification evidence: §5.5 **Zero-finding floor**
- Deterministic: rerunning without changes produces consistent results; a rerun *after* remediation additionally reports its delta per §6 **Rerun delta**

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.analyze" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Artifact Commit

At wrap-up, **before** the Feedback and Documentation steps, commit the artifact this command produced — and only that artifact, staged by explicit path. Follow the canonical convention in `.specify/shared/workflow/artifact-commit-step.md`: run the deletion-surface audit first, use a single-line message per `.specify/templates/commit-template.md`, never `git add -A`, and never fold another command's uncommitted artifacts into this commit (report that as an upstream deviation instead). A read-only run that produced no artifact skips this step and says so in one line rather than creating an empty commit. Committing here does not advance the feature's lifecycle status and does not push.

## Handoffs

**Before**: Run `/speckit.tasks` first so there is a complete `tasks.md` to analyze.

**After**: If CRITICAL/HIGH issues found, fix via `/speckit.requirements`, `/speckit.plan`, or `/speckit.tasks` and re-run. Otherwise proceed to `/speckit.implement`.