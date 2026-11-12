# Acceptance Hardening — Feature Status, Verification Vocabulary, Gates and Closure Verdict

**本文件为 owner，其余为指针（092 D1/D2）**：下文定义的每一条 schema 若在别处被复述，该处 MUST 改写成
「路径 + `§ section anchor`」指针，MUST NOT 保留第二份定义（判定形态见 § Schema Uniqueness）。

**Owner (single definition point)**: this file, `.specify/shared/workflow/acceptance-hardening.md`, owns the schemas that
make "may this feature be called `Implemented`?" a deterministic question: the feature-status value `Blocked`
and its four transitions, the verification vocabulary and its measurement ladder, the gate conditions that read
them, the closure verdict with its closed reason set, exit codes and `final_path` counts, and the three artifact
schemas that say **what a feature must own and what it must have inherited** — the runtime-stack table, the
execution-premises table and the inherited-blockers table. Every other surface — template, command, skill, driver
doc — reaches these by path plus `§ section anchor`, and **none restates** a table, a value domain, a threshold or
a reason literal.

**Declared carriers (projections, never second owners)**: `.specify/templates/feature-details-template.md` § Canonical
Status State Machine, `.specify/templates/verification-log-template.md`, `.specify/templates/tasks-template.md` (§ GATE-4) and
`.specify/templates/plan-template.md` (the two plan-table skeletons, which carry **column names only**) physically hold what
this file defines, because a consumer that is editing a template must find the rules where it is editing. A carrier
is a **declared projection**: it may not widen a value domain, and where a carrier and this file disagree, this file
wins and the carrier is stale. Each carrier also owes a narrowing assertion of its own — the plan skeleton, in
particular, may repeat a column set and **zero** domain literals. This paragraph declares carriers; it does **not**
define the schema-uniqueness guard's allow-list. Which surfaces that guard permits, on which subject and across
which paths, is owned by § Schema Uniqueness.

**Scope of this revision**: § Feature Status · § Verification Vocabulary · § Gates · § Closure Verdict ·
§ Runtime Stack & Dependency Ownership · § Execution Premises · § Inherited Blockers · § Schema Uniqueness ·
§ Review Composition.
Sections belonging to later slices are listed in § Extension Points, together with the owner their obligations
currently have. Nothing here is inferred from a slice that has not landed.

**Machine-readable form**: `.specify/scripts/python/closure-acceptance-check.py` is the only program that turns these
schemas into a verdict. Its calling surface is fixed by a contract; its verdict is **not** re-derivable by a
model, by an ad-hoc grep, or by a second script.

## Feature Status

`Blocked` is a **first-class feature status**, not "`Implemented` with a note attached". It says: the work that
could be done is done, and the feature is still not acceptable. It exists because the pre-change bar —
every task closed, a status row per criterion — is satisfied by a feature whose main journey never ran.

### `Planned → Implemented` is four conjunctive conditions

All four MUST hold. Three of four is `Blocked`.

1. `tasks.md` has zero open rows — no `[ ]` and no `[>]`.
2. Every success criterion has a status row in `verification.md` (see § Verification Vocabulary).
3. **Every `final`-path criterion's status is `pass`.**
4. The feature's smoke record is `pass` (command, exit code `0`, evidence path present — see § Verification
   Vocabulary).

### The four `Blocked` transitions

| From | To | Allowed | Condition |
|------|----|---------|-----------|
| `Planned` | `Blocked` | yes | tasks are closed but at least one `final`-path criterion is not `pass` |
| `Blocked` | `Implemented` | yes | the blocker is lifted **and** every `final`-path criterion is `pass` |
| `Blocked` | `Ready for Review` | **no — illegal** | a blocked feature has not earned review; it must re-enter through `Implemented` |
| `Implemented` | `Blocked` | yes, narrow | **audit correction only**, and it MUST cite the evidence that makes the claim false |

### Never regress — two narrow audit corrections

Every backward transition stays illegal, with exactly two exceptions, each an audit correction that cites its
evidence: `Implemented → Blocked`, and `Sealed → Ready for Review` (the seal conclusion is falsified; the
evidence lands on both verifiable carriers — the registry row and the feature detail). "The user did not
object", an agent's own confirmation, or a later discovery that nobody wrote down is not evidence. Neither
exception widens into a general rollback channel.

### `Sealed` — the terminal status for new work

`Sealed` is the **terminal feature status for new work**: no forward transition leaves it, and it is the only
status admitted to archive — the admission itself is owned by `.specify/scripts/python/seal-utils.py` `--action
archive-gate` and is queried, never re-implemented. Exactly one forward transition enters it —
`Ready for Review → Sealed` — and `/speckit.seal` is that transition's only owner command. `Completed` is not
a second terminal: it survives only as a legacy record value (no retroactive rewrite, no downgrade) and new
work MUST NOT land it.

| Term | Meaning |
|------|---------|
| `Sealed` | The spec's review is concluded, its acceptance records are complete and merge-back has landed when slices exist; the feature detail and the registry row both read `Sealed`. |
| `Ready for Review → Sealed` | The single forward transition into `Sealed`; owner command `/speckit.seal`; the conjunctive conditions below. |
| `Sealed → Ready for Review` | Audit correction only, citing the evidence that the seal conclusion does not hold — the same shape as `Implemented → Blocked`. |

**The `Ready for Review → Sealed` conditions (all conjunctive).** All MUST hold; any failure refuses the
transition, leaves the status unchanged and names every unmet condition with its repair path:

1. The from state is `Ready for Review` on both carriers and they agree; a mismatch or a missing carrier is
   `state-drift` — an input error, never a one-sided reading.
2. The current review conclusion carries zero unhandled P0: every P0 is fixed (with a fix pointer) or
   explicitly waived by the user, and the current `code-review.md` carries zero `blocking` entries. A
   driver's or an agent's confirmation is never a user waiver.
3. The acceptance record is complete per the closure checker: every success criterion has a status row, every
   `final`-path criterion is `pass`, the smoke record is `pass`, and every SC line carries its `**Path**`
   marker. The checker's exit `2` is an input defect, never an `accept`.
4. Merge-back is complete when the slice set is non-empty: the merge manifest covers every slice × output
   pair with zero unresolved conflicts (`not-applicable` carries its basis) and every slice is closed; with
   no slices the manifest records `not-applicable` and its basis.
5. The parent spec tree carries no uncommitted change outside this flow (`dirty-spec-tree`).

## Verification Vocabulary

### The closed six-value status set

`pass` · `fail` · `partial` · `blocked` · `deferred` · `unknown`

Closed: no gate, Definition-of-Done row or task row may narrow it to a subset, because a narrower set silently
forbids an honest value and forces a reclassification judgement. **`blocked` vs `deferred`, in one sentence
each** — `blocked` means the environment cannot measure this assertion, so the feature is **not** acceptable;
`deferred` means the assertion was not attempted this round and the feature **may still** be acceptable, which
is legal only on a `supporting`-path criterion.

### The five measurement-ladder fields

A `blocked`, `deferred` or `partial` row MUST carry all five, named with the criterion id as prefix and spelled
exactly:

| Field | Content |
|-------|---------|
| `SC-NNN_blocked_at` | ISO date, or the name of the reason it is blocked |
| `SC-NNN_reduced_measurement` | what **can** be measured instead |
| `SC-NNN_reduced_measurement_run` | `yes` / `no` |
| `SC-NNN_why_reduced_insufficient` | why the reduced measurement does not stand in for the assertion |
| `SC-NNN_unblock` | what would lift it |

**Illegal row (mechanical trigger, no semantic judgement)**: `SC-NNN_reduced_measurement` is **non-empty** AND
`SC-NNN_reduced_measurement_run=no`. A missing ladder field is illegal in the same way. The trigger reads
*non-empty*, never "available" — a measurement written down and not run is not an honest substitute for running
it, it is the same shape as the defect the ladder was introduced to stop.

### The smoke record — three fields, exactly one per feature

| Field | Content |
|-------|---------|
| `smoke_command` | one shell command, verbatim; end-to-end over the feature's main flow, not the whole suite |
| `smoke_exit_code` | `0` for a feature claiming `Implemented` |
| `smoke_evidence_path` | repo-relative path to a file that exists and is non-empty |

A second `smoke_command=` line is a defect, not a choice. A feature that cannot run its smoke lands `Blocked` —
"needs a real cluster" or "needs real network" is **not** an exemption: either the command is made
deterministic on a local fixture, or the feature is `Blocked`. A **missing** smoke record is never an input
error; it is a completeness fact about the feature, and it blocks completion condition ④.

### The four `blocked` literals are four unrelated facts

The character sequence `blocked` is spelled in four places in this framework, and they are four independent
closed sets with four owners. This subsection is the **only** place their reconciliation is written: each
carrier keeps its own vocabulary and points here, and no carrier restates this table.

| Literal | What it is | Owner — and the only place its domain is decided |
|---------|-----------|--------------------------------------------------|
| `Blocked` | a **feature status** | `.specify/templates/feature-details-template.md` § Canonical Status State Machine, whose rows and conditions this file's § Feature Status owns |
| `blocked` | a **verification status** of one success criterion | `.specify/templates/verification-log-template.md`, whose six values and ladder this file's § Verification Vocabulary owns |
| `blocked` | a **line state** in the driver's registry | `.specify/skills/sdd-loop-driver/scripts/line-registry.py` (`STATE_VALUES`; the state's consequences are A6's, not this row's) |
| `blockedBy` | a **task dependency tag** | `.specify/templates/tasks-template.md` — a tag, **not** a state |

The four stay four. No fifth meaning may be introduced, and none of the four may borrow another's value
domain: the domains themselves — the values, the transition rows, the thresholds, the guard sets — are decided
in the owner named in the right-hand column and are cited here, never restated. These four are also not the
three **vocabulary owners** `Blocked` must appear in, and not this file's four **declared carriers**: the three
sets overlap without being equal, and a reader who collapses them will demand a value domain from a file whose
job is to tag a task.

**Every other occurrence is classified, not left implicit.** An occurrence of `blocked` outside those four
owners belongs to exactly one of two classes, and either class is decided per occurrence by these criteria
alone — which is why no per-site list is carried here:

1. **A use of one of the four vocabularies.** The occurrence reports a feature, a criterion, a line or a task
   dependency in that state, in prose or in a machine-readable field, and it means whatever the owner above
   says. Nothing new is created: a sentence such as "this feature is `Blocked`" is a use of row 1.
2. **An unrelated pre-existing closed set that merely shares the spelling.** A set that exists for its own
   reason and would still exist if this feature had never been written. The framework has one: the driver's
   queue report groups runnable lines by the dependencies they are waiting on (`blocked_by`, emitted by
   `.specify/skills/sdd-loop-driver/scripts/line-registry.py`'s `--action next-runnable`), which names a line's
   **unmet dependencies**, never the line's own state.

An occurrence that fits neither class is not classified — it is the third meaning this subsection exists to
forbid, and it is resolved by adding a row above (or naming a new class here) **before** any carrier adopts it,
never by quietly widening one of the four.

## Gates

### The fourth `Implemented → Ready for Review` condition

`Implemented → Ready for Review` is conjunctive like the transition that precedes it, and its fourth condition
is: **no `final`-path criterion sits in `blocked` / `deferred` / `fail`, unless an explicit user waiver names
it.** A waiver is a user-authored artifact or the user's own ruling; a driver's or an agent's confirmation, and
the absence of objection, are never waivers. The reachable block consumers cite is § Canonical Status State
Machine of `.specify/templates/feature-details-template.md`; `/speckit.review`, `/speckit.checklist` and
`.specify/shared/workflow/feature-integration.md` § Pre-Status-Flip Gate reference that block and do not restate it.

### GATE-4 (tasks stage)

For every `final`-path criterion, GATE-4 requires a `pass` status **and** a present smoke record — or an
explicit user waiver naming the criterion. The carrier is `.specify/templates/tasks-template.md`; the condition set is
this section's.

### Superseded pre-split records retain their claims

A split merge disposes a parent's pre-split task rows by `supersede`: the row survives as a `> ` quoted
record, which removes it from the **current** plan (it is not an open row and owes no blockedBy, `[P]` or
phase obligation) but MUST NOT void the row's `[green: <contract>#<clause>]` declarations. A `[green:]`
declaration inside a `## Superseded pre-split record` block is a **retained claim** and coverage accounting
MUST count it exactly like a current row's claim, because the clause's delivery was carried by the slices
the record names. The opposite reading turns every split merge's fully claimed parent contracts into an
uncovered residual — an accounting artifact, never a delivery gap. `.specify/scripts/python/validate-tasks.py`
parses these claims (the one implementation of the mention/fence rules) and supplies them to
`.specify/scripts/python/account-clause-coverage.py`; the block is never re-validated as a current plan.

### The A13 boundary — three carriers, one fact each

Three tables look alike and judge different things. The same fact MUST live in exactly one of them, and the
others reference it (`see § …`), never copy it:

| Carrier | Judges |
|---------|--------|
| `plan.md` § Execution Premises | planning-time load-bearing premises and whether evidence supports them |
| `plan.md` § Inherited Blockers | records inherited from a dependency feature, and this feature's disposition of each |
| `tasks.md` § Environment Prerequisites | task-generation probe verdicts, each with its probe command and an ISO date |

A fact written in two of the three is a defect; the second occurrence MUST be converted into a pointer.

## Closure Verdict

### Binary, and only binary

`accept` or `block`. There is no third value, no severity scale and no advisory tier. The payload carries the
verdict, the reasons, the `final_path` counts and the feature class (`execution` / `expression`) — and nothing
else is a verdict.

### The three exit codes

| Exit | Meaning |
|------|---------|
| `0` | `accept` |
| `1` | `block` |
| `2` | an input is missing or unparsable |

A missing input is **never** reported as `block`: it is a defect of the artifact or of the invocation, not a
finding about the feature. In audit mode the exit code reflects input validity only — `0` whenever the inputs
parse, however many features the audit reports.

### `final_path` counts, computed once

`final_path = {pass, blocked, deferred, partial, fail, unknown, total}` over the `final`-path
criteria — six status buckets plus the total, and the record is **closed**: a seventh bucket requires
revising this section, never a local addition. Two of the six are easy to confuse and are therefore
distinguished here once:

| Bucket | Meaning |
|--------|---------|
| `unknown` | **no status row exists** for the criterion. A missing measurement is not evidence of anything, least of all of a pass. |
| `partial` | the row **exists and was measured** as `partial`. It is a measurement, not a gap — the same status the verification vocabulary admits, counted rather than reinterpreted. |

The checker computes these counts; no caller, template or report recomputes them — a report copies
them. A second count is a second source of truth, and the two drift.

### The seven reason templates

`block` MUST carry at least one reason drawn from this closed set. Five take an argument, two take none:

| Template | Argument |
|----------|----------|
| `zero-final-path-pass` | — |
| `final-path-not-pass: SC-NNN` | `SC-\d{3}` |
| `blocked-without-measurement-ladder: SC-NNN` | `SC-\d{3}` |
| `runtime-dependency-not-owned: RS-NNN` | `RS-\d{3}`, or the reserved literal `runtime-stack` for a section with zero data rows |
| `falsified-premise-undecided: EP-NNN` | `EP-\d{3}` |
| `inherited-blocker-undisposed: <feature>:<row>` | `<feature>` = the dependency's feature id; `<row>` = that source row's locator as the dependency artifact writes it |
| `status-claims-implemented-but-blocked` | — |

**Template versus instance, and membership**: these seven are **templates**. An emitted reason is an
**instance** — `prefix + ": " + argument`, where the prefix is the template with its `: <placeholder>` suffix
removed, joined by exactly one `": "`, and the argument satisfies the grammar above. Membership is therefore a
mechanical **two-part test**: template match (byte-identical prefix) **and** a well-formed argument. A bare
prefix of an argument-taking template is not a member; no third spelling, trailing colon or re-spelled
placeholder is admitted. One argument slot is a **reserved literal** rather than an id: the runtime-row class has a
shape with no `RS-NNN` to name — the section exists but carries **zero data rows** — and that shape's instance is
`runtime-dependency-not-owned: runtime-stack`. Emitting nothing there is the false green the finding exists to
catch, and a fabricated `RS-NNN` would be worse than silence: it points at a row nobody wrote. A reason outside the set, or an instance with a malformed argument, is a defect of the
checker — not a finding about the feature.

The set is **closed**: an eighth reason requires revising this file, never a local addition. A non-`pass`
`supporting`-path criterion produces no reason of its own; only `final`-path criteria can refuse a verdict. For
an `expression`-class feature the `final`-path rule is **vacuous** — the class is read from the declared flow
class, so the exemption is mechanical, and such a feature is never forced to invent a `final` criterion.

A declaring specification records the same seven templates in its own `## Shared Strings` so its tests can pin
them verbatim. That is a per-spec declaration for matching, not a second schema: this file is authoritative for
what a consumer emits.

### Input contract — the `Path` marker

Every success-criterion definition line carries `**Path**: final` or `**Path**: supporting`, written as the
**last token of the line, exactly once**. `final` = the criterion proves the feature's main user journey /
product flow works; `supporting` = auxiliary quality, hygiene, documentation or non-blocking evidence. An
`execution`-class feature MUST carry at least one `final`-path criterion; an `expression`-class feature is
exempt and MUST NOT be forced to invent one. A missing marker, a second `**Path**` on the same line, or a value
outside the two-value domain is a format violation reported with file and line — and a marker that cannot be
parsed makes the closure check an **input error** (exit `2`), never a `block`.

**The two members are declared, not restated.** `final` / `supporting` are machine-read values, so their single
home is `.specify/shared/declarations/facts/success-criterion-path-values.yaml#/statement`; both checkers read that
declaration through the shared read entry. This section keeps the rule they apply — the marker's position, the
one-`final` floor, the refusal template and the exit-code meaning above — and carries no second copy of the
member set.

### When the judgement runs

At the **feature line's closure**. One line carries a feature's whole slice set, so the verdict runs once, when
that line closes — a `final`-path criterion is legitimately not `pass` in an early slice, and reading the
judgement as "every slice merge must pass it" would block the first merge by construction. Slice merges are
judged by the review gate. The three call sites — implement (before `Planned → Implemented`), review (before
`Implemented → Ready for Review`) and the driver's closure/merge step — share this one verdict, and no call site
may substitute a model judgement, a different script or an ad-hoc grep for it.

## Runtime Stack & Dependency Ownership

The requirements-side table that answers "is the runtime this feature stands on inside the feature's own
acceptance boundary?" Mandatory in `requirements.md` of an `execution`-class feature. The columns are fixed and are
read **by column name** — never recovered from another cell's prose:

| Column | Content |
|--------|---------|
| `ID` | `RS-\d{3}`, dense and unique |
| `Capability` | one runtime capability the feature consumes or delivers |
| `Form` | the closed domain below |
| `Owner` | who provides it |
| `Pin` | version / digest / commit — measured, never invented; required for `signed-contract` |
| `Contract` | repo-relative path of the file the contract actually lives in; required for `signed-contract`, and it MUST resolve in the checkout |
| `Joint acceptance` | a named owner or a command; required for `signed-contract` and for `in-scope` |
| `FR` | the `FR-NNN` list that delivers the capability; required for `in-scope` |
| `Premises` | the `EP-NNN` ids the row's FRs depend on, `, `-separated; each MUST exist in `plan.md` § Execution Premises and obey § Execution Premises below |

`Contract` and `Premises` are **their own cells**, and that is load-bearing rather than cosmetic: a contract path
living inside `Owner` prose gave the contract-path check nothing to read, and a premise id with no cell of its own
made "every runtime-dependent FR cites a premise" uncheckable.

### The `Form` domain

`in-scope` · `signed-contract` · `user-waived` — closed. An `expression`-class feature MAY record `not-required`
with a stated reason; on an `execution`-class feature `not-required` is a defective cell.

`in-scope` means **this feature delivers the capability**. A capability supplied externally and merely consumed
here MUST be `signed-contract` (or `user-waived`) — recording it `in-scope` only renames the outsourcing.

`signed-contract` MUST carry a `Contract` cell that resolves, a measured `Pin`, an external `Owner` and a named
joint-acceptance owner or command. `user-waived` MUST cite the user ruling and state the residual risk.

### The three `in-scope` duties, each judged where its carrier is readable

| Duty | Obligation | Judged at | Failure class |
|------|-----------|-----------|---------------|
| ① | the `FR` cell is non-empty and resolves to an FR defined in **this** spec | requirements | **input error** (exit `2`) — a defective cell is a fact about the artifact, never a `block` about the feature |
| ② | at least one `tasks.md` row quotes that FR, by a **line-level** match `^- \[.\] T\d{3}.*\bFR-0NN\b` — an FR named in a table cell or in prose is not a task row | tasks | `runtime-dependency-not-owned: RS-NNN` |
| ③ | `verification.md` carries a joint-acceptance row naming that `RS-NNN` | closure | `runtime-dependency-not-owned: RS-NNN` |

A stage that cannot see the carrier artifact MUST NOT report the duty as satisfied. Duties ② and ③ share their
reason with the prose-only case below, because they are the same conclusion about the same artifact — the
capability is claimed and nothing owns it. No reason is coined for them.

### Three shapes, three verdicts — silence is not one of them

| Shape | Verdict |
|-------|---------|
| the section is absent | **input error** (exit `2`) — the artifact is incomplete |
| the section is present with **zero data rows** | `runtime-dependency-not-owned: runtime-stack` — the reserved argument (§ Closure Verdict), because this shape has no `RS-NNN` to name |
| a data row with a required-but-empty cell | `runtime-dependency-not-owned: RS-NNN` |

Zero data rows is the most complete form of "no table row" and MUST NOT be read as "this feature has no runtime
dependency". Emitting nothing there is the false green this class exists to remove, and a fabricated `RS-NNN` would
be worse than silence: it points at a row nobody wrote.

**Cell-shape defects are input errors, existence and acceptability defects are reasons.** A `Form` value outside
the domain, `not-required` on an `execution` feature, a `Premises` id with no matching premise row, and a
`Contract` path that does not resolve all exit `2`; a missing `RS` obligation, an unsupported waiver, and a
`user-waived` row whose residual-risk cell is empty are `runtime-dependency-not-owned: RS-NNN`. The split is not
re-decided per caller.

### The prose-declaration rule — mechanical, code blocks excluded

"Prose only" is decidable rather than a reading. Inside the section, fenced code blocks (backtick and tilde
fences) and heading lines are removed first; a remaining line shaped

```text
- **Runtime dependency**: <capability> — <owner>
```

is a **prose declaration**: carrying an `RS-NNN` it yields `runtime-dependency-not-owned: RS-NNN`, carrying none it
is an input error naming that line. A narrative line **without** the marker — for example an explanatory paragraph
that mentions `RS-004` — is not a declaration and MUST NOT fire. The marker is the rule; without it "prose" would
be a judgement, and the obligation would only bite on examples written to be caught.

## Execution Premises

The plan-side table that records what the plan **assumes at planning time** and whether evidence supports it.
Mandatory in `plan.md` of an `execution`-class feature.

| Column | Content |
|--------|---------|
| `ID` | `EP-\d{3}`, dense and unique |
| `Premise` | one load-bearing assumption the plan rests on |
| `Evidence` | a path, a command, or a measurement — citable |
| `Status` | the closed domain below |
| `Decision` | the closed domain below |

### `Status` — closed over three values

`verified` · `unverified` · `falsified`.

### `Decision` — required whenever `Status` is `falsified`

`resolve-in-scope` · `fallback` · `user-waiver`, closed. A `falsified` premise whose `Decision` cell is empty or
absent is `falsified-premise-undecided: EP-NNN` (§ Closure Verdict): the premise is a known-bad fact and nobody has
said what happens about it. A `Decision` value outside the domain is a defective cell.

### Two duties

1. **Every FR that consumes a runtime capability cites a premise id**, and the carrier is the `Premises` cell of
   the runtime-stack row naming that FR (§ Runtime Stack & Dependency Ownership) — not a prose sentence in the
   plan. A cell naming an absent id is a defective cell (exit `2`); a cited premise that is `falsified` with no
   `Decision` is `falsified-premise-undecided: EP-NNN`. When one FR appears in several rows, every one of those
   rows carries the id.
2. **A known negative conclusion is a `falsified` premise with a `Decision`**, never an "out-of-scope P2/P3" line.
   Parking it is the same defect as not recording it: the fact stays known, and the feature keeps standing on it
   while the document says it does not.

Boundary (A13): planning-time premises only. § Gates § The A13 boundary owns the split between this table, the
inherited-blockers table and `tasks.md` § Environment Prerequisites; this section does not restate it.

## Inherited Blockers

The plan-side table that records what a **dependency** feature already measured, and this feature's disposition of
each record. Mandatory in `plan.md` of an `execution`-class feature. Columns, read by name:

| Column | Content |
|--------|---------|
| `#` | the row's ordinal in this table — bookkeeping only, never a join key |
| `Source row` | the extracted dependency record's locator — the join key, spelled below |
| `Disposition` | the closed domain below |
| `Carrier` | required when `Disposition` is `inherited`; one of the two forms below |
| `Carrier slice` | `this-slice` or a later slice id — see below |
| `Evidence / note` | a path plus one line, or the one-line reason the disposition holds |

### The dependency set is declared, never implied

The plan states which dependencies it read, and for each one the basis on which it is included or excluded. An
implied set is unreadable: nobody can tell whether a row is missing or a dependency was never opened.

**The declaration's marker is fixed, because both the gate and the closure checker read it mechanically.** A plan
with dependencies carries a paragraph whose first token is the literal
`**Dependency artifacts (declared, never implied)**`, followed by one bullet per dependency; each bullet names that
dependency's artifacts in backticks (its feature detail and its `verification.md`), as repo-relative paths or paths
relative to the spec directory:

```text
**Dependency artifacts (declared, never implied)** — the checker reads only the paths in this block:
- `NNN`: `.specify/memory/features/NNN.md`, `.specify/specs/NNN-<slug>/verification.md`
```

Only backticked `.md` paths **inside this block** are read; a backticked `.md` token elsewhere in the section (this
spec's own `verification.md`, a research note) is never a dependency. A plan with no dependencies writes the exact
sentence `Dependency set: none`. Any other dependency-set sentence without the block is an **input error**: an
absent declaration MUST NOT silently disable the fourth finding.

### The extraction set — closed at three sources

Each dependency yields rows from exactly three places and from nowhere else:

| Source | Row |
|--------|-----|
| the dependency's detail, its `## Deferred` section | one row per non-empty list item |
| the dependency's `verification.md` | one row per status row in `blocked` · `deferred` · **`partial`** |
| the dependency's `verification.md` | one row for a **non-empty** `deferred_tasks=` list — an empty value yields no row |

`partial` is inside the set: a dependency may carry `partial` rows and nothing else, and an extraction set that
excludes it is disjoint from the disposition set, which makes the finding unreachable.

### The row locator, and the join key

`Source row` = `<feature-id>:<row-locator>`, no whitespace. `<feature-id>` is the dependency's feature id
(`\d{3}`); `<row-locator>` is exactly one of:

| Form | Written for |
|------|-------------|
| `SC-\d{3}_status` | a `verification.md` status row — e.g. `071:SC-006_status` |
| `deferred_tasks` | a non-empty `deferred_tasks=` list — e.g. `077:deferred_tasks` |
| `deferred:<slug>` | a `## Deferred` list item; `<slug>` = `[a-z0-9][a-z0-9-]*`, the item's label lowercased with whitespace collapsed to `-`, else `row-<n>` by 1-based position inside the section |

`Source row` **is the join key**: every disposition row reproduces the extracted locator verbatim, and a locator
disposed twice is a defective cell (two dispositions for one key). An extracted row with no disposition row of its
own is an undisposed row.

A disposition row that disposes **nothing** — normally `not-applicable` with no extracted record behind it — writes
`—` (or the legacy `(none)`) in `Source row`. That sentinel is not a locator and is never joined; any other value
MUST satisfy the grammar above.

### `Disposition` — closed over three values, and what each one owes

| Disposition | Obligation |
|-------------|-----------|
| `resolved` | the blocker is gone, with re-checkable evidence — a command and its output, or the row's measured value |
| `inherited` | this feature takes the measurement over, and MUST name a runtime-reachable **carrier** (below) |
| `not-applicable` | the thing measured does not apply to this feature, with the reason |

### The `inherited` carrier

`Carrier` is exactly one of two forms, no whitespace:

| Form | Parts |
|------|-------|
| `task:<T-ID>+test:<repo-relative test path>` | **conjunctive**: `<T-ID>` = `T\d{3}` and MUST be a mandatory row of this slice's `tasks.md`, and the test path MUST appear verbatim in that row's description. One part alone is not this form |
| `gate:<GATE-ID>` | `<GATE-ID>` = `GATE-[0-9]+` and MUST be one of this slice's completion gates |

**Eligibility**: a carrier MUST be a `final`-path criterion, a mandatory task row of the same slice, or a mandatory
gate. It MUST NOT be a deferrable `supporting`-path criterion — a thing that may be `deferred` cannot carry an
inherited measurement.

**`Carrier slice`** is `this-slice` or a later slice id (`081c`, `081d`, …). `this-slice` requires both limbs
above to hold in this judgement. A later slice id is legal **only** while the parent feature's claimed status is
`Blocked` and that slice is listed in the plan's § D10 slice table; the row then reads **`inherited-later`**. Any
other value is a defective cell.

### `inherited-later` — a fourth *reading*, never a fourth disposition

The disposition cell stays three-valued. `inherited-later` is derived from `Carrier slice` plus the parent's
claimed status, and it means **disclosed, neither blocking nor resolved**: it is counted separately from resolved
carriers and MUST NOT be counted as undisposed. In such a row `Carrier` is `test:<repo-relative test path>`
**alone** — the task id belongs to a `tasks.md` that does not exist yet, and writing one would be a fabricated id.
`Carrier slice` supplies the slice. The row is re-read at that slice's closure, where the carrier MUST be completed
to `task:<T-ID>+test:<path>` and resolve; an incomplete carrier there is an undisposed row **in that slice**, under
the same reason.

### One reason for five ways to fail

An undisposed row, an `inherited` row with no `Carrier`, a `Carrier` that does not parse as one of the two forms, a
`Carrier` that does not resolve, and a `Carrier` pointing at a deferrable `supporting`-path criterion are judged
**the same**, under `inherited-blocker-undisposed: <feature>:<row>`. The closed reason set does not grow for any of
them. A later-slice `Carrier slice` is not in that class — that is `inherited-later`, above.

Boundary (A13): dependency-inherited records only. § Gates § The A13 boundary owns the split between this table,
the plan's premises and `tasks.md` § Environment Prerequisites; this section does not restate it.

## Schema Uniqueness

What the schema-uniqueness guard asserts, on what subject, over which paths — stated here once. `requirements.md`
SC-009 ④ states the criterion's reading, `contracts/artifact-schemas.contract.md` AS-13…AS-16 the contract
obligation, and the guard test the enumeration; none of the three re-derives an allow-list of its own.

**The subject is the column-name set, not the value domain.** The guarded literal is the **`Column` cell** of each
of this file's three column-declaration tables — the one in § Runtime Stack & Dependency Ownership, the one in
§ Execution Premises and the one in § Inherited Blockers. The names are therefore never enumerated a second time,
here or in the guard: the test reads them out of those three tables, which is the only place they are defined.

**The domain literals are explicitly NOT the subject**, and a guard restated as "the owner's value-domain literals
appear zero times in the scan domain" is **wrong on a real tree** — three of those literals are simultaneously
members of unrelated closed sets that legitimately live in `.specify/templates/` and `.specify/shared/`: `not-required` is the
traceability binary in `.specify/shared/definitions/sdd-routing-definitions.md`; `not-applicable` is the code-review
segment verdict in `.specify/templates/review-template.md` and `.specify/templates/commands/review.md` and the site-layer verdict in
`.specify/shared/workflow/expression-gates.md`; `in-scope` occurs as ordinary English in
`.specify/shared/definitions/derivation-definitions.md`. A literal-set guard therefore has to carry an exclusion list of
its own — which would make the guard's `expected` a second definition point, the very defect it exists to
prevent. The subject is the column set precisely because a column set has no third-party meaning.

**Scan domain**: `.specify/templates/` and `.specify/shared/` — framework source. `.specify/` copies are mirrors of these paths and
are never scanned; a divergence there is a mirror defect, judged by `.specify/scripts/python/sync-mirrors.py --check`, not
by this guard.

**Assertion**: across that domain the three column sets appear **zero** times outside this file, with exactly one
allowed surface: **`.specify/templates/plan-template.md`**, which carries the Execution Premises and Inherited Blockers
column sets as its two skeletons, because an empty table whose columns are not given forces every future plan to
invent its own — the columns are precisely what the skeleton exists to hand down. Its narrowing assertion is that
it carries the column names and **zero** owner-exported domain literals (measured: 0). This file is the definition
site and is the hit the guard excludes by identity, not by a list entry.

**A hit is a whole column set, matched as the ordered cell sequence of a table header row** — not an individual
name. That distinction is what makes the assertion true rather than aspirational: `Status`, `Form`, `Owner`, `ID`
and `Evidence` are ordinary column names of unrelated tables in the same domain (measured: `Status` in
`.specify/templates/feature-index-template.md`, `.specify/templates/glossary-template.md` and `.specify/templates/plan-template.md`'s
Constitution Check table; `Form` in `.specify/shared/definitions/agent-definitions.md`; `Owner` in
`.specify/shared/definitions/derivation-definitions.md` and `.specify/shared/guidelines/directory-governance.md`; `Capability` in
`.specify/shared/guidelines/dogfooding.md`). Matching a single name would either fail on the tree as it stands or force the
guard to name those tables one by one — a hand-maintained exclusion list is exactly the drift the guard exists to
prevent. The set as a whole has no second user, which is why it is the subject.

**Surfaces outside the scan are not exemptions.** `data-model.md`, `contracts/` and `requirements.md` FR-003 live
under `.specify/specs/<key>/`, where the scan cannot reach them; they are therefore **not**, and MUST NOT be
described as, exemptions of this guard. Each still owes its own narrowing assertion — `data-model.md` and
`requirements.md` carry **no** `From | To | Allowed | Condition` transition row (a restated row is an unguarded
duplicate), and a projection may narrow a value domain but never widen it. Those are duties of the projection
relation, owned by the carrier and one-source rules in this file's opening block, not members of a guard
allow-list: calling a path the scan cannot reach an "exemption" makes the allow-list describe a boundary of
nothing while the in-domain surfaces that really do carry owner material go unguarded.

## Review Composition

What `/speckit.review` runs, in what order, and what each part is allowed to answer. This section owns the
composition's **content** — the four segments and their fixed order, each segment's judgment object and boundary
sentence, the expected-artifact denominator and its derivation rule, the Acceptance Reality Check's clause and the
feedback unit census of one composed run. It owns no segment's **method**: the dimension sets and the report slots
belong to the skills, and the two segments a skill carries are named in `.specify/skills/internal/review-feature-quality/SKILL.md`
§ Segment A / § Segment B.

**The two layers, and which one this is.** A **content** owner is the one place a fact about the composition is
written. A **declaration** owner repeats only the shape a caller must find where it is editing: the four segment
headings and the five per-segment field names (`Skill`, `Judgment object`, `Severity vocabulary`, `Inputs`,
`Outputs`) are declared in `.specify/templates/commands/review.md` § Composition **by anchor** to this section. A declaration
made of headings and field names is not a second definition; a copy of this section's segment prose, order rationale
or boundary sentences at that anchor would be, and is a defect. Every other surface — the report template, the two
sibling skills, the docs page — reaches this content by path plus `§ Review Composition`.

Obligations: FR-013, FR-014, FR-015 and FR-016 of the declaring feature own the requirements side; RC-01…RC-19 of
its `contracts/review-composition.contract.md` own the clause-level form; SV-05 owns the status-vocabulary
boundary. This section states what those obligations mean together and cites nothing's wording on their behalf.

### Four segments, one fixed order, and one check that is not a segment

| Order | Segment | Judged by | Answers the question |
|-------|---------|-----------|----------------------|
| 1 | process | `review-sdd-process` | was this slice produced by a sound SDD process? |
| 2 | artifact | `review-feature-quality` § Segment A | does the slice's artifact set meet what its stage requires? |
| 3 | implementation | `review-feature-quality` § Segment B | does this slice's delta do what `requirements.md` and `tasks.md` say? |
| 4 | code | `code-review` | does the committed code delta contain verifiable defects? |
| — | Acceptance Reality Check | the closure checker, through § Closure Verdict | does the feature's claimed status survive its own counts? |

**The order is content, not invocation.** `$ARGUMENTS` guides review focus; it never selects, reorders or skips a
segment. No execution class and no expression class exempts the process segment, and neither does an absent code
delta, an empty base range or an earlier segment's outcome: the process segment runs on every invocation. Because the
order is a property of the composition, no delegated skill may reverse or skip another — and the Acceptance Reality
Check is last for the same reason, since its input is the state the four segments leave behind.

### Each segment answers its own question, and only that

**Process** judges the SDD process that produced the slice — process and tooling quality: friction, ambiguity,
cargo-cult boilerplate, drift risk and process gaps. It does not judge the artifacts' content and it does not judge
the code, and it is **not** a substitute for the artifact or implementation segments: a clean process review says
nothing about whether the artifacts are complete or whether the implementation delivered.

**Artifact** judges the slice's **stage artifacts** — the set the slice's stage rules and `plan.md` § Project
Structure require (see the derivation rule below) — for completeness, internal consistency, traceability
(FR → task → SC → evidence), dependency and premise ownership, and acceptance honesty. Its object is the artifacts,
not the code that produced them and not the process that produced them.

**Implementation** judges **this slice's `base..head` delta** against `requirements.md` and `tasks.md` for
correctness, scope and regression, and it runs or verifies the feature's smoke test, recording the command, the exit
code and the evidence path. `base..head` resolution has one route, the code skill's
`.specify/skills/internal/code-review/scripts/git-delta-review.sh`; this segment implements no second base resolution. The
`final_path` record appears here only as a **quotation** — the hard condition stays the implement gate's.

**Code** judges the committed code delta for verifiable defects under its own method and its own six-level family.

**Neither answers the other, and the code segment answers neither.** An artifact set can be complete while the
implementation is wrong, an implementation can satisfy every requirement while the artifacts contradict each other,
and a code delta can be clean while a requirement went unimplemented — so the artifact and implementation segments
MUST NOT substitute for one another, and neither MUST be answered by the code segment. Each of the four is written
up, ranked and read on its own conclusion.

The artifact segment reads the three plan/tasks tables' **ownership** as evidence — which artifact owns a fact and
whether the pointer is there — but not their rules: the same-fact rule's one statement is § Gates § The A13 boundary,
and this section does not restate it.

### Never merged, never converted, never scored

The four conclusions are never merged. Not into one severity system, not into one score, not through a mapping
table, not through a numeric conversion, and not through a "highest severity wins" rule: no mapping table between
the `P0`/`P1`/`P2` family and the six-level code family may exist anywhere in the tree, and the run stores no
combined value. Each family keeps its own owner — `P0`/`P1`/`P2` by `.specify/skills/internal/review-sdd-process/SKILL.md`,
the six-level family by `.specify/skills/internal/code-review/SKILL.md` — and neither skill redefines, relabels or reweights a
level of the other's family. Two vocabularies that can be converted into one another are one vocabulary, and the
second one then no longer means what its owner says.

### The artifact denominator is the expected set

The coverage denominator is derived, and the derivation is the whole rule:

> The **expected set** is the union of what the slice's stage rules require it to have produced for the stage it is
> closing, and what that feature's `plan.md` **§ Project Structure** declares it owns. The denominator is that union —
> never "the artifacts that happen to exist".

A member of the expected set that is absent from disk is **a finding** and **counts as uncovered**. Both, not
either: a missing artifact reported but excluded from the denominator under-reports the gap, and one counted but not
named tells a reader a number moved without telling them what is missing.

"Not present" therefore can never render as 100 % coverage, and that is the entire point of the rule. The competing
reading fails in one direction only — a missing artifact drops out of the denominator, so an empty directory reads as
full coverage and the review reports nothing — which is why the denominator's source is fixed here rather than left
to each run's taste.

The coverage line is written `checked / expected`, and its product is a **per-feature fact, not a constant**: for a
feature whose plan declares the standard spec set the union is that set, and for a slice whose stage rules add or
drop a member it is not. The seven-member set is the product **when the plan declares nothing further**; a plan
that declares additional artifacts extends the set, and the run MUST print the size it used — one number, never
two readings of the same rule. The finding form (severity, artifact path, and the `line` rule with its one stated-reason
escape) belongs to the segment's method, not here.

### Records and rotation

A composed run writes two records: `review.md` (the four segments plus ARC) and `code-review.md` (the code
segment). When a record already exists, the run archives it **inside the same directory** as
`<record>-<slice>.md` — the slice id of the run, e.g. `review-081c.md` — and then writes the new record. The
timestamped `<record>-<YYYYMMDDTHHMMSSZ>.md` (UTC, second resolution) form is the fallback when no slice id
exists; two runs inside one second either wait for the next second or exit `2`, an existing archive path is
never overwritten, and a first run records `none`. Both records follow the same rule, and the run records the
archive path it used.

### The Acceptance Reality Check is a check, not a fifth segment

The Acceptance Reality Check (ARC) reads the closure checker's `final_path` record for the feature and copies it
**verbatim and in full** into the report's carrier slot `### 2.4`. The record's key set, its closure and its bucket
meanings are owned by § Closure Verdict § `final_path` counts, computed once; this section does not restate them, and
neither does ARC print a narrower summary of them — a partial copy is a re-derivation with extra steps.

ARC then compares the copied record against the feature's **claimed** status. When the claim is `Implemented` or
`Ready for Review` and the record's `pass` bucket is zero, ARC emits the fixed item `F-ACCEPTANCE` at `P0` and the
transition is **refused**. The refusal names the condition that failed, not merely that the transition was refused,
and it leaves the claimed status **unchanged** — `Implemented` stays `Implemented` and `Ready for Review` stays
`Ready for Review`, because a refusal is not a downgrade and this feature does not admit one. A user waiver of the
transition's conditions does not lift ARC's zero-`pass` refusal; the waiver is recorded as residual risk in
`review.md` and the item still fires.

The comparison verdict pairs the two alphabets explicitly: `agree` when the checker's verdict is `block` and
the claim is already `Blocked`/`Planned` (or when `accept` agrees with the claim); `refused` when the verdict is
`block` and the claim is `Implemented`/`Ready for Review`, or when `F-ACCEPTANCE` fires.

ARC is **not a segment** and is **not delegated**: it runs one deterministic program and reports that program's
verdict, so there is no judgement for a skill to own and no fifth entry in the order above. It is not a model
judgement, it is not "ARC reads `verification.md` and counts", and it never recomputes a bucket — the three
call sites share one verdict (§ Closure Verdict § When the judgement runs), and a second counter at the review site
would be a second source of truth for the same counts.

The literal `F-ACCEPTANCE` is owned by the declaring feature's `## Shared Strings`, so its tests can pin the spelling
verbatim; that is a per-spec declaration for matching, not a second schema, exactly as with the seven reason
templates in § Closure Verdict.

### The feedback unit census of one composed run

One composed run records **four** units, not three and not two: the command (`/speckit.review`), the delegated
process skill (`skill:review-sdd-process`), the carrier skill of the two middle segments
(`skill:review-feature-quality`) and the delegated code skill (`skill:code-review`). All four share the run's
`run_id` and differ in `unit_id` — the key the feedback engine already uses — so none dedups, merges or truncates
another, and each completes its **own** closing record.

The count is a consequence, not a preference: every runtime-reachable segment carrier is a unit, so adding a carrier
adds a unit, and the count moves with the carrier rather than the carrier being folded into a neighbour to keep the
number still. Three rules follow:

- the command MUST NOT suppress any skill's wrap-up, MUST NOT write a skill's run determination on its behalf, and
  MUST NOT back-fill one after the fact;
- a segment recorded `not-applicable` or `not-evaluated` still closes its own record — a non-conclusion is a
  conclusion about that segment, not a missing unit;
- the census is stated on the surfaces that run it (the command's feedback boundary and each skill's own
  closing-record section) and counted by a guard, so a quiet reversion to three is a failing assertion rather than a
  reading nobody re-checks.

## Extension Points

Sections later slices add to **this** file. Each line names the owner its obligations have **today**, so that
nothing is undefined while the section is absent.

- The closed status **value domain** of `.specify/templates/feature-index-template.md` (**081d**; owner today: the
  declaring specification's **FR-018**, via SV-06) — that file carries only the `Status` **column header** of its
  index table today, so its obligation is to **add** a value domain rather than to insert one value into an
  existing list, and the transition rows and row-level semantics stay with the owner named in § Feature Status.
  The reconciliation of the four `blocked` literals (**FR-019**) is no longer promised here: it landed as
  § Verification Vocabulary § The four `blocked` literals are four unrelated facts.
