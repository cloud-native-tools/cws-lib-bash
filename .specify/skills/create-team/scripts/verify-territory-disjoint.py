#!/usr/bin/env python3
"""Creation-time territory pairwise-disjoint verifier (042-goal-team-creation).

Thin I/O wrapper: proposal JSON in → pairwise overlap verdicts out. The entire
overlap grammar (expand_scopes / scopes_overlap / overlap_verdict /
detect_overlaps semantics) is IMPORTED from build-summary-input.py — zero
second grammar (042 creation-territory-disjoint.contract.md §Authority).

Checked set = proposed teams ∪ existing teams under the same `goal_slug`
(read from `.specify/teams/*/team.md` frontmatter; an undeclared territory is
`undecidable`, never guessed). A valid repo root without `.specify/teams/` is
a fresh project: zero existing teams, proposals only.

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


if __name__ == "__main__":
    raise SystemExit(main())
