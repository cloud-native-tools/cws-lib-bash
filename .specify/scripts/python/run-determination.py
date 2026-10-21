#!/usr/bin/env python3
"""Run Determination engine (运行判定) for Spec Kit.

One completed run reaches wrap-up; this engine evaluates four measured
quantities for it — token 消耗, 耗时, 制品正确性 and 满意度 — and emits exactly
one ``run_determination`` record. The record *is* the 改点 (owner:
``.specify/memory/glossary.md`` → `改点`): an observation sensor inside the
improve flow, never a feedback entry and never an intervention ledger.

Program-First (``.specify/shared/guidelines/token-efficiency.md`` § 程序优先) is the whole
reason this file exists: every fixed-rule judgment below — source-hierarchy
resolution, name-level set difference, literal-substring evidence search, the
satisfaction decision table, the trigger conjunction — is computed here, and the
model supplies only the coarse classifications it is the sole competent judge of
(``--complexity``, ``--qualification``, ``--user-turn-class``,
``--unresolved-red``). Summary-First (§ 摘要优先) binds the read side: this
engine reads originals freely and emits projections only.

Ownership (``.specify/shared/guidelines/one-source-of-truth.md``, tier 1 = code). This
module is the code-side owner of the ``run_determination`` record schema and of
every value domain the program branches on. The design-time owner of the four
quantities' 判定口径, the three lanes' read surfaces, the two consumption points
and the SI-4 routing conclusion is the dated S1 record at
``.specify/teams/.work/session-driven-self-improvement/outputs/judgment-contract.md``,
which migrates those facts to the landed framework surfaces named in its header
block and MUST NOT be cited as current reality afterwards.

Deliberately reached by reference, never restated here:

* Exit codes — the house table, owned by the ``EXIT_*`` constants shared across
  ``.specify/scripts/python/`` engines and by STR-007 in
  ``.specify/specs/053-machine-decidable-artifacts/requirements.md`` § Shared
  Strings. One code never carries two meanings across actions of this binary.
* ``not_evaluated`` and the comparison words — owned by STR-004 (same file) and
  ``.specify/shared/workflow/self-improvement-workflow.md`` SI-8.
* The four feedback red lines and the never-solicit line — owned by
  ``.specify/shared/workflow/feedback-step.md`` § Positioning & Red Lines.
* The name-level baseline form, red-first evidence, mutation drill and the
  anti-vacuity sentinel — owned by ``.specify/memory/glossary.md``.
* Which agent CLIs have a resolvable session store, and which do not — owned by
  ``STORE_RESOLVERS`` / ``UNSUPPORTED_TOOL_HINTS`` in
  ``.specify/scripts/python/history-utils.py``.
* The memory store's layout, entry format and index — owned by
  ``.specify/scripts/python/memory-utils.py``, which is the only writer this engine uses.
* The evidence store's run layout and freshness gate — owned by
  ``.specify/scripts/python/evidence-utils.py``.
* ``should_prompt`` and its threshold — owned by ``.specify/scripts/python/feedback-utils.py``.
  This engine composes with it and never re-implements it.

Hard separation from 情境评估 (Situational Assessment, owner
``.specify/shared/guidelines/proactive-trigger.md``): the two are structural siblings with
disjoint jobs. This engine writes no per-turn row, adds no situation or signal
vocabulary, and never calls that engine.

Actions:
  determine   write one record for the run that just reached wrap-up; also
              settles the latest unsettled record of the same unit when
              --prev-user-turn-class is supplied
  settle      amend the satisfaction axis of one already-persisted record
  history     read-only projection of past records (never record bodies)

No aggregate score exists in this engine and none may be added: a scalar roll-up
is rejected by ``.specify/shared/guidelines/fast-fail.md`` § 范围限制 and by the B2
adjudication in ``.specify/teams/session-driven-self-improvement/team.md``.
The only roll-up is the boolean ``passive_trigger.trigger_feedback``.

Zero network. Stdlib only. No interactive surface of any kind.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Exit codes: the house table. Owner is code (the EXIT_* constants shared across
# .specify/scripts/python/ engines) plus STR-007; see the module docstring.
EXIT_OK = 0
EXIT_INPUT_ERROR = 2
EXIT_NOT_FOUND = 3
EXIT_INVALID = 4

RECORD_KIND = "speckit.run-determination"
SCHEMA_VERSION = 1
ENGINE_REL_PATH = ".specify/scripts/python/run-determination.py"

ACTIONS = ("determine", "settle", "history", "args-manifest")

# --- argument manifest (063 C-22) ---------------------------------------------
# Per-action required/source classification. "required" = flags this engine
# itself validates as required for the action (the SAME lists the one-shot
# missing-argument check consumes — C-23); "source" = run-evidence inputs the
# caller may carry. `--action args-manifest` verifies every listed flag against
# build_parser()'s LIVE option strings before emitting, so a renamed/removed
# parser flag can never leave a stale manifest behind (parser = single source
# of truth). The compile-embeds renderer consumes this manifest; it holds no
# argument table of its own (063 C-21).
ARG_MANIFEST = {
    "determine": {
        "required": ["--unit-id", "--run-id", "--complexity"],
        "source": [
            "--session-file", "--session-rows", "--tool", "--proxy-paths",
            "--token-note", "--elapsed-ms", "--elapsed-note",
            "--names-current", "--names-baseline", "--declared-check",
            "--green-check", "--red-first-refs", "--collected",
            "--prev-user-turn-class", "--unresolved-red", "--red-source",
        ],
    },
    "settle": {
        "required": ["--unit-id", "--user-turn-class"],
        "source": ["--run-id"],
    },
    "history": {
        "required": ["--target"],
        "source": ["--run-id", "--limit", "--unsettled"],
    },
    "args-manifest": {"required": [], "source": []},
}

# One-shot missing-argument error tails (C-23): the load-bearing guidance the
# old sequential errors carried, kept per flag inside the SINGLE message.
_REQUIRED_GUIDANCE = {
    "--unit-id": "expected /speckit.<command>, skill:<name> or "
                 "custom:<owner>/<name>",
    "--run-id": "the key is (unit_id, run_id)",
    "--complexity": "it is a caller declaration, never an engine derivation",
    "--user-turn-class": "this is the turn that settles the previous run",
    "--target": "the unit whose determination history is requested",
}

# --- value domains (code-owned; see the module docstring) --------------------

AXES = ("token_consumption", "elapsed", "artifact_correctness", "satisfaction")

COMPARISON_VERDICTS = ("improved", "unchanged", "regressed", "not_evaluated")
CORRECTNESS_VERDICTS = ("ok", "regressed", "not_evaluated")
SATISFACTION_VERDICTS = ("accepted", "rejected", "not_evaluated")

#: Closed reason set. Grows only by revising the landed owner, never per caller.
REASONS = (
    "source_unavailable", "not_comparable", "no_baseline", "no_declared_checks",
    "green_unproven", "red_adjacent", "red_state_undeclared", "no_user_input",
    "pending_next_turn", "unqualified_run",
)

QUALIFICATIONS = ("qualified", "trivial", "aborted", "partial")
COMPLEXITIES = ("complex", "simple")
UNIT_TYPES = ("command", "skill", "custom-unit")

TOKEN_SOURCES = ("tool_session_usage", "line_byte_proxy", "unavailable")
ELAPSED_SOURCES = ("tool_session_timestamps", "caller_declared_ms", "unavailable")
UNAVAILABLE = "unavailable"

FAILED_DIFF_STATUSES = ("empty", "non_empty", "not_evaluated")
GREEN_EVIDENCE_STATUSES = ("complete", "partial", "absent", "not_evaluated")

USER_TURN_CLASSES = ("continuation_negative", "continuation_non_negative",
                     "topic_change", "session_end", "no_user_input")
UNRESOLVED_RED_VALUES = ("true", "false", "unknown")
RED_SOURCES = ("engine_nonzero_exit", "surfaced_anomaly_unanswered", "none", "undeclared")
ADJACENT_TURN_CLASSES = ("topic_change", "session_end")

DIRECTIONS = ("improve", "reduce")
SIGNAL_DIRECTIONS = {
    "token_consumption": "reduce",
    "elapsed": "reduce",
    "artifact_correctness": "improve",
    "satisfaction": "improve",
}

PARKED_VIA = ("todo", "spec", "none")
FINDING_STATUS = "observed"

#: Verdicts that need no finding: the axis was measured and came out fine.
GOOD_VERDICTS = ("improved", "unchanged", "ok", "accepted")

# --- Summary-First bounds (projections, never judgment thresholds) -----------

MAX_ADDED_NAMES = 25
MAX_EVIDENCE_REFS = 12
MAX_OUT_OF_SCOPE = 12
MAX_PROJECTED_EVIDENCE = 20
OBSERVATION_LIMIT = 240
MAX_NOTE_CHARS = 500
MAX_RECORD_BYTES = 16384

MEMORY_SCOPE = "session"
MEMORY_TAG = "run-determination"

_USAGE_FIELDS = ("input_tokens", "output_tokens",
                 "cache_read_input_tokens", "cache_creation_input_tokens")

_UNIT_ID_RE = re.compile(
    r"^(?:/speckit\.[a-z0-9][a-z0-9._-]*"
    r"|skill:[a-z0-9][a-z0-9._-]*"
    r"|custom:[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*)$"
)
_ROW_SPAN_RE = re.compile(r"^(\d+):(\d+)$")
_FENCE_RE = re.compile(r"```json\n(.*?)\n```", re.S)

#: § 6 lane 3 projection: a strict allowlist over ``findings.json``. Everything
#: not named here — ``evidenceRefs`` bodies, ``lanes/*`` raw files, the
#: ``manifest.json`` engine block, the file as a whole — is excluded by
#: construction, not by omission.
FINDINGS_PROJECTION_FIELDS = ("id", "lane", "evidenceState", "summary", "signals")

HONESTY_BOUNDARY = (
    "the unresolved-red state is declared by the caller, never derived (§ 5.4)",
    "a wrap-up that never called determine leaves no trace: absence of a record "
    "is not evidence of a clean run (§ 4)",
)

#: **SINGLE SITE for a contract conflict, reported as an anomaly, not settled
#: silently.** § 7 rule 2 states that ``reason`` is non-null *iff* the verdict is
#: ``not_evaluated``. § 5.4 requires the opposite for one row: a default-accept
#: reached while the red state was undeclared carries ``accepted`` **and**
#: ``red_state_undeclared``, so an honest reader can tell a derived accept from an
#: undeclared one and ``--action history`` can count them separately. Both rules
#: are normative and they cannot both hold as written. The § 5.4 requirement wins
#: here because it is the one the contract defends at length and the one OI-9's
#: stated mitigation depends on; the biconditional is narrowed by exactly this
#: triple and by nothing else. ``validate_record`` and the contract test both read
#: this constant, so widening it is a visible edit rather than a quiet one.
REASON_WITH_SUBSTANTIVE_VERDICT = (("satisfaction", "accepted", "red_state_undeclared"),)

# ---------------------------------------------------------------------------
# Open-item seams — each is ONE site, so a later ruling is a local edit
# ---------------------------------------------------------------------------

#: **OI-1, provisional ruling (a) — SINGLE SITE.** An empty failed-set difference
#: whose green checks carry no red-first or mutation-drill evidence reports
#: ``not_evaluated / green_unproven``, NOT ``regressed``. Rationale: an unproven
#: green is an *unverified claim*, not a *measured regression* — reporting
#: ``regressed`` would state a fact nobody measured, and would make "new failure"
#: indistinguishable from "old green never proven" in the record. Both
#: sub-signals stay visible either way, so overriding this to ruling (b) is a
#: one-line edit here and nothing else: ``("regressed", None)``.
GREEN_UNPROVEN_VERDICT = ("not_evaluated", "green_unproven")

#: **OI-2 seam — the record's durable landing point.** Option (a) is active:
#: through ``memory-utils.py`` into ``.specify/memory/session/``. Swap the name
#: here and register the alternative in ``PERSISTENCE_ADAPTERS``; no axis logic,
#: no schema field and no caller flag changes. Adapter contract:
#: ``(workspace_root: Path, record: dict) -> {"persisted": bool, ...}``.
OI2_PERSISTENCE_ADAPTER = "memory-utils-session"

#: **OI-9 seam — how the unresolved-red state is produced.** Option (a) is
#: active: a caller declaration on one flag pair (``--unresolved-red`` /
#: ``--red-source``), the same shape as the existing ``--compliance-done``
#: precedent. A machine-derived producer replaces ``read_red_state`` only; the
#: record field and the satisfaction table are unaffected.
OI9_RED_STATE_INPUT = "caller-declaration"


class DeterminationError(Exception):
    """Base for every rejection this engine defines."""


class InputError(DeterminationError):
    """A malformed call (exit code 2)."""


class NotFoundError(DeterminationError):
    """A referenced record does not exist (exit code 3)."""


class InvalidError(DeterminationError):
    """An artifact exists but cannot be interpreted, or a record this engine
    built violates its own schema rules (exit code 4)."""


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_unit_id(unit_id: str) -> bool:
    return bool(unit_id) and bool(_UNIT_ID_RE.match(unit_id.strip()))


def unit_type_of(unit_id: str) -> str:
    uid = (unit_id or "").strip()
    if uid.startswith("/speckit."):
        return "command"
    if uid.startswith("skill:"):
        return "skill"
    if uid.startswith("custom:"):
        return "custom-unit"
    raise InputError(
        f"invalid --unit-id: {unit_id!r} — expected /speckit.<command>, "
        f"skill:<name> or custom:<owner>/<name>"
    )


def domain_of(axis: str) -> Tuple[str, ...]:
    if axis in ("token_consumption", "elapsed"):
        return COMPARISON_VERDICTS
    if axis == "artifact_correctness":
        return CORRECTNESS_VERDICTS
    if axis == "satisfaction":
        return SATISFACTION_VERDICTS
    raise InputError(f"unknown axis: {axis!r}")


def clip_note(note: Optional[str]) -> Optional[str]:
    """Echo a caller note verbatim, bounded. Never parsed, never judged."""
    if note is None:
        return None
    text = str(note)
    return text if len(text) <= MAX_NOTE_CHARS else text[:MAX_NOTE_CHARS] + " …[clipped]"


_SIBLING_CACHE: Dict[str, Any] = {}


def sibling_engine(filename: str):
    """Load a sibling engine module from this engine's own directory.

    Self-location fires only on a literal component of this file's own resolved
    path, which is the two-hats-safe form: the framework copy finds its siblings
    beside itself in the root tree, the installed runtime copy finds them beside
    itself in the generated mirror, and neither walks up looking for a workspace
    (the walk-up heuristic self-matches in a self-hosting repository).
    """
    if filename in _SIBLING_CACHE:
        return _SIBLING_CACHE[filename]
    path = Path(__file__).resolve().parent / filename
    if not path.is_file():
        raise DeterminationError(f"sibling engine not found beside this one: {path}")
    name = "_rd_" + filename.replace("-", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DeterminationError(f"cannot load sibling engine: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    _SIBLING_CACHE[filename] = module
    return module


def resolve_workspace_root(explicit: Optional[str]) -> Path:
    """Delegate to the memory engine, which owns workspace resolution."""
    if explicit:
        return Path(explicit).resolve()
    try:
        memory = sibling_engine("memory-utils.py")
    except DeterminationError:
        return Path.cwd().resolve()
    return memory.resolve_workspace_root(None)


# ---------------------------------------------------------------------------
# Session-store measurement (§ 5.1 source 1, § 5.2 source 1)
# ---------------------------------------------------------------------------

def probe_session_store(tool: str, project_root: Path) -> Dict[str, Any]:
    """Report store availability honestly, from the resolvers' own verdict."""
    try:
        history = sibling_engine("history-utils.py")
    except DeterminationError as exc:
        return {"tool": tool, "supported": False, "note": str(exc)}
    resolver = history.STORE_RESOLVERS.get(tool)
    if resolver is None:
        return {"tool": tool, "supported": False,
                "note": history.UNSUPPORTED_TOOL_HINTS.get(
                    tool, "no resolver exists for this agent CLI")}
    info = resolver(Path(project_root))
    return {"tool": tool,
            "supported": bool(info.get("supported")),
            "note": info.get("note") or "",
            "session_store": info.get("session_store")}


def read_session_rows(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            rows.append(parsed)
    return rows


def parse_row_span(spec: str, row_count: int) -> Tuple[int, int]:
    match = _ROW_SPAN_RE.match((spec or "").strip())
    if not match:
        raise InputError(f"--session-rows expects START:END (inclusive, 0-based), got {spec!r}")
    start, end = int(match.group(1)), int(match.group(2))
    if start > end:
        raise InputError(f"--session-rows START exceeds END: {spec!r}")
    if end >= row_count:
        raise InputError(
            f"--session-rows {spec!r} exceeds the session's {row_count} row(s); "
            f"a span outside the file cannot be attributed to this run"
        )
    return start, end


def measure_session_usage(rows: Sequence[Dict[str, Any]],
                          span: Tuple[int, int]) -> Optional[Dict[str, int]]:
    """Sum ``message.usage`` over assistant rows inside the declared span.

    Returns None when no row in the span carries a usage counter at all — an
    absent counter is never a zero.
    """
    start, end = span
    totals = {field: 0 for field in _USAGE_FIELDS}
    seen = False
    for row in rows[start:end + 1]:
        message = row.get("message")
        usage = message.get("usage") if isinstance(message, dict) else None
        if not isinstance(usage, dict):
            continue
        for field in _USAGE_FIELDS:
            value = usage.get(field)
            if isinstance(value, int) and not isinstance(value, bool):
                totals[field] += value
                seen = True
    if not seen:
        return None
    totals["total_tokens"] = sum(totals[field] for field in _USAGE_FIELDS)
    return totals


def parse_row_timestamp(value: Any) -> Optional[datetime]:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def measure_session_elapsed_ms(rows: Sequence[Dict[str, Any]],
                               span: Tuple[int, int]) -> Optional[int]:
    """Last row of the span minus first row, in milliseconds.

    Any row in the span without a parseable timestamp degrades the whole
    measurement to None: a partial span would report a duration nobody measured.
    """
    start, end = span
    stamps: List[datetime] = []
    for row in rows[start:end + 1]:
        parsed = parse_row_timestamp(row.get("timestamp"))
        if parsed is None:
            return None
        stamps.append(parsed)
    if not stamps:
        return None
    return int((max(stamps) - min(stamps)).total_seconds() * 1000)


def measure_proxy(paths: Sequence[str]) -> Dict[str, int]:
    """Lines and bytes of a caller-declared read set (§ 5.1 source 2)."""
    lines = 0
    nbytes = 0
    for raw in paths:
        path = Path(raw)
        if not path.is_file():
            raise InputError(f"--proxy-paths entry is not a readable file: {raw}")
        data = path.read_bytes()
        nbytes += len(data)
        lines += data.count(b"\n") + (1 if data and not data.endswith(b"\n") else 0)
    return {"proxy_lines": lines, "proxy_bytes": nbytes}


def token_value(measurement: Dict[str, Any]) -> Optional[int]:
    """The single comparable scalar for the token axis — ONE site.

    Source 1 compares the exact counter total; source 2 compares bytes, which is
    the finer of the two proxy figures the discipline authorizes, with lines
    recorded beside it so a reader sees both.
    """
    if measurement.get("source") == "tool_session_usage":
        return measurement.get("total_tokens")
    if measurement.get("source") == "line_byte_proxy":
        return measurement.get("proxy_bytes")
    return None


def elapsed_value(measurement: Dict[str, Any]) -> Optional[int]:
    if measurement.get("source") == UNAVAILABLE:
        return None
    return measurement.get("ms")


def sources_comparable(current: Optional[str], baseline: Optional[str]) -> bool:
    """ONE site for the mixing rule.

    An exact counter and a line/byte proxy must never meet in one trend, in
    either direction: two reviewers would reach two verdicts. Equality of source
    is the decidable form of that rule.
    """
    if not current or not baseline:
        return False
    if current == UNAVAILABLE or baseline == UNAVAILABLE:
        return False
    return current == baseline


def compare_values(current: int, baseline: int, direction: str) -> str:
    """Exact comparison. No tolerance band exists and none is invented (OI-8)."""
    if current == baseline:
        return "unchanged"
    better = current < baseline if direction == "reduce" else current > baseline
    return "improved" if better else "regressed"


# ---------------------------------------------------------------------------
# § 5.3 — 制品正确性 (artifact correctness ONLY)
# ---------------------------------------------------------------------------

def read_names(path: Optional[str], flag: str) -> Optional[List[str]]:
    """A sorted, de-duplicated FAILED-nodeid list (名字级基线)."""
    if not path:
        return None
    candidate = Path(path)
    if not candidate.is_file():
        if flag == "--names-current":
            raise InputError(f"{flag} is not a readable file: {path}")
        return None  # a missing baseline is the contract's no_baseline case
    names = {line.strip() for line in
             candidate.read_text(encoding="utf-8", errors="replace").splitlines()}
    return sorted(n for n in names if n)


def failed_set_diff(baseline_names: Optional[List[str]],
                    current_names: Optional[List[str]]) -> Dict[str, Any]:
    """``comm -13 baseline current`` computed program-side: names only, never
    pytest output bodies. ``added`` is a bounded projection, not a transcript."""
    if baseline_names is None or current_names is None:
        return {"status": "not_evaluated", "added": [],
                "added_count": None, "truncated": False}
    known = set(baseline_names)
    added = [name for name in current_names if name not in known]
    return {
        "status": "non_empty" if added else "empty",
        "added": added[:MAX_ADDED_NAMES],
        "added_count": len(added),
        "truncated": len(added) > MAX_ADDED_NAMES,
    }


def diff_was_meaningful(current_names: Optional[List[str]],
                        baseline_names: Optional[List[str]],
                        collected: Optional[int]) -> bool:
    """反空真哨兵 on the difference. Without it, "collected nothing" and "passed
    everything" produce the same empty diff — the blind-check class."""
    return bool(current_names) or bool(baseline_names) or bool(collected and collected > 0)


def read_refs_text(paths: Sequence[str]) -> str:
    blobs: List[str] = []
    for raw in paths:
        path = Path(raw)
        if not path.is_file():
            raise InputError(f"--red-first-refs entry is not a readable file: {raw}")
        blobs.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(blobs)


def green_evidence(green_checks: Sequence[str], refs_text: str) -> Dict[str, Any]:
    """One literal-substring search per declared green check — the Program-First
    positive example, not "paste the document and let the model look".

    Zero green checks is ``absent``, never a vacuous ``complete``: "every green
    check carries evidence" is vacuously true over an empty set, and a vacuous
    green is exactly what the sentinel exists to reject.
    """
    if not green_checks:
        return {"status": "absent", "uncovered": []}
    uncovered = [name for name in green_checks if name not in refs_text]
    covered_count = len(green_checks) - len(uncovered)
    if covered_count == 0:
        status = "absent"
    elif uncovered:
        status = "partial"
    else:
        status = "complete"
    return {"status": status, "uncovered": uncovered}


def green_unproven_verdict() -> Tuple[str, Optional[str]]:
    """The OI-1 mapping, read through its single site."""
    return GREEN_UNPROVEN_VERDICT


def evaluate_artifact_correctness(args: argparse.Namespace) -> Dict[str, Any]:
    axis = _axis_skeleton("artifact_correctness")
    declared = list(args.declared_check or [])
    green = list(args.green_check or [])
    for name in green:
        if name not in declared:
            raise InputError(
                f"--green-check {name!r} was not declared via --declared-check; "
                f"a green check outside the declared set cannot be evidenced"
            )
    current_names = read_names(args.names_current, "--names-current")
    baseline_names = read_names(args.names_baseline, "--names-baseline")
    if args.names_baseline and not args.names_current:
        raise InputError("--names-baseline requires --names-current: a baseline "
                         "with nothing to compare against is a malformed call")
    refs_text = read_refs_text(args.red_first_refs or [])

    anything_declared = bool(declared) or current_names is not None or bool(args.names_baseline)
    axis["declared_checks"] = len(declared) if anything_declared else None
    axis["collected"] = args.collected
    axis["failed_set_diff"] = {"status": "not_evaluated", "added": [],
                               "added_count": None, "truncated": False}
    axis["green_evidence"] = {"status": "not_evaluated", "uncovered": []}
    axis["evidence_refs"] = _bounded_refs([args.names_current, args.names_baseline,
                                           *(args.red_first_refs or [])])

    # Verdict mapping, in the contract's precedence order.
    if not axis["declared_checks"]:
        axis["verdict"], axis["reason"] = "not_evaluated", "no_declared_checks"
        return axis
    if baseline_names is None:
        axis["verdict"], axis["reason"] = "not_evaluated", "no_baseline"
        return axis

    diff = failed_set_diff(baseline_names, current_names)
    axis["failed_set_diff"] = diff
    axis["green_evidence"] = green_evidence(green, refs_text)

    if diff["status"] == "non_empty":
        axis["verdict"], axis["reason"] = "regressed", None
        return axis
    if not diff_was_meaningful(current_names, baseline_names, args.collected):
        axis["verdict"], axis["reason"] = "not_evaluated", "no_declared_checks"
        return axis
    if axis["green_evidence"]["status"] == "complete":
        axis["verdict"], axis["reason"] = "ok", None
        return axis
    axis["verdict"], axis["reason"] = green_unproven_verdict()
    return axis


def _bounded_refs(paths: Sequence[Optional[str]]) -> List[str]:
    refs = [str(p) for p in paths if p]
    return refs[:MAX_EVIDENCE_REFS]


# ---------------------------------------------------------------------------
# § 5.4 — satisfaction
# ---------------------------------------------------------------------------

def _build_satisfaction_table() -> Dict[Tuple[str, str], Tuple[str, Optional[str]]]:
    """The decision table as a total function over a closed input domain: no
    "usually", no confidence, no residual case. The hedge 「大部分情况」 is gone."""
    table: Dict[Tuple[str, str], Tuple[str, Optional[str]]] = {}
    for red in UNRESOLVED_RED_VALUES:
        table[("continuation_negative", red)] = ("rejected", None)
        table[("continuation_non_negative", red)] = ("accepted", None)
        table[("no_user_input", red)] = ("not_evaluated", "no_user_input")
    for turn in ADJACENT_TURN_CLASSES:
        table[(turn, "false")] = ("accepted", None)
        table[(turn, "true")] = ("not_evaluated", "red_adjacent")
        # Default-accept survives an undeclared red state, or the axis never
        # fires at all; the reason keeps the two accepts distinguishable and
        # `--action history` counts them separately.
        table[(turn, "unknown")] = ("accepted", "red_state_undeclared")
    missing = ({(c, r) for c in USER_TURN_CLASSES for r in UNRESOLVED_RED_VALUES}
               - set(table))
    if missing:
        raise RuntimeError(f"satisfaction table is not total; uncovered: {sorted(missing)}")
    return table


SATISFACTION_TABLE = _build_satisfaction_table()


def resolve_satisfaction(turn_class: str, red_present: str, red_source: str,
                         qualification: str) -> Dict[str, Any]:
    """Map a caller classification to a verdict. The classification is a semantic
    judgment and belongs to the model; this mapping is a fixed rule and belongs
    here (§ 程序优先 / § 判定边界)."""
    if turn_class not in USER_TURN_CLASSES:
        raise InputError(f"invalid user turn class: {turn_class!r}")
    if red_present not in UNRESOLVED_RED_VALUES:
        raise InputError(f"invalid unresolved-red value: {red_present!r}")
    adjacent = turn_class in ADJACENT_TURN_CLASSES
    if qualification != "qualified":
        verdict, reason = "not_evaluated", "unqualified_run"
    else:
        verdict, reason = SATISFACTION_TABLE[(turn_class, red_present)]
    return {
        "verdict": verdict,
        "reason": reason,
        "user_turn_class": turn_class,
        "unresolved_red": {"present": red_present, "source": red_source},
        "adjacent": adjacent,
        "signal": _signal("satisfaction"),
    }


def read_red_state(args: argparse.Namespace) -> Tuple[str, str]:
    """OI-9 producer seam. B3's two producers are the only legal sources of a
    ``true``; a ``true`` with no named producer is an unusable declaration."""
    present = args.unresolved_red or "unknown"
    source = args.red_source
    expected = {
        "true": ("engine_nonzero_exit", "surfaced_anomaly_unanswered"),
        "false": ("none",),
        "unknown": ("undeclared",),
    }[present]
    if source is None:
        if present == "true":
            raise InputError(
                "--unresolved-red true requires --red-source naming its producer "
                "(engine_nonzero_exit | surfaced_anomaly_unanswered)"
            )
        source = expected[0]
    elif source not in expected:
        raise InputError(
            f"--red-source {source!r} contradicts --unresolved-red {present!r}; "
            f"legal producers for {present!r}: {', '.join(expected)}"
        )
    return present, source


# ---------------------------------------------------------------------------
# Axis assembly
# ---------------------------------------------------------------------------

def _signal(axis: str) -> Dict[str, str]:
    """The ``{key, direction}`` shape of ``expectedSignal`` in
    ``.specify/shared/workflow/evidence-step.md`` § Step E, so a finding can become a
    ledger entry without a translation layer."""
    direction = SIGNAL_DIRECTIONS[axis]
    if direction not in DIRECTIONS:
        raise RuntimeError(f"axis {axis!r} declares a direction outside {DIRECTIONS}")
    return {"key": axis, "direction": direction}


def _axis_skeleton(axis: str) -> Dict[str, Any]:
    return {"verdict": "not_evaluated", "reason": None, "signal": _signal(axis)}


def measure_token_consumption(args: argparse.Namespace,
                              ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Three-tier source hierarchy, tried in order. No absolute target exists
    anywhere in this engine and none is invented (OI-3)."""
    measurement: Dict[str, Any] = {
        "source": UNAVAILABLE,
        "input_tokens": None, "output_tokens": None,
        "cache_read_input_tokens": None, "cache_creation_input_tokens": None,
        "total_tokens": None, "proxy_lines": None, "proxy_bytes": None,
        "note": clip_note(args.token_note),
    }
    span = ctx.get("session_span")
    if span is not None:
        usage = measure_session_usage(ctx.get("session_rows") or [], span)
        if usage is not None:
            measurement["source"] = "tool_session_usage"
            for field in _USAGE_FIELDS:
                measurement[field] = usage[field]
            measurement["total_tokens"] = usage["total_tokens"]
            return measurement
    if args.proxy_paths:
        measurement.update(measure_proxy(args.proxy_paths))
        measurement["source"] = "line_byte_proxy"
        return measurement
    return measurement


def measure_elapsed(args: argparse.Namespace, ctx: Dict[str, Any]) -> Dict[str, Any]:
    measurement: Dict[str, Any] = {
        "source": UNAVAILABLE, "ms": None, "note": clip_note(args.elapsed_note),
    }
    span = ctx.get("session_span")
    if span is not None:
        ms = measure_session_elapsed_ms(ctx.get("session_rows") or [], span)
        if ms is not None:
            measurement["source"] = "tool_session_timestamps"
            measurement["ms"] = ms
            return measurement
    if args.elapsed_ms is not None:
        measurement["source"] = "caller_declared_ms"
        measurement["ms"] = args.elapsed_ms
        return measurement
    return measurement


def resolve_comparison_axis(axis: str, measurement: Dict[str, Any],
                            value_of, baseline_record: Optional[Dict[str, Any]],
                            refs: List[str]) -> Dict[str, Any]:
    body = _axis_skeleton(axis)
    body["measurement"] = measurement
    body["baseline"] = None
    body["evidence_refs"] = refs[:MAX_EVIDENCE_REFS]
    value = value_of(measurement)
    if measurement.get("source") == UNAVAILABLE or value is None:
        # Never ok, never 0, never an estimate, never a figure carried over from
        # another unit's run.
        body["verdict"], body["reason"] = "not_evaluated", "source_unavailable"
        return body
    if baseline_record is None:
        body["verdict"], body["reason"] = "not_evaluated", "no_baseline"
        return body
    baseline_axis = (baseline_record.get("axes") or {}).get(axis) or {}
    baseline_measurement = baseline_axis.get("measurement") or {}
    baseline_value = value_of(baseline_measurement)
    body["baseline"] = {
        "run_id": baseline_record.get("run_id"),
        "source": baseline_measurement.get("source"),
        "value": baseline_value,
    }
    if baseline_value is None or not sources_comparable(measurement["source"],
                                                        baseline_measurement.get("source")):
        body["verdict"], body["reason"] = "not_evaluated", "not_comparable"
        return body
    body["verdict"] = compare_values(value, baseline_value, SIGNAL_DIRECTIONS[axis])
    body["reason"] = None
    return body


def apply_qualification_gate(record: Dict[str, Any]) -> None:
    """L2 of the generalization: an unqualified run can no longer be reported
    green. Measurements stay visible; only the claim is withdrawn."""
    if record.get("qualification") == "qualified":
        return
    for axis in AXES:
        body = record["axes"][axis]
        body["verdict"] = "not_evaluated"
        body["reason"] = "unqualified_run"


# ---------------------------------------------------------------------------
# § 8 / § 10 / § 12 — change point, trigger, passive scope
# ---------------------------------------------------------------------------

def observation_for(axis: str, body: Dict[str, Any]) -> str:
    """One bounded line: what was measured, never what to fix. Counts route; they
    do not conclude (``.specify/shared/workflow/evidence-step.md`` red line 3)."""
    verdict = body.get("verdict")
    reason = body.get("reason")
    if axis in ("token_consumption", "elapsed"):
        measurement = body.get("measurement") or {}
        value_of = token_value if axis == "token_consumption" else elapsed_value
        baseline = (body.get("baseline") or {}).get("value")
        text = (f"{axis} {verdict} via source={measurement.get('source')}: "
                f"current={value_of(measurement)} baseline={baseline}")
    elif axis == "artifact_correctness":
        diff = body.get("failed_set_diff") or {}
        green = body.get("green_evidence") or {}
        text = (f"{axis} {verdict}: failed-set diff {diff.get('status')} "
                f"added={diff.get('added_count')}, green evidence {green.get('status')} "
                f"uncovered={len(green.get('uncovered') or [])} "
                f"declared_checks={body.get('declared_checks')} collected={body.get('collected')}")
    else:
        red = (body.get("unresolved_red") or {}).get("present")
        text = (f"{axis} {verdict}: user_turn_class={body.get('user_turn_class')} "
                f"unresolved_red={red} adjacent={body.get('adjacent')}")
    if reason:
        text += f" reason={reason}"
    return text[:OBSERVATION_LIMIT]


def in_passive_scope(finding: Dict[str, Any], record_unit_id: str,
                     current_unit_id: str) -> bool:
    """§ 12: in scope for the passive turn = this unit, and an axis that was
    actually evaluated in this run. Everything else is recorded, not acted on."""
    return record_unit_id == current_unit_id and finding.get("verdict") != "not_evaluated"


def build_findings(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    for axis in AXES:
        body = record["axes"][axis]
        if body.get("verdict") in GOOD_VERDICTS:
            continue
        findings.append({
            "axis": axis,
            "verdict": body.get("verdict"),
            "reason": body.get("reason"),
            "observation": observation_for(axis, body),
            "signal": _signal(axis),
            "evidence_refs": list(body.get("evidence_refs") or [])[:MAX_EVIDENCE_REFS],
            "status": FINDING_STATUS,
        })
    return findings


def rebuild_change_point(record: Dict[str, Any]) -> None:
    """Recompute the 改点 and the routing bit from the axes as they now stand.
    Settlement changes an axis, so it must also change what the run concluded."""
    findings = build_findings(record)
    record["change_point"] = {
        "id": f"cp-{record['run_id']}",
        "clean": not findings,
        "findings": findings,
    }
    unit_id = record["unit_id"]
    parked: List[Dict[str, Any]] = []
    for finding in findings:
        if in_passive_scope(finding, unit_id, unit_id):
            continue
        if len(parked) >= MAX_OUT_OF_SCOPE:
            break
        # `parked_via: none` is legal and is the honest default: assigning a
        # carrier (todo | spec) is the active flow's job, not this engine's.
        parked.append({"observation": finding["observation"],
                       "parked_via": "none", "ref": None})
    record["passive_trigger"] = {
        "trigger_feedback": derive_trigger_feedback(record["qualification"], record["axes"]),
        "composes_with_should_prompt": True,
        "out_of_scope": parked,
    }


def derive_trigger_feedback(qualification: str, axes: Dict[str, Any]) -> bool:
    """The routing bit — a boolean, not a score. It composes with the feedback
    engine's own ``should_prompt``; neither replaces the other.

    The deliberate asymmetry (a single regressed comparison axis does not fire)
    is the structural noise guard that replaces a tolerance band.
    """
    if qualification != "qualified":
        return False
    verdict = {axis: (axes.get(axis) or {}).get("verdict") for axis in AXES}
    return bool(
        verdict["artifact_correctness"] == "regressed"
        or verdict["satisfaction"] == "rejected"
        or (verdict["token_consumption"] == "regressed"
            and verdict["elapsed"] == "regressed")
    )


# ---------------------------------------------------------------------------
# § 7 — record schema rules
# ---------------------------------------------------------------------------

def validate_record(record: Dict[str, Any]) -> List[str]:
    """The schema rules, enforced by the engine on itself before anything lands."""
    problems: List[str] = []
    if record.get("kind") != RECORD_KIND:
        problems.append(f"kind must be {RECORD_KIND!r}, got {record.get('kind')!r}")
    if record.get("schema_version") != SCHEMA_VERSION:
        problems.append(f"schema_version must be {SCHEMA_VERSION}")
    for key in ("unit_id", "run_id", "determined_at", "complexity", "qualification"):
        if not record.get(key):
            problems.append(f"missing required field: {key}")
    axes = record.get("axes")
    if not isinstance(axes, dict):
        problems.append("axes must be an object")
        return problems
    for axis in AXES:
        if axis not in axes:
            problems.append(f"missing axis: {axis}")
            continue
        body = axes[axis]
        if not isinstance(body, dict):
            problems.append(f"axis {axis} must be an object, never null")
            continue
        verdict = body.get("verdict")
        reason = body.get("reason")
        if verdict not in domain_of(axis):
            problems.append(f"axis {axis}: verdict {verdict!r} outside its domain")
        declared_exception = (axis, verdict, reason) in REASON_WITH_SUBSTANTIVE_VERDICT
        if (reason is not None) != (verdict == "not_evaluated") and not declared_exception:
            problems.append(
                f"axis {axis}: reason must be non-null iff verdict is not_evaluated "
                f"(got verdict={verdict!r} reason={reason!r})"
            )
        if verdict == "not_evaluated" and reason is None:
            problems.append(f"axis {axis}: not_evaluated without a reason")
        if reason is not None and reason not in REASONS:
            problems.append(f"axis {axis}: reason {reason!r} outside the closed set")
        signal = body.get("signal")
        if signal != _signal(axis):
            problems.append(f"axis {axis}: signal must be {_signal(axis)}, got {signal!r}")
        if axis in ("token_consumption", "elapsed"):
            allowed = TOKEN_SOURCES if axis == "token_consumption" else ELAPSED_SOURCES
            source = (body.get("measurement") or {}).get("source")
            if source not in allowed:
                problems.append(f"axis {axis}: measurement source {source!r} "
                                f"outside its closed hierarchy {allowed}")
            if source == UNAVAILABLE:
                measured = [k for k, v in (body.get("measurement") or {}).items()
                            if k not in ("source", "note") and v is not None]
                if measured:
                    problems.append(
                        f"axis {axis}: an unavailable source must carry no measured "
                        f"value, never a fabricated zero; got {sorted(measured)}")
        if axis == "artifact_correctness":
            diff_status = (body.get("failed_set_diff") or {}).get("status")
            if diff_status not in FAILED_DIFF_STATUSES:
                problems.append(f"axis {axis}: failed_set_diff.status {diff_status!r} "
                                f"outside {FAILED_DIFF_STATUSES}")
            green_status = (body.get("green_evidence") or {}).get("status")
            if green_status not in GREEN_EVIDENCE_STATUSES:
                problems.append(f"axis {axis}: green_evidence.status {green_status!r} "
                                f"outside {GREEN_EVIDENCE_STATUSES}")
            if diff_status == "empty" and verdict == "ok" and green_status != "complete":
                problems.append(
                    f"axis {axis}: ok requires the green-evidence conjunction, "
                    f"got {green_status!r}")
    change = record.get("change_point") or {}
    findings = change.get("findings")
    if not isinstance(findings, list):
        problems.append("change_point.findings must be a list")
        findings = []
    if change.get("clean") is not (not findings):
        problems.append("change_point.clean must be true iff findings is empty")
    for position, row in enumerate((record.get("passive_trigger") or {}).get("out_of_scope") or []):
        if row.get("parked_via") not in PARKED_VIA:
            problems.append(f"passive_trigger.out_of_scope[{position}].parked_via "
                            f"{row.get('parked_via')!r} outside {PARKED_VIA}")
        if set(row) != {"observation", "parked_via", "ref"}:
            problems.append(f"passive_trigger.out_of_scope[{position}] has an "
                            f"unexpected key set: {sorted(row)}")
    for position, finding in enumerate(findings):
        if finding.get("status") != FINDING_STATUS:
            problems.append(f"findings[{position}].status must be the constant "
                            f"{FINDING_STATUS!r}, got {finding.get('status')!r}")
        observation = finding.get("observation")
        if not isinstance(observation, str) or not observation or "\n" in observation:
            problems.append(f"findings[{position}].observation must be one bounded line")
        elif len(observation) > OBSERVATION_LIMIT:
            problems.append(f"findings[{position}].observation exceeds the bound")
    if len(json.dumps(record, ensure_ascii=False).encode("utf-8")) > MAX_RECORD_BYTES:
        problems.append(f"record exceeds the {MAX_RECORD_BYTES}-byte bound")
    return problems


def summary_line(record: Dict[str, Any]) -> str:
    """The one line the memory index exposes for lane 1's projection."""
    axes = record["axes"]
    return (f"{record['unit_id']} run={record['run_id']} "
            f"token={axes['token_consumption']['verdict']} "
            f"elapsed={axes['elapsed']['verdict']} "
            f"artifact={axes['artifact_correctness']['verdict']} "
            f"satisfaction={axes['satisfaction']['verdict']}")


def compose_entry_body(record: Dict[str, Any]) -> str:
    """Body = the one-line summary, then the JSON record in a fence. The memory
    engine derives ``summary`` from the first non-empty content line, which is
    what puts the one line into the index projection."""
    payload = json.dumps(record, ensure_ascii=False, indent=2)
    return f"{summary_line(record)}\n\n```json\n{payload}\n```"


def parse_entry_body(text: str) -> Optional[Dict[str, Any]]:
    match = _FENCE_RE.search(text or "")
    if not match:
        return None
    try:
        record = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None
    if not isinstance(record, dict) or record.get("kind") != RECORD_KIND:
        return None
    return record


# ---------------------------------------------------------------------------
# § 6 — lane projections
# ---------------------------------------------------------------------------

def project_findings(findings: Dict[str, Any],
                     limit: int = MAX_PROJECTED_EVIDENCE) -> Dict[str, Any]:
    """The § 6 lane-3 projection: a strict allowlist over ``findings.json``.

    Excluded by construction: ``evidenceRefs`` bodies, ``lanes/*`` raw files, the
    ``manifest.json`` engine block, and the file as a whole. The store holds over
    a hundred files across its run directories; wholesale injection is the exact
    failure Summary-First names.
    """
    evidence = findings.get("evidence") or []
    projected = [
        {field: item.get(field) for field in FINDINGS_PROJECTION_FIELDS}
        for item in evidence[:limit]
        if isinstance(item, dict)
    ]
    return {
        "findingsDigest": findings.get("findingsDigest"),
        "evidence": projected,
        "truncated": len(evidence) > limit,
    }


def probe_evidence_lane(workspace_root: Path, unit_id: str) -> Dict[str, Any]:
    """Lane 3. Freshness is gated by the evidence engine's own ``stale`` flag; an
    over-age run is reported and NOT consumed."""
    try:
        evidence = sibling_engine("evidence-utils.py")
    except DeterminationError:
        return {"state": "unavailable", "digests": []}
    recoverable = (evidence.CliError, OSError, ValueError, KeyError)
    try:
        latest = evidence.action_latest(argparse.Namespace(
            workspace_root=str(workspace_root), target=unit_id,
            max_age_days=evidence.DEFAULT_MAX_AGE_DAYS))
    except recoverable:
        return {"state": "unavailable", "digests": []}
    if not latest.get("found"):
        return {"state": "unavailable", "digests": []}
    if latest.get("stale"):
        return {"state": "stale", "digests": [], "runId": latest.get("runId"),
                "warning": latest.get("warning")}
    try:
        findings = evidence.load_run(workspace_root, latest["runId"])
    except recoverable:
        return {"state": "unavailable", "digests": []}
    projected = project_findings(findings)
    digest = projected.get("findingsDigest")
    return {"state": "available", "digests": [digest] if digest else [],
            "runId": latest.get("runId"),
            "projected_evidence_count": len(projected.get("evidence") or [])}


def project_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """The § 11 *why*-step projection: verdicts, reasons, signals, settlement
    state and the caller-declaration list. Never a record body, never a
    measurement."""
    axes = record.get("axes") or {}
    return {
        "unit_id": record.get("unit_id"),
        "run_id": record.get("run_id"),
        "determined_at": record.get("determined_at"),
        "settled_at": record.get("settled_at"),
        "complexity": record.get("complexity"),
        "qualification": record.get("qualification"),
        "axes": {
            axis: {"verdict": (axes.get(axis) or {}).get("verdict"),
                   "reason": (axes.get(axis) or {}).get("reason"),
                   "signal": (axes.get(axis) or {}).get("signal")}
            for axis in AXES
        },
        "change_point": {
            "id": (record.get("change_point") or {}).get("id"),
            "clean": (record.get("change_point") or {}).get("clean"),
            "finding_axes": [f.get("axis") for f in
                             (record.get("change_point") or {}).get("findings") or []],
        },
        "passive_trigger": {
            "trigger_feedback": (record.get("passive_trigger") or {}).get("trigger_feedback"),
        },
        "provenance": {
            "declared_by_caller": (record.get("provenance") or {}).get("declared_by_caller") or [],
        },
    }


# ---------------------------------------------------------------------------
# Store access — every write goes through memory-utils.py (no new store)
# ---------------------------------------------------------------------------

def load_determinations(workspace_root: Path,
                        unit_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Lane 1 read: the index first (a projection), then only the entry files the
    index names. Foreign entries and unreadable bodies are skipped, never guessed
    at."""
    memory = sibling_engine("memory-utils.py")
    try:
        index = memory.load_index(workspace_root, MEMORY_SCOPE)
    except (OSError, ValueError) as exc:
        raise InvalidError(f"cannot read the memory index: {exc}") from exc
    scope_dir = memory.scope_dir(workspace_root, MEMORY_SCOPE)
    found: List[Dict[str, Any]] = []
    for entry in index.get("entries") or []:
        if MEMORY_TAG not in (entry.get("tags") or []):
            continue
        if unit_id and entry.get("source") != unit_id:
            continue
        filename = entry.get("file") or ""
        path = scope_dir / filename
        if not filename or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        record = parse_entry_body(text)
        if record is None:
            continue
        found.append({"entry": entry, "path": path, "record": record})
    return found


def latest_settled_record(records: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Baseline = the same unit's most recent SETTLED record. An unsettled record
    is not a baseline: its own satisfaction was never resolved."""
    settled = [r for r in records if r.get("settled_at")]
    if not settled:
        return None
    return sorted(settled, key=lambda r: (r.get("determined_at") or "",
                                          r.get("run_id") or ""))[-1]


def persist_record(workspace_root: Path, record: Dict[str, Any]) -> Dict[str, Any]:
    """OI-2 seam: resolve the adapter at call time so a later ruling is a
    single-site edit."""
    adapter = PERSISTENCE_ADAPTERS.get(OI2_PERSISTENCE_ADAPTER)
    if adapter is None:
        raise InvalidError(
            f"no persistence adapter registered for {OI2_PERSISTENCE_ADAPTER!r}")
    return adapter(workspace_root, record)


def _persist_via_memory_utils(workspace_root: Path, record: Dict[str, Any]) -> Dict[str, Any]:
    """OI-2 option (a): land through the existing memory engine, into the store it
    already owns. No new store, no new directory, no new file kind."""
    memory = sibling_engine("memory-utils.py")
    unit_id = record["unit_id"]
    if not memory.validate_source(unit_id):
        # § 3 admits custom:<owner>/<name>; the memory engine's enforced --source
        # contract does not. Report the gap instead of dropping the record or
        # widening a contract this engine does not own.
        return {"persisted": False, "adapter": OI2_PERSISTENCE_ADAPTER,
                "reason": (f"the memory engine's --source contract does not accept "
                           f"{unit_id!r}; the record is emitted but not landed")}
    namespace = argparse.Namespace(
        workspace_root=str(workspace_root), scope=MEMORY_SCOPE, source=unit_id,
        title=f"{MEMORY_TAG} {unit_id} {record['run_id']}",
        content=compose_entry_body(record),
        content_file=None, tags=",".join([MEMORY_TAG, record["run_id"]]),
        feature=record.get("feature") or "", session_id="")
    try:
        result = memory.action_record(namespace)
    except memory.MemoryError as exc:
        return {"persisted": False, "adapter": OI2_PERSISTENCE_ADAPTER, "reason": str(exc)}
    except OSError as exc:
        return {"persisted": False, "adapter": OI2_PERSISTENCE_ADAPTER, "reason": str(exc)}
    return {"persisted": True, "adapter": OI2_PERSISTENCE_ADAPTER,
            "scope": result.get("scope"), "id": result.get("id"),
            "path": result.get("path")}


PERSISTENCE_ADAPTERS = {"memory-utils-session": _persist_via_memory_utils}


def amend_record(path: Path, record: Dict[str, Any]) -> None:
    """Settlement amends one entry in place, using the memory engine's own format
    owners. It has no amend action and § 2 forbids modifying an existing engine,
    so the format stays owned there while the bytes are rewritten here."""
    memory = sibling_engine("memory-utils.py")
    meta, _ = memory.parse_frontmatter(path.read_text(encoding="utf-8"))
    if not meta:
        raise InvalidError(f"entry has no frontmatter; cannot amend: {path}")
    meta["summary"] = summary_line(record)
    path.write_text(memory.compose_entry(meta, compose_entry_body(record)),
                    encoding="utf-8")


def reindex_session(workspace_root: Path) -> None:
    memory = sibling_engine("memory-utils.py")
    memory.action_reindex(argparse.Namespace(workspace_root=str(workspace_root),
                                             scope=MEMORY_SCOPE))


# ---------------------------------------------------------------------------
# Record construction
# ---------------------------------------------------------------------------

def load_session_context(args: argparse.Namespace, workspace_root: Path) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {"session_rows": [], "session_span": None, "session_store": None}
    if args.tool:
        ctx["session_store"] = probe_session_store(args.tool, workspace_root)
    if not args.session_file:
        if args.session_rows:
            raise InputError("--session-rows requires --session-file")
        return ctx
    path = Path(args.session_file)
    if not path.is_file():
        raise InputError(f"--session-file is not a readable file: {args.session_file}")
    rows = read_session_rows(path)
    if args.session_rows is None:
        # No declared span => the rows cannot be attributed to this run, and
        # summing a whole session would carry another run's consumption in.
        return ctx
    ctx["session_rows"] = rows
    ctx["session_span"] = parse_row_span(args.session_rows, len(rows))
    return ctx


def declared_by_caller(args: argparse.Namespace) -> List[str]:
    declared = ["complexity", "user_turn_class", "unresolved_red", "qualification"]
    optional = (
        ("session_file", args.session_file), ("session_rows", args.session_rows),
        ("tool", args.tool), ("proxy_paths", args.proxy_paths),
        ("elapsed_ms", args.elapsed_ms), ("names_current", args.names_current),
        ("names_baseline", args.names_baseline), ("declared_check", args.declared_check),
        ("green_check", args.green_check), ("red_first_refs", args.red_first_refs),
        ("collected", args.collected), ("feature", args.feature),
    )
    for name, value in optional:
        if value:
            declared.append(name)
    return declared


def build_provenance(args: argparse.Namespace, ctx: Dict[str, Any],
                     lane_states: Dict[str, str], digests: List[str]) -> Dict[str, Any]:
    provenance: Dict[str, Any] = {
        "engine": ENGINE_REL_PATH,
        "declared_by_caller": declared_by_caller(args),
        "lanes_read": lane_states,
        "evidence_digests": digests,
        "honesty_boundary": list(HONESTY_BOUNDARY),
        "red_state_input": OI9_RED_STATE_INPUT,
    }
    if ctx.get("session_store") is not None:
        provenance["session_store"] = ctx["session_store"]
    return provenance


def build_record(args: argparse.Namespace, workspace_root: Path,
                 unit_id: str, unit_type: str, red_state: Tuple[str, str],
                 baseline_record: Optional[Dict[str, Any]],
                 ctx: Dict[str, Any]) -> Dict[str, Any]:
    lane3 = probe_evidence_lane(workspace_root, unit_id)
    memory = sibling_engine("memory-utils.py")
    lane_states = {
        "session": "available" if memory.scope_dir(workspace_root, MEMORY_SCOPE).is_dir()
                   else "unavailable",
        # Lane 2 is the current turn's text already in context: zero extra reads,
        # and only the closed-enumeration classification ever crosses into here.
        "user_input": "in_context",
        "evidence": lane3["state"],
    }
    record: Dict[str, Any] = {
        "kind": RECORD_KIND,
        "schema_version": SCHEMA_VERSION,
        "unit_id": unit_id,
        "unit_type": unit_type,
        "run_id": args.run_id,
        "feature": args.feature or None,
        "feature_id": args.feature_id or None,
        "determined_at": now_iso(),
        "settled_at": None,
        "complexity": args.complexity,
        "qualification": args.qualification,
        "axes": {},
        "provenance": build_provenance(args, ctx, lane_states, list(lane3.get("digests") or [])),
    }

    token_refs: List[str] = []
    if args.session_file:
        token_refs.append(str(args.session_file))
    token_refs.extend(str(p) for p in (args.proxy_paths or []))
    record["axes"]["token_consumption"] = resolve_comparison_axis(
        "token_consumption", measure_token_consumption(args, ctx), token_value,
        baseline_record, token_refs)

    elapsed_refs = [str(args.session_file)] if args.session_file else []
    record["axes"]["elapsed"] = resolve_comparison_axis(
        "elapsed", measure_elapsed(args, ctx), elapsed_value,
        baseline_record, elapsed_refs)

    record["axes"]["artifact_correctness"] = evaluate_artifact_correctness(args)

    # § 4: at wrap-up the settling turn does not exist yet, so the axis is
    # honestly pending. Default-accept fires normally because settlement rides
    # on the next determination call rather than on a separate hook.
    record["axes"]["satisfaction"] = {
        "verdict": "not_evaluated",
        "reason": "pending_next_turn",
        "user_turn_class": "no_user_input",
        "unresolved_red": {"present": red_state[0], "source": red_state[1]},
        "adjacent": False,
        "signal": _signal("satisfaction"),
    }

    apply_qualification_gate(record)
    rebuild_change_point(record)
    return record


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def require_unit(args: argparse.Namespace) -> Tuple[str, str]:
    if not args.unit_id:
        raise InputError("--unit-id is required")
    unit_id = args.unit_id.strip()
    if not validate_unit_id(unit_id):
        raise InputError(
            f"invalid --unit-id: {args.unit_id!r} — expected /speckit.<command>, "
            f"skill:<name> or custom:<owner>/<name>"
        )
    unit_type = unit_type_of(unit_id)
    if args.unit_type and args.unit_type != unit_type:
        raise InputError(
            f"--unit-type {args.unit_type!r} contradicts --unit-id {unit_id!r}, "
            f"which implies {unit_type!r}"
        )
    return unit_id, unit_type


def _missing_required(args: argparse.Namespace, action: str) -> List[str]:
    """C-23 (063): collect EVERY missing required flag of `action` in one pass.
    The required list is ARG_MANIFEST's — the same classification the
    args-manifest action emits, so validation and manifest cannot drift apart."""
    parser = build_parser()
    missing: List[str] = []
    for flag in ARG_MANIFEST[action]["required"]:
        act = parser._option_string_actions.get(flag)
        if act is None:
            raise InvalidError(
                f"argument manifest drifted from the parser: {flag} is not an "
                "option of this engine")
        value = getattr(args, act.dest, None)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(flag)
    return missing


def _raise_missing(action: str, missing: List[str]) -> None:
    """C-23 (063): ONE InputError naming ALL missing required arguments —
    replaces the sequential one-at-a-time checks (a call missing ≥2 required
    args yields exactly one error listing every one of them)."""
    if not missing:
        return
    parts: List[str] = []
    for flag in missing:
        note = _REQUIRED_GUIDANCE.get(flag)
        parts.append(f"{flag} ({note})" if note else flag)
    raise InputError(
        f"{action} is missing required arguments: " + "; ".join(parts))


def settle_one(workspace_root: Path, target: Dict[str, Any], turn_class: str) -> Dict[str, Any]:
    record = target["record"]
    red = (record["axes"]["satisfaction"].get("unresolved_red") or {})
    record["axes"]["satisfaction"] = resolve_satisfaction(
        turn_class, red.get("present", "unknown"), red.get("source", "undeclared"),
        record.get("qualification", "qualified"))
    record["settled_at"] = now_iso()
    rebuild_change_point(record)
    problems = validate_record(record)
    if problems:
        raise InvalidError("settled record violates its own schema: " + "; ".join(problems))
    amend_record(target["path"], record)
    reindex_session(workspace_root)
    return record


def action_determine(args: argparse.Namespace) -> Tuple[Dict[str, Any], int]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    # C-23 (063): ALL missing required arguments in ONE error — replaces the
    # sequential --run-id / --complexity checks; a call missing ≥2 required
    # args names them all in a single InputError (exit 2 stays).
    _raise_missing("determine", _missing_required(args, "determine"))
    unit_id, unit_type = require_unit(args)
    if args.user_turn_class is not None:
        raise InputError(
            "--user-turn-class is not an input to `determine`: this run's "
            "satisfaction is settled by a LATER turn. To settle the previous "
            "unsettled record of this unit in the same call, pass "
            "--prev-user-turn-class; to settle one record explicitly, use "
            "--action settle."
        )
    if args.complexity == "simple":
        # § 3 scope gate: a simple unit produces no determination and no write.
        return {"skipped": "simple-unit"}, EXIT_OK

    existing = load_determinations(workspace_root, unit_id)
    if any(item["record"].get("run_id") == args.run_id for item in existing):
        return {"duplicate": True, "unit_id": unit_id, "run_id": args.run_id,
                "note": "this (unit_id, run_id) was already determined"}, EXIT_OK

    settled_previous: Optional[Dict[str, Any]] = None
    if args.prev_user_turn_class:
        unsettled = [item for item in existing if not item["record"].get("settled_at")]
        if unsettled:
            target = sorted(unsettled,
                            key=lambda i: (i["record"].get("determined_at") or "",
                                           i["record"].get("run_id") or ""))[-1]
            settled = settle_one(workspace_root, target, args.prev_user_turn_class)
            settled_previous = {"run_id": settled["run_id"],
                                "verdict": settled["axes"]["satisfaction"]["verdict"],
                                "reason": settled["axes"]["satisfaction"]["reason"]}

    records = [item["record"] for item in load_determinations(workspace_root, unit_id)]
    baseline_record = latest_settled_record(records)
    ctx = load_session_context(args, workspace_root)
    red_state = read_red_state(args)
    record = build_record(args, workspace_root, unit_id, unit_type, red_state,
                          baseline_record, ctx)
    problems = validate_record(record)
    if problems:
        raise InvalidError("record violates its own schema: " + "; ".join(problems))
    persistence = persist_record(workspace_root, record)
    payload = {
        "unit_id": unit_id,
        "run_id": args.run_id,
        "trigger_feedback": record["passive_trigger"]["trigger_feedback"],
        "verdicts": {axis: record["axes"][axis]["verdict"] for axis in AXES},
        "settled_previous": settled_previous,
        "persistence": persistence,
        "record": record,
    }
    return payload, EXIT_OK


def action_settle(args: argparse.Namespace) -> Tuple[Dict[str, Any], int]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    # C-23 (063): the same one-shot missing-argument contract as determine.
    _raise_missing("settle", _missing_required(args, "settle"))
    unit_id, _ = require_unit(args)
    if not args.user_turn_class:
        raise InputError("--user-turn-class is required for settle")
    if args.unresolved_red is not None or args.red_source is not None:
        raise InputError(
            "settle does not take a red state: the unresolved red belongs to the "
            "run being settled and was declared at its own wrap-up. Re-declaring "
            "it here would retrofit the adjacency exception."
        )
    records = load_determinations(workspace_root, unit_id)
    if args.run_id:
        candidates = [item for item in records if item["record"].get("run_id") == args.run_id]
    else:
        candidates = [item for item in records if not item["record"].get("settled_at")]
    if not candidates:
        raise NotFoundError(
            f"no {'unsettled ' if not args.run_id else ''}determination record for "
            f"unit_id={unit_id!r}" + (f" run_id={args.run_id!r}" if args.run_id else "")
        )
    target = sorted(candidates,
                    key=lambda i: (i["record"].get("determined_at") or "",
                                   i["record"].get("run_id") or ""))[-1]
    if target["record"].get("settled_at"):
        return {"already_settled": True, "settled": False, "unit_id": unit_id,
                "run_id": target["record"].get("run_id"),
                "settled_at": target["record"].get("settled_at")}, EXIT_OK
    record = settle_one(workspace_root, target, args.user_turn_class)
    return {"settled": True, "unit_id": unit_id, "run_id": record["run_id"],
            "settled_at": record["settled_at"],
            "satisfaction": record["axes"]["satisfaction"],
            "change_point": record["change_point"],
            "trigger_feedback": record["passive_trigger"]["trigger_feedback"]}, EXIT_OK


def action_history(args: argparse.Namespace) -> Tuple[Dict[str, Any], int]:
    workspace_root = resolve_workspace_root(args.workspace_root)
    # C-23 (063): the same one-shot missing-argument contract as determine.
    _raise_missing("history", _missing_required(args, "history"))
    if not args.target:
        raise InputError("--target is required for history")
    unit_id = args.target.strip()
    if not validate_unit_id(unit_id):
        raise InputError(f"invalid --target: {args.target!r}")
    records = load_determinations(workspace_root, unit_id)
    if args.run_id:
        records = [item for item in records if item["record"].get("run_id") == args.run_id]
    records.sort(key=lambda i: (i["record"].get("determined_at") or "",
                                i["record"].get("run_id") or ""), reverse=True)
    rows = [project_record(item["record"]) for item in records]
    if args.unsettled:
        rows = [row for row in rows if not row["settled_at"]]
    limit = args.limit if args.limit and args.limit > 0 else len(rows)
    counts = {
        "total": len(rows),
        "settled": sum(1 for r in rows if r["settled_at"]),
        "unsettled": sum(1 for r in rows if not r["settled_at"]),
        # § 5.4: an honest reader must be able to tell a derived accept from an
        # undeclared one, so the two are counted separately.
        "derived_accepts": sum(
            1 for r in rows
            if r["axes"]["satisfaction"]["verdict"] == "accepted"
            and r["axes"]["satisfaction"]["reason"] is None),
        "red_state_undeclared_accepts": sum(
            1 for r in rows
            if r["axes"]["satisfaction"]["reason"] == "red_state_undeclared"),
        "trigger_feedback": sum(1 for r in rows if r["passive_trigger"]["trigger_feedback"]),
    }
    return {"target": unit_id, "counts": counts, "records": rows[:limit]}, EXIT_OK


def action_args_manifest(args: argparse.Namespace) -> Tuple[Dict[str, Any], int]:
    """C-22 (063): machine-readable per-action argument manifest, BUILT FROM
    this engine's own parser — every classified flag is verified against the
    live parser's option strings before emitting, so a renamed/removed parser
    flag can never leave a stale manifest entry behind. Pure query face: no
    workspace access, no write."""
    parser = build_parser()
    live = {opt for act in parser._actions for opt in act.option_strings}
    manifest: Dict[str, Any] = {}
    for action in ACTIONS:
        spec = ARG_MANIFEST.get(action)
        if spec is None:
            raise InvalidError(
                f"args-manifest: action {action!r} has no manifest spec")
        for key in ("required", "source"):
            unknown = [f for f in spec[key] if f not in live]
            if unknown:
                raise InvalidError(
                    f"args-manifest: {action} {key} flags are not options of "
                    f"this engine's parser: {unknown}")
        manifest[action] = {"required": list(spec["required"]),
                            "source": list(spec["source"])}
    return manifest, EXIT_OK


_ACTIONS = {
    "determine": action_determine,
    "settle": action_settle,
    "history": action_history,
    "args-manifest": action_args_manifest,
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    # `--json` and `--workspace-root` are defined ONCE, on a shared parent parser.
    # This binary has no subparsers — the action is a flag — so the C-11 defect
    # (a per-action flag silently losing to an argparse default, documented at
    # .specify/specs/053-machine-decidable-artifacts/contracts/run-checks.md) has
    # no surface to appear on, and the flag is position-independent by
    # construction. `test_run_determination_engine.py` pins that.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workspace-root", default=None,
                        help="project workspace owning .specify/ (default: resolved "
                             "by the memory engine)")
    common.add_argument("--json", action="store_true", help="machine-readable output")

    parser = argparse.ArgumentParser(
        description="Run Determination engine (运行判定) — four measured quantities "
                    "per completed run, one record.",
        parents=[common],
    )
    parser.add_argument("--action", required=True, choices=list(ACTIONS))

    identity = parser.add_argument_group("identity & scope")
    identity.add_argument("--unit-id", default=None,
                          help="/speckit.<command> | skill:<name> | custom:<owner>/<name>")
    identity.add_argument("--unit-type", default=None, choices=list(UNIT_TYPES),
                          help="optional override; must agree with --unit-id")
    identity.add_argument("--run-id", default=None, help="the other half of the key")
    identity.add_argument("--complexity", default=None, choices=list(COMPLEXITIES),
                          help="caller-declared scope gate; simple emits no record")
    identity.add_argument("--qualification", default="qualified", choices=list(QUALIFICATIONS),
                          help="caller-declared; anything but qualified forces "
                               "not_evaluated/unqualified_run on every axis")
    identity.add_argument("--feature", default=None,
                          help="requirement key (e.g. 038-goal-target); NOT the registry ID")
    identity.add_argument("--feature-id", dest="feature_id", default=None,
                          help="Feature registry ID (e.g. 041); a different number space")

    token = parser.add_argument_group("token 消耗 / 耗时 sources")
    token.add_argument("--session-file", default=None,
                       help="AI-tool session JSONL for the exact sources")
    token.add_argument("--session-rows", default=None, metavar="START:END",
                       help="inclusive 0-based row span of THIS run inside --session-file")
    token.add_argument("--tool", default=None,
                       help="agent CLI name, for an honest store-availability probe")
    token.add_argument("--proxy-paths", action="append", default=[],
                       help="a file of the caller-declared read set (repeatable)")
    token.add_argument("--token-note", default=None, help="free text; echoed, never parsed")
    token.add_argument("--elapsed-ms", type=int, default=None,
                       help="a wall-clock span the caller measured itself")
    token.add_argument("--elapsed-note", default=None, help="free text; echoed, never parsed")

    correctness = parser.add_argument_group("制品正确性 sources")
    correctness.add_argument("--names-current", default=None,
                             help="sorted FAILED-nodeid list from run-tests.sh --names-out")
    correctness.add_argument("--names-baseline", default=None,
                             help="the frozen baseline list (名字级基线)")
    correctness.add_argument("--declared-check", action="append", default=[],
                             help="a check this run declared (repeatable)")
    correctness.add_argument("--green-check", action="append", default=[],
                             help="a declared check that returned green (repeatable)")
    correctness.add_argument("--red-first-refs", action="append", default=[],
                             help="file searched for each green check's literal name "
                                  "(red-first evidence or a mutation-drill record)")
    correctness.add_argument("--collected", type=int, default=None,
                             help="tests collected; feeds the anti-vacuity sentinel")

    satisfaction = parser.add_argument_group("满意度 inputs")
    satisfaction.add_argument("--user-turn-class", default=None, choices=list(USER_TURN_CLASSES),
                              help="settle: the class of the turn after the run")
    satisfaction.add_argument("--prev-user-turn-class", default=None,
                              choices=list(USER_TURN_CLASSES),
                              help="determine: settle this unit's latest unsettled "
                                   "record with the current turn's class")
    satisfaction.add_argument("--unresolved-red", default=None,
                              choices=list(UNRESOLVED_RED_VALUES),
                              help="caller declaration (OI-9 option a); default unknown")
    satisfaction.add_argument("--red-source", default=None, choices=list(RED_SOURCES),
                              help="the producer of a declared red")

    history = parser.add_argument_group("history projection")
    history.add_argument("--target", default=None, help="history: the unit to project")
    history.add_argument("--limit", type=int, default=20, help="history: max rows (0 = all)")
    history.add_argument("--unsettled", action="store_true",
                         help="history: only records whose satisfaction is unresolved")
    return parser


def render_text(action: str, payload: Dict[str, Any]) -> str:
    if action == "args-manifest":
        # C-22 (063): the manifest is a machine face — pure JSON regardless of
        # --json, so the compile-embeds renderer consumes one invocation form.
        return json.dumps(payload, ensure_ascii=False, indent=2)
    lines: List[str] = []
    if "skipped" in payload:
        return f"skipped: {payload['skipped']}"
    if action == "determine":
        if payload.get("duplicate"):
            return (f"duplicate: {payload['unit_id']} {payload['run_id']} "
                    f"was already determined")
        verdicts = payload.get("verdicts") or {}
        lines.append(f"unit: {payload.get('unit_id')}   run: {payload.get('run_id')}")
        for axis in AXES:
            reason = ((payload.get("record") or {}).get("axes", {})
                      .get(axis, {}).get("reason"))
            tail = f" ({reason})" if reason else ""
            lines.append(f"  {axis:<20} {verdicts.get(axis)}{tail}")
        lines.append(f"trigger_feedback: {str(payload.get('trigger_feedback')).lower()}")
        change = (payload.get("record") or {}).get("change_point") or {}
        lines.append(f"change_point: {change.get('id')} clean="
                     f"{str(change.get('clean')).lower()} "
                     f"findings={len(change.get('findings') or [])}")
        persistence = payload.get("persistence") or {}
        if persistence.get("persisted"):
            lines.append(f"persisted: {persistence.get('path')}")
        else:
            lines.append(f"not persisted: {persistence.get('reason')}")
        if payload.get("settled_previous"):
            previous = payload["settled_previous"]
            lines.append(f"settled previous run {previous['run_id']}: "
                         f"{previous['verdict']}")
        return "\n".join(lines)
    if action == "settle":
        if payload.get("already_settled"):
            return (f"already settled: {payload.get('run_id')} at {payload.get('settled_at')}")
        satisfaction = payload.get("satisfaction") or {}
        return (f"settled: {payload.get('unit_id')} {payload.get('run_id')} -> "
                f"{satisfaction.get('verdict')}"
                + (f" ({satisfaction.get('reason')})" if satisfaction.get("reason") else ""))
    counts = payload.get("counts") or {}
    lines.append(f"target: {payload.get('target')}   "
                 f"total={counts.get('total')} unsettled={counts.get('unsettled')} "
                 f"trigger_feedback={counts.get('trigger_feedback')}")
    for row in payload.get("records") or []:
        verdicts = " ".join(f"{axis.split('_')[0]}={row['axes'][axis]['verdict']}"
                            for axis in AXES)
        state = "settled" if row.get("settled_at") else "unsettled"
        lines.append(f"  {row.get('run_id'):<24} {state:<9} {verdicts}")
    return "\n".join(lines)


def _emit(payload: Dict[str, Any], as_json: bool, action: str) -> None:
    """The single emit path every action ends on."""
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if "error" in payload:
        print(f"error: {payload['error']}", file=sys.stderr)
        return
    print(render_text(action, payload))


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        payload, code = _ACTIONS[args.action](args)
    except NotFoundError as exc:
        _emit({"error": str(exc)}, args.json, args.action)
        return EXIT_NOT_FOUND
    except InvalidError as exc:
        _emit({"error": str(exc)}, args.json, args.action)
        return EXIT_INVALID
    except InputError as exc:
        _emit({"error": str(exc)}, args.json, args.action)
        return EXIT_INPUT_ERROR
    except DeterminationError as exc:
        _emit({"error": str(exc)}, args.json, args.action)
        return EXIT_INPUT_ERROR
    _emit(payload, args.json, args.action)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
