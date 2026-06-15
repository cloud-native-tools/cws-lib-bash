# Skill Quality Checklist

Use this checklist when improving a Skill after a real execution. The focus is evidence from what just happened, not abstract best-practice auditing.

## Execution Feedback Collection

- Target Skill and execution window are clear.
- For self-improvement of `improve-skills`, the reviewed window is the latest improvement loop and duplicate lessons are not re-added without new evidence.
- The canonical `.specify/skills/<name>/SKILL.md` was re-read before editing if recent edits, formatters, or refresh scripts may have changed it.
- User feedback, corrections, and requested behavior changes are captured.
- Tool failures, test failures, terminal errors, or validation gaps are captured when relevant.
- Changed files and manual fixes from the execution are reviewed, with generated manifests separated from hand-edited Skill files.
- Timestamp-only generated manifest diffs are identified as validation churn, not behavior change.
- Facts are separated from assumptions or general preferences.

## Feedback Organization

- Each issue has an observed symptom.
- Each issue has a likely cause in the current Skill instructions or resources.
- Each issue has a desired next-run behavior.
- Issues are grouped by failure mode: trigger/discovery, scope inference, missing context, wrong tool choice, unsafe step, unclear output, validation gap, or resource/reference issue.
- One-off environment noise is excluded unless the Skill should handle it in future runs; successful fallback warnings are tracked as validation notes, not root causes.

## Root-Cause-Driven Improvement

- Every Skill edit maps back to at least one observed issue.
- Repeated user corrections become explicit decision branches.
- Repeated manual checks become checklist items or deterministic scripts when useful.
- Broad principle-only changes are avoided unless supported by execution evidence.
- Detailed lessons are distilled into reusable guidance rather than copied as raw logs.

## Frontmatter

- `name` exists, matches the parent directory, and is stable.
- `description` is specific, non-empty, and under 1024 characters.
- `description` includes both capability and trigger keywords.
- `description` is changed only when real trigger/discovery feedback shows it is needed.
- Optional fields are absent unless they change real behavior.
- `skill_id`, when present, points to the canonical `.specify/skills/<name>/SKILL.md` path.

## Discoverability

- Trigger keywords include likely user wording, aliases, and domain-specific terms.
- The description avoids vague phrases such as “helps with” without concrete tasks.
- Similar Skills have distinct descriptions to prevent accidental activation.

## Body Structure

- The first section states the result goal.
- Steps are ordered, executable, and checkable.
- Decision branches tell the agent what to do when scope is partial, broad, or ambiguous.
- A single existing Skill name as input is handled as "refine this Skill", not as a missing-description failure.
- History collection, evidence organization, root-cause analysis, Skill update, and validation appear as an explicit loop.
- The body contains operational instructions, not general background.
- The main `SKILL.md` stays below 500 lines.

## SKILL.md Slimming

- `SKILL.md` contains only contract content: frontmatter, resource index, workflow skeleton (step heading + one-sentence goal + anchor link), strict requirements, and conventions.
- No how-to checklist longer than 10 lines lives in `SKILL.md`; it is in a reference.
- No error table (symptom / cause / fix) lives in `SKILL.md`; it is in a reference.
- No code block longer than 5 lines lives in `SKILL.md` (except workflow diagrams).
- No install / bootstrap commands appear in `SKILL.md`.
- No environment-detection / OS-branching logic appears in workflow steps.
- Each removed section has been **absorbed** into the target reference in the same edit (not dropped silently).
- Each remaining pointer in `SKILL.md` has a valid anchor link to the reference that now holds the detail.
- No two locations explain the same topic; one is the source of truth, others link to it.
- After slimming, a grep for removed slugs/filenames returns 0 dangling references.

## Resources

- `./references/` contains detailed knowledge loaded on demand.
- `./scripts/` contains deterministic repeated operations only.
- `./assets/` contains static templates or reusable output files only.
- Resource references are relative to the Skill root and do not form deep reference chains.

## Compatibility and Registry

- `.specify/skills/<name>/` is the primary copy.
- `.github/skills/<name>` is a compatibility entrypoint, preferably a symlink or placeholder, not an independent divergent copy; a directory-level `.github/skills -> ../.specify/skills` symlink is also valid.
- `.specify/instructions.md` has one deduplicated Skills registry row per canonical `skill_id`.
- If `skill_id` metadata is added or corrected, the Skills registry row is checked and updated in the same improvement loop.
- Registry rows are sorted and no `None yet.` placeholder remains once real entries exist.
- `/speckit.skills` prompt sources use `./scripts/` for Skill-owned scripts and call `refresh-tools.sh` with explicit source flags before `--json`.

## Validation Summary Template

Report results with:

1. Execution feedback reviewed
2. Root causes identified
3. Skill changes made
4. Validation results
5. Feedback still needing another execution

Before reporting validation results, confirm that compound commands did not hide later checks. If output is partial, rerun missing checks individually.
