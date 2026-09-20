# Spec Kit Framework Map

Single source of truth for the `.specify/` layout map. Referenced from the `## Spec Kit Framework Map` summary in `.specify/instructions.md` — keep that summary a pointer; the table lives here.

This is a **map, not a manual**: it tells you *what* exists and *where* it lives; the *how* belongs to the documents each row points to. The framework state lives under `.specify/`:

| What | Where | Notes (what lives there — not how to use it) |
|------|-------|-----------------------------------------------|
| Project memory | `.specify/memory/` | constitution, features index + `features/<ID>.md`, glossary, `tools/` records, feedback store |
| Artifact templates | `.specify/templates/` | requirements/plan/tasks templates rendered by `/speckit.*` |
| Automation scripts | `.specify/scripts/` | bash/python engines invoked by commands and skills |
| Installed skills | `.specify/skills/` | one directory per skill (`SKILL.md` + references/ + scripts/) |
| Skills system guide | `.specify/skills.md` | how skills are discovered and created — no registry |
| Tools system guide | `.specify/tools.md` | how tools are recorded and discovered — no registry |
| Git workflow state | `.specify/git-workflow.md` | branch-role managed block, machine-maintained by the `git-workflow` skill |
| **Agent Templates** | `.specify/agents/templates/` | capability descriptions — shipped role set installed by `specify init`; each `.agent.md` is self-contained |
| **Agent Instances** | `.specify/agents/instances/` | responsibility-bound agents authored in this project; reference a Template |
| **Agent Execution** | `.specify/agents/execution/` | dispatch `configs/` + `scripts/` (tracked); runtime `logs/` (gitignored, never committed) |
| Teams | `.specify/teams/<slug>/` | team definitions + `runs/` reports; run intermediates in git-ignored `.work/` |
| Derivations | `.specify/derive/` | one derivation archive per topic (`<topic-slug>/derive.md`) plus the project-level reasoning-move library `moves.md` (engine-written, accumulating); record semantics in `definitions/derivation-definitions.md` |
| Shared definitions & conventions | `.specify/shared/` | canonical concept docs — e.g. agent taxonomy (`definitions/agent-definitions.md`), subagent modes (`definitions/subagent-definitions.md`), tool definitions, workflow conventions |
| Feature specs | `.specify/specs/<ID>-<slug>/` | requirements / plan / tasks / verification per feature |
| Canonical AI instructions | `.specify/instructions.md` | single source of truth for project-level AI instructions; per-tool files are symlinks (see `workflow/symlink-model.md`) |
| [Other project-specific location] | [Path] | [What lives there] |

> Agent layer taxonomy (Template → Instance → Execution) is defined once in `.specify/shared/definitions/agent-definitions.md` — consult it before creating/refining/running agents.
>
> Self-Improvement terminology is defined once in `.specify/shared/definitions/self-improvement-definitions.md`; policy, reusable structure, and execution order live respectively under `guidelines/`, `patterns/`, and `workflow/`.
