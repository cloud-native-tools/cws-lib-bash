---
description: 创建或更新项目宪法，并保持依赖模板同步
---
<!-- AUTO-GENERATED from templates/commands/constitution.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as governance principles, amendment intentions, or supplemental context.

## Delegation

`/speckit.constitution` creates or updates the project constitution at `/.specify/memory/constitution.md` and keeps every dependent template in sync with the amended principles.

**Load and follow** `.specify/skills/internal/manage-constitution/SKILL.md`:

- **Inputs**: the processed `$ARGUMENTS` substance — governance principles, amendment intentions, or supplemental context; project context for the Pre-flight inference (`README.md`, the manifest file that exists, `docs/`); the template at `/.specify/templates/constitution-template.md` when the constitution file does not exist yet (bootstrap).
- **Outputs**: the updated `.specify/memory/constitution.md` (every bracketed placeholder resolved or explicitly justified, the mandatory-principle set enforced, the `x.y.z.ddd` version bumped per the skill's MAJOR/MINOR/PATCH/DAILY rules) with the Sync Impact Report prepended as an HTML comment; the consistency-propagation checklist applied across the dependent templates (plan / requirements / tasks templates, `README.md`, `docs/tutorials/quickstart.md`) with any un-automatable file flagged; a final summary (new version + bump rationale, flagged files, suggested commit message).

The skill owns the entire workflow: pre-flight project-context inference, bootstrap + Template Cleanup Mandate, placeholder value collection, the version-increment rules, the mandatory-principle payloads, drafting and formatting rules, propagation, validation, write-back, and the edge rules (partial updates, TODO-marked missing info, never create a new template).

## Handoffs

**Before**: Use when governance/principles need introduction or amendment. If constitution exists at version ≥ 1.0.0 with no `$ARGUMENTS`, ask what amendments are desired.

**After**: `/speckit.feature` to refresh feature registry. `/speckit.requirements` for in-progress specs. `/speckit.plan` if "Constitution Check" in plan-template was modified.