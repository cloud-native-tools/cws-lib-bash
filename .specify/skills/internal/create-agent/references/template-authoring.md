# Template Authoring: Capacity-Template Skeleton

The structure a new `agent-capacity-<slug>-template.md` MUST follow. Six mandatory body
sections; frontmatter uses Qoder-compatible fields. Validation rules stay in `SKILL.md`
(`## Constraints`) — this file is the shape to copy. Persistent Templates/Instances also
append `${SKILL_HOME}/templates/agent-self-improvement.md` exactly once; that cross-cutting
contract does not alter the six-section role schema.

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
