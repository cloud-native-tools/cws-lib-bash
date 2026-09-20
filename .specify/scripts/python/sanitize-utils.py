#!/usr/bin/env python3
"""sanitize-utils.py — framework material hygiene engine (Feature 047, requirement 045).

Deterministic correctness checks (dead-reference / index-consistency /
broken-symlink / mirror-drift), evidence-pack assembly for agent-side semantic
staleness judgment, a cumulative findings ledger with lifecycle states, and a
confirmation-gated cleanup apply. Contracts live at
.specify/specs/045-sanitize-command/contracts/sanitize-*.md — this engine is
their executable form. stdlib-only, mirroring the feedback/evidence utils
discipline.

Scope red lines (FR-001/FR-006): check stages never modify any material; apply
executes only delete/archive against material-root-whitelisted targets and
refuses everything else with exit 2.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CATEGORIES = [
    "stale-residue", "redundant", "dead-reference",
    "index-inconsistency", "broken-symlink", "mirror-drift",
]
SEVERITIES = ["high", "medium", "low"]
DISPOSITIONS = ["delete", "archive", "repair", "delegate", "dismiss"]
STATES = ["pending", "resolved", "dismissed"]
DETECTIONS = ["programmatic", "semantic"]
REVERSIBILITY = {
    "delete": "irreversible", "archive": "irreversible",
    "repair": "reversible", "delegate": "reversible", "dismiss": "reversible",
}
DEFAULT_SEVERITY = {
    "stale-residue": "high", "redundant": "low", "dead-reference": "medium",
    "index-inconsistency": "medium", "broken-symlink": "medium", "mirror-drift": "medium",
}
DETERMINISTIC_CATEGORIES = {"dead-reference", "index-inconsistency", "broken-symlink", "mirror-drift"}
SEMANTIC_CATEGORIES = {"stale-residue", "redundant"}

STORE_REL = Path(".specify") / "memory" / "sanitize" / "findings.json"
PLAN_REL = Path(".specify") / "memory" / "sanitize" / "cleanup-plan.json"
ARCHIVE_REL = Path(".specify") / "archive"

# Material roots (data-model §4): runtime-probed; missing roots are empty sets,
# never errors. The engine's own store is exempt from scanning (no recursion).
MATERIAL_ROOTS = [
    ("memory-todo", ".specify/memory/todo"),
    ("memory-draft", ".specify/memory/draft"),
    ("memory-indexes", ".specify/memory"),
    ("specs", ".specify/specs"),
    ("archive-spec", ".specify/archive/spec"),
    ("history", ".specify/history"),
    ("mirror-skills", ".specify/skills"),
    ("mirror-agents", ".specify/agents"),
    ("mirror-shared", ".specify/shared"),
    ("mirror-scripts", ".specify/scripts"),
    ("docs", "docs"),
]
MATERIAL_TARGET_PREFIXES = tuple(sorted({path for _, path in MATERIAL_ROOTS}))
FORBIDDEN_TARGET_PREFIXES = ("src/", "tests/", "node_modules/", ".git/")
SELF_EXEMPT_PREFIX = ".specify/memory/sanitize"

COMPAT_SYMLINKS = [
    "CLAUDE.md", "QODER.md", "AGENTS.md",
    ".github/copilot-instructions.md", ".github/skills",
]
# A compat link is EXPECTED only when its owning tool surface exists; a client
# workspace initialized for one CLI must not be flagged for another CLI's link.
COMPAT_SYMLINK_EXPECTATIONS = {
    "CLAUDE.md": ".claude",
    "QODER.md": ".qoder",
    "AGENTS.md": ".specify/instructions.md",
    ".github/copilot-instructions.md": ".github",
    ".github/skills": ".github",
}

DELEGATE_COMMAND_RE = re.compile(r"speckit\.[a-z][a-z-]*|sync-mirrors|regen-command-copies")


class CliError(Exception):
    """Bad invocation / unreadable input — exit 1."""


class VerificationError(Exception):
    """Schema or gate violation — exit 2, zero side effects."""

    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or []


# --------------------------------------------------------------------------
# store primitives
# --------------------------------------------------------------------------

def stable_id(category: str, target: str) -> str:
    return hashlib.sha1(f"{category}|{target}".encode()).hexdigest()[:12]


def _utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def store_path(root: Path) -> Path:
    return root / STORE_REL


def plan_path(root: Path) -> Path:
    return root / PLAN_REL


def load_store(root: Path):
    """Return (store, notes). Missing -> empty; corrupt -> rebuilt empty + note."""
    path = store_path(root)
    if not path.is_file():
        return {"version": 1, "updated": None, "findings": []}, []
    try:
        store = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(store, dict) or not isinstance(store.get("findings"), list):
            raise ValueError("store shape invalid")
        store.setdefault("version", 1)
        return store, []
    except (ValueError, OSError):
        return {"version": 1, "updated": None, "findings": []}, ["findings store corrupt — rebuilt empty"]


def save_store(root: Path, store: dict) -> None:
    path = store_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    store["updated"] = _utcnow()
    part = path.with_suffix(".json.part")
    part.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(part), str(path))


# --------------------------------------------------------------------------
# schema validation (contracts/sanitize-findings.md C-1..C-7)
# --------------------------------------------------------------------------

REQUIRED_FINDING_KEYS = [
    "id", "category", "target", "severity", "summary", "evidenceRefs",
    "detection", "disposition", "reversibility", "state",
]


def _has_prefix(target: str, prefixes) -> bool:
    return any(target == p or target.startswith(p + "/") for p in prefixes)


def is_material_target(root: Path, target: str) -> bool:
    if _has_prefix(target, FORBIDDEN_TARGET_PREFIXES):
        return False
    return _has_prefix(target, MATERIAL_TARGET_PREFIXES)


def validate_finding(finding: dict, root: Path) -> list:
    errors = []
    for key in REQUIRED_FINDING_KEYS:
        if key not in finding:
            errors.append(f"missing key: {key}")
    if errors:
        return errors
    if finding["id"] != stable_id(finding["category"], finding["target"]):
        errors.append("id must equal stable_id(category|target)")
    if finding["category"] not in CATEGORIES:
        errors.append(f"category must be one of {CATEGORIES}")
    if finding["severity"] not in SEVERITIES:
        errors.append(f"severity must be one of {SEVERITIES}")
    if finding["detection"] not in DETECTIONS:
        errors.append(f"detection must be one of {DETECTIONS}")
    if finding["disposition"] not in DISPOSITIONS:
        errors.append(f"disposition must be one of {DISPOSITIONS}")
    if finding["state"] != "pending":
        errors.append("new findings must enter the store as pending")
    if finding["reversibility"] != REVERSIBILITY.get(finding["disposition"]):
        errors.append(f"reversibility must be {REVERSIBILITY.get(finding['disposition'])} for disposition={finding['disposition']}")
    refs = finding.get("evidenceRefs") or []
    if finding["category"] in SEMANTIC_CATEGORIES:
        if not any(r.get("kind") in ("commit", "path") for r in refs):
            errors.append("semantic findings need at least one commit/path evidence ref")
    if finding["disposition"] == "delegate" and not DELEGATE_COMMAND_RE.search(finding["summary"] or ""):
        errors.append("disposition=delegate requires the target command in summary")
    if not is_material_target(root, finding["target"]):
        errors.append(f"target outside material roots: {finding['target']}")
    return errors


# --------------------------------------------------------------------------
# merge semantics (contracts/sanitize-findings.md C-8..C-13)
# --------------------------------------------------------------------------

def merge_findings(store: dict, findings: list, run_ts: str, scanned_categories: set) -> dict:
    stats = {"added": 0, "refreshed": 0, "reopened": 0, "auto_resolved": 0, "kept": 0}
    by_id = {f["id"]: f for f in store["findings"]}
    incoming_ids = set()
    for f in findings:
        fid = f["id"]
        incoming_ids.add(fid)
        existing = by_id.get(fid)
        if existing is None:
            entry = dict(f)
            entry["state"] = "pending"
            entry["firstSeenRun"] = run_ts
            entry["lastSeenRun"] = run_ts
            entry["resolvedAt"] = None
            entry["notes"] = []
            store["findings"].append(entry)
            by_id[fid] = entry
            stats["added"] += 1
        elif existing["state"] == "pending":
            for key in ("severity", "summary", "evidenceRefs", "disposition", "reversibility"):
                if key in f:
                    existing[key] = f[key]
            existing["lastSeenRun"] = run_ts
            stats["refreshed"] += 1
        elif existing["state"] == "resolved":
            existing["state"] = "pending"
            existing["resolvedAt"] = None
            existing["lastSeenRun"] = run_ts
            existing.setdefault("notes", []).append(f"reopened {run_ts} (re-detected)")
            stats["reopened"] += 1
        else:  # dismissed — user verdict stays authoritative
            existing["lastSeenRun"] = run_ts
            stats["kept"] += 1
    for f in store["findings"]:
        if f["state"] == "pending" and f["category"] in scanned_categories and f["id"] not in incoming_ids:
            f["state"] = "resolved"
            f["resolvedAt"] = run_ts
            f.setdefault("notes", []).append(f"not re-detected this run ({run_ts})")
            stats["auto_resolved"] += 1
    return stats


def store_digest(store: dict) -> dict:
    findings = store.get("findings", [])
    by_state, by_category, by_severity = {}, {}, {}
    for f in findings:
        by_state[f["state"]] = by_state.get(f["state"], 0) + 1
        by_category[f["category"]] = by_category.get(f["category"], 0) + 1
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
    return {
        "total": len(findings),
        "byState": by_state, "byCategory": by_category, "bySeverity": by_severity,
        "pendingTargets": [f["target"] for f in findings if f["state"] == "pending"],
    }


# --------------------------------------------------------------------------
# material roots
# --------------------------------------------------------------------------

def probe_roots(root: Path) -> list:
    return [
        {"kind": kind, "path": rel, "exists": (root / rel).exists()}
        for kind, rel in MATERIAL_ROOTS
    ]


def _iter_root_files(root: Path, kinds: set):
    """Yield repo-relative material file paths under the given root kinds."""
    for kind, rel in MATERIAL_ROOTS:
        if kind not in kinds:
            continue
        base = root / rel
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in (".md", ".json"):
                relpath = path.relative_to(root).as_posix()
                if relpath.startswith(SELF_EXEMPT_PREFIX):
                    continue
                yield relpath


# --------------------------------------------------------------------------
# deterministic checkers (contracts/sanitize-detection-rules.md)
# --------------------------------------------------------------------------

DEFAULT_DISPOSITION = {
    "stale-residue": "delete", "redundant": "archive", "dead-reference": "repair",
    "index-inconsistency": "repair", "broken-symlink": "delegate", "mirror-drift": "delegate",
}


def _finding(category: str, target: str, summary: str, evidence=None,
             disposition=None, severity=None) -> dict:
    disposition = disposition or DEFAULT_DISPOSITION[category]
    return {
        "id": stable_id(category, target),
        "category": category,
        "target": target,
        "severity": severity or DEFAULT_SEVERITY[category],
        "summary": summary,
        "evidenceRefs": evidence or [{"kind": "path", "ref": target.split("#", 1)[0]}],
        "detection": "programmatic",
        "disposition": disposition,
        "reversibility": REVERSIBILITY[disposition],
        "state": "pending",
    }


SPECS_ARCHIVE_PREFIX = ".specify/specs/.archive/"


def _iter_reference_materials(root: Path):
    """LIVE materials whose prose references are checked by the sanitize
    grammar. Frozen history (`.specify/archive/**`, `.specify/history/**`) is
    exempt — its references describe past states and are dead by design.
    Machine-generated stores (feedback/evidence/session/knowledge) are data,
    not prose — excluded. Docs tree is covered solely by the docs-utils lane."""
    candidates = [
        root / ".specify" / "memory" / "todo",
        root / ".specify" / "memory" / "draft",
    ]
    for base in candidates:
        if base.is_dir():
            for path in sorted(base.rglob("*.md")):
                yield path.relative_to(root).as_posix()
    specs = root / ".specify" / "specs"
    if specs.is_dir():
        for path in sorted(specs.rglob("*.md")):
            relpath = path.relative_to(root).as_posix()
            if relpath.startswith(SPECS_ARCHIVE_PREFIX):
                continue
            yield relpath
    for path in sorted((root / ".specify" / "memory").glob("*.md")):
        yield path.relative_to(root).as_posix()


FENCE_RE = re.compile(r"```.*?```", re.S)
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
CMD_RE = re.compile(r"speckit\.([a-z][a-z-]*)")
SKILL_REF_RE = re.compile(r"skills/([a-z0-9][a-z0-9-]*)")
PLACEHOLDER_RE = re.compile(r"[<>{}\[\]]")


def _strip_fences(text: str) -> str:
    return FENCE_RE.sub("", text)


def _link_target_ok(target: str) -> bool:
    if "://" in target or target.startswith(("mailto:", "#", "/", "~")):
        return False
    if PLACEHOLDER_RE.search(target):
        return False
    return bool(target)


def _path_target_ok(target: str) -> bool:
    return not PLACEHOLDER_RE.search(target)


def check_dead_references(root: Path) -> list:
    findings = []
    reported = {}  # (material, refkey) -> finding

    def report(material, refkey, summary):
        key = (material, refkey)
        if key in reported:
            return
        finding = _finding("dead-reference", f"{material}#{refkey}", summary)
        reported[key] = finding
        findings.append(finding)

    for relpath in _iter_reference_materials(root):
        if relpath.startswith(SELF_EXEMPT_PREFIX):
            continue
        try:
            text = (root / relpath).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        body = _strip_fences(text)
        # 1) markdown links (resolved against the file dir, then repo root)
        for target in LINK_RE.findall(body):
            target = target.strip("<>")
            if not _link_target_ok(target):
                continue
            rel_file = root / relpath
            resolved = (rel_file.parent / target)
            try:
                resolved = Path(os.path.normpath(str(resolved)))
            except ValueError:
                continue
            repo_root_resolved = root / target if _has_prefix(
                target, MATERIAL_TARGET_PREFIXES + ("scripts/", "shared/", "templates/",
                                                    "skills/", "agents/", "src/", "tests/")) else None
            if resolved.exists() or (repo_root_resolved and repo_root_resolved.exists()):
                continue
            report(relpath, target, f"引用了不存在的链接目标 {target}")
        # 2) repo-prefixed paths (inline backticks included)
        for path in REPO_PATH_RE.findall(body):
            if not _path_target_ok(path):
                continue
            refkey = path.rstrip("/")
            if not (root / refkey).exists():
                report(relpath, refkey, f"引用了不存在的路径 {refkey}")
        # 3) command refs
        for name in CMD_RE.findall(body):
            if not (root / "templates" / "commands" / f"{name}.md").exists():
                report(relpath, f"speckit.{name}", f"引用了不存在的命令 speckit.{name}")
        # 4) skill refs
        for name in SKILL_REF_RE.findall(body):
            if not (root / "skills" / name).is_dir():
                report(relpath, f"skills/{name}", f"引用了不存在的技能目录 skills/{name}")

    # docs tree + root registry files: reuse docs-utils (Tool Reuse, C-4)
    docs_violations = check_docs_lane(root)
    if docs_violations:
        for violation in docs_violations:
            path = violation.get("path", "")
            detail = violation.get("detail", "")
            findings.append(_finding(
                "dead-reference", f"{path}#{detail}",
                f"docs 断链(docs-utils):引用了不存在的 {detail}",
                evidence=[{"kind": "output", "ref": "docs-utils:broken-links"}]))
    return findings


FEATURES_ROW_RE = re.compile(r"^\| (\d{3}) \|")
FEEDBACK_ENTRY_RE = re.compile(r"^\d{8}T\d{6}Z-")


def check_index_consistency(root: Path) -> list:
    findings = []
    memory = root / ".specify" / "memory"

    # features family (C-6)
    features_md = memory / "features.md"
    if features_md.is_file():
        rows = {}
        for line in features_md.read_text(encoding="utf-8", errors="replace").splitlines():
            match = FEATURES_ROW_RE.match(line)
            if not match:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) > 5:
                rows[match.group(1)] = parts[5]
        for fid, detail in rows.items():
            if detail and detail != "-" and not (root / detail).is_file():
                findings.append(_finding(
                    "index-inconsistency", f"{features_md.relative_to(root).as_posix()}#missing-{fid}",
                    f"features 索引行 {fid} 指向不存在的 {detail}"))
        features_dir = memory / "features"
        if features_dir.is_dir():
            for path in sorted(features_dir.glob("*.md")):
                fid = path.stem
                if fid not in rows:
                    findings.append(_finding(
                        "index-inconsistency", path.relative_to(root).as_posix(),
                        f"features/{fid}.md 存在而索引无对应行(反向缺项)"))

    # feedback + evidence families (C-7/C-8)
    for store_name, key_field in (("feedback", "file"), ("evidence", "runId")):
        index_path = memory / store_name / "index.json"
        if not index_path.is_file():
            continue
        rel_index = index_path.relative_to(root).as_posix()
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
            entries = index.get("entries", [])
        except (ValueError, OSError):
            findings.append(_finding(
                "index-inconsistency", rel_index,
                f"{store_name} 索引不可解析(单条发现,不逐条展开)"))
            continue
        indexed = set()
        for entry in entries:
            value = entry.get(key_field) if isinstance(entry, dict) else None
            if not value:
                continue
            indexed.add(value)
            if key_field == "file":
                target_path = memory / store_name / value
                if not target_path.is_file():
                    findings.append(_finding(
                        "index-inconsistency", f"{rel_index}#{value}",
                        f"feedback 索引条目 {entry.get('id', value)} 指向不存在的 {value}"))
            else:
                if not (memory / store_name / value).is_dir():
                    findings.append(_finding(
                        "index-inconsistency", f"{rel_index}#{value}",
                        f"evidence 索引条目 {value} 指向不存在的运行目录"))
        store_dir = memory / store_name
        if key_field == "file":
            # only timestamp-named entry files count on disk; bookkeeping files
            # (cleanup-log / consume-log / migration-log / probe-map / ...) are
            # store scaffolding, not feedback entries
            for path in sorted(store_dir.glob("*.md")):
                if path.name not in indexed and FEEDBACK_ENTRY_RE.match(path.name):
                    findings.append(_finding(
                        "index-inconsistency", path.relative_to(root).as_posix(),
                        f"feedback 条目文件 {path.name} 存在而索引无登记(反向缺项)"))
        else:
            for path in sorted(store_dir.glob("ev-*")):
                if path.is_dir() and path.name not in indexed:
                    findings.append(_finding(
                        "index-inconsistency", path.relative_to(root).as_posix(),
                        f"evidence 运行目录 {path.name} 存在而索引无登记(反向缺项)"))
    return findings


def check_broken_symlinks(root: Path) -> list:
    findings = []
    for name in COMPAT_SYMLINKS:
        link = root / name
        expected = (root / COMPAT_SYMLINK_EXPECTATIONS[name]).exists()
        if link.is_symlink():
            if not link.exists():  # symlink whose target is gone
                findings.append(_finding(
                    "broken-symlink", name,
                    f"兼容性符号链接 {name} 目标缺失(断链)——经 /speckit.instructions 再生成修复"))
        elif link.exists():
            findings.append(_finding(
                "broken-symlink", name,
                f"{name} 已被普通文件替换(形态漂移)——经 /speckit.instructions 再生成修复"))
        elif expected:
            findings.append(_finding(
                "broken-symlink", name,
                f"兼容性符号链接 {name} 缺失——经 /speckit.instructions 再生成修复"))
    return findings


def run_sync_mirrors_check(root: Path):
    """Run the sibling sync-mirrors.py --check. sync-mirrors resolves its repo
    from its own script location, so the lane only runs when the workspace IS
    that repo (framework dogfood or an installed client copy); against any
    other workspace it would inspect the wrong tree — skip instead. Returns
    (returncode, stdout); stdout is parsed for drift lines regardless of rc."""
    script = Path(__file__).with_name("sync-mirrors.py")
    try:
        script_repo = script.resolve().parents[2]
    except OSError:
        return 0, ""
    if root.resolve() != script_repo:
        return 0, ""
    proc = subprocess.run(
        [sys.executable, str(script), "--check"],
        cwd=str(root), capture_output=True, text=True, timeout=180)
    return proc.returncode, proc.stdout


DRIFT_LINE_RE = re.compile(r"^(MISS|DIFF|ORPHAN)\s+(\S+)")


def parse_mirror_drift_lines(text: str) -> list:
    items = []
    for line in text.splitlines():
        match = DRIFT_LINE_RE.match(line.strip())
        if match:
            items.append((match.group(2), match.group(1)))
    return items


# Orphan-dir detection is scoped to the skills pair: `agents/` mirrors only
# *.agent.md files while `.specify/agents/` additionally carries legitimate
# runtime structure (templates/instances/execution per agent-definitions),
# so source-less dirs there are not rename residue.
MIRROR_DIR_PAIRS = [("skills", ".specify/skills")]


def find_orphan_mirror_dirs(root: Path, registry: set) -> list:
    findings = []
    for src_rel, mirror_rel in MIRROR_DIR_PAIRS:
        src, mirror = root / src_rel, root / mirror_rel
        if not (src.is_dir() and mirror.is_dir()):
            continue  # client projects have no source root — pair not applicable
        for child in sorted(mirror.iterdir()):
            if not child.is_dir() or (src / child.name).exists():
                continue
            if child.name in registry:
                findings.append(_finding(
                    "mirror-drift", f"{mirror_rel}/{child.name}",
                    f"已注册孤儿镜像目录(obsolete-asset registry 已登记 {child.name}),"
                    "由 init 回收或手动移除;sync-mirrors 不删除",
                    disposition="delegate", severity="medium"))
            else:
                findings.append(_finding(
                    "mirror-drift", f"{mirror_rel}/{child.name}",
                    f"未注册孤儿镜像目录:源侧 {src_rel}/ 已无 {child.name}(重命名未登记 "
                    "_OBSOLETE_* registry)——建议删除并在 registry 登记",
                    disposition="delete", severity="high"))
    return findings


OBSOLETE_MARKER_RE = re.compile(
    r"OBSOLETE-ASSET-REGISTRY[-:]START(.*?)OBSOLETE-ASSET-REGISTRY[-:]END", re.S)
QUOTED_RE = re.compile(r'"([^"]+)"')


def load_obsolete_registry(root: Path) -> set:
    path = root / "src" / "specify_cli" / "__init__.py"
    if not path.is_file():
        return set()
    match = OBSOLETE_MARKER_RE.search(path.read_text(encoding="utf-8", errors="replace"))
    if not match:
        return set()
    return set(QUOTED_RE.findall(match.group(1)))


def check_mirror_drift(root: Path) -> list:
    findings = []
    try:
        _, output = run_sync_mirrors_check(root)
        for path, kind in parse_mirror_drift_lines(output):
            findings.append(_finding(
                "mirror-drift", path,
                f"sync-mirrors --check 报告 {kind}——运行 sync-mirrors --write 收敛",
                disposition="delegate"))
    except (OSError, subprocess.TimeoutExpired):
        pass  # sub-lane unavailable; orphan check still applies
    findings.extend(find_orphan_mirror_dirs(root, load_obsolete_registry(root)))
    return findings


def check_docs_lane(root: Path):
    """Docs-tree dead references reuse docs-utils (Tool Reuse, contract C-4)."""
    try:
        spec = importlib.util.spec_from_file_location(
            "sanitize_docs_utils", Path(__file__).with_name("docs-utils.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.broken_links(root)
    except Exception as exc:  # docs engine unavailable -> lane skipped, noted
        return None


CHECKERS = [
    ("dead-reference", check_dead_references),
    ("index-inconsistency", check_index_consistency),
    ("broken-symlink", check_broken_symlinks),
    ("mirror-drift", check_mirror_drift),
]


def run_deterministic_checks(root: Path, roots_filter=None):
    findings, notes = [], []
    scanned = set()
    for category, fn in CHECKERS:
        try:
            findings.extend(fn(root))
            scanned.add(category)
        except Exception as exc:
            notes.append(f"checker {category} skipped after failure: {exc}")
    return findings, scanned, notes


# --------------------------------------------------------------------------
# semantic candidates (contracts/sanitize-detection-rules.md §5) — the engine
# gathers mechanical claims + a bounded evidence pack; the agent judges
# staleness/redundancy against that pack only (FR-007 program-first).
# --------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)
CLAIM_PHRASES = ["未落地", "未实现", "未合入", "待办", "pending", "not landed", "TODO"]
REPO_PATH_RE = re.compile(
    r"((?:scripts|shared|templates|docs|skills|agents|src|tests|\.specify)/[A-Za-z0-9_./-]+)")
FILE_FRAGMENT_RE = re.compile(r"([A-Za-z0-9_][\w./-]*\.(?:mjs|py|md|sh|json|ts|vscdb|db))")


def _parse_frontmatter(text: str) -> dict:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    return fm


def extract_claims(text: str) -> list:
    """Mechanical claim extraction (C-15): frontmatter status/date fields plus
    declaration phrases. No semantic induction — phrases are matched verbatim."""
    claims = []
    fm = _parse_frontmatter(text)
    for key in ("status", "parked_at", "created"):
        if key in fm:
            claims.append(f"{key}={fm[key]}")
    body = FRONTMATTER_RE.sub("", text)
    lowered = body.lower()
    for phrase in CLAIM_PHRASES:
        if phrase.lower() in lowered:
            claims.append(phrase)
    claims.extend(re.findall(r"P[1-9](?:[–—-]\w+)?", body)[:6])
    seen, ordered = set(), []
    for claim in claims:
        if claim not in seen:
            seen.add(claim)
            ordered.append(claim)
    return ordered[:15]


def extract_repo_paths(text: str) -> list:
    return sorted(set(REPO_PATH_RE.findall(text)))


def _git(root: Path, args: list):
    """Run git in the workspace; None on any failure/timeout (never raises)."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(root), capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return proc.stdout if proc.returncode == 0 else None


def collect_semantic_candidates(root: Path):
    candidates, notes = [], []
    for relpath in _iter_root_files(root, {"memory-todo", "memory-draft"}):
        if not relpath.endswith(".md"):
            continue
        text = (root / relpath).read_text(encoding="utf-8", errors="replace")
        paths = extract_repo_paths(text)
        # file-like fragments without a rooted prefix still carry locating
        # power as glob pathspecs ("*platforms/opencode.mjs" matches
        # scripts/js/.../platforms/opencode.mjs) — absence-of-work claims are
        # often contradicted by commits that PREDATE the claim date, so the
        # pack carries the latest bounded history instead of a since-window
        fragments = [f for f in FILE_FRAGMENT_RE.findall(text) if f not in paths]
        pathspecs = list(paths) + [f"*{f}" for f in fragments]
        log = _git(root, ["log", "--oneline", "-n", "20"]
                   + ["--"] + (pathspecs or [".specify/memory"]))
        if log is None:
            notes.append("git unavailable - semantic detection degraded")
            return [], notes
        candidates.append({
            "material": relpath,
            "claims": extract_claims(text),
            "evidencePack": {
                "gitLog": [line for line in log.splitlines() if line.strip()][:20],
                "pathExistence": {p: (root / p).exists() for p in paths},
            },
        })
    return candidates, notes


# --------------------------------------------------------------------------
# actions
# --------------------------------------------------------------------------

def _emit(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False))


def cmd_collect(root: Path, roots_filter=None) -> int:
    run_ts = _utcnow()
    store, notes = load_store(root)
    findings, scanned, checker_notes = run_deterministic_checks(root, roots_filter)
    notes.extend(checker_notes)
    # Conservative C-14 rule: a partial (--roots-filtered) scan never
    # auto-resolves; only full scans converge pending findings.
    if roots_filter is not None:
        scanned = set()
    stats = merge_findings(store, findings, run_ts, scanned)
    save_store(root, store)
    candidates, semantic_notes = collect_semantic_candidates(root)
    notes.extend(semantic_notes)
    _emit({
        "ok": True,
        "action": "collect",
        "store": store_digest(store),
        "deterministic": stats,
        "semanticCandidates": candidates,
        "roots": probe_roots(root),
        "notes": notes,
    })
    return 0


def cmd_record(root: Path, file: str) -> int:
    path = Path(file)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CliError(f"cannot read verdicts file: {exc}")
    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise CliError("verdicts file must carry {\"findings\": [...]}")
    errors = []
    for idx, f in enumerate(findings):
        if not isinstance(f, dict):
            errors.append(f"finding #{idx}: not an object")
            continue
        errs = validate_finding(f, root)
        errors.extend(f"finding #{idx} ({f.get('id', '?')}): {e}" for e in errs)
        if f.get("detection") != "semantic":
            errors.append(f"finding #{idx}: record accepts semantic verdicts only (programmatic findings come from collect)")
    if errors:
        raise VerificationError("verdicts rejected (all-or-nothing)", errors)
    run_ts = _utcnow()
    store, notes = load_store(root)
    stats = merge_findings(store, findings, run_ts, SEMANTIC_CATEGORIES)
    save_store(root, store)
    _emit({
        "ok": True, "action": "record", "store": store_digest(store),
        "merged": stats, "notes": notes,
    })
    return 0


def cmd_status(root: Path) -> int:
    store, notes = load_store(root)
    _emit({"ok": True, "action": "status", "store": store_digest(store), "notes": notes})
    return 0


APPLYABLE_DISPOSITIONS = {"delete", "archive", "repair", "dismiss"}


def cmd_apply(root: Path, plan_file: str) -> int:
    path = Path(plan_file)
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CliError(f"cannot read plan file: {exc}")
    if plan.get("confirmed") is not True:
        raise VerificationError("plan not confirmed", ["apply requires the user-confirmed cleanup plan (confirmed: true)"])
    items = plan.get("items")
    if not isinstance(items, list) or not items:
        raise VerificationError("plan has no items")
    store, _ = load_store(root)
    by_id = {f["id"]: f for f in store["findings"]}
    errors = []
    for idx, item in enumerate(items):
        f = by_id.get(item.get("findingId"))
        if f is None:
            errors.append(f"item #{idx}: unknown findingId {item.get('findingId')}")
            continue
        if f["state"] != "pending":
            errors.append(f"item #{idx}: finding {f['id']} is {f['state']}, not pending")
        if item.get("disposition") not in APPLYABLE_DISPOSITIONS:
            errors.append(f"item #{idx}: disposition {item.get('disposition')} is not applyable (delegate items are recommendations, not plan rows)")
        elif item["disposition"] != f["disposition"] and item["disposition"] != "dismiss":
            errors.append(f"item #{idx}: disposition {item['disposition']} does not match the finding's suggestion {f['disposition']}")
        if item.get("target") != f["target"]:
            errors.append(f"item #{idx}: target mismatch with finding")
        if not is_material_target(root, item.get("target", "")):
            errors.append(f"item #{idx}: target outside material roots: {item.get('target')}")
    if errors:
        raise VerificationError("plan rejected", errors)

    run_ts = _utcnow()
    executed, artifacts, failures, modify_paths = [], [], [], []
    for item in plan["items"]:
        f = by_id[item["findingId"]]
        disposition, target = item["disposition"], item["target"]
        try:
            if disposition == "delete":
                victim = root / target
                if victim.is_dir():
                    if any(victim.iterdir()):
                        raise VerificationError("refusing to delete non-empty directory")
                    victim.rmdir()
                else:
                    victim.unlink()
                artifacts.append({"change": "deleted", "path": target})
                modify_paths.append(f"git history retains {target} (recoverable via git checkout)")
            elif disposition == "archive":
                src = root / target
                # archive preserves relative layout under .specify/archive/
                # (a .specify-prefixed target drops its leading .specify/)
                rel = target[len(".specify/"):] if target.startswith(".specify/") else target
                dest = root / ARCHIVE_REL / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest))
                artifacts.append({"change": "archived", "path": target, "to": (ARCHIVE_REL / rel).as_posix()})
                modify_paths.append((ARCHIVE_REL / rel).as_posix())
            elif disposition in ("repair", "dismiss"):
                artifacts.append({"change": f"{disposition}-state-only", "path": target})
                modify_paths.append(target)
            f["state"] = "resolved"
            f["resolvedAt"] = run_ts
            f.setdefault("notes", []).append(f"{disposition} applied {run_ts}")
            executed.append({"findingId": f["id"], "disposition": disposition, "outcome": "ok"})
        except Exception as exc:
            f.setdefault("notes", []).append(f"apply failed {run_ts}: {exc}")
            failures.append({"findingId": f["id"], "reason": str(exc)})
            executed.append({"findingId": f["id"], "disposition": disposition, "outcome": "failed"})
    save_store(root, store)
    plan["executed"] = True
    try:
        path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass
    _emit({
        "ok": not failures, "action": "apply",
        "executed": executed, "artifacts": artifacts,
        "failures": failures, "modifyPaths": modify_paths,
    })
    return 0 if not failures else 2


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sanitize-utils.py",
        description="Framework material hygiene engine (Feature 047, requirement 045).",
    )
    parser.add_argument("--action", default=None,
                        help="engine action to run (collect/record/status/apply)")
    parser.add_argument("--workspace-root", default=".", help="workspace root (default: cwd)")
    parser.add_argument("--format", default="json", choices=["text", "json"],
                        help="output format (engine always emits JSON)")
    parser.add_argument("--file", help="record: agent verdicts file ({\"findings\": [...]})")
    parser.add_argument("--plan", help="apply: cleanup plan file path")
    parser.add_argument("--roots", help="collect: comma-separated root kinds to scan (partial scan; never auto-resolves)")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.workspace_root).resolve()
    known_actions = {"collect", "record", "status", "apply"}
    try:
        if not args.action or args.action not in known_actions:
            raise CliError(f"unknown or missing action: {args.action!r} (expected one of {sorted(known_actions)})")
        if args.action == "collect":
            roots_filter = set(filter(None, (args.roots or "").split(","))) or None
            return cmd_collect(root, roots_filter)
        if args.action == "status":
            return cmd_status(root)
        if args.action == "record":
            if not args.file:
                raise CliError("record requires --file <verdicts.json>")
            return cmd_record(root, args.file)
        if args.action == "apply":
            if not args.plan:
                raise CliError("apply requires --plan <cleanup-plan.json>")
            return cmd_apply(root, args.plan)
        raise CliError(f"unknown action: {args.action}")
    except CliError as exc:
        _emit({"ok": False, "error": str(exc)})
        return 1
    except VerificationError as exc:
        _emit({"ok": False, "error": str(exc), "details": getattr(exc, "details", [])})
        return 2
    except Exception as exc:  # noqa: BLE001 — engine must fail loudly, not silently
        _emit({"ok": False, "error": f"unexpected failure: {exc}"})
        return 1


if __name__ == "__main__":
    sys.exit(main())
