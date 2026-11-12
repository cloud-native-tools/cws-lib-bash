#!/usr/bin/env python3
"""docs-utils.py — deterministic engine for the /speckit.docs command.

Stdlib-only. Prints exactly one JSON object to stdout per invocation.
Contract: docs-utils CLI output contract (owned by the framework's docs-command feature records).
Shared literals (requirements.md Shared Strings): STR-001 "draft",
STR-002 "expired", STR-003 "archived", STR-004 "expires".
"""
from __future__ import annotations

import argparse
import hashlib
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
    "GEMINI.md", "HERMES.md", "OPENCODE.md",
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


def cmd_validate(root: Path, extra_special: set[str] | None = None) -> dict:
    violations: list[dict] = []
    allowed_special = ALLOWED_SPECIAL | (extra_special or set())
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
        elif name not in allowed_special and re.sub(r"[^A-Za-z]", "", path.stem).isupper() \
                and len(re.sub(r"[^A-Za-z]", "", path.stem)) >= 2:
            violations.append({
                "kind": "reserved-name-misuse", "path": name,
                "detail": "ALL-CAPS names are reserved; use kebab-case.md or register the name",
            })
    docs = root / "docs"
    # dot-directories (e.g. docs/.speckit/ — the machine area) are not documents
    doc_files = sorted(
        p for p in docs.rglob("*.md") if not any(part.startswith(".") for part in p.parts)
    ) if docs.is_dir() else []
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


# ---------------------------------------------------------------------------
# --action obligation — the accompanying-diagram obligation checker (spec 087)
#
# Read-only by construction (C-002): every function below opens files for reading only,
# creates no directory, touches no mtime and calls no network or engine. The judgement is a
# pure function of --root + --record + --only, so two runs on one input serialise identically
# (C-006). Owner of the vocabulary, the precedence order and the payload shape is
# contracts/diagram-obligation.contract.md (C-001…C-016); this block implements it and
# re-states no rule of its own.
#
# Engine availability is deliberately NOT one of the `not-evaluated` conditions: this checker
# calls no engine at all, so "the engine is down" cannot make a document unjudgeable here
# (C-012). Engine refusal semantics belong to the producing run. A sixth `not-evaluated`
# condition would be an extension of the frozen closed set and is not available to this block.
# ---------------------------------------------------------------------------

# C-003 — the carrier set. Six typed documentation directories read RECURSIVELY (a one-level
# glob loses every nested file: docs/reference/ has 1 first-level document and 64 in total),
# plus docs/ARCHITECTURE.md when it exists. docs/notes/, docs/archive/, docs/.speckit/ and
# site-tooling directories are never carriers — they are invisible, never "passing".
CARRIER_DIRS = ("concepts", "tutorials", "tasks", "reference", "decisions", "contribute")
CARRIER_ROOT_FILE = "ARCHITECTURE.md"
HIDDEN_DOC_PARTS = ("notes", "archive", "node_modules", "site", "assets", ".git")

# C-004 / C-005 — the closed verdict set and its closed reason table (one row per allowed pair).
VERDICT_REASONS = {
    "satisfied": ("reference-resolves",),
    "missing": ("no-diagram-reference", "reference-unresolved", "orphan-source", "orphan-rendered"),
    "stale": ("source-newer-than-render", "render-digest-mismatch"),
    "not-evaluated": ("no-trace-record", "trace-incomplete", "exemption-invalid", "render-unreadable"),
    "recorded-exemption": ("exempt-chronological",),
}

# C-011 — the closed three-value exemption reason set, and the record locations (C-001).
EXEMPTION_REASONS = ("exempt-chronological", "exempt-flat-reference", "exempt-licence")
RUNS_DIR = Path("docs") / ".speckit" / "runs"
EXEMPTIONS_DIR = Path("docs") / ".speckit" / "exemptions"

# C-010 — the requirement set a trace record's `diagrams[]` entry must satisfy.
TRACE_REQUIRED = ("document", "engine", "engine_reason", "ldm_summary", "delivery", "source", "rendered")

# C-010 — the recognisable-diagram suffix set. The extension table is owned by
# `.specify/skills/draw-diagram/references/delivery-contract.md` § D1/D2; this tuple is a projection of
# that table and MUST NOT invent an extension the contract does not carry. Read, in the delivery contract's own
# terms: D1's `.html` entry page; D2's editable sources and the renders it allows beside them; plus the graphviz
# family the delivery path already reached. No engine is named here: this set says which FILE a reader may
# recognise as a diagram face, never which capability produced it (FR-011 keeps the engine table in one place).
DIAGRAM_SUFFIXES = (
    ".html",
    ".svg", ".png", ".pdf",
    ".mmd", ".mermaid", ".puml", ".plantuml", ".excalidraw", ".drawio",
    ".dot", ".gv", ".dotx",
)


def _has_rendered_face(entry: dict | None, rel_path: str) -> bool:
    """True when `rel_path` is one of `entry`'s `rendered[].path` values (C-007 condition 2)."""
    if not entry:
        return False
    for face in entry.get("rendered") or []:
        if face.get("path") == rel_path:
            return True
    return False


def _carrier_files(root: Path) -> list[Path]:
    """Every carrier document under `root`, POSIX-sorted by repository-relative path."""
    docs = root / "docs"
    if not docs.is_dir():
        return []
    found: list[Path] = []
    for name in CARRIER_DIRS:
        base = docs / name
        if not base.is_dir():
            continue
        for path in base.rglob("*.md"):
            rel_parts = path.relative_to(docs).parts
            if any(part.startswith(".") or part in HIDDEN_DOC_PARTS for part in rel_parts[:-1]):
                continue
            if path.is_file():
                found.append(path)
    root_file = docs / CARRIER_ROOT_FILE
    if root_file.is_file():
        found.append(root_file)
    return sorted(found, key=lambda p: rel(root, p))


def _blank_fenced_blocks(text: str) -> str:
    """Replace every fenced code block with one blank line per line it occupied.

    C-005 requires `line` to be the reference's own line. Deleting a block outright (the old
    `re.sub(r"```.*?```", "", text)`) also deletes its newlines, so every later reference shifts upward and the
    reported line sends its reader to the wrong place. Blanking preserves the line count while still keeping
    fenced examples out of the link scan.
    """
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else line)
    return "\n".join(out)


def _relative_links(text: str) -> list[tuple[int, str]]:
    """(1-based line, target) for every relative Markdown link — no http(s), no absolute, no anchors."""
    stripped = _blank_fenced_blocks(text)
    stripped = "\n".join(re.sub(r"`[^`\n]*`", "", line) for line in stripped.splitlines())
    out: list[tuple[int, str]] = []
    for lineno, line in enumerate(stripped.splitlines(), start=1):
        for target in LINK_RE.findall(line):
            bare = target.split("#", 1)[0].strip()
            if not bare or "://" in bare or bare.startswith(("mailto:", "/", "#")):
                continue
            out.append((lineno, bare))
    return out


def _diagram_reference(root: Path, doc: Path) -> tuple[int, Path] | None:
    """The first relative reference from `doc` that names a diagram-shaped file (resolving or not)."""
    try:
        text = doc.read_text(encoding="utf-8")
    except OSError:
        return None
    for lineno, target in _relative_links(text):
        if Path(target).suffix.lower() not in DIAGRAM_SUFFIXES:
            continue
        resolved = Path(os.path.normpath(os.path.join(str(doc.parent), target)))
        return lineno, resolved
    return None


def _record_path(root: Path, record: str) -> Path:
    """The one file `--record` names, resolved **relative to `--root`** (C-010's own convention).

    Only an explicitly absolute value escapes the root; no other candidate is ever tried, so a
    relative value that does not exist under the root is an input error rather than a silent
    fallback to the caller's cwd (C-006 rule 3, `--record` is read, never discovered).
    """
    given = Path(record)
    return given if given.is_absolute() else root / given


def _load_trace_record(root: Path, record: str | None) -> dict | None:
    """Read ONLY the file `--record` names. Never glob `runs/`, never guess the newest (C-006 rule 3)."""
    if not record:
        return None
    path = _record_path(root, record)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(_input_error(f"--record is not readable: {exc}"), file=sys.stderr)
        raise SystemExit(2)
    if not isinstance(payload, dict):
        print(_input_error(f"--record is not a JSON object: {path}"), file=sys.stderr)
        raise SystemExit(2)
    return payload


def _trace_entry_for(record: dict | None, reference_rel: str) -> dict | None:
    """The `diagrams[]` entry that owns the file `reference_rel`, or None.

    A document's diagram reference may point at either face — the render (the normal case) or the
    re-editable source (the orphan case, where the render is gone but the reference was written against
    the source). The entry is therefore matched on its `rendered[].path` **or** its `source`, which is
    what lets the tier-5 face-loss rules distinguish `orphan-rendered` from `orphan-source` at all
    (C-005: the two values are mirror images and MUST NOT be swapped).
    """
    if not record:
        return None
    for entry in record.get("diagrams") or []:
        if entry.get("source") == reference_rel:
            return entry
        for face in entry.get("rendered") or []:
            if face.get("path") == reference_rel:
                return entry
    return None


def _trace_entry_complete(entry: dict) -> bool:
    """C-010 — every required field present and non-empty; `rendered[].path` on every face."""
    if not isinstance(entry.get("delivery"), dict) or entry["delivery"].get("accepted") is None:
        return False
    for key in ("document", "engine", "engine_reason", "ldm_summary", "source"):
        if not entry.get(key):
            return False
    faces = entry.get("rendered")
    if not isinstance(faces, list) or not faces:
        return False
    return all(isinstance(face, dict) and face.get("path") for face in faces)


def _read_exemption(root: Path, doc: Path) -> dict | None:
    """The exemption record for `doc`, parsed; None when no record exists (C-011)."""
    rel_doc = rel(root, doc)
    # C-011's landing is `<root>/docs/.speckit/exemptions/<relative doc path>.md`, and the
    # relative doc path already carries its own `.md` — the record mirrors the document's path.
    # `str.removeprefix` is 3.9+; this script declares and keeps a >=3.8 floor (RS-001).
    suffix = rel_doc[len("docs/"):] if rel_doc.startswith("docs/") else rel_doc
    path = root / EXEMPTIONS_DIR / suffix
    if not path.is_file():
        return None
    fields: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {"_invalid": "unreadable"}
    if not lines or lines[0].strip() != "---":
        return {"_invalid": "no-frontmatter"}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        match = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return {"_invalid": "unterminated-frontmatter"}


def _exemption_status(record: dict | None, rel_doc: str) -> tuple[str, str] | None:
    """(state, reason) where state is absent/valid/invalid, plus the record's own reason when valid."""
    if record is None:
        return None
    if "_invalid" in record:
        return ("invalid", "exemption-invalid")
    if record.get("document") != rel_doc:
        return ("invalid", "exemption-invalid")
    if record.get("reason") not in EXEMPTION_REASONS:
        return ("invalid", "exemption-invalid")
    justification = record.get("justification") or ""
    if len(justification.strip()) < 8:
        return ("invalid", "exemption-invalid")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", record.get("recorded_at") or ""):
        return ("invalid", "exemption-invalid")
    return ("valid", record["reason"])


def _relative_to_root(root: Path, target: Path) -> str | None:
    """`target`'s root-relative POSIX path, or None when it falls outside `root`.

    `Path.is_relative_to` is 3.9+; this script keeps a >=3.8 floor (RS-001), so the containment test is the
    3.8-compatible `relative_to` call with its own exception as the negative answer.
    """
    try:
        return target.relative_to(root).as_posix()
    except ValueError:
        return None


def _file_sha256(path: Path) -> str | None:
    """sha256 of a rendered face, or None when the face cannot be read (C-012's `render-unreadable`).

    The whole file is read rather than a header: a face that is present but unreadable must be distinguishable
    from one that was never there, and the only signal that a read failed is the exception. `known=False` in
    the caller turns this None into `render-unreadable`; a missing face never gets here.
    """
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _judge_document(root: Path, doc: Path, record: dict | None) -> dict:
    """The ordered single pass of C-016. First hit wins; no backtracking, no second overwrite.

    This is the ONLY place a verdict is assigned. Reading it top to bottom reads the contract's
    precedence table top to bottom; a tier only gets to fire when its own precondition holds.
    """
    rel_doc = rel(root, doc)
    verdict = reason = None
    line = 0
    superseded = False

    # tier 1/2 — an exemption record, valid or overturned, is decided before anything else
    exemption = _read_exemption(root, doc)
    status = _exemption_status(exemption, rel_doc)
    reference = _diagram_reference(root, doc)
    if status is not None:
        state, exempt_reason = status
        if state == "valid" and reference is None:
            verdict, reason = "recorded-exemption", exempt_reason
        else:
            # A valid record whose document now carries a diagram-shaped reference has been OVERTURNED by fact;
            # an invalid record is simply unjudgeable — both deny a judgement and land here (C-011, FR-004). Only
            # the former is the "reason no longer holds" signal the summary counts.
            verdict, reason = "not-evaluated", "exemption-invalid"
            superseded = state == "valid"
            if reference is not None:
                line = reference[0]

    # tier 3 — nothing in the document points at a diagram file
    if verdict is None and reference is None:
        verdict, reason = "missing", "no-diagram-reference"

    if verdict is None:
        line, target = reference
        reference_rel = _relative_to_root(root, target)

        # tier 4 — the reference does not resolve to a file on disk
        if not target.is_file():
            verdict, reason = "missing", "reference-unresolved"
        else:
            entry = _trace_entry_for(record, reference_rel) if reference_rel else None
            source = root / entry["source"] if entry and entry.get("source") else None
            faces = [root / face["path"] for face in (entry or {}).get("rendered") or []]

            # tier 5 — a face is missing from a pair whose other face is on disk
            if entry is not None and source is not None:
                source_on_disk = source.is_file()
                rendered_on_disk = any(face.is_file() for face in faces)
                if source_on_disk and not rendered_on_disk:
                    verdict, reason = "missing", "orphan-rendered"
                elif rendered_on_disk and not source_on_disk:
                    verdict, reason = "missing", "orphan-source"

            # tier 6/7 — the record cannot point at this diagram, or there is no record at all
            if verdict is None:
                if record is None:
                    verdict, reason = "not-evaluated", "no-trace-record"
                elif entry is None or not _trace_entry_complete(entry):
                    verdict, reason = "not-evaluated", "trace-incomplete"

            # tier 8 — the record is complete: the two faces are allowed to disagree (C-008)
            if verdict is None:
                # rule 2 is evaluated here, not after rule 1, because an unreadable face is C-012's own
                # `render-unreadable` condition and has to be seen even when rule 1 settles the document:
                # the tiers below THIS one must not mask a closed condition of the one above.
                digests = [(_file_sha256(face_path), face.get("sha256"))
                           for face, face_path in zip(entry.get("rendered") or [], faces)
                           if face.get("sha256")]
                try:
                    source_mtime = source.stat().st_mtime
                except OSError:
                    source_mtime = None
                rendered_mtimes = []
                unreadable = False
                for face in faces:
                    try:
                        rendered_mtimes.append(face.stat().st_mtime)
                    except OSError:
                        unreadable = True
                if unreadable or any(actual is None for actual, _ in digests):
                    verdict, reason = "not-evaluated", "render-unreadable"
                elif source_mtime is not None and rendered_mtimes and source_mtime > min(rendered_mtimes):
                    verdict, reason = "stale", "source-newer-than-render"
                elif any(actual != expected for actual, expected in digests):
                    verdict, reason = "stale", "render-digest-mismatch"

            # tier 6b — a reference that names the EDITABLE SOURCE while the record points at this document is the
            # face-loss reading, not a pass and not an incompleteness: the document must reference a rendered face
            # (FR-005, C-007 condition 2), so a source-only link means the render is what is missing. It therefore
            # lands the paired value `missing` / `orphan-rendered`, above `trace-incomplete` — otherwise a document
            # whose render was deleted would be reported as a record problem instead of naming the missing face
            # (C-005: "失面必须报具名的那一面"; FR-008 / FR-023, SC-002's judgement body).
            if (verdict is None and entry is not None
                    and not _has_rendered_face(entry, reference_rel)):
                verdict, reason = "missing", "orphan-rendered"

            # tier 9 — both faces present, record complete, no staleness rule holding, and the reference names a
            # rendered face. A reference at the editable source is NEVER `satisfied` (C-007 condition 2): the check
            # is on the resolved target, not on whether some entry happens to own it.
            if verdict is None and not _has_rendered_face(entry, reference_rel):
                verdict, reason = "missing", "orphan-rendered"
            if verdict is None:
                verdict, reason = "satisfied", "reference-resolves"

    assert verdict in VERDICT_REASONS, f"verdict {verdict!r} is outside the closed set"
    assert reason in VERDICT_REASONS[verdict], f"reason {reason!r} does not pair with verdict {verdict!r}"
    return {"path": rel_doc, "line": line if verdict not in ("missing",) or line else 0,
            "verdict": verdict, "reason": reason, "_superseded": superseded}


def _resolved_record(root: Path, record: str | None) -> str | None:
    if not record:
        return None
    return str(_record_path(root, record).resolve())


def cmd_obligation(root: Path, record: str | None, only: str | None) -> dict:
    """The read-only obligation judgement. Opens no file for writing (C-002)."""
    trace = _load_trace_record(root, record)
    carriers = _carrier_files(root)
    if only:
        wanted = only.replace(os.sep, "/").lstrip("./")
        carriers = [p for p in carriers if rel(root, p) == wanted]

    documents = [_judge_document(root, path, trace) for path in carriers]
    documents.sort(key=lambda entry: entry["path"])

    counts = {name: 0 for name in ("satisfied", "missing", "stale", "recorded-exemption", "not-evaluated")}
    superseded = 0
    for entry in documents:
        counts[entry["verdict"]] += 1
        if entry.pop("_superseded"):
            superseded += 1

    judged_scope_has_carrier = True if only else len(carriers) > 0
    converged = bool(
        judged_scope_has_carrier
        and counts["missing"] == 0
        and counts["stale"] == 0
        and counts["not-evaluated"] == 0
    )
    clean = bool(converged and counts["recorded-exemption"] == 0)

    return {
        "action": "obligation",
        "root": str(root),
        "record": _resolved_record(root, record),
        "carriers": len(_carrier_files(root)),
        "documents": documents,
        "summary": {
            "satisfied": counts["satisfied"],
            "missing": counts["missing"],
            "stale": counts["stale"],
            "exempted": counts["recorded-exemption"],
            "not_evaluated": counts["not-evaluated"],
            "converged": converged,
            "clean": clean,
            "exemption_superseded": superseded,
        },
    }


def _input_error(message: str) -> str:
    return f"docs-utils.py: error: {message}"


# ---------------------------------------------------------------------------
# End of the read-only obligation block. `cmd_audit` below is a WRITING command of another
# action; it lives after this line so the obligation block's read-only span stays contiguous
# (asserted by `U::test_c002_open_for_write_never_seen`).
# ---------------------------------------------------------------------------


def cmd_audit(root: Path, scope: str, summary: str, items_file: str | None) -> dict:
    audit_dir = root / "docs" / ".speckit" / "audit"
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
                 "fix-links", "audit", "obligation"],
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--yes", action="store_true", help="confirm deletion for clean")
    parser.add_argument("--apply", action="store_true", help="apply fix-links rewrites (default dry-run)")
    parser.add_argument("--moves", default=None, help="JSON file mapping old path prefixes to new (fix-links)")
    parser.add_argument("--scope", default="unspecified", help="audit scope label")
    parser.add_argument("--summary", default="", help="audit summary line")
    parser.add_argument("--items-file", default=None, help="JSON file with audit items")
    parser.add_argument("--record", default=None, metavar="FILE",
                        help="obligation: the one diagram trace record to judge against "
                             "(never globbed, never guessed; absent ⇒ nothing can be satisfied)")
    parser.add_argument("--only", default=None, metavar="DOC",
                        help="obligation: judge this one carrier document instead of the whole space")
    parser.add_argument("--json", action="store_true",
                        help="obligation: readability no-op — every action already prints one JSON object")
    parser.add_argument("--allow-special", action="append", default=None, metavar="NAME",
                        help="additional tool-mandated ALL-CAPS filename to accept at the "
                             "project root (repeatable); extends the ADR-0001 registry "
                             "without editing this engine")
    args = parser.parse_args()

    # The missing-root check is scoped to `obligation` ALONE (C-015): the other actions keep their pre-existing
    # behaviour on an absent root (an empty report, exit 0), so a caller that relies on that reading is not broken
    # by this feature. The obligation branch performs its own check below.
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
        out = cmd_validate(root, set(args.allow_special or []))
    elif args.action == "fix-links":
        out = cmd_fix_links(root, args.moves, args.apply)
    elif args.action == "obligation":
        if not root.is_dir():
            print(_input_error(f"--root does not exist: {args.root}"), file=sys.stderr)
            return 2
        out = cmd_obligation(root, args.record, args.only)
    else:
        out = cmd_audit(root, args.scope, args.summary, args.items_file)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
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

_SIG_FILE = globals().get('__file__')
_SIG_OWNER = _sig_pathlib.Path(_SIG_FILE).resolve().parent if _SIG_FILE else _sig_pathlib.Path('.')
while not ((_SIG_OWNER / 'pyproject.toml').is_file()
           and (_SIG_OWNER / '.git').exists()) and _SIG_OWNER.parent != _SIG_OWNER:
    _SIG_OWNER = _SIG_OWNER.parent
_SIG_OWNER = str(_SIG_OWNER / 'scripts' / 'python')
if _SIG_OWNER not in _sig_sys.path:
    _sig_sys.path.insert(0, _SIG_OWNER)

_SIG_SCRIPT = '.specify/skills/create-docs/scripts/docs-utils.py'
_SIG_DECLARED = ('--action', '--allow-special', '--apply', '--items-file', '--json',
                 '--moves', '--only', '--record', '--root', '--scope', '--summary', '--yes')
_SIG_HELP = (
    'usage: docs-utils.py [options]\n'
    'options:\n'
    '  --action\n  --allow-special\n  --apply\n  --items-file\n  --json\n  --moves\n  --only\n  --record\n  --root\n  --scope\n  --summary\n  --yes\n'
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
    sys.exit(main())
