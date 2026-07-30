## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as supplemental analysis focus areas, not standalone instructions.

## Goal

Identify inconsistencies, duplications, ambiguities, underspecified items, and feature-linkage drift across the core artifacts (`requirements.md`, `plan.md`, `tasks.md`) plus feature memory (`.specify/memory/features.md` and `.specify/memory/features/*.md`) before implementation. This command MUST run only after `/speckit.tasks` has successfully produced a complete `tasks.md`.

## Operating Constraints

**STRICTLY READ-ONLY**: Do **not** modify any files. Output a structured analysis report. Offer an optional remediation plan (user must explicitly approve before any follow-up editing commands would be invoked manually).

**Constitution Authority**: The project constitution (`.specify/memory/constitution.md`) is **non-negotiable** within this analysis scope. Constitution conflicts are automatically CRITICAL and require adjustment of the spec, plan, or tasks—not dilution, reinterpretation, or silent ignoring of the principle. If a principle itself needs to change, that must occur in a separate, explicit constitution update outside `/speckit.analyze`.

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

### 6. Produce Compact Analysis Report

Output Markdown report (no file writes):

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|

One row per finding; stable IDs prefixed by category initial.

Also include: **Coverage Summary Table**, **Feature Linkage Summary Table**, **Constitution Alignment Issues**, **Unmapped Tasks**, **Metrics** (Total Reqs, Tasks, Coverage %, Feature Linkage %, Ambiguity/Duplication/Inconsistency/Critical counts).

### 7. Next Actions & Remediation

- CRITICAL issues: resolve before `/speckit.implement`
- LOW/MEDIUM only: proceed with suggestions
- Offer: "Would you like concrete remediation edits for top N issues?" (do NOT apply automatically)

## Operating Principles

- Read-only: NEVER modify files
- Focus on actionable findings; limit to 50 rows; summarize overflow
- Prioritize constitution violations (always CRITICAL)
- Feature checks are evidence-based; lower confidence when evidence is weak
- Report zero issues gracefully (emit success report with coverage statistics)
- Deterministic: rerunning without changes produces consistent results

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this command reached its wrap-up stage. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against `/speckit.analyze`'s declared purpose and produce a short review plus ≥1 concrete, command-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this command's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id` (e.g. the feature key + a run timestamp); if a nested skill/command already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "/speckit.analyze" --unit-type command \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Handoffs

**Before**: Run `/speckit.tasks` first so there is a complete `tasks.md` to analyze.

**After**: If CRITICAL/HIGH issues found, fix via `/speckit.requirements`, `/speckit.plan`, or `/speckit.tasks` and re-run. Otherwise proceed to `/speckit.implement`.