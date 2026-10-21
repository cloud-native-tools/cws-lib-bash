---
name: create-checklist
description: Generate a requirements-quality checklist for the current feature — "unit tests for requirements writing" that validate the quality, clarity and completeness of requirements rather than implementation behaviour. Produces a NEW dated checklist file under the requirements directory, items numbered from CHK001 in question form, grouped by quality dimension, ≥80% traceable to a requirement or an explicit gap, soft-capped at 40. Use this when the user mentions ["checklist", "requirements checklist", "质量检查清单", "需求质量", "CHK", "unit tests for english", "spec quality gate", "需求验收清单", "quality dimensions"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/create-checklist/SKILL.md>"
---

# create-checklist

## Goal

Produce a **requirements-quality checklist** for the current feature: an instrument that
tests the *specification*, not the implementation. Every item is a question about whether
something is defined, specified, bounded or quantified — so that answering it is a
judgement about the requirement text, never a run of the product.

Canonical extraction source: `.specify/templates/commands/checklist.md` § Checklist Purpose and
§ Execution Steps 1–7. The command template keeps entry + delegation only.

## Input Contract

- **Argument handling**: `$ARGUMENTS` are **command parameters**, not standalone
  instructions. They may pre-answer the intent-clarification step; when they already make a
  dimension unambiguous, do not re-ask it.
- **Prerequisite**: run the command's declared prerequisite script from repo root and parse
  its JSON for `REQUIREMENTS_DIR` and `AVAILABLE_DOCS`. **All paths must be absolute.**
- **Methodology owner**: `.specify/shared/guidelines/checklist-methodology.md` holds the
  detailed methodology, examples, anti-examples and quality-dimension patterns — read it;
  do not restate it here.

## The purpose, stated once

Checklists are **UNIT TESTS FOR REQUIREMENTS WRITING**. They validate quality, clarity and
completeness of the requirements. They are **NOT** implementation verification, and an item
that could only be answered by running code is a defect in the checklist.

## Workflow

### 1. Setup

Run the prerequisite script; derive `REQUIREMENTS_DIR` and `AVAILABLE_DOCS` as absolute
paths.

### 2. Clarify intent

Derive **up to three** contextual clarifying questions from the user's phrasing plus signals
extracted from `requirements.md`. Questions MUST:

- be generated from the user phrasing + extracted domain signals;
- ask only about information that **materially changes checklist content**;
- be **skipped** when `$ARGUMENTS` already makes them unambiguous;
- follow the archetypes: *scope refinement · risk prioritization · depth calibration ·
  audience framing · boundary exclusion · scenario class gap*;
- be presented as a compact table (Option | Candidate | Why It Matters).

**Defaults** when nothing overrides them: Depth = Standard · Audience = Reviewer · Focus =
top 2 relevance clusters.

### 3. Understand the request

Combine `$ARGUMENTS` with the answers to derive the checklist **theme**, consolidate the
must-have items, and map them onto the category scaffolding below.

### 4. Load feature context

From `REQUIREMENTS_DIR`:

| Artifact | Use it for |
|----------|-----------|
| `requirements.md` | Feature scope + requirements (the *what*) + acceptance criteria |
| `plan.md` (if present) | Specification context, **for gap-finding only** |
| `tasks.md` (if present) | Specification decomposition, **for missing-requirement detection only** |

`plan.md` and `tasks.md` are loaded to find what the requirements *omit* — never to test
whether the plan or the tasks are good.

**Same-author detection delegation.** The checklist is an audit instrument for a spec this
same agent usually just wrote, so it inherits the author's blind spots: the gaps a spec never
mentions are largely the gaps the author never thought of while writing it, and a re-read by
that author reproduces the same reading. When that condition holds, **derive the gap-finding
pass from fresh-context read-only subagents**. Apply the canonical gate in
`.specify/shared/workflow/objective-analysis-gate.md` (single source of truth; do not restate
its rules).

This skill has **no severity tiers**; its local analogue of the propagation-surface cap is
the traceability rule in step 5 — a **CHK** item carries the requirement or gap it guards, so
an item guarding nothing is visible as *untraceable* instead of passing as coverage.

### 5. Generate the checklist

- Create `REQUIREMENTS_DIR/checklists/` if needed.
- Use a short descriptive filename: `[domain].md` (e.g. `ux.md`, `api.md`, `security.md`).
- Number items sequentially from **CHK001**.
- **Each run creates a NEW file** — never overwrite an existing checklist.
- **Recheck form (append-only)**: when a later round answers an earlier item, write the
  answer to a NEW `checklists/recheck-<date>-<topic>.md` file — one file per round. Every
  answered entry MUST quote the requirement line it answers (verbatim, with its
  `requirements.md` anchor). The original checklist MUST NOT be refreshed in place: its
  unchecked rows stay as history.
- Apply the methodology: group by quality dimensions (**Completeness · Clarity ·
  Consistency · Measurability · Coverage · Edge Cases · Non-Functional · Dependencies ·
  Ambiguities**); each item is a *question* + a quality-dimension bracket + a traceability
  reference; **≥80 % of items must carry traceability** (`[Req §X]`, `[Gap]`,
  `[Ambiguity]`, …); **soft cap 40 items**, prioritized by risk/impact.

**PROHIBITED**: items starting with "Verify / Test / Confirm / Check" followed by
implementation behaviour.

**REQUIRED**: question patterns such as *"Are [X] defined/specified?"* and
*"Is [vague term] quantified?"*.

### 6. Structure

Follow `.specify/templates/checklist-template.md` for the canonical format. If it is unavailable: an
H1 title, a purpose/meta block, `##` category sections, and `- [ ] CHK### <item>` lines.

### 7. Report

Output: file path, item count, focus areas, depth level, and any user-specified items that
were incorporated.

## Feature Integration

Apply the Feature Integration Protocol
(`.specify/shared/workflow/feature-integration.md`). This capability transitions feature
status **`Implemented → Ready for Review`** when applicable.

## Boundaries

- **Not implementation verification.** An item answerable only by running the product is
  out of scope by construction (§ The purpose).
- **Not a plan/tasks reviewer.** `plan.md` and `tasks.md` are read to expose requirement
  gaps, not to be graded themselves.
- **Not the checklist methodology owner.** The dimension patterns and worked examples live
  in `.specify/shared/guidelines/checklist-methodology.md`.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:create-checklist" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:create-checklist" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:create-checklist" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
