#!/usr/bin/env python3
"""Scan framework sources for blocking user-confirmation gates.

Measurement & anti-backflow tool for Feature 046 (Confirmation Gate
Governance, requirement 044). Deterministic Program-First classification per
shared/guidelines/confirmation-gates.md: destructive keywords and
governance-kept path patterns -> keep_gate; everything else -> reversible /
auto_execute; doubtful cases default to destructive (存疑从严).

Contract: .specify/specs/044-reduce-confirmation-flows/contracts/gate-scanner-contract.md

Usage:
  python3 scripts/python/scan-confirmation-gates.py [--root <repo-root>]
      [--baseline <baseline.json>] [--json | --summary]

Exit codes: 0 = scan complete; 1 = argument/environment error;
2 = baseline provided and reversible gates still present in blocking form
(backflow violations).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Guard mirrored invocation: running the .specify/scripts/python copy must
# resolve the repo root, not .specify itself.
_HERE = Path(__file__).resolve()
REPO_ROOT = _HERE.parents[2]
if REPO_ROOT.name == ".specify":
    REPO_ROOT = REPO_ROOT.parent

SCAN_DIRS = ("templates/commands", "skills", "shared")
SCAN_ROOT_FILES = ("templates",)  # templates/*.md (non-directory entries)
SKIP_DIR_PARTS = {".specify", ".claude", ".qoder", ".github", ".opencode", "__pycache__", ".archive"}
SELF_REL = Path("shared/guidelines/confirmation-gates.md")
# Policy anchors that DEFINE the confirmation discipline cite gate patterns
# prescriptively — excluded from counting for the same reason as SELF_REL.
POLICY_DOCS = (
    Path("shared/patterns/reconcile-pattern.md"),
    Path("shared/patterns/interview-pattern.md"),
)

BLOCKING_PATTERNS = (
    r"等待用户确认",
    r"等待确认",
    r"用户确认后才",
    r"确认后才(?:执行|写入|落盘|启动|持久化)",
    r"显式用户确认|explicit user confirmation",
    r"wait for user confirmation",
    r"MUST NOT execute before confirmation",
    r"stop and confirm",
    r"after user confirmation|after confirmation",
    r"[Cc]onfirm before",
    r"[Pp]roceed[^\n]{0,40}yes/no",
    r"preview\s*(?:→|->)\s*confirm\s*(?:→|->)\s*execute",
    r"confirmation gate|确认门[禁控]",
    r"Confirm and persist|确认并落盘|合并确认",
    r"Execute on Confirmation",
    r"interactive confirmation",
    r"inviting the user to submit collected feedback",
)
BLOCKING_RE = re.compile("|".join(BLOCKING_PATTERNS))

DESTRUCTIVE_KEYWORDS = (
    "删除", "移动", "归档", "覆盖", "推送", "外部",
    "delete", "archive", "overwrite", "push", "clobber",
)
GOVERNANCE_PATH_PATTERNS = (
    r"interview", r"constitution-template", r"git-workflow",
    r"feedback\.md", r"docs\.md", r"session\.md", r"feature\.md",
    r"analyze\.md", r"tools\.md", r"operating-loops", r"project-cluster",
    r"gate\.yaml", r"CONFIRM",
)
GOVERNANCE_RE = re.compile("|".join(GOVERNANCE_PATH_PATTERNS))


def iter_source_files(root: Path):
    for d in SCAN_DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.md")):
            rel = path.relative_to(root)
            if any(part in SKIP_DIR_PARTS for part in rel.parts):
                continue
            yield path, rel
    for top in SCAN_ROOT_FILES:
        base = root / top
        if not base.is_dir():
            continue
        for path in sorted(base.glob("*.md")):
            yield path, path.relative_to(root)


def classify(rel_path: Path, line: str):
    rel_str = rel_path.as_posix()
    if GOVERNANCE_RE.search(rel_str):
        return "governance_kept", "keep_gate", "治理保留清单(路径命中)"
    lowered = line.lower()
    for kw in DESTRUCTIVE_KEYWORDS:
        if kw in lowered or kw.lower() in lowered:
            return "destructive", "keep_gate", f"破坏性清单关键词:{kw}"
    if BLOCKING_RE.search(line) and not any(c in line for c in ("执行", "写入", "落盘", "启动", "继续")):
        # no reversible-action context near the gate -> doubtful, be strict
        return "destructive", "keep_gate", "存疑从严(无可逆动作上下文)"
    return "reversible", "auto_execute", "两级判据:可逆动作自动执行"


def scan(root: Path):
    gates = []
    for path, rel in iter_source_files(root):
        if rel == SELF_REL or rel in POLICY_DOCS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not BLOCKING_RE.search(line):
                continue
            action_class, verdict, evidence = classify(rel, line)
            gates.append(
                {
                    "id": f"gate-{len(gates) + 1:03d}",
                    "file": rel.as_posix(),
                    "line": lineno,
                    "trigger": line.strip()[:120],
                    "action_class": action_class,
                    "verdict": verdict,
                    "evidence": evidence,
                }
            )
    by_class = {}
    by_verdict = {}
    for g in gates:
        by_class[g["action_class"]] = by_class.get(g["action_class"], 0) + 1
        by_verdict[g["verdict"]] = by_verdict.get(g["verdict"], 0) + 1
    return {
        "total": len(gates),
        "gates": gates,
        "by_class": by_class,
        "by_verdict": by_verdict,
        "baseline_delta": None,
        "violations": [],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=str(REPO_ROOT))
    parser.add_argument("--baseline", default=None)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--json", action="store_true")
    group.add_argument("--summary", action="store_true")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"error: root not a directory: {root}", file=sys.stderr)
        return 1

    report = scan(root)
    violations = [g for g in report["gates"] if g["verdict"] == "auto_execute"]

    if args.baseline:
        baseline_path = Path(args.baseline)
        if not baseline_path.is_file():
            print(f"error: baseline not found: {baseline_path}", file=sys.stderr)
            return 1
        try:
            baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"error: baseline unreadable: {exc}", file=sys.stderr)
            return 1
        base_by_class = baseline.get("by_class", {})
        delta_class = {
            k: report["by_class"].get(k, 0) - base_by_class.get(k, 0)
            for k in sorted(set(report["by_class"]) | set(base_by_class))
        }
        report["baseline_delta"] = {
            "total": report["total"] - baseline.get("total", 0),
            "by_class": delta_class,
        }
        report["violations"] = violations

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"blocking confirmation gates: {report['total']}")
        for k in sorted(report["by_class"]):
            print(f"  {k}: {report['by_class'][k]}")
        if report["baseline_delta"] is not None:
            print(f"baseline delta total: {report['baseline_delta']['total']:+d}")
        print(f"violations (reversible gates still blocking): {len(report['violations'])}")

    if args.baseline and violations:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
