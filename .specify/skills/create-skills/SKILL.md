---
name: create-skills
description: This skill can create new Spec Kit Skills from user input or conversation history. Use this when the user mentions ["create a skill", "new skill", "make a skill", "skill creation", "添加技能", "创建skill", "新建skill"]
skill_id: "<SKILL:.specify/skills/create-skills/SKILL.md>"
---

# create-skills

## Goal

Create a high-quality Spec Kit Skill from explicit user input or by distilling reusable workflows from the current conversation. The expected result is a well-structured `SKILL.md` with valid frontmatter, clear trigger descriptions, appropriate resource organization, and a deterministic registry entry.

## Workflow

### 1. Determine the creation source

**Case A — User provided explicit input**

Parse `skill name` and `description` from the user input:

- **skill name**: A concise command-like identifier matching the project script validator: letters, digits, hyphens (`-`), and underscores (`_`) only. When inventing a name, prefer lowercase kebab-case (for example, `api-testing`) unless the user explicitly needs another valid form.
- **description**: A capability summary plus trigger keyword list. Format: `This skill can <capability>. Use this when the user mentions [ "keyword1", "keyword2", ... ]`.

If the input contains only a valid name and the Skill already exists (`.specify/skills/<name>/SKILL.md`), redirect to `improve-skills` rather than creating a duplicate.

If the description is missing, derive it from the current conversation or ask one targeted clarification question.

**Case B — User provided no input (empty arguments)**

Distill a reusable Skill from the current conversation history:

1. **Review the conversation history**: Identify recurring task patterns, explicit user intent (e.g., "save as a skill", "solidify this workflow"), multi-step operations with reuse value, and domain-specific decision logic.
2. **Distill a reusable workflow**: Extract the core task objective, key execution steps, trigger conditions/keywords, and required tools/scripts/resources.
3. **Generate Skill metadata**: Produce a concise English `name` (e.g., `data-validation`, `api-testing`) and a `description` with capability summary plus trigger keywords.
4. **Minimal clarification**: If critical information cannot be determined, ask **only one question at a time**. Prioritize: target output, scope (project vs personal), checklist vs multi-step workflow.

### 2. Determine SKILL_HOME and metadata

- **skill name** determines `SKILL_HOME`. Example: `name = "testing"` → `SKILL_HOME = .specify/skills/testing/` (project-level).
- **description** must include keywords and trigger scenarios; avoid vague descriptions.

Storage location options (`SKILL_HOME`):
- `.specify/skills/<name>/` — project-level primary (preferred)
- `.github/skills/<name>/` — compatibility entry (symlink, not primary)
- `~/.copilot/skills/<name>/` — personal-level

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
- [ ] Registry: one deduplicated row in `.specify/instructions.md`
- [ ] Size: `SKILL.md` < 500 lines
- [ ] No unrelated documentation files

### 7. Report completion

Summarize:
- Skill capabilities and directory structure
- `SKILL.md` path and `skill_id`
- Example prompts
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