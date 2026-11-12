# Skill Reference Definitions

**Single source of truth** (唯一真源) for **how a framework entry names a Skill**; `run-skills`, `create-skills`, `improve-skills`, `merge-skills` and `coaching-skills` normalize their input by this file before resolving.

**This file owns** four fact groups; each has a landing section below: the closed set of accepted forms (§ Accepted forms); **the normalization order** and the output shape (§ Normalization); **the disambiguation rules** (§ Disambiguation rules); **the failure semantics** (§ Failure semantics).

**This file does not own** (reach the owner, never restate it): **the position ladder** — which location wins when a name is resolved — → `.specify/skills/internal/run-skills/SKILL.md` § 1（the position ladder）; `.specify/scripts/python/sync-mirrors.py` owns **mirror generation**.

## Accepted forms

The set is **closed**. A new form is a revision of this file — it MUST NOT be added by a
consumer in place. The `form` column is literal (it is the value the matrix fixture keys on).
| form | example | meaning |
|------|---------|---------|
| bare name | `improve-skills` | the Skill whose directory / frontmatter `name` is that string |
| slash reference | `/improve-skills` | that Skill's **slash-command surface** — not an instruction to invoke it directly |
| at reference | `@merge-skills` | host-style mention of the same Skill |
| labelled reference | `skill:merge-skills` | the same Skill behind the `skill:` label |
| canonical path | `.specify/skills/merge-skills/SKILL.md` | a path ending in `SKILL.md` |
| directory path | `skills/external/merge-skills` | a Skill directory (a trailing `/` is allowed) |

Every example above MUST have a row with an expected output in the normalization matrix.

## Normalization

Deterministic and non-interactive: the same input yields the same output, no context state
is consulted, no network is touched, no question is asked. The steps are written as one
numbered table so that the order they state is the order that runs. **The step order is
not exchangeable** — in particular NP-3 and NP-4 run *before* NP-6.

| Step | Action |
|------|--------|
| **NP-1** | **Form determination**: is this a *call* (the `cli` form — a `/speckit.*` invocation arriving as a command token) or an *invocation* (a chat-message parameter)? The two forms differ only in failure reachability (§ Failure semantics); both yield the same normalized identifier. |
| **NP-2** | Trim leading/trailing whitespace, then one **paired** wrapping quote (`"…"` or `'…'`). An unpaired quote is a failure, not a silent trim. |
| **NP-3** | Strip **one** `skill:` label. |
| **NP-4** | Strip **one** `@` or `/` prefix — `@/name` counts as **one** prefix segment and is accepted. What remains MUST NOT be empty. |
| **NP-5** | Strip **one** `SKILL.md` suffix or one trailing `/` (in that order when both appear). A `.md` that is not `SKILL.md` is **not** stripped. |
| **NP-6** | **Channel test**: does the residual contain `/`? Yes → **path** channel; no → **name** channel. A `..` relative segment in a path-channel residual is a failure. |
| **NP-7** | **Hit test**: name channel matches by name (§ Disambiguation rules, case rule); path channel is tested against the position ladder. Zero hit / out-of-ladder / unreadable / two distinct layers → failure. |
| **NP-8** | **Output**: exactly one of the three values below, reported **paired** with the raw identifier. |

**Why NP-3 / NP-4 precede NP-6**: `/improve-skills`, `@/merge-skills` and
`skill:/merge-skills` all carry a `/` that belongs to the *prefix*, not to a path. Testing
the channel first reads every one of them as a path and never reaches the strip steps.
`speckit.skills` and `speckit.skills/SKILL.md` are the same command name written two ways;
NP-5 (strip `SKILL.md`) before NP-6 makes both converge on `command-surface`.

**Channel test is one criterion**: whether the residual contains `/`. The name channel
MUST NOT add a character-class assertion — `speckit.skills` is a legal dotted name, and
rejecting it as "illegal characters" would turn an input that must report `command-surface`
into a failure.

**Case rule (two passes)**: first an exact match; **only on zero hits** one
case-insensitive pass. A case-insensitive pass that hits **more than one** candidate closes as
the `dual-layer` failure — never pick one.

**Output shape** — exactly three values, closed:

| outcome | payload |
|---------|---------|
| `command-surface` | the command name (not a skill path) |
| `skill` | the name, **or** the path plus its layer |
| `failure` | the failure class plus that class's required report items (§ Failure semantics) |

The normalized identifier carries **no stripped prefix or suffix** — the prefix and suffix
are recognized and then discarded, never left for a downstream reader to guess. There is
**no fourth value**: "return it as-is and let the caller decide" is not an outcome.

The report is always **paired**: raw identifier + normalized identifier + decision class
(one of the three). Reporting only the name makes the decision class unre-computable.

**Extensions**: a name may omit the extension when the caller *settles* the reference — that
is a settlement convention, **not** a normalization step. `.md` is therefore not stripped:
`my-draft.md` normalizes to the name `my-draft.md`.

## Disambiguation rules

**(a) A leading `/` marks the slash-command surface, not "invoke it instead".**
Example: `/improve-skills` → `skill` / `improve-skills` — the parameter still denotes *the
Skill to operate on*, and the caller MUST NOT execute it in place of its own flow.

**(b) A `/speckit.*` command name is a command, not a Skill.**
Example: `speckit.skills` → `command-surface` / `speckit.skills`, pointing at that command.
It MUST NOT be resolved as a Skill and MUST NOT be force-executed. If a Skill of the same
name genuinely exists, they are two different objects — the report names both rather than
silently choosing one. The same rule covers `speckit.skills/SKILL.md` (NP-5 strips the
suffix before NP-6 tests the channel).

**(c) Two hits in one layer are one hit; two different layers are two.**
Example: `improve-skills` present both in the dev canonical tree and in the installed
mirror → **one** hit. The criterion is the **layer**, not the path literal — comparing path
literals would read the source directory and its `.specify/` mirror as two.

**(d) A meta-skill working item is an ordinary work item.**
Example: `coaching-skills` asked to improve `improve-skills` — that request MUST NOT be
reclassified as "not a real work item", and the caller MUST NOT execute the trainee's steps
in its place.

## Failure semantics

Exactly four classes. Every class **closes** (stops); there is no "try one and continue"
recovery edge. Re-writing the reference from the user side is a **new** normalization and
MUST NOT reuse the previous failure's conclusion.

| class | condition | required report items |
|-------|-----------|-----------------------|
| `zero-hit` | no hit after normalization | raw input, normalized form, every searched coordinate |
| `out-of-ladder` | a path falling outside the known locations | that path + the known location set |
| `unreadable` | a directory without a readable `SKILL.md`, or invalid frontmatter | the path + the defect |
| `dual-layer` | two hits in **different** layers with the same name | both candidate paths (never the nearest one) |

The four classes are **mutually exclusive**: an out-of-ladder input MUST NOT be reported as
`zero-hit`, and an unreadable directory MUST NOT be reported as `out-of-ladder`. Every class
reports both the **raw** and the **normalized** identifier — either one missing means the
failure was not reported.

**`@name` in the `cli` form**: the host CLI consumes `@` before the meta-skill sees it, so
the form is unreachable there. Rule it as `zero-hit` **plus** the note "this form is
unreachable in the cli form". Do not invent a syntax to rescue it.

## Boundary

- The **position ladder** is not inlined here — which location wins is `.specify/skills/internal/run-skills/SKILL.md` § 1, reached by reference. This file never states a directory priority and never adds a location.
- No other owner's rule literals appear here. The directories in the accepted-form examples are *examples*, not priority claims.
- **No new machinery**: no new command, gate script, directory root, environment variable or second classification data file. The only executable form of this grammar is a test-only implementation under `tests/`, never under `.specify/scripts/`, never a gate.

## Change Log

| date | change | basis |
|------|--------|-------|
| 2026-11-05 | Normalization order rewritten to NP-1…NP-8 (form determination → trim/quote → `skill:` → `@`//` → `SKILL.md`// → channel → hit → output), with NP-3/NP-4 ahead of NP-6 so `@/name`, `skill:/name` and both spellings of a dotted command converge; the three-value output made closed (the prior procedure could express only NAME/PATH); the `cli`-form `@name` ruling added. | 082 `requirements.md` FR-021 / FR-023 / FR-030, clarify decision (1), `research.md` § R10 (probe: 14 rows, 2 outcome classes) |
| 2026-11-05 | § Normalization states the step table's order as the order that runs, closing the gap between "not exchangeable" and the table it governs (no rule changed; the table already ran NP-1 → NP-8 with NP-3/NP-4 before NP-6). | FR-021, GR-03 |
| 2026-11-05 | Head ownership declaration completed (four owned fact groups with landing sections; the two not-owned facts with owner paths); consumers' reference target fixed to the framework-source path; the head now declares itself by the literal `single source of truth`. | FR-019, FR-022, FR-028 |
