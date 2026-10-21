---
description: 单代理操作统一入口：按意图路由创建、优化或运行代理
---
<!-- AUTO-GENERATED from templates/commands/agents.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
> Compatibility: Follow VS Code Copilot custom agent format for `.agent.md` files.

## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). If empty, execute the **Default Behavior (No Arguments)** owned by the run-agent skill (below). If non-empty but intent is ambiguous or unsupported, report capabilities and request the missing intent (do NOT guess silently).

## Delegation

`/speckit.agents` is the single entry point for every **single-agent** operation. It recognizes intent from `$ARGUMENTS` and conversation/repo context, routes to the owning skill, and delegates — it does not render any operation inline. Team operations (organize / run multiple agents) are out of scope here → `/speckit.team`.

Load skills by their runtime path (internal skills are path-referenced by the workflow):

| Intent | Skill to load | Inputs | Outputs |
|---|---|---|---|
| **run** an agent, or empty arguments | `.specify/skills/internal/run-agent/SKILL.md` | `run <agent-name> [task]`, or empty (no-argument listing behavior); agent resolved by `name` — `.specify/agents/instances/<name>.agent.md` falling back to `.specify/agents/templates/<name>.agent.md` (instance wins on collision), plus `.specify/agents/execution/configs/<name>.yaml` when present | A live, independent Agent Execution dispatched as a subagent (execution mode per `.specify/shared/definitions/subagent-definitions.md`) with the fast-fail injection clause verified at dispatch, result relayed back to the user; or the no-argument listing + contextual suggestions + capability summary (non-destructive) |
| **create** a new agent | `.specify/skills/internal/create-agent/SKILL.md` | The `AgentAuthoringRequest` (layer/kind: `role` / `supervisor` / `custom` / `project-custom`; ask ONE elicitation question if the mode is genuinely ambiguous; layer resolved if unambiguous); existence check across `.specify/agents/{templates,instances}/<name>.agent.md` — absent → create; an existing definition is never silently overwritten (reuse-first / refine instead, per the skill) | The authored definition written to the layer's canonical store (`.specify/agents/{templates,instances}/`); trigger teaching — reach the host registration surface via `specify render-agents --ai <tool>` (init is the first-install entry, not the re-render path) |
| **refine** an existing agent | `.specify/skills/internal/improve-agent/SKILL.md` | The target artifact (`.specify/agents/templates/<name>.agent.md`, `.specify/agents/instances/<name>.agent.md`, or `.specify/agents/execution/configs/<name>.yaml` — layer mandatory and explicit) + evidence of what to improve | Targeted, evidence-based edits applied to the definition, taking effect on subsequent `run` invocations |

Ambiguous or unsupported intent → report the three capabilities (create / refine / run) and request the missing intent; for teams direct to `/speckit.team`.

The authoring baseline (frontmatter vocabulary, valid file locations, validation rules, Role × Stage × Type conceptual model) is owned by these skills and `.specify/shared/definitions/agent-definitions.md` — it is not restated in this template.

## Handoffs

**Before**: Optional `/speckit.skills` if an agent depends on a new skill. Optional `/speckit.tools` for tool records.

**After**: Run `/speckit.instructions` to sync discoverability.