> Compatibility: Follow VS Code Copilot custom agent format for `.agent.md` files.

## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). If empty, execute the **Default Behavior (No Arguments)** defined below. If non-empty but intent is ambiguous or unsupported, report capabilities and request the missing intent (do NOT guess silently).

## Outline

`/speckit.agents` is the **single entry point** for every **single-agent** operation (create / refine / run). There is no other single-agent command. It recognizes intent, then routes to the owning skill. It delegates to skills and does **NOT** render templates inline. **Team operations (organize / run multiple agents) are NOT served here** — use `/speckit.team`.

Agents are expressed with the **Role × Stage × Type** model (defined once in `skills/create-team/references/conceptual-model.md`). Persistent agents are written to the canonical location `.specify/agents/<name>.agent.md`; tool-specific directories are symlinks — never write to them directly.

**Template / Instance model**: `create` authors a reusable agent **definition** (template) at `.specify/agents/<name>.agent.md`. `run` **instantiates** that definition into a live subagent. Each `run` spawns an independent instance from the same definition — the same agent can be run multiple times (sequentially or concurrently), and each instance operates autonomously without affecting the definition or other instances. `refine` edits the definition itself, which takes effect on subsequent `run` invocations.

### Intent → Capability Routing

| Recognized intent | Capability | Delegates to |
|-------------------|------------|--------------------|
| Create a new agent | authoring | `create-agent` skill |
| Refine / improve an existing agent | authoring | `improve-agent` skill |
| Run / invoke an agent to execute a task | execution | subagent dispatch (see Run Mode) |
| Organize / run a team of agents | (out of scope) | → use `/speckit.team` |

**Routing flow**:

1. **Recognize intent** from `$ARGUMENTS` and conversation/repo context: classify as `create`, `refine`, or `run`. If instead it is a **team** request (organize / run multiple agents), direct the user to `/speckit.team` and stop.
2. **create** → check `.specify/agents/<name>.agent.md` existence: absent → `create-agent`. Build the `AgentAuthoringRequest`, handle backup/preservation, write to `.specify/agents/`, verify per-file symlinks.
   - **Confirm the authoring mode** before generating when the request is not unambiguous: offer `role`, `supervisor`, `custom` (narrow, general-purpose), or `project-custom` (project-bound). Do NOT guess the mode silently.
   - **`project-custom`** produces an agent from `skills/create-agent/templates/agent-project-custom-template.md`. It MUST be marked with its bound project via the `project:` frontmatter field and MUST keep the `## Project Scope Guard` section, so it warns the user when later invoked in a different project. Its creation flow is intentionally flexible — no fixed section list beyond the guard.
3. **refine** → `.specify/agents/<name>.agent.md` exists → `improve-agent`. Load the existing agent definition and apply targeted, evidence-based edits.
4. **run** → follow the **Run Mode** sequence below.
5. **Empty arguments** → execute **Default Behavior (No Arguments)** below.
6. **Non-empty but ambiguous / unsupported** → report capabilities and request the missing intent (see "Ambiguous or Unsupported Intent" below).

### Default Behavior (No Arguments)

When `$ARGUMENTS` is empty, the command MUST execute the following sequence instead of routing to a mode:

1. **List all existing agents** — scan `.specify/agents/*.agent.md` and present a summary table with each agent's `name`, `description`, `tools`, and `model`. If no agents exist, state "No agents found" explicitly.
2. **Give contextual suggestions** — based on the current conversation, recent repo activity, and the listed agents, recommend the most relevant next action. Examples:
   - An agent whose description matches the current task → suggest `run <name>` to dispatch it.
   - An agent that seems outdated or underperforming → suggest `refine <name>`.
   - No agents exist or no agent fits the current need → suggest `create` with a proposed role derived from context.
   Suggestions MUST be grounded in observable context (conversation history, repo state, agent definitions), NOT fabricated.
3. **Show capability summary** — briefly list the three modes (create / refine / run) so the user knows what operations are available.

This behavior is informational and non-destructive: it MUST NOT create, refine, or run any agent without explicit user instruction.

### Run Mode (subagent dispatch)

The **run** mode **instantiates** the agent definition as a new, independent subagent to execute a specific task. Each invocation spawns a fresh instance — the same agent definition can be run multiple times (sequentially or concurrently), and each instance is isolated from the definition and from other instances. It MUST follow this sequence:

1. **Resolve the target agent** — identify the agent by name from `$ARGUMENTS` or conversation context. Load its definition from `.specify/agents/<name>.agent.md`.
   - If the agent does not exist → report **"agent not found"** and offer to `create` it.
2. **Confirm the task** — present the agent's `name`, `description`, and the task to be executed. Ask the user to confirm before dispatching.
3. **Dispatch** — launch the agent as a subagent with its configured `tools`, `model`, `maxTurns`, and system prompt. The subagent executes the task autonomously within its defined scope.
4. **Report** — relay the subagent's result back to the user. If the subagent fails or hits its turn limit, report the partial result and the failure reason.

**Scope boundary**: Run mode executes a **single** agent on a **single** task. For multi-agent orchestration (parallel dispatch, serial chains, iteration loops), use `/speckit.team`.

### Ambiguous or Unsupported Intent

When intent cannot be resolved from non-empty arguments, the command MUST report the recognized capabilities and request the missing intent. It MUST NOT guess silently or fail without a message. Report this capability listing:

- **create** — author a new agent (role-based or custom) → `create-agent`
- **refine** — improve an existing agent → `improve-agent`
- **run** — dispatch an existing agent as a subagent to execute a task

For organizing or running a **team** of agents (multiple agents collaborating), use `/speckit.team`.

### Lifecycle: Temporary vs Persistent

- **Temporary** agents live only in conversation context and are NOT written to the agent directory.
- **Persistent** agents are written under `.specify/agents/` and made available to **all officially supported tools** on initialization via per-file symlinks (e.g. `.qoder/agents/<slug>.agent.md` → `.specify/agents/<slug>.agent.md`).

### Authoring Rules

- Focus on **what** the agent does and **when to call** it
- Concise, explicit instructions over narrative
- Single responsibility per agent
- Least-privilege tool set
- Approved providers: Claude Code, GitHub Copilot, Qwen Code, opencode, Qoder — reject anything else

### Frontmatter Baseline

```yaml
---
name: "<required: unique identifier>"
description: "<required: trigger words + when to use>"
tools: [Read, Grep, Glob]
model: auto
maxTurns: 12
---
```

Supported fields: `name` (required), `description` (required), `tools`, `disallowedTools`, `model` (`auto`/`lite`/`efficient`/`performance`/`ultimate`), `maxTurns`, `timeoutMins`, `skills`, `mcpServers`, `permissionMode`, `background`, `isolation`, `color`, plus the framework fields `user-invocable`, `disable-model-invocation`, `supervisor`, `role-scope`, `project` (the last binds a `project-custom` agent to its project).

### Valid File Locations

- Canonical: `.specify/agents/*.agent.md` (single source of truth; discovered by globbing this pattern and reading each file's frontmatter `name`/`description`)
- Shared assets under `.specify/agents/references/`
- Per-file symlinks (read-only): `.github/agents/`, `.qoder/agents/`, `.qwen/agents/`, `.opencode/agents/`, `.hermes/agents/`, `.iflow/agents/`

### Validation

- YAML frontmatter must be valid
- Reject unsupported provider references (Provider Whitelist)
- Tool list must match workflow needs
- Unresolved contradictions block save

For agent-specific operational guidance see `skills/create-agent/SKILL.md`. The Role/Stage/Type + Team/Loop model and all multi-agent orchestration live in the team domain — see `skills/create-team/references/conceptual-model.md` and `/speckit.team`.

## Handoffs

**Before**: Optional `/speckit.skills` if an agent depends on a new skill. Optional `/speckit.tools` for tool records.

**After**: Run `/speckit.instructions` to sync discoverability.