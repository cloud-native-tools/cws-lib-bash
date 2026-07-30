#!/usr/bin/env python3
"""Detect project information sources for the summarize-project skill.

Purpose: identify whether a target project is managed with the SpecKit
framework (a .specify/ directory with recognizable structure) and enumerate
the artifacts and candidate external documents the skill should read.

Input:  --target <project-root> (default: current directory)
Output: JSON on stdout with keys:
  - speckit: bool — True when .specify/ exists with recognizable structure
  - specify_dir: relative path of .specify/ or null
  - artifacts: SpecKit artifacts found (constitution, features index,
    feature detail files, per-spec requirements/tasks/plan/verification,
    project dir files); empty when not a SpecKit project
  - candidates: non-SpecKit source hints (README, docs/, common doc files)
  - default_report_path: suggested summary report location
Exit code: 0 on success, 1 when the target directory does not exist.
"""
import argparse
import json
import sys
from pathlib import Path

SPEC_ARTIFACTS = ("requirements.md", "plan.md", "tasks.md", "verification.md")
DOC_NAMES = ("README.md", "README.zh.md", "CHANGELOG.md", "ROADMAP.md")
DOC_GLOBS = ("*.md", "*.docx", "*.pdf")


def detect(target: Path) -> dict:
    specify = target / ".specify"
    artifacts: dict = {
        "constitution": None,
        "features_index": None,
        "feature_files": 0,
        "specs": [],
        "project_dir": [],
    }
    if specify.is_dir():
        memory = specify / "memory"
        constitution = memory / "constitution.md"
        if constitution.is_file():
            artifacts["constitution"] = str(constitution.relative_to(target))
        features_index = memory / "features.md"
        if features_index.is_file():
            artifacts["features_index"] = str(features_index.relative_to(target))
        features_dir = memory / "features"
        if features_dir.is_dir():
            artifacts["feature_files"] = len(list(features_dir.glob("*.md")))
        specs_dir = specify / "specs"
        if specs_dir.is_dir():
            for spec in sorted(p for p in specs_dir.iterdir() if p.is_dir()):
                artifacts["specs"].append(
                    {
                        "key": spec.name,
                        **{
                            name.split(".")[0]: (spec / name).is_file()
                            for name in SPEC_ARTIFACTS
                        },
                    }
                )
        project_dir = specify / "project"
        if project_dir.is_dir():
            artifacts["project_dir"] = sorted(
                p.name for p in project_dir.iterdir() if p.is_file()
            )

    candidates: dict = {"readme": None, "docs_dir": None, "documents": []}
    for name in DOC_NAMES:
        if (target / name).is_file():
            key = "readme" if name.startswith("README") else "documents"
            if key == "readme" and candidates["readme"] is None:
                candidates["readme"] = name
            else:
                candidates["documents"].append(name)
    docs_dir = target / "docs"
    if docs_dir.is_dir():
        candidates["docs_dir"] = "docs"
        candidates["documents"].extend(
            str(p.relative_to(target))
            for glob in DOC_GLOBS
            for p in sorted(docs_dir.glob(glob))
        )
    candidates["documents"] = sorted(set(candidates["documents"]))

    speckit = bool(
        specify.is_dir()
        and (artifacts["constitution"] or artifacts["specs"] or artifacts["features_index"])
    )
    return {
        "speckit": speckit,
        "specify_dir": ".specify" if specify.is_dir() else None,
        "artifacts": artifacts if speckit else {},
        "candidates": candidates,
        "default_report_path": (
            ".specify/project/summary.md" if speckit else "docs/project-summary.md"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--target", default=".", help="project root directory")
    args = parser.parse_args()
    target = Path(args.target).resolve()
    if not target.is_dir():
        print(json.dumps({"error": f"target not found: {target}"}), file=sys.stderr)
        return 1
    print(json.dumps(detect(target), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
