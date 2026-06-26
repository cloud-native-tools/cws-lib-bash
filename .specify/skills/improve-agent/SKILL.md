---
name: improve-agent
description: This skill iteratively improves existing role-based agent templates from execution feedback, user corrections, and behavioral observations. Use this when the user mentions ["improve agent", "refine agent", "fix agent", "agent feedback", "agent not working", "优化agent", "改进agent", "agent执行反馈"]
skill_id: "<SKILL:.specify/skills/improve-agent/SKILL.md>"
---

# improve-agent

## Goal

Improve an existing role-based agent template in `templates/` based on evidence from real usage — user feedback, failure cases, behavioral drift, or observed inefficiencies. The result is a targeted update to the template that fixes the identified issues while preserving the established template structure.

## Input Contract

The input is a description of the agent to improve and what went wrong or could be better. Parse:

- **Target identifier**: Identify the agent template by role name, slug, or file path. Must resolve to exactly one `templates/agent-role-*-template.md` file.
- **Improvement direction**: What specifically needs to change — extracted from user feedback, observed failures, or behavioral drift.
- **Evidence**: Concrete examples of the problem (conversation excerpts, incorrect outputs, missing behaviors).

## Workflow

### 1. Identify the target template

- Parse the user's input for a role name, slug, or template path
- Resolve to `templates/agent-role-<slug>-template.md`
- If multiple templates match or none match, ask one clarifying question
- Read the current template content before making changes

### 2. Gather evidence

Collect concrete evidence of what needs improvement:

- **User feedback**: Direct statements about what the agent did wrong
- **Behavioral observations**: How the generated agent actually behaved vs. expected behavior
- **Output quality**: Whether the agent's output format matched the template's specification
- **Workflow adherence**: Whether the agent followed its defined workflow steps
- **Handoff issues**: Whether upstream/downstream references worked correctly

### 3. Analyze root causes

For each issue, determine whether the root cause is in:

- **Identity section**: Role definition too vague or too narrow
- **Responsibilities**: Missing duties or conflicting priorities
- **Workflow**: Steps unclear, wrong order, or missing critical steps
- **Upstream/Downstream**: Incorrect references or missing handoff artifacts
- **Output Format**: Expected output not matching what downstream roles need
- **Placeholders**: Wrong context variables for this role's needs

### 4. Apply targeted fixes

- Make minimal, focused changes that address the identified root causes
- Preserve the established template structure (six mandatory sections)
- Do not change sections that are working correctly
- Verify that fixes maintain handoff chain consistency with other roles

### 5. Validate the updated template

- Verify YAML frontmatter still has required fields
- Verify `tools` field remains omitted
- Verify all six mandatory sections are still present
- Verify only approved `{{PLACEHOLDER}}` variables are used
- Verify upstream/downstream references are still consistent

### 6. Report

- List the specific changes made and why
- Reference the evidence that motivated each change
- Suggest re-running `/speckit.agents` to regenerate the agent from the updated template
- Recommend testing the improved agent with the scenario that originally failed

## Constraints

- This skill operates on templates in `templates/`, NOT on generated agents in `.specify/agents/`
- Changes MUST be evidence-based — do not optimize from generic best practices without concrete evidence
- The established template structure (six mandatory sections) MUST be preserved
- Handoff chain consistency with other role templates MUST be maintained
- Prefer minimal changes that fix the observed problem over broad rewrites

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
.specify/memory/feedback/improve-agent-<agent-slug>-<YYYY-MM-DDTHH-MM-SS>.md
```

The feedback document MUST contain:

```markdown
# Agent Execution Feedback

**Source**: improve-agent
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
