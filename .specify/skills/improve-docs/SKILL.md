---
name: improve-docs
description: |
  This skill can improve an existing document in the project documentation space — correct inaccurate or stale content, close a completeness gap, restructure an unreadable page, repair broken links and anchors, fix content that breaks the site build, promote a matured note, or annotate a superseded decision — driven by reader feedback, review findings, and deterministic engine findings rather than taste. Use this when the user mentions ["improve docs", "improve documentation", "fix the doc", "update the doc", "doc is wrong", "doc is outdated", "documentation feedback", "doc quality", "rewrite this doc", "split this doc", "supersede decision", "annotate ADR", "改进文档", "优化文档", "修正文档", "文档过时", "文档不准确", "文档看不懂", "文档反馈", "文档质量", "补充文档", "拆分文档", "废弃决策", "笔记转正"]
skill_id: "<SKILL:.specify/skills/improve-docs/SKILL.md>"
---

# improve-docs

## Goal

Improve **one existing document** in the managed documentation space so the next reader succeeds where the last one failed: fix content that is wrong, stale, incomplete, unreadable, unlinkable, or unrenderable. This is the **content-quality** member of the docs trio: `create-docs` owns the structure, `create-pages` owns the optional presentation layer.

Edits are **section-level**: load the document, change only what the evidence justifies, verify, report. Never regenerate a document from an outline and never rewrite a page wholesale to "clean it up" — that discards accumulated, hard-won wording and silently drops facts.

Goal anchor (Constitution Principle XIII): this skill is a Better-Harness instrument — a document that states the system correctly strengthens **Task Understanding**, and folding reader feedback back into it closes the **Learning Capture** loop; goal model in `.specify/shared/guidelines/better-harness.md`.

### Ownership boundary (do not cross)

| Concern | Owner |
|---------|-------|
| Create a document that does not exist yet; bootstrap the space | `create-docs` |
| Placement, naming, taxonomy, moves, archiving, index/registry structure, notes state transitions on disk | `create-docs` |
| Static-site presentation / publishing (Hugo project, layouts, mounts, build, CI) — optional | `create-pages` |
| **Content** of a document that already exists and is already correctly placed | **this skill** |
| Improving `create-docs` / `create-pages` / `improve-docs` themselves (the skill bodies) | `improve-skills` |

If the evidence calls for a move, an archive, a rename, or a brand-new document, **stop and hand off to `create-docs`**; if it calls for site scaffolding, mount repair, or a publishing pipeline, hand off to `create-pages`. Do not perform either here — do the content fix that is yours and say so in the report.

## Input Contract

- **Target**: resolve exactly **one** document by path, title, or description. If several match, present the candidates and ask which one. If none exists, report "no such document" and offer `create-docs` — never create one implicitly.
  - A **bounded batch** is allowed only when the improvement is one mechanical dimension across files (e.g. every broken link `validate` reports). State the dimension and the file list up front; anything requiring per-document judgement is one run per document.
- **Improvement direction**: extract what is wrong from the input. If absent, derive it only from concrete evidence (below) — never from taste, and never restyle a document that no evidence faults.
- **User emphasis**: what the user states is the highest-priority evidence, even when other parts of the document also look improvable.

## Workflow

### 1. Resolve the target and restate it

Read the document in full before editing, and restate which single file you resolved plus what will change — so a mis-resolution surfaces before any write. Note its language and local conventions (many documents here are Chinese; heading depth, table style, and link style are per-directory conventions that outrank any template).

### 2. Gather evidence (deterministic sources first)

Prefer machine findings and quoted reader failures over impressions:

```bash
python3 ${SKILL_WORKDIR}/.specify/scripts/python/docs-utils.py --action validate --root .   # broken links, oversize root entry, ADR gaps, notes frontmatter
python3 ${SKILL_WORKDIR}/.specify/scripts/python/docs-utils.py --action scan --root .       # notes lifecycle state
python3 ${SKILL_WORKDIR}/.specify/scripts/python/feedback-utils.py --action list --contains "<topic>"
python3 ${SKILL_WORKDIR}/.specify/skills/create-pages/scripts/scaffold-hugo.py --action build --root .   # only if a site layer exists — content that breaks rendering
```

Other admissible evidence: a `/speckit.review` finding, a `memory-recall` hit, a distilled `.specify/history/` lesson, a user correction in this session, or a **verified** staleness signal — a path, command, flag, count, or version the document asserts that no longer holds. Verify each such claim against the repository (does the path exist? does `--help` still list the flag?) and record what you checked.

**Unobserved is a valid finding.** If nothing concrete faults the document, say so and stop; do not manufacture improvements.

### 3. Classify the improvement

Each class carries a different verification obligation:

| Class | Typical change | Verification consequence |
|-------|----------------|--------------------------|
| **Accuracy correction** | wrong path, command, flag, name, or claim | Re-verify against the repo; never replace one unverified claim with another |
| **Staleness refresh** | stale counts, versions, removed features, renamed concepts | Re-measure from the source of truth; prefer a derivable statement over a hard-coded number that will rot again |
| **Completeness gap** | missing prerequisite, edge case, failure mode, or "why" | Add only evidence-supported content; no speculative sections |
| **Readability restructure** | reorder sections, add a table, cut padding | Every load-bearing fact must survive; changed headings change anchors — repair inbound links in the same run |
| **Link / anchor repair** | broken relative link, renamed heading | `docs-utils.py --action fix-links --root .` (dry-run first, then `--apply`); re-run `validate` |
| **Render defect** | content breaks the site build (bad code-fence attributes, unsafe HTML) | Fix the **content**; never loosen the site config to accommodate broken source. Re-run the build |
| **Oversize relief** | a root entry exceeds the one-screen rule, or a page is unnavigable | Sink detail into the typed `docs/` tree — the *destination file* is `create-docs` work; hand off |
| **Notes promotion** | a `draft` note has matured into a formal fact | Merge the content into its `target`; the note's archive move and status flip on disk are `create-docs` work |
| **Decision supersession** | a recorded decision is obsolete | **Annotate** `Deprecated` / `Superseded by`; never rewrite or delete decision history |

### 4. Apply the minimal section-level edit

Change only what the evidence supports; preserve every untouched section verbatim, including its wording, ordering, and language. Keep the document's own voice — an improvement is not a rewrite. If a fact must be removed, replace it with the corrected fact or an explicit annotation; never leave a silent hole.

### 5. Verify

- Re-run `docs-utils.py --action validate --root .` → the target's findings are gone and **no new violation** appears anywhere.
- If the site layer is scaffolded, re-run the Hugo build → still green.
- Re-read the edited sections against the evidence list: every finding is either fixed or explicitly deferred with a reason.

### 6. Record and report

Append the audit entry so the change is traceable next to the space's other convergence records:

```bash
python3 ${SKILL_WORKDIR}/.specify/scripts/python/docs-utils.py --action audit --root . \
  --scope improve-docs --summary "<one-line>"
```

Report: the document changed, the evidence behind each edit, class per edit, before → after for every factual change, verification results, and any **hand-off to `create-docs`** (moves, new files, archiving) or residual the user must decide.

## Constraints

- **One document per run** — or one explicitly bounded, single-dimension batch. Improving several documents by judgement is several runs. The one exception is **mandated collateral repair**: when an edit changes a heading or anchor, repairing the inbound links in other files belongs to the *same* run — leaving them broken to honour the one-document rule is a misreading, not compliance.
- **Never create, move, rename, or archive** a document here — that is `create-docs`. Report the need instead. This governs **documents**: the audit entry and the feedback record written by the engines in steps 6 and Feedback are expected run outputs, not document creation.
- **Never rewrite decision history.** Obsolete decisions are annotated (`Deprecated` / `Superseded by`), never edited into a different decision or deleted.
- **Never delete content as an improvement.** Superseded prose is corrected or annotated; removal at file scope goes through `create-docs` (archive-not-delete).
- **Never assert what you did not verify.** An unverifiable claim is either dropped with a note or marked as needing confirmation — do not launder a guess into documentation.
- **Never edit a generated file or a mirror.** Files carrying an `AUTO-GENERATED` header, `.specify/**` mirrors, and per-tool command copies are outputs: fix the canonical source, then run `python3 scripts/python/sync-mirrors.py --write`.
- **Never touch non-document managed state as documentation.** `.specify/docs/target-structure.md` is a **cross-run non-document contract**: read only when context requires it and **never edit** it. `.specify/docs/plans/` and `.specify/docs/audit/` are run artifacts; `.specify/memory/**` is machine-managed data; `docs/public/` is generated presentation output.
- **Never restyle without a finding.** Cosmetic churn on an unfaulted document is a violation of the anti-churn discipline, not an improvement.
- **Reserved filenames stay reserved** (`README.md` / `ARCHITECTURE.md` / `CONTRIBUTING.md` / `CHANGELOG.md` at the root only; directory indexes are `index.md`).
- **Do not improve this skill or `create-docs` here** → `improve-skills`.

## Resource ID

- Canonical ID: `<SKILL:.specify/skills/improve-docs/SKILL.md>`
- Canonical Path: `.specify/skills/improve-docs/SKILL.md`

## Path Conventions

- `${SKILL_HOME}/<relative-path>` — Skill-owned resources (none currently; this skill drives project engines).
- `${SKILL_WORKDIR}/<relative-path>` — runtime/user-facing paths (the documents being improved, the engines invoked).

## Resources

| Path | Contents |
|------|----------|
| `.specify/skills/create-docs/SKILL.md` | Desired-state baseline (taxonomy, reserved names, notes lifecycle) — the structural authority this skill must not violate |
| `.specify/scripts/python/docs-utils.py` | Deterministic findings: `validate`, `scan`, `fix-links`, `audit` |
| `.specify/skills/create-pages/scripts/scaffold-hugo.py` | Site build check (`--action build`) for render defects — only when the optional site layer is installed |
| `.specify/scripts/python/feedback-utils.py` | Recorded feedback digest (`--action list --contains`) |
| `.specify/shared/patterns/reconcile-pattern.md` | Tolerance-band and anti-churn semantics shared with `create-docs` |

## Self-Improvement Alignment

The document being edited is not an Execution Subject by default, so this flow is Assisted Improvement of a Harness asset, even when the document reports its own validation results. Do not install self-modifying behavior in the document. This `improve-docs` Skill is itself an Execution Subject: qualified evidence from its own completed runs may enter `.specify/shared/workflow/self-improvement-workflow.md` and route to `improve-skills`.

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:improve-docs" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
