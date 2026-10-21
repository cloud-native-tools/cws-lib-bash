# Agent Definitions Reference

Canonical taxonomy of the **Agent** concept in Spec Kit. The word "agent" is used for three materially different things — a capability description, a responsibility-bound definition, and a running execution — and conflating them causes real editing and dispatch errors. This file names the three layers, fixes their boundaries, and maps them onto the framework's existing vocabulary. It is the single source of truth for the Agent concept; other documents (`/speckit.agents`, `create-agent`, `create-team`, `subagent-definitions.md`, `docs/reference/agents/design.md`) link here rather than re-defining it.

## The Three Layers

| Layer | Form | Question answered | Canonical homes | Produced / owned by |
|-------|------|-------------------|-----------------|---------------------|
| **1. Agent Template** | Markdown **capability description** — behavior framework, enablement surface (`capability-tools:`, `skills:`, `model-tier:`, `run-turn-budget:` — neutral vocabulary, rendered per tool at init), professional identity, domain workflow. Role-generic; team- and task-agnostic; may carry unfilled `{{PLACEHOLDERS}}` | *"What can this kind of agent do?"* | **`.specify/agents/templates/`** — the shipped role set, predefined in the spec-kit source `agents/` directory and installed here by `specify init`; abstract capacity classes in `.specify/skills/internal/create-agent/templates/agent-capacity-*-template.md`; stage/orchestration frames in `.specify/skills/internal/create-team/templates/agents/` | framework distribution; authored/refined via `create-agent` (capacity) and `create-team` (stage frames) |
| **2. Agent Instance** | Markdown **responsibility description** — references an Agent Template (e.g. via `capacity-scope:` frontmatter) and binds it to a concrete duty: a task domain ("analyze this repo's code"), project context, a team seat with territory and handoffs | *"What is this agent for, here?"* | **`.specify/agents/instances/`** (persistent); roster seats in `.specify/teams/<slug>/team.md`; temporary instances living only in the orchestrator's context | `/speckit.agents create` → `create-agent`; `/speckit.team create` → `create-team`; refined by `improve-agent` / `improve-team` |
| **3. Agent Execution** | A **live run** — an OS process or in-session activity with its own lifecycle (start / progress / exit), session id, and turn budget. Its durable artifacts are dispatch configs/scripts; its runtime artifacts are logs and result manifests | *"How is it running right now?"* | **`.specify/agents/execution/`** — `configs/` (dispatch configs, tracked), `.specify/scripts/` (wrappers, tracked), `logs/` (runtime logs, **gitignored — never committed**); the three execution modes — **native / virtual / external** — are defined in [`subagent-definitions.md`](subagent-definitions.md), including the External Dispatch Visibility Contract | launched by `/speckit.agents run`, team run dispatch, or any orchestrator; configs authored via `create-agent` (`kind: execution-config`) |

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
- **Self-Improvement boundary**: Templates and Instances may be Execution Subjects; an Execution is own-run evidence, never the self-edited target. Persistent agents reference `.specify/shared/workflow/self-improvement-workflow.md` through the contract composed by `create-agent`.

## Driving Subagents via the Three Layers (驱动子代理的公用机制接线)

Orchestration skills that need to **drive subagents** (驱动子代理 — e.g. `sdd-loop-driver`, `sdd-project-setup`) do not carry their own dispatch mechanics; they exercise the three layers through the three single-agent skills:

- **Create** (Template → Instance): delegated to `.specify/skills/internal/create-agent/SKILL.md` — author the capacity template, then instantiate duty-bound instances from it.
- **Dispatch** (Instance → Execution): delegated to `.specify/skills/internal/run-agent/SKILL.md` — resolve the definition, accept the Execution topology declaration (see `subagent-definitions.md` § Execution Topology Declaration), and launch per the mode rules and the External Dispatch Visibility Contract.
- **Improve** (evidence → Template/Instance): delegated to `.specify/skills/internal/improve-agent/SKILL.md` — execution evidence (logs, visibility triplet, anomaly return lines, failure modes) refines the definition layers.

Concrete command shapes for driving an external subagent live in `.specify/shared/workflow/external-dispatch-recipes.md`; what a dispatch must satisfy lives in `subagent-definitions.md`. This section wires the consumers to those owners — it does not restate their rules.

**职责切分线 (responsibility divide)**: **orchestration（编排）** (the SDD six-stage loop, the reconcile sequence, state spines, candidate lists) stays with the driving skill's own body; **create / dispatch / improve** belong to the three承接 skills. Neither side absorbs the other.

**Layer-boundary rules (层界判定，三行)**:

- **Agent Template — 能力面**: answers "what can this kind of agent do" (e.g. work in a project directory, load project context, run `/speckit.*` stage commands). A change is Template-layer iff it alters the capability face.
- **Agent Instance — 职责绑定**: answers "what is this agent for, here" (one duty per instance, bound via `capacity-scope` reference — never a capability restatement). A change is Instance-layer iff it alters the duty binding.
- **Agent Execution — 运行拓扑**: answers "where and how does it run" (local path or ssh target + run user + CLI + project directory). A change is Execution-layer iff it alters the topology declaration.

**Cross-layer change ban (越层禁令)**: 改能力不去改拓扑，改拓扑不去改能力 — a single change's diff must not span the Template/Instance face and the Execution topology face; a change that needs both is two changes, landed separately in their own layers.

## Storage Layout

```
.specify/agents/
├── .specify/templates/     # layer 1 — Agent Templates (shipped role set; installed by `specify init`)
├── instances/     # layer 2 — Agent Instances (project-authored, reference a Template)
└── execution/     # layer 3 — Agent Execution artifacts
    ├── configs/     # dispatch configs (<slug>.yaml) — tracked
    ├── .specify/scripts/     # dispatch wrappers — tracked
    └── logs/        # runtime logs — gitignored, never committed
```

Agent definition files are **self-contained** — there is no shared-assets directory under the agent stores; anything a definition depends on is either inlined or referenced from its owning document (`.specify/shared/`, skill references). Tool directories (`.qoder/agents/`, `.github/agents/`, …) hold **renderer-produced real files** aggregated from `.specify/templates/` + `instances/` (instance wins on filename collision) — never symlinks, never hand-written copies (see § Host Registration Surface below); `execution/` is never rendered. The mirror `sync-mirrors.py` maps source `agents/` → `.specify/agents/templates/` only; `instances/` and `execution/` are project-local.

## Layer Discriminator

Classify by **content form and lifecycle, not by directory**:

- Unfilled placeholders, role-generic wording, no project/task binding → **Template**.
- Filled, responsibility- or project-bound, referenced by runs and rosters → **Instance**.
- Has a session/PID and a turn budget being consumed → **Execution** (durable form: its dispatch config under `execution/configs/`).

**Dogfooding note**: in the spec-kit repository itself, source `agents/` and `.specify/agents/templates/` are byte-identical by design (`sync-mirrors.py`). The shipped role agents are pre-filled for this project, so they double as ready-to-run definitions; their *distribution role* across projects remains Template. Which agents ship is enumerated by the `agents/` directory listing — the count is deliberately not restated here, because a pinned number goes stale the moment an agent is added or retired.

## Mapping to Existing Framework Vocabulary

The taxonomy renames nothing — it gives canonical layer names to distinctions the framework already draws:

| Existing phrase | Where | Taxonomy mapping |
|-----------------|-------|------------------|
| abstract agent Class / 能力模板（抽象类） | `create-agent` SKILL, `docs/reference/agents/design.md` | Agent Template |
| concrete agent definition / 落地定义（具体类） | same | Agent Instance |
| live instance (object) / 运行实例（对象） | same | Agent Execution |
| **capacity** — what the agent *can do* | `.specify/skills/internal/create-team/references/capacity-vs-responsibility.md` | Template-layer concern |
| **responsibility** — what a seat *is accountable for* | same | Instance-layer concern (bound at the team roster) |
| **subagent** | [`subagent-definitions.md`](subagent-definitions.md) | an Agent Execution, viewed from the orchestrator that delegated it |
| temporary / persistent lifecycle | `/speckit.agents` | storage property of the Instance layer |

## Terminology Boundaries

| Term | Meaning | Where defined |
|------|---------|---------------|
| **Agent Template / Instance / Execution** (this document) | The three layers above | here |
| **Subagent** | A delegated Agent Execution and its three modes (native/virtual/external) | `.specify/shared/definitions/subagent-definitions.md` |
| **Team** | Multi-agent structure binding Instances into seats and orchestrating their Executions | `/speckit.team`, `skills/internal/create-team` |
| **`AGENTS.md`** | The project-instructions file for AI tools — unrelated to the agent artifact system | `/speckit.instructions` |
| **AI agent CLI** | A supported coding agent binary (`qodercli`, `claude`, …) that *hosts* executions | `docs/reference/cli/` |
| **Agent tool-call list** | The `capability-tools:` frontmatter key (neutral vocabulary; rendered to each tool's own field name at init) — the LLM's callable surface inside one agent | `.specify/agents/{templates,instances}/<slug>.agent.md` frontmatter |
| **Tool** / Tool record | Pre-verified reusable capability record | `.specify/shared/definitions/tool-definitions.md` |

## Host Registration Surface

The **Host Registration Surface** of a render-mode tool is the directory that tool actually reads agent definitions from — the render pipeline's target surface. One surface per render-mode tool (qoder, claude, copilot, opencode; codex/hermes are annotated-mode and carry no surface); its path comes from the CLI's tool-metadata mapping (`_AGENT_METADATA_MAPPING[tool]["target_dir"]` in `src/specify_cli/__init__.py` — e.g. qoder's project-level `.qoder/agents/`), and its contents are **renderer-produced real files** — never symlinks, never hand-written copies. The render manifest (`.specify/agents/.render-manifest.json`) distinguishes rendered products from user-owned files sharing the directory; user assets are never pruned. Verified 2026-10-08 against official docs (the CLI/IDE shared-path statement lives in `.specify/shared/workflow/symlink-model.md`): Qoder CLI and Qoder IDE read the SAME project-level `.qoder/agents/`, and a filename does not define the agent name — the frontmatter `name` field does.

**Seat Instance** — an Agent Instance produced by the create-team flow's seat-instantiation step (`.specify/skills/internal/create-team/references/create-mode.md` step 4): instantiated from a stage frame via create-agent delegation with ALL frame placeholders resolved, carrying the framework-only `team-scope: <team-slug>` frontmatter key as its team provenance (key semantics owned by the CLI's neutral key set; never rendered to any tool). Seat instances share the Agent Instance layer's store (`.specify/agents/instances/`) and validation; a `team-scope` pointing at a nonexistent team marks the instance **orphaned** — machine-detectable by that key alone.
