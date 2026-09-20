---
name: {{SKILL_NAME}}
description: |
  {{DESCRIPTION}}
skill_id: "{{SKILL_ID}}"
---

<!--
  DESCRIPTION RULE (P9): the frontmatter `description` states the capability and
  its trigger conditions/keywords ONLY ("<capability>. Use this when the user
  mentions [...]"). It MUST NOT summarize the workflow steps or body content —
  an agent that reads a workflow summary in the description will skip loading
  the body and execute a degraded version of the skill.
-->

# {{SKILL_NAME}}

## Overview
Briefly describe what this skill does and when it should be triggered. (Conciseness is key!)

## Workflow / Instructions
1. Step 1
2. Step 2
...

## Loop Card (optional — REQUIRED for skills that loop, retry, or run on a cadence)

| Field | Value |
|-------|-------|
| WHEN  | What triggers a run (event/cadence/user intent) |
| SEE   | What state/inputs the run reads first |
| DO    | The bounded unit of work per run |
| CHECK | How the result is verified (concrete command/criterion) |
| STOP  | Termination condition + hard caps (max attempts/iterations) |
| LEAVE | What is handed off / persisted / cleaned up on exit |

## Resource ID
- Canonical ID: `{{SKILL_ID}}`
- Canonical Path: `.specify/skills/{{SKILL_NAME}}/SKILL.md`

## Path Conventions

This Skill follows the canonical `${SKILL_HOME}` / `${SKILL_WORKDIR}` path conventions:

- Use `${SKILL_HOME}/<relative-path>` for every Skill-owned resource reference (scripts, references, assets, sub-directory files).
- Use `${SKILL_WORKDIR}/<relative-path>` for every runtime/user-facing path this Skill reads from or writes to (inputs in the user's project, outputs delivered to the user).
- Never conflate the two; never embed agent-specific install paths (e.g., `${HOME}/.copilot/skills/...`, hard-coded `.specify/skills/...`).

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

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:{{SKILL_NAME}}" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
