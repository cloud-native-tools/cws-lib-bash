#!/usr/bin/env python3
"""overlap-check.py — deterministic cross-feature overlap pre-check.

Runs at the driver's clarify U4. The current feature declares the repository
paths it intends to deliver in ``feature-ref.md`` (falling back to
``tasks.md``/``plan.md``); every other feature under the specs root is compared
by its **actual** delivery surface — the shared-root files changed by commits
that touched its spec directory — so cited inputs are never mistaken for
deliverables. Two features that claim the same path, or nested paths, will
collide during implementation. The check reports each overlap with its relation
(``same-path`` or ``nested-path``).

Only shared, repo-visible delivery roots are compared (skills/, .specify/shared/,
.specify/scripts/, .specify/templates/, src/, agents/, docs/); feature-internal artifacts under
the spec directory never count as overlaps. A missing specs root or a
spec directory with no declared paths is not an error.

Exit codes:
  0 = clear (no overlap)
  1 = overlap (adjudicate ownership before plan)
  2 = input or parse error

Standard library only, Python >= 3.8. Self-contained; never reads the
framework runtime scripts tree.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

SPEC_DIR = re.compile(r"^[0-9]{3}-")
DECLARATION_FILES = ("feature-ref.md",)
FALLBACK_DECLARATION_FILES = ("tasks.md", "plan.md")
BACKTICK = re.compile(r"`([^`\n]+)`")
PATH_TOKEN = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)+/?$")
LINE_PATH = re.compile(r"^\s*([A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)+)")
PATH_ROOTS = (
    "skills/", ".specify/shared/", ".specify/scripts/", ".specify/templates/",
    "src/", "agents/", "docs/",
)


class InputError(Exception):
    pass


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise InputError("cannot read %s: %s" % (path, exc))


def _collect(text, spec_rel, declared):
    for line in text.splitlines():
        candidates = [match.group(1).strip() for match in BACKTICK.finditer(line)]
        leading = LINE_PATH.match(line)
        if leading:
            candidates.append(leading.group(1).strip())
        for token in candidates:
            if not PATH_TOKEN.match(token):
                continue
            if not token.startswith(PATH_ROOTS):
                continue
            if spec_rel and (token == spec_rel or token.startswith(spec_rel + "/")):
                continue
            # A bare directory token (`skills/external`) names a whole area, not
            # a deliverable; keep explicit directory claims ending with `/`.
            if not token.endswith("/") and not os.path.splitext(token)[1]:
                continue
            declared.add(token.rstrip("/"))


def declared_paths(spec_dir, spec_rel):
    declared = set()
    used = False
    for name in DECLARATION_FILES:
        path = os.path.join(spec_dir, name)
        if os.path.isfile(path):
            _collect(read_file(path), spec_rel, declared)
            used = True
    if not declared:
        for name in FALLBACK_DECLARATION_FILES:
            path = os.path.join(spec_dir, name)
            if os.path.isfile(path):
                _collect(read_file(path), spec_rel, declared)
                used = True
    return sorted(declared), used


def delivered_paths(spec_dir, spec_rel, repo):
    """A finished feature's true delivery surface: shared-root files changed by
    commits whose message names the spec (the repo's commit convention), then
    by commits that touched the spec directory. Falls back to the declared
    list when git has no history for the spec (in-flight feature or fixture)."""
    if repo:
        delivered = set()
        name = os.path.basename(spec_dir.rstrip(os.sep))
        for selector in (["--grep", name], ["--", spec_rel or spec_dir]):
            completed = subprocess.run(
                ["git", "-C", repo, "log", "--format=", "--name-only"] + selector,
                capture_output=True, text=True)
            if completed.returncode != 0:
                continue
            for line in completed.stdout.splitlines():
                token = line.strip()
                if token.startswith(PATH_ROOTS):
                    delivered.add(token)
            if delivered:
                break
        if delivered:
            return sorted(delivered)
    return declared_paths(spec_dir, spec_rel)[0]


def relation(left, right):
    if left == right:
        return "same-path"
    if left.startswith(right + "/") or right.startswith(left + "/"):
        return "nested-path"
    return ""


def spec_directories(specs_root, current):
    entries = []
    for name in sorted(os.listdir(specs_root)):
        path = os.path.join(specs_root, name)
        if not os.path.isdir(path) or not SPEC_DIR.match(name):
            continue
        entries.append((name, path))
    if not any(os.path.samefile(path, current) for _, path in entries):
        entries.append((os.path.basename(current.rstrip(os.sep)), current))
    return entries


def run(args):
    current = os.path.abspath(args.spec_dir)
    if not os.path.isdir(current):
        raise InputError("spec dir not found: %s" % current)
    specs_root = os.path.abspath(args.specs_root or os.path.dirname(current))
    if not os.path.isdir(specs_root):
        raise InputError("specs root not found: %s" % specs_root)
    repo = os.path.abspath(args.repo) if args.repo else ""
    current_rel = ""
    if repo:
        current_rel = os.path.relpath(current, repo).replace(os.sep, "/")

    current_paths, used = declared_paths(current, current_rel)
    if not current_paths:
        note = ("current feature declares no shared delivery paths"
                if used else "current feature has no declaration artifact")
        return {
            "decision": "clear",
            "current_spec": os.path.basename(current),
            "checked_specs": [os.path.basename(current)],
            "overlaps": [],
            "note": note,
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

    overlaps = []
    checked = []
    for name, path in spec_directories(specs_root, current):
        if os.path.samefile(path, current):
            continue
        checked.append(name)
        other_rel = ""
        if repo:
            other_rel = os.path.relpath(path, repo).replace(os.sep, "/")
        other_paths = delivered_paths(path, other_rel, repo)
        for left in current_paths:
            for right in other_paths:
                rel = relation(left, right)
                if rel:
                    overlaps.append({
                        "other_spec": name,
                        "relation": rel,
                        "current_path": left,
                        "other_path": right,
                    })

    return {
        "decision": "overlap" if overlaps else "clear",
        "current_spec": os.path.basename(current),
        "checked_specs": [os.path.basename(current)] + checked,
        "current_paths": current_paths,
        "overlaps": overlaps,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Deterministic cross-feature delivery overlap pre-check.")
    parser.add_argument("--spec-dir", required=True)
    parser.add_argument("--specs-root", default="",
                        help="directory holding sibling spec dirs (default: parent)")
    parser.add_argument("--repo", default="",
                        help="repo root used to relativize spec dirs")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args(argv)

    try:
        record = run(args)
    except InputError as exc:
        print("overlap-check: input error: %s" % exc, file=sys.stderr)
        return 2

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    print(json.dumps(record, ensure_ascii=False))
    print("overlap-check: current=%s checked=%d overlaps=%d decision=%s"
          % (record["current_spec"], len(record["checked_specs"]),
             len(record["overlaps"]), record["decision"]), file=sys.stderr)
    return 1 if record["decision"] == "overlap" else 0


if __name__ == "__main__":
    sys.exit(main())
