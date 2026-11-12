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
import fcntl
import glob
import hashlib
import json
import os
import re
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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

# The declaration layer's single read entry (feature 084). Import-qualified, so a plain import works:
# every consumer is invoked as `python3 <dir>/this-file.py`, which puts this directory on sys.path.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import declaration_reader  # noqa: E402  (import follows the sys.path entry above)

FEEDBACK_SUBDIR = Path(".specify") / "memory" / "feedback"
PACKAGES_DIRNAME = "packages"
STATE_DIRNAME = "state"
# Legacy single-file index (pre-055): kept only as a read-only fallback
# source for the three store scalars, and deleted on first mutation.
INDEX_NAME = "index.json"
STORE_NAME = "feedback"
# Feature 084, batch 1 row 1: the prompt threshold is a declaration-layer fact. This engine carries no
# copy of the value — it reads `.specify/shared/declarations/facts/feedback-prompt-threshold.yaml` through the
# shared read entry, and a project without the layer is labelled rather than defaulted (FR-012 /
# C-049: the compatibility path MUST NOT be readable as a pass).
THRESHOLD_FACT = "feedback-prompt-threshold"
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
_NOW_OVERRIDE: Optional[str] = None


def set_now_option(value: Optional[str]) -> None:
    """Apply the optional injected clock (--now) for this invocation.

    ``value=None`` restores the real clock, so an invocation without the option is
    byte-identical to the pre-change engine. A value must be a canonical
    second-granularity UTC stamp (``YYYY-MM-DDTHH:MM:SSZ``) — the engine's stored
    form — otherwise the invocation is rejected with a named error.
    """
    global _NOW_OVERRIDE
    if value is None:
        _NOW_OVERRIDE = None
        return
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        raise FeedbackError(
            f"--now: cannot parse {value!r} — expected YYYY-MM-DDTHH:MM:SSZ")
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise FeedbackError(
            f"--now: {value!r} is not a canonical second-granularity UTC stamp "
            "(expected YYYY-MM-DDTHH:MM:SSZ)")
    _NOW_OVERRIDE = value


def now_iso() -> str:
    if _NOW_OVERRIDE is not None:
        return _NOW_OVERRIDE
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def timestamp_id() -> str:
    if _NOW_OVERRIDE is not None:
        return _NOW_OVERRIDE.replace("-", "").replace(":", "")
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


def should_prompt_or_degrade(count: int, threshold: Optional[int]) -> bool:
    """`should_prompt` with the degraded read pinned to "do not prompt" (FR-012 / C-049).

    ``threshold is None`` means the declaration layer could not be read (a legacy project). Prompting on
    a value nobody can point at would be exactly the silent default FR-012 forbids, so the reading
    degrades to "do not prompt" and the caller puts the `declaration-absent` label on its output line.

    The predicate itself stays byte-identical: `tests/contract/test_client_metrics.py` C-42 pins
    ``should_prompt``'s source text because the threshold-combination rule is a 055-era contract that this
    migration must not re-shape. The degradation therefore lives here, beside it, not inside it.
    """
    if threshold is None:
        return False
    return should_prompt(count, threshold)


def declared_threshold() -> Tuple[Optional[int], Optional[str]]:
    """`(value, label)` for the declared prompt threshold.

    The value comes from the declaration layer through the shared read entry — never from a constant in
    this file (there is none). ``label`` is the `declaration-absent` instance when the layer or the fact
    is missing, and ``None`` when the read succeeded; a caller puts it on its output line so a degraded
    read is visible rather than read as a pass (C-049).
    """
    repo = declaration_reader.find_repo(Path(__file__).resolve())
    try:
        fact = declaration_reader.load_fact(repo, THRESHOLD_FACT)
        return int(str(fact["body"]["statement"]).strip()), None
    except (declaration_reader.DeclarationError, KeyError, TypeError, ValueError):
        return None, declaration_reader.absent_label(THRESHOLD_FACT)


def resolve_threshold(explicit: Optional[int], stored: Optional[int]) -> Optional[int]:
    """explicit > env > stored > the declaration layer. No inline default survives this chain."""
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
    return declared_threshold()[0]


def threshold_label() -> Optional[str]:
    """The `declaration-absent` label when the layer cannot be read, else ``None`` (FR-012)."""
    return declared_threshold()[1]


def with_threshold_label(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Carry the degraded-wiring label on the output line, never as a pass (C-049)."""
    label = threshold_label()
    if label:
        payload["threshold_label"] = label
    return payload


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
                      else declared_threshold()[0]),
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
    "client-metrics": {"required": [], "source": ["--unit"]},
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
        return with_threshold_label({
            "id": existing.get("id", ""),
            "path": rel,
            "duplicate": True,
            "count_since_submission": count,
            "threshold": threshold,
            "should_prompt": should_prompt_or_degrade(count, threshold),
            "migrated": False,
        })

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
    return with_threshold_label({
        "id": entry_id,
        "path": rel,
        "duplicate": False,
        "count_since_submission": count,
        "threshold": threshold,
        "should_prompt": should_prompt_or_degrade(count, threshold),
        "migrated": migrated,
    })


def action_status(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    state = load_store_state(workspace_root)
    threshold = resolve_threshold(args.threshold, state["threshold"])
    count = state["count_since_submission"]
    entries = state["entries"]
    return with_threshold_label({
        "count_since_submission": count,
        "threshold": threshold,
        "should_prompt": should_prompt_or_degrade(count, threshold),
        "total_entries": len(entries),
        "submitted_at": state["submitted_at"],
        "legacy_remaining": sum(1 for e in entries if not e.get("probe")),
        "external_count": sum(1 for e in entries if e.get("kind") == "external"),
        "legacy": state["legacy"],
    })


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
# Client loop metrics (Feature 072, C-46…C-50)
# --------------------------------------------------------------------------- #
# Read-built four-metric view over the existing store, routing backlog, and
# code-segment records. This action has NO write point: it never creates,
# rewrites, or persists anything — readings are recomputed from the records
# on every report (程序优先: the engine derives; the agent never recomputes
# from raw list output). No scoring, weight, total, or cross-metric
# conversion exists; the four metrics never compose into a single number.
_RECORD_RUN_STAMP_RE = re.compile(r"^\| \*\*日期\*\* \| `([^`]+)` \|$", re.M)
_NOTE_HEADING_RE = re.compile(r"^###\s+\S+\s+\[([A-Z]+)\]\s+([^\s(]+)", re.M)
_BACKTICK_PATH_RE = re.compile(r"`([^`]+)`")
_REPEAT_PROXY_LABEL = (
    "coarse proxy - (file, severity) pair reappearance across records of the "
    "same unit; not a defect recurrence rate"
)


def _parse_iso_epoch(value: Any) -> Optional[float]:
    try:
        return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc).timestamp()
    except (ValueError, TypeError):
        return None


def _code_segment_record_stamps(workspace_root: Path) -> Dict[str, Path]:
    """run stamp -> record path for the code-segment records the review
    script produces (`.specify/specs/*/code-review.md`). Read-only scan."""
    out: Dict[str, Path] = {}
    specs = workspace_root / ".specify" / "specs"
    if specs.is_dir():
        for path in sorted(specs.glob("*/code-review.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            m = _RECORD_RUN_STAMP_RE.search(text)
            if m and m.group(1) not in out:
                out[m.group(1)] = path
    return out


def _entry_record_pointer(workspace_root: Path, entry: Dict[str, Any]) -> Optional[Path]:
    """The record file an entry points at (its body's `record=` line)."""
    entry_file = feedback_dir(workspace_root) / entry.get("file", "")
    try:
        text = entry_file.read_text(encoding="utf-8")
    except OSError:
        return None
    _meta, body = parse_frontmatter(text)
    for line in body.splitlines():
        if line.startswith("record="):
            rel = line[len("record="):].strip()
            return (workspace_root / rel) if rel else None
    return None


def _record_pairs(record_path: Optional[Path]) -> Optional[Set[Tuple[str, str]]]:
    """(file, severity) pairs from a code-segment record's note headings;
    None = the record is unreadable (C-50 exclusion rule)."""
    if record_path is None:
        return None
    try:
        text = record_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    pairs: Set[Tuple[str, str]] = set()
    for severity, fpath in _NOTE_HEADING_RE.findall(text):
        pairs.add((fpath, severity.lower()))
    return pairs


def _routing_backlog_rows(workspace_root: Path) -> List[str]:
    """Raw table rows of the existing routing backlog (read-only)."""
    path = feedback_dir(workspace_root) / "backlog.md"
    if not path.is_file():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    rows = []
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells or all(set(c) <= set("-: ") for c in cells if c):
            continue  # markdown separator row
        if cells[0].lower() == "routed":
            continue  # table header
        rows.append(s)
    return rows


def _row_is_carried(row: str) -> bool:
    """承接类行 (data-model E8): a cell whose text starts with carried-by-."""
    for cell in row.strip().strip("|").split("|"):
        cleaned = cell.strip().strip("*").strip()
        if cleaned.startswith("carried-by-"):
            return True
    return False


def _row_owner_files_changed(workspace_root: Path, row: str,
                             created_epoch: Optional[float]) -> bool:
    """Closure evidence (C-44/V-28): a named owner file exists and its mtime
    is later than the entry's created stamp. Routing marks never count."""
    if created_epoch is None:
        return False
    for token in _BACKTICK_PATH_RE.findall(row):
        token = token.strip()
        if not token:
            continue
        candidates: List[Path] = []
        if "*" in token:
            candidates = [Path(p) for p in
                          glob.glob(str(workspace_root / token), recursive=True)]
        else:
            candidates = [workspace_root / token]
        for candidate in candidates:
            try:
                if candidate.is_file() and candidate.stat().st_mtime > created_epoch:
                    return True
            except OSError:
                continue
    return False


def _not_evaluated(reason: str, **extra: Any) -> Dict[str, Any]:
    row: Dict[str, Any] = {"status": "not-evaluated", "reason": reason,
                           "numerator": 0, "denominator": 0}
    row.update(extra)
    return row


def _evaluated(numerator: int, denominator: int, **extra: Any) -> Dict[str, Any]:
    row: Dict[str, Any] = {"status": "evaluated", "numerator": numerator,
                           "denominator": denominator,
                           "value": numerator / denominator}
    row.update(extra)
    return row


def action_client_metrics(args: argparse.Namespace) -> Dict[str, Any]:
    """Feature 072: read-only loop-effectiveness metrics (C-46…C-50).

    Derivation is program-first from three existing faces only — the feedback
    store (`kind: external` entries), the routing backlog
    (`.specify/memory/feedback/backlog.md`), and the code-segment records
    (`.specify/specs/*/code-review.md`). Nothing is written; no aggregate,
    index, score, weight, or total is produced or persisted.
    """
    workspace_root = resolve_workspace_root(args.workspace_root)
    unit = (getattr(args, "unit", None) or "").strip() or None
    entries = [e for e in load_store_state(workspace_root)["entries"]
               if e.get("kind") == "external"
               and (unit is None or e.get("unit_id") == unit)]
    scope = f"unit {unit!r}" if unit else "all client units"
    boundary = min((str(e.get("created", "")) for e in entries), default=None)
    records = _code_segment_record_stamps(workspace_root)
    backlog_rows = _routing_backlog_rows(workspace_root)

    # --- capture coverage (C-43, C-49): captured record run stamps out of
    # the record run stamps at/after the arming boundary. The boundary is the
    # creation stamp of the first external entry; earlier records are
    # excluded by rule and disclosed — never backfilled (C-41).
    if not entries:
        coverage = _not_evaluated(
            "no client entries in scope (" + scope + ") - the arming boundary "
            "(first external entry's created stamp) cannot be derived; "
            "pre-arming records are never backfilled (C-41/C-49)",
            excluded_before_arming=0)
    else:
        qualifying = {s for s in records if s >= str(boundary)}
        excluded = len(records) - len(qualifying)
        if not qualifying:
            coverage = _not_evaluated(
                "no code-segment records at or after the arming boundary "
                f"({boundary}) - earlier records are excluded by rule, never "
                "backfilled (C-41/C-49)",
                excluded_before_arming=excluded)
        else:
            captured = {str(e.get("run_id", "")) for e in entries} & qualifying
            coverage = _evaluated(
                len(captured), len(qualifying),
                excluded_before_arming=excluded, boundary=str(boundary))

    # --- into-loop ratio (C-43): entries with a carried-by-* backlog row.
    total = len(entries)
    if total == 0:
        into_loop = _not_evaluated(
            "no client entries in scope (" + scope + ")")
        closure = _not_evaluated(
            "no client entries in scope (" + scope + ")")
    else:
        rows_by_entry = {
            e["id"]: [r for r in backlog_rows
                      if str(e.get("id", "")) and str(e.get("id")) in r]
            for e in entries
        }
        carried_by_entry = {
            eid: [r for r in rows if _row_is_carried(r)]
            for eid, rows in rows_by_entry.items()
        }
        into_num = sum(1 for e in entries if carried_by_entry.get(e["id"]))
        closure_num = 0
        for e in entries:
            created_epoch = _parse_iso_epoch(e.get("created", ""))
            if any(_row_owner_files_changed(workspace_root, r, created_epoch)
                   for r in carried_by_entry.get(e["id"], [])):
                closure_num += 1
        into_loop = _evaluated(into_num, total)
        # C-44: closure counts only owner-file change evidence; routing marks
        # (dispose processed/ignored, a carried-by row alone, open-unverified)
        # are never closure evidence — routing is not completion.
        closure = _evaluated(closure_num, total)

    # --- repeat-finding rate (C-45, C-50): coarse proxy over (file,
    # severity) pairs extracted deterministically from the pointed-to record.
    excluded_unreadable = 0
    repeat_num = 0
    repeat_den = 0
    by_unit: Dict[str, List[Dict[str, Any]]] = {}
    for e in entries:
        by_unit.setdefault(str(e.get("unit_id", "")), []).append(e)
    for unit_id in sorted(by_unit):
        ordered = sorted(by_unit[unit_id],
                         key=lambda e: (str(e.get("created", "")),
                                        str(e.get("id", ""))))
        seen_pairs: Set[Tuple[str, str]] = set()
        for e in ordered:
            pairs = _record_pairs(_entry_record_pointer(workspace_root, e))
            if pairs is None:
                excluded_unreadable += 1  # numerator and denominator together
                continue
            repeat_den += 1
            if pairs & seen_pairs:
                repeat_num += 1
            seen_pairs |= pairs
    repeat_extra: Dict[str, Any] = {
        "proxy": True,
        "proxy_label": _REPEAT_PROXY_LABEL,
        "excluded_unreadable_records": excluded_unreadable,
    }
    if excluded_unreadable:
        repeat_extra["excluded_reason"] = (
            f"{excluded_unreadable} entr(y/ies) whose pointed-to record is "
            "unreadable - excluded from numerator and denominator together "
            "(C-50)")
    if repeat_den == 0:
        repeat = _not_evaluated(
            "no client entries with readable pointed-to records in scope ("
            + scope + ")"
            + (f"; {excluded_unreadable} excluded as unreadable (C-50)"
               if excluded_unreadable else ""),
            **repeat_extra)
    else:
        repeat = _evaluated(repeat_num, repeat_den, **repeat_extra)

    return {
        "unit": unit,
        "boundary": boundary,
        "metrics": {
            "capture_coverage": coverage,
            "into_loop_ratio": into_loop,
            "closure_ratio": closure,
            "repeat_finding_rate": repeat,
        },
    }


# --------------------------------------------------------------------------- #
# Upstream detection / packaging (no network operations — red line)
# --------------------------------------------------------------------------- #
def _speckit_version() -> str:
    try:
        from importlib import metadata
        return metadata.version(DIST_NAME)
    except Exception:
        return "unknown"



def _skill_names_in(skills_dir: Path) -> set:
    if not skills_dir.is_dir():
        return set()
    return {p.name for p in skills_dir.iterdir()
            if p.is_dir() and (p / "SKILL.md").is_file()}


def framework_skill_names(workspace_root: Path) -> Tuple[Optional[set], str]:
    """Resolve the skill names bundled with the Spec Kit framework itself.

    Returns ``(names, source)``; ``names`` is None when the bundle cannot be
    resolved at all. Sources, in priority order:

    1. the installed spec-kit package (``<pkg>/skills/<name>/SKILL.md``) —
       the wheel ships only framework skills, so this set excludes any
       user-authored skills a downstream project installed alongside them;
    2. a framework-repo checkout (``<workspace_root>/skills/`` next to
       ``src/specify_cli/``).
    """
    try:
        import importlib.util
        spec = importlib.util.find_spec("specify_cli")
        if spec is not None and getattr(spec, "origin", None):
            names = _skill_names_in(Path(spec.origin).resolve().parent / "skills")
            if names:
                return names, "installed-package"
    except Exception:
        pass
    if (workspace_root / "src" / "specify_cli").is_dir():
        names = _skill_names_in(workspace_root / "skills")
        if names:
            return names, "framework-repo"
    return None, "unresolved"


def is_framework_unit(unit_id: str, framework_skills: Optional[set]) -> bool:
    """Whether a feedback unit targets the Spec Kit framework itself.

    ``/speckit.*`` commands are framework units by definition; a ``skill:``
    unit is a framework unit only when the skill ships in the framework
    bundle. Feedback about user-project skills stays local (it has local
    workaround value) but is never packaged for upstream delivery.
    """
    if unit_id.startswith("/speckit."):
        return True
    if unit_id.startswith("skill:"):
        return framework_skills is not None and unit_id[len("skill:"):] in framework_skills
    return False


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


# --------------------------------------------------------------------------- #
# Exec-Quant payload (068 package leg; contracts/package-layout.md C-1..C-9)
# --------------------------------------------------------------------------- #
EXEC_QUANT_STORAGE_REL = Path(".specify") / "memory" / "exec-quant"
PAYLOAD_DIRNAME = "exec-quant"
PAYLOAD_RECORDS_DIRNAME = "records"
PAYLOAD_MANIFEST_NAME = "payload-manifest.json"
PAYLOAD_KIND = "speckit.exec-quant-payload"  # data-model § E4
PAYLOAD_SCHEMA_VERSION = 1
# [[STR-001]] (requirements § Shared Strings; same anchor as the quant
# engine's KIND constant)
RECORD_KIND = "speckit.exec-quant"
# C-2 is the single normative source of the cap values; these constants are
# the implementation's only definition of them (no second table anywhere).
MAX_PAYLOAD_RECORDS = 1000
MAX_PAYLOAD_BYTES = 16 * 1024 * 1024  # 16 MiB

# 068 intake leg (intake-contract C-10..C-17; data-model § E6 / research D5/D6)
AGGREGATED_DIRNAME = "aggregated"
AGGREGATED_RECORDS_DIRNAME = "records"
AGGREGATE_LOCK_NAME = ".write.lock"  # C-13 shared critical section
ENVELOPE_SCHEMA_VERSION = 1  # data-model § E6
ENVELOPE_KIND = "speckit.exec-quant-aggregated"  # data-model § E6
IDENTITY_KEY_SEP = "\x1f"  # C-13 / D6 five-tuple separator
UNKNOWN_PROJECT = "unknown-project"  # C-12 literal group (E2 enum value)

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_PROJECT_NAME_RE = re.compile(
    r"^\s*(?:-\s*)?\*\*Project Name\*\*:\s*(.+?)\s*$", re.M)


def exec_quant_dir(workspace_root: Path) -> Path:
    return Path(workspace_root).resolve() / EXEC_QUANT_STORAGE_REL


def _resolve_source_commit(workspace_root: Path) -> Optional[str]:
    """Workspace HEAD commit (C-5 / research D3), or ``None``.

    ``git rev-parse HEAD`` is implemented by its semantic — resolving the
    workspace repo's current HEAD commit — via pure local file reads:
    ``.git`` directory or gitdir-pointer file → ``HEAD`` → loose ref file →
    ``packed-refs``. Rationale (recorded in notes/red-first-evidence.md,
    ruling B): this engine carries a red-line guard
    (``tests/unit/test_feedback_package.py::test_engine_source_has_no_network_
    or_push``) that forbids a process-spawn surface, and the package leg is
    zero-network (C-9). Any failure → ``None`` (no retry, no blocking). Only
    40-hex values are accepted (data-model § E2); anything else degrades to
    ``None``.
    """
    git = Path(workspace_root) / ".git"
    try:
        if git.is_file():  # worktree/submodule: "gitdir: <path>" pointer
            pointer = git.read_text(encoding="utf-8").strip()
            if not pointer.startswith("gitdir:"):
                return None
            git = (Path(workspace_root)
                   / pointer[len("gitdir:"):].strip()).resolve()
        if not git.is_dir():
            return None
        head = (git / "HEAD").read_text(encoding="utf-8").strip()
        if _SHA_RE.match(head):  # detached HEAD
            return head
        if not head.startswith("ref:"):
            return None
        ref = head[len("ref:"):].strip()
        loose = git / ref
        if loose.is_file():
            sha = loose.read_text(encoding="utf-8").strip()
            return sha if _SHA_RE.match(sha) else None
        packed = git / "packed-refs"
        if packed.is_file():
            for line in packed.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                sha, _, ref_name = line.partition(" ")
                if ref_name == ref and _SHA_RE.match(sha):
                    return sha
        return None
    except (OSError, ValueError):
        return None


def _resolve_package_identity(workspace_root: Path) -> Dict[str, Any]:
    """Package-level source project identity (C-5 / research D3).

    ``project_name``: ``**Project Name**:`` line of the workspace's
    ``.specify/instructions.md`` → workspace directory basename → empty +
    ``identity_status: "unknown-project"``. Never a filesystem absolute path
    and no new credential surface (FR-003).
    """
    project_name = ""
    instructions = (Path(workspace_root) / ".specify" / "instructions.md")
    try:
        match = _PROJECT_NAME_RE.search(instructions.read_text(encoding="utf-8"))
        if match:
            project_name = match.group(1)
    except (OSError, ValueError):
        pass
    if not project_name:
        project_name = Path(workspace_root).resolve().name or ""
    return {
        "project_name": project_name,
        "source_commit": _resolve_source_commit(workspace_root),
        "identity_status": "identified" if project_name else "unknown-project",
    }


def _read_payload_object(raw: bytes) -> Optional[Dict[str, Any]]:
    """One swept item → record object, or None (C-1: object + kind gate)."""
    try:
        obj = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    if not isinstance(obj, dict) or obj.get("kind") != RECORD_KIND:
        return None
    return obj


def _collect_exec_quant_payload(workspace_root: Path) -> Dict[str, Any]:
    """Read-only sweep of the workspace exec-quant store (C-1 / C-2).

    Dual form: per-entry ``records/*.json`` files plus the legacy single-file
    ``records.jsonl`` stream, both fully included when they coexist (FR-001,
    no watermark). Items that fail to parse as a record-kind object are
    skipped and counted in ``skipped_unreadable``. Legacy entries are named
    ``legacy-records-L%04d.json`` from physical line number 1; blank lines
    are not records (ruling A, notes/red-first-evidence.md). Scan window =
    snapshot taken when the sweep starts (A3 semantics). Sort key
    ``(collected_at ascending, payload record name ascending)``; a missing
    ``collected_at`` sorts as the empty string (ruling U-02). Caps are
    applied to the sorted prefix as whole records (ruling U-01): the first
    entry that would exceed a cap — and every entry after it — counts into
    ``truncated_count``, so a single oversize record is itself truncated and
    no partial bytes ever leave the store. Every probed item lands in
    exactly one of the three buckets (ruling U-03), so
    ``skipped_unreadable + truncated_count + record_count`` equals the
    probed total.

    Never raises: every degradation lands in a counter (C-9, non-blocking).
    """
    store = exec_quant_dir(workspace_root)
    records_dir = store / "records"
    legacy_path = store / "records.jsonl"
    counts = {"records-dir": 0, "legacy-jsonl": 0}
    skipped = 0
    # candidates: (name, source_form, collected_at, raw bytes), usable only
    candidates: List[Tuple[str, str, str, bytes]] = []

    # Snapshot window (C-1): materialize the name list once at sweep start —
    # writes landing mid-sweep are not included.
    if records_dir.is_dir():
        for path in sorted(records_dir.glob("*.json")):
            try:
                raw = path.read_bytes()
            except OSError:
                skipped += 1
                continue
            if _read_payload_object(raw) is None:
                skipped += 1
                continue
            record = json.loads(raw.decode("utf-8"))
            collected_at = str(record.get("collected_at", "") or "")
            candidates.append((path.name, "records-dir", collected_at, raw))
            counts["records-dir"] += 1
    if legacy_path.is_file():
        try:
            lines = legacy_path.read_text(encoding="utf-8").splitlines()
        except (OSError, ValueError):
            lines = []
        for lineno, line in enumerate(lines, start=1):
            if not line.strip():
                continue  # ruling A: blank line is not a record
            raw = line.encode("utf-8")
            if _read_payload_object(raw) is None:
                skipped += 1
                continue
            record = json.loads(raw.decode("utf-8"))
            collected_at = str(record.get("collected_at", "") or "")
            candidates.append((f"legacy-records-L{lineno:04d}.json",
                               "legacy-jsonl", collected_at, raw))
            counts["legacy-jsonl"] += 1

    # C-2: deterministic, cross-machine reproducible (ruling U-02).
    candidates.sort(key=lambda c: (c[2], c[0]))

    included: List[Dict[str, Any]] = []
    total_bytes = 0
    for name, source_form, collected_at, raw in candidates:
        if (len(included) >= MAX_PAYLOAD_RECORDS
                or total_bytes + len(raw) > MAX_PAYLOAD_BYTES):
            break  # U-01: first violator and every entry after it truncate
        included.append({"name": name, "source_form": source_form,
                         "collected_at": collected_at, "data": raw})
        total_bytes += len(raw)

    return {
        "identity": _resolve_package_identity(workspace_root),  # C-5 / D3
        "records": included,
        "record_count": len(included),
        "source_form_counts": counts,
        "skipped_unreadable": skipped,
        "truncated_count": len(candidates) - len(included),
        "cap_records": MAX_PAYLOAD_RECORDS,
        "cap_bytes": MAX_PAYLOAD_BYTES,
        "collected_at_range": ([included[0]["collected_at"],
                                included[-1]["collected_at"]]
                               if included else None),
    }


def _payload_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    """C-7 JSON-report projection: counts + identity, never record bytes."""
    identity = payload["identity"]
    return {
        "record_count": payload["record_count"],
        "source_form_counts": dict(payload["source_form_counts"]),
        "skipped_unreadable": payload["skipped_unreadable"],
        "truncated_count": payload["truncated_count"],
        "cap_records": payload["cap_records"],
        "cap_bytes": payload["cap_bytes"],
        "collected_at_range": payload["collected_at_range"],
        "identity_status": identity["identity_status"],
        "project_name": identity["project_name"] or None,
        "source_commit": identity["source_commit"],
    }


def _render_payload_sections(
        payload: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """C-4 / C-6 / data-model E5: ONE renderer, two faces.

    The machine manifest (``exec-quant/payload-manifest.json``, field set =
    data-model § E4) and the human ``MANIFEST.md`` § Exec-Quant Payload lines
    are derived here from the same payload values, so the two faces cannot
    drift apart (One Source Of Truth). The empty-payload section is always
    rendered and declares 「无量化数据」 (FR-005 explicit degradation).
    """
    identity = payload["identity"]
    manifest = {
        "schema_version": PAYLOAD_SCHEMA_VERSION,
        "kind": PAYLOAD_KIND,
        "identity": dict(identity),
        "record_count": payload["record_count"],
        "source_form_counts": dict(payload["source_form_counts"]),
        "skipped_unreadable": payload["skipped_unreadable"],
        "truncated_count": payload["truncated_count"],
        "cap_records": payload["cap_records"],
        "cap_bytes": payload["cap_bytes"],
        "collected_at_range": payload["collected_at_range"],
    }
    forms = manifest["source_form_counts"]
    project = identity["project_name"] or "unknown-project"
    lines = ["## Exec-Quant Payload", ""]
    if manifest["record_count"] == 0:
        lines += ["Exec-Quant Payload: none (无量化数据).",
                  "The source store had no readable exec-quant records at "
                  "package time."]
    else:
        lines += [f"- **Records**: {manifest['record_count']}",
                  f"- **Source forms**: records-dir {forms['records-dir']}, "
                  f"legacy-jsonl {forms['legacy-jsonl']}"]
    lines += [f"- **Skipped unreadable**: {manifest['skipped_unreadable']}",
              f"- **Truncated**: {manifest['truncated_count']}",
              f"- **Cap**: {manifest['cap_records']} records / "
              f"{manifest['cap_bytes']} bytes "
              f"(triggered: {'yes' if manifest['truncated_count'] else 'no'})",
              f"- **Source project**: {project}"]
    if manifest["collected_at_range"]:
        lines.append(f"- **Collected range**: "
                     f"{manifest['collected_at_range'][0]} → "
                     f"{manifest['collected_at_range'][1]}")
    lines.append("")
    return manifest, lines


# --------------------------------------------------------------------------- #
# Exec-Quant intake (068 US2 receive leg; contracts/intake-contract.md C-10..C-17)
# --------------------------------------------------------------------------- #
def _identity_key(record: Dict[str, Any], source_project: str) -> str:
    """C-13 / D6: sha256 of the five-tuple ``source_project ␟ unit_id ␟
    unit_type ␟ run_id ␟ collected_at`` joined with ``\\x1f``. The tuple is
    content-free (the F-01 remediation): ``content_hash`` is computed
    separately and MUST NOT enter this key. A missing field participates as
    the empty string (same convention as the U-02 sort rule)."""
    parts = [str(source_project or ""),
             str(record.get("unit_id", "") or ""),
             str(record.get("unit_type", "") or ""),
             str(record.get("run_id", "") or ""),
             str(record.get("collected_at", "") or "")]
    return hashlib.sha256(
        IDENTITY_KEY_SEP.join(parts).encode("utf-8")).hexdigest()


def _canonical_json(record: Dict[str, Any]) -> str:
    """C-13 / D6 canonical form: sort_keys + ensure_ascii=False + compact."""
    return json.dumps(record, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))


def _content_hash(record: Dict[str, Any]) -> str:
    """C-13: independent canonical-JSON sha256 — comparison field only,
    never mixed into ``identity_key`` (D6 / analyze F-01)."""
    return hashlib.sha256(
        _canonical_json(record).encode("utf-8")).hexdigest()


def _source_slug(project_name: str, identity_key: str) -> str:
    """D5 / E6: slugged project name (lowercase, ``[a-z0-9-]``) + 8-char
    identity short hash; an empty identity string collapses to the literal
    ``unknown-project`` group (deterministic, no hash suffix, C-12)."""
    name = re.sub(r"[^a-z0-9]+", "-",
                  str(project_name or "").strip().lower()).strip("-")
    if not name:
        return UNKNOWN_PROJECT
    return f"{name}-{identity_key[:8]}"


def _build_envelope(record: Dict[str, Any], identity: Any,
                    package_file: str) -> Dict[str, Any]:
    """Data-model § E6 envelope: attribution face + the source record sealed
    verbatim under ``record`` (C-14/C-15 — no rewrite, completion or drop of
    any source field; unknown fields ride along untouched)."""
    ident = dict(identity) if isinstance(identity, dict) else {}
    project = str(ident.get("project_name") or "").strip()
    status = str(ident.get("identity_status")
                 or (UNKNOWN_PROJECT if not project else "identified"))
    source_project = project or UNKNOWN_PROJECT  # E6: missing → literal
    return {
        "aggregation_envelope": {
            "schema_version": ENVELOPE_SCHEMA_VERSION,
            "kind": ENVELOPE_KIND,
            "source_project": source_project,
            "source_commit": ident.get("source_commit"),
            "identity_status": status or UNKNOWN_PROJECT,
            "identity_key": _identity_key(record, source_project),
            "content_hash": _content_hash(record),
            "package_file": str(package_file or ""),
            "ingested_at": now_iso(),
        },
        "record": record,
    }


def _intake_entry_filename() -> str:
    """C-14: envelope filename rides the quant engine's ``entry_filename()``
    form (timestamp with microseconds + 8-hex uuid), decoupled from the
    source member names (which are not guaranteed unique across packages).
    The engine stay decoupled, so the format is re-derived here; the
    normative owner is intake-contract C-14."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}.json"


def _write_envelope_atomic(group_dir: Path,
                           envelope: Dict[str, Any]) -> Path:
    """tmp+rename atomic write (write_entry form); leaves zero residue."""
    group_dir.mkdir(parents=True, exist_ok=True)
    target = group_dir / _intake_entry_filename()
    tmp = group_dir / (".tmp-" + uuid.uuid4().hex + ".part")
    tmp.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    os.replace(tmp, target)
    return target


def _scan_identity_window(aggregated: Path) -> Dict[str, str]:
    """C-13 dedup window: ``identity_key → content_hash`` over every existing
    aggregated envelope (all groups). Unreadable envelopes stay outside the
    window (they cannot veto a write they cannot be compared against)."""
    window: Dict[str, str] = {}
    if not aggregated.is_dir():
        return window
    for group in sorted(aggregated.iterdir()):
        records_dir = group / AGGREGATED_RECORDS_DIRNAME
        if not records_dir.is_dir():
            continue
        for path in sorted(records_dir.glob("*.json")):
            try:
                envelope = json.loads(path.read_text(encoding="utf-8"))
                env = envelope["aggregation_envelope"]
                key = env["identity_key"]
                content_hash = env["content_hash"]
            except (OSError, ValueError, KeyError, TypeError):
                continue
            if isinstance(key, str) and isinstance(content_hash, str):
                window[key] = content_hash
    return window


def _intake_result(record_count: int, ingested: int, duplicates: int,
                   skipped: int, conflicts: int, groups: int,
                   manifest_unreadable: bool) -> Dict[str, Any]:
    """C-16 output face: the fixed seven-key report."""
    return {
        "record_count": record_count,
        "ingested": ingested,
        "duplicates_skipped": duplicates,
        "skipped_unreadable": skipped,
        "identity_conflicts": conflicts,
        "groups_touched": groups,
        "manifest_unreadable": manifest_unreadable,
    }


def action_ingest_exec_quant(args: argparse.Namespace) -> Dict[str, Any]:
    """Unpack the ``exec-quant/`` payload of an inbound feedback bundle into
    the local aggregated layer (068 US2; intake-contract C-10..C-17).

    Payload recognition = zip member path prefix ``exec-quant/`` (C-11): a
    package without it is a zero-count no-op with zero storage writes (the
    068-pre package stays zero-difference, FR-009). Attribution reads the
    payload manifest identity only — a missing/corrupt manifest or an
    ``unknown-project`` identity lands the literal ``unknown-project`` group
    and is never guessed from paths or content (C-12, FR-006). Per-member
    parse/kind failures are non-blocking ``skipped_unreadable`` (C-11,
    FR-010). Dedup check + write share ONE flock critical section on
    ``aggregated/.write.lock`` (C-13): same identity_key + same content_hash
    → ``duplicates_skipped``; same key + different content → keep-first +
    ``identity_conflicts``. Envelopes are per-entry tmp+rename atomic writes
    (C-14) and the feedback store is never read or written (C-14/FR-006;
    the intake never triggers aggregate, C-17). Exit ladder: degradations
    complete with exit 0; ``--package`` missing/not a zip/an unwritable
    aggregated store is exit 2 (C-16/D10).
    """
    if not getattr(args, "package", None):
        raise FeedbackError(
            "ingest-exec-quant: --package <zip> is required (the inbound "
            "feedback bundle carrying the exec-quant payload)")
    package_path = Path(args.package)
    if not package_path.is_file():
        raise FeedbackError(
            f"ingest-exec-quant: --package file not found: {package_path}")
    try:
        archive = zipfile.ZipFile(package_path)
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        raise FeedbackError(
            f"ingest-exec-quant: --package is not a readable zip: "
            f"{package_path} ({exc})")
    workspace_root = resolve_workspace_root(args.workspace_root)
    store = exec_quant_dir(workspace_root)  # single quant-store locator (068 boundary)
    aggregated = store / AGGREGATED_DIRNAME

    prefix = PAYLOAD_DIRNAME + "/"
    manifest_name = f"{prefix}{PAYLOAD_MANIFEST_NAME}"
    with archive:
        names = archive.namelist()
        payload_members = sorted(
            name for name in names
            if name.startswith(prefix) and name != manifest_name)
        if not payload_members:
            # C-11: no exec-quant/ payload → zero difference vs 068-pre.
            return _intake_result(0, 0, 0, 0, 0, 0, False)

        manifest: Optional[Dict[str, Any]] = None
        manifest_unreadable = manifest_name not in names
        if not manifest_unreadable:
            try:
                manifest = json.loads(archive.read(manifest_name)
                                      .decode("utf-8"))
                if not isinstance(manifest, dict):
                    manifest, manifest_unreadable = None, True
            except (OSError, ValueError, UnicodeDecodeError,
                    zipfile.BadZipFile):
                manifest, manifest_unreadable = None, True

        # C-12: attribution from the manifest identity ONLY. A missing or
        # unknown-project identity normalizes to the literal group; no
        # guessing from the zip path or the record content.
        raw_identity = manifest.get("identity") if manifest else None
        identity = dict(raw_identity) if isinstance(raw_identity, dict) else {}
        project_name = str(identity.get("project_name") or "").strip()
        if (str(identity.get("identity_status") or "") == UNKNOWN_PROJECT
                or not project_name):
            identity = {"project_name": "",
                        "source_commit": identity.get("source_commit"),
                        "identity_status": UNKNOWN_PROJECT}

        record_count = 0
        skipped = 0
        parsed: List[Dict[str, Any]] = []
        for member in payload_members:
            record_count += 1
            try:
                obj = json.loads(archive.read(member).decode("utf-8"))
            except (OSError, ValueError, UnicodeDecodeError,
                    zipfile.BadZipFile):
                skipped += 1
                continue
            if not isinstance(obj, dict) or obj.get("kind") != RECORD_KIND:
                skipped += 1
                continue
            parsed.append(obj)

    if not parsed:
        # Nothing writable: zero storage touch even when members were skipped.
        return _intake_result(record_count, 0, 0, skipped, 0, 0,
                              manifest_unreadable)

    resolved_project = project_name or UNKNOWN_PROJECT
    # D5: the source-slug group is anchored on the first parsed record's
    # identity short hash (the red-first contract pins this form).
    group_slug = _source_slug(
        project_name, _identity_key(parsed[0], resolved_project))

    try:
        aggregated.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise FeedbackError(
            f"ingest-exec-quant: aggregated store is not writable: "
            f"{aggregated} ({exc})")

    ingested = 0
    duplicates = 0
    conflicts = 0
    groups_touched: set = set()
    lock_path = aggregated / AGGREGATE_LOCK_NAME
    with lock_path.open("a+") as lock_handle:
        fcntl.flock(lock_handle, fcntl.LOCK_EX)
        try:
            # C-13: the dedup check and every write share this one critical
            # section, so two concurrent intakes can never double-write.
            window = _scan_identity_window(aggregated)
            for record in parsed:
                key = _identity_key(record, resolved_project)
                content_hash = _content_hash(record)
                prior = window.get(key)
                if prior is not None:
                    if prior == content_hash:
                        duplicates += 1
                    else:  # keep-first: same identity, different content
                        conflicts += 1
                    continue
                _write_envelope_atomic(
                    aggregated / group_slug / AGGREGATED_RECORDS_DIRNAME,
                    _build_envelope(record, identity, package_path.name))
                window[key] = content_hash
                ingested += 1
                groups_touched.add(group_slug)
        finally:
            fcntl.flock(lock_handle, fcntl.LOCK_UN)

    return _intake_result(record_count, ingested, duplicates, skipped,
                          conflicts, len(groups_touched), manifest_unreadable)


def write_package(
    workspace_root: Path,
    index: Dict[str, Any],
    selected: List[Dict[str, Any]],
    notes: Optional[str] = None,
    include_introspection: bool = False,
    payload: Optional[Dict[str, Any]] = None,
    excluded: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Zip ``selected`` entries into ``packages/``; source files are never touched.

    When ``notes`` is given, a ``SUBMISSION-NOTES.md`` disposition record is
    added to the archive so every counter reset leaves auditable context.
    When ``include_introspection`` is set, introspection reports referenced by
    the selected entries ride along under ``introspection/`` and are listed in
    a MANIFEST section (engine-cli C-9..C-12).

    068 package leg: when ``payload`` (from ``_collect_exec_quant_payload``)
    is given, its records ride along under ``exec-quant/`` as a first-class
    payload (C-3) declared by ``exec-quant/payload-manifest.json`` (C-4) and
    a MANIFEST § Exec-Quant Payload section rendered by the same function
    (C-6). FR-019: the early return fires only when BOTH the feedback
    entries and the payload records are empty — payload-only packages are
    produced with an explicit ``Entries: 0``.
    """
    upstream = detect_upstream(index)
    payload_records = list(payload["records"]) if payload else []
    if not selected and not payload_records:
        result = {"packaged": 0, "zip": None, "missing": [],
                  "upstream": upstream,
                  "note": "No feedback entries or exec-quant payload records "
                          "to package."}
        if excluded:
            result["excluded"] = sorted({str(e.get("unit_id", "?")) for e in excluded})
        if payload is not None:
            result["exec_quant_payload"] = _payload_report(payload)
        return result

    store_dir = feedback_dir(workspace_root)
    packages_dir = store_dir / PACKAGES_DIRNAME
    packages_dir.mkdir(parents=True, exist_ok=True)
    zip_name = f"feedback-{timestamp_id()}.zip"
    zip_path = packages_dir / zip_name
    counter = 1
    while zip_path.exists():
        zip_path = packages_dir / f"feedback-{timestamp_id()}-{counter}.zip"
        counter += 1

    # FR-019: selected may be empty while a payload-only package is produced.
    time_range = (f"{selected[0].get('created', '-')} → "
                  f"{selected[-1].get('created', '-')}"
                  if selected else "-")
    manifest_lines = [
        "# Feedback Package Manifest",
        "",
        "> This feedback targets the Spec Kit framework itself (templates, "
        "commands, skills, scripts, docs) — not the LLM, agent CLI, harness, "
        "or any user project code.",
        "",
        f"- **Generated**: {now_iso()}",
        f"- **Entries**: {len(selected)}",
        f"- **Time range**: {time_range}",
        f"- **spec-kit version**: {_speckit_version()}",
        f"- **Install source**: {upstream.get('url') or 'unknown'}"
        + (f" @ {upstream['commit']}" if upstream.get("commit") else ""),
    ]
    if excluded:
        excluded_units = sorted({str(e.get("unit_id", "?")) for e in excluded})
        manifest_lines.append(
            f"- **Excluded (non-framework, kept local)**: {len(excluded)} "
            f"entr{'y' if len(excluded) == 1 else 'ies'} — "
            + ", ".join(excluded_units)
        )
    manifest_lines += [
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
        if payload is not None:
            # 068 C-3/C-4: payload members only under exec-quant/; record
            # members are byte-verbatim copies of the source bytes (zero
            # re-sort, re-encode, or field filtering); the machine manifest
            # and the human section below come from ONE renderer (C-6).
            payload_manifest, payload_lines = _render_payload_sections(payload)
            for record in payload_records:
                zf.writestr(f"{PAYLOAD_DIRNAME}/{PAYLOAD_RECORDS_DIRNAME}/"
                            f"{record['name']}", record["data"])
            zf.writestr(f"{PAYLOAD_DIRNAME}/{PAYLOAD_MANIFEST_NAME}",
                        json.dumps(payload_manifest, ensure_ascii=False,
                                   indent=2) + "\n")
            manifest_lines += payload_lines
        zf.writestr("MANIFEST.md", "\n".join(manifest_lines) + "\n")
        if notes and notes.strip():
            zf.writestr(
                "SUBMISSION-NOTES.md",
                "# Submission Notes (disposition of this batch)\n\n"
                f"- **Recorded**: {now_iso()}\n\n{notes.strip()}\n",
            )

    rel_zip = zip_path.relative_to(workspace_root).as_posix()
    result = {"packaged": len(packaged), "zip": rel_zip, "missing": missing,
              "excluded": sorted({str(e.get("unit_id", "?")) for e in (excluded or [])}),
              "upstream": upstream}
    if payload is not None:
        result["exec_quant_payload"] = _payload_report(payload)
    return result


def action_package(args: argparse.Namespace) -> Dict[str, Any]:
    """Zip pending entries for manual delivery. Source files are never touched.

    External entries (``kind: external``) are host-project-local by contract
    (engine-cli C-4): they are excluded from the upstream package and only
    surfaced as an ``excluded_external`` count.

    068 package leg: the workspace exec-quant store is swept read-only
    (C-1/C-2) and its records ride along as the exec-quant payload (FR-001
    full inclusion — the sweep is independent of the entry time filter, so
    no watermark exists). Every payload degradation is non-blocking (C-9):
    it surfaces as counters in the report faces, never as a failure.
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

    # Framework-scope filter: only feedback about the Spec Kit framework itself
    # is packaged for upstream delivery. User-project skill feedback stays local.
    framework_skills, bundle_source = framework_skill_names(workspace_root)
    excluded_framework = [
        e for e in selected
        if not is_framework_unit(str(e.get("unit_id", "")), framework_skills)
    ]
    included = [e for e in selected if e not in excluded_framework]
    excluded_units = sorted({str(e.get("unit_id", "?")) for e in excluded_framework})

    payload = _collect_exec_quant_payload(workspace_root)  # C-9: never raises
    result = write_package(workspace_root, {
        "upstream_repo": state["upstream_repo"],
        "introspections": state["introspections"],
    }, included,
                           include_introspection=bool(
                               getattr(args, "include_introspection", False)),
                           payload=payload, excluded=excluded_framework)
    result["excluded_external"] = excluded_external
    if excluded_units:
        result["excluded"] = excluded_units
    if not result.get("zip"):
        result["upstream"] = detect_upstream(
            {"upstream_repo": state["upstream_repo"]})
        if excluded_framework:
            note = ("All pending entries target non-framework units "
                    "(user-project skills); they stay local and are not "
                    "packaged for upstream delivery.")
            if bundle_source == "unresolved":
                note += (" The framework skill bundle could not be resolved, so "
                         "only /speckit.* command entries would be packaged.")
            result["note"] = note
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
    if action == "client-metrics":
        lines = ["Client loop metrics (read-built from existing records; "
                 "advisory only - not a gate, not a status transition, not a "
                 "threshold input):"]
        for name in ("capture_coverage", "into_loop_ratio", "closure_ratio",
                     "repeat_finding_rate"):
            row = payload["metrics"][name]
            if row.get("status") == "evaluated":
                lines.append(f"  {name}: {row['numerator']}/{row['denominator']}"
                             f" = {row['value']:.4g}")
            else:
                lines.append(f"  {name}: not-evaluated - {row['reason']}")
            if name == "repeat_finding_rate" and row.get("proxy"):
                lines.append(f"    ({row['proxy_label']})")
        return "\n".join(lines)
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
        if payload.get("excluded"):
            lines.append("  excluded non-framework units (kept local): "
                         + ", ".join(payload["excluded"]))
        rep = payload.get("exec_quant_payload")
        if rep:  # 068 C-7: payload inclusion visible on the text face too
            if rep.get("record_count"):
                lines.append(
                    f"  exec-quant payload: {rep['record_count']} record(s) "
                    f"(skipped unreadable: {rep['skipped_unreadable']}, "
                    f"truncated: {rep['truncated_count']})")
            else:
                lines.append(
                    "  exec-quant payload: none (no readable exec-quant "
                    "records — 无量化数据)")
        lines.extend(f"  {step}" for step in payload.get("next_steps", []))
        return "\n".join(lines)
    if action == "upstream":
        url = payload.get("url")
        if not url:
            return ("Upstream repo: unknown — configure once via "
                    "--action upstream --set <repo-url>")
        commit = f" @ {payload['commit']}" if payload.get("commit") else ""
        return f"Upstream repo ({payload.get('source')}): {url}{commit}"
    if action == "ingest-exec-quant":
        if not payload.get("record_count"):
            return ("Exec-quant payload: none (无量化数据) — nothing to "
                    "ingest; the feedback face was not touched.")
        lines = [
            f"Ingested exec-quant payload: {payload['record_count']} record(s) "
            f"({payload['ingested']} new, "
            f"{payload['duplicates_skipped']} duplicate(s) skipped, "
            f"{payload['skipped_unreadable']} skipped unreadable, "
            f"{payload['identity_conflicts']} identity conflict(s); "
            f"groups touched: {payload['groups_touched']})",
            "  next: aggregate is a separate explicit action (--action "
            "aggregate on the quant engine) — ingest never triggers it",
        ]
        if payload.get("manifest_unreadable"):
            lines.append(
                "  note: payload-manifest.json was missing/unreadable — "
                "members were attempted one by one; identity fell back to "
                "unknown-project")
        return "\n".join(lines)
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
    _sig_configure(parser)

    parser.add_argument(
        "--action",
        required=True,
        choices=["record", "status", "list", "dispose", "mark-submitted", "reindex",
                 "package", "cleanup", "upstream", "migrate-legacy",
                 "introspect-register", "args-manifest", "ingest-exec-quant",
                 "client-metrics"],
    )
    parser.add_argument("--package", default=None,
                        help="cleanup: path to the package zip (workspace-"
                             "relative or absolute), or 'latest'; "
                             "ingest-exec-quant: the inbound feedback bundle "
                             "to unpack (required)")
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
    parser.add_argument("--now", default=None,
                        help="inject a fixed UTC clock for every now_iso() / "
                             "timestamp_id() reading in this invocation: "
                             "YYYY-MM-DDTHH:MM:SSZ (second granularity); absent "
                             "= the real clock, byte-identical")
    parser.add_argument("--unit", default=None,
                        help="client-metrics: optional unit filter "
                             "(custom:<owner>/<name>); without it all client "
                             "units are in scope")
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
                   "introspect-register", "client-metrics", "args-manifest"):
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
    "client-metrics": action_client_metrics,
    "args-manifest": action_args_manifest,
    "ingest-exec-quant": action_ingest_exec_quant,
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


# --version, wired through the one version source (C-8)
#
# `guard_argv()` answers `--version` (and rejects an undeclared option) BEFORE any parser
# reads the line, so it works for a flat argparse parser, for one whose subcommands are
# required, and for the two modules that read sys.argv by hand. It writes nothing and
# resolves `<script-name> <framework-version>` from the nearest pyproject.toml at run
# time — this file carries no version literal. `--help` is left to the module's own body.
import sys as _sig_sys  # noqa: E402
import pathlib as _sig_pathlib

_SIG_DIR = str(_sig_pathlib.Path(__file__).resolve().parent)
if _SIG_DIR not in _sig_sys.path:
    _sig_sys.path.insert(0, _SIG_DIR)
try:  # the helper owns the rule; an engine copied WITHOUT it still runs its actions
    from script_interface_cli import configure_parser as _sig_configure  # noqa: E402
    from script_interface_cli import guard_argv as _sig_guard  # noqa: E402
except ImportError:  # a sandbox/handler copy carries the engine but not the helper
    def _sig_configure(parser, **_kwargs):
        return parser

    def _sig_guard(_argv=None, declared=None, **_kwargs):
        return None

def main(argv: Optional[List[str]] = None) -> int:
    _sig_guard(argv, declared=['--action', '--package', '--report-file', '--include-introspection', '--confirm', '--lifecycle-point', '--plan-file', '--dry-run', '--slice', '--kind', '--disposition', '--id', '--to', '--reason', '--ref', '--workspace-root', '--now', '--unit', '--unit-id', '--unit-type', '--run-id', '--review', '--review-file', '--points', '--points-file', '--partial', '--feature', '--feature-id', '--notes', '--threshold', '--since', '--limit', '--contains', '--all', '--set', '--format'])  # answer --version / reject an undeclared option
    parser = build_parser()
    args = parser.parse_args(argv)
    warn_anchor_mismatch(args.action, args)
    try:
        set_now_option(args.now)
        payload = _ACTIONS[args.action](args)
    except FeedbackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.format == "json" or args.action in (
            "record", "status", "mark-submitted", "reindex", "args-manifest",
            "client-metrics"):
        # args-manifest (063 C-22): pure JSON regardless of --format — the
        # machine face the compile-embeds renderer consumes.
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(args.action, payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
