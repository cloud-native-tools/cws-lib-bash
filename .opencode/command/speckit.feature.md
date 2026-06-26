# Background

In an IPD (Integrated Product Development) workflow, a **Feature** is the durable capability layer that
connects customer problems to implementable requirements. In practice, a feature:

- Is **value-oriented**: it represents a meaningful capability that users can perceive.
- Aggregates related functions into a **cohesive scope**.
- Has a deliverable granularity: bigger than a single story, smaller than an epic.

This command keeps feature metadata consistent and up-to-date so that specs, plans, and implementation
work can reference a stable backbone.

## User Input

```text
$ARGUMENTS
```

You **MUST** analyze the user input in `$ARGUMENTS`, infer the user's intent, and use that intent to select the correct execution mode for feature maintenance.

The user input may include:

1. Concrete change context (commit/PR/branch/diff reference) for impact mining.
2. Description-only feature targeting hints for index locate-and-refresh.
3. Additional constraints that require custom handling during refresh.

When processing the user input:

1. You **MUST** treat `$ARGUMENTS` as parameters for the current command.
2. Do **NOT** treat the input as a standalone instruction that overrides or replaces the command workflow.
3. If `$ARGUMENTS` is empty, run global generate/refresh mode.
4. If the input mode is ambiguous, ask concise clarification questions before applying updates.
5. If the input contains clear ambiguity, confusion, or likely misspellings that materially affect interpretation, stop and ask the user to rephrase with clearer wording.

Interpret `$ARGUMENTS` in one of the following modes:

- **No arguments** → global generate/refresh mode.
- **Concrete context** (e.g. a commit id, PR/MR URL, branch name, diff reference) → context mining mode.
- **Description only** → index-locate-and-refresh mode.

## Outline

You are managing feature metadata across two artifacts:

1. **Feature detail files**: `.specify/memory/features/<ID>.md` (instantiated from
   `.specify/templates/feature-details-template.md`).
2. **Feature index**: `.specify/templates/features-template.md`.

Features are classified into two types:

- **Functional features**: user-facing capabilities and workflows.
- **Non-functional features**: quality attributes and engineering characteristics (maintainability,
  observability, testability, security, performance, release/rollback, resilience, etc.).

Features are also classified by temporal origin:

- **Current features**: capabilities that already exist in the codebase (discovered by scanning).
- **Future features**: capabilities the project **should** have but does not yet implement. These are
  identified through gap analysis against the DFX catalog (see below) and `PROJECT_TYPE`-specific
  expectations. Future features are always created with status `Draft`.

## Actions

0. Determine the `PROJECT_TYPE` and `DELIVERY_MODEL` (MUST do first)
   - Infer from repo structure, README/docs, build config, and common layouts.
   - Output an explicit `PROJECT_TYPE` and cite the key evidence (e.g. file names / directories).
   - Also determine the `DELIVERY_MODEL` — how the project's artifacts are consumed:
     - **Runtime code**: compiled/interpreted programs that execute at runtime (services, CLIs, libraries).
     - **Document/prompt artifacts**: templates, prompts, markdown, or configuration files consumed by
       other tools (AI agents, documentation systems, build pipelines).
     - **Hybrid**: both runtime code and document artifacts are primary deliverables.
   - The `DELIVERY_MODEL` directly constrains which DFX categories and future features are relevant.
     Document-artifact projects should focus on content quality, structural consistency, distribution,
     and cross-consumer compatibility — NOT runtime concerns like CI/CD pipelines, shell completion,
     performance profiling, or dependency scanning unless there is a substantial runtime component.

1. Determine the input mode (MUST do first)
   - No arguments → global generate/refresh.
   - Concrete context → context mining.
   - Description only → locate in `.specify/memory/features.md` and refresh.

2. Generate/refresh the **current** feature list (functional + non-functional)
   - For functional features, tailor the list to `PROJECT_TYPE`:
     - CLI: commands/subcommands, input/output formats, config management, pipeline/script integration.
     - Library/SDK: core APIs, extension points, compatibility strategy, examples and docs experience.
     - Framework: core abstractions, extension mechanisms, conventions/defaults, scaffolding.
     - Microservice: domain capabilities, external interfaces, workflows/rules, service collaboration.
     - Other: derive primary capabilities from repo evidence.
   - For non-functional features, derive a broad set from the repo’s current state.

3. Discover **future** features via project-intrinsic gap analysis
   - **Prioritize project-intrinsic features first**: features that directly improve the project’s core
     value delivery. Ask: "What would make this project’s primary artifacts better, more consistent, or
     easier to evolve?" These always take priority over DFX infrastructure features.
   - For `DELIVERY_MODEL = document/prompt artifacts`, focus on:
     - Content structural quality (template validation, schema enforcement).
     - Cross-consumer compatibility (multi-agent portability, format consistency).
     - Artifact lifecycle (versioning, migration, evolution across releases).
     - Authoring experience (contributor tooling, preview, testing against consumers).
   - For `DELIVERY_MODEL = runtime code`, the DFX Catalog below is more applicable.
   - **Avoid over-design**: do NOT propose DFX features that assume a runtime deployment model when the
     project’s primary artifacts are documents/prompts. Specifically:
     - A prompt/template framework does NOT need CI/CD pipelines, shell completion, performance profiling,
       observability stacks, or dependency security scanning unless it has substantial runtime code.
     - Only propose DFX features when the project clearly operates in that domain.
   - Compare the current feature list against the **DFX Catalog** below, filtered by BOTH `PROJECT_TYPE`
     applicability AND `DELIVERY_MODEL` relevance.
   - For each DFX category, check whether the project already has evidence of the capability
     (config files, code patterns, dependencies, CI workflows). If not, AND the category is relevant
     to the delivery model, propose it as a future feature.
   - Also check `PROJECT_TYPE`-specific functional gaps (only those relevant to `DELIVERY_MODEL`):
     - CLI (runtime): shell completion, plugin/extension system, offline mode, i18n/l10n.
     - CLI (document-artifact): template quality, workspace versioning, cross-tool distribution.
     - Library/SDK: type stubs / declaration files, versioning / changelog, migration guides.
     - Framework: hot reload / dev experience, generator / scaffolding, convention-over-configuration defaults.
     - Microservice: API versioning, rate limiting, circuit breaker, service mesh integration.
     - Web App: accessibility (a11y), PWA support, SEO, responsive design.
     - Data Pipeline: data validation / schema enforcement, lineage tracking, backfill support.
     - Other: derive expected capabilities from industry norms for the domain.
   - Future features MUST be created with status `Draft` and a clear description of the gap.
   - In the feature detail file, populate `Key Changes` with the high-level steps needed to implement
     the capability, and `Implementation Notes` with relevant constraints (e.g. "requires Python ≥ 3.10
     for `truststore`").
   - Do NOT propose features that are obviously out of scope for the project’s purpose or scale.
     Use judgment: a prompt template toolkit does not need CI/CD pipelines or shell completion.

4. Apply updates based on the input mode
   - Global mode: scan the repository, infer missing features, refresh all relevant files, **then** run
     future-feature discovery (Action 3).
   - Context mining mode: locate the relevant changes and update/add features impacted by the change.
     Skip future-feature discovery unless the user explicitly requests it.
   - Description-only mode: find the best matching feature in `.specify/memory/features.md` and refresh its
     description, status, and key changes based on the latest repo state.

5. Allocate new IDs (only when creating new features)
   - Determine the next sequential `FEATURE_ID` (three digits) by scanning
     `.specify/memory/features/*.md`.
   - Future features follow the same ID sequence — they are regular features with `Draft` status.

6. Instantiate or update feature detail files
   - For each new feature, instantiate `.specify/templates/feature-details-template.md` and replace all
     placeholders: `[FEATURE_*]`, `[KEY_CHANGE_N]`, `[IMPLEMENTATION_NOTE_N]`, `[STATUS_*_CRITERIA]`.
   - Remove unused trailing placeholder lines (e.g. if only 2 key changes are present, remove 3–5).
   - Dates:
     - `FEATURE_CREATED_DATE` = today (YYYY-MM-DD) for new features.
     - `FEATURE_LAST_UPDATED_DATE` = today for any modified feature.
   - Status MUST be one of: Draft | Planned | Implemented | Ready for Review | Completed.
   - For future features, set status to `Draft` and populate the `Future Evolution Suggestions` section
     with references to related DFX categories and industry best practices.
   - For existing features, preserve unchanged sections and only update necessary parts.

7. Update `.specify/memory/features.md`
   - Ensure the table lists all features with columns:
     `ID | Name | Description | Status | Feature Details | Last Updated`.
   - **Auto-derive `FEATURE_COUNT`**: After mutating the table (add / remove / rename a row), recompute `Total Features` from the data-row count of the table. Do NOT carry over the previous count. Reference shell check (any equivalent acceptable):
     ```sh
     awk -F'|' '/^\| [0-9]{3} \|/ {n++} END{print n}' .specify/memory/features.md
     ```
     The recomputed value MUST match the line `**Total Features**: <N>`. This eliminates the prior hand-maintained-count drift.

8. Sync the root README feature list
   - Read the table in `.specify/memory/features.md`.
   - Generate or replace a “Feature List” section in the root README, split into:
     - Functional Features
     - Non-functional Features (include both current and future/Draft features)
   - Keep README style and heading levels consistent with existing content.

9. Validate before writing
   - No leftover bracketed placeholders in generated/updated files.
   - IDs are unique and sequential.
   - Dates are valid ISO (YYYY-MM-DD).
   - Markdown tables render correctly (pipes/alignment).

### Practical scanning hints

When deriving non-functional features, prioritize scanning common config and infrastructure files when
present (pick what exists in the repo):

- Python: `pyproject.toml`, `requirements.txt`, `Pipfile`, `poetry.lock`, `setup.cfg`, `setup.py`
- Node/TypeScript: `package.json`, lock files, `tsconfig.json`, `next.config.js`, `vite.config.*`
- Java: `pom.xml`, `build.gradle*`, `application.yml` / `application.properties`
- Go: `go.mod`, `go.sum`, `Makefile`, `cmd/`, `internal/`
- Rust: `Cargo.toml`, `Cargo.lock`
- Infra/CI: `Dockerfile`, `docker-compose.yml`, Helm charts, K8s manifests, CI workflows

### DFX Catalog (Design For X)

Use this catalog as a checklist during future-feature discovery (Action 3). For each category, check
whether the project already covers the capability. If not, and the category is applicable to the
`PROJECT_TYPE`, propose a `Draft` feature.

| DFX Category | Abbr | Description | Typical Evidence (if already present) | Applicability |
|------------|------|-------------|---------------------------------------|---------------|
| Design for Testability | DFT | Unit/integration/contract test frameworks, test fixtures, mocking infrastructure, coverage reporting | `pytest`/`jest`/`JUnit` config, `tests/` dir, coverage config, CI test steps | All |
| Design for Observability | DFO | Structured logging, metrics collection, distributed tracing, health endpoints | logging config, `opentelemetry`/`prometheus` deps, `/health` routes | Services, Web Apps, Pipelines |
| Design for Reliability | DFR | Error handling strategy, retry/backoff, circuit breakers, graceful degradation, chaos testing | retry libraries, error middleware, fallback patterns, resilience4j/polly deps | Services, Web Apps, Pipelines |
| Design for Security | DFSec | Authentication, authorization, input validation, secrets management, dependency scanning, SBOM | auth middleware, `.env` handling, `dependabot`/`snyk` config, CSP headers | All |
| Design for Performance | DFP | Profiling, benchmarking, caching strategy, connection pooling, lazy loading, async processing | benchmark suites, cache config (`redis`/`memcached`), profiler config | All |
| Design for Scalability | DFS | Horizontal scaling, stateless design, queue-based decoupling, sharding strategy | message queue deps, stateless session config, k8s HPA, load balancer config | Services, Pipelines |
| Design for Deployment | DFD | CI/CD pipelines, containerization, IaC, blue-green/canary deployment, rollback strategy | `Dockerfile`, CI workflows, Helm/Terraform, deployment scripts | All (except pure libraries) |
| Design for Maintainability | DFM | Code linting/formatting, dependency management, changelog, contribution guidelines, architecture docs | linter config, `.editorconfig`, `CHANGELOG.md`, `CONTRIBUTING.md` | All |
| Design for Compatibility | DFC | API versioning, backward compatibility, migration tooling, deprecation policy, multi-platform support | version headers, migration scripts, platform CI matrix, compatibility tables | Libraries, SDKs, Frameworks |
| Design for Accessibility | DFA | WCAG compliance, keyboard navigation, screen reader support, color contrast, aria labels | a11y test config, `axe`/`pa11y` deps, aria attributes in templates | Web Apps, UI Libraries |
| Design for Internationalization | DFI | i18n/l10n framework, string externalization, locale management, RTL support | i18n libraries (`gettext`/`i18next`/`react-intl`), locale files, translation config | Web Apps, CLIs, UI Libraries |
| Design for Configuration | DFCfg | External configuration, environment-specific overrides, feature flags, secrets injection | config loaders, `.env` files, feature flag SDK, config schema validation | All |
| Design for Documentation | DFDoc | API docs generation, user guides, architecture decision records (ADRs), runbooks | doc generator config (`sphinx`/`typedoc`/`javadoc`), `docs/` dir, ADR dir | All |
| Design for Data Integrity | DFDat | Schema validation, data migration, backup/restore, audit logging, idempotency | migration frameworks (`alembic`/`flyway`), schema validators, audit trail tables | Services, Pipelines |

#### Applying the catalog

1. Filter categories by `PROJECT_TYPE` applicability column.
2. For each applicable category, search the repo for the "Typical Evidence" signals.
3. If evidence is found → the capability is covered; skip or tag the existing feature with the DFX label.
4. If evidence is absent → propose a new `Draft` feature named after the DFX category
   (e.g. "Structured Logging" for DFO, "CI/CD Pipeline" for DFD).
5. In the feature detail, reference the DFX category and describe the gap concisely.
6. Prioritize: propose at most **8–12** future features per run to avoid overwhelming the backlog.
   Focus on the most impactful gaps first (security, testability, and observability are almost always
   high priority).

### Formatting & style requirements

- Use headings exactly as provided by the feature detail template.
- Remove any placeholder checklist section from a detail file after instantiation.
- Keep lists dense; avoid empty bullets.
- Feature names are concise (2–5 words).
- Index table: single header row, all columns present, aligned pipes, no trailing spaces.
- No bracketed placeholders remain after processing.

### Fallbacks / inference

- If a description is absent: derive a one-line summary from the name.
- If status is absent: default to `Draft`.
- Feature detail links MUST point to `.specify/memory/features/[FEATURE_ID].md`.
- Do NOT modify `.specify/templates/feature-details-template.md`; only instantiate copies.

## Handoffs

**Before running this command**:

- Run `/speckit.constitution` if you are changing governance rules that affect feature definitions.
- Ensure you have enough repo context (README/docs) for feature mining or refresh.

**After running this command**:

- Typically proceed to `/speckit.requirements` to produce a requirements specification for a chosen feature.
- If feature scope or naming changes, keep them traceable to the most recent spec/plan evidence.