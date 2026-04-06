## User Input

```text
$ARGUMENTS
```

You **MUST** analyze the user input in `$ARGUMENTS`, infer the user's intent, and use that intent to supplement the analysis context and focus areas.

The user input may include:

1. Special requests that require extra care or custom handling during the analysis workflow.
2. Supplemental information that provides additional context or reference material.
3. Additional analysis focus areas that go beyond the default scope described in this document.

When processing the user input:

1. You **MUST** treat `$ARGUMENTS` as parameters for the current command.
2. Do **NOT** treat the input as a standalone instruction that overrides or replaces the command workflow.
3. If the input contains clear ambiguity, confusion, or likely misspellings that materially affect interpretation, stop and ask the user to rephrase the request with clearer wording. Provide brief guidance when possible.

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

- Identify near-duplicate requirements
- Mark lower-quality phrasing for consolidation

#### B. Ambiguity Detection

- Flag vague adjectives (fast, scalable, secure, intuitive, robust) lacking measurable criteria
- Flag unresolved placeholders (TODO, TKTK, ???, `<placeholder>`, etc.)

#### C. Underspecification

- Requirements with verbs but missing object or measurable outcome
- User stories missing acceptance criteria alignment
- Tasks referencing files or components not defined in spec/plan

#### D. Constitution Alignment

- Any requirement or plan element conflicting with a MUST principle
- Missing mandated sections or quality gates from constitution

#### E. Coverage Gaps

- Requirements with zero associated tasks
- Tasks with no mapped requirement/story
- Non-functional requirements not reflected in tasks (e.g., performance, security)

#### F. Inconsistency

- Terminology drift (same concept named differently across files)
- Data entities referenced in plan but absent in spec (or vice versa)
- Task ordering contradictions (e.g., integration tasks before foundational setup tasks without dependency note)
- Conflicting requirements (e.g., one requires Next.js while other specifies Vue)

#### G. Feature Relevance & Accuracy

- Determine whether the current requirement implementation scope is actually related to a concrete feature candidate
- Flag missing feature binding when requirement text clearly implies a feature capability but no feature can be mapped
- Flag incorrect or stale feature metadata in requirements (wrong Feature ID/name, mismatched scope wording)
- Flag index/detail divergence in feature registry (same feature with conflicting name/status/description)
- Flag requirement-feature inconsistency where requirement claims one feature but tasks/plan evidence aligns with another

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

Output a Markdown report (no file writes) with the following structure:

## Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Duplication | HIGH | requirements.md:L120-134 | Two similar requirements ... | Merge phrasing; keep clearer version |

(Add one row per finding; generate stable IDs prefixed by category initial.)

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|

**Feature Linkage Summary Table:**

| Requirement Key | Candidate Feature | Confidence | Status | Notes |
|-----------------|-------------------|------------|--------|-------|

**Constitution Alignment Issues:** (if any)

**Unmapped Tasks:** (if any)

**Metrics:**

- Total Requirements
- Total Tasks
- Coverage % (requirements with >=1 task)
- Feature Linkage Coverage % (requirements with identified feature candidate)
- Ambiguity Count
- Duplication Count
- Feature Inconsistency Count
- Critical Issues Count

### 7. Provide Next Actions

At end of report, output a concise Next Actions block:

- If CRITICAL issues exist: Recommend resolving before `/speckit.implement`
- If only LOW/MEDIUM: User may proceed, but provide improvement suggestions
- Provide explicit command suggestions: e.g., "Run /speckit.feature to refresh feature registry", "Run /speckit.requirements with refinement", "Run /speckit.plan to adjust architecture", "Manually edit tasks.md to add coverage for 'performance-metrics'"

### 8. Offer Remediation

Ask the user: "Would you like me to suggest concrete remediation edits for the top N issues?" (Do NOT apply them automatically.)

## Operating Principles

### Context Efficiency

- **Minimal high-signal tokens**: Focus on actionable findings, not exhaustive documentation
- **Progressive disclosure**: Load artifacts incrementally; don't dump all content into analysis
- **Token-efficient output**: Limit findings table to 50 rows; summarize overflow
- **Deterministic results**: Rerunning without changes should produce consistent IDs and counts

### Analysis Guidelines

- **NEVER modify files** (this is read-only analysis)
- **NEVER hallucinate missing sections** (if absent, report them accurately)
- **Prioritize constitution violations** (these are always CRITICAL)
- **Feature checks are evidence-based** (use spec/plan/tasks plus feature index/detail; if evidence is weak, lower confidence instead of over-asserting)
- **Use examples over exhaustive rules** (cite specific instances, not generic patterns)
- **Report zero issues gracefully** (emit success report with coverage statistics)

## Context

{ARGS}

## Handoffs

**Before running this command**:

- Run `/speckit.tasks` first so there is a complete `tasks.md` to analyze.

**After running this command**:

- If CRITICAL/HIGH issues are found, apply fixes in `/speckit.requirements`, `/speckit.plan`, or `/speckit.tasks` (as appropriate) and re-run analysis.
- If issues are acceptable or resolved, proceed to `/speckit.implement`.