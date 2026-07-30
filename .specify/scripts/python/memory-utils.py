#!/usr/bin/env python3
"""Memory-as-files engine for Spec Kit.

Persists structured records of conversations that happen *through* Spec Kit
commands or skills into the project memory directory, using plain Markdown
files plus a lightweight local JSON index (no vector store).

Layout (relative to workspace root):

    .specify/memory/session/     # short-term / working memory (append-only)
    .specify/memory/knowledge/   # long-term / distilled memory (upsert by slug)
    .specify/memory/<scope>/index.json

Only conversations driven by a `/speckit.<command>` or a `skill:<name>` source
are recorded; the `record` action rejects any other `--source`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCOPES = ("session", "knowledge")
MEMORY_SUBDIR = Path(".specify") / "memory"
INDEX_NAME = "index.json"

# A source is valid only when it names a Spec Kit command or skill.
_SOURCE_RE = re.compile(r"^(?:/speckit\.[a-z0-9][a-z0-9._-]*|skill:[a-z0-9][a-z0-9._-]*)$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_WORD_RE = re.compile(r"[a-z0-9]+")


class MemoryError(ValueError):
    """Raised for user-facing validation failures."""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def timestamp_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def slugify(text: str, fallback: str = "entry") -> str:
    slug = _SLUG_RE.sub("-", (text or "").strip().lower()).strip("-")
    slug = slug[:60].strip("-")
    return slug or fallback


def stable_slug(text: str) -> str:
    """ASCII-safe slug that stays unique per distinct title.

    A plain ASCII slug silently drops non-ASCII (e.g. CJK) characters, so two
    different Chinese titles could collapse to the same slug and overwrite each
    other under knowledge's upsert-by-slug. When the title carries non-ASCII
    content (or yields no ASCII at all), append a short stable hash of the
    normalized title so identical titles still upsert while distinct ones do not
    collide.
    """
    text = (text or "").strip()
    if not text:
        return "entry"
    ascii_slug = slugify(text)
    has_non_ascii = any(ord(ch) > 127 for ch in text)
    if not has_non_ascii and ascii_slug != "entry":
        return ascii_slug
    digest = hashlib.sha1(text.lower().encode("utf-8")).hexdigest()[:8]
    return f"mem-{digest}" if ascii_slug == "entry" else f"{ascii_slug}-{digest}"


def validate_source(source: str) -> bool:
    return bool(source) and bool(_SOURCE_RE.match(source.strip()))


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


def memory_root(workspace_root: Path) -> Path:
    return Path(workspace_root).resolve() / MEMORY_SUBDIR


def scope_dir(workspace_root: Path, scope: str) -> Path:
    if scope not in SCOPES:
        raise MemoryError(f"Unknown scope: {scope} (expected one of {', '.join(SCOPES)})")
    return memory_root(workspace_root) / scope


def ensure_scope_dir(workspace_root: Path, scope: str) -> Path:
    target = scope_dir(workspace_root, scope)
    target.mkdir(parents=True, exist_ok=True)
    return target


def read_content(args: argparse.Namespace) -> str:
    if args.content is not None:
        return args.content
    if args.content_file:
        return Path(args.content_file).read_text(encoding="utf-8")
    if not sys.stdin.isatty():
        data = sys.stdin.read()
        if data.strip():
            return data
    raise MemoryError("record requires --content, --content-file, or piped stdin")


def make_summary(content: str, title: str) -> str:
    for line in content.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:200]
    return (title or "").strip()[:200]


def parse_tags(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    parts = re.split(r"[,\s]+", raw.strip())
    seen: List[str] = []
    for part in parts:
        tag = part.strip().lower()
        if tag and tag not in seen:
            seen.append(tag)
    return seen


def tokenize(text: str) -> List[str]:
    return _WORD_RE.findall((text or "").lower())


# --------------------------------------------------------------------------- #
# Frontmatter (minimal, dependency-free)
# --------------------------------------------------------------------------- #
def _scalar(value: str) -> Any:
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return value.strip().strip('"')


def dump_frontmatter(meta: Dict[str, Any]) -> str:
    order = ["id", "scope", "source", "feature", "tags", "title", "created", "session_id", "summary"]
    lines = ["---"]
    for key in order:
        if key not in meta:
            continue
        value = meta[key]
        if value in (None, ""):
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


def compose_entry(meta: Dict[str, Any], body: str) -> str:
    return dump_frontmatter(meta) + "\n\n" + body.strip() + "\n"


# --------------------------------------------------------------------------- #
# Index
# --------------------------------------------------------------------------- #
def index_path(workspace_root: Path, scope: str) -> Path:
    return scope_dir(workspace_root, scope) / INDEX_NAME


def load_index(workspace_root: Path, scope: str) -> Dict[str, Any]:
    path = index_path(workspace_root, scope)
    if not path.exists():
        return {"scope": scope, "updated": None, "entries": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {"scope": scope, "updated": None, "entries": []}
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        return {"scope": scope, "updated": None, "entries": []}
    return data


def save_index(workspace_root: Path, scope: str, entries: List[Dict[str, Any]]) -> None:
    entries = sorted(entries, key=lambda e: e.get("created", ""), reverse=True)
    payload = {"scope": scope, "updated": now_iso(), "entries": entries}
    ensure_scope_dir(workspace_root, scope)
    index_path(workspace_root, scope).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def entry_meta(meta: Dict[str, Any], filename: str) -> Dict[str, Any]:
    record = {
        "id": meta.get("id", ""),
        "file": filename,
        "scope": meta.get("scope", ""),
        "source": meta.get("source", ""),
        "feature": meta.get("feature", ""),
        "tags": meta.get("tags", []),
        "title": meta.get("title", ""),
        "created": meta.get("created", ""),
        "summary": meta.get("summary", ""),
    }
    if meta.get("session_id"):
        record["session_id"] = meta["session_id"]
    return record


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #
def action_record(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    scope = args.scope
    source = (args.source or "").strip()
    if not validate_source(source):
        raise MemoryError(
            "Invalid --source; memory only records Spec Kit conversations. "
            "Use '/speckit.<command>' or 'skill:<name>'."
        )

    content = read_content(args)
    title = (args.title or "").strip()
    tags = parse_tags(args.tags)
    created = now_iso()
    first_line = content.splitlines()[0] if content.strip() else ""
    slug = stable_slug(title or first_line)

    target_dir = ensure_scope_dir(workspace_root, scope)
    index = load_index(workspace_root, scope)
    entries = index["entries"]

    if scope == "knowledge":
        filename = f"{slug}.md"
        entry_id = slug
        existing = next((e for e in entries if e.get("file") == filename), None)
        if existing:
            merged = list(existing.get("tags", []))
            for tag in tags:
                if tag not in merged:
                    merged.append(tag)
            tags = merged
    else:
        entry_id = f"{timestamp_id()}-{slug}"
        filename = f"{entry_id}.md"
        counter = 1
        while (target_dir / filename).exists():
            filename = f"{entry_id}-{counter}.md"
            counter += 1
        entry_id = filename[:-3]

    meta = {
        "id": entry_id,
        "scope": scope,
        "source": source,
        "feature": (args.feature or "").strip(),
        "tags": tags,
        "title": title or slug.replace("-", " "),
        "created": created,
        "session_id": (args.session_id or "").strip(),
        "summary": make_summary(content, title),
    }
    (target_dir / filename).write_text(compose_entry(meta, content), encoding="utf-8")

    entries = [e for e in entries if e.get("file") != filename]
    entries.append(entry_meta(meta, filename))
    save_index(workspace_root, scope, entries)

    rel = (target_dir / filename).resolve().relative_to(workspace_root).as_posix()
    return {"id": entry_id, "scope": scope, "path": rel}


def _score_entry(entry: Dict[str, Any], query_tokens: List[str]) -> int:
    if not query_tokens:
        return 0
    haystack = tokenize(
        " ".join(
            [
                str(entry.get("title", "")),
                str(entry.get("summary", "")),
                " ".join(entry.get("tags", []) or []),
                str(entry.get("source", "")),
                str(entry.get("feature", "")),
            ]
        )
    )
    counts: Dict[str, int] = {}
    for token in haystack:
        counts[token] = counts.get(token, 0) + 1
    score = 0
    for token in query_tokens:
        if token in counts:
            score += 2 + counts[token]
    return score


def _collect_scopes(scope: str) -> List[str]:
    return list(SCOPES) if scope == "all" else [scope]


def action_recall(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    if args.scope != "all" and args.scope not in SCOPES:
        raise MemoryError(f"Unknown scope: {args.scope}")

    query_tokens = tokenize(args.query or "")
    tag_filter = parse_tags(args.tags)
    source_filter = (args.source or "").strip()
    feature_filter = (args.feature or "").strip()
    since = (args.since or "").strip()
    limit = max(1, args.limit)

    candidates: List[Dict[str, Any]] = []
    for scope in _collect_scopes(args.scope):
        for entry in load_index(workspace_root, scope)["entries"]:
            if tag_filter and not (set(tag_filter) & set(entry.get("tags", []) or [])):
                continue
            if source_filter and entry.get("source") != source_filter:
                continue
            if feature_filter and entry.get("feature") != feature_filter:
                continue
            if since and str(entry.get("created", "")) < since:
                continue
            score = _score_entry(entry, query_tokens)
            if query_tokens and score == 0:
                continue
            item = dict(entry)
            item["score"] = score
            item["path"] = (MEMORY_SUBDIR / scope / entry["file"]).as_posix()
            candidates.append(item)

    candidates.sort(key=lambda e: (e["score"], e.get("created", "")), reverse=True)
    return {"count": min(len(candidates), limit), "matches": candidates[:limit]}


def action_list(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    limit = max(1, args.limit)
    items: List[Dict[str, Any]] = []
    for scope in _collect_scopes(args.scope):
        for entry in load_index(workspace_root, scope)["entries"]:
            item = dict(entry)
            item["path"] = (MEMORY_SUBDIR / scope / entry["file"]).as_posix()
            items.append(item)
    items.sort(key=lambda e: e.get("created", ""), reverse=True)
    return {"count": min(len(items), limit), "matches": items[:limit]}


def action_prune(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    scope = args.scope
    if scope not in SCOPES:
        raise MemoryError(f"prune requires a concrete scope, got: {scope}")
    if args.max_entries is None and args.max_age_days is None:
        raise MemoryError("prune requires --max-entries and/or --max-age-days")

    entries = sorted(
        load_index(workspace_root, scope)["entries"],
        key=lambda e: e.get("created", ""),
        reverse=True,
    )
    keep: List[Dict[str, Any]] = []
    removed: List[str] = []
    cutoff = None
    if args.max_age_days is not None:
        cutoff_dt = datetime.now(timezone.utc).timestamp() - args.max_age_days * 86400

    for position, entry in enumerate(entries):
        drop = False
        if args.max_entries is not None and position >= args.max_entries:
            drop = True
        if args.max_age_days is not None and not drop:
            created = str(entry.get("created", ""))
            try:
                created_ts = datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(
                    tzinfo=timezone.utc
                ).timestamp()
                if created_ts < cutoff_dt:
                    drop = True
            except ValueError:
                pass
        if drop:
            path = scope_dir(workspace_root, scope) / entry.get("file", "")
            if path.exists():
                path.unlink()
            removed.append(entry.get("file", ""))
        else:
            keep.append(entry)

    save_index(workspace_root, scope, keep)
    return {"scope": scope, "removed": removed, "remaining": len(keep)}


def action_reindex(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    result: Dict[str, Any] = {}
    for scope in _collect_scopes(args.scope):
        target = scope_dir(workspace_root, scope)
        entries: List[Dict[str, Any]] = []
        if target.exists():
            for path in sorted(target.glob("*.md")):
                meta, _ = parse_frontmatter(path.read_text(encoding="utf-8"))
                if not meta:
                    continue
                meta.setdefault("scope", scope)
                entries.append(entry_meta(meta, path.name))
        save_index(workspace_root, scope, entries)
        result[scope] = len(entries)
    return {"reindexed": result}


# --------------------------------------------------------------------------- #
# Rendering / CLI
# --------------------------------------------------------------------------- #
def render_text(action: str, payload: Dict[str, Any]) -> str:
    if action in ("recall", "list"):
        matches = payload.get("matches", [])
        if not matches:
            return "No matching memory entries."
        lines = []
        for item in matches:
            tags = ", ".join(item.get("tags", []) or []) or "-"
            score = f" score={item['score']}" if "score" in item else ""
            lines.append(f"- [{item.get('scope', '?')}] {item.get('title', '(untitled)')}{score}")
            lines.append(f"  path: {item.get('path', '')}")
            lines.append(f"  source: {item.get('source', '-')} | feature: {item.get('feature') or '-'} | tags: {tags}")
            lines.append(f"  created: {item.get('created', '-')}")
            if item.get("summary"):
                lines.append(f"  summary: {item['summary']}")
        return "\n".join(lines)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Spec Kit memory-as-files engine")
    parser.add_argument(
        "--action",
        required=True,
        choices=["record", "recall", "list", "prune", "reindex"],
    )
    parser.add_argument("--workspace-root", default=None)
    parser.add_argument("--scope", default="session")
    parser.add_argument("--source", default=None)
    parser.add_argument("--title", default=None)
    parser.add_argument("--content", default=None)
    parser.add_argument("--content-file", default=None)
    parser.add_argument("--tags", default=None)
    parser.add_argument("--feature", default=None)
    parser.add_argument("--session-id", default=None)
    parser.add_argument("--query", default=None)
    parser.add_argument("--since", default=None)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--max-entries", type=int, default=None)
    parser.add_argument("--max-age-days", type=int, default=None)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


_ACTIONS = {
    "record": action_record,
    "recall": action_recall,
    "list": action_list,
    "prune": action_prune,
    "reindex": action_reindex,
}


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = _ACTIONS[args.action](args)
    except MemoryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.format == "json" or args.action in ("record", "prune", "reindex"):
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(args.action, payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
