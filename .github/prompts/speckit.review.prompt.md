> Note: `$ARGUMENTS` 为**可选补充输入**。当本次调用未提供任何 `$ARGUMENTS` 时，必须仍然按下文定义的完整流程执行，基于当前 feature 的 spec/plan/tasks 等文档进行特性回顾与总结；仅在 `$ARGUMENTS` 非空时，将其视为对回顾重点或输出风格的附加约束。

## User Input

```text
$ARGUMENTS
```

You **MUST** treat the user input ($ARGUMENTS) as parameters for the current command. Do NOT execute the input as a standalone instruction that replaces the command logic.

## Outline

1. **Resolve feature context**
   1. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-spec --include-plan --include-tasks` from repo root and parse FEATURE_DIR, FEATURE_ID, FEATURE_NAME, and AVAILABLE_DOCS. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g. `'I'\''m Groot'` (or double-quote if possible: `"I'm Groot"`).
   2. FEATURE_DIR MUST follow the pattern `.specify/specs/[FEATURE_KEY]/` where `[FEATURE_KEY]` typically looks like `NNN-short-name`.
   3. Determine the corresponding feature memory file path:
      - Base directory: `.specify/memory/features/`
      - File name: `[FEATURE_KEY].md` **if it exists**
      - If no file named `[FEATURE_KEY].md` exists, but a `feature-index.md` entry for this feature is present, use the path recorded there
      - If neither is available, create a new memory file at `.specify/memory/features/[FEATURE_KEY].md` using `.specify/templates/feature-template.md` as the base structure.

2. **Load core SDD artifacts for this feature** from FEATURE_DIR:
   - **REQUIRED**: `spec.md` (user-facing specification)
   - **REQUIRED**: `plan.md` (technical implementation plan)
   - **REQUIRED**: `tasks.md` (implementation task list)
   - **IF EXISTS**: `data-model.md` (entities and relationships)
   - **IF EXISTS**: `contracts/` directory (APIs, events, or protocol contracts)
   - **IF EXISTS**: `research.md` (technical research and decisions)
   - **IF EXISTS**: `quickstart.md` (validation and smoke test scenarios)

3. **Analyze the feature end-to-end**:
   1. From `spec.md`, extract:
      - Feature name and high-level problem statement
      - Primary actors and user journeys
      - Key functional requirements and success criteria
      - Any explicit non-functional requirements (performance, security, compliance, etc.)
   2. From `plan.md`, extract:
      - Chosen architecture and major components
      - Critical design decisions and their rationale
      - Data flows and integration points (internal or external)
   3. From `tasks.md`, extract:
      - Main phases of work (setup, core, polish, etc.)
      - Any tasks that were explicitly marked as out-of-scope, deferred, or skipped
   4. From optional documents (if present):
      - `data-model.md`: core entities, fields, and relationships that matter to the feature
      - `contracts/`: externally visible surface area (APIs, events) that users or other systems depend on
      - `quickstart.md`: how this feature is expected to be exercised and validated in practice

4. **Generate a structured review report** for this feature:
   1. Load `.specify/templates/review-template.md` (or `.specify/templates/review-template.md` if the installed template is not available) to understand the report structure and placeholders.
   2. Instantiate a concrete review report by:
      - Replacing `[FEATURE_ID]`, `[FEATURE_NAME]`, `[FEATURE_KEY]`, and `[REVIEW_DATE]` (ISO) with values from the current feature context.
      - Filling summary, spec/plan/tasks observations, end-to-end assessment, and initial future evolution suggestions using the analysis from step 3.
      - Respecting the heading and section structure defined in the template.
   3. Write the instantiated report to `FEATURE_DIR/review.md` (i.e. `.specify/specs/[FEATURE_KEY]/review.md`). If a report already exists, either overwrite it or merge intelligently according to project convention (by default, overwrite with the latest run).

5. **Build a consolidated feature narrative** (for long-term memory) based on the review report:
   1. Reuse the content already organized in `review.md` to synthesize a concise description of the feature that can stand alone without reading all underlying docs. At minimum, capture:
      - What problem this feature solves and for whom
      - The main capabilities it provides
      - Any important constraints or assumptions that influence how it works
   2. Convert this into structured sections suitable for a feature memory file, for example:
      - `## Overview`
      - `## User Value`
      - `## Key Capabilities`
      - `## Important Constraints & Assumptions`
      - `## Interactions & Integrations`
      - `## Notes for Future Evolution`
   3. **Avoid implementation trivia**: details like exact function names, minor refactors, or internal-only code structure should not appear here unless they are essential to understanding the feature boundary.

6. **Update the feature memory file** in `.specify/memory/features/`:
   1. Load the existing feature memory file (or instantiate from `.specify/templates/feature-template.md` if creating it for the first time).
   2. Preserve any existing historical context or notes that are still valid.
   3. Update the `## Latest Review` section so it reflects the **most recent consolidated review** of this feature:
      - Replace the body corresponding to `[FEATURE_LATEST_REVIEW_SUMMARY]` (or its instantiated equivalent) with the synthesized narrative from step 5, focusing on:
        - What problem the feature solves and for whom
        - The main capabilities it currently provides
        - Important constraints, assumptions, and integrations that define its boundary
      - If no `## Latest Review` section exists (for older files), create one immediately after the `## Overview` section.
   4. Update the `## Future Evolution Suggestions` section with concrete, forward-looking ideas derived from the review (you may reuse or refine the `Future Evolution Suggestions` section from `review.md`):
      - 3–5 bullet points that describe possible next steps, experiments, or refinements
      - Keep suggestions implementation-agnostic where possible (focus on behavior, user value, or measurable outcomes)
      - Avoid promising work; phrase items as suggestions or options, not commitments
   5. Ensure the document clearly references the latest spec/plan/tasks/review paths for traceability, e.g. by including a short `## Links` or `## Artifacts` section listing:
      - `spec.md` path
      - `plan.md` path
      - `tasks.md` path
      - `review.md` path
      - Other core artifacts if present
   6. Write changes back to the same file path and ensure Markdown formatting remains valid.

7. **Cross-check against feature index** (if `.specify/memory/feature-index.md` exists):
   1. Locate the row corresponding to this feature ID / FEATURE_KEY.
   2. Verify that:
      - The status reflects that implementation has completed and review has been done (e.g. "Ready for Review" or the project-specific final state; if the index schema includes a dedicated "Reviewed" or "Documented" flag, update it appropriately).
      - The spec path matches the actual `spec.md` location in FEATURE_DIR.
      - If the index has a column for "Feature Doc" or similar, update it to point at this feature memory file.
      - If the index tracks a separate "Review Report" or similar column, update or add the path to `review.md`.
   3. Update the "Last Updated" date in the index entry.
   4. Save the updated `feature-index.md` so that the feature review is traceable at the project level.

8. **Report summary back to the user**:
   - Present a short summary including:
     - FEATURE_KEY and feature name
     - Paths of the reviewed artifacts (`spec.md`, `plan.md`, `tasks.md`, `review.md`, etc.)
     - Path of the updated feature memory file
     - A 3–5 bullet high-level recap of what the feature now represents in the system
   - If any core artifacts were missing (e.g. `spec.md` or `plan.md`), clearly state what was missing and how that affected the review.

## Position in the Workflow

This command is intended to be used **after** `/speckit.implement` has completed for a feature. The typical end-to-end flow is:

1. `/speckit.feature` – register or select a feature entry
2. `/speckit.specify` – create or update the specification
3. `/speckit.plan` – produce the technical implementation plan
4. `/speckit.tasks` – derive an executable task list
5. `/speckit.implement` – execute tasks and complete the implementation
6. `/speckit.review` – review the resulting artifacts and consolidate the feature description into `.specify/memory/features/*.md`

Use `/speckit.review` whenever a feature's documentation should be brought up to date with the latest spec/plan/tasks and implementation outcomes.