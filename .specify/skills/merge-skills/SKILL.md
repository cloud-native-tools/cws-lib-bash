---
name: merge-skills
description: This skill merges one skill into another by decomposing the source skill's content and re-expressing it in the target skill's own conventions — never a raw folder merge — so the target fully covers the source and can replace it in every scenario, then decommissions the source's independent wiring. Use this when the user mentions ["合并技能", "技能合并", "把这个技能合并到", "归并技能", "整合技能", "技能下线合并", "吸收技能", "merge skill", "merge skills", "consolidate skills", "fold skill into", "absorb skill into", "combine skills"]
skill_id: "<SKILL:.specify/skills/merge-skills/SKILL.md>"
classification: external
---

# merge-skills

## Goal

Merge a **source** skill into a **target** skill so the target ends up **functionally covering** the source: every scenario that used to invoke the source can be served by the merged target, and the source no longer needs to exist as an independent skill.

The defining constraint — and the reason this is not a `cp -r` / folder merge — is **content-preserving, form-discarding**:

- **Preserve content**: every capability, fact, parameter, enumerated value, and workflow the source carried survives the merge.
- **Discard form**: the source's *structure* (its file layout, doc format, frontmatter, naming) is thrown away and the content is **re-expressed in the target skill's own conventions** (its reference-doc granularity, table idioms, frontmatter shape, cross-reference style, danger-op conventions).

A merge is complete only when (a) a coverage check proves no content was lost, (b) the source's independent wiring is decommissioned so it stops competing for the same triggers, and (c) the target **commits the proof** — a capability-inheritance record plus frozen coverage baselines under its own `references/`, so a later session can re-check that the target still does what its sources did.

Goal anchor (Constitution Principle XIII — Better-Harness): consolidating two overlapping skills into one strengthens **Controlled Execution** (one authoritative path instead of two drifting ones) and reduces trigger ambiguity; goal model in `.specify/shared/guidelines/better-harness.md`.

## Input Contract

Resolve two skills and one relationship before editing:

- **Source skill** (merged *from*, then decommissioned): identify by `skill_id`, frontmatter `name`, canonical path, or directory. It may be a peer skill, a global/library skill, or an **externally-managed** marketplace/upstream skill — this classification decides the decommission scope (see Phase 6).
- **Target skill** (merged *into*, survives and grows): identify the same way. It MUST already exist; if the user names a non-existent target, this is not a merge — redirect to `create-skills`.
- **Merge intent**: full absorption (source disappears) is the default. If the user wants the source to keep existing, that is not this skill — route to `improve-skills` (borrow one capability) instead.

If either skill cannot be resolved uniquely, or source and target resolve to the same skill, ask **one** targeted clarification before touching any file. Never guess the direction — merging A→B and B→A produce opposite decommission targets.

## Workflow

Overall shape: **survey (1) → extract (2) → plan (3) → rewrite (4) → prove coverage (5) → wire target & record inheritance (6) → decommission source (7) → verify & report (8)**. Phases 4–5 are the load-bearing loop; Phase 5 is the gate that separates a real merge from a lossy one; Phase 6 is what makes that verdict survive the merge.

### 1. Survey both skills

- **Target conventions (do this first, it governs everything downstream)**: read the target's `SKILL.md` and **1–2 of its existing `references/` docs** as the format template — note its reference-doc granularity (one topic per file? how large?), table idioms, frontmatter keys, danger-op/confirmation口径, and cross-reference style. The merged content must look like it was always part of the target.
- **Source inventory**: list the source's files and classify its content *form* (Markdown prose, HTML docs, scripts, assets) and *content* (capabilities, commands, facts, enums). Measure size to plan the extraction. Enumerate the source's **capability families** explicitly — what a user could ask it to do — because each one becomes a row of the Phase-6 inheritance record, and a family nobody enumerated is a family nobody later checks.
- **Relationship & decommission scope**: determine whether the source is a peer/global skill (profiles-managed, fully decommissionable) or an externally-managed marketplace/upstream entity (content absorbed, but the upstream entity is **left intact** — only the local wiring is removed). Record which.

Detail & the survey checklist: [`./references/restructure-mapping.md`](./references/restructure-mapping.md) `## 1. Survey`.

### 2. Extract source content into neutral material

Convert the source's content into a neutral, readable intermediate (scratch, **not** committed to the target) so it can be reorganized freely:

- Markdown source → usually already neutral; read directly.
- HTML / rich formats → convert to Markdown with a deterministic tool (program-first — do not hand-transcribe). Example converter and the extraction recipes: [`./references/content-extraction.md`](./references/content-extraction.md).
- Scripts / assets → inventory their behavior; scripts usually move into the target's `.specify/scripts/` largely intact (form is already code, not doc prose).

Land the intermediate under a scratch dir (e.g. `${SKILL_WORKDIR}/tmp/merge-<source>/`); it is working material, cleaned up in Phase 8.

### 3. Plan the target-conformant structure

Decide how source content maps into the target's structure **before writing**:

- Which **new reference docs** to create (named per the target's convention, one topic each, sized like the target's siblings), and which existing target docs absorb which source fragments.
- Which **SKILL.md** edits the target needs: description/trigger-keyword additions (so the source's triggers now route to the target), resource-table rows, intent/cross-ref pointers.
- The mapping is explicit: every source content-block → a named destination in the target. A block with no destination is a coverage gap caught now, not after deletion.

Mapping heuristics (granularity, naming, where triggers go): [`./references/restructure-mapping.md`](./references/restructure-mapping.md) `## 2. Mapping`.

### 4. Rewrite (decompose & restructure)

Author the destination docs in the **target's idiom**, not the source's:

- Re-express content as the target does (tables over prose lists if that's the target's style, `⚠️` callouts for pitfalls, the target's danger-op confirmation wording, its cross-reference format).
- Work doc-by-doc from the Phase-2 intermediate; keep each new reference doc a single-topic contract sized like the target's existing references.
- Add the planned `SKILL.md` edits: fold the source's capability + trigger keywords into the target's `description` (capability + triggers only — never a workflow summary), and add resource-table / cross-ref entries.
- **Never copy the source's form carriers** (its HTML, its index pages, its frontmatter) into the target.

### 5. Prove coverage — the no-loss gate (mandatory)

This gate is what makes the merge trustworthy. Extract **fact tokens** from the Phase-2 source material (endpoints, flags, identifiers, UPPER-CASE enum values, status codes, inline code spans, URLs) and verify each appears in the rewritten target docs:

```bash
python3 ${SKILL_HOME}/scripts/coverage_probe.py <source-material-dir> <target-doc>...
```

- **The exit code decides the gate, not your impression.** Drive **unresolved** misses to zero. A miss that is a *verified false positive* (the fact survived under different wording) is recorded in an allow file with a one-line reason — **never** edit the target doc into containing a stale token just to make the probe pass.
- **A probe that read nothing is not a passed gate.** Exit `4` means the source material was missing or yielded zero tokens (typo'd scratch path, or Phase-8 cleanup already removed it): the gate did **not** run. Re-extract and re-run; never proceed to decommission on it.
- **Prove both directions.** Phase 3 edits *existing* target docs, so the target can lose its own facts while absorbing the source's. Re-run the probe with the pre-merge version of each edited target doc as the material.
- **Freeze the proof before the scratch dies.** At exit `0` in both directions, emit one baseline per source into the target — `--emit-baseline <target>/references/merge-provenance/<source>.baseline.txt`, with the same `--allow` file so its reasons travel along. It refuses while misses are unresolved: freezing a lossy state launders the loss into a "proven" baseline. Baselines are re-read verbatim, never re-extracted — recipe and the non-idempotence trap: [`./references/provenance-record.md`](./references/provenance-record.md) `## Freezing the baseline (Phase 5)`.

Do not proceed to decommission while real content is still unaccounted for. Token classes and the lowercase-enum limitation, exit codes, the allow-file and both-direction recipes: [`./references/coverage-verification.md`](./references/coverage-verification.md).

### 6. Wire the target and record the inheritance

Make the target's metadata reflect its grown scope, and commit what the merge proved:

- Confirm `description` now carries the source's trigger keywords (Phase 4), and the resource table lists the new reference docs **and the provenance record**; add intent-guide / cross-reference pointers where the target uses them.
- **Write the capability-inheritance record** into the target's `references/merge-provenance.md`: one `## Source:` section per absorbed skill (A+B→C writes two; a later merge appends rather than rewrites history), each with source identity, decommission class, retirement registration, the Phase-5 baseline path, a `**Corpus**` scope whenever several sources land in one target (an unscoped corpus lets a sibling's docs mask a fact this source lost), and one capability row per Phase-1 family — capability as the source served it → backticked destination in the target → how to verify → status. In the record, name this skill's `provenance_check.py` by its **resolved host path**: `${SKILL_HOME}` expands to the *target's* home there. Schema, status vocabulary, row granularity: [`./references/provenance-record.md`](./references/provenance-record.md).
- The target's method and flow may differ from the source's — that is the premise of a restructure. What a row may not lack is a destination or a verification cell: an uncheckable row is a description, not a checklist. `pending` is an open gap and blocks Phase 7.
- If the target has a mirror discipline (spec-kit `skills/` ↔ `.specify/skills/`), do NOT hand-copy — the Phase-8 sync handles it.

### 7. Decommission the source as an independent skill

A merge that leaves the source wired still has two skills competing for the same triggers. Remove the source's **independent existence**, scoped by the Phase-1 classification:

- **Form carriers**: once Phase 5 passes, remove any raw source files that were staged into the target (prefer `git rm` — recoverable via history).
- **Wiring & registration cleanup** (host-specific — **delegate, do not hardcode paths**): symlinks in agent load directories, registry rows, database records, and topology docs that made the source independently discoverable. In an environment with an agent-management skill/scripts (e.g. a `manage-agents`/`profiles-agents` front door), delegate this cleanup to it rather than reinventing per-agent paths.
- **Declarations that name the source by slug** — these must be **moved to the target**, not merely deleted: agent skill declarations (`skills:` frontmatter and any skill-enablement table — a dangling slug both silently strips the capability from that agent and fails the host's skill-enablement contract), and, when the host repo ships an obsolete-asset reclaim registry, the retired name registered there (spec-kit: `_OBSOLETE_SKILLS`). An unregistered retirement is resurrected by the next `specify init`, because the additive copy never deletes.
- **Boundary — leave externally-managed entities intact**: if the source is a marketplace/upstream skill, its upstream entity is self-managed; remove only the **local wiring** that pointed at it, never the upstream source.
- **Danger-op discipline**: symlink removal, DB row deletion, and registry edits are destructive and irreversible — confirm the target list with the user before executing, and back up any DB/registry before editing.

Decommission playbook (classification → cleanup surfaces → boundary → topology sync): [`./references/decommission-and-wiring.md`](./references/decommission-and-wiring.md).

### 8. Verify, sync mirrors, and report

- **Coverage**: the Phase-5 probe exits `0` in **both** directions (source→target and pre-merge-target→target), with every allow-file entry reported as an accepted false positive and its reason, and one baseline frozen per source.
- **Inheritance record re-verified**: `python3 ${SKILL_HOME}/scripts/provenance_check.py <target-skill-dir>` exits `0` on the canonical target copy. `3` reports drift whose findings each name their own repair; `4` means the gate **did not run** (no record, or zero parsed sources) and is never a pass. The mirror sync below then guarantees the installed copy carries the same record.
- **Links & residue**: the target's internal links resolve; no dangling reference to a deleted source doc; **no residual reference to the old skill/form** anywhere in the target (grep the source name).
- **Declarations re-pointed**: no agent still declares the retired slug, and the host's skill-enablement / obsolete-asset contracts are green.
- **Mirror sync** (when the host keeps a canonical↔mirror pair, e.g. spec-kit `skills/` ↔ `.specify/skills/`): sync with the host's own tool, never by hand — command and drift re-check in [`./references/decommission-and-wiring.md`](./references/decommission-and-wiring.md) `## Mirror sync`.
- **Wiring health** (when decommission touched wiring): dangling-symlink scan returns zero, the target still resolves in every load directory, description-caching registries refreshed.
- **Cleanup** the Phase-2 scratch — **only after** the record and baselines are committed and `provenance_check.py` exits `0`. A green probe is not enough: the allow file lives in scratch, so cleaning up on the probe alone destroys the only copy of the proof. Confirm both artifacts are tracked in the target, not left in a scratch or git-ignored workspace directory, then delete.
- **Report**: what merged; coverage (tokens extracted / unresolved / allowed, with reasons); the committed record — path, rows verified vs. dropped-with-reason, baseline token counts per source; the standing re-verification command with its resolved host path; decommission scope — removed vs. deliberately left intact; declarations re-pointed; follow-up.

## Design Principles

- **Content is sacred, form is disposable.** The merge is judged by coverage of content, never by preserving the source's file shapes.
- **Target conventions win.** When source and target formats disagree, the target's idiom always governs — the reader must not be able to tell the content was imported.
- **Prove, don't assert, no-loss.** The coverage probe is a gate, not a nicety; "I think I got everything" is not a completed merge.
- **The proof outlives the merge.** A verdict nobody can re-check is a memory, not a record. Commit the capability inheritance and the frozen baselines into the target so "C still covers A and B" stays falsifiable — after the scratch is deleted, and after the target goes on evolving without you.
- **Full replacement includes decommission.** Leaving the source wired means the merge did not actually consolidate anything.
- **Environment-agnostic core, delegated wiring.** This skill hardcodes no host-specific agent paths; wiring cleanup is delegated to the host's agent-management capability. Keep it portable.
- **Reversibility first.** Absorb-then-delete via `git rm`; back up registries/DBs; confirm destructive wiring changes. Never delete-and-drop.

## Anti-Patterns

- Folder merge: copying the source directory into the target's `references/` and calling it done (form preserved, not restructured).
- Deleting source content without a coverage proof (silent capability loss).
- Importing the source's format (HTML pages, its frontmatter, its index) into the target.
- Absorbing content but leaving the source's symlinks/registry rows live (two skills still compete).
- Reading a probe that found no material (exit `4`) as "coverage clean" — the gate never ran.
- Gaming the gate: editing the target until the probe passes, instead of recording a verified false positive with its reason.
- Offering a name-level "formerly A and B, merged with content preserved" note as the record — an assertion with nothing in it to re-check.
- Deleting the scratch on a green probe while the allow file, the only copy of the proof, still lives in it; or committing the record to a git-ignored workspace directory.
- Archiving the source's own docs into the target as evidence of coverage: form re-imported, and it verifies nothing — the checker excludes the record and baseline dir from its corpus by design.
- Emptying, deleting, or self-regenerating a baseline to reach a green re-verification: deleting a failing test, again.
- Retiring a source while an agent still declares its slug, or without registering the name in the host's obsolete-asset reclaim registry.
- Hardcoding profiles/host-specific wiring paths into this generic skill.
- Removing an externally-managed upstream entity that is not yours to delete.

## Resources

| Directory | Contents |
|-----------|----------|
| `${SKILL_HOME}/references/` | `restructure-mapping.md` — Phase 1 survey + Phase 3 source-block→destination mapping · `content-extraction.md` — Phase 2 form→neutral material, HTML converter · `coverage-verification.md` — Phase 5 no-loss gate: token classes, exit codes, allow-file, both directions · `provenance-record.md` — Phase 5 baseline freeze, Phase 6 record schema + capability rows, Phase 8 re-verification and its limits · `decommission-and-wiring.md` — Phase 7 cleanup surfaces, boundary, danger ops, mirror sync |
| `${SKILL_HOME}/scripts/` | `coverage_probe.py` — fact-token coverage gate: exit `0` pass · `2` usage · `3` unresolved misses · `4` gate did not run. Options: `--allow` verified false positives, `--emit-baseline` freeze the proven token set, `--baseline` re-verify later with no scratch. `provenance_check.py <target-skill-dir>` — re-checks a merged target's committed record: baselines clean, destinations resolve, no `pending` row, no unreasoned `dropped`: exit `0` holds · `2` usage · `3` drift or open gap · `4` did not run |

## Wrap-up

<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — truth source: .specify/shared/definitions/probe-definitions.md (## Handler / ## HandlerBinding) — fingerprint: 7877db82c58c — do not edit; edit the registry, then recompile -->

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills directory) — skip this entire Wrap-up step: no engine call, no feedback entry.

1. Run Determination — `python3 .specify/scripts/python/run-determination.py --action determine --unit-id "skill:merge-skills" --unit-type skill --run-id <RUN_ID> --complexity <COMPLEXITY>`；source args when available: `--session-file <SESSION_FILE> --session-rows <SESSION_ROWS> --tool <TOOL> --proxy-paths <PROXY_PATHS> --token-note <TOKEN_NOTE> --elapsed-ms <ELAPSED_MS> --elapsed-note <ELAPSED_NOTE> --names-current <NAMES_CURRENT> --names-baseline <NAMES_BASELINE> --declared-check <DECLARED_CHECK> --green-check <GREEN_CHECK> --red-first-refs <RED_FIRST_REFS> --collected <COLLECTED> --prev-user-turn-class <PREV_USER_TURN_CLASS> --unresolved-red <UNRESOLVED_RED> --red-source <RED_SOURCE>`
   尖括号为本轮运行时值——代入后照抄执行(占位 = 参数名去 --、转下划线、全大写;渲染集 = 引擎 manifest required + source,身份对已带实值)
2. Exec Quant — `python3 .specify/scripts/python/exec-quant.py --action collect --unit-id "skill:merge-skills" --unit-type skill`；source args when available: `--run-id <RUN_ID>`
3. Feedback Record — `python3 .specify/scripts/python/feedback-utils.py --action record --unit-id "skill:merge-skills" --unit-type skill --run-id <RUN_ID> --review <REVIEW> --points <POINTS>`
4. Threshold Notice — `.specify/shared/workflow/feedback-step.md` § "Threshold prompt protocol (canonical semantics for step 6)"
5. Token Reflection — `.specify/shared/workflow/feedback-step.md` § "Reflection procedure (the embedded step points here)"
