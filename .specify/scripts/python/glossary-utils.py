#!/usr/bin/env python3
"""Glossary-as-a-file engine for Spec Kit.

Manages the single project-wide glossary at ``.specify/memory/glossary.md`` —
a human-readable Markdown table anchoring project vocabulary and correcting
voice/dictated input (homophones, easily-confused words). Patterned on
``feedback-utils.py`` / ``memory-utils.py``: plain Markdown, stdlib only.

Scope discipline (Constitution Principle IX): this engine performs only
deterministic FILE operations (init / list / validate / add / remove) and
STRUCTURAL conflict detection. Fuzzy homophone / meaning judgment is left to
the AI agent (prompt side). The engine's single guarantee for conflicts is that
``add`` refuses to write a conflicting change without an explicit
``--confirmed-resolution``.

Actions:
    init             create the glossary from a template if absent (non-destructive)
    list             emit {count, entries[]} parsed from the table
    validate         check the file against the format contract
    detect-conflict  report structural collisions for a candidate term
    add              add/confirm an entry (conflict- and precedence-guarded)
    remove           remove an entry by canonical term (no-op if absent)

All actions print JSON to stdout; validation failures exit non-zero with a
message on stderr.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

GLOSSARY_PATH = Path(".specify") / "memory" / "glossary.md"
DEFAULT_TEMPLATE = Path("templates") / "glossary-template.md"
TABLE_HEADER_RE = re.compile(r"^\|\s*Canonical\s*\|\s*Variants\s*\|", re.IGNORECASE)
SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|?\s*$")
VALID_ORIGIN = ("auto", "user")
VALID_STATUS = ("proposed", "confirmed")
PLACEHOLDER_CANONICAL = "none yet."


class GlossaryError(ValueError):
    """User-facing validation failure (exit code 2)."""


# --------------------------------------------------------------------------- #
# Helpers (pure)
# --------------------------------------------------------------------------- #
def split_variants(raw: str) -> List[str]:
    if raw is None:
        return []
    raw = raw.strip()
    if raw in ("", "-"):
        return []
    return [v.strip() for v in raw.split(",") if v.strip()]


def join_variants(variants: List[str]) -> str:
    cleaned = [v.strip() for v in (variants or []) if v.strip()]
    return ", ".join(cleaned) if cleaned else "-"


def _split_row(line: str) -> List[str]:
    """Split a Markdown table row into trimmed cell values."""
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [c.strip() for c in inner.split("|")]


def is_placeholder(entry: Dict[str, Any]) -> bool:
    return entry.get("canonical", "").strip().lower() == PLACEHOLDER_CANONICAL


# --------------------------------------------------------------------------- #
# Parse / serialize
# --------------------------------------------------------------------------- #
def parse_entries(text: str) -> List[Dict[str, Any]]:
    """Parse the glossary table into entry dicts (placeholders excluded)."""
    lines = text.splitlines()
    entries: List[Dict[str, Any]] = []
    in_table = False
    for line in lines:
        if TABLE_HEADER_RE.match(line):
            in_table = True
            continue
        if not in_table:
            continue
        if SEPARATOR_RE.match(line):
            continue
        if not line.strip().startswith("|"):
            if line.strip() == "":
                continue
            break  # table ended
        cells = _split_row(line)
        if len(cells) < 5:
            continue
        canonical, variants, meaning, origin, status = cells[:5]
        entry = {
            "canonical": canonical,
            "variants": split_variants(variants),
            "meaning": meaning,
            "origin": origin.lower(),
            "status": status.lower(),
        }
        if is_placeholder(entry):
            continue
        entries.append(entry)
    return entries


def render_row(entry: Dict[str, Any]) -> str:
    return "| {canonical} | {variants} | {meaning} | {origin} | {status} |".format(
        canonical=entry["canonical"],
        variants=join_variants(entry.get("variants", [])),
        meaning=entry.get("meaning", ""),
        origin=entry.get("origin", "auto"),
        status=entry.get("status", "proposed"),
    )


def replace_table(text: str, entries: List[Dict[str, Any]]) -> str:
    """Return the file text with the data rows replaced by ``entries``.

    Preserves everything up to and including the header + separator; rewrites
    the body rows. If no entries remain, writes the ``None yet.`` placeholder.
    """
    lines = text.splitlines()
    out: List[str] = []
    idx = 0
    header_seen = False
    while idx < len(lines):
        line = lines[idx]
        out.append(line)
        idx += 1
        if TABLE_HEADER_RE.match(line):
            header_seen = True
            # keep the separator line if present
            if idx < len(lines) and SEPARATOR_RE.match(lines[idx]):
                out.append(lines[idx])
                idx += 1
            break
    if not header_seen:
        raise GlossaryError("glossary table header not found")
    # skip existing data rows (until blank line or non-row)
    while idx < len(lines):
        line = lines[idx]
        if line.strip().startswith("|"):
            idx += 1
            continue
        break
    # emit new rows
    if entries:
        for entry in entries:
            out.append(render_row(entry))
    else:
        out.append("| None yet. | - | - | - | - |")
    # append remaining tail
    while idx < len(lines):
        out.append(lines[idx])
        idx += 1
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


# --------------------------------------------------------------------------- #
# Store
# --------------------------------------------------------------------------- #
def glossary_file(root: Path) -> Path:
    return Path(root).resolve() / GLOSSARY_PATH


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def find_entry(entries: List[Dict[str, Any]], canonical: str) -> Optional[Dict[str, Any]]:
    key = canonical.strip().lower()
    for e in entries:
        if e["canonical"].strip().lower() == key:
            return e
    return None


def detect_conflict(
    entries: List[Dict[str, Any]], canonical: str, variants: List[str]
) -> Dict[str, Any]:
    """Structural collision detection only (no phonetics)."""
    key = canonical.strip().lower()
    collides: List[str] = []
    kind: Optional[str] = None
    # identical canonical
    existing = find_entry(entries, canonical)
    if existing is not None:
        collides.append(existing["canonical"])
        kind = "same-term-diff-meaning"
    # a proposed variant already bound to a different canonical
    variant_keys = {v.strip().lower() for v in variants}
    for e in entries:
        if e["canonical"].strip().lower() == key:
            continue
        ev = {v.strip().lower() for v in e["variants"]}
        if variant_keys & ev or key in ev or (e["canonical"].strip().lower() in variant_keys):
            if e["canonical"] not in collides:
                collides.append(e["canonical"])
            kind = kind or "homophone/near-duplicate"
    return {"conflict": bool(collides), "kind": kind, "collidesWith": collides}


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #
def action_init(args: argparse.Namespace) -> Dict[str, Any]:
    root = Path(args.root)
    target = glossary_file(root)
    template = Path(args.from_template) if args.from_template else (root / DEFAULT_TEMPLATE)
    if target.exists() and not args.force:
        return {"created": False, "reason": "exists", "path": str(target)}
    if not template.exists():
        raise GlossaryError(f"template not found: {template}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(read_text(template), encoding="utf-8")
    return {"created": True, "path": str(target)}


def action_list(args: argparse.Namespace) -> Dict[str, Any]:
    target = glossary_file(Path(args.root))
    if not target.exists():
        raise GlossaryError(f"glossary not found: {target}")
    entries = parse_entries(read_text(target))
    return {"count": len(entries), "entries": entries}


def action_validate(args: argparse.Namespace) -> Dict[str, Any]:
    target = glossary_file(Path(args.root))
    if not target.exists():
        raise GlossaryError(f"glossary not found: {target}")
    text = read_text(target)
    if not re.search(r"^#\s+.*[Gg]lossary", text, re.MULTILINE):
        raise GlossaryError("missing glossary H1 title")
    if not any(TABLE_HEADER_RE.match(l) for l in text.splitlines()):
        raise GlossaryError("missing '| Canonical | ... |' table header")
    for e in parse_entries(text):
        if not e["canonical"]:
            raise GlossaryError("entry with empty Canonical")
        if not e["meaning"]:
            raise GlossaryError(f"entry '{e['canonical']}' has empty Meaning")
        if e["origin"] not in VALID_ORIGIN:
            raise GlossaryError(f"entry '{e['canonical']}' has invalid Origin '{e['origin']}'")
        if e["status"] not in VALID_STATUS:
            raise GlossaryError(f"entry '{e['canonical']}' has invalid Status '{e['status']}'")
    return {"valid": True, "path": str(target)}


def action_detect_conflict(args: argparse.Namespace) -> Dict[str, Any]:
    target = glossary_file(Path(args.root))
    entries = parse_entries(read_text(target)) if target.exists() else []
    return detect_conflict(entries, args.canonical, split_variants(args.variants or ""))


def action_add(args: argparse.Namespace) -> Dict[str, Any]:
    if args.origin not in VALID_ORIGIN:
        raise GlossaryError(f"invalid --origin '{args.origin}'")
    if args.status not in VALID_STATUS:
        raise GlossaryError(f"invalid --status '{args.status}'")
    target = glossary_file(Path(args.root))
    if not target.exists():
        raise GlossaryError(f"glossary not found (run init first): {target}")
    text = read_text(target)
    entries = parse_entries(text)
    variants = split_variants(args.variants or "")
    existing = find_entry(entries, args.canonical)

    # Precedence: an auto proposal MUST NOT overwrite a user entry without confirmation.
    if existing is not None and existing["origin"] == "user" and args.origin == "auto" \
            and not args.confirmed_resolution:
        raise GlossaryError(
            f"'{args.canonical}' is user-authored; auto proposal cannot overwrite it "
            f"without --confirmed-resolution"
        )

    # Conflict guard: refuse conflicting write without an explicit resolution.
    conflict = detect_conflict([e for e in entries if e is not existing], args.canonical, variants)
    if conflict["conflict"] and not args.confirmed_resolution:
        payload = {"error": "conflict", **conflict, "written": False}
        raise GlossaryError(json.dumps(payload, ensure_ascii=False))

    new_entry = {
        "canonical": args.canonical.strip(),
        "variants": variants,
        "meaning": (args.meaning or "").strip(),
        "origin": args.origin,
        "status": args.status,
    }
    if existing is not None:
        entries = [new_entry if e is existing else e for e in entries]
    else:
        entries.append(new_entry)
    target.write_text(replace_table(text, entries), encoding="utf-8")
    return {"written": True, "canonical": new_entry["canonical"], "count": len(entries)}


def action_remove(args: argparse.Namespace) -> Dict[str, Any]:
    target = glossary_file(Path(args.root))
    if not target.exists():
        raise GlossaryError(f"glossary not found: {target}")
    text = read_text(target)
    entries = parse_entries(text)
    kept = [e for e in entries if e["canonical"].strip().lower() != args.canonical.strip().lower()]
    removed = len(entries) - len(kept)
    if removed:
        target.write_text(replace_table(text, kept), encoding="utf-8")
    return {"removed": removed, "canonical": args.canonical, "count": len(kept)}


_ACTIONS = {
    "init": action_init,
    "list": action_list,
    "validate": action_validate,
    "detect-conflict": action_detect_conflict,
    "add": action_add,
    "remove": action_remove,
}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Spec Kit glossary engine")
    p.add_argument("--action", required=True, choices=sorted(_ACTIONS))
    p.add_argument("--root", default=".", help="workspace root (default: cwd)")
    p.add_argument("--from-template", default=None, help="template for init")
    p.add_argument("--force", action="store_true", help="init: overwrite existing")
    p.add_argument("--canonical", default=None)
    p.add_argument("--variants", default=None, help="comma-separated")
    p.add_argument("--meaning", default=None)
    p.add_argument("--origin", default="auto")
    p.add_argument("--status", default="proposed")
    p.add_argument("--confirmed-resolution", dest="confirmed_resolution", default=None,
                   help="explicit user resolution; required to write a conflicting/overriding change")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    action = _ACTIONS[args.action]
    if args.action in ("add", "remove", "detect-conflict") and not args.canonical:
        print("--canonical is required for this action", file=sys.stderr)
        return 2
    try:
        payload = action(args)
    except GlossaryError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"io error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
