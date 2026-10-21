# Merge Provenance — git-utils

Capability-inheritance record for the four skills merged into this one on 2026-10-09
(merge B2d). Committed, not scratch: it is the standing evidence that this skill still
covers what its sources could do.

> **2026-10-15 rename**: this skill was renamed `git-workspace` → `git-utils` when the
> code-hosting-platform scope (GitHub/Gitee/Aone Code) split out into a separate local
> skill. The four frozen baselines under `references/merge-provenance/` record the
> 2026-10-09 merge event verbatim and intentionally retain their pre-rename unit-id
> strings — they are historical snapshots, not live references.

Re-verify with:

```bash
python3 .specify/skills/merge-skills/scripts/provenance_check.py skills/external/git-utils
```

The method and flow below are this skill's own; only the **responsibility** is inherited.
A row marked `verified` means the destination exists and the capability was walked through;
the Verification column names how to check it again.

## Source: git-workflow

- **Merged**: 2026-10-09
- **Source identity**: `git-workflow` · `<SKILL:.specify/skills/git-workflow/SKILL.md>` · class: peer (host-managed)
- **Retirement registered**: `_OBSOLETE_SKILLS` in `src/specify_cli/__init__.py`
- **Baseline**: `./merge-provenance/git-workflow.baseline.txt`

### Capability inheritance

| # | Capability (what the source could do) | Target destination | Verification | Status |
|---|---------------------------------------|--------------------|--------------|--------|
| 1 | Bootstrap a three-tier MAIN/PRE/DEV branch structure in a repo | `references/bootstrap-commands.md` | walk migration → branch detect/create → `.gitexcludes` init | verified |
| 2 | Health-check branch structure, sync state, and exclusion rules | `references/health-check-commands.md` | walk the Phase-2 checks against a repo holding a managed block | verified |
| 3 | Directed convergence: rebase sync, selective merge, force-with-lease push | `references/execute-commands.md` | walk operations A–G; confirm the pre/post subroutine markers | verified |
| 4 | Per-branch file exclusion via `.gitexcludes` | `references/gitexcludes-subroutine.md` | confirm every sync/merge command routes through the subroutine | verified |
| 5 | Single-source branch state in the managed block of `docs/git-workflow.md` | `references/instructions-lookup.md` | locate/create rules present; block machine-written, never hand-edited | verified |
| 6 | Diagnose known branch-workflow failures | `references/troubleshooting.md` | each source Known-Issue row present with its remedy | verified |

## Source: git-fleet

- **Merged**: 2026-10-09
- **Source identity**: `git-fleet` · `<SKILL:.specify/skills/git-fleet/SKILL.md>` · class: peer (host-managed)
- **Retirement registered**: `_OBSOLETE_SKILLS` in `src/specify_cli/__init__.py`
- **Baseline**: `./merge-provenance/git-fleet.baseline.txt`

### Capability inheritance

| # | Capability (what the source could do) | Target destination | Verification | Status |
|---|---------------------------------------|--------------------|--------------|--------|
| 1 | Collect a read-only normalized state record per (repo, environment) | `references/fleet-inventory-schema.md` | `python3 .specify/scripts/git_fleet.py scan --help` | verified |
| 2 | Raise graded cross-environment hazard verdicts | `references/fleet-hazard-taxonomy.md` | `python3 .specify/scripts/git_fleet.py report --help` | verified |
| 3 | Model the inter-repo dependency graph and order work dependency-first | `references/fleet-dependency-model.md` | `python3 .specify/scripts/git_fleet.py deps --help` | verified |
| 4 | Plan and execute cross-environment convergence, SAFE steps only unless applied | `references/fleet-coordination-playbook.md` | `python3 .specify/scripts/git_fleet.py plan --help` then `sync --help` (dry-run default) | verified |
| 5 | Run the fleet reconcile loop end-to-end (observe → diff → converge → verify) | `references/fleet-workflow.md` | walk the loop on a two-environment inventory | verified |

## Source: git-submodule-edit

- **Merged**: 2026-10-09
- **Source identity**: `git-submodule-edit` · `<SKILL:.specify/skills/git-submodule-edit/SKILL.md>` · class: peer (host-managed)
- **Retirement registered**: `_OBSOLETE_SKILLS` in `src/specify_cli/__init__.py`
- **Baseline**: `./merge-provenance/git-submodule-edit.baseline.txt`

### Capability inheritance

| # | Capability (what the source could do) | Target destination | Verification | Status |
|---|---------------------------------------|--------------------|--------------|--------|
| 1 | Edit submodule code on a branch named after the parent project | `references/submodule-workflow.md` | walk the `project-<PARENT_SLUG>/*` rule and the detached-HEAD guard | verified |
| 2 | Run the submodule edit/commit command set from the parent | `references/submodule-command-recipes.md` | each source recipe present and parent-relative | verified |
| 3 | Record every validated gitlink bump in an auditable ledger | `.specify/scripts/record-bump.sh` | usage header + `assets/ledger-template.md`; `--status pass\|fail` annotation | verified |

## Source: git-server-init

- **Merged**: 2026-10-09
- **Source identity**: `git-server-init` · `<SKILL:.specify/skills/git-server-init/SKILL.md>` · class: peer (host-managed)
- **Retirement registered**: `_OBSOLETE_SKILLS` in `src/specify_cli/__init__.py`
- **Baseline**: `./merge-provenance/git-server-init.baseline.txt`

### Capability inheritance

| # | Capability (what the source could do) | Target destination | Verification | Status |
|---|---------------------------------------|--------------------|--------------|--------|
| 1 | Provision a plain SSH server into a git server (desired state D1–D4) | `references/server-workflow.md` | `bash .specify/scripts/provision-git-server.sh --help`; walk D1–D4 convergence | verified |
| 2 | Create bare repos under the git home with the expected owner and HEAD | `references/server-workflow.md` | `--repo <namespace/name>` repeatable flag documented | verified |
| 3 | Authorize local public keys, deduped by fingerprint, StrictModes-safe | `references/server-workflow.md` | `--pubkey <path>` repeatable flag documented | verified |
| 4 | Add the matching Host entry to the local ssh config | `references/server-ssh-config-entry.md` | `python3 .specify/scripts/ssh_config_insert.py --help` | verified |
| 5 | Diagnose server-side provisioning failures | `references/server-troubleshooting.md` | each source troubleshooting row present | verified |
| 6 | Stay environment-agnostic (no hardcoded hostnames or absolute paths) | `references/server-reference-architecture.md` | grep for literal hostnames/paths — expect none | verified |
