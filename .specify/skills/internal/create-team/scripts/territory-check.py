#!/usr/bin/env python3
"""Territory check — may a crew seat write this path? (094 handoff contract, C-61…C-63).

The design face of a handoff contract feeds the construction crew a closed allow/forbid
list: `requirements.md`, `tasks.md`, `verification.md` and `handoff.md` land in
`territory.forbidden` of every seat that carries the expansion, and the granted writes
stay inside the spec directory (FR-036 / SC-007). This script answers one concrete
question for one path — the refusal MUST NOT depend on the crew's cooperation.

The scope grammar (`expand_scopes` / `scopes_overlap`) is IMPORTED from the skill's
`build-summary-input.py` — zero second grammar, the same discipline as
`verify-territory-disjoint.py`. A path is refused when it matches `territory.forbidden`
(an explicit negative always wins), when no `territory.write` entry contains it, or when
the team declares no territory at all — an absent scope is never a permission.

Read-only: reports a verdict, writes nothing.

Usage:
  territory-check.py --team <team.md> --path <path> [--seat <seat-slug>]
      [--repo-root <dir>] [--json]

Exit codes:
  0  allowed — the seat's territory contains the path
  1  refused — the documented check failed (forbidden / outside-write-scope / undeclared)
  2  an argument or environment error (missing team file, unresolvable seat, bad flag)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent

EXIT_ALLOWED = 0
EXIT_REFUSED = 1
EXIT_INPUT_ERROR = 2


def _load_grammar():
    spec = importlib.util.spec_from_file_location(
        "bsi_territory_check", _HERE / "build-summary-input.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["bsi_territory_check"] = module
    spec.loader.exec_module(module)
    return module


bsi = _load_grammar()


def _scopes(raw: object) -> list[str]:
    return sorted(bsi.expand_scopes([str(item) for item in raw or []])) \
        if isinstance(raw, list) else []


def _territory_block(raw: object) -> dict | None:
    """A `{write, read, forbidden}` block; None means UNDECLARED, never empty."""
    if not isinstance(raw, dict):
        return None
    return {
        "write": _scopes(raw.get("write")),
        "forbidden": _scopes(raw.get("forbidden")),
    }


def _check_path(path: str, territory: dict) -> str | None:
    """(reason) when refused, None when allowed; forbidden always wins (C-62)."""
    for entry in territory["forbidden"]:
        if bsi.scopes_overlap(entry, path):
            return "forbidden"
    for entry in territory["write"]:
        if bsi.scopes_overlap(entry, path):
            return None
    return "outside-write-scope"


def _member_territory(frontmatter: dict, seat: str) -> dict | None:
    """The named seat's member-level territory, when the roster declares one."""
    members = frontmatter.get("members")
    for member in members if isinstance(members, list) else []:
        if not isinstance(member, dict):
            continue
        if str(member.get("agent") or "") == seat or str(member.get("role") or "") == seat:
            found = member
            break
    else:
        raise LookupError(seat)
    raw = found.get("territory")
    return _territory_block(raw) if isinstance(raw, dict) else None


def _normalize_path(raw: str, repo_root: Path) -> str:
    candidate = Path(raw)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(repo_root).as_posix()
        except ValueError:
            return raw.replace("\\", "/")
    return bsi.normalize_scope(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--team", required=True, help="the crew's team.md path")
    parser.add_argument("--path", required=True, help="the concrete path a seat may write")
    parser.add_argument("--seat", default=None,
                        help="seat slug (agent or role) whose member territory also applies")
    parser.add_argument("--repo-root", default=None, help="repository root (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    def emit(payload: dict) -> None:
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(payload.get("line") or payload.get("error") or "")
        payload.pop("line", None)

    team_path = Path(args.team)
    if not team_path.is_file():
        emit({"error": f"team definition not found: {team_path}"})
        return EXIT_INPUT_ERROR
    try:
        frontmatter = bsi.split_frontmatter(team_path.read_text(encoding="utf-8"))
    except OSError as exc:
        emit({"error": f"team definition unreadable: {exc}"})
        return EXIT_INPUT_ERROR
    if not frontmatter:
        emit({"error": f"team definition carries no readable frontmatter: {team_path}"})
        return EXIT_INPUT_ERROR

    team_slug = str(frontmatter.get("slug") or team_path.parent.name)
    seat = args.seat or team_slug
    repo_root = Path(args.repo_root or ".").resolve()
    path = _normalize_path(args.path, repo_root)

    team_level = _territory_block(frontmatter.get("territory"))
    member_level = None
    if args.seat:
        try:
            member_level = _member_territory(frontmatter, args.seat)
        except LookupError:
            emit({"error": f"seat-unresolvable: {args.seat!r} names no roster member of "
                           f"team {team_slug!r}"})
            return EXIT_INPUT_ERROR

    reason = None
    if team_level is None:
        reason = "territory-undeclared"
    else:
        reason = _check_path(path, team_level)
    if reason is None and member_level is not None:
        reason = _check_path(path, member_level)

    payload = {
        "team": team_slug,
        "seat": seat,
        "path": path,
        "verdict": "allowed" if reason is None else "refused",
        "reason": reason,
        "line": (f"allowed: path {path!r} is writable by seat {seat!r}"
                 if reason is None else
                 f"refused: path {path!r} is not writable by seat {seat!r} ({reason})"),
    }
    emit(payload)
    return EXIT_ALLOWED if reason is None else EXIT_REFUSED


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

_SIG_SCRIPT = '.specify/skills/internal/create-team/scripts/territory-check.py'
_SIG_DECLARED = ('--json', '--path', '--repo-root', '--seat', '--team')
_SIG_HELP = (
    'usage: territory-check.py [options]\n'
    'options:\n'
    '  --team\n  --path\n  --seat\n  --json\n  --repo-root\n'
    '  -h, --help    print this help and exit\n'
    '  --version     print the script name and the framework version, then exit\n'
    +
    'side-effects:' + ' ' + 'reads the team definition and reports a verdict; writes nothing' + '\n'
    +
    'exit-codes:' + ' ' + '0 allowed; 1 a documented check failed (refused); 2 argument or environment error' + '\n'
)


def _sig_guard(argv):
    # Answer the flags and reject an undeclared option before any parsing or write.
    # RULES are asked of the owner (script_interface_cli.guard_argv), never restated.
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
    raise SystemExit(main())
