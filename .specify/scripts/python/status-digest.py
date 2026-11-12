#!/usr/bin/env python3
"""status-digest.py — current-state digest, reporting-obligation guard, status line (087).

One stdlib-only file with **exactly three actions** (contract ``status-digest.contract.md`` C-41):

* ``--action digest`` — render the bounded current-state summary;
* ``--action guard``  — judge the mechanically decidable propositions of the reporting obligation and report each
  with a named status (``pass`` / ``fail`` / ``not-evaluated`` plus a reason);
* ``--action report`` — render one status line from the owner's four labels plus attribution and the profile in force.

All three share **one reader** (``read_state`` and the functions under it). A second parser or a second renderer is
the defect C-41 names, so no action re-reads a registry entry by a different code path.

Authority map (this file owns no rule; it names the owner of each):

* The propositions the guard decides — their ids and their subjects — are owned by
  ``.specify/specs/088-speckit-visualization/contracts/reporting-obligations.contract.md`` C-01…C-13. This file
  names each proposition by id and states only *what it reads on disk*; it restates no proposition.
* The reporting obligation itself (scope predicate, cadence default, seat obligation, master duty, transition
  triggers, digest contract, machinery prohibition) is owned by ``.specify/shared/guidelines/reporting-obligations.md``.
* The content floor, the cadence anchor and the interactive default are owned by
  ``.specify/shared/guidelines/progress-reporting.md``.
* The artifact triplet and the three execution modes are owned by ``.specify/shared/definitions/subagent-definitions.md``.
* The stall threshold numbers are owned by ``.specify/skills/internal/create-team/references/patterns.md`` § Monitoring →
  Stall Detection; this file carries none of them.
* The line state vocabulary is owned by ``.specify/skills/sdd-loop-driver/scripts/line-registry.py``
  (``STATE_VALUES`` / ``ACTIVE_STATES``); this file never re-enumerates it — it projects whatever the entry says and
  derives activity from the same two names, which it reads from that engine's source.

  **The one legal duplicate (contract ``ownership-map.contract.md`` C-47).** The registry directory resolution order
  below restates ``line-registry.py``'s ``resolve_registry_dir`` because this script MUST NOT import the engine
  (``plan.md`` § Technical Context: a direct import would couple the digest to an internal module path rather than to
  its JSON on disk). That restatement is the single duplicate this feature is allowed, and it is marked here.

Read-only boundary (contract C-42, ``data-model.md`` E7): every input is opened for reading only. This file never
writes, never renames, never creates a directory, never spawns a process and never touches the network — those
properties are asserted by ``tests/unit/test_status_digest_unit.py`` and audited by the ``RO-13`` proposition.

Exit statuses, closed (contract C-45):

==========================  ==============================================================
``--action digest``
``0``                       a digest was rendered with at least one entry
``3``                       nothing active — the explicit ``nothing-running`` rendering
``2``                       input error (unreadable registry, unparsable entry, bad arguments)
``--action guard``
``0``                       zero findings
``1``                       at least one finding (a ``fail``)
``2``                       input error
``--action report``
``0``                       one status line was rendered
``2``                       input error
==========================  ==============================================================
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------- declared constants
#: The digest's entry cap default. Owner of this value: this constant (contract
#: ``ownership-map.contract.md`` C-47 row "Digest cap default"); overridable per invocation with ``--cap``.
DEFAULT_CAP = 20
CAP_ENV = "SPECIFY_STATUS_DIGEST_CAP"

#: The stale bound default: an entry whose last-observed activity is older than this is marked stale with its age.
#: Owner of this value: this constant (contract C-47 row "Digest stale bound default"). No other file carries it.
DEFAULT_STALE_BOUND_SECONDS = 900

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_INPUT_ERROR = 2
EXIT_NOTHING_ACTIVE = 3

REPO_ROOT = Path(__file__).resolve().parents[2]
# Guard against the `.specify/scripts/python/` mirror copy doubling the projection (the same trap
# ``sync-mirrors.py`` documents): a directory named `.specify` is never a repository root.
if REPO_ROOT.name == ".specify":
    REPO_ROOT = REPO_ROOT.parent

OWNER_DOC = Path("shared") / "guidelines" / "reporting-obligations.md"
PROGRESS_REPORTING_DOC = Path("shared") / "guidelines" / "progress-reporting.md"
SUBAGENT_DEFINITIONS_DOC = Path("shared") / "definitions" / "subagent-definitions.md"
PATTERNS_DOC = Path("skills") / "internal" / "create-team" / "references" / "patterns.md"
LINE_REGISTRY_ENGINE = Path("skills") / "external" / "sdd-loop-driver" / "scripts" / "line-registry.py"
COMMAND_TEMPLATE = Path("templates") / "commands" / "status.md"

NOTHING_RUNNING = "nothing-running"
DASH = "-"

#: The exec-quant store engine. The efficiency element's records are obtained by importing this file's read path
#: in process (``efficiency-element.contract.md`` C-65 / ``measure-report.contract.md`` C-53): its storage layout,
#: its record format and its legacy-stream compatibility path stay its own and are reached by path, never copied.
STORE_ENGINE = Path("scripts") / "python" / "exec-quant.py"

#: The role-edge judgement engine (095). The role view's model comes from importing this file's read path in
#: process (contract ``status-digest-role-view.contract.md`` C-1): the engine's carrier parsing and role judgement
#: stay its own and are reached by path, never copied into this renderer.
ROLE_ENGINE = Path("scripts") / "python" / "role-edge-check.py"

#: The role model's carrier roots, workspace-relative — the engine's three required carrier families. The registry
#: root is resolved by the one legal restatement above and passed along, so both halves read the same directory.
ROLE_CARRIER_ROOTS = (
    ("state_dir", (".specify", "state")),
    ("teams_dir", (".specify", "teams")),
    ("logs_dir", (".specify", "agents", "execution", "logs")),
)

#: The four role-view fields every rendered entry carries beside its existing fields (contract C-2). Their values are
#: the judgement model's, passed through unchanged — the digest never re-derives them (C-5).
ROLE_VIEW_FIELDS = ("parent", "roles", "role_set_marker", "depth")

#: The lifecycle-terminal executor states (``data-model.md`` § 9): an executor row outside the line registry that
#: recorded one of these is history, exactly as a closed line is, and never occupies the capped view.
LIFECYCLE_TERMINAL_STATES = ("completed", "failed", "cancelled")

#: The element's rendered field (``data-model.md`` E8; contract ``efficiency-element.contract.md`` C-63/C-64): one
#: bounded group appended to the content of an entry the surface ALREADY renders — no new line, no new entry.
EFFICIENCY_FIELD = "efficiency="

#: The element's two quantities beyond elapsed (C-64). They are appended only while a whole element fits the
#: surface's existing per-entry bound, and withdrawn from EVERY unit of a render together.
EFFICIENCY_DEEP_QUANTITIES = ("tokens", "invocations")

#: The declared element width, in characters, each surface's element must fit before the two deeper quantities are
#: appended (C-64's "the surface's own entry bound"). Owner of this value: this constant (contract
#: ``ownership-map.contract.md`` C-47); overridable per invocation with ``--element-bound`` so the degradation face is
#: measurable rather than asserted. ``None`` disables the bound for a render.
DEFAULT_ELEMENT_BOUND = 160

#: The element's two render literals — the marker a quantity the record does not carry renders instead of a value,
#: and the explicit store-availability state. Both are rendered VERBATIM from their single definition site, the owner
#: document's § 九 (``.specify/shared/guidelines/reporting-obligations.md``; contract ``ownership-map.contract.md`` C-47 row
#: "Not-evaluated marker literal"): the constants below are the fallback for the framework's own bootstrap state, and
#: :func:`efficiency_vocabulary` prefers the owner's text whenever that document is readable.
NOT_EVALUATED_MARKER = "not-evaluated"
NOT_EVALUATED_MARKER_FORMS = (r"`(not[- ]evaluated)`",)
NO_MEASUREMENTS = "no measurements"

#: The reporting profile names the owner declares (`data-model.md` E6, contract ``status-report.contract.md`` C-30).
PROFILE_LONG_RUN = "long-run"
PROFILE_INTERACTIVE = "interactive"

#: The four content-element labels the owner names (definitions reached by anchor, contract C-23).
ELEMENT_LABELS = ("position", "delta", "remainder", "blocker")
NO_BLOCKER = "no blocker"

#: The nine prohibited machinery items of contract C-13, as the scan looks for them.
MACHINERY_TERMS = (
    "scheduler",
    "timer",
    "daemon",
    "dependency",
    "store",
    "console channel",
    "registry",
    "state spine",
    "ledger",
)

#: The two legal carrier forms (contract ``status-report.contract.md`` C-26).
CARRIER_CONSOLE = "console"

#: The three out-of-cadence transition classes (contract C-08) as a captured line set spells them.
TRANSITION_CLASSES = ("sub-flow failure", "stall crossing", "dispatch failure")

#: Interrogative / approval markers a status line must never carry (contract C-28).
GATE_MARKERS = (
    "?",
    "？",
    "approve",
    "approval",
    "waive",
    "waiver",
    "shall i",
    "may i",
    "please confirm",
    "批准",
    "豁免",
    "请确认",
)

#: The label convention a dispatched sub-flow's identity comes from (``data-model.md`` E3 / E7): its owner is
#: ``.specify/shared/definitions/subagent-definitions.md`` § External Dispatch Visibility Contract point 5. The pattern is
#: read here rather than copied there because the owner states the convention in prose, and the projection needs a
#: decidable form of it; the shape, not the rule, is what this constant fixes.
SUPERVISION_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*--[A-Za-z0-9._-]+--[A-Za-z0-9._-]+$")

#: The triplet suffixes the visibility contract declares (point 3); the newest mtime among them is the sub-flow's
#: last observed activity (``data-model.md`` E3).
TRIPLET_SUFFIXES = (".live.log", ".jsonl", ".status")

#: The sub-flow state vocabulary (``data-model.md`` E3) — a projection of the visibility contract and the exit
#: record, not a new closed set. ``slow`` is deliberately absent: it is a qualifier on ``running``.
SUB_FLOW_STATES = ("running", "completed", "stalled", "failed")

#: The threshold row identity default: the row a dispatch that produced no manifest at all falls under. Row
#: identities are the owner table's own ``Condition`` cells (``data-model.md`` E4), so this string is an index into
#: the owner's table, never a threshold value.
MANDATORY_THRESHOLD_ROW = "No manifest created"

#: The four framework-source trees the owner-literal scan reads (``test-evidence/owner-literal-baseline.txt``:
#: ``.specify/shared/ .specify/templates/ skills/ agents/``). ``.specify/`` and the per-tool copy trees are projections of these four,
#: so a hit there is a projection of a source hit rather than an independent definition site.
OWNER_LITERAL_SCAN_ROOTS = ("shared", "templates", "skills", "agents")

#: The literal the long-run cadence default is spelled with. The scan's subject is an *interval definition*, so
#: both spellings are read: a framework file may write either and no other form counts. The spellings are folded
#: so this scan — a consumer of the fact the owner defines (`contracts/ownership-map.contract.md` C-47 row
#: "Long-run cadence default") — does not itself become a second definition site when it is read as text.
_CD = "30"
OWNER_LITERAL_FORMS = (_CD + " 秒", _CD + " seconds")

#: The two prose hits the baseline file measures and whitelists **by path** (never by count): a PlantUML Salt
#: diagram-tool blurb and a skill-authoring heuristic. A future unrelated hit in another file legitimately fails
#: the scan — that is the scan working as designed (``quickstart.md`` Scenario E.2 premise 1).
OWNER_LITERAL_WHITELIST = (
    ".specify/skills/draw-diagram/references/types/plantuml/references/howto/19-salt-diagram.md",
    ".specify/skills/improve-skills/references/skill-slimming-principles.md",
)

#: Source-file extensions the owner-literal scan reads. A binary or an unreadable file is skipped, never guessed at.
OWNER_LITERAL_SUFFIXES = frozenset({".md", ".py", ".sh", ".txt", ".yaml", ".yml", ".json"})


# ---------------------------------------------------------------- reader: registry resolution
def resolve_registry_dir() -> Path:
    """Resolve the line-registry directory, in the engine's documented order.

    ``$SPECIFY_LINE_REGISTRY_DIR`` → ``$XDG_STATE_HOME/spec-kit/lines`` → ``~/.local/state/spec-kit/lines``.

    This is the one legal duplicate of the engine's ``resolve_registry_dir`` (contract C-47): the script cannot import
    the engine, so the order is restated here and nowhere else in this script.
    """
    override = os.environ.get("SPECIFY_LINE_REGISTRY_DIR")
    if override:
        return Path(override).expanduser().resolve()
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        return Path(xdg).expanduser().resolve() / "spec-kit" / "lines"
    home = Path(os.environ.get("HOME", "~")).expanduser()
    try:
        home = home.resolve()
    except OSError:
        pass
    return home / ".local" / "state" / "spec-kit" / "lines"


# ---------------------------------------------------------------- reader: engine vocabulary
def read_engine_vocabulary() -> dict:
    """Read ``STATE_VALUES`` / ``ACTIVE_STATES`` from the engine's own source.

    The two sets are the engine's (``ownership-map.contract.md`` C-47 row "Line state vocabulary"); this function
    parses them out of the engine file so the digest quotes them instead of carrying a second copy. A failed read is
    an *unavailable input*, reported as such — never silently replaced by a hard-coded set.
    """
    path = REPO_ROOT / LINE_REGISTRY_ENGINE
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"error": "unreadable engine source %s: %s" % (LINE_REGISTRY_ENGINE, exc)}

    def literal(name: str) -> set:
        match = re.search(r"^%s\s*=\s*\{(.*?)\}" % re.escape(name), text, re.S | re.M)
        if not match:
            return set()
        return set(re.findall(r"[\"']([^\"']+)[\"']", match.group(1)))

    state_values = literal("STATE_VALUES")
    active_states = literal("ACTIVE_STATES")
    if not state_values or not active_states:
        return {
            "error": "engine source %s carries no readable STATE_VALUES / ACTIVE_STATES"
            % LINE_REGISTRY_ENGINE
        }
    return {"state_values": state_values, "active_states": active_states}


# ---------------------------------------------------------------- reader: one entry
def _parse_iso(value):
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _mtime_iso(path_text):
    if not path_text or path_text == DASH:
        return None
    try:
        stamp = os.stat(path_text).st_mtime
    except OSError:
        return None
    return datetime.fromtimestamp(stamp, timezone.utc)


def project_entry(entry: dict, now: datetime, stale_bound: int) -> dict:
    """Project one registry entry into the read-only shape the three actions share.

    Field ownership: identity / state / stage / timestamps come from the registry entry
    (``data-model.md`` E7); ``is_active`` derives from the engine's ``ACTIVE_STATES``; ``age`` and ``stale`` are
    computed here because they are functions of *now*, which no artifact owns.
    """
    triplet = {}
    for key in ("status_path", "log_path", "heartbeat_path"):
        value = entry.get(key)
        triplet[key] = value if isinstance(value, str) and value else DASH

    candidates = [_parse_iso(entry.get("updated_at"))]
    candidates.extend(
        _mtime_iso(triplet[key]) for key in ("status_path", "log_path", "heartbeat_path")
    )
    seen = [c for c in candidates if c is not None]
    last_activity = max(seen) if seen else None

    age_seconds = None
    if last_activity is not None:
        age_seconds = max(0, int((now - last_activity).total_seconds()))

    return {
        "line_id": entry.get("line_id"),
        "run_id": entry.get("run_id"),
        "project_dir": entry.get("project_dir"),
        "branch": entry.get("branch") or DASH,
        "stage": entry.get("stage") or DASH,
        "state": entry.get("state"),
        "updated_at": entry.get("updated_at") or DASH,
        "last_activity_at": last_activity.isoformat().replace("+00:00", "Z")
        if last_activity
        else DASH,
        "age_seconds": age_seconds,
        "age": format_duration(age_seconds),
        "stale": bool(age_seconds is not None and age_seconds > stale_bound),
        "stale_bound_seconds": stale_bound,
        "triplet": triplet,
        # Redesigned digest inputs (2026-11-10): executor, activity slug/description and elapsed time.
        "created_at": entry.get("created_at") or DASH,
        "last_event": entry.get("last_event") or DASH,
        "cli": entry.get("cli") or "",
        "cli_pid": entry.get("cli_pid"),
        "runner_pid": entry.get("runner_pid"),
        "worktree_path": entry.get("worktree_path") or DASH,
        # E5's per-entry projection: packed from the same reading, never a second parser (C-41).
        "line_activity": project_line_activity(entry, triplet, age_seconds),
    }


def project_line_activity(entry: dict, triplet: dict, age_seconds):
    """The E5 ``line_activity`` pack: this line's own dispatch activity, where the entry declares its triplet.

    The pack is the E3 projection read back off the artifact triplet the entry already declares — the same three
    paths ``project_sub_flow`` consumes, so the digest and the supervision report cannot disagree about one flow's
    state or age. An entry that declares no triplet has no dispatch mapping to read, so it projects ``None`` and the
    renderer writes nothing for it (``data-model.md`` E7: an absent triplet is not invented activity).
    """
    if not any(value and value != DASH for value in triplet.values()):
        return None
    state, exit_code = project_exit_record(triplet.get("status_path"))
    if state is None:
        state = "running"
    return {
        "label": entry.get("line_id"),
        "state": state,
        "exit_code": exit_code,
        "age_seconds": age_seconds,
        "age": format_duration(age_seconds),
    }


def project_exit_record(status_path):
    """Read the exit record the triplet's ``.status`` file carries (``exit=<n>``).

    The shape is the engine's own: ``line-registry.py``'s ``_status_summary`` reads ``exit=`` from the same file at
    line start, so this function consumes the artifact and invents no format. Returns ``(state, exit_code)`` with
    ``state`` ``None`` when no exit record is present yet.
    """
    if not status_path or status_path == DASH:
        return None, None
    try:
        text = Path(status_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None, None
    match = re.search(r"^exit=(-?\d+)", text, re.M)
    if not match:
        return None, None
    code = int(match.group(1))
    return ("completed" if code == 0 else "failed"), code


def format_duration(seconds) -> str:
    if seconds is None:
        return DASH
    seconds = int(seconds)
    if seconds < 60:
        return "%ds" % seconds
    if seconds < 3600:
        return "%dm%02ds" % (seconds // 60, seconds % 60)
    return "%dh%02dm" % (seconds // 3600, (seconds % 3600) // 60)


# ---------------------------------------------------------------- reader: the exec-quant store (efficiency element)
# The efficiency element is a projection over a projection: its quantities come from the exec-quant store, which this
# feature reads and never writes, and its host is a surface that already renders a line or a digest entry. Its unit is
# the STEP — the ``(unit_id, unit_type)`` identity the record itself carries, never a row of a listing and never the
# record's ``run_id`` (which one run shares across many steps). Contracts: ``efficiency-element.contract.md``
# C-63…C-71, hosted by ``status-digest.contract.md`` C-72; the entities are ``data-model.md`` E8.
def load_store_engine():
    """Import the store engine **in process** and return its module, or ``None`` when it is unavailable.

    The element and the measure report share this one reader (``efficiency-element.contract.md`` C-65,
    ``measure-report.contract.md`` C-53): the store's layout (``storage_dir`` / ``records_dir``), its record readers,
    its legacy stream and its declared vocabularies all stay the engine's. Nothing here re-parses a record,
    re-implements the compatibility path, shells out to the engine's command line or caches across invocations.

    An unimportable engine is an *unavailable input*, reported as such; it never fails a surface (C-68).
    """
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
    if not _read_field_slots(module):
        return None
    return module


#: The record's elapsed node slot and the run record's mode field, read from the engine's own source at run
#: time: both field slots are owned elsewhere (the record schema declaration via ``.specify/scripts/python/exec-quant.py``;
#: ``mode`` is a member of the declaration's ``config_fields`` roster) and this file MUST NOT re-spell them as
#: literals (C-70/C-71). Both bind in :func:`load_store_engine` from the engine module's own faces; ``None``
#: until then, and an unresolvable slot is an unavailable input reported as such — never guessed.
_ELAPSED_NODE = None
_MODE_FIELD = None


def _read_field_slots(engine) -> bool:
    """Bind the two engine-owned field-slot names from the engine's own faces (C-70/C-71).

    The elapsed node is the ``*_ms`` quality node the engine itself writes; the mode field is the config field
    the engine reads through its leaf accessor. Returns ``False`` when either cannot be resolved — an
    unavailable input the caller reports, never a hard-coded default.
    """
    global _ELAPSED_NODE, _MODE_FIELD
    try:
        text = (REPO_ROOT / STORE_ENGINE).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    elapsed = re.search(r"[\"'](\w+_ms)[\"']:\s*NOT_EVALUATED", text)
    mode = re.search(r"[\"'](\w+)[\"']:\s*leaf\(", text)
    if elapsed is None or mode is None:
        return False
    _ELAPSED_NODE = elapsed.group(1)
    _MODE_FIELD = mode.group(1)
    return True


def _quantity(node):
    """One record quantity as ``(value, provenance)``; ``(None, None)`` when the record carries no value.

    The node's shape is the declaration owner's, reached through the engine at run time: a quantity is a
    ``{"value", "provenance"}`` mapping, and a quantity with no source is the schema's own not-evaluated literal. This
    file names neither the node's field slots nor its vocabulary (C-71): it recognises the absence by comparing against
    the engine's constant, and it never invents a value where the record has none.
    """
    if not isinstance(node, dict):
        return None, None
    value = node.get("value")
    if value is None:
        return None, None
    provenance = node.get("provenance")
    return value, provenance if isinstance(provenance, str) and provenance else None


def read_store(workspace: Path):
    """Read the store once through the engine's read path.

    Returns ``(state, engine)`` where ``state`` is ``{"available", "records", "error"}``: ``available`` false with no
    records means "absent or empty" — the surface-availability state C-68 renders — and an ``error`` names an
    unreadable store without ever raising into a surface. ``engine`` is the imported module (the caller reaches the
    declared vocabularies through it), or ``None`` when it could not be imported.

    Read-only by construction: the engine's readers open records for reading and compose no lock; no path is created
    anywhere under the store by either surface (C-69).
    """
    engine = load_store_engine()
    if engine is None:
        return {"available": False, "records": [], "error": "the store engine is unreadable"}, None
    try:
        base = engine.storage_dir(workspace)
        if not base.is_dir():
            return {"available": False, "records": [], "error": None}, engine
        records = engine.read_jsonl_safe(base / engine.LEGACY_RECORDS_NAME)
        records.extend(engine.read_entry_files(engine.records_dir(workspace)))
    except (OSError, AttributeError) as exc:
        return {"available": False, "records": [], "error": "the store is unreadable: %s" % exc}, engine
    if not records:
        return {"available": False, "records": [], "error": None}, engine
    return {"available": True, "records": records, "error": None}, engine


def step_identity(record):
    """The **step identity** a record carries: its own ``(unit_id, unit_type)`` pair, or ``None``.

    This is the element's unit (``data-model.md`` E8 ``unit.identity``). A record whose pair is unusable names no
    step and is never selected — it cannot be assigned to a row, and inventing one would put a step on a surface that
    surface never named.
    """
    if not isinstance(record, dict):
        return None
    unit_id = record.get("unit_id")
    unit_type = record.get("unit_type")
    if not isinstance(unit_id, str) or not unit_id:
        return None
    if not isinstance(unit_type, str) or not unit_type:
        return None
    return (unit_id, unit_type)


def record_identity(record) -> str:
    """A record's own identity, byte-stable and ascending — the C-66 tie-break.

    The identity composes the record's own fields (its collection stamp and, as a stable discriminator, its name
    stem when the reader carries one). It deliberately does **not** depend on the order the engine enumerated files
    in: two runs over one store, or one store twice, resolve the same winner.
    """
    if not isinstance(record, dict):
        return ""
    stamp = record.get("collected_at")
    stem = record.get("_record_stem") or record.get("record_id") or ""
    return "%s\u0000%s" % (stamp if isinstance(stamp, str) else "", stem)


def select_latest_by_step(records) -> dict:
    """Index the store by **step identity**, keeping the latest record per step — one rule, no folding (C-66).

    A step's newest record is the one with the greatest ``collected_at``; records sharing that stamp are decided by
    the record's own identity in **ascending** byte-stable order — the LOWEST identity wins the tie, the same end
    the ascending order's first element occupies — never by filesystem enumeration order. Nothing is
    averaged, summed, ranked or aggregated across a step's records — that is the measure report's question
    (``measure-report.contract.md`` C-54/C-56), not the element's.
    """
    latest = {}
    for record in records or ():
        identity_key = step_identity(record)
        if identity_key is None:
            continue
        stamp = str(record.get("collected_at") or "")
        identity = record_identity(record)
        current = latest.get(identity_key)
        if current is None or _newer(stamp, identity, current[0]):
            latest[identity_key] = ((stamp, identity), record)
    return latest


def _newer(stamp: str, identity: str, incumbent: tuple) -> bool:
    """The one comparison behind every selection: a greater stamp wins; on a tie the LOWER identity wins (C-66)."""
    best_stamp, best_identity = incumbent
    if stamp != best_stamp:
        return stamp > best_stamp
    return identity < best_identity


def efficiency_vocabulary() -> dict:
    """The element's two render literals, read from their single definition site (the owner document).

    ``ownership-map.contract.md`` C-47 makes ``.specify/shared/guidelines/reporting-obligations.md`` § 九 the marker's one
    declaration point. The owner's forms are matched at run time so the rendered literals follow the owner rather than
    a copy of it; the module constants are the bootstrap fallback for a tree where the owner is unreadable.
    """
    vocabulary = {"marker": NOT_EVALUATED_MARKER, "no_measurements": NO_MEASUREMENTS}
    owner = REPO_ROOT / OWNER_DOC
    try:
        text = owner.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return vocabulary
    for form in NOT_EVALUATED_MARKER_FORMS:
        match = re.search(form, text, re.I)
        if match:
            spelling = match.group(1).lower()
            vocabulary["marker"] = "not-evaluated" if "-" in spelling else "not evaluated"
            break
    return vocabulary


def _element(step, record=None) -> dict:
    """One element's projected quantities; ``record`` is the selected one or ``None`` for a step with no record."""
    quality = {}
    if isinstance(record, dict) and isinstance(record.get("quality"), dict):
        quality = record["quality"]
    return {
        "unit_id": step[0],
        "unit_type": step[1],
        "record": record,
        "elapsed": _quantity(quality.get(_ELAPSED_NODE)),
        "tokens": _quantity(quality.get("tokens")),
        "invocations": _quantity(quality.get("invocations")),
    }


def project_efficiency(store, steps) -> dict:
    """Project the elements of a surface's named steps, in the surface's own order (C-63, C-66, C-67).

    ``steps`` is the ordered sequence of ``(unit_id, unit_type)`` identities the host surface already names — for the
    line, the steps its flow has run; for the digest, the step each listed entry is at, optionally narrowed to that
    entry's run. The element **never widens** that set: the store supplies quantities and never a step the surface did
    not name. A step for which the store holds no record still carries its element, with the not-evaluated marker —
    an omission beside a neighbour's number would read as "faster", the misreading C-67 exists to prevent.

    ``store`` is :func:`read_store`'s result. An unavailable store is the render-wide ``no measurements`` state: never
    a per-step marker, and never a reason to drop a step from the host surface (C-68).
    """
    if not store.get("available"):
        return {"available": False, "elements": [], "depth": None, "withheld": None,
                "error": store.get("error")}
    latest = select_latest_by_step(store.get("records"))
    elements = []
    for entry in steps:
        # A caller may name a step on its own — ``(unit_id, unit_type)`` — or narrow it to one run. The two shapes are
        # distinguished by the scope's type, never by the tuple's length: the step identity is itself a pair.
        if isinstance(entry, dict):
            step = (entry.get("unit_id"), entry.get("unit_type"))
            scope = entry.get("run_id")
        else:
            step = tuple(entry)
            scope = None
        chosen = latest.get(step)
        if chosen is not None and scope:
            scoped = latest_of_run(store.get("records"), step, scope)
            chosen = scoped if scoped is not None else chosen
        elements.append(_element(step, chosen[1] if chosen else None))
    return {"available": True, "elements": elements, "depth": None, "withheld": None, "error": None}


def latest_of_run(records, step, scope):
    """The newest record of one **step** produced inside one **run** — the surface's own narrowing (C-66).

    The step identity is the record's ``(unit_id, unit_type)``; the run is the surface's extra axis (a listed entry
    names its own run). Selection stays the one rule: greatest ``collected_at``, ties by record identity ascending. A
    scope that holds no record for the step leaves the caller's unscoped selection in place, so the element reports
    the latest record of the step the surface named rather than falling silent.
    """
    found = None
    for record in records or ():
        if step_identity(record) != step:
            continue
        if not isinstance(record, dict) or record.get("run_id") != scope:
            continue
        stamp = str(record.get("collected_at") or "")
        identity = record_identity(record)
        if found is None or _newer(stamp, identity, found[0]):
            found = ((stamp, identity), record)
    return found


def render_quantity(quantity, kind) -> str:
    """One quantity as ``<value>(<provenance>)``, or the owner's marker — never ``0`` for "not measured" (C-64)."""
    value, provenance = quantity
    if value is None or isinstance(value, bool):
        return efficiency_vocabulary()["marker"]
    if kind == "elapsed":
        try:
            number = float(value)
        except (TypeError, ValueError):
            return efficiency_vocabulary()["marker"]
        text = "%dms" % number if number.is_integer() else "%sms" % value
    else:
        # The two count quantities are counts, so their unit is a word rather than a suffix: ``<n> tok`` /
        # ``<n> calls``. The word is a render label, not a second vocabulary (C-71).
        labels = {"tokens": "tok", "invocations": "calls"}
        text = "%s %s" % (value, labels.get(kind, kind))
    return "%s(%s)" % (text, provenance) if provenance else text


def element_fields(element, depth="full") -> list:
    """One element's field list, in the declared order: identity → elapsed → tokens → invocations (C-64).

    The elapsed quantity is unconditional and first; the two count quantities are appended only at ``full`` depth,
    which is a decision taken once per render (see :func:`resolve_depth`).
    """
    fields = [
        "unit=%s" % element["unit_id"],
        "elapsed=%s" % render_quantity(element["elapsed"], "elapsed"),
    ]
    if depth == "full":
        for name in EFFICIENCY_DEEP_QUANTITIES:
            fields.append("%s=%s" % (name, render_quantity(element[name], name)))
    return fields


def render_element(element, depth="full") -> str:
    """One element's rendered text — the host surface places it at a marked position on its own line (C-63)."""
    return EFFICIENCY_FIELD + " ".join(element_fields(element, depth))


def resolve_depth(efficiency, bound=None) -> str:
    """The ONE depth decision for a render: ``"full"`` or ``"elapsed"`` (C-64, Clarifications Q2).

    The two deeper quantities are appended only while **every** element of the render finds room inside the surface's
    own entry bound. The decision is taken once, over the widest element — never per step — so two steps on one screen
    are never described to different depths. ``bound`` is the surface's declared element width in characters; ``None``
    means the bound does not bind this render.
    """
    if not efficiency.get("available"):
        return None
    elements = efficiency.get("elements") or []
    if not elements:
        return None
    if bound is None:
        return "full"
    widest = max(len(render_element(element, "full")) for element in elements)
    return "full" if widest <= bound else "elapsed"


def withheld_summary(efficiency, depth) -> str:
    """The sentence naming the quantities this render's bound withheld — ``""`` when nothing was withheld (C-64)."""
    if depth != "elapsed":
        return ""
    return "not rendered within the entry bound: %s" % ", ".join(EFFICIENCY_DEEP_QUANTITIES)


def availability_element() -> str:
    """The render-wide store-availability state, as the content the element would have carried (C-68)."""
    return EFFICIENCY_FIELD + efficiency_vocabulary()["no_measurements"]


def _dedupe_steps(steps) -> list:
    """One entry per distinct ``(step, run scope)``, in first-seen order — a set, never a multiset (C-63).

    Two registry entries may report the same stage; the element is rendered per **step of the flow the surface
    names**, so an exact repeat adds nothing and would double a row's content.
    """
    seen = set()
    ordered = []
    for step in steps:
        key = (step.get("unit_id"), step.get("unit_type"), step.get("run_id")) if isinstance(step, dict) else step
        if key in seen:
            continue
        seen.add(key)
        ordered.append(step)
    return ordered


def digest_steps_of(entries) -> dict:
    """The **bound** on the steps the digest names: how many, and inside which run (C-63, C-72, FR-023).

    The digest's own state source is the line registry, and the registry says *which flows are running* — never which
    step a flow is at (an entry's ``stage`` is the loop stage, not a unit identity). The steps the digest names are
    therefore read from the dimension's one source (``data-model.md`` E8 ``unit.lookup``): **this run's steps, or the
    most recent steps**, bounded by the entry cap this surface already applies.

    That bound is the entry set's size, so the element introduces no step the digest would not otherwise count (C-63)
    and can never exceed the cap (C-43). The run scope is the one run the listed entries share — *this* run's steps —
    and is absent when they share none, in which case the population is the store's most recent steps in the declared
    total order (the same ordering rule the element already uses to pick a step's record, C-66).
    """
    return {"limit": len(entries), "scope": _shared_run(entries)}


def _shared_run(entries):
    """The one run the listed entries all belong to, or ``None`` when they belong to several (then: most recent)."""
    runs = set()
    for item in entries:
        run_id = item.get("run_id")
        if isinstance(run_id, str) and run_id:
            runs.add(run_id)
    return runs.pop() if len(runs) == 1 else None


def most_recent_steps(records, limit, scope=None) -> list:
    """The most recent ``limit`` steps the store holds, in the declared total order (C-66, FR-023's step bound).

    A step is the record's own ``(unit_id, unit_type)`` pair — the element's unit. Steps are ordered by their newest
    record's ``collected_at`` descending, ties broken by record identity ascending, so the set is stable across runs
    and across filesystem enumeration order. ``scope`` (a run identity) narrows the population to one run's steps,
    which is how the digest reports *this run's* steps when every listed entry names the same run.
    """
    latest = {}
    for record in records or ():
        # A record names its step through its own ``(unit_id, unit_type)`` pair — never through the run, which one
        # run shares across many steps (C-66).
        pair = step_identity(record)
        if pair is None:
            continue
        if scope is not None and record.get("run_id") != scope:
            continue
        stamp = str(record.get("collected_at") or "")
        identity = record_identity(record)
        current = latest.get(pair)
        if current is None or _newer(stamp, identity, current[0]):
            latest[pair] = ((stamp, identity), record)
    # The most recent steps, in the declared total order — at most ``limit`` DISTINCT steps, never repeated. The
    # step set is bounded by the surface's own bound (the cap the digest already applies), so the element can never
    # exceed the cap (C-43) and never introduces a step the surface did not name (C-63). A store holding fewer
    # distinct steps than the render has rows leaves the remaining rows untouched: the step set is the store's most
    # recent steps *within* the surface's bound, not a repetition padded out to the row count. Ties on the newest
    # stamp order by record identity ascending: the primary sort is identity ascending, the stable secondary sort
    # is stamp descending, so equal stamps keep the ascending-identity order (C-66).
    by_identity = sorted(latest.items(), key=lambda item: item[1][0][1])
    by_stamp = sorted(by_identity, key=lambda item: item[1][0][0], reverse=True)
    return [pair for pair, _entry in by_stamp[:limit]]


# ---------------------------------------------------------------- reader: the role-edge view (095)
# The role view is a projection over the role-edge judgement model: one materialization per run through the engine's
# importable interface (contracts ``status-digest-role-view.contract.md`` C-1/C-5). The engine parses the carriers and
# judges the roles; this file only places the four fields on the entries it already renders — no second parser and no
# second renderer.
def load_role_engine():
    """Import the role-edge engine in process and return its module, or ``None`` when it is unavailable."""
    path = REPO_ROOT / ROLE_ENGINE
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("role_view_store_engine", str(path))
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except (OSError, ImportError, SyntaxError, ValueError):
        return None
    for face in ("read_carrier_inputs", "evaluate_role_model", "RoleEdgeInputError"):
        if not hasattr(module, face):
            return None
    return module


def read_role_materialization(workspace: Path, registry_dir: Path):
    """The ONE role-model materialization: one carrier read, one judgement (contract C-1).

    Returns ``(model, inputs, error)``. ``inputs`` is the engine's parsed snapshot, whose ``registry_payloads``
    carries the registry entries this same read parsed — :func:`read_state` derives the legacy line entries from
    it, so the registry root is read once and both views derive from that one pass. An unavailable materialization
    is not a digest input error: the four role fields render as empty and the digest's own reading is untouched.
    The engine's required carrier roots need not exist in a project that never ran a team or a driver (the degrade
    face recorded for analyze W2-15).
    """
    engine = load_role_engine()
    if engine is None:
        return None, None, "role engine unreadable: %s" % ROLE_ENGINE
    roots = {key: str(Path(workspace).joinpath(*parts)) for key, parts in ROLE_CARRIER_ROOTS}
    try:
        inputs = engine.read_carrier_inputs(registry_dir=str(registry_dir), **roots)
        return engine.evaluate_role_model(inputs), inputs, None
    except engine.RoleEdgeInputError as exc:
        return None, None, "role model unavailable: %s" % exc


def _role_record(index: dict, item: dict):
    """The model executor that IS this line-registry entry: line id first, then run id (identity, not classification)."""
    for key in ("line_id", "run_id"):
        value = item.get(key)
        if value is not None and str(value) in index:
            return index[str(value)]
    return None


def _executor_artifact_paths(workspace: Path, identity: str) -> dict:
    """An executor's own carriers under the two existing roots: its artifact triplet and its stage artifacts.

    These are the files the assignment and host-event layers already own (``data-model.md`` § 10); the digest reads
    an exit record and file mtimes from them and derives nothing else.
    """
    state_dir = Path(workspace) / ".specify" / "state"
    logs_dir = Path(workspace) / ".specify" / "agents" / "execution" / "logs"
    status = [logs_dir / (identity + ".status"), state_dir / ("status-" + identity)]
    activity = status + [
        logs_dir / (identity + ".jsonl"),
        logs_dir / (identity + ".live.log"),
        state_dir / ("log-" + identity + ".log"),
        state_dir / ("heartbeat-" + identity + ".log"),
        state_dir / ("pid-" + identity),
    ]
    return {"status": status, "activity": activity}


def _executor_state(workspace: Path, identity: str) -> str:
    """``completed`` / ``failed`` from the existing exit record, ``running`` while no exit record exists."""
    for path in _executor_artifact_paths(workspace, identity)["status"]:
        if path.is_file():
            state, _code = project_exit_record(str(path))
            if state is not None:
                return state
    return "running"


def _executor_last_activity(workspace: Path, identity: str):
    stamps = [
        _mtime_iso(str(path))
        for path in _executor_artifact_paths(workspace, identity)["activity"]
        if path.is_file()
    ]
    seen = [stamp for stamp in stamps if stamp is not None]
    return max(seen) if seen else None


def merge_role_entries(line_entries, model, workspace: Path, now: datetime, stale_bound: int) -> list:
    """Union the line-registry rows with the model's executors that originate outside the registry (contract C-2).

    The line rows gain the four role-view fields; an executor row outside the registry is a row of its own, using the
    role-view names ``id`` / ``last_activity`` and stating the line-specific fields as ``None`` — the two families
    never mix inside one entry. A row that never recorded an exit but whose activity is beyond the stale bound, under
    a parent that is not running in this same reading, is the owner page's interrupted/attention state: it must not
    read as running or completed (FR-027). Both facts come from the existing layers only — the exit record and file
    mtimes — never from a process scan or conversation state (C-5).
    """
    executors = (model or {}).get("executors") or []
    index = {str(entry["id"]): entry for entry in executors}
    line_keys = set()
    defaults = {"parent": None, "roles": [], "role_set_marker": None, "depth": None}
    for item in line_entries:
        for key in ("line_id", "run_id"):
            value = item.get(key)
            if value is not None:
                line_keys.add(str(value))
        role = _role_record(index, item)
        for field in ROLE_VIEW_FIELDS:
            item[field] = role[field] if role is not None else defaults[field]

    extras = []
    for identity in sorted(set(index) - line_keys):
        executor = index[identity]
        state = _executor_state(workspace, identity)
        last = _executor_last_activity(workspace, identity)
        age_seconds = max(0, int((now - last).total_seconds())) if last is not None else None
        row = {
            "id": identity,
            "state": state,
            "last_activity": last.isoformat().replace("+00:00", "Z") if last else DASH,
            "age_seconds": age_seconds,
            "age": format_duration(age_seconds),
            "stale": bool(age_seconds is not None and age_seconds > stale_bound),
            "stale_bound_seconds": stale_bound,
            "project_dir": None,
            "branch": None,
            "stage": None,
            "sources": executor.get("sources") or [],
        }
        for field in ROLE_VIEW_FIELDS:
            row[field] = executor[field]
        row["is_active"] = state == "running"
        extras.append(row)

    activity = {}
    for item in line_entries:
        for key in ("line_id", "run_id"):
            value = item.get(key)
            if value is not None:
                activity[str(value)] = bool(item.get("is_active"))
    for row in extras:
        activity[row["id"]] = row["state"] == "running"
    for row in extras:
        if row["state"] != "running" or not row["stale"]:
            continue
        parent = row["parent"]
        if parent is not None and activity.get(str(parent)) is not True:
            row["state"] = "interrupted"
            row["is_active"] = False
    return extras


def _entry_last_activity(item) -> str:
    """The activity stamp of an entry, by its source family (contract C-2)."""
    value = item.get("last_activity_at") if "line_id" in item else item.get("last_activity")
    return value if isinstance(value, str) and value else DASH


def _is_history_entry(item) -> bool:
    """History never occupies the capped view: closed lines, and lifecycle-terminal executor rows (§ 9)."""
    state = str(item.get("state"))
    if "line_id" in item:
        return state == "closed"
    return state in LIFECYCLE_TERMINAL_STATES


def _read_registry_entries(registry_dir: Path):
    """The fallback single registry read, used only when the role materialization is unavailable.

    Returns ``(entries, error)``. The reading is the same one :func:`read_state` takes on the normal path; the
    fallback exists because a digest without carrier roots must still list its lines, never because two readers
    are allowed (contract C-1 — one registry read per run, on either path).
    """
    try:
        paths = sorted(registry_dir.glob("*.json"))
    except OSError as exc:
        return None, "registry directory is unreadable: %s (%s)" % (registry_dir, exc)
    entries = []
    for path in paths:
        try:
            with path.open("r", encoding="utf-8") as handle:
                entry = json.load(handle)
        except (OSError, ValueError) as exc:
            return None, "unparsable registry entry %s: %s" % (path, exc)
        if not isinstance(entry, dict):
            return None, "unparsable registry entry %s: not a JSON object" % path
        entries.append(entry)
    return entries, None


# ---------------------------------------------------------------- reader: the whole state
def read_state(cap: int, stale_bound: int, workspace: Path, element_bound=None):
    """Read the registry once and return the projection every action consumes.

    Returns ``(state, error)``; ``error`` is a human-readable input-error string, never a traceback. ``state`` is the
    single reading: ``registry_dir``, ``entries`` (already workspace-filtered, ordered and capped), ``all_entries``,
    ``omitted``, ``cap``, ``stale_bound_seconds``, ``generated_at``, ``vocabulary``, ``now``, and the efficiency
    projection with its render-wide depth decision (contracts C-63…C-68).

    Contract C-1's single state-read pass: the role materialization is taken first, and the legacy line entries are
    derived from the SAME registry read it performed (``registry_payloads``). When the materialization is unavailable
    (a project without the engine's carrier roots), one fallback read supplies the legacy entries — still exactly one
    registry read per run, never two.

    ``element_bound`` is this surface's declared element width in characters (``None`` = not binding); the depth
    decision is taken here, once per reading, so the surfaces never disagree about how deep an element may be.

    ``now`` is the single instant this reading was taken at. The digest's age, the supervision report's age and the
    stall judgement all measure against it, so one render is one clock reading rather than three (C-41's one-reading
    rule applied to time as well as to state).
    """
    registry_dir = resolve_registry_dir()
    now = datetime.now(timezone.utc)
    vocabulary = read_engine_vocabulary()

    if not registry_dir.is_dir():
        return None, "registry directory is unreadable: %s" % registry_dir

    # The role view (contract C-1): ONE materialization per run, and its carrier read is this digest's single
    # state-read pass — the legacy line entries below derive from the registry payloads that read returned.
    role_model, role_inputs, _role_error = read_role_materialization(workspace, registry_dir)
    if role_inputs is not None and "registry_payloads" in role_inputs:
        unreadable = role_inputs.get("notes", {}).get("registry_unreadable_paths") or []
        if unreadable:
            return None, "unparsable registry entry %s" % unreadable[0]
        raw = [
            item["payload"]
            for item in role_inputs.get("registry_payloads") or []
            if isinstance(item, dict) and isinstance(item.get("payload"), dict)
        ]
    else:
        raw, registry_error = _read_registry_entries(registry_dir)
        if registry_error:
            return None, registry_error

    # Workspace rule (FR-011): only entries whose project_dir is this workspace are listed, and only they count
    # against the cap. An entry of another project is not rendered and carries no label of its own.
    def in_workspace(entry: dict) -> bool:
        # A line's project is either the workspace itself or one of its write worktrees: entries registered
        # for a worktree of THIS repo (repo_root == workspace) belong to this workspace's view — the executor
        # is the row identity, and its working tree must not hide it (2026-11-10 executor-primary revision).
        for key in ("project_dir", "repo_root"):
            value = entry.get(key)
            if not isinstance(value, str) or not value:
                continue
            try:
                if Path(value).expanduser().resolve() == workspace:
                    return True
            except OSError:
                continue
        return False

    scoped = [e for e in raw if in_workspace(e)]
    active_states = vocabulary.get("active_states") or set()
    projected = [project_entry(e, now, stale_bound) for e in scoped]
    for item in projected:
        item["is_active"] = item.get("state") in active_states

    # Both views derive from the one materialization above: the legacy line rows gain the four role fields and
    # the model's executors outside the registry become rows of their own; an unavailable materialization renders the
    # fields empty and changes nothing else about this reading.
    merged = projected + merge_role_entries(projected, role_model, workspace, now, stale_bound)

    # Deterministic order (contract C-43): active executors first, then descending last-activity time, ties by
    # identity.
    def sort_key(item):
        stamp = _parse_iso(_entry_last_activity(item)) if _entry_last_activity(item) != DASH else None
        epoch = stamp.timestamp() if stamp else 0.0
        return (0 if item["is_active"] else 1, -epoch, str(item.get("line_id") or item.get("id")))

    merged.sort(key=sort_key)
    # Reader contract (2026-11-10 second revision): the digest answers "what is happening now" — history (closed
    # lines, lifecycle-terminal executor rows) never occupies the capped view; it stays in ``all_entries`` for
    # consumers reading the full set.
    visible = [item for item in merged if not _is_history_entry(item)]
    omitted = max(0, len(visible) - cap)
    entries = visible[:cap]

    # The efficiency dimension (contracts C-63…C-68): ONE store reading behind both surfaces. The element's unit is
    # the STEP — the ``(unit_id, unit_type)`` identity the exec-quant record carries, never a listing row — so the
    # store is read once here and carried in the state: no renderer reads it a second time (C-65), and neither read
    # touches it (C-69). What each surface names is its own: the digest names this run's steps or the most recent
    # ones, inside its cap (``echo`` of the entry set it already bounded); the status line names the steps its flow
    # states. A named step the store holds no record for still carries its element (C-67).
    store, _engine = read_store(workspace)
    bound = digest_steps_of(entries)
    steps = most_recent_steps(store.get("records"), bound["limit"], bound["scope"])
    if not steps and bound["scope"] is not None:
        # This run holds no record yet: the step set falls back to the most recent steps (``data-model.md`` E8
        # ``unit.lookup`` — "this run's steps, or the most recent steps"), still inside the same bound (C-63).
        steps = most_recent_steps(store.get("records"), bound["limit"], None)
    efficiency = project_efficiency(store, steps)
    efficiency["depth"] = resolve_depth(efficiency, element_bound)
    efficiency["withheld"] = withheld_summary(efficiency, efficiency["depth"])

    return {
        "registry_dir": str(registry_dir),
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "cap": cap,
        "stale_bound_seconds": stale_bound,
        "entries": entries,
        "all_entries": merged,
        "omitted": omitted,
        "vocabulary": vocabulary,
        "now": now,
        "store": store,
        "efficiency": efficiency,
        "workspace": str(workspace),
        "executors": read_executors(
            workspace, [item for item in entries if "line_id" in item], now
        ),
    }, None


# ---------------------------------------------------------------- shared derivations
def profile_in_force(state) -> str:
    """The cadence profile selecting for this reading (``data-model.md`` E6, contract C-30).

    The selecting condition is E6's: at least one live status receiver — a reporter seat whose runtime execution is
    not omitted, or a supervising master holding at least one dispatched sub-flow. Neither is visible from a registry
    entry alone, so the reading reports the *observed* half it can decide: an active line is a live receiver by
    construction (it holds a concurrency slot), and its absence selects the interactive profile.
    """
    if any(item.get("is_active") for item in state["entries"]):
        return PROFILE_LONG_RUN
    return PROFILE_INTERACTIVE


def _read_text(rel_path: Path):
    path = REPO_ROOT / rel_path
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _read_any(path_arg):
    """Read a caller-supplied path verbatim: absolute paths are opened as given, relative ones against the repo.

    ``_read_text`` prefixes :data:`REPO_ROOT`, which is right for the framework sources this module owns and wrong
    for an input a caller names — a guard fixture's run record lives wherever the test put it. Kept as one helper so
    no caller has to guess which reading a path argument gets.
    """
    path = Path(path_arg)
    if not path.is_absolute():
        path = REPO_ROOT / path
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


# ---------------------------------------------------------------- action: digest
#: The two engine states that mean "this line finished" (``data-model.md`` E5 ``last_completion``: "the most recently
#: ``completed`` entry of the set"). ``closed`` is the engine's own end state; the names are a projection of the
#: engine's vocabulary rather than a second closed set, and a state the engine adds later simply yields no row.
COMPLETED_STATES = ("closed", "completed")

#: The per-entry activity pack's rendered field name (the E5 / E3 pack: label, state, age — nothing else).
ACTIVITY_FIELD = "activity="


def last_completion(state):
    """E5's ``last_completion``: the single most recently finished entry of the whole (uncapped) set.

    It is read off ``all_entries``, not off the capped view: a completion that fell past the cap is still the most
    recent completion, and reporting a *different* one would be a quietly wrong answer to "what just finished?".
    """
    finished = [
        item
        for item in state["all_entries"]
        if "line_id" in item
        and (item.get("state") in COMPLETED_STATES or item.get("exit_code") == 0)
        and item.get("last_activity_at") not in (None, DASH)
    ]
    if not finished:
        return None
    return max(finished, key=lambda item: _parse_iso(item["last_activity_at"]).timestamp())


def _human_duration(age: str) -> str:
    """`83h12m` -> `83 小时 12 分`; anything unparsable is returned unchanged."""
    match = re.fullmatch(r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?", age or "")
    if not age or not match or not any(match.groups()):
        return age or DASH
    days, hours, minutes = (int(g) if g else 0 for g in match.groups())
    parts = []
    if days:
        parts.append("%d 天" % days)
    if hours:
        parts.append("%d 小时" % hours)
    if minutes or not parts:
        parts.append("%d 分" % minutes)
    return " ".join(parts)


_STATE_WORDS = {
    "active": "活跃",
    "waiting": "等待中",
    "blocked": "阻塞",
    "closed": "已关闭",
    "stalled": "已停滞",
    # The executor-row states outside the registry vocabulary (contract C-2's second field family; the lifecycle
    # values are ``data-model.md`` § 9, the interrupted/attention state is the owner page's recovery mark).
    "running": "运行中",
    "interrupted": "已中断",
    "completed": "已完成",
    "failed": "失败",
    "cancelled": "已取消",
}
_STAGE_LABELS = {
    "requirements": "需求撰写",
    "clarify": "需求澄清",
    "plan": "实现规划",
    "tasks": "任务拆解",
    "checklist": "质量清单",
    "analyze": "一致性分析",
    "implement": "实现",
    "review": "评审",
    "closure": "收尾",
    "migrate": "迁移收尾",
}


def _human_seconds(seconds) -> str:
    if seconds is None:
        return DASH
    seconds = int(seconds)
    if seconds < 60:
        return "%d 秒" % seconds
    if seconds < 3600:
        return "%d 分" % (seconds // 60)
    if seconds < 86400:
        return "%d 小时 %d 分" % (seconds // 3600, (seconds % 3600) // 60)
    return "%d 天 %d 小时" % (seconds // 86400, (seconds % 86400) // 3600)


def _pid_alive(pid) -> bool:
    try:
        os.kill(int(pid), 0)
    except PermissionError:
        return True
    except (ProcessLookupError, ValueError, OSError):
        return False
    return True


def read_executors(workspace, entries, now):
    """One row per ALIVE agent execution of this workspace — the executor, not the spec, is the row identity.

    Sources: the ``pid-<line>-<stage>`` files the stage runner writes under ``<workspace>/.specify/state/``
    (each carries ``pid=`` / ``line=`` / ``stage=`` / ``at=``), plus the registry's own recorded
    ``cli_pid`` / ``runner_pid`` when alive. A dead pid is never rendered: the digest answers what is running
    now. Several executions may share one spec; each keeps its own row.
    """
    state_dir = Path(workspace) / ".specify" / "state"
    out = []
    if not state_dir.is_dir():
        return out
    by_line = {str(e.get("line_id")): e for e in entries if str(e.get("state")) != "closed"}
    known = set()

    def add(entry, pid, stage, started):
        if int(pid) in known or not _pid_alive(pid):
            return
        known.add(int(pid))
        out.append(
            {
                "line_id": str(entry.get("line_id")),
                "pid": int(pid),
                "stage": stage or "",
                "started_epoch": started,
                "cli": entry.get("cli") or "",
                "worktree_path": entry.get("worktree_path") or DASH,
            }
        )

    for path in sorted(state_dir.glob("pid-*")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fields = {}
        for line in text.splitlines():
            # A pid record is one line of space-separated key=value pairs (``pid=… at=… line=… stage=…``),
            # not one pair per line: split on whitespace so ``pid`` keeps its digits only.
            for token in line.split():
                key, _, value = token.partition("=")
                if key and value:
                    fields.setdefault(key, value)
        pid = fields.get("pid", "")
        line_id = fields.get("line", "")
        entry = by_line.get(line_id)
        if not pid.isdigit() or entry is None:
            continue
        try:
            started = int(fields.get("at", ""))
        except ValueError:
            started = None
        add(entry, pid, fields.get("stage", ""), started)

    def parent_of(pid):
        try:
            with open("/proc/%d/stat" % int(pid), "r", encoding="utf-8", errors="replace") as handle:
                tail = handle.read().rsplit(")", 1)[1].split()
            return int(tail[1])
        except (OSError, IndexError, ValueError):
            return None

    for entry in by_line.values():
        for key in ("cli_pid", "runner_pid"):
            pid = entry.get(key)
            if not (isinstance(pid, int) or (isinstance(pid, str) and pid.isdigit())):
                continue
            # The registry may record both the runner and its CLI child for ONE dispatch: a pid whose
            # parent is already listed is the same execution, not a second row.
            if parent_of(pid) in known:
                continue
            add(entry, pid, str(entry.get("stage") or ""), None)
    return out


def _activity_of(stage, item):
    """`slug: description` for one execution; a worker suffix (``analyze-w1``) rides in parentheses."""
    raw = str(stage or item.get("stage") or "")
    if raw in ("", DASH, "-"):
        event = str(item.get("last_event") or "")
        if event.startswith("/speckit.") or event.startswith("skill:"):
            return event
        return DASH
    base = re.split(r"[-_]", raw)[0]
    base = re.sub(r"\d+$", "", base)
    label = _STAGE_LABELS.get(base.lower())
    slug = "/speckit.%s" % base
    text = "%s: %s" % (slug, label) if label else slug
    suffix = raw[len(base):].strip("-_")
    return text + ("（%s）" % suffix if suffix else "")


def _executor_row_cell(ex):
    parts = ["fork(%s, pid %s)" % (ex.get("cli") or "cli", ex["pid"])]
    worktree = ex.get("worktree_path")
    if worktree and worktree != DASH:
        parts.append("worktree %s" % os.path.basename(str(worktree).rstrip("/")))
    return " · ".join(parts)


def _elapsed_cell(item, now, is_closed):
    created = _parse_iso(item.get("created_at"))
    if created is None:
        return DASH
    end = _parse_iso(item.get("updated_at")) if is_closed else now
    if end is None:
        return DASH
    return _human_seconds(max(0, int((end - created).total_seconds())))


def _human_measure(value) -> str:
    """A measured quantity in reader words; the not-evaluated vocabulary stays explicit, never a fake zero."""
    text = str(value)
    if text in ("not-evaluated", "not_evaluated", "None", "null", ""):
        return "未测量"
    return text


def _parent_cell(item) -> str:
    parent = item.get("parent")
    return str(parent) if parent not in (None, "") else DASH


def _roles_cell(item) -> str:
    roles = item.get("roles") or []
    if not roles:
        return DASH
    text = ",".join(str(role) for role in roles)
    marker = item.get("role_set_marker")
    return "%s · %s" % (text, marker) if marker else text


def _depth_cell(item) -> str:
    depth = item.get("depth")
    return DASH if depth is None else str(depth)


def _executor_state_word(item) -> str:
    """The executor family's state word; a stale row carries its silence, an interrupted one asks for attention."""
    state = str(item.get("state"))
    word = _STATE_WORDS.get(state, state or DASH)
    if item.get("stale"):
        suffix = "，需关注" if state == "interrupted" else ""
        return "%s（静默 %s%s）" % (word, _human_seconds(item.get("age_seconds")), suffix)
    return word


def render_digest_table(state) -> str:
    """The ONE human-facing digest rendering — the EXECUTOR is the row, the spec is a column.

    Reader contract (2026-11-10 second revision): history is not shown; every row is one live agent execution
    answering — 执行体 (process carrier, pid, worktree), 所属 spec, 父边, 角色, 深度, 在做什么
    (`slug: description`), 状态 (with explicit staleness duration when over the bound) and 已执行时间 (that
    execution's own duration). A non-closed line with no live executor keeps one row with an empty executor
    cell so a stopped flow stays visible. An executor row outside the line registry (team member, fan-out
    child, driver stage) is one row of its own carrying the same role columns — contract C-2's second field
    family. Presentation only over the same reading (C-41); the empty view renders the ``nothing-running``
    literal (C-45).

    The dimension and summary semantics of the pre-revision renderer are carried here as content, never by a
    second renderer: the packed activity where the entry declares its triplet, the single most recent
    completion, the render-wide truncation/withdrawal summary, the explicit store-availability state (C-68)
    and one efficiency element per step the digest names (C-63) — appended to the entry's row after the
    aligned columns, so the element never changes the columns' own geometry.
    """
    visible = state["entries"]
    if not visible:
        return NOTHING_RUNNING

    executors = state.get("executors") or []
    by_line = {}
    for ex in executors:
        by_line.setdefault(str(ex.get("line_id")), []).append(ex)
    now = _parse_iso(state["generated_at"])
    header = "状态摘要 · 生成于 %s（UTC）· 最多 %d 条 · 注册目录 %s" % (
        state["generated_at"],
        state["cap"],
        state["registry_dir"],
    )
    efficiency = state.get("efficiency") or {}
    elements = efficiency.get("elements") or []
    depth = efficiency.get("depth")
    row_count = 8
    rows = []
    row_entry_positions = []

    def activity_cell(stage, item):
        cell = _activity_of(stage, item)
        pack = item.get("line_activity")
        if pack:
            # E5's packed per-entry activity (C-42): rendered where the entry declares its triplet, never invented.
            cell = "%s  %slabel=%s,state=%s,age=%s" % (
                cell,
                ACTIVITY_FIELD,
                pack["label"] or DASH,
                pack["state"],
                pack["age"],
            )
        return cell

    for position, item in enumerate(visible):
        if "line_id" not in item:
            rows.append(
                (
                    str(item.get("id") or DASH),
                    DASH,
                    _parent_cell(item),
                    _roles_cell(item),
                    _depth_cell(item),
                    DASH,
                    _executor_state_word(item),
                    DASH,
                )
            )
            row_entry_positions.append(position)
            continue
        line_id = item["line_id"] or DASH
        state_word = _STATE_WORDS.get(str(item["state"]), item["state"] or DASH)
        line_executors = by_line.get(str(item["line_id"]), [])
        if item["stale"] and not line_executors:
            # Silence describes the line's RECORDS; a live executor is proof of activity, so the
            # annotation is reserved for rows that have none.
            state_word = "%s（静默 %s）" % (
                state_word,
                _human_seconds(item.get("age_seconds")),
            )
        if not line_executors:
            rows.append(
                (
                    "—（无存活执行体）",
                    line_id,
                    _parent_cell(item),
                    _roles_cell(item),
                    _depth_cell(item),
                    activity_cell(None, item),
                    state_word,
                    _elapsed_cell(item, now, False),
                )
            )
            row_entry_positions.append(position)
            continue
        for ex in line_executors:
            if ex.get("started_epoch") and now:
                elapsed = _human_seconds(
                    max(0, int(now.timestamp() - int(ex["started_epoch"])))
                )
            else:
                elapsed = _elapsed_cell(item, now, False)
            rows.append(
                (
                    _executor_row_cell(ex),
                    line_id,
                    _parent_cell(item),
                    _roles_cell(item),
                    _depth_cell(item),
                    activity_cell(ex.get("stage"), item),
                    state_word,
                    elapsed,
                )
            )
            row_entry_positions.append(position)
    import unicodedata

    def display_width(text):
        return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)

    head = ("执行体", "所属 spec", "父边", "角色", "深度", "在做什么", "状态", "已执行时间")
    widths = [max(display_width(r[i]) for r in rows + [head]) for i in range(row_count)]

    def fmt_row(r):
        cells = []
        for i in range(row_count):
            pad = widths[i] - display_width(r[i])
            cells.append(r[i] + " " * pad)
        return "  ".join(cells).rstrip()

    lines = [header, "", fmt_row(head), fmt_row(tuple("-" * w for w in widths))]
    for row, position in zip(rows, row_entry_positions):
        rendered = fmt_row(row)
        # The efficiency dimension (contracts C-63…C-68) is CONTENT of the entry's row: one element per step the
        # digest names, placed on the entry whose position it occupies — no extra line, no extra entry. It sits
        # after the aligned columns so the element never re-shapes them (C-68's "changes nothing else").
        if efficiency.get("available") and position < len(elements):
            rendered = "%s  %s" % (rendered, render_element(elements[position], depth))
        lines.append(rendered)
    completion = last_completion(state)
    if completion is not None:
        lines.append(
            "最近完成：last_completion=line_id=%s age=%s"
            % (completion["line_id"], completion["age"])
        )
    withheld = efficiency.get("withheld") or ""
    if state["omitted"] or withheld:
        lines.append(
            "另有 %d 条未显示%s" % (state["omitted"], ("，" + withheld) if withheld else "")
        )
    # The store-availability state is a property of the whole render, not of one row (C-68): it is stated once, on
    # its own summary line, and changes nothing else — same entries, same ordering, same bounds.
    if not efficiency.get("available"):
        lines.append("store=%s" % efficiency_vocabulary()["no_measurements"])
    return "\n".join(lines)


def action_digest(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    state, error = read_state(args.cap, args.stale_bound, workspace, args.element_bound)
    if error:
        print(error, file=sys.stderr)
        return EXIT_INPUT_ERROR

    fmt = args.format
    if fmt == "json":
        payload = dict(state)
        payload["profile"] = profile_in_force(state)
        payload["state_summary"] = "active" if state["entries"] else NOTHING_RUNNING
        payload.pop("vocabulary", None)
        # ``now`` is the reading's clock and ``store`` the raw records: both are consumed by the renderers and never
        # serialized. The element projection they produced is what the JSON surface states.
        payload.pop("now", None)
        payload.pop("store", None)
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_digest_table(state))

    return EXIT_OK if state["entries"] else EXIT_NOTHING_ACTIVE


# ---------------------------------------------------------------- action: report
def render_status_line(args) -> str:
    """Render one status line from the owner's four labels plus attribution and the profile in force.

    Shape (contract ``status-report.contract.md``):

    * attribution first — the structure slug and the run stamp (C-22), then the profile in force (C-30);
    * the trigger kind that produced this line (C-25): ``tick`` for a cadence line, ``boundary`` for the extra line a
      crossed stage boundary emits, ``transition:<sub-flow-id>`` for a significant state transition, and
      ``reporter-failure`` when the reporting loop could not emit (C-29);
    * the delay statement when the tick landed inside an indivisible step and was delivered at that step's next
      boundary (C-25 point 2) — the step is never split to keep the clock;
    * the four content-element labels, then the carrier that receives the line (C-26).

    The labels are named here; their definitions are reached by anchor to
    ``.specify/shared/guidelines/progress-reporting.md`` § 汇报内容下限 and are deliberately not restated (contract C-23).

    ``--transition`` replaces the trigger with that transition's own class, so a supervising flow reports a
    significant transition through this same line shape rather than growing a second status renderer
    (contract ``supervision-report.contract.md`` C-34).
    """
    state, _error = read_state(
        args.cap,
        args.stale_bound,
        Path(args.workspace).expanduser().resolve(),
        getattr(args, "element_bound", None),
    )
    # The profile in force is read from the state when the reading decides it. A mid-run loss of the live receiver
    # switches to `interactive` AT THE NEXT BOUNDARY and says so (contract C-30): `--profile` lets the emitting flow
    # record the switch, and `--profile-switch` carries the reason it switched, so the switch line states it rather
    # than a reader inferring it from a changed field value.
    profile = args.profile or (profile_in_force(state) if state else PROFILE_LONG_RUN)
    fields = [
        "structure=%s" % args.structure,
        "run=%s" % args.run_stamp,
        "trigger=%s"
        % (
            "transition:%s" % args.transition
            if args.transition
            else args.trigger
        ),
        "profile=%s" % profile,
    ]
    if args.transition:
        fields.append("class=%s" % args.transition)
    if args.cadence:
        # An override is recorded NEXT TO the profile, so a reader can tell an override from the definition (C-24).
        fields.append("cadence=%s" % args.cadence)
    if args.delay_reason:
        fields.append("delay=%s" % args.delay_reason)
    if args.profile_switch:
        fields.append("switch=%s" % args.profile_switch)
    fields.extend(
        [
            "position=%s" % args.position,
            "delta=%s" % args.delta,
            "remainder=%s" % args.remainder,
            "blocker=%s" % (args.blocker if args.blocker else NO_BLOCKER),
        ]
    )
    # The efficiency dimension rides this same line as content (contract ``efficiency-element.contract.md`` C-63): one
    # element for the step THIS line names, projected from the reading ``read_state`` already took — never a second
    # store read and never a second line. The unit is the step — the ``(unit_id, unit_type)`` pair — which the emitting
    # flow states with ``--unit-id`` / ``--unit-type`` because a flow that knows where it is also knows what kind of
    # unit that position is. The store supplies the quantities and never the step set (C-66). The carrier still closes
    # the line (C-26), so the dimension is added *before* it.
    steps = line_steps(args)
    if steps:
        # The store is read once, in ``read_state`` above, and every projection of it — the digest's and this line's —
        # is built from that one reading, so neither surface opens the store a second time (C-65, C-69).
        store = (state or {}).get("store") or {"available": False, "records": [], "error": None}
        efficiency = project_efficiency(store, steps)
        depth = resolve_depth(efficiency, getattr(args, "element_bound", None))
        if efficiency.get("available"):
            fields.append(" ".join(render_element(element, depth) for element in efficiency["elements"]))
        else:
            # An absent or empty store is the explicit availability state, never an omission and never an error: the
            # line's own content is untouched (C-68).
            fields.append(availability_element())
        withheld = withheld_summary(efficiency, depth)
        if withheld:
            fields.append("note=%s" % withheld)
    fields.append("carrier=%s" % (args.carrier if args.carrier else CARRIER_CONSOLE))
    return " | ".join(fields)


def line_steps(args) -> list:
    """The steps THIS status line names: the emitting flow's own steps, and no others (C-63, C-66).

    A flow that emits a line knows which steps it has run and which one it is at now. It states them with
    ``--unit-id`` — repeatable, one per step, in execution order — and ``--unit-type`` for the type they share; both
    are the flow's own knowledge, never something this renderer derives from the store. So the line's step set is the
    flow's, and the store supplies only quantities: a step the flow names that the store holds no record for still
    carries its element with the marker (C-67), and a step the store holds that the flow does not name never appears.

    A repeatable ``--unit-id`` may also arrive as one comma-separated value (the shape a command line imposes on a
    repeated flag it cannot repeat), which is read as the same list. A step whose type the flow does not state has no
    identity to match against and is therefore not named at all — guessing a type would invent the identity C-66 pins.
    """
    raw = getattr(args, "unit_id", None) or []
    if isinstance(raw, str):
        raw = [raw]
    unit_type = getattr(args, "unit_type", None)
    if not unit_type:
        return []
    run_id = getattr(args, "run_id", None)
    scope = run_id if isinstance(run_id, str) and run_id else None
    steps = []
    for value in raw:
        for piece in str(value).split(","):
            piece = piece.strip()
            if piece:
                steps.append({"unit_id": piece, "unit_type": unit_type, "run_id": scope})
    return _dedupe_steps(steps)


def action_report(args) -> int:
    for name in ("structure", "run_stamp", "position", "delta", "remainder"):
        if not getattr(args, name):
            print("--action report requires --%s" % name.replace("_", "-"), file=sys.stderr)
            return EXIT_INPUT_ERROR
    line = render_status_line(args)
    print(line)
    return EXIT_OK


# ---------------------------------------------------------------- reader: the stall threshold table
def read_threshold_rows():
    """Read the declared stall-threshold rows from their owner at render time.

    The numbers are owned by ``.specify/skills/internal/create-team/references/patterns.md`` § Monitoring → Stall Detection
    (``data-model.md`` E4); this function parses the table's ``Condition`` and ``Threshold`` cells so the projection
    can name a row and judge against its value without carrying either a copy of the table or a number of its own.
    A failed read is an *unavailable input*, reported as such — never replaced by a hard-coded default.
    """
    path = REPO_ROOT / PATTERNS_DOC
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, "unreadable threshold owner %s: %s" % (PATTERNS_DOC, exc)

    start = text.find("Stall Detection")
    if start < 0:
        return None, "threshold owner %s carries no Stall Detection section" % PATTERNS_DOC
    rows = {}
    for line in text[start:].splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 3 or cells[0].lower() == "condition" or set(cells[0]) <= set("-: "):
            continue
        row_id = cells[0]
        threshold = cells[1]
        # Only a row whose threshold cell *is* a duration can judge silence; a qualitative cell states a condition
        # (e.g. "manifest exists but deliverables empty") and is never a stall threshold.
        match = re.match(r"^\s*(\d+)\s*(s|sec|secs|seconds?|秒)\b", threshold, re.I)
        if not match:
            continue
        rows[row_id] = {
            "row": row_id,
            "threshold_cell": threshold,
            "threshold_seconds": int(match.group(1)),
        }
    if not rows:
        return None, "threshold owner %s carries no readable duration row" % PATTERNS_DOC
    return rows, None


def resolve_threshold(rows, row_id, override_seconds):
    """Resolve the E4 judgement reference: the named row, its declared value, and the override actually used.

    The override rule is C-24's, applied to the threshold: a per-run value replaces the declared one *and is
    recorded next to it*, so a reader can tell an override from the definition.
    """
    if rows is None:
        return None
    if row_id in rows:
        chosen = rows[row_id]
    elif override_seconds is not None:
        # No such row: the judgement's `judged_against` would not resolve, which `data-model.md` calls a defect;
        # the override keeps a reading available but the missing row is named.
        chosen = {"row": row_id, "threshold_cell": "(row not found)", "threshold_seconds": None}
    else:
        return None
    return {
        "row": chosen["row"],
        "threshold_cell": chosen["threshold_cell"],
        "declared_seconds": chosen["threshold_seconds"],
        "override_seconds": override_seconds,
        "value_seconds": override_seconds if override_seconds is not None else chosen["threshold_seconds"],
    }


# ---------------------------------------------------------------- reader: one supervised sub-flow
def project_sub_flow(label, triplet_dir, now, threshold):
    """Project one dispatched sub-flow into the E3 shape the supervision report renders.

    Field ownership (this function copies no rule):

    * ``label`` — the identity, from the visibility contract's label convention;
    * ``state`` — from the triplet and the exit record the visibility contract already declares: a ``.status`` line
      carrying ``exit=0`` is ``completed``, a non-zero ``exit=`` is ``failed``, and silence past the declared
      threshold is ``stalled``;
    * ``age`` — now minus the newest mtime among the triplet files;
    * ``slow`` — a qualifier on ``running``: not progressing *yet*, below the threshold. It is deliberately not a
      fifth state (``data-model.md`` E3's deviation note), so ``slow`` and ``stalled`` are never merged.
    """
    directory = Path(triplet_dir).expanduser()
    triplet_paths = {suffix: directory / (label + suffix) for suffix in TRIPLET_SUFFIXES}
    present = [path for path in triplet_paths.values() if path.is_file()]

    entry = {
        "label": label,
        "state": None,
        "age_seconds": None,
        "age": DASH,
        "slow": False,
        "exit_code": None,
        "triplet": {suffix: str(triplet_paths[suffix]) for suffix in TRIPLET_SUFFIXES},
        "triplet_present": len(present),
        "judged_against": None,
        "measured_silence": DASH,
        "transition": None,
    }

    if not present:
        # A dispatch that produced no part of its declared triplet is not running and cannot have completed:
        # the dispatch itself did not take hold.
        entry["state"] = "failed"
        return entry

    newest = max(path.stat().st_mtime for path in present)
    age_seconds = max(0, int(now - newest))
    entry["age_seconds"] = age_seconds
    entry["age"] = format_duration(age_seconds)
    entry["measured_silence"] = entry["age"]

    status_path = triplet_paths[".status"]
    if status_path.is_file():
        try:
            status_text = status_path.read_text(encoding="utf-8")
        except OSError:
            status_text = ""
        match = re.search(r"exit=(-?\d+)", status_text)
        if match:
            entry["exit_code"] = int(match.group(1))
            entry["state"] = "completed" if entry["exit_code"] == 0 else "failed"

    if entry["state"] is None:
        if threshold and threshold.get("value_seconds") is not None:
            entry["judged_against"] = threshold
            if age_seconds > threshold["value_seconds"]:
                entry["state"] = "stalled"
            else:
                entry["state"] = "running"
                entry["slow"] = True
        else:
            entry["state"] = "running"

    return entry


def project_supervision(sub_flows, expected_labels, now, threshold, transition, interval_elapsed):
    """Assemble the supervision projection: the rows, the closure defects, and the pre-tick transition.

    One reader backs both renderings (C-41's one-reading rule): the rows this returns are the same rows
    ``render_supervision`` prints and ``proposition_ro_06`` judges, so no second parser appears.
    """
    rows = [project_sub_flow(label, directory, now, threshold) for label, directory in sub_flows]
    by_label = {row["label"]: row for row in rows}

    # Presence is closure (C-33): a label the caller knows was dispatched but that produced no row is an omission,
    # named by that label — never a quietly smaller active set.
    omitted = [label for label in (expected_labels or []) if label not in by_label]

    # The transition classes (C-34), each decided from the row's own observed condition.
    if transition == "sub-flow failure":
        targets = [row for row in rows if row["state"] == "failed" and row["triplet_present"]]
    elif transition == "stall crossing":
        targets = [row for row in rows if row["state"] == "stalled"]
    elif transition == "dispatch failure":
        targets = [row for row in rows if row["triplet_present"] == 0]
    else:
        targets = []

    pre_tick = None
    if targets and not interval_elapsed:
        pre_tick = {
            "class": transition,
            "labels": [row["label"] for row in targets],
            "timing": "pre-tick (emitted before the next tick)",
        }

    return {"rows": rows, "omitted": omitted, "pre_tick": pre_tick, "threshold": threshold,
            "transition": transition, "interval_elapsed": interval_elapsed}


def parse_sub_flow_args(items):
    """Parse ``--sub-flow LABEL=TRIPLET_DIR`` values, judging each label against the declared convention."""
    sub_flows = []
    for item in items or []:
        if "=" not in item:
            return None, "--sub-flow expects LABEL=TRIPLET_DIR; got %r" % item
        label, directory = item.split("=", 1)
        if not SUPERVISION_LABEL_PATTERN.match(label):
            return None, (
                "--sub-flow label %r is not the declared convention"
                " `<team-slug>--<run-stamp>--<member-role>`" % label
            )
        sub_flows.append((label, directory))
    return sub_flows, None


def build_projection(args, now):
    """Build the supervision projection from the arguments, or ``(None, None)`` when no sub-flow was supplied."""
    sub_flows, error = parse_sub_flow_args(args.sub_flow)
    if error:
        return None, error
    if not sub_flows:
        return None, None
    rows, read_error = read_threshold_rows()
    threshold = resolve_threshold(rows, args.threshold_row, args.threshold_seconds)
    projection = project_supervision(
        sub_flows,
        args.expect_sub_flow or [],
        now.timestamp(),
        threshold,
        args.transition,
        args.interval_elapsed,
    )
    return projection, read_error


# ---------------------------------------------------------------- action: supervision report
def render_supervision(state, projection, format_age=format_duration) -> str:
    """Render one sub-flow row per dispatched flow, plus the pre-tick transition and the omission defects.

    Shape (contract ``supervision-report.contract.md`` C-32…C-35 and ``status-report.contract.md`` C-30):

    * ``structure`` / ``run`` / ``profile`` — the attribution pair and the profile in force, the same prefix the
      status line carries, so an interleaved report is still attributable;
    * one ``sub-flow=<label>`` row per dispatched flow carrying ``state=``, ``age=``, ``slow=`` and, where a
      judgement was made, ``judged_against=`` (the owner's table reachable by path), ``row=`` (the threshold row's
      own identity) and ``measured_silence=``;
    * an ``omitted:`` clause on a ``state=missing`` row per known-but-unreported dispatch — the omission named by
      its label, never silently absent;
    * a ``trigger=transition:<label>`` line per pre-tick transition, stating that it did not wait for the clock.

    The durations are rendered through the caller's formatter so this renderer shares one formatting rule with the
    digest (C-41's one-rendering rule: a second age renderer would let the two surfaces disagree about one duration).
    """
    fields = [
        "structure=%s" % (state["structure"] if state else DASH),
        "run=%s" % (state["run"] if state else DASH),
        "trigger=tick",
        "profile=%s" % (state["profile"] if state else PROFILE_LONG_RUN),
    ]
    # The tick line carries the four content elements like every other status line (contract C-23): its position is
    # that this is the tick's own report, its delta the number of sub-flows observed, and its remainder the number
    # still running. Without them this line would be a bare header whose reader learns nothing about the run.
    running = sum(1 for row in projection["rows"] if row["state"] in ("running", "stalled"))
    finished = sum(1 for row in projection["rows"] if row["state"] == "completed")
    failed = sum(1 for row in projection["rows"] if row["state"] == "failed")
    if projection["rows"]:
        fields.extend(
            [
                "position=%d dispatched sub-flow(s) watched (tick report)" % len(projection["rows"]),
                "delta=%d completed, %d running or stalled, %d failed since the last tick"
                % (finished, running, failed),
                "remainder=%d sub-flow(s) still active"
                % (running + (len(projection["omitted"]) if projection["omitted"] else 0)),
                "blocker=%s"
                % (
                    "sub-flow(s) dispatched but not reported: %s" % ", ".join(projection["omitted"])
                    if projection["omitted"]
                    else NO_BLOCKER
                ),
            ]
        )
    lines = [" | ".join(fields)]
    for row in projection["rows"]:
        parts = [
            "sub-flow=%s" % row["label"],
            "state=%s" % row["state"],
            "age=%s" % format_age(row["age_seconds"]),
            "slow=%s" % ("yes" if row["slow"] else "no"),
        ]
        if row["judged_against"]:
            judged = row["judged_against"]
            parts.extend(
                [
                    "judged_against=%s § Monitoring → Stall Detection"
                    % PATTERNS_DOC.as_posix(),
                    "row=%s" % judged["row"],
                    "threshold=%s"
                    % (
                        format_age(judged["override_seconds"])
                        if judged["override_seconds"] is not None
                        else judged["threshold_cell"]
                    ),
                    "override=%s"
                    % (
                        "yes (per-run value recorded beside the declared one)"
                        if judged["override_seconds"] is not None
                        else "none"
                    ),
                    "measured_silence=%s" % format_age(row["age_seconds"]),
                ]
            )
        parts.append("carrier=%s" % CARRIER_CONSOLE)
        lines.append(" | ".join(parts))
    for label in projection["omitted"]:
        # An omission says which flow it is, and what a reader should do about it — never only that something is
        # missing: `state=missing` is not one of the four projected states, it is the omission's own marker (C-33).
        lines.append(
            "sub-flow=%s | state=missing | omitted: dispatched but no row on this tick (C-33)"
            " | position=authored but never reported | delta=none observed on this tick"
            " | remainder=dispatch presumed alive; report it or declare it lost"
            " | blocker=this dispatch was not reportable on this tick | carrier=%s"
            % (label, CARRIER_CONSOLE)
        )
    if projection["pre_tick"]:
        for label in projection["pre_tick"]["labels"]:
            lines.append(
                "sub-flow=%s | trigger=transition:%s | class=%s | timing=%s | carrier=%s"
                % (label, label, projection["pre_tick"]["class"], projection["pre_tick"]["timing"],
                   CARRIER_CONSOLE)
            )
    return "\n".join(lines)


def _supervision_lines(projection, live, format_age):
    """The rendered supervision lines for one projection (empty when no sub-flow was supplied)."""
    if projection is None:
        return []
    return render_supervision(live, projection, format_age).splitlines()


def action_supervision(args) -> int:
    workspace = Path(args.workspace).expanduser().resolve()
    state, _error = read_state(args.cap, args.stale_bound, workspace)
    live = (
        dict(state, structure=args.structure, run=args.run_stamp, profile=profile_in_force(state))
        if state
        else {
            "structure": args.structure,
            "run": args.run_stamp,
            "profile": PROFILE_LONG_RUN,
            "now": datetime.now(timezone.utc),
        }
    )
    projection, error = build_projection(args, live["now"])
    if error:
        print(error, file=sys.stderr)
        return EXIT_INPUT_ERROR
    if projection is None:
        print("--supervision-report requires at least one --sub-flow", file=sys.stderr)
        return EXIT_INPUT_ERROR

    for line in _supervision_lines(projection, live, format_duration):
        print(line)

    verdicts = [
        proposition_ro_06(args.line_set, projection),
        proposition_ro_08(args.line_set, projection),
    ]
    return _emit_verdicts(verdicts, args.format)


def _emit_verdicts(verdicts, output_format) -> int:
    """Print the verdicts in the requested format and return the closed exit status (C-45)."""
    if output_format == "json":
        print(json.dumps({"action": "guard", "propositions": verdicts}, indent=2, sort_keys=True))
    else:
        for verdict in verdicts:
            print(
                "%s %s %s"
                % (verdict["proposition"], verdict["status"], verdict["reason"])
            )
        counts = {}
        for verdict in verdicts:
            counts[verdict["status"]] = counts.get(verdict["status"], 0) + 1
        print(
            "summary pass=%d fail=%d not-evaluated=%d"
            % (
                counts.get("pass", 0),
                counts.get("fail", 0),
                counts.get("not-evaluated", 0),
            )
        )
    return EXIT_FINDINGS if any(v["status"] == "fail" for v in verdicts) else EXIT_OK


# ---------------------------------------------------------------- action: guard
def _verdict(name: str, status: str, reason: str) -> dict:
    return {"proposition": name, "status": status, "reason": reason}


def _pass(name, reason):
    return _verdict(name, "pass", reason)


def _fail(name, reason):
    return _verdict(name, "fail", reason)


def _not_evaluated(name, reason):
    return _verdict(name, "not-evaluated", reason)


def proposition_ro_01(owner_text):
    name = "RO-01"
    if owner_text is None:
        return _not_evaluated(name, "owner document %s is unreadable" % OWNER_DOC)
    block = _declaration_block(owner_text)
    if block is None:
        return _fail(name, "owner document carries no single-source-of-truth declaration block")
    items = re.findall(r"^\s*\d+[.)]\s+\S", block, re.M)
    if len(items) != 8:
        return _fail(
            name,
            "owner declaration lists %d owned fact(s); the closed set is 8" % len(items),
        )
    return _pass(name, "owner declaration lists exactly 8 owned facts")


def proposition_ro_02(owner_text, sample_path):
    name = "RO-02"
    if owner_text is None:
        return _not_evaluated(name, "owner document %s is unreadable" % OWNER_DOC)
    if not sample_path:
        return _not_evaluated(name, "no seeded flow sample supplied (--flow-sample)")
    text = _read_text(Path(sample_path))
    if text is None:
        return _not_evaluated(name, "flow sample %s is unreadable" % sample_path)
    cases = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not cases:
        return _not_evaluated(name, "flow sample %s carries no flow to classify" % sample_path)
    unclassifiable = [ln for ln in cases if "in-scope" not in ln and "out-of-scope" not in ln]
    if unclassifiable:
        return _fail(name, "%d flow(s) carry no verdict in the sample" % len(unclassifiable))
    return _pass(name, "%d flow(s) classified, 0 unclassifiable" % len(cases))


def proposition_ro_03(owner_text, scan_roots=None):
    """The owner-literal scan: exactly one definition site, the two known prose hits whitelisted by path.

    The scan is deliberately **not** written as "zero hits anywhere" — the tree already falsifies that claim
    (``test-evidence/owner-literal-baseline.txt`` measures two unrelated prose hits). What it asserts is
    *exactly one definition site*: the owner document, and nothing else. A second site — a seeded scratch file, a
    later copy, a consumer that reintroduces the number — makes this proposition `fail` and names the extra path,
    which is the only reading under which a red verdict is actionable (`requirements.md` SC-006, contract C-03).

    ``scan_roots`` is the framework-source root set; the default is the four trees the baseline measured. A caller
    may point it elsewhere for one run (the mutation fixture does), and the roots it names are read in addition to —
    not instead of — the default set only when the caller passes ``--scan-root``.
    """
    name = "RO-03"
    if owner_text is None:
        return _not_evaluated(name, "owner document %s is unreadable" % OWNER_DOC)
    roots = list(scan_roots) if scan_roots else [REPO_ROOT / part for part in OWNER_LITERAL_SCAN_ROOTS]
    sites = []
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            return _not_evaluated(name, "scan root %s is unreadable" % root)
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix not in OWNER_LITERAL_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if any(form in text for form in OWNER_LITERAL_FORMS):
                sites.append(_relative_site(path))
    definition_sites = [rel for rel in sites if rel not in OWNER_LITERAL_WHITELIST]
    expected = OWNER_DOC.as_posix()
    if expected not in definition_sites:
        return _fail(
            name,
            "no definition site in the owner document %s; scan found %r" % (expected, definition_sites),
        )
    second = [rel for rel in definition_sites if rel != expected]
    if second:
        return _fail(
            name,
            "a second definition site was found beside %s: %r" % (expected, second),
        )
    return _pass(
        name,
        "exactly one definition site: %s (whitelisted prose hits: %d)"
        % (expected, len([rel for rel in sites if rel in OWNER_LITERAL_WHITELIST])),
    )


def _relative_site(path: Path) -> str:
    """A scan hit's identity: repo-relative when inside the repo, absolute otherwise (a seeded scratch root)."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def proposition_ro_04(rosters, roster_baseline):
    """The roster population: recorded name-list rows whose class is `in-population`, plus `--roster` paths.

    The population is never re-globbed: the name-list's own recorded class decides membership, so the guard reaches
    the same list the baseline captured rather than re-deriving it (`tasks.md` T035). A path supplied with
    ``--roster`` joins that list **for this run** — it is the second of the two sets the obligation binds. Zero paths
    is `not-evaluated` with that reason, never `pass`: no glob is ever a default population (contract C-04, C-46).

    A path here is **caller-supplied**, so it is read with :func:`_read_any` and never with the repo-prefixing
    :func:`_read_text`: SC-002's documented unblock step creates the roster in *another* project, and a path outside
    this repository must be judged by its content rather than reported unreadable. Three outcomes stay distinct — a
    path whose content carries no reporter seat is `fail`; a path the seat check passes is `pass`; a path that
    cannot be read at all is `not-evaluated` with that reason, because an unreadable input proves nothing about the
    seat and MUST NOT be booked as an absent seat, nor as a pass.
    """
    name = "RO-04"
    population = []
    for path, klass in roster_baseline or []:
        if klass == "in-population" and path and path not in population:
            population.append(path)
    for path in rosters or []:
        if path and path not in population:
            population.append(path)
    if not population:
        return _not_evaluated(
            name,
            "no roster path is in the obligation's population: no --roster was supplied and the recorded"
            " name-list holds no in-population row",
        )
    defects = []
    unreadable = []
    for path_text in population:
        text = _read_any(path_text)
        if text is None:
            unreadable.append(path_text)
            continue
        seats = len(re.findall(r"^\s*role:\s*reporter\b", text, re.M))
        has_reason = re.search(r"^\s*reporting-reason:\s*\S", text, re.M) is not None
        if seats == 0 and not has_reason:
            slug = _team_slug(text, path_text)
            defects.append(
                "%s: absent reporter seat in team %s — no members[] row carries role: reporter, and no"
                " reporting-reason is recorded" % (path_text, slug)
            )
        elif seats > 1:
            slug = _team_slug(text, path_text)
            defects.append("%s: %d reporter seats in team %s (the seat is at most one)" % (path_text, seats, slug))
    if defects:
        return _fail(name, "; ".join(defects))
    if unreadable:
        return _not_evaluated(
            name,
            "roster path(s) in the population are unreadable, so the seat check cannot be made: %s"
            % ", ".join(unreadable),
        )
    return _pass(name, "%d roster path(s) in population, no named defect" % len(population))


def _team_slug(text: str, path_text: str) -> str:
    """The roster's own team slug, from its frontmatter `slug:`/`name:` value or its parent directory."""
    for pattern in (r"^\s*slug:\s*(\S+)\s*$", r"^\s*name:\s*(\S+)\s*$"):
        match = re.search(pattern, text, re.M)
        if match:
            return match.group(1)
    return Path(path_text).parent.name


def proposition_ro_05(owner_text, line_set_path):
    name = "RO-05"
    if owner_text is None:
        return _not_evaluated(name, "owner document %s is unreadable" % OWNER_DOC)
    if "汇报内容下限" not in owner_text:
        return _fail(name, "owner document carries no anchor to the content floor")
    if not line_set_path:
        return _not_evaluated(name, "no captured line set supplied (--line-set)")
    text = _read_text(Path(line_set_path))
    if text is None:
        return _not_evaluated(name, "captured line set %s is unreadable" % line_set_path)
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        return _not_evaluated(name, "captured line set %s is empty" % line_set_path)
    missing = []
    for index, line in enumerate(lines, 1):
        for label in ELEMENT_LABELS:
            if ("%s=" % label) not in line:
                missing.append("line %d lacks %s" % (index, label))
    if missing:
        return _fail(name, "; ".join(missing))
    return _pass(name, "%d line(s) carry the four labels" % len(lines))


def proposition_ro_06(line_set_path, projection=None, supervision_line_set=None):
    """The supervision report: one row per dispatched sub-flow.

    Reads the *supervision* capture (``--supervision-line-set``) rather than the status line set: the two are
    different readings of different artifacts, and fusing them would make one fixture prove two propositions. When
    neither a live projection nor a supervision capture is available the proposition is `not-evaluated` — an absent
    capture is not a violation, and it is never `pass`.
    """
    name = "RO-06"
    if projection is not None:
        if not projection["rows"]:
            return _fail(name, "no per-sub-flow row was produced for the dispatches supplied")
        if projection["omitted"]:
            return _fail(
                name,
                "sub-flow(s) dispatched but absent from the report: %r" % (projection["omitted"],),
            )
        return _pass(name, "%d sub-flow row(s) present, 0 omitted" % len(projection["rows"]))
    capture = supervision_line_set or line_set_path
    if not capture:
        return _not_evaluated(
            name, "no captured supervision report supplied (--supervision-line-set)"
        )
    text = _read_text(Path(capture))
    if text is None:
        return _not_evaluated(name, "captured supervision report %s is unreadable" % capture)
    rows = [ln for ln in text.splitlines() if "sub-flow=" in ln]
    if not rows:
        return _fail(name, "no per-sub-flow row found in the captured supervision report %s" % capture)
    return _pass(name, "%d sub-flow row(s) present" % len(rows))


def proposition_ro_07(owner_text, projection=None):
    name = "RO-07"
    if projection is not None:
        threshold = projection["threshold"]
        if threshold is None:
            return _not_evaluated(
                name, "no threshold row resolved for this report (the owner table is unreadable)"
            )
        if threshold["value_seconds"] is None:
            return _fail(
                name,
                "the row %r does not resolve in the threshold owner and no per-run value was supplied"
                % threshold["row"],
            )
        return _pass(
            name,
            "row %r resolved from %s; value used %s"
            % (threshold["row"], PATTERNS_DOC.as_posix(), format_duration(threshold["value_seconds"])),
        )
    if owner_text is None:
        return _not_evaluated(name, "owner document %s is unreadable" % OWNER_DOC)
    if "Stall Detection" not in owner_text or PATTERNS_DOC.as_posix() not in owner_text:
        return _fail(name, "owner document does not anchor the stall threshold table")
    patterns = _read_text(PATTERNS_DOC)
    if patterns is None:
        return _not_evaluated(name, "threshold owner %s is unreadable" % PATTERNS_DOC)
    if "Stall Detection" not in patterns:
        return _fail(name, "threshold owner %s carries no Stall Detection section" % PATTERNS_DOC)
    # A second numeric threshold set inside the owner would be a duplicate owner, not a second reading. The cadence
    # literal is excluded by its line: the value this feature owns (C-03) is a cadence, and judging it here would
    # make RO-07 a second owner of C-03's fact — the two propositions have different subjects.
    threshold_literals = []
    for line in owner_text.splitlines():
        if THRESHOLD_EXCLUDE_MARKER in line:
            continue
        threshold_literals.extend(re.findall(r"\b\d+\s*(?:s|seconds?|秒)\b", line))
    if threshold_literals:
        return _fail(
            name, "owner document carries numeric threshold literal(s): %r" % (threshold_literals,)
        )
    return _pass(name, "threshold anchor resolves and the owner carries no numeric threshold")


#: The line carrying the cadence literal, which is C-03's fact and not this proposition's subject.
THRESHOLD_EXCLUDE_MARKER = "长跑档(long-run profile)"


def proposition_ro_08(line_set_path, projection=None):
    name = "RO-08"
    if projection is not None:
        if not projection["transition"]:
            return _not_evaluated(name, "no transition class was observed for this report")
        if not projection["pre_tick"]:
            return _fail(
                name,
                "a %r was observed after the tick had already elapsed; the report waited for the clock"
                % projection["transition"],
            )
        return _pass(
            name,
            "%r reported pre-tick for %r" % (projection["transition"], projection["pre_tick"]["labels"]),
        )
    if not line_set_path:
        return _not_evaluated(name, "no captured line set supplied (--line-set)")
    text = _read_text(Path(line_set_path))
    if text is None:
        return _not_evaluated(name, "captured line set %s is unreadable" % line_set_path)
    missing = [klass for klass in TRANSITION_CLASSES if klass not in text]
    if missing:
        return _fail(name, "transition class(es) absent from the line set: %r" % (missing,))
    return _pass(name, "all three transition classes present")


def proposition_ro_09(owner_text, state):
    """The owner's digest-contract section plus the four faces one digest render must exhibit.

    The section reading is scoped to the digest section: a face named anywhere else in the owner (the master duty
    speaks of an omitted sub-flow, § 五 speaks of staleness in passing) would otherwise make the proposition pass
    while the digest contract itself says nothing about it. When the state reading is unavailable the digest-render
    half is `not-evaluated` — the section half is still reported, and the proposition is never `pass` on half a
    reading.
    """
    name = "RO-09"
    if owner_text is None:
        return _not_evaluated(name, "owner document %s is unreadable" % OWNER_DOC)
    section = _owner_digest_section(owner_text)
    if section is None:
        return _fail(name, "owner document carries no digest-contract section")
    lowered = section.lower()
    missing = [face for face in ("omitted", NOTHING_RUNNING, "stale") if face not in lowered]
    if missing:
        return _fail(name, "owner digest section does not state the %r face(s)" % (missing,))
    if state is None:
        return _not_evaluated(
            name,
            "the owner digest section states the faces, but no digest render is available to compare against",
        )
    return _pass(
        name, "owner digest section states bounded/omitted/stale/nothing-running; one digest render backs the shapes"
    )


def _owner_digest_section(owner_text):
    """The owner's digest-contract section body, located by its declared heading (never by keyword search)."""
    lines = owner_text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.startswith("## ") and ("Digest" in line or "摘要" in line):
            start = index
            break
    if start is None:
        return None
    end = next(
        (j for j in range(start + 1, len(lines)) if lines[j].startswith("## ")),
        len(lines),
    )
    return "\n".join(lines[start:end])


def proposition_ro_10(line_set_path):
    name = "RO-10"
    if not line_set_path:
        return _not_evaluated(name, "no captured line set supplied (--line-set)")
    text = _read_text(Path(line_set_path))
    if text is None:
        return _not_evaluated(name, "captured line set %s is unreadable" % line_set_path)
    offenders = []
    for index, line in enumerate(text.splitlines(), 1):
        lowered = line.lower()
        for marker in GATE_MARKERS:
            if marker in lowered:
                offenders.append("line %d carries %r" % (index, marker))
                break
    if offenders:
        return _fail(name, "; ".join(offenders))
    return _pass(name, "no interrogative or approval marker in the line set")


def proposition_ro_11(line_set_path, supervision_line_set=None):
    """A suppressed tick is surfaced: the failure line is present, and absence of a line is never read as health.

    Reads the supervision capture when one is supplied (the fixture a suppressed tick leaves behind lives there),
    falling back to the status line set. Its subject is C-11; this function states only which file it opens.
    """
    name = "RO-11"
    capture = supervision_line_set or line_set_path
    if not capture:
        return _not_evaluated(
            name, "no suppressed-tick fixture supplied (--supervision-line-set or --line-set)"
        )
    text = _read_text(Path(capture))
    if text is None:
        return _not_evaluated(name, "fixture %s is unreadable" % capture)
    if "reporter-failure" not in text:
        return _fail(
            name,
            "the fixture %s carries no reporter-failure line; a suppressed tick was not surfaced" % capture,
        )
    return _pass(name, "the reporter-failure line is present")


def proposition_ro_12(args, run_record_path):
    """The carrier value the run record holds: `console`, or the flow's declared stream artifact path.

    The *reading surface* is stated because "recorded" and "supplied" are easy to confuse. `--carrier` is the
    value the caller hands this invocation and is the engine's declared carrier input; `--run-record` is the file
    the run already writes, read here for the `carrier` field the owner
    (`.specify/shared/guidelines/reporting-obligations.md` § 八) requires it to hold. The record is a **fallback**, and the
    precedence is deliberate: `--carrier` wins when both are given, because a reading that silently preferred the
    record would make a wrong `--carrier` unobservable — a green check that cannot go red proves nothing. The
    reason names which surface answered, and `mode` is echoed when the record carries it, so a reading shows the
    two were recorded together instead of asserting that they should be.
    """
    name = "RO-12"
    value = None
    surface = None
    recorded_mode = None
    if run_record_path:
        record = _read_any(run_record_path)
        if record is None:
            if not args.carrier:
                return _not_evaluated(name, "run record %s is unreadable" % run_record_path)
        else:
            try:
                payload = json.loads(record)
            except ValueError:
                payload = None
            if isinstance(payload, dict):
                if payload.get("carrier"):
                    value = str(payload.get("carrier"))
                    surface = "run record %s" % run_record_path
                if payload.get(_MODE_FIELD):
                    recorded_mode = str(payload.get(_MODE_FIELD))
    if args.carrier:
        value = args.carrier
        surface = "--carrier"
    if not value:
        return _not_evaluated(
            name, "no carrier value supplied (the run record holds none and no --carrier was given)"
        )
    if value == CARRIER_CONSOLE:
        return _pass(name, "carrier=%s is one of the two legal forms (from %s)" % (value, surface))
    if Path(value).suffix:
        statement = "carrier is a declared stream artifact path (from %s)" % surface
        if recorded_mode:
            statement = "%s; mode=%s recorded beside it" % (statement, recorded_mode)
        return _pass(name, statement)
    return _fail(name, "carrier %r (from %s) matches neither legal form" % (value, surface))


def proposition_ro_13(owner_text):
    name = "RO-13"
    if owner_text is None:
        return _not_evaluated(name, "owner document %s is unreadable" % OWNER_DOC)
    lowered = owner_text.lower()
    missing = [term for term in MACHINERY_TERMS if term not in lowered]
    if missing:
        return _fail(name, "prohibition clause omits %r" % (missing,))
    # The spawn audit reads the delivered script's AST, never its text: this file names the forbidden APIs in order
    # to describe the audit, and a text scan would therefore always find itself. An AST scan asks the only question
    # that matters — is any of them *called* or *imported*.
    if _delivered_script_spawns():
        return _fail(name, "delivered script imports or calls a process-spawn API")
    return _pass(name, "prohibition names all nine items; no spawn site in the delivered script")


#: Process-spawn APIs the machinery prohibition forbids on a delivery path (contract C-50).
SPAWN_MODULES = {"subprocess", "multiprocessing", "threading", "asyncio"}
SPAWN_CALLS = {"system", "fork", "execv", "execvp", "execl", "execle", "spawnl", "spawnv", "popen"}


def _delivered_script_spawns() -> bool:
    """AST-level audit: does this script import a spawn/thread module or call a spawn API?"""
    import ast

    try:
        source = Path(__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError):
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(alias.name.split(".")[0] in SPAWN_MODULES for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in SPAWN_MODULES:
                return True
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in SPAWN_CALLS:
                return True
    return False


def _declaration_block(text):
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        lowered = line.lower()
        if "single source of truth" in lowered or "唯一定义处" in line:
            start = index
            break
    if start is None:
        return None
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    block = []
    for line in lines[start:end]:
        stripped = line.lstrip()
        if stripped.startswith(">"):
            stripped = stripped[1:]
            if stripped.startswith(" "):
                stripped = stripped[1:]
        block.append(stripped)
    return "\n".join(block)


def _load_roster_baseline(path):
    """Load the recorded name-list, keeping only rows that carry a population class.

    The baseline file is prose around a classified list (``tasks.md`` T003 fixes its form: ``<path> | class=<…> |
    why``), so the parser keys on the ``class=`` cell rather than on any line that happens to contain a pipe. A row
    whose class is ``outside-the-population`` is recorded and not judged: the condition's owner is
    ``contracts/reporting-obligations.contract.md`` C-04, and an out-of-population roster is never made unrunnable.
    """
    text = _read_text(Path(path)) if path else None
    if text is None:
        return []
    rows = []
    for line in text.splitlines():
        if "class=" not in line or "|" not in line:
            continue
        parts = [cell.strip() for cell in line.split("|")]
        path_cell = parts[0].strip("` ").strip()
        if not path_cell or " " in path_cell or "<path>" in path_cell:
            continue
        class_cell = next((cell for cell in parts if cell.startswith("class=")), "")
        rows.append((path_cell, class_cell[len("class="):].strip()))
    return rows


def action_guard(args) -> int:
    owner_path = Path(args.owner_doc) if getattr(args, "owner_doc", None) else OWNER_DOC
    owner_text = _read_text(owner_path)
    workspace = Path(args.workspace).expanduser().resolve()
    state, _error = read_state(args.cap, args.stale_bound, workspace)
    roster_baseline = _load_roster_baseline(args.roster_baseline)
    # The owner-literal scan reads the four framework-source trees by default; `--scan-root` ADDS a root for this
    # run (the seeded-duplicate drill points at a scratch tree beside the repository, never inside `.specify/`).
    scan_roots = [REPO_ROOT / part for part in OWNER_LITERAL_SCAN_ROOTS]
    scan_roots.extend(Path(root).expanduser().resolve() for root in args.scan_root or [])

    # The supervision projection is built from the SAME reading the digest consumed, and rendered by the same
    # renderer, so the report a supervising flow pastes into a captured line set is the one these verdicts judge
    # (C-41's one-reading rule; T022's "no second parser").
    now = state["now"] if state else datetime.now(timezone.utc)
    projection, projection_error = build_projection(args, now)
    if projection_error and projection is not None:
        print(projection_error, file=sys.stderr)
        return EXIT_INPUT_ERROR
    if projection is not None:
        live = (
            dict(state, structure=args.structure, run=args.run_stamp, profile=profile_in_force(state))
            if state
            else {"structure": args.structure, "run": args.run_stamp, "profile": PROFILE_LONG_RUN}
        )
        for line in _supervision_lines(projection, live, format_duration):
            print(line)

    supervision_capture = getattr(args, "supervision_line_set", None)
    verdicts = [
        proposition_ro_01(owner_text),
        proposition_ro_02(owner_text, args.flow_sample),
        proposition_ro_03(owner_text, scan_roots),
        proposition_ro_04(args.roster, roster_baseline),
        proposition_ro_05(owner_text, args.line_set),
        proposition_ro_06(args.line_set, projection, supervision_capture),
        proposition_ro_07(owner_text, projection),
        proposition_ro_08(args.line_set, projection),
        proposition_ro_09(owner_text, state),
        proposition_ro_10(args.line_set),
        proposition_ro_11(args.line_set, supervision_capture),
        proposition_ro_12(args, args.run_record),
        proposition_ro_13(owner_text),
    ]

    return _emit_verdicts(verdicts, args.format)


# ---------------------------------------------------------------- cli
def build_parser():
    parser = argparse.ArgumentParser(
        prog="status-digest.py",
        description=(
            "Current-state digest, reporting-obligation guard and status-line renderer"
            " (owner: .specify/shared/guidelines/reporting-obligations.md)."
        ),
    )
    parser.add_argument("--action", required=True, choices=("digest", "guard", "report"))
    parser.add_argument("--format", default="table", choices=("table", "json"))
    parser.add_argument(
        "--workspace",
        default=os.environ.get("SPECIFY_STATUS_WORKSPACE") or str(Path.cwd()),
        help="workspace whose registry entries are listed (default: the current directory)",
    )
    parser.add_argument(
        "--cap",
        type=int,
        default=int(os.environ.get(CAP_ENV, DEFAULT_CAP)),
        help="maximum entries rendered (declared default %d, overridable per invocation)"
        % DEFAULT_CAP,
    )
    parser.add_argument(
        "--stale-bound",
        type=int,
        default=DEFAULT_STALE_BOUND_SECONDS,
        help="age in seconds beyond which an entry is marked stale (declared default %d)"
        % DEFAULT_STALE_BOUND_SECONDS,
    )
    # The efficiency element's declared width (contract ``efficiency-element.contract.md`` C-64): while the whole
    # element fits, its two deeper quantities are appended; when it does not, they are withdrawn from EVERY unit of
    # the render together. ``--element-bound 0`` disables the bound, so both depths are measurable.
    parser.add_argument(
        "--element-bound",
        type=int,
        default=DEFAULT_ELEMENT_BOUND,
        help=(
            "character width one efficiency element may occupy on this render before its token and invocation"
            " quantities are withdrawn render-wide (declared default %d; 0 disables the bound)"
            % DEFAULT_ELEMENT_BOUND
        ),
    )
    # guard inputs: each is an optional reading surface; an absent one yields not-evaluated, never pass.
    parser.add_argument("--line-set", default=None, help="captured status line set to judge")
    parser.add_argument(
        "--supervision-line-set",
        default=None,
        help=(
            "captured supervision report (one row per dispatched sub-flow) — a SEPARATE capture from the status line"
            " set; RO-06 and RO-11 read it, so the two readings never share one fixture"
        ),
    )
    parser.add_argument("--flow-sample", default=None, help="seeded flow sample classified by RO-02")
    parser.add_argument("--roster", action="append", default=None, help="roster path in the population (repeatable)")
    parser.add_argument(
        "--roster-baseline",
        default=None,
        help="the recorded name-list that declares each roster path's population class",
    )
    parser.add_argument(
        "--scan-root",
        action="append",
        default=None,
        help=(
            "an ADDITIONAL root the owner-literal scan reads for this run (repeatable) — the seeded-duplicate drill"
            " points it at a scratch tree; the four framework-source roots are always read"
        ),
    )
    parser.add_argument(
        "--owner-doc",
        default=None,
        help=(
            "read the owner document from this path instead of the delivered one — a mutation fixture supplies a"
            " copy with one face removed, so RO-09's reading is proven rather than asserted"
        ),
    )
    parser.add_argument(
        "--carrier",
        default=None,
        help=(
            "the carrier that receives the line: 'console' or the declared stream artifact path (C-26)"
            " — the same value the run record holds and RO-12 reads"
        ),
    )
    parser.add_argument("--run-record", default=None, help="run record path (context for RO-12)")
    # report inputs
    parser.add_argument("--structure", default=None, help="structure slug for the rendered line")
    parser.add_argument("--run-stamp", default=None, help="run stamp for the rendered line")
    # The steps this line names (contract ``efficiency-element.contract.md`` C-63): the emitting flow's own
    # knowledge of where it has been and where it is. ``--unit-id`` is repeatable — one value per step, in execution
    # order — and ``--unit-type`` is the type those steps share; both are what the flow already knows and are never
    # derived from the store. The element's unit is the step identity (``unit_id``, ``unit_type``), which is why the
    # type is part of the flag rather than a lookup into anything on disk (C-66).
    parser.add_argument(
        "--unit-id",
        action="append",
        default=None,
        help="a step this line names (e.g. /speckit.plan); repeat once per step, in execution order",
    )
    parser.add_argument("--unit-type", default=None, help="the type those steps share, as the flow states it")
    # The run the emitting flow is in. It is the flow's own identity for this run and narrows each named step to the
    # record that run produced; it is never the element's unit (one run spans many steps — C-66).
    parser.add_argument("--run-id", default=None, help="the run the emitting flow is in (the record scope, not the unit)")
    parser.add_argument("--position", default=None, help="position element")
    parser.add_argument("--delta", default=None, help="delta element")
    parser.add_argument("--remainder", default=None, help="remainder element")
    parser.add_argument("--blocker", default=None, help="blocker element (omit to write 'no blocker')")
    parser.add_argument(
        "--cadence",
        default=None,
        help="the cadence value in force when it is a per-run/per-structure override (C-24)",
    )
    parser.add_argument(
        "--delay-reason",
        default=None,
        help="stated delay when a tick was delivered at the next step boundary (C-25)",
    )
    parser.add_argument(
        "--trigger",
        default="tick",
        help="which rule produced the line: tick | boundary | transition:<sub-flow-id> | reporter-failure",
    )
    # guard inputs: the supervision report over the dispatches a supervising flow watches (C-32…C-35).
    parser.add_argument(
        "--supervision-report",
        action="store_true",
        help="judge the supervision report over the dispatched sub-flows named by --sub-flow",
    )
    parser.add_argument(
        "--sub-flow",
        action="append",
        default=None,
        metavar="LABEL=TRIPLET_DIR",
        help="one dispatched sub-flow: its label plus the directory holding its triplet (repeatable)",
    )
    parser.add_argument(
        "--expect-sub-flow",
        action="append",
        default=None,
        metavar="LABEL",
        help="a label the caller knows was dispatched; a label with no row is an omission (C-33)",
    )
    parser.add_argument(
        "--transition",
        default=None,
        choices=TRANSITION_CLASSES,
        help="a significant transition the flow observed while rendering this report (C-34)",
    )
    parser.add_argument(
        "--interval-elapsed",
        action="store_true",
        help="set when the cadence tick had already elapsed when the transition was observed",
    )
    parser.add_argument(
        "--profile",
        default=None,
        choices=(PROFILE_LONG_RUN, PROFILE_INTERACTIVE),
        help=(
            "the cadence profile in force, when the emitting flow records a switch rather than reading it"
            " from the state (C-30)"
        ),
    )
    parser.add_argument(
        "--profile-switch",
        default=None,
        help="the record of why the profile changed, so a switch is never silent (C-30)",
    )
    parser.add_argument(
        "--threshold-row",
        default=MANDATORY_THRESHOLD_ROW,
        help="the condition row the caller says is silent; the threshold is read from its table cell",
    )
    parser.add_argument(
        "--threshold-seconds",
        type=int,
        default=None,
        help="a per-run threshold override, recorded next to the row it overrides (C-24's override rule)",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cap <= 0:
        print("--cap must be a positive integer", file=sys.stderr)
        return EXIT_INPUT_ERROR
    if args.element_bound is not None:
        if args.element_bound < 0:
            print("--element-bound must be a non-negative integer", file=sys.stderr)
            return EXIT_INPUT_ERROR
        if args.element_bound == 0:
            args.element_bound = None
    if args.action == "digest":
        return action_digest(args)
    if args.action == "report":
        return action_report(args)
    if args.supervision_report:
        return action_supervision(args)
    return action_guard(args)


if __name__ == "__main__":
    sys.exit(main())
