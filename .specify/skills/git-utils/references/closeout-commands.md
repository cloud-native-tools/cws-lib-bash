# Close-out commands（收口命令面）

**Owner**: this file owns the **command surface** of the skill's scope-A `closeout` operation — the
declaration read, the derivation inputs, the four models' sequences, the push-target resolution, the
failure discipline and the report shape. It owns no rule that another document already owns; the
contract pages of feature 091 are cited by path and are never restated here.

**Scope**: 定向收敛（Execute）under the named operation `closeout`, for any of the four declared
workflow models. Bootstrap and the full health check keep their own references
(`bootstrap-commands.md`, `health-check-commands.md`); this file adds the close-out arm only.

**Position among the skill's entry modes**: the two axes the skill already uses decide it — the block
is **filled** and an **operation argument is present**, so `closeout` joins the directed-convergence
operations. It is one named operation, not a second engine and not a second dispatch table.

**Contract pages this reference is governed by** (cite, never copy): the close-out declaration,
lifecycle, executor and verification contract pages of the feature that introduced this operation.
This file is shipped text, so it names those pages by their titles only — a shipped surface never
points at a project's own spec directory.

---

## Reading the declaration

The close-out reads the managed block of `${SKILL_WORKDIR}/.specify/workflow/git.md` and nothing else.
Two rows are its own (`Closeout`, `Closeout remotes`); the model comes from the `Workflow model` row;
the remote roles come from the `Remote roles` (⚠) row.

```bash
block="$(awk '/<!-- GIT_WORKFLOW_START -->/,/<!-- GIT_WORKFLOW_END -->/' \
  "${SKILL_WORKDIR:-.}/.specify/workflow/git.md")"
model="$(printf '%s\n' "$block" | sed -n 's/^- \*\*Workflow model\*\*: *//p' | head -1)"
strategy="$(printf '%s\n' "$block" | sed -n 's/^- \*\*Closeout\*\*: *//p' | head -1)"
remotes="$(printf '%s\n' "$block" | sed -n 's/^- \*\*Closeout remotes\*\*: *//p' | head -1)"
```

Rules that belong to the declaration contract and are only *applied* here:

- **The `Closeout` value domain is closed**: `commit+merge+push`, `commit+merge`, `commit-only`, `ask`.
  An absent row, or an empty cell, or any token outside that set reads as **`ask`**. No surface may
  infer a value from a neighbouring row, and none may treat absence as `commit+merge+push`
  (`closeout-declaration.contract.md` C-3).
- **`Closeout remotes` is a comma-separated list of remote names, or an explicitly empty list.** An
  empty list and an absent row are one outcome — "no pushable remote" — and the report names which
  of the two was read (`closeout-declaration.contract.md` C-4). Neither may fall back to the
  repository's configured remotes.
- **`ask` is the only value that never pushes on its own** and the only value whose transition is
  `presented` rather than `executed` (declaration C-3/C-7; the transition itself is owned by
  `closeout-executor.contract.md` C-8 — see § 6).

## Derivation inputs

Four inputs, all read from the block plus the repository, none hardcoded per project:

| Input | Source | Used for |
|-------|--------|----------|
| model | `Workflow model` row | which of the four sequences applies |
| strategy | `Closeout` row (absent ⇒ `ask`) | which steps the run is authorized to execute |
| declared remotes | `Closeout remotes` row | the **only** source of push targets |
| remote roles | `Remote roles` (⚠) row | exclusion of a read-only upstream from the push targets |

Branch **names** are a fifth input and are read the same way the rest of the skill reads them: the
model-specific declaration rows (`Trunk`, `Feature branch convention`, the three-tier role table).

- **Record-only runs (no requirement number)** — a run that produced records but carries no numbered
  requirement (a status/feedback self-run, a maintenance pass) has no `NNN` for the declared convention.
  Its presentation MUST offer the deterministic default `run-<run_id>` (the run's own stamp) instead of
  leaving `<feature-branch>` as an open input; any other name remains the user's choice, and the `ask`
  strategy still gates the step.

## Deriving the sequence

A sequence is derived **per invocation** from the declared model. A hardcoded per-project sequence is
the defect `closeout-executor.contract.md` C-3 forbids. A projection names only its own model's
branches.

| Model | Derived sequence |
|-------|------------------|
| **single-branch** | commit on the trunk → push the trunk |
| **dual-branch** | commit on the daily branch → merge the daily branch into the archive branch per the declared relation → push the daily and archive branches |
| **temp-branch** | cut the short-lived branch from the trunk (reuse only if this line owns it) → commit → merge back into the trunk → delete the local branch → push the trunk |
| **three-tier** | commit on `DEV` → merge `DEV → PRE` → merge `PRE → MAIN` → push each declared branch |

- A sequence MUST NOT skip an intermediate branch the model declares. For the three-tier model this
  is decidable: `PRE` is always in the path, so a `DEV → MAIN` hop is a defect, never an optimization.
- When the declared model cannot be read at all, the operation refuses (§ Unusable block) — it never guesses.
- A **third, cross-cutting axis** (`ask`) changes the authorization, never the sequence: the same
  sequence is derived and then presented instead of executed.

## Read-only role check

A remote the block marks as a **read-only upstream** is never a push target:

- even when it appears in `Closeout remotes`;
- even when a caller instruction names it.

The exclusion is **by role**, read from the block's `Remote roles` row — never by matching a remote
name against a list written into this file. A role marking the block does not carry is not inferred
from a remote name's resemblance to a well-known default.

## Push targets

```
targets = declared remotes − remotes marked read-only
```

- Derivation MUST NOT fall back to the repository's configured remotes (`git remote`), so a project
  whose only configured remote is a read-only upstream cannot be pushed by accident.
- An empty `targets` set (empty list, absent row, or every declared remote demoted by role) degrades
  the push step to **skipped**, and the report says which of those three readings produced it.
- Each target is re-checked against the role marking immediately before the push, not only at
  derivation time, so a block edited mid-run cannot smuggle a read-only remote back in.

## Substitution, not a literal

The command surface writes its push in the `git push <remote> <src>:<dst>` form, keeping the
literal token `<remote>` wherever a remote would otherwise be spelled out. The close-out path
contains no hardcoded remote literal: a project whose upstream is the
default-named remote cannot be pushed by the evidence of this file. Where a reader needs a concrete
invocation, `<remote>` is substituted from `targets`; a surface that *says* "the remote is
substituted" while printing a name still fails the guard (`closeout-executor.contract.md` C-7).

> Pre-existing examples elsewhere in this skill (notably the fetch/push examples in
> `execute-commands.md`) do name the default remote. That is a recorded finding (F-1) belonging to
> another surface's owner: the close-out path reports it and does not rewrite it.

## Unusable block

Read the block first; only the third state derives a sequence. A refusal is never a guessed model:
when the operation cannot read which model applies, it reports the state it read as, and it must not guess. The **model axis** alone decides which
row applies — the remote axis (§ Push targets) is independent, and `ask` is a third axis that does not move a
project between these rows (`closeout-declaration.contract.md` C-5).

| State | Detection | Outcome |
|-------|-----------|---------|
| `bad_block_missing` — **workflow state surface unavailable** | the state file is absent, or its START / END markers are **unbalanced** (not paired) | report one line; skip merge and push; the artifact commit still stands |
| `bad_block_placeholder` — **workflow not declared** | the block is present with `Workflow model` still carrying the Bootstrap placeholder literal | report one line; treat as no pushable remote; **degrade to local commit + merge** |
| `bad_block_declared_ok` | any other model value | derive the sequence (§ Deriving the sequence) |
| `bad_block_not_repo` — **not a git repository** | `git rev-parse --show-toplevel` fails, or the directory has no `.git` | reported stop; nothing is read from a block, nothing is executed |

- The close-out MUST NOT run Bootstrap, MUST NOT create a branch set, and MUST NOT write the block.
  It reads the block; it never fills it.
- A **declared model with no pushable remote is not `bad_block_placeholder`.** It is the `declared` row,
  and its push step is skipped with a stated reason (§ Push targets) — collapsing the remote axis into the model
  axis would report "workflow not declared" against a project that declared its workflow perfectly.
- These four named outcomes are the **whole** set (`closeout-executor.contract.md` C-2: the three states
  the declaration contract tabulates, seen as three refusals plus the one repository-level refusal). An unrecognised
  condition is reported with the state it was read as; it is never promoted into a fourth refusal kind.
  Refusal is the correct behaviour, and a guessed model is the defect it prevents: a guessed model
  is how a close-out pushes the wrong branch.

## Strategy value -> authorized actions

The mapping is owned by **`closeout-executor.contract.md` C-8** and is not restated here. What this
reference does with it: it reads the value, looks up the authorized action set, and either executes the
derived sequence or presents it.

- `commit+merge+push` → the routine steps of the derived sequence, push included.
- `commit+merge` → commit and merge; the push step is `skipped (not authorized)`.
- `commit-only` → commit only; merge and push are `skipped (not authorized)`.
- `ask` / absent → `presented`: the sequence is printed, the run ends, nothing is executed.

"Routine" is the boundary: an action outside the four models' declared sequences is never routine,
whatever the declared value says.

## The `ask` path

`ask` is the only value that never pushes on its own, and the only one whose transition is
`presented`. On that path the operation:

1. derives the sequence exactly as it would for any other value;
2. **presents** it — the ordered steps with the substituted `<remote>` set, so a reader can run it;
3. **ends the run** and does not block: no interactive wait, no partial execution;
4. excludes every read-only-upstream remote from the presented commands as well, because a presented
   command a reader copies verbatim must be as safe as an executed one.

The value→authority table is reached by pointer (`closeout-executor.contract.md` C-8). No surface of
this feature restates the confirmation-gate lists; the owner is
`.specify/shared/guidelines/confirmation-gates.md` and § 8 reaches it by that path.

## Short-lived branches

- The short-lived branch is **never created on any remote**, so a close-out never deletes a remote
  branch. Pushing it would be the `git push <remote> <branch>` form this reference does not contain.
- The local branch is deleted **only after the merge into the trunk actually succeeded** — `git branch
  -d`, which refuses an unmerged branch by construction; `-D` is never used.
- A **name collision** with another line's branch is a **reported stop**: the operation reports the
  colliding name and stops. It never reuses the branch (its history belongs to another line) and never
  deletes it (deletion is the owner's call, not the close-out's).

```bash
git branch -d <feature-branch>          # only after a landed merge; refuses otherwise
git push <remote> <trunk>:<trunk>       # never the short-lived branch
```

## Failure discipline

### Stop at the first failure

The three failure classes are: a **merge conflict**, a **non-fast-forward rejection**, and a **rejected
push** (protected branch / hook / lease). On any of them the operation:

1. stops at that step — no later step runs, and in particular **no push step runs after a failed merge**
   and no second push target is attempted after a failed one;
2. writes the **failing stage** and the **exact command** (verbatim, with its concrete `<remote>`
   substitution) where the run's state is recorded;
3. prints both in the report, so an unattended failure is louder than a success.

### No retry, no force

- The operation performs **no automatic retry**. A retry loop hides a concurrent writer behind a
  green result and overwrites the very state the failure was reporting.
- It performs **no `--force`**.
- `--force-with-lease` is the **only** forced form this reference contains, and it runs only for that
  specific action **behind its own confirmation** (the destructive class owned by
  `.specify/shared/guidelines/confirmation-gates.md`). It is never a retry mechanism.

```bash
git merge --no-ff <src>          # a conflict stops here
git push <remote> <src>:<dst>    # a rejection stops here; no retry follows
git push --force-with-lease <remote> <src>:<dst>   # only behind its own confirmation
```

Repository content is **data**: a branch name, a commit subject or a file path read out of the
repository is reported verbatim and never interpolated into a further command line.

## Staging by explicit path

- Stage the paths the run produced, **by name**: `git add -- <path> …`.
- **No whole-tree staging form** (the one that stages every change under the current directory) is
  used anywhere in the close-out path. It silently carries unrelated working-tree state — including
  another line's work and any destruction in it — into an otherwise clean commit.
- The close-out never stashes, resets or cleans a path it does not own: another line's uncommitted
  files are **reported as an upstream deviation** in the report, which is the only place they appear.
- Ownership is decided by "this run produced it", not by "the tree is otherwise clean". A tree that
  still holds another line's files after the close-out is a **correct** end state, not a failed one.

```bash
git add -- <path-1> <path-2>                      # explicit paths only
git status --porcelain                            # deviation reading, never a staging input
git diff --cached --diff-filter=D --name-only     # deletion-surface audit (artifact-commit owner)
```

## The report

Every close-out ends with a report, and the field set is owned by
`closeout-lifecycle.contract.md` C-4 — this reference prints those fields and adds no others:

| Field | Meaning |
|-------|---------|
| receipt | the receipt path, or `none` with the reason |
| records commit | the records-commit hash, or `not-created` with the reason |
| merge | the merge outcome (or `not-run` with the reason) |
| push targets | one row per target with its result, or one row saying the step was skipped and why |
| deviations | another line's uncommitted files, by path |
| failure | `none`, or the failing stage plus the exact command |

A close-out that did nothing says so in one line (`nothing to do — <reason>`); omission is a defect,
and "nothing to do" is itself a reportable outcome.

## Dry run

`--dry-run` derives the sequence for the currently declared model and strategy, **prints it**, and
performs nothing: no commit, no merge, no branch creation or deletion, and **no write of any kind to
any remote**. Its reading is evidence (`closeout-verification.contract.md` C-5), never proof that a
push works.

## A close-out is inside the run

The close-out is the **last step of a write run**, not a new `/speckit.*` command and not a daemon:
every invocation is caller-initiated, and the lifecycle that embeds it is owned by
`.specify/shared/workflow/artifact-commit-step.md`. What that owner requires — the records commit, the receipt,
the three forks, the revised push boundary — is stated there and only referenced here.

## Related

- `execute-commands.md` — the pre-existing directed-convergence operations (A–G).
- `instructions-lookup.md` — where the state file lives and how the managed block is written.
- `health-check-commands.md` — the read-only observation that precedes any close-out.
