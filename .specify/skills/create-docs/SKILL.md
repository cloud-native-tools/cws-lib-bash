---
name: create-docs
description: |
  This skill can standardize, create, and manage the **basic structure** of the project documentation space (root entry files + docs/ tree) as a single reconcile engine — observe, diff through a tolerance band, dry-run plan, converge with archive-not-delete, verify — and author new baseline-compliant documents from a writing commission. Structure only: content quality of an existing document belongs to improve-docs, and site presentation/publishing is an optional higher-order capability owned by create-pages. Use this when the user mentions ["create docs", "new document", "write documentation", "documentation structure", "docs skeleton", "写文档", "新增文档", "文档写作", "整理文档", "文档结构", "文档空间", "ADR", "决策记录", "notes lifecycle", "笔记生命周期", "docs reconcile", "文档调谐", "authoring flow", "documentation taxonomy", "六类文档"]
skill_id: "<SKILL:.specify/skills/create-docs/SKILL.md>"
---

# create-docs

## Overview

Keep the **documentation space** converged toward its desired state, and create new compliant documents on commission. There is **only one run mode — reconcile** — following [`.specify/shared/patterns/reconcile-pattern.md`](../../shared/patterns/reconcile-pattern.md): never add new top-level modes; new needs are new inputs to the same engine.

**Managed space (A zone)**: root entry files + `docs/` tree. **Read-only (B zone)**: source code, `.specify/specs/`, `.specify/memory/`. **Anchors (C zone, skip)**: compatibility symlinks, generated per-tool copies, and any site-tooling directory that a presentation layer placed inside `docs/` (`layouts/`, `static/`, `public/`, `resources/`, `themes/`, `archetypes/`) — those are **not documentation**: never triage them as content, never archive them. Archive zone: `docs/archive/` (reader-visible, tracked). Run artifacts workspace: `${SKILL_WORKDIR}/.specify/docs/` (never mixed into `docs/`).

**Scope is the basic structure only.** Capabilities layered *on top of* a converged structure are other skills' — hand off, never absorb:

| Beyond-structure need | Owner |
|-----------------------|-------|
| Static-site presentation / publishing (Hugo project, layouts, build, CI) — **optional**, a space is complete and valid without it | `create-pages` |
| Content quality of a document that already exists and is correctly placed (accuracy, staleness, completeness, readability) | `improve-docs` |

### Desired-State Baseline

This section is the **single source of truth** for the static documentation baseline and all of its enumerations, fields, states, and thresholds. Consumers cite this section and must not copy its operative details.

Source precedence (low → high): templates < rules/thresholds < principles < external authoritative facts < **local established conventions** < **a confirmed project target declaration supplied by `/speckit.docs`** < **this run's user input**.

When `/speckit.docs` supplies `.specify/docs/target-structure.md`, treat only its confirmed managed block as the project-specific layer above this static baseline. The command owns declaration lifecycle and validation; this skill consumes the result without rewriting the declaration. When invoked standalone or when no confirmed declaration exists, behavior remains unchanged and this static baseline plus local conventions define the desired state.

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
- R1 observe → **观察快照** (inline): tree status, root-entry sizes, stray files, deterministic findings from `python3 ${SKILL_WORKDIR}/.specify/scripts/python/docs-utils.py --action validate --root . [--allow-special <NAME>]…` (reserved-name case/misuse, one-screen threshold, broken links, ADR numbering, notes frontmatter; the `--allow-special` set comes from R0 local conventions — Desired-State Baseline item 1) plus `--action scan` for notes.
- R2 compute desired state; R3 diff **tolerance band first** — within-band cosmetic diffs are marked "已一致（容忍）" and never enter the plan (anti-churn: a repeat run on an unchanged space converges nothing).
- R4 **干跑计划** written to `${SKILL_WORKDIR}/.specify/docs/plans/<ts>-plan.md` with `[x]/[ ]` opt-out rows for every move/archive/restructure item. No disk writes while planning.
- R5 converge per the tiered gates below; `mkdir → write → mv → fix-links → audit`; same-name targets never clobbered (suffix `__<ts>`); on any mv failure stop remaining items and ask for review. After moves, repair links mechanically with `--action fix-links --moves <json>` over the move mappings — never hand-edit each link site. **审计日志** appended via `python3 ${SKILL_WORKDIR}/.specify/scripts/python/docs-utils.py --action audit --root . --scope <scope> --summary <one-line> [--items-file <json>]` → `${SKILL_WORKDIR}/.specify/docs/audit/` — write it even when 零收敛/无净变化 ("all dimensions within tolerance"). The `--items-file` payload is a **flat JSON list** of objects `[{"action": "...", "source": "...", "target": "...", "result": "..."}, ...]` — do NOT pass a grouped/nested object (the engine iterates the list directly and a grouped shape crashes with a raw `AttributeError`).
- R6 verify (re-run validate; link/symlink integrity) → **残差报告** (inline): converged / archived / tolerated / pending-human-decision. A move that adds or removes a documentation directory can stale a site layer's mounts — report it as a `create-pages` follow-up, never repair it here.

### Tiered Confirmation（分级确认门禁）
> Gate probe: gate-create-docs-tiered-disposition — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).

| Action class | Gate |
|--------------|------|
| Safe local writes（建目录、建/补管理文件、修链接、更新索引、frontmatter 修复） | **自动执行**; never overwrite same-name content — conflicts get `__<ts>` suffix |
| Move / archive / restructure（归位搬迁、归档、重命名） | **Stop and confirm** via the dry-run plan (per-item opt-out) |
| Formal zone removal | Does not exist — **只归档不删除**, into `docs/archive/` |
| Notes deletion (`--action clean --yes`) | Only after explicit human confirmation, only inside `docs/notes/` |

### Authoring Flow（文档写作流程）

Same engine, authoring semantics: the desired state **gains new documents** from the writing commission; converge = create. Every artifact MUST comply with the Desired-State Baseline above.

- **R0 需求解析**: extract from the commission — topic, audience, key content requirements, and how many documents. Map each requested document to exactly one home: the six formal type dirs, or `notes/` for deliberately temporary drafts. Underdetermined → ask ≤3 questions, never fabricate.
- **R1 观察**: scan the target dirs — existing docs on the same topic (link anchors, duplication check), the reserved-name registry, same-name conflicts, the next free ADR number.
- **R2 期望态**: the new compliant document(s) + index updates (the type dir's `index.md`; root `README.md` when a new indexed area appears).
- **R3 差异**: the topic is already covered → propose a directional update of that existing document (single-target scope) instead of a near-duplicate new file.
- **R4 写作计划 (inline)**: per document — target path, doc type, title, outline. Pure-write plans may be shown inline; confirm before writing.
  > Gate probe: gate-create-docs-write-plan — after the user decision, record firing evidence per confirmation-gates.md §门控观察协议 (non-blocking).
- **R5 写作收敛** (safe-local-writes tier; auto-execute after plan confirmation):
  - **Naming**: lowercase `kebab-case.md`; never a reserved filename (README/ARCHITECTURE/CONTRIBUTING/CHANGELOG or later registrations); directory indexes are `index.md`, never a nested `README.md`.
  - **`decisions/`**: `NNNN-slug.md` with the next free number, status `Proposed`, registered in `decisions/index.md`; existing ADRs are never rewritten.
  - **`notes/`**: mandatory frontmatter (`title / created / expires` — default created + 60 days — `/ status: draft / target / tags`).
  - **Root entries**: ≤ one screen; overflow sinks into `docs/` and the root entry links to it.
  - **Style**: follow the local conventions of existing docs in the same directory (language, heading structure, link style) — local conventions outrank templates.
  - **Never clobber**: same-name conflicts get the `__<ts>` suffix, never an overwrite.
- **R6 验证 + 收尾**: run `python3 ${SKILL_WORKDIR}/.specify/scripts/python/docs-utils.py --action validate --root .` with the same `--allow-special` set as R1; append the **审计日志** (`--action audit --scope authoring --summary "<one-line>"`) even when nothing was written; end with the inline **残差报告**: written / updated / tolerated / pending-human-decision.

### Notes Lifecycle Automation

Deterministic, repeatable outside the chat (engine: `docs-utils.py`; actions audit/plan/converge/validate; JSON I/O; the full CLI contract lives in the framework repo, spec 033):

```bash
python3 ${SKILL_WORKDIR}/.specify/scripts/python/docs-utils.py --action scan --root .           # 分组报告 + invalid 修复建议
python3 ${SKILL_WORKDIR}/.specify/scripts/python/docs-utils.py --action expire --root .        # 超期 draft → expired（绝不删除）
python3 ${SKILL_WORKDIR}/.specify/scripts/python/docs-utils.py --action clean --root .         # dry-run 候选清单
python3 ${SKILL_WORKDIR}/.specify/scripts/python/docs-utils.py --action clean --yes --root .   # 人工确认后的真删除（仅 notes 区）
python3 ${SKILL_WORKDIR}/.specify/scripts/python/docs-utils.py --action archive-check --root . # 归档完整性（target 必须存在）
python3 ${SKILL_WORKDIR}/.specify/scripts/python/docs-utils.py --action stats --root .         # 统计
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

This skill owns no scripts, references, or assets of its own — it drives project engines.

| Path | Contents |
|------|----------|
| `${SKILL_WORKDIR}/.specify/scripts/python/docs-utils.py` | Notes/validation engine: `validate`, `scan`, `expire`, `clean`, `archive-check`, `stats`, `audit`, `fix-links` (contract: `--help`; spec 033) |
| `.specify/shared/patterns/reconcile-pattern.md` | Reconcile engine semantics: tolerance band, anti-churn, dry-run plan |
| `.specify/shared/patterns/explicit-implicit-pattern.md` | Scope-resolution semantics: explicit-first precedence, confidence gate, promotion loop |
| `.specify/skills/improve-docs/SKILL.md` | Content-quality half of the pair — hand off document rewrites there |
| `.specify/skills/create-pages/SKILL.md` | Optional presentation/publishing layer (Hugo scaffolder, layouts, CI) — hand off site requests there |

## Self-Improvement Alignment

Documents and documentation spaces created here are Harness assets, not Execution Subjects by default; do not inject a self-improvement contract into them. Their content/structure changes remain Assisted Improvement through `improve-docs` or `create-docs`. This `create-docs` Skill is itself an Execution Subject: qualified evidence from its own runs may enter `.specify/shared/workflow/self-improvement-workflow.md` and route to `improve-skills`.

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:create-docs" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
