---
name: manage-constitution
description: Create or update the project constitution at `/.specify/memory/constitution.md` from interactive or provided principle inputs — bootstrap it from the constitution template when absent, infer the project's real context, fill every placeholder with concrete values, decide the `x.y.z.ddd` version bump (MAJOR / MINOR / PATCH / DAILY), enforce the mandatory-principle set, propagate every amendment across the dependent templates, and emit the Sync Impact Report. Use this when the user mentions ["constitution", "宪法", "update constitution", "amend constitution", "修订宪法", "governance principles", "治理原则", "principle amendment", "principles update", "version bump", "Sync Impact Report", "constitution version"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/manage-constitution/SKILL.md>"
---

# manage-constitution

## Goal

Create or update the project constitution at `/.specify/memory/constitution.md`. That file is
a TEMPLATE containing placeholder tokens in square brackets (e.g. `[PROJECT_NAME]`,
`[PRINCIPLE_1_NAME]`). The job is threefold: (a) collect/derive concrete values, (b) fill the
template precisely, and (c) propagate any amendments across dependent artifacts.

Owning command: `/speckit.constitution`. Canonical extraction source:
`.specify/templates/commands/constitution.md` § Pre-flight and execution flow steps 1–8 — including
the `x.y.z.ddd` version-increment rules, the consistency-propagation checklist, and the Sync
Impact Report format. Content moved here in substance; the command template keeps entry,
user-input handling, and handoffs only.

## Input Contract

- **Intent**: create (bootstrap) or amend the constitution. The owning command processes
  `$ARGUMENTS` per its User Input Protocol (`.specify/shared/workflow/user-input-protocol.md`) and
  hands over the processed substance: governance principles, amendment intentions, or
  supplemental context.
- **Operating file**: the project constitution at `/.specify/memory/constitution.md`. Paths
  below are repo-root-relative (a leading `/` means the repository root).
- **Scope of writes**: the constitution file plus the dependent artifacts named in the
  consistency-propagation checklist (Step 4). Nothing else.

## Workflow

### Pre-flight: Project Context Inference

Before processing the template, scan the project to understand its actual context:

- Read `README.md` to determine the project's purpose, language(s), and domain.
- Read `pyproject.toml` / `package.json` / `pom.xml` / `Cargo.toml` (whichever exists) to
  identify language version, key dependencies, and project type.
- Scan `docs/` to understand documentation patterns and scope.
- From this context, determine:
  - **Language(s)**: Python, Java, TypeScript, etc.
  - **Framework(s)**: e.g., FastAPI, Express, Spring Boot.
  - **Project type**: CLI tool / Web SaaS / Library / Single-page app / Monorepo / API
    service, etc.
  - **Domain context**: e.g., "internal DevOps CLI", "public-facing payment API",
    "enterprise data pipeline".
- Use this inferred context to:
  - Reject template principles that are irrelevant (e.g., "CLI & Text I/O" for a web SaaS,
    "Library-First Design" for a standalone script).
  - Replace with domain-appropriate principles in the generated constitution.

### Step 1 — Ensure and bootstrap the constitution

- Ensure the constitution file exists at `/.specify/memory/constitution.md`.
- If the file does **not** exist, generate it from
  `/.specify/templates/constitution-template.md` (copy the template content as the initial
  constitution, then immediately adapt it to the project's actual context by
  adding/removing/modifying principles and sections as needed).
- Once ensured, load the existing constitution content and identify every placeholder token
  (Step 2 holds the patterns).
- The user might require fewer or more principles than the ones used in the template. If a
  number is specified, respect that — follow the general template; update the doc
  accordingly.
- **Template Cleanup Mandate** — when bootstrapping from `constitution-template.md`, the LLM
  MUST:
  - (a) resolve ALL bracketed placeholders into concrete values based on project context;
  - (b) replace generic principles (e.g., "Library-First Design", "CLI & Text I/O") with
    principles relevant to the actual project domain identified in Pre-flight;
  - (c) remove any unused template sections or rename them to match the project context;
  - (d) delete instructional HTML comments once their guidance has been incorporated — do
    NOT leave them as leftover artifacts.

### Step 2 — Collect/derive values for placeholders

- Identify all placeholder tokens matching these patterns:
  - Square-bracketed all-caps identifiers: `[ALL_CAPS_IDENTIFIER]`
  - Square-bracketed lowercase or mixed-case placeholders: `[placeholder_name]`
  - Template directives enclosed in HTML comments that need resolution or removal
- If user input (conversation) supplies a value, use it. Otherwise infer from existing repo
  context (README, docs, prior constitution versions if embedded).
- For governance dates: `RATIFICATION_DATE` is the original adoption date (if unknown ask or
  mark TODO); `LAST_AMENDED_DATE` is today if changes are made, otherwise keep previous.
- `CONSTITUTION_VERSION` must use the `x.y.z.ddd` format and increment according to the
  following rules:
  - **MAJOR (x)**: rewrite-level changes — complete restructuring of principles, backward
    incompatible governance removals or fundamental redefinitions. Bump: `x+1.0.0.0`
  - **MINOR (y)**: core section modifications — adding/removing/renaming principles,
    materially expanding or contracting principle scope. Bump: `x.y+1.0.0`
  - **PATCH (z)**: descriptive refinements — clarifications, wording improvements, typo
    fixes, non-semantic adjustments to existing principles. Bump: `x.y.z+1.0`
  - **DAILY (ddd)**: every update — this counter increments on EVERY constitution update
    regardless of the change magnitude. Bump: `x.y.z.ddd+1`
  - When x, y, or z increments, the `ddd` counter resets to `0` and then increments to `1`
    (e.g., `1.2.3.15` → minor bump → `1.3.0.1`).
  - When only ddd increments, x, y, z remain unchanged (e.g., `1.2.3.15` → daily bump →
    `1.2.3.16`).
- If the version bump type is ambiguous, propose reasoning before finalizing.

### Step 3 — Draft the updated constitution content

- Replace every placeholder with concrete text (no bracketed tokens left except
  intentionally retained template slots that the project has chosen not to define yet —
  explicitly justify any left).
- Preserve heading hierarchy, and comments can be removed once replaced unless they still
  add clarifying guidance.
- Ensure each Principle section: succinct name line, paragraph (or bullet list) capturing
  non-negotiable rules, explicit rationale if not obvious.
- **MUST include** the following mandatory principles — the mandate text below is the
  payload the generated constitution must carry (guideline paths are referenced, never
  restated, inside the constitution itself):
  - **Documentation-First** — ordered ABOVE any Test-First / testing principle (it MUST
    appear before the testing principle in the principle list) and mandating: the project
    maintains sufficiently detailed and accurate documentation to serve as context for AI
    agents / large language models (project knowledge and background); documentation does
    NOT capture implementation details (those belong in the code); documents are split into
    smaller, cohesive documents when they grow too complex; documents cross-reference one
    another so basic navigation works through internal links; Markdown documents maintain
    basic metadata (title, purpose/summary, status, last-updated date, related links).
  - **Feature-centric development** — the feature list is the long-lived project backbone;
    every spec/plan/tasks/implement step must re-evaluate Feature additions/removals;
    feature changes are recorded and traceable to spec/plan evidence.
  - **Code as the Single Source of Truth** — source code is the authoritative source of
    truth for the project's actual state; documentation describes intended/target behavior
    that may not yet be realized. When establishing or citing facts about how the system
    currently behaves, code MUST take precedence over documentation, unless a document is
    explicitly designated as authoritative for that fact. When code and documentation
    disagree, treat the divergence as a signal to update the documentation (or flag the code
    as not-yet-implementing the intended goal), not to trust the document as current
    reality.
  - **Documentation Naming & Location Conventions** — ALL-CAPS Markdown filenames are
    RESERVED for conventional, ecosystem-recognized root-level artifacts (e.g. `README.md`,
    `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`); ordinary content documents use lowercase
    `kebab-case.md` and MUST NOT squat these names. A document's meaning derives from its
    FULL PATH, not just its filename: place docs so that `<area>/<topic>.md` reads as "the
    <topic> of <area>" (e.g. `docs/team/overview.md`, `docs/agents/design.md`), reusing
    generic filenames scoped by directory rather than inventing globally-unique names.
    Tool/framework-mandated filenames are NON-NEGOTIABLE and MUST match the exact required
    pattern and location (e.g. GitHub Copilot commands MUST be
    `.github/prompts/<name>.prompt.md`); such names MUST NOT be renamed to fit project
    conventions.
  - **Better-Harness Orientation** — the project treats itself as a *harness* for AI agent
    work — an environment in which an agent can understand the task, execute on supported
    and repeatable paths, validate its changes, deliver safely, and carry lessons forward —
    and improvement work is oriented toward making that harness better. Improvements are
    located and motivated against the five Agent Work Loop dimensions (Task Understanding,
    Controlled Execution, Change Validation, Reliable Delivery, Learning Capture); the
    canonical goal model lives at `.specify/shared/guidelines/better-harness.md` and MUST be
    referenced, not restated. Evidence discipline governs improvement claims: a configured
    asset proves at most that a mechanism exists (configured ≠ used); unobserved evidence
    MUST NOT be treated as a defect or a conclusion; "improved" MUST only be claimed from
    comparable before/after evidence. This principle adds orientation, not machinery: it
    MUST NOT justify new scoring systems, maturity reports, or tracking/recording engines.
  - **One Source of Truth (Authority & Reference Discipline)** — every fact (a concept's
    meaning, a normative rule, a threshold, an enumerated list, a configuration value, a
    count) has exactly one authoritative definition point (its **owner**), and every other
    location reaches it by reference rather than by copy. The full discipline (owner
    declaration, the owner-selection order, when a duplicate is legitimate, the counts and
    enumerations rules, the disagreement procedure) lives at
    `.specify/shared/guidelines/one-source-of-truth.md` and MUST be referenced, not
    restated. On a disagreement the owner is authoritative and every diverging location is
    stale; the repair converts the copy into a reference instead of re-wording it to agree.
    This principle adds a way of writing, not machinery: it MUST NOT justify a
    duplicate-fact scanner, an authority registry, or any other new scoring or tracking
    system.
  - **User-Facing Comprehension (No Jargon, With Context)** — every message a flow sends to
    a human is readable by someone who did not take part in the run, which bounds both its
    vocabulary and the context it carries. The full discipline (permitted-jargon whitelist,
    forbidden-jargon blacklist, context floor and ceiling, their adjudication order,
    reproducible verdict questions) lives at
    `.specify/shared/guidelines/user-facing-comprehension.md` and MUST be referenced, not
    restated. Jargon is bounded rather than banned — a term stands unexplained only where a
    closed whitelist condition holds — and context is bounded the same way: carry the facts
    a reader needs in order to act, and reach everything else by path reference. This
    principle adds a way of writing, not machinery: it MUST NOT justify a jargon linter, a
    wording scorer, a maturity report, or any other new tracking system.
  - **Fast Fail (Surface Load-Bearing Anomalies, Repair the Rest)** — an anomaly found
    mid-run is triaged before it is acted on, so a wrong premise stops where it is
    discovered instead of spreading into every artifact built on it. The full discipline
    (binary triage criterion, the two closed lists, the surface-report form, the
    bidirectional growth rule, the boundaries with adjacent disciplines) lives at
    `.specify/shared/guidelines/fast-fail.md` and MUST be referenced, not restated. Triage
    is binary and decidable — correction (exactly one reading consistent with the recorded
    intent) is repaired in passing and disclosed; decision (choosing between readings, or
    inventing intent no artifact records) halts at the anomaly point and hands the user a
    surface report. A severity scale or an undecidable middle tier MUST NOT be substituted,
    and a list hit is not a licence: the criteria outrank list membership. A green check is
    a claim, not evidence: where a check would not go red if its subject broke, that pass is
    reported as a fast fail rather than cited as proof. Subagents are injected at dispatch —
    a standing instruction layer cannot reach them, so the caller carries the clause into
    every dispatch and requires an explicit anomaly line on return. This principle adds a
    way of triaging, not machinery: it MUST NOT justify an anomaly-detection engine, a
    triage scorer, a maturity report, or any new ledger or registry.
- Ensure the Governance section lists amendment procedure, versioning policy, and compliance
  review expectations.

### Step 4 — Consistency propagation checklist

Convert the prior checklist into active validations. For each file below, verify ALL
principle references match the updated constitution:

- `/.specify/templates/plan-template.md` → the "Constitution Check" principle list MUST map
  1:1 to actual principles in the updated constitution; if a principle was renamed or
  renumbered, update the reference accordingly.
- `/.specify/templates/requirements-template.md` → the Feature binding section MUST
  reference the correct principle for Feature-centric development (Principle II by default);
  no stale principle numbers or removed principle references allowed.
- `/.specify/templates/tasks-template.md` → any "per Constitution Principle X" refs MUST use
  the correct principle number and name after update.
- `/README.md` and `/docs/tutorials/quickstart.md` → update any references to changed
  principles.
- If any file CANNOT be updated automatically, flag it in the Sync Impact Report with the
  specific file path, line range (if determinable), and what needs manual review.

### Step 5 — Sync Impact Report

Produce a Sync Impact Report and prepend it as an HTML comment at the top of the
constitution file after update. It carries:

- Version change: old → new (with bump type: MAJOR / MINOR / PATCH / DAILY)
- List of modified principles (old title → new title if renamed)
- Added sections
- Removed sections
- Templates requiring updates (✅ updated / ⚠ pending) with file paths
- Follow-up TODOs if any placeholders were intentionally deferred.

### Step 6 — Validation before final output

- No remaining unexplained bracket tokens.
- Version line matches the report and follows the `x.y.z.ddd` format.
- Dates in ISO format YYYY-MM-DD.
- Principles are declarative, testable, and free of vague language ("should" → replace with
  MUST/SHOULD rationale where appropriate).

### Step 7 — Write back

Write the completed constitution to `/.specify/memory/constitution.md` (overwrite).

### Step 8 — Final summary to the user

- New version (`x.y.z.ddd`) and bump rationale (MAJOR / MINOR / PATCH / DAILY).
- Any files flagged for manual follow-up.
- Suggested commit message, e.g.
  `docs: amend constitution to vX.Y.Z.DDD (principle additions + governance update)`.

### Formatting & style requirements

- Use Markdown headings exactly as in the template (do not demote/promote levels).
- Wrap long rationale lines to keep readability (<100 chars ideally) but do not hard-enforce
  with awkward breaks.
- Keep a single blank line between sections.
- Avoid trailing whitespace.

### Edge rules

- If the user supplies partial updates (e.g., only one principle revision), still perform
  the validation and version decision steps.
- If critical info is missing (e.g., the ratification date is truly unknown), insert
  `TODO(<FIELD_NAME>): explanation` and include it in the Sync Impact Report under deferred
  items.
- Do not create a new template; always operate on the existing
  `/.specify/memory/constitution.md` file.

## Boundaries

- This skill owns the constitution's content lifecycle only. Follow-on work — refreshing the
  feature registry (`/speckit.feature`), updating requirements (`/speckit.requirements`),
  re-checking plans after a "Constitution Check" change (`/speckit.plan`) — is routed by the
  owning command's Handoffs, not re-invoked here.
- User-input processing and handoff wiring stay with the command template
  (`.specify/templates/commands/constitution.md`); this skill starts from the processed intent.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:manage-constitution" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:manage-constitution" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:manage-constitution" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
