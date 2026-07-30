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

At the end of a substantial run of this skill, perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this run reached a meaningful wrap-up. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against this skill's declared purpose and produce a short review plus ≥1 concrete, skill-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this skill's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id`; if a parent flow already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "skill:{{SKILL_NAME}}" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
