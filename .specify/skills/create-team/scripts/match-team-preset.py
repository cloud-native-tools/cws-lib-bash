#!/usr/bin/env python3
"""Match a user goal against the predefined team presets.

Deterministic scorer for create-team step 2. It only ranks candidates; the
calling agent decides what to do with them (see references/teams.md).

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
                "matchedPatternKeywords":[...],"summary","whenToUse","file"}]}

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


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
