---
name: manage-features
description: Maintain and refresh the project feature registry — the feature index (`.specify/memory/features.md`) plus the per-feature detail files (`.specify/memory/features/<ID>.md`) — by reconciling it against repo reality under the reconcile model (tolerance band, archive-not-delete, never regress status). Generates/refreshes current features (functional + non-functional), discovers future features via gap analysis, allocates sequential three-digit IDs, instantiates detail files from the template, keeps the index table and the README "Feature List" in sync, and validates. Use this when the user mentions ["feature registry", "features.md", "feature index", "feature list", "feature details", "维护特性", "特性注册表", "特性索引", "特性清单", "更新特性", "特性详情", "reconcile features", "future features", "gap analysis", "DFX", "功能特性"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/manage-features/SKILL.md>"
---

# manage-features

## Goal

Keep the project's **feature registry** converged with what the repo actually delivers:
a durable registry (index + per-feature detail files) that reflects current features,
records credible future gaps, and stays format-clean across repeated invocations. This
skill owns the executable core of `/speckit.feature` — the reconcile model application
and Actions 0–9 — while the command template keeps entry, user-input handling and
lifecycle only.

Canonical extraction source: `.specify/templates/commands/feature.md` § Outline (registry
surfaces + feature classification), § Reconcile model, § Actions, and § Formatting
Requirements. Content moved here verbatim in substance.

## Input Contract

- **Registry surfaces** (the durable artifact space this skill owns):
  1. **Feature detail files**: `.specify/memory/features/<ID>.md` — instantiated from
     `.specify/templates/feature-details-template.md`.
  2. **Feature index**: `.specify/memory/features.md` — one table row per feature.
- **Feature classification**: **functional** (user-facing) vs **non-functional** (quality
  attributes), and **current** (existing) vs **future** (gap-identified, status `Draft`).
- **Repo context must be readable** (README/docs/build config): desired state is computed
  from what the repo actually delivers, so a run without repo context cannot diff.
- **Scope resolution** (one engine, three inputs — see the table in Reconcile Model):
  no args → full-registry reconcile; concrete context (commit/PR/branch) → fan-out
  mining; a feature description → single-target convergence.

## Reconcile Model

The registry is a durable artifact space and this skill is its reconcile engine. The
pattern itself — full loop R0–R6, tiered confirmation, scope zones, anti-patterns — is
owned by `.specify/shared/patterns/reconcile-pattern.md`; read it before designing
changes to this engine. This section records only the registry-specific application.

**Desired state** = what the repo actually delivers (current features) + credible gaps
(future features) + registry format rules; **current state** = the existing index +
detail files. Each run observes, diffs through a tolerance band, and converges:

| Input | Scope | Behavior |
|-------|-------|----------|
| No args | **Full-registry reconcile** | Diff every registry row against repo reality; empty registry → bootstrap from scratch |
| Concrete context (commit/PR/branch) | **Fan-out mining** | Extract feature-relevant facts from the context, triage each to its owning feature row (or a new one) |
| Description | **Single-target convergence** | Locate the matching feature and converge only it |

Three binding rules of the application:

- **Tolerance band**: rows whose Name/Description/Status still match repo reality are
  left untouched — do not rewrite descriptions for cosmetic wording, do not touch
  `Last Updated` on unchanged rows. Unchanged rows stay byte-identical.
- **Archive-not-delete**: never remove a feature row or detail file because the
  capability disappeared from the code — keep the row and mark its status/description
  accordingly (history is part of the registry's value).
- **Never regress status**: registry convergence must not move a feature's status
  backward (e.g. Implemented → Draft) without explicit user confirmation.
  > Gate probe: gate-feature-status-regression — after the user decision, record firing
  > evidence per `.specify/shared/guidelines/confirmation-gates.md` §门控观察协议
  > (non-blocking).

## Workflow (Actions 0–9)

0. **Determine PROJECT_TYPE and DELIVERY_MODEL** (MUST do first):
   - Infer from repo structure, README/docs, build config.
   - DELIVERY_MODEL: `runtime code` | `document/prompt artifacts` | `hybrid`.
   - This constrains which DFX categories and future features are relevant.

1. **Determine scope**: No args → full-registry reconcile. Concrete context → fan-out
   mining. Description → single-target convergence (table above).

2. **Generate/refresh current features** (functional + non-functional):
   - Functional: tailor to PROJECT_TYPE (CLI: commands/IO/config; Library:
     APIs/extension; Framework: abstractions/scaffolding;
     Microservice: domain/interfaces/workflows).
   - Non-functional: derive from repo's current state.

3. **Discover future features** via gap analysis:
   - Prioritize project-intrinsic features first (what improves core value delivery).
   - For document artifacts: content quality, cross-consumer compatibility, lifecycle,
     authoring experience.
   - For runtime code: apply the DFX Catalog from
     `.specify/shared/constants/dfx-catalog.md` (category applicability, typical
     evidence, and the 8–12-per-run cap live there — do not restate them here).
   - Avoid over-design: don't propose runtime DFX for document-only projects.
   - Future features: status `Draft`, max 8–12 per run.

4. **Apply updates** per scope, honoring the tolerance band (unchanged rows stay
   byte-identical) and the never-regress-status rule.

5. **Allocate IDs**: Sequential three-digit FEATURE_ID from scanning
   `.specify/memory/features/*.md`.

6. **Instantiate/update detail files**: From `.specify/templates/feature-details-template.md`,
   replace all placeholders, remove unused ones (placeholder glossary and replacement
   rules are owned by that template). Dates ISO format.

7. **Update `.specify/memory/features.md`**: Table with
   `ID | Name | Description | Status | Feature Details | Last Updated`. Auto-derive
   FEATURE_COUNT from table row count — recompute on every write, never hand-maintain
   (the auto-derive contract is owned by `.specify/templates/feature-index-template.md`).

8. **Sync README**: Generate/replace the "Feature List" section split into Functional
   and Non-functional.

9. **Validate & report residuals**: No leftover placeholders, unique sequential IDs,
   valid dates, correct markdown tables. Close with a brief residual report: rows
   converged / rows tolerated (unchanged) / new rows added / items needing user
   decision. If nothing changed, say so plainly.

## Formatting Requirements

- Feature names: 2–5 words
- Index table: single header row, all columns, aligned pipes
- Status vocabulary: `Draft | Planned | Implemented | Ready for Review | Completed`
- Feature detail links: `.specify/memory/features/[FEATURE_ID].md`
- Do NOT modify templates; only instantiate copies

## Boundaries

- **Status advancement** is not this skill's job beyond recording what repo reality
  already shows: the canonical transition table (Draft → Planned owner `/speckit.plan`,
  Planned → Implemented owner `/speckit.implement`, etc.) lives in
  `.specify/templates/feature-details-template.md` § Canonical Status State Machine.
  This skill records statuses per that machine and never regresses them (rule above);
  the extension-slice rule there also forbids `Implemented → Planned` on extension work.
- **Requirements authoring** is not this skill — that is `/speckit.requirements`. The
  registry tracks feature metadata; requirement specs live under `.specify/specs/`.
- **Templates are read-only inputs** (`.specify/templates/feature-details-template.md`,
  `.specify/templates/feature-index-template.md`): instantiate copies, never edit the
  template files themselves.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:manage-features" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:manage-features" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:manage-features" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
