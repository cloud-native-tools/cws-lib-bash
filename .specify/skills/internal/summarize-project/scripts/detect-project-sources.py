#!/usr/bin/env python3
"""Probe an **opt-in** repository for supplementary sources (summarize-project).

Role (narrowed): this script is NOT the main input path. The skill's input model
is "required-info table + context ingestion + form fill-in" (see
references/required-info.md): project management facts come from the project
input form (<delivery-dir>/data/project-input.yaml), not from scanning code
repositories.

This probe runs ONLY when the form opts in to repo material -- i.e. the form
declares `project.repos[]` (repo_id + repo_path) and some field is marked
"derive from repo" via `derive_fields`. For such a repository it reports which
supplementary sources happen to exist, so the skill can issue **targeted**
queries for the authorised fields only (never a full-repo scan; see
references/source-tiers.md).

Input:  --target <repo-path> (default: current directory)
Output: JSON on stdout. Backward-compatible keys (unchanged, nothing removed):
  - speckit: bool — True when .specify/ exists with recognizable structure
  - specify_dir: relative path of .specify/ or null
  - artifacts: SpecKit artifacts found (constitution, features index,
    feature detail files, per-spec requirements/tasks/plan/verification,
    project dir files); empty when not a SpecKit project
  - candidates: doc-level source hints (README, docs/, common doc files)
  - default_report_path: suggested summary delivery directory (summary.md + assets/ + data/)
Tier classification keys (supplementary-source ladder — see references/source-tiers.md):
  - source_tiers: per-tier {present, ...detail} for spec/memory/code_build/
    git/external_docs
  - primary_tier: the highest present tier name, or null
  - build: {languages, manifests, build_files, entry_points, ci}
  - features_index_populated: bool — features.md has >=1 data row
  - feature_row_count: int — number of feature data rows in features.md
  - git: {present, tags_present}
Exit code: 0 on success, 1 when the target directory does not exist.

Read-only: inspects file existence/content only; never writes to the repository.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SPEC_ARTIFACTS = ("requirements.md", "plan.md", "tasks.md", "verification.md")
DOC_NAMES = ("README.md", "README.zh.md", "CHANGELOG.md", "ROADMAP.md")
DOC_GLOBS = ("*.md", "*.docx", "*.pdf")

# Language clue: manifest filename -> language/ecosystem.
MANIFEST_LANG = {
    "Cargo.toml": "rust",
    "pyproject.toml": "python",
    "setup.py": "python",
    "setup.cfg": "python",
    "package.json": "node",
    "go.mod": "go",
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "java",
    "CMakeLists.txt": "c/c++",
    "Gemfile": "ruby",
    "composer.json": "php",
}
# Build-system files at the project root (CI is detected separately).
BUILD_FILES = (
    "Makefile", "makefile", "GNUmakefile",
    "CMakeLists.txt", "Justfile", "justfile",
    "Taskfile.yml", "Taskfile.yaml", "Dockerfile",
)
# A feature data row in features.md, per the awk expression documented inside
# that file: /^\| [0-9]{3} \|/ — a 3-digit feature id in the first cell.
FEATURE_ROW_RE = re.compile(r"^\|\s*\d{3}\s*\|")

# Highest-to-lowest tier order for primary_tier selection.
TIER_ORDER = ("spec", "memory", "code_build", "git", "external_docs")


def count_feature_rows(features_path: Path) -> int:
    """Count feature data rows in features.md (excludes header/separator)."""
    try:
        text = features_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return 0
    return sum(1 for line in text.splitlines() if FEATURE_ROW_RE.match(line))


def detect_build(target: Path) -> dict:
    """Detect language/build system, entry points, and CI presence."""
    manifests = [name for name in MANIFEST_LANG if (target / name).is_file()]
    languages = sorted({MANIFEST_LANG[name] for name in manifests})
    build_files = [name for name in BUILD_FILES if (target / name).is_file()]

    entry_points = detect_entry_points(target, languages)
    ci = detect_ci(target)
    return {
        "languages": languages,
        "manifests": sorted(manifests),
        "build_files": sorted(set(build_files)),
        "entry_points": entry_points,
        "ci": ci,
    }


def detect_entry_points(target: Path, languages: list) -> list:
    """Best-effort, language-aware entry-point file hints (existence only)."""
    checks: list = []
    dirs: list = []
    if "rust" in languages:
        checks += ["src/main.rs", "src/lib.rs"]
        if (target / "src" / "bin").is_dir():
            dirs.append("src/bin/")
    if "python" in languages:
        checks += ["__main__.py", "main.py", "app.py"]
    if "node" in languages:
        checks += ["index.js", "src/index.js", "index.ts", "src/index.ts"]
        pkg = target / "package.json"
        if pkg.is_file():
            try:
                data = json.loads(pkg.read_text(encoding="utf-8", errors="ignore"))
                for key in ("main", "bin"):
                    val = data.get(key)
                    if isinstance(val, str):
                        checks.append(val)
                    elif isinstance(val, dict):
                        checks.extend(v for v in val.values() if isinstance(v, str))
            except (OSError, ValueError):
                pass
    if "go" in languages:
        checks += ["main.go"]
        if (target / "cmd").is_dir():
            dirs.append("cmd/")
    found = [c for c in checks if (target / c).is_file()]
    return sorted(set(found + dirs))


def detect_ci(target: Path) -> list:
    """Detect CI pipeline definitions (NOT .github/prompts or other content)."""
    ci: list = []
    workflows = target / ".github" / "workflows"
    if workflows.is_dir():
        ci += [
            f".github/workflows/{p.name}"
            for p in sorted(workflows.iterdir())
            if p.suffix in (".yml", ".yaml")
        ]
    for name in (".gitlab-ci.yml", "azure-pipelines.yml", "Jenkinsfile"):
        if (target / name).is_file():
            ci.append(name)
    if (target / ".circleci" / "config.yml").is_file():
        ci.append(".circleci/config.yml")
    return sorted(set(ci))


def detect_git(target: Path) -> dict:
    """Detect a git repo and whether any tags exist (read-only file inspect)."""
    gitpath = target / ".git"
    present = gitpath.exists()
    tags_present = False
    if gitpath.is_dir():
        tags_dir = gitpath / "refs" / "tags"
        if tags_dir.is_dir() and any(tags_dir.iterdir()):
            tags_present = True
        else:
            packed = gitpath / "packed-refs"
            if packed.is_file():
                try:
                    tags_present = "refs/tags/" in packed.read_text(errors="ignore")
                except OSError:
                    pass
    return {"present": present, "tags_present": tags_present}


def build_source_tiers(
    artifacts: dict,
    candidates: dict,
    build_info: dict,
    git_info: dict,
    feature_rows: int,
) -> dict:
    """Classify the project's information sources into the five-tier ladder."""
    specs = artifacts.get("specs", [])
    spec_count = sum(
        1
        for s in specs
        if s.get("requirements") or s.get("tasks") or s.get("plan")
    )
    spec_present = spec_count > 0

    memory_present = bool(
        artifacts.get("constitution")
        or artifacts.get("features_index")
        or artifacts.get("feature_files")
    )
    code_present = bool(build_info["manifests"] or build_info["build_files"])
    docs_present = bool(
        candidates.get("readme")
        or candidates.get("docs_dir")
        or candidates.get("documents")
    )
    return {
        "spec": {"present": spec_present, "spec_count": spec_count},
        "memory": {
            "present": memory_present,
            "constitution": bool(artifacts.get("constitution")),
            "features_populated": feature_rows > 0,
            "feature_files": artifacts.get("feature_files", 0),
        },
        "code_build": {
            "present": code_present,
            "languages": build_info["languages"],
            "manifests": build_info["manifests"],
        },
        "git": {
            "present": git_info["present"],
            "tags_present": git_info["tags_present"],
        },
        "external_docs": {
            "present": docs_present,
            "readme": candidates.get("readme"),
            "docs_dir": candidates.get("docs_dir"),
        },
    }


def pick_primary_tier(source_tiers: dict):
    """Return the highest present tier name, or None when the project is empty."""
    for tier in TIER_ORDER:
        if source_tiers.get(tier, {}).get("present"):
            return tier
    return None


def detect(target: Path) -> dict:
    specify = target / ".specify"
    artifacts: dict = {
        "constitution": None,
        "features_index": None,
        "feature_files": 0,
        "specs": [],
        "project_dir": [],
    }
    feature_rows = 0
    if specify.is_dir():
        memory = specify / "memory"
        constitution = memory / "constitution.md"
        if constitution.is_file():
            artifacts["constitution"] = str(constitution.relative_to(target))
        features_index = memory / "features.md"
        if features_index.is_file():
            artifacts["features_index"] = str(features_index.relative_to(target))
            feature_rows = count_feature_rows(features_index)
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

    build_info = detect_build(target)
    git_info = detect_git(target)
    source_tiers = build_source_tiers(
        artifacts, candidates, build_info, git_info, feature_rows
    )
    primary_tier = pick_primary_tier(source_tiers)

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
            ".specify/project/summary/" if speckit else "docs/project-summary/"
        ),
        # --- tier classification (additive; see references/source-tiers.md) ---
        "source_tiers": source_tiers,
        "primary_tier": primary_tier,
        "build": build_info,
        "features_index_populated": feature_rows > 0,
        "feature_row_count": feature_rows,
        "git": git_info,
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
