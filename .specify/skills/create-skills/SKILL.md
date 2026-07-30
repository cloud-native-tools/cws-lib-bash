---
name: create-skills
description: This skill can create new Spec Kit Skills from user input or conversation history. Use this when the user mentions ["create a skill", "new skill", "make a skill", "skill creation", "添加技能", "创建skill", "新建skill"]
skill_id: "<SKILL:.specify/skills/create-skills/SKILL.md>"
---

# create-skills

## Goal

Create a high-quality Spec Kit Skill from explicit user input or by distilling reusable workflows from the current conversation. The expected result is a well-structured `SKILL.md` with valid frontmatter, clear trigger descriptions, appropriate resource organization, and a deterministic registry entry.

## Workflow

### 0. Detect the runtime mode (Spec Kit project vs standalone)

Spec Kit skills serve both code projects and non-code agent applications (e.g. QoderWork, Wukong, OpenClaw global skill directories). Before anything else, apply the canonical detection rule from `.specify/shared/workflow/runtime-mode.md`:

- `${SKILL_WORKDIR}/.specify/` **exists** → **Spec Kit project mode**: run the full workflow below (scaffolding, registration, agent propagation, engine-backed Feedback).
- `${SKILL_WORKDIR}/.specify/` **does not exist** → **standalone mode**: the target is a plain skills directory owned by the host application. In this mode:
  - `SKILL_HOME` is a sibling directory in the host skills directory; **align the new Skill's format with the existing skills there** (inspect one or two siblings first).
  - **Skip** Step 5 (registration into `.specify/instructions.md`) and Step 7 (propagation to built-in role agents) — neither surface exists.
  - In Step 3, emit a **self-contained** `## Feedback` section (gated reflection, no `feedback-utils.py` invocation) instead of the engine-backed canonical block.
  - Do not scaffold or reference any `.specify/**` path in the generated Skill.

State the detected mode briefly in the final report.

### 1. Determine the creation source

**Case A — User provided explicit input**

Parse `skill name` and `description` from the user input:

- **skill name**: A concise command-like identifier matching the project script validator: letters, digits, hyphens (`-`), and underscores (`_`) only. When inventing a name, prefer lowercase kebab-case (for example, `api-testing`) unless the user explicitly needs another valid form.
- **description**: A capability summary plus trigger keyword list. Format: `This skill can <capability>. Use this when the user mentions [ "keyword1", "keyword2", ... ]`.

If the input contains only a valid name and the Skill already exists (`.specify/skills/<name>/SKILL.md`), redirect to `improve-skills` rather than creating a duplicate.

If the description is missing, derive it from the current conversation or ask one targeted clarification question.

**Case B — User provided no input (empty arguments)**

Distill a reusable Skill from the current conversation history:

1. **Prefer an execution-notes doc over raw transcript**: if the workflow ran in a prior (possibly compacted) session, first look for a dated notes doc (e.g. `${SKILL_WORKDIR}/docs/notes/`) capturing the key commands and outcomes, and distill from it — mining a raw or compacted transcript is slow and lossy. When no such note exists, advise the user (in the wrap-up report) to record key commands into a dated notes doc *during* future executions so later distillation has a reliable source.
2. **Review the conversation history**: Identify recurring task patterns, explicit user intent (e.g., "save as a skill", "solidify this workflow"), multi-step operations with reuse value, and domain-specific decision logic.
3. **Distill a reusable workflow**: Extract the core task objective, key execution steps, trigger conditions/keywords, and required tools/scripts/resources.
4. **Generate Skill metadata**: Produce a concise English `name` (e.g., `data-validation`, `api-testing`) and a `description` with capability summary plus trigger keywords.
5. **Minimal clarification**: If critical information cannot be determined, ask **only one question at a time**. Prioritize: target output, scope (project vs personal), checklist vs multi-step workflow.

### 2. Determine SKILL_HOME and metadata

- **skill name** determines `SKILL_HOME`. Example: `name = "testing"` → `SKILL_HOME = .specify/skills/testing/` (project-level).
- **description** must include keywords and trigger scenarios; avoid vague descriptions.

Storage location options (`SKILL_HOME`):
- `.specify/skills/<name>/` — project-level primary (preferred in Spec Kit project mode)
- `.github/skills/<name>/` — compatibility entry (symlink, not primary)
- `${HOME}/.copilot/skills/<name>/` — personal-level
- host skills directory `<skills-dir>/<name>/` — standalone mode (the directory the host agent application loads skills from)

When authoring the new Skill, follow the path conventions from `templates/commands/skills.md` (`## Path Conventions`):

- Use `${SKILL_HOME}/<relative-path>` for every Skill-owned resource reference (scripts, references, assets).
- Use `${SKILL_WORKDIR}/<relative-path>` for every runtime/user-facing path the new Skill reads or writes (inputs in the user's project, outputs delivered to the user).

### 3. Structure the Skill

#### SKILL.md Specification

**Frontmatter** (minimum required):

```yaml
---
name: <name>
description: <capability + trigger keywords>
---
```

Optional frontmatter (on demand):
- `argument-hint`
- `user-invocable`
- `disable-model-invocation`
- `skill_id`: deterministic identifier for discoverability

**Body** — keep concise and actionable. Must include:
- Result goal
- Key steps (executable, checkable)
- Resource references (use relative paths: `./scripts/x.py`, `./references/details.md`)
- A `## Feedback` section as the final workflow section (mandatory per Feature 028). In Spec Kit project mode, copy the canonical block from `.specify/shared/workflow/feedback-step.md` (it begins with the runtime-mode gate), substituting `skill:<name>` / `--unit-type skill`; in standalone mode, write a self-contained variant — keep the runtime-mode gate and the reflection steps, drop the `feedback-utils.py` invocation and threshold prompt. A new Skill lacking a `## Feedback` section is **non-conformant** and MUST fail validation.

**Size control**: Keep `SKILL.md` under 500 lines. Move large details into `./references/`.

#### Resource Directory Layout

```
${SKILL_HOME}/
├── SKILL.md            # Required, Skill main body
├── scripts/            # Executable scripts (optional)
├── references/         # Reference materials loaded on demand (optional)
└── assets/             # Static assets for outputs (optional)
```

The project creation script may create standard empty resource directories during scaffolding. Treat those as acceptable generated structure; only fail validation for unrelated documentation files, broken links, or resource directories whose checked-in contents are not needed by the Skill.

#### Progressive Disclosure

1. Discovery: Read `name` + `description`
2. After match: Read `SKILL.md` body
3. When needed: Read `scripts/`, `references/`, `assets/`

Constraints:
- `SKILL.md` recommended < 500 lines
- Reference chain at most one level (from `SKILL.md` directly to resource)
- Use relative paths uniformly (prefer `./references/...`)

#### Content NOT to include

Do not add unrelated documents: `README.md`, `INSTALLATION_GUIDE.md`, `QUICK_REFERENCE.md`, `CHANGELOG.md`, process logs, or full retrospectives.

### 4. Incrementally clarify details

Ask **only one question per round**, waiting for user response. Prioritize:
- Target output: What should the Skill produce?
- Applicable scenarios: Under what trigger conditions?
- Resource needs: Scripts, references, templates, or toolchain?

Iterate until:
1. Frontmatter is complete (`name`, `description`)
2. Body has clear executable steps
3. Resource directories are ready as needed
4. All resource links use relative paths

### 5. Register the Skill

**Spec Kit project mode only** — in standalone mode skip this step entirely (the host application discovers skills by scanning its skills directory; there is no registry file).

Generate the Resource ID and persist:

- **skill_id**: `<SKILL:.specify/skills/<name>/SKILL.md>`
- **Canonical Path**: `.specify/skills/<name>/SKILL.md`

Write to `.specify/instructions.md` → `### Skills` table:
- `Skill Name`, `Skill ID`, `Description`, `Canonical Path`

Constraints:
- Do not write duplicate entries for the same `skill_id`
- Keep the list sorted and deduplicated
- Remove `None yet.` once real entries exist

### 6. Validate the Skill

Run quality checks before reporting completion. See [the quality checklist](./references/skill-creation-quality-checklist.md) for the full validation workflow.

Minimum checks:
- [ ] Frontmatter: `name` matches directory, `description` has triggers
- [ ] Body: clear steps, no vague placeholders
- [ ] Resources: relative paths, no broken links; standard generated resource directories are acceptable
- [ ] Registry: one deduplicated row in `.specify/instructions.md` (Spec Kit project mode only; not applicable standalone)
- [ ] Size: `SKILL.md` < 500 lines
- [ ] No unrelated documentation files
- [ ] Feedback: a `## Feedback` section is present as the final workflow section (Feature 028), beginning with the runtime-mode gate. Spec Kit project mode requires the canonical engine-backed block from `.specify/shared/workflow/feedback-step.md`; standalone mode requires the self-contained variant (no engine call). A Skill without the section is non-conformant — fix before reporting completion.
- [ ] Standalone mode only: format is consistent with sibling skills in the host directory, and no `.specify/**` path is referenced
- [ ] Spec Kit project mode: **run the existing skill-conformance contract suite** (`pytest tests/contract/ -q -k "skill or runtime_mode"`) before reporting completion — new skills are subject to ALL pre-existing conformance contracts (runtime-mode gate, feedback-section shape, registry dedup); a later full-suite regression is the wrong place to discover a miss

### 7. Propagate the Skill to built-in agents

Applies only when creating a **new** Skill **in Spec Kit project mode** — in standalone mode skip this step (no built-in role agents exist). Wire it into the built-in role agents so they prefer it for role-relevant work, following the Feature 026 Skill Enablement convention (see `docs/agents/command-and-skills.md`).

1. **Guard**: skip if the new Skill is non-declarable (reference-only/meta: `create-agent`, `improve-agent`, `create-skills`, `improve-skills`, `create-team`, `improve-team`, `create-tools`, `improve-tools`). Normal user-created Skills proceed.
2. **Analyze**: read the 7 built-in role agents from `.specify/agents/` (`requirements-analyst`, `system-designer`, `module-designer`, `test-engineer`, `qa-engineer`, `knowledge-manager`, `ux-analyst`) and judge each agent's role against the new Skill's capability + trigger keywords.
3. **Match**: pick the agents whose role operations the Skill covers; draft a one-line "when to use" per match. If none match, report "no role-relevant agents" and skip edits (no forced use).
4. **Propose then apply**: show a `| Agent | Skill | When to use |` table and wait for confirmation. On confirm, for each matched agent edit BOTH `agents/<slug>.agent.md` and `.specify/agents/<slug>.agent.md`:
   - Append the canonical Skill slug to the `skills:` frontmatter list (dedup; preserve order and all other keys).
   - Add a `| <skill> | <when-to-use> |` row to that agent's `## Skill Enablement` table.

**Invariants**: use the canonical slug; it MUST resolve to an installed `.specify/skills/<slug>/SKILL.md`; never add a non-declarable slug; preserve all existing frontmatter. Generator templates (`agent-capacity-*-template.md`) are intentionally NOT updated — a later regeneration would drop the added Skill.

### 8. Report completion

Summarize:
- Detected runtime mode (Spec Kit project vs standalone) and which Spec-Kit-specific steps were skipped
- Skill capabilities and directory structure
- `SKILL.md` path and `skill_id`
- Example prompts
- Which built-in agents the Skill was propagated to (or "none" if no role match)
- Suggested next-step customizations (e.g., add references, scripts, or personalized trigger keywords)

## Design Principles

### Manage Degrees of Freedom

- **High freedom**: Text strategies for multi-path problems
- **Medium freedom**: Pseudocode / parameterized scripts for configurable primary paths
- **Low freedom**: Fixed scripts / steps for high-risk error-prone operations

### Discoverable Descriptions

`description` must include keywords and trigger scenarios. Avoid vague one-liners.

### Anti-Patterns

- Vague descriptions that fail to trigger
- `SKILL.md` too large without splitting into `./references/`
- Directory name inconsistent with `name` in frontmatter
- Missing executable steps (only background prose)
- Inconsistent or broken resource paths

## Slash Behavior Notes

Skill behavior in the `/` menu is controlled by frontmatter:
- Default: Manually invocable + auto-triggerable
- `user-invocable: false`: Not manually invocable
- `disable-model-invocation: true`: Not auto-triggerable
- Both set: Both disabled

## Continuous Improvement

1. Validate the skill with real tasks
2. Record pain points and inefficient steps
3. Revise `SKILL.md` or resource directories
4. Validate again, forming a stable iteration

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
     --unit-id "skill:create-skills" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
