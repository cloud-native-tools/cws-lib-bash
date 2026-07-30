# git-submodule-edit — Command Recipes

Exact command sequences for the workflow in `SKILL.md`. Run from the parent repo root unless noted. `<path>` is the submodule path (e.g. `libs/foo`).

## 0. Compute names

```bash
PARENT_SLUG="$(basename "$(git rev-parse --show-toplevel)")"
TOPIC="${TOPIC:-$(git rev-parse --abbrev-ref HEAD | tr '/' '-')}"   # short change slug; default = parent's current branch
BRANCH="project-${PARENT_SLUG}/${TOPIC}"   # convention: project-<项目名>/*  (always includes a topic segment)
```

## 1. Enter edit mode

```bash
# Confirm it is a submodule and initialized
grep -q "path = <path>" .gitmodules || echo "NOT a submodule"
git submodule update --init <path>

# Create/checkout the project-<PARENT_SLUG>/<topic> branch off the CURRENT gitlink commit
if git -C <path> show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git -C <path> checkout "${BRANCH}"
else
  git -C <path> checkout -b "${BRANCH}"     # branches from the exact commit the parent references
fi

# Verify NOT detached
git -C <path> symbolic-ref --short HEAD      # must print ${BRANCH}
```

## 2. Edit & commit inside the submodule

```bash
# ...make edits under <path>...
git -C <path> add -A
git -C <path> commit -m "[${PARENT_SLUG}] <what changed and why>"
```

## 3. Bump the parent gitlink & record

```bash
git add <path>                               # stages the new submodule SHA in the parent
scripts/record-bump.sh <path>                # or ${SKILL_HOME}/scripts/record-bump.sh <path>
git commit -m "chore(submodule): bump <path> to $(git -C <path> rev-parse --short HEAD) (validating <topic>)"
```

## 4. Validate & mark status

```bash
# run parent build/tests/app, then:
scripts/record-bump.sh --status pass <path>   # or: fail
```

## 5. Hand off upstream

```bash
git -C <path> push -u origin "${BRANCH}"
# open PR/MR in the submodule repo from ${BRANCH} (a project-<项目名>/* branch).
# The PR MUST list affected consumers + migration steps; link the validating parent commit(s) from the ledger.
```

## Ledger row schema

`${SKILL_WORKDIR}/submodule-edits.md` is a Markdown table. One row per pointer bump:

| Column | Meaning |
|--------|---------|
| Date | ISO date of the bump |
| Submodule | submodule path (`<path>`) |
| Branch | submodule branch (`project-<PARENT_SLUG>/<topic>`) |
| Old SHA | previous gitlink short SHA |
| New SHA | new gitlink short SHA |
| Parent Commit | parent short SHA/branch that recorded & validated this bump |
| Validation | `pending` / `pass` / `fail` |
| Notes | topic, PR link, or reason |

Manual row (when scripts are unavailable):

```markdown
| 2026-07-02 | libs/foo | project-myapp/fix-null-deref | a1b2c3d | e4f5a6b | myapp@9c0d1e2 | pending | fix null deref |
```

## Troubleshooting

- **Detached HEAD after editing** — you committed on detached HEAD. Recover: `git -C <path> branch project-<PARENT_SLUG>/<topic> <the-commit-sha>` then `git -C <path> checkout project-<PARENT_SLUG>/<topic>`. Find the sha via `git -C <path> reflog`.
- **Branched off the wrong base** — you branched off upstream tip, not the gitlink. Rebase onto the recorded commit: read the gitlink with `git ls-tree HEAD <path>` (the SHA in the parent), then `git -C <path> rebase --onto <gitlink-sha> <upstream-base> project-<PARENT_SLUG>/<topic>`.
- **Parent shows submodule "modified" but nothing to commit** — the submodule HEAD differs from the gitlink. Either bump (`git add <path>`) if intended, or `git submodule update <path>` to discard.
- **Parent commit didn't capture submodule file changes** — expected: the parent only ever stores the submodule SHA (the gitlink), never the submodule's file diffs. The diffs live in the submodule's own history on `project-<PARENT_SLUG>/<topic>`.
