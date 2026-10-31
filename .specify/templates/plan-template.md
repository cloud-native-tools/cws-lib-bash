# Implementation Plan: [SPEC]

**Branch**: `[###-spec-name]` | **Date**: [DATE] | **Spec**: [link]
**Requirement → Feature**: `[REQUIREMENTS_KEY]` → Feature [FEATURE_ID] [FEATURE_NAME]
**Input**: Specification from `.specify/specs/[REQUIREMENTS_KEY]/requirements.md`

**Note**: This template is filled in by the `/speckit.plan` command, which **replaces** every `[PLACEHOLDER]` token in place — it MUST NOT append a second copy of this template below the filled content. See the `/speckit.plan` command for the execution workflow.

## Summary

[Extract from spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]  
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]  
**Storage**: [if applicable, e.g., PostgreSQL, CoreData, files or N/A]  
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]  
**Target Platform**: [e.g., Linux server, iOS 15+, WASM or NEEDS CLARIFICATION]
**Project Type**: [single/web/mobile - determines source structure]  
**Performance Goals**: [domain-specific, e.g., 1000 req/s, 10k lines/sec, 60 fps or NEEDS CLARIFICATION]  
**Constraints**: [domain-specific, e.g., <200ms p95, <100MB memory, offline-capable or NEEDS CLARIFICATION]  
**Scale/Scope**: [domain-specific, e.g., 10k users, 1M LOC, 50 screens or NEEDS CLARIFICATION]

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

<!--
  ACTION REQUIRED for /speckit.plan:
  Do NOT hard-code principle names here. Instead, read `.specify/memory/constitution.md`,
  enumerate every heading matching `### <roman-or-arabic-numeral>. <name>` (e.g.
  `### I. Template-First Architecture`, `### IV. Test-First Development`), and render
  ONE row in the table below per principle in the exact order they appear in the
  constitution. Include the principle's NON-NEGOTIABLE / MANDATORY annotation verbatim
  when present. This avoids the drift documented in the constitution's Sync Impact Report.

  Each row must contain:
  - Principle (verbatim heading without the leading `### N.`)
  - Compliance ("✅ Pass" / "❌ Fail" / "⚠ Partial — see Complexity Tracking")
  - Evidence (one-line citation pointing at the design artefact that demonstrates compliance)
-->

**Core Principles Compliance** (rendered from `.specify/memory/constitution.md`):

| # | Principle | Compliance | Evidence |
|---|-----------|------------|----------|
| I | [PRINCIPLE_1_NAME] [NON-NEGOTIABLE?] | ✅ Pass / ❌ Fail / ⚠ Partial | [one-line evidence: file or section] |
| II | [PRINCIPLE_2_NAME] [NON-NEGOTIABLE?] | ✅ Pass / ❌ Fail / ⚠ Partial | [...] |
| ... | [continue for every principle declared in constitution.md] | | |

**Gates Status**: [✅ All gates pass / ❌ Specific gate failures with justification — list failing principle numbers and link to Complexity Tracking row]

**Re-check after Phase 1**: [Date and short note when the post-design re-check was run; copy the same table refreshed against the design artefacts]

## Decision Tensions

*Owner of the record shape, the admissibility criteria, the rejection forms and the load-bearing
threshold: `.specify/shared/guidelines/decision-tension.md` — one pointer, read from the repository
root (the same form this template uses for `.specify/memory/constitution.md`); a plan artifact lives
under `.specify/specs/<key>/`, so a plan-directory-relative link would resolve to a path that does
not exist. This section lists the field names and points at that file — it MUST NOT restate the
criteria table, the rejection list or the threshold table.*

Fields: `decision`, `antithesis`, `binding_constraints` (with `pole_a` and `pole_b`),
`discriminating_evidence`, `expected_sacrifice`, `revision_trigger`; record identifier `tension_id`
(`T-NNN`).

Every record is carried by a level-3 sub-section whose heading begins with `T-NNN`
(e.g. `### T-001 — <one-line title>`), and its six fields are written in the owner's shape.

If and only if this plan contains no load-bearing decision, write the literal `N/A` plus one line
per trigger explaining why that trigger does not hold (the trigger list is owned by the owner's
threshold section); the section MUST NOT be deleted or left empty.

## Project Structure

### Documentation (this spec)

```text
.specify/specs/[REQUIREMENTS_KEY]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command) — see note below
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
├── feature-ref.md       # Phase 1 output (/speckit.plan command)
├── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
└── verification.md     # Implementation output (/speckit.implement command)
```

<!--
  research.md conditional guidance:
  Produce `research.md` as a standalone file when Phase 0 research exceeds ~50 lines
  or involves external source evaluation (API docs, vendor comparisons, benchmark data).
  When Phase 0 findings are brief (< 50 lines) and fully resolvable from internal
  investigation (project docs, constitution, existing code), inline them into plan.md
  under the `## Phase 0: Research Review` heading and note in this tree:
  "No standalone research.md — findings inlined below."
-->

### Source Code (repository root)
<!--
  ACTION REQUIRED:
  Document ONLY the directories actually changed or created by THIS spec, with a
  one-line purpose per directory. Do NOT invent a generic layout, and do NOT paste
  a "Single project / Web / Mobile" stub if it does not reflect this project.

  Examples of valid shapes (see `.specify/templates/examples/structure-*.md` if
  shipped, otherwise infer from the repo):
    - Single application:           src/, tests/
    - Web app:                      backend/, frontend/
    - Mobile + API:                 api/, ios/ or android/
    - Library / SDK:                src/<package>/, examples/, tests/
    - Monorepo:                     packages/<name>/, apps/<name>/
    - Container-image factory:      images/, script/snippets/, script/build/
    - Code generator / framework:   templates/, scripts/, src/<package>/

  If your project does not match any of these, document what is true. The goal is
  evidence-faithful structure, not adherence to a fixed taxonomy.

  MIRROR OBLIGATIONS: if any changed file has mirrors or generated runtime copies
  (dual-written template dirs, per-tool command copies, script mirrors), list EVERY
  copy explicitly in this tree — missed mirrors are the highest-frequency rework
  source during implementation.
-->

```text
[REPLACE THIS BLOCK with the real directories changed by this spec, one line per dir,
 each followed by `# <one-line purpose>`. Keep it terse — do not enumerate every file.]
```

**Structure Decision**: [Name the shape this spec actually lands in (e.g. "extends the
existing container-image factory by adding two new snippets under
`script/snippets/docker/config/users/` and weaving them into 19 daemon images") and
reference the real directories captured above. Explicitly note any new top-level dir.]

### Mirror Obligations *(mandatory when any changed file has mirrors or generated copies)*

<!--
  ACTION REQUIRED: for every source file this spec touches that has mirrors or
  generated runtime copies (dual-written template dirs, skills/ ↔ .specify/skills/,
  shared/ ↔ .specify/shared/, per-tool command copies, script mirrors), list EVERY
  affected copy as a first-class design output. /speckit.tasks turns each row into a
  paired dual-write + diff-verify task; /speckit.implement checks every row off.
  Delete this section only when the spec touches NO mirrored surface.

  The live mirror pairs are defined in scripts/python/sync-mirrors.py MIRROR_PAIRS —
  consult it, not memory. NOTE: `.specify/templates/commands/` is RETIRED (the
  templates pair excludes commands/); command templates fan out ONLY to the
  regen-command-copies.py per-tool copies listed below.

  BASELINE DRIFT: a Verify cell is an expected result, and expected results are
  measured, never pre-written. Run the mirror check once BEFORE the edit, record the
  drift it already reports, and state the criterion as "no NEW drift on the mirror
  pairs this spec touches". An absolute pass criterion (a bare exit code or "all
  green") is unpassable whenever unrelated drift predates this spec — writing it down
  anyway ships a criterion nobody measured and forces a correction pass at
  implementation time.
-->

| Source file (edited) | Mirror / generated copies (must land identically) | Verify |
|----------------------|---------------------------------------------------|--------|
| [e.g. `templates/commands/x.md`] | [e.g. `.claude/commands/speckit.x.md`; `.github/prompts/speckit.x.prompt.md`; `.qoder/commands/speckit.x.md`; `.opencode/command/speckit.x.md` — per-tool copies via regen-command-copies.py; NO `.specify/templates/commands/` mirror (retired)] | [e.g. `diff -q` on the pairs touched here, judged against the baseline measured before the edit — "no NEW drift"; regenerated copies contain the edit. Never a pre-written exit code] |

## Document Structure

<!--
  ACTION REQUIRED (expression-class lines only): replace every [<placeholder>] below, or delete
  this whole section. Delete it also when this line declares no class.

  OWNERSHIP: this template is the **producer** of the skeleton, so the literals are written here
  verbatim — the chapter heading `## Document Structure` and its four subsections `### Chapter Tree`,
  `### Reader Baseline`, `### Evidence List`, `### Fact Owners`. Read them from this file, not from
  another project's spec artifacts: `[[STR-NNN]]` ids are a per-spec namespace, so a downstream
  project that went looking for `[[STR-002]]`…`[[STR-006]]` in its own § Shared Strings would find
  unrelated literals or nothing at all.
  The semantics, and the code-first owner of the grammar, are
  `scripts/python/doc-consistency-check.py` (`STRUCTURE_HEADING`, `STRUCTURE_SUBSECTIONS`,
  `CHAPTER_TREE_COLUMNS`, `EVIDENCE_LIST_COLUMNS`, `FACT_OWNERS_COLUMNS`,
  `READER_BASELINE_MARKERS`); a checker consumes those constants, never a copied heading.
  A feature spec that keeps its own Shared Strings table MAY cite this section by its STR ids —
  that is a per-spec convenience and never the owner.

  CLASS CONDITION: 表达类 MUST 产出该章节、执行类 MUST NOT 被要求产出 — this section is a required
  plan output for an expression-class line, and it MUST NOT become a new mandatory section for an
  execution-class line (that would contradict the zero-change guarantee for execution-class lines).

  JUDGEMENT: `doc-consistency-check.py --action structure --spec-dir <spec dir>` reads this section;
  a missing chapter is `document-structure-missing` and a missing subsection is `subsection-missing`.
  Add `--path <delivered document>` to compare the delivered document's top-level chapters against
  the Chapter Tree; without it the run says `two-way: not-run` and MUST NOT be read as two-way pass.
-->

### Chapter Tree

*The single structural source for the delivered document: every chapter planned here MUST appear in
the delivered document, and a delivered top-level chapter absent from this table is
`chapter-unexpected`. `父节` takes the top-level marker `—` or the name of another row of this table.*

| 节名 | 父节 | 目的 | 边界 |
|------|------|------|------|
| [<chapter name>] | — | [<the decision the reader must be able to make after this chapter>] | [<what this chapter does not cover>] |
| [<chapter name>] | [<another row's chapter name>] | [<...>] | [<...>] |

### Reader Baseline

**Readers**: [<the baseline reader — reuse `shared/guidelines/user-facing-comprehension.md` § 基准读者与覆盖协议; do NOT invent a second definition>]
**Reading scenario**: [<the reading situation this document is written for>]

### Evidence List

*One row per factual assertion the delivered document will carry. Grade, as-of and source are a
triple: `shared/workflow/expression-gates.md` § 证据分级与 as-of owns the vocabulary and the
marriage rule, so this table only repeats the four columns.*

| 断言 | 证据等级 | as-of | source |
|------|----------|-------|--------|
| [<assertion>] | [<grade>] | [<YYYY-MM-DD>] | [<path, command or URL the grade rests on>] |

### Fact Owners

*Each fact has exactly one owner. Two rows owning the same fact is `owner-duplicate`; an owner path
that does not exist in the repository is `owner-path-missing`; an empty anchor is
`owner-anchor-missing`.*

| 事实 | owner 路径 | 章节锚 |
|------|------------|--------|
| [<fact>] | [<repository-relative owner path>] | [<§ section anchor in that owner>] |

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**
> If no violations, explicitly write "N/A" and remove the table.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |

## Phase 1: Design Artifacts Summary

<!--
  ACTION REQUIRED (backfill ONLY — delete this comment when filling):
  Fill this section AFTER the Phase 1 artifacts (data-model.md, contracts/,
  quickstart.md, feature-ref.md) have landed on disk — never pre-write counts
  here. Record the actual artifact inventory: entity count, contract count and
  names, quickstart scenario count, and any drift from the Phase 0 expectation.
  Summarize after, not before: pre-written counts routinely drift from the
  actual output and force a correction pass.
  Every derived command printed here MUST have been actually run with its real
  output pasted, and every count taken from that output — never from memory;
  where a count comes from a pattern match, state whether that pattern can also
  match non-target lines. (The run-and-paste duty for EVERY emitted command
  example, declared expected results included, is owned by the execution-verify
  rule in `/speckit.plan`'s Post-Generation Quality Gate
  (`templates/commands/plan.md`) — this note is only its count-taking
  specialization.)
-->

| Artifact | Path | Count / Scope |
|----------|------|---------------|
| [e.g. Data model] | [`data-model.md`] | [N entities] |
| [e.g. Contracts] | [`contracts/`] | [N files: names] |
| [e.g. Quickstart] | [`quickstart.md`] | [N scenarios] |
