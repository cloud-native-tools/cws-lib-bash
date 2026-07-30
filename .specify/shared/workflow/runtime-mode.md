# Runtime Mode Detection (Spec Kit project vs standalone)

Spec Kit supports two kinds of consumers:

1. **Spec Kit project mode (code project)** — the working directory is a project
   managed by the Spec Kit framework: a `.specify/` directory exists at the project
   root (instructions, memory, scripts, agents, skills mirror). The full SDD flow
   and all Spec-Kit-specific integrations are available.
2. **Standalone mode (non-code / agent application)** — the same skills are loaded
   by an agent application outside any Spec Kit project, e.g. a global skills
   directory for QoderWork, Wukong (悟空), OpenClaw, or a personal
   `~/.qoderwork/skills/`-style install. There is **no** `.specify/` directory,
   no `feedback-utils.py` / `memory-utils.py` engine, no `instructions.md`
   registry, and no built-in role agents.

Every skill (and any unit embedding a Spec-Kit-specific step) MUST detect the mode
before running such a step, and MUST NOT fail or block in standalone mode.

## Detection rule (canonical)

```bash
if [ -d "${SKILL_WORKDIR:-.}/.specify" ]; then
  RUNTIME_MODE="spec-kit"     # Spec Kit project mode
else
  RUNTIME_MODE="standalone"   # non-code / agent application mode
fi
```

- The check is on the **working directory root** (`${SKILL_WORKDIR}`), not on the
  skill's own install location (`${SKILL_HOME}`).
- The check is cheap and repeatable; when in doubt, re-check rather than caching a
  stale result across directory changes.

## Behavior matrix

| Spec-Kit-specific step | Spec Kit project mode | Standalone mode |
|---|---|---|
| `## Feedback` engine persistence (`feedback-utils.py`) | Run per `feedback-step.md` | **Skip the entire Feedback step** (no engine, no store, no prompt) |
| Registry write to `.specify/instructions.md` (Skills/Agents/Tools tables) | Required | **Skip** — the host application discovers skills by directory scan |
| Propagation to built-in role agents (`.specify/agents/*.agent.md`) | Per convention (e.g. Skill Enablement) | **Skip** — no role agents exist |
| Memory engine (`memory-utils.py`, `.specify/memory/session|knowledge/`) | Available | **Unavailable** — state the limitation instead of erroring |
| Canonical shared docs (`.specify/shared/workflow/*.md`) | Read as source of truth | **Not present** — the block embedded in the skill file governs |
| Output paths under `.specify/**` (reports, teams, review records, workflow docs) | Default | **Fall back** to the skill's declared alternative (e.g. `docs/`, the host skills directory, or a user-specified path); ask when no alternative is declared |
| Mirror/dual-copy discipline (`skills/` ↔ `.specify/skills/`) | Enforced | **Not applicable** — edit only the single host copy, matching the host directory's existing skill format |

Steps that are not Spec-Kit-specific (the skill's core capability, its own
`${SKILL_HOME}` scripts/references/assets) run identically in both modes.

## Canonical gate line for `## Feedback` sections

Every skill's `## Feedback` section MUST begin with this gate (copy verbatim):

```markdown
**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.
```

## Authoring rules (create-skills / improve-skills)

- When **creating** a skill in standalone mode: align with the host directory's
  existing skill format, do not scaffold `.specify/` paths, do not register into
  any instructions file, do not propagate to role agents, and emit a
  self-contained `## Feedback` section (reflection summary in the reply only —
  no engine invocation).
- When **validating/repairing** a skill found in a standalone directory: the
  engine-backed Feedback block is NOT required; a self-contained reflection
  section (or the gated canonical block) is conformant.
