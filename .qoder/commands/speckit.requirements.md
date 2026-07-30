## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). The text after `/speckit.requirements` IS the feature description.

## Glossary

Consult the project glossary (`.specify/memory/glossary.md`, ambient via the Documentation Map) and apply the protocol in `.specify/shared/workflow/glossary.md`:

- **Before acting on the user input**, map any recorded homophone/confusable variant to its canonical term (correcting voice/dictated input); surface each correction so the user can override it, and defer to the user on ambiguous variants.
- **At wrap-up**, propose any new project-specific terms (`origin=auto`, `status=proposed`), excluding common words; run conflict detection and obtain explicit user confirmation before writing. User-authored entries are authoritative.

## Outline

1. **Generate short name** (2-4 words, action-noun format, e.g., "user-auth", "fix-payment-timeout").

2. **Check existing branches**:
   - `git fetch --all --prune`
   - Find highest number across: remote branches, local branches, specs directories matching `[0-9]+-<short-name>`
   - Next number = highest + 1 (or 1 if none found)

3. **Run script** `
```bash
cat << 'EOF' | .specify/scripts/bash/create-new-requirements.sh --json --short-name "<SHORT_NAME>"
$ARGUMENTS
EOF
```
` from repo root (replace `<SHORT_NAME>`). Parse JSON for BRANCH_NAME and SPEC_FILE. Run only once.

4. **Load** `.specify/templates/requirements-template.md` for required sections.

5. **Execute spec generation**:
   1. Parse user description. If empty: ERROR. **Conceptual/idea-level input** (long-form essays, methodology explanations, advocacy material): first distill it into landable requirement slices — identify the landing level(s) the material maps to (e.g. the framework/tool itself vs. the downstream projects adopting it) and draft stories for each level separately, instead of transcribing the material's own structure into the spec.
   2. Extract key concepts: actors, actions, data, constraints.
   3. Initialize `Related Feature`: `Feature ID: Need clarification`, `Feature Name: Need clarification` (resolved by `/speckit.clarify`).
   4. **Peek at house conventions**: skim the highest-numbered existing spec under `.specify/specs/` before drafting — match its language, section conventions (e.g. Assumptions subsection), and Shared Strings usage. Aligning with the most recent merged spec reduces convention drift at zero clarification cost.
   5. **Reserved identifier check**: if the spec names any new identifier (env var, macro, CLI flag, config key), grep the codebase for that name before drafting — a collision with an existing/reserved identifier (e.g. a build env var) must be surfaced with a proposed alternate name and an explicit user-override note, not silently adopted.
   6. **Port/integration input hygiene**: when the feature ports or integrates an external codebase, (a) treat the upstream's docs/roadmap as claims and verify capability statements against its **source code** before they shape story priorities (docs routinely lag code); (b) write any fact still pending async verification (inventory sizes, entry counts, platform matrices) in "dynamically probed at runtime" phrasing from the first draft — hard-coded point-in-time numbers force multi-section rewrites when verification returns.
   7. For unclear aspects: make informed guesses. Only use `[NEEDS CLARIFICATION: question]` if choice significantly impacts scope/UX, multiple interpretations exist, and no reasonable default. **Max 3 markers.**
   8. Fill User Scenarios & Testing — write as many stories as the feature decomposes into (the template's three slots are open-ended scaffolding, not a quota; delete unused slots).
   9. Generate testable Functional Requirements.
   10. Define measurable, technology-agnostic Success Criteria.
   11. Identify Key Entities (if data involved).

6. **Write spec** to SPEC_FILE. Preserve section order. Keep `Related Feature` with default "Need clarification" values.

7. **Quality Validation**: Follow the validation process in `.specify/shared/guidelines/requirements-guidelines.md`:
   - Create checklist at `FEATURE_DIR/checklists/requirements.md`
   - Validate spec against each item
   - Handle failures (max 3 iterations) and remaining clarifications (max 3 questions with table format)
   - Update checklist with pass/fail status

8. **Report**: Branch name, spec file path, checklist results, next phase readiness.

## Feature Integration

Apply [Feature Integration Protocol](.specify/shared/workflow/feature-integration.md) § Feature Binding Rules for lookup rules and integration responsibilities. **Binding timing**: this command does NOT create or bind Features itself — it always initializes `Related Feature` with `Need clarification` values (Outline steps 3/6) and defers the actual Feature lookup/creation/binding to the `/speckit.clarify` checkpoint, where the Binding Rules are applied.

## Guidelines

For detailed quality validation, success criteria guidelines, and AI generation best practices, see `.specify/shared/guidelines/requirements-guidelines.md`.

Key rules:
- Focus on WHAT and WHY, not HOW
- Written for business stakeholders
- No embedded checklists (separate command)
- Max 3 [NEEDS CLARIFICATION] markers

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this command reached its wrap-up stage. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against `/speckit.requirements`'s declared purpose and produce a short review plus ≥1 concrete, command-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this command's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id` (e.g. the feature key + a run timestamp); if a nested skill/command already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "/speckit.requirements" --unit-type command \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Handoffs

**Before**: Optional `/speckit.feature` to ensure feature registry is up to date.

**After**: If spec has `[NEEDS CLARIFICATION]` or `Related Feature: Need clarification` → `/speckit.clarify`. Otherwise → `/speckit.plan`.