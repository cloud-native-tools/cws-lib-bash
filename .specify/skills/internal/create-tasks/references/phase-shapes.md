# Phase Shapes (conditional overrides for create-tasks)

Extracted from `.specify/templates/commands/tasks.md` § Task Generation Rules → Phase Structure.
These two shapes apply only when the spec's deliverables match their trigger case; the
default within-story order (Tests → Models → Services → Endpoints → Integration) holds
otherwise. Consulted on demand by the `create-tasks` skill (`.specify/skills/internal/create-tasks/SKILL.md`).

## Asset-migration phase shape (porting/vendoring an external code subset)

When a spec copies an external codebase subset in as a hosted asset, split the copy from
its acceptance: the **physical copy + static dependency-closure check** is Foundational
(Phase 2 — it blocks everything), while **governance artifacts** (provenance ledger,
license, ported regression tests, mirrors) belong to the user story that owns the asset.
Two standard acceptance actions for the copy task: (1) grep-assert every import resolves
to the runtime's builtins or inside the subset; (2) **actually resolve all entry modules
with the runtime** (e.g. `node -e "await import(...)"` per entry) — checklist-driven
copying misses transitive dependencies that only real module resolution exposes.

## Doc-feature phase shape (template-only / documentation / prompt-framework specs)

When the spec's deliverables are templates, docs, prompts, or skills rather than runtime
code, "Models → Services → Endpoints" does not apply — do not force it. Switch the
within-story order to the doc-feature taxonomy:

1. **author-section** — write/edit the template or document section itself
2. **mirror-parity** — every row of plan.md's *Mirror Obligations* table MUST be covered
   by an explicit write task and an explicit verify task: rows that share one fan-out
   command (e.g. a single `sync-mirrors.py --write`) MAY share the write task (one per
   phase, not one per row), but each verify task MUST enumerate the rows it covers
   (`diff -q` for mirrors; grep-for-the-edit for regenerated per-tool copies). Mirror
   pairs are first-class tasks, never implicit side-effects of the authoring task.
3. **render-verify** — actually render/execute the artifact (render the diagram, run the
   template through its consumer) and inspect the output
4. **refresh-verify** — re-run the artifact's refresh/regeneration path to confirm
   repeatability

The app-shaped examples in the tasks template are illustrative, not mandatory; pick the
taxonomy that matches the spec's actual deliverables.
