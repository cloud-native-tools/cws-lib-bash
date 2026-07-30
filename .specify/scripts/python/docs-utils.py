#!/usr/bin/env python3
"""docs-utils.py — deterministic engine for the /speckit.docs command.

Stdlib-only. Prints exactly one JSON object to stdout per invocation.
Contract: .specify/specs/033-docs-command/contracts/docs-utils-cli.md
Shared literals (requirements.md Shared Strings): STR-001 "draft",
STR-002 "expired", STR-003 "archived", STR-004 "expires".
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

STATUS_DRAFT = "draft"        # STR-001
STATUS_EXPIRED = "expired"    # STR-002
STATUS_ARCHIVED = "archived"  # STR-003
KEY_EXPIRES = "expires"       # STR-004

REQUIRED_KEYS = ("title", "created", KEY_EXPIRES, "status")
DEFAULT_TTL_DAYS = 60
ROOT_ENTRY_MAX_LINES = 60

# Principle X Reserved Filenames: name -> (fixed semantics, registered location).
# Reserved names may appear ONLY at their registered location; directory indexes
# elsewhere use index.md.
REGISTRY = {
    "README.md": "root entry point indexing all of docs/",
    "ARCHITECTURE.md": "one-page summary of docs/concepts/ + docs/decisions/",
    "CONTRIBUTING.md": "contribution entry summarizing docs/contribute/",
    "CHANGELOG.md": "self-contained timeline",
}
INDEX_NAME = "index.md"
# Tool/ecosystem-mandated ALL-CAPS names (constitution Principle X) that are
# legitimate outside the registry.
ALLOWED_SPECIAL = {
    "LICENSE.md", "NOTICE.md", "SECURITY.md", "CODEOWNERS.md",
    "CODE_OF_CONDUCT.md", "AGENTS.md", "AGENT.md", "CLAUDE.md", "QODER.md",
    "QWEN.md", "GEMINI.md", "IFLOW.md", "HERMES.md", "OPENCODE.md",
}

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
ADR_RE = re.compile(r"^(\d{4})-.+\.md$")


def notes_dir(root: Path) -> Path:
    return root / "docs" / "notes"


def parse_frontmatter(path: Path) -> dict | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    fm: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fm
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"').strip("'")
    return None


def parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def iter_notes(root: Path):
    ndir = notes_dir(root)
    if not ndir.is_dir():
        return
    for path in sorted(ndir.glob("*.md")):
        if path.name in ("README.md", INDEX_NAME):
            continue
        yield path


def rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def classify_notes(root: Path, today: date) -> dict:
    groups: dict[str, list] = {"drafts": [], "expireds": [], "archiveds": [], "invalid": []}
    for path in iter_notes(root):
        fm = parse_frontmatter(path)
        missing = [k for k in REQUIRED_KEYS if not fm or not fm.get(k)]
        if fm is None or missing:
            created = parse_date((fm or {}).get("created", "")) or today
            groups["invalid"].append({
                "path": rel(root, path),
                "missing": missing if fm is not None else list(REQUIRED_KEYS),
                "suggestion": {
                    "status": STATUS_DRAFT,
                    KEY_EXPIRES: (created + timedelta(days=DEFAULT_TTL_DAYS)).isoformat(),
                },
            })
            continue
        entry = {"path": rel(root, path), "title": fm["title"], KEY_EXPIRES: fm[KEY_EXPIRES]}
        status = fm["status"]
        expires = parse_date(fm[KEY_EXPIRES])
        if status == STATUS_ARCHIVED:
            entry["target"] = fm.get("target", "")
            groups["archiveds"].append(entry)
        elif status == STATUS_EXPIRED:
            groups["expireds"].append(entry)
        elif status == STATUS_DRAFT:
            if expires is not None and expires < today:
                groups["expireds"].append(entry)
            else:
                groups["drafts"].append(entry)
        else:
            groups["invalid"].append({
                "path": rel(root, path),
                "missing": [],
                "detail": f"unknown status: {status}",
                "suggestion": {"status": STATUS_DRAFT, KEY_EXPIRES: fm[KEY_EXPIRES]},
            })
    return groups


def cmd_scan(root: Path) -> dict:
    return classify_notes(root, date.today())


def cmd_expire(root: Path) -> dict:
    today = date.today()
    marked = []
    for path in iter_notes(root):
        fm = parse_frontmatter(path)
        if not fm or any(not fm.get(k) for k in REQUIRED_KEYS):
            continue
        expires = parse_date(fm[KEY_EXPIRES])
        if fm["status"] == STATUS_DRAFT and expires is not None and expires < today:
            text = path.read_text(encoding="utf-8")
            path.write_text(
                text.replace(f"status: {STATUS_DRAFT}", f"status: {STATUS_EXPIRED}", 1),
                encoding="utf-8",
            )
            marked.append(rel(root, path))
    return {"marked": marked, "count": len(marked)}


def cmd_clean(root: Path, yes: bool) -> dict:
    candidates = []
    for path in iter_notes(root):
        fm = parse_frontmatter(path)
        if fm and fm.get("status") == STATUS_EXPIRED:
            candidates.append(path)
    if not yes:
        return {"dry_run": True, "candidates": [rel(root, p) for p in candidates], "deleted": []}
    deleted = []
    for path in candidates:
        path.unlink()
        deleted.append(rel(root, path))
    return {"dry_run": False, "candidates": [], "deleted": deleted}


def cmd_archive_check(root: Path) -> dict:
    ok, broken = [], []
    for path in iter_notes(root):
        fm = parse_frontmatter(path)
        if not fm or fm.get("status") != STATUS_ARCHIVED:
            continue
        target = fm.get("target", "")
        entry = {"path": rel(root, path), "target": target}
        if not target:
            entry["reason"] = "no-target"
            broken.append(entry)
        elif not (root / target).is_file():
            entry["reason"] = "missing-target"
            broken.append(entry)
        else:
            ok.append(entry)
    return {"ok": ok, "broken": broken}


def cmd_stats(root: Path) -> dict:
    groups = classify_notes(root, date.today())
    total = sum(len(groups[k]) for k in ("drafts", "expireds", "archiveds", "invalid"))
    return {
        "total": total,
        "drafts": len(groups["drafts"]),
        "expireds": len(groups["expireds"]),
        "archiveds": len(groups["archiveds"]),
        "invalid": len(groups["invalid"]),
    }


def check_links(root: Path, files: list[Path], violations: list) -> None:
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        # links quoted inside fenced code blocks or inline code are examples, not references
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        text = re.sub(r"`[^`\n]*`", "", text)
        for target in LINK_RE.findall(text):
            target = target.split("#", 1)[0]
            if not target or "://" in target or target.startswith(("mailto:", "/", "#")):
                continue
            if not (path.parent / target).exists():
                violations.append({
                    "kind": "broken-link",
                    "path": rel(root, path),
                    "detail": target,
                })


def cmd_validate(root: Path) -> dict:
    violations: list[dict] = []
    lower_registry = {name.lower(): name for name in REGISTRY}
    for path in sorted(root.glob("*.md")):
        name = path.name
        if name in REGISTRY:
            lines = len(path.read_text(encoding="utf-8").splitlines())
            if lines > ROOT_ENTRY_MAX_LINES:
                violations.append({
                    "kind": "root-entry-oversize", "path": name,
                    "detail": f"{lines} lines > {ROOT_ENTRY_MAX_LINES} (one-screen rule)",
                })
            continue
        if name.lower() in lower_registry:
            violations.append({
                "kind": "reserved-name-case", "path": name,
                "detail": f"rename to {lower_registry[name.lower()]}",
            })
        elif name not in ALLOWED_SPECIAL and re.sub(r"[^A-Za-z]", "", path.stem).isupper() \
                and len(re.sub(r"[^A-Za-z]", "", path.stem)) >= 2:
            violations.append({
                "kind": "reserved-name-misuse", "path": name,
                "detail": "ALL-CAPS names are reserved; use kebab-case.md or register the name",
            })
    docs = root / "docs"
    doc_files = sorted(docs.rglob("*.md")) if docs.is_dir() else []
    # Reserved Filenames strict blocking: reserved names only at their registered
    # location (project root); directory indexes elsewhere use index.md.
    for path in doc_files:
        name = path.name
        if name in REGISTRY:
            alt = INDEX_NAME if name == "README.md" else "a lowercase kebab-case name"
            violations.append({
                "kind": "reserved-name-misplaced", "path": rel(root, path),
                "detail": f"reserved filename outside its registered location (root); use {alt}",
            })
        elif re.sub(r"[^A-Za-z]", "", path.stem).isupper() \
                and len(re.sub(r"[^A-Za-z]", "", path.stem)) >= 2:
            violations.append({
                "kind": "reserved-name-misuse", "path": rel(root, path),
                "detail": "ALL-CAPS names are reserved identifiers; use kebab-case.md",
            })
    # notes zone is temporary (no stability guarantee): exempt from link checking
    doc_files = [f for f in doc_files if notes_dir(root) not in f.parents]
    root_entries = [root / n for n in REGISTRY if (root / n).is_file()]
    check_links(root, root_entries + doc_files, violations)
    decisions = docs / "decisions"
    if decisions.is_dir():
        numbers = sorted(
            int(m.group(1)) for f in decisions.glob("*.md")
            if (m := ADR_RE.match(f.name))
        )
        if numbers:
            expected = list(range(numbers[0], numbers[0] + len(numbers)))
            if numbers != expected:
                violations.append({
                    "kind": "adr-gap", "path": "docs/decisions/",
                    "detail": f"non-continuous numbering: {numbers}",
                })
    for entry in classify_notes(root, date.today())["invalid"]:
        violations.append({
            "kind": "note-frontmatter", "path": entry["path"],
            "detail": "missing: " + ",".join(entry.get("missing", [])),
        })
    return {"violations": violations}


def broken_links(root: Path) -> list:
    return [v for v in cmd_validate(root)["violations"] if v["kind"] == "broken-link"]


def cmd_fix_links(root: Path, moves_file: str | None, apply: bool) -> dict:
    moves: dict[str, str] = {}
    if moves_file:
        moves = json.loads(Path(moves_file).read_text(encoding="utf-8"))

    def move_map(p: str) -> str | None:
        for old, new in moves.items():
            if old.endswith("/") and p.startswith(old):
                return new + p[len(old):]
            if p == old:
                return new
        return None

    def resolve(fpath: Path, target: str) -> Path | None:
        if (root / target).exists():
            return root / target
        mm = move_map(target)
        if mm and (root / mm).exists():
            return root / mm
        for extra in ("", "../", "../../"):
            norm = os.path.normpath(os.path.join(str(fpath.parent), extra + target))
            try:
                rn = str(Path(norm).resolve().relative_to(root))
            except ValueError:
                continue
            if (root / rn).exists():
                return root / rn
            mm2 = move_map(rn)
            if mm2 and (root / mm2).exists():
                return root / mm2
        return None

    fixed, unresolved = [], []
    for rounds in range(3):
        changed = False
        for v in broken_links(root):
            f = root / v["path"]
            target = v["detail"]
            cand = resolve(f, target)
            if cand is None:
                unresolved.append({"path": v["path"], "target": target})
                continue
            newrel = os.path.relpath(cand, f.parent)
            if newrel == target:
                continue
            if apply:
                text = f.read_text(encoding="utf-8")
                pat = re.compile(r"\(" + re.escape(target) + r"(#[^)]*)?\)")
                new_text = pat.sub(lambda m: f"({newrel}{m.group(1) or ''})", text)
                if new_text != text:
                    f.write_text(new_text, encoding="utf-8")
                    changed = True
            fixed.append({"path": v["path"], "old": target, "new": newrel})
        if not (apply and changed):
            break
    # dedup preserving order
    seen, uniq = set(), []
    for item in fixed:
        key = (item["path"], item["old"], item["new"])
        if key not in seen:
            seen.add(key)
            uniq.append(item)
    return {"dry_run": not apply, "fixed": uniq, "unresolved": unresolved}


def cmd_audit(root: Path, scope: str, summary: str, items_file: str | None) -> dict:
    audit_dir = root / ".specify" / "docs" / "audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = audit_dir / f"{ts}-docs-audit.md"
    seq = 1
    while path.exists():
        seq += 1
        path = audit_dir / f"{ts}-docs-audit-{seq}.md"
    items = []
    if items_file:
        items = json.loads(Path(items_file).read_text(encoding="utf-8"))
    lines = [
        "# Docs Reconcile Audit",
        "",
        f"- timestamp: {ts}",
        f"- scope: {scope}",
        f"- summary: {summary}",
        "",
    ]
    if items:
        lines.append("| action | source | target | result |")
        lines.append("|--------|--------|--------|--------|")
        for it in items:
            lines.append(
                f"| {it.get('action', '')} | {it.get('source', '')} "
                f"| {it.get('target', '')} | {it.get('result', '')} |"
            )
    else:
        lines.append("(no convergence items)")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"path": rel(root, path), "written": True}


def main() -> int:
    parser = argparse.ArgumentParser(description="docs space deterministic engine")
    parser.add_argument(
        "--action", required=True,
        choices=["scan", "expire", "clean", "archive-check", "stats", "validate",
                 "fix-links", "audit"],
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--yes", action="store_true", help="confirm deletion for clean")
    parser.add_argument("--apply", action="store_true", help="apply fix-links rewrites (default dry-run)")
    parser.add_argument("--moves", default=None, help="JSON file mapping old path prefixes to new (fix-links)")
    parser.add_argument("--scope", default="unspecified", help="audit scope label")
    parser.add_argument("--summary", default="", help="audit summary line")
    parser.add_argument("--items-file", default=None, help="JSON file with audit items")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if args.action == "scan":
        out = cmd_scan(root)
    elif args.action == "expire":
        out = cmd_expire(root)
    elif args.action == "clean":
        out = cmd_clean(root, args.yes)
    elif args.action == "archive-check":
        out = cmd_archive_check(root)
    elif args.action == "stats":
        out = cmd_stats(root)
    elif args.action == "validate":
        out = cmd_validate(root)
    elif args.action == "fix-links":
        out = cmd_fix_links(root, args.moves, args.apply)
    else:
        out = cmd_audit(root, args.scope, args.summary, args.items_file)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
