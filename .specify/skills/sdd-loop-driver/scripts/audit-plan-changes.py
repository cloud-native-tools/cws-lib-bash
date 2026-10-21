#!/usr/bin/env python3
"""Mechanically audit plan-owned changes after the plan stage.

Reports the touched plan-owned paths (committed range + uncommitted changes),
the ``PLAN-EDIT:`` declaration lines, the undeclared verdict and the final
cumulative diff stats. Semantic minor/substantive classification stays with the
driver; this script is read-only and never modifies the worktree.

Exit codes: 0 no undeclared touch, 1 undeclared touch, 2 input or parse error.

Python >= 3.8, standard library only.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_UNDECLARED = 1
EXIT_INPUT = 2

DECLARATION_TOKEN = "PLAN-EDIT:"


class InputError(Exception):
    pass


def git(repo, *args):
    completed = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True)
    if completed.returncode != 0:
        raise InputError("git %s failed: %s" % (
            " ".join(args), completed.stderr.strip()))
    return completed.stdout


def verify_ref(repo, ref):
    try:
        return git(repo, "rev-parse", "--verify", "%s^{commit}" % ref).strip()
    except InputError:
        raise InputError("unknown git ref: %s" % ref)


def parse_status_path(line):
    if len(line) < 4:
        return ""
    path = line[3:]
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return path.strip().strip('"')


def pathspecs(owned):
    specs = []
    for name in owned:
        name = name.rstrip("/")
        if "/" in name:
            specs.append(name)
        else:
            specs.append(":(glob)**/%s" % name)
            specs.append(":(glob)**/%s/**" % name)
    return specs


def committed_paths(repo, base, head, specs):
    output = git(repo, "diff", "--name-only", "%s..%s" % (base, head), "--", *specs)
    return [line.strip() for line in output.splitlines() if line.strip()]


def uncommitted_paths(repo, specs):
    output = git(repo, "status", "--porcelain", "--", *specs)
    return [parse_status_path(line) for line in output.splitlines()
            if line.strip() and parse_status_path(line)]


def diff_stats(repo, base, specs):
    output = git(repo, "diff", "--numstat", base, "--", *specs)
    stats = []
    for line in output.splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        added = int(parts[0]) if parts[0].isdigit() else 0
        deleted = int(parts[1]) if parts[1].isdigit() else 0
        stats.append({"path": parts[2], "added": added, "deleted": deleted})
    return sorted(stats, key=lambda item: item["path"])


def declaration_lines(path):
    if not Path(path).exists():
        raise InputError("declarations file not found: %s" % path)
    lines = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if DECLARATION_TOKEN in line:
            lines.append(line.strip())
    return lines


def covered(path, declarations):
    basename = path.rsplit("/", 1)[-1]
    for line in declarations:
        if path in line or basename in line:
            return True
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Report plan-owned touches, PLAN-EDIT declarations and the "
                    "final cumulative diff for the driver's U4 classification.")
    parser.add_argument("--repo", required=True, help="repository root")
    parser.add_argument("--base", required=True, help="stage base commit")
    parser.add_argument("--head", required=True, help="stage head commit")
    parser.add_argument("--plan-owned", action="append", required=True,
                        help="plan-owned path (repeatable)")
    parser.add_argument("--declarations", required=True,
                        help="file carrying the stage's PLAN-EDIT: lines")
    args = parser.parse_args(argv)

    try:
        base = verify_ref(args.repo, args.base)
        head = verify_ref(args.repo, args.head)
        specs = pathspecs(args.plan_owned)
        touched = committed_paths(args.repo, base, head, specs)
        pending = uncommitted_paths(args.repo, specs)
        for path in pending:
            if path not in touched:
                touched.append(path)
        touched = sorted(touched)
        declarations = declaration_lines(args.declarations)
        stats = diff_stats(args.repo, base, specs)
    except InputError as error:
        print("ERROR: %s" % error, file=sys.stderr)
        return EXIT_INPUT

    undeclared_paths = [path for path in touched
                        if not covered(path, declarations)]
    if not touched:
        classification = "none"
    elif undeclared_paths:
        classification = "undeclared"
    else:
        classification = "declared"

    payload = {
        "base": base,
        "head": head,
        "plan_owned": args.plan_owned,
        "touched_paths": touched,
        "uncommitted_paths": sorted(pending),
        "declaration_lines": declarations,
        "undeclared": bool(undeclared_paths),
        "undeclared_paths": undeclared_paths,
        "classification": classification,
        "diff_stats": stats,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return EXIT_UNDECLARED if undeclared_paths else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
