# One Source of Truth

Single source of truth for the authority-and-reference discipline. Referenced from the `## One Source of Truth` summary in `.specify/instructions.md` — keep that summary a pointer; the full discipline lives here. Any command, skill, agent, or shared workflow that invokes this discipline MUST cite this file by path and MUST NOT copy its rules.

**The rule**: every fact — a concept's meaning, a normative rule, a threshold, an enumerated list, a configuration value, a state machine, a count — MUST have exactly one authoritative definition point, its **owner**. Every other location that needs the fact MUST reach it by reference and MUST NOT restate its content.

The failure this prevents is not disagreement, it is *silent* disagreement. A fact written in one place is either right or wrong. The same fact written in five places is right in some of them, and nothing tells a reader which.

## Declare the owner

- A document that owns a fact MUST say so in its opening lines, and MUST name **what** it owns — "single source of truth" with no object is decoration, not a claim.
- A fact with no declared owner has as many owners as it has copies. When two locations state the same fact and neither claims authority, that is a defect to repair, not a stylistic preference.
- Ownership is granted per fact, not per document. One document MAY own several facts, and a large owner MAY delegate one section as the definition point of one value — in which case that section says so, and other locations cite the section rather than the file.

**Owner selection order** — when it is not obvious which of several candidates should own a fact:

1. **Code** — for any fact about how the system *actually behaves* (supported values, defaults, enumerations the program branches on). Code is the executable record; documents describing it are derived.
2. **Machine-generated artifact** — for any fact a generator can derive from a set (counts, indexes, inventories, matrices). Let the generator own it.
3. **Authored document** — for definitional facts a program cannot derive: what a concept means, which rule applies, what threshold was agreed.

The first tier is the operative form of *Code as the Single Source of Truth*: that principle settles **which** source wins; this document adds the obligation the winning source imposes on everyone else.

## Reference, don't copy

- A reference is a **path** — plus a section anchor when the fact is one section of a larger owner. It MUST be resolvable by a reader who has only this repository.
- A **summary pointer** is permitted and encouraged: a short orienting paraphrase, then the owner's path. It MUST NOT carry the owner's operative detail — not the table, not the threshold literal, not the enumeration. The test is behavioural: a reader who intends to *act* must still have to open the owner. A summary that lets them skip it has become a copy.
- Naming a fact is not restating it. "Which tier a tool belongs to" is a reference; "Tier 1 is A, B, C" is a copy.

Rule of thumb: **if changing the fact would require editing more than one file, the discipline is already broken.** Apply it before writing the second location, not after the two disagree.

## Legitimate duplicates

Not every second copy is a violation. Three kinds are allowed, each only under its condition:

| Kind | What it is | Condition that makes it legitimate |
|------|-----------|-------------------------------------|
| **Mechanical copy** | A copy produced from the owner by a script or generator — mirrors, per-tool regenerated files, generated indexes, symlinks | A command exists that regenerates it from the owner, it is never hand-edited, AND divergence is detectable (a `--check` mode, a parity test, or a broken-link check) |
| **Guard copy** | A literal pinned inside a test | It exists *in order to* fail when the owner changes. A guard copy serves the build, never the reader |
| **Dated record** | A specification, feedback entry, review report, or session note that captured the fact as it stood at a point in time | It is scoped to a date or version, and is never cited as current reality |

Any other location that repeats a fact is a **drifting copy**, and MUST be converted into a reference.

Two consequences worth stating outright: a mechanical copy that has lost its generator has become a drifting copy, whatever its history; and hand-editing a mechanical copy is the more serious defect, because the next regeneration silently discards the edit.

## Counts and enumerations

Numbers and lists are the highest-risk facts in any document set, because nothing breaks when they go stale — a wrong count reads exactly like a right one.

- A count MUST NOT be hand-written where the underlying set is machine-countable. State the set's owner instead, or let a generator derive the number into the owner.
- Prose SHOULD prefer "see `<owner>`" over "N items (a, b, c, …)". A reader who needs the list needs it current, and an inline list goes stale on the next addition — which is exactly when nobody is looking at this file.
- On finding a stale count, **remove the copy; do not correct the number**. A corrected number drifts again on the next change; a reference does not. Correcting it in place feels like a fix and buys nothing.

## Resolving a disagreement

When two locations state the same fact differently:

1. **Identify the owner** — by declared authority, otherwise by the selection order above.
2. **Trust the owner.** Every disagreeing location is stale by definition, however recently it was edited and however confident its wording.
3. **Repair the copy, and repair it by converting it into a reference.** Editing the copy to agree is a fix of the instance; removing its ability to disagree is a fix of the mechanism. Only the second one holds. This is the same reasoning as *Fix the mechanism, not just the instance*.
4. **If no owner can be identified**, designating and declaring one is the first act of the repair — before any wording is touched.

An owner that turns out to be wrong is a normal outcome, and is handled by correcting the owner. It is not an argument for keeping a second copy as a hedge.

## Relationship to adjacent principles

Referenced by name, never by number — numbering is per-project and renumbers over time:

- **Code as the Single Source of Truth** decides which source wins for facts about actual behaviour. This discipline generalizes the question to every kind of fact, and adds the reference obligation on the consuming side.
- **Fix the mechanism, not just the instance** supplies the repair direction in the section above: a drifting copy is an instance, and converting it into a reference is the mechanism-side fix.
- **Framework Scope Discipline** bounds this document: the discipline is a way of writing, enforced by review and by targeted tests where a fact matters enough to guard. It MUST NOT be used to justify a duplicate-fact scanner, an authority registry, or any other new tracking machinery.
