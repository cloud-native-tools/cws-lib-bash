#!/usr/bin/env python3
"""Read-only role-edge judgement engine (Feature 095).

Rule owner: ``.specify/shared/definitions/superagent-definitions.md`` ([[STR-004]]). Executable
interface: ``contracts/role-edge-engine.contract.md`` C-1 … C-11; the parsed carrier
shapes and the violation predicates are owned by ``data-model.md`` § 2 / § 3 / § 5.

The engine answers, from existing run records only: does an edge exist between two
executors, which roles does each edge endpoint hold, how deep is each executor, and
which recorded anomaly exists. It is a projection — no store, no cache, no write point.

Carriers (read-only, no new store):

* team run-report mapping table inside ``## Execution Detail`` (``--teams-dir``);
* driver stage envelope sidecar ``prompt-<line>-<stage>.md.meta.json`` with its
  ``role_edge`` object, plus the four-piece artifact set when the sidecar is absent
  (``--state-dir``);
* ``run-agent`` dispatch record written by ``exec-quant.py --action collect-dispatch``,
  located at the store the record shape already declares — ``<state-dir>/../memory/
  exec-quant/records`` (``run-agent-label`` carrier); the child's artifact triplet
  under ``--logs-dir`` confirms the dispatch took hold;
* the line registry (``--registry-dir``) cross-checks identities only; when absent it
  is empty, never fatal.

Implementation readings disclosed here, each pinned by the guarding contract test:

* ``dispatch_duty`` and ``role_declaration`` are declared only by carriers that carry
  the field. A carrier without the field contributes the edge defaults
  ``subagent`` / ``not-granted`` (the R3-02 disposition: the exec-quant dispatch record
  carries neither field, and a ``dispatch_duty: granted`` declaration is never inferred).
* ``attempt`` is the carrier's explicit attempt identifier when it records one, else the
  literal ``1`` (a retry is a new label, so an unrecorded attempt is a single attempt).
* When the same field of one edge is declared differently by two carriers, the conflict
  row names the field and every declaring path, and the edge value comes from the
  primary carrier precedence ``team-report`` > ``driver-spine`` > ``run-agent-label``
  (parent-side records are primary per FR-003) — the choice is never silent.
* ``state`` / ``last_activity`` / ``age`` / ``stale`` are digest-view fields, not engine
  output keys (data-model § 4); the digest renders them from its existing sources.

Zero write points: this module opens no file for writing, creates no temporary file and
mutates no input. The importable interface (``read_carrier_inputs`` +
``evaluate_role_model``) is the single materialization the digest consumes.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import deque
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
# Guard: the .specify/scripts/python/ mirror copy resolves parents[2] to `.specify`
# and would project every runtime path a second level deep.
if REPO_ROOT.name == ".specify":
    REPO_ROOT = REPO_ROOT.parent

SCHEMA_VERSION = 1

DECLARED_ROLES = ("subagent", "superagent")
DUTY_VALUES = ("granted", "not-granted")
DEFAULT_ROLE = "subagent"
DEFAULT_DUTY = "not-granted"
DUAL_ROLE_MARKER = "dual-role"
ROOT_LITERAL = "root"

VIOLATION_KINDS = (
    "self-dispatch",
    "dangling-parent",
    "unbacked-role-claim",
    "depth-inconsistent",
)

CARRIER_TEAM = "team-report"
CARRIER_DRIVER = "driver-spine"
CARRIER_RUN_AGENT = "run-agent-label"
CARRIER_PRECEDENCE = {CARRIER_TEAM: 3, CARRIER_DRIVER: 2, CARRIER_RUN_AGENT: 1}

MAPPING_COLUMNS = ("label", "role", "dispatch_duty", "workspace", "parent")
ROLE_EDGE_FIELDS = (
    "parent_identity",
    "child_label",
    "role_declaration",
    "dispatch_duty",
    "depth_position",
    "authority_ref",
    "return_channel",
)
TRIPLET_SUFFIXES = (".status", ".jsonl", ".live.log")
STAGE_ARTIFACT_PREFIXES = ("pid-", "status-", "log-", "heartbeat-")
SIDECAR_SUFFIX = ".md.meta.json"
SPINE_BLOCK_RE = re.compile(
    r"<!-- loop-state:begin -->(.*?)<!-- loop-state:end -->", re.S
)
SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.M)


class RoleEdgeInputError(Exception):
    """Unreadable or malformed input; the CLI reports it as a named exit 2."""


# --------------------------------------------------------------------------- #
# small readers
# --------------------------------------------------------------------------- #
def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RoleEdgeInputError("unreadable input %s: %s" % (path, exc))


def _parse_spines(state_dir: Path) -> dict:
    spines = {}
    for path in sorted(state_dir.glob("*.md")):
        text = _read_text(path)
        match = SPINE_BLOCK_RE.search(text)
        if not match:
            continue
        fields = {}
        for line in match.group(1).splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            fields[key.strip()] = value.strip()
        run_id = fields.get("run_id")
        if not run_id:
            continue
        spines[path.stem] = {
            "path": str(path),
            "line_id": path.stem,
            "run_id": run_id,
            "attempt": fields.get("attempt") or None,
        }
    return spines


def _tables_in_execution_detail(text: str):
    """Yield ``(header_cells, [(line_number, cells), ...])`` for the section's tables."""
    in_detail = False
    block = []
    start_line = 0
    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("## "):
            if in_detail and block:
                yield _table_block(block, start_line)
                block = []
            in_detail = stripped == "## Execution Detail"
            continue
        if in_detail and stripped.startswith("|"):
            if not block:
                start_line = lineno
            block.append((lineno, stripped))
            continue
        if block:
            yield _table_block(block, start_line)
            block = []
    if block:
        yield _table_block(block, start_line)


def _table_block(block, start_line):
    header = _split_table_row(block[0][1])
    rows = []
    for lineno, line in block[1:]:
        cells = _split_table_row(line)
        if all(SEPARATOR_CELL_RE.match(cell) for cell in cells if cell):
            continue
        rows.append((lineno, cells))
    return header, rows, start_line


def _split_table_row(line: str):
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [cell.strip() for cell in text.split("|")]


def _parse_team_rows(teams_dir: Path) -> list:
    rows = []
    for path in sorted(teams_dir.glob("*/runs/*-report.md")):
        text = _read_text(path)
        for header, table_rows, _start in _tables_in_execution_detail(text):
            if tuple(header) != MAPPING_COLUMNS:
                continue
            for lineno, cells in table_rows:
                if len(cells) != len(MAPPING_COLUMNS):
                    raise RoleEdgeInputError(
                        "malformed carrier row in %s:%d: expected %d columns, found %d"
                        % (path, lineno, len(MAPPING_COLUMNS), len(cells))
                    )
                label, role, duty, _workspace, parent = cells
                if not label or not parent:
                    raise RoleEdgeInputError(
                        "malformed carrier row in %s:%d: label and parent are required"
                        % (path, lineno)
                    )
                if role not in DECLARED_ROLES:
                    raise RoleEdgeInputError(
                        "malformed carrier row in %s:%d: role %r is outside {%s}"
                        % (path, lineno, role, ", ".join(DECLARED_ROLES))
                    )
                if duty not in DUTY_VALUES:
                    raise RoleEdgeInputError(
                        "malformed carrier row in %s:%d: dispatch_duty %r is outside {%s}"
                        % (path, lineno, duty, ", ".join(DUTY_VALUES))
                    )
                rows.append(
                    {
                        "carrier": CARRIER_TEAM,
                        "path": str(path),
                        "line": lineno,
                        "parent_raw": parent,
                        "child_raw": label,
                        "attempt": "1",
                        "role_declaration": role,
                        "dispatch_duty": duty,
                        "depth_position": None,
                    }
                )
    return rows


def _line_for_stem(stem: str, line_ids) -> str:
    candidates = [
        line_id
        for line_id in line_ids
        if stem == line_id or stem.startswith(line_id + "-")
    ]
    if not candidates:
        return None
    return max(candidates, key=len)


def _parse_sidecars(state_dir: Path, spines: dict, line_ids) -> tuple:
    rows = []
    stems = set()
    for path in sorted(state_dir.glob("prompt-*" + SIDECAR_SUFFIX)):
        stem = path.name[len("prompt-") : -len(SIDECAR_SUFFIX)]
        stems.add(stem)
        text = _read_text(path)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RoleEdgeInputError("malformed carrier record %s: %s" % (path, exc))
        if not isinstance(payload, dict):
            raise RoleEdgeInputError(
                "malformed carrier record %s: top level is not an object" % (path,)
            )
        role_edge = payload.get("role_edge")
        if role_edge is None:
            continue
        if not isinstance(role_edge, dict):
            raise RoleEdgeInputError(
                "malformed carrier record %s: role_edge is not an object" % (path,)
            )
        for field in ROLE_EDGE_FIELDS:
            if field not in role_edge:
                raise RoleEdgeInputError(
                    "malformed carrier record %s: role_edge is missing %r"
                    % (path, field)
                )
        role = role_edge["role_declaration"]
        duty = role_edge["dispatch_duty"]
        depth_position = role_edge["depth_position"]
        if role not in DECLARED_ROLES:
            raise RoleEdgeInputError(
                "malformed carrier record %s: role_edge.role_declaration %r is outside {%s}"
                % (path, role, ", ".join(DECLARED_ROLES))
            )
        if duty not in DUTY_VALUES:
            raise RoleEdgeInputError(
                "malformed carrier record %s: role_edge.dispatch_duty %r is outside {%s}"
                % (path, duty, ", ".join(DUTY_VALUES))
            )
        if (
            not isinstance(depth_position, int)
            or isinstance(depth_position, bool)
            or depth_position < 0
        ):
            raise RoleEdgeInputError(
                "malformed carrier record %s: role_edge.depth_position %r is not a "
                "non-negative integer" % (path, depth_position)
            )
        parent_raw = role_edge["parent_identity"]
        child_raw = role_edge["child_label"]
        if not isinstance(parent_raw, str) or not parent_raw:
            raise RoleEdgeInputError(
                "malformed carrier record %s: role_edge.parent_identity is empty" % (path,)
            )
        if not isinstance(child_raw, str) or not child_raw:
            raise RoleEdgeInputError(
                "malformed carrier record %s: role_edge.child_label is empty" % (path,)
            )
        line_id = _line_for_stem(stem, line_ids)
        spine = spines.get(line_id) if line_id else None
        attempt = (spine or {}).get("attempt") or "1"
        rows.append(
            {
                "carrier": CARRIER_DRIVER,
                "path": str(path),
                "line": None,
                "parent_raw": parent_raw,
                "child_raw": child_raw,
                "attempt": str(attempt),
                "role_declaration": role,
                "dispatch_duty": duty,
                "depth_position": depth_position,
            }
        )
    return rows, stems


def _parse_stage_artifacts(state_dir: Path, spines: dict, line_ids, sidecar_stems) -> list:
    """Derive the edge from the four-piece artifact set when the sidecar is absent."""
    rows = []
    seen = set()
    for path in sorted(state_dir.iterdir()):
        if not path.is_file():
            continue
        prefix = next(
            (item for item in STAGE_ARTIFACT_PREFIXES if path.name.startswith(item)),
            None,
        )
        if prefix is None:
            continue
        rest = path.name[len(prefix) :]
        if rest.endswith(".log"):
            rest = rest[:-4]
        line_id = _line_for_stem(rest, line_ids)
        if line_id is None:
            continue
        stage = rest[len(line_id) :].lstrip("-")
        if not stage or rest in sidecar_stems or rest in seen:
            continue
        spine = spines.get(line_id)
        if spine is None:
            continue
        seen.add(rest)
        rows.append(
            {
                "carrier": CARRIER_DRIVER,
                "path": str(path),
                "line": None,
                "parent_raw": spine["run_id"],
                "child_raw": rest,
                "attempt": str(spine.get("attempt") or "1"),
                "role_declaration": None,
                "dispatch_duty": None,
                "depth_position": None,
            }
        )
    return rows


def _scan_triplets(logs_dir: Path) -> dict:
    labels = {}
    for path in sorted(logs_dir.iterdir()):
        if not path.is_file():
            continue
        for suffix in TRIPLET_SUFFIXES:
            if path.name.endswith(suffix):
                label = path.name[: -len(suffix)]
                labels.setdefault(label, []).append(str(path))
                break
    return labels


def _parse_registry(registry_dir) -> tuple:
    if registry_dir is None:
        return [], "absent", [], []
    directory = Path(registry_dir)
    if not directory.is_dir():
        return [], "absent", [], []
    entries = []
    unreadable = []
    payloads = []
    for path in sorted(directory.glob("*.json")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            unreadable.append(str(path))
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            unreadable.append(str(path))
            continue
        if not isinstance(payload, dict):
            unreadable.append(str(path))
            continue
        # The parsed payload rides the same read: the digest's legacy line rows derive from it, so the registry
        # root is read once and both views (line rows, role cross-check) consume that one pass.
        payloads.append({"path": str(path), "payload": payload})
        line_id = payload.get("line_id")
        if not isinstance(line_id, str) or not line_id:
            continue
        entries.append({"path": str(path), "line_id": line_id})
    return entries, "present", unreadable, payloads


def _parse_dispatch_records(state_dir: Path, triplet_labels) -> tuple:
    store = state_dir.parent / "memory" / "exec-quant" / "records"
    rows = []
    unconfirmed = 0
    if not store.is_dir():
        return rows, False, unconfirmed, str(store)
    for path in sorted(store.glob("*.json")):
        text = _read_text(path)
        try:
            record = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RoleEdgeInputError("malformed carrier record %s: %s" % (path, exc))
        if not isinstance(record, dict):
            raise RoleEdgeInputError(
                "malformed carrier record %s: top level is not an object" % (path,)
            )
        if record.get("unit_type") != "agent":
            continue
        unit_id = record.get("unit_id")
        label = record.get("run_id")
        if not isinstance(unit_id, str) or not unit_id.startswith("agent:"):
            continue
        if not isinstance(label, str) or not label:
            raise RoleEdgeInputError(
                "malformed carrier record %s: run_id is missing" % (path,)
            )
        if label not in triplet_labels:
            unconfirmed += 1
            continue
        rows.append(
            {
                "carrier": CARRIER_RUN_AGENT,
                "path": str(path),
                "line": None,
                "parent_raw": unit_id[len("agent:") :],
                "child_raw": label,
                "attempt": "1",
                "role_declaration": None,
                "dispatch_duty": None,
                "depth_position": None,
            }
        )
    return rows, True, unconfirmed, str(store)


def _default_registry_dir():
    """Ask the owning engine for the default registry root; never restate its chain."""
    candidates = (
        REPO_ROOT / "skills" / "external" / "sdd-loop-driver" / "scripts" / "line-registry.py",
        REPO_ROOT / ".specify" / "skills" / "sdd-loop-driver" / "scripts" / "line-registry.py",
    )
    for engine in candidates:
        if not engine.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location(
                "line_registry_owner", str(engine)
            )
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            resolver = getattr(module, "resolve_registry_dir", None)
            if resolver is None:
                return None
            return resolver()
        except Exception:  # an unreadable owner narrows cross-checking, never fatal
            return None
    return None


# --------------------------------------------------------------------------- #
# importable interface (contract C-1)
# --------------------------------------------------------------------------- #
def read_carrier_inputs(*, state_dir, teams_dir, logs_dir, registry_dir=None) -> dict:
    """Parse the three carrier forms plus the registry cross-check into one snapshot."""
    state_path = Path(state_dir)
    teams_path = Path(teams_dir)
    logs_path = Path(logs_dir)
    for option, path in (
        ("--state-dir", state_path),
        ("--teams-dir", teams_path),
        ("--logs-dir", logs_path),
    ):
        if not path.is_dir():
            raise RoleEdgeInputError(
                "required root %s is missing or not a directory: %s" % (option, path)
            )

    resolved_registry = registry_dir if registry_dir is not None else _default_registry_dir()
    registry_entries, registry_state, registry_unreadable, registry_payloads = _parse_registry(
        resolved_registry
    )
    triplets = _scan_triplets(logs_path)
    spines = _parse_spines(state_path)
    line_ids = set(spines) | {entry["line_id"] for entry in registry_entries}

    team_rows = _parse_team_rows(teams_path)
    sidecar_rows, sidecar_stems = _parse_sidecars(state_path, spines, line_ids)
    artifact_rows = _parse_stage_artifacts(state_path, spines, line_ids, sidecar_stems)
    dispatch_rows, store_present, unconfirmed, store_path = _parse_dispatch_records(
        state_path, set(triplets)
    )

    return {
        "roots": {
            "state_dir": str(state_dir),
            "teams_dir": str(teams_dir),
            "logs_dir": str(logs_dir),
            "registry_dir": None if resolved_registry is None else str(resolved_registry),
            "registry": registry_state,
            "dispatch_store": store_path,
            "dispatch_store_present": store_present,
        },
        "rows": team_rows + sidecar_rows + artifact_rows + dispatch_rows,
        "spines": spines,
        "line_ids": sorted(line_ids),
        "run_ids": sorted({spine["run_id"] for spine in spines.values()}),
        "registry_entries": registry_entries,
        # The same read's parsed payloads, consumed by ``status-digest.py`` for its legacy line rows — one
        # registry read feeds both the role cross-check and the line projection (digest contract C-1).
        "registry_payloads": registry_payloads,
        "triplets": sorted(triplets),
        "carrier_rows": {
            CARRIER_TEAM: len(team_rows),
            CARRIER_DRIVER: len(sidecar_rows) + len(artifact_rows),
            CARRIER_RUN_AGENT: len(dispatch_rows),
        },
        "notes": {
            "registry_unreadable": len(registry_unreadable),
            "registry_unreadable_paths": registry_unreadable,
            "unconfirmed_dispatch_records": unconfirmed,
        },
    }


def _resolve_identity(raw: str, inputs: dict):
    """data-model § 3: label → line id → spine run_id → literal root → dangling."""
    raw = str(raw)
    if raw in {row["child_raw"] for row in inputs["rows"]}:
        return raw
    if raw in set(inputs["line_ids"]):
        return raw
    if raw in set(inputs["run_ids"]):
        return raw
    if raw == ROOT_LITERAL:
        return raw
    return None


def _roles_for(is_parent: bool, is_child: bool) -> list:
    roles = []
    if is_parent:
        roles.append("superagent")
    if is_child:
        roles.append("subagent")
    return sorted(roles)


def _primary_row(group: list) -> dict:
    def key(row):
        line = row["line"] if row["line"] is not None else 0
        return (-CARRIER_PRECEDENCE.get(row["carrier"], 0), row["path"], line)

    return sorted(group, key=key)[0]


def _input_snapshot(inputs: dict) -> dict:
    roots = inputs["roots"]
    return {
        "state_dir": roots["state_dir"],
        "teams_dir": roots["teams_dir"],
        "logs_dir": roots["logs_dir"],
        "registry_dir": roots["registry_dir"],
        "registry": roots["registry"],
        "dispatch_store": roots["dispatch_store"],
        "dispatch_store_present": roots["dispatch_store_present"],
        "spines": len(inputs["spines"]),
        "registry_entries": len(inputs["registry_entries"]),
        "triplets": len(inputs["triplets"]),
        "carrier_rows": dict(inputs["carrier_rows"]),
        "registry_unreadable": inputs["notes"]["registry_unreadable"],
        "unconfirmed_dispatch_records": inputs["notes"]["unconfirmed_dispatch_records"],
    }


def evaluate_role_model(inputs: dict) -> dict:
    """Judge the parsed snapshot into the report model (contract C-3)."""
    rows = inputs["rows"]
    violated_paths = {}

    def add_violation(kind, subjects, paths):
        key = (kind, tuple(sorted(subjects)))
        violated_paths.setdefault(key, set()).update(paths)

    edge_groups = {}
    dangling_rows = []
    for row in rows:
        parent = _resolve_identity(row["parent_raw"], inputs)
        if parent is None:
            add_violation(
                "dangling-parent",
                [row["parent_raw"], row["child_raw"]],
                [row["path"]],
            )
            dangling_rows.append(row)
            continue
        key = (parent, row["child_raw"], str(row["attempt"]))
        edge_groups.setdefault(key, []).append(row)
        if parent == row["child_raw"]:
            add_violation("self-dispatch", [row["child_raw"]], [row["path"]])

    edges = []
    conflicts = []
    for key in sorted(edge_groups):
        group = edge_groups[key]
        chosen = _primary_row(group)
        for field in ("role_declaration", "dispatch_duty", "depth_position"):
            declared = [(row[field], row["path"]) for row in group if row[field] is not None]
            if len({value for value, _path in declared}) > 1:
                conflicts.append(
                    {
                        "field": field,
                        "paths": sorted({path for _value, path in declared}),
                        "edge": {
                            "parent": key[0],
                            "child": key[1],
                            "attempt": key[2],
                        },
                    }
                )
        edges.append(
            {
                "parent": key[0],
                "child": key[1],
                "attempt": key[2],
                "role_declaration": chosen["role_declaration"] or DEFAULT_ROLE,
                "dispatch_duty": chosen["dispatch_duty"] or DEFAULT_DUTY,
                "depth": None,
                "source": {
                    "carrier": chosen["carrier"],
                    "path": chosen["path"],
                    "line": chosen["line"],
                },
            }
        )

    parents = {key[0] for key in edge_groups}
    children = {key[1] for key in edge_groups}
    dangling_children = {row["child_raw"] for row in dangling_rows}

    adjacency = {}
    incoming = {}
    for key in sorted(edge_groups):
        adjacency.setdefault(key[0], set()).add(key[1])
        incoming.setdefault(key[1], []).append((key[0], key[2]))

    roots = sorted(
        node
        for node in (parents | children)
        if node not in incoming and node not in dangling_children
    )
    depth = {}
    queue = deque()
    for node in roots:
        depth[node] = 0
        queue.append(node)
    while queue:
        node = queue.popleft()
        for child in sorted(adjacency.get(node, ())):
            if child not in depth:
                depth[child] = depth[node] + 1
                queue.append(child)

    # A cycle detached from every root makes depth unresolvable (data-model § 5).
    def reachable(start, skip_direct_self):
        seen = set()
        frontier = [start]
        while frontier:
            node = frontier.pop()
            for child in adjacency.get(node, ()):
                if skip_direct_self and node == start and child == start:
                    continue
                if child not in seen:
                    seen.add(child)
                    frontier.append(child)
        return seen

    cycle_nodes = set()
    for node in sorted((parents | children) - set(depth)):
        if node in reachable(node, skip_direct_self=True):
            cycle_nodes.add(node)

    remaining = set(cycle_nodes)
    while remaining:
        seed = sorted(remaining)[0]
        component = {seed}
        frontier = [seed]
        while frontier:
            node = frontier.pop()
            neighbours = set(adjacency.get(node, ()))
            for other in cycle_nodes:
                if node in adjacency.get(other, ()):
                    neighbours.add(other)
            for other in neighbours:
                if other in cycle_nodes and other not in component:
                    component.add(other)
                    frontier.append(other)
        remaining -= component
        paths = sorted(
            {
                row["path"]
                for key, group in edge_groups.items()
                if key[0] in component and key[1] in component
                for row in group
            }
        )
        add_violation("depth-inconsistent", sorted(component), paths)

    for row in rows:
        if row["depth_position"] is None:
            continue
        if _resolve_identity(row["parent_raw"], inputs) is None:
            continue
        node = row["child_raw"]
        computed = depth.get(node)
        if computed is None or computed != row["depth_position"]:
            add_violation("depth-inconsistent", [node], [row["path"]])

    for row in rows:
        if row["role_declaration"] != "superagent":
            continue
        node = row["child_raw"]
        if node not in parents:
            add_violation("unbacked-role-claim", [node], [row["path"]])

    executor_ids = parents | children | dangling_children
    executors = []
    for node in sorted(executor_ids):
        is_parent = node in parents
        is_child = node in children or node in dangling_children
        roles = _roles_for(is_parent, is_child)
        marker = DUAL_ROLE_MARKER if roles == ["subagent", "superagent"] else None
        incoming_edges = sorted(incoming.get(node, []))
        sources = set()
        for key, group in edge_groups.items():
            if node in (key[0], key[1]):
                for row in group:
                    sources.add((row["carrier"], row["path"], row["line"]))
        for row in dangling_rows:
            if row["child_raw"] == node:
                sources.add((row["carrier"], row["path"], row["line"]))
        executors.append(
            {
                "id": node,
                "parent": incoming_edges[0][0] if incoming_edges else None,
                "roles": roles,
                "role_set_marker": marker,
                "depth": depth.get(node),
                "sources": [
                    {"carrier": carrier, "path": path, "line": line}
                    for carrier, path, line in sorted(
                        sources,
                        key=lambda item: (
                            item[0],
                            item[1],
                            -1 if item[2] is None else item[2],
                        ),
                    )
                ],
            }
        )

    for edge in edges:
        edge["depth"] = depth.get(edge["child"])

    violations = [
        {"kind": kind, "subjects": list(subjects), "paths": sorted(paths)}
        for (kind, subjects), paths in violated_paths.items()
    ]
    violations.sort(key=lambda row: (row["kind"], row["subjects"]))
    conflicts.sort(
        key=lambda row: (
            row["field"],
            row["edge"]["parent"],
            row["edge"]["child"],
            row["edge"]["attempt"],
        )
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "action": "report",
        "inputs": _input_snapshot(inputs),
        "roots": roots,
        "executors": executors,
        "edges": edges,
        "violations": violations,
        "conflicts": conflicts,
        "summary": {
            "edges": len(edges),
            "executors": len(executors),
            "violations": len(violations),
            "conflicts": len(conflicts),
        },
    }


def build_query_answer(model: dict, inputs: dict, parent_arg: str, child_arg: str) -> dict:
    """Answer one pair query (contract C-4); unknown queried identities are exit 2."""
    executors = {entry["id"]: entry for entry in model["executors"]}

    def resolve(option, value):
        identity = _resolve_identity(value, inputs)
        if identity is None or identity not in executors:
            raise RoleEdgeInputError(
                "%s %r does not resolve to a known executor" % (option, value)
            )
        return identity

    parent_id = resolve("--parent", parent_arg)
    child_id = resolve("--child", child_arg)
    edge = next(
        (
            item
            for item in model["edges"]
            if item["parent"] == parent_id and item["child"] == child_id
        ),
        None,
    )

    def view(entry):
        return {
            "id": entry["id"],
            "roles": entry["roles"],
            "role_set_marker": entry["role_set_marker"],
            "depth": entry["depth"],
        }

    violations = [
        row
        for row in model["violations"]
        if parent_id in row["subjects"] or child_id in row["subjects"]
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "action": "query",
        "edge_exists": edge is not None,
        "edge": edge,
        "parent": view(executors[parent_id]),
        "child": view(executors[child_id]),
        "violations": violations,
    }


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #
def _dash(value):
    return "-" if value is None else value


def _edge_line(edge: dict) -> str:
    return (
        "edge parent=%s child=%s attempt=%s role_declaration=%s dispatch_duty=%s "
        "depth=%s source=%s:%s"
        % (
            edge["parent"],
            edge["child"],
            edge["attempt"],
            edge["role_declaration"],
            edge["dispatch_duty"],
            _dash(edge["depth"]),
            edge["source"]["carrier"],
            edge["source"]["path"],
        )
    )


def _violation_line(row: dict) -> str:
    return "violation kind=%s subjects=%s paths=%s" % (
        row["kind"],
        ",".join(row["subjects"]),
        ",".join(row["paths"]),
    )


def render(payload: dict, output_format: str) -> None:
    if output_format == "json":
        sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        return
    lines = []
    if payload.get("action") == "query":
        lines.append("edge_exists=%s" % ("true" if payload["edge_exists"] else "false"))
        if payload.get("edge") is not None:
            lines.append(_edge_line(payload["edge"]))
    else:
        for edge in payload["edges"]:
            lines.append(_edge_line(edge))
    for row in payload["violations"]:
        lines.append(_violation_line(row))
    if payload.get("action") == "report":
        summary = payload["summary"]
        lines.append(
            "summary edges=%d executors=%d violations=%d conflicts=%d"
            % (
                summary["edges"],
                summary["executors"],
                summary["violations"],
                summary["conflicts"],
            )
        )
    sys.stdout.write("\n".join(lines) + "\n")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _framework_version() -> str:
    current = Path(__file__).resolve().parent
    for candidate in [current] + list(current.parents):
        if not (candidate / ".git").exists():
            continue
        pyproject = candidate / "pyproject.toml"
        try:
            text = pyproject.read_text(encoding="utf-8")
        except OSError:
            return "unknown"
        match = VERSION_RE.search(text)
        return match.group(1) if match else "unknown"
    return "unknown"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="role-edge-check.py",
        description=(
            "Read-only role-edge judgement over existing run records: edge existence, "
            "per-edge roles, role sets, depth and the closed four violation kinds."
        ),
        epilog=(
            "Side effects: read-only; no file is written and no temporary file is "
            "created.\n"
            "Exit codes: 0 judged clean (an empty edge set is explicitly summarized); "
            "1 violations found; 2 unreadable or malformed input."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version="role-edge-check.py " + _framework_version(),
    )
    parser.add_argument("--action", choices=("report", "query"), default="report")
    parser.add_argument("--parent", help="query: parent identity")
    parser.add_argument("--child", help="query: child identity")
    parser.add_argument("--state-dir", default=".specify/state")
    parser.add_argument("--teams-dir", default=".specify/teams")
    parser.add_argument("--logs-dir", default=".specify/agents/execution/logs")
    parser.add_argument(
        "--registry-dir",
        default=None,
        help="line-registry cross-check root (default: the owning engine's resolution)",
    )
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.action == "query" and (not args.parent or not args.child):
            raise RoleEdgeInputError(
                "--action query requires both --parent and --child"
            )
        inputs = read_carrier_inputs(
            state_dir=args.state_dir,
            teams_dir=args.teams_dir,
            logs_dir=args.logs_dir,
            registry_dir=args.registry_dir,
        )
        model = evaluate_role_model(inputs)
        payload = (
            build_query_answer(model, inputs, args.parent, args.child)
            if args.action == "query"
            else model
        )
    except RoleEdgeInputError as exc:
        sys.stderr.write("role-edge-check.py: error: %s\n" % exc)
        return 2
    render(payload, args.format)
    return 1 if payload["violations"] else 0


if __name__ == "__main__":
    sys.exit(main())
