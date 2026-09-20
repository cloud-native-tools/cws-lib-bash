#!/usr/bin/env python3
"""Proactive flow trigger engine (spec 050 — Proactive Flow Trigger).

Deterministic half of the proactive-trigger mechanism: situation identity
resolution, rule matching, consecutive counting, threshold promotion, telemetry,
rotation and evidence aggregation. Semantic judgement (whether to adopt a tuning
proposal, which flow a missed situation belongs to) stays with the agent and is
handed back through `semanticJudgmentPending`.

Contract: .specify/specs/050-proactive-flow-trigger/contracts/trigger-engine.md
Discipline: shared/guidelines/proactive-trigger.md (the single source of truth)
Paradigm source: scripts/python/derive-utils.py (camelCase envelope, atomic
write, graded exit codes). Threshold semantics are isomorphic to
feedback-utils.py's, re-implemented locally rather than imported: scripts/ is
mirrored as independent STRICT copies, so a cross-engine import would couple two
separately mirrored files.

Design boundaries that are contractually enforced, not stylistic:
  * The engine never executes a flow. `autoExecute` is advice for the agent
    (C-21); no flow name is hard-coded here — they are seed data.
  * No network capability is imported (C-19); state is project-local.
  * Without --probe, no artifact file is opened (C-13).

Usage:
  python3 trigger-utils.py --action <action> [options]

Exit codes: 0 ok · 1 usage · 2 input error · 3 not found · 4 invalid identifier
or vocabulary.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# --- C-5: graded exit codes ---
EXIT_OK = 0
EXIT_USAGE = 1
EXIT_INPUT_ERROR = 2
EXIT_NOT_FOUND = 3
EXIT_INVALID = 4

_HERE = Path(__file__).resolve()
REPO_ROOT = _HERE.parents[2]
if REPO_ROOT.name == ".specify":
    REPO_ROOT = REPO_ROOT.parent

STORE_RELPATH = Path(".specify") / "memory" / "trigger"
INDEX_NAME = "index.json"
TELEMETRY_NAME = "telemetry.jsonl"
IGNORE_ENTRY = ".specify/memory/trigger/telemetry.jsonl"
SEED_CANDIDATES = (
    Path(".specify") / "templates" / "proactive-trigger-seed.json",
    Path("templates") / "proactive-trigger-seed.json",
)
FEEDBACK_ENGINE = Path(".specify") / "scripts" / "python" / "feedback-utils.py"

SCHEMA_VERSION = 1
DEFAULT_CONFIG = {
    "enabled": True,
    "threshold": 3,
    "telemetryWindow": 200,
    "probeBudgetPct": 20,
    "minSample": 5,
}
THRESHOLD_DEFAULT = 3
THRESHOLD_FLOOR = 2
THRESHOLD_ENV = "SPECKIT_TRIGGER_THRESHOLD"

SNAPSHOT_MAX_CHARS = 200
PROBE_ITEM_MAX_CHARS = 200
PAYLOAD_MAX_LINES = 60
PAYLOAD_MAX_CHARS = 2000
STATUS_TEXT_MAX_LINES = 30

# C-9: closed action enumeration.
ACTIONS = (
    "init", "assess", "record", "record-manual", "status", "rules",
    "reset", "config", "tune", "tune-apply", "rotate",
)

RESPONSES = ("accepted", "declined", "ignored")
PROPOSAL_KINDS = ("tighten", "suppress", "add-rule", "extend-vocabulary")
PROPOSAL_STATES = ("proposed", "ratified", "applied", "rejected")
RULE_STATES = ("active", "suppressed", "promoted")

# C-22: closed error/warning code set.
CODES = frozenset({
    "ordering-violation", "state-unreadable", "threshold-below-floor",
    "vocabulary-out-of-range", "no-prior-assess", "rule-not-found",
    "proposal-not-found", "identifier-malformed", "seed-unreadable",
    "telemetry-unwritable",
})

# Controlled vocabulary (data-model.md §受控词表). Expansion goes through the
# user-approval channel only — the engine never coins a situation on the fly.
STAGES = frozenset({
    "no-spec", "requirements-unclear", "requirements-draft", "planned",
    "tasks-ready", "implementing", "implemented", "review-pending", "non-feature",
})
SIGNALS = frozenset({
    "needs-clarification", "no-plan", "no-tasks", "open-tasks", "deferred-tasks",
    "checklist-absent", "feedback-threshold", "introspection-pending", "docs-drift",
    "instructions-stale", "feature-index-absent", "constitution-absent",
})

# V2.5: identifier grammar.
RULE_ID_RE = re.compile(r"^r-[0-9]{3}$")
SITUATION_ID_RE = re.compile(r"^s[0-9]{2}$")
PROPOSAL_ID_RE = re.compile(r"^p-[0-9]{3}$")
EVENT_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9]{2}$")
SESSION_ID_RE = re.compile(r"^s[0-9A-Za-z-]{1,32}$")
TURN_ID_RE = re.compile(r"^(?P<session>.+)-[0-9]{2,4}$")

# tune's emission criteria — contract constants, not config keys (adding one
# would require amending E6's closed config set and C-10's closed flag set in
# the same batch).
SUPPRESS_RATIO = 0.50
TIGHTEN_RATIO = 0.50
ADD_RULE_MIN_MISSED = 2

DEFAULT_SESSION = "sdefault"


# --------------------------------------------------------------------------
# time / paths
# --------------------------------------------------------------------------

def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_compact() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_root(workspace: str | None = None) -> Path:
    """C-7: explicit --workspace > engine self-location > nearest .specify ancestor > CWD."""
    if workspace:
        root = Path(workspace).resolve()
        return root.parent if root.name == ".specify" else root

    # Engine self-location applies only to the mirrored copy under
    # */.specify/scripts/. The canonical source copy must fall through to the
    # CWD walk, or every downstream invocation would resolve back to this repo.
    for parent in _HERE.parents:
        if parent.name == ".specify":
            return parent.parent

    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".specify").is_dir():
            return candidate
    return cwd


def store_dir(root: Path) -> Path:
    return root / STORE_RELPATH


def index_path(root: Path) -> Path:
    return store_dir(root) / INDEX_NAME


def telemetry_path(root: Path) -> Path:
    return store_dir(root) / TELEMETRY_NAME


def seed_path(root: Path) -> Path | None:
    for rel in SEED_CANDIDATES:
        candidate = root / rel
        if candidate.is_file():
            return candidate
    fallback = REPO_ROOT / SEED_CANDIDATES[1]
    return fallback if fallback.is_file() else None


# --------------------------------------------------------------------------
# pure functions (unit-tested in tests/unit/test_trigger_utils_units.py)
# --------------------------------------------------------------------------

def envelope(action, root, errors, warnings, semantic, notes, payload, ok=None) -> dict:
    """C-3: the fixed 9-key camelCase envelope."""
    return {
        "ok": (not errors) if ok is None else ok,
        "action": action,
        "workspaceRoot": str(root),
        "generatedAt": utc_now(),
        "errors": list(errors),
        "warnings": list(warnings),
        "semanticJudgmentPending": list(semantic),
        "notes": list(notes),
        "payload": payload,
    }


def vocabulary_violations(stage, signals) -> list:
    """V1.2: report every out-of-range token; the caller turns this into EXIT_INVALID."""
    out = []
    if stage is not None and stage not in STAGES:
        out.append(f"stage:{stage}")
    for sig in signals or ():
        if sig not in SIGNALS:
            out.append(f"signal:{sig}")
    return out


def resolve_situation(situations, stage, signals, rules=None) -> str | None:
    """E1 V1.5/V1.6: deterministic single-identity resolution.

    Order: predicate match -> largest signalsAll cardinality -> best (lowest)
    rule priority for that situation -> lexicographically smallest id. The
    priority step is what lets a governance-first situation win a cardinality
    tie without introducing negative signals outside the enumeration.
    """
    given = set(signals or ())
    matched = []
    for sit in situations or ():
        m = sit.get("match") or {}
        if m.get("stage") != stage:
            continue
        if not set(m.get("signalsAll") or ()) <= given:
            continue
        any_set = set(m.get("signalsAny") or ())
        if any_set and not (any_set & given):
            continue
        matched.append(sit)
    if not matched:
        return None

    priority_of = {}
    for rule in rules or ():
        sid = rule.get("situationId")
        prio = rule.get("priority")
        if sid is None or not isinstance(prio, int):
            continue
        priority_of[sid] = min(priority_of.get(sid, prio), prio)

    def key(sit):
        sid = sit["id"]
        return (
            -len(sit.get("match", {}).get("signalsAll") or ()),
            priority_of.get(sid, 10 ** 6),
            sid,
        )

    return sorted(matched, key=key)[0]["id"]


def resolve_threshold(explicit=None, env_value=None, stored=None, default=THRESHOLD_DEFAULT):
    """V6.2 / C-18: explicit > environment > stored > default.

    An unusable environment value downgrades silently to the next level; it is
    never an error, because a broken shell variable must not break the turn.
    """
    if explicit is not None:
        try:
            return int(explicit)
        except (TypeError, ValueError):
            pass
    if env_value is not None:
        try:
            text = str(env_value).strip()
            if text:
                return int(text)
        except (TypeError, ValueError):
            pass
    if stored is not None:
        try:
            return int(stored)
        except (TypeError, ValueError):
            pass
    return default


def threshold_below_floor(value) -> bool:
    """V6.3: 0 or 1 would auto-execute a reversible flow with zero observation."""
    try:
        return int(value) < THRESHOLD_FLOOR
    except (TypeError, ValueError):
        return True


def shape_telemetry_row(turn_id, escalated, suggested, compliance_done,
                        visible_output, ts) -> dict:
    """E4: the seven telemetry keys, with V4.2 enforced by the shaper itself."""
    suggested = bool(suggested)
    return {
        "turnId": str(turn_id),
        "assessed": True,          # V4.5: only assess writes rows, so this records an invariant
        "escalated": bool(escalated),
        "suggested": suggested,
        "complianceDone": bool(compliance_done),
        "visibleOutput": bool(visible_output) if suggested else False,
        "ts": ts,
    }


def snapshot_ok(text) -> bool:
    """V3.3: snapshots stay summary-sized; artifact bodies never enter the store."""
    return len(text or "") <= SNAPSHOT_MAX_CHARS


def next_consecutive(current, response) -> int:
    """V3.1/V3.2: accepted increments, declined and ignored both reset to zero."""
    if response == "accepted":
        return max(0, int(current or 0)) + 1
    if response in ("declined", "ignored"):
        return 0
    raise ValueError(f"unknown response: {response!r}")


def is_destructive_exempt(confirmation_class) -> bool:
    return confirmation_class == "destructive"


def should_promote(consecutive, threshold, confirmation_class) -> bool:
    """C-17 zero tolerance: a destructive flow never earns auto-execution."""
    if is_destructive_exempt(confirmation_class):
        return False
    try:
        return int(consecutive) >= int(threshold)
    except (TypeError, ValueError):
        return False


def turn_id_ok(session, turn_id) -> bool:
    """V2.5: turnId is ^<sessionId>-[0-9]{2,4}$."""
    if not session or not turn_id:
        return False
    m = TURN_ID_RE.match(turn_id)
    return bool(m) and m.group("session") == session


def is_suppressed(last, session, situation_id, rule_id) -> bool:
    """V6.7/C-20: suppress only when identity AND rule are both unchanged.

    Accepts either shape the store presents: a single lastSuggestion entry
    (carrying its own sessionId) or the session-keyed map held in index.json.
    """
    if not last or not isinstance(last, dict):
        return False
    entry = last if "sessionId" in last else last.get(session)
    if not isinstance(entry, dict):
        return False
    return (
        entry.get("sessionId") == session
        and entry.get("situationId") == situation_id
        and entry.get("ruleId") == rule_id
    )


def bounded(text, limit=PROBE_ITEM_MAX_CHARS) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


# --------------------------------------------------------------------------
# state I/O
# --------------------------------------------------------------------------

def load_seed(root: Path):
    path = seed_path(root)
    if path is None or not path.is_file():
        return None, "seed-unreadable"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, "seed-unreadable"
    if not isinstance(data, dict) or "rules" not in data or "situations" not in data:
        return None, "seed-unreadable"
    return data, None


def blank_state(seed) -> dict:
    return {
        "store": ".specify/memory/trigger/",
        "schemaVersion": SCHEMA_VERSION,
        "updated": utc_now(),
        "config": dict(DEFAULT_CONFIG),
        "situations": list((seed or {}).get("situations") or []),
        "rules": [materialize_rule(r) for r in (seed or {}).get("rules") or []],
        "events": [],
        "lastSuggestion": {},
        "proposals": [],
        "manualInvocations": [],
    }


def materialize_rule(seed_rule: dict) -> dict:
    """Turn a shipped seed entry into a runtime rule (C-4's isomorphism, applied)."""
    rule = {
        "ruleId": seed_rule["ruleId"],
        "situationId": seed_rule["situationId"],
        "flow": seed_rule["flow"],
        "invocation": seed_rule["invocation"],
        "rationale": seed_rule["rationale"],
        "confirmationClass": seed_rule["confirmationClass"],
        "origin": seed_rule.get("origin", "seed"),
        "priority": seed_rule.get("priority", 100),
        "state": "active",
        "promotion": {
            "consecutive": 0,
            "threshold": DEFAULT_CONFIG["threshold"],
            "promoted": False,
            "destructiveExempt": is_destructive_exempt(seed_rule["confirmationClass"]),
            "resetBy": None,
            "userResetAt": None,
        },
        "stats": {"hits": 0, "accepted": 0, "declined": 0, "ignored": 0, "lastSeen": None},
    }
    if seed_rule.get("provenance"):
        rule["provenance"] = seed_rule["provenance"]
    if seed_rule.get("notes"):
        rule["notes"] = seed_rule["notes"]
    return rule


def read_index(root: Path):
    """Return (state, degraded_code). Never raises: C-8 degrades instead of failing."""
    path = index_path(root)
    seed, seed_err = load_seed(root)
    if not path.is_file():
        return blank_state(seed), "state-unreadable"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return blank_state(seed), "state-unreadable"
    if not isinstance(data, dict) or data.get("schemaVersion") != SCHEMA_VERSION:
        return blank_state(seed), "state-unreadable"
    for key, default in (("config", DEFAULT_CONFIG), ("situations", []), ("rules", []),
                         ("events", []), ("proposals", [])):
        data.setdefault(key, dict(default) if isinstance(default, dict) else list(default))
    data.setdefault("lastSuggestion", {})
    data.setdefault("manualInvocations", [])
    data.setdefault("store", ".specify/memory/trigger/")
    data.setdefault("updated", utc_now())
    return data, None


def write_index_atomic(root: Path, state: dict) -> None:
    """C-6 / V6.5: <path>.part then os.replace — never a half-written index."""
    state["updated"] = utc_now()
    path = index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    part.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(str(part), str(path))


def append_telemetry(root: Path, row: dict, window: int) -> str | None:
    """V4.3: append then truncate, so the window bound holds after every write."""
    path = telemetry_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        truncate_telemetry(root, window)
    except OSError:
        return "telemetry-unwritable"
    return None


def read_telemetry(root: Path) -> list:
    path = telemetry_path(root)
    if not path.is_file():
        return []
    rows = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        return []
    return rows


def truncate_telemetry(root: Path, window: int) -> None:
    path = telemetry_path(root)
    if not path.is_file():
        return
    try:
        window = max(1, int(window))
    except (TypeError, ValueError):
        window = DEFAULT_CONFIG["telemetryWindow"]
    lines = [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(lines) <= window:
        return
    kept = lines[-window:]
    part = path.with_name(path.name + ".part")
    part.write_text("\n".join(kept) + "\n", encoding="utf-8")
    os.replace(str(part), str(path))


def ensure_ignore_entry(root: Path) -> None:
    """V6.9: telemetry is per-turn churn and is ignored; index.json stays tracked."""
    gi = root / ".gitignore"
    try:
        existing = gi.read_text(encoding="utf-8") if gi.is_file() else ""
    except OSError:
        return
    if IGNORE_ENTRY in existing:
        return
    prefix = "" if existing.endswith("\n") or not existing else "\n"
    block = (
        f"{prefix}# proactive flow trigger: per-turn telemetry churns, learning state must not\n"
        f"{IGNORE_ENTRY}\n"
    )
    try:
        with gi.open("a", encoding="utf-8") as fh:
            fh.write(block)
    except OSError:
        pass


def resolve_threshold_for(state, explicit=None):
    return resolve_threshold(
        explicit=explicit,
        env_value=os.environ.get(THRESHOLD_ENV),
        stored=(state.get("config") or {}).get("threshold"),
        default=THRESHOLD_DEFAULT,
    )


def rejudge_promotions(state: dict) -> None:
    """V5.4: promotions are re-decided under the current threshold."""
    threshold = (state.get("config") or {}).get("threshold", THRESHOLD_DEFAULT)
    for rule in state.get("rules", []):
        promo = rule.setdefault("promotion", {})
        promo["threshold"] = threshold
        promo["destructiveExempt"] = is_destructive_exempt(rule.get("confirmationClass"))
        earned = should_promote(promo.get("consecutive", 0), threshold,
                                rule.get("confirmationClass"))
        promo["promoted"] = earned
        if rule.get("state") == "promoted" and not earned:
            rule["state"] = "active"
        elif earned and rule.get("state") == "active":
            rule["state"] = "promoted"


# --------------------------------------------------------------------------
# probes (P1-P5, summaries only — C-13)
# --------------------------------------------------------------------------

def current_feature_dir(root: Path) -> Path | None:
    specs = root / ".specify" / "specs"
    if not specs.is_dir():
        return None
    numbered = [d for d in specs.iterdir() if d.is_dir() and re.match(r"^\d{3}-", d.name)]
    if not numbered:
        return None
    return sorted(numbered, key=lambda d: d.name)[-1]


def run_probes(root: Path) -> list:
    """Deterministic existence/count/set-difference probes. Never artifact bodies."""
    out = []

    feature = current_feature_dir(root)
    if feature is None:
        out.append(bounded("P1 no feature directory under .specify/specs/"))
    else:
        present = [n for n in ("requirements.md", "plan.md", "tasks.md")
                   if (feature / n).is_file()]
        out.append(bounded(f"P1 feature={feature.name} artifacts={len(present)}/3 "
                           f"({','.join(present) or 'none'})"))

        req = feature / "requirements.md"
        if req.is_file():
            try:
                text = req.read_text(encoding="utf-8")
            except OSError:
                text = ""
            n = len(re.findall(r"NEEDS CLARIFICATION", text)) + \
                len(re.findall(r"Need clarification", text))
            out.append(bounded(f"P2 requirements.md open-clarification-markers={n}"))
        else:
            out.append(bounded("P2 requirements.md absent"))

        tasks = feature / "tasks.md"
        if tasks.is_file():
            try:
                text = tasks.read_text(encoding="utf-8")
            except OSError:
                text = ""
            counts = {
                "open": len(re.findall(r"(?m)^- \[ \]", text)),
                "done": len(re.findall(r"(?m)^- \[[Xx]\]", text)),
                "deferred": len(re.findall(r"(?m)^- \[~\]", text)),
                "claimed": len(re.findall(r"(?m)^- \[>\]", text)),
            }
            out.append(bounded("P3 tasks.md " + " ".join(f"{k}={v}" for k, v in counts.items())))
        else:
            out.append(bounded("P3 tasks.md absent"))

    fb = root / FEEDBACK_ENGINE
    if fb.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(fb), "--action", "status"],
                cwd=str(root), capture_output=True, text=True, timeout=20,
            )
            payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
            inner = payload.get("payload", payload)
            fields = {k: inner.get(k) for k in
                      ("count", "countSinceSubmission", "threshold", "shouldPrompt")
                      if inner.get(k) is not None}
            out.append(bounded(f"P4 feedback {fields or 'no threshold fields'}"))
        except (OSError, ValueError, subprocess.SubprocessError):
            out.append(bounded("P4 feedback engine unreadable"))
    else:
        out.append(bounded("P4 feedback engine absent"))

    live = root / ".specify" / "instructions.md"
    tmpl = root / ".specify" / "templates" / "instructions-template.md"
    if live.is_file() and tmpl.is_file():
        try:
            live_h = set(re.findall(r"(?m)^## .+$", live.read_text(encoding="utf-8")))
            tmpl_h = set(re.findall(r"(?m)^## .+$", tmpl.read_text(encoding="utf-8")))
        except OSError:
            live_h = tmpl_h = set()
        missing = sorted(tmpl_h - live_h)
        extra = sorted(live_h - tmpl_h)
        out.append(bounded(f"P5 instructions stale-sections={len(missing)} "
                           f"project-local-sections={len(extra)}"))
    else:
        out.append(bounded("P5 instructions or template absent"))

    return out


# --------------------------------------------------------------------------
# actions
# --------------------------------------------------------------------------

def merge_seed_into(state: dict, seed: dict, notes: list) -> None:
    """V2.3: a seed refresh may update wording, never revert a user's tuning."""
    existing = {r["ruleId"]: r for r in state.get("rules", [])}
    situations = {s["id"]: s for s in state.get("situations", [])}
    for sit in seed.get("situations", []):
        situations[sit["id"]] = sit
    state["situations"] = [situations[k] for k in sorted(situations)]

    for seed_rule in seed.get("rules", []):
        rid = seed_rule["ruleId"]
        current = existing.get(rid)
        if current is None:
            state["rules"].append(materialize_rule(seed_rule))
            continue
        refreshed = []
        # `provenance` belongs in the refresh set even though it is not wording: it is a
        # derived pointer into the seed's anchor section, never a user-tuned field. Left
        # to setdefault it silently keeps quoting text the owner no longer contains, and
        # no reader compares the index back against the seed to notice.
        for field in ("rationale", "invocation", "provenance"):
            if field not in seed_rule:
                continue
            if current.get(field) != seed_rule[field]:
                current[field] = seed_rule[field]
                refreshed.append(field)
        if refreshed:
            notes.append(f"seed refresh {rid}: {','.join(refreshed)}")
        if not current.get("tuning"):
            # Untuned rules may follow the seed's ordering and classification.
            current["priority"] = seed_rule.get("priority", current.get("priority"))
            current["confirmationClass"] = seed_rule.get(
                "confirmationClass", current.get("confirmationClass"))
            current["flow"] = seed_rule.get("flow", current.get("flow"))
            current["situationId"] = seed_rule.get("situationId", current.get("situationId"))
        else:
            notes.append(f"seed refresh {rid}: local tuning preserved (V2.3)")
    state["rules"].sort(key=lambda r: r["ruleId"])


def action_init(root: Path, args) -> tuple:
    seed, seed_err = load_seed(root)
    errors, warnings, notes = [], [], []
    if seed is None:
        errors.append(seed_err or "seed-unreadable")
        return EXIT_INPUT_ERROR, errors, warnings, [], notes, {}

    state, degraded = read_index(root)
    existed = index_path(root).is_file() and degraded is None
    if not existed:
        state = blank_state(seed)
    merge_seed_into(state, seed, notes)
    rejudge_promotions(state)
    write_index_atomic(root, state)
    ensure_ignore_entry(root)
    notes.append("seed installed" if not existed else "seed reconciled (idempotent)")
    payload = {
        "created": not existed,
        "situations": len(state["situations"]),
        "rules": len(state["rules"]),
        "config": state["config"],
    }
    return EXIT_OK, errors, warnings, [], notes, payload


def pick_rule(state: dict, situation_id: str):
    """FR-008: converge multiple hits on one situation to the highest priority."""
    candidates = [
        r for r in state.get("rules", [])
        if r.get("situationId") == situation_id and r.get("state") != "suppressed"
    ]
    if not candidates:
        return None
    return sorted(candidates, key=lambda r: (r.get("priority", 10 ** 6), r["ruleId"]))[0]


def next_event_id(events: list) -> str:
    stamp = utc_compact()
    seq = 1
    taken = {e.get("eventId") for e in events}
    while f"{stamp}-{seq:02d}" in taken:
        seq += 1
    return f"{stamp}-{seq:02d}"


def action_assess(root: Path, args) -> tuple:
    errors, warnings, notes, semantic = [], [], [], []
    signals = list(args.signal or [])

    violations = vocabulary_violations(args.stage, signals)
    if violations:
        errors.append("vocabulary-out-of-range")
        return EXIT_INVALID, errors, warnings, semantic, notes, {
            "suggestion": None, "reason": "vocabulary-out-of-range",
            "violations": violations,
        }

    session = args.session or DEFAULT_SESSION
    if not SESSION_ID_RE.match(session):
        errors.append("identifier-malformed")
        return EXIT_INVALID, errors, warnings, semantic, notes, {
            "suggestion": None, "reason": "identifier-malformed"}

    state, degraded = read_index(root)
    if degraded:
        warnings.append(degraded)
    seed, seed_err = load_seed(root)
    if not state.get("rules") and seed:
        merge_seed_into(state, seed, notes)

    rows_before = read_telemetry(root)
    turn_id = args.turn_id
    if not turn_id:
        seq = sum(1 for r in rows_before if str(r.get("turnId", "")).startswith(f"{session}-"))
        turn_id = f"{session}-{seq + 1:02d}"
    elif not turn_id_ok(session, turn_id):
        errors.append("identifier-malformed")
        return EXIT_INVALID, errors, warnings, semantic, notes, {
            "suggestion": None, "reason": "identifier-malformed"}

    config = state.get("config") or {}
    enabled = bool(config.get("enabled", True))
    escalated = bool(args.probe)
    probes = run_probes(root) if escalated else []

    payload = {
        "sessionId": session,
        "turnId": turn_id,
        "stage": args.stage,
        "signals": signals,
        "situationId": None,
        "suggestion": None,
        "suppressed": False,
        "visibleOutput": False,
        "enabled": enabled,
    }
    if degraded:
        payload["degraded"] = "suggest-only"
    if probes:
        payload["probes"] = probes

    suggested = False
    situation_id = None
    rule = None

    if enabled and args.stage:
        situation_id = resolve_situation(state.get("situations"), args.stage, signals,
                                         state.get("rules"))
        payload["situationId"] = situation_id
        if situation_id is None:
            payload["reason"] = "no-situation-match"
        else:
            rule = pick_rule(state, situation_id)
            if rule is None:
                payload["reason"] = "no-active-rule"
            elif is_suppressed(state.get("lastSuggestion"), session, situation_id,
                               rule["ruleId"]):
                payload["suppressed"] = True
                payload["reason"] = "session-suppressed"
            else:
                suggested = True
                threshold = resolve_threshold_for(state)
                promo = rule.get("promotion") or {}
                auto = bool(promo.get("promoted")) and not is_destructive_exempt(
                    rule.get("confirmationClass"))
                payload["suggestion"] = {
                    "ruleId": rule["ruleId"],
                    "flow": rule["flow"],
                    "invocation": rule["invocation"],
                    "rationale": rule["rationale"],
                    "autoExecute": auto,
                }
                payload["visibleOutput"] = True
                rule.setdefault("stats", {})
                rule["stats"]["hits"] = int(rule["stats"].get("hits", 0)) + 1
                rule["stats"]["lastSeen"] = utc_now()

    if suggested and not args.compliance_done:
        # V4.1 / SC-012: the ordering contract is declared by the caller, never inferred.
        errors.append("ordering-violation")

    row = shape_telemetry_row(
        turn_id=turn_id, escalated=escalated, suggested=suggested,
        compliance_done=bool(args.compliance_done),
        visible_output=payload.get("visibleOutput", False), ts=utc_now(),
    )
    telemetry_err = append_telemetry(root, row, config.get("telemetryWindow",
                                                           DEFAULT_CONFIG["telemetryWindow"]))
    if telemetry_err:
        warnings.append(telemetry_err)

    if suggested and rule is not None:
        snapshot = bounded(f"{args.stage}|{','.join(sorted(signals)) or '-'}",
                           SNAPSHOT_MAX_CHARS)
        state.setdefault("lastSuggestion", {})[session] = {
            "sessionId": session, "turnId": turn_id, "situationId": situation_id,
            "ruleId": rule["ruleId"], "snapshot": snapshot, "escalated": escalated,
            "suggested": True, "ts": row["ts"],
        }
    write_index_atomic(root, state)

    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if len(rendered) > PAYLOAD_MAX_CHARS or len(rendered.splitlines()) > PAYLOAD_MAX_LINES:
        notes.append("payload trimmed to stay within the C-15 bound")
        payload = {k: payload[k] for k in
                   ("sessionId", "turnId", "situationId", "suggestion", "suppressed")
                   if k in payload}

    # ok stays true even with an ordering violation: the turn still produced its
    # telemetry, and the violation is a reportable fact rather than a failed call.
    return EXIT_OK, errors, warnings, semantic, notes, payload


def action_record(root: Path, args) -> tuple:
    errors, warnings, notes, semantic = [], [], [], []
    if not args.rule or not RULE_ID_RE.match(args.rule):
        errors.append("identifier-malformed")
        return EXIT_INVALID, errors, warnings, semantic, notes, {}
    if args.response not in RESPONSES:
        errors.append("identifier-malformed")
        return EXIT_INVALID, errors, warnings, semantic, notes, {}

    state, degraded = read_index(root)
    if degraded:
        warnings.append(degraded)
    rule = next((r for r in state.get("rules", []) if r["ruleId"] == args.rule), None)
    if rule is None:
        errors.append("rule-not-found")
        return EXIT_NOT_FOUND, errors, warnings, semantic, notes, {}

    session = args.session or DEFAULT_SESSION
    last = (state.get("lastSuggestion") or {}).get(session)
    if not last:
        # V3.4: refuse rather than store a half-formed event.
        errors.append("no-prior-assess")
        return EXIT_INPUT_ERROR, errors, warnings, semantic, notes, {}

    event = {
        "eventId": next_event_id(state.get("events", [])),
        "ruleId": args.rule,
        "situationId": last.get("situationId"),
        "snapshot": bounded(last.get("snapshot") or "", SNAPSHOT_MAX_CHARS),
        "response": args.response,
        "escalated": bool(last.get("escalated")),
        "created": utc_now(),
    }
    state.setdefault("events", []).insert(0, event)

    stats = rule.setdefault("stats", {"hits": 0, "accepted": 0, "declined": 0,
                                      "ignored": 0, "lastSeen": None})
    stats[args.response] = int(stats.get(args.response, 0)) + 1
    stats["lastSeen"] = event["created"]

    promo = rule.setdefault("promotion", {})
    promo["consecutive"] = next_consecutive(promo.get("consecutive", 0), args.response)
    promo["destructiveExempt"] = is_destructive_exempt(rule.get("confirmationClass"))
    threshold = resolve_threshold_for(state)
    promo["threshold"] = threshold

    if args.response == "accepted":
        if should_promote(promo["consecutive"], threshold, rule.get("confirmationClass")):
            promo["promoted"] = True
            if rule.get("state") == "active":
                rule["state"] = "promoted"
        else:
            promo["promoted"] = False
    else:
        promo["promoted"] = False
        promo["resetBy"] = event["eventId"]
        if rule.get("state") == "promoted":
            rule["state"] = "active"

    write_index_atomic(root, state)
    payload = {
        "eventId": event["eventId"],
        "ruleId": args.rule,
        "response": args.response,
        "consecutive": promo["consecutive"],
        "promoted": promo["promoted"],
        "state": rule.get("state"),
        "destructiveExempt": promo["destructiveExempt"],
    }
    return EXIT_OK, errors, warnings, semantic, notes, payload


def action_record_manual(root: Path, args) -> tuple:
    """FR-015: a flow the user ran by hand is missed-suggestion evidence."""
    errors, warnings, notes, semantic = [], [], [], []
    if not args.flow or not args.flow.strip():
        errors.append("identifier-malformed")
        return EXIT_INVALID, errors, warnings, semantic, notes, {}

    state, degraded = read_index(root)
    if degraded:
        warnings.append(degraded)
    session = args.session or DEFAULT_SESSION
    last = (state.get("lastSuggestion") or {}).get(session)
    rows = read_telemetry(root)
    session_rows = [r for r in rows if str(r.get("turnId", "")).startswith(f"{session}-")]
    suggested = bool(session_rows and session_rows[-1].get("suggested"))

    entry = {
        "flow": args.flow.strip(),
        "sessionId": session,
        "turnId": (session_rows[-1].get("turnId") if session_rows else None),
        "suggested": suggested,
        "situationId": (last or {}).get("situationId"),
        "ts": utc_now(),
    }
    state.setdefault("manualInvocations", []).append(entry)
    write_index_atomic(root, state)

    if not suggested:
        notes.append(f"missed-suggestion evidence recorded for {entry['flow']}")
        semantic.append({
            "question": "which situation should this manually-invoked flow bind to?",
            "flow": entry["flow"],
            "sessionId": session,
        })
    payload = {"recorded": True, "missed": not suggested, **entry}
    return EXIT_OK, errors, warnings, semantic, notes, payload


def telemetry_summary(rows: list, session: str | None, config: dict) -> dict:
    """C-23: rows is the window-bounded file; turns is this session's own rows."""
    if session:
        scoped = [r for r in rows if str(r.get("turnId", "")).startswith(f"{session}-")]
    else:
        scoped = list(rows)
    turns = len(scoped)
    escalated = sum(1 for r in scoped if r.get("escalated"))
    suggested = sum(1 for r in scoped if r.get("suggested"))
    visible = sum(1 for r in scoped if r.get("visibleOutput"))
    pct = (escalated / turns * 100.0) if turns else 0.0
    budget = int(config.get("probeBudgetPct", DEFAULT_CONFIG["probeBudgetPct"]))
    return {
        "rows": len(rows),
        "window": int(config.get("telemetryWindow", DEFAULT_CONFIG["telemetryWindow"])),
        "turns": turns,
        "escalated": escalated,
        "suggested": suggested,
        "visibleOutputCount": visible,
        "escalationPct": round(pct, 2),
        "probeBudgetPct": budget,
        "budgetOver": pct > budget,
    }


def action_status(root: Path, args) -> tuple:
    errors, warnings, notes, semantic = [], [], [], []
    state, degraded = read_index(root)
    if degraded:
        warnings.append(degraded)
    config = dict(state.get("config") or DEFAULT_CONFIG)
    config["threshold"] = resolve_threshold_for(state, args.threshold)
    rules = state.get("rules", [])
    by_state = {s: 0 for s in RULE_STATES}
    for rule in rules:
        by_state[rule.get("state", "active")] = by_state.get(rule.get("state", "active"), 0) + 1
    rows = read_telemetry(root)
    payload = {
        "config": config,
        "ruleCountByState": by_state,
        "promotedRules": sorted(r["ruleId"] for r in rules
                                if (r.get("promotion") or {}).get("promoted")),
        "pendingProposals": sum(1 for p in state.get("proposals", [])
                                if p.get("state") == "proposed"),
        "telemetry": telemetry_summary(rows, args.session, config),
    }
    if degraded:
        payload["degraded"] = "suggest-only"
    return EXIT_OK, errors, warnings, semantic, notes, payload


def action_rules(root: Path, args) -> tuple:
    errors, warnings, notes, semantic = [], [], [], []
    state, degraded = read_index(root)
    if degraded:
        warnings.append(degraded)
    rules = sorted(state.get("rules", []), key=lambda r: r["ruleId"])
    payload = {"rules": rules, "count": len(rules)}
    return EXIT_OK, errors, warnings, semantic, notes, payload


def action_reset(root: Path, args) -> tuple:
    errors, warnings, notes, semantic = [], [], [], []
    state, degraded = read_index(root)
    if degraded:
        warnings.append(degraded)
    stamp = utc_now()

    if args.all:
        targets = state.get("rules", [])
    elif args.rule:
        if not RULE_ID_RE.match(args.rule):
            errors.append("identifier-malformed")
            return EXIT_INVALID, errors, warnings, semantic, notes, {}
        targets = [r for r in state.get("rules", []) if r["ruleId"] == args.rule]
        if not targets:
            errors.append("rule-not-found")
            return EXIT_NOT_FOUND, errors, warnings, semantic, notes, {}
    else:
        errors.append("identifier-malformed")
        return EXIT_USAGE, errors, warnings, semantic, notes, {}

    for rule in targets:
        promo = rule.setdefault("promotion", {})
        promo["consecutive"] = 0
        promo["promoted"] = False
        promo["userResetAt"] = stamp
        if rule.get("state") == "promoted":
            rule["state"] = "active"

    if args.all:
        # V6.8: otherwise the first turn after a reset stays suppressed and the
        # user sees no evidence that the reset took effect.
        state["lastSuggestion"] = {}
    write_index_atomic(root, state)
    notes.append(f"reset {len(targets)} rule(s)" + (" and cleared session suppression"
                                                    if args.all else ""))
    return EXIT_OK, errors, warnings, semantic, notes, {
        "reset": [r["ruleId"] for r in targets],
        "clearedSuppression": bool(args.all),
        "userResetAt": stamp,
    }


def action_config(root: Path, args) -> tuple:
    errors, warnings, notes, semantic = [], [], [], []
    state, degraded = read_index(root)
    if degraded:
        warnings.append(degraded)
    config = state.setdefault("config", dict(DEFAULT_CONFIG))
    changed = []

    if args.threshold is not None:
        resolved = resolve_threshold(explicit=args.threshold,
                                     env_value=os.environ.get(THRESHOLD_ENV),
                                     stored=config.get("threshold"))
        if threshold_below_floor(resolved):
            errors.append("threshold-below-floor")
            return EXIT_USAGE, errors, warnings, semantic, notes, {
                "config": config, "rejected": {"threshold": resolved}}
        config["threshold"] = resolved
        rejudge_promotions(state)
        changed.append(f"threshold={resolved}")

    for flag, key, caster in (
        ("window", "telemetryWindow", int),
        ("probe_budget", "probeBudgetPct", int),
        ("min_sample", "minSample", int),
    ):
        value = getattr(args, flag, None)
        if value is not None:
            try:
                config[key] = caster(value)
            except (TypeError, ValueError):
                errors.append("identifier-malformed")
                return EXIT_INVALID, errors, warnings, semantic, notes, {"config": config}
            changed.append(f"{key}={config[key]}")

    if args.enabled is not None:
        text = str(args.enabled).strip().lower()
        if text in ("true", "1", "yes", "on"):
            new = True
        elif text in ("false", "0", "no", "off"):
            new = False
        else:
            errors.append("identifier-malformed")
            return EXIT_INVALID, errors, warnings, semantic, notes, {"config": config}
        previous = bool(config.get("enabled", True))
        config["enabled"] = new
        changed.append(f"enabled={new}")
        if new and not previous:
            # V6.8: re-enabling must not inherit stale suppression.
            state["lastSuggestion"] = {}
            notes.append("re-enabled: session suppression cleared")

    if args.window is not None:
        truncate_telemetry(root, config.get("telemetryWindow",
                                            DEFAULT_CONFIG["telemetryWindow"]))

    write_index_atomic(root, state)
    return EXIT_OK, errors, warnings, semantic, notes, {
        "config": config, "changed": changed,
        "promotedRules": sorted(r["ruleId"] for r in state.get("rules", [])
                                if (r.get("promotion") or {}).get("promoted")),
    }


def action_rotate(root: Path, args) -> tuple:
    """FR-009a / V4.4: telemetry only. index.json is never touched."""
    errors, warnings, notes, semantic = [], [], [], []
    state, degraded = read_index(root)
    if degraded:
        warnings.append(degraded)
    config = state.get("config") or {}
    window = int(config.get("telemetryWindow", DEFAULT_CONFIG["telemetryWindow"]))
    before = len(read_telemetry(root))
    truncate_telemetry(root, window)
    after = len(read_telemetry(root))
    notes.append(f"rotated telemetry {before} -> {after} rows (window {window}); "
                 "index.json untouched")
    return EXIT_OK, errors, warnings, semantic, notes, {
        "rowsBefore": before, "rowsAfter": after, "window": window,
        "indexTouched": False,
    }


def proposal_key(kind, rule_id=None, flow=None) -> tuple:
    return (kind, rule_id or "", flow or "")


def action_tune(root: Path, args) -> tuple:
    errors, warnings, notes, semantic = [], [], [], []
    state, degraded = read_index(root)
    if degraded:
        warnings.append(degraded)
    config = state.get("config") or {}
    min_sample = args.min_sample if args.min_sample is not None else \
        int(config.get("minSample", DEFAULT_CONFIG["minSample"]))

    existing = state.setdefault("proposals", [])
    open_keys = {proposal_key(p.get("kind"), p.get("ruleId"), p.get("flow"))
                 for p in existing if p.get("state") in ("proposed", "ratified")}

    missed = {}
    for entry in state.get("manualInvocations", []):
        if entry.get("suggested"):
            continue
        missed[entry["flow"]] = missed.get(entry["flow"], 0) + 1

    def next_proposal_id() -> str:
        used = {p.get("proposalId") for p in existing}
        n = 1
        while f"p-{n:03d}" in used:
            n += 1
        return f"p-{n:03d}"

    created = 0
    for rule in state.get("rules", []):
        stats = rule.get("stats") or {}
        hits = int(stats.get("hits", 0))
        declined = int(stats.get("declined", 0))
        ignored = int(stats.get("ignored", 0))
        if hits < min_sample:
            # FR-017: skipped rules are named, not silently dropped.
            if hits and (declined or ignored):
                notes.append(f"small-sample guard: {rule['ruleId']} skipped "
                             f"(hits={hits} < minSample={min_sample})")
            continue

        kind = metric = value = None
        if hits and declined / hits >= SUPPRESS_RATIO:
            kind, metric, value = "suppress", "declineRate", round(declined / hits, 4)
        elif hits and ignored / hits >= TIGHTEN_RATIO:
            kind, metric, value = "tighten", "ignoreRate", round(ignored / hits, 4)
        if kind is None:
            continue
        key = proposal_key(kind, rule["ruleId"])
        if key in open_keys:
            continue
        pid = next_proposal_id()
        existing.append({
            "proposalId": pid, "kind": kind, "ruleId": rule["ruleId"],
            "evidence": {"metric": metric, "value": value, "sampleSize": hits},
            "state": "proposed", "createdAt": utc_now(),
        })
        open_keys.add(key)
        created += 1
        semantic.append({
            "question": f"adopt {kind} for {rule['ruleId']}?",
            "proposalId": pid, "metric": metric, "value": value, "sampleSize": hits,
        })

    for flow, count in sorted(missed.items()):
        if count < ADD_RULE_MIN_MISSED:
            continue
        key = proposal_key("add-rule", None, flow)
        if key in open_keys:
            continue
        pid = next_proposal_id()
        existing.append({
            "proposalId": pid, "kind": "add-rule", "flow": flow,
            "evidence": {"metric": "missedInvocations", "value": count,
                         "sampleSize": count},
            "state": "proposed", "createdAt": utc_now(),
        })
        open_keys.add(key)
        created += 1
        semantic.append({
            "question": f"which situation should {flow} bind to?",
            "proposalId": pid, "missedInvocations": count,
        })

    write_index_atomic(root, state)
    notes.append(f"minSample={min_sample}; {created} new proposal(s)")
    payload = {
        "proposals": existing,
        "created": created,
        "minSample": min_sample,
        "missedFlows": missed,
    }
    return EXIT_OK, errors, warnings, semantic, notes, payload


def action_tune_apply(root: Path, args) -> tuple:
    errors, warnings, notes, semantic = [], [], [], []
    if not args.proposal or not PROPOSAL_ID_RE.match(args.proposal):
        errors.append("identifier-malformed")
        return EXIT_INVALID, errors, warnings, semantic, notes, {}
    if not args.reason or not args.reason.strip():
        errors.append("identifier-malformed")
        return EXIT_USAGE, errors, warnings, semantic, notes, {}

    state, degraded = read_index(root)
    if degraded:
        warnings.append(degraded)
    proposal = next((p for p in state.get("proposals", [])
                     if p.get("proposalId") == args.proposal), None)
    if proposal is None:
        errors.append("proposal-not-found")
        return EXIT_NOT_FOUND, errors, warnings, semantic, notes, {}
    if proposal.get("state") == "applied":
        notes.append(f"{args.proposal} already applied")
        return EXIT_OK, errors, warnings, semantic, notes, {"proposal": proposal}

    # SM-2: ratification and application are separately dated, so "approved"
    # stays an auditable event rather than being conflated with "took effect".
    ratified_at = utc_now()
    proposal["state"] = "ratified"
    proposal["ratifiedAt"] = ratified_at
    proposal["reason"] = args.reason.strip()

    rule_id = proposal.get("ruleId")
    rule = next((r for r in state.get("rules", []) if r.get("ruleId") == rule_id), None) \
        if rule_id else None
    if rule is not None:
        tuning = rule.setdefault("tuning", {})
        tuning["ratifiedAt"] = ratified_at
        tuning["evidenceRef"] = (f"{proposal['proposalId']}#"
                                 f"{(proposal.get('evidence') or {}).get('metric', 'evidence')}")
        if proposal["kind"] == "suppress":
            tuning["suppressedBy"] = proposal["proposalId"]
            rule["state"] = "suppressed"
            promo = rule.setdefault("promotion", {})
            promo["promoted"] = False
        elif proposal["kind"] == "tighten":
            rule["priority"] = int(rule.get("priority", 100)) + 10
            tuning["tightenedBy"] = proposal["proposalId"]

    proposal["state"] = "applied"
    proposal["appliedAt"] = utc_now()

    if proposal["kind"] in ("add-rule", "extend-vocabulary"):
        semantic.append({
            "question": "author the new rule text and its situation binding",
            "proposalId": proposal["proposalId"],
            "flow": proposal.get("flow"),
            "note": "the engine will not invent a situation or a flow mapping",
        })

    write_index_atomic(root, state)
    notes.append(f"applied {proposal['proposalId']} ({proposal['kind']})")
    return EXIT_OK, errors, warnings, semantic, notes, {
        "proposal": proposal,
        "ruleId": rule_id,
        "ruleState": (rule or {}).get("state"),
    }


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------

def render_text(env: dict) -> str:
    action = env["action"]
    payload = env.get("payload") or {}
    lines = [f"{action}: {'ok' if env.get('ok') else 'failed'}"]
    for code in env.get("errors", []):
        lines.append(f"  error: {code}")
    for code in env.get("warnings", []):
        lines.append(f"  warning: {code}")
    for note in env.get("notes", []):
        lines.append(f"  note: {bounded(note, 160)}")

    if action == "status":
        cfg = payload.get("config", {})
        tel = payload.get("telemetry", {})
        lines.append(f"  enabled={cfg.get('enabled')} threshold={cfg.get('threshold')} "
                     f"window={cfg.get('telemetryWindow')} "
                     f"probeBudgetPct={cfg.get('probeBudgetPct')} "
                     f"minSample={cfg.get('minSample')}")
        counts = payload.get("ruleCountByState", {})
        lines.append("  rules: " + " ".join(f"{k}={counts.get(k, 0)}" for k in RULE_STATES))
        promoted = payload.get("promotedRules") or []
        lines.append(f"  promoted: {','.join(promoted) or 'none'}")
        lines.append(f"  pendingProposals: {payload.get('pendingProposals', 0)}")
        lines.append(f"  telemetry: rows={tel.get('rows')} turns={tel.get('turns')} "
                     f"escalated={tel.get('escalated')} suggested={tel.get('suggested')} "
                     f"visibleOutputCount={tel.get('visibleOutputCount')}")
        lines.append(f"  escalationPct={tel.get('escalationPct')} "
                     f"budget={tel.get('probeBudgetPct')} "
                     f"over={tel.get('budgetOver')}")
    elif action == "rules":
        lines.append("  ruleId situationId flow class origin state consecutive hits declined")
        for rule in payload.get("rules", []):
            promo = rule.get("promotion") or {}
            stats = rule.get("stats") or {}
            lines.append(
                f"  {rule['ruleId']} {rule['situationId']} {rule['flow']} "
                f"{rule['confirmationClass']} {rule.get('origin')} {rule.get('state')} "
                f"{promo.get('consecutive', 0)} {stats.get('hits', 0)} "
                f"{stats.get('declined', 0)}"
            )
    elif action == "assess":
        sug = payload.get("suggestion")
        if sug:
            lines.append(f"  situation: {payload.get('situationId')}")
            lines.append(f"  suggest: {sug['invocation']}")
            lines.append(f"  why: {bounded(sug['rationale'], 160)}")
            lines.append(f"  autoExecute: {sug['autoExecute']}")
        elif payload.get("suppressed"):
            lines.append("  suppressed: unchanged since the last suggestion this session")
        else:
            lines.append(f"  no suggestion ({payload.get('reason', 'no-situation-match')})")
        for item in payload.get("probes", []) or []:
            lines.append(f"  probe: {item}")
    else:
        for key in sorted(payload):
            value = payload[key]
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            lines.append(f"  {key}: {bounded(value, 160)}")

    for item in env.get("semanticJudgmentPending", []):
        lines.append(f"  judgment: {bounded(item if isinstance(item, str) else json.dumps(item, ensure_ascii=False), 160)}")
    return "\n".join(lines[:STATUS_TEXT_MAX_LINES * 2]) + "\n"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

class _UsageError(Exception):
    """Raised instead of argparse's own exit(2) so C-9/C-10 hold on the usage path."""


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # noqa: D102 - argparse hook
        raise _UsageError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="trigger-utils.py",
        description="Proactive flow trigger engine (deterministic half).",
    )
    parser.add_argument("--action", required=True, choices=list(ACTIONS))
    parser.add_argument("--format", default="json", choices=["text", "json"])
    parser.add_argument("--workspace", default=None)
    parser.add_argument("--session", default=None)
    parser.add_argument("--turn-id", dest="turn_id", default=None)
    parser.add_argument("--stage", default=None)
    parser.add_argument("--signal", action="append", default=None)
    parser.add_argument("--probe", action="store_true", default=False)
    # C-10/C-14: defaults to False on purpose. The ordering contract must be
    # declared explicitly by the caller, never satisfied by default.
    parser.add_argument("--compliance-done", dest="compliance_done",
                        action="store_true", default=False)
    parser.add_argument("--rule", default=None)
    parser.add_argument("--response", default=None, choices=list(RESPONSES))
    parser.add_argument("--flow", default=None)
    parser.add_argument("--threshold", type=int, default=None)
    parser.add_argument("--enabled", default=None)
    parser.add_argument("--window", type=int, default=None)
    parser.add_argument("--probe-budget", dest="probe_budget", type=int, default=None)
    parser.add_argument("--proposal", default=None)
    parser.add_argument("--reason", default=None)
    parser.add_argument("--all", action="store_true", default=False)
    parser.add_argument("--min-sample", dest="min_sample", type=int, default=None)
    return parser


HANDLERS = {
    "init": action_init,
    "assess": action_assess,
    "record": action_record,
    "record-manual": action_record_manual,
    "status": action_status,
    "rules": action_rules,
    "reset": action_reset,
    "config": action_config,
    "tune": action_tune,
    "tune-apply": action_tune_apply,
    "rotate": action_rotate,
}


def emit(env: dict, fmt: str) -> None:
    if fmt == "text":
        sys.stdout.write(render_text(env))
    else:
        sys.stdout.write(json.dumps(env, ensure_ascii=False, indent=2) + "\n")


def main(argv=None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except _UsageError as exc:
        env = envelope("unknown", ".", [str(exc)], [], [], [], {})
        env["ok"] = False
        emit(env, "json")
        return EXIT_USAGE

    root = resolve_root(args.workspace)
    handler = HANDLERS.get(args.action)
    if handler is None:  # pragma: no cover - argparse choices already guard this
        emit(envelope(args.action, root, ["identifier-malformed"], [], [], [], {}),
             args.format)
        return EXIT_USAGE

    try:
        code, errors, warnings, semantic, notes, payload = handler(root, args)
    except OSError as exc:
        emit(envelope(args.action, root, [f"input-error: {exc}"], [], [], [], {}),
             args.format)
        return EXIT_INPUT_ERROR

    env = envelope(args.action, root, errors, warnings, semantic, notes, payload)
    env["ok"] = code == EXIT_OK and not errors
    if args.action == "assess" and "ordering-violation" in errors:
        # The turn still succeeded; the violation is a reported fact (SC-012).
        env["ok"] = True
    emit(env, args.format)
    return code


if __name__ == "__main__":
    sys.exit(main())
