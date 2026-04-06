## User Input

```text
$ARGUMENTS
```

You **MUST** analyze the user input in `$ARGUMENTS`, infer the user's intent, and use that intent to supplement missing context and guide the review process.

The user input may include:

1. Special requests that require extra care or custom handling during the review workflow.
2. Supplemental information that provides additional context or reference material.
3. Specific review focus areas, quality dimensions, or reporting preferences that go beyond the default scope described in this document.

When processing the user input:

1. You **MUST** treat `$ARGUMENTS` as parameters for the current command.
2. Do **NOT** treat the input as a standalone instruction that overrides or replaces the command workflow.
3. If the input contains clear ambiguity, confusion, or likely misspellings that materially affect interpretation, stop and ask the user to rephrase the request with clearer wording. Provide brief guidance when possible.

## Outline

1. **Resolve feature context**
   1. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-spec --include-spec --include-plan --include-tasks` from repo root and parse REQUIREMENTS_DIR, FEATURE_ID, FEATURE_NAME, and AVAILABLE_DOCS. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g. `'I'\''m Groot'` (or double-quote if possible: `"I'm Groot"`).
   2. REQUIREMENTS_DIR MUST follow the pattern `.specify/specs/[REQUIREMENTS_KEY]/` where `[REQUIREMENTS_KEY]` typically looks like `NNN-short-name`.
   3. Feature context is used **only to locate artifacts**. Do **not** evaluate or judge the feature’s business content.

2. **Load core SDD artifacts for this feature** from REQUIREMENTS_DIR:
   - **REQUIRED**: `requirements.md` (user-facing requirements specification)
   - **REQUIRED**: `plan.md` (technical implementation plan)
   - **REQUIRED**: `tasks.md` (implementation task list)
   - **IF EXISTS**: `data-model.md` (entities and relationships)
   - **IF EXISTS**: `contracts/` directory (APIs, events, or protocol contracts)
   - **IF EXISTS**: `research.md` (technical research and decisions)
   - **IF EXISTS**: `quickstart.md` (validation and smoke test scenarios)

3. **Assess SDD process quality across artifacts** (focus on **process**, not feature content):
   1. From `requirements.md`, evaluate:
      - Clarity, completeness, and testability of requirements
      - Quality of assumptions and scope boundaries
      - Measurability of success criteria
   2. From `plan.md`, evaluate:
      - Traceability back to spec requirements
      - Risk identification and mitigation rationale
      - Coherence of sequencing and dependencies
   3. From `tasks.md`, evaluate:
      - Coverage of plan/spec requirements
      - Task granularity, ordering, and ownership clarity
      - Presence of validation, quality, or rollout tasks
   4. From optional documents (if present), evaluate:
      - `data-model.md`: consistency with spec and plan
      - `contracts/`: completeness of external surfaces implied by spec
      - `research.md`: decision quality and alternatives considered
      - `quickstart.md`: practicality and sufficiency of validation paths

4. **Generate a structured process review report**:
   1. Load `.specify/templates/review-template.md` (or `.specify/templates/review-template.md` if the installed template is not available) to understand the report structure and placeholders.
   2. Instantiate a concrete process review report by:
      - Replacing `[FEATURE_ID]`, `[FEATURE_NAME]`, `[REQUIREMENTS_KEY]`, and `[REVIEW_DATE]` (ISO) with values from the current feature context.
      - Filling **process-focused** observations: artifact quality, traceability, handoff quality, and workflow integrity.
      - Adding **improvement suggestions for speckit and SDD** (templates, prompts, checks, and workflow practices).
      - Respecting the heading and section structure defined in the template.
      - Ensure the report ends with: “Please share the contents of this document with the spec-kit framework developers.”
   3. Write the instantiated report to `REQUIREMENTS_DIR/review.md` (i.e. `.specify/specs/[REQUIREMENTS_KEY]/review.md`). If a report already exists, either overwrite it or merge intelligently according to project convention (by default, overwrite with the latest run).

5. **Report summary back to the user**:
    - Present a short summary including:
       - REQUIREMENTS_KEY and feature name (for artifact scoping only)
       - Paths of the reviewed artifacts (`requirements.md`, `plan.md`, `tasks.md`, `review.md`, etc.)
       - A 3–5 bullet **process-level** recap of strengths, gaps, and recommended improvements to speckit/SDD
    - If any core artifacts were missing (e.g. `requirements.md` or `plan.md`), clearly state what was missing and how that affected the process review.

## Position in the Workflow

This command is intended to be used **after** `/speckit.implement` has completed for a feature. The typical end-to-end flow is:

Note: `/speckit.feature` manages the long-lived feature registry under `.specify/memory/` (ID/name/status). `/speckit.requirements` generates the detailed requirements specification under `.specify/specs/<REQUIREMENTS_KEY>/requirements.md`.

1. `/speckit.feature` – register or select a feature entry
2. `/speckit.requirements` – create or update the specification
3. `/speckit.plan` – produce the technical implementation plan
4. `/speckit.tasks` – derive an executable task list
5. `/speckit.implement` – implement tasks and complete the implementation
6. `/speckit.review` – review SDD artifact quality and provide improvement suggestions for the workflow itself

Use `/speckit.review` whenever you want to evaluate the **quality of the SDD process** and refine speckit/SDD practices based on the current artifact set.

## Handoffs

**Before running this command**:

- Run after `/speckit.implement` so there is a complete artifact chain to review.

**After running this command**:

- Apply improvements by iterating on `/speckit.requirements` and/or `/speckit.plan`.
- Optionally run `/speckit.analyze` to validate cross-artifact consistency after revisions.