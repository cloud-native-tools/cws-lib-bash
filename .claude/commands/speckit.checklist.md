<!-- AUTO-GENERATED from templates/commands/checklist.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
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

**Same-author detection delegation**: the checklist is an audit instrument for a spec this same agent usually just wrote, so it inherits the author's blind spots — the gaps the spec never mentions are largely the gaps the author never thought of while writing it, and a re-read by that author reproduces the same reading. When that condition holds, derive the gap-finding pass from fresh-context read-only subagents. Apply the canonical gate in `.specify/shared/workflow/objective-analysis-gate.md` (single source of truth; do not restate its rules here). This command has no severity tiers; its local analogue of the propagation-surface cap is the traceability rule step 5 already states — a **CHK** item carries the requirement or gap it guards, so an item guarding nothing is visible as untraceable instead of passing as coverage.

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

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.checklist" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Handoffs

**Before**: Run after requirements exist (ideally plan/tasks too) so checklist is grounded.

**After**: If items fail → iterate `/speckit.plan` or `/speckit.tasks`. Once satisfied → `/speckit.implement`.