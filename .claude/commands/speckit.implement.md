<!-- AUTO-GENERATED from templates/commands/implement.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
> **Concurrency obligation（执行义务，按指针抵达）**: this command is an execution body — consider concurrency first, default to it when the class and capability allow, and, when serial, name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This template restates none of their rules.

## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions.

### 类别读取与文档型门禁

- **判定前一次读取**：本阶段在任何依赖类别的动作之前执行一次 `python3 .specify/scripts/python/flow-class-check.py --action lookup --unit-id "spec:<spec 目录名>"`（`<spec 目录名>` 取本线 spec 目录的 basename）；同一次阶段运行只读一次，结果复用于本阶段全部判定，委派技能复用该结果、不再读第二次。
- **两条 owner 指针**：类别判据与取值归 `.specify/shared/definitions/flow-class-definitions.md`；阶段算子、阻断级别与降级归 `.specify/shared/workflow/expression-gates.md`。本模板只调用读取入口，不复制判据、面表或算子表。
- **两分支**：解析为**表达类**时，本阶段按门禁 owner § 阶段算子表执行本阶段登记的行；其余情形（含未声明按默认）保持既有门禁集**逐字不变**——零新增阻断项、零新增必填章节。
- **降级可见**：读取报 `owner-unavailable`（退出码 2：引擎缺席、owner 不可解析或输入非法）时，原样显示该标签并保持既有门禁集，不中断本阶段、不转绿、不切换门禁集。
- **作者输入错误即停**：解析以退出码 1 报作者输入错误（取值越界或声明行形态不合规）时，本阶段停下，以阶段协议异常行 `ANOMALY: <一句话事实>` 作为最后一行输出并点名文件与行号；MUST NOT 落入上一条「既有门禁集逐字不变」那一支继续执行——那一支只适用于退出码 0 的未声明与降级路径。

## Glossary

Consult the project glossary (`.specify/glossary.md`, ambient via the Documentation Map) and apply the protocol in `.specify/shared/workflow/glossary.md`:

- **Before acting on the user input**, map any recorded homophone/confusable variant to its canonical term (correcting voice/dictated input); surface each correction so the user can override it, and defer to the user on ambiguous variants.
- **At wrap-up**, propose any new project-specific terms (`origin=auto`, `status=proposed`), excluding common words; run conflict detection; non-conflicting new terms MUST be written directly and merged into the wrap-up report (non-blocking); only writes that conflict with or overwrite an existing user entry MUST still pause for user confirmation. User-authored entries are authoritative.

## Skill Delegation

The executable core of this command is the **`implement-feature`** skill (`.specify/skills/internal/implement-feature/SKILL.md`): it turns the feature's `tasks.md` into a completed, verified, committed implementation. This template keeps entry, user input, glossary, the feature-status flip, and the wrap-up lifecycle only.

- **Inputs**: `$ARGUMENTS` (processed per the User Input Protocol); `REQUIREMENTS_DIR` and `AVAILABLE_DOCS` from the `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` prerequisite run (frontmatter `scripts:`), all paths absolute; `tasks.md` and `plan.md` are REQUIRED.
- **Baseline pre-flight** (before entering the skill): re-capture every frozen baseline of the feature — the set is derived from the spec directory by glob (`<spec-dir>/baseline-*`, `<spec-dir>/notes/baseline-*`) plus the coverage baseline file ([[STR-002]]); where a re-capture differs from the frozen value, write the new value into the row that cites it and classify every difference — BEFORE any drift verdict — via `git log` provenance as `upstream repair` / `inherited` / `attributable to this feature` / `undecidable` (reported explicitly; MUST NOT guess between the attributed classes); a missing baseline file is a first capture with provenance recorded, never zero drift.
- **How to call**: read the skill and follow its steps 1–9 — checklist exemption gate (waiver probe), summary-first context load, project setup + writability pre-probe, topological `tasks.md` parse (dependencies, `[P]`, `[blockedBy]`, `[>]` claims), phase-by-phase TDD implementation (mechanical write gate, failure attribution first, batched regens, evidence-backed closure IDENTIFY→RUN→READ→VERIFY→CLAIM), progress tracking with honest deferred-task marks, Completion Gate re-validation + commit gate (deletion-surface audit, approval routing), Pre-Status-Flip Gate + verification log.
- **Also owned by the skill**: mid-run user directives (scope revision — upstream first, append-only tasks, re-verify the touched surface), the opt-in Long-Run self-iterating loop (state file, iteration cap, stagnation two-strike), and the Optional Git Commit fallback (`.specify/templates/commit-template.md`, explicit user approval only).
- **Outputs**: every task `[X]` or honestly `[~]`, the `## Completion Gate` re-validated against the current tree, `verification.md` populated, phase-boundary commits landed.

> **Fast Fail 实例指针**:本文件中"即停 / 即中止 / 不得静默降级"一类规则是快速失败纪律的既有**实例**;其判据与两份清单的唯一真源是 `.specify/shared/guidelines/fast-fail.md`(本文件引用它,MUST NOT 复述它)。

## Feature Integration

Apply [Feature Integration Protocol](.specify/shared/workflow/feature-integration.md). This command's transition: `Planned → Implemented` (requires gate pass).

- **Closure verdict before the flip**: run `python3 .specify/scripts/python/closure-acceptance-check.py --spec-dir <REQUIREMENTS_DIR>` from the repository root before landing the status. The verdict, the closed reason set and the `final_path` counts are owned by `.specify/shared/workflow/acceptance-hardening.md` § Closure Verdict — this command calls that judgement and never restates a condition. On `block`, land `Blocked` (recording the emitted reasons in `REQUIREMENTS_DIR/verification.md`) and MUST NOT write `Implemented`: a `block` is the honest outcome of a run whose `final`-path criterion did not pass, not a defect of this command.
- **The status claim is a gate product, never a stage self-assessment (status 是门产物,不是阶段自评)**: the registry row (`.specify/features.md`) and the feature detail's `**Status**` line are **read-only** to this stage until the checker has returned `accept` for the tree being closed. Concretely, in one commit and in this order: (1) run the checker on the tree to be claimed (never an earlier reading — a verdict is a measurement of one tree), (2) copy its `verdict` and emitted reasons into `REQUIREMENTS_DIR/verification.md`, (3) only then write the registry row / detail status. On `block` the stage MUST NOT write `Implemented` anywhere — not into the registry, not into the detail file, not into its own wrap-up prose — and a document that declines the claim must not sit beside a registry row that makes it: the two are one fact and land together. A hand-written `Implemented` that no `accept` verdict backs is exactly the defect this rule removes, and it is not repairable by a later stage overwriting it.
- **The evidence carrier is the key=value block**: the checker reads `SC-NNN_status=` rows in `REQUIREMENTS_DIR/verification.md` and nothing else, so `.specify/templates/verification-log-template.md` (the vocabulary owner) requires that block in addition to any human table. A `pass` that exists only inside a Markdown table row reads as no row at all — `unknown`, never `pass` — and the run MUST NOT cite such a table as its closure evidence.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "/speckit.implement" --unit-type command --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "/speckit.implement" --unit-type command`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "/speckit.implement" --unit-type command --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Docs Sync Eval — `.specify/shared/workflow/docs-step.md` § "Evaluation procedure (the embedded step points here)"
7. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"

## Handoffs

**Before**: `/speckit.tasks` to ensure complete tasks.md exists.

**After**: `/speckit.review` for SDD process quality evaluation. Optional `/speckit.analyze` for drift detection.