---
name: git-submodule-edit
description: |
  Edit and commit code inside a git submodule from within the parent (referencing) project under disciplined, traceable rules. Enforces two rules: (1) every submodule edit happens on a branch named after the parent project so the submodule owner can trace and merge the change upstream; (2) each submodule-pointer (gitlink) bump validated in the parent is recorded in a ledger for auditability. Use this when the user mentions ["edit submodule", "commit submodule", "submodule branch", "submodule change", "modify submodule code", "submodule pointer", "gitlink bump", "编辑submodule", "提交submodule", "修改子模块", "子模块修改", "子模块分支", "子模块提交"]
skill_id: "<SKILL:.specify/skills/git-submodule-edit/SKILL.md>"
---

# git-submodule-edit

## Overview

A git submodule is normally treated as read-only inside its parent (referencing) project — you consume its code, you don't edit it in place. Occasionally you must: fix a bug in the submodule while validating it against the parent, or prototype an upstream change. Doing this ad-hoc creates two problems: (a) submodule commits land on a detached HEAD and get lost, and (b) the parent's gitlink drifts silently with no record of which parent state validated which submodule commit.

This skill imposes two rules that solve both:

1. **Project-named branch** — every submodule edit happens on a `project-<PARENT_SLUG>/<topic>` branch in the submodule (convention `project-<项目名>/*`). The submodule repo owner can then see exactly which referencing project a change flows back from and merge it upstream cleanly.
2. **Recorded pointer bumps** — because validating a submodule change requires repeatedly bumping the parent's gitlink, every bump is appended to a ledger (`${SKILL_WORKDIR}/submodule-edits.md`) capturing old→new SHA, submodule branch, the parent branch/commit that validated it, and validation status.

## When to Use / Not Use

**Use when**: you need to change code *inside* a submodule and verify it against the parent before handing the change to the submodule's owner.

**Do NOT use when**: you only need to advance the submodule to an existing upstream commit (`git submodule update --remote` is enough), or the submodule is vendored read-only and changes must go directly to its own repo checkout outside the parent.

## Key Concepts & Conventions

- **PARENT_SLUG** — basename of the parent repo toplevel: `basename "$(git rev-parse --show-toplevel)"` run from the parent.
- **Submodule branch name** — always a `project-<PARENT_SLUG>/*` branch: `project-<PARENT_SLUG>/<topic>`, where `<topic>` is a short slug of the change (default: the parent's current branch name, sanitized). Never edit a submodule on `main`/`master` or on detached HEAD.
- **Gitlink** — the parent's recorded submodule commit SHA (stored in the parent tree, shown by `git submodule status`). "Bumping the pointer" = staging the submodule path in the parent so the parent records the new submodule SHA.
- **Ledger** — `${SKILL_WORKDIR}/submodule-edits.md` in the parent project. One row per pointer bump. Created from `${SKILL_HOME}/assets/ledger-template.md` on first use.

### Branch Naming Convention

| Pattern | Purpose | PR requirement |
|---------|---------|----------------|
| `project-<项目名>/*` | 引用项目 via submodule 回传 | 须在 PR 中列明受影响消费者与迁移步骤 |

`<项目名>` is `PARENT_SLUG` (the parent repo basename); `*` is the change topic. In English: submodule contributions flow back from the referencing project on a `project-<PARENT_SLUG>/<topic>` branch, and the upstream PR **MUST list the affected consumers and the migration steps** so the submodule owner can assess downstream impact before merging.

## Workflow

Run all git commands from the parent repo root (`${SKILL_WORKDIR}`) unless a step says `cd <submodule>`. Detailed copy-paste command recipes live in `${SKILL_HOME}/references/command-recipes.md` — read it when you need exact commands.

### Phase 1 — Enter edit mode (create the `project-<PARENT_SLUG>/<topic>` branch)

1. Confirm the target is a real submodule: it appears in `.gitmodules` and `git submodule status <path>` succeeds.
2. Ensure the submodule is initialized/updated (`git submodule update --init <path>`).
3. Compute `PARENT_SLUG` and choose a `<topic>` slug for this change; the branch is `project-<PARENT_SLUG>/<topic>`.
4. In the submodule, create or check out the `project-<PARENT_SLUG>/<topic>` branch **off the current gitlink commit** (not off an arbitrary upstream tip), so you edit exactly what the parent references:
   - If the branch exists: `git -C <path> checkout project-<PARENT_SLUG>/<topic>`
   - Else: `git -C <path> checkout -b project-<PARENT_SLUG>/<topic>`
5. Verify the submodule is no longer detached: `git -C <path> symbolic-ref --short HEAD` prints the branch.

### Phase 2 — Edit & commit inside the submodule

1. Make the code changes inside the submodule directory.
2. Commit **in the submodule** on the `project-<PARENT_SLUG>/<topic>` branch, with a message that names the parent project so upstream reviewers have context: `[<PARENT_SLUG>] <what changed and why>`.
3. Do NOT push yet if you still need to validate; you may commit multiple times during iteration.

### Phase 3 — Bump the parent gitlink & record it

1. Back in the parent, stage the submodule path to record the new SHA: `git add <path>`.
2. Append a ledger entry. Prefer the helper (deterministic):
   ```bash
   ${SKILL_HOME}/scripts/record-bump.sh <path>
   ```
   It reads old/new SHAs and the submodule branch, then appends a row to `${SKILL_WORKDIR}/submodule-edits.md` (creating it from the template on first run). If you cannot run scripts, append the row by hand per the schema in `${SKILL_HOME}/references/command-recipes.md`.
3. Commit the parent pointer bump: `git commit -m "chore(submodule): bump <path> to <short-sha> (validating <topic>)"`. Committing the ledger together with the gitlink keeps them in lockstep.

### Phase 4 — Validate in the parent

1. Run the parent project's validation (build/tests/app) against the new pointer.
2. Update the ledger row's **Validation** column to `pass`/`fail` (re-run `record-bump.sh --status pass <path>` or edit the row).
3. On failure, iterate Phase 2→3 (new submodule commit → new bump → new ledger row). Each iteration is its own row; the trail shows the convergence.

### Phase 5 — Hand off upstream

1. Push the submodule's `project-<PARENT_SLUG>/<topic>` branch to the submodule's own remote: `git -C <path> push -u origin project-<PARENT_SLUG>/<topic>`.
2. Open a PR/MR in the submodule repo from `project-<PARENT_SLUG>/<topic>`; the `project-<name>/*` branch name tells the owner which referencing project the change flows back from. The PR **MUST list the affected consumers and the migration steps** (which downstream projects/APIs this change touches and how they must adapt). Link the validating parent commit(s) from the ledger.
3. Once upstream merges and tags/releases, bump the parent pointer to the merged upstream SHA and add a final ledger row marking the edit **landed** (so the parent no longer tracks a private branch commit).

## Safety Rules

- Never leave a submodule on detached HEAD after editing — commits there are unreferenced and easily lost.
- Never `git commit -m` the parent with an unstaged submodule change expecting it to include submodule edits; the parent only records the gitlink SHA, never the submodule's file diffs.
- Never force-push the `project-<PARENT_SLUG>/<topic>` branch over shared history without `--force-with-lease`.
- Keep one submodule concern per branch/topic so upstream can cherry-pick cleanly.
- The ledger is the source of truth for "which parent commit validated which submodule SHA" — always bump the pointer and record in the same parent commit.

## Resource ID
- Canonical ID: `<SKILL:.specify/skills/git-submodule-edit/SKILL.md>`
- Canonical Path: `.specify/skills/git-submodule-edit/SKILL.md`

## Path Conventions

This Skill follows the canonical path conventions defined in `templates/commands/skills.md` (`## Path Conventions`):

- Use `${SKILL_HOME}/<relative-path>` for every Skill-owned resource (scripts, references, assets).
- Use `${SKILL_WORKDIR}/<relative-path>` for runtime/user-facing paths — here, the parent project's ledger at `${SKILL_WORKDIR}/submodule-edits.md`.
- Never conflate the two; never embed agent-specific install paths.

For shell scripts under `${SKILL_HOME}/scripts/`, the FR-016 idiom is copied verbatim at the top of each script:

```bash
SKILL_HOME="${SKILL_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd -P)}"
SKILL_WORKDIR="${SKILL_WORKDIR:-$(pwd -P)}"
```

## Resources

### Scripts (`${SKILL_HOME}/scripts/`)
- `record-bump.sh` — read old/new submodule SHAs + branch and append a ledger row to `${SKILL_WORKDIR}/submodule-edits.md` (creates it from the template on first run). Supports `--status <pass|fail>` to update the latest row.

### References (`${SKILL_HOME}/references/`)
- `command-recipes.md` — exact copy-paste git command sequences for every phase, the ledger row schema, and troubleshooting (detached HEAD recovery, wrong-base branch, pointer drift).

### Assets (`${SKILL_HOME}/assets/`)
- `ledger-template.md` — the `submodule-edits.md` ledger scaffold (header + column schema) copied into the parent project on first use.

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At the end of a substantial run of this skill, perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this run reached a meaningful wrap-up. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against this skill's declared purpose and produce a short review plus ≥1 concrete, skill-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this skill's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id`; if a parent flow already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "skill:git-submodule-edit" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
