---
description: 技能管理编排入口：委托创建或优化对应技能
---
<!-- AUTO-GENERATED from templates/commands/skills.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
> `/speckit.skills` is the orchestration entrypoint for Skill management. It delegates to `create-skills` (new) or `improve-skills` (existing, with mandatory spec-compliance modernization pass first).

## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Extract target Skill name (concise command-like identifier: letters, digits, hyphens, underscores).

## Orchestration Workflow

### Step 1: Parse target Skill

- If user names a Skill explicitly → use that name
- If empty → infer from conversation or ask one targeted question

### Step 2: Check existence

Check `.specify/skills/<name>/SKILL.md` exists (canonical source).

### Step 3: Route

**If NOT exists** → delegate to `create-skills` skill:
- Read `skills/create-skills/SKILL.md` for full workflow
- New Skill MUST conform to current spec (directory layout, frontmatter, `${SKILL_HOME}`/`${SKILL_WORKDIR}` conventions)
- Use `.specify/templates/skills-template.md` as starting point

**If EXISTS** → delegate to `improve-skills` skill with two-phase pass:
1. **Phase A — Spec-compliance modernization** (mandatory before any optimization):
   - Canonical path: `.specify/skills/<name>/SKILL.md`
   - Directory structure: `SKILL.md`, `.specify/scripts/`, `references/`, `assets/`
   - Frontmatter: `name`, `description` (with triggers), `skill_id`
   - Path conventions: `${SKILL_HOME}/` for Skill-owned resources, `${SKILL_WORKDIR}/` for runtime paths
   - Legacy idiom migration: `./X` → `${SKILL_HOME}/X`, `${SKILL_ROOT}/X` → `${SKILL_HOME}/X`
   - Discoverability: `.specify/skills/<name>/SKILL.md` present with valid frontmatter — no registration table exists (see `.specify/skills.md`)
   - Hygiene: SKILL.md under 500 lines; oversize → `references/`

2. **Phase B — User-requested refinement**: Standard `improve-skills` workflow.

For detailed path conventions (`${SKILL_HOME}` / `${SKILL_WORKDIR}` semantics, computation idioms, nested invocations), see `skills/create-skills/SKILL.md`.

### Step 4: Propagate to built-in agents (create path only)

After a **new** Skill is created (skip on the `improve-skills` path), wire it into the built-in role agents so they prefer it for role-relevant work (Skill Enablement convention: the `## Skill Enablement` section pattern carried by the built-in role agents under `.specify/agents/templates/`).

1. **Guard**: skip if the new Skill is non-declarable (reference-only/meta: `create-agent`, `improve-agent`, `create-skills`, `improve-skills`, `create-team`, `improve-team`). Normal user-created Skills proceed.
2. **Analyze**: read the Meta Agent preset set from `.specify/agents/templates/` and the 7 Worker role capability templates from `skills/create-agent/templates/` (`requirements-analyst`, `system-designer`, `module-designer`, `test-engineer`, `qa-engineer`, `knowledge-manager`, `ux-analyst`). Judge each agent's role (Identity & Responsibilities) against the new Skill's capability + trigger keywords.
3. **Match**: select the agents whose role operations the Skill covers and draft a one-line "when to use" per match. If none match, report "no role-relevant agents" and skip edits (no forced use).
4. **Propose**: present a `| Agent | Skill | When to use |` table as disclosure (non-blocking).
5. **Apply** (directly after the proposal is presented; edits are reversible via later edits): for each matched agent, edit BOTH `agents/<slug>.agent.md` and `.specify/agents/templates/<slug>.agent.md`:
   - Append the canonical Skill slug to the `skills:` frontmatter list (dedup; preserve order and all other keys).
   - Add a `| <skill> | <when-to-use> |` row to that agent's `## Skill Enablement` table.
6. **Invariants**: use the canonical slug; it MUST resolve to an installed `.specify/skills/<slug>/SKILL.md`; never add a non-declarable slug; preserve all existing frontmatter. Generator templates (`agent-capacity-*-template.md`) are intentionally NOT updated (a later regeneration would drop the added Skill).

### Step 5: Validate and report

- Confirm frontmatter valid (`name`, `description`, `skill_id`)
- Verify canonical path matches `.specify/skills/<name>/SKILL.md`
- Verify the skill is discoverable from the filesystem (`.specify/skills/<name>/SKILL.md`, valid frontmatter)
- Report: paths, skill_id, modernization results, and (create path) which built-in agents the Skill was propagated to

For agent-specific operational guidance, see `.specify/shared/workflow/agent-configuration.md`.

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.skills" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Handoffs

**After**: Run `/speckit.instructions` to update discovery metadata.