#!/usr/bin/env python3
"""Mechanical write-path gate checker (P2).

Evaluates candidate write paths against .specify/gate.yaml (deny > confirm > allow)
and reports the strictest verdict via exit code. No LLM judgment involved.

Usage:
  python3 .specify/scripts/python/gate-check.py <path> [<path> ...]
  git diff --name-only | python3 .specify/scripts/python/gate-check.py --stdin

Exit codes:
  0  all paths allowed
  1  at least one path requires human confirmation (none denied)
  2  at least one path is denied
  3  gate file missing or unparsable (fail-open is NOT assumed; caller decides)

Gate file format (YAML subset: top-level keys with "- pattern" list items only,
parsed without external deps so the checker runs on bare python3):
  deny:    [fnmatch globs]
  confirm: [fnmatch globs]
  allow:   [fnmatch globs]   # documentation only; no match already means allow
"""

from __future__ import annotations

import sys
from fnmatch import fnmatch
from pathlib import Path

def _find_repo_root() -> Path:
    # Fixed parents[2] breaks when invoked via the .specify/scripts/python/
    # mirror copy (resolves to `.specify`, doubled paths, gate unreadable).
    # Walk up to the nearest ancestor containing a .specify/ directory so
    # both the canonical and the mirror copy resolve the same repo root.
    for parent in Path(__file__).resolve().parents:
        # skip a parent that IS `.specify`: a stray nested projection
        # (`.specify/.specify/`) would otherwise self-match here and
        # mis-root the mirror copy onto the runtime dir
        if parent.name != ".specify" and (parent / ".specify").is_dir():
            return parent
    return Path(__file__).resolve().parents[2]


REPO_ROOT = _find_repo_root()
GATE_FILE = REPO_ROOT / ".specify" / "gate.yaml"


def parse_gate(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"deny": [], "confirm": [], "allow": []}
    current: str | None = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            key = line[:-1].strip()
            current = key if key in sections else None
        elif line.strip().startswith("- ") and current:
            item = line.strip()[2:].strip().strip("\"'")
            if item:
                sections[current].append(item)
        elif line.strip().endswith("[]") and line.split(":")[0].strip() in sections:
            current = None
    return sections


def match(path: str, patterns: list[str]) -> str | None:
    # normalize: strip an explicit ./ prefix (NOT lstrip — that eats dotfile names)
    norm = path[2:] if path.startswith("./") else path
    norm = norm.lstrip("/")
    for pat in patterns:
        if fnmatch(norm, pat) or fnmatch("/" + norm, "/" + pat):
            return pat
        # "**/x" should also match "x" at repo root
        if pat.startswith("**/") and fnmatch(norm, pat[3:]):
            return pat
    return None


# --version, wired through the one version source (C-8)
#
# `guard_argv()` answers `--version` (and rejects an undeclared option) BEFORE any parser
# reads the line, so it works for a flat argparse parser, for one whose subcommands are
# required, and for the two modules that read sys.argv by hand. It writes nothing and
# resolves `<script-name> <framework-version>` from the nearest pyproject.toml at run
# time — this file carries no version literal. `--help` is left to the module's own body.
import sys as _sig_sys  # noqa: E402
import pathlib as _sig_pathlib

_SIG_DIR = str(_sig_pathlib.Path(__file__).resolve().parent)
if _SIG_DIR not in _sig_sys.path:
    _sig_sys.path.insert(0, _SIG_DIR)
try:  # the helper ships beside the engine; a copied tree may lack it
    from script_interface_cli import fill_help_labels  # noqa: E402
    from script_interface_cli import guard_argv as _sig_guard  # noqa: E402
except ImportError:  # a skill-local or sandbox copy still runs its action
    def fill_help_labels(text, **_kwargs):
        return text

    def _sig_guard(_argv=None, declared=None, **_kwargs):
        return None


_HELP = """usage: gate-check.py <path> [...] | --stdin
options:
  -h, --help     print this help and exit
  --version      print <script-name> <framework-version> and exit
  --stdin        read the candidate paths from standard input, one per line
side-effects: none; reads the gate file and the named paths and writes nothing
exit-codes: 0 all paths allowed; 1 at least one path requires confirmation; 2 at least one
  path is denied or an option is undeclared; 3 the gate file is missing or unparsable
"""


def main() -> int:
    # `declared` is this script's own vocabulary: `--stdin` is the one option its hand-rolled
    # loop accepts, and stating it here is what keeps the guard from refusing a legal token.
    _sig_guard(declared=["--stdin"])  # answer --version / reject an undeclared option
    if any(a in ("-h", "--help") for a in sys.argv[1:]):
        print(fill_help_labels(_HELP), end="")
        return 0
    args = sys.argv[1:]
    if "--stdin" in args:
        args.remove("--stdin")
        args += [ln.strip() for ln in sys.stdin if ln.strip()]
    if not args:
        print("usage: gate-check.py <path> [...] | --stdin", file=sys.stderr)
        return 3

    if not GATE_FILE.exists():
        print(f"gate file not found: {GATE_FILE}", file=sys.stderr)
        return 3
    try:
        gate = parse_gate(GATE_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # unparsable gate must be visible, not ignored
        print(f"gate file unparsable: {exc}", file=sys.stderr)
        return 3

    verdict = 0
    for path in args:
        pat = match(path, gate["deny"])
        if pat:
            print(f"DENY    {path}  (rule: {pat})")
            verdict = max(verdict, 2)
            continue
        pat = match(path, gate["confirm"])
        if pat:
            print(f"CONFIRM {path}  (rule: {pat})")
            verdict = max(verdict, 1)
            continue
        print(f"allow   {path}")
    return verdict


if __name__ == "__main__":
    sys.exit(main())
