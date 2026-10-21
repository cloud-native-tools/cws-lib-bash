#!/usr/bin/env python3
"""Feedback-as-files engine for Spec Kit.

Persists local, unit-scoped feedback entries produced at the wrap-up of a
*qualifying* flow (every skill; complex commands only) into the project
feedback store, using plain Markdown files plus a lightweight local JSON index
(no vector store). Patterned on ``memory-utils.py``.

Layout (relative to workspace root):

    .specify/memory/feedback/
        <created-ts>-<unit-slug>.md   # one file per recorded run
        state/<scalar>.json           # one tiny file per store scalar
                                       # (threshold / submitted-at / upstream-repo)
        .gitkeep                      # already present

Conflict-free store discipline (req 055): information that multiple flows
may update concurrently never lives in one shared file. Entries are the
record itself (append-only, one file per run); the entry list is derived
on demand by scanning ``*.md`` frontmatter — never persisted. The only
mutable state is three scalars, each in its own ``state/`` file whose
absence means the default. ``record`` touches nothing but the new entry
file, so concurrent records across branches cannot conflict. A legacy
``index.json`` is read as a read-only fallback and retired (deleted) on
the first mutating action; the return value discloses ``"migrated": true``
when that happened.

An entry's ``unit_id`` must name a Spec Kit command or skill
(``/speckit.<command>`` | ``skill:<name>``); ``record`` rejects any other id.
Each entry is local-scoped (``scope: local``: one unit + one run); a
framework-wide view exists only as the aggregation built over recorded entries.
``/speckit.review`` is a separate SDD-flow mechanism that reviews one feature's
process — not a whole-framework report (boundary owner:
``.specify/shared/workflow/feedback-step.md`` § Mechanism boundary).

Positioning: feedback targets the Spec Kit framework itself (templates,
commands, skills, scripts, docs) — never the LLM, agent CLI, harness, or the
user's project code. Entries are user data: recording and processing are fully
optional and ignorable. This engine performs **no network operations of any
kind**; ``package`` only produces a local zip that the user may send manually,
and ``mark-submitted`` archives the pending batch into ``packages/`` (with an
optional disposition note, ``--notes``) before resetting the local counter
("user confirmed disposition", NOT "uploaded") — a reset therefore always
leaves an auditable package artifact behind.

Identifier discipline: ``--feature`` carries the **requirement key** (e.g.
``038-goal-target``); ``--feature-id`` carries the **Feature registry ID**
(e.g. ``041``). They are different number spaces — never overload one field
with both.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Probe-family functions live in the shared engine (requirement 056). The
# hyphenated engine filename is not import-qualified, so load it by path —
# reusing an already-registered instance (tests load it via script_api) and
# resolving the sibling next to THIS file, which keeps the source copy and the
# .specify mirror each self-consistent.
if "probe_utils" in sys.modules:
    _probe_utils = sys.modules["probe_utils"]
else:
    import importlib.util as _ilutil
    _spec = _ilutil.spec_from_file_location(
        "probe_utils", str(Path(__file__).resolve().parent / "probe-utils.py"))
    _probe_utils = _ilutil.module_from_spec(_spec)
    sys.modules["probe_utils"] = _probe_utils
    _spec.loader.exec_module(_probe_utils)
load_probe_registry = _probe_utils.load_probe_registry
probe_defs_path = _probe_utils.probe_defs_path
resolve_probe = _probe_utils.resolve_probe
_CUSTOM_UNIT_RE = _probe_utils._CUSTOM_UNIT_RE

FEEDBACK_SUBDIR = Path(".specify") / "memory" / "feedback"
PACKAGES_DIRNAME = "packages"
STATE_DIRNAME = "state"
# Legacy single-file index (pre-055): kept only as a read-only fallback
# source for the three store scalars, and deleted on first mutation.
INDEX_NAME = "index.json"
STORE_NAME = "feedback"
DEFAULT_THRESHOLD = 10
NO_OP_POINT = "No significant optimization points identified this run."
DIST_NAME = "specify-cli"

_STATE_FILES = {
    "threshold": "threshold.json",
    "submitted_at": "submitted-at.json",
    "upstream_repo": "upstream-repo.json",
}

# A unit id is valid only when it names a Spec Kit command or skill.
_UNIT_ID_RE = re.compile(r"^(?:/speckit\.[a-z0-9._-]+|skill:[a-z0-9._-]+)$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


class FeedbackError(ValueError):
    """Raised for user-facing validation failures (exit code 2)."""


# --------------------------------------------------------------------------- #
# Helpers (pure)
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def validate_unit_id(unit_id: str) -> bool:
    return bool(unit_id) and bool(_UNIT_ID_RE.match(unit_id.strip()))


def unit_slug(unit_id: str) -> str:
    """`/speckit.plan` -> `speckit-plan`; `skill:study-project` -> `skill-study-project`."""
    slug = _SLUG_RE.sub("-", (unit_id or "").strip().lower()).strip("-")
    return slug or "unit"


def make_summary(review: str) -> str:
    for line in (review or "").splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:200]
    return ""


def count_since_submission(entries: List[Dict[str, Any]], submitted_at: Optional[str]) -> int:
    """Number of entries recorded since the last submission (all when never submitted)."""
    if not submitted_at:
        return len(entries)
    return sum(1 for e in entries if str(e.get("created", "")) > submitted_at)


def should_prompt(count: int, threshold: int) -> bool:
    return count >= threshold


def resolve_threshold(explicit: Optional[int], stored: Optional[int]) -> int:
    if explicit is not None:
        return explicit
    env = os.environ.get("SPECKIT_FEEDBACK_THRESHOLD")
    if env:
        try:
            return int(env)
        except ValueError:
            pass
    if stored is not None:
        return stored
    return DEFAULT_THRESHOLD


def resolve_workspace_root(explicit: Optional[str]) -> Path:
    """Locate the project workspace root that owns the ``.specify/`` store.

    Priority: explicit CLI argument > script self-location (an engine copy
    installed under ``*/.specify/scripts/`` anchors its parent project) >
    nearest CWD ancestor containing ``.specify/`` > CWD itself. Self-location
    must outrank the walk-up: when the agent's CWD sits inside a skill
    directory that contains a stray nested ``.specify/`` (created by an
    earlier bug), the walk-up would capture that nested tree and split the
    store. Falling back to bare CWD is only a last resort outside any project.
    """
    if explicit:
        return Path(explicit).resolve()
    script = Path(__file__).resolve()
    parts = script.parts
    for i, part in enumerate(parts):
        if part == ".specify" and i + 1 < len(parts) and parts[i + 1] == "scripts":
            return Path(*parts[:i])
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".specify").is_dir():
            return candidate
    return cwd


# --------------------------------------------------------------------------- #
# Input reading
# --------------------------------------------------------------------------- #
def read_review(args: argparse.Namespace) -> str:
    if getattr(args, "review", None) is not None:
        return args.review
    if getattr(args, "review_file", None):
        return Path(args.review_file).read_text(encoding="utf-8")
    return ""


def read_points(args: argparse.Namespace) -> List[str]:
    raw = ""
    if getattr(args, "points", None) is not None:
        raw = args.points
    elif getattr(args, "points_file", None):
        raw = Path(args.points_file).read_text(encoding="utf-8")
    points = [line.strip().lstrip("-").strip() for line in raw.splitlines()]
    return [p for p in points if p]


# --------------------------------------------------------------------------- #
# Frontmatter (minimal, dependency-free)
# --------------------------------------------------------------------------- #
def _scalar(value: str) -> Any:
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return value.strip().strip('"')


def dump_frontmatter(meta: Dict[str, Any]) -> str:
    order = ["id", "unit_id", "unit_type", "run_id", "scope",
             "probe", "kind", "slice",
             "feature", "feature_id", "disposition", "migrated_from", "partial", "created", "summary",
             "introspection_ref", "disposition_reason"]
    lines = ["---"]
    for key in order:
        if key not in meta:
            continue
        value = meta[key]
        if value is None or value == "":
            if key not in ("partial",):
                continue
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    meta: Dict[str, Any] = {}
    idx = 1
    while idx < len(lines) and lines[idx].strip() != "---":
        line = lines[idx]
        if ":" in line:
            key, _, raw = line.partition(":")
            meta[key.strip()] = _scalar(raw.strip())
        idx += 1
    body = "\n".join(lines[idx + 1:]) if idx < len(lines) else ""
    return meta, body.lstrip("\n")


def compose_entry(meta: Dict[str, Any], review: str, points: List[str], partial: bool) -> str:
    review_body = review.strip()
    if partial and not review_body.startswith("**Partial run**"):
        review_body = f"**Partial run** — {review_body}"
    bullet_lines = "\n".join(f"- {p}" for p in points)
    body = f"## Review\n{review_body}\n\n## Optimization Points\n{bullet_lines}"
    return dump_frontmatter(meta) + "\n\n" + body.strip() + "\n"


# --------------------------------------------------------------------------- #
# Store / index
# --------------------------------------------------------------------------- #
def feedback_dir(workspace_root: Path) -> Path:
    return Path(workspace_root).resolve() / FEEDBACK_SUBDIR


def ensure_feedback_dir(workspace_root: Path) -> Path:
    target = feedback_dir(workspace_root)
    target.mkdir(parents=True, exist_ok=True)
    return target


def index_path(workspace_root: Path) -> Path:
    return feedback_dir(workspace_root) / INDEX_NAME


def state_dir(workspace_root: Path) -> Path:
    return feedback_dir(workspace_root) / STATE_DIRNAME


def write_text_atomic(path: Path, text: str) -> None:
    part = path.with_name(path.name + ".part")
    part.write_text(text, encoding="utf-8")
    try:
        os.replace(part, path)
    except OSError:
        part.unlink(missing_ok=True)
        raise


def write_state_file(workspace_root: Path, key: str, value: Any) -> None:
    """Persist one store scalar into its own tiny state file (req 055).

    One file per scalar, absence = default: concurrent flows that touch
    different scalars never share a write target.
    """
    filename = _STATE_FILES[key]
    ensure_feedback_dir(workspace_root)
    sdir = state_dir(workspace_root)
    sdir.mkdir(parents=True, exist_ok=True)
    write_text_atomic(sdir / filename, json.dumps({key: value}, ensure_ascii=False) + "\n")


def read_state_file(workspace_root: Path, key: str) -> Any:
    path = state_dir(workspace_root) / _STATE_FILES[key]
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return data.get(key) if isinstance(data, dict) else None


def _read_legacy_index(workspace_root: Path) -> Optional[Dict[str, Any]]:
    path = index_path(workspace_root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return data if isinstance(data, dict) else None


def scan_entries(workspace_root: Path) -> List[Dict[str, Any]]:
    """Derive the entry list from the ``*.md`` files themselves.

    Bookkeeping files (backlog / cleanup-log / migration-log / probe-map / …)
    carry no frontmatter and are skipped by the ``if not meta`` guard.
    """
    target = feedback_dir(workspace_root)
    entries: List[Dict[str, Any]] = []
    if not target.is_dir():
        return entries
    for path in sorted(target.glob("*.md")):
        meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        if not meta:
            continue
        entries.append(entry_meta(meta, path.name))
    entries.sort(key=lambda e: e.get("created", ""), reverse=True)
    return entries


def scan_introspections(workspace_root: Path) -> List[Dict[str, Any]]:
    """Derive the introspection roster from ``introspection/*.md`` frontmatter."""
    target = feedback_dir(workspace_root) / INTROSPECTION_DIRNAME
    records: List[Dict[str, Any]] = []
    if not target.is_dir():
        return records
    for path in sorted(target.glob("*.md")):
        meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
        if not meta or not meta.get("id"):
            continue
        try:
            scope_entries = _list_value(meta.get("scope_entries", []))
        except FeedbackError:
            scope_entries = []
        records.append({
            "id": str(meta.get("id", "")),
            "file": f"{INTROSPECTION_DIRNAME}/{path.name}",
            "created": str(meta.get("created", "")),
            "status": str(meta.get("status", "")),
            "supersedes": meta.get("supersedes") or None,
            "entries": list(scope_entries),
        })
    records.sort(key=lambda r: r.get("created", ""), reverse=True)
    return records


def load_store_state(workspace_root: Path) -> Dict[str, Any]:
    """Scan-derived store truth: entries + introspections + three scalars.

    Scalar precedence: ``state/<scalar>.json`` first; a legacy ``index.json``
    (when present and parseable) is the read-only fallback and sets
    ``legacy: True``. Entries and introspections always come from the scan —
    never from the legacy index — so a stale mirror cannot lie.
    """
    entries = scan_entries(workspace_root)
    introspections = scan_introspections(workspace_root)
    legacy_data = _read_legacy_index(workspace_root)

    def scalar(key: str) -> Any:
        value = read_state_file(workspace_root, key)
        if value is None and legacy_data is not None:
            value = legacy_data.get(key)
        return value

    submitted_at = scalar("submitted_at")
    return {
        "entries": entries,
        "introspections": introspections,
        "threshold": scalar("threshold"),
        "submitted_at": submitted_at,
        "upstream_repo": scalar("upstream_repo"),
        "count_since_submission": count_since_submission(entries, submitted_at),
        "legacy": legacy_data is not None,
    }


def migrate_legacy_index(workspace_root: Path) -> bool:
    """Retire a legacy ``index.json`` (req 055): materialize its scalars into
    ``state/`` files (only when the state file is absent — state wins over a
    legacy value), then delete the index. Idempotent; returns True when a
    legacy index was retired by this call."""
    legacy_data = _read_legacy_index(workspace_root)
    if legacy_data is None:
        return False
    if (legacy_data.get("threshold") is not None
            and read_state_file(workspace_root, "threshold") is None):
        write_state_file(workspace_root, "threshold", legacy_data["threshold"])
    if legacy_data.get("submitted_at") and read_state_file(workspace_root, "submitted_at") is None:
        write_state_file(workspace_root, "submitted_at", legacy_data["submitted_at"])
    if legacy_data.get("upstream_repo") and read_state_file(workspace_root, "upstream_repo") is None:
        write_state_file(workspace_root, "upstream_repo", legacy_data["upstream_repo"])
    try:
        index_path(workspace_root).unlink()
    except OSError:
        pass
    return True


def load_index(workspace_root: Path) -> Dict[str, Any]:
    """Legacy-shape projection of the scan-derived store state.

    Kept for in-process callers (tests, packaging helpers); the values are
    fully derived — ``updated`` is never persisted. Writing this shape back
    is no longer supported (``save_index`` was removed with req 055).
    """
    state = load_store_state(workspace_root)
    return {
        "store": STORE_NAME,
        "updated": None,
        "threshold": (state["threshold"] if state["threshold"] is not None
                      else DEFAULT_THRESHOLD),
        "count_since_submission": state["count_since_submission"],
        "submitted_at": state["submitted_at"],
        "entries": state["entries"],
        "introspections": state["introspections"],
        "upstream_repo": state["upstream_repo"],
    }


def entry_meta(meta: Dict[str, Any], filename: str) -> Dict[str, Any]:
    return {
        "id": meta.get("id", ""),
        "file": filename,
        "unit_id": meta.get("unit_id", ""),
        "unit_type": meta.get("unit_type", ""),
        "run_id": meta.get("run_id", ""),
        "probe": meta.get("probe", ""),
        "kind": meta.get("kind", ""),
        "slice": meta.get("slice", ""),
        "feature": meta.get("feature", ""),
        "feature_id": meta.get("feature_id", ""),
        "disposition": meta.get("disposition", ""),
        "introspection_ref": meta.get("introspection_ref", ""),
        "disposition_reason": meta.get("disposition_reason", ""),
        "partial": bool(meta.get("partial", False)),
        "created": meta.get("created", ""),
        "summary": meta.get("summary", ""),
    }


# --------------------------------------------------------------------------- #
# Introspection reports (requirement 047)
# --------------------------------------------------------------------------- #
INTROSPECTION_DIRNAME = "introspection"
_REPORT_ID_RE = re.compile(r"^introspection-[0-9TZ-]+$")
_REPORT_FIELDS = ("id", "created", "status", "scope_filter", "scope_entries",
                  "supersedes", "confirmed_at")
_REPORT_STATUSES = ("draft", "confirmed", "superseded")
_FINDING_HEAD_RE = re.compile(r"^### (F-\d{2,}): (.+)$")
_FINDING_FIELD_RES = {
    "root_cause": re.compile(r"^- \*\*根因\*\*: (.+)$"),
    "evidence": re.compile(r"^- \*\*证据锚点\*\*: (.+)$"),
    "members": re.compile(r"^- \*\*成员条目\*\*: (.+)$"),
    "routing": re.compile(r"^- \*\*分流决定\*\*: (local-sink|upstream-bound)\(([^)]+)\)\s*$"),
    "proposal": re.compile(r"^- \*\*优化方案\*\*: (.+)$"),
    "override": re.compile(r"^- \*\*用户覆盖\*\*: (.+)$"),
    "suggestions": re.compile(r"^- \*\*建议处置\*\*: (.+)$"),
}
_MEMBER_RE = re.compile(r"([0-9A-Za-z-]+)\((成立|部分成立|已过时|不成立)\)")
_SUGGESTION_RE = re.compile(r"([0-9A-Za-z-]+):(processed|ignored)")
_EXCLUDED_RE = re.compile(r"^- ([0-9A-Za-z-]+) — (.+)$")
_INTROSPECTION_REF_RE = re.compile(r"^introspection-[0-9TZ-]+#F-\d{2,}$")


def _list_value(raw: Any) -> List[str]:
    """Parse a scope_entries value: JSON list preferred, ast.literal_eval as
    fallback for hand-written single-quoted lists."""
    import ast
    if isinstance(raw, list):
        items = raw
    else:
        text = str(raw).strip()
        try:
            items = json.loads(text)
        except ValueError:
            try:
                items = ast.literal_eval(text)
            except (ValueError, SyntaxError):
                raise FeedbackError(
                    f"scope_entries is not a list: {text[:60]!r}")
    if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
        raise FeedbackError("scope_entries must be a list of entry-id strings")
    return items


def _parse_finding_block(block: str) -> Dict[str, Any]:
    lines = block.splitlines()
    head = _FINDING_HEAD_RE.match(lines[0].strip())
    finding: Dict[str, Any] = {
        "finding_id": head.group(1), "statement": head.group(2).strip(),
        "root_cause": None, "evidence": None, "members": [],
        "routing": None, "proposal": None, "override": None,
        "suggestions": {},
    }
    seen: set = set()
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        for key, rx in _FINDING_FIELD_RES.items():
            m = rx.match(stripped)
            if not m:
                continue
            if key in seen:
                raise FeedbackError(
                    f"duplicate field {key} in finding {finding['finding_id']} (C-7)")
            seen.add(key)
            if key == "members":
                finding["members"] = _MEMBER_RE.findall(m.group(1))
                if not finding["members"]:
                    raise FeedbackError(
                        f"no parseable members in finding {finding['finding_id']} (C-7)")
            elif key == "routing":
                finding["routing"] = (m.group(1), m.group(2).strip())
            elif key == "suggestions":
                finding["suggestions"] = dict(_SUGGESTION_RE.findall(m.group(1)))
            else:
                finding[key] = m.group(1).strip()
            break
        else:
            raise FeedbackError(
                f"unknown finding field line in {finding['finding_id']}: "
                f"{stripped[:60]!r} (C-7)")
    for key, label in (("root_cause", "根因"), ("evidence", "证据锚点"),
                       ("routing", "分流决定"), ("proposal", "优化方案")):
        if not finding[key]:
            raise FeedbackError(
                f"finding {finding['finding_id']} missing {label} (C-9/V-2)")
    if not finding["members"]:
        raise FeedbackError(
            f"finding {finding['finding_id']} missing 成员条目 (C-7)")
    return finding


def parse_report(path: Path) -> Dict[str, Any]:
    """Parse + structurally validate an introspection report (C-1..C-9).

    Raises FeedbackError on any structural violation.
    """
    path = Path(path)
    if path.parent.name != INTROSPECTION_DIRNAME:
        raise FeedbackError(
            f"report must live under {INTROSPECTION_DIRNAME}/ (C-1/C-2): {path}")
    stem = path.stem
    if not _REPORT_ID_RE.match(stem):
        raise FeedbackError(f"invalid report filename (C-1): {path.name}")
    meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    missing = [f for f in _REPORT_FIELDS if f not in meta]
    unknown = [f for f in meta if f not in _REPORT_FIELDS]
    if missing:
        raise FeedbackError(f"report frontmatter missing fields (C-4): {missing}")
    if unknown:
        raise FeedbackError(f"report frontmatter unknown fields (C-4): {unknown}")
    if meta["id"] != stem:
        raise FeedbackError(
            f"report id {meta['id']!r} != filename stem {stem!r} (C-5)")
    if meta["status"] not in _REPORT_STATUSES:
        raise FeedbackError(f"invalid report status (C-4): {meta['status']!r}")
    scope_entries = _list_value(meta["scope_entries"])
    if len(scope_entries) != len(set(scope_entries)):
        raise FeedbackError("scope_entries contains duplicates (C-5)")
    meta["scope_entries"] = scope_entries

    marker_f = body.find("## Findings")
    marker_e = body.find("## Excluded")
    if not body.lstrip().startswith(f"# Introspection Report: {stem}"):
        raise FeedbackError("missing/mismatched H1 title (C-6)")
    if marker_f < 0 or marker_e < 0 or marker_f > marker_e:
        raise FeedbackError("sections must be: H1 → ## Findings → ## Excluded (C-6)")

    findings_text = body[marker_f + len("## Findings"):marker_e]
    blocks: List[str] = []
    current: List[str] = []
    for line in findings_text.splitlines():
        if _FINDING_HEAD_RE.match(line.strip()):
            if current:
                blocks.append("\n".join(current))
            current = [line.strip()]
        elif current:
            current.append(line)
    if current:
        blocks.append("\n".join(current))
    if not blocks:
        raise FeedbackError("report has no findings (C-6)")
    findings = [_parse_finding_block(b) for b in blocks]
    expected_ids = [f"F-{i + 1:02d}" for i in range(len(findings))]
    actual_ids = [f["finding_id"] for f in findings]
    if actual_ids != expected_ids:
        raise FeedbackError(
            f"finding ids must be sequential from F-01 (C-7): {actual_ids}")

    excluded: List[Tuple[str, str]] = []
    excluded_text = body[marker_e + len("## Excluded"):]
    for line in excluded_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "无":
            continue
        m = _EXCLUDED_RE.match(stripped)
        if not m:
            raise FeedbackError(f"malformed Excluded row (C-8): {stripped[:60]!r}")
        excluded.append((m.group(1), m.group(2).strip()))

    return {"meta": meta, "findings": findings, "excluded": excluded,
            "path": path}


def validate_report(workspace_root: Path, report: Dict[str, Any]) -> List[str]:
    """Semantic validation against the store: V-1 coverage, V-3 existence,
    V-4 external constraint, C-10 supersession. Returns violation strings."""
    workspace_root = Path(workspace_root).resolve()
    violations: List[str] = []
    index = load_index(workspace_root)
    known = {e.get("id"): e for e in index.get("entries", [])}
    meta = report["meta"]
    scope = set(meta["scope_entries"])

    members: List[str] = []
    for finding in report["findings"]:
        members.extend(eid for eid, _verdict in finding["members"])
    excluded_ids = [eid for eid, _reason in report["excluded"]]
    covered = set(members) | set(excluded_ids)
    if covered != scope:
        violations.append(
            f"V-1 coverage mismatch: uncovered={sorted(scope - covered)}, "
            f"out_of_scope={sorted(covered - scope)}")
    if len(members) != len(set(members)):
        violations.append("V-1 duplicate membership across findings")

    for eid in sorted(scope):
        if eid not in known:
            violations.append(f"V-3 unknown entry id: {eid}")

    for finding in report["findings"]:
        direction, _channel = finding["routing"]
        if direction == "upstream-bound":
            external_members = [eid for eid, _v in finding["members"]
                                if known.get(eid, {}).get("kind") == "external"]
            if external_members:
                violations.append(
                    f"V-4 external entries in upstream-bound finding "
                    f"{finding['finding_id']}: {external_members}")

    supersedes = meta.get("supersedes")
    if supersedes:
        prior = (feedback_dir(workspace_root) / INTROSPECTION_DIRNAME
                 / f"{supersedes}.md")
        known_reports = {r.get("id") for r in index.get("introspections", [])}
        if not prior.is_file() and supersedes not in known_reports:
            violations.append(f"C-10 supersedes target not found: {supersedes}")
    return violations


def _dump_report(meta: Dict[str, Any]) -> str:
    """Frontmatter dump with the report field order; CJK unescaped (C-3)."""
    lines = ["---"]
    for key in _REPORT_FIELDS:
        lines.append(f"{key}: {json.dumps(meta.get(key), ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def write_report(path: Path, report: Dict[str, Any]) -> None:
    """Rewrite a report file's frontmatter (status transitions); body untouched."""
    path = Path(path)
    _meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    path.write_text(
        _dump_report(report["meta"]) + "\n\n" + body.strip() + "\n",
        encoding="utf-8")


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #
# Argument manifest (063 C-22): per-action required/source classification.
# "required" = flags this engine itself validates as required (the same
# classification the one-shot missing-argument check consumes — C-23);
# "source" = this engine's DECLARED run-evidence input set (undeclared = []).
# `--action args-manifest` verifies every listed flag against build_parser()'s
# LIVE option strings before emitting — the parser stays the single source of
# truth; the compile-embeds renderer consumes this and holds no table of its
# own (063 C-21).
ARG_MANIFEST = {
    "record": {
        "required": ["--unit-id", "--run-id", "--review", "--points"],
        "source": [],
    },
    "status": {"required": [], "source": []},
    "list": {"required": [], "source": ["--since", "--limit", "--contains",
                                        "--slice", "--kind", "--disposition"]},
    "dispose": {"required": ["--id", "--to"],
                "source": ["--reason", "--ref"]},
    "mark-submitted": {"required": [], "source": ["--notes"]},
    "reindex": {"required": [], "source": []},
    "package": {"required": [], "source": ["--include-introspection", "--all"]},
    "cleanup": {"required": ["--package"], "source": ["--dry-run"]},
    "upstream": {"required": [], "source": ["--set"]},
    "migrate-legacy": {"required": ["--plan-file"], "source": []},
    "introspect-register": {"required": ["--report-file"], "source": ["--confirm"]},
    "args-manifest": {"required": [], "source": []},
}

# One-shot missing-argument error tails (C-23): the load-bearing guidance the
# old sequential errors carried, kept per slot inside the SINGLE message.
_RECORD_MISSING_GUIDANCE = {
    "--unit-id": ("expected '/speckit.<command>', 'skill:<name>' or "
                  "'custom:<owner>/<name>'"),
    "--run-id": "the entry key is (unit_id, run_id)",
    "--review / --review-file": "record requires a non-empty review",
    "--points / --points-file": "at least one line; use '{NO_OP_POINT}' for a clean run",
}


def action_record(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    unit_id = (args.unit_id or "").strip()
    unit_type = (args.unit_type or "").strip()
    # C-23 (063): collect EVERY missing required argument first, then raise ONE
    # FeedbackError naming them all — replaces the sequential one-at-a-time
    # checks; the input-error exit code stays 2.
    missing: List[str] = []
    if not unit_id:
        missing.append("--unit-id")
    run_id = (args.run_id or "").strip()
    if not run_id:
        missing.append("--run-id")
    review = read_review(args)
    if not review.strip():
        missing.append("--review / --review-file")
    points = read_points(args)
    if not points:
        missing.append("--points / --points-file")
    if missing:
        raise FeedbackError(
            "record is missing required arguments: "
            + "; ".join(
                f"{slot} ({_RECORD_MISSING_GUIDANCE[slot].format(NO_OP_POINT=NO_OP_POINT)})"
                for slot in missing))
    if unit_id.startswith("custom:"):
        if not _CUSTOM_UNIT_RE.match(unit_id):
            raise FeedbackError(
                "Invalid --unit-id; expected 'custom:<owner>/<name>'.")
        if unit_type != "custom-unit":
            raise FeedbackError("--unit-type must be 'custom-unit' for custom: units.")
    else:
        if not validate_unit_id(unit_id):
            raise FeedbackError(
                "Invalid --unit-id; expected '/speckit.<command>' or 'skill:<name>'."
            )
        if unit_type == "custom-unit":
            raise FeedbackError(
                "--unit-type 'custom-unit' requires a 'custom:' --unit-id.")
        if unit_type not in ("skill", "command"):
            raise FeedbackError("--unit-type must be 'skill' or 'command'.")

    # Probe resolution (requirement 041): with the registry installed, every
    # entry MUST carry probe attribution (engine-resolved; never caller-set).
    # Registry absent (un-upgraded workspace) → legacy record without fields.
    registry = load_probe_registry(workspace_root)
    probe = None
    if registry["available"]:
        lifecycle_point = (getattr(args, "lifecycle_point", None) or "").strip() or None
        probe = resolve_probe(registry, unit_id, lifecycle_point)
        if probe is None:
            if lifecycle_point:
                raise FeedbackError(
                    f"no probe object for unit: {unit_id} "
                    f"with lifecycle_point: {lifecycle_point}"
                )
            raise FeedbackError(f"no probe object for unit: {unit_id}")

    state = load_store_state(workspace_root)
    stored_threshold = state["threshold"]
    threshold = resolve_threshold(args.threshold, stored_threshold)
    entries = state["entries"]

    existing = next(
        (e for e in entries if e.get("unit_id") == unit_id and e.get("run_id") == run_id),
        None,
    )
    if existing:
        rel = (FEEDBACK_SUBDIR / existing["file"]).as_posix()
        count = state["count_since_submission"]
        return {
            "id": existing.get("id", ""),
            "path": rel,
            "duplicate": True,
            "count_since_submission": count,
            "threshold": threshold,
            "should_prompt": should_prompt(count, threshold),
            "migrated": False,
        }

    created = now_iso()
    slug = unit_slug(unit_id)
    entry_id = f"{timestamp_id()}-{slug}"
    target_dir = ensure_feedback_dir(workspace_root)
    filename = f"{entry_id}.md"
    counter = 1
    while (target_dir / filename).exists():
        filename = f"{entry_id}-{counter}.md"
        counter += 1
    entry_id = filename[:-3]

    partial = bool(args.partial)
    meta = {
        "id": entry_id,
        "unit_id": unit_id,
        "unit_type": unit_type,
        "run_id": run_id,
        "scope": "local",
        "feature": (args.feature or "").strip(),
        "feature_id": (getattr(args, "feature_id", "") or "").strip(),
        "partial": partial,
        "created": created,
        "summary": make_summary(review),
    }
    if probe is not None:
        meta["probe"] = probe["object_id"]
        meta["kind"] = probe["kind"]
        meta["slice"] = probe["slice"]
    (target_dir / filename).write_text(
        compose_entry(meta, review, points, partial), encoding="utf-8"
    )

    # FR-003 (req 055): persist a threshold only when explicitly requested and
    # different from what is stored — resolution from env/defaults stays
    # ephemeral, so concurrent records never fight over this file.
    if args.threshold is not None and args.threshold != stored_threshold:
        write_state_file(workspace_root, "threshold", threshold)

    migrated = migrate_legacy_index(workspace_root)
    count = state["count_since_submission"] + 1
    rel = (FEEDBACK_SUBDIR / filename).as_posix()
    return {
        "id": entry_id,
        "path": rel,
        "duplicate": False,
        "count_since_submission": count,
        "threshold": threshold,
        "should_prompt": should_prompt(count, threshold),
        "migrated": migrated,
    }


def action_status(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    state = load_store_state(workspace_root)
    threshold = resolve_threshold(args.threshold, state["threshold"])
    count = state["count_since_submission"]
    entries = state["entries"]
    return {
        "count_since_submission": count,
        "threshold": threshold,
        "should_prompt": should_prompt(count, threshold),
        "total_entries": len(entries),
        "submitted_at": state["submitted_at"],
        "legacy_remaining": sum(1 for e in entries if not e.get("probe")),
        "external_count": sum(1 for e in entries if e.get("kind") == "external"),
        "legacy": state["legacy"],
    }


def action_list(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    limit = None if args.limit == 0 else max(1, args.limit)
    unit_id = (args.unit_id or "").strip()
    unit_type = (args.unit_type or "").strip()
    since = (args.since or "").strip()
    contains = (args.contains or "").strip().lower()
    slice_filter = (getattr(args, "slice", None) or "").strip()
    kind_filter = (getattr(args, "kind", None) or "").strip()
    disposition = (getattr(args, "disposition", None) or "").strip()

    items: List[Dict[str, Any]] = []
    for entry in load_store_state(workspace_root)["entries"]:
        if unit_id and entry.get("unit_id") != unit_id:
            continue
        if unit_type and entry.get("unit_type") != unit_type:
            continue
        if since and str(entry.get("created", "")) < since:
            continue
        if slice_filter and entry.get("slice", "") != slice_filter:
            continue
        if kind_filter and entry.get("kind", "") != kind_filter:
            continue
        if disposition:
            current = entry.get("disposition", "") or "open"
            if current != disposition:
                continue
        if contains:
            haystack = str(entry.get("summary", ""))
            entry_file = feedback_dir(workspace_root) / entry.get("file", "")
            if entry_file.is_file():
                haystack += "\n" + entry_file.read_text(encoding="utf-8")
            if contains not in haystack.lower():
                continue
        item = dict(entry)
        item["path"] = (FEEDBACK_SUBDIR / entry["file"]).as_posix()
        items.append(item)
    items.sort(key=lambda e: e.get("created", ""), reverse=True)
    matches = items if limit is None else items[:limit]
    return {"count": len(matches), "matches": matches}


_VALID_DISPOSITIONS = ("processed", "ignored")


def action_dispose(args: argparse.Namespace) -> Dict[str, Any]:
    """Mark one entry's disposition (local metadata; body never rewritten)."""
    workspace_root = resolve_workspace_root(args.workspace_root)
    target_state = (getattr(args, "to", None) or "").strip()
    if target_state not in _VALID_DISPOSITIONS:
        raise FeedbackError(
            "--to must be one of " + " | ".join(_VALID_DISPOSITIONS) + ".")
    entry_id = (getattr(args, "id", None) or "").strip()
    if not entry_id:
        raise FeedbackError("--id is required.")
    reason = (getattr(args, "reason", None) or "").strip()
    ref = (getattr(args, "ref", None) or "").strip()
    if ref and not _INTROSPECTION_REF_RE.match(ref):
        raise FeedbackError(
            "--ref must match introspection-<ts>#F-<nn> (engine-cli C-8).")
    entries = load_store_state(workspace_root)["entries"]
    for entry in entries:
        if entry.get("id") != entry_id:
            continue
        entry_file = feedback_dir(workspace_root) / entry.get("file", "")
        if entry_file.is_file():
            meta, body = parse_frontmatter(entry_file.read_text(encoding="utf-8"))
            meta["disposition"] = target_state
            if reason:
                meta["disposition_reason"] = reason
            if ref:
                meta["introspection_ref"] = ref
            write_text_atomic(
                entry_file,
                dump_frontmatter(meta) + "\n\n" + body.strip() + "\n",
            )
        migrated = migrate_legacy_index(workspace_root)
        return {"id": entry_id, "disposition": target_state, "migrated": migrated}
    raise FeedbackError(f"no entry with id: {entry_id}")


def action_mark_submitted(args: argparse.Namespace) -> Dict[str, Any]:
    """Archive the pending batch, then reset the local counter.

    Every reset leaves an auditable package artifact behind (F2): the entries
    accumulated since the last submission are zipped into ``packages/`` before
    the counter resets. An optional ``--notes`` disposition summary is stored
    inside the archive as ``SUBMISSION-NOTES.md`` (F3). This is purely local
    bookkeeping — it does NOT upload or transmit anything.
    """
    workspace_root = resolve_workspace_root(args.workspace_root)
    state = load_store_state(workspace_root)
    reset_from = state["count_since_submission"]

    submitted_at = state["submitted_at"]
    entries = state["entries"]
    if submitted_at:
        selected = [e for e in entries if str(e.get("created", "")) > submitted_at]
    else:
        selected = list(entries)
    selected.sort(key=lambda e: e.get("created", ""))
    package = write_package(workspace_root, {
        "upstream_repo": state["upstream_repo"],
        "introspections": state["introspections"],
    }, selected,
        notes=getattr(args, "notes", None))

    new_submitted_at = now_iso()
    write_state_file(workspace_root, "submitted_at", new_submitted_at)
    migrated = migrate_legacy_index(workspace_root)
    return {
        "submitted_at": new_submitted_at,
        "reset_from": reset_from,
        "packaged": package.get("packaged", 0),
        "zip": package.get("zip"),
        "migrated": migrated,
    }


def action_reindex(args: argparse.Namespace) -> Dict[str, Any]:
    """Explicit store reconciliation and migration entry point (req 055).

    The entry list is always derived from the ``*.md`` files, so reindex is
    a no-op for entries; what it materializes are the store scalars into
    ``state/`` and the retirement of a legacy ``index.json``. Idempotent —
    a second run reports ``migrated: false`` and writes nothing.
    """
    workspace_root = resolve_workspace_root(args.workspace_root)
    state = load_store_state(workspace_root)
    if args.threshold is not None and args.threshold != state["threshold"]:
        write_state_file(workspace_root, "threshold", args.threshold)
    migrated = migrate_legacy_index(workspace_root)
    entries = scan_entries(workspace_root)
    return {"reindexed": len(entries), "migrated": migrated}


# --------------------------------------------------------------------------- #
# Upstream detection / packaging (no network operations — red line)
# --------------------------------------------------------------------------- #
def _speckit_version() -> str:
    try:
        from importlib import metadata
        return metadata.version(DIST_NAME)
    except Exception:
        return "unknown"


def detect_upstream(index: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve the upstream repo URL for manual feedback delivery.

    Priority: user-configured ``upstream_repo`` ( callers pass the scan-derived
    store state / ``state/upstream-repo.json`` value) > PEP 610
    ``direct_url.json`` install metadata (records the git URL the custom
    spec-kit build was installed from) > none (user must ``--set``).
    Detection only reads local files; it never touches the network.
    """
    configured = (index.get("upstream_repo") or "").strip()
    if configured:
        return {"url": configured, "source": "configured", "commit": None}
    try:
        from importlib import metadata
        raw = metadata.distribution(DIST_NAME).read_text("direct_url.json")
        if raw:
            data = json.loads(raw)
            url = (data.get("url") or "").strip()
            vcs = data.get("vcs_info") or {}
            if url and vcs.get("vcs") == "git":
                return {
                    "url": url,
                    "source": "install-metadata",
                    "commit": vcs.get("commit_id"),
                }
    except Exception:
        pass
    return {"url": None, "source": None, "commit": None}


def _send_guidance(upstream: Dict[str, Any]) -> List[str]:
    url = upstream.get("url")
    if not url:
        return [
            "Upstream repo unknown — set it once via: "
            "--action upstream --set <repo-url>",
            "Then send the zip manually (issue attachment or MR); "
            "this engine never sends anything itself.",
        ]
    host_kind = "GitHub" if "github" in url.lower() else "GitLab"
    if host_kind == "GitHub":
        how = "open an issue on the upstream repo and attach the zip"
    else:
        how = ("open an issue and attach the zip, or submit an MR adding it "
               "under the repo's feedback intake directory")
    return [
        f"Send the zip manually to the upstream repo ({host_kind}): {url}",
        f"Suggested: {how}.",
        "Sending is entirely manual and optional — this engine performs no "
        "network operations.",
    ]


def action_upstream(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    state = load_store_state(workspace_root)
    set_url = (args.set_url or "").strip()
    if set_url:
        write_state_file(workspace_root, "upstream_repo", set_url)
        migrate_legacy_index(workspace_root)
    return detect_upstream({"upstream_repo": set_url or state["upstream_repo"]})


def write_package(
    workspace_root: Path,
    index: Dict[str, Any],
    selected: List[Dict[str, Any]],
    notes: Optional[str] = None,
    include_introspection: bool = False,
) -> Dict[str, Any]:
    """Zip ``selected`` entries into ``packages/``; source files are never touched.

    When ``notes`` is given, a ``SUBMISSION-NOTES.md`` disposition record is
    added to the archive so every counter reset leaves auditable context.
    When ``include_introspection`` is set, introspection reports referenced by
    the selected entries ride along under ``introspection/`` and are listed in
    a MANIFEST section (engine-cli C-9..C-12).
    """
    upstream = detect_upstream(index)
    if not selected:
        return {"packaged": 0, "zip": None, "missing": [], "upstream": upstream,
                "note": "No feedback entries to package."}

    store_dir = feedback_dir(workspace_root)
    packages_dir = store_dir / PACKAGES_DIRNAME
    packages_dir.mkdir(parents=True, exist_ok=True)
    zip_name = f"feedback-{timestamp_id()}.zip"
    zip_path = packages_dir / zip_name
    counter = 1
    while zip_path.exists():
        zip_path = packages_dir / f"feedback-{timestamp_id()}-{counter}.zip"
        counter += 1

    manifest_lines = [
        "# Feedback Package Manifest",
        "",
        "> This feedback targets the Spec Kit framework itself (templates, "
        "commands, skills, scripts, docs) — not the LLM, agent CLI, harness, "
        "or any user project code.",
        "",
        f"- **Generated**: {now_iso()}",
        f"- **Entries**: {len(selected)}",
        f"- **Time range**: {selected[0].get('created', '-')} → "
        f"{selected[-1].get('created', '-')}",
        f"- **spec-kit version**: {_speckit_version()}",
        f"- **Install source**: {upstream.get('url') or 'unknown'}"
        + (f" @ {upstream['commit']}" if upstream.get("commit") else ""),
        "",
        "| Created | Unit | Partial | Probe | Slice | Summary |",
        "|---------|------|---------|-------|-------|---------|",
    ]
    missing: List[str] = []
    packaged: List[str] = []
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for entry in selected:
            src = store_dir / entry["file"]
            if not src.exists():
                missing.append(entry["file"])
                continue
            zf.write(src, arcname=entry["file"])  # read-only: sources untouched
            packaged.append(entry["file"])
            summary = str(entry.get("summary", "")).replace("|", "\\|")[:120]
            manifest_lines.append(
                f"| {entry.get('created', '-')} | {entry.get('unit_id', '?')} "
                f"| {entry.get('partial', False)} | {entry.get('probe', '-') or '-'} "
                f"| {entry.get('slice', '-') or '-'} | {summary} |"
            )
        report_ids: List[str] = []
        if include_introspection:
            for entry in selected:
                ref = entry.get("introspection_ref", "") or ""
                rid = ref.split("#", 1)[0]
                if rid and rid not in report_ids:
                    report_ids.append(rid)
            if report_ids:
                report_status = {r.get("id"): r.get("status", "?")
                                 for r in index.get("introspections", [])}
                manifest_lines += ["", "## Introspection Reports", "",
                                   "| Report | Linked Entries | Status |",
                                   "|--------|----------------|--------|"]
                for rid in report_ids:
                    rfile = store_dir / INTROSPECTION_DIRNAME / f"{rid}.md"
                    linked_n = sum(
                        1 for e in selected
                        if (e.get("introspection_ref") or "").startswith(rid + "#"))
                    if rfile.is_file():
                        zf.write(rfile,
                                 arcname=f"{INTROSPECTION_DIRNAME}/{rid}.md")
                        status = report_status.get(rid, "?")
                    else:
                        status = f"{report_status.get(rid, '?')} (missing)"
                    manifest_lines.append(
                        f"| {rid} | {linked_n} | {status} |")
        zf.writestr("MANIFEST.md", "\n".join(manifest_lines) + "\n")
        if notes and notes.strip():
            zf.writestr(
                "SUBMISSION-NOTES.md",
                "# Submission Notes (disposition of this batch)\n\n"
                f"- **Recorded**: {now_iso()}\n\n{notes.strip()}\n",
            )

    rel_zip = zip_path.relative_to(workspace_root).as_posix()
    return {"packaged": len(packaged), "zip": rel_zip, "missing": missing,
            "upstream": upstream}


def action_package(args: argparse.Namespace) -> Dict[str, Any]:
    """Zip pending entries for manual delivery. Source files are never touched.

    External entries (``kind: external``) are host-project-local by contract
    (engine-cli C-4): they are excluded from the upstream package and only
    surfaced as an ``excluded_external`` count.
    """
    workspace_root = resolve_workspace_root(args.workspace_root)
    state = load_store_state(workspace_root)
    submitted_at = state["submitted_at"]
    entries = state["entries"]
    if not args.all and submitted_at:
        selected = [e for e in entries if str(e.get("created", "")) > submitted_at]
    else:
        selected = list(entries)
    selected.sort(key=lambda e: e.get("created", ""))
    excluded_external = sum(1 for e in selected if e.get("kind") == "external")
    selected = [e for e in selected if e.get("kind") != "external"]

    result = write_package(workspace_root, {
        "upstream_repo": state["upstream_repo"],
        "introspections": state["introspections"],
    }, selected,
                           include_introspection=bool(
                               getattr(args, "include_introspection", False)))
    result["excluded_external"] = excluded_external
    if not result.get("zip"):
        result["upstream"] = detect_upstream(
            {"upstream_repo": state["upstream_repo"]})
        return result
    result["next_steps"] = _send_guidance(result["upstream"]) + [
        "After you have dealt with the batch (sent or deliberately ignored), "
        "reset the local counter: --action mark-submitted"]
    return result


CLEANUP_LOG_NAME = "cleanup-log.md"


def action_cleanup(args: argparse.Namespace) -> Dict[str, Any]:
    """Post-package cleanup (req 041; /speckit.feedback Path B): remove entries
    that a package already archived — the zip is the record; the active store
    converges.

    Scope is strictly the packaged batch (engine-cli C-5): only entry files
    actually inside the named zip are removed, never un-packaged entries.
    """
    workspace_root = resolve_workspace_root(args.workspace_root)
    packages_dir = feedback_dir(workspace_root) / PACKAGES_DIRNAME
    spec = (getattr(args, "package", None) or "").strip()
    if spec == "latest":
        zips = sorted(packages_dir.glob("feedback-*.zip")) if packages_dir.is_dir() else []
        if not zips:
            raise FeedbackError(f"no packages found under {packages_dir}")
        zip_path = zips[-1]
    else:
        if not spec:
            raise FeedbackError("--package <zip-path|latest> is required.")
        zip_path = Path(spec)
        if not zip_path.is_absolute():
            zip_path = workspace_root / spec
    if not zip_path.is_file():
        raise FeedbackError(f"package not found: {zip_path}")

    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        if "MANIFEST.md" not in names:
            raise FeedbackError(f"package has no MANIFEST.md: {zip_path}")
        packaged = {n for n in names if n.endswith(".md")
                    and n not in ("MANIFEST.md", "SUBMISSION-NOTES.md")}

    entries = load_store_state(workspace_root)["entries"]
    targeted = [e for e in entries if e.get("file") in packaged]
    dry_run = bool(getattr(args, "dry_run", False))
    removed: List[str] = []
    migrated = False
    if not dry_run:
        store = feedback_dir(workspace_root)
        for entry in targeted:
            source = store / entry["file"]
            if source.is_file():
                source.unlink()
            removed.append(entry.get("id", entry["file"]))
        migrated = migrate_legacy_index(workspace_root)
        log_path = store / CLEANUP_LOG_NAME
        stamp = now_iso()
        lines = [f"## {stamp} — {zip_path.name}"]
        for entry in targeted:
            lines.append(
                f"- removed {entry.get('id', '?')} ({entry.get('unit_id', '?')}, "
                f"created {entry.get('created', '-')}) — archived in "
                f"{zip_path.name}")
        with log_path.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    would_remove = [e.get("id", e["file"]) for e in targeted]
    remaining_entries = len(scan_entries(workspace_root))
    return {
        "package": zip_path.relative_to(workspace_root).as_posix()
        if zip_path.is_relative_to(workspace_root) else str(zip_path),
        "dry_run": dry_run,
        "would_remove": would_remove if dry_run else [],
        "would_remove_count": len(would_remove),
        "removed": removed,
        "remaining_entries": remaining_entries,
        # A dry run never touches the store, so the post-cleanup figure has to be
        # projected here — otherwise the summary keys read as "nothing changes".
        "remaining_after": remaining_entries - len(would_remove) if dry_run else remaining_entries,
        "migrated": migrated,
    }


MIGRATION_LOG_NAME = "migration-log.md"


def action_migrate_legacy(args: argparse.Namespace) -> Dict[str, Any]:
    """One-shot legacy-entry convergence (req 041, engine-cli C-8).

    The plan file (agent-produced, user-confirmed) carries one directive per
    line: ``<entry-id> -> delete | re-register``. The engine only executes;
    it never decides dispositions itself. Every outcome lands in
    ``migration-log.md``.
    """
    workspace_root = resolve_workspace_root(args.workspace_root)
    plan_path = Path(getattr(args, "plan_file", "") or "")
    if not str(plan_path):
        raise FeedbackError("--plan-file is required.")
    if not plan_path.is_absolute():
        plan_path = workspace_root / plan_path
    if not plan_path.is_file():
        raise FeedbackError(f"plan file not found: {plan_path}")

    registry = load_probe_registry(workspace_root)
    if not registry["available"]:
        raise FeedbackError(f"probe registry not found: {probe_defs_path(workspace_root)}")

    directives: List[Tuple[str, str]] = []
    for raw in plan_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "->" not in line:
            raise FeedbackError(f"unparsable plan line: {raw!r}")
        entry_id, _, action = (part.strip() for part in line.partition("->"))
        action = action.split("#", 1)[0].strip()  # tolerate inline comments
        entry_id = entry_id.split("#", 1)[0].strip()
        if action not in ("delete", "re-register"):
            raise FeedbackError(f"unknown disposition {action!r} for {entry_id}")
        directives.append((entry_id, action))

    entries = load_store_state(workspace_root)["entries"]
    by_id = {e.get("id"): e for e in entries}
    unknown = [eid for eid, _ in directives if eid not in by_id]
    if unknown:
        raise FeedbackError("plan references unknown entry ids: " + ", ".join(unknown))

    store = feedback_dir(workspace_root)
    deleted: List[str] = []
    re_registered: List[str] = []
    log_lines = [f"## {now_iso()} — plan {plan_path.name}"]
    for entry_id, action in directives:
        entry = by_id[entry_id]
        entry_file = store / entry["file"]
        if action == "delete":
            if entry_file.is_file():
                entry_file.unlink()
            deleted.append(entry_id)
            log_lines.append(
                f"- {entry_id} | delete | rationale: per approved plan | "
                f"unit {entry.get('unit_id', '?')}")
        else:  # re-register in place with probe attribution
            if not entry_file.is_file():
                raise FeedbackError(f"entry file missing for re-register: {entry_id}")
            meta, body = parse_frontmatter(entry_file.read_text(encoding="utf-8"))
            probe = resolve_probe(registry, str(meta.get("unit_id", "")))
            if probe is None:
                raise FeedbackError(
                    f"cannot re-register {entry_id}: no probe object for unit "
                    f"{meta.get('unit_id', '?')}")
            meta["probe"] = probe["object_id"]
            meta["kind"] = probe["kind"]
            meta["slice"] = probe["slice"]
            meta["migrated_from"] = entry_id
            write_text_atomic(
                entry_file,
                dump_frontmatter(meta) + "\n\n" + body.strip() + "\n",
            )
            re_registered.append(entry_id)
            log_lines.append(
                f"- {entry_id} | re-register | probe {probe['object_id']} "
                f"| unit {meta.get('unit_id', '?')}")

    migrated = migrate_legacy_index(workspace_root)
    with (store / MIGRATION_LOG_NAME).open("a", encoding="utf-8") as fh:
        fh.write("\n".join(log_lines) + "\n")
    remaining = sum(1 for e in scan_entries(workspace_root) if not e.get("probe"))
    return {
        "deleted": deleted,
        "re_registered": re_registered,
        "legacy_remaining": remaining,
        "log": (FEEDBACK_SUBDIR / MIGRATION_LOG_NAME).as_posix(),
        "migrated": migrated,
    }


def _apply_disposition(workspace_root: Path, entry: Dict[str, Any],
                       state: str, reason: str, ref: str) -> None:
    """dispose-equivalent write used by introspect-register --confirm (C-3)."""
    entry_file = feedback_dir(workspace_root) / entry.get("file", "")
    if entry_file.is_file():
        meta, body = parse_frontmatter(entry_file.read_text(encoding="utf-8"))
        meta["disposition"] = state
        if reason:
            meta["disposition_reason"] = reason
        if ref:
            meta["introspection_ref"] = ref
        write_text_atomic(
            entry_file,
            dump_frontmatter(meta) + "\n\n" + body.strip() + "\n",
        )


def action_introspect_register(args: argparse.Namespace) -> Dict[str, Any]:
    """Register an introspection report: validate → link entries → reports.

    With --confirm (user ratified in-session): flip the report to confirmed and
    apply each finding's 建议处置 rows as batch dispositions (engine-cli C-3).
    """
    workspace_root = resolve_workspace_root(args.workspace_root)
    report_file = (getattr(args, "report_file", None) or "").strip()
    if not report_file:
        raise FeedbackError("--report-file is required.")
    report_path = Path(report_file)
    if not report_path.is_absolute():
        report_path = Path.cwd() / report_path
    report = parse_report(report_path)
    violations = validate_report(workspace_root, report)
    if violations:
        raise FeedbackError("report validation failed:\n- "
                            + "\n- ".join(violations))

    store_state = load_store_state(workspace_root)
    meta = report["meta"]
    report_id = meta["id"]
    by_id = {e.get("id"): e for e in store_state["entries"]}

    linked = 0
    for finding in report["findings"]:
        ref = f"{report_id}#{finding['finding_id']}"
        for eid, _verdict in finding["members"]:
            entry = by_id.get(eid)
            if entry is None:
                continue
            _apply_disposition(workspace_root, entry,
                               entry.get("disposition", "") or "",
                               "", ref)
            linked += 1

    disposed = 0
    if getattr(args, "confirm", False):
        for finding in report["findings"]:
            ref = f"{report_id}#{finding['finding_id']}"
            for eid, state in finding["suggestions"].items():
                entry = by_id.get(eid)
                if entry is None:
                    continue
                _apply_disposition(workspace_root, entry, state,
                                   f"introspection:{ref}", ref)
                disposed += 1
        meta["status"] = "confirmed"
        meta["confirmed_at"] = now_iso()
        write_report(report_path, report)

    superseded = meta.get("supersedes") or None
    if superseded:
        prior_path = (feedback_dir(workspace_root) / INTROSPECTION_DIRNAME
                      / f"{superseded}.md")
        if prior_path.is_file():
            prior = parse_report(prior_path)
            if prior["meta"]["status"] != "superseded":
                prior["meta"]["status"] = "superseded"
                write_report(prior_path, prior)

    # The introspection roster is derived by scanning introspection/*.md
    # (req 055) — nothing to maintain in an index. A re-register without
    # --confirm never reopens a confirmed report: the report file itself
    # carries status=confirmed and is only rewritten under --confirm.
    migrated = migrate_legacy_index(workspace_root)
    return {"report_id": report_id, "linked": linked, "disposed": disposed,
            "superseded": superseded, "migrated": migrated}


# --------------------------------------------------------------------------- #
# Rendering / CLI
# --------------------------------------------------------------------------- #
def render_text(action: str, payload: Dict[str, Any]) -> str:
    if action == "package":
        if not payload.get("zip"):
            return payload.get("note", "Nothing to package.")
        lines = [
            f"Packaged {payload['packaged']} feedback entr"
            f"{'y' if payload['packaged'] == 1 else 'ies'} (sources untouched):",
            f"  zip: {payload['zip']}",
        ]
        if payload.get("missing"):
            lines.append(f"  missing entry files skipped: {payload['missing']}")
        lines.extend(f"  {step}" for step in payload.get("next_steps", []))
        return "\n".join(lines)
    if action == "upstream":
        url = payload.get("url")
        if not url:
            return ("Upstream repo: unknown — configure once via "
                    "--action upstream --set <repo-url>")
        commit = f" @ {payload['commit']}" if payload.get("commit") else ""
        return f"Upstream repo ({payload.get('source')}): {url}{commit}"
    if action == "list":
        matches = payload.get("matches", [])
        if not matches:
            return "No matching entries."
        lines = []
        for item in matches:
            lines.append(f"- [{item.get('unit_type', '?')}] {item.get('unit_id', '?')}")
            lines.append(f"  path: {item.get('path', '')}")
            lines.append(
                f"  run_id: {item.get('run_id', '-')} | feature: {item.get('feature') or '-'}"
                f" | feature_id: {item.get('feature_id') or '-'}"
                f" | partial: {item.get('partial', False)}"
            )
            lines.append(f"  created: {item.get('created', '-')}")
            if item.get("summary"):
                lines.append(f"  summary: {item['summary']}")
        return "\n".join(lines)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Spec Kit feedback-as-files engine")
    parser.add_argument(
        "--action",
        required=True,
        choices=["record", "status", "list", "dispose", "mark-submitted", "reindex",
                 "package", "cleanup", "upstream", "migrate-legacy",
                 "introspect-register", "args-manifest"],
    )
    parser.add_argument("--package", default=None,
                        help="cleanup: path to the package zip (workspace-"
                             "relative or absolute), or 'latest'")
    parser.add_argument("--report-file", default=None,
                        help="introspect-register: path to the introspection "
                             "report file")
    parser.add_argument("--include-introspection", action="store_true",
                        help="package: include introspection reports covering "
                             "the packaged entries (introspection/ payload + "
                             "MANIFEST section)")
    parser.add_argument("--confirm", action="store_true",
                        help="introspect-register: user has ratified the "
                             "report; flip to confirmed and apply batch "
                             "dispositions from 建议处置 rows")
    parser.add_argument("--lifecycle-point", default=None,
                        help="record: resolve the probe object by (unit, lifecycle_point), "
                             "e.g. gate-<slug> for gate probes")
    parser.add_argument("--plan-file", default=None,
                        help="migrate-legacy: approved disposition plan, one "
                             "'<entry-id> -> delete|re-register' per line")
    parser.add_argument("--dry-run", action="store_true",
                        help="cleanup: list what would be removed, change nothing")
    parser.add_argument("--slice", default=None,
                        help="list: filter entries by target system slice "
                             "(inherited from the entry's probe class)")
    parser.add_argument("--kind", default=None,
                        help="list: filter entries by probe kind "
                             "(internal|external)")
    parser.add_argument("--disposition", default=None,
                        help="list: filter entries by disposition "
                             "(processed|ignored|open)")
    parser.add_argument("--id", default=None,
                        help="dispose: target entry id")
    parser.add_argument("--to", default=None,
                        help="dispose: target disposition state "
                             "(processed|ignored)")
    parser.add_argument("--reason", default=None,
                        help="dispose: optional disposition reason text")
    parser.add_argument("--ref", default=None,
                        help="dispose: optional introspection ref "
                             "(introspection-<ts>#F-<nn>)")
    parser.add_argument("--workspace-root", default=None)
    parser.add_argument("--unit-id", default=None)
    parser.add_argument("--unit-type", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--review", default=None)
    parser.add_argument("--review-file", default=None)
    parser.add_argument("--points", default=None)
    parser.add_argument("--points-file", default=None)
    parser.add_argument("--partial", action="store_true")
    parser.add_argument("--feature", default=None,
                        help="record: requirement key (e.g. 038-goal-target); "
                             "NOT the Feature registry ID")
    parser.add_argument("--feature-id", dest="feature_id", default=None,
                        help="record: Feature registry ID (e.g. 041); distinct "
                             "number space from --feature")
    parser.add_argument("--notes", default=None,
                        help="mark-submitted: disposition summary for this batch, "
                             "archived as SUBMISSION-NOTES.md inside the package")
    parser.add_argument("--threshold", type=int, default=None)
    parser.add_argument("--since", default=None)
    parser.add_argument("--limit", type=int, default=5,
                        help="list: max entries returned; 0 = no limit")
    parser.add_argument("--contains", default=None,
                        help="list: case-insensitive substring filter over entry "
                             "summary + body (engine-side read; output stays summary-level)")
    parser.add_argument("--all", action="store_true",
                        help="package: include entries from before the last "
                             "mark-submitted as well")
    parser.add_argument("--set", dest="set_url", default=None,
                        help="upstream: persist the upstream repo URL")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


def action_args_manifest(args: argparse.Namespace) -> Dict[str, Any]:
    """C-22 (063): machine-readable per-action argument manifest, BUILT FROM
    this engine's own parser — every classified flag is verified against the
    live parser's option strings before emitting. Pure query face: no
    workspace access, no write."""
    parser = build_parser()
    live = {opt for act in parser._actions for opt in act.option_strings}
    manifest: Dict[str, Any] = {}
    for action in ("record", "status", "list", "dispose", "mark-submitted",
                   "reindex", "package", "cleanup", "upstream", "migrate-legacy",
                   "introspect-register", "args-manifest"):
        spec = ARG_MANIFEST.get(action)
        if spec is None:
            raise FeedbackError(
                f"args-manifest: action {action!r} has no manifest spec")
        for key in ("required", "source"):
            unknown = [f for f in spec[key] if f not in live]
            if unknown:
                raise FeedbackError(
                    f"args-manifest: {action} {key} flags are not options of "
                    f"this engine's parser: {unknown}")
        manifest[action] = {"required": list(spec["required"]),
                            "source": list(spec["source"])}
    return manifest


_ACTIONS = {
    "record": action_record,
    "status": action_status,
    "list": action_list,
    "dispose": action_dispose,
    "mark-submitted": action_mark_submitted,
    "reindex": action_reindex,
    "package": action_package,
    "upstream": action_upstream,
    "cleanup": action_cleanup,
    "migrate-legacy": action_migrate_legacy,
    "introspect-register": action_introspect_register,
    "args-manifest": action_args_manifest,
}


_DESTRUCTIVE_ACTIONS = {"package", "cleanup", "migrate-legacy",
                        "mark-submitted", "dispose", "introspect-register"}


def _cwd_project_root() -> Optional[Path]:
    """Nearest ancestor of the CURRENT working directory containing .specify/."""
    cur = Path.cwd().resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / ".specify").is_dir():
            return candidate
    return None


def warn_anchor_mismatch(action: str, args: argparse.Namespace) -> None:
    """F16 guard: destructive actions warn when the engine's self-location
    anchor disagrees with the CWD's project root (cross-project invocation
    without an explicit --workspace-root — the 041 T021 incident class).
    Non-blocking (red line 2): a warning, never a gate."""
    if action not in _DESTRUCTIVE_ACTIONS:
        return
    if getattr(args, "workspace_root", None):
        return  # explicit override always silences the check
    try:
        anchored = resolve_workspace_root(None)
    except Exception:
        return
    cwd_root = _cwd_project_root()
    if cwd_root is None or anchored == cwd_root:
        return
    print(
        f"warning: destructive action '{action}' is anchored at {anchored} "
        f"(engine self-location) while the CWD project appears to be "
        f"{cwd_root}. Pass --workspace-root to target the intended store.",
        file=sys.stderr,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    warn_anchor_mismatch(args.action, args)
    try:
        payload = _ACTIONS[args.action](args)
    except FeedbackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.format == "json" or args.action in (
            "record", "status", "mark-submitted", "reindex", "args-manifest"):
        # args-manifest (063 C-22): pure JSON regardless of --format — the
        # machine face the compile-embeds renderer consumes.
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(args.action, payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
