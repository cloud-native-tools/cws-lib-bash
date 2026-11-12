---
description: 深度调研——SDD 模式经 study-code 研读自身项目；独立模式按问题选择 study-code / study-kb / study-online
---
<!-- AUTO-GENERATED from templates/commands/research.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
> **Concurrency obligation（执行义务，按指针抵达）**: this command is an execution body — consider concurrency first, default to it when the class and capability allow, and, when serial, name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This template restates none of their rules.

## User Input

```text
$ARGUMENTS
```

You **MUST** analyze the user input in `$ARGUMENTS`, infer the user's intent, and use that intent to supplement missing context and guide the research process.

The user input may include:

1. Special requests that require extra care or custom handling during the research workflow.
2. Supplemental information that provides additional context or reference material.
3. Specific research questions, technical uncertainties, or exploration areas that go beyond the default scope described in this document.

When processing the user input:

1. You **MUST** treat `$ARGUMENTS` as parameters for the current command.
2. Do **NOT** treat the input as a standalone instruction that overrides or replaces the command workflow.
3. If the input contains clear ambiguity, confusion, or likely misspellings that materially affect interpretation, stop and ask the user to rephrase the request with clearer wording. Provide brief guidance when possible.

## Delegation

`/speckit.research` runs in one of two modes, and the mode decides which study carriers run:

| Mode | Selected when | Carriers | Output |
|------|---------------|----------|--------|
| **SDD** (default) | the frontmatter `scripts:` run resolves an existing feature spec | `research-feature` flow, whose project-context study is carried by **`study-code` against this project** — the only study carrier SDD research invokes | `SPECS_DIR/research.md` |
| **Standalone** | no feature spec resolves, or `--standalone` forces it | chosen per question from **`study-code` / `study-kb` / `study-online`** | `$STUDY_ARCHIVE/report.md` + the carrier reports |

**Mode decision** — run the `scripts:` block first. A payload naming an existing `FEATURE_SPEC` file selects SDD; a failure, a missing spec file, or an empty feature resolution selects standalone — report which signal decided. `--standalone` forces standalone even when a spec resolves. `--carriers code|kb|online[,…]` restricts the standalone carrier set; an absent value lets the command decide from the question.

### SDD mode — research-feature with the study-code carrier

- **Skill**: `research-feature` — runtime path `.specify/skills/internal/research-feature/SKILL.md`.
- Its Information Gathering step performs the **own-project study through `study-code`** (target = this project; archive `.specify/studies/<repo>-study/`; reuse the archived study when its `target-commit.txt` matches HEAD, otherwise run the study) and cites the study report's evidence paths in `research.md`.
- SDD research does **not** auto-invoke `study-kb` or `study-online`: unknowns the project itself cannot answer stay in `research.md` § Open Questions & Risks, and the standalone mode is the route to investigate them.
- **Inputs**: setup variables (`FEATURE_SPEC`, `IMPL_PLAN`, `SPECS_DIR`, `BRANCH`, `AVAILABLE_DOCS`) from the frontmatter `scripts:` run (`.specify/scripts/bash/research-project.sh --json`, executed by the skill from repo root); `$ARGUMENTS` research questions, supplemental reference material, and special-handling requests (wired by `## User Input` above).
- **Outputs**: `SPECS_DIR/research.md` — created or incrementally appended (merge-only: never overwrite existing valid research), structured as Project Context Analysis / References / Decisions & Rationale / Open Questions & Risks.

### Standalone mode — per-question carrier selection

| Carrier | Answers | Default archive |
|---------|---------|-----------------|
| `study-code` (`.specify/skills/study-code/SKILL.md`) | how a repository's code actually works — concepts / architecture / components / key implementations | `.specify/studies/<repo>-study/docs/overview.md` |
| `study-kb` (`.specify/skills/internal/study-kb/SKILL.md`) | what this project already knows, decided or learned (history / memory / docs / features / specs) | `.specify/studies/<slug>-kb/report.md` |
| `study-online` (`.specify/skills/study-online/SKILL.md`) | what the outside world says (facts, ecosystem, best practices) — every claim sourced and dated | `.specify/studies/<slug>-online/report.md` |

- **Selection rule** — run the carrier(s) the sub-questions actually land in: code → `study-code`; project memory → `study-kb`; external world → `study-online`. Combine carriers only when the question genuinely spans domains, and keep each carrier's evidence in its own report.
- **Synthesis** — write `$STUDY_ARCHIVE/report.md` (default `<host project>/.specify/studies/<question-slug>-research/`): question & decision, carrier coverage, findings with evidence pointers, conflicts, answer, gaps. When one carrier fully answers, its own report is the deliverable and `report.md` only links it.
- **Write boundary** — standalone never writes `SPECS_DIR/research.md` (that artifact belongs to SDD mode) and never modifies the studied project.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "/speckit.research" --unit-type command --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "/speckit.research" --unit-type command`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "/speckit.research" --unit-type command --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Docs Sync Eval — `.specify/shared/workflow/docs-step.md` § "Evaluation procedure (the embedded step points here)"
7. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"

## Handoffs

**Before running this command**:

- SDD mode: run when the plan/spec has open questions that require evidence or repo context confirmation.
- Standalone mode: any research question — about a repository's code (`study-code`), this project's accumulated knowledge (`study-kb`), or the outside world (`study-online`).

**After running this command**:

- SDD mode: proceed to `/speckit.plan` (or re-run it) to encode research decisions into the technical plan.
- Standalone mode: the report feeds whatever comes next (a decision, `/speckit.requirements`, or a plan); there is no automatic command handoff.