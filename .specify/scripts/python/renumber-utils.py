#!/usr/bin/env python3
"""Renumber engine — sequence-number collision repair for framework materials.

Concurrent and parallel lines allocate the "next" number from the same base, so
a merge can leave two artifacts owning one number. This engine detects those
collisions deterministically across four number families (spec directories,
register IDs, REC/OI prefix-follow, feature-local T/CHK IDs), proposes a
duplicate-only renumber mapping with a complete reference inventory, and — after
a single front-loaded confirmation — executes the renames and rewrites, then
verifies that no in-scope reference to the old token survives.

Contract notes:
  * duplicate-only: a free number is never reused and gaps are never compacted;
  * dated records are never rewritten (history / archives / date-named files);
  * git refs are never touched — branch renames are reported, never executed;
  * no plan is executed unless ``plan.confirmed`` is true (exit 2, zero
    side effects).

Stdlib only, mirroring the record-retention / sanitize engine discipline.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

KIND = "speckit.renumber"
SCHEMA_VERSION = 1
RENUMBER_REL = Path(".specify") / "memory" / "renumber"

ACTIONS = ("scan", "plan", "apply", "status", "dismiss", "args-manifest")

FAMILIES = ("spec-number", "register", "rec-follow", "local")

STATUS_PROPOSED = "proposed"
STATUS_NEEDS_DECISION = "needs-decision"
STATUS_BLOCKED = "blocked"
STATUS_DISMISSED = "dismissed"

# Framework-owned material roots that participate in reference rewriting.
SCAN_ROOTS = (".specify", "scripts", "templates", "skills", "agents", "shared",
              "src", "docs", "tests")
SPECS_REL = ".specify/specs"
MEMORY_REL = ".specify/memory"
REGISTER_REL = ".specify/memory/register.md"
FEATURES_REL = ".specify/memory/features.md"

EXCLUDED_PREFIXES = (
    ".specify/history/",
    ".specify/archive/",
    ".specify/specs/.archive/",
)
# Machine-generated stores name old identifiers by design; never rewrite them.
MACHINE_PREFIXES = (
    ".specify/memory/sanitize/",
    ".specify/memory/retention/",
    ".specify/memory/renumber/",
)
DATED_RE = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{8})")
# Evidence logs record what happened under the old identity; rewriting them would
# falsify the record. They are excluded like date-named records.
EVIDENCE_SEGMENTS = frozenset({"test-evidence"})

SPEC_DIR_RE = re.compile(r"^(\d{3})-([a-z0-9][a-z0-9-]*)$")
SPEC_PREFIX_ANY_RE = re.compile(r"^(\d+)-")
SPEC_REF_RE = re.compile(r"\.specify/specs/(\d{3})-([a-z0-9][a-z0-9-]*)")

REC_TOKEN_RE = re.compile(r"^REC-(\d{3}[a-z]?)-\d{2}$")
OI_SCOPED_TOKEN_RE = re.compile(r"^OI-(\d{3}[a-z]?)-\d{2}$")
OI_TOKEN_RE = re.compile(r"^OI-(\d+)$")
T_REGISTER_TOKEN_RE = re.compile(r"^T-(\d{3})$")

TASK_DEF_RE = re.compile(r"^- \[[ xX>~]\]\s+(T\d{3}[A-Za-z]?)\b")
CHK_DEF_RE = re.compile(r"^[-*] \[[ xX]\]\s+(CHK\d{3})\b")

SAFE_LIMIT_BYTES = 2 * 1024 * 1024


class RenumberError(ValueError):
    """User-facing refusal (exit 2) — always zero side effects on refusal."""


class UsageError(Exception):
    """Bad invocation or unreadable input (exit 1)."""


# ---------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def group_id(family: str, token: str, scope: str) -> str:
    return hashlib.sha1(f"{family}|{token}|{scope}".encode("utf-8")).hexdigest()[:12]


def write_json_atomic(path: Path, payload: Dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / (".tmp-" + uuid.uuid4().hex + ".part")
    with temporary.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    os.replace(temporary, path)
    return path


def read_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        node = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return node if isinstance(node, dict) else None


def resolve_root(explicit: Optional[str]) -> Path:
    # Deliberately no ancestor walk: walking up would self-match the framework
    # repository and write workspace state into the wrong tree.
    return Path(explicit).resolve() if explicit else Path.cwd().resolve()


def token_pattern(token: str) -> "re.Pattern[str]":
    return re.compile(r"(?<![0-9A-Za-z_-])" + re.escape(token) + r"(?![0-9A-Za-z_-])")


def count_hits(text: str, token: str) -> int:
    return len(token_pattern(token).findall(text))


# ---------------------------------------------------------------------------
# git helpers (read-only except `git mv` during apply)
# ---------------------------------------------------------------------------

def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git", "-C", str(root), *args],
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:  # pragma: no cover
        return subprocess.CompletedProcess(args, 1, "", str(exc))


def is_git_repo(root: Path) -> bool:
    return _git(root, "rev-parse", "--git-dir").returncode == 0


def git_added(root: Path, relpath: str) -> Optional[int]:
    result = _git(root, "log", "--diff-filter=A", "--format=%ct", "--", relpath)
    if result.returncode != 0:
        return None
    values = [int(v) for v in result.stdout.split() if v.strip().isdigit()]
    return min(values) if values else None


def branch_names(root: Path) -> List[str]:
    result = _git(root, "for-each-ref", "--format=%(refname:short)",
                  "refs/heads", "refs/remotes")
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def matching_branches(root: Path, prefix: str) -> List[str]:
    pattern = re.compile(r"(?:^|/)" + re.escape(prefix) + r"(?:-[^/]*)?$")
    return sorted(name for name in branch_names(root) if pattern.search(name))


def git_clean(root: Path, paths: Sequence[str]) -> Tuple[bool, List[str]]:
    if not is_git_repo(root):
        return False, ["not-a-git-repository"]
    if not paths:
        return True, []
    status = _git(root, "status", "--porcelain", "--", *paths)
    if status.returncode != 0:
        return False, [status.stderr.strip() or "git-status-failed"]
    dirty = [line for line in status.stdout.splitlines() if line.strip()]
    return (not dirty), dirty


# ---------------------------------------------------------------------------
# material walk
# ---------------------------------------------------------------------------

def _iter_material_files(root: Path):
    seen = set()
    for rel in SCAN_ROOTS:
        base = root / rel
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_dir() or path.is_symlink():
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield path

def _relpath(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_machine(relpath: str) -> bool:
    return any(relpath.startswith(prefix) for prefix in MACHINE_PREFIXES)


def _is_dated_record(relpath: str) -> bool:
    if any(relpath.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return True
    if EVIDENCE_SEGMENTS & set(Path(relpath).parts):
        return True
    return bool(DATED_RE.search(Path(relpath).name))


def _read_text(path: Path) -> Optional[str]:
    try:
        if path.stat().st_size > SAFE_LIMIT_BYTES:
            return None
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def scan_token_hits(root: Path, token: str) -> Dict[str, Any]:
    """Return in-scope hits and excluded (dated / archived) hits for a token."""
    in_scope: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []
    pattern = token_pattern(token)
    for path in _iter_material_files(root):
        relpath = _relpath(root, path)
        if _is_machine(relpath):
            continue
        text = _read_text(path)
        if text is None:
            continue
        hits = len(pattern.findall(text))
        if not hits:
            continue
        entry = {"path": relpath, "hits": hits}
        (excluded if _is_dated_record(relpath) else in_scope).append(entry)
    return {"in_scope": in_scope, "excluded": excluded,
            "in_scope_total": sum(e["hits"] for e in in_scope),
            "excluded_total": sum(e["hits"] for e in excluded)}


def rewrite_token(root: Path, token: str, replacement: str,
                  skip: Optional[set] = None) -> Dict[str, Any]:
    """Rewrite in-scope occurrences; ``skip`` holds (relpath, line) pairs to spare."""
    pattern = token_pattern(token)
    skip = skip or set()
    written: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    for path in _iter_material_files(root):
        relpath = _relpath(root, path)
        if _is_machine(relpath) or _is_dated_record(relpath):
            continue
        text = _read_text(path)
        if text is None or not pattern.search(text):
            continue
        lines = text.splitlines(keepends=True)
        hits = 0
        for index, line in enumerate(lines, 1):
            if (relpath, index) in skip:
                continue
            count = len(pattern.findall(line))
            if count:
                hits += count
                lines[index - 1] = pattern.sub(lambda _m: replacement, line)
        if not hits:
            continue
        try:
            path.write_text("".join(lines), encoding="utf-8")
            written.append({"path": relpath, "hits": hits})
        except OSError as exc:
            failures.append({"path": relpath, "error": str(exc)})
    return {"written": written, "failures": failures}


def _safe_path(root: Path, relpath: str, roots: Sequence[str] = SCAN_ROOTS) -> Optional[Path]:
    """Resolve a plan-supplied path, refusing escapes and out-of-scope roots."""
    try:
        candidate = (root / relpath).resolve()
        relative = candidate.relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return None
    if not any(relative == base or relative.startswith(base + "/") for base in roots):
        return None
    return candidate


def rewrite_line(root: Path, relpath: str, line_number: int,
                 token: str, replacement: str) -> Dict[str, Any]:
    """Rewrite the first occurrence of ``token`` on one specific line."""
    path = _safe_path(root, relpath)
    if path is None:
        return {"ok": False, "problem": "path-outside-scope"}
    text = _read_text(path)
    if text is None:
        return {"ok": False, "problem": "unreadable-file"}
    lines = text.splitlines(keepends=True)
    if line_number < 1 or line_number > len(lines):
        return {"ok": False, "problem": "line-out-of-range"}
    pattern = token_pattern(token)
    if not pattern.search(lines[line_number - 1]):
        return {"ok": False, "problem": "token-not-on-line"}
    lines[line_number - 1] = pattern.sub(lambda _m: replacement,
                                         lines[line_number - 1], count=1)
    try:
        path.write_text("".join(lines), encoding="utf-8")
        return {"ok": True, "path": relpath, "line": line_number}
    except OSError as exc:
        return {"ok": False, "problem": str(exc)}


# ---------------------------------------------------------------------------
# features index / spec directories
# ---------------------------------------------------------------------------

def features_rows(root: Path) -> List[Dict[str, Any]]:
    path = root / FEATURES_REL
    if not path.is_file():
        return []
    text = _read_text(path)
    if not text:
        return []
    rows: List[Dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) < 3 or not re.fullmatch(r"\d{3}", cells[1]):
            continue
        rows.append({"line": number, "id": cells[1], "cells": cells})
    return rows


def registered_spec_dirs(root: Path) -> set:
    names = set()
    for row in features_rows(root):
        for cell in row["cells"]:
            match = SPEC_REF_RE.search(cell)
            if match:
                names.add(f"{match.group(1)}-{match.group(2)}")
    return names


def spec_dirs(root: Path) -> List[Path]:
    base = root / SPECS_REL
    if not base.is_dir():
        return []
    return sorted(path for path in base.iterdir()
                  if path.is_dir() and not path.name.startswith("."))


def taken_spec_numbers(root: Path) -> set:
    numbers = set()

    def add(name: str) -> None:
        match = SPEC_PREFIX_ANY_RE.match(name)
        if match:
            numbers.add(int(match.group(1)))

    for path in spec_dirs(root):
        add(path.name)
    archive = root / SPECS_REL / ".archive"
    if archive.is_dir():
        for path in archive.iterdir():
            add(path.name)
    for row in features_rows(root):
        for cell in row["cells"]:
            match = SPEC_REF_RE.search(cell)
            if match:
                numbers.add(int(match.group(1)))
    for name in branch_names(root):
        add(name.rsplit("/", 1)[-1])
    return numbers


def next_spec_number(taken: set, offset: int = 0) -> int:
    return (max(taken) if taken else 0) + 1 + offset


def _spec_keep_key(root: Path, path: Path, registered: set):
    added = git_added(root, f"{SPECS_REL}/{path.name}")
    return (0 if path.name in registered else 1,
            added if added is not None else float("inf"),
            path.name)


# ---------------------------------------------------------------------------
# register parsing
# ---------------------------------------------------------------------------

def register_rows(root: Path) -> List[Dict[str, Any]]:
    path = root / REGISTER_REL
    if not path.is_file():
        return []
    rows: List[Dict[str, Any]] = []
    text = _read_text(path)
    if not text:
        return []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) < 3 or cells[1] in ("编号", "") or set(cells[1]) <= {"-", ":", " "}:
            continue
        rows.append({"line": number, "idcell": cells[1]})
    return rows


def defined_register_tokens(cell: str) -> List[str]:
    tokens: List[str] = []
    for part in re.split(r"\s*/\s*", cell.replace("*", "")):
        token = part.strip()
        if not token:
            continue
        if REC_TOKEN_RE.match(token) or OI_SCOPED_TOKEN_RE.match(token) \
                or OI_TOKEN_RE.match(token) or T_REGISTER_TOKEN_RE.match(token):
            tokens.append(token)
    return tokens


def token_scope(token: str) -> Optional[Tuple[str, int, int]]:
    """Return (scope, number, width) for a renumberable register token."""
    match = REC_TOKEN_RE.match(token)
    if match:
        return (f"REC-{match.group(1)}", int(token.rsplit("-", 1)[1]), 2)
    match = OI_SCOPED_TOKEN_RE.match(token)
    if match:
        return (f"OI-{match.group(1)}", int(token.rsplit("-", 1)[1]), 2)
    match = OI_TOKEN_RE.match(token)
    if match:
        return ("OI", int(match.group(1)), 1)
    match = T_REGISTER_TOKEN_RE.match(token)
    if match:
        return ("T", int(match.group(1)), 3)
    return None


def build_token(scope: str, number: int, width: int) -> str:
    return f"{scope}-{number:0{width}d}"


def register_definitions(root: Path) -> Dict[str, List[int]]:
    definitions: Dict[str, List[int]] = {}
    for row in register_rows(root):
        for token in defined_register_tokens(row["idcell"]):
            lines = definitions.setdefault(token, [])
            if row["line"] not in lines:
                lines.append(row["line"])
    return definitions


def next_scoped_number(definitions: Dict[str, List[int]], scope: str) -> Tuple[int, int]:
    width = 3 if scope == "T" else (1 if scope == "OI" else 2)
    highest = 0
    for token in definitions:
        info = token_scope(token)
        if info and info[0] == scope:
            highest = max(highest, info[1])
    return highest + 1, width


# ---------------------------------------------------------------------------
# detection — four families
# ---------------------------------------------------------------------------

def spec_number_groups(root: Path) -> List[Dict[str, Any]]:
    groups: List[Dict[str, Any]] = []
    by_prefix: Dict[str, List[Path]] = {}
    for path in spec_dirs(root):
        match = SPEC_DIR_RE.match(path.name)
        if match:
            by_prefix.setdefault(match.group(1), []).append(path)
    registered = registered_spec_dirs(root)
    taken = taken_spec_numbers(root)
    offset = 0
    for prefix in sorted(by_prefix):
        dirs = by_prefix[prefix]
        if len(dirs) < 2:
            continue
        keep = min(dirs, key=lambda p: _spec_keep_key(root, p, registered))
        for candidate in dirs:
            if candidate == keep:
                continue
            new_number = next_spec_number(taken, offset)
            offset += 1
            slug = candidate.name[len(prefix) + 1:]
            new_name = f"{new_number:03d}-{slug}"
            token = candidate.name
            hits = scan_token_hits(root, token)
            groups.append({
                "family": "spec-number",
                "scope": prefix,
                "old_token": token,
                "new_token": new_name,
                "keep": {"token": keep.name,
                         "evidence": ("features-row" if keep.name in registered
                                      else "git-added" if git_added(
                                          root, f"{SPECS_REL}/{keep.name}") is not None
                                      else "lexicographic")},
                "status": STATUS_PROPOSED,
                "verify": "token-absent",
                "items": [{"kind": "dir-rename",
                           "from": f"{SPECS_REL}/{candidate.name}",
                           "to": f"{SPECS_REL}/{new_name}"}],
                "refs": hits,
                "guards": {"branches": matching_branches(root, prefix),
                           "ambiguous_refs": 0},
                "depends_on": [],
            })
    return groups


def register_groups(root: Path) -> List[Dict[str, Any]]:
    definitions = register_definitions(root)
    groups: List[Dict[str, Any]] = []
    reserve: Dict[str, int] = {}
    for token in sorted(definitions):
        lines = sorted(definitions[token])
        if len(lines) < 2:
            continue
        info = token_scope(token)
        if info is None:
            continue
        scope, _number, width = info
        if scope not in reserve:
            reserve[scope], _ = next_scoped_number(definitions, scope)
        new_token = build_token(scope, reserve[scope], width)
        reserve[scope] += 1
        hits = scan_token_hits(root, token)
        # Every mention beyond the definitions themselves is ambiguous:
        # a duplicated identifier cannot tell which definition it means.
        ambiguous = hits["in_scope_total"] - len(lines)
        groups.append({
            "family": "register",
            "scope": scope,
            "old_token": token,
            "new_token": new_token,
            "keep": {"token": token, "evidence": f"register-row:{lines[0]}"},
            "status": STATUS_PROPOSED if ambiguous <= 0 else STATUS_NEEDS_DECISION,
            "verify": "duplicate-resolved",
            "items": [{"kind": "cell-rewrite", "path": REGISTER_REL,
                       "line": lines[-1], "from": token, "to": new_token,
                       "keep_path": REGISTER_REL, "keep_line": lines[0]}],
            "refs": hits,
            "guards": {"branches": [], "ambiguous_refs": max(ambiguous, 0)},
            "depends_on": [],
        })
    return groups


def token_locations(root: Path, token: str) -> List[str]:
    pattern = token_pattern(token)
    found = []
    base = root / SPECS_REL
    if not base.is_dir():
        return found
    for spec in spec_dirs(root):
        for path in sorted(spec.rglob("*.md")):
            text = _read_text(path)
            if text and pattern.search(text):
                found.append(spec.name)
                break
    return found


def rec_follow_groups(root: Path, spec_groups: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    groups: List[Dict[str, Any]] = []
    definitions = register_definitions(root)
    for spec_group in spec_groups:
        old_prefix = spec_group["scope"]
        new_prefix = spec_group["new_token"].split("-", 1)[0]
        for token in sorted(definitions):
            info = token_scope(token)
            if info is None:
                continue
            scope, _number, width = info
            if scope not in (f"REC-{old_prefix}", f"OI-{old_prefix}"):
                continue
            owners = token_locations(root, token)
            owner = owners[0] if len(owners) == 1 else ""
            if owner != spec_group["old_token"]:
                continue  # belongs to the kept spec (or ambiguous) — never follow
            new_token = f"{scope.replace(old_prefix, new_prefix, 1)}-{token.rsplit('-', 1)[1]}"
            hits = scan_token_hits(root, token)
            groups.append({
                "family": "rec-follow",
                "scope": scope,
                "old_token": token,
                "new_token": new_token,
                "keep": {"token": token, "evidence": f"owner:{owner}"},
                "status": STATUS_PROPOSED,
                "items": [],
                "refs": hits,
                "guards": {"branches": [], "ambiguous_refs": 0},
                "depends_on": [group_id("spec-number", spec_group["old_token"],
                                        spec_group["scope"])],
            })
    return groups


def local_groups(root: Path) -> List[Dict[str, Any]]:
    groups: List[Dict[str, Any]] = []
    base = root / SPECS_REL
    if not base.is_dir():
        return groups
    for spec in spec_dirs(root):
        for path in sorted(spec.rglob("*.md")):
            text = _read_text(path)
            if not text:
                continue
            matcher = TASK_DEF_RE if path.name == "tasks.md" else CHK_DEF_RE
            definitions: Dict[str, List[int]] = {}
            for number, line in enumerate(text.splitlines(), 1):
                match = matcher.match(line)
                if match:
                    definitions.setdefault(match.group(1), []).append(number)
            if not definitions:
                continue
            width = 3
            highest = 0
            for token in definitions:
                digits = re.search(r"(\d+)[A-Za-z]?$", token)
                if digits:
                    highest = max(highest, int(digits.group(1)))
            relpath = _relpath(root, path)
            for token in sorted(definitions):
                if len(definitions[token]) < 2:
                    continue
                highest += 1
                new_token = re.sub(r"\d+", f"{highest:0{width}d}", token, count=1)
                hits = scan_token_hits(root, token)
                ambiguous = hits["in_scope_total"] - len(definitions[token])
                groups.append({
                    "family": "local",
                    "scope": relpath,
                    "old_token": token,
                    "new_token": new_token,
                    "keep": {"token": token,
                             "evidence": f"first-definition:{definitions[token][0]}"},
                    "status": STATUS_PROPOSED if ambiguous <= 0 else STATUS_NEEDS_DECISION,
                    "verify": "duplicate-resolved",
                    "items": [{"kind": "definition-rewrite", "path": relpath,
                               "line": definitions[token][-1], "from": token,
                               "to": new_token, "keep_path": relpath,
                               "keep_line": definitions[token][0]}],
                    "refs": hits,
                    "guards": {"branches": [], "ambiguous_refs": max(ambiguous, 0)},
                    "depends_on": [],
                })
    return groups


def informational(root: Path) -> List[Dict[str, Any]]:
    notes: List[Dict[str, Any]] = []
    for path in spec_dirs(root):
        if SPEC_DIR_RE.match(path.name) or not path.name[:1].isdigit():
            continue
        notes.append({"kind": "nonconforming-spec-prefix", "target": path.name,
                      "hint": "字母后缀前缀不被 common.sh 识别,解析器会回退到最新 spec"})
    for row in register_rows(root):
        tokens = defined_register_tokens(row["idcell"])
        if tokens or row["idcell"] == "":
            continue
        notes.append({"kind": "non-machine-register-code", "target": row["idcell"],
                      "line": row["line"],
                      "hint": "无机器分配规则的编号,只报告不重排"})
    return notes


# ---------------------------------------------------------------------------
# dismissals / store
# ---------------------------------------------------------------------------

def store_dir(root: Path) -> Path:
    return root / RENUMBER_REL


def plans_dir(root: Path) -> Path:
    return store_dir(root) / "plans"


def dismissals_dir(root: Path) -> Path:
    return store_dir(root) / "dismissals"


def ledger_dir(root: Path) -> Path:
    return store_dir(root) / "ledger"


def load_dismissals(root: Path) -> Dict[str, Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    directory = dismissals_dir(root)
    if not directory.is_dir():
        return latest
    for path in sorted(directory.glob("*.json")):
        node = read_json(path)
        if not node or not node.get("group_id"):
            continue
        latest[str(node["group_id"])] = node
    return latest


def active_dismissals(root: Path) -> Dict[str, Dict[str, Any]]:
    return {gid: node for gid, node in load_dismissals(root).items()
            if not node.get("reopened")}


def build_groups(root: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    specs = spec_number_groups(root)
    groups = specs + rec_follow_groups(root, specs) + register_groups(root) + local_groups(root)
    dismissed = active_dismissals(root)
    for group in groups:
        gid = group_id(group["family"], group["old_token"], group["scope"])
        group["group_id"] = gid
        if gid in dismissed:
            group["status"] = STATUS_DISMISSED
            group["dismissal"] = {"reason": dismissed[gid].get("reason"),
                                  "decided_at": dismissed[gid].get("decided_at")}
    order = {name: index for index, name in enumerate(FAMILIES)}
    groups.sort(key=lambda g: (order.get(g["family"], 99), g["old_token"]))
    return groups, informational(root)


def group_digest(group: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "group_id": group["group_id"],
        "family": group["family"],
        "scope": group["scope"],
        "old_token": group["old_token"],
        "new_token": group["new_token"],
        "keep": group["keep"],
        "status": group["status"],
        "in_scope_hits": group["refs"]["in_scope_total"],
        "excluded_hits": group["refs"]["excluded_total"],
        "ambiguous_refs": group["guards"]["ambiguous_refs"],
        "branches": group["guards"]["branches"],
        "depends_on": group["depends_on"],
    }


def summarize(groups: List[Dict[str, Any]]) -> Dict[str, Any]:
    families: Dict[str, Dict[str, int]] = {}
    for group in groups:
        bucket = families.setdefault(group["family"], {
            STATUS_PROPOSED: 0, STATUS_NEEDS_DECISION: 0,
            STATUS_BLOCKED: 0, STATUS_DISMISSED: 0})
        bucket[group["status"]] = bucket.get(group["status"], 0) + 1
    return families


# ---------------------------------------------------------------------------
# actions
# ---------------------------------------------------------------------------

def action_scan(args: argparse.Namespace) -> Dict[str, Any]:
    root = resolve_root(args.workspace_root)
    groups, notes = build_groups(root)
    ledgers = len(list(ledger_dir(root).glob("*.json"))) if ledger_dir(root).is_dir() else 0
    active = [g for g in groups if g["status"] != STATUS_DISMISSED]
    return {"ok": True, "action": "scan", "families": summarize(groups),
            "groups": [group_digest(g) for g in active],
            "dismissed": [group_digest(g) for g in groups if g["status"] == STATUS_DISMISSED],
            "info": notes, "ledgers": ledgers,
            "pending": sum(1 for g in active if g["status"] == STATUS_PROPOSED)}


def action_plan(args: argparse.Namespace) -> Dict[str, Any]:
    root = resolve_root(args.workspace_root)
    groups, notes = build_groups(root)
    selected = [g for g in groups if g["status"] != STATUS_DISMISSED]
    if not selected:
        return {"ok": True, "action": "plan", "groups": 0,
                "note": "no undismissed numbering collision found"}
    plan = {"kind": KIND + ".plan", "schema_version": SCHEMA_VERSION,
            "created_at": now_iso(), "workspace_root": str(root),
            "confirmed": False, "families": FAMILIES,
            "groups": selected, "info": notes}
    out = Path(args.plan_out) if args.plan_out else None
    if out is None:
        out = plans_dir(root) / f"{stamp()}-plan.json"
    elif not out.is_absolute():
        out = root / out
    write_json_atomic(out, plan)
    return {"ok": True, "action": "plan", "plan": str(out),
            "groups": len(selected), "families": summarize(selected),
            "needs_decision": sum(1 for g in selected
                                  if g["status"] == STATUS_NEEDS_DECISION),
            "digest": [group_digest(g) for g in selected]}


def _revalidate(root: Path, group: Dict[str, Any]) -> Optional[str]:
    """Return a problem string when the mapping no longer holds."""
    family = group["family"]
    old, new = group["old_token"], group["new_token"]
    if family == "spec-number":
        old_dir = root / SPECS_REL / old
        new_dir = root / SPECS_REL / new
        if not old_dir.is_dir():
            return "old-dir-missing"
        if new_dir.exists():
            return "new-dir-exists"
        sharing = [p.name for p in spec_dirs(root)
                   if p.name.startswith(group["scope"] + "-")]
        if len(sharing) < 2:
            return "collision-gone"
        if matching_branches(root, group["scope"]):
            return "branch-name-conflict"
        return None
    if family in ("register", "rec-follow"):
        definitions = register_definitions(root)
        if family == "register" and len(definitions.get(old, [])) < 2:
            return "duplicate-gone"
        if any(new == token for token in definitions):
            return "new-token-defined"
        return None
    if family == "local":
        path = root / group["scope"]
        text = _read_text(path) if path.is_file() else None
        if text is None:
            return "file-missing"
        if count_hits(text, old) < 2:
            return "duplicate-gone"
        return None
    return "unknown-family"


def _rename_dir(root: Path, rel_from: str, rel_to: str) -> str:
    source = _safe_path(root, rel_from, (SPECS_REL,))
    target = _safe_path(root, rel_to, (SPECS_REL,))
    if source is None or target is None:
        return "path-outside-scope"
    result = _git(root, "mv", rel_from, rel_to)
    if result.returncode == 0:
        return ""
    try:
        source.rename(target)
        return ""
    except OSError as exc:
        return str(exc)


def action_apply(args: argparse.Namespace) -> Dict[str, Any]:
    root = resolve_root(args.workspace_root)
    plan_path = Path(args.plan or "")
    if not plan_path.is_absolute():
        from_cwd = Path.cwd() / plan_path
        plan_path = from_cwd if from_cwd.is_file() else root / plan_path
    plan = read_json(plan_path)
    if plan is None:
        raise UsageError(f"cannot read plan: {plan_path}")
    if plan.get("confirmed") is not True:
        raise RenumberError("apply refused: plan.confirmed must be true")
    groups = plan.get("groups")
    if not isinstance(groups, list) or not groups:
        raise RenumberError("apply refused: plan.groups must be a non-empty list")
    if not is_git_repo(root):
        raise RenumberError("apply refused: workspace is not a git repository "
                            "(a directory rename outside git loses its history)")

    wanted = None
    if args.groups:
        wanted = {part.strip() for part in str(args.groups).split(",") if part.strip()}
        unknown = wanted - {str(g.get("group_id")) for g in groups}
        if unknown:
            raise RenumberError(f"apply refused: unknown group ids: {sorted(unknown)}")

    selected = [g for g in groups
                if wanted is None or str(g.get("group_id")) in wanted]
    selected.sort(key=lambda g: (0 if g["family"] == "spec-number" else 1))

    selected_ids = {str(g.get("group_id")) for g in selected}
    dependency_problems = [
        {"group_id": group.get("group_id"), "problem": "dependency-not-selected",
         "missing": [dep for dep in (group.get("depends_on") or [])
                     if dep not in selected_ids]}
        for group in selected
        if any(dep not in selected_ids for dep in (group.get("depends_on") or []))
    ]
    if dependency_problems:
        raise RenumberError(
            "apply refused: a dependent group was selected without its spec group: "
            + ", ".join(f"{p['group_id']}->{p['missing']}" for p in dependency_problems))

    problems: List[Dict[str, Any]] = []
    for group in selected:
        if group.get("status") != STATUS_PROPOSED:
            if group.get("status") == STATUS_NEEDS_DECISION \
                    and group["guards"].get("ambiguous_refs") \
                    and args.adopt_ambiguous_refs:
                pass
            else:
                problems.append({"group_id": group.get("group_id"),
                                 "problem": group.get("status")})
                continue
        elif group["guards"].get("ambiguous_refs") and not args.adopt_ambiguous_refs:
            problems.append({"group_id": group.get("group_id"),
                             "problem": "ambiguous-refs"})
            continue
        issue = _revalidate(root, group)
        if issue:
            problems.append({"group_id": group.get("group_id"), "problem": issue})
    if problems:
        raise RenumberError(
            "apply refused (re-scan and re-plan): "
            + ", ".join(f"{p['group_id']}:{p['problem']}" for p in problems))

    targets = [str(item.get("from") or item.get("path") or "")
               for group in selected for item in group["items"]]
    targets = [target for target in targets if target]
    targets += [entry["path"] for group in selected
                for entry in group["refs"]["in_scope"]]
    clean, dirty = git_clean(root, sorted(set(targets)))
    if not clean:
        raise RenumberError("apply refused: target paths are not clean in git "
                            f"(commit first): {dirty[:5]}")

    applied: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    for group in selected:
        result: Dict[str, Any] = {"group_id": group["group_id"],
                                  "family": group["family"],
                                  "old_token": group["old_token"],
                                  "new_token": group["new_token"]}
        failed = False
        skip = set()
        for item in group["items"]:
            if item["kind"] == "dir-rename":
                error = _rename_dir(root, item["from"], item["to"])
                if error:
                    failures.append({**result, "problem": "rename-failed",
                                     "error": error})
                    failed = True
                    break
            elif item["kind"] in ("cell-rewrite", "definition-rewrite"):
                outcome = rewrite_line(root, item["path"], item["line"],
                                       item["from"], item["to"])
                if not outcome["ok"]:
                    failures.append({**result, "problem": "definition-rewrite-failed",
                                     **outcome})
                    failed = True
                    break
                skip.add((str(item["keep_path"]), int(item["keep_line"])))
                skip.add((str(item["path"]), int(item["line"])))
        if failed:
            continue
        if group.get("verify") == "token-absent":
            # The token is unique outside the kept artifact: rewrite exhaustively.
            rewrite = rewrite_token(root, group["old_token"], group["new_token"])
        else:
            # Duplicate repair: the kept definition must retain the old token, so
            # only adopted ambiguous references follow the renumbered definition.
            rewrite = {"written": [], "failures": []}
            if args.adopt_ambiguous_refs and group["guards"].get("ambiguous_refs"):
                rewrite = rewrite_token(root, group["old_token"],
                                        group["new_token"], skip=skip)
        result["written"] = rewrite["written"]
        if rewrite["failures"]:
            failures.extend({**result, "problem": "rewrite-failed", **entry}
                            for entry in rewrite["failures"])
        applied.append(result)

    post_groups, _notes = build_groups(root)
    post_ids = {group["group_id"] for group in post_groups}
    unresolved = [{"group_id": item["group_id"],
                   "family": item["family"],
                   "old_token": item["old_token"]}
                  for item in applied if item["group_id"] in post_ids]

    excluded_hits: List[Dict[str, Any]] = []
    for group in selected:
        for entry in scan_token_hits(root, group["old_token"])["excluded"]:
            excluded_hits.append({**entry, "group_id": group["group_id"],
                                  "old_token": group["old_token"]})

    ledger = {"kind": KIND + ".ledger", "schema_version": SCHEMA_VERSION,
              "applied_at": now_iso(), "plan": str(plan_path),
              "groups": applied, "failures": failures,
              "excluded_hits": excluded_hits,
              "verification": {"resolved": len(applied) - len(unresolved),
                               "unresolved": unresolved,
                               "excluded_hits": len(excluded_hits)},
              "ok": not unresolved and not failures}
    target = ledger_dir(root) / f"{stamp()}-renumber.json"
    write_json_atomic(target, ledger)
    result_payload = {"ok": ledger["ok"], "action": "apply", "ledger": str(target),
                      "groups": len(applied), "failures": failures,
                      "excluded_hits": len(excluded_hits),
                      "unresolved": unresolved}
    if not ledger["ok"]:
        raise RenumberError(json.dumps(result_payload, ensure_ascii=False))
    return result_payload


def action_dismiss(args: argparse.Namespace) -> Dict[str, Any]:
    root = resolve_root(args.workspace_root)
    if not args.group:
        raise UsageError("dismiss requires --group <group_id>")
    groups, _notes = build_groups(root)
    by_id = {group["group_id"]: group for group in groups}
    if args.reopen:
        active = active_dismissals(root)
        if args.group not in active:
            raise RenumberError(f"reopen refused: {args.group} is not dismissed")
    elif args.group not in by_id:
        raise RenumberError(f"dismiss refused: unknown group id {args.group}")
    payload = {"kind": KIND + ".dismissal", "schema_version": SCHEMA_VERSION,
               "group_id": args.group, "decided_at": now_iso(),
               "reason": args.reason or "", "reopened": bool(args.reopen)}
    if args.group in by_id:
        payload["family"] = by_id[args.group]["family"]
        payload["old_token"] = by_id[args.group]["old_token"]
    target = dismissals_dir(root) / f"{stamp()}-dismissal.json"
    write_json_atomic(target, payload)
    return {"ok": True, "action": "dismiss", "group_id": args.group,
            "reopened": bool(args.reopen), "dismissal": str(target)}


def action_status(args: argparse.Namespace) -> Dict[str, Any]:
    root = resolve_root(args.workspace_root)
    groups, _notes = build_groups(root)
    ledgers = sorted(ledger_dir(root).glob("*.json")) if ledger_dir(root).is_dir() else []
    plans = sorted(plans_dir(root).glob("*.json")) if plans_dir(root).is_dir() else []
    dismissals = load_dismissals(root)
    return {"ok": True, "action": "status", "families": summarize(groups),
            "pending": sum(1 for g in groups if g["status"] == STATUS_PROPOSED),
            "needs_decision": sum(1 for g in groups
                                  if g["status"] == STATUS_NEEDS_DECISION),
            "dismissed": sum(1 for g in groups if g["status"] == STATUS_DISMISSED),
            "plans": len(plans), "ledgers": len(ledgers),
            "dismissal_entries": len(dismissals),
            "latest_plan": str(plans[-1]) if plans else None,
            "latest_ledger": str(ledgers[-1]) if ledgers else None}


ARG_MANIFEST = {
    "scan": {"required": [], "source": ["--workspace-root"]},
    "plan": {"required": [], "source": ["--plan-out", "--workspace-root"]},
    "apply": {"required": ["--plan"], "source": ["--groups",
                                                 "--adopt-ambiguous-refs",
                                                 "--workspace-root"]},
    "status": {"required": [], "source": ["--workspace-root"]},
    "dismiss": {"required": ["--group"], "source": ["--reason", "--reopen",
                                                     "--workspace-root"]},
    "args-manifest": {"required": [], "source": []},
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Renumber engine (sequence-number collision repair)")
    parser.add_argument("--action", choices=list(ACTIONS), required=True)
    parser.add_argument("--workspace-root", default=None)
    parser.add_argument("--plan", default=None)
    parser.add_argument("--plan-out", default=None)
    parser.add_argument("--groups", default=None)
    parser.add_argument("--group", default=None)
    parser.add_argument("--reason", default=None)
    parser.add_argument("--reopen", action="store_true")
    parser.add_argument("--adopt-ambiguous-refs", action="store_true")
    parser.add_argument("--format", choices=["text", "json"], default="json")
    return parser


def action_args_manifest(args: argparse.Namespace) -> Dict[str, Any]:
    parser = build_parser()
    live = {opt for action in parser._actions for opt in action.option_strings}
    manifest: Dict[str, Any] = {}
    for name in ACTIONS:
        spec = ARG_MANIFEST.get(name)
        if spec is None:
            raise UsageError(f"args-manifest: action {name!r} has no manifest spec")
        for key in ("required", "source"):
            unknown = [flag for flag in spec[key] if flag not in live]
            if unknown:
                raise UsageError(
                    f"args-manifest: {name} {key} flags are not parser options: {unknown}")
        manifest[name] = {"required": list(spec["required"]),
                          "source": list(spec["source"])}
    return manifest


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        handler = {
            "scan": action_scan,
            "plan": action_plan,
            "apply": action_apply,
            "status": action_status,
            "dismiss": action_dismiss,
            "args-manifest": action_args_manifest,
        }[args.action]
        payload = handler(args)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except RenumberError as exc:
        print(f"renumber-utils: {exc}", file=sys.stderr)
        return 2
    except UsageError as exc:
        print(f"renumber-utils: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # never raise into the caller
        print(f"renumber-utils: unexpected failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
