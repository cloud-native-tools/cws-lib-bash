#!/usr/bin/env python3
"""Scan shipped framework surfaces for unsanctioned temporary-directory usage.

Contract: ``.specify/shared/guidelines/temp-directory-discipline.md``.

The scanner is a documentation/shell guard, not a Python static analyzer: it
checks shipped ``.md`` / ``.sh`` / ``.bash`` surfaces for bare ``/tmp`` paths,
``${TMPDIR:-/tmp}`` fallbacks, ``mktemp -d`` and ``/var/tmp``. Python
``mkdtemp`` / ``TemporaryDirectory`` calls are governed by the owner document's
exception clauses, not by this scanner.

Usage:
  python3 .specify/scripts/python/scan-temp-usage.py [--root <repo-root>]
      [--json | --summary]

Exit codes: 0 = clean; 1 = argument/environment error; 2 = violations found.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from pathlib import Path

# Guard mirrored invocation: running the .specify/scripts/python copy must
# resolve the repo root, not .specify itself.
_HERE = Path(__file__).resolve()
REPO_ROOT = _HERE.parents[2]
if REPO_ROOT.name == ".specify":
    REPO_ROOT = REPO_ROOT.parent

SCAN_DIRS = ("shared", "templates", "skills", "agents", "scripts")
SCAN_SUFFIXES = {".md", ".sh", ".bash"}
SKIP_DIR_PARTS = {
    ".specify", ".claude", ".qoder", ".github", ".opencode",
    "__pycache__", ".archive", "node_modules", "site",
}
SELF_REL = Path(".specify/shared/guidelines/temp-directory-discipline.md")

# Every allowlist row carries a reason. The owner document quotes forbidden
# forms prescriptively; the other rows are third-party tooling whose temp paths
# are not agent-created scratch.
ALLOWLIST = {
    ".specify/shared/guidelines/temp-directory-discipline.md":
        "owner document quotes forbidden forms",
    ".specify/skills/document-utils/*":
        "third-party Office tooling manages its own OS temp",
    ".specify/skills/draw-diagram/references/types/plantuml/*":
        "jar discovery path, not agent-created scratch",
}

SANCTIONED_FORMS = (
    re.compile(r"~/tmp(?:/|\b|$)"),
    re.compile(r"\$HOME/tmp(?:/|\b|$)"),
    re.compile(r"\$\{HOME\}/tmp(?:/|\b|$)"),
    re.compile(r"\.specify/\.tmp(?:/|\b|$)"),
)
BARE_TMP_RE = re.compile(r"(?<!~)/tmp\b")
VAR_TMP_RE = re.compile(r"/var/tmp\b")
TMPDIR_FALLBACK_RE = re.compile(r"\$\{TMPDIR:-?/tmp\}|\$\{TMPDIR:-?\s*/tmp\}")
MKTEMP_D_RE = re.compile(r"\bmktemp\s+-d\b")


def sanitize(line: str):
    """Replace sanctioned temp roots so they cannot trip the bare-temp checks."""
    had_sanctioned = False
    for pattern in SANCTIONED_FORMS:
        if pattern.search(line):
            had_sanctioned = True
            line = pattern.sub("SANCTIONED", line)
    return line, had_sanctioned


def classify(line: str):
    sanitized, had_sanctioned = sanitize(line)
    reasons = []
    if BARE_TMP_RE.search(sanitized):
        reasons.append("bare-system-temp")
    if VAR_TMP_RE.search(sanitized):
        reasons.append("var-tmp")
    if TMPDIR_FALLBACK_RE.search(line):
        reasons.append("tmpdir-fallback")
    if MKTEMP_D_RE.search(sanitized) and not had_sanctioned:
        reasons.append("mktemp-d")
    return reasons


def allowlist_reason(rel: Path):
    rel_str = rel.as_posix()
    for pattern, reason in ALLOWLIST.items():
        if fnmatch.fnmatch(rel_str, pattern):
            return reason
    return None


def iter_source_files(root: Path):
    for directory in SCAN_DIRS:
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
                continue
            rel = path.relative_to(root)
            if any(part in SKIP_DIR_PARTS for part in rel.parts):
                continue
            yield path, rel


def scan(root: Path):
    violations = []
    allowlisted = []
    scanned = 0
    for path, rel in iter_source_files(root):
        if rel == SELF_REL:
            continue
        reason = allowlist_reason(rel)
        if reason:
            allowlisted.append({"path": rel.as_posix(), "reason": reason})
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        scanned += 1
        for lineno, line in enumerate(text.splitlines(), 1):
            reasons = classify(line)
            if reasons:
                violations.append({
                    "path": rel.as_posix(),
                    "line": lineno,
                    "text": line.strip()[:160],
                    "reasons": reasons,
                })
    return {
        "scanned_files": scanned,
        "violations": violations,
        "allowlisted": allowlisted,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Scan shipped surfaces for unsanctioned temporary directories."
    )
    parser.add_argument("--root", default=str(REPO_ROOT),
                        help="repository root to scan (default: the enclosing repo)")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--summary", action="store_true", help="emit counts only")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 1

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: root is not a directory: {root}", file=sys.stderr)
        return 1

    result = scan(root)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.summary:
        print(f"temp-directory violations: {len(result['violations'])}")
        print(f"scanned files: {result['scanned_files']}")
        print(f"allowlisted: {len(result['allowlisted'])}")
    else:
        for violation in result["violations"]:
            reasons = ", ".join(violation["reasons"])
            print(f"{violation['path']}:{violation['line']}: {reasons}: "
                  f"{violation['text']}")
        print(f"temp-directory violations: {len(result['violations'])}")
    return 2 if result["violations"] else 0


if __name__ == "__main__":
    sys.exit(main())
