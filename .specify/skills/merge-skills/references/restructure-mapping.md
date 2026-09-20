# Survey & Mapping — fitting source content into the target's structure

Covers Phase 1 (survey) and Phase 3 (mapping) of the merge — the judgment work of deciding
*where* each piece of source content lands so the result reads as native to the target.

## 1. Survey

Before any extraction, characterize both skills. **The target's conventions govern the whole
merge**, so survey the target first and in depth.

### Target (the format authority)

Read the target's `SKILL.md` and **1–2 representative `references/` docs**, and record:

- **Reference-doc granularity**: does the target keep one topic per file? What's the typical
  file size (lines/kb)? This sets how finely the source content must be split.
- **Idiom**: tables vs. prose lists; how it marks pitfalls (`⚠️`), danger ops, and examples;
  bilingual headings or not; code-block conventions.
- **Frontmatter shape**: which keys the target uses (`name`, `description`, `skill_id`,
  `cli_version`, …) — the merge adds to `description`, never restructures frontmatter.
- **Cross-reference style**: relative links `./references/x.md`, an intent-guide table, a
  resource table in `SKILL.md`. New docs must plug into the same wiring.
- **Danger-op / confirmation口径**: how the target tells the agent to confirm destructive
  actions — merged content that carries destructive commands must adopt this wording.

### Source (the content to preserve)

- **File inventory + form classification** (see `content-extraction.md`): Markdown / HTML /
  scripts / assets / frontmatter.
- **Content inventory**: capability families, command groups, fact tables, enumerated values,
  workflows. This is the checklist Phase 5 later proves survived.
- **Trigger keywords** from the source's `description` — these must migrate into the target's
  `description` so the source's invocation scenarios now route to the target.

### Relationship (sets decommission scope — Phase 7)

| Source class | Content | Local wiring | Upstream entity |
|--------------|---------|--------------|-----------------|
| Peer / global skill (host-managed) | Absorb | Remove fully | n/a |
| Externally-managed marketplace / upstream skill | Absorb | Remove local wiring only | **Leave intact** (not yours to delete) |

Record the class explicitly; it is the single most consequential survey output.

## 2. Mapping

Produce an explicit **source-block → target-destination** map before writing a line. Every
source content-block must have a named destination; a block with no home is a coverage gap
surfaced now (cheap) instead of after deletion (expensive).

### Choosing destinations

- **Split by topic to match the target's granularity.** If the target keeps ~150–300-line
  single-topic reference docs, a large source doc-site splits into several such docs, not one
  giant import. (Real example: a 17-file HTML doc site → four topic-scoped reference docs.)
- **Name per the target's convention.** Prefix/namespace new docs so they read as the
  target's own (e.g. `<source-domain>-<topic>.md`), matching sibling names.
- **Prefer absorbing into an existing target doc** when the content is a natural extension of
  one — only create a new doc when the topic is genuinely distinct.
- **Scripts** land in the target's `scripts/`; **assets** are dropped unless referenced.

### Where the triggers and self-references go

- Source capability + trigger keywords → target `SKILL.md` `description` (capability + triggers
  only; never a workflow summary — that makes the agent skip the body).
- New reference docs → target `SKILL.md` resource table + any intent-guide/cross-ref table.
- If two skills had a division-of-labor note, add a one-line pointer in the target explaining
  how the absorbed area relates to the target's existing areas.

### Mapping record (keep it visible during Phase 4)

A simple table is enough:

| Source block (from scratch material) | Destination in target | New or existing |
|---------------------------------------|------------------------|-----------------|
| `auth.md` (rate-limit + tokens) | `references/<domain>-openapi.md` §Auth | new |
| `skill-api.md` (resource endpoints) | `references/<domain>-skill-api.md` | new |
| `overview.html` intro | folded into new doc headers | new |
| `scripts/foo.py` | `scripts/foo.py` (as-is) | moved |

This table is also the input to the Phase-5 coverage check: if the probe flags a token, trace
it back to its source block and confirm the destination actually received it.
