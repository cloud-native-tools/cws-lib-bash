<!-- AUTO-GENERATED from templates/commands/docs.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions. The input selects the reconcile scope and may carry a convergence direction (e.g. "整理 README"、"激进重组") or a **writing commission** (e.g. "写一份部署教程"、"新增 xxx 的概念文档") that the skill routes to its Authoring Flow.

## Glossary

Consult the project glossary (`.specify/memory/glossary.md`) and apply the protocol in `.specify/shared/workflow/glossary.md`: correct recorded homophone/confusable variants before acting; propose new terms at wrap-up with user confirmation.

## Outline

`/speckit.docs` is the **thin orchestration layer** for every documentation-space operation: it owns only target-declaration coordination, typed-action decomposition, and dispatch order, and delegates all execution to two owning skills — never copying engine rules into this command:

- **`create-docs`** — `.specify/skills/create-docs/SKILL.md` (runtime: `.specify/skills/create-docs/SKILL.md`) — single source of truth for the static baseline, Scope Resolution (全量 / 单目标 / 写作 / 扇出 / Bootstrap), structural actions, the Reconcile Loop from `.specify/shared/patterns/reconcile-pattern.md`, the four per-run artifacts (观察快照 / 干跑计划 / 审计日志 / 残差报告), tiered confirmation, the Authoring Flow, and `docs-utils.py` automation.
- **`improve-docs`** — `.specify/skills/improve-docs/SKILL.md` (runtime: `.specify/skills/improve-docs/SKILL.md`) — single source of truth for evidence-backed content improvement of an existing correctly placed document.

**Delegation (mandatory)**: load both owning skills and execute per their workflows. Do NOT inline or re-implement their baseline, scope table, gates, reconcile loop, authoring rules, or content-improvement rules here. Use the owners' existing confirmation tiers — this orchestration does not introduce another gate. The tier assignment is a governance keep this command still declares at dispatch: safe local writes remain 自动执行; move/archive/restructure actions remain **stop-and-confirm**; the formal zone remains 只归档不删除.

### 类别读取与文档型门禁(判定前一次,本命令不复制判据)

- **先读数、后判定**：在任何门禁判定之前执行一次 `python3 .specify/scripts/python/flow-class-check.py --action lookup --unit-id "/speckit.docs"`。取值、判据与逐流程台账的唯一所有者是 `.specify/shared/definitions/flow-class-definitions.md`；本模板只调用，不复述。
- **按门禁 owner 的调用点行执行算子**：算子集、阶段映射与阻断级别的唯一所有者是 `.specify/shared/workflow/expression-gates.md`；本命令只执行其 `/speckit.docs` 调用点行登记的文档型算子——读者/目的/边界、证据/as-of 与事实一致性三面由 `python3 .specify/scripts/python/doc-consistency-check.py --action verify --path <每个受触文档> [--spec-dir <spec-dir>] --strict` 承担（`--path` 逐个列出本轮受触文档、规格面存在时另加 `--spec-dir`，`--strict` 使任一 blocking 面的 `not-evaluated` 计为失败；计数面委派既有检查器），结构/链接/构建沿用既有 `docs-utils.py --action validate`（判据为零新增违规），评审沿用既有 `/speckit.review`。本模板不复制该表。
- **降级可见、门禁不因此转绿**：`source: default` 时原样显示其 `marker`（未登记·按默认）；所有者不可解析或引擎缺席（退出码 2）时显示 `owner-unavailable` 且 `marker` 为 null（两标签互斥）。文档型门禁的阻断级别归 `.specify/shared/workflow/expression-gates.md`：检查器退出码 1/2、或任一 blocking 面为 `not-evaluated` 时，本轮 MUST 报为门禁未通过并阻止「收敛完成」结论。MUST NOT 以 `owner-unavailable` 静默跳过门禁，MUST NOT 把降级当作通过，也 MUST NOT 因降级而静默切换门禁集。

### 技能输入(本命令解析 `$ARGUMENTS` 后传入)

- Resolved reconcile scope; the persistent declaration `docs/.speckit/target-structure.md` (bootstrap template: `.specify/skills/create-docs/assets/docs-target-structure-template.md`; managed region bounded by `<!-- DOCS_TARGET_STRUCTURE_START -->` and `<!-- DOCS_TARGET_STRUCTURE_END -->`). The declaration lifecycle below is **command-owned** — `create-docs` consumes the confirmed managed block without rewriting the declaration.
- Every substantive action row carries type / target / owning skill / confirmation tier / source / result (a content action also carries concrete evidence — deterministic findings, verified staleness, user correction, or feedback; **Unobserved** is not a defect and produces no content action).

### Target-structure declaration lifecycle (command-owned)

1. If the declaration is absent, inspect repository evidence for project shape, audience, current topic inventory, and project-specific extensions. If that evidence is underdetermined, ask one batch of **1–3 necessary questions**; **no declaration or convergence write** happens **before answers arrive**.
2. Present the first declaration and the convergence plan together at the existing **R4** dry-run confirmation. Safe local writes remain 自动执行; move/archive/restructure actions remain **stop-and-confirm**; the formal zone remains 只归档不删除.
3. If a valid declaration exists and the user did not request a reset, reuse it without redesign or timestamp churn.
4. If repository evidence shows **substantive drift**, add a **redesign proposal** to the same R4 plan. The declaration remains byte-identical **before confirmation**.
5. On missing, unpaired, or unparseable markers, stop and request repair or explicit rebuild authorization; never overwrite the whole file. A valid refresh replaces only managed content and preserves all **outside-block bytes**.

### 分派(本命令保留的编排职责)

- **structure** actions → `create-docs`(one reconcile);**content** actions → `improve-docs`, dispatched **one document at a time**, **sequential in severity order**; only a single mechanical dimension may use the bounded-batch exception owned by `improve-docs`. No per-run cap, no truncation of the tail; announce the full document count before dispatch so the user can abort.
- A **user commission** is classified by its actual structure/content effect, then uses the same routing rule. A **writing commission** answers two questions before writing: what to write (content plan: target reader / task context / user input / repository evidence / writing boundary) and where it lives (existing canonical owner → section-level update via `improve-docs`, no near-duplicate; otherwise exactly one canonical home and route creation/placement to `create-docs`).
- Every created or moved canonical document updates its nearest **human index** and any required root entry in the same reconcile; if its canonical path belongs in Agent project knowledge, dispatch `/speckit.instructions` to refresh the `.specify/instructions.md` **Documentation Map** — `/speckit.docs` **must not edit compatibility instruction aliases** directly.
- 产出:audit log appended even on **zero convergence** + residual report grouped by owning skill (converged / tolerated / pending-human-decision / pending / "no finding"); `$ARGUMENTS` remains an input to this one reconcile engine, never a separate top-level mode.

> **Fast Fail 实例指针**:本文件中"即停 / 即中止 / 不得静默降级"一类规则是快速失败纪律的既有**实例**;其判据与两份清单的唯一真源是 `.specify/shared/guidelines/fast-fail.md`(本文件引用它,MUST NOT 复述它)。

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "/speckit.docs" --unit-type command --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "/speckit.docs" --unit-type command`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "/speckit.docs" --unit-type command --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Docs Sync Eval — `.specify/shared/workflow/docs-step.md` § "Evaluation procedure (the embedded step points here)"

## Handoffs

**Before running this command**:

- None required. On a project without a `docs/` structure the run resolves to Bootstrap scope.

**After running this command**:

- Address the residual report's pending-human-decision items.
- Invoke `memory-record` (`.specify/skills/internal/memory-record/SKILL.md`) to persist notable reconcile decisions.
- If the reconcile changed instructions-facing structure (e.g. documentation map), run `/speckit.instructions` to refresh generated instruction files.
- To publish the space as a static site — or to repair mounts staled by a move — use the `create-pages` skill; presentation is an optional layer this command never scaffolds or builds.