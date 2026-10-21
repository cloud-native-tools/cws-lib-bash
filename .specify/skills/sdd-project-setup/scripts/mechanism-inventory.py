#!/usr/bin/env python3
"""mechanism-inventory — spec-kit 安装机制的确定性盘点脚本（sdd-project-setup S1）.

只读扫描 <project>/.specify/，输出机制矩阵与状态分级；无副作用。
用法:
  mechanism-inventory.py --project <path> [--json]
退出码: 0 成功 / 2 参数或路径错误
分级判据见 references/setup-recipes.md「状态分级判据」。
"""
import argparse
import json
import os
import sys

COMPAT_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "QODER.md",
    ".github/copilot-instructions.md",
]


def check_compat(project: str) -> dict:
    """兼容链接核验：指向 .specify/instructions.md 且未断。"""
    links = {}
    for name in COMPAT_FILES:
        p = os.path.join(project, name)
        if os.path.islink(p):
            target = os.path.realpath(p)
            intact = os.path.exists(target)
            links[name] = {"type": "symlink", "target": target, "intact": intact}
        elif os.path.exists(p):
            links[name] = {"type": "file"}
        else:
            links[name] = {"type": "missing"}
    return links


def grade(matrix: dict, compat: dict) -> str:
    if not matrix["specify_dir"]:
        return "absent"
    if not matrix["const"] or (not matrix["skills"] and not matrix["feat"]):
        return "degraded"
    missing = sum(
        1 for k in ("const", "feat", "skills", "tmpl") if not matrix[k]
    )
    broken_link = any(
        v.get("type") == "symlink" and not v.get("intact") for v in compat.values()
    )
    if missing >= 2 or broken_link:
        return "partial"
    if missing == 0:
        return "complete"
    return "partial"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True, help="project root path")
    ap.add_argument("--json", action="store_true", help="JSON output")
    args = ap.parse_args()

    sp = os.path.join(args.project, ".specify")
    if not os.path.isdir(args.project):
        print(f"error: project not found: {args.project}", file=sys.stderr)
        return 2

    def exists(rel: str) -> bool:
        return os.path.exists(os.path.join(sp, rel))

    skills_dir = os.path.join(sp, "skills")
    skills_count = (
        len([d for d in os.listdir(skills_dir) if os.path.isdir(os.path.join(skills_dir, d))])
        if os.path.isdir(skills_dir)
        else 0
    )
    specs_dir = os.path.join(sp, "specs")
    specs_count = (
        len(os.listdir(specs_dir)) if os.path.isdir(specs_dir) else 0
    )

    src = {}
    source_path = os.path.join(sp, "source.json")
    if os.path.isfile(source_path):
        try:
            with open(source_path) as f:
                src = json.load(f)
        except (OSError, ValueError):
            src = {"parse_error": True}

    matrix = {
        "specify_dir": os.path.isdir(sp),
        "const": exists(".specify/memory/constitution.md"),
        "feat": exists(".specify/memory/features.md") and os.path.isdir(os.path.join(sp, ".specify/memory/features")),
        "gloss": exists(".specify/memory/glossary.md"),
        "fb": os.path.isdir(os.path.join(sp, ".specify/memory/feedback")),
        "reg": exists(".specify/memory/register.md"),
        "kb": os.path.isdir(os.path.join(sp, ".specify/memory/knowledge")),
        "session": os.path.isdir(os.path.join(sp, ".specify/memory/session")),
        "tools": exists(".specify/memory/tools.md"),
        "skills": skills_count > 0,
        "skills_count": skills_count,
        "tmpl": os.path.isdir(os.path.join(sp, "templates")),
        "specs": specs_count > 0,
        "specs_count": specs_count,
        "src": bool(src),
    }
    compat = check_compat(args.project)
    g = grade(matrix, compat)

    if args.json:
        print(json.dumps({"matrix": matrix, "compat": compat, "grade": g, "source": src}, ensure_ascii=False, indent=1))
        return 0

    dims = ["const", "feat", "gloss", "fb", "reg", "kb", "session", "tools", "skills", "tmpl", "src"]
    line = " ".join(f"{d}:{'ok' if matrix[d] else '-'}" for d in dims)
    print(f"grade={g} {line} skills={matrix['skills_count']} specs={matrix['specs_count']}")
    broken = [k for k, v in compat.items() if v.get("type") == "symlink" and not v.get("intact")]
    if broken:
        print(f"compat-broken: {','.join(broken)}")
    if src:
        v = src.get("version") or src.get("spec_kit_version") or "?"
        print(f"source: version={v} stamped={src.get('stamped_at', '?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
