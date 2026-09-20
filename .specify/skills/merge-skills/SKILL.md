---
name: merge-skills
description: This skill merges one skill into another by decomposing the source skill's content and re-expressing it in the target skill's own conventions — never a raw folder merge — so the target fully covers the source and can replace it in every scenario, then decommissions the source's independent wiring. Use this when the user mentions ["合并技能", "技能合并", "把这个技能合并到", "归并技能", "整合技能", "技能下线合并", "吸收技能", "merge skill", "merge skills", "consolidate skills", "fold skill into", "absorb skill into", "combine skills"]
skill_id: "<SKILL:.specify/skills/merge-skills/SKILL.md>"
---

# merge-skills

## Goal

Merge a **source** skill into a **target** skill so the target ends up **functionally covering** the source: every scenario that used to invoke the source can be served by the merged target, and the source no longer needs to exist as an independent skill.

The defining constraint — and the reason this is not a `cp -r` / folder merge — is **content-preserving, form-discarding**:

- **Preserve content**: every capability, fact, parameter, enumerated value, and workflow the source carried survives the merge.
- **Discard form**: the source's *structure* (its file layout, doc format, frontmatter, naming) is thrown away and the content is **re-expressed in the target skill's own conventions** (its reference-doc granularity, table idioms, frontmatter shape, cross-reference style, danger-op conventions).

A merge is complete only when (a) a coverage check proves no content was lost, and (b) the source's independent wiring is decommissioned so it stops competing for the same triggers.

Goal anchor (Constitution Principle XIII — Better-Harness): consolidating two overlapping skills into one strengthens **Controlled Execution** (one authoritative path instead of two drifting ones) and reduces trigger ambiguity; goal model in `.specify/shared/guidelines/better-harness.md`.

## Input Contract

Resolve two skills and one relationship before editing:

- **Source skill** (merged *from*, then decommissioned): identify by `skill_id`, frontmatter `name`, canonical path, or directory. It may be a peer skill, a global/library skill, or an **externally-managed** marketplace/upstream skill — this classification decides the decommission scope (see Phase 6).
- **Target skill** (merged *into*, survives and grows): identify the same way. It MUST already exist; if the user names a non-existent target, this is not a merge — redirect to `create-skills`.
- **Merge intent**: full absorption (source disappears) is the default. If the user wants the source to keep existing, that is not this skill — route to `improve-skills` (borrow one capability) instead.

If either skill cannot be resolved uniquely, or source and target resolve to the same skill, ask **one** targeted clarification before touching any file. Never guess the direction — merging A→B and B→A produce opposite decommission targets.

## Workflow

Overall shape: **survey (1) → extract (2) → plan (3) → rewrite (4) → prove coverage (5) → wire target (6) → decommission source (7) → verify & report (8)**. Phases 4–5 are the load-bearing loop; Phase 5 is the gate that separates a real merge from a lossy one.

### 1. Survey both skills

- **Target conventions (do this first, it governs everything downstream)**: read the target's `SKILL.md` and **1–2 of its existing `references/` docs** as the format template — note its reference-doc granularity (one topic per file? how large?), table idioms, frontmatter keys, danger-op/confirmation口径, and cross-reference style. The merged content must look like it was always part of the target.
- **Source inventory**: list the source's files and classify its content *form* (Markdown prose, HTML docs, scripts, assets) and *content* (capabilities, commands, facts, enums). Measure size to plan the extraction.
- **Relationship & decommission scope**: determine whether the source is a peer/global skill (profiles-managed, fully decommissionable) or an externally-managed marketplace/upstream entity (content absorbed, but the upstream entity is **left intact** — only the local wiring is removed). Record which.

Detail & the survey checklist: [`./references/restructure-mapping.md`](./references/restructure-mapping.md) `## 1. Survey`.

### 2. Extract source content into neutral material

Convert the source's content into a neutral, readable intermediate (scratch, **not** committed to the target) so it can be reorganized freely:

- Markdown source → usually already neutral; read directly.
- HTML / rich formats → convert to Markdown with a deterministic tool (program-first — do not hand-transcribe). Example converter and the extraction recipes: [`./references/content-extraction.md`](./references/content-extraction.md).
- Scripts / assets → inventory their behavior; scripts usually move into the target's `scripts/` largely intact (form is already code, not doc prose).

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

Do not proceed to decommission while real content is still unaccounted for. Token classes and the lowercase-enum limitation, exit codes, the allow-file and both-direction recipes: [`./references/coverage-verification.md`](./references/coverage-verification.md).

### 6. Wire the target (self-references)

Make the target's own metadata reflect its grown scope:

- Confirm `SKILL.md` `description` now carries the source's trigger keywords (from Phase 4).
- Confirm resource table lists the new reference docs; add intent-guide / cross-reference pointers where the target uses them.
- If the target has a mirror discipline (spec-kit `skills/` ↔ `.specify/skills/`), do NOT hand-copy — the mirror sync in Phase 8 handles it.

### 7. Decommission the source as an independent skill

A merge that leaves the source wired still has two skills competing for the same triggers. Remove the source's **independent existence**, scoped by the Phase-1 classification:

- **Form carriers**: once Phase 5 passes, remove any raw source files that were staged into the target (prefer `git rm` — recoverable via history).
- **Wiring & registration cleanup** (host-specific — **delegate, do not hardcode paths**): symlinks in agent load directories, registry rows, database records, and topology docs that made the source independently discoverable. In an environment with an agent-management skill/scripts (e.g. a `manage-agents`/`profiles-agents` front door), delegate this cleanup to it rather than reinventing per-agent paths.
- **Declarations that name the source by slug** — these must be **moved to the target**, not merely deleted: agent skill declarations (`skills:` frontmatter and any skill-enablement table — a dangling slug both silently strips the capability from that agent and fails the host's skill-enablement contract), and, when the host repo ships an obsolete-asset reclaim registry, the retired name registered there (spec-kit: `_OBSOLETE_SKILLS`). An unregistered retirement is resurrected by the next `specify init`, because the additive copy never deletes.
- **Boundary — leave externally-managed entities intact**: if the source is a marketplace/upstream skill, its upstream entity is self-managed; remove only the **local wiring** that pointed at it, never the upstream source.
- **Danger-op discipline**: symlink removal, DB row deletion, and registry edits are destructive and irreversible — confirm the target list with the user before executing, and back up any DB/registry before editing.

Decommission playbook (classification → cleanup surfaces → boundary → topology sync): [`./references/decommission-and-wiring.md`](./references/decommission-and-wiring.md).

### 8. Verify, sync mirrors, and report

- **Coverage**: the Phase-5 probe exits `0` in **both** directions (source→target and pre-merge-target→target), with every allow-file entry reported as an accepted false positive and its reason.
- **Links & residue**: the target's internal links resolve; no dangling reference to a deleted source doc; **no residual reference to the old skill/form** anywhere in the target (grep the source name).
- **Declarations re-pointed**: no agent still declares the retired slug, and the host's skill-enablement / obsolete-asset contracts are green.
- **Mirror sync** (when the host keeps a canonical↔mirror pair, e.g. spec-kit `skills/` ↔ `.specify/skills/`): sync with the host's own tool, never by hand — command and drift re-check in [`./references/decommission-and-wiring.md`](./references/decommission-and-wiring.md) `## Mirror sync`.
- **Wiring health** (when decommission touched wiring): dangling-symlink scan returns zero, the target still resolves in every load directory, description-caching registries refreshed.
- **Cleanup** the Phase-2 scratch intermediate — **only after** the probe has passed; deleting it first leaves any re-run exiting `4` with no material to read.
- **Report**: what merged; the coverage result (tokens extracted / unresolved / allowed, with reasons); decommission scope — what was removed vs. deliberately left intact; which declarations were re-pointed to the target; and any follow-up.

## Design Principles

- **Content is sacred, form is disposable.** The merge is judged by coverage of content, never by preserving the source's file shapes.
- **Target conventions win.** When source and target formats disagree, the target's idiom always governs — the reader must not be able to tell the content was imported.
- **Prove, don't assert, no-loss.** The coverage probe is a gate, not a nicety; "I think I got everything" is not a completed merge.
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
- Retiring a source while an agent still declares its slug, or without registering the name in the host's obsolete-asset reclaim registry.
- Hardcoding profiles/host-specific wiring paths into this generic skill.
- Removing an externally-managed upstream entity that is not yours to delete.

## Resources

| Directory | Contents |
|-----------|----------|
| `${SKILL_HOME}/references/` | `restructure-mapping.md` — Phase 1 survey + Phase 3 source-block→destination mapping · `content-extraction.md` — Phase 2 form→neutral material, HTML converter · `coverage-verification.md` — Phase 5 no-loss gate: token classes, exit codes, allow-file, both-direction recipes · `decommission-and-wiring.md` — Phase 7 cleanup surfaces, boundary, danger ops, mirror sync |
| `${SKILL_HOME}/scripts/` | `coverage_probe.py` — fact-token coverage gate. Exit `0` pass · `2` usage · `3` unresolved misses · `4` gate did not run (no material read). `--allow FILE` records verified false positives |

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:merge-skills" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
