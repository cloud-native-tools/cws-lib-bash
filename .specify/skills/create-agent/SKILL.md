---
name: create-agent
description: General-purpose authoring skill for single Spec Kit agents — creates role, supervisor, custom, or project-specific (project-custom) agents. Use this when the user mentions ["create an agent", "new agent", "add agent role", "agent template", "supervisor agent", "project-specific agent", "custom project agent", "创建agent", "新建agent", "添加角色", "项目自定义agent", "项目专属agent"]
skill_id: "<SKILL:.specify/skills/create-agent/SKILL.md>"
---

# create-agent

## Goal

Author a **single agent artifact** for the Spec Kit agent system — a **capacity** template, a capacity-scoped **supervisor**, a **custom** `.agent.md`, or a **project-custom** agent. This skill is the single authoring engine invoked by `/speckit.agents` for single-agent work; the command gathers project context and delegates here rather than rendering templates inline. Multi-agent teams (organizing/running several agents) are out of scope — see `/speckit.team` and the `create-team` skill.

> **Class → Instance**: a template here is an **abstract agent Class** — a `agent-capacity-<X>-template.md` with unfilled `{{PLACEHOLDERS}}`. Authoring **instantiates** that Class: `create-agent` fills the placeholders and writes a **concrete agent definition** into its layer's store under `.specify/agents/` (role Templates → `templates/`, responsibility-bound Instances → `instances/`; see § Layer Targeting). At runtime, `/speckit.agents run` spawns a **live instance (object)** from that definition — many instances from one definition, each independent. This skill operates at the Class/definition layer, never on running instances. In the canonical Agent taxonomy (`.specify/shared/definitions/agent-definitions.md`) these three layers are **Agent Template → Agent Instance → Agent Execution**; the Execution layer's dispatch modes are governed by `.specify/shared/definitions/subagent-definitions.md`.

> **Conceptual Model**: the multi-agent Role × Stage × Type + Team/Loop model is defined once in the team domain — see `skills/create-team/references/conceptual-model.md`. This skill authors the single **capacity** Classes that fill a team's Role seats.

> **Capacity, not responsibility**: templates here define an agent's **capacity** — what it *can do*, team-agnostic (tools, skills, model budget, professional identity, domain method). Team-scoped **responsibility** (the Role seat, stage assignment, write territory, handoff paths, reporting duty) is defined in the team domain, never here. The authoritative boundary and edit routing: `skills/create-team/references/capacity-vs-responsibility.md`.

Canonical template home: `skills/create-agent/templates/` (installed mirror: `.specify/skills/create-agent/templates/`).

## Layer Targeting (mandatory, explicit)

Every operation of this skill MUST declare which **agent layer** it operates on (taxonomy: `.specify/shared/definitions/agent-definitions.md`). Never infer the layer silently — if the request does not state it and the `kind` does not imply it unambiguously, ask the user before writing anything.

| Layer | Project directory | What lives there | Operated by |
|-------|-------------------|------------------|-------------|
| `template` | `.specify/agents/templates/` | Agent Templates — the shipped role set installed by `specify init` from the spec-kit source `agents/` directory, plus project-authored role templates | kinds `capacity`, `supervisor` |
| `instance` | `.specify/agents/instances/` | Agent Instances — responsibility-bound agents referencing a Template | kinds `custom`, `project-custom` |
| `execution` | `.specify/agents/execution/` | Agent Execution — dispatch `configs/`, wrapper `scripts/`, runtime `logs/` (logs gitignored, never committed) | kind `execution-config` |

The `kind` → layer mapping above is fixed; state the resolved layer in the pre-generation disclosure and in the final report.

## Capability Matrix

Select the capability from the request `kind` (or infer from user intent):

| kind | Layer | Produces | Source templates | Primary section |
|------|-------|----------|------------------|-----------------|
| `capacity` | template | One capacity agent Class (six mandatory sections) | `skills/create-agent/templates/agent-capacity-*-template.md` | Workflow steps 1–5 below |
| `supervisor` | template | A capacity agent that orchestrates a role-scoped EEI quality loop; persistent output also receives the standard Self-Improvement Contract | capacity template + `skills/create-agent/templates/agent-supervision-delegation.md` inlined | § Supervisor Capability |
| `custom` | instance | A single narrow, general-purpose custom `.agent.md` (not bound to a project) | free-form per intent | § Mode Confirmation |
| `project-custom` | instance | A project-bound custom agent that marks its project and guards against being run elsewhere | `skills/create-agent/templates/agent-project-custom-template.md` | § Project-Custom Capability |
| `execution-config` | execution | A dispatch config (and optional wrapper script) for running an agent | § Execution Config Capability | § Execution Config Capability |

### Mode Confirmation

When a create request does not clearly map to a single `kind`, do **not** guess. Ask the user which authoring mode they want (ONE elicitation question — never guess silently), offering the choices explicitly: `capacity` / `supervisor` (template layer), `custom` (narrow, general-purpose) / `project-custom` (project-bound) (instance layer), or `execution-config` (execution layer). This is the one decision point shared by all authoring capabilities; once resolved, proceed directly (no further blocking stop). It MUST surface the resolved **layer** alongside the kind.

All capabilities share the same validate + report tail (Workflow steps 4–5) and the Agent-Specific Configuration handling below.

## AgentAuthoringRequest Intake

When invoked by `/speckit.agents`, accept the `AgentAuthoringRequest` (defined in the framework repo, spec 022) and consume every field: `kind`, `role_slug`, `task`, `scoring_dimensions[]`, `threshold`, `max_iterations`, `environment_paths[]`, `workspace_paths[]`, `project_context`. Missing optional fields fall back to role defaults (threshold from role, `max_iterations`=20). Return an `AuthoringResult` (`artifact_paths`, `kind`, `status`).

## Workflow

### 1. Determine the role definition

**Case A — User provided explicit role description**

Parse the role name, responsibilities, and workflow constraints from the user input:

- **Role name**: A concise display name (e.g., "Security Auditor", "DevOps Engineer")
- **Role slug**: Derive kebab-case slug from role name (e.g., `security-auditor`, `devops-engineer`)
- **Responsibilities**: Core duties of this role in a software development workflow
- **Upstream/Downstream**: Who provides inputs and who consumes outputs

**Case B — User provided no input (empty arguments)**

Analyze the conversation history and project context to infer a useful role:

1. Review conversation for recurring task patterns or specialized workflows
2. Identify the role's position in the development workflow
3. Ask one targeted clarification question if the role is ambiguous

### 2. Validate against existing templates

- Check `skills/create-agent/templates/agent-capacity-*-template.md` for existing roles
- If a similar role exists, suggest updating it via `improve-agent` instead
- Ensure the new role does not overlap significantly with the seven preset roles

### 3. Create the template file

Write `skills/create-agent/templates/agent-capacity-<slug>-template.md` following the skeleton in [`./references/template-authoring.md`](./references/template-authoring.md) — Qoder-compatible frontmatter plus six mandatory body sections (Identity & Responsibilities, Project Context, Workflow, Upstream, Downstream, Output Format). For every persistent Template/Instance, append `${SKILL_HOME}/templates/agent-self-improvement.md` as the cross-cutting `## Self-Improvement Contract`; temporary executions do not receive it.

### 4. Validate the template

- Verify YAML frontmatter has required fields (name, description, user-invocable)
- Verify Qoder-compatible fields are present (`model`, `tools`, `maxTurns`); pick role-appropriate `tools`/`maxTurns`/`color`
- Verify all six mandatory sections are present
- For a persistent Template/Instance, verify the `## Self-Improvement Contract` from `${SKILL_HOME}/templates/agent-self-improvement.md` is present exactly once
- Verify only approved `{{PLACEHOLDER}}` variables are used
- Verify upstream/downstream references are consistent with existing role chain
- Verify token-efficiency compliance per `.specify/shared/guidelines/token-efficiency.md`: deterministic steps delegated to programs; no whole-file injection of machine-managed data files

### 5. Report

- Report the created template file path and the resolved **layer**
- Suggest running `/speckit.agents` to install the role Template to `.specify/agents/templates/<slug>.agent.md`
- Propose how this role fits into the existing workflow chain

## Constraints

- Templates MUST follow the established role-based structure (six mandatory sections)
- Every persistent Template/Instance MUST include `## Self-Improvement Contract` exactly once; temporary Executions/configs MUST NOT claim a separate subject identity
- Templates MUST use only approved `{{PLACEHOLDER}}` variables
- Frontmatter uses Qoder-compatible fields — `model` (default `auto`, Qoder smart routing), `tools`/`disallowedTools`, `maxTurns`/`timeoutMins`, `skills`/`mcpServers`, `permissionMode`, `background`, `isolation`, `color`. Only `name` and `description` are strictly required; set `model`/`tools`/`maxTurns` for every role and leave the rest unset unless needed.
- Role instructions MUST be written in first-person professional identity
- Layer discipline: template-layer output goes to `.specify/agents/templates/`, instance-layer output to `.specify/agents/instances/`, execution-layer output to `.specify/agents/execution/{configs,scripts}/`; abstract capacity Classes stay in `skills/create-agent/templates/`. Never write across layers, and never write logs anywhere but `.specify/agents/execution/logs/` (gitignored)
- An instance-layer agent derived from a role MUST reference its Template (`capacity-scope:` frontmatter) instead of restating capability
- `project-custom` agents MUST carry the `project:` frontmatter marker and the mandatory `## Project Scope Guard` section (see § Project-Custom Capability)
- The full framework frontmatter field set is: `user-invocable`, `disable-model-invocation`, `supervisor`, `capacity-scope`, `project` (the last used only by `project-custom` agents)

## Agent Lifecycle (temporary vs persistent)

Every agent this skill can produce has one of two lifecycles. Choose the lifecycle before generating files.

| Lifecycle | Where it lives | When to use | Tool config |
|-----------|----------------|-------------|-------------|
| **temporary** | Context-only — never written to disk | A worker/stage agent spawned for a single run; discarded when the run ends | None; it exists only in the invoking context (FR-011) |
| **persistent** | `.specify/agents/templates/<slug>.agent.md` (template layer) or `.specify/agents/instances/<slug>.agent.md` (instance layer) — the canonical stores | A reusable role or supervisor the project keeps across sessions | Per-file symlinked into every officially supported tool's agent config directory on initialization (FR-010/012) |

**Persistent generation rules**:

- Write the generated agent to its layer's canonical store: role Templates to `.specify/agents/templates/<slug>.agent.md`, responsibility-bound Instances to `.specify/agents/instances/<slug>.agent.md` (single source of truth per layer).
- On initialization the CLI (re)creates a **per-file** symlink for each `*.agent.md` under `.specify/agents/{templates,instances}/` inside every officially supported tool's agent config dir — e.g. `.qoder/agents/<slug>.agent.md → ../../.specify/agents/templates/<slug>.agent.md`, plus `.github/agents`, `.opencode/agents`, `.hermes/agents`. On a filename collision the instance wins. Each tool `agents/` is a real directory of per-file links (so tools may add their own overrides beside the framework links); never write tool-specific copies of framework agents.
- Agents are discovered by globbing `.specify/agents/{templates,instances}/*.agent.md` and reading each file's frontmatter `name`/`description`; no separate registry file is maintained. The `execution/` directory holds no agent definitions and is never globbed for discovery.

**Temporary generation rules**:

- Do NOT write the agent under `.specify/agents/` and do NOT create tool config links. A team orchestrator instantiates it from a role template into its own context for the duration of the run only (FR-011).

## Supervisor Capability

Use this capability (`kind: supervisor`) to author a **role-scoped supervisor** — a role agent that, for quality-gated deliverables, orchestrates its own EEI loop. Per the amendment decisions: supervision is **active by default** (OQ-1) and the delegation section is **composed at generation, not copied into role templates** (OQ-2).

### How it works

1. Load the capacity template `skills/create-agent/templates/agent-capacity-<capacity_slug>-template.md` (it carries `supervisor: true` and `capacity-scope: <capacity_slug>` in frontmatter).
2. **Inline the single-source snippet** `skills/create-agent/templates/agent-supervision-delegation.md` into the generated agent body, resolving its placeholders:
   - `{{CAPACITY_SCOPE}}` → `capacity_slug` (the request's `role_slug`)
   - `{{ROLE_NAME}}` → role display name
   - `{{ROLE_DIMENSIONS}}` → the request's `scoring_dimensions` (or role-appropriate defaults if omitted)
3. Preserve `supervisor: true` in the generated frontmatter (honor `supervisor: false` only if the request explicitly opts out).
4. Write the generated agent to `.specify/agents/templates/<capacity_slug>.agent.md` (template layer) and run the shared validate + report tail.

### Rule

Never copy the delegation section text into `skills/create-agent/templates/agent-capacity-*-template.md`; edit it only in `skills/create-agent/templates/agent-supervision-delegation.md` so all supervisors stay in sync (single source of truth).

## Project-Custom Capability

Use this capability (`kind: project-custom`) to author a **project-bound custom agent** — an agent that is specific to one project's terminology, assumptions, and workflows, and that should refuse to run silently elsewhere. This is the escape hatch for projects whose needs fall outside the seven preset roles and the generic `custom` kind.

### When to Use

Trigger on phrases: "project-specific agent", "custom project agent", "an agent just for this project", "项目自定义agent", "项目专属agent", or any request for an agent whose behavior is tailored to a single project rather than a reusable role.

### Flexible (non-fixed) flow

Unlike the role-based flow (Workflow steps 1–5), project-custom creation is **deliberately not a fixed sequence** — different projects need very different agents. Only two things are mandatory; everything else adapts to the project:

1. **Confirm the mode** (see § Mode Confirmation) — verify the user wants `project-custom` and not `custom`/`role`.
2. **Bind the project name** — resolve the current project name (from `.specify/instructions.md`, the constitution, or `README.md`) and record it in the `project:` frontmatter marker. The agent MUST be explicitly marked with its project name.
3. **Draft freely** — fill Purpose / Workflow / Output Format (and add/remove sections) to fit the project; there is no required section list beyond the guard.
4. **Preserve the guard** — keep the mandatory `## Project Scope Guard` section that detects a project mismatch at invocation and warns the user before proceeding.

### How it works

1. Load the scaffold `skills/create-agent/templates/agent-project-custom-template.md`.
2. Resolve `{{PROJECT_NAME}}` to the bound project and `{{AGENT_NAME}}`/`{{AGENT_DESCRIPTION}}` from the user's intent.
3. Fill the free-form body sections; delete the scaffold NOTE comment.
4. Keep the `project:` frontmatter marker and the `## Project Scope Guard` section intact — these enable the mismatch warning behavior.
5. Write the generated agent to `.specify/agents/instances/<slug>.agent.md` (instance layer) and run the shared validate + report tail (Workflow steps 4–5).

### Rule

A project-custom agent MUST always carry both the `project:` frontmatter marker and the `## Project Scope Guard` section. When such an agent is invoked in a project other than the one it is bound to, it MUST warn the user and request explicit confirmation rather than silently executing.

## Execution Config Capability

Use this capability (`kind: execution-config`) to author the **execution-layer artifacts** for an agent — the durable dispatch configuration (and optional wrapper script) that turns an Agent Instance/Template into a repeatable **Agent Execution** (see `.specify/shared/definitions/subagent-definitions.md` for the three execution modes and the External Dispatch Visibility Contract).

### Directory contract

| Path | Content | Versioned |
|------|---------|-----------|
| `.specify/agents/execution/configs/<slug>.yaml` | Dispatch config for one agent | yes |
| `.specify/agents/execution/scripts/` | Optional per-agent dispatch wrappers (thin; prefer reusing `skills/create-team/scripts/dispatch.sh`) | yes |
| `.specify/agents/execution/logs/` | Runtime artifacts (`<label>.live.log` / `.jsonl` / `.status`) | **no — gitignored, never committed** |

### Config schema (`configs/<slug>.yaml`)

Field-level schema in [`./references/execution-config.md`](./references/execution-config.md) — `agent`, `mode` (native | virtual | external), `cli`, per-dispatch overrides (`model`, `reasoning_effort`, `context_window`, `extra_flags`), and `log_dir`.

### Rules

- The config references an existing agent definition; if `<slug>` resolves to neither `templates/` nor `instances/`, stop and report instead of inventing one.
- External-mode configs MUST honor the Visibility Contract — dispatch through the stream-json + filter pipeline (reference implementation `skills/create-team/scripts/dispatch.sh` with `DISPATCH_LOG_DIR` pointed at `log_dir`); silent `cli -p … > log 2>&1` dispatch is prohibited.
- Logs are runtime evidence, not deliverables: never commit them, never edit them, and point `log_dir` only inside `execution/logs/`.

## Agent-Specific Configuration

### Step 1: Identify Executing Agent

Before executing this skill's workflow, identify which AI agent you are:

| Agent | Detection Signals |
|-------|-------------------|
| **Claude Code** | System prompt contains "Claude Code"; tools include `Agent`, `Edit`, `Bash`, `Read`; `.claude/` directory exists |
| **GitHub Copilot** | Running in VS Code Copilot Chat context; `.github/copilot-instructions.md` loaded; tools include `workspace edit`, `@terminal` |
| **Qoder CLI** | `.qoder/` directory exists; `AGENTS.md` instructions loaded |
| **opencode** | `.opencode/` directory exists |
| **Codex CLI** | `.codex/` directory exists |
| **Hermes Agent** | `.hermes/` directory exists |

If you cannot identify your agent, skip Step 2 and proceed with the standard workflow.

### Step 2: Load Agent-Specific Guidance

If you identified your agent in Step 1, check if a guide exists at:

```
${SKILL_HOME}/references/<agent-slug>-guide.md
```

Where `<agent-slug>` is: `claude-code`, `copilot`, `qoder`, `opencode`, `codex`, `hermes`.

If the guide exists, read it and apply the agent-specific tool mappings, best practices, and pitfall avoidances during execution. If no guide exists for your agent, proceed with the standard workflow.

### Step 3: Capture Execution Feedback

If you encounter an agent-specific obstacle during execution (e.g., a tool call is unavailable, output format doesn't match expectations, a workaround was needed), generate a feedback document at:

```
.specify/memory/feedback/create-agent-<agent-slug>-<YYYY-MM-DDTHH-MM-SS>.md
```

The feedback document MUST contain:

```markdown
# Agent Execution Feedback

**Source**: create-agent
**Agent**: <agent-slug>
**Timestamp**: <ISO-8601>
**Outcome**: <success-with-workaround | partial-failure | full-failure>

## Obstacle
[Description of the agent-specific issue encountered]

## Workaround Applied
[What was done to work around the issue, if anything]

## Suggested Improvement
[Specific change to the skill or reference document that would prevent this issue]
```

Only generate feedback when a genuine agent-specific obstacle was encountered.

## Self-Improvement Integration

Persistent Agent Templates and Instances are Execution Subjects; one live Agent Execution is evidence, not an editable subject. For every persistent agent, install a compact `## Self-Improvement Contract` that identifies own-run evidence, the editable layer, `improve-agent` as the improvement route, an independent behavior verifier, and a later comparison signal. Follow `.specify/shared/workflow/self-improvement-workflow.md` Create-Flow Integration; do not copy its stages. Execution configs attach evidence to their referenced Agent and do not become a second subject. This `create-agent` Skill is itself a Skill subject and routes its own qualified run evidence through `improve-skills`.

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:create-agent" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
