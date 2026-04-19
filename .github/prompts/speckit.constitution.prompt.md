## User Input

```text
$ARGUMENTS
```

You **MUST** analyze the user input in `$ARGUMENTS`, infer the user's intent, and use that intent to supplement missing context and guide the constitution update process.

The user input may include:

1. Special requests that require extra care or custom handling during the constitution update workflow.
2. Supplemental information that provides additional context or reference material.
3. Specific governance principles, rules, or amendment intentions that go beyond the default scope described in this document.

When processing the user input:

1. You **MUST** treat `$ARGUMENTS` as parameters for the current command.
2. Do **NOT** treat the input as a standalone instruction that overrides or replaces the command workflow.
3. If the input contains clear ambiguity, confusion, or likely misspellings that materially affect interpretation, stop and ask the user to rephrase the request with clearer wording. Provide brief guidance when possible.

## Outline

You are updating the project constitution at `/.specify/memory/constitution.md`. This file is a TEMPLATE containing placeholder tokens in square brackets (e.g. `[PROJECT_NAME]`, `[PRINCIPLE_1_NAME]`). Your job is to (a) collect/derive concrete values, (b) fill the template precisely, and (c) propagate any amendments across dependent artifacts.

### Pre-flight: Project Context Inference

Before processing the template, scan the project to understand its actual context:

- Read `README.md` to determine the project's purpose, language(s), and domain.
- Read `pyproject.toml` / `package.json` / `pom.xml` / `Cargo.toml` (whichever exists) to identify language version, key dependencies, and project type.
- Scan `docs/` directory to understand documentation patterns and scope.
- From this context, determine:
  - **Language(s)**: Python, Java, TypeScript, etc.
  - **Framework(s)**: e.g., FastAPI, Express, Spring Boot.
  - **Project type**: CLI tool / Web SaaS / Library / Single-page app / Monorepo / API service / etc.
  - **Domain context**: e.g., "internal DevOps CLI", "public-facing payment API", "enterprise data pipeline".
- Use this inferred context to:
  - Reject template principles that are irrelevant (e.g., "CLI & Text I/O" for a web SaaS, "Library-First Design" for a standalone script).
  - Replace with domain-appropriate principles in the generated constitution.

Follow this execution flow:

1. Ensure the constitution file exists at `/.specify/memory/constitution.md`.
   - If the file does **not** exist, generate it from the template at `/.specify/templates/constitution-template.md` (copy the template content as the initial constitution, then immediately adapt it to the project's actual context by adding/removing/modifying principles and sections as needed).
   - Once ensured, load the existing constitution template content from `/.specify/memory/constitution.md`.
   - Identify every placeholder token (see Step 2 for pattern details).
   **IMPORTANT**: The user might require less or more principles than the ones used in the template. If a number is specified, respect that - follow the general template. You will update the doc accordingly.
   - **Template Cleanup Mandate**: When bootstrapping from `constitution-template.md`, the LLM MUST:
     (a) Resolve ALL bracketed placeholders into concrete values based on project context.
     (b) Replace generic principles (e.g., "Library-First Design", "CLI & Text I/O") with principles relevant to the actual project domain identified in Pre-flight.
     (c) Remove any unused template sections or rename them to match the project context.
     (d) Delete instructional HTML comments once their guidance has been incorporated; do NOT leave them as leftover artifacts.

2. Collect/derive values for placeholders:
   - Identify all placeholder tokens matching these patterns:
     - Square-bracketed all-caps identifiers: `[ALL_CAPS_IDENTIFIER]`
     - Square-bracketed lowercase or mixed-case placeholders: `[placeholder_name]`
     - Template directives enclosed in HTML comments that need resolution or removal
   - If user input (conversation) supplies a value, use it.
   - Otherwise infer from existing repo context (README, docs, prior constitution versions if embedded).
   - For governance dates: `RATIFICATION_DATE` is the original adoption date (if unknown ask or mark TODO), `LAST_AMENDED_DATE` is today if changes are made, otherwise keep previous.
   - `CONSTITUTION_VERSION` must increment according to semantic versioning rules:
     - MAJOR: Backward incompatible governance/principle removals or redefinitions.
     - MINOR: New principle/section added or materially expanded guidance.
     - PATCH: Clarifications, wording, typo fixes, non-semantic refinements.
   - If version bump type ambiguous, propose reasoning before finalizing.

3. Draft the updated constitution content:
   - Replace every placeholder with concrete text (no bracketed tokens left except intentionally retained template slots that the project has chosen not to define yet—explicitly justify any left).
   - Preserve heading hierarchy and comments can be removed once replaced unless they still add clarifying guidance.
   - Ensure each Principle section: succinct name line, paragraph (or bullet list) capturing non‑negotiable rules, explicit rationale if not obvious.
   - **MUST include** a principle for “以特性（Feature）为核心的开发理念” that mandates:
     - Feature list is the long‑lived project backbone.
     - Every spec/plan/tasks/implement step must re‑evaluate Feature additions/removals.
     - Feature changes are recorded and traceable to spec/plan evidence.
   - Ensure Governance section lists amendment procedure, versioning policy, and compliance review expectations.

4. Consistency propagation checklist (convert prior checklist into active validations):
   For each file below, verify ALL principle references match the updated constitution:
   - `/.specify/templates/plan-template.md` → "Constitution Check" principle list
     MUST map 1:1 to actual principles in the updated constitution; if a principle was
     renamed or renumbered, update the reference accordingly.
   - `/.specify/templates/requirements-template.md` → Feature binding section MUST
     reference the correct principle for Feature-centric development (Principle II by default);
     no stale principle numbers or removed principle references allowed.
   - `/.specify/templates/tasks-template.md` → Any "per Constitution Principle X" refs
     MUST use the correct principle number and name after update.
   - `/README.md` and `/docs/quickstart.md` → Update any references to changed principles.
   - If any file CANNOT be updated automatically, flag it in the Sync Impact Report
     with the specific file path, line range (if determinable), and what needs manual review.

5. Produce a Sync Impact Report (prepend as an HTML comment at top of the constitution file after update):
   - Version change: old → new
   - List of modified principles (old title → new title if renamed)
   - Added sections
   - Removed sections
   - Templates requiring updates (✅ updated / ⚠ pending) with file paths
   - Follow-up TODOs if any placeholders intentionally deferred.

6. Idempotency safeguard:
   - Compare the proposed constitution content with the existing `constitution.md` content.
   - If no semantic change is detected (ignoring whitespace, date-only updates, and the Sync Impact Report):
     - Do NOT increment the version.
     - Inform the user that the constitution is already up to date with the proposed changes.
     - Terminate without writing the file.

7. Validation before final output:
   - No remaining unexplained bracket tokens.
   - Version line matches report.
   - Dates ISO format YYYY-MM-DD.
   - Principles are declarative, testable, and free of vague language ("should" → replace with MUST/SHOULD rationale where appropriate).

8. Write the completed constitution back to `.specify/memory/constitution.md` (overwrite).

9. Output a final summary to the user with:
   - New version and bump rationale.
   - Any files flagged for manual follow-up.
   - Suggested commit message (e.g., `docs: amend constitution to vX.Y.Z (principle additions + governance update)`).

Formatting & Style Requirements:

- Use Markdown headings exactly as in the template (do not demote/promote levels).
- Wrap long rationale lines to keep readability (<100 chars ideally) but do not hard enforce with awkward breaks.
- Keep a single blank line between sections.
- Avoid trailing whitespace.

If the user supplies partial updates (e.g., only one principle revision), still perform validation and version decision steps.

If critical info missing (e.g., ratification date truly unknown), insert `TODO(<FIELD_NAME>): explanation` and include in the Sync Impact Report under deferred items.

Do not create a new template; always operate on the existing `.specify/memory/constitution.md` file.

## Handoffs

**Before running this command**:

- Use when governance/principles need to be introduced or amended.
- If constitution already exists at `/.specify/memory/constitution.md` with a version ≥ 1.0.0
  and no user `$ARGUMENTS` specify changes, warn the user that the constitution is already
  initialized and ask what amendments are desired.

**After running this command**:

- Run `/speckit.feature` to refresh feature index and per-feature detail files under the updated rules.
- Run `/speckit.requirements` for any in-progress specs to ensure alignment with the new constitution.
- If the "Constitution Check" in `plan-template.md` was modified, run `/speckit.plan` on any
  open spec to re-validate against the updated principles.
- Proceed with `/speckit.requirements` to ensure specs align with the updated constitution.