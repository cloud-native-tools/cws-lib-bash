#!/usr/bin/env python3
"""Record retention engine (records consume -> receipt -> retire).

Owns the cross-store lifecycle that the per-store engines deliberately leave out:
one durable receipt per consumed raw record, one retirement plan, one append-only
retirement ledger per apply batch. Raw records are deleted only when a receipt
covers them and the grace period has elapsed.

Stdlib only. Schema parsing is delegated to the sibling engines through
``sibling_engine``; this file owns only the retention lifecycle and its stores.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

KIND = "speckit.record-retention"
SCHEMA_VERSION = 1
RETENTION_REL = Path(".specify") / "memory" / "retention"
DEFAULT_GRACE_DAYS = 30

STORE_EXEC_QUANT = "exec-quant"
STORE_FEEDBACK = "feedback"
STORE_RUN_DETERMINATION = "run-determination"
STORE_SESSION_NOTE = "session-note"
STORES = (
    STORE_EXEC_QUANT,
    STORE_FEEDBACK,
    STORE_RUN_DETERMINATION,
    STORE_SESSION_NOTE,
)

STATUS_ELIGIBLE = "eligible"
STATUS_TOO_YOUNG = "too-young"
STATUS_BLOCKED = "blocked"

ACTIONS = ("scan", "distill", "plan", "apply", "status", "args-manifest")


class RetentionError(ValueError):
    """User-facing validation failure (exit 2)."""


# ---------------------------------------------------------------------------
# sibling engines (schema owners)
# ---------------------------------------------------------------------------

_SIBLING_CACHE: Dict[str, Any] = {}


def sibling_engine(filename: str):
    if filename in _SIBLING_CACHE:
        return _SIBLING_CACHE[filename]
    path = Path(__file__).resolve().parent / filename
    if not path.is_file():
        raise RetentionError(f"sibling engine not found beside this one: {path}")
    module_name = "_rr_" + filename.replace("-", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RetentionError(f"cannot load sibling engine: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    _SIBLING_CACHE[filename] = module
    return module


def execq():
    return sibling_engine("exec-quant.py")


def feedback():
    return sibling_engine("feedback-utils.py")


def memory():
    return sibling_engine("memory-utils.py")


def rundet():
    return sibling_engine("run-determination.py")


# ---------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def parse_iso(value: Any) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def age_days(created: Any) -> Optional[float]:
    parsed = parse_iso(created)
    if parsed is None:
        return None
    return (datetime.now(timezone.utc) - parsed).total_seconds() / 86400.0


def digest_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def digest_file(path: Path) -> str:
    try:
        return digest_text(path.read_text(encoding="utf-8"))
    except OSError:
        return "unreadable"


def entry_hash(store: str, entry_id: str) -> str:
    return hashlib.sha1(f"{store}|{entry_id}".encode("utf-8")).hexdigest()[:12]


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


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


def write_product(directory: Path, prefix: str, payload: Dict[str, Any]) -> Path:
    target = directory / f"{stamp()}-{prefix}.json"
    return write_json_atomic(target, payload)


# ---------------------------------------------------------------------------
# retention store layout
# ---------------------------------------------------------------------------

def retention_dir(workspace_root: Path) -> Path:
    return Path(workspace_root).resolve() / RETENTION_REL


def receipts_dir(workspace_root: Path) -> Path:
    return retention_dir(workspace_root) / "receipts"


def summaries_dir(workspace_root: Path, store: str) -> Path:
    return retention_dir(workspace_root) / "summaries" / store


def plans_dir(workspace_root: Path) -> Path:
    return retention_dir(workspace_root) / "plans"


def ledger_dir(workspace_root: Path) -> Path:
    return retention_dir(workspace_root) / "ledger"


def resolve_workspace_root(explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit).resolve()
    try:
        return memory().resolve_workspace_root(None)
    except Exception:
        return Path.cwd().resolve()


def selected_stores(spec: str) -> List[str]:
    requested = [part.strip() for part in (spec or "").split(",") if part.strip()]
    if not requested or requested == ["all"]:
        return list(STORES)
    unknown = [item for item in requested if item not in STORES]
    if unknown:
        raise RetentionError(f"unknown store(s): {', '.join(unknown)}")
    return requested


# ---------------------------------------------------------------------------
# receipts
# ---------------------------------------------------------------------------

def load_receipts(workspace_root: Path) -> Dict[Tuple[str, str], Path]:
    found: Dict[Tuple[str, str], Path] = {}
    base = receipts_dir(workspace_root)
    if not base.is_dir():
        return found
    for path in sorted(base.glob("*.json")):
        node = read_json(path)
        if not node:
            continue
        store = str(node.get("store") or "")
        entry_id = str(node.get("entry_id") or "")
        if store and entry_id:
            found[(store, entry_id)] = path
    return found


def write_receipt(workspace_root: Path, store: str, entry_id: str,
                  entry_file: str, carrier: Dict[str, Any],
                  summary_file: Optional[Path] = None) -> Path:
    base = receipts_dir(workspace_root)
    base.mkdir(parents=True, exist_ok=True)
    payload = {
        "kind": KIND + ".receipt",
        "schema_version": SCHEMA_VERSION,
        "store": store,
        "entry_id": entry_id,
        "entry_file": entry_file,
        "carrier": carrier,
        "summary_file": (summary_file.relative_to(workspace_root).as_posix()
                         if summary_file else None),
        "consumed_at": now_iso(),
    }
    name = f"{stamp()}-{entry_hash(store, entry_id)}.json"
    return write_json_atomic(base / name, payload)


# ---------------------------------------------------------------------------
# inventory
# ---------------------------------------------------------------------------

def _entry(store: str, entry_id: str, file: Path, workspace_root: Path,
           created: Any, **extra: Any) -> Dict[str, Any]:
    rel = file.relative_to(workspace_root).as_posix()
    record = {
        "store": store,
        "entry_id": entry_id,
        "file": rel,
        "created": str(created or ""),
        "status": STATUS_BLOCKED,
        "reason": "",
        "blocked": True,
    }
    record.update(extra)
    return record


def scan_exec_quant(workspace_root: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    base = execq().records_dir(workspace_root)
    if not base.is_dir():
        return out
    for path in sorted(base.glob("*.json")):
        try:
            node = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            out.append(_entry(STORE_EXEC_QUANT, f"record:{path.name}", path,
                              workspace_root, "", status=STATUS_BLOCKED,
                              reason="unreadable", blocked=True))
            continue
        if not isinstance(node, dict) or node.get("kind") != "speckit.exec-quant":
            out.append(_entry(STORE_EXEC_QUANT, f"record:{path.name}", path,
                              workspace_root, "", status=STATUS_BLOCKED,
                              reason="invalid-record", blocked=True))
            continue
        out.append(_entry(
            STORE_EXEC_QUANT,
            f"record:{path.name}",
            path,
            workspace_root,
            node.get("collected_at"),
            unit_id=str(node.get("unit_id") or ""),
            run_id=str(node.get("run_id") or ""),
            status=STATUS_BLOCKED,
            reason="unreceipted",
            blocked=False,
        ))
    return out


def _consume_log_carrier(workspace_root: Path, entry: Dict[str, Any]
                         ) -> Optional[Dict[str, Any]]:
    path = feedback().feedback_dir(workspace_root) / "consume-log.md"
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    needles = [str(entry.get("id") or ""), str(entry.get("unit_id") or ""),
               str(entry.get("run_id") or "")]
    for line in text.splitlines():
        if any(needle and needle in line for needle in needles):
            return {"type": "consume-log",
                    "path": path.relative_to(workspace_root).as_posix(),
                    "digest": digest_text(line.strip())}
    return None


def scan_feedback(workspace_root: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for entry in feedback().scan_entries(workspace_root):
        entry_id = str(entry.get("id") or "")
        filename = str(entry.get("file") or "")
        if not entry_id or not filename:
            continue
        path = feedback().feedback_dir(workspace_root) / filename
        record = _entry(STORE_FEEDBACK, entry_id, path, workspace_root,
                        entry.get("created"),
                        unit_id=str(entry.get("unit_id") or ""),
                        run_id=str(entry.get("run_id") or ""),
                        disposition=str(entry.get("disposition") or ""),
                        reason=STATUS_BLOCKED)
        disposition = record["disposition"]
        carrier: Optional[Dict[str, Any]] = None
        if disposition not in ("processed", "ignored"):
            record["reason"] = "open" if disposition in ("", "open") else "unclassified"
            record["blocked"] = True
        elif entry.get("introspection_ref"):
            carrier = {"type": "introspection",
                       "ref": str(entry.get("introspection_ref")),
                       "path": "feedback/introspection",
                       "digest": digest_text(str(entry.get("introspection_ref")))}
        elif entry.get("disposition_reason"):
            reason = str(entry.get("disposition_reason"))
            carrier = {"type": "disposition_reason", "text": reason,
                       "digest": digest_text(reason)}
        else:
            carrier = _consume_log_carrier(workspace_root, entry)
            if carrier is None:
                record["reason"] = "no-carrier"
                record["blocked"] = True
        if carrier is not None:
            record["status"] = STATUS_BLOCKED
            record["reason"] = "unreceipted"
            record["blocked"] = False
            record["carrier"] = carrier
        out.append(record)
    return out


def _session_entries(workspace_root: Path) -> Iterable[Tuple[Path, Dict[str, Any], str]]:
    base = memory().scope_dir(workspace_root, "session")
    if not base.is_dir():
        return []
    rows: List[Tuple[Path, Dict[str, Any], str]] = []
    for path in sorted(base.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        meta, _body = memory().parse_frontmatter(text)
        rows.append((path, meta, text))
    return rows


def _created_for_note(path: Path, meta: Dict[str, Any]) -> str:
    created = str(meta.get("created") or "")
    if created:
        return created
    name = path.name
    if len(name) >= 15 and name[8] == "T":
        return (f"{name[0:4]}-{name[4:6]}-{name[6:8]}T"
                f"{name[9:11]}:{name[11:13]}:{name[13:15]}Z")
    if len(name) >= 10 and name[4] == "-" and name[7] == "-":
        return name[:10] + "T00:00:00Z"
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc
                                      ).strftime("%Y-%m-%dT%H:%M:%SZ")
    except OSError:
        return ""


def scan_run_determination(workspace_root: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for item in rundet().load_determinations(workspace_root):
        entry = item["entry"]
        path = item["path"]
        record = item["record"]
        entry_id = str(entry.get("id") or path.name)
        settled_at = record.get("settled_at")
        row = _entry(STORE_RUN_DETERMINATION, entry_id, path, workspace_root,
                     record.get("determined_at") or entry.get("created"),
                     unit_id=str(record.get("unit_id") or ""),
                     run_id=str(record.get("run_id") or ""),
                     settled_at=str(settled_at or ""),
                     status=STATUS_BLOCKED,
                     blocked=not bool(settled_at))
        row["reason"] = "unreceipted" if settled_at else "unsettled"
        out.append(row)
    return out


def scan_session_notes(workspace_root: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for path, meta, _text in _session_entries(workspace_root):
        tags = meta.get("tags") or []
        if isinstance(tags, str):
            tags = [tags]
        if "run-determination" in tags:
            continue
        entry_id = str(meta.get("id") or path.name)
        row = _entry(STORE_SESSION_NOTE, entry_id, path, workspace_root,
                     _created_for_note(path, meta),
                     unit_id=str(meta.get("source") or ""),
                     run_id="",
                     title=str(meta.get("title") or ""),
                     status=STATUS_BLOCKED,
                     reason="needs-promotion",
                     blocked=False)
        out.append(row)
    return out


def scan_store(workspace_root: Path, store: str) -> List[Dict[str, Any]]:
    if store == STORE_EXEC_QUANT:
        return scan_exec_quant(workspace_root)
    if store == STORE_FEEDBACK:
        return scan_feedback(workspace_root)
    if store == STORE_RUN_DETERMINATION:
        return scan_run_determination(workspace_root)
    if store == STORE_SESSION_NOTE:
        return scan_session_notes(workspace_root)
    raise RetentionError(f"unknown store: {store}")


def apply_status(workspace_root: Path, entries: Sequence[Dict[str, Any]],
                 receipts: Dict[Tuple[str, str], Path], grace_days: int) -> None:
    for entry in entries:
        if entry.get("blocked"):
            continue
        receipt = receipts.get((entry["store"], entry["entry_id"]))
        age = age_days(entry.get("created"))
        if receipt is None:
            entry["status"] = STATUS_BLOCKED
            entry["reason"] = ("needs-promotion"
                               if entry["store"] == STORE_SESSION_NOTE
                               else "unreceipted")
        elif age is None:
            entry["status"] = STATUS_BLOCKED
            entry["reason"] = "unknown-age"
        elif age < grace_days:
            entry["status"] = STATUS_TOO_YOUNG
            entry["reason"] = "grace"
            entry["receipt"] = receipt.relative_to(workspace_root).as_posix()
        else:
            entry["status"] = STATUS_ELIGIBLE
            entry["reason"] = "covered"
            entry["receipt"] = receipt.relative_to(workspace_root).as_posix()


def scan_all(workspace_root: Path, stores: Sequence[str],
             grace_days: int) -> Dict[str, Any]:
    receipts = load_receipts(workspace_root)
    by_store: Dict[str, List[Dict[str, Any]]] = {}
    for store in stores:
        entries = scan_store(workspace_root, store)
        apply_status(workspace_root, entries, receipts, grace_days)
        by_store[store] = entries
    return {"receipts": receipts, "stores": by_store}


def digest_scan(result: Dict[str, Any]) -> Dict[str, Any]:
    stores: Dict[str, Dict[str, int]] = {}
    for store, entries in result["stores"].items():
        eligible = sum(1 for entry in entries
                       if entry.get("status") == STATUS_ELIGIBLE)
        too_young = sum(1 for entry in entries
                        if entry.get("status") == STATUS_TOO_YOUNG)
        blocked = sum(1 for entry in entries
                      if entry.get("status") == STATUS_BLOCKED)
        stores[store] = {"total": len(entries), "eligible": eligible,
                         "too_young": too_young, "blocked": blocked,
                         "with_receipt": eligible + too_young}
    return {"stores": stores,
            "receipts": len(result["receipts"])}


# ---------------------------------------------------------------------------
# distill
# ---------------------------------------------------------------------------

def _month_of(value: Any) -> str:
    parsed = parse_iso(value)
    return parsed.strftime("%Y-%m") if parsed else "unknown"


def _summary_path(workspace_root: Path, store: str, month: str) -> Path:
    return summaries_dir(workspace_root, store) / f"{stamp()}-{month}.json"


def _receipt_carrier_for_summary(workspace_root: Path, summary: Path) -> Dict[str, Any]:
    return {"type": "summary",
            "path": summary.relative_to(workspace_root).as_posix(),
            "digest": digest_file(summary)}


def distill_exec_quant(workspace_root: Path, entries: Sequence[Dict[str, Any]],
                       receipts: Dict[Tuple[str, str], Path]) -> Dict[str, Any]:
    created: List[str] = []
    skipped = 0
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        if entry.get("blocked"):
            skipped += 1
            continue
        if (STORE_EXEC_QUANT, entry["entry_id"]) in receipts:
            continue
        node = read_json(Path(workspace_root) / entry["file"])
        if node is None:
            skipped += 1
            continue
        groups.setdefault(_month_of(entry.get("created")), []).append(
            {**entry, "_record": node})
    for month, members in sorted(groups.items()):
        units: Dict[str, int] = {}
        quality: Dict[str, Dict[str, int]] = {}
        roster: List[Dict[str, Any]] = []
        for member in members:
            record = member["_record"]
            unit = str(record.get("unit_id") or "")
            units[unit] = units.get(unit, 0) + 1
            q = record.get("quality") if isinstance(record.get("quality"), dict) else {}
            for field, value in q.items():
                slot = quality.setdefault(field, {"evaluated": 0, "not_evaluated": 0})
                if isinstance(value, dict) and "value" in value:
                    slot["evaluated"] += 1
                else:
                    slot["not_evaluated"] += 1
            roster.append({"entry_id": member["entry_id"],
                           "file": member["file"],
                           "unit_id": unit,
                           "run_id": str(record.get("run_id") or ""),
                           "collected_at": str(record.get("collected_at") or "")})
        summary = _summary_path(workspace_root, STORE_EXEC_QUANT, month)
        write_json_atomic(summary, {
            "kind": KIND + ".summary",
            "schema_version": SCHEMA_VERSION,
            "store": STORE_EXEC_QUANT,
            "month": month,
            "generated_at": now_iso(),
            "record_count": len(members),
            "units": units,
            "quality": quality,
            "records": roster,
        })
        carrier = _receipt_carrier_for_summary(workspace_root, summary)
        for member in members:
            key = (STORE_EXEC_QUANT, member["entry_id"])
            if key in receipts:
                continue
            write_receipt(workspace_root, STORE_EXEC_QUANT, member["entry_id"],
                          member["file"], carrier, summary)
            created.append(member["entry_id"])
    return {"summaries": len(groups), "receipts": len(created),
            "entries": created, "skipped": skipped}


def distill_run_determination(workspace_root: Path, entries: Sequence[Dict[str, Any]],
                              receipts: Dict[Tuple[str, str], Path]) -> Dict[str, Any]:
    created: List[str] = []
    skipped = 0
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for entry in entries:
        if entry.get("blocked") or not entry.get("settled_at"):
            skipped += 1
            continue
        if (STORE_RUN_DETERMINATION, entry["entry_id"]) in receipts:
            continue
        path = Path(workspace_root) / entry["file"]
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            skipped += 1
            continue
        record = rundet().parse_entry_body(text)
        if record is None:
            skipped += 1
            continue
        groups.setdefault(_month_of(entry.get("created")), []).append(
            {**entry, "_record": record})
    for month, members in sorted(groups.items()):
        units: Dict[str, int] = {}
        axes: Dict[str, Dict[str, int]] = {}
        qualifications: Dict[str, int] = {}
        roster: List[Dict[str, Any]] = []
        for member in members:
            record = member["_record"]
            unit = str(record.get("unit_id") or "")
            units[unit] = units.get(unit, 0) + 1
            qual = str(record.get("qualification") or "")
            qualifications[qual] = qualifications.get(qual, 0) + 1
            for axis, value in (record.get("axes") or {}).items():
                verdict = str((value or {}).get("verdict") or "")
                slot = axes.setdefault(axis, {})
                slot[verdict] = slot.get(verdict, 0) + 1
            roster.append({"entry_id": member["entry_id"],
                           "file": member["file"],
                           "unit_id": unit,
                           "run_id": str(record.get("run_id") or ""),
                           "determined_at": str(record.get("determined_at") or ""),
                           "settled_at": str(record.get("settled_at") or "")})
        summary = _summary_path(workspace_root, STORE_RUN_DETERMINATION, month)
        write_json_atomic(summary, {
            "kind": KIND + ".summary",
            "schema_version": SCHEMA_VERSION,
            "store": STORE_RUN_DETERMINATION,
            "month": month,
            "generated_at": now_iso(),
            "record_count": len(members),
            "units": units,
            "axes": axes,
            "qualifications": qualifications,
            "records": roster,
        })
        carrier = _receipt_carrier_for_summary(workspace_root, summary)
        for member in members:
            key = (STORE_RUN_DETERMINATION, member["entry_id"])
            if key in receipts:
                continue
            write_receipt(workspace_root, STORE_RUN_DETERMINATION,
                          member["entry_id"], member["file"], carrier, summary)
            created.append(member["entry_id"])
    return {"summaries": len(groups), "receipts": len(created),
            "entries": created, "skipped": skipped}


def distill_feedback(workspace_root: Path, entries: Sequence[Dict[str, Any]],
                     receipts: Dict[Tuple[str, str], Path]) -> Dict[str, Any]:
    created: List[str] = []
    skipped = 0
    for entry in entries:
        carrier = entry.get("carrier")
        if carrier is None:
            skipped += 1
            continue
        key = (STORE_FEEDBACK, entry["entry_id"])
        if key in receipts:
            continue
        write_receipt(workspace_root, STORE_FEEDBACK, entry["entry_id"],
                      entry["file"], carrier)
        created.append(entry["entry_id"])
    return {"summaries": 0, "receipts": len(created),
            "entries": created, "skipped": skipped}


def _load_promotions(path: Optional[str]) -> Dict[str, Dict[str, Any]]:
    if not path:
        return {}
    node = read_json(Path(path))
    if node is None:
        raise RetentionError(f"cannot read promotions file: {path}")
    rows = node.get("promotions")
    if not isinstance(rows, list):
        raise RetentionError("promotions file must carry a 'promotions' list")
    mapping: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = str(row.get("entry") or row.get("entry_id") or row.get("file") or "")
        if not key:
            continue
        mapping[key] = row
    return mapping


def distill_session_notes(workspace_root: Path, entries: Sequence[Dict[str, Any]],
                          receipts: Dict[Tuple[str, str], Path],
                          promotions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    created: List[str] = []
    skipped = 0
    for entry in entries:
        key = (STORE_SESSION_NOTE, entry["entry_id"])
        if key in receipts:
            continue
        promotion = (promotions.get(entry["entry_id"])
                     or promotions.get(entry["file"])
                     or promotions.get(Path(entry["file"]).name))
        if promotion is None:
            skipped += 1
            continue
        kind = str(promotion.get("type") or promotion.get("carrier_type") or "")
        if kind not in ("knowledge", "history", "ephemeral"):
            skipped += 1
            continue
        carrier_path = str(promotion.get("path") or "")
        if kind != "ephemeral":
            candidate = (Path(workspace_root) / carrier_path
                         if carrier_path else None)
            if candidate is None or not candidate.is_file():
                skipped += 1
                continue
            carrier = {"type": kind, "path": carrier_path,
                       "digest": digest_file(candidate)}
        else:
            carrier = {"type": "ephemeral",
                       "reason": str(promotion.get("reason") or "")}
        write_receipt(workspace_root, STORE_SESSION_NOTE, entry["entry_id"],
                      entry["file"], carrier)
        created.append(entry["entry_id"])
    return {"summaries": 0, "receipts": len(created),
            "entries": created, "skipped": skipped}


def action_distill(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    stores = selected_stores(args.stores)
    result = scan_all(workspace_root, stores, 0)
    receipts = result["receipts"]
    promotions = _load_promotions(args.promotions)
    outputs: Dict[str, Any] = {}
    for store in stores:
        entries = result["stores"][store]
        if store == STORE_EXEC_QUANT:
            outputs[store] = distill_exec_quant(workspace_root, entries, receipts)
        elif store == STORE_FEEDBACK:
            outputs[store] = distill_feedback(workspace_root, entries, receipts)
        elif store == STORE_RUN_DETERMINATION:
            outputs[store] = distill_run_determination(workspace_root, entries, receipts)
        elif store == STORE_SESSION_NOTE:
            outputs[store] = distill_session_notes(
                workspace_root, entries, receipts, promotions)
    return {"ok": True, "action": "distill", "stores": outputs}


# ---------------------------------------------------------------------------
# plan / apply
# ---------------------------------------------------------------------------

def build_plan(workspace_root: Path, stores: Sequence[str],
               grace_days: int) -> Dict[str, Any]:
    result = scan_all(workspace_root, stores, grace_days)
    items: List[Dict[str, Any]] = []
    for store in stores:
        for entry in result["stores"][store]:
            if entry.get("status") != STATUS_ELIGIBLE:
                continue
            items.append({
                "store": store,
                "entry_id": entry["entry_id"],
                "file": entry["file"],
                "created": entry.get("created", ""),
                "age_days": round(age_days(entry.get("created")) or 0.0, 3),
                "receipt": entry.get("receipt", ""),
            })
    return {"kind": KIND + ".plan", "schema_version": SCHEMA_VERSION,
            "created": now_iso(), "confirmed": False,
            "grace_days": grace_days, "stores": list(stores), "items": items}


def action_plan(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    stores = selected_stores(args.stores)
    plan = build_plan(workspace_root, stores, args.grace_days)
    target = (Path(args.plan_out) if args.plan_out
              else plans_dir(workspace_root) / f"{stamp()}-retention-plan.json")
    if not target.is_absolute():
        from_cwd = Path.cwd() / target
        target = from_cwd if from_cwd.parent.is_dir() else workspace_root / target
    write_json_atomic(target, plan)
    return {"ok": True, "action": "plan", "plan": str(target),
            "items": len(plan["items"]),
            "stores": {store: sum(1 for item in plan["items"]
                                  if item["store"] == store)
                       for store in stores}}


def _store_root(workspace_root: Path, store: str) -> Path:
    if store == STORE_EXEC_QUANT:
        return execq().records_dir(workspace_root)
    if store == STORE_FEEDBACK:
        return feedback().feedback_dir(workspace_root)
    if store == STORE_RUN_DETERMINATION:
        return memory().scope_dir(workspace_root, "session")
    if store == STORE_SESSION_NOTE:
        return memory().scope_dir(workspace_root, "session")
    raise RetentionError(f"unknown store: {store}")


def _recheck_entry(workspace_root: Path, store: str, path: Path,
                   receipt_node: Dict[str, Any]) -> str:
    """Re-validate the entry's own state at apply time (it may have changed)."""
    if store == STORE_EXEC_QUANT:
        node = read_json(path)
        if node is None or node.get("kind") != "speckit.exec-quant":
            return "entry-invalid"
    elif store == STORE_FEEDBACK:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return "entry-unreadable"
        meta, _body = feedback().parse_frontmatter(text)
        if str(meta.get("disposition") or "") not in ("processed", "ignored"):
            return "entry-open"
        if not receipt_node.get("carrier"):
            return "receipt-carrier-missing"
    elif store == STORE_RUN_DETERMINATION:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            return "entry-unreadable"
        record = rundet().parse_entry_body(text)
        if record is None or not record.get("settled_at"):
            return "entry-unsettled"
    elif store == STORE_SESSION_NOTE:
        carrier = receipt_node.get("carrier")
        if not isinstance(carrier, dict) or not carrier:
            return "receipt-carrier-missing"
        carrier_type = str(carrier.get("type") or "")
        if carrier_type not in ("knowledge", "history", "ephemeral"):
            return "receipt-carrier-invalid"
        if carrier_type != "ephemeral":
            carrier_path = str(carrier.get("path") or "")
            if not carrier_path or not (workspace_root / carrier_path).is_file():
                return "carrier-missing"
    return ""


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args],
                          capture_output=True, text=True, timeout=30)


def _git_clean(root: Path, files: Sequence[str]) -> Tuple[bool, List[str]]:
    check = _git(root, "rev-parse", "--git-dir")
    if check.returncode != 0:
        return False, ["not-a-git-repository"]
    if not files:
        return True, []
    status = _git(root, "status", "--porcelain", "--", *files)
    if status.returncode != 0:
        return False, [status.stderr.strip() or "git-status-failed"]
    dirty = [line for line in status.stdout.splitlines() if line.strip()]
    return (not dirty), dirty


def _count_entries(workspace_root: Path, stores: Sequence[str]) -> int:
    total = 0
    for store in stores:
        total += len(scan_store(workspace_root, store))
    return total


def action_apply(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    plan_path = Path(args.plan or "")
    if not plan_path.is_absolute():
        from_cwd = Path.cwd() / plan_path
        plan_path = from_cwd if from_cwd.is_file() else workspace_root / plan_path
    plan = read_json(plan_path)
    if plan is None:
        raise RetentionError(f"cannot read plan: {plan_path}")
    if plan.get("confirmed") is not True:
        raise RetentionError("apply refused: plan.confirmed must be true")
    items = plan.get("items")
    if not isinstance(items, list):
        raise RetentionError("apply refused: plan.items must be a list")
    grace_days = int(plan.get("grace_days") or DEFAULT_GRACE_DAYS)
    stores = [str(store) for store in (plan.get("stores") or [])
              if str(store) in STORES]
    if not stores:
        stores = sorted({str(item.get("store") or "") for item in items
                         if item.get("store")}) or list(STORES)

    receipts = load_receipts(workspace_root)
    before = _count_entries(workspace_root, stores)
    validated: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    seen_items: set = set()
    for item in items:
        store = str(item.get("store") or "")
        entry_id = str(item.get("entry_id") or "")
        file_rel = str(item.get("file") or "")
        receipt_rel = str(item.get("receipt") or "")
        problem = ""
        item_key = (store, entry_id)
        if item_key in seen_items:
            problem = "duplicate-item"
        seen_items.add(item_key)
        if problem:
            pass
        elif store not in STORES or not entry_id or not file_rel:
            problem = "invalid-item"
        else:
            path = (workspace_root / file_rel).resolve()
            root = _store_root(workspace_root, store)
            if not is_relative_to(path, root.resolve()):
                problem = "outside-store-root"
            elif not path.is_file():
                problem = "missing-file"
            elif not receipt_rel:
                problem = "missing-receipt"
            else:
                receipt_path = Path(receipt_rel)
                if not receipt_path.is_absolute():
                    receipt_path = (workspace_root / receipt_path).resolve()
                node = read_json(receipt_path)
                if node is None or node.get("store") != store \
                        or node.get("entry_id") != entry_id:
                    problem = "receipt-mismatch"
                elif node.get("entry_file") != file_rel:
                    problem = "receipt-entry-file-mismatch"
                elif (store, entry_id) not in receipts:
                    problem = "receipt-not-indexed"
                else:
                    problem = _recheck_entry(workspace_root, store, path, node)
        age = age_days(item.get("created"))
        if not problem and (age is None or age < grace_days):
            problem = "grace-not-elapsed"
        if problem:
            failures.append({"store": store, "entry_id": entry_id,
                             "file": file_rel, "problem": problem})
        else:
            validated.append({"store": store, "entry_id": entry_id,
                              "file": file_rel, "receipt": receipt_rel,
                              "path": str((workspace_root / file_rel).resolve())})

    if failures:
        raise RetentionError(
            "apply refused: " + ", ".join(f"{f['entry_id']}:{f['problem']}"
                                          for f in failures))

    clean, dirty = _git_clean(workspace_root, [item["file"] for item in validated])
    if not clean and not args.allow_unversioned:
        raise RetentionError(
            "apply refused: target files are not clean in git (commit them first) "
            f"or pass --allow-unversioned: {dirty[:5]}")

    removed: List[Dict[str, Any]] = []
    delete_failures: List[Dict[str, Any]] = []
    for item in validated:
        path = Path(item["path"])
        try:
            path.unlink()
            removed.append({key: item[key] for key in
                            ("store", "entry_id", "file", "receipt")})
        except OSError as exc:
            delete_failures.append({**item, "error": str(exc)})

    try:
        feedback().migrate_legacy_index(workspace_root)
    except Exception:
        pass
    try:
        memory().migrate_legacy_index(workspace_root, "session")
    except Exception:
        pass

    after = _count_entries(workspace_root, stores)
    expected = before - len(removed)
    conservation_ok = after == expected
    ledger = {
        "kind": KIND + ".ledger",
        "schema_version": SCHEMA_VERSION,
        "applied_at": now_iso(),
        "plan": str(plan_path),
        "removed": removed,
        "delete_failures": delete_failures,
        "counts": {"before": before, "removed": len(removed),
                   "remaining": after, "expected_remaining": expected},
        "conservation_ok": conservation_ok,
        "git": {"clean": clean, "allow_unversioned": bool(args.allow_unversioned),
                "dirty": dirty},
    }
    target = ledger_dir(workspace_root) / f"{stamp()}-retirement.json"
    write_json_atomic(target, ledger)
    result = {"ok": conservation_ok and not delete_failures,
              "action": "apply", "ledger": str(target),
              "removed": len(removed), "remaining": after,
              "conservation_ok": conservation_ok,
              "delete_failures": delete_failures}
    if not conservation_ok or delete_failures:
        raise RetentionError(json.dumps(result, ensure_ascii=False))
    return result


# ---------------------------------------------------------------------------
# scan / status / args-manifest
# ---------------------------------------------------------------------------

def action_scan(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    stores = selected_stores(args.stores)
    result = scan_all(workspace_root, stores, args.grace_days)
    digest = digest_scan(result)
    return {"ok": True, "action": "scan", "grace_days": args.grace_days,
            "stores": digest["stores"], "receipts": digest["receipts"],
            "candidates": [
                {key: entry.get(key) for key in
                 ("store", "entry_id", "file", "created", "status", "reason")}
                for store in stores for entry in result["stores"][store]
                if entry.get("status") == STATUS_ELIGIBLE
            ],
            "blocked": [
                {key: entry.get(key) for key in
                 ("store", "entry_id", "file", "created", "reason")}
                for store in stores for entry in result["stores"][store]
                if entry.get("status") == STATUS_BLOCKED
            ]}


def action_status(args: argparse.Namespace) -> Dict[str, Any]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    stores = selected_stores(args.stores)
    result = scan_all(workspace_root, stores, args.grace_days)
    digest = digest_scan(result)
    ledger_count = len(list(ledger_dir(workspace_root).glob("*.json"))) \
        if ledger_dir(workspace_root).is_dir() else 0
    return {"ok": True, "action": "status", "stores": digest["stores"],
            "receipts": digest["receipts"], "ledgers": ledger_count}


ARG_MANIFEST = {
    "scan": {"required": [], "source": ["--stores", "--grace-days",
                                         "--workspace-root"]},
    "distill": {"required": [], "source": ["--stores", "--promotions",
                                            "--workspace-root"]},
    "plan": {"required": [], "source": ["--stores", "--grace-days",
                                         "--plan-out", "--workspace-root"]},
    "apply": {"required": ["--plan"], "source": ["--allow-unversioned",
                                                  "--workspace-root"]},
    "status": {"required": [], "source": ["--stores", "--grace-days",
                                           "--workspace-root"]},
    "args-manifest": {"required": [], "source": []},
}


def action_args_manifest(args: argparse.Namespace) -> Dict[str, Any]:
    parser = build_parser()
    live = {opt for action in parser._actions for opt in action.option_strings}
    manifest: Dict[str, Any] = {}
    for action_name in ACTIONS:
        spec = ARG_MANIFEST.get(action_name)
        if spec is None:
            raise RetentionError(
                f"args-manifest: action {action_name!r} has no manifest spec")
        for key in ("required", "source"):
            unknown = [flag for flag in spec[key] if flag not in live]
            if unknown:
                raise RetentionError(
                    f"args-manifest: {action_name} {key} flags are not options "
                    f"of this engine's parser: {unknown}")
        manifest[action_name] = {"required": list(spec["required"]),
                                 "source": list(spec["source"])}
    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Record retention engine (consume -> receipt -> retire)")
    parser.add_argument("--action", choices=list(ACTIONS), required=True)
    parser.add_argument("--workspace-root", default=None)
    parser.add_argument("--stores", default="all")
    parser.add_argument("--grace-days", type=int, default=DEFAULT_GRACE_DAYS)
    parser.add_argument("--promotions", default=None)
    parser.add_argument("--plan", default=None)
    parser.add_argument("--plan-out", default=None)
    parser.add_argument("--allow-unversioned", action="store_true")
    parser.add_argument("--format", choices=["text", "json"], default="json")
    return parser


def _emit(payload: Dict[str, Any], fmt: str) -> None:
    if fmt == "text":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.action == "scan":
            payload = action_scan(args)
        elif args.action == "distill":
            payload = action_distill(args)
        elif args.action == "plan":
            payload = action_plan(args)
        elif args.action == "apply":
            payload = action_apply(args)
        elif args.action == "status":
            payload = action_status(args)
        elif args.action == "args-manifest":
            payload = action_args_manifest(args)
        else:  # pragma: no cover - argparse closes the set
            raise RetentionError(f"unknown action: {args.action}")
        _emit(payload, args.format)
        return 0
    except RetentionError as exc:
        print(f"record-retention: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # never raise into the caller
        print(f"record-retention: unexpected failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
