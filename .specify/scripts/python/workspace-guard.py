#!/usr/bin/env python3
"""workspace-guard.py — snapshot and compare a workspace's git refs and spec dirs.

Why this exists: a probe or a subagent that resolves its repository root by walking up
can write branches or `.specify/specs/` entries into the MEASURED repository instead of
its own sandbox. That happened on 2026-11-07 (40 branches and spec dirs). A stage that
runs probes owes a before/after comparison of this signature; this engine is that check.

Usage:
  python3 workspace-guard.py --snapshot FILE [--repo PATH] [--json]
  python3 workspace-guard.py --check FILE [--repo PATH] [--json]

Exit codes:
  0  the snapshot was recorded, or the workspace matches it
  1  the workspace drifted (branch, refs or spec dirs differ)
  2  input error (bad path, unreadable snapshot, neither/both actions)

Read-only: --snapshot writes only the FILE it is given; --check writes nothing.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from script_interface_cli import (  # noqa: E402
    add_version_argument,
    configure_parser,
    console_script_name,
)


def _git(repo: Path, *args: str) -> str:
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                              text=True, timeout=30, stdin=subprocess.DEVNULL)
        return proc.stdout if proc.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def signature(repo: Path) -> dict:
    specs = repo / ".specify" / "specs"
    return {
        "branch": _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip(),
        "refs": sorted(line for line in _git(repo, "for-each-ref", "--format=%(refname)").splitlines() if line),
        "specs": sorted(item.name for item in specs.iterdir()) if specs.is_dir() else [],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=console_script_name(),
        description="Snapshot or compare a workspace's git refs and .specify/specs listing.",
    )
    configure_parser(
        parser,
        effects="snapshot writes only the FILE it is given; check writes nothing",
        codes="0 recorded or matched; 1 drift; 2 input error",
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--snapshot", metavar="FILE", help="record the current signature")
    action.add_argument("--check", metavar="FILE", help="compare the workspace with FILE")
    parser.add_argument("--repo", default=".", metavar="PATH",
                        help="workspace root (default: the current directory)")
    parser.add_argument("--json", action="store_true", help="machine-readable verdict")
    add_version_argument(parser)
    return parser


def main(argv: Optional[list] = None) -> int:
    from script_interface_cli import guard_argv
    guard_argv(argv, declared=("--snapshot", "--check", "--repo", "--json",
                               "--version", "-h", "--help"))
    args = build_parser().parse_args(argv)
    repo = Path(args.repo).resolve()
    if not repo.is_dir():
        print("workspace-guard: not a directory: %s" % repo, file=sys.stderr)
        return 2
    current = signature(repo)
    if args.snapshot:
        target = Path(args.snapshot)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if args.json:
            print(json.dumps({"status": "recorded", "path": str(target), "signature": current}))
        else:
            print("recorded %s" % target)
        return 0
    try:
        stored = json.loads(Path(args.check).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print("workspace-guard: cannot read snapshot %s: %s" % (args.check, exc), file=sys.stderr)
        return 2
    changed = sorted(key for key in ("branch", "refs", "specs") if stored.get(key) != current.get(key))
    if args.json:
        print(json.dumps({"status": "drift" if changed else "clean",
                          "changed": changed, "current": current, "stored": stored}))
    elif changed:
        print("DRIFT: %s" % ", ".join(changed))
        for key in changed:
            print("  %s before=%r now=%r" % (key, stored.get(key), current.get(key)))
    else:
        print("clean")
    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
