---
name: create-agent
description: General-purpose authoring skill for single Spec Kit agents — creates role, supervisor, custom, or project-specific (project-custom) agents. Use this when the user mentions ["create an agent", "new agent", "add agent role", "agent template", "supervisor agent", "project-specific agent", "custom project agent", "创建agent", "新建agent", "添加角色", "项目自定义agent", "项目专属agent"]
skill_id: "<SKILL:.specify/skills/create-agent/SKILL.md>"
---

# create-agent

## Goal

Author a **single agent artifact** for the Spec Kit agent system — a **capacity** template, a capacity-scoped **supervisor**, a **custom** `.agent.md`, or a **project-custom** agent. This skill is the single authoring engine invoked by `/speckit.agents` for single-agent work; the command gathers project context and delegates here rather than rendering templates inline. Multi-agent teams (organizing/running several agents) are out of scope — see `/speckit.team` and the `create-team` skill.

> **Class → Instance**: a template here is an **abstract agent Class** — a `agent-capacity-<X>-template.md` with unfilled `{{PLACEHOLDERS}}`. Authoring **instantiates** that Class: `create-agent` fills the placeholders and writes a **concrete agent definition** to `.specify/agents/<slug>.agent.md`. At runtime, `/speckit.agents run` spawns a **live instance (object)** from that definition — many instances from one definition, each independent. This skill operates at the Class/definition layer, never on running instances.

> **Conceptual Model**: the multi-agent Role × Stage × Type + Team/Loop model is defined once in the team domain — see `skills/create-team/references/conceptual-model.md`. This skill authors the single **capacity** Classes that fill a team's Role seats.

> **Capacity, not responsibility**: templates here define an agent's **capacity** — what it *can do*, team-agnostic (tools, skills, model budget, professional identity, domain method). Team-scoped **responsibility** (the Role seat, stage assignment, write territory, handoff paths, reporting duty) is defined in the team domain, never here. The authoritative boundary and edit routing: `skills/create-team/references/capacity-vs-responsibility.md`.

Canonical template home: `skills/create-agent/templates/` (installed mirror: `.specify/skills/create-agent/templates/`).

## Capability Matrix

Select the capability from the request `kind` (or infer from user intent):

| kind | Produces | Source templates | Primary section |
|------|----------|------------------|-----------------|
| `capacity` | One capacity agent Class (six mandatory sections) | `skills/create-agent/templates/agent-capacity-*-template.md` | Workflow steps 1–5 below |
| `supervisor` | A capacity agent that runs its own self-improvement loop | capacity template + `skills/create-agent/templates/agent-supervision-delegation.md` inlined | § Supervisor Capability |
| `custom` | A single narrow, general-purpose custom `.agent.md` (not bound to a project) | free-form per intent | § Mode Confirmation |
| `project-custom` | A project-bound custom agent that marks its project and guards against being run elsewhere | `skills/create-agent/templates/agent-project-custom-template.md` | § Project-Custom Capability |

### Mode Confirmation

When a create request does not clearly map to a single `kind`, do **not** guess. Confirm with the user which authoring mode they want before generating — offer the choices explicitly: `capacity`, `supervisor`, `custom` (narrow, general-purpose), or `project-custom` (project-bound). This is the one confirmation gate shared by all authoring capabilities.

All capabilities share the same validate + report tail (Workflow steps 4–5) and the Agent-Specific Configuration handling below.

## AgentAuthoringRequest Intake

When invoked by `/speckit.agents`, accept the `AgentAuthoringRequest` defined in `.specify/specs/022-eei-agent-triad/contracts/agent-authoring-contract.md` and consume every field: `kind`, `role_slug`, `task`, `scoring_dimensions[]`, `threshold`, `max_iterations`, `environment_paths[]`, `workspace_paths[]`, `project_context`. Missing optional fields fall back to role defaults (threshold from role, `max_iterations`=20). Return an `AuthoringResult` (`artifact_paths`, `kind`, `status`).

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

Write `skills/create-agent/templates/agent-capacity-<slug>-template.md` following the established structure:

```markdown
---
name: {{AGENT_NAME}}
description: {{AGENT_DESCRIPTION}}
user-invocable: true
disable-model-invocation: false
supervisor: true
capacity-scope: <slug>
model: auto
tools: [Read, Grep, Glob, Write, Edit]
maxTurns: 12
color: blue
---
You are a **<Role Name>** for the {{PROJECT_NAME}} project.

## Identity & Responsibilities
[First-person professional identity and core duties]

## Project Context
[Project-specific placeholders from approved list]

## Workflow
[Step-by-step workflow for this role]

## Upstream (Inputs)
[Who provides inputs and what format]

## Downstream (Outputs)
[Who consumes outputs and what format]

## Output Format
[Expected output structure]
```

### 4. Validate the template

- Verify YAML frontmatter has required fields (name, description, user-invocable)
- Verify Qoder-compatible fields are present (`model`, `tools`, `maxTurns`); pick role-appropriate `tools`/`maxTurns`/`color`
- Verify all six mandatory sections are present
- Verify only approved `{{PLACEHOLDER}}` variables are used
- Verify upstream/downstream references are consistent with existing role chain

### 5. Report

- Report the created template file path
- Suggest running `/speckit.agents` to generate the new agent from the template
- Propose how this role fits into the existing workflow chain

## Constraints

- Templates MUST follow the established role-based structure (six mandatory sections)
- Templates MUST use only approved `{{PLACEHOLDER}}` variables
- Frontmatter uses Qoder-compatible fields — `model` (default `auto`, Qoder smart routing), `tools`/`disallowedTools`, `maxTurns`/`timeoutMins`, `skills`/`mcpServers`, `permissionMode`, `background`, `isolation`, `color`. Only `name` and `description` are strictly required; set `model`/`tools`/`maxTurns` for every role and leave the rest unset unless needed.
- Role instructions MUST be written in first-person professional identity
- This skill operates on templates in `skills/create-agent/templates/`, NOT on generated agents in `.specify/agents/`
- `project-custom` agents MUST carry the `project:` frontmatter marker and the mandatory `## Project Scope Guard` section (see § Project-Custom Capability)
- The full framework frontmatter field set is: `user-invocable`, `disable-model-invocation`, `supervisor`, `capacity-scope`, `project` (the last used only by `project-custom` agents)

## Agent Lifecycle (temporary vs persistent)

Every agent this skill can produce has one of two lifecycles. Choose the lifecycle before generating files.

| Lifecycle | Where it lives | When to use | Tool config |
|-----------|----------------|-------------|-------------|
| **temporary** | Context-only — never written to disk | A worker/stage agent spawned for a single run; discarded when the run ends | None; it exists only in the invoking context (FR-011) |
| **persistent** | `.specify/agents/<slug>.agent.md` (the canonical store) | A reusable role or supervisor the project keeps across sessions | Per-file symlinked into every officially supported tool's agent config directory on initialization (FR-010/012) |

**Persistent generation rules**:

- Write the generated agent to `.specify/agents/<slug>.agent.md` (canonical, single source of truth).
- On initialization the CLI (re)creates a **per-file** symlink for each `.specify/agents/*.agent.md` inside every officially supported tool's agent config dir — e.g. `.qoder/agents/<slug>.agent.md → ../../.specify/agents/<slug>.agent.md`, plus `.github/agents`, `.qwen/agents`, `.opencode/agents`, `.hermes/agents`, `.iflow/agents`. Each tool `agents/` is a real directory of per-file links (so tools may add their own overrides beside the framework links); never write tool-specific copies of framework agents.
- Agents are discovered by globbing `.specify/agents/*.agent.md` and reading each file's frontmatter `name`/`description`; no separate registry file is maintained.

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
4. Write the generated agent to `.specify/agents/<capacity_slug>.agent.md` and run the shared validate + report tail.

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
5. Write the generated agent to `.specify/agents/<slug>.agent.md` and run the shared validate + report tail (Workflow steps 4–5).

### Rule

A project-custom agent MUST always carry both the `project:` frontmatter marker and the `## Project Scope Guard` section. When such an agent is invoked in a project other than the one it is bound to, it MUST warn the user and request explicit confirmation rather than silently executing.

## Agent-Specific Configuration

### Step 1: Identify Executing Agent

Before executing this skill's workflow, identify which AI agent you are:

| Agent | Detection Signals |
|-------|-------------------|
| **Claude Code** | System prompt contains "Claude Code"; tools include `Agent`, `Edit`, `Bash`, `Read`; `.claude/` directory exists |
| **GitHub Copilot** | Running in VS Code Copilot Chat context; `.github/copilot-instructions.md` loaded; tools include `workspace edit`, `@terminal` |
| **Qoder CLI** | `.qoder/` directory exists; `AGENTS.md` instructions loaded |
| **opencode** | `.opencode/` directory exists |
| **Qwen Code** | `QWEN.md` instructions loaded; `.qwen/` directory exists |
| **Codex CLI** | `.codex/` directory exists |
| **Hermes Agent** | `.hermes/` directory exists |
| **iFlow** | `.iflow/` directory exists |

If you cannot identify your agent, skip Step 2 and proceed with the standard workflow.

### Step 2: Load Agent-Specific Guidance

If you identified your agent in Step 1, check if a guide exists at:

```
${SKILL_HOME}/references/<agent-slug>-guide.md
```

Where `<agent-slug>` is: `claude-code`, `copilot`, `qoder`, `opencode`, `qwen`, `codex`, `hermes`, or `iflow`.

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

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At the end of a substantial run of this skill, perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this run reached a meaningful wrap-up. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against this skill's declared purpose and produce a short review plus ≥1 concrete, skill-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this skill's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id`; if a parent flow already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "skill:create-agent" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
