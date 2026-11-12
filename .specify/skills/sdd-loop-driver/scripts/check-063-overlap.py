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
    "075-sdd-loop-efficiency/contracts/cli-profiles.md",
    "test_cli_profile_record.py",
    "references/cli/README.md",
)
DEFAULT_BRANCH = "075-sdd-loop-efficiency"


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


#
# Emitted by `.specify/scripts/python/sync-mirrors.py`; the authority for this block is
# `contracts/mirror-projection.contract.md` C-34 / C-36. It depends on nothing
# that exists only in the source tree: it re-derives its own version line (C-36).
_VERSION_SOURCE = "pyproject.toml"
_VERSION_QUOTES = chr(39) + chr(34)
_MAX_UPWARD_LEVELS = 12


def _bridge_version(start):
    _here = start.resolve()
    for _ in range(_MAX_UPWARD_LEVELS + 1):
        if (_here / _VERSION_SOURCE).is_file() and (_here / ".git").exists():
            try:
                _text = (_here / _VERSION_SOURCE).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return "unknown"
            _in_project = False
            for _raw in _text.splitlines():
                _line = _raw.strip()
                if not _line or _line.startswith("#"):
                    continue
                if _line.startswith("[") and _line.endswith("]"):
                    _in_project = _line == "[project]"
                    continue
                if not _in_project:
                    continue
                _key, _sep, _value = _line.partition("=")
                if _sep and _key.strip() == "version":
                    _value = _value.strip()
                    if len(_value) >= 2 and _value[0] == _value[-1] and _value[0] in _VERSION_QUOTES:
                        _value = _value[1:-1]
                    return _value or "unknown"
            return "unknown"
        if _here.parent == _here:
            return "unknown"
        _here = _here.parent
    return "unknown"

def _bridge_main():
    import sys as _bridge_sys
    from pathlib import Path as _bridge_path

    _argv = list(_bridge_sys.argv[1:])
    if "--version" not in _argv:
        return
    if "--" in _argv and _argv.index("--version") > _argv.index("--"):
        return
    _invoked = _bridge_sys.argv[0] if _bridge_sys.argv[0] else "."
    _name = _bridge_path(_invoked).name or "script"
    print("%s %s" % (_name, _bridge_version(_bridge_path(_invoked).resolve().parent)))
    raise SystemExit(0)


_bridge_main()
del _bridge_main
# script-interface:86:begin (feature 086 -- generated; the rule is owned by
# `.specify/shared/definitions/script-interface-definitions.md`, its executable form by
# `.specify/scripts/python/script_interface_cli.py`. This block owns no rule of its own.)
import sys as _sig_sys
import pathlib as _sig_pathlib

_SIG_OWNER = _sig_pathlib.Path(__file__).resolve().parent
while not ((_SIG_OWNER / 'pyproject.toml').is_file()
           and (_SIG_OWNER / '.git').exists()) and _SIG_OWNER.parent != _SIG_OWNER:
    _SIG_OWNER = _SIG_OWNER.parent
_SIG_OWNER = str(_SIG_OWNER / 'scripts' / 'python')
if _SIG_OWNER not in _sig_sys.path:
    _sig_sys.path.insert(0, _SIG_OWNER)

_SIG_SCRIPT = '.specify/skills/sdd-loop-driver/scripts/check-063-overlap.py'
_SIG_DECLARED = ('--branch', '--repo', '--strict-premerge')
_SIG_HELP = (
    'usage: check-063-overlap.py [options]\n'
    'options:\n'
    '  --branch\n  --repo\n  --strict-premerge\n'
    '  -h, --help    print this help and exit\n'
    '  --version     print the script name and the framework version, then exit\n'
    +
    'side-effects:' + ' ' + 'writes only through the options it documents; a flag-only invocation writes nothing' + '\n'
    +
    'exit-codes:' + ' ' + '0 success; 1 a documented check failed; 2 argument or environment error' + '\n'
)


def _sig_guard(argv):
    # Answer the flags and reject an undeclared option before any parsing or write.
    # RULES are asked of the owner (script_interface_cli.guard_argv), never restated:
    # the declared vocabulary and the flag forms are its, and C-9 (a recognized option
    # never rescues an unrecognized one) is its judgement. What stays local is the help
    # BODY, because its operand sentence is this script's own.
    try:
        import script_interface_cli as _sig  # noqa: E402 -- deferred: a copied script may lack it
    except ImportError:  # skill-local or sandbox copy: the module's own parser still runs
        return list(argv)
    line = list(argv)
    try:
        _sig.guard_argv(line, declared=_SIG_DECLARED)
    except SystemExit as answered:  # what guard_argv raises; _sig_sys.exit IS SystemExit
        if answered.code == 0:
            raise
        # The owner prints the rejection line and this script's help body is appended after
        # it, so the reader sees the vocabulary and not only the refusal.
        _sig_sys.stderr.write(_SIG_HELP)
        raise _sig_sys.exit(answered.code)
    stop = line.index('--') if '--' in line else len(line)
    if '-h' in line[:stop] or '--help' in line[:stop]:
        _sig_sys.stdout.write(_SIG_HELP)
        raise _sig_sys.exit(0)
    return line

if __name__ == "__main__":
    _sig_sys.argv = [_sig_sys.argv[0]] + _sig_guard(_sig_sys.argv[1:])
# script-interface:86:end

if __name__ == "__main__":
    sys.exit(main())
