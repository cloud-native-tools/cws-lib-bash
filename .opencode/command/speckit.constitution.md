## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as governance principles, amendment intentions, or supplemental context.

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
   - `CONSTITUTION_VERSION` must use the `x.y.z.ddd` format and increment according to the following rules:
     - **MAJOR (x)**: Rewrite-level changes — complete restructuring of principles, backward incompatible governance removals or fundamental redefinitions. Bump: `x+1.0.0.0`
     - **MINOR (y)**: Core section modifications — adding/removing/renaming principles, materially expanding or contracting principle scope. Bump: `x.y+1.0.0`
     - **PATCH (z)**: Descriptive refinements — clarifications, wording improvements, typo fixes, non-semantic adjustments to existing principles. Bump: `x.y.z+1.0`
     - **DAILY (ddd)**: Every update — this counter increments on EVERY constitution update regardless of the change magnitude. Bump: `x.y.z.ddd+1`
     - When x, y, or z increments, the `ddd` counter resets to `0` and then increments to `1` (e.g., `1.2.3.15` → minor bump → `1.3.0.1`).
     - When only ddd increments, x, y, z remain unchanged (e.g., `1.2.3.15` → daily bump → `1.2.3.16`).
   - If version bump type ambiguous, propose reasoning before finalizing.

3. Draft the updated constitution content:
   - Replace every placeholder with concrete text (no bracketed tokens left except intentionally retained template slots that the project has chosen not to define yet—explicitly justify any left).
   - Preserve heading hierarchy and comments can be removed once replaced unless they still add clarifying guidance.
   - Ensure each Principle section: succinct name line, paragraph (or bullet list) capturing non‑negotiable rules, explicit rationale if not obvious.
   - **MUST include** a principle for "Documentation-First" that is ordered ABOVE any
     Test-First / testing principle (i.e. it MUST appear before the testing principle in
     the principle list) and mandates:
     - The project maintains sufficiently detailed and accurate documentation to serve as
       context for AI agents / large language models (project knowledge and background).
     - Documentation does NOT capture implementation details; those belong in the code.
     - Documents are split into smaller, cohesive documents when they grow too complex.
     - Documents cross-reference one another so basic navigation works through internal links.
     - Markdown documents maintain basic metadata (title, purpose/summary, status,
       last-updated date, related links).
   - **MUST include** a principle for "Feature-centric development" that mandates:
     - Feature list is the long‑lived project backbone.
     - Every spec/plan/tasks/implement step must re‑evaluate Feature additions/removals.
     - Feature changes are recorded and traceable to spec/plan evidence.
   - **MUST include** a principle for "Code as the Single Source of Truth" that mandates:
     - Source code is the authoritative source of truth for the project's actual state;
       documentation describes intended/target behavior that may not yet be realized.
     - When establishing or citing facts about how the system currently behaves, code MUST
       take precedence over documentation, unless a document is explicitly designated as
       authoritative for that fact.
     - When code and documentation disagree, treat the divergence as a signal to update the
       documentation (or flag the code as not-yet-implementing the intended goal), not to
       trust the document as current reality.
   - **MUST include** a principle for "Documentation Naming & Location Conventions" that mandates:
     - ALL-CAPS Markdown filenames are RESERVED for conventional, ecosystem-recognized
       root-level artifacts (e.g. `README.md`, `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`);
       ordinary content documents use lowercase `kebab-case.md` and MUST NOT squat these names.
     - A document's meaning derives from its FULL PATH, not just its filename: place docs so
       that `<area>/<topic>.md` reads as "the <topic> of <area>" (e.g. `docs/team/overview.md`,
       `docs/agents/design.md`), reusing generic filenames scoped by directory rather than
       inventing globally-unique names.
     - Tool/framework-mandated filenames are NON-NEGOTIABLE and MUST match the exact required
       pattern and location (e.g. GitHub Copilot commands MUST be `.github/prompts/<name>.prompt.md`);
       such names MUST NOT be renamed to fit project conventions.
   - **MUST include** a principle for "Better-Harness Orientation" that mandates:
     - The project treats itself as a *harness* for AI agent work — an environment in which
       an agent can understand the task, execute on supported and repeatable paths, validate
       its changes, deliver safely, and carry lessons forward — and improvement work is
       oriented toward making that harness better.
     - Improvements are located and motivated against the five Agent Work Loop dimensions
       (Task Understanding, Controlled Execution, Change Validation, Reliable Delivery,
       Learning Capture); the canonical goal model lives at
       `.specify/shared/guidelines/better-harness.md` and MUST be referenced, not restated.
     - Evidence discipline governs improvement claims: a configured asset proves at most that
       a mechanism exists (configured ≠ used); unobserved evidence MUST NOT be treated as a
       defect or a conclusion; "improved" MUST only be claimed from comparable before/after
       evidence.
     - This principle adds orientation, not machinery: it MUST NOT justify new scoring
       systems, maturity reports, or tracking/recording engines.
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
   - Version change: old → new (with bump type: MAJOR / MINOR / PATCH / DAILY)
   - List of modified principles (old title → new title if renamed)
   - Added sections
   - Removed sections
   - Templates requiring updates (✅ updated / ⚠ pending) with file paths
   - Follow-up TODOs if any placeholders intentionally deferred.

6. Validation before final output:
   - No remaining unexplained bracket tokens.
   - Version line matches report and follows `x.y.z.ddd` format.
   - Dates ISO format YYYY-MM-DD.
   - Principles are declarative, testable, and free of vague language ("should" → replace with MUST/SHOULD rationale where appropriate).

7. Write the completed constitution back to `.specify/memory/constitution.md` (overwrite).

8. Output a final summary to the user with:
   - New version (`x.y.z.ddd`) and bump rationale (MAJOR / MINOR / PATCH / DAILY).
   - Any files flagged for manual follow-up.
   - Suggested commit message (e.g., `docs: amend constitution to vX.Y.Z.DDD (principle additions + governance update)`).

Formatting & Style Requirements:

- Use Markdown headings exactly as in the template (do not demote/promote levels).
- Wrap long rationale lines to keep readability (<100 chars ideally) but do not hard enforce with awkward breaks.
- Keep a single blank line between sections.
- Avoid trailing whitespace.

If the user supplies partial updates (e.g., only one principle revision), still perform validation and version decision steps.

If critical info missing (e.g., ratification date truly unknown), insert `TODO(<FIELD_NAME>): explanation` and include in the Sync Impact Report under deferred items.

Do not create a new template; always operate on the existing `.specify/memory/constitution.md` file.

## Handoffs

**Before**: Use when governance/principles need introduction or amendment. If constitution exists at version ≥ 1.0.0 with no `$ARGUMENTS`, ask what amendments are desired.

**After**: `/speckit.feature` to refresh feature registry. `/speckit.requirements` for in-progress specs. `/speckit.plan` if "Constitution Check" in plan-template was modified.