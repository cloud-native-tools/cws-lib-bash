#!/usr/bin/env python3
"""Spec Kit shared probe engine — registry, map, injection, handlers, compile-embeds.

Owns the probe-family actions (requirement 056): ``probes`` / ``map`` /
``probe-inject`` migrated verbatim from feedback-utils.py (behavior-identical;
``--validate`` / ``--reconcile`` remain flags of ``probes``), the NEW
``handlers`` query/validate surface ([C2]: Handler six-field closed set +
HandlerBinding subscription table, identity triple, per-point order uniqueness)
and ``compile-embeds`` ([C3] compiler: renders each unit's single AUTO-GENERATED
``## Wrap-up`` section from the Handler/HandlerBinding chapters, --check drift
pre-check, closed refuse set). feedback-utils.py imports the
registry layer from here (its migrate-legacy action re-registers entries with
probe attribution).

stdlib-only; same deployment shape as feedback-utils.py (framework source
``.specify/scripts/python/`` + ``.specify/scripts/python/`` mirror). The registry file
is read from ``<workspace_root>/.specify/shared/definitions/probe-definitions.md``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

FEEDBACK_SUBDIR = Path(".specify") / "memory" / "feedback"
EXTERNAL_PROBES_DIRNAME = "probes"

_UNIT_ID_RE = re.compile(r"^(?:/speckit\.[a-z0-9._-]+|skill:[a-z0-9._-]+)$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


class FeedbackError(ValueError):
    """Raised for user-facing validation failures (exit code 2)."""


class CheckDriftError(Exception):
    """compile-embeds --check found drift (writes nothing).

    Exit code: 1 for regenerable drift (a stale render of an older registry
    state — recompile fixes it); 2 for structural classes (orphan/missing
    handler lines in an artifact whose banner fingerprint claims currency —
    hand corruption, review before recompiling)."""

    def __init__(self, payload: Dict[str, Any]):
        parts = payload.get("structural", []) + payload.get("drift", [])
        super().__init__("; ".join(parts) or "drift")
        self.payload = payload

    @property
    def exit_code(self) -> int:
        return 2 if self.payload.get("structural") else 1


def validate_unit_id(unit_id: str) -> bool:
    return bool(unit_id) and bool(_UNIT_ID_RE.match(unit_id.strip()))


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
# Frontmatter (minimal, dependency-free)
# --------------------------------------------------------------------------- #
def _scalar(value: str) -> Any:
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return value.strip().strip('"')


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


# --------------------------------------------------------------------------- #
# Store paths
# --------------------------------------------------------------------------- #
def feedback_dir(workspace_root: Path) -> Path:
    return Path(workspace_root).resolve() / FEEDBACK_SUBDIR


def ensure_feedback_dir(workspace_root: Path) -> Path:
    target = feedback_dir(workspace_root)
    target.mkdir(parents=True, exist_ok=True)
    return target


# --------------------------------------------------------------------------- #
# Probe registry (migrated verbatim from feedback-utils.py — 041 + 056 US1)
# --------------------------------------------------------------------------- #
PROBE_DEFS_REL = Path(".specify") / "shared" / "definitions" / "probe-definitions.md"
_PROBE_ID_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_CUSTOM_UNIT_RE = re.compile(r"^custom:[a-z0-9._/-]+$")
_PROBE_KINDS = ("internal", "external")
_CLASS_FIELDS = ("class_id", "kind", "collection", "target_slice",
                 "processing", "insertion_type")
_OBJECT_FIELDS = ("object_id", "class_id", "unit", "lifecycle_point")
_SCRIPT_UNIT_RE = re.compile(r"^.specify/scripts/(?:bash|python)/[a-z0-9][a-z0-9._-]*\.(?:py|sh)$")
_CATALOG_HEADING = "非实体 probe 目录"
_CATALOG_ENTRY_RE = re.compile(r"^- `([^`]+)` — .+$")


def _catalog_entries(text: str) -> List[Tuple[str, str]]:
    """Parse the non-entity probe catalog chapter as (path, raw-line) tuples.

    The catalog is pointer-only and MUST NOT participate in any registry
    counting — this helper is consumed solely for reachability validation.
    """
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == f"## {_CATALOG_HEADING}":
            start = i + 1
            break
    if start is None:
        return []
    out: List[Tuple[str, str]] = []
    for line in lines[start:]:
        if line.strip().startswith("## "):
            break
        m = _CATALOG_ENTRY_RE.match(line.strip())
        if m:
            out.append((m.group(1), line.strip()))
    return out


def probe_defs_path(workspace_root: Path) -> Path:
    return workspace_root / PROBE_DEFS_REL


def _table_rows(text: str, heading: str) -> List[Dict[str, str]]:
    """Parse the first pipe table under ``## <heading>``; keys = header cells."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip().lower() == f"## {heading}".lower():
            start = i + 1
            break
    if start is None:
        return []
    headers: Optional[List[str]] = None
    rows: List[Dict[str, str]] = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if not stripped.startswith("|"):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if headers is None:
            headers = cells
            continue
        if all(set(c) <= {"-", ":"} for c in cells):
            continue
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def _load_external_probes(workspace_root: Path,
                          errors: List[str]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    probes_dir = feedback_dir(workspace_root) / EXTERNAL_PROBES_DIRNAME
    if not probes_dir.is_dir():
        return out
    for path in sorted(probes_dir.glob("*.md")):
        meta, _body = parse_frontmatter(path.read_text(encoding="utf-8"))
        obj = {f: str(meta.get(f, "")).strip() for f in _OBJECT_FIELDS}
        if not obj["object_id"]:
            errors.append(f"external probe {path.name}: missing object_id")
            continue
        out.append(obj)
    return out


def load_probe_registry(workspace_root: Path) -> Dict[str, Any]:
    """Load + structurally validate the merged probe truth source.

    ``available`` is False when the framework definitions file is absent
    (un-upgraded workspace): callers fall back to legacy behavior instead of
    hard-failing, per red line 2 (the mechanism must never block work).
    """
    errors: List[str] = []
    classes: List[Dict[str, str]] = []
    objects: List[Dict[str, str]] = []
    defs = probe_defs_path(workspace_root)
    available = defs.is_file()
    external: List[Dict[str, str]] = []
    if available:
        text = defs.read_text(encoding="utf-8")
        classes = _table_rows(text, "Classes")
        objects = _table_rows(text, "Objects")
        seen_classes = set()
        for c in classes:
            cid = c.get("class_id", "")
            for field in _CLASS_FIELDS:
                if not c.get(field, "").strip():
                    errors.append(f"class '{cid or '?'}': field '{field}' must be non-empty")
            if not _PROBE_ID_RE.match(cid):
                errors.append(f"class '{cid}': id must match ^[a-z][a-z0-9-]*$")
            if cid in seen_classes:
                errors.append(f"class '{cid}': duplicate class_id")
            seen_classes.add(cid)
            if c.get("kind", "") not in _PROBE_KINDS:
                errors.append(f"class '{cid}': kind must be one of internal|external")
        class_ids = {c.get("class_id", "") for c in classes}
        class_slice = {c.get("class_id", ""): c.get("target_slice", "") for c in classes}
        seen_objects = set()
        for o in objects:
            oid = o.get("object_id", "")
            if not _PROBE_ID_RE.match(oid):
                errors.append(f"object '{oid}': id must match ^[a-z][a-z0-9-]*$")
            if oid in seen_objects:
                errors.append(f"object '{oid}': duplicate object_id")
            seen_objects.add(oid)
            if o.get("class_id", "") not in class_ids:
                errors.append(f"object '{oid}': unknown class '{o.get('class_id', '')}'")
            if class_slice.get(o.get("class_id", "")) == "scripts":
                if not _SCRIPT_UNIT_RE.match(o.get("unit", "")):
                    errors.append(
                        f"object '{oid}': unit '{o.get('unit', '')}' must be an engine "
                        "script path (.specify/scripts/python/*.py or .specify/scripts/bash/*.sh) for "
                        "scripts-slice classes")
            elif not validate_unit_id(o.get("unit", "")):
                errors.append(
                    f"object '{oid}': unit '{o.get('unit', '')}' must be /speckit.* or skill:*")
        for rel, _entry in _catalog_entries(text):
            if not (workspace_root / rel).is_file():
                errors.append(f"non-entity catalog entry unreachable: {rel}")
        external = _load_external_probes(workspace_root, errors)
        class_kind = {c.get("class_id", ""): c.get("kind", "") for c in classes}
        for e in external:
            oid = e.get("object_id", "")
            if not oid.startswith("ext-"):
                errors.append(f"external probe '{oid}': object_id MUST start with 'ext-'")
            if oid in seen_objects:
                errors.append(f"external probe '{oid}': duplicate object_id")
            seen_objects.add(oid)
            kind = class_kind.get(e.get("class_id", ""), "")
            if kind != "external":
                errors.append(
                    f"external probe '{oid}': class '{e.get('class_id', '')}' "
                    "must be kind=external")
            if not _CUSTOM_UNIT_RE.match(e.get("unit", "")):
                errors.append(
                    f"external probe '{oid}': unit '{e.get('unit', '')}' must match custom:<owner>/<name>")
    return {
        "available": available,
        "defs_path": defs.as_posix(),
        "classes": classes,
        "objects": objects,
        "external": external,
        "errors": errors,
    }


def _class_index(registry: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    return {c.get("class_id", ""): c for c in registry["classes"]}


def merged_probe_objects(registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Internal + external objects with class features merged in."""
    classes = _class_index(registry)

    def _merge(obj: Dict[str, str], is_external: bool) -> Dict[str, Any]:
        c = classes.get(obj.get("class_id", ""), {})
        return {
            "object_id": obj.get("object_id", ""),
            "class_id": obj.get("class_id", ""),
            "unit": obj.get("unit", ""),
            "lifecycle_point": obj.get("lifecycle_point", ""),
            "kind": c.get("kind", ""),
            "slice": c.get("target_slice", ""),
            "collection": c.get("collection", ""),
            "processing": c.get("processing", ""),
            "external": is_external,
        }

    out = [_merge(o, False) for o in registry["objects"]]
    out += [_merge(e, True) for e in registry["external"]]
    return out


def resolve_probe(
    registry: Dict[str, Any], unit_id: str, lifecycle_point: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    if lifecycle_point:
        for obj in merged_probe_objects(registry):
            if obj["unit"] == unit_id and obj["lifecycle_point"] == lifecycle_point:
                return obj
        return None
    for obj in merged_probe_objects(registry):
        if obj["unit"] == unit_id:
            return obj
    return None


def _embed_candidate_paths(workspace_root: Path) -> List[Tuple[str, Path]]:
    """(unit_id, path) for every command/skill compile unit, framework layout.

    Two-layer aware: a skill lives at skills/<name>/ (flat runtime shape) or at
    skills/{external,internal}/<name>/ (source-tree layering). A one-level glob saw
    ZERO embeds in a layered repo, so --reconcile reported "probe object without
    embed" for every skill row and could neither enforce nor detect the
    rows<->embed contract. Same path-resolution trap class as the engine
    self-location rule in AGENTS.md.
    """
    out: List[Tuple[str, Path]] = []
    cmd_dir = workspace_root / "templates" / "commands"
    if cmd_dir.is_dir():
        for path in sorted(cmd_dir.glob("*.md")):
            out.append((f"/speckit.{path.stem}", path))
    skills_dir = workspace_root / "skills"
    if skills_dir.is_dir():
        candidates = list(skills_dir.glob("*/SKILL.md"))
        for layer in ("external", "internal"):
            candidates.extend((skills_dir / layer).glob("*/SKILL.md"))
        for path in sorted(set(candidates)):
            out.append((f"skill:{path.parent.name}", path))
    return out


def scan_embed_units(workspace_root: Path) -> Dict[str, str]:
    """unit_id → file, from the wrap-up face (framework repo layout).

    Post-056 the face is the compiled `## Wrap-up`; the pre-056 `## Feedback`
    literal is dead on a migrated tree, so the reconcile must not key on it
    (keying on it reports every migrated unit as embed-less)."""
    return {
        unit_id: path.relative_to(workspace_root).as_posix()
        for unit_id, path in _embed_candidate_paths(workspace_root)
        if "## Wrap-up" in path.read_text(encoding="utf-8")
    }


def action_probes(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    registry = load_probe_registry(workspace_root)
    errors = list(registry["errors"])
    if args.validate or args.reconcile:
        if not registry["available"]:
            raise FeedbackError(f"probe registry not found: {probe_defs_path(workspace_root)}")
        if args.reconcile:
            embeds = scan_embed_units(workspace_root)
            declared = {o.get("unit", ""): o for o in registry["objects"]}
            wrapup_classes = {
                c.get("class_id", "")
                for c in registry["classes"]
                if c.get("insertion_type", "") == "wrap-up"
                and c.get("target_slice", "") != "scripts"
            }
            for unit in sorted(u for u in embeds if u not in declared):
                errors.append(f"embed without probe object: {unit} ({embeds[unit]})")
            for obj in registry["objects"]:
                if obj.get("class_id", "") not in wrapup_classes:
                    continue
                if obj.get("unit", "") not in embeds:
                    errors.append(
                        f"probe object without embed: {obj.get('object_id', '')} "
                        f"({obj.get('unit', '')})")
        if errors:
            raise FeedbackError("probe registry invalid:\n- " + "\n- ".join(errors))
        return {
            "ok": True,
            "reconciled": bool(args.reconcile),
            "classes": len(registry["classes"]),
            "objects": len(registry["objects"]),
            "external_objects": len(registry["external"]),
            "embeds": len(scan_embed_units(workspace_root)) if args.reconcile else None,
        }
    return {
        "available": registry["available"],
        "classes": registry["classes"],
        "objects": merged_probe_objects(registry),
    }


# --------------------------------------------------------------------------- #
# Probe map (migrated verbatim)
# --------------------------------------------------------------------------- #
PROBE_MAP_NAME = "probe-map.md"


def _map_slug(name: str) -> str:
    """Deterministic Mermaid node id: keep [a-zA-Z0-9_] only."""
    return _SLUG_RE.sub("_", name).strip("_")


def compose_probe_map(registry: Dict[str, Any]) -> str:
    """Render the derived probe map (deterministic: sorted, no timestamps).

    Rebuilding from an unchanged truth source MUST be byte-identical — that
    invariant is what makes drift detectable (SC-003).
    """
    classes = _class_index(registry)
    objects = merged_probe_objects(registry)
    lines: List[str] = [
        "# Feedback Probe Map(反馈插点结构图)",
        "",
        "> **派生物** — 由 `--action map` 自 probe 真源整体重建,禁止手工编辑;",
        "> 真源:`.specify/shared/definitions/probe-definitions.md` + 项目外部 probe。",
        "",
    ]
    for kind, kind_label in (("internal", "internal(内部 — 目标为 Spec Kit 框架)"),
                             ("external", "external(外部 — 目标为宿主项目自定义单元)")):
        group = sorted((o for o in objects if o.get("kind") == kind),
                       key=lambda o: (o.get("class_id", ""), o.get("object_id", "")))
        by_class: Dict[str, List[Dict[str, Any]]] = {}
        for o in group:
            by_class.setdefault(o.get("class_id", ""), []).append(o)
        # render EVERY class of this kind — zero-object classes stay visible
        kind_classes = sorted(
            (c for c in registry["classes"]
             if c.get("kind") == kind and c.get("class_id")),
            key=lambda c: c.get("class_id", ""))
        if not kind_classes:
            continue
        lines.append(f"## {kind_label}")
        lines.append("")
        for cid in [c.get("class_id", "") for c in kind_classes]:
            c = classes.get(cid, {})
            members = sorted(by_class.get(cid, []),
                             key=lambda x: x.get("object_id", ""))
            lines.append(f"### {cid}  [slice: {c.get('target_slice', '-')}]")
            lines.append("")
            lines.append(f"- **收集内容**: {c.get('collection', '-')}")
            lines.append(f"- **处理流程**: {c.get('processing', '-')}")
            lines.append(f"- **适用插入位置**: {c.get('insertion_type', '-')}")
            if members:
                lines.append(f"- **Objects** ({len(members)}):")
                for o in members:
                    lines.append(
                        f"  - `{o.get('object_id')}` — {o.get('unit')} @ "
                        f"{o.get('lifecycle_point')}")
            else:
                lines.append("- **Objects** (0 — 尚无实例;外部类经模式三注入)")
            lines.append("")
    lines.append("## 结构总览(Mermaid)")
    lines.append("")
    lines.append("```mermaid")
    lines.append("graph TD")
    lines.append("  root[Feedback Probe]")
    for kind in ("internal", "external"):
        group = [o for o in objects if o.get("kind") == kind]
        kind_classes = sorted(
            (c for c in registry["classes"]
             if c.get("kind") == kind and c.get("class_id")),
            key=lambda c: c.get("class_id", ""))
        if not group and not kind_classes:
            continue
        kind_node = _map_slug(f"kind {kind}")
        lines.append(f"  root --> {kind_node}[{kind}]")
        by_class: Dict[str, List[Dict[str, Any]]] = {}
        for o in group:
            by_class.setdefault(o.get("class_id", ""), []).append(o)
        for cid in [c.get("class_id", "") for c in kind_classes]:
            class_node = _map_slug(f"class {cid}")
            lines.append(f"  {kind_node} --> {class_node}[{cid}]")
            for o in sorted(by_class.get(cid, []), key=lambda x: x.get("object_id", "")):
                obj_node = _map_slug(f"obj {o.get('object_id', '')}")
                lines.append(f"  {class_node} --> {obj_node}[{o.get('object_id')}]")
    lines.append("```")
    lines.append("")
    lines.append("## 明细表")
    lines.append("")
    lines.append("| Object | Class | Kind | 插入位置(unit @ lifecycle) | 收集内容 | 处理流程 |")
    lines.append("|--------|-------|------|------------------------------|----------|----------|")
    for o in sorted(objects, key=lambda x: (x.get("kind", ""), x.get("class_id", ""),
                                            x.get("object_id", ""))):
        c = classes.get(o.get("class_id", ""), {})
        lines.append(
            f"| `{o.get('object_id')}` | {o.get('class_id')} | {o.get('kind')} "
            f"| {o.get('unit')} @ {o.get('lifecycle_point')} "
            f"| {c.get('collection', '-')} | {c.get('processing', '-')} |")
    lines.append("")
    return "\n".join(lines)


def action_map(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    registry = load_probe_registry(workspace_root)
    if not registry["available"]:
        raise FeedbackError(f"probe registry not found: {probe_defs_path(workspace_root)}")
    if registry["errors"]:
        raise FeedbackError(
            "probe registry invalid (run --action probes --validate):\n- "
            + "\n- ".join(registry["errors"][:10]))
    target_dir = ensure_feedback_dir(workspace_root)
    (target_dir / PROBE_MAP_NAME).write_text(
        compose_probe_map(registry), encoding="utf-8")
    rel = (FEEDBACK_SUBDIR / PROBE_MAP_NAME).as_posix()
    return {
        "map": rel,
        "classes": len(registry["classes"]),
        "objects": len(registry["objects"]),
        "external_objects": len(registry["external"]),
    }


# --------------------------------------------------------------------------- #
# Probe injection (migrated verbatim)
# --------------------------------------------------------------------------- #
def action_probe_inject(args: argparse.Namespace) -> Dict[str, Any]:
    """/speckit.feedback § Probe Injection (req 041, engine-cli C-6): inject an
    external probe for a client-project custom unit into the project-side
    registry."""
    workspace_root = resolve_workspace_root(args.workspace_root)
    unit = ((getattr(args, "unit", None) or "")).strip()
    if not _CUSTOM_UNIT_RE.match(unit):
        raise FeedbackError("--unit must match custom:<owner>/<name>.")
    registry = load_probe_registry(workspace_root)
    if not registry["available"]:
        raise FeedbackError(f"probe registry not found: {probe_defs_path(workspace_root)}")
    external_classes = [c for c in registry["classes"]
                        if c.get("kind") == "external" and c.get("class_id")]
    if not external_classes:
        raise FeedbackError("registry declares no kind=external class to instantiate.")
    class_id = external_classes[0]["class_id"]
    lifecycle = (getattr(args, "lifecycle_point", None) or "wrap-up").strip()

    slug = _SLUG_RE.sub("-", unit.removeprefix("custom:")).strip("-")
    object_id = f"ext-{slug}"
    probes_dir = feedback_dir(workspace_root) / EXTERNAL_PROBES_DIRNAME
    probes_dir.mkdir(parents=True, exist_ok=True)
    target = probes_dir / f"{object_id}.md"
    if target.exists():
        raise FeedbackError(
            f"probe object already exists: {object_id} ({target.name})")

    notes = ""
    notes_file = getattr(args, "notes_file", None)
    if notes_file:
        notes = Path(notes_file).read_text(encoding="utf-8").strip()
    elif getattr(args, "notes", None):
        notes = str(args.notes).strip()

    meta = {
        "object_id": object_id,
        "class_id": class_id,
        "unit": unit,
        "lifecycle_point": lifecycle,
    }
    fm = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}"
                   for k, v in meta.items())
    target.write_text(
        f"---\n{fm}\n---\n\n{notes or 'External probe for a host-project custom unit.'}\n",
        encoding="utf-8",
    )
    # validate the registry still passes with the new object
    recheck = load_probe_registry(workspace_root)
    if recheck["errors"]:
        target.unlink(missing_ok=True)
        raise FeedbackError(
            "injection would invalidate the registry:\n- "
            + "\n- ".join(recheck["errors"]))
    return {
        "object_id": object_id,
        "class_id": class_id,
        "path": (FEEDBACK_SUBDIR / EXTERNAL_PROBES_DIRNAME
                 / f"{object_id}.md").as_posix(),
        "note": "external probe feedback stays host-project-local; "
                "it is excluded from upstream packages.",
    }


# --------------------------------------------------------------------------- #
# Handler / HandlerBinding (NEW — requirement 056 US2, [C2])
# --------------------------------------------------------------------------- #
HANDLER_KINDS = ("engine", "agent", "gate")
HANDLER_MODES = ("non-blocking", "blocking")
LIFECYCLE_POINTS = ("wrap-up", "situation", "phase-boundary", "confirm-gate")
BINDING_SCOPES = ("complex-commands", "skills", "all")
_SELECTOR_RE = re.compile(r"^@point:([a-z-]+)$")
_HEADING_RE = re.compile(r"^## (.+)$", re.MULTILINE)
_ORDER_RE = re.compile(r"-?\d+")

# kind=engine action closure = the REAL argparse choices / action constants of
# the engine scripts sitting next to this file (source copy and .specify mirror
# each resolve their own siblings — never a hand-copied list).
_ENGINE_SIBLINGS = ("feedback-utils.py", "run-determination.py", "probe-utils.py",
                    "trigger-utils.py", "exec-quant.py")


def _engine_action_union() -> set:
    here = Path(__file__).resolve().parent
    actions: set = set()
    for name in _ENGINE_SIBLINGS:
        path = here / name
        if not path.is_file():
            continue
        src = path.read_text(encoding="utf-8")
        if name in ("run-determination.py", "trigger-utils.py"):
            # Both engines declare their action closure as an ACTIONS tuple.
            m = re.search(r"^ACTIONS = \(([^)]*)\)", src, re.MULTILINE)
            if m:
                actions |= set(re.findall(r'"([^"]+)"', m.group(1)))
            continue
        idx = src.find('"--action"')
        if idx < 0:
            continue
        m = re.search(r"choices=\[(.*?)\]", src[idx:], re.DOTALL)
        if m:
            actions |= set(re.findall(r'"([^"]+)"', m.group(1)))
    return actions


def _owner_headings(path: Path) -> set:
    return set(_HEADING_RE.findall(path.read_text(encoding="utf-8")))


def validate_handlers(workspace_root: Path) -> List[str]:
    """[C2] closed validation set — every violation named, caller decides exit."""
    errors: List[str] = []
    defs = probe_defs_path(workspace_root)
    if not defs.is_file():
        return [f"probe registry not found: {defs}"]
    text = defs.read_text(encoding="utf-8")
    handlers = _table_rows(text, "Handler")
    bindings = _table_rows(text, "HandlerBinding")
    if not handlers and not bindings:
        return ["registry declares no Handler/HandlerBinding chapters"]
    engine_actions = _engine_action_union()
    seen_ids: set = set()
    handler_order: Dict[str, int] = {}
    for h in handlers:
        hid = h.get("handler_id", "")
        if not hid.startswith("h-"):
            errors.append(f"handler '{hid}': id must carry the h- prefix")
        if hid in seen_ids:
            errors.append(f"handler '{hid}': duplicate handler_id")
        seen_ids.add(hid)
        if h.get("kind", "") not in HANDLER_KINDS:
            errors.append(
                f"handler '{hid}': kind '{h.get('kind', '')}' must be one of "
                + "|".join(HANDLER_KINDS))
        if h.get("mode", "") not in HANDLER_MODES:
            errors.append(
                f"handler '{hid}': mode '{h.get('mode', '')}' must be one of "
                + "|".join(HANDLER_MODES))
        if not _ORDER_RE.fullmatch(h.get("order", "")):
            errors.append(f"handler '{hid}': order must be an integer")
        elif hid not in handler_order:
            handler_order[hid] = int(h["order"])
        owner = h.get("behavior_owner", "")
        rel, _, anchor = owner.partition("#")
        path = workspace_root / rel
        headings: set = set()
        if not path.is_file():
            errors.append(f"handler '{hid}': behavior_owner unreachable: {rel}")
        else:
            headings = _owner_headings(path)
            if anchor and anchor not in headings:
                errors.append(
                    f"handler '{hid}': owner anchor '{anchor}' is not a `##` "
                    f"heading of {rel}")
        kind = h.get("kind", "")
        action = h.get("action", "").strip("`")
        if kind == "engine":
            if engine_actions and action not in engine_actions:
                errors.append(
                    f"handler '{hid}': kind=engine action '{action}' is not a "
                    "real engine action")
        elif kind == "agent":
            if headings and action not in headings:
                errors.append(
                    f"handler '{hid}': kind=agent action '{action}' is not a "
                    f"`##` heading of {rel}")
        elif kind == "gate" and path.is_file():
            if action not in path.read_text(encoding="utf-8"):
                errors.append(
                    f"handler '{hid}': kind=gate action '{action}' not found "
                    f"in {rel}")
    object_ids = {o.get("object_id", "") for o in _table_rows(text, "Objects")}
    seen_triples: set = set()
    per_point: Dict[str, Dict[int, set]] = {}
    for b in bindings:
        hid = b.get("handler_id", "")
        selector = b.get("selector", "")
        scope = b.get("scope", "")
        triple = (hid, selector, scope)
        if triple in seen_triples:
            errors.append(f"duplicate binding identity triple: {triple}")
        seen_triples.add(triple)
        if hid not in seen_ids:
            errors.append(f"binding {triple}: references unknown handler '{hid}'")
            continue
        m = _SELECTOR_RE.match(selector)
        if not m:
            errors.append(f"binding {triple}: malformed selector {selector!r}")
            continue
        point = m.group(1)
        if point not in LIFECYCLE_POINTS:
            errors.append(
                f"binding {triple}: selector point '{point}' outside closed set "
                + "|".join(LIFECYCLE_POINTS))
        if scope not in BINDING_SCOPES and scope not in object_ids:
            errors.append(
                f"binding {triple}: scope '{scope}' is neither a scope keyword "
                "nor a registered object_id")
        if hid in handler_order and point in LIFECYCLE_POINTS:
            # distinct-handler set: the same handler bound via several
            # selectors/scopes merges into one entry (data-model 合并规则);
            # order conflicts fire only across DIFFERENT handlers.
            per_point.setdefault(point, {}).setdefault(
                handler_order[hid], set()).add(hid)
    for point in sorted(per_point):
        for order in sorted(per_point[point]):
            hids = per_point[point][order]
            if len(hids) > 1:
                errors.append(
                    f"order conflict at @{point}: {' and '.join(sorted(hids))} "
                    f"both order {order}")
    return errors


def action_handlers(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    defs = probe_defs_path(workspace_root)
    if not defs.is_file():
        raise FeedbackError(f"probe registry not found: {defs}")
    text = defs.read_text(encoding="utf-8")
    handlers = _table_rows(text, "Handler")
    bindings = _table_rows(text, "HandlerBinding")
    if args.validate:
        errors = validate_handlers(workspace_root)
        if errors:
            raise FeedbackError("handler binding invalid:\n- " + "\n- ".join(errors))
        return {"ok": True, "handlers": len(handlers), "bindings": len(bindings)}
    point = getattr(args, "point", None)
    scope = getattr(args, "scope", None)
    kind = getattr(args, "kind", None)
    mode = getattr(args, "mode", None)
    if args.bindings:
        rows = bindings
        if point:
            rows = [b for b in rows if b.get("selector", "") == f"@point:{point}"]
        if scope:
            rows = [b for b in rows if b.get("scope", "") == scope]
        return {"bindings": rows}
    if point or scope:
        matched = set()
        for b in bindings:
            if point and b.get("selector", "") != f"@point:{point}":
                continue
            if scope and b.get("scope", "") != scope:
                continue
            matched.add(b.get("handler_id", ""))
        handlers = [h for h in handlers if h.get("handler_id", "") in matched]
    if kind:
        handlers = [h for h in handlers if h.get("kind", "") == kind]
    if mode:
        handlers = [h for h in handlers if h.get("mode", "") == mode]
    return {"handlers": handlers}


# --------------------------------------------------------------------------- #
# compile-embeds (NEW — requirement 056 US3, [C3])
# --------------------------------------------------------------------------- #
# MVP resolves @point:wrap-up bindings only; other lifecycle points extend the
# renderer in phase 6 (T031+). Refuse set (exit 2, closed): validate_handlers
# errors (missing handler ref / illegal engine action / order conflict /
# unreachable behavior_owner / duplicate triple) + orphan handler (registered,
# never bound) + BLOCKING_PATTERNS hit on generated wording. --check drift is
# exit 1. Units outside the scan universe are never touched (simple commands /
# external units keep their no-section form, FR-013).
_WRAP_UP_HEADING = "## Wrap-up"
_H2_RE = re.compile(r"^## (.+)$")
_SECTION_END_RE = re.compile(r"^#{1,2} ")
_UNIT_SECTION_HEADINGS = ("Feedback", "Documentation", "Wrap-up")
_SKILL_GATE_LINE = (
    "**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, "
    "this skill is running in standalone mode (a non–Spec Kit deployment, "
    "e.g. a global agent skills directory) — skip this entire Wrap-up step: "
    "no engine call, no feedback entry.")


def _blocking_re() -> "re.Pattern[str]":
    """BLOCKING_PATTERNS owner = scan-confirmation-gates.py (imported by path —
    hyphenated sibling; same sys.modules dedupe as the feedback-utils import)."""
    if "scan_confirmation_gates" in sys.modules:
        mod = sys.modules["scan_confirmation_gates"]
    else:
        import importlib.util as _ilu
        path = Path(__file__).resolve().parent / "scan-confirmation-gates.py"
        spec = _ilu.spec_from_file_location("scan_confirmation_gates", str(path))
        if spec is None or spec.loader is None:
            raise FeedbackError(f"cannot load wording-gate owner: {path}")
        mod = _ilu.module_from_spec(spec)
        sys.modules["scan_confirmation_gates"] = mod
        spec.loader.exec_module(mod)
    return mod.BLOCKING_RE


def scan_compile_units(workspace_root: Path) -> Dict[str, Path]:
    """Units carrying a wrap-up obligation: a literal ``## Feedback`` embed, a
    manual ``## Documentation`` (docs-sync) embed, or an H2 ``## Wrap-up``
    (compiled output — keeps re-scans stable post-migration)."""
    found: Dict[str, Path] = {}
    for unit_id, path in _embed_candidate_paths(workspace_root):
        text = path.read_text(encoding="utf-8")
        hit = "## Feedback" in text
        if not hit:
            for line in text.splitlines():
                m = _H2_RE.match(line)
                if m and m.group(1).strip() in _UNIT_SECTION_HEADINGS:
                    hit = True
                    break
        if hit:
            found[unit_id] = path
    return found


def _runtime_path(owner: str) -> str:
    """Registry owner paths are framework-source-face (.specify/scripts/, .specify/shared/);
    compiled sections must reference the runtime face that resolves in every
    consumer — the framework repo AND downstream projects (only .specify/
    exists there): .specify/scripts/python/x.py → .specify/scripts/python/x.py."""
    if owner.startswith((".specify/scripts/", ".specify/shared/", ".specify/templates/")):
        return ".specify/" + owner
    return owner


def _handler_label(handler_id: str) -> str:
    if not handler_id.startswith("h-"):
        return handler_id
    return " ".join(w.capitalize() for w in handler_id[2:].split("-"))


# --- compiled-face argument rendering (063 C-20 / C-21 / C-22) ---------------
# The renderer holds NO argument table of its own (C-21): every flag it renders
# comes from the owner engine's args-manifest, fetched at compile time by
# running the engine itself (C-22). The convention (placeholder syntax,
# substitution rule, rendered-set membership) is declared ONCE in the registry
# § Handler note — never per command hand-written (C-20).
_IDENTITY_FLAGS = ("--unit-id", "--unit-type")
_PLACEHOLDER_RE = re.compile(r"--[a-z-]+ <[A-Z_]+>")
_CONVENTION_RE = re.compile(r"Compiled-face convention line[:：]\s*(.+)")


def _placeholder(flag: str) -> str:
    """Placeholder syntax per the registry § Handler note: flag name sans `--`,
    hyphens → underscores, uppercased (`--run-id` ⇒ `<RUN_ID>`)."""
    return "<" + flag.lstrip("-").replace("-", "_").upper() + ">"


def _handler_note_convention(defs_text: str) -> Optional[str]:
    m = _CONVENTION_RE.search(defs_text)
    return m.group(1).strip() if m else None


def _engine_script(workspace_root: Path, owner: str) -> Optional[Path]:
    """The owner engine as an executable script: framework-source face first,
    runtime face (.specify/) second — downstream projects only have the latter."""
    for candidate in (workspace_root / owner,
                      workspace_root / ".specify" / owner):
        if candidate.is_file():
            return candidate
    return None


def _engine_manifests(workspace_root: Path, owner: str, handler_id: str,
                      cache: Dict[str, Any]) -> Dict[str, Any]:
    """C-22 (063): the owner engine's argument manifest, obtained FROM the
    engine at compile time (`--action args-manifest`). Any divergence — engine
    missing, action absent, unparsable output — is a LOUD compile refusal;
    never a silent unit-id-only fallback (registry/engine divergence is a
    fast-fail surface)."""
    key = f"{workspace_root.resolve()}|{owner}"
    if key in cache:
        return cache[key]
    script = _engine_script(workspace_root, owner)
    if script is None:
        raise FeedbackError(
            f"handler '{handler_id}': behavior_owner engine not found for the "
            f"manifest fetch: {owner} (looked under the workspace root and "
            f".specify/)")
    proc = subprocess.run(
        [sys.executable, str(script), "--action", "args-manifest"],
        capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise FeedbackError(
            f"handler '{handler_id}': engine {owner} --action args-manifest "
            f"failed (rc={proc.returncode}): {proc.stderr.strip()[:300]}")
    try:
        manifest = json.loads(proc.stdout)
    except ValueError as exc:
        raise FeedbackError(
            f"handler '{handler_id}': engine {owner} args-manifest output is "
            f"not JSON: {exc}")
    if not isinstance(manifest, dict) or not manifest:
        raise FeedbackError(
            f"handler '{handler_id}': engine {owner} emits an empty "
            "args-manifest")
    cache[key] = manifest
    return manifest


def _fingerprint(handlers: List[Dict[str, str]],
                 bindings: List[Dict[str, str]]) -> str:
    blob = json.dumps([handlers, bindings], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def _render_call_line(handler: Dict[str, str], unit_id: str, unit_type: str,
                      index: int, workspace_root: Path,
                      manifest_cache: Dict[str, Any]) -> str:
    kind = handler.get("kind", "")
    action = handler.get("action", "").strip("`")
    label = _handler_label(handler.get("handler_id", ""))
    owner = _runtime_path(handler.get("behavior_owner", ""))
    if kind == "engine":
        cli = (f"python3 {owner} --action {action} "
               f"--unit-id \"{unit_id}\" --unit-type {unit_type}")
        # C-20/C-21: the rendered argument tail is exactly the engine's own
        # manifest — required set inline, declared source args as the
        # "when available" clause; identity pair already carries real values.
        manifest = _engine_manifests(workspace_root,
                                     handler.get("behavior_owner", ""),
                                     handler.get("handler_id", ""),
                                     manifest_cache)
        spec = manifest.get(action)
        if not isinstance(spec, dict):
            raise FeedbackError(
                f"handler '{handler.get('handler_id', '')}': engine "
                f"{handler.get('behavior_owner', '')} has no args-manifest "
                f"entry for action '{action}' — registry/engine divergence")
        req = [f for f in spec.get("required", []) if f not in _IDENTITY_FLAGS]
        src = [f for f in spec.get("source", []) if f not in _IDENTITY_FLAGS]
        if req:
            cli += " " + " ".join(f"{f} {_placeholder(f)}" for f in req)
        if src:
            cli += ("`；source args when available: `"
                    + " ".join(f"{f} {_placeholder(f)}" for f in src))
        return f"{index}. {label} — `{cli}`"
    if kind in ("agent", "gate"):
        return f"{index}. {label} — `{owner}` § \"{action}\""
    return f"{index}. {label} — {action}"


def render_wrap_up_section(handlers: List[Dict[str, str]], unit_id: str,
                           is_skill: bool, fingerprint: str,
                           workspace_root: Path,
                           manifest_cache: Dict[str, Any],
                           convention: Optional[str]) -> str:
    """One AUTO-GENERATED `## Wrap-up` section: banner, skill runtime-mode
    gate (FR-013), then one kind-derived call line per effective handler in
    ascending order. C-20 (063): when any engine line carries a placeholder,
    exactly ONE convention line (text declared in the registry § Handler note)
    renders right after that line. Deterministic — same registry + unit ⇒
    same bytes."""
    lines = [
        _WRAP_UP_HEADING,
        "",
        f"<!-- AUTO-GENERATED by probe-utils.py --action compile-embeds — "
        f"truth source: .specify/shared/definitions/probe-definitions.md "
        f"(## Handler / ## HandlerBinding) — fingerprint: {fingerprint} — "
        f"do not edit; edit the registry, then recompile -->",
        "",
    ]
    if is_skill:
        lines += [_SKILL_GATE_LINE, ""]
    unit_type = "skill" if is_skill else "command"
    ordered = sorted(handlers, key=lambda h: int(h.get("order", "") or 0))
    convention_emitted = False
    for i, handler in enumerate(ordered, 1):
        line = _render_call_line(handler, unit_id, unit_type, i,
                                 workspace_root, manifest_cache)
        lines.append(line)
        if (convention and not convention_emitted
                and _PLACEHOLDER_RE.search(line)):
            lines.append(f"   {convention}")
            convention_emitted = True
    lines.append("")
    return "\n".join(lines)


_CALL_ENGINE_RE = re.compile(r"^\d+\. .+? — `python3 (\S+) --action (\S+)")
_CALL_ANCHOR_RE = re.compile(r'^\d+\. .+? — `([^`]+)` § "(.+)"$')
_FINGERPRINT_RE = re.compile(r"fingerprint: ([0-9a-f]{12})")


def _banner_fingerprint(text: str) -> Optional[str]:
    m = _FINGERPRINT_RE.search(text)
    return m.group(1) if m else None


def _parse_call_lines(section_text: str) -> List[Tuple[str, str]]:
    """(runtime-owner, action) pairs from a compiled section's call lines."""
    pairs: List[Tuple[str, str]] = []
    for line in section_text.splitlines():
        m = _CALL_ENGINE_RE.match(line)
        if m:
            pairs.append((m.group(1), m.group(2)))
            continue
        m = _CALL_ANCHOR_RE.match(line)
        if m:
            pairs.append((m.group(1), m.group(2)))
    return pairs


def _compiled_section_body(text: str) -> str:
    """The current file's `## Wrap-up` section body, or '' when absent."""
    lines = text.splitlines()
    for start, end in _section_spans(lines):
        if lines[start].strip() == _WRAP_UP_HEADING:
            return "\n".join(lines[start:end])
    return ""


def _section_spans(lines: List[str]) -> List[Tuple[int, int]]:
    """[start, end) line spans of H2 Feedback / Documentation / Wrap-up
    sections; a span ends at the next H1/H2 heading (H3 subsections stay
    inside) or EOF."""
    spans: List[Tuple[int, int]] = []
    i, n = 0, len(lines)
    while i < n:
        m = _H2_RE.match(lines[i])
        if m and m.group(1).strip() in _UNIT_SECTION_HEADINGS:
            j = i + 1
            while j < n and not _SECTION_END_RE.match(lines[j]):
                j += 1
            spans.append((i, j))
            i = j
        else:
            i += 1
    return spans


def _replace_sections(text: str, section: Optional[str]) -> str:
    """Drop every manual Feedback/Documentation and compiled Wrap-up H2 span,
    then emit the compiled section at the first dropped span's position
    (写入位置 = 既有手工 ## Feedback 段落位) or append at EOF. Zero-effective
    units (section=None) end up with no section at all (Q5)."""
    lines = text.splitlines()
    spans = _section_spans(lines)
    if not spans:
        if not section:
            return text
        if lines and lines[-1].strip():
            lines.append("")
        # split("\n"), not splitlines(): the section ends with a blank-line
        # separator that splitlines() silently drops (the next heading would
        # glue onto the last item).
        lines.extend(section.split("\n"))
    else:
        drop: set = set()
        for start, end in spans:
            drop.update(range(start, end))
        kept = [line for idx, line in enumerate(lines) if idx not in drop]
        if section:
            kept[spans[0][0]:spans[0][0]] = section.split("\n")
        lines = kept
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def _effective_handlers(unit_id: str, is_skill: bool, unit_object_ids: set,
                        handlers: List[Dict[str, str]],
                        bindings: List[Dict[str, str]],
                        point: str) -> List[Dict[str, str]]:
    """Selector hit → scope match (all / complex-commands / skills / per-unit
    object_id rows, additive) → handler resolve, deduped by handler_id (multi-
    selector hits merge into one entry). Order sorting happens at render."""
    by_id = {h.get("handler_id", ""): h for h in handlers}
    hit_ids: List[str] = []
    for b in bindings:
        if b.get("selector", "") != f"@point:{point}":
            continue
        scope = b.get("scope", "")
        hit = (scope == "all"
               or (scope == "complex-commands" and not is_skill)
               or (scope == "skills" and is_skill)
               or scope in unit_object_ids)
        hid = b.get("handler_id", "")
        if hit and hid in by_id and hid not in hit_ids:
            hit_ids.append(hid)
    return [by_id[h] for h in hit_ids]


def action_compile_embeds(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    defs = probe_defs_path(workspace_root)
    if not defs.is_file():
        raise FeedbackError(f"probe registry not found: {defs}")
    registry = load_probe_registry(workspace_root)
    if registry["errors"]:
        raise FeedbackError(
            "probe registry invalid:\n- " + "\n- ".join(registry["errors"]))
    text = defs.read_text(encoding="utf-8")
    handlers = _table_rows(text, "Handler")
    bindings = _table_rows(text, "HandlerBinding")
    errors = validate_handlers(workspace_root)
    if not handlers:
        errors.append("registry declares no Handler chapter — nothing to compile")
    bound_ids = {b.get("handler_id", "") for b in bindings}
    for h in handlers:
        if h.get("handler_id", "") not in bound_ids:
            errors.append(
                f"orphan handler: '{h.get('handler_id', '')}' has no "
                "HandlerBinding row")
    if errors:
        raise FeedbackError("compile-embeds refused:\n- " + "\n- ".join(errors))
    unit_objects: Dict[str, set] = {}
    for obj in registry["objects"]:
        unit_objects.setdefault(obj.get("unit", ""), set()).add(
            obj.get("object_id", ""))
    fingerprint = _fingerprint(
        [h for h in handlers
         if h.get("handler_id", "") in {b.get("handler_id", "")
                                        for b in bindings
                                        if b.get("selector", "") == "@point:wrap-up"}],
        [b for b in bindings if b.get("selector", "") == "@point:wrap-up"])
    # The banner fingerprint identifies the registry state the WRAP-UP faces
    # render from: only the wrap-up projection (its bindings + their handlers).
    # Phase-2 points (situation / phase-boundary / confirm-gate) declare
    # runtime subscriptions without touching compiled output — folding them in
    # would stale-date every banner on any phase-2 registry edit.
    convention = _handler_note_convention(text)
    manifest_cache: Dict[str, Any] = {}
    plans: List[Tuple[str, Path, Optional[str], set]] = []
    for unit_id, path in sorted(scan_compile_units(workspace_root).items()):
        is_skill = unit_id.startswith("skill:")
        effective = _effective_handlers(
            unit_id, is_skill, unit_objects.get(unit_id, set()),
            handlers, bindings, "wrap-up")
        effective_ids = {h.get("handler_id", "") for h in effective}
        section = (render_wrap_up_section(effective, unit_id, is_skill,
                                          fingerprint, workspace_root,
                                          manifest_cache, convention)
                   if effective else None)
        plans.append((unit_id, path, section, effective_ids))
    # C-20 (063): a placeholder-carrying face without a registry-declared
    # convention is registry divergence — refuse loudly, never render a
    # per-command hand-written convention.
    for unit_id, _path, section, _ids in plans:
        if section and _PLACEHOLDER_RE.search(section) and not convention:
            raise FeedbackError(
                f"compile-embeds refused: {unit_id} renders engine-line "
                "placeholders but the registry § Handler note declares no "
                "'Compiled-face convention line' (063 C-20 — the convention "
                "MUST be declared in the registry, not hand-written)")
    wording_hits = []
    blocking = _blocking_re()
    for unit_id, _path, section, _ids in plans:
        if section:
            m = blocking.search(section)
            if m:
                wording_hits.append(
                    f"{unit_id}: generated wording hits BLOCKING_PATTERNS "
                    f"({m.group(0)!r})")
    if wording_hits:
        raise FeedbackError(
            "compile-embeds refused (wording gate):\n- " + "\n- ".join(wording_hits))
    if args.check:
        structural: List[str] = []
        drift: List[str] = []
        resolvable = {
            (_runtime_path(h.get("behavior_owner", "")),
             h.get("action", "").strip("`")): h.get("handler_id", "")
            for h in handlers
        }
        for unit_id, path, section, effective_ids in plans:
            current = path.read_text(encoding="utf-8")
            if _replace_sections(current, section) == current:
                continue
            if _banner_fingerprint(current) != fingerprint:
                # A render of an older registry state: regenerable, recompile fixes it.
                drift.append(unit_id)
                continue
            # The banner claims currency — any line-level difference is hand corruption.
            present = _parse_call_lines(_compiled_section_body(current))
            expected_pairs = {
                (_runtime_path(h.get("behavior_owner", "")),
                 h.get("action", "").strip("`"))
                for h in handlers if h.get("handler_id", "") in effective_ids}
            problems: List[str] = []
            for owner, action in present:
                hid = resolvable.get((owner, action))
                if hid is None:
                    problems.append(
                        f"orphan handler line: {owner} --action {action} "
                        "(no such registered handler)")
                elif hid not in effective_ids:
                    problems.append(
                        f"orphan handler line: {owner} --action {action} "
                        "(registered but not subscribed to this unit)")
            for owner, action in sorted(expected_pairs - set(present)):
                problems.append(
                    f"missing handler line: {owner} --action {action} "
                    "(subscribed but absent from the artifact)")
            if problems:
                structural.extend(f"{unit_id}: {p}" for p in problems)
            else:
                drift.append(unit_id)
        if structural or drift:
            raise CheckDriftError({"ok": False, "check": True, "units": len(plans),
                                   "structural": structural, "drift": drift})
        return {"ok": True, "check": True, "units": len(plans),
                "structural": [], "drift": []}
    written: List[str] = []
    unchanged = 0
    for unit_id, path, section, _ids in plans:
        current = path.read_text(encoding="utf-8")
        expected = _replace_sections(current, section)
        if expected == current:
            unchanged += 1
            continue
        tmp = path.with_name(path.name + ".compile-tmp")
        tmp.write_text(expected, encoding="utf-8")
        os.replace(tmp, path)
        written.append(unit_id)
    return {
        "ok": True,
        "units": len(plans),
        "written": written,
        "unchanged": unchanged,
        "zero_section": [u for u, _p, s, _i in plans if s is None],
    }


# --------------------------------------------------------------------------- #
# Output rendering
# --------------------------------------------------------------------------- #
def render_text(action: str, payload: Dict[str, Any]) -> str:
    if action == "probes":
        if payload.get("ok"):
            scope = "reconciled zero-gap" if payload.get("reconciled") else "valid"
            return (f"Probe registry {scope}: {payload.get('classes')} classes, "
                    f"{payload.get('objects')} internal + "
                    f"{payload.get('external_objects')} external objects"
                    + (f", {payload.get('embeds')} embeds" if payload.get("reconciled") else ""))
        if not payload.get("available"):
            return ("No probe registry found at "
                    ".specify/shared/definitions/probe-definitions.md — "
                    "run /speckit.instructions to install it.")
        lines = ["# Probe overview", ""]
        objects = payload.get("objects", [])
        classes = payload.get("classes", [])
        for kind in ("internal", "external"):
            kind_classes = sorted(
                (c for c in classes
                 if c.get("kind") == kind and c.get("class_id")),
                key=lambda c: c.get("class_id", ""))
            if not kind_classes:
                continue
            lines.append(f"## {kind}")
            lines.append("")
            by_class: Dict[str, List[Dict[str, Any]]] = {}
            for o in objects:
                if o.get("kind") == kind:
                    by_class.setdefault(o.get("class_id", ""), []).append(o)
            for c in kind_classes:
                cid = c.get("class_id", "")
                members = sorted(by_class.get(cid, []),
                                 key=lambda x: x.get("object_id", ""))
                lines.append(
                    f"- {cid}  [slice: {c.get('target_slice', '-')}] — "
                    f"{c.get('collection', '-')} → {c.get('processing', '-')}")
                if members:
                    for o in members:
                        lines.append(
                            f"  - {o.get('object_id')}   ({o.get('unit')} @ "
                            f"{o.get('lifecycle_point')})")
                else:
                    lines.append("  - (0 objects — 尚无实例;外部类经 /speckit.feedback § Probe Injection 注入)")
            lines.append("")
        return "\n".join(lines).rstrip()
    if action == "handlers":
        if payload.get("ok"):
            return (f"Handler binding valid: {payload.get('handlers')} handlers, "
                    f"{payload.get('bindings')} bindings")
        handlers = payload.get("handlers", [])
        if not handlers:
            return "No matching handlers."
        lines = ["# Handler overview", ""]
        for h in handlers:
            lines.append(
                f"- {h.get('handler_id', '')}  [{h.get('kind', '')}/"
                f"{h.get('mode', '')}] order {h.get('order', '')} — "
                f"action `{h.get('action', '')}`")
            lines.append(f"  owner: {h.get('behavior_owner', '')}")
        return "\n".join(lines)
    if action == "handlers-bindings":
        bindings = payload.get("bindings", [])
        if not bindings:
            return "No matching bindings."
        lines = ["# HandlerBinding overview", ""]
        for b in bindings:
            lines.append(
                f"- {b.get('handler_id', '')} {b.get('selector', '')} → "
                f"{b.get('scope', '')}")
        return "\n".join(lines)
    if action == "compile-embeds":
        if payload.get("check"):
            return (f"compile-embeds --check: {payload.get('units')} units, "
                    "zero drift")
        written = payload.get("written", [])
        zero = payload.get("zero_section", [])
        out = (f"compiled {payload.get('units')} units: "
               f"{len(written)} written, {payload.get('unchanged')} unchanged")
        if zero:
            out += f"; zero-section (no handler, no section emitted): {', '.join(zero)}"
        return out
    return json.dumps(payload, ensure_ascii=False, indent=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Spec Kit shared probe engine "
                    "(probe registry / map / injection / handlers / compile-embeds)")
    parser.add_argument(
        "--action",
        required=True,
        choices=["probes", "map", "probe-inject", "handlers", "compile-embeds"],
    )
    parser.add_argument("--validate", action="store_true",
                        help="probes: structurally validate the merged probe "
                             "registry (exit 2 listing every violation); "
                             "handlers: validate Handler/HandlerBinding "
                             "chapters ([C2] closed set, exit 2)")
    parser.add_argument("--reconcile", action="store_true",
                        help="probes: additionally reconcile internal probe "
                             "objects against live ## Feedback embeds "
                             "(two-way zero-gap required)")
    parser.add_argument("--bindings", action="store_true",
                        help="handlers: render the HandlerBinding view instead "
                             "of Handler rows")
    parser.add_argument("--point", default=None,
                        help="handlers: filter by lifecycle point (intersection)")
    parser.add_argument("--scope", default=None,
                        help="handlers: filter by scope keyword or object_id")
    parser.add_argument("--kind", default=None,
                        help="handlers: filter by handler kind (engine|agent|gate)")
    parser.add_argument("--mode", default=None,
                        help="handlers: filter by handler mode "
                             "(non-blocking|blocking)")
    parser.add_argument("--unit", default=None,
                        help="probe-inject: target custom unit custom:<owner>/<name>")
    parser.add_argument("--lifecycle-point", default=None,
                        help="probe-inject: lifecycle point (default wrap-up)")
    parser.add_argument("--notes-file", default=None,
                        help="probe-inject: collection-intent note file")
    parser.add_argument("--notes", default=None,
                        help="probe-inject: inline collection-intent note")
    parser.add_argument("--check", action="store_true",
                        help="compile-embeds: drift pre-check — exit 1 when any "
                             "compiled embed differs from the registry, write nothing")
    parser.add_argument("--workspace-root", default=None)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    return parser


_ACTIONS = {
    "probes": action_probes,
    "map": action_map,
    "probe-inject": action_probe_inject,
    "handlers": action_handlers,
    "compile-embeds": action_compile_embeds,
}


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload = _ACTIONS[args.action](args)
    except FeedbackError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except CheckDriftError as exc:
        if args.format == "json":
            print(json.dumps(exc.payload, ensure_ascii=False, indent=2))
        else:
            structural = exc.payload.get("structural", [])
            drift = exc.payload.get("drift", [])
            if structural:
                print(f"compile-embeds --check: STRUCTURAL drift in "
                      f"{len(structural)} of {exc.payload.get('units')} units "
                      "(exit 2 — review before recompiling; nothing written):")
                for line in structural:
                    print(f"- {line}")
                if drift:
                    print(f"plus regenerable drift in {len(drift)} units:")
                    for unit_id in drift:
                        print(f"- {unit_id}")
            else:
                print(f"compile-embeds drift in {len(drift)} of "
                      f"{exc.payload.get('units')} units (--check; nothing written):")
                for unit_id in drift:
                    print(f"- {unit_id}")
        return exc.exit_code
    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    elif args.action == "handlers" and args.bindings and not payload.get("ok"):
        print(render_text("handlers-bindings", payload))
    else:
        print(render_text(args.action, payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
