<!-- AUTO-GENERATED from templates/commands/plan.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

You **MUST** analyze the user input in `$ARGUMENTS`, infer the user's intent, and use that intent to supplement missing context and guide the planning process.

The user input may include:

1. Special requests that require extra care or custom handling during the planning workflow.
2. Supplemental information that provides additional context or reference material.
3. Specific planning constraints, architectural preferences, or technical requirements that go beyond the default scope described in this document.

When processing the user input:

1. You **MUST** treat `$ARGUMENTS` as parameters for the current command.
2. Do **NOT** treat the input as a standalone instruction that overrides or replaces the command workflow.
3. If the input contains clear ambiguity, confusion, or likely misspellings that materially affect interpretation, stop and ask the user to rephrase the request with clearer wording. Provide brief guidance when possible.

## Glossary

Consult the project glossary (`.specify/memory/glossary.md`, ambient via the Documentation Map) and apply the protocol in `.specify/shared/workflow/glossary.md`:

- **Before acting on the user input**, map any recorded homophone/confusable variant to its canonical term (correcting voice/dictated input); surface each correction so the user can override it, and defer to the user on ambiguous variants.
- **At wrap-up**, propose any new project-specific terms (`origin=auto`, `status=proposed`), excluding common words; run conflict detection; non-conflicting new terms MUST be written directly and merged into the wrap-up report (non-blocking); only writes that conflict with or overwrite an existing user entry MUST still pause for user confirmation. User-authored entries are authoritative.

## Outline

1. **Setup**: Run `.specify/scripts/bash/create-new-plan.sh --json` from repo root and parse JSON for FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

2. **Analyze and process user input**: 
   - Read `$ARGUMENTS` content
   - Determine if it contains background information, planning outline, or specific constraints
   - Apply appropriate processing strategy based on content type
   - **Mid-run addenda**: input arriving after this run started is handled per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md) § Mid-Run Addendum Input — batched (never interleaved with plan filling), landed upstream first with the upstream gate re-run once for the whole batch, and recorded verbatim under `## Clarifications` (append-only). Apply that section; do not restate it here. **Plan-specific upstream artifact**: `requirements.md`. If an addendum expands or changes the requirement scope, do NOT plan against the stale spec — first restructure `requirements.md` (new/changed stories, FRs, success criteria), re-validate its checklist once, and only then fill the plan template. Plan artifacts are trustworthy only after that spec restructure has landed.

3. **Load context**: Read FEATURE_SPEC, `.specify/memory/constitution.md`, and processed `$ARGUMENTS` context. Load IMPL_PLAN template (already copied).
   - Check if `SPECS_DIR/research.md` exists. If so, read it.
   - **Crucial**: You MUST also read and analyze the project's **existing documentation** (`README.md`, `docs/`) and **feature memory** (`.specify/memory/`) to ensure the plan aligns with the system's architecture and evolution.

4. **Implement plan workflow**: Follow the structure in IMPL_PLAN template to:
   - **Fill the template in place**: replace every `[PLACEHOLDER]` token in the copied IMPL_PLAN. Do **NOT** append a second copy of the template below your filled content (a duplicated `# Implementation Plan:` block with leftover placeholder tokens is a defect).
   - Stamp the header line `**Requirement → Feature**: <REQUIREMENTS_KEY> → Feature <FEATURE_ID> <FEATURE_NAME>` so the requirement key and the bound feature ID are never confused, and reference the feature as `Feature <ID>` (never a bare number) throughout.
   - Fill Technical Context (mark unknowns as "NEEDS CLARIFICATION")
     - Incorporate relevant background information from `$ARGUMENTS`
     - Incorporate findings from `research.md` if available
   - Fill Constitution Check section by **dynamically deriving** the principle table from `.specify/memory/constitution.md`:
     1. Parse every heading matching `### <numeral>. <name>` (Roman or Arabic) in the order they appear.
     2. Preserve any `(NON-NEGOTIABLE)` / `(MANDATORY)` annotation verbatim in the row label.
     3. Emit one row in the Constitution Check table per principle — DO NOT use a hard-coded list, and DO NOT inherit stale principles left over from a previous spec's plan.md.
     4. Mark each row Pass / Fail / Partial based on the design artefacts (`requirements.md`, `data-model.md`, `contracts/`, `tasks.md`).
     5. Any Fail or Partial row MUST have a matching entry under Complexity Tracking with justification.
     - **Same-author detection delegation**: this command scores its own design twice — the Constitution Check rows above and the Post-Generation Quality Gate below — and in a `requirements → plan` chain without a break the artifacts being scored were written by this same agent, so self-review is weak evidence. When that condition holds, delegate the scoring to fresh-context read-only subagents per the canonical gate in `.specify/shared/workflow/objective-analysis-gate.md` (single source of truth; do not restate its rules here). This command's local parameter: a `Fail` or **Partial** row MUST name the downstream artifact it breaks — a compliance verdict that nothing inherits is Complexity Tracking noise, not a gate failure.
     - Include any additional constraints from `$ARGUMENTS`
   - Evaluate gates (ERROR if violations unjustified)
   - If `$ARGUMENTS` contains a planning outline:
     - Integrate the outline structure into the plan template
     - Ensure all required sections are properly filled
   - Phase 0: Resolve clarifications (refer to `research.md` or conduct analysis)
   - Phase 1: Generate data-model.md, contracts/, quickstart.md, feature-ref.md
     - **Summarize after, not before**: any Phase 1 summary written into plan.md (entity counts, contract counts, artifact lists) MUST be filled in AFTER the artifacts land on disk — pre-written counts routinely drift from the actual output and force a correction pass. The template carries a commented `## Phase 1: Design Artifacts Summary` placeholder section for exactly this backfill — fill it in place, never pre-write it. The same discipline reaches any **expected result** written next to a command in a Phase 1 artifact (exit code, verdict); the Post-Generation Quality Gate's execution-verify rule owns that requirement.
   - Re-evaluate Constitution Check post-design

5. **Plan integrity gate + stop and report**: Before finishing, verify the filled IMPL_PLAN contains (a) **no** residual `[UPPER_SNAKE_CASE]` placeholder tokens, (b) **exactly one** top-level `# Implementation Plan:` heading (no duplicated template body appended), and (c) the `**Requirement → Feature**` stamp. The template's self-referential **Note** line (the one mentioning `[PLACEHOLDER]` replacement) is REMOVED when filling — keeping it false-positives check (a). Fix the file if any check fails. Then report branch, IMPL_PLAN path, and generated artifacts.

## Feature Integration

The `/speckit.plan` command automatically integrates with the feature tracking system:

- If a `.specify/memory/features.md` file exists, the command will:
  - Detect the current feature directory (format: `.specify/specs/[REQUIREMENTS_KEY]/`)
  - Extract the feature ID from the directory name
  - Update the corresponding feature entry in `.specify/memory/features.md`:
    - **Bound-but-unregistered Feature**: if the spec's `Related Feature` names a Feature ID that has NO row yet in `features.md` (e.g. the binding was decided at `/speckit.clarify` but never registered), first CREATE the row and the `.specify/memory/features/<ID>.md` detail from `.specify/templates/feature-details-template.md` — then advance status. Do not leave the create-vs-advance branch implicit or skip registration because the ID is already written into the spec.
    - Advance status `Draft → Planned` per the canonical state machine in `.specify/templates/feature-details-template.md` § "Canonical Status State Machine". `/speckit.plan` MUST NOT land status `Implemented` — that transition is owned by `/speckit.implement`.
    - Keep the specification path unchanged
    - Update the "Last Updated" date
  - Automatically stage the changes to `.specify/memory/features.md` for git commit

In addition, **the plan phase MUST review the Feature list**:

- Check whether this plan introduces new Features or deprecates/merges existing Features.
- Ensure functional/non-functional Feature classification remains consistent.
- If there are changes, the following must be updated synchronously:
   - `.specify/memory/features/<ID>.md`
   - `.specify/memory/features.md`
- Record the "key changes / notes" corresponding to this plan in the Feature detail.

This integration ensures that all feature planning activities are properly tracked and linked to their corresponding entries in the project's feature index.

## Phases

### Phase 0: Research Review & Context

1. **Information Gathering** (summary-first — see `.specify/shared/guidelines/token-efficiency.md`):
   - **Project Docs**: consult `README.md` and pull `docs/` content as targeted excerpts for the areas this plan touches — do NOT read all files in `docs/` wholesale.
   - **Feature Memory**: project the feature index with `grep -E '^\| [0-9]{3}' .specify/memory/features.md` (ID/name/status rows) and read ONLY the detail file(s) of the bound/related Feature(s) under `.specify/memory/features/` — do NOT read the whole directory; escalate per the discipline doc's ladder when a row genuinely needs more depth.
   - **Codebase exploration pass**: before filling the template, run a dedicated exploration pass (use an Explore subagent when available) over the code the plan will touch — touchpoints, existing precedents, and downstream consumers. Use the findings to confirm or refute the spec's documented assumptions in one round rather than discovering them mid-design. **Subagent-unavailable fallback**: if the Agent/Explore dispatch fails twice in a row (upstream error), degrade to a bounded manual probe — grep for headings/symbols + targeted excerpt reads under the token-efficiency discipline — and note the degraded evidence path in the plan's Phase 0 section.
   - **Research Check**: Check if `research.md` exists in the local directory.
     - **If yes**: Read and analyze its contents. Use the Decisions and Rationale to resolve "NEEDS CLARIFICATION" items in the Technical Context.
     - **If no**: Perform sufficient analysis of project docs and memory to populate the Technical Context. If significant unknowns remain, ERROR and instruct the user to run `/speckit.research`.

2. **Refine Technical Context**:
   - Update the "Technical Context" section in the plan based on the gathered info and any `$ARGUMENTS`.
   - Ensure all key technical decisions (language, framework, storage, API style) are explicitly stated.
   - **Underdetermined design → interview, never fabricate**: when a key decision is not answerable from the spec, `research.md`, or the codebase because it is a **user preference or trade-off acceptance**, run the interview pattern (`.specify/shared/patterns/interview-pattern.md`) over the plan — ask the settled-prerequisite decisions in one round with recommended answers, write each answer into Technical Context before asking the next round. For a wide or deeply branching design space, hand off to `/speckit.interview` with `plan.md` as the target artifact instead of running an ad-hoc loop here. Silently inventing a design the user never chose is the failure this prevents.

**Output**: Updated IMPL_PLAN with technical context filled.

### Phase 1: Design & Contracts

**Prerequisites:** Technical Context defined and unknowns resolved.

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Record feature binding** → `feature-ref.md`: the bound Feature ID/name and how this plan maps to it (see the plan template's Project Structure).

**Output**: data-model.md, /contracts/*, quickstart.md, feature-ref.md (records the bound Feature ID/name and how this plan maps to it — see the plan template's Project Structure)

### Post-Generation Quality Gate: Contract Artifact Cleanup

After generating all Phase 1 artifacts (especially contract documents under `contracts/`), perform a mandatory review pass:

1. Scan each generated contract artifact for **internal deliberation markers** — phrases that indicate stream-of-consciousness reasoning leaked into the specification:
   - "Wait —", "Actually,", "On second thought", "Let me reconsider", "re-reading:", "Hmm,", "I think", "I realize", "To be clear:", "For the avoidance of doubt" (when followed by reasoning rather than a declarative statement)
2. For each instance found, **rewrite as a declarative statement**. Contract documents must read as specifications, not conversation transcripts. The reader should see conclusions, not the path to them.
3. Verify each contract artifact contains only:
   - Declarative interface definitions (inputs, outputs, constraints)
   - Normative rules (MUST, MUST NOT, SHOULD)
   - Concrete examples or schemas
   - No first-person reasoning, no self-correction prose, no exploratory narration
4. **Execution-verify emitted command examples**: every executable CLI example written into `quickstart.md` or `contracts/` MUST be either (a) executed once against the real tool during this phase, or (b) pinned by a contract test asserting its validity. Examples written from intent instead of code routinely drift from actual validators (flags, ID formats, argument grammars) and ship as broken documentation. **Declared expected results are part of the example**: an exit code, count, output value, or pass/fail verdict written next to a command MUST be verified by the same route (a) or (b) — a command that runs is not evidence that its stated expected result holds. Pre-written expectations collide with the live baseline (a check that exits non-zero on drift predating this spec), and the collision surfaces only for whoever runs it next. A **file-level** disclaimer ("this component is not implemented yet, so the examples below cannot be executed") does NOT discharge this rule for the examples it does not cover — it silently vouches for them. Scope any disclaimer **per example**, and for route (b) name exactly which examples the contract test pins. Where an example depends on a multi-step pipeline, show every step: a scenario that omits a required step is wrong even when each command it does show works. (Observed in practice: a quickstart disclaimed only its not-yet-implemented engine examples, which implicitly vouched for a `specify init` example that was never executed and was wrong — it assumed init creates the agent instruction symlinks, which it does not.)

## Key rules

- Use absolute paths
- ERROR on gate failures or unresolved clarifications

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.plan" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Documentation

At the same wrap-up point as the Feedback step, apply the docs-sync evaluation per the canonical convention in `.specify/shared/workflow/docs-step.md`: assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space, and conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`. Never block wrap-up; incremental judgment only (no full reconcile sweep); when a move/archive-level change is needed, recommend running `/speckit.docs` instead of executing it here.

## Artifact Commit

At wrap-up, **before** the Feedback and Documentation steps, commit the artifact this command produced — and only that artifact, staged by explicit path. Follow the canonical convention in `.specify/shared/workflow/artifact-commit-step.md`: run the deletion-surface audit first, use a single-line message per `.specify/templates/commit-template.md`, never `git add -A`, and never fold another command's uncommitted artifacts into this commit (report that as an upstream deviation instead). A read-only run that produced no artifact skips this step and says so in one line rather than creating an empty commit. Committing here does not advance the feature's lifecycle status and does not push.

## Handoffs

**Before running this command**:

- Ensure `/speckit.requirements` has produced a requirements specification.
- If `requirements.md` contains any `[NEEDS CLARIFICATION]`, run `/speckit.clarify` first.

**After running this command**:

- Typically run `/speckit.tasks` to decompose the plan into an executable task list.
- Optionally run `/speckit.checklist` to introduce domain-specific quality gates before implementation.