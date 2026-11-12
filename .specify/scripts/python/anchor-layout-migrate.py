#!/usr/bin/env python3
"""anchor-layout-migrate.py — converge a project to the anchor layout (feature 094-era architecture).

Layout owned here (mechanism): the project anchors live at the `.specify/` root —
`features.md`, `constitution.md`, `glossary.md`, `register.md`, `tools.md` — and the feature-detail files
live at `.specify/features/<NNN>-<slug>.md`. The legacy layout kept the five anchors under
`.specify/memory/` and the details at `.specify/memory/features/<NNN>.md`.

`--check`  detect only: exit 0 clean, 1 findings (a plan), 2 input error.
`--apply`  archive-first convergence. Every replaced/moved/merged original is copied into
           `--archive-root` before the target changes; the legacy copy is removed only after its archive
           copy is verified. A placeholder target is replaced by the legacy real content; two real
           contents are merged (feature registries by table-row union, other anchors by append with a
           fixed marker). A merge never silently drops either side. Idempotent: a second apply is a no-op.
           Prints the reference paths the caller must update (the script never rewrites project documents).

Options (closed set): --workspace PATH, --action check|apply, --json, --placeholder-dir PATH,
--archive-root PATH. `-h/--help`, `--version` answer without acting.
Side effects: `--apply` writes under `.specify/` and the archive root; `--check` writes nothing.
Exit codes: 0 clean/applied; 1 findings (check); 2 argument or environment error.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ANCHORS = ("features.md", "constitution.md", "glossary.md", "register.md", "tools.md")
PLACEHOLDER_MARKER = "This file is a placeholder for the project"
FEATURE_ROW_RE = re.compile(r"^\|\s*(\d{3}[a-z]?)\s*\|")
LAST_UPDATED_RE = re.compile(r"\*\*Last Updated\*\*:\s*(\d{4}-\d{2}-\d{2})")
TOTAL_FEATURES_RE = re.compile(r"(\*\*Total Features\*\*:\s*)(\d+)")

MERGE_KINDS = (
    "placeholder-replace",
    "drop-placeholder",
    "dedupe-identical",
    "merge",
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"


def _ensure_trailing_newline(text: str) -> str:
    return text if text.endswith("\n") else text + "\n"


def _digest_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _placeholder_texts(placeholder_dir):
    texts = {}
    if not placeholder_dir:
        return texts
    root = Path(placeholder_dir).expanduser()
    for anchor in ANCHORS:
        candidate = root / anchor
        if not candidate.is_file():
            continue
        try:
            texts[anchor] = _normalized(_read_text(candidate))
        except (OSError, UnicodeDecodeError):
            continue
    return texts


def _is_placeholder(path: Path, anchor: str, placeholders):
    """True/False, or None when the file cannot be read as UTF-8 text."""
    try:
        text = _read_text(path)
    except (OSError, UnicodeDecodeError):
        return None
    norm = _normalized(text)
    if not norm.strip():
        return True
    expected = placeholders.get(anchor)
    if expected is not None and norm == expected:
        return True
    return PLACEHOLDER_MARKER in norm and len(norm.encode("utf-8")) <= 2048


def _feature_rows(text: str):
    rows = []
    for index, line in enumerate(text.splitlines()):
        match = FEATURE_ROW_RE.match(line)
        if match:
            rows.append((match.group(1), index, line))
    return rows


def _merge_features(target_text: str, legacy_text: str):
    target_rows = _feature_rows(target_text)
    legacy_rows = _feature_rows(legacy_text)
    if not target_rows:
        return (
            _merge_append(target_text, legacy_text, "features.md"),
            {"targetRows": 0, "legacyOnlyRows": len(legacy_rows), "duplicates": 0},
        )

    target_keys = {key for key, _index, _line in target_rows}
    seen = set()
    legacy_only = []
    duplicates = 0
    for key, _index, line in legacy_rows:
        if key in target_keys:
            duplicates += 1
            continue
        if key in seen:
            continue
        seen.add(key)
        legacy_only.append((key, line))
    legacy_only.sort(key=lambda item: item[0])

    lines = target_text.splitlines()
    insert_at = target_rows[-1][1] + 1
    insertion = [line for _key, line in legacy_only]
    if insertion:
        lines[insert_at:insert_at] = insertion
    merged = "\n".join(lines)
    total = len(target_keys | seen)
    merged = TOTAL_FEATURES_RE.sub(lambda m: f"{m.group(1)}{total}", merged, count=1)

    dates = []
    for text in (target_text, legacy_text):
        found = LAST_UPDATED_RE.search(text)
        if found:
            dates.append(found.group(1))
    if dates:
        merged = LAST_UPDATED_RE.sub(
            lambda m: f"**Last Updated**: {max(dates)}", merged, count=1
        )

    return (
        _ensure_trailing_newline(merged),
        {"targetRows": len(target_keys), "legacyOnlyRows": len(legacy_only),
         "duplicates": duplicates},
    )


def _merge_append(target_text: str, legacy_text: str, anchor: str) -> str:
    if _normalized(target_text) == _normalized(legacy_text):
        return _ensure_trailing_newline(target_text)
    marker = (
        "<!-- specify-migrate: legacy anchor .specify/memory/%s merged below; "
        "both originals archived; reconcile with the owning /speckit command -->"
        % anchor
    )
    return (
        target_text.rstrip("\n")
        + "\n\n---\n\n"
        + marker
        + "\n\n"
        + legacy_text.strip("\n")
        + "\n"
    )


def _merge_text(anchor: str, target_text: str, legacy_text: str):
    if anchor == "features.md":
        return _merge_features(target_text, legacy_text)
    merged = _merge_append(target_text, legacy_text, anchor)
    return merged, {"targetRows": 0, "legacyOnlyRows": 0, "duplicates": 0}


def _archive_copy(workspace: Path, archive_root: Path, source: Path) -> Path:
    try:
        rel = source.relative_to(workspace)
    except ValueError:
        rel = Path(source.name)
    if rel.parts and rel.parts[0] == ".specify":
        rel = Path(*rel.parts[1:])
    destination = archive_root / rel
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if not destination.is_file():
        raise OSError("archive copy missing: %s" % destination)
    return destination


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".anchor-merge-", dir=str(path.parent))
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _slug_from_registry(workspace: Path, fid: str):
    # The registry lives at the anchor root in a migrated project and under .specify/memory/ in a legacy one.
    for candidate in (workspace / ".specify" / "features.md",
                      workspace / ".specify" / "memory" / "features.md"):
        if candidate.is_file():
            registry = candidate
            break
    else:
        return None
    pattern = re.compile(r"^\|\s*" + re.escape(fid) + r"\s*\|")
    for line in registry.read_text(encoding="utf-8", errors="replace").splitlines():
        if not pattern.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        spec = cells[5] if len(cells) > 5 else ""
        match = re.search(r"specs/(\d{3})-([A-Za-z0-9-]+)/", spec)
        if match and match.group(1) == fid:
            return match.group(2)
    return None


def _slug_from_content(path: Path):
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines()[:12]:
        heading = re.sub(r"^#+\s*", "", line).strip()
        if heading:
            heading = re.sub(r"^\d{3}\s*[—:-]\s*", "", heading)
            slug = re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")
            return slug or None
    return None


def plan(workspace: Path, placeholder_dir=None):
    spec = workspace / ".specify"
    steps = []
    if not spec.is_dir():
        raise SystemExit("input error: no .specify/ directory under %s" % workspace)
    memory = spec / "memory"
    placeholders = _placeholder_texts(placeholder_dir)
    for anchor in ANCHORS:
        legacy = memory / anchor
        target = spec / anchor
        if not legacy.is_file():
            continue
        if target.is_symlink() or (target.exists() and not target.is_file()):
            steps.append({
                "kind": "refuse-existing-target",
                "anchor": anchor,
                "from": str(legacy),
                "to": str(target),
                "reason": "target is not a regular file; refusing to replace it",
            })
            continue
        if not target.exists():
            steps.append({
                "kind": "move",
                "anchor": anchor,
                "from": str(legacy),
                "to": str(target),
                "strategy": None,
                "archiveFrom": None,
                "archiveTo": None,
                "counts": {"targetRows": 0, "legacyOnlyRows": 0, "duplicates": 0},
                "status": "planned",
                "error": None,
            })
            continue
        legacy_placeholder = _is_placeholder(legacy, anchor, placeholders)
        target_placeholder = _is_placeholder(target, anchor, placeholders)
        if legacy_placeholder is None or target_placeholder is None:
            steps.append({
                "kind": "refuse-existing-target",
                "anchor": anchor,
                "from": str(legacy),
                "to": str(target),
                "reason": "anchor is not readable as UTF-8 text; refusing to merge",
            })
            continue
        try:
            legacy_text = _read_text(legacy)
            target_text = _read_text(target)
        except (OSError, UnicodeDecodeError) as exc:
            steps.append({
                "kind": "refuse-existing-target",
                "anchor": anchor,
                "from": str(legacy),
                "to": str(target),
                "reason": "unreadable anchor: %s" % exc,
            })
            continue
        if _normalized(legacy_text) == _normalized(target_text):
            kind, strategy = "dedupe-identical", "verbatim-identical"
        elif target_placeholder and not legacy_placeholder:
            kind, strategy = "placeholder-replace", "replace-placeholder"
        elif legacy_placeholder and not target_placeholder:
            kind, strategy = "drop-placeholder", "drop-placeholder"
        elif legacy_placeholder and target_placeholder:
            kind, strategy = "dedupe-identical", "both-placeholders"
        else:
            kind = "merge"
            strategy = "features-table-union" if anchor == "features.md" else "append-marker"
        step = {
            "kind": kind,
            "anchor": anchor,
            "from": str(legacy),
            "to": str(target),
            "strategy": strategy,
            "archiveFrom": None,
            "archiveTo": None,
            "counts": {"targetRows": 0, "legacyOnlyRows": 0, "duplicates": 0},
            "status": "planned",
            "error": None,
        }
        if kind == "merge":
            _merged, counts = _merge_text(anchor, target_text, legacy_text)
            step["counts"] = counts
        steps.append(step)

    legacy_details = memory / "features"
    if legacy_details.is_dir():
        for item in sorted(legacy_details.glob("[0-9][0-9][0-9].md")):
            fid = item.stem
            slug = _slug_from_registry(workspace, fid) or _slug_from_content(item) or "feature"
            target = spec / "features" / ("%s-%s.md" % (fid, slug))
            steps.append({
                "kind": "move",
                "anchor": "features/%s.md" % fid,
                "from": str(item),
                "to": str(target),
                "strategy": None,
                "archiveFrom": None,
                "archiveTo": None,
                "counts": {"targetRows": 0, "legacyOnlyRows": 0, "duplicates": 0},
                "status": "planned",
                "error": None,
            })
    return steps


def apply(workspace: Path, steps, archive_root: Path):
    applied = []
    skipped = []
    refused = []
    failed = []
    for step in steps:
        kind = step["kind"]
        if kind == "refuse-existing-target":
            refused.append(step)
            continue
        source = Path(step["from"])
        target = Path(step["to"])
        if kind == "move":
            if not source.is_file() or target.exists() or target.is_symlink():
                skipped.append(step)
                continue
            try:
                archive = _archive_copy(workspace, archive_root, source)
                target.parent.mkdir(parents=True, exist_ok=True)
                os.replace(source, target)
            except OSError as exc:
                failed.append({**step, "status": "failed", "error": str(exc)})
                continue
            applied.append({
                **step,
                "status": "applied",
                "archiveFrom": str(archive),
                "digestFrom": _digest_file(target),
            })
            continue

        try:
            legacy_text = _read_text(source)
            target_text = _read_text(target)
        except (OSError, UnicodeDecodeError) as exc:
            failed.append({**step, "status": "failed", "error": str(exc)})
            continue

        archive_from = None
        archive_to = None
        result_text = target_text
        counts = dict(step.get("counts") or {})
        try:
            if kind == "placeholder-replace":
                result_text = _ensure_trailing_newline(legacy_text)
            elif kind in ("drop-placeholder", "dedupe-identical"):
                result_text = target_text
            elif kind == "merge":
                result_text, counts = _merge_text(step["anchor"], target_text, legacy_text)
            else:
                failed.append({
                    **step, "status": "failed",
                    "error": "unknown merge kind: %s" % kind,
                })
                continue

            archive_from = _archive_copy(workspace, archive_root, source)
            if kind in ("placeholder-replace", "merge"):
                archive_to = _archive_copy(workspace, archive_root, target)
            if kind not in ("drop-placeholder", "dedupe-identical"):
                _atomic_write(target, result_text)
            if not archive_from.is_file():
                raise OSError("legacy archive copy missing before removal")
            if archive_to is not None and not archive_to.is_file():
                raise OSError("target archive copy missing before replacement")
            source.unlink()
        except OSError as exc:
            failed.append({
                **step, "status": "failed", "error": str(exc),
                "archiveFrom": str(archive_from) if archive_from else None,
                "archiveTo": str(archive_to) if archive_to else None,
            })
            continue

        applied.append({
            **step,
            "status": "applied",
            "counts": counts,
            "archiveFrom": str(archive_from) if archive_from else None,
            "archiveTo": str(archive_to) if archive_to else None,
            "digestFrom": _digest_text(legacy_text),
            "digestTo": _digest_text(target_text),
            "resultDigest": _digest_text(result_text),
        })
    return applied, skipped, refused, failed


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="anchor-layout-migrate.py",
        description=(
            "Detect or apply the anchor layout (.specify/{features,constitution,glossary,register,tools}.md; "
            ".specify/features/<NNN>-<slug>.md). Apply is archive-first and merges old/new anchors."
        ),
    )
    parser.add_argument("--action", choices=("check", "apply"), default="check")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument(
        "--placeholder-dir",
        default=None,
        help="Directory holding the packaged placeholder anchors (enables exact stub detection).",
    )
    parser.add_argument(
        "--archive-root",
        default=None,
        help="Archive root for apply (default: .specify/archive/anchor-layout/<UTC-ts>).",
    )
    parser.add_argument("--version", action="version", version="anchor-layout-migrate.py 2.0.0")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).expanduser().resolve()
    steps = plan(workspace, args.placeholder_dir)
    if args.action == "check":
        if args.as_json:
            print(json.dumps({"steps": steps, "clean": not steps}, indent=2))
        else:
            if not steps:
                print("anchor layout: clean")
            else:
                for step in steps:
                    print("%s: %s -> %s" % (step["kind"], step["from"], step["to"]))
        return 0 if not steps else 1

    archive_root = (
        Path(args.archive_root).expanduser().resolve()
        if args.archive_root
        else workspace / ".specify" / "archive" / "anchor-layout" / _utc_stamp()
    )
    applied, skipped, refused, failed = apply(workspace, steps, archive_root)
    if args.as_json:
        print(json.dumps({
            "applied": applied,
            "skipped": skipped,
            "refused": refused,
            "failed": failed,
            "archiveRoot": str(archive_root),
            "clean": not (applied or skipped or refused or failed),
        }, indent=2))
    else:
        for step in applied:
            print("applied: %s %s -> %s" % (step["kind"], step["from"], step["to"]))
        for step in steps:
            if step["kind"] == "refuse-existing-target":
                print("refused: %s (%s)" % (step["from"], step.get("reason", "")))
        for step in skipped:
            print("skipped: %s (target exists)" % step["from"])
        for step in failed:
            print("failed: %s (%s)" % (step["from"], step.get("error", "")))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
