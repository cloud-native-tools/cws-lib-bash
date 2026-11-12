#!/usr/bin/env python3
"""Creation-time territory pairwise-disjoint verifier (042-goal-team-creation).

Thin I/O wrapper: proposal JSON in → pairwise overlap verdicts out. The entire
overlap grammar (expand_scopes / scopes_overlap / overlap_verdict /
detect_overlaps semantics) is IMPORTED from build-summary-input.py — zero
second grammar (042 creation-territory-disjoint.contract.md §Authority).

Checked set = proposed teams ∪ existing teams under the same `goal_slug`
(read from `.specify/teams/*/team.md` frontmatter; an undeclared territory is
`undecidable`, never guessed). A valid repo root without `.specify/teams/` is
a fresh project: zero existing teams, proposals only. A slug present on BOTH
sides is one party, not two: such a self-pair is skipped, because a scope
always intersects itself and reporting that as `overlap` would block a
re-proposal of an already-landed team.

Exit codes: 0 all `no-overlap` / 2 invalid input JSON or schema / 3 repo root
does not exist / 4 any `overlap` (contested paths listed) or `undecidable`
(undeclared party listed). The script performs ZERO writes.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent

EXIT_OK = 0
EXIT_INPUT_ERROR = 2
EXIT_ROOT_ERROR = 3
EXIT_CONFLICT = 4


def _load_grammar():
    spec = importlib.util.spec_from_file_location(
        "bsi_overlap_grammar", _HERE / "build-summary-input.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["bsi_overlap_grammar"] = module
    spec.loader.exec_module(module)
    return module


bsi = _load_grammar()


def _validate(payload: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["input root must be a JSON object"]
    goal_slug = payload.get("goal_slug")
    if not isinstance(goal_slug, str) or not goal_slug.strip():
        errors.append("goal_slug must be a non-empty string")
    teams = payload.get("teams")
    if not isinstance(teams, list) or not teams:
        return errors + ["teams must be a non-empty list"]
    for i, team in enumerate(teams, 1):
        if not isinstance(team, dict):
            errors.append(f"teams[{i}] must be an object")
            continue
        if not isinstance(team.get("slug"), str) or not team.get("slug", "").strip():
            errors.append(f"teams[{i}].slug must be a non-empty string")
        for key in ("write", "read", "forbidden"):
            value = team.get(key, [])
            if not isinstance(value, list) or not all(
                    isinstance(x, str) for x in value):
                errors.append(f"teams[{i}].{key} must be a list of path strings")
        if not isinstance(team.get("non_path", []), list):
            errors.append(f"teams[{i}].non_path must be a list")
    return errors


def _existing_territories(repo_root: Path, goal_slug: str) -> list[tuple[str, Any]]:
    teams_dir = repo_root / ".specify" / "teams"
    out: list[tuple[str, Any]] = []
    if not teams_dir.is_dir():
        return out
    for team_md in sorted(teams_dir.glob("*/team.md")):
        fm = bsi.split_frontmatter(team_md.read_text(encoding="utf-8"))
        if str(fm.get("goal_slug") or "").strip() != goal_slug:
            continue
        out.append((str(fm.get("slug") or team_md.parent.name), fm.get("territory")))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="proposal JSON path (data-model §5)")
    parser.add_argument("--repo-root", default=None, help="repository root (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    def emit(payload: dict) -> None:
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            for key, value in payload.items():
                print(f"{key}: {value}")

    try:
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        emit({"error": f"input unreadable or not valid JSON: {exc}"})
        return EXIT_INPUT_ERROR
    problems = _validate(payload)
    if problems:
        emit({"error": "input schema invalid", "problems": problems})
        return EXIT_INPUT_ERROR

    repo_root = Path(args.repo_root or ".").resolve()
    if not repo_root.is_dir():
        emit({"error": f"repo root does not exist: {repo_root}"})
        return EXIT_ROOT_ERROR

    goal_slug = payload["goal_slug"].strip()
    proposed = [
        (team["slug"],
         {"write": list(team.get("write", [])),
          "read": list(team.get("read", [])),
          "forbidden": list(team.get("forbidden", [])),
          "non_path": list(team.get("non_path", []))})
        for team in payload["teams"]
    ]
    all_teams = proposed + _existing_territories(repo_root, goal_slug)

    verdicts: list[dict] = []
    for i in range(len(all_teams)):
        for j in range(i + 1, len(all_teams)):
            slug_a, terr_a = all_teams[i]
            slug_b, terr_b = all_teams[j]
            if slug_a == slug_b:
                continue
            finding = bsi.overlap_verdict(slug_a, terr_a, slug_b, terr_b)
            contested = sorted({path for pair in finding.get("entries", [])
                                for path in pair})
            verdicts.append({"a": slug_a, "b": slug_b,
                             "verdict": finding["verdict"],
                             **({"contested": contested} if contested else {})})

    summary = {
        "pairs": len(verdicts),
        "no-overlap": sum(1 for v in verdicts if v["verdict"] == "no-overlap"),
        "overlap": sum(1 for v in verdicts if v["verdict"] == "overlap"),
        "undecidable": sum(1 for v in verdicts if v["verdict"] == "undecidable"),
    }
    emit({"verdicts": verdicts, "summary": summary})
    if summary["overlap"] or summary["undecidable"]:
        return EXIT_CONFLICT
    return EXIT_OK


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

_SIG_SCRIPT = '.specify/skills/internal/create-team/scripts/verify-territory-disjoint.py'
_SIG_DECLARED = ('--input', '--json', '--repo-root')
_SIG_HELP = (
    'usage: verify-territory-disjoint.py [options]\n'
    'options:\n'
    '  --input\n  --json\n  --repo-root\n'
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
    raise SystemExit(main())
