# hazard taxonomy

Every verdict is `(severity, code, detail)`. Severity is the coordination cost of
leaving it alone, not the size of the diff.

## P0 — work can be lost or forked irreconcilably

| Code | Fires when | Why it is P0 | Handling |
|------|-----------|--------------|----------|
| `MULTI_DIRTY` | Uncommitted changes exist in **≥2 different environments** for the same logical repo. | Two divergent WIPs against a shared base. Whoever commits second must merge by hand, and neither side is recorded anywhere. | Review both working trees before anything moves. Decide which is authoritative, commit and push it, then bring the other forward. Never ff-pull over either. |
| `DIVERGENT_UNPUSHED` | ≥2 environments have `ahead > 0` **on the same branch**. | The same branch name has genuinely forked; one side's history cannot fast-forward onto the other. | Pick a base, rebase the other onto it. This is a three-tier branch decision → delegate to `git-workflow`. |

## P1 — work exists in exactly one place, or a pointer is wrong

| Code | Fires when | Handling |
|------|-----------|----------|
| `UNPUSHED` | Exactly one environment has `ahead > 0`. | Land it first. Until it reaches the shared remote it exists on one machine only, and every other environment's state is a partial view. |
| `PARALLEL_UNPUSHED` | ≥2 environments have `ahead > 0` on **different** branches. | Usually deliberate parallel work, not a fork. Land each on its own branch; confirm the branch names are intended before assuming so. |
| `HEAD_DIVERGED` | Same branch, different HEAD sha, across **≥2 environments**. | The strongest signal available, because it needs no fetch. Read together with `STALE_REFS`: if refs are stale, trust this over `ahead/behind`. |
| `SUBMODULE_DRIFT` | `git submodule status` reports `+` (checked-out sha ≠ gitlink) or `U` (conflict). | The parent pins one commit and the working tree has another. Editing inside a submodule is `git-submodule-edit`'s job — delegate rather than bumping the gitlink here. |

## P2 — recoverable, but ordering matters

| Code | Fires when | Handling |
|------|-----------|----------|
| `BEHIND_DIRTY` | `behind > 0` **and** the tree is dirty. | A plain pull will refuse or clobber. Protect first (`stash push -u`), then ff-pull, then hand the stash back deliberately. |
| `STASH` | `stash list` is non-empty. | Hidden work with no branch and no remote copy. The single easiest thing to lose in a machine rebuild. Surface it; do not drop it. |
| `DETACHED` | `HEAD` is not on a branch. | Fine for a pinned submodule, suspicious for a top-level clone: commits made here are unreachable once HEAD moves. |

## P3 — informational; may be entirely correct

| Code | Fires when | Note |
|------|-----------|------|
| `BEHIND` | `behind > 0`, clean tree, `ahead == 0`. | The one genuinely trivial case: ff-pull is in the SAFE set. |
| `SAME_ENV_CLONES` | ≥2 dirty checkouts of one origin **inside a single environment**. | Deliberate parallel clones / worktrees. Reported so the checkouts are known, explicitly **not** treated as a cross-environment conflict. |
| `NO_UPSTREAM` | Branch has no upstream. | `ahead/behind` are meaningless here; the branch is local-only. |
| `NEVER_FETCHED` | No `FETCH_HEAD` in the git dir. | `ahead/behind` are `0/0` by absence of data, not by agreement. |
| `STALE_REFS` | `FETCH_HEAD` older than 3 days. | Quantifies how much to distrust `ahead/behind`. |

## Deliberate non-verdicts

These are **not** hazards, and treating them as such produced false positives in
practice:

- **A submodule's HEAD differing from a standalone clone of the same origin.** The
  parent pins it; that is the whole point. Submodule checkouts are keyed separately
  (`⊂<parent>`) precisely so this comparison never happens.
- **Two clones of one origin on one machine at different commits.** Parallel work on
  two branches. Only `SAME_ENV_CLONES` (P3) is emitted.
- **A repo naming its own origin in `go.mod` / `package.json`.** A self-declaration,
  not a dependency edge; dropped during graph construction.
- **Untracked files alone.** Counted and shown, but on their own never escalate past
  the severity the other signals justify — build output is not pending work.

## Reading the report

Exit code `0` means nothing was flagged; `10` means at least one repo was. Group
order is by worst severity, then key. Within a repo the matrix comes first (raw
observation) and verdicts second (interpretation) — check the matrix when a verdict
looks wrong, because the matrix is what was actually measured.
