---
name: improve-skills
description: This skill continuously improves one local Skill from a user-provided Skill description, execution history, user feedback, failure cases, and observed inefficiencies. Use this when the user mentions ["improve skills after use", "skill execution feedback", "refine SKILL.md", "skill retrospective", "skill iteration", "技能执行反馈", "基于执行问题优化skill", "持续改进Skill"]
skill_id: "<SKILL:.specify/skills/improve-skills/SKILL.md>"
---

# improve-skills

## Goal

Continuously improve one existing local SpecKit Skill from a user-provided Skill description and evidence from real executions. The expected result is a focused Skill update that fixes observed problems, captures reusable lessons, and makes the next execution more reliable.

## Input Contract

The input is a description of the Skill to improve. It must be interpreted as follows:

- **Target identifier**: identify exactly one local Skill by `skill_id`, frontmatter `name`, canonical path, or Skill directory name. If multiple Skills match or no local Skill can be found, ask one targeted clarification before editing.
- **Optimization direction**: extract the requested direction when present, such as fixing execution failures, improving efficiency, clarifying inputs/outputs, correcting tool usage, or strengthening validation. If no direction is present, infer it only from concrete execution history and user feedback.
- **User emphasis**: treat details in the user's description as high-priority evidence. Analyze them explicitly even when broader execution history suggests additional improvements.

## Workflow

1. **Identify the target Skill, optimization direction, and execution window**
   - Parse the user's Skill description for a `skill_id`, frontmatter `name`, canonical path, or Skill directory name; improve only that local Skill.
   - If the user says “this Skill”, infer the target from the active file or recent conversation, then verify it resolves to exactly one local Skill.
   - Extract the requested optimization direction when present and carry it through evidence collection, analysis, edits, validation, and reporting.
   - Treat `.specify/skills/<name>/SKILL.md` as the canonical source of truth; use `.github/skills/<name>` only as a compatibility entrypoint.
   - Re-read the canonical `SKILL.md` before editing, especially when the system reports recent user or formatter changes, or when a refresh/script may have modified metadata.
   - Define the execution window to review: current conversation, last Skill run, failed command output, user correction, test failure, or recent edits.
   - When improving `improve-skills` itself, use the most recent improvement loop as the execution window and avoid reapplying the same lesson unless new evidence shows the previous fix was insufficient.

2. **Measure execution effectiveness from history**
   - Gather concrete evidence before editing: user feedback, steps that were confusing, tool failures, wrong assumptions, repeated manual fixes, validation gaps, and changed files from the execution.
   - Include terminal/test outputs and error messages when they explain what went wrong.
   - Review changed files as evidence, but classify generated validation artifacts such as `tools/*.json` separately from hand-edited Skill instructions.
   - Measure the target Skill against the requested or inferred optimization goal: whether it could be invoked, whether its expected input format was accepted, whether the workflow produced the expected output, how many avoidable manual/tool steps occurred, and whether validation caught the issue.
   - Identify the execution-flow steps that did not meet expectations, including broken command-line parameters, mismatched expected formats, missing prerequisites, ambiguous target resolution, inefficient tool choices, repeated searches, or unnecessary user handoffs.
   - Separate facts from interpretation. Do not optimize from generic best-practice principles when no execution evidence supports the change.
   - If evidence is insufficient, ask one targeted question about what failed, what was inefficient, or what should happen differently next time.

3. **Analyze user-provided emphasis and organize improvement items**
   - Give the user's stated optimization direction a dedicated analysis pass: confirm which parts are already satisfied, which parts are missing, and which edits will directly address the request.
   - Group observations by failure mode: trigger/discovery, scope inference, missing context, wrong tool choice, unsafe step, unclear output, validation gap, or resource/reference issue.
   - For each item, record: observed symptom, likely cause in the current Skill instructions, desired next behavior, and the file section to change.
   - Discard one-off environment noise unless the Skill should explicitly handle it in future runs. If a refresh command exits successfully with a fallback after an optional source warning, record it as a validation note rather than a root cause.
   - **Legacy path idioms**: when the Skill under review still uses any of the following, flag them as migration candidates and apply the Migration Mapping table from `templates/commands/skills.md` (`## Migration Mapping`):
     - Bare relative paths such as `./scripts/init.sh` or `./references/checklist.md` → rewrite as `${SKILL_HOME}/...`.
     - `${SKILL_ROOT}/X` references → rewrite as `${SKILL_HOME}/X`.
     - Agent-specific install paths embedded in prose (e.g., `~/.copilot/skills/<name>/...`, hard-coded `.specify/skills/<name>/...`) → rewrite as `${SKILL_HOME}/...`.

4. **Correct the root causes with minimal changes**
   - For complete execution failures, fix the instruction that caused non-execution first, such as wrong command-line arguments, nonexistent paths, invalid expected file formats, incompatible metadata, or missing prerequisite checks.
   - For successful but inefficient executions, replace the inefficient step with a more direct method, deterministic script, narrower search, better evidence filter, or clearer decision branch.
   - Prefer changing the step that caused the observed problem over adding broad new rules.
   - Convert repeated user corrections into explicit decision branches.
   - Convert repeated manual checks into checklist items or deterministic scripts when appropriate.
   - Move detailed lessons to `./references/` only when they are useful but not needed every run.
   - **Slim `SKILL.md` toward contract-only content**: when an edit touches `SKILL.md`, also evaluate whether existing sections should be moved out per [`./references/skill-slimming-principles.md`](./references/skill-slimming-principles.md). The body is a contract — frontmatter, resource index, workflow skeleton, strict requirements, and conventions — not a manual. How-to checklists, error tables, command-pair comparisons, environment-detection scripts, install commands, and intra-domain routing tables belong in references; replace them with a one-sentence pointer + anchor link. Always **delete-and-absorb** (copy the substantive content into the target reference in the same edit), never delete-and-drop. Defer environment-level recovery (auto-install, shell switching, OS branching) to the user — surface the error and fix command, then stop.

5. **Update the Skill for the next execution**
   - Edit `SKILL.md` to make the improved behavior executable and checkable.
   - Update frontmatter `description` only when execution feedback shows trigger/discovery mismatch.
   - Update `./references/`, `./scripts/`, or `./assets/` only when the evidence shows they will reduce future mistakes.
   - Avoid adding process logs, changelogs, or full retrospectives to the Skill; distill only reusable lessons.

6. **Validate the improvement loop**
   - Re-read the changed Skill and verify that each edit maps to an observed execution issue.
   - Check frontmatter, resource paths, line count, compatibility entry, and registry row when metadata changed. If `skill_id` is added or corrected, ensure `.specify/instructions.md` has one deduplicated Skills registry row for the canonical Skill.
   - Accept a directory-level `.github/skills -> ../.specify/skills` symlink as a valid compatibility entrypoint; do not require a separate per-Skill symlink when the directory symlink already exposes the Skill.
   - If a combined validation command returns only partial output or omits later checks, rerun the missing checks individually before concluding validation passed.
   - Do not document `.specify/scripts/` as a Skill-owned resource directory; Skill-owned executable resources belong in `./scripts/`.

7. **Report the feedback-driven changes**
   - Summarize the execution feedback that drove the update.
   - List changed Skill files and the behavior expected to improve next time.
   - Note any unresolved feedback that needs another real execution to validate.

## Quality Checklist

Use [the Skill quality checklist](./references/skill-quality-checklist.md) to structure execution feedback, root-cause analysis, and validation when the improvement involves more than one observed issue.

## Resource ID

- Canonical ID: `<SKILL:.specify/skills/improve-skills/SKILL.md>`
- Canonical Path: `.specify/skills/improve-skills/SKILL.md`
