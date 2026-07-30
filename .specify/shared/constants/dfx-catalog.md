# DFX Catalog (Design For X)

Use this catalog as a checklist during future-feature discovery. For each category, check whether the project already covers the capability. If not, and the category is applicable to the `PROJECT_TYPE` and `DELIVERY_MODEL`, propose a `Draft` feature.

## Catalog Table

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

## Applying the Catalog

1. Filter categories by `PROJECT_TYPE` applicability column AND `DELIVERY_MODEL` relevance.
2. For each applicable category, search the repo for "Typical Evidence" signals.
3. If evidence found → capability is covered; skip or tag existing feature with DFX label.
4. If evidence absent → propose a new `Draft` feature named after the DFX category.
5. In the feature detail, reference the DFX category and describe the gap concisely.
6. Prioritize: propose at most **8–12** future features per run. Focus on most impactful gaps first (security, testability, observability are almost always high priority).

## DELIVERY_MODEL Constraints

- **Document/prompt artifacts**: Focus on content quality, structural consistency, distribution, cross-consumer compatibility. NOT runtime concerns (CI/CD, shell completion, performance profiling, dependency scanning) unless substantial runtime component exists.
- **Runtime code**: Full DFX catalog applicable.
- **Hybrid**: Apply judgment per category.

## PROJECT_TYPE Functional Gaps

Check for missing functional features based on project type:

- **CLI (runtime)**: shell completion, plugin/extension system, offline mode, i18n/l10n
- **CLI (document-artifact)**: template quality, workspace versioning, cross-tool distribution
- **Library/SDK**: type stubs, versioning/changelog, migration guides
- **Framework**: hot reload/dev experience, generator/scaffolding, convention-over-configuration
- **Microservice**: API versioning, rate limiting, circuit breaker, service mesh
- **Web App**: accessibility (a11y), PWA support, SEO, responsive design
- **Data Pipeline**: data validation/schema enforcement, lineage tracking, backfill support

## Practical Scanning Hints

Prioritize scanning common config/infrastructure files:

- **Python**: `pyproject.toml`, `requirements.txt`, `Pipfile`, `poetry.lock`, `setup.cfg`
- **Node/TypeScript**: `package.json`, lock files, `tsconfig.json`, `next.config.js`, `vite.config.*`
- **Java**: `pom.xml`, `build.gradle*`, `application.yml`/`application.properties`
- **Go**: `go.mod`, `go.sum`, `Makefile`, `cmd/`, `internal/`
- **Rust**: `Cargo.toml`, `Cargo.lock`
- **Infra/CI**: `Dockerfile`, `docker-compose.yml`, Helm charts, K8s manifests, CI workflows
