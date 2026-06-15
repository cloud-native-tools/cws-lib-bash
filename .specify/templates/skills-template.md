---
name: {{SKILL_NAME}}
description: |
  {{DESCRIPTION}}
skill_id: "{{SKILL_ID}}"
---

# {{SKILL_NAME}}

## Overview
Briefly describe what this skill does and when it should be triggered. (Conciseness is key!)

## Workflow / Instructions
1. Step 1
2. Step 2
...

## Resource ID
- Canonical ID: `{{SKILL_ID}}`
- Canonical Path: `.specify/skills/{{SKILL_NAME}}/SKILL.md`

## Path Conventions

This Skill follows the canonical path conventions defined in `templates/commands/skills.md` (`## Path Conventions`):

- Use `${SKILL_HOME}/<relative-path>` for every Skill-owned resource reference (scripts, references, assets, sub-directory files).
- Use `${SKILL_WORKDIR}/<relative-path>` for every runtime/user-facing path this Skill reads from or writes to (inputs in the user's project, outputs delivered to the user).
- Never conflate the two; never embed agent-specific install paths (e.g., `~/.copilot/skills/...`, hard-coded `.specify/skills/...`).

For shell scripts under `${SKILL_HOME}/scripts/`, copy this idiom verbatim at the top of each script:

```bash
SKILL_HOME="${SKILL_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd -P)}"
SKILL_WORKDIR="${SKILL_WORKDIR:-$(pwd -P)}"
```

## Resources

### Scripts (`${SKILL_HOME}/scripts/`)
- No scripts currently. (Add executable scripts here for deterministic tasks.)

### References (`${SKILL_HOME}/references/`)
- No references currently. (Add documentation/schemas here to be loaded on-demand.)

### Assets (`${SKILL_HOME}/assets/`)
- No assets currently. (Add output templates/files here.)
