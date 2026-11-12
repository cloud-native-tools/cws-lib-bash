#!/usr/bin/env python3
# Provenance: mirrored from .specify/skills/sdd-project-setup/scripts/logical-framework.py
# so this external skill stays independently runnable. Parity is enforced by
# tests/contract/test_sdd_house_keeping_skill.py (the three provenance lines are ignored).
"""Logical-framework inventory for a Spec Kit project (read-only).

The physical inventory (`mechanism-inventory.py`) answers "are the mechanism
directories installed". This one answers the complement: "is the project's
logical framework configured" — instructions, goals, features, docs, plus the
conditional layers (teams, agents) and the advisory knowledge assets.

Three readiness tiers (absence is not automatically a defect):

  required      instructions.md, features registry + detail files, docs tree
  recommended   goals, glossary, register, knowledge
  conditional   teams, agent instances/templates (not-configured is legitimate)

Exit codes: 0 required tier ok; 1 a required gap; 2 usage/parse error.
`--strict` promotes recommended gaps to failures as well.

Usage:
    python3 logical-framework.py --project . [--json] [--strict]
"""

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED = "required"
RECOMMENDED = "recommended"
CONDITIONAL = "conditional"

OK = "ok"
GAP = "gap"
NOT_CONFIGURED = "not-configured"
NA = "n/a"


def rel(project: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def count_feature_rows(registry: Path) -> int:
    rows = 0
    for line in read_text(registry).splitlines():
        if re.match(r"^\|\s*\d{3}\s*\|", line):
            rows += 1
    return rows


def total_marker(registry: Path):
    match = re.search(r"\*\*Total Features\*\*:\s*(\d+)", read_text(registry))
    return int(match.group(1)) if match else None


def check_instructions(project: Path):
    spec = project / ".specify"
    instr = spec / "instructions.md"
    if not instr.is_file():
        return {"status": GAP, "detail": "missing .specify/instructions.md"}
    broken = []
    for name in ("AGENTS.md", "CLAUDE.md", "QODER.md", "QWEN.md",
                 ".github/copilot-instructions.md", ".qoder/project_rules.md"):
        link = project / name
        if link.is_symlink() and not link.exists():
            broken.append(name)
    detail = f"{len(read_text(instr).splitlines())} lines"
    if broken:
        return {"status": GAP, "detail": "broken compat links: " + ", ".join(broken)}
    return {"status": OK, "detail": detail}


def check_features(project: Path):
    spec = project / ".specify"
    registry = spec / "features.md"
    details = spec / "features"
    if not registry.is_file():
        return {"status": GAP, "detail": "missing .specify/features.md"}
    rows = count_feature_rows(registry)
    files = sorted(p.stem for p in details.glob("*.md")) if details.is_dir() else []
    marker = total_marker(registry)
    problems = []
    if rows == 0:
        problems.append("registry has no feature rows")
    if marker is not None and marker != rows:
        problems.append(f"Total Features={marker} but rows={rows}")
    if rows and len(files) < rows:
        problems.append(f"{rows} rows but {len(files)} detail files")
    if problems:
        return {"status": GAP, "detail": "; ".join(problems)}
    return {"status": OK, "detail": f"{rows} features / {len(files)} detail files"}


def check_docs(project: Path):
    docs = project / "docs"
    if not docs.is_dir():
        return {"status": GAP, "detail": "missing docs/ tree"}
    entries = [docs / n for n in ("README.md", "index.md", "INDEX.md")]
    md = list(docs.rglob("*.md"))
    if not md:
        return {"status": GAP, "detail": "docs/ has no markdown"}
    entry = next((rel(project, p) for p in entries if p.is_file()), None)
    return {"status": OK, "detail": f"{len(md)} md files; entry={entry or 'none'}"}


def check_goals(project: Path):
    goals = project / ".specify" / "goal"
    if not goals.is_dir():
        return {"status": GAP, "detail": "no .specify/goal/ definitions"}
    defined = sorted(p.parent.name for p in goals.glob("*/goal.md"))
    if not defined:
        return {"status": GAP, "detail": "goal/ exists but no */goal.md"}
    note = f"{len(defined)} goals"
    if len(defined) < 3:
        note += " (recommended range 3-5)"
    return {"status": OK, "detail": note + ": " + ", ".join(defined)}


def check_advisory(project: Path):
    spec = project / ".specify"
    mem = spec / "memory"
    out = {}
    for key, path in (("glossary", spec / "glossary.md"),
                      ("register", spec / "register.md"),
                      ("knowledge", mem / "knowledge")):
        out[key] = {"status": OK if path.exists() else GAP,
                    "detail": rel(project, path) if path.exists() else "absent"}
    return out


def check_conditional(project: Path):
    spec = project / ".specify"
    teams = spec / "teams"
    agents = spec / "agents"
    team_dirs = [p for p in teams.iterdir() if p.is_dir()] if teams.is_dir() else []
    agent_files = []
    for sub in ("templates", "instances"):
        d = agents / sub
        if d.is_dir():
            agent_files.extend(p.name for p in d.glob("*.agent.md"))
    return {
        "teams": {"status": OK if team_dirs else NOT_CONFIGURED,
                  "detail": f"{len(team_dirs)} teams" if team_dirs else "no .specify/teams entries"},
        "agents": {"status": OK if agent_files else NOT_CONFIGURED,
                   "detail": f"{len(agent_files)} agent definitions" if agent_files else "no .specify/templates/instances"},
    }


def build_report(project: Path, strict: bool):
    checks = {
        "instructions": dict(check_instructions(project), tier=REQUIRED),
        "features": dict(check_features(project), tier=REQUIRED),
        "docs": dict(check_docs(project), tier=REQUIRED),
        "goals": dict(check_goals(project), tier=RECOMMENDED),
    }
    for key, value in check_advisory(project).items():
        checks[key] = dict(value, tier=RECOMMENDED)
    for key, value in check_conditional(project).items():
        checks[key] = dict(value, tier=CONDITIONAL)

    required_gaps = [k for k, v in checks.items() if v["tier"] == REQUIRED and v["status"] == GAP]
    recommended_gaps = [k for k, v in checks.items() if v["tier"] == RECOMMENDED and v["status"] == GAP]
    failing = required_gaps + (recommended_gaps if strict else [])
    verdict = "gap" if failing else ("partial" if recommended_gaps else "ready")
    return {
        "project": str(project),
        "verdict": verdict,
        "strict": strict,
        "required_gaps": required_gaps,
        "recommended_gaps": recommended_gaps,
        "conditional": {k: checks[k]["status"] for k in ("teams", "agents")},
        "checks": checks,
    }


def render_text(report):
    lines = [f"logical-framework — {report['project']}",
             f"  verdict: {report['verdict']} (strict={report['strict']})"]
    for tier in (REQUIRED, RECOMMENDED, CONDITIONAL):
        for key, value in report["checks"].items():
            if value["tier"] != tier:
                continue
            lines.append(f"  [{tier:11s}] {key:13s} {value['status']:14s} {value['detail']}")
    if report["required_gaps"]:
        lines.append("  required gaps: " + ", ".join(report["required_gaps"]))
    if report["recommended_gaps"]:
        lines.append("  recommended gaps: " + ", ".join(report["recommended_gaps"]))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", default=".", help="project root (default: .)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument("--strict", action="store_true", help="recommended gaps also fail")
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not (project / ".specify").is_dir():
        message = f"not a Spec Kit project (no .specify/): {project}"
        print(json.dumps({"error": message}) if args.json else message)
        return 2
    report = build_report(project, args.strict)
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render_text(report))
    return 1 if (report["required_gaps"] or (args.strict and report["recommended_gaps"])) else 0


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

_SIG_SCRIPT = '.specify/skills/sdd-house-keeping/scripts/logical-framework.py'
_SIG_DECLARED = ('--json', '--project', '--strict')
_SIG_HELP = (
    'usage: logical-framework.py [options]\n'
    'options:\n'
    '  --json\n  --project\n  --strict\n'
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
