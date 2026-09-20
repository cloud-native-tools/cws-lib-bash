# coordination playbook

## The one ordering rule

**Work that exists in only one place lands first.**

A commit sitting on a single machine has no second copy. Every operation elsewhere
either ignores it (fine) or makes merging it harder (not fine). So the sequence is
always:

1. `fetch` everywhere — free, read-only, makes the rest of the judgement honest.
2. Land the unique work: review → commit → push, on the environment that holds it.
3. Bring every other environment forward (ff-pull), now that the shared remote is
   the superset.

`plan` emits exactly this order and marks each step `SAFE` or `GATED`.

## Choosing the authoritative environment

When two environments both hold uncommitted work (`MULTI_DIRTY`), one has to go
first. In descending priority:

1. **The one with unpushed commits.** Its history is already further along; making
   it land first means the other side rebases onto a superset instead of forking.
2. **The one whose changes are larger or older.** Reconstructing a small recent edit
   elsewhere is cheaper than reconstructing a large one.
3. **The one you are sitting at.** You can inspect it, run its tests, and judge
   whether the change is even worth keeping.

Never resolve this by picking whichever machine is convenient to reach. Look at both
working trees first — this is the one hazard where the skill deliberately refuses to
choose for you.

## Per-hazard sequences

**`BEHIND` (clean)** — SAFE, automatable:
```
git fetch --all --prune
git branch fleet-backup/<ts> HEAD     # cheap insurance
git pull --ff-only
```

**`BEHIND_DIRTY`** — SAFE but ordered; the stash is not returned automatically:
```
git fetch --all --prune
git stash push -u -m git-fleet        # protect
git pull --ff-only
# then hand the stash back yourself, deliberately:
git stash list                        # note the ref
git stash pop                         # resolve conflicts if any
```
Automatic `pop` is refused on purpose: on conflict it writes conflict markers into a
tree you are not currently looking at.

**`UNPUSHED`** — GATED at the push:
```
git status                            # review what is actually there
git log @{upstream}..HEAD             # review what would be published
git push                              # requires confirmation: shared state
```

**`DIVERGENT_UNPUSHED` / true fork (`ahead>0 && behind>0`)** — do not resolve here.
Branch-role semantics (which tier may merge into which, when force-with-lease is
acceptable, the team sync window) belong to **`git-workflow`**. This skill's job ends
at "these two environments have forked; here is the evidence".

**`SUBMODULE_DRIFT`** — do not bump the gitlink here. Editing inside a submodule,
naming the branch after the parent, recording the bump in the ledger, and listing
affected consumers in the PR are all **`git-submodule-edit`**'s contract. Feed it the
consumer list from `deps` (see below).

**`STASH`** — never dropped, never popped automatically. Report and let the owner
decide; a forgotten stash is lost work, and `stash drop` is engine-refused.

## Dependency-ordered propagation

When a change must ripple across repos, use `deps` to order the work:

```bash
git_fleet.py ... deps            # prints dependency-first order
```

Upgrade in that order — a repo appears only after everything it depends on. Going the
other way means re-doing consumers each time a provider shifts.

Before changing a repo, read its **被依赖 / depended-on-by** table: that is the
concrete answer to "who breaks if I change this", and it is the data source for the
consumer list that `git-submodule-edit` requires in its PRs.

If `deps` reports a cycle, it refuses to emit an order rather than inventing one.
Break the cycle (usually a spurious manifest edge, or a genuine circular submodule)
before relying on propagation order.

## Delegation boundary, restated

| Operation | Owner |
|-----------|-------|
| Collect state across environments; decide *which* environment acts | **git-fleet** |
| Sequence remediation across environments | **git-fleet** |
| `fetch`, ff-pull, stash-protect, backup branch | **git-fleet** (SAFE set) |
| Branch roles, rebase sync, merges, force-with-lease, `.gitexcludes` | **git-workflow** |
| Anything inside a submodule; gitlink bumps; bump ledger | **git-submodule-edit** |
| Reviewing the diff itself | **code-review** |

Re-implementing any right-hand-column operation inside this skill creates a second
source of truth for the same git semantics. Delegate instead.
