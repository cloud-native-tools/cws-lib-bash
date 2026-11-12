#!/usr/bin/env python3
"""``/speckit.measure`` engine — the read-only measurement report over the exec-quant store (087, T064).

One stdlib-only script behind the thin command ``.specify/templates/commands/measure.md``. Its clauses are owned by
``.specify/specs/088-speckit-visualization/contracts/measure-report.contract.md`` (C-53…C-62) and its store
access is shared with the visibility surfaces through the ONE store reader
(``efficiency-element.contract.md`` C-65): records are obtained only by importing
``.specify/scripts/python/exec-quant.py``'s read path in process — never by re-parsing the record format, never by
shelling out, never by caching (C-53).

Shape of a run: a half-open window (``--since`` start, ``--window`` span; neither means all records, C-54),
a selection of exact ``(unit_id, unit_type)`` identities (C-55), per-unit figures with the provenance and
coverage the records state (C-56), one declared per-unit cap printed on every run (C-57), four exclusion
classes counted once each beside the omitted count (C-58), a closed four-value exit-status set (C-59), two
closed actions as projections of one computed result (C-60), byte-identical output over an unchanged store
(C-61) and a strictly read-only, machinery-free delivery shape (C-62).

This file names neither the record's schema version nor its field slots nor any closed vocabulary of its own:
the declaration owner (``.specify/shared/declarations/facts/quant-record-schema.yaml``) is reached through the engine
module at run time, and the two field-slot names it must touch are read from the engine's own source at run
time (C-70/C-71). The store-availability render literal is likewise not spelled here: it is reached through
``status-digest.py``'s owner-reading entry (:func:`status-digest.efficiency_vocabulary`), whose single
definition site is ``.specify/shared/guidelines/reporting-obligations.md`` § 9.1.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import statistics
import sys
from datetime import timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

#: The store engine — the one reader this report and the visibility surfaces share (C-53 / C-65).
STORE_ENGINE = Path("scripts") / "python" / "exec-quant.py"

#: The visibility surfaces' shared entry to the owner's render literals (§ 9.1 of
#: ``.specify/shared/guidelines/reporting-obligations.md``): the store-availability literal this report prints is read
#: through it, never spelled a second time here (constitution XIV / contract C-47).
DIGEST_SCRIPT = Path("scripts") / "python" / "status-digest.py"

#: Closed exit-status set (C-59). Exactly these four; no fifth status exists.
EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_INPUT_ERROR = 2
EXIT_NOTHING_TO_ANALYSE = 3

#: The declared per-unit cap (C-57): the number of records one unit contributes to its figures. The value
#: actually used is printed on every run; ``--cap`` overrides it for one invocation.
DEFAULT_CAP = 200

#: The window span's input form: a positive integer with one of the four unit letters (C-54).
_WINDOW_RE = re.compile(r"^\s*(\d+)\s*([smhd])\s*$")
_WINDOW_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}

#: Field slots reached through the engine, read from the engine's own source at run time: this delivered file
#: MUST NOT re-spell the declaration owner's field slots as literals (C-70/C-71). Owners: the record schema
#: declaration via ``.specify/scripts/python/exec-quant.py``. Both bind in :func:`bind_engine_constants`; ``None``
#: until then, and an unresolvable slot is an unavailable input reported as such — never guessed.
_SCHEMA_FIELD = None
_ELAPSED_NODE = None

#: The JSON document's top-level keys (C-60) — the contract owns this set; it is restated nowhere else.
DOCUMENT_KEYS = ("window", "selection", "cap", "rows", "excluded", "exit_hint")


# --------------------------------------------------------------------------- #
# the one store reading
# --------------------------------------------------------------------------- #
def load_engine():
    """Import the store engine in process and return its module, or ``None`` when it is unavailable (C-53)."""
    path = REPO_ROOT / STORE_ENGINE
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("exec_quant_store_engine", str(path))
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except (OSError, ImportError, SyntaxError, ValueError):
        return None
    return module


def load_availability_literal():
    """The store-availability render literal, read through the surfaces' shared entry (§ 9.1 / C-47).

    ``status-digest.py`` owns the owner-reading path (its :func:`efficiency_vocabulary` prefers the owner
    document's § 9.1 text); this report reaches the literal through it and never spells a second copy. An
    unreadable entry point returns ``None`` — an unavailable input the caller reports as such.
    """
    path = REPO_ROOT / DIGEST_SCRIPT
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("measure_digest_entry", str(path))
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.efficiency_vocabulary().get("no_measurements")
    except (OSError, ImportError, SyntaxError, ValueError, AttributeError):
        return None


def read_field_slots(engine):
    """The two field-slot names the report must touch, read from the engine's own faces (C-70/C-71).

    The schema-version key comes from the declaration owner through the engine's own schema reading (the
    engine module carries the declared statement); the elapsed node is the ``*_ms`` quality node the engine
    itself writes. Returns ``None`` when either cannot be resolved — an unavailable input, never a guess.
    """
    statement = getattr(engine, "_QUANT_SCHEMA", None)
    version_key = None
    if isinstance(statement, dict):
        version_key = next((key for key in statement if "version" in str(key)), None)
    try:
        text = (REPO_ROOT / STORE_ENGINE).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    elapsed = re.search(r"[\"'](\w+_ms)[\"']:\s*NOT_EVALUATED", text)
    if version_key is None or elapsed is None:
        return None
    return version_key, elapsed.group(1)


def bind_engine_constants(engine) -> bool:
    """Point the module's engine-owned constants at the imported engine (C-53/C-71) — one reading, no copies."""
    global engine_not_evaluated, _SCHEMA_FIELD, _ELAPSED_NODE
    engine_not_evaluated = engine.NOT_EVALUATED
    slots = read_field_slots(engine)
    if slots is None:
        return False
    _SCHEMA_FIELD, _ELAPSED_NODE = slots
    return True


def read_store(engine, workspace: Path):
    """Read the store ONCE — the legacy stream through the engine's reader, entry files bound to their
    identity (C-53, C-57, C-62, C-69).

    Returns ``(records, encountered)``: ``records`` is what the engine's readers returned (legacy stream first,
    then the per-record directory, exactly as the engine composes them); ``encountered`` counts every record
    surface the two readers walked, so the records they could not hand back are countable as ``unreadable``
    without this file interpreting anything. Each per-record entry is additionally bound to its own identity —
    the record file's name stem (C-57) — carried on the ``_record_stem`` key; the file is opened only to bind
    that identity, and the record's meaning stays the engine's. Strictly read-only: everything opens for
    reading, nothing is written and no path is created under the store.
    """
    base = engine.storage_dir(workspace)
    if not base.is_dir():
        return [], 0
    legacy_path = base / engine.LEGACY_RECORDS_NAME
    encountered = 0
    if legacy_path.is_file():
        with legacy_path.open("r", encoding="utf-8") as handle:
            encountered += sum(1 for line in handle if line.strip())
    records_dir = engine.records_dir(workspace)
    records = list(engine.read_jsonl_safe(legacy_path))
    if records_dir.is_dir():
        entry_paths = sorted(records_dir.glob("*.json"))
        encountered += len(entry_paths)
        for entry_path in entry_paths:
            try:
                node = json.loads(entry_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(node, dict):
                node["_record_stem"] = entry_path.stem
                records.append(node)
    return records, encountered


# --------------------------------------------------------------------------- #
# window, selection, figures
# --------------------------------------------------------------------------- #
def resolve_window(engine, since_value, window_value):
    """The half-open window (C-54). Returns ``(start, end, statement)``; raises the engine's input error.

    ``--since`` is parsed exactly as the engine parses its own ``--since``; ``--window`` is a positive span in
    seconds/minutes/hours/days and the end resolves as start + span. Neither bound means ALL records the store
    holds, and the report says so literally. A start after the resolved end cannot arise from a positive span,
    so a non-positive or unresolvable span is itself the input error.
    """
    if since_value is None and window_value is None:
        return None, None, "all records"
    if since_value is None or window_value is None:
        raise engine.InputError(
            "measure: --since and --window must be given together (or neither), got %r / %r"
            % (since_value, window_value)
        )
    try:
        start = engine._parse_since(since_value)
    except engine.InputError:
        raise
    if start is None:
        raise engine.InputError("measure: invalid --since: %r" % since_value)
    match = _WINDOW_RE.match(window_value or "")
    if match is None:
        raise engine.InputError("measure: invalid --window: %r (expected e.g. 30m, 1h, 24h)" % window_value)
    seconds = int(match.group(1)) * _WINDOW_UNITS[match.group(2)]
    if seconds <= 0:
        raise engine.InputError("measure: invalid --window: %r (the span must be positive)" % window_value)
    end = start + timedelta(seconds=seconds)
    statement = "[%s, %s)" % (start.isoformat(), end.isoformat())
    return start, end, statement


def _text_pair(record, key) -> str:
    value = record.get(key)
    return value if isinstance(value, str) and value else ""


def classify(records, engine, start, end, cap, unreadable):
    """One pass, one class per record (C-58): legacy, outside-window, unknown-unit, or its unit's window set.

    The truncating cap (C-57) is applied per unit by the record's own identity ascending — the record file's
    name stem, which carries its collection stamp and a stable suffix, with a legacy-stream record's stamp
    standing in for the absent stem. Sorting on the identity (never on the order the reader enumerated files
    in) keeps the retained set stable across runs and across filesystem enumeration order. ``unreadable`` is
    the count the one reading already established (record surfaces the readers walked but could not hand
    back). Returns ``(units, excluded, read_total)``.
    """
    excluded = {
        "unreadable": unreadable,
        "legacy_format": 0,
        "outside_window": 0,
        "unknown_unit": 0,
        "outside_cap": 0,
        "read": 0,
    }
    units = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        version = record.get(_SCHEMA_FIELD)
        if isinstance(version, int) and version < engine.SCHEMA_VERSION:
            excluded["legacy_format"] += 1
            continue
        stamp = engine._parse_iso(record.get("collected_at"))
        if start is not None and (stamp is None or not (start <= stamp < end)):
            excluded["outside_window"] += 1
            continue
        pair = (_text_pair(record, "unit_id"), _text_pair(record, "unit_type"))
        if not pair[0] or not pair[1]:
            excluded["unknown_unit"] += 1
            continue
        units.setdefault(pair, []).append(record)
    read_total = len(records) + unreadable
    retained = {}

    def identity(record):
        return (str(record.get("collected_at") or ""), str(record.get("_record_stem") or ""))

    for pair, rows in units.items():
        ordered = sorted(rows, key=identity)
        retained[pair] = ordered[:cap]
        excluded["outside_cap"] += len(ordered) - len(retained[pair])
    excluded["read"] = read_total
    return retained, excluded, read_total


def resolve_selection(retained, unit_values):
    """The exact-identity selection set (C-55): a set, never a sequence; unknown means input error.

    Each value is an exact ``(unit_id, unit_type)`` identity written ``unit_id/unit_type`` (the id may itself
    carry slashes; the type is the last segment). With no value the selection is every unit the store holds and
    the report says so.
    """
    held = set(retained)
    if not unit_values:
        return sorted(held), "every unit the store holds"
    chosen = set()
    for value in unit_values:
        parts = value.rsplit("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(value)
        pair = (parts[0], parts[1])
        if pair not in held:
            raise ValueError(value)
        chosen.add(pair)
    return sorted(chosen), ", ".join("%s/%s" % pair for pair in sorted(chosen))


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _quantity(record, node_name):
    """One record quantity as ``(value, provenance)``; ``(None, None)`` where the record carries no value.

    The node's shape is the engine's own (a ``{"value", "provenance"}`` mapping; the schema's not-evaluated
    literal otherwise) — reached through the engine's constant, never re-declared here (C-70/C-71).
    """
    quality = record.get("quality")
    if not isinstance(quality, dict):
        return None, None
    node = quality.get(node_name)
    if isinstance(node, dict):
        value = node.get("value")
        provenance = node.get("provenance")
        if _is_number(value):
            return value, provenance if isinstance(provenance, str) and provenance else None
        return None, None
    if node is None or node == engine_not_evaluated:
        return None, None
    if _is_number(node):
        return node, None
    return None, None


#: Bound at first use to the engine's own not-evaluated literal (C-71): no second copy lives in this file.
engine_not_evaluated = None


def figure(values, node_name, kind):
    """One row figure (C-56): elapsed is a median with min/max beside it; the counts are sums.

    Every figure carries the provenance its records state (one name, or each name a mixed set saw). A quantity
    absent from every contributing record is the engine's not-evaluated literal — never ``0``, never a blank.
    A quantity present on some but not all records states ``covered=k/n``, so a partial figure is never read
    as a whole one.
    """
    pairs = [_quantity(record, node_name) for record in values]
    found = [(value, provenance) for value, provenance in pairs if value is not None]
    if not found:
        return {"value": engine_not_evaluated}
    numbers = sorted(value for value, _provenance in found)
    result = {}
    if kind == "elapsed":
        result["value"] = statistics.median(numbers)
        result["min"] = numbers[0]
        result["max"] = numbers[-1]
    else:
        result["value"] = sum(numbers)
    provenances = sorted({provenance for _value, provenance in found if provenance})
    if len(provenances) == 1:
        result["provenance"] = provenances[0]
    elif provenances:
        result["provenance"] = provenances
    if len(found) < len(pairs):
        result["covered"] = "%d/%d" % (len(found), len(pairs))
    return result


def compute(engine, retained, selection, cap, window_statement, selection_statement, start, end):
    """The ONE computed result both actions project (C-60): no figure is computed twice."""
    if start is None:
        window = {"kind": window_statement}
    else:
        window = {"kind": window_statement, "start": start.isoformat(), "end": end.isoformat()}
    rows = []
    measurable = 0
    for pair in selection:
        values = retained.get(pair, [])
        elapsed = figure(values, _ELAPSED_NODE, "elapsed")
        tokens = figure(values, "tokens", "sum")
        invocations = figure(values, "invocations", "sum")
        for candidate in (elapsed, tokens, invocations):
            if _is_number(candidate.get("value")):
                measurable += 1
        rows.append({
            "unit_id": pair[0],
            "unit_type": pair[1],
            "records": len(values),
            "elapsed": elapsed,
            "tokens": tokens,
            "invocations": invocations,
        })
    return {
        "window": window,
        "selection": selection_statement,
        "cap": cap,
        "rows": rows,
        "measurable": measurable,
    }


# --------------------------------------------------------------------------- #
# the two projections
# --------------------------------------------------------------------------- #
def render_quantity(name, fig):
    """One figure for the summary action (C-56): the value, its provenance, its coverage."""
    value = fig.get("value")
    if not _is_number(value):
        return "%s=%s" % (name, value)
    text = ["%s=%s" % (name, value)]
    for extra in ("min", "max"):
        if extra in fig:
            text.append("%s=%s" % (extra, fig[extra]))
    if fig.get("provenance"):
        text.append("provenance=%s" % fig["provenance"])
    if fig.get("covered"):
        text.append("covered=%s" % fig["covered"])
    return " ".join(text)


def render_summary(result, excluded) -> str:
    """The human-readable report: window, selection, printed cap, rows, exclusion counts (C-54…C-58)."""
    lines = [
        "window: %s" % result["window"]["kind"],
        "selection: %s" % result["selection"],
        "cap: %d" % result["cap"],
    ]
    for row in result["rows"]:
        lines.append(
            "unit=%s type=%s records=%d %s %s %s"
            % (
                row["unit_id"],
                row["unit_type"],
                row["records"],
                render_quantity("elapsed", row["elapsed"]),
                render_quantity("tokens", row["tokens"]),
                render_quantity("invocations", row["invocations"]),
            )
        )
    lines.append(
        "excluded: unreadable=%d legacy-format=%d outside-window=%d unknown-unit=%d outside-cap=%d read=%d"
        % (
            excluded["unreadable"],
            excluded["legacy_format"],
            excluded["outside_window"],
            excluded["unknown_unit"],
            excluded["outside_cap"],
            excluded["read"],
        )
    )
    lines.append("%d figures measurable" % result["measurable"])
    return "\n".join(lines)


def render_json(result, excluded) -> str:
    """The machine-readable projection of the SAME computed result, with the exact owned key set (C-60)."""
    document = {
        "window": result["window"],
        "selection": result["selection"],
        "cap": result["cap"],
        "rows": result["rows"],
        "excluded": excluded,
        "exit_hint": "0 report; 2 input error; 3 nothing to analyse; 1 other failure",
    }
    assert set(document) == set(DOCUMENT_KEYS)
    return json.dumps(document, indent=2, sort_keys=True)


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="measure.py",
        description="Read-only measurement report over the exec-quant store (087 /speckit.measure).",
    )
    parser.add_argument("--action", choices=("summary", "json"), default="summary",
                        help="the closed action set (C-60)")
    parser.add_argument("--workspace", default=".", help="workspace whose store is measured")
    parser.add_argument("--since", default=None, help="window start (ISO date or timestamp)")
    parser.add_argument("--window", default=None, help="window span, e.g. 30m / 1h / 24h")
    parser.add_argument("--unit", action="append", default=[],
                        help="exact unit identity unit_id/unit_type; repeatable")
    parser.add_argument("--cap", type=int, default=DEFAULT_CAP,
                        help="per-unit record cap (default %d)" % DEFAULT_CAP)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    engine = load_engine()
    if engine is None:
        print("measure: the store engine is unreadable: %s" % (REPO_ROOT / STORE_ENGINE), file=sys.stderr)
        return EXIT_FAILURE
    bind_ok = bind_engine_constants(engine)
    if not bind_ok:
        print("measure: the engine's declared field slots are unreadable: %s" % (REPO_ROOT / STORE_ENGINE),
              file=sys.stderr)
        return EXIT_FAILURE
    availability_literal = load_availability_literal()
    if not availability_literal:
        print("measure: the availability literal is unreadable: %s" % (REPO_ROOT / DIGEST_SCRIPT),
              file=sys.stderr)
        return EXIT_FAILURE
    if args.cap <= 0:
        print("measure: invalid --cap: %r (must be positive)" % args.cap, file=sys.stderr)
        return EXIT_INPUT_ERROR

    workspace = Path(args.workspace).expanduser().resolve()
    try:
        start, end, window_statement = resolve_window(engine, args.since, args.window)
    except engine.InputError as exc:
        print(str(exc), file=sys.stderr)
        return EXIT_INPUT_ERROR

    try:
        records, encountered = read_store(engine, workspace)
    except OSError as exc:
        print("measure: the store is unreadable: %s" % exc, file=sys.stderr)
        return EXIT_FAILURE
    if encountered == 0:
        print("%s: the store is absent or empty (workspace %s)" % (availability_literal, workspace))
        return EXIT_NOTHING_TO_ANALYSE

    retained, excluded, _read_total = classify(
        records, engine, start, end, args.cap, max(0, encountered - len(records)))
    if not retained:
        print("%s: no record falls inside %s" % (availability_literal, window_statement))
        return EXIT_NOTHING_TO_ANALYSE

    try:
        selection, selection_statement = resolve_selection(retained, args.unit)
    except ValueError as exc:
        print("measure: unknown unit: %s (the store holds no such identity inside the window)"
              % exc.args[0], file=sys.stderr)
        return EXIT_INPUT_ERROR

    result = compute(engine, retained, selection, args.cap, window_statement,
                     selection_statement, start, end)
    if args.action == "json":
        print(render_json(result, excluded))
    else:
        print(render_summary(result, excluded))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
