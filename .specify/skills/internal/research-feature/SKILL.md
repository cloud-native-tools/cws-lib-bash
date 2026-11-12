---
name: research-feature
description: Conduct in-depth research and analysis to support the implementation plan — resolve the AVAILABLE_DOCS inventory into a documentation reading list, load the feature spec + constitution + relevant project docs + feature memory, carry the project-context study through the study-code skill against this project, resolve every unknown (spec "NEEDS CLARIFICATION" markers and user research questions), and generate or incrementally append to the feature's research.md with structured Decisions & Rationale (decision / rationale / alternatives considered / impact). Use this when the user mentions ["research", "深度调研", "调研分析", "技术调研", "research findings", "research.md", "NEEDS CLARIFICATION", "open questions", "未决问题", "技术选型", "technology selection", "可行性分析", "feasibility"].
classification: internal
skill_id: "<SKILL:.specify/skills/internal/research-feature/SKILL.md>"
---

# research-feature

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.


## Goal

Conduct the in-depth research and analysis that backs the implementation planning: resolve
what project documentation exists and which of it is relevant, load the feature spec together
with the constitution and the project's docs / feature memory, carry the project-context study
through **`study-code` against this project**, resolve every unknown the spec or the user
raised, and land the findings as structured **Decisions & Rationale** (decision / rationale /
alternatives / impact) in the feature's `research.md`. This skill owns the SDD mode of
`/speckit.research` — Outline steps 1–5 and the research output structure — while the command
template keeps entry, mode routing, the `scripts:` block, the User Input Protocol, and the
wrap-up lifecycle (Feedback / Documentation / Handoffs).

Canonical extraction source: `.specify/templates/commands/research.md` § Outline (steps 1–5) and §
Research Output Structure. Content moved here verbatim in substance; the command template
keeps entry + lifecycle only.

## Input Contract

- **Setup variables**: FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH, and AVAILABLE_DOCS come
  from the command's `{SCRIPT}` prerequisite run (its `scripts:` entry resolves to
  `.specify/scripts/bash/research-project.sh --json`, run from repo root); all paths used below are
  absolute. `research.md` lives in `SPECS_DIR`.
- **User parameters**: `$ARGUMENTS` arrive already processed by the command's User Input
  Protocol (parameters for the run, never a standalone instruction overriding the workflow);
  they may carry special handling requests, supplemental reference material, and specific
  research questions beyond the default scope — those feed Unknown Resolution in Step 3.

## Workflow (Outline steps 1–5)

### Step 1 — Setup and documentation inventory

Run `{SCRIPT}` from repo root and parse JSON for FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH,
and **AVAILABLE_DOCS**.

- **Review Output**: analyze the `AVAILABLE_DOCS` list provided in the JSON output to identify
  potentially relevant documentation. This inventory drives Step 2's reading list — do not
  skip it.

### Step 2 — Load context

- Read `FEATURE_SPEC`.
- Read `.specify/constitution.md`.
- **Crucial**: based on `AVAILABLE_DOCS` and the feature requirements, read and analyze the
  relevant files from the project documentation. DO NOT rely only on memory; check `README.md`
  and the key docs found in the list.
- Read targeted excerpts for the areas this research touches rather than whole-directory
  sweeps (summary-first per `.specify/shared/guidelines/token-efficiency.md`; escalate through
  that discipline's ladder when a doc genuinely needs more depth).

### Step 3 — Information gathering & analysis

- **Own-project study (`study-code` carrier)**: the project-context study is a `study-code`
  invocation against this project (`.specify/skills/study-code/SKILL.md`): ensure a current
  study exists at `.specify/studies/<repo>-study/` — reuse it when `target-commit.txt` matches
  HEAD, otherwise run the study — and cite its report (`docs/overview.md`) plus evidence paths
  in `research.md`. SDD research invokes **no other study carrier**: unknowns the study cannot
  answer stay in Open Questions & Risks (the standalone `/speckit.research` mode is their route).
- **Project Architecture**: understand how the new feature fits into the existing system —
  sourced from the study report's architecture and component sections.
- **Feature Interdependencies**: check `.specify/features.md` and
  `.specify/features/` for conflicts or reuse opportunities.
- **Unknown Resolution**: address any defined "NEEDS CLARIFICATION" markers or research
  questions from `$ARGUMENTS`.
- **Technology Selection**: verify best practices using the gathered context.

### Step 4 — Generate/Update `research.md`

- The file lives at `SPECS_DIR/research.md`.
- **Merge Strategy (incremental append, never overwrite)**:
  - If the file exists, **APPEND** new findings to existing sections or create new sections.
    Do not overwrite existing valid research unless explicitly correcting it.
  - Properly integrate new "Decisions" and "References" without duplicating existing entries.
- If the file does not exist, create it with the structure below.

### Step 5 — Stop and report

Report the path of the generated `research.md` and summarize the key findings.

## Research Output Structure (`research.md`)

```markdown
# Research Findings: [Feature Name]

## Project Context Analysis
[Summarize insights from project docs and feature memory relevant to this plan. Mention constraints or patterns adopted.]

## References
- [List specific doc files or feature memory files referenced]
- [List external references provided in arguments]

## Decisions & Rationale

### [Decision Topic 1]
- **Decision**: [what was chosen]
- **Rationale**: [why chosen, citing references where applicable]
- **Alternatives considered**: [what else evaluated]
- **Impact**: [how this affects the plan]

## Open Questions & Risks
- [List any remaining unknowns that require human input or further experimentation]
```

Every decision records the same four axes — decision, rationale, alternatives considered,
impact — so the downstream implementation planning can encode each decision without
re-deriving it. Unresolved items land under Open Questions & Risks: they require human input
or further experimentation, and are never silently invented away.

## Boundaries

- **Entry & lifecycle stay in the command template** `/speckit.research`: the AUTO-GENERATED
  header, the `scripts:` block, the User Input Protocol, `## Feedback`, `## Documentation`,
  and `## Handoffs` (before/after command sequencing and next-command suggestions) are
  command surfaces, not skill content.
- **Merge-only writes**: this skill creates `research.md` or appends to it — existing valid
  research is touched only to explicitly correct it (Step 4's Merge Strategy).
- **No silent resolution**: unknowns that survive the research pass are recorded as Open
  Questions & Risks, never papered over with an invented answer.
- **Own-project study belongs to `study-code`**: this skill cites the study report and its
  evidence paths; it never duplicates the study method or writes into the study archive.
  SDD research invokes no `study-kb` / `study-online` — those carriers belong to the
  command's standalone mode, chosen per question there.
- **Shared conventions stay pointers**: summary-first reading is owned by
  `.specify/shared/guidelines/token-efficiency.md`; never copy its rules here.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:research-feature" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:research-feature" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:research-feature" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
