---
description: 单代理操作统一入口：按意图路由创建、优化或运行代理
---
<!-- AUTO-GENERATED from templates/commands/agents.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
> Compatibility: Follow VS Code Copilot custom agent format for `.agent.md` files.

## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). If empty, execute the **Default Behavior (No Arguments)** defined below. If non-empty but intent is ambiguous or unsupported, report capabilities and request the missing intent (do NOT guess silently).

## Outline

`/speckit.agents` is the **single entry point** for every **single-agent** operation (create / refine / run). There is no other single-agent command. It recognizes intent, then routes to the owning skill. It delegates to skills and does **NOT** render templates inline. **Team operations (organize / run multiple agents) are NOT served here** — use `/speckit.team`.

Agents are expressed with the **Role × Stage × Type** model (defined once in `skills/create-team/references/conceptual-model.md`). Persistent agents are written to the canonical layered stores `.specify/agents/templates/<name>.agent.md` (Agent Templates — installed by `specify init`) and `.specify/agents/instances/<name>.agent.md` (Agent Instances); runtime artifacts live under `.specify/agents/execution/` (dispatch `configs/`+`.specify/scripts/` tracked, `logs/` gitignored). Tool-specific directories are symlinks — never write to them directly.

**Layer explicitness**: every operation targets exactly one layer — `template` / `instance` / `execution` (taxonomy: `.specify/shared/definitions/agent-definitions.md`). If the user's request does not make the layer unambiguous, ask before acting; never guess silently.

**Template / Instance / Execution model** (canonical taxonomy: `.specify/shared/definitions/agent-definitions.md`): `create` instantiates an **Agent Template** (capacity class) into an **Agent Instance** — a reusable, responsibility-bound definition at `.specify/agents/instances/<name>.agent.md` (role Templates themselves are authored/installed at `.specify/agents/templates/`). `run` turns a definition into a live **Agent Execution** (subagent). Each `run` spawns an independent Execution from the same definition — the same agent can be run multiple times (sequentially or concurrently), and each Execution operates autonomously without affecting the definition or other Executions. `refine` edits the definition itself, which takes effect on subsequent `run` invocations.

### Intent → Capability Routing

| Recognized intent | Capability | Delegates to |
|-------------------|------------|--------------------|
| Create a new agent | authoring | `create-agent` skill |
| Refine / improve an existing agent | authoring | `improve-agent` skill |
| Run / invoke an agent to execute a task | execution | subagent dispatch (see Run Mode) |
| Organize / run a team of agents | (out of scope) | → use `/speckit.team` |

**Routing flow**:

1. **Recognize intent** from `$ARGUMENTS` and conversation/repo context: classify as `create`, `refine`, or `run`. If instead it is a **team** request (organize / run multiple agents), direct the user to `/speckit.team` and stop.
2. **create** → resolve the target **layer** (template / instance / execution; ask if ambiguous), check `.specify/agents/{templates,instances}/<name>.agent.md` existence: absent → `create-agent`. Build the `AgentAuthoringRequest` (carrying the layer/kind), handle backup/preservation, write to the layer's store, re-render the tool agent directories (or advise `specify init`).
   - **Resolve the authoring mode**: infer it from the request; when genuinely ambiguous, ask ONE elicitation question offering `role`, `supervisor`, `custom` (narrow, general-purpose), or `project-custom` (project-bound) — do NOT guess silently, but once resolved proceed directly without a blocking confirmation.
   - **`project-custom`** produces an agent from `skills/create-agent/templates/agent-project-custom-template.md`. It MUST be marked with its bound project via the `project:` frontmatter field and MUST keep the `## Project Scope Guard` section, so it warns the user when later invoked in a different project. Its creation flow is intentionally flexible — no fixed section list beyond the guard.
3. **refine** → resolve the target **layer**, then the artifact (`.specify/agents/templates/<name>.agent.md`, `.specify/agents/instances/<name>.agent.md`, or `.specify/agents/execution/configs/<name>.yaml`) exists → `improve-agent`. Load the existing definition and apply targeted, evidence-based edits.
4. **run** → follow the **Run Mode** sequence below.
5. **Empty arguments** → execute **Default Behavior (No Arguments)** below.
6. **Non-empty but ambiguous / unsupported** → report capabilities and request the missing intent (see "Ambiguous or Unsupported Intent" below).

### Default Behavior (No Arguments)

When `$ARGUMENTS` is empty, the command MUST execute the following sequence instead of routing to a mode:

1. **List all existing agents** — scan `.specify/agents/{templates,instances}/*.agent.md` and present a summary table with each agent's **layer**, `name`, `description`, `tools`, and `model`. If no agents exist, state "No agents found" explicitly.
2. **Give contextual suggestions** — based on the current conversation, recent repo activity, and the listed agents, recommend the most relevant next action. Examples:
   - An agent whose description matches the current task → suggest `run <name>` to dispatch it.
   - An agent that seems outdated or underperforming → suggest `refine <name>`.
   - No agents exist or no agent fits the current need → suggest `create` with a proposed role derived from context.
   Suggestions MUST be grounded in observable context (conversation history, repo state, agent definitions), NOT fabricated.
3. **Show capability summary** — briefly list the three modes (create / refine / run) so the user knows what operations are available.

This behavior is informational and non-destructive: it MUST NOT create, refine, or run any agent without explicit user instruction.

### Run Mode (subagent dispatch)

The **run** mode turns the **Agent Instance** definition into a new, independent **Agent Execution** (subagent) for a specific task. Each invocation spawns a fresh Execution — the same Instance can be run multiple times (sequentially or concurrently), and each Execution is isolated from the definition and from other Executions. It MUST follow this sequence:

1. **Resolve the target agent** — identify the agent by name from `$ARGUMENTS` or conversation context. Load its definition from `.specify/agents/instances/<name>.agent.md`, falling back to `.specify/agents/templates/<name>.agent.md` (instance wins on collision); apply `.specify/agents/execution/configs/<name>.yaml` when present.
   - If the agent does not exist → report **"agent not found"** and offer to `create` it.
2. **Present & dispatch** — present the agent's `name`, `description`, and the task to be executed, then dispatch directly (presentation is disclosure, not a blocking gate; 用户可随时叫停).
3. **Dispatch** — launch the agent as a subagent with its configured `capability-tools`, `model-tier`, and `run-turn-budget`, and system prompt. Choose the execution mode per `.specify/shared/definitions/subagent-definitions.md` (**native** when the runtime supports subagents, **virtual** in-session when it does not, **external** CLI process for long-running/parallel work or per-dispatch model overrides); external CLI dispatch MUST follow that document's Visibility Contract (stream-json + compact filter + `.live.log`/`.jsonl`/`.status` triplet) — never redirect print-mode output into a silent log. The subagent executes the task autonomously within its defined scope.
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
- **Persistent** agents are written under `.specify/agents/templates/` (Meta Agent presets) or `.specify/agents/instances/` (Instances) and made available to **all officially supported tools** on initialization via per-tool rendering into real files (e.g. `.qoder/agents/<slug>.agent.md` in Qoder format; instance wins on filename collision).

### Authoring Rules

- Focus on **what** the agent does and **when to call** it
- Concise, explicit instructions over narrative
- Single responsibility per agent
- Least-privilege tool set
- Approved providers: Claude Code, opencode, Qoder, Codex CLI, Hermes Agent, GitHub Copilot — reject anything else

### Frontmatter Baseline

```yaml
---
name: "<required: unique identifier>"
description: "<required: trigger words + when to use>"
capability-tools: [Read, Grep, Glob]
model-tier: auto
run-turn-budget: 12
display-color: purple
---
```

Supported fields (neutral vocabulary, per `.specify/shared/definitions/agent-definitions.md` — the shipped role set is the reference implementation): `name` (required), `description` (required), `capability-tools`, `disallowed-tools`, `model-tier` (`auto`/`lite`/`efficient`/`performance`/`ultimate`), `run-turn-budget`, `timeout-mins`, `skills`, `mcp-servers`, `permission-mode`, `background`, `isolation`, `display-color`, plus the framework fields `user-invocable`, `disable-model-invocation`, `supervisor`, `role-scope`, `project` (the last binds a `project-custom` agent to its project). Host-CLI-specific renderers map these neutral fields onto each tool's native keys at init time.

### Valid File Locations

- Canonical: `.specify/agents/templates/*.agent.md` + `.specify/agents/instances/*.agent.md` (single source of truth per layer; discovered by globbing these patterns and reading each file's frontmatter `name`/`description`)
- Execution artifacts: `.specify/agents/execution/{configs,scripts}/` tracked; `execution/logs/` gitignored, never committed
- Rendered outputs (read-only, rebuilt from the neutral source): `.qoder/agents/`, `.claude/agents/`, `.github/agents/`, `.opencode/agents/`

Agent definitions are **self-contained**: everything an agent needs lives in its own `.agent.md` (no shared-assets directory under the agent stores).

### Validation

- YAML frontmatter must be valid
- Reject unsupported provider references (Provider Whitelist)
- Tool list must match workflow needs
- Unresolved contradictions block save

For agent-specific operational guidance see `skills/create-agent/SKILL.md`. The Role/Stage/Type + Team/Loop model and all multi-agent orchestration live in the team domain — see `skills/create-team/references/conceptual-model.md` and `/speckit.team`.

## Handoffs

**Before**: Optional `/speckit.skills` if an agent depends on a new skill. Optional `/speckit.tools` for tool records.

**After**: Run `/speckit.instructions` to sync discoverability.