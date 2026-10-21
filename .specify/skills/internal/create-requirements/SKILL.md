---
name: create-requirements
description: Create or update the feature's requirements specification (requirements.md) from a natural language feature description — derive the short name and the next spec branch number (including the archived-spec and slash-namespace remote-branch numbering pitfalls), scaffold the spec via the creation script, run the bounded generation pass (concept-owner check, reserved-identifier check, port/integration input hygiene, max-3 clarification markers), then run the deterministic validator FIRST and present its output verbatim before any checklist work starts. Use this when the user mentions ["requirements", "requirements.md", "创建需求", "需求文档", "需求规格", "写需求", "write spec", "create spec", "new feature spec", "user stories", "用户故事", "spec 生成", "需求说明"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/create-requirements/SKILL.md>"
---

# create-requirements

## Goal

Create or update the Requirements from a natural language feature description: one
`requirements.md` under the feature's spec directory, branch-numbered against the live
numbering space, aligned with house conventions, and validated by the deterministic
checker before anything downstream may start.

Owning command: `/speckit.requirements`. Canonical extraction source:
`.specify/templates/commands/requirements.md` § Outline 1–8 (short-name derivation, branch-number
derivation, execution steps 5.1–5.12, quality validation) plus § Glossary, § Feature
Integration and § Guidelines. Content moved here verbatim in substance; the command
template keeps entry, input wiring, and lifecycle delegation only.

## Input Contract

- **Input**: the text after the command IS the feature description — the command's
  `$ARGUMENTS`. It may be a one-line idea or long-form material (see step 5.1). The
  command template owns the User Input wiring.
- **Glossary anchoring (runs first)**: apply the glossary protocol in
  `.specify/shared/workflow/glossary.md`, reading the project glossary at
  `.specify/memory/glossary.md` (ambient via the Documentation Map). That file owns
  every rule of this step — input correction and anchoring, progressive enrichment at
  wrap-up, conflict detection, manual edits and user precedence — and this skill
  restates none of them. Step 5.5's concept-name handling leans on the file's
  constraint-side reading of a registered term.

## Workflow

### 1. Generate short name

2–4 words, action-noun format, e.g. `user-auth`, `fix-payment-timeout`.

### 2. Derive the next branch number

- `git fetch --all --prune`
- Derive the next number from `.specify/specs/` directories (**INCLUDING
  `.specify/specs/.archive/`** — archived specs keep their numbers and a globally-max
  archived number would otherwise collide) plus branch names in the exact top-level
  `<NNN>-<slug>` form ONLY.
- **Slash-namespaced remote branches are NOT spec numbering** (e.g.
  `origin/community/4059-*`, `origin/fix/4198-*`): their trailing digits must be
  excluded, or the next number gets inflated (e.g. 200 instead of 045).
- Next number = highest + 1 (or 1 if none found).

### 3. Scaffold the spec

Run the command's declared script — the `{SCRIPT}` slot:
`.specify/scripts/bash/create-new-requirements.sh --json --short-name "<SHORT_NAME>"`
with the feature description piped on stdin — from repo root. Parse JSON for
`BRANCH_NAME` and `SPEC_FILE`. **Run only once.**

Note: the script **pre-creates SPEC_FILE** with template placeholder content — you MUST
`Read` it before writing (or overwrite via `Edit`); a blind `Write` fails with "File has
not been read yet".

### 4. Load the template

Load `.specify/templates/requirements-template.md` for the required sections.

### 5. Execute spec generation

1. **Parse user description.** If empty: ERROR. **Conceptual/idea-level input**
   (long-form essays, methodology explanations, advocacy material): first distill it
   into landable requirement slices — identify the landing level(s) the material maps
   to (e.g. the framework/tool itself vs. the downstream projects adopting it) and
   draft stories for each level separately, instead of transcribing the material's own
   structure into the spec.
2. **Extract key concepts**: actors, actions, data, constraints.
3. **Initialize `Related Feature`**: `Feature ID: Need clarification`,
   `Feature Name: Need clarification` (resolved by `/speckit.clarify`).
4. **Peek at house conventions (bounded, summary-first)**: sample the highest-numbered
   existing spec directory under `.specify/specs/<NNN>-<slug>/` and read its
   **`requirements.md`** — the same artifact filename this skill writes (SPEC_FILE,
   step 3), and the same one `.specify/templates/requirements-template.md` scaffolds — with
   targeted excerpts: heading structure (`grep -n '^#'`), one user story, a few FR/SC
   lines, instead of reading the whole spec (see
   `.specify/shared/guidelines/token-efficiency.md`). Match its language, section
   conventions (e.g. Assumptions subsection), and Shared Strings usage. Aligning with
   the most recent merged spec reduces convention drift at zero clarification cost.
5. **Concept-owner check**: when a requirement introduces, constrains, or redefines a
   concept the framework already defines, locate that concept's owner document under
   `.specify/shared/definitions/` **before drafting** and write to the owner's
   definition — not to recall of it, and not to a paraphrase from training knowledge. A
   concept with no locatable owner is a **new** concept: say so in the spec instead of
   defining it inline. Concept *names* additionally go through the glossary's
   constraint-side reading — the command template's `## Glossary` step, carried in this
   skill as § Input Contract → Glossary anchoring above.
6. **Reserved identifier check**: if the spec names any new identifier (env var, macro,
   CLI flag, config key), grep the codebase for that name before drafting — a collision
   with an existing/reserved identifier (e.g. a build env var) must be surfaced with a
   proposed alternate name and an explicit user-override note, not silently adopted.
7. **Port/integration input hygiene**: when the feature ports or integrates an external
   codebase, (a) treat the upstream's docs/roadmap as claims and verify capability
   statements against its **source code** before they shape story priorities (docs
   routinely lag code); (b) write any fact still pending async verification (inventory
   sizes, entry counts, platform matrices) in "dynamically probed at runtime" phrasing
   from the first draft — hard-coded point-in-time numbers force multi-section rewrites
   when verification returns.
8. **Unclear aspects**: make informed guesses. Only use `[NEEDS CLARIFICATION: question]`
   if the choice significantly impacts scope/UX, multiple interpretations exist, and no
   reasonable default. **Max 3 markers.**
9. **Fill User Scenarios & Testing** — write as many stories as the feature decomposes
   into (the template's three slots are open-ended scaffolding, not a quota; delete
   unused slots).
10. **Generate testable Functional Requirements.**
11. **Define measurable, technology-agnostic Success Criteria.**
12. **Identify Key Entities** (if data involved).

### 6. Write the spec

Write the spec to SPEC_FILE. Preserve section order. Keep `Related Feature` with its
default values (`Related Feature: Need clarification`) — binding is not this run's job.

### 7. Quality validation (checker FIRST, checklist postponed)

Run the deterministic checker FIRST — `python3 .specify/scripts/python/validate-requirements.py SPEC_FILE` — and present its output **verbatim** (do not paraphrase or condense it). If
it reports any ERROR, **STOP** and fix the spec, re-running until it exits 0: the
checklist and the clarification loop both come after, and neither may start while an
ERROR stands.

Then follow the validation process in `.specify/shared/guidelines/requirements-guidelines.md`:

- Create checklist at `FEATURE_DIR/checklists/requirements.md`
- Validate spec against each item
- Handle failures (max 3 iterations) and remaining clarifications (max 3 questions with
  table format)
- Update checklist with pass/fail status **after** the clarification write-back — every
  count and reference resolution the checklist records derives from a checker run, never
  hand-typed, so re-run the checker once the write-back has landed

### 8. Report

Branch name, spec file path, checklist results, next phase readiness.

## Feature Integration

Apply the Feature Integration Protocol (`.specify/shared/workflow/feature-integration.md`)
§ Feature Binding Rules for lookup rules and integration responsibilities. **Binding
timing**: this skill does NOT create or bind Features itself — it always initializes
`Related Feature` with `Need clarification` values (steps 5.3/6) and defers the actual
Feature lookup/creation/binding to the `/speckit.clarify` checkpoint, where the Binding
Rules are applied.

## Generation guidelines

For detailed quality validation, success criteria guidelines (including the reader
baseline these artifacts are written for), and AI generation best practices, see
`.specify/shared/guidelines/requirements-guidelines.md`.

Key rules:
- Focus on WHAT and WHY, not HOW
- No embedded checklists (separate command)
- Max 3 [NEEDS CLARIFICATION] markers

## Boundaries

- **Command-level wiring stays with `/speckit.requirements`.** The command frontmatter
  (`scripts:` slot), the User Input step, and the wrap-up lifecycle (Artifact Commit,
  Feedback, Documentation, Handoffs, next-command suggestions) are owned by the command
  template, not absorbed here.
- **Requirements-quality checklist generation is not this skill.** The standalone
  `/speckit.checklist` instrument (CHK items, quality dimensions) is the
  `create-checklist` skill; step 7's checklist pass here validates the freshly written
  spec per `requirements-guidelines.md`.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:create-requirements" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:create-requirements" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:create-requirements" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
