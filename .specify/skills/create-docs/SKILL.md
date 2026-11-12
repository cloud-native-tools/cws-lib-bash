---
name: create-docs
description: |
  This skill can standardize, create, and manage the **basic structure** of the project documentation space (root entry files + docs/ tree) as a single reconcile engine — observe, diff through a tolerance band, dry-run plan, converge with archive-not-delete, verify — and author new baseline-compliant documents from a writing commission. Structure only: content quality of an existing document belongs to improve-docs, and site presentation/publishing is an optional higher-order capability owned by create-pages. Use this when the user mentions ["create docs", "new document", "write documentation", "documentation structure", "docs skeleton", "写文档", "新增文档", "文档写作", "整理文档", "文档结构", "文档空间", "ADR", "决策记录", "notes lifecycle", "笔记生命周期", "docs reconcile", "文档调谐", "authoring flow", "documentation taxonomy", "六类文档"]
skill_id: "<SKILL:.specify/skills/create-docs/SKILL.md>"
classification: external
---

# create-docs

> **Concurrency obligation（执行义务，按指针抵达）**: this skill is an execution body — before the first real action, run the one-shot assessment (class → carrier → partition), default to concurrent execution for two or more independent units, and when serial name a reason code and record the `requested` / `effective` / `effective_reason` reading. Authored text: `.specify/shared/definitions/subagent-definitions.md` § The Concurrency Obligation; class table: `.specify/shared/declarations/facts/concurrency-class.yaml`; reason codes: `.specify/shared/declarations/facts/serial-reason.yaml`; reading fields: `.specify/shared/declarations/facts/effective-concurrency.yaml`. This body restates none of their rules.


## Overview

Keep the **documentation space** converged toward its desired state, and create new compliant documents on commission. There is **only one run mode — reconcile** — following [`.specify/shared/patterns/reconcile-pattern.md`](../../shared/patterns/reconcile-pattern.md): never add new top-level modes; new needs are new inputs to the same engine.

**Managed space (A zone)**: root entry files + `docs/` tree. **Read-only (B zone)**: source code, `.specify/specs/`, `.specify/memory/`. **Anchors (C zone, skip)**: compatibility symlinks, generated per-tool copies, the `docs/.speckit/` machine area (target-structure declaration + run artifacts — never triaged as content), machine-maintained state files at the docs root (e.g. a legacy pre-migration `docs/git-workflow.md`; current git workflow state lives at `.specify/workflow/git.md`, outside the docs space), and any site-tooling directory that a presentation layer placed inside `docs/` (`layouts/`, `static/`, `public/`, `resources/`, `themes/`, `archetypes/`, dot-directories) — those are **not documentation**: never triage them as content, never archive them. Archive zone: `docs/archive/` (reader-visible, tracked). Run artifacts workspace: `${SKILL_WORKDIR}/docs/.speckit/` (never mixed into `docs/` as content).

**Scope is the basic structure only.** Capabilities layered *on top of* a converged structure are other skills' — hand off, never absorb:

| Beyond-structure need | Owner |
|-----------------------|-------|
| Static-site presentation / publishing (Hugo project, layouts, build, CI) — **optional**, a space is complete and valid without it | `create-pages` |
| Content quality of a document that already exists and is correctly placed (accuracy, staleness, completeness, readability) | `improve-docs` |

### Desired-State Baseline

This section is the **single source of truth** for the static documentation baseline and all of its enumerations, fields, states, and thresholds. Consumers cite this section and must not copy its operative details.

Source precedence (low → high): templates < rules/thresholds < principles < external authoritative facts < **local established conventions** < **a confirmed project target declaration supplied by `/speckit.docs`** < **this run's user input**.

When `/speckit.docs` supplies `docs/.speckit/target-structure.md`, treat only its confirmed managed block as the project-specific layer above this static baseline. The command owns declaration lifecycle and validation; this skill consumes the result without rewriting the declaration. When invoked standalone or when no confirmed declaration exists, behavior remains unchanged and this static baseline plus local conventions define the desired state.

1. **Thin root layer — uppercase special names (filename IS semantics; ALL-CAPS reserved)**, each ≤ one screen (~60 lines), overflow sinks into `docs/`:

   | Special file | Fixed semantics |
   |--------------|-----------------|
   | `README.md` | Root entry; indexes all of `docs/` |
   | `ARCHITECTURE.md` | One-page summary of `docs/concepts/` + `docs/decisions/` |
   | `CONTRIBUTING.md` | Contribution entry summarizing `docs/contribute/` |
   | `CHANGELOG.md` | Self-contained timeline |

   These are **Reserved Filenames（保留文件名）** — like reserved keywords: each entry registers fixed semantics AND a registered location (currently project root), and may appear ONLY there (strict blocking, constitution Principle X). User documents MUST NOT use a reserved name; same-semantics documents elsewhere use lowercase alternatives — **directory indexes are `index.md`, never a nested `README.md`**. The registry is extensible (a new reserved name registers semantics + location). An ALL-CAPS root name the engine's built-in registry does not carry, but that local conventions establish as a tool-mandated anchor (e.g. a C-zone compatibility entry file the host AI agent requires), is accepted by passing it on **every** validate call as `--allow-special <NAME>` (repeatable; flag semantics: the engine's `--help`) — the set is resolved once at R0 from local conventions, so a tolerated name stays tolerated instead of re-appearing as a finding on every run. A name without that local standing remains a violation — the flag extends the registry, it does not mute the check. Ordinary documents MUST be lowercase `kebab-case.md`.

2. **Thick `docs/` layer — six formal type directories + notes**: `concepts/` (What & Why) · `tutorials/` (learning path) · `tasks/` (task steps) · `reference/` (exact specs) · `decisions/` (ADR, append-only: NNNN-slug.md + index.md + template; status Proposed/Accepted/Deprecated/Superseded by — annotate, never rewrite history) · `contribute/` (contributor guide) · `notes/` (temporary, lifecycle-constrained, exits).

3. **Notes lifecycle**: every note carries frontmatter `title / created / expires (default created + 60 days) / status (draft|expired|archived) / target / tags`. State machine: draft →(合入 target)→ archived; draft →(超期)→ expired; expired →(续期)→ draft; expired →(人工确认)→ deleted (notes 区是唯一允许确认后真删除的区域). `docs/notes/index.md` states the rules and this frontmatter template:

   ```yaml
   ---
   title: "<one-line title>"
   created: YYYY-MM-DD
   expires: YYYY-MM-DD    # required; default = created + 60 days
   status: draft          # draft | expired | archived
   target: ""             # intended formal destination, required when archived
   tags: []
   ---
   ```

4. **Document lifecycle flow**: idea → ADR Proposed → Accepted → settled into `concepts/`/`reference/` → task/tutorial docs → obsolete decisions annotated Deprecated/Superseded.

5. **Diagram obligation — a document arrives with the diagram of the structure it describes**: the obligation is one clause in three parts, and only the third is optional:
   - **Carrier set** — which documents are judged: the six formal type directories (recursively, each `index.md` included) plus the root `ARCHITECTURE.md`. The set is owned by this item, and its machine-readable table is owned by the framework repository's `contracts/diagram-obligation.contract.md` (`C-003`) — a framework-side path that does not ship with this skill, so it is cited by name and never by a link; the checker implements that table and MUST NOT widen it. Notes, the archive, `docs/.speckit/`, `docs/assets/` and site-tooling directories are outside it — not judged is not the same as judged-and-passing.
   - **Obligation** — a carrier document is compliant only when it carries a **resolvable relative reference** to a rendered face of a diagram whose editable source and rendered face(s) land in the single landing § Assets registers, and a producing run has left that diagram's **traceability record** in `docs/.speckit/runs/` in the same run that produced the faces. Compliance is judged with `docs-utils.py --action obligation`; this baseline names the requirement and MUST NOT restate the checker's verdict words or their reasons — the record schemas, the five verdicts and the reason table live in [`references/diagram-obligation.md`](references/diagram-obligation.md), which ships with this skill.
   - **Named exemption** — a document with nothing to draw (a pure chronological log, a flat reference table, a licence text) is compliant through a **named, recorded exemption** under `docs/.speckit/exemptions/` ([`references/diagram-obligation.md`](references/diagram-obligation.md) § 3), which stays visible in every reading: an exemption is never a silent omission and never a pass.

   Deriving a diagram goes through the existing `draw-diagram` capability **by path** — `skills/external/draw-diagram` — its routing, semantic model, delivery contract and refusal semantics remain that skill's, quoted nowhere here. Background is written by a producing run, never by the checker.

   #### Assets

   `<root>/docs/assets/<slug>.<ext>` — the **single landing** for diagram material (this subsection owns the area convention). Both faces of one diagram land here together — the editable source (`.mmd`, `.puml`, `.drawio`…) and the rendered face(s) the delivery contract requires (`.svg`, `.png`…) — under one `<slug>`.

   - **One landing, no `diagrams/` subtree.** A second landing (`docs/<type>/diagrams/`, or any per-type fork of `assets/`) does not exist; a diagram never acquires a life of its own outside this directory.
   - **Reached by a resolvable relative reference.** A document points at a rendered face with a relative Markdown link (`../assets/<slug>.svg`), never an absolute path and never an external URL — that link is what the obligation's judgement resolves.
   - **Shared diagrams stay single.** Two or more documents may reference the same diagram; the source and the rendered faces stay one copy here (the trace record keeps one entry per diagram), and sharing MUST NOT fork the material into per-document duplicates.
   - **Not documentation content.** `assets/` is outside the carrier set: nothing in it is triaged as prose, counted as a carrier document, moved into `docs/archive/`, or read as a prose finding.
   - **The three face findings are named, one per face** — `orphan-rendered` (a rendered face is missing while the editable source is on disk), `orphan-source` (the source is missing while a rendered face is on disk), and `source-newer-than-render` (the source was edited after its rendered face) — each reported by its own name rather than as a single "the diagram is wrong". What each one means, which document lands it, and the step sequence it is decided in, are tabulated once in [`references/diagram-obligation.md`](references/diagram-obligation.md) § 4, § 6 and § 7 — that shipped reference is the single registry for the face names and for the decision order; this subsection names the faces and MUST NOT re-state those tables.

## Workflow

### Scope Resolution（作用域判定）

| Input | Scope | Behavior |
|-------|-------|----------|
| No arguments | **全量 (full sweep)** | Run the complete loop over the whole managed space |
| A target path/file | **单目标 (single target)** | Reconcile that target's **structure** only — placement, naming, links, index/registry rows, frontmatter; converge directionally with any supplementary instruction. Rewriting what the document *says* is `improve-docs` |
| A writing commission — requirements to CREATE content that does not exist yet ("写一份 X"、"新增 … 教程/概念/参考文档"), no single target | **文档写作 (authoring)** | Run the Authoring Flow below: parse requirements → place per taxonomy → write compliant documents → validate + index + audit |
| Raw material without a single target | **扇出 (fan-out intake)** | Decompose → triage per doc type → converge multiple targets; residue goes to `docs/notes/`, never dropped |
| Managed space absent/empty | **Bootstrap** | Generate the full skeleton (4 root entries + 6 type dirs + `decisions/index.md` + `decisions/template.md` + `notes/index.md`). Presentation/publishing is **not** bootstrapped — offer `create-pages` if the user wants a site |

**Authoring vs fan-out discriminator**: the commission asks to *create* content (topic/requirements given, artifact absent) → authoring; the input *is* the content (existing material to file away) → fan-out. Ambiguous → ask per the R0 rule (≤3 questions), never guess.

**Resolution discipline**: resolving input to exactly one scope is a routing decision that runs under the explicit–implicit rule pattern — the table above is this engine's explicit layer; precedence, confidence-gate, and promotion semantics are owned by [`.specify/shared/patterns/explicit-implicit-pattern.md`](../../shared/patterns/explicit-implicit-pattern.md).

**Site requests are a hand-off, not a scope.** "生成站点"/"发布文档"/"build the site" is beyond-structure work: name `create-pages` and stop. This engine never scaffolds, mounts, or builds a site — but it does keep skipping site-tooling directories per the C-zone rule above.

### Reconcile Loop (thin dispatch — engine semantics live in the pattern doc)

- R0 baseline: load the Desired-State Baseline + local conventions + user input. Underdetermined → ask ≤3 questions, never fabricate.
- R1 observe → **观察快照** (inline): tree status, root-entry sizes, stray files, deterministic findings from `python3 ${SKILL_HOME}/scripts/docs-utils.py --action validate --root . [--allow-special <NAME>]…` (reserved-name case/misuse, one-screen threshold, broken links, ADR numbering, notes frontmatter; the `--allow-special` set comes from R0 local conventions — Desired-State Baseline item 1) plus `--action scan` for notes.
- R2 compute desired state — the tolerance band's reference point, covering **every document in scope on two dimensions**: the structural baseline (items 1–4) and the **diagram dimension** (item 5 + § Assets) — for a single-target scope the target document, for a full sweep every carrier. A document that satisfies the structural baseline and carries no diagram is therefore already non-conforming, not "compliant with a follow-up". R3 diff **tolerance band first** — within-band cosmetic diffs are marked "已一致（容忍）" and never enter the plan (anti-churn: a repeat run on an unchanged space converges nothing).
- R3 differences — `python3 ${SKILL_HOME}/scripts/docs-utils.py --action obligation --root . --record <本次运行记录>` (the verbatim command form lives in R6; the record is the latest one this run knows about, `--record` omitted when none exists) is run at the **same rank as** `validate`: each of its per-document readings for `missing` / `stale` / `not-evaluated` is one difference item, carrying the document path, the named face or the named reason, and the line the reference sits on. An engine refusal is **not** a text-only difference: a `draw-diagram` preflight failure (its Step 2), an unreachable shared render backend (its Step 2.5) or a failed delivery check (its Step 4) is carried through **verbatim as that capability's own stop-and-report** — this loop MUST NOT absorb it into "文档已写完", MUST NOT render locally as a fallback, and MUST NOT report the diagram as skipped. The refusal's wording is `draw-diagram`'s; this loop only carries it.
- R4 **干跑计划** written to `${SKILL_WORKDIR}/docs/.speckit/plans/<ts>-plan.md` with `[x]/[ ]` opt-out rows for every move/archive/restructure item. **Each R3 diagram difference gets exactly one produce / re-render row** in the same plan — `[ ]` + document path + planned diagram class + engine layer (`待前门路由` when the diagram is new, the recorded engine when it is an update) + landing `assets/` (§ Assets) + the action (produce a first diagram, re-render a stale one, add the missing record). Those rows are **pure writes** (`FR-021`'s guard: converging an existing space happens ONLY under this dry-run plan plus the tolerance band and the existing stop-and-confirm tiers — no document is silently re-classified as non-conforming): they add the diagram faces and the reference, they NEVER rewrite the document body, and they NEVER join the move/archive opt-out list — moving a document and drawing it are different actions and MUST NOT ride in one row. No disk writes while planning.
- R5 converge per the tiered gates below; `mkdir → write → mv → fix-links → audit`; same-name targets never clobbered (suffix `__<ts>`); on any mv failure stop remaining items and ask for review. After moves, repair links mechanically with `--action fix-links --moves <json>` over the move mappings — never hand-edit each link site. **Diagram rows converge here, in this loop** — for each R4 produce / re-render row, call the `draw-diagram` front door (`skills/external/draw-diagram`) to produce the editable source and the rendered face(s) its delivery contract requires **and**, in the **same run**, write the document's resolvable relative reference and the traceability record — under the existing safe-local-writes tier (§ Tiered Confirmation), never by handing the work back to the authoring flow (one reconcile that re-commissions itself is an unbounded recursion). A diagram whose record already exists keeps the engine that record names and is never re-routed; only a new diagram is routed. This step is not skippable: a `not-evaluated` document (no record, or an incomplete one) gets its record completed or its diagram drawn here, and `exempt-*` documents (a valid recorded exemption) are **not residual** — the loop leaves them alone rather than drawing over them. **审计日志** appended via `python3 ${SKILL_HOME}/scripts/docs-utils.py --action audit --root . --scope <scope> --summary <one-line> [--items-file <json>]` → `${SKILL_WORKDIR}/docs/.speckit/audit/` — write it even when 零收敛/无净变化 ("all dimensions within tolerance"). The `--items-file` payload is a **flat JSON list** of objects `[{"action": "...", "source": "...", "target": "...", "result": "..."}, ...]` — do NOT pass a grouped/nested object (the engine iterates the list directly and a grouped shape crashes with a raw `AttributeError`).
- R6 verify (re-run validate **and** re-run `--action obligation` with this run's record; link/symlink integrity) → **残差报告** (inline): converged / archived / tolerated / pending-human-decision, and a **diagram-dimension block** carrying its five counts (`satisfied` / `missing` / `stale` / `exempted` / `not-evaluated`) plus the two predicates `converged` and `clean` as the checker reports them. **Convergence criterion is `converged`, not `clean`** (`contracts/diagram-obligation.contract.md` § `C-013`): any non-zero `missing` / `stale` / `not-evaluated` blocks the "收敛完成" conclusion, while `exempted` is counted separately and is a **lawful terminal state, not a residual** — an exempted space converges as `converged=true` + `clean=false`, and MUST NOT be reported as unconverged. Every count MUST be accompanied by the four evidences `FR-022` names for each document behind it: source path, rendered face path(s), the document's reference, and the trace-record path. **`D-001`'s semantic face is named once per report as 未覆盖**: a diagram whose picture still disagrees with its prose is not converged by this mechanism (the checker has no parser), and the report says so rather than implying a clean bill. A move that adds or removes a documentation directory can stale a site layer's mounts — report it as a `create-pages` follow-up, never repair it here. **门禁补强**:按门禁 owner `.specify/shared/workflow/expression-gates.md` 的 `skill:create-docs` 调用点行——当调用方已解析为文档型算子集时,对受触文档执行 `python3 .specify/scripts/python/doc-consistency-check.py --action verify --path <每个受触文档> [--spec-dir <spec-dir>] --strict`(`--path` 逐个列出本轮受触文档、规格面存在时另加 `--spec-dir`;复用调用方同一次执行的输出,不重复执行);退出码 1/2 或任一 blocking 面 `not-evaluated` 即门禁未通过,必须阻止「收敛完成」结论——owner 或引擎缺席时同样按失败呈现而非跳过。类别由调用方依 `.specify/shared/definitions/flow-class-definitions.md` 读取,本技能不新增读取、不复制判据或算子表。

### Tiered Confirmation（分级确认门禁）
> Gate probe: gate-create-docs-tiered-disposition — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).

| Action class | Gate |
|--------------|------|
| Safe local writes（建目录、建/补管理文件、修链接、更新索引、frontmatter 修复、**写图**：产/重渲染 `assets/` 下的一面或两面、补文档里的相对引用、写追溯记录或豁免记录） | **自动执行**; never overwrite same-name content — conflicts get `__<ts>` suffix |
| Move / archive / restructure（归位搬迁、归档、重命名） | **Stop and confirm** via the dry-run plan (per-item opt-out) |
| Formal zone removal | Does not exist — **只归档不删除**, into `docs/archive/` |
| Notes deletion (`--action clean --yes`) | Only after explicit human confirmation, only inside `docs/notes/` |

### Authoring Flow（文档写作流程）

Same engine, authoring semantics: the desired state **gains new documents** from the writing commission; converge = create. Every artifact MUST comply with the Desired-State Baseline above.

- **R0 需求解析**: extract from the commission — topic, audience, key content requirements, and how many documents. Map each requested document to exactly one home: the six formal type dirs, or `notes/` for deliberately temporary drafts. Underdetermined → ask ≤3 questions, never fabricate.
- **R1 观察**: scan the target dirs — existing docs on the same topic (link anchors, duplication check), the reserved-name registry, same-name conflicts, the next free ADR number.
- **R2 期望态**: the new compliant document(s) + index updates (the type dir's `index.md`; root `README.md` when a new indexed area appears) + **each new document's diagram plan** — the structure the document will describe, its diagram class and intended engine layer (`待前门路由` where the routing is not decided yet), and where the source and the rendered face(s) will land — the landing (§ Assets, `docs/assets/<slug>.<ext>`). A document planned without its diagram has not reached its desired state: the diagram is part of the desired state, not a follow-up task.
- **R3 差异**: the topic is already covered → propose a directional update of that existing document (single-target scope) instead of a near-duplicate new file.
- **R4 写作计划 (inline)**: per document — target path, doc type, title, outline, and the diagram its plan names (R2). Pure-write plans may be shown inline; confirm before writing.
  > Gate probe: gate-create-docs-write-plan — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).
- **R5 写作收敛** (safe-local-writes tier; auto-execute after plan confirmation):
  - **Diagram**: every newly written document leaves this step with its diagram — call the `draw-diagram` front door (`skills/external/draw-diagram`) for the structure the document describes, produce the **editable source** and the **rendered face(s)** its delivery contract requires into § Assets' single landing, and in the **same run** write the document's **resolvable relative reference** to a rendered face and the diagram's **traceability record** under `docs/.speckit/runs/`. One run yields all four on-disk artifacts (the document, the source, the rendered face(s), the reference); the record travels with them, written by this run and never back-filled by a later one. An existing diagram is updated through the engine its record already names — never re-routed. When the capability **refuses** (front-door preflight, unreachable render backend, failed delivery check), that refusal is carried through to the user verbatim and the run does NOT report itself complete: there is no local fallback rendering, no second rendering path here, and no version of this run in which the document counts as finished while its diagram was left undone. A document with nothing to draw gets a **named recorded exemption** instead of an omission (§ Desired-State Baseline item 5).
  - **Naming**: lowercase `kebab-case.md`; never a reserved filename (README/ARCHITECTURE/CONTRIBUTING/CHANGELOG or later registrations); directory indexes are `index.md`, never a nested `README.md`.
  - **`decisions/`**: `NNNN-slug.md` with the next free number, status `Proposed`, registered in `decisions/index.md`; existing ADRs are never rewritten.
  - **`notes/`**: mandatory frontmatter (`title / created / expires` — default created + 60 days — `/ status: draft / target / tags`).
  - **Root entries**: ≤ one screen; overflow sinks into `docs/` and the root entry links to it.
  - **Style**: follow the local conventions of existing docs in the same directory (language, heading structure, link style) — local conventions outrank templates.
  - **Never clobber**: same-name conflicts get the `__<ts>` suffix, never an overwrite.
- **R6 验证 + 收尾**: run `python3 ${SKILL_HOME}/scripts/docs-utils.py --action validate --root .` with the same `--allow-special` set as R1, **and run `python3 ${SKILL_HOME}/scripts/docs-utils.py --action obligation --root . --record <本次运行写下的追溯记录>` alongside it** (the record R5 wrote in this run; when the run wrote none, the check runs without `--record` and its readings are part of the residual report, not a skipped step). Both readings enter the inline **残差报告**: written / updated / tolerated / pending-human-decision, plus the diagram dimension's counts (`satisfied` / `missing` / `stale` / `exempted` / `not-evaluated`) with the four evidences `FR-022` requires per document — source path, rendered face path(s), the document's reference and the trace-record path. `missing` / `stale` / `not-evaluated` non-zero ⇒ the run MUST NOT conclude 「收敛完成」; an `exempted` document is reported as exempted, not as a residual. Also append the **审计日志** (`--action audit --scope authoring --summary "<one-line>"`) even when nothing was written. **门禁补强**:按门禁 owner `.specify/shared/workflow/expression-gates.md` 的 `skill:create-docs` 调用点行——当调用方已解析为文档型算子集时,对受触文档执行 `python3 .specify/scripts/python/doc-consistency-check.py --action verify --path <每个受触文档> [--spec-dir <spec-dir>] --strict`(`--path` 逐个列出本轮受触文档、规格面存在时另加 `--spec-dir`;复用调用方同一次执行的输出,不重复执行);退出码 1/2 或任一 blocking 面 `not-evaluated` 即门禁未通过,必须阻止「收敛完成」结论——owner 或引擎缺席时同样按失败呈现而非跳过。类别由调用方依 `.specify/shared/definitions/flow-class-definitions.md` 读取,本技能不新增读取、不复制判据或算子表。

### Notes Lifecycle Automation

Deterministic, repeatable outside the chat (engine: `docs-utils.py`; actions audit/plan/converge/validate; JSON I/O; the full CLI contract lives in the framework repo, spec 033):

```bash
python3 ${SKILL_HOME}/scripts/docs-utils.py --action scan --root .           # 分组报告 + invalid 修复建议
python3 ${SKILL_HOME}/scripts/docs-utils.py --action expire --root .        # 超期 draft → expired（绝不删除）
python3 ${SKILL_HOME}/scripts/docs-utils.py --action clean --root .         # dry-run 候选清单
python3 ${SKILL_HOME}/scripts/docs-utils.py --action clean --yes --root .   # 人工确认后的真删除（仅 notes 区）
python3 ${SKILL_HOME}/scripts/docs-utils.py --action archive-check --root . # 归档完整性（target 必须存在）
python3 ${SKILL_HOME}/scripts/docs-utils.py --action stats --root .         # 统计
```

Reference documentation: `docs/reference/commands/docs.md`.

## Resource ID

- Canonical ID: `<SKILL:.specify/skills/create-docs/SKILL.md>`
- Canonical Path: `.specify/skills/create-docs/SKILL.md`

## Path Conventions

This Skill follows the canonical `${SKILL_HOME}` / `${SKILL_WORKDIR}` path conventions:

- Use `${SKILL_HOME}/<relative-path>` for every Skill-owned resource reference (scripts, references, assets).
- Use `${SKILL_WORKDIR}/<relative-path>` for every runtime/user-facing path this Skill reads from or writes to (inputs in the user's project, outputs delivered to the user).
- Never conflate the two; never embed agent-specific install paths.

## Resources

This skill is self-contained for structure work: it owns its deterministic engine and the target-structure bootstrap asset; the shared pattern docs below are design guidance, not run-time dependencies.

| Path | Contents |
|------|----------|
| `${SKILL_HOME}/scripts/docs-utils.py` | Notes/validation engine: `validate`, `scan`, `expire`, `clean`, `archive-check`, `stats`, `audit`, `fix-links` (contract: `--help`; spec 033), plus the read-only obligation sweep `obligation` |
| `${SKILL_HOME}/references/diagram-obligation.md` | Item 5's shipped page: record schemas, verdict/reason table and precedence — cited instead of restating the engine's vocabulary |
| `${SKILL_HOME}/assets/docs-target-structure-template.md` | Target-structure bootstrap template — the command seeds `docs/.speckit/target-structure.md` from it |
| `.specify/shared/patterns/reconcile-pattern.md` | Reconcile engine semantics: tolerance band, anti-churn, dry-run plan |
| `.specify/shared/patterns/explicit-implicit-pattern.md` | Scope-resolution semantics: explicit-first precedence, confidence gate, promotion loop |
| `.specify/skills/improve-docs/SKILL.md` | Content-quality half of the pair — hand off document rewrites there |
| `.specify/skills/create-pages/SKILL.md` | Optional presentation/publishing layer (Hugo scaffolder, layouts, CI) — hand off site requests there |

## Self-Improvement Alignment

Documents and documentation spaces created here are Harness assets, not Execution Subjects by default; do not inject a self-improvement contract into them. Their content/structure changes remain Assisted Improvement through `improve-docs` or `create-docs`. This `create-docs` Skill is itself an Execution Subject: qualified evidence from its own runs may enter `.specify/shared/workflow/self-improvement-workflow.md` and route to `improve-skills`.

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 4682b9e38032 — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:create-docs" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:create-docs" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:create-docs" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
6. Closeout — `.specify/shared/workflow/artifact-commit-step.md` § "The `## Close-out` step"
