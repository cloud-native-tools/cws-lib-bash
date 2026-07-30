# Feature Integration Protocol

This document defines the standard feature tracking integration used by SDD lifecycle commands.

## Core Protocol

Every SDD lifecycle command (`/speckit.requirements`, `/speckit.plan`, `/speckit.tasks`, `/speckit.implement`, `/speckit.checklist`) automatically integrates with the feature tracking system:

1. **Detect feature context**:
   - If `.specify/memory/features.md` exists, detect the current feature directory (format: `.specify/specs/[REQUIREMENTS_KEY]/`)
   - Extract the feature ID from the directory name

2. **Update feature entry** in `.specify/memory/features.md`:
   - Apply the command-specific status transition (see Status State Machine below)
   - Keep the specification path unchanged
   - Update the "Last Updated" date
   - Automatically stage the changes for git commit

3. **Feature list re-validation** (mandatory for plan, tasks, implement phases):
   - Check whether the current work introduces new Features or deprecates/merges existing ones
   - Ensure functional/non-functional Feature classification remains consistent
   - If changes are discovered, synchronously update:
     - `.specify/memory/features/<ID>.md`
     - `.specify/memory/features.md`
   - Record "key changes / notes" in the Feature detail

## Status State Machine

Each command owns exactly one transition:

| Command | Transition | Notes |
|---------|-----------|-------|
| `/speckit.requirements` | (none) → `Draft` or keep existing | Feature binding only |
| `/speckit.plan` | `Draft → Planned` | MUST NOT land `Implemented` |
| `/speckit.tasks` | Maintain `Planned` | Status unchanged |
| `/speckit.implement` | `Planned → Implemented` | Requires Pre-Status-Flip Gate |
| `/speckit.checklist` | `Implemented → Ready for Review` | If applicable |

## Pre-Status-Flip Gate (implement phase only)

Before advancing to `Implemented`:

1. Convert deferred tasks: `[ ]` → `[~]` with `<!-- deferred: <reason> -->` comment
2. Zero open-task check: `grep -cE '^\- \[ \]' tasks.md` must return 0
3. Verification log completeness: every `SC-NNN` has a status row
4. Deferred task registry: `deferred_tasks=` in `verification.md` lists all `[~]` IDs
5. Only if ALL checks pass: advance status

## Feature Binding Rules (requirements phase)

When `/speckit.requirements` creates a new spec:

1. **Scan for existing Feature**:
   - Search by context: Scan `memory/features/*.md` and `memory/feature-index.md`
   - Search by ID: Check `SPECIFY_FEATURE` env, git branch name, numeric prefix in BRANCH_NAME
   - **Binding-precedent heuristic**: for each candidate Feature, check its sibling specs (prior spec directories already bound to it, e.g. via its detail file's Related Files/history). A Feature whose siblings repeatedly absorbed similar work is strong evidence for **bind**; a candidate with no topical siblings is evidence for **create**. Surface the precedent when recommending bind-vs-create.

2. **Bind or Create**:
   - If matching Feature found → bind to that Feature ID, do NOT create new
   - If NO match → create new Feature from `.specify/templates/feature-details-template.md`, add row to index

3. **Integration responsibilities**:
   - Ensure corresponding Feature entry exists
   - Update `memory/feature-index.md`: keep Status at least `Planned`, update Spec Path, refresh date
   - Never create duplicate Feature IDs

## Feature Continuous Evolution

- Before generating/updating a spec, the Feature list MUST be reviewed
- A new SPEC may introduce a new Feature or make existing ones obsolete
- Functional/non-functional classification consistency MUST be preserved
- Feature changes must record source evidence as "key changes / notes"
