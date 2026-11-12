#!/usr/bin/env python3
"""decomposition-check.py — deterministic large-feature decomposition gate.

Two decision points share the ceilings of the fast-lane medium interval
(``FR_CEILING`` = FR_MAX, ``TASK_CEILING`` = TASK_MAX):

  plan   at plan entry: > FR_CEILING requirement definitions -> split-required
  tasks  at tasks U4:   > FR_CEILING FR definitions or
                        > TASK_CEILING task rows -> split-required

Every value is derived from the artifacts; there is no self-attestation.
An unreadable or empty input is an input error (exit 2).

Exit codes:
  0 = proceed (fits the single-feature interval)
  1 = split-required (decompose before the next stage)
  2 = input or parse error

Standard library only, Python >= 3.8. Self-contained; never reads the
framework runtime scripts tree.
"""

import argparse
import json
import os
import re
import sys
import time

FR_CEILING = 120
TASK_CEILING = 160
FR_PATTERN = re.compile(r"^- \*\*FR-[0-9]{3}\*\*:")
TASK_PATTERN = re.compile(r"^- \[[ xX>~]\] T[0-9]{3}")


class InputError(Exception):
    pass


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise InputError("cannot read %s: %s" % (path, exc))


def count_fr(text):
    return sum(1 for line in text.splitlines() if FR_PATTERN.match(line))


def count_tasks(text):
    return sum(1 for line in text.splitlines() if TASK_PATTERN.match(line))


def measure(mode, requirements_path, tasks_path):
    if not os.path.isfile(requirements_path):
        raise InputError("missing requirements file: %s" % requirements_path)
    fr_count = count_fr(read_file(requirements_path))
    if fr_count == 0:
        raise InputError("no FR definitions (^- **FR-NNN**:) in %s" % requirements_path)

    task_count = None
    if mode == "tasks":
        if not tasks_path:
            raise InputError("--mode tasks requires --tasks")
        if not os.path.isfile(tasks_path):
            raise InputError("missing tasks file: %s" % tasks_path)
        task_count = count_tasks(read_file(tasks_path))
        if task_count == 0:
            raise InputError("no task rows (^- [x] TNNN) in %s" % tasks_path)

    reasons = []
    if fr_count > FR_CEILING:
        reasons.append("FR definitions=%d exceeds ceiling %d" % (fr_count, FR_CEILING))
    if task_count is not None and task_count > TASK_CEILING:
        reasons.append("task rows=%d exceeds ceiling %d" % (task_count, TASK_CEILING))

    return {
        "mode": mode,
        "decision": "split-required" if reasons else "proceed",
        "measured": {
            "fr_count": fr_count,
            "task_count": task_count,
            "fr_ceiling": FR_CEILING,
            "task_ceiling": TASK_CEILING,
        },
        "reasons": reasons,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Deterministic large-feature decomposition gate.")
    parser.add_argument("--mode", choices=("plan", "tasks"), default="plan",
                        help="decision point: plan entry or tasks U4")
    parser.add_argument("--requirements", required=True)
    parser.add_argument("--tasks", default="")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args(argv)

    try:
        record = measure(args.mode, args.requirements, args.tasks)
    except InputError as exc:
        print("decomposition-check: input error: %s" % exc, file=sys.stderr)
        return 2

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    print(json.dumps(record, ensure_ascii=False))
    return 0 if record["decision"] == "proceed" else 1


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

_SIG_SCRIPT = '.specify/skills/sdd-loop-driver/scripts/decomposition-check.py'
_SIG_DECLARED = ('--json-out', '--mode', '--requirements', '--tasks')
_SIG_HELP = (
    'usage: decomposition-check.py [options]\n'
    'options:\n'
    '  --json-out\n  --mode\n  --requirements\n  --tasks\n'
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
