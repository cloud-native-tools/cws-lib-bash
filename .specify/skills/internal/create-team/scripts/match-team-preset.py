#!/usr/bin/env python3
"""Match a user goal against the predefined team presets.

Deterministic scorer for create-team step 2. It only ranks candidates; the
calling agent decides what to do with them (see references/team-presets.md).

Inputs (one of):
  --goal "<text>"     the user's goal / request text
  --goal-file <path>  read the goal text from a file ("-" = stdin)
Options:
  --presets-dir <dir> preset directory (default: ../templates/teams
                      relative to this script)
  --top N             how many candidates to return (default 3)

Output: JSON on stdout
  {"goalChars": int, "presetsScanned": int, "confidence": "high|medium|low|none",
   "matches": [{"presetId","name","pattern","score","matchedSignals":[...],
                "matchedPatternKeywords":[...],"patternKeywordsOnly":bool,
                "summary","whenToUse","file"}]}

`patternKeywordsOnly` marks a candidate whose score comes from pattern-level
vocabulary alone (zero of the preset's own `signals` matched). Such a candidate
never carries a preset recommendation: when the top-ranked one is keyword-only,
`confidence` is `none` — pattern vocabulary is shared by every preset of that
pattern, so it cannot discriminate one preset from another.

Exit codes: 0 ok, 2 usage error, 3 preset directory unreadable.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Pattern-level keywords are weaker evidence than a preset's own signals.
PATTERN_KEYWORDS = {
    "parallel": ["并行", "同时", "independent", "parallel", "效率", "throughput"],
    "serial": ["串行", "阶段", "依次", "pipeline", "chain", "serial", "流水线"],
    "iteration": ["迭代", "闭环", "收敛", "打分", "iterate", "converge", "quality loop"],
    "continuous": ["持续", "长期", "运营", "周期", "每天", "每小时", "continuous", "cadence", "keep running", "operating loop"],
}

SIGNAL_WEIGHT = 3.0
PATTERN_WEIGHT = 1.0
HIGH_CONFIDENCE_SCORE = 9.0
MEDIUM_CONFIDENCE_SCORE = 4.0
# A clear winner must also lead the runner-up; otherwise it is ambiguous.
HIGH_CONFIDENCE_MARGIN = 3.0


def parse_frontmatter(text: str) -> dict:
    """Extract the scalar and list fields this matcher needs from YAML frontmatter.

    Intentionally minimal (no PyYAML dependency): reads top-level scalars and
    the flat `signals:` list, which is all the scoring needs.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]

    fields: dict = {}
    signals: list[str] = []
    in_signals = False
    for raw in block.splitlines():
        if re.match(r"^signals:\s*$", raw):
            in_signals = True
            continue
        flow = re.match(r"^signals:\s*\[(.*)\]\s*$", raw)
        if flow:
            signals.extend(
                item.strip().strip("\"'")
                for item in flow.group(1).split(",")
                if item.strip()
            )
            continue
        if in_signals:
            item = re.match(r"^\s+-\s+(.*\S)\s*$", raw)
            if item:
                signals.append(item.group(1).strip().strip("\"'"))
                continue
            if raw.strip() and not raw.startswith((" ", "\t")):
                in_signals = False
            else:
                continue
        scalar = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*\S)\s*$", raw)
        if scalar:
            fields[scalar.group(1)] = scalar.group(2).strip().strip("\"'")
    fields["signals"] = signals
    return fields


def score_preset(goal_lower: str, fields: dict) -> tuple[float, list[str], list[str]]:
    matched_signals = [s for s in fields.get("signals", []) if s and s.lower() in goal_lower]
    pattern = fields.get("pattern", "")
    matched_pattern = [k for k in PATTERN_KEYWORDS.get(pattern, []) if k.lower() in goal_lower]
    score = SIGNAL_WEIGHT * len(matched_signals) + PATTERN_WEIGHT * len(matched_pattern)
    return score, matched_signals, matched_pattern


def confidence_of(matches: list[dict]) -> str:
    if not matches or matches[0]["score"] <= 0:
        return "none"
    if matches[0].get("patternKeywordsOnly"):
        return "none"
    top = matches[0]["score"]
    runner_up = matches[1]["score"] if len(matches) > 1 else 0.0
    if top >= HIGH_CONFIDENCE_SCORE and (top - runner_up) >= HIGH_CONFIDENCE_MARGIN:
        return "high"
    if top >= MEDIUM_CONFIDENCE_SCORE:
        return "medium"
    return "low"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(add_help=True, description=__doc__)
    parser.add_argument("--goal")
    parser.add_argument("--goal-file")
    parser.add_argument("--presets-dir")
    parser.add_argument("--top", type=int, default=3)
    args = parser.parse_args(argv)

    if args.goal_file:
        goal = sys.stdin.read() if args.goal_file == "-" else Path(args.goal_file).read_text(encoding="utf-8")
    elif args.goal:
        goal = args.goal
    else:
        print(json.dumps({"error": "provide --goal or --goal-file"}), file=sys.stderr)
        return 2

    presets_dir = Path(args.presets_dir) if args.presets_dir else Path(__file__).resolve().parent.parent / "templates" / "teams"
    if not presets_dir.is_dir():
        print(json.dumps({"error": f"presets dir not found: {presets_dir}"}), file=sys.stderr)
        return 3

    goal_lower = goal.lower()
    matches = []
    for path in sorted(presets_dir.glob("*.md")):
        fields = parse_frontmatter(path.read_text(encoding="utf-8"))
        preset_id = fields.get("preset_id")
        if not preset_id:
            continue
        score, sig, pat = score_preset(goal_lower, fields)
        matches.append({
            "presetId": preset_id,
            "name": fields.get("name", preset_id),
            "pattern": fields.get("pattern", ""),
            "score": round(score, 2),
            "matchedSignals": sig,
            "matchedPatternKeywords": pat,
            "patternKeywordsOnly": bool(pat) and not sig,
            "summary": fields.get("summary", ""),
            "whenToUse": fields.get("when_to_use", ""),
            "file": str(path),
        })

    scanned = len(matches)
    matches.sort(key=lambda m: (-m["score"], m["presetId"]))
    conf = confidence_of(matches)
    top_matches = [m for m in matches[: max(args.top, 1)] if m["score"] > 0]

    print(json.dumps({
        "goalChars": len(goal),
        "presetsScanned": scanned,
        "confidence": conf,
        "matches": top_matches,
    }, ensure_ascii=False, indent=2))
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

_SIG_SCRIPT = '.specify/skills/internal/create-team/scripts/match-team-preset.py'
_SIG_DECLARED = ('--goal', '--goal-file', '--presets-dir', '--top')
_SIG_HELP = (
    'usage: match-team-preset.py [options]\n'
    'options:\n'
    '  --goal\n  --goal-file\n  --presets-dir\n  --top\n'
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
    sys.exit(main(sys.argv[1:]))
