#!/usr/bin/env python3
"""check-063-overlap.py — branch-aware guard for the 063 provisional CLI scope.

The 063 in-flight branch carries a provisional `contracts/cli-profiles.md`
and related assets that 064 owns authoritatively.  A worktree-local scan cannot
see that branch, so this guard inspects the branch tree itself:

  * branch absent              -> clean (nothing to reconcile)
  * branch present, not merged -> pending-merge-obligation (paths listed)
  * branch merged into HEAD    -> dual-owner: exit 3 until the provisional
                                  assets are deleted (or turned into pointers)

Use `--strict-premerge` in a 063 merge checklist to turn the pending list into
a hard failure before landing.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

LEGACY_SUFFIXES = (
    "063-sdd-loop-efficiency/contracts/cli-profiles.md",
    "test_cli_profile_record.py",
    "references/cli/README.md",
)
DEFAULT_BRANCH = "063-sdd-loop-efficiency"


def git(repo: Path, *args: str):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def tree_files(repo: Path, ref: str) -> list[str] | None:
    proc = git(repo, "ls-tree", "-r", "--name-only", ref)
    if proc.returncode != 0:
        return None
    return [line for line in proc.stdout.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="check-063-overlap.py")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--strict-premerge", action="store_true", default=False)
    args = parser.parse_args(argv)

    repo = Path(args.repo).expanduser().resolve()
    if git(repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{args.branch}").returncode != 0:
        print(json.dumps({"status": "branch-absent", "branch": args.branch}, sort_keys=True))
        return 0

    files = tree_files(repo, args.branch)
    if files is None:
        print(json.dumps({"status": "unreadable", "branch": args.branch}, sort_keys=True))
        return 6
    legacy = sorted({
        path for path in files
        if any(path.endswith(suffix) for suffix in LEGACY_SUFFIXES)
    })
    merged = git(repo, "merge-base", "--is-ancestor", args.branch, "HEAD").returncode == 0
    if merged and legacy:
        print(json.dumps({
            "status": "dual-owner",
            "branch": args.branch,
            "paths": legacy,
            "action": "delete the 063 provisional CLI-profile assets (or turn them into pointers) before landing",
        }, sort_keys=True))
        return 3
    if legacy:
        status = "pending-merge-obligation"
        code = 3 if args.strict_premerge else 0
        print(json.dumps({
            "status": status,
            "branch": args.branch,
            "paths": legacy,
            "action": "recorded merge-time deletion/pointer obligations (notes/063-overlap-adjudication.md)",
        }, sort_keys=True))
        return code
    print(json.dumps({"status": "clean", "branch": args.branch}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
