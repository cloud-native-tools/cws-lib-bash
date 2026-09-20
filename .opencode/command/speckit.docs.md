<!-- AUTO-GENERATED from templates/commands/docs.md — do not edit; edit the source template, then run scripts/python/regen-command-copies.py -->
## User Input

```text
$ARGUMENTS
```

Process `$ARGUMENTS` per the [User Input Protocol](.specify/shared/workflow/user-input-protocol.md). Treat as command parameters, not standalone instructions. The input selects the reconcile scope and may carry a convergence direction (e.g. "整理 README"、"激进重组") or a **writing commission** (e.g. "写一份部署教程"、"新增 xxx 的概念文档") that the skill routes to its Authoring Flow.

## Glossary

Consult the project glossary (`.specify/memory/glossary.md`) and apply the protocol in `.specify/shared/workflow/glossary.md`: correct recorded homophone/confusable variants before acting; propose new terms at wrap-up with user confirmation.

## Outline

`/speckit.docs` is the **thin orchestration layer** for every documentation-space operation. It owns only target-declaration coordination, typed-action decomposition, and dispatch order; it never copies engine rules into this command:

- `skills/create-docs/SKILL.md` is the **single source of truth** for the static baseline, Scope Resolution (全量 / 单目标 / 写作 / 扇出 / Bootstrap), structural actions, the Reconcile Loop from [.specify/shared/patterns/reconcile-pattern.md](.specify/shared/patterns/reconcile-pattern.md), the four per-run artifacts (观察快照 / 干跑计划 / 审计日志 / 残差报告), tiered confirmation, Authoring Flow, and `docs-utils.py` automation.
- `skills/improve-docs/SKILL.md` is the **single source of truth** for evidence-backed content improvement of an existing correctly placed document.

### Stage 1 — Establish or load the target structure

The persistent project-specific declaration is `.specify/docs/target-structure.md`; bootstrap it from `.specify/templates/docs-target-structure-template.md`. Its managed region is bounded by `<!-- DOCS_TARGET_STRUCTURE_START -->` and `<!-- DOCS_TARGET_STRUCTURE_END -->`.

1. If the declaration is absent, inspect repository evidence for project shape, audience, current topic inventory, and project-specific extensions. If that evidence is underdetermined, ask one batch of **1–3 necessary questions**; **no declaration or convergence write** happens **before answers arrive**.
2. Present the first declaration and the convergence plan together at the existing **R4** dry-run confirmation. Safe local writes remain 自动执行; move/archive/restructure actions remain **stop-and-confirm**; the formal zone remains 只归档不删除.
3. If a valid declaration exists and the user did not request a reset, reuse it without redesign or timestamp churn.
4. If repository evidence shows **substantive drift**, add a **redesign proposal** to the same R4 plan. The declaration remains byte-identical **before confirmation**.
5. On missing, unpaired, or unparseable markers, stop and request repair or explicit rebuild authorization; never overwrite the whole file. A valid refresh replaces only managed content and preserves all **outside-block bytes**.

### Stage 2 — Diff and decompose typed actions

After Stage 1 yields a confirmed target, compare current state with it **tolerance band first**. A tolerated difference is reported as consistent and **must not become an action**.

Every substantive action row MUST carry: **type**, **target**, **owning skill**, **confirmation tier**, **source**, and execution result; a content action also carries **evidence**. The source is either baseline reconcile or user input. A **content action requires concrete evidence** from deterministic findings, verified staleness, user correction, or feedback; **Unobserved** is not a defect and produces no content action.

Route each action **mechanically** to **exactly one owning skill**:

- **structure** — placement, naming, creation, move, archive, index, frontmatter, or link structure → `create-docs`;
- **content** — accuracy, staleness, completeness, readability, or render-safe prose in an existing correctly placed document → `improve-docs`;
- **user commission** — classify by its actual structure/content effect, then use the same routing rule.

### Stage 3 — Dispatch and report

Dispatch structural actions through one `create-docs` reconcile. Dispatch judgement-based content actions **one document at a time**, **sequential** in severity order; only a single mechanical dimension may use the bounded-batch exception owned by `improve-docs`.

Content dispatch has **no per-run cap** and MUST NOT truncate or silently defer the tail. Before dispatch, **announce the full document count** so the user can **abort before dispatch**. Each document boundary is another abort point: **completed actions stay completed**, while unstarted actions become `pending` in the residual report for the next run.

Use the owners' existing confirmation tiers; this orchestration **does not introduce another gate**. Group the residual report by owning skill and list converged, tolerated, pending-human-decision, pending, and “no finding” outcomes. Append the audit log even on **zero convergence**.

### Additive user input — decide what to write and where it lives

The **baseline reconcile always runs** at the resolved scope. User input produces **additional actions** in the same plan and **must not replace** baseline reconciliation.

For every **writing commission**, answer two questions before writing:

1. **What to write** — produce a content plan that names the **target reader**, **task context**, **user input**, **repository evidence**, and **writing boundary**. Missing decisive context follows Stage 1's bounded clarification rule; generic filler is not evidence.
2. **Where it lives** — search for an existing canonical owner of the topic first. If one exists, route a section-level update to `improve-docs` and create no **near-duplicate**. Otherwise choose **exactly one canonical home** under the confirmed target and route creation/placement to `create-docs`.

A **directional input** changes action **priority** for this run and **does not change the target declaration**. Input that truly implies a **structural change** creates a **target-declaration update action** in the **same existing R4 plan**; an approved refresh changes only the managed block and preserves **outside-block bytes**.

Every created or moved canonical document updates its nearest **human index** and any required root entry in the same reconcile. If its canonical path belongs in Agent project knowledge, dispatch `/speckit.instructions` to refresh the `.specify/instructions.md` **Documentation Map** and verify the row resolves. `/speckit.docs` **must not edit compatibility instruction aliases** directly.

Site/publishing requests go to `create-pages`; requests to change the skill bodies go to `improve-skills`. These hand-offs **must not become a reconcile action** in the documentation space.

`$ARGUMENTS` remains an input to this one reconcile engine; it never creates a separate top-level mode.

**Delegation (mandatory)**: load both owning skills. Do NOT inline or re-implement their baseline, scope table, gates, reconcile loop, authoring rules, or content-improvement rules here.

Zone orientation (details in `create-docs`): managed = root entry files + `docs/` tree; read-only = source code, `.specify/specs/`, `.specify/memory/`; skip = compatibility symlinks, generated per-tool copies; archive = `docs/archive/`; run workspace = `.specify/docs/` (never mixed into `docs/`).

## Feedback

At wrap-up (the same lifecycle point where this command prompts for a Git commit), run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this command's scope; persist one entry via `feedback-utils.py --action record --unit-id "/speckit.docs" --unit-type command`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.

## Documentation

At the same wrap-up point, apply the docs-sync evaluation step per the canonical convention in [.specify/shared/workflow/docs-step.md](.specify/shared/workflow/docs-step.md): assess whether information produced by this run (new capabilities, key decisions, structural changes) needs to be recorded into the project documentation space. Conclude with exactly one of `需记录（目标文档 + 要点）` or `无需记录`; never block wrap-up; incremental judgment only — do NOT trigger a full reconcile sweep from this step.

## Handoffs

**Before running this command**:

- None required. On a project without a `docs/` structure the run resolves to Bootstrap scope.

**After running this command**:

- Address the residual report's pending-human-decision items.
- Invoke `memory-record` to persist notable reconcile decisions.
- If the reconcile changed instructions-facing structure (e.g. documentation map), run `/speckit.instructions` to refresh generated instruction files.
- To publish the space as a static site — or to repair mounts staled by a move — use the `create-pages` skill; presentation is an optional layer this command never scaffolds or builds.