## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions.

## Checklist Purpose: "Unit Tests for English"

Checklists are **UNIT TESTS FOR REQUIREMENTS WRITING** — they validate quality, clarity, and completeness of requirements. NOT implementation verification.

For detailed methodology, examples, anti-examples, and quality dimension patterns, see `.specify/shared/guidelines/checklist-methodology.md`.

## Execution Steps

1. **Setup**: Run `.specify/scripts/bash/check-prerequisites.sh --json` from repo root and parse JSON for REQUIREMENTS_DIR and AVAILABLE_DOCS. All paths must be absolute.

2. **Clarify intent**: Derive up to THREE contextual clarifying questions from the user's phrasing + signals from requirements.md. Questions MUST:
   - Be generated from user phrasing + extracted domain signals
   - Only ask about information that materially changes checklist content
   - Be skipped if already unambiguous in `$ARGUMENTS`
   - Follow archetypes: scope refinement, risk prioritization, depth calibration, audience framing, boundary exclusion, scenario class gap
   - Present options as compact table (Option | Candidate | Why It Matters)
   - Defaults: Depth=Standard, Audience=Reviewer, Focus=Top 2 relevance clusters

3. **Understand request**: Combine `$ARGUMENTS` + answers to derive checklist theme, consolidate must-have items, map to category scaffolding.

4. **Load feature context** from REQUIREMENTS_DIR:
   - requirements.md: Feature scope + Requirements (What) + acceptance criteria
   - plan.md (if exists): Specification context for gap-finding only
   - tasks.md (if exists): Specification decomposition for missing requirement detection only

5. **Generate checklist** — Create "Unit Tests for Requirements":
   - Create `REQUIREMENTS_DIR/checklists/` if needed
   - Use short descriptive filename: `[domain].md` (e.g., `ux.md`, `api.md`, `security.md`)
   - Number items sequentially from CHK001
   - Each run creates a NEW file (never overwrites existing)
   - Apply methodology from `.specify/shared/guidelines/checklist-methodology.md`:
     - Group by quality dimensions (Completeness, Clarity, Consistency, Measurability, Coverage, Edge Cases, Non-Functional, Dependencies, Ambiguities)
     - Each item: question format + quality dimension bracket + traceability reference
     - ≥80% items must include traceability (`[Req §X]`, `[Gap]`, `[Ambiguity]`, etc.)
     - Soft cap: 40 items max, prioritize by risk/impact
   - **PROHIBITED**: Items starting with "Verify/Test/Confirm/Check" + implementation behavior
   - **REQUIRED**: "Are [X] defined/specified?" / "Is [vague term] quantified?" patterns

6. **Structure**: Follow `.specify/templates/checklist-template.md` for canonical format. If unavailable: H1 title, purpose/meta, `##` category sections, `- [ ] CHK### <item>` lines.

7. **Report**: Output path, item count, focus areas, depth level, any user-specified items incorporated.

## Feature Integration

Apply [Feature Integration Protocol](.specify/shared/workflow/feature-integration.md). This command transitions status: `Implemented → Ready for Review` (if applicable).

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this command reached its wrap-up stage. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against `/speckit.checklist`'s declared purpose and produce a short review plus ≥1 concrete, command-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this command's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id` (e.g. the feature key + a run timestamp); if a nested skill/command already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "/speckit.checklist" --unit-type command \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Handoffs

**Before**: Run after requirements exist (ideally plan/tasks too) so checklist is grounded.

**After**: If items fail → iterate `/speckit.plan` or `/speckit.tasks`. Once satisfied → `/speckit.implement`.