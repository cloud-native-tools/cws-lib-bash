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
- **Not a substitute for pushing.** This step commits locally. Pushing is a
  shared-state action governed by the host project's git workflow state file
  (`.specify/git-workflow.md`) and requires its own authorization.
- **Read-only commands** that produce no artifact (a pure analysis with no
  authorized remediation) skip this step and say so in one line, rather than
  creating an empty commit.

## Why a shared owner rather than five copies

The rule could have been written into each command template directly. It was not:
five restatements of one obligation is five future drift points, and the
`/speckit.implement` copy already existed — so the obligation would have had two
owners with no way to keep them in agreement. Each command embeds a pointer to
this file instead, which is the house pattern already used for `## Feedback`
(`feedback-step.md`) and `## Documentation` (`docs-step.md`).
