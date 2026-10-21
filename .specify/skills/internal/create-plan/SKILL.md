---
name: create-plan
description: Fill a validated requirements spec into the implementation planning artifacts — run the plan setup script, load spec + constitution + research context, fill the plan template in place with a dynamically derived Constitution Check table, generate the Phase 1 design artifacts (data-model.md, contracts/, quickstart.md, feature-ref.md), clean the contract artifacts through the post-generation quality gate, and advance the feature tracking system (Draft → Planned). Use this when the user mentions ["create plan", "implementation plan", "generate plan", "fill plan", "plan template", "constitution check", "design artifacts", "生成实现规划", "实现规划", "规划产物", "设计产物", "实现计划", "填充计划"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/create-plan/SKILL.md>"
---

# create-plan

## Goal

Turn a validated requirements specification into the implementation planning artifact set:
one in-place-filled `plan.md` plus its Phase 1 design artifacts (`data-model.md`,
`contracts/`, `quickstart.md`, `feature-ref.md`), with the Constitution Check table
**dynamically derived** from the project constitution and the feature tracking system
advanced to match. This skill owns the executable core of `/speckit.plan` — Outline steps
1–5, Phase 0/1, Feature Integration, the Post-Generation Quality Gate, and the
"Summarize after, not before" discipline — while the command template keeps entry, the
`scripts:` block, the User Input Protocol, and the wrap-up lifecycle (Feedback /
Documentation / Artifact Commit / Handoffs).

Canonical extraction source: `.specify/templates/commands/plan.md` § Outline (steps 1–5), § Feature
Integration, § Phases (Phase 0 / Phase 1), and § Post-Generation Quality Gate. Content
moved here verbatim in substance.

## Input Contract

- **Upstream artifact**: a requirements specification (`requirements.md`) must exist and
  contain no unresolved `[NEEDS CLARIFICATION]` markers — if any remain, the planning run
  does not start (the command's Handoffs surface the prerequisite command; this skill
  fails fast on a stale or ambiguous spec).
- **Setup variables**: FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH come from the command's
  `{SCRIPT}` prerequisite run (its `scripts:` entry resolves to
  `.specify/scripts/bash/create-new-plan.sh --json`, run from repo root); all paths used below are
  absolute.
- **User parameters**: arrive already processed by the command's User Input Protocol
  (parameters for the run, never a standalone instruction overriding the workflow); this
  skill still classifies their content type per Workflow step 2.

## Workflow (Outline steps 1–5)

### Step 1 — Setup

Run `{SCRIPT}` from repo root and parse JSON for FEATURE_SPEC, IMPL_PLAN, SPECS_DIR,
BRANCH. For single quotes in args like "I'm Groot", use escape syntax: e.g
`'I'\''m Groot'` (or double-quote if possible: `"I'm Groot"`).

### Step 2 — Analyze and process user input

- Read `$ARGUMENTS` content.
- Determine whether it contains background information, a planning outline, or specific
  constraints.
- Apply the appropriate processing strategy based on content type.
- **Mid-run addenda**: input arriving after this run started is handled per the
  [User Input Protocol](.specify/shared/workflow/user-input-protocol.md) § Mid-Run
  Addendum Input — batched (never interleaved with plan filling), landed upstream first
  with the upstream gate re-run once for the whole batch, and recorded verbatim under
  `## Clarifications` (append-only). Apply that section; do not restate it here.
  **Plan-specific upstream artifact**: `requirements.md`. If an addendum expands or
  changes the requirement scope, do NOT plan against the stale spec — first restructure
  `requirements.md` (new/changed stories, FRs, success criteria), re-validate its
  checklist once, and only then fill the plan template. Plan artifacts are trustworthy
  only after that spec restructure has landed.

### Step 3 — Load context

Read FEATURE_SPEC, `.specify/memory/constitution.md`, and processed `$ARGUMENTS` context.
Load the IMPL_PLAN template (already copied).

- Check if `SPECS_DIR/research.md` exists. If so, read it.
- **Crucial**: also read and analyze the project's **existing documentation**
  (`README.md`, `docs/`) and **feature memory** (`.specify/memory/`) to ensure the plan
  aligns with the system's architecture and evolution.

### Step 4 — Implement plan workflow

Follow the structure in the IMPL_PLAN template to:

- **Fill the template in place**: replace every `[PLACEHOLDER]` token in the copied
  IMPL_PLAN. Do **NOT** append a second copy of the template below the filled content (a
  duplicated `# Implementation Plan:` block with leftover placeholder tokens is a defect).
- Stamp the header line
  `**Requirement → Feature**: <REQUIREMENTS_KEY> → Feature <FEATURE_ID> <FEATURE_NAME>`
  so the requirement key and the bound feature ID are never confused, and reference the
  feature as `Feature <ID>` (never a bare number) throughout.
- Fill Technical Context (mark unknowns as "NEEDS CLARIFICATION")
  - Incorporate relevant background information from `$ARGUMENTS`
  - Incorporate findings from `research.md` if available
- Fill Constitution Check section by **dynamically deriving** the principle table from
  `.specify/memory/constitution.md`:
  1. Parse every heading matching `### <numeral>. <name>` (Roman or Arabic) in the order
     they appear.
  2. Preserve any `(NON-NEGOTIABLE)` / `(MANDATORY)` annotation verbatim in the row
     label.
  3. Emit one row in the Constitution Check table per principle — DO NOT use a hard-coded
     list, and DO NOT inherit stale principles left over from a previous spec's plan.md.
  4. Mark each row Pass / Fail / Partial based on the design artefacts
     (`requirements.md`, `data-model.md`, `contracts/`, `tasks.md`).
  5. Any Fail or Partial row MUST have a matching entry under Complexity Tracking with
     justification.
- **Same-author detection delegation**: this planning run scores its own design twice —
  the Constitution Check rows above and the Post-Generation Quality Gate below — and in a
  `requirements → plan` chain without a break the artifacts being scored were written by
  this same agent, so self-review is weak evidence. When that condition holds, delegate
  the scoring to fresh-context read-only subagents per the canonical gate in
  `.specify/shared/workflow/objective-analysis-gate.md` (single source of truth; do not
  restate its rules here). This skill's local parameter: a `Fail` or **Partial** row MUST
  name the downstream artifact it breaks — a compliance verdict that nothing inherits is
  Complexity Tracking noise, not a gate failure.
- Include any additional constraints from `$ARGUMENTS`
- Evaluate gates (ERROR if violations unjustified)
- If `$ARGUMENTS` contains a planning outline:
  - Integrate the outline structure into the plan template
  - Ensure all required sections are properly filled
- Phase 0: Resolve clarifications (refer to `research.md` or conduct analysis) — see
  § Phase 0 below.
- Phase 1: Generate data-model.md, contracts/, quickstart.md, feature-ref.md — see
  § Phase 1 below.
  - **Summarize after, not before**: any Phase 1 summary written into plan.md (entity
    counts, contract counts, artifact lists) MUST be filled in AFTER the artifacts land
    on disk — pre-written counts routinely drift from the actual output and force a
    correction pass. The template carries a commented `## Phase 1: Design Artifacts Summary` placeholder
    section for exactly this backfill — fill it in place, never
    pre-write it. The same discipline reaches any **expected result** written next to a
    command in a Phase 1 artifact (exit code, verdict); the Post-Generation Quality
    Gate's execution-verify rule owns that requirement.
- Re-evaluate Constitution Check post-design

### Step 5 — Plan integrity gate + stop and report

Before finishing, verify the filled IMPL_PLAN contains (a) **no** residual
`[UPPER_SNAKE_CASE]` placeholder tokens, (b) **exactly one** top-level
`# Implementation Plan:` heading (no duplicated template body appended), and (c) the
`**Requirement → Feature**` stamp. The template's self-referential **Note** line (the one
mentioning `[PLACEHOLDER]` replacement) is REMOVED when filling — keeping it
false-positives check (a). Fix the file if any check fails. Then report branch, IMPL_PLAN
path, and generated artifacts.

## Feature Integration

The `/speckit.plan` command automatically integrates with the feature tracking system:

- If a `.specify/memory/features.md` file exists, this skill will:
  - Detect the current feature directory (format: `.specify/specs/[REQUIREMENTS_KEY]/`)
  - Extract the feature ID from the directory name
  - Update the corresponding feature entry in `.specify/memory/features.md`:
    - **Bound-but-unregistered Feature**: if the spec's `Related Feature` names a Feature
      ID that has NO row yet in `features.md` (e.g. the binding was decided at
      `/speckit.clarify` but never registered), first CREATE the row and the
      `.specify/memory/features/<ID>.md` detail from
      `.specify/templates/feature-details-template.md` — then advance status. Do not
      leave the create-vs-advance branch implicit or skip registration because the ID is
      already written into the spec.
    - Advance status `Draft → Planned` per the canonical state machine in
      `.specify/templates/feature-details-template.md` § "Canonical Status State
      Machine". The plan phase MUST NOT land status `Implemented` — that transition is
      owned by `/speckit.implement`.
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

This integration ensures that all feature planning activities are properly tracked and
linked to their corresponding entries in the project's feature index.

## Phase 0: Research Review & Context

1. **Information Gathering** (summary-first — see
   `.specify/shared/guidelines/token-efficiency.md`):
   - **Project Docs**: consult `README.md` and pull `docs/` content as targeted excerpts
     for the areas this plan touches — do NOT read all files in `docs/` wholesale.
   - **Feature Memory**: project the feature index with
     `grep -E '^\| [0-9]{3}' .specify/memory/features.md` (ID/name/status rows) and read
     ONLY the detail file(s) of the bound/related Feature(s) under
     `.specify/memory/features/` — do NOT read the whole directory; escalate per the
     discipline doc's ladder when a row genuinely needs more depth.
   - **Codebase exploration pass**: before filling the template, run a dedicated
     exploration pass (use an Explore subagent when available) over the code the plan
     will touch — touchpoints, existing precedents, and downstream consumers. Use the
     findings to confirm or refute the spec's documented assumptions in one round rather
     than discovering them mid-design. **Subagent-unavailable fallback**: if the
     Agent/Explore dispatch fails twice in a row (upstream error), degrade to a bounded
     manual probe — grep for headings/symbols + targeted excerpt reads under the
     token-efficiency discipline — and note the degraded evidence path in the plan's
     Phase 0 section.
   - **Research Check**: Check if `research.md` exists in the local directory.
     - **If yes**: Read and analyze its contents. Use the Decisions and Rationale to
       resolve "NEEDS CLARIFICATION" items in the Technical Context.
     - **If no**: Perform sufficient analysis of project docs and memory to populate the
       Technical Context. If significant unknowns remain, ERROR and instruct the user to
       run `/speckit.research`.

2. **Refine Technical Context**:
   - Update the "Technical Context" section in the plan based on the gathered info and
     any `$ARGUMENTS`.
   - Ensure all key technical decisions (language, framework, storage, API style) are
     explicitly stated.
   - **Underdetermined design → interview, never fabricate**: when a key decision is not
     answerable from the spec, `research.md`, or the codebase because it is a **user
     preference or trade-off acceptance**, run the interview pattern
     (`.specify/shared/patterns/interview-pattern.md`) over the plan — ask the
     settled-prerequisite decisions in one round with recommended answers, write each
     answer into Technical Context before asking the next round. For a wide or deeply
     branching design space, hand off to `/speckit.interview` with `plan.md` as the
     target artifact instead of running an ad-hoc loop here. Silently inventing a design
     the user never chose is the failure this prevents.

**Output**: Updated IMPL_PLAN with technical context filled.

## Phase 1: Design & Contracts

**Prerequisites:** Technical Context defined and unknowns resolved.

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Record feature binding** → `feature-ref.md`: the bound Feature ID/name and how this
   plan maps to it (see the plan template's Project Structure —
   `.specify/templates/plan-template.md`).

**Output**: data-model.md, /contracts/*, quickstart.md, feature-ref.md (records the bound
Feature ID/name and how this plan maps to it — see the plan template's Project Structure,
`.specify/templates/plan-template.md`)

## Post-Generation Quality Gate: Contract Artifact Cleanup

After generating all Phase 1 artifacts (especially contract documents under
`contracts/`), perform a mandatory review pass:

1. Scan each generated contract artifact for **internal deliberation markers** — phrases
   that indicate stream-of-consciousness reasoning leaked into the specification:
   - "Wait —", "Actually,", "On second thought", "Let me reconsider", "re-reading:",
     "Hmm,", "I think", "I realize", "To be clear:", "For the avoidance of doubt" (when
     followed by reasoning rather than a declarative statement)
2. For each instance found, **rewrite as a declarative statement**. Contract documents
   must read as specifications, not conversation transcripts. The reader should see
   conclusions, not the path to them.
3. Verify each contract artifact contains only:
   - Declarative interface definitions (inputs, outputs, constraints)
   - Normative rules (MUST, MUST NOT, SHOULD)
   - Concrete examples or schemas
   - No first-person reasoning, no self-correction prose, no exploratory narration
4. **Execution-verify emitted command examples**: every executable CLI example written
   into **any artifact this run produces** — `plan.md` itself (its
   `## Phase 1: Design Artifacts Summary` counts and its *Mirror Obligations* `Verify`
   column included), `quickstart.md`, `contracts/`, `data-model.md`, `feature-ref.md` — MUST be either (a)
   executed once against the real tool during this phase, or (b) pinned by a contract
   test asserting its validity. Scope is the whole artifact set, not a named subset: an
   unlisted artifact is where an unrun command survives, and a command that is too broad
   or simply wrong is caught by nobody. Examples written from intent instead of code
   routinely drift from actual validators (flags, ID formats, argument grammars) and ship
   as broken documentation. **Declared expected results are part of the example**: an
   exit code, count, output value, or pass/fail verdict written next to a command MUST be
   verified by the same route (a) or (b) — a command that runs is not evidence that its
   stated expected result holds. Pre-written expectations collide with the live baseline
   (a check that exits non-zero on drift predating this spec), and the collision surfaces
   only for whoever runs it next. A **file-level** disclaimer ("this component is not
   implemented yet, so the examples below cannot be executed") does NOT discharge this
   rule for the examples it does not cover — it silently vouches for them. Scope any
   disclaimer **per example**, and for route (b) name exactly which examples the contract
   test pins. **A disclaimer MUST also list the premises that example rests on** — the
   assumed flags, ID forms, counts, file locations, or tool behaviors it was written
   against — because discharging the run obligation without naming the premises hands the
   next phase a claim it cannot re-probe; the premise list is what tells `/speckit.tasks`
   and `/speckit.implement` which facts to re-measure instead of inherit. Where an
   example depends on a multi-step pipeline, show every step: a scenario that omits a
   required step is wrong even when each command it does show works. **Teardown is
   verified to the same standard as setup**: in a multi-step scenario, actually run the
   cleanup/teardown steps too — an unrun teardown ships a scenario that leaves state
   behind, so the second run fails on the first. When a cleanup step invokes an engine
   action, check that action's parameter preconditions BEFORE writing the step (required
   arguments, store state the action expects to exist), not after it errors at run time.
   (Observed in practice: a quickstart disclaimed only its not-yet-implemented engine
   examples, which implicitly vouched for a `specify init` example that was never
   executed and was wrong — it assumed init creates the agent instruction symlinks, which
   it does not.)

## Key rules

- Use absolute paths
- ERROR on gate failures or unresolved clarifications

## Boundaries

- **Entry & lifecycle stay in the command template** `/speckit.plan`: the AUTO-GENERATED
  header, the `scripts:` block, the User Input Protocol, the Glossary protocol step,
  `## Feedback`, `## Documentation`, `## Artifact Commit`, and `## Handoffs`
  (before/after command sequencing and next-command suggestions) are command surfaces,
  not skill content.
- **Templates and shared conventions stay pointers**: the plan template being filled is
  referenced via IMPL_PLAN (`.specify/templates/plan-template.md`); the feature status state
  machine is owned by `.specify/templates/feature-details-template.md`; the mid-run
  addendum protocol by `.specify/shared/workflow/user-input-protocol.md`; the
  same-author delegation gate by `.specify/shared/workflow/objective-analysis-gate.md`;
  the interview pattern by `.specify/shared/patterns/interview-pattern.md`. Never copy
  their text here.
- **Status ceiling**: this skill advances a feature at most to `Planned`; the
  `Implemented` transition belongs to `/speckit.implement` (see Feature Integration).

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:create-plan" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:create-plan" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:create-plan" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
