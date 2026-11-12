# Canonical `## Artifact Commit` Step

This file is the single source of truth for the `## Artifact Commit` step embedded
by every artifact-producing command. It exists because a gap was measured, not
predicted: one feature's five upstream runs (`requirements`, two `clarify`,
`plan`, `tasks`, `analyze`) produced roughly 1,200 lines of design artifacts that
existed **only in the working tree**, and were finally committed in one lump by
`/speckit.implement` at the start of its own run. `git log --diff-filter=A` showed
every design artifact sharing that single implement-phase commit, while
`plan.md`'s own header was dated a day earlier.

Two consequences, both real:

- **Loss window.** The whole design phase sat one `git checkout`, one failed
  stash, or one parallel session away from being unrecoverable.
- **Broken audit trail.** `/speckit.review`'s step 2 reconstructs process history
  from `git log` scoped to the spec directory. When every design artifact shares
  one later commit, no design-phase timeline can be attributed to the command that
  produced it — the review had to fall back to feedback-entry timestamps and
  document-internal dates.

`/speckit.implement` already carries this obligation for its own output ("The spec
dir MUST NOT be left *entirely* uncommitted when validation completes"). That rule
was enforced only at the end of the lifecycle, by the one command that did not
create the risk. This step moves it to each producer.

## The step

At wrap-up — the same lifecycle point as the `## Feedback` and `## Documentation`
steps, and **before** them so the commit contains the artifact rather than the
reflection about it:

1. **Commit the artifact this command produced**, and only that. Stage by explicit
   path; never `git add -A`, which silently carries unrelated working-tree state
   (and any destruction in it) into an otherwise-clean commit.
2. **Run the deletion-surface audit first**: `git diff --cached --diff-filter=D
   --name-only`. Every listed deletion must reconcile against this run's intent;
   an unexplained deletion aborts the commit for human review.
3. **Message shape** follows `.specify/templates/commit-template.md`
   (`[TYPE]([SCOPE]): [SUBJECT]`, single line). Use `docs(<requirement-key>)` for
   spec artifacts; name the command that produced it so the trail reads as a
   sequence.
4. **Do not commit another command's artifacts.** If the spec directory contains
   uncommitted files this command did not produce, that is a **finding**: report
   it in the wrap-up as an upstream deviation rather than sweeping it into this
   commit. Folding it in destroys exactly the attribution this step exists to
   create.
5. **Approval routing** follows the host project's confirmation discipline. Where
   commits are pre-authorized for the session, commit without re-asking; otherwise
   present the command and wait. A run MUST NOT end with its artifact uncommitted
   while no commit command was ever presented.

## Boundaries

- **Not a status transition.** Committing an artifact does not advance a feature's
  lifecycle status; that remains gated by `.specify/shared/workflow/feature-integration.md`.
- **Not a substitute for pushing.** The artifact-commit step itself does not push;
  pushing belongs to the close-out step that follows it. That step is governed by the
  framework-level git workflow state file (`.specify/workflow/git.md`), derives its push
  targets from the project's `Closeout remotes` declaration, and skips the push when the
  declaration authorizes none.
- **Read-only commands** that produce no artifact (a pure analysis with no
  authorized remediation) skip this step and say so in one line, rather than
  creating an empty commit.

## The `## Close-out` step

This is a **named section of this same owner**, not a second owner: the step lives here because
this file already owns "what a write run leaves behind", and the close-out is the last thing a write
run leaves behind. Its position in the lifecycle is fixed — **after** the artifact commit and **after**
the record-producing steps (`## Feedback`, the documentation evaluation), because the close-out
commits the records those steps produce. The artifact commit stays first so attribution is unchanged,
and no existing step is moved or renamed.

The close-out is **not a command**. A run reaches it by embedding this file, exactly as it reaches the
feedback and documentation steps, so every artifact-producing command and every unattended mechanism
gets it without a new entry point.

### What it commits

1. **The run's records, once.** Every record the run produced (a run-determination record, an
   exec-quant record, a feedback entry, a session/memory note — whichever classes this run actually
   produced) is carried by **exactly one** commit, together with its receipt. The four record classes
   are not split into per-class commits: attribution's unit is one run, so one hash names the whole set.
2. **Never twice.** A record file that appeared in the artifact commit MUST NOT appear again here. A
   record the close-out could not include is **listed in the report** with the reason; it is never
   silently dropped, and it is never swept in by a whole-tree staging form.
3. **The artifact commit is not re-opened.** If the run produced artifacts and no records, the close-out
   commits nothing new and says so (see the forks below).

### The receipt

Each run writes **one receipt** — a new file, never an edit of an existing one — under
`.specify/memory/retention/closeout/`, named by the run and its timestamp, written once. It is a
sibling of the retention family's other outputs (`receipts/`, `plans/`) and creates no new top-level
store.

The receipt names, per covered record: the record's path, its action (`committed`), and the hash of
the commit that carried it — plus a **pointer** to the read rule of the engine that consumes that
record class, so the receipt never restates a schema it does not own.

- The close-out MUST NOT modify, truncate or delete a record file. Consuming, retiring and
  compacting records is the retention lane the receipt points at, and that lane owns alone whether a
  record may be removed.
- The hash is written **per row**, and because one run produces exactly one records commit, **every
  `commit` value inside one receipt is equal**. That invariant — not the field's arity — is what makes
  the receipt checkable.
- Two concurrent runs never contend: each writes a distinct timestamp-named path.

### The report

Every close-out ends with a report, and **omission is a defect**. The field set:

| Field | Content |
|-------|---------|
| receipt | the receipt path, or `none` with the reason it was not written |
| records commit | the commit hash, or `not-created` with the reason |
| merge | the merge outcome, or `not-run` with the reason |
| push targets | one row per target with its result; or one row saying the step was skipped and why |
| deviations | another line's uncommitted files, by path |
| failure | `none`, or the failing stage plus the exact command |

A close-out that did nothing says so in one line (`nothing to do — <reason>`). "Nothing to do" is
itself a reportable outcome, never an empty report.

### The three forks

| Fork | Condition | Behaviour |
|------|-----------|-----------|
| read-only run | no artifact and no record was produced | skip the close-out entirely, state it in **one line**, and create **no empty commit** |
| artifacts without records | an artifact commit exists, no record was produced | still merge and push what exists; the report states that this close-out carried no records commit |
| other lines' dirty files | the working tree holds uncommitted paths this run did not produce | report them as an **upstream deviation**; never stage them |

The third fork is the one that silently widens a commit's blast radius if it is missed: the close-out
stages **only the paths this run produced, by explicit path**, and never uses a whole-tree staging
form. It never stashes, resets or cleans a path it does not own.

### Its boundaries

- **It never writes the workflow state surface.** It reads the managed block and derives its sequence;
  it does not fill, repair or create the block, and it does not run Bootstrap. A block that is absent,
  unpaired or still a placeholder is a **reported** state, handled as the declaration contract defines.
- **It never widens its own authority.** The declared strategy authorizes the routine steps of the
  derived sequence and nothing else. A **destructive or governance-kept** step stops and presents
  before it runs: the close-out does not execute it, does not treat the strategy as covering it, and
  hands the decision back with the exact command. The gate list is owned by
  `.specify/shared/guidelines/confirmation-gates.md` and is reached **by pointer** — never restated here.
- **It fails at the first failure.** A failing stage stops the run, is recorded where the run's state
  is kept, and is printed with its exact command. There is no automatic retry, no `--force`, and no
  `--force-with-lease` outside that action's own confirmation.
- **One implementation.** Every unattended mechanism that commits, merges or pushes reaches this
  section by pointer to this file; none keeps a second close-out of its own, and reaching it by
  pointer grants the *sequence*, never a new permission.

## Why a shared owner rather than five copies

The rule could have been written into each command template directly. It was not:
five restatements of one obligation is five future drift points, and the
`/speckit.implement` copy already existed — so the obligation would have had two
owners with no way to keep them in agreement. Each command embeds a pointer to
this file instead, which is the house pattern already used for `## Feedback`
(`feedback-step.md`) and `## Documentation` (`docs-step.md`).
