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

_SIG_SCRIPT = '.specify/skills/sdd-loop-driver/scripts/audit-plan-changes.py'
_SIG_DECLARED = ('--base', '--declarations', '--head', '--plan-owned', '--repo')
_SIG_HELP = (
    'usage: audit-plan-changes.py [options]\n'
    'options:\n'
    '  --base\n  --declarations\n  --head\n  --plan-owned\n  --repo\n'
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
