---
name: create-agent
description: This skill creates new role-based agent templates for the Spec Kit agent system. Use this when the user mentions ["create an agent", "new agent", "add agent role", "agent template", "创建agent", "新建agent", "添加角色"]
skill_id: "<SKILL:.specify/skills/create-agent/SKILL.md>"
---

# create-agent

## Goal

Create a new role-based agent template in `templates/` that can be used by `/speckit.agents` to generate project-aware agents. The template follows the established role-based structure with Identity & Responsibilities, Project Context, Workflow, Upstream/Downstream, and Output Format sections.

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

- Check `templates/agent-role-*-template.md` for existing roles
- If a similar role exists, suggest updating it via `improve-agent` instead
- Ensure the new role does not overlap significantly with the six preset roles

### 3. Create the template file

Write `templates/agent-role-<slug>-template.md` following the established structure:

```markdown
---
name: {{AGENT_NAME}}
description: {{AGENT_DESCRIPTION}}
user-invocable: true
disable-model-invocation: false
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
- Verify `tools` field is omitted (inherits platform defaults)
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
- The `tools` field MUST be omitted from YAML frontmatter
- Role instructions MUST be written in first-person professional identity
- This skill operates on templates in `templates/`, NOT on generated agents in `.specify/agents/`

## Agent-Specific Configuration

### Step 1: Identify Executing Agent

Before executing this skill's workflow, identify which AI agent you are:

| Agent | Detection Signals |
|-------|-------------------|
| **Claude Code** | System prompt contains "Claude Code"; tools include `Agent`, `Edit`, `Bash`, `Read`; `.claude/` directory exists |
| **GitHub Copilot** | Running in VS Code Copilot Chat context; `.github/copilot-instructions.md` loaded; tools include `workspace edit`, `@terminal` |
| **Qoder CLI** | `.qoder/` directory exists; `QODER.md` instructions loaded |
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
