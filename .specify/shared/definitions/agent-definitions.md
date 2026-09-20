# Agent Definitions Reference

Canonical taxonomy of the **Agent** concept in Spec Kit. The word "agent" is used for three materially different things — a capability description, a responsibility-bound definition, and a running execution — and conflating them causes real editing and dispatch errors. This file names the three layers, fixes their boundaries, and maps them onto the framework's existing vocabulary. It is the single source of truth for the Agent concept; other documents (`/speckit.agents`, `create-agent`, `create-team`, `subagent-definitions.md`, `docs/reference/agents/design.md`) link here rather than re-defining it.

## The Three Layers

| Layer | Form | Question answered | Canonical homes | Produced / owned by |
|-------|------|-------------------|-----------------|---------------------|
| **1. Agent Template** | Markdown **capability description** — behavior framework, enablement surface (`capability-tools:`, `skills:`, `model-tier:`, `run-turn-budget:` — neutral vocabulary, rendered per tool at init), professional identity, domain workflow. Role-generic; team- and task-agnostic; may carry unfilled `{{PLACEHOLDERS}}` | *"What can this kind of agent do?"* | **`.specify/agents/templates/`** — the shipped role set, predefined in the spec-kit source `agents/` directory and installed here by `specify init`; abstract capacity classes in `skills/create-agent/templates/agent-capacity-*-template.md`; stage/orchestration frames in `skills/create-team/templates/agents/` | framework distribution; authored/refined via `create-agent` (capacity) and `create-team` (stage frames) |
| **2. Agent Instance** | Markdown **responsibility description** — references an Agent Template (e.g. via `capacity-scope:` frontmatter) and binds it to a concrete duty: a task domain ("analyze this repo's code"), project context, a team seat with territory and handoffs | *"What is this agent for, here?"* | **`.specify/agents/instances/`** (persistent); roster seats in `.specify/teams/<slug>/team.md`; temporary instances living only in the orchestrator's context | `/speckit.agents create` → `create-agent`; `/speckit.team create` → `create-team`; refined by `improve-agent` / `improve-team` |
| **3. Agent Execution** | A **live run** — an OS process or in-session activity with its own lifecycle (start / progress / exit), session id, and turn budget. Its durable artifacts are dispatch configs/scripts; its runtime artifacts are logs and result manifests | *"How is it running right now?"* | **`.specify/agents/execution/`** — `configs/` (dispatch configs, tracked), `scripts/` (wrappers, tracked), `logs/` (runtime logs, **gitignored — never committed**); the three execution modes — **native / virtual / external** — are defined in [`subagent-definitions.md`](subagent-definitions.md), including the External Dispatch Visibility Contract | launched by `/speckit.agents run`, team run dispatch, or any orchestrator; configs authored via `create-agent` (`kind: execution-config`) |

**Layer explicitness rule**: agent operations (`/speckit.agents`, `create-agent`, `improve-agent`) MUST state which layer they operate on — `template` / `instance` / `execution` — and MUST NOT infer it silently when ambiguous.

## Transformation Chain

```
Agent Template ──(command/skill)──▶ Agent Instance ──(tool call / MCP / shell)──▶ Agent Execution
capability, .md                     responsibility, .md                           runtime form
```

- **Template → Instance** (authoring time): a command or skill performs the instantiation — `/speckit.agents create` (via `create-agent`) fills a capacity template's placeholders and writes the definition; `/speckit.team create` (via `create-team`) binds instances into roster seats and layers team responsibility on top. An Instance MUST reference the Template it derives from rather than restating capability.
- **Instance → Execution** (runtime): a dispatch mechanism turns the definition into a live run — a harness **tool call** (native subagent), in-session adoption when no mechanism exists (**virtual**), or an **MCP / shell**-launched separate agent process (**external**). Mode selection and the visibility rules live in `subagent-definitions.md`.
- **Cardinality**: one Template serves many Instances (the same `qa-engineer` capacity fills seats in different teams); one Instance serves many Executions (each `run` spawns an independent execution; concurrent runs never affect the definition).
- **Edit routing**: `refine` operations (`improve-agent`, `improve-team`) act on Templates and Instances — never on Executions. A misbehaving Execution is terminated or re-dispatched; the fix lands in the layer below.
- **Self-Improvement boundary**: Templates and Instances may be Execution Subjects; an Execution is own-run evidence, never the self-edited target. Persistent agents reference `shared/workflow/self-improvement-workflow.md` through the contract composed by `create-agent`.

## Storage Layout

```
.specify/agents/
├── templates/     # layer 1 — Agent Templates (shipped role set; installed by `specify init`)
├── instances/     # layer 2 — Agent Instances (project-authored, reference a Template)
└── execution/     # layer 3 — Agent Execution artifacts
    ├── configs/     # dispatch configs (<slug>.yaml) — tracked
    ├── scripts/     # dispatch wrappers — tracked
    └── logs/        # runtime logs — gitignored, never committed
```

Agent definition files are **self-contained** — there is no shared-assets directory under the agent stores; anything a definition depends on is either inlined or referenced from its owning document (`shared/`, skill references). Tool directories (`.qoder/agents/`, `.github/agents/`, …) hold per-file symlinks aggregated from `templates/` + `instances/` (instance wins on filename collision); `execution/` is never linked. The mirror `sync-mirrors.py` maps source `agents/` → `.specify/agents/templates/` only; `instances/` and `execution/` are project-local.

## Layer Discriminator

Classify by **content form and lifecycle, not by directory**:

- Unfilled placeholders, role-generic wording, no project/task binding → **Template**.
- Filled, responsibility- or project-bound, referenced by runs and rosters → **Instance**.
- Has a session/PID and a turn budget being consumed → **Execution** (durable form: its dispatch config under `execution/configs/`).

**Dogfooding note**: in the spec-kit repository itself, source `agents/` and `.specify/agents/templates/` are byte-identical by design (`sync-mirrors.py`). The seven shipped role agents are pre-filled for this project, so they double as ready-to-run definitions; their *distribution role* across projects remains Template.

## Mapping to Existing Framework Vocabulary

The taxonomy renames nothing — it gives canonical layer names to distinctions the framework already draws:

| Existing phrase | Where | Taxonomy mapping |
|-----------------|-------|------------------|
| abstract agent Class / 能力模板（抽象类） | `create-agent` SKILL, `docs/reference/agents/design.md` | Agent Template |
| concrete agent definition / 落地定义（具体类） | same | Agent Instance |
| live instance (object) / 运行实例（对象） | same | Agent Execution |
| **capacity** — what the agent *can do* | `skills/create-team/references/capacity-vs-responsibility.md` | Template-layer concern |
| **responsibility** — what a seat *is accountable for* | same | Instance-layer concern (bound at the team roster) |
| **subagent** | [`subagent-definitions.md`](subagent-definitions.md) | an Agent Execution, viewed from the orchestrator that delegated it |
| temporary / persistent lifecycle | `/speckit.agents` | storage property of the Instance layer |

## Terminology Boundaries

| Term | Meaning | Where defined |
|------|---------|---------------|
| **Agent Template / Instance / Execution** (this document) | The three layers above | here |
| **Subagent** | A delegated Agent Execution and its three modes (native/virtual/external) | `shared/definitions/subagent-definitions.md` |
| **Team** | Multi-agent structure binding Instances into seats and orchestrating their Executions | `/speckit.team`, `skills/create-team` |
| **`AGENTS.md`** | The project-instructions file for AI tools — unrelated to the agent artifact system | `/speckit.instructions` |
| **AI agent CLI** | A supported coding agent binary (`qodercli`, `claude`, …) that *hosts* executions | `docs/reference/cli/` |
| **Agent tool-call list** | The `capability-tools:` frontmatter key (neutral vocabulary; rendered to each tool's own field name at init) — the LLM's callable surface inside one agent | `.specify/agents/{templates,instances}/<slug>.agent.md` frontmatter |
| **Tool** / Tool record | Pre-verified reusable capability record | `shared/definitions/tool-definitions.md` |
