# Provenance Record — the capability inheritance the target commits (Phases 5, 6, 8)

A merge proves no-loss **once**, at merge time, against scratch material that Phase 8 then
deletes. The proof dies with it. What survives in the target is usually a name-level note —
"Formerly A and B, merged with content preserved" — and that is an **assertion of no-loss**,
which is precisely what this skill forbids asserting. Nobody can re-check it: not the next
session, not the improve-skills loop that restructures the target a month later, not the user
asking "can C still do what A did?".

So the merge commits its proof into the target. Two artifacts, both under the target's own
`references/`, both tracked:

| Artifact | Role |
|----------|------|
| `references/merge-provenance.md` | The **capability inheritance record**: who was absorbed, what each could do, where each capability lives now, and how to check it. Machine-parsed by `provenance_check.py`. |
| `references/merge-provenance/<source>.baseline.txt` | The **frozen fact-token set** per source, emitted by `coverage_probe.py --emit-baseline`. One file per source skill. |

The record is what makes the target's claim falsifiable. A capability row with no destination
path, or a source with no baseline, is not a smaller record — it is an uncheckable one.

## Record schema

Machine-parsed. Headings, field names, and column names are the contract; prose inside cells
is yours. A record with no `## Source:` section at all makes `provenance_check.py` exit `4`
(the gate did not run); a source section whose capability table cannot be found is a finding
and exits `3`. Either way a free-form rewrite disables the check instead of satisfying it.

```markdown
# Merge Provenance — <target-skill>

One line on what this file is and the command that re-verifies it.

## Source: <source-skill-name>

- **Merged**: <YYYY-MM-DD>
- **Source identity**: `<name>` · `<skill_id>` · class: peer (host-managed) | externally-managed
- **Retirement registered**: <where the retired name is registered, or `n/a — upstream left intact`>
- **Baseline**: `./merge-provenance/<source>.baseline.txt`
- **Corpus**: `references/types/<engine>`, `references/*.md`, `SKILL.md`

### Capability inheritance

| # | Capability (what the source could do) | Target destination | Verification | Status |
|---|---------------------------------------|--------------------|--------------|--------|
| 1 | …                                   | `references/…`     | …            | verified |
```

Parsing rules the checker relies on:

- One `## Source: <name>` section per absorbed skill — this is what accumulates for an
  A+B→C merge and for every later merge into the same target.
- `**Baseline**:` value in backticks. `./merge-provenance/x.txt`, `references/merge-provenance/x.txt`,
  or a bare `x.txt` all resolve.
- `**Corpus**:` is optional; see below. Backticked paths or globs relative to the skill dir,
  comma-separated.
- The capability table is found **by column name**, so columns may be reordered and headers
  qualified (`Capability (what the source could do)`), but all four names must be present.
- Every path the checker resolves is read from a **backticked** span. A destination written as
  prose ("see the workflow section") is unresolvable and reported as a finding.

### Scoping the corpus — mandatory when several sources land in one target

By default the checker reads the whole target skill, which is right when one source was
absorbed. It is **wrong when several were**, and wrong silently: a fact lost from its own
source's destination still matches if a *sibling* source's docs happen to contain the same
token. Measured on a real six-engine merge, 14–34% of each source's fact tokens also occur in
its siblings — so an unscoped corpus turns roughly a fifth of the gate into a formality.

Declare a `**Corpus**:` for each source in that situation: its own subtree plus the target's
shared docs, and nothing belonging to a sibling.

```markdown
- **Corpus**: `references/types/mermaid`, `references/*.md`, `SKILL.md`
```

Globs are what make this expressible: `references/*.md` matches the target's own top-level
reference docs but **not** `references/types/**`, which is exactly the sibling content that
must stay out. An entry that resolves to nothing is a **finding**, never a silent widening
back to the whole target — a scope that quietly stopped applying is the same false green the
field exists to prevent.

### Status vocabulary — closed set

| Status | Meaning | Effect on the gate |
|--------|---------|--------------------|
| `verified` | Destination exists and the capability was walked through at merge time | pass |
| `pending` | Not yet verified | **open gap** — the gate stays red; do not decommission on it |
| `dropped(<reason>)` | Deliberately not inherited | pass, and printed as a reasoned retirement |

`dropped` requires a reason inside the parentheses — a capability that vanished without a
recorded decision is a loss, not a choice. Anything outside these three is an invalid status.

## Filling the capability rows

Rows come from the **Phase-1 source inventory**, not from the source's table of contents.

- **One row per capability family** — a thing a user could ask the source to do. Not one row
  per file, and not one row for the whole skill. A source with four scopes yields roughly four
  to a dozen rows.
- **Capability column**: phrase it as the scenario the source served ("Run an inventory scan
  across every checkout"), not as a doc title ("fleet-inventory-schema.md"). The point of the
  record is that C inherited a *responsibility*, and responsibilities are worded independently
  of the file layout that happened to carry them.
- **Target destination**: backticked path in the target — the reference doc, `SKILL.md`, or the
  script that now serves it. The method and flow are allowed to differ from the source's; that
  is the whole premise of a restructure. What is not allowed is a capability with nowhere to go.
- **Verification**: how a later reader checks this row — a runnable command, a probe
  invocation, or a concrete scenario to walk through. An empty cell is a finding: a checklist
  whose items cannot be checked is a description.
- **Capability with no destination**: that is a Phase-3 mapping gap. Fix the merge; do not
  record the gap as `dropped` to make the table complete.

## Freezing the baseline (Phase 5)

Emit **after** both probe directions reach exit `0` — `--emit-baseline` refuses while misses
are unresolved, because freezing a lossy state would launder the loss into a "proven" baseline:

```bash
python3 ${SKILL_HOME}/scripts/coverage_probe.py \
  --allow <scratch>/coverage.allow \
  --emit-baseline <target>/references/merge-provenance/<source>.baseline.txt \
  <scratch-material> <target-doc>...
```

The allow-file reasons are folded into the baseline as ` # reason` suffixes, so the audit trail
travels with the committed artifact instead of staying in scratch. Baselines are **frozen**:
`--baseline` loads them verbatim and never re-extracts, because extraction is not idempotent —
re-extracting from a token list loses backtick-derived tokens and truncates relative paths,
producing a weaker gate that still prints "coverage clean".

## Re-verifying (Phase 8, and forever after)

One command, from anywhere, with no scratch material present:

```bash
python3 <resolved-path-to>/merge-skills/scripts/provenance_check.py <target-skill-dir>
```

⚠️ **`${SKILL_HOME}` does not work in the record.** Inside the target, `${SKILL_HOME}` resolves
to the *target's* home, not to merge-skills'. Write the resolved host path into the record's
header line when you create it — the record is host data, so a concrete path is correct there
even though this skill stays host-agnostic.

Exit codes: `0` record holds · `2` usage / not a skill dir · `3` drift or open gap · `4` gate
did not run (no record, or zero parsed sources).

Both tools exclude the provenance record and the baseline directory from the corpus they
check against — in every mode, not just this one. A baseline enumerates each frozen token by
construction, so reading it back as target content would satisfy every token unconditionally
and the re-verification could never fail. Passing a whole skill directory as the corpus is
therefore safe.

What a green verdict **does** and **does not** prove:

| Proven mechanically | Not proven — needs the Verification column run |
|---------------------|-----------------------------------------------|
| Every frozen fact token still appears somewhere in the target's shipped files | That the capability is still served **end-to-end** as a behavior |
| Every capability row's destination path still resolves | That the fact still sits in the *right* section (`§`/anchor parts are not checked) |
| No row is left `pending`, no `dropped` lacks a reason | Prose-level and lowercase-enum facts the probe never tokenized |

Say this plainly in the merge report rather than citing a green checker as proof of full
behavioral coverage — same discipline as the token probe's own limitation list.

## Maintaining the record after the merge

The record belongs to the target now, and the target keeps changing. When a later edit retires
an absorbed capability **deliberately**: update the row to `dropped(<reason>)`, and prune the
corresponding tokens from the baseline **with a reason suffix**. Never delete a baseline file,
and never empty one, to reach a green verdict — that is the same failure as deleting a failing
test, and the checker reports both as findings rather than passing them.

When the finding is *not* deliberate, the target drifted: restore the fact or the destination.
The finding text names which.

## Anti-patterns

- A name-level "formerly X, merged with content preserved" note offered as the record — an
  assertion with nothing to re-check.
- Leaving the proof in scratch or in a git-ignored workspace directory: the allow file and the
  material are exactly what Phase 8 deletes, and a git-ignored record is uninterpretable to any
  later session.
- Copying the source's docs into `references/merge-provenance/` as an archive. The record
  inherits **capabilities**, not files; archived source form re-imports the shape the merge
  exists to discard — and buys no verification either, since the checker excludes the record
  and the baseline dir from its corpus on purpose (a baseline lists every frozen token, so
  reading it would make the fact check pass unconditionally).
- One row for the whole source skill ("everything → SKILL.md"): unfalsifiable, and it hides
  every per-capability gap.
- Regenerating a baseline from itself instead of from source material.
- Recording a Phase-3 mapping gap as `dropped` to complete the table.
