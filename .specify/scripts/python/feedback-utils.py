#!/usr/bin/env python3
"""Feedback-as-files engine for Spec Kit.

Persists local, unit-scoped feedback entries produced at the wrap-up of a
*qualifying* flow (every skill; complex commands only) into the project
feedback store, using plain Markdown files plus a lightweight local JSON index
(no vector store). Patterned on ``memory-utils.py``.

Layout (relative to workspace root):

    .specify/memory/feedback/
        <created-ts>-<unit-slug>.md   # one file per recorded run
        index.json                    # store metadata + entry mirror
        .gitkeep                      # already present

An entry's ``unit_id`` must name a Spec Kit command or skill
(``/speckit.<command>`` | ``skill:<name>``); ``record`` rejects any other id.
Each entry is local-scoped (``scope: local``) and stays strictly distinct from
the global ``/speckit.review`` report.

Positioning: feedback targets the Spec Kit framework itself (templates,
commands, skills, scripts, docs) — never the LLM, agent CLI, harness, or the
user's project code. Entries are user data: recording and processing are fully
optional and ignorable. This engine performs **no network operations of any
kind**; ``package`` only produces a local zip that the user may send manually,
and ``mark-submitted`` merely resets the local counter ("user confirmed
disposition", NOT "uploaded").
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

FEEDBACK_SUBDIR = Path(".specify") / "memory" / "feedback"
PACKAGES_DIRNAME = "packages"
INDEX_NAME = "index.json"
STORE_NAME = "feedback"
DEFAULT_THRESHOLD = 10
NO_OP_POINT = "No significant optimization points identified this run."
DIST_NAME = "specify-cli"

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
             "feature", "partial", "created", "summary"]
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


def empty_index() -> Dict[str, Any]:
    return {
        "store": STORE_NAME,
        "updated": None,
        "threshold": DEFAULT_THRESHOLD,
        "count_since_submission": 0,
        "submitted_at": None,
        "entries": [],
    }


def load_index(workspace_root: Path) -> Dict[str, Any]:
    path = index_path(workspace_root)
    if not path.exists():
        return empty_index()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return empty_index()
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return empty_index()
    base = empty_index()
    base.update(data)
    return base


def save_index(workspace_root: Path, index: Dict[str, Any]) -> None:
    index["entries"] = sorted(
        index.get("entries", []), key=lambda e: e.get("created", ""), reverse=True
    )
    index["store"] = STORE_NAME
    index["updated"] = now_iso()
    ensure_feedback_dir(workspace_root)
    index_path(workspace_root).write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def entry_meta(meta: Dict[str, Any], filename: str) -> Dict[str, Any]:
    return {
        "id": meta.get("id", ""),
        "file": filename,
        "unit_id": meta.get("unit_id", ""),
        "unit_type": meta.get("unit_type", ""),
        "run_id": meta.get("run_id", ""),
        "feature": meta.get("feature", ""),
        "partial": bool(meta.get("partial", False)),
        "created": meta.get("created", ""),
        "summary": meta.get("summary", ""),
    }


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #
def action_record(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    unit_id = (args.unit_id or "").strip()
    if not validate_unit_id(unit_id):
        raise FeedbackError(
            "Invalid --unit-id; expected '/speckit.<command>' or 'skill:<name>'."
        )
    unit_type = (args.unit_type or "").strip()
    if unit_type not in ("skill", "command"):
        raise FeedbackError("--unit-type must be 'skill' or 'command'.")
    run_id = (args.run_id or "").strip()
    if not run_id:
        raise FeedbackError("--run-id is required.")

    review = read_review(args)
    if not review.strip():
        raise FeedbackError("record requires a non-empty --review / --review-file.")
    points = read_points(args)
    if not points:
        raise FeedbackError(
            "record requires --points / --points-file with at least one line "
            f"(use '{NO_OP_POINT}' for a clean run)."
        )

    index = load_index(workspace_root)
    threshold = resolve_threshold(args.threshold, index.get("threshold"))
    index["threshold"] = threshold
    entries = index["entries"]

    existing = next(
        (e for e in entries if e.get("unit_id") == unit_id and e.get("run_id") == run_id),
        None,
    )
    if existing:
        rel = (FEEDBACK_SUBDIR / existing["file"]).as_posix()
        count = index.get("count_since_submission", 0)
        return {
            "id": existing.get("id", ""),
            "path": rel,
            "duplicate": True,
            "count_since_submission": count,
            "threshold": threshold,
            "should_prompt": should_prompt(count, threshold),
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
        "partial": partial,
        "created": created,
        "summary": make_summary(review),
    }
    (target_dir / filename).write_text(
        compose_entry(meta, review, points, partial), encoding="utf-8"
    )

    entries.append(entry_meta(meta, filename))
    index["count_since_submission"] = index.get("count_since_submission", 0) + 1
    save_index(workspace_root, index)

    count = index["count_since_submission"]
    rel = (FEEDBACK_SUBDIR / filename).as_posix()
    return {
        "id": entry_id,
        "path": rel,
        "duplicate": False,
        "count_since_submission": count,
        "threshold": threshold,
        "should_prompt": should_prompt(count, threshold),
    }


def action_status(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    index = load_index(workspace_root)
    threshold = resolve_threshold(args.threshold, index.get("threshold"))
    count = index.get("count_since_submission", 0)
    return {
        "count_since_submission": count,
        "threshold": threshold,
        "should_prompt": should_prompt(count, threshold),
        "total_entries": len(index.get("entries", [])),
        "submitted_at": index.get("submitted_at"),
    }


def action_list(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    limit = max(1, args.limit)
    unit_id = (args.unit_id or "").strip()
    unit_type = (args.unit_type or "").strip()
    since = (args.since or "").strip()

    items: List[Dict[str, Any]] = []
    for entry in load_index(workspace_root).get("entries", []):
        if unit_id and entry.get("unit_id") != unit_id:
            continue
        if unit_type and entry.get("unit_type") != unit_type:
            continue
        if since and str(entry.get("created", "")) < since:
            continue
        item = dict(entry)
        item["path"] = (FEEDBACK_SUBDIR / entry["file"]).as_posix()
        items.append(item)
    items.sort(key=lambda e: e.get("created", ""), reverse=True)
    return {"count": min(len(items), limit), "matches": items[:limit]}


def action_mark_submitted(args: argparse.Namespace) -> Dict[str, Any]:
    """Reset the local counter after the user confirms disposition.

    This is purely local bookkeeping — it does NOT upload or transmit anything.
    """
    workspace_root = resolve_workspace_root(args.workspace_root)
    index = load_index(workspace_root)
    reset_from = index.get("count_since_submission", 0)
    submitted_at = now_iso()
    index["count_since_submission"] = 0
    index["submitted_at"] = submitted_at
    save_index(workspace_root, index)
    return {"submitted_at": submitted_at, "reset_from": reset_from}


def action_reindex(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    prior = load_index(workspace_root)
    submitted_at = prior.get("submitted_at")
    threshold = resolve_threshold(args.threshold, prior.get("threshold"))

    target = feedback_dir(workspace_root)
    entries: List[Dict[str, Any]] = []
    if target.exists():
        for path in sorted(target.glob("*.md")):
            meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
            if not meta:
                continue
            entries.append(entry_meta(meta, path.name))

    index = empty_index()
    index["threshold"] = threshold
    index["submitted_at"] = submitted_at
    if prior.get("upstream_repo"):
        index["upstream_repo"] = prior["upstream_repo"]
    index["entries"] = entries
    index["count_since_submission"] = count_since_submission(entries, submitted_at)
    save_index(workspace_root, index)
    return {"reindexed": len(entries)}


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

    Priority: user-configured ``upstream_repo`` in index.json > PEP 610
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
    index = load_index(workspace_root)
    set_url = (args.set_url or "").strip()
    if set_url:
        index["upstream_repo"] = set_url
        save_index(workspace_root, index)
    return detect_upstream(index)


def action_package(args: argparse.Namespace) -> Dict[str, Any]:
    """Zip pending entries for manual delivery. Source files are never touched."""
    workspace_root = resolve_workspace_root(args.workspace_root)
    index = load_index(workspace_root)
    submitted_at = index.get("submitted_at")
    entries = index.get("entries", [])
    if not args.all and submitted_at:
        selected = [e for e in entries if str(e.get("created", "")) > submitted_at]
    else:
        selected = list(entries)
    selected.sort(key=lambda e: e.get("created", ""))

    upstream = detect_upstream(index)
    if not selected:
        return {
            "packaged": 0,
            "zip": None,
            "upstream": upstream,
            "note": "No feedback entries to package.",
        }

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
        "| Created | Unit | Partial | Summary |",
        "|---------|------|---------|---------|",
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
                f"| {entry.get('partial', False)} | {summary} |"
            )
        zf.writestr("MANIFEST.md", "\n".join(manifest_lines) + "\n")

    rel_zip = zip_path.relative_to(workspace_root).as_posix()
    return {
        "packaged": len(packaged),
        "zip": rel_zip,
        "missing": missing,
        "upstream": upstream,
        "next_steps": _send_guidance(upstream)
        + ["After you have dealt with the batch (sent or deliberately ignored), "
           "reset the local counter: --action mark-submitted"],
    }


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
        choices=["record", "status", "list", "mark-submitted", "reindex",
                 "package", "upstream"],
    )
    parser.add_argument("--workspace-root", default=None)
    parser.add_argument("--unit-id", default=None)
    parser.add_argument("--unit-type", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--review", default=None)
    parser.add_argument("--review-file", default=None)
    parser.add_argument("--points", default=None)
    parser.add_argument("--points-file", default=None)
    parser.add_argument("--partial", action="store_true")
    parser.add_argument("--feature", default=None)
    parser.add_argument("--threshold", type=int, default=None)
    parser.add_argument("--since", default=None)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--all", action="store_true",
                        help="package: include entries from before the last "
                             "mark-submitted as well")
    parser.add_argument("--set", dest="set_url", default=None,
                        help="upstream: persist the upstream repo URL")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


_ACTIONS = {
    "record": action_record,
    "status": action_status,
    "list": action_list,
    "mark-submitted": action_mark_submitted,
    "reindex": action_reindex,
    "package": action_package,
    "upstream": action_upstream,
}


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = _ACTIONS[args.action](args)
    except FeedbackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.format == "json" or args.action in ("record", "status", "mark-submitted", "reindex"):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(args.action, payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
