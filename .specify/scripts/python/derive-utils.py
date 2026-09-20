#!/usr/bin/env python3
"""Derivation engine for `/speckit.derive` (requirement 048, Feature 049).

The command owns the interaction and every semantic judgment; this engine owns
the deterministic parts — identity issuance, structural validation, dedup, link
probing and counting. Fixed rules belong in a program, not in a model
(Program-First).

A Derivation reaches an architecture by replaying the reasoning methods of
verified sources. Four record kinds compose it: Source (S-nnn, per topic),
Reasoning Move (M-nnn, project-wide), Derivation Step (D-k) and Architecture
Element (A-k), with Open Questions (Q-k) holding every gap the chain could not
close. Nothing here decides what a source *means* — only whether an artifact
claiming to derive something is structurally honest about it.

Concept authority: shared/definitions/derivation-definitions.md
Contract:  .specify/specs/048-derive-command/contracts/derive-engine.md
           .specify/specs/048-derive-command/contracts/derivation-model.md
           .specify/specs/048-derive-command/contracts/move-library.md

Actions:
  init         --slug <topic-slug> [--force] [--max-steps N]
  validate     (--file <path> | --slug <slug>) [--max-steps N]
  moves-list   [--name-contains X] [--status active|superseded] [--anchor REF]
  moves-add    --file <moves.json>
  probe-links  --file <urls.json>
  stats        [--file <path> | --slug <slug>]

Exit codes: 0 ok | 1 usage | 2 input error | 3 not found | 4 validation failed
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_INPUT_ERROR = 2
EXIT_NOT_FOUND = 3
EXIT_INVALID = 4

_HERE = Path(__file__).resolve()
REPO_ROOT = _HERE.parents[2]
if REPO_ROOT.name == ".specify":  # invoked from the strict mirror copy
    REPO_ROOT = REPO_ROOT.parent

# C-5: storage locations are pinned constants, never configuration.
ARCHIVE_DIRNAME = ".specify/derive"
MOVES_FILENAME = "moves.md"
ARCHIVE_FILENAME = "derive.md"

DEFAULT_MAX_STEPS = 12
PROBE_TIMEOUT_SECONDS = 10

# C-29 (move-library): pinned copy of the threshold owned by
# shared/guidelines/token-efficiency.md §小文件阈值. A drift test keeps them equal.
SMALL_FILE_MAX_LINES = 100
SMALL_FILE_MAX_BYTES = 10 * 1024

#: Identity grammar reused from goal-utils.py — no second grammar (C-6).
_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")

SOURCE_ID_RE = re.compile(r"^S-\d{3,}$")
QUALIFIED_SOURCE_RE = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.\-]*)\.S-(\d{3,})$")
MOVE_ID_RE = re.compile(r"^M-(\d{3,})$")
STEP_ID_RE = re.compile(r"^(D|A|Q)-\d{1,}$")
PROJECTION_MARKER_RE = re.compile(r"<!--\s*projection of moves\.md#(M-\d{3,})\s*-->")
RESTATED_MOVE_ROW_RE = re.compile(r"^\|\s*(M-\d{3,})\s*\|")

GRADES = ("primary", "authoritative-secondary", "community", "unverified")
ANCHORING_GRADES = frozenset({"primary", "authoritative-secondary"})
ACCESS_VALUES = ("live", "dead", "paywalled", "unknown")
#: tally buckets — `wayback:<ts>` collapses to `wayback` so the key set is
#: the complete enum (C-19) rather than one key per snapshot timestamp.
ACCESS_BUCKETS = ("live", "wayback", "dead", "paywalled", "unknown")
RESOLVED_VIA = ("direct", "websearch", "wayback")
MOVE_STATUSES = ("active", "superseded")
DISPOSITIONS = ("new", "reused", "reinforced")
MOVE_INTENTS = ("new", "reuse", "reinforce", "supersede")
CONFIDENCES = ("derived", "provisional", "contested")
CONFIDENCE_RANK = {"derived": 2, "provisional": 1, "contested": 0}
ATTESTATION_RESULTS = ("attested", "not-attested", "pending")
TERMINATION_CONDITIONS = ("a", "b")
SEMANTIC_CHECKS_PENDING = ("A11", "A14", "A16")
ENGINE_CHECKS = ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "A12", "A13",
                 "A15")
ALL_CHECKS = tuple("A%d" % n for n in range(1, 17))

NO_ONLINE_CAPABILITY = "no-online-capability"

#: Concept-anchor §Banned Justifications — pinned copy. A drift test asserts this
#: equals the anchor's list and requirements.md [[STR-001]] (derivation-model C-16).
BANNED_JUSTIFICATIONS = (
    "best practice", "best practices", "industry standard", "commonly accepted",
    "it is generally agreed", "everyone knows", "as is well known", "obviously",
    "业界通用", "业界最佳实践", "最佳实践", "众所周知", "经验之谈", "权威做法", "不言而喻",
)

BARE_ATTESTATIONS = frozenset({
    "verified", "checked", "confirmed", "ok", "fine", "good", "n/a", "na", "none",
    "-", "—", "已核实", "已确认", "已检查", "无", "略", "经分析", "见上",
})
VACUOUS_FALSIFICATION = frozenset({"none", "n/a", "na", "-", "—", "无"})
VERIFICATION_MIN_CODEPOINTS = 16
DERIVATION_MIN_CODEPOINTS = 40

#: C-33 evidence tokens — hitting any one means the cell cites concrete evidence.
EVIDENCE_TOKEN_RES = (
    re.compile(r"https?://"),
    re.compile(r"\b[1-5]\d{2}\b"),
    re.compile(r"\b(?:19|20)\d{12}\b"),
    re.compile(r"search:\s*\S+"),
    re.compile(r"result #\d+"),
)

#: C-44 — exactly six, MUST NOT grow or shrink.
WARNING_CODES = frozenset({
    "secondary-sole-anchor", "unresolved-title", "verification-evidence-token-absent",
    "step-budget-reached", "attestation-method-degenerate", "degraded-run",
})

#: C-20 — audit results are DERIVED from error codes, never maintained separately.
AUDIT_CODE_MAP = {
    "A1": {"grade-not-in-enum", "title-mismatch-asserted", "title-mismatch-without-both-titles",
           "verification-too-short", "verification-bare-attestation",
           "unknown-access-with-verified-grade"},
    "A2": {"premise-grade-ineligible", "unverified-source-unrecorded"},
    "A3": {"resolved-title-not-cited"},
    "A4": {"orphan-source-premise", "unresolved-lead", "forward-step-reference",
           "self-referential-step"},
    "A5": {"banned-justification"},
    "A6": {"falsification-vacuous-literal", "falsification-restates-conclusion"},
    "A7": {"element-derived-from-missing", "element-derived-from-unresolved"},
    "A8": {"element-confidence-not-minimum"},
    "A9": {"move-not-in-library", "unmarked-move-copy", "divergent-move-projection",
           "superseded-move-applied"},
    "A10": {"open-question-link-unresolved", "blocked-element-not-downgraded",
            "contested-not-routed"},
    "A12": {"termination-condition-absent", "step-budget-diverges", "step-budget-exceeded"},
    "A13": {"moves-library-hand-edited", "newly-issued-move-unresolved"},
    "A15": {"criterion-id-malformed", "criterion-duplicate-id", "criterion-kind-invalid",
            "criterion-provenance-invalid", "criterion-statement-empty",
            "criterion-source-unresolved", "agent-prior-without-owner",
            "agent-prior-without-identity", "dp-field-missing",
            "dp-selected-not-candidate", "dp-ranking-without-criterion",
            "dp-alternates-exceed-two", "dp-alternate-without-trigger",
            "dp-reference-unresolved"},
}

SEC_SOURCES = "## Sources"
SEC_UNVERIFIABLE = "## Unverifiable Sources"
SEC_MOVES_APPLIED = "## Reasoning Moves Applied"
SEC_CHAIN = "## Derivation Chain"
SEC_TERMINATION = "## Termination"
SEC_ARCHITECTURE = "## Derived Architecture"
SEC_QUESTIONS = "## Open Questions"
SEC_AUDIT = "## Self-Audit"
ARTIFACT_SECTIONS = (SEC_SOURCES, SEC_UNVERIFIABLE, SEC_MOVES_APPLIED, SEC_CHAIN,
                     SEC_TERMINATION, SEC_ARCHITECTURE, SEC_QUESTIONS, SEC_AUDIT)

#: Optional sections (criteria/decision-point layer). Deliberately NOT in
#: ARTIFACT_SECTIONS: an archive predating the criterion layer must still
#: validate — a missing section parses to zero rows and A15 passes vacuously.
SEC_IDENTITY = "## Agent Identity"
SEC_CRITERIA = "## Criteria"
SEC_DECISIONS = "## Decision Points"

#: Criterion record — the ranking grounds a Decision Point may cite.
#: provenance `source` = truth-claim grounded in an S-row; `declared` =
#: stakeholder-stated criterion; `agent-prior` = signed decision-claim owned
#: by the run's Agent Identity (revisable by re-declaration, never a
#: truth-claim — the category distinction the banned-justification set guards).
CRITERION_COLUMNS = ("id", "statement", "kind", "provenance", "owner", "weight", "defeater")
CRITERION_KINDS = ("constraint", "preference")
CRITERION_PROVENANCES = ("source", "declared", "agent-prior")
CRITERION_ID_RE = re.compile(r"^C-\d{3,}$")
DP_MAX_ALTERNATES = 2

SOURCE_COLUMNS = ("id", "claimed_title", "resolved_title", "title_mismatch",
                  "grade", "url", "access", "resolved_via", "verification")
MOVE_COLUMNS = ("move_id", "name", "inference_form", "prevents",
                "applies_when", "anchor", "status")
AUDIT_COLUMNS = ("#", "check", "method", "result")
AUDIT_HEADER = "| # | check | method | result |"

MOVES_TITLE = "# Reasoning Move Library"
MOVES_MARKER = ("<!-- engine-written: derive-utils.py --action moves-add is the only "
                "writer; hand edits are DETECTED by validate, never silently accepted -->")
MOVES_HEADER = "| move_id | name | inference_form | prevents | applies_when | anchor | status |"
MOVES_SEPARATOR = "|---------|------|----------------|----------|--------------|--------|--------|"

WAYBACK_AVAILABILITY = "https://archive.org/wayback/available?url="
USER_AGENT = "spec-kit-derive-utils (link-liveness corroborator; offline-tolerant)"

_SLOT_BACKTICK_RE = re.compile(r"`[^`]+`")
_SLOT_SINGLE_UPPER_RE = re.compile(r"(?<![A-Za-z])[A-Z](?![A-Za-z])")
_CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")


# --------------------------------------------------------------------------
# normalization (derivation-model C-22 — five steps, in order)
# --------------------------------------------------------------------------

def normalize_text(value: str) -> str | None:
    """① NFKC ② casefold ③ drop Unicode P*/S* codepoints and ZWSP/BOM
    ④ collapse whitespace ⑤ empty -> None. No similarity thresholds, no edit distance."""
    if value is None:
        return None
    text = unicodedata.normalize("NFKC", value)
    text = text.casefold()
    kept = []
    for ch in text:
        if ch in ("\u200b", "\ufeff"):
            continue
        if unicodedata.category(ch).startswith(("P", "S")):
            continue
        kept.append(ch)
    text = re.sub(r"\s+", " ", "".join(kept)).strip()
    return text or None


def slot_isomorphic_key(value: str) -> str | None:
    """Second dedup level (move-library C-14): named slots carry no semantics, so
    the same inference shape written with different slot letters is one move."""
    normalized = normalize_text(value)
    if normalized is None:
        return None
    text = _SLOT_BACKTICK_RE.sub("<SLOT>", value or "")
    text = _SLOT_SINGLE_UPPER_RE.sub("<SLOT>", text)
    return normalize_text(text)


# --------------------------------------------------------------------------
# workspace resolution
# --------------------------------------------------------------------------

def resolve_root(workspace_root: str | None) -> Path:
    root = Path(workspace_root or ".").resolve()
    if root.name == ".specify":
        root = root.parent
    return root


def derive_root(root: Path) -> Path:
    return root / ARCHIVE_DIRNAME


def moves_path(root: Path) -> Path:
    return derive_root(root) / MOVES_FILENAME


def archive_path(root: Path, slug: str) -> Path:
    return derive_root(root) / slug / ARCHIVE_FILENAME


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------
# markdown table primitives
# --------------------------------------------------------------------------

def split_cells(line: str) -> list[str]:
    """Split on unescaped pipes (move-library C-4); `\\|` inside a cell is literal."""
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [c.replace("\\|", "|").strip() for c in _CELL_SPLIT_RE.split(body)]


def escape_cell(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\n", "; ").strip()


def render_table(columns, rows) -> str:
    out = ["| " + " | ".join(columns) + " |",
           "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(escape_cell(str(row.get(c, ""))) for c in columns) + " |")
    return "\n".join(out)


def parse_table(text: str, columns) -> list[dict]:
    header = "| " + " | ".join(columns) + " |"
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if line.strip() != header:
            continue
        rows = []
        for row_line in lines[idx + 2:]:
            if not row_line.strip().startswith("|"):
                break
            cells = split_cells(row_line)
            if len(cells) < len(columns):
                cells += [""] * (len(columns) - len(cells))
            rows.append({c: cells[i] for i, c in enumerate(columns)})
        return rows
    return []


def section(text: str, heading: str) -> str:
    m = re.search(r"^" + re.escape(heading) + r"\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def parse_blocks(body: str, prefix: str) -> list[dict]:
    blocks = []
    pattern = r"^###\s+(" + re.escape(prefix) + r"-\d+)([^\n]*)\n(.*?)(?=^###\s|\Z)"
    for m in re.finditer(pattern, body, re.M | re.S):
        fields = {"_id": m.group(1), "_title": m.group(2).strip()}
        for line in m.group(3).splitlines():
            fm = re.match(r"^-\s+([A-Za-z][A-Za-z0-9_\-]*)\s*:\s*(.*)$", line)
            if fm:
                fields[fm.group(1)] = fm.group(2).strip()
        blocks.append(fields)
    return blocks


def parse_id_list(value: str) -> list[str]:
    return [t.strip() for t in re.split(r"[,;]\s*", value or "") if t.strip()]


# --------------------------------------------------------------------------
# report + envelope
# --------------------------------------------------------------------------

class Report:
    """One error per fact, deduped by (rule, locator) — derivation-model C-3."""

    def __init__(self) -> None:
        self._seen = set()
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.notes: list[str] = []

    def error(self, rule, code, locator, message, value=None):
        key = (rule, locator)
        if key in self._seen:
            return
        self._seen.add(key)
        entry = {"rule": rule, "code": code, "locator": locator, "message": message}
        if value is not None:
            entry["value"] = value
        self.errors.append(entry)

    def warn(self, code, locator, message):
        if code not in WARNING_CODES:  # C-44: the warning set is closed
            raise AssertionError("warning code %r is not in the closed six" % code)
        self.warnings.append({"code": code, "locator": locator, "message": message})

    def note(self, text):
        self.notes.append(text)

    @property
    def ok(self) -> bool:
        return not self.errors

    def audit_engine(self) -> dict:
        hit = {e["code"] for e in self.errors}
        return {a: ("fail" if hit & codes else "pass") for a, codes in AUDIT_CODE_MAP.items()}


def envelope(action, root, rep, payload, ok=None) -> dict:
    return {
        "ok": rep.ok if ok is None else ok,
        "action": action,
        "workspaceRoot": str(root),
        "generatedAt": utc_now(),
        "errors": rep.errors,
        "warnings": rep.warnings,
        "semanticChecksPending": list(SEMANTIC_CHECKS_PENDING) if action == "validate" else [],
        "notes": rep.notes,
        "payload": payload,
    }


def error_envelope(action, root, code, message, locator="<input>", rule=None,
                   exit_code=EXIT_INPUT_ERROR, notes=None):
    """A single-error envelope. Built explicitly rather than with `dict | dict`,
    which is 3.9+ while this project's floor is Python 3.8."""
    data = envelope(action, root, Report(), {}, ok=False)
    data["errors"] = [{"rule": rule, "code": code, "locator": locator, "message": message}]
    if notes:
        data["notes"] = list(notes)
    return exit_code, data


def fail_envelope(action, root, code, message, locator=None, exit_code=EXIT_INPUT_ERROR):
    return error_envelope(action, root, code, message, locator or "<input>",
                          exit_code=exit_code)


# --------------------------------------------------------------------------
# move library
# --------------------------------------------------------------------------

def moves_file_text(rows) -> str:
    lines = [MOVES_TITLE, "",
             "Project-level accumulation of inference patterns extracted by `/speckit.derive`.",
             "Concept authority: `shared/definitions/derivation-definitions.md` §Reasoning Move.",
             "", MOVES_MARKER, "", MOVES_HEADER, MOVES_SEPARATOR]
    for row in rows:
        lines.append("| " + " | ".join(escape_cell(str(row.get(c, ""))) for c in MOVE_COLUMNS) + " |")
    return "\n".join(lines) + "\n"


def load_moves(root: Path) -> list[dict]:
    path = moves_path(root)
    if not path.is_file():
        return []
    return parse_table(path.read_text(encoding="utf-8"), MOVE_COLUMNS)


def moves_file_stats(root: Path) -> dict:
    path = moves_path(root)
    if not path.is_file():
        return {"lines": 0, "bytes": 0}
    raw = path.read_bytes()
    return {"lines": raw.decode("utf-8", "replace").count("\n") + 1, "bytes": len(raw)}


def check_library_invariants(rep: Report, root: Path, rows: list[dict]) -> set:
    """A13 / move-library §1–§4: the library's physical and identity invariants."""
    path = moves_path(root)
    ids = set()
    if path.is_file():
        raw = path.read_text(encoding="utf-8")
        if MOVES_MARKER not in raw:
            rep.error("A13", "moves-library-hand-edited", MOVES_FILENAME,
                      "engine-written marker line is missing or altered",
                      value="header-marker-missing")
        if MOVES_HEADER not in raw or MOVES_SEPARATOR not in raw:
            rep.error("A13", "moves-library-hand-edited", MOVES_FILENAME,
                      "table header or separator row does not match the pinned literal",
                      value="row-shape")
        # C-4: every data row must parse to exactly 7 non-empty cells.
        # C-8: rows ascend by move_id with no blank or comment lines between them,
        #      and the file ends in exactly one newline.
        if not raw.endswith("\n") or raw.endswith("\n\n"):
            rep.error("A13", "moves-library-hand-edited", MOVES_FILENAME,
                      "the file must end in exactly one newline", value="row-shape")
        body = raw.split(MOVES_SEPARATOR, 1)[1].lstrip("\n") if MOVES_SEPARATOR in raw else ""
        for offset, line in enumerate(body.splitlines()):
            if not line.strip():
                rep.error("A13", "moves-library-hand-edited",
                          "%s:%d" % (MOVES_FILENAME, offset),
                          "no blank line may separate data rows — a split row would be "
                          "misread as an identity violation", value="row-shape")
                continue
            if not line.strip().startswith("|"):
                rep.error("A13", "moves-library-hand-edited",
                          "%s:%d" % (MOVES_FILENAME, offset),
                          "only the one move table may follow the separator", value="row-shape")
                continue
            cells = split_cells(line)
            if len(cells) != len(MOVE_COLUMNS) or not all(cells):
                rep.error("A13", "moves-library-hand-edited",
                          "%s:%d" % (MOVES_FILENAME, offset),
                          "a data row must parse to exactly %d non-empty cells, got %d"
                          % (len(MOVE_COLUMNS), len(cells)), value="row-shape")
    seen_forms = {}
    highest = 0
    for row in rows:
        mid = (row.get("move_id") or "").strip()
        m = MOVE_ID_RE.match(mid)
        if not m:
            rep.error("A13", "moves-library-hand-edited", mid or "<row>",
                      "move_id must match M-<nnn>; only moves-add issues identities",
                      value="id-grammar")
            continue
        if mid in ids:
            rep.error("A13", "moves-library-hand-edited", mid,
                      "duplicate move_id", value="duplicate-id")
        ids.add(mid)
        num = int(m.group(1))
        if num <= highest:
            rep.error("A13", "moves-library-hand-edited", mid,
                      "identities are monotonic and never renumbered", value="id-not-monotonic")
        highest = num
        status = (row.get("status") or "").strip()
        if status not in MOVE_STATUSES:
            rep.error("A13", "moves-library-hand-edited", mid,
                      "status %r is outside the durable enum %s — run-relative dispositions "
                      "are engine output, never a library column"
                      % (status, "/".join(MOVE_STATUSES)), value="status-not-in-enum")
        form = normalize_text(row.get("inference_form", ""))
        if form is None:
            rep.error("A13", "moves-library-hand-edited", mid,
                      "inference_form must not be empty", value="row-shape")
        elif status == "active":
            # Scoped to active rows: C-18 legitimately produces a superseded row plus
            # an active successor sharing one shape. Two *citable* rows sharing a form
            # is the real defect — dedup should have refused the second.
            iso = slot_isomorphic_key(row.get("inference_form", ""))
            if iso in seen_forms:
                rep.error("A13", "moves-library-hand-edited",
                          "%s/%s" % (seen_forms[iso], mid),
                          "two moves share a slot-isomorphic inference_form — moves-add "
                          "should have refused the second", value="duplicate-form")
            else:
                seen_forms[iso] = mid
        for ref in [a.strip() for a in (row.get("anchor") or "").split(",") if a.strip()]:
            if not QUALIFIED_SOURCE_RE.match(ref):
                rep.error("A13", "moves-library-hand-edited", "%s.anchor" % mid,
                          "anchor %r must be the qualified form <topic-slug>.S-<nnn> — the "
                          "library is project-wide while S-<nnn> is per topic" % ref,
                          value="anchor-form")
        if not (row.get("applies_when") or "").strip():
            rep.error("A13", "moves-library-hand-edited", mid,
                      "applies_when must carry an over-application guard", value="row-shape")
    return ids


def write_moves_atomic(root: Path, rows) -> Path:
    """C-29: write <moves.md>.part then os.replace — never a half-written library."""
    path = moves_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(".md.part")
    part.write_text(moves_file_text(rows), encoding="utf-8")
    os.replace(str(part), str(path))
    return path


def next_move_id(rows) -> str:
    highest = 0
    for row in rows:
        m = MOVE_ID_RE.match((row.get("move_id") or "").strip())
        if m:
            highest = max(highest, int(m.group(1)))
    return "M-%03d" % (highest + 1)


def sort_anchor_refs(refs) -> list[str]:
    """C-20: slug segment lexicographic, then S- number ascending."""
    def key(ref):
        m = QUALIFIED_SOURCE_RE.match(ref)
        return (m.group(1), int(m.group(2))) if m else (ref, 0)
    return sorted(set(refs), key=key)


def moves_add(root: Path, spec: dict):
    rep = Report()
    rows = load_moves(root)
    check_library_invariants(rep, root, rows)
    if not rep.ok:
        rep.note("the library failed its invariants; moves-add refuses to issue identities "
                 "rather than renumber its way past the damage")
        return EXIT_INPUT_ERROR, envelope("moves-add", root, rep, {}, ok=False)

    incoming = spec.get("moves")
    if not isinstance(incoming, list) or not incoming:
                return fail_envelope("moves-add", root, "input-schema",
                               "moves-add needs a non-empty 'moves' list")

    # C-28: schema validation is all-or-nothing — zero writes on any violation.
    prepared = []
    for index, cand in enumerate(incoming):
        if not isinstance(cand, dict):
                        return fail_envelope("moves-add", root, "input-schema",
                                   "moves[%d] must be an object" % index)
        intent = (cand.get("intent") or "new").strip()
        if intent not in MOVE_INTENTS:
                        return fail_envelope("moves-add", root, "input-schema",
                                   "moves[%d].intent %r is not one of %s"
                                   % (index, intent, "/".join(MOVE_INTENTS)))
        existing_id = (cand.get("existingMoveId") or "").strip()
        if intent in ("reuse", "reinforce", "supersede") and not existing_id:
            return fail_envelope("moves-add", root, "input-schema",
                                 "intent %r requires existingMoveId" % intent)
        anchors = [a.strip() for a in re.split(r"[,;]\s*", str(cand.get("anchor") or ""))
                   if a.strip()]
        if intent == "new":
            for field in ("name", "inferenceForm", "prevents", "appliesWhen"):
                if not str(cand.get(field) or "").strip():
                    return fail_envelope("moves-add", root, "input-schema",
                                         "moves[%d].%s is required" % (index, field))
            if not anchors:
                return fail_envelope("moves-add", root, "input-schema",
                                     "moves[%d].anchor needs at least one source reference"
                                     % index)
        for a in anchors:
            if not QUALIFIED_SOURCE_RE.match(a):
                return fail_envelope(
                    "moves-add", root, "input-schema",
                    "moves[%d].anchor %r must be the qualified form "
                    "<topic-slug>.S-<nnn> — the library is project-wide while "
                    "S-<nnn> is per topic, and moves-add carries no topic to "
                    "qualify a bare reference with" % (index, a))
        prepared.append((index, cand, intent, existing_id, anchors))

    by_form = {}
    for row in rows:
        # move-library C-18: `superseded` is terminal. A shape that is needed again
        # is re-laid as a NEW row — indexing terminal rows here would let an
        # intent:new candidate dedup onto a dead id and grow its anchors, which is
        # revival by another name.
        if (row.get("status") or "").strip() != "active":
            continue
        iso = slot_isomorphic_key(row.get("inference_form", ""))
        if iso:
            by_form[iso] = row
    by_id = {(r.get("move_id") or "").strip(): r for r in rows}

    appended = deduped = superseded = 0
    issued, dispositions, duplicates = [], [], []

    for index, cand, intent, existing_id, anchors in prepared:
        if intent in ("reuse", "reinforce", "supersede"):
            row = by_id.get(existing_id)
            if row is None:
                                return fail_envelope("moves-add", root, "move-not-in-library",
                                       "existingMoveId %r has no library row" % existing_id)
            current = (row.get("status") or "").strip()
            if intent == "supersede":
                if current != "active":  # move-library C-18: superseded is terminal
                                        return fail_envelope("moves-add", root, "illegal-status-transition",
                                           "%s → superseded is not a legal transition "
                                           "(superseded is terminal)" % current)
                row["status"] = "superseded"
                superseded += 1
                continue
            if current != "active":
                                return fail_envelope("moves-add", root, "illegal-status-transition",
                                       "a superseded move cannot be reused or reinforced")
            known = [a.strip() for a in (row.get("anchor") or "").split(",") if a.strip()]
            if intent == "reuse":
                dispositions.append({"moveId": existing_id, "disposition": "reused"})
                continue
            fresh = [a for a in anchors if a not in known]
            if not fresh:  # move-library C-19
                                return fail_envelope("moves-add", root, "reinforce-without-new-anchor",
                                       "reinforce needs at least one anchor the row does not "
                                       "already carry")
            row["anchor"] = ", ".join(sort_anchor_refs(known + fresh))
            dispositions.append({"moveId": existing_id, "disposition": "reinforced"})
            continue

        iso = slot_isomorphic_key(cand.get("inferenceForm", ""))
        hit = by_form.get(iso)
        if hit is not None:
            # C-15: refusing a near-duplicate is the SUCCESS path, exit 0.
            mid = (hit.get("move_id") or "").strip()
            deduped += 1
            duplicates.append({"requestIndex": index, "normalizedForm": iso,
                               "existingMoveId": mid})
            known = [a.strip() for a in (hit.get("anchor") or "").split(",") if a.strip()]
            fresh = [a for a in anchors if a not in known]
            if fresh:
                hit["anchor"] = ", ".join(sort_anchor_refs(known + fresh))
                dispositions.append({"moveId": mid, "disposition": "reinforced"})
            else:
                dispositions.append({"moveId": mid, "disposition": "reused"})
            continue

        mid = next_move_id(rows)
        rows.append({
            "move_id": mid,
            "name": str(cand.get("name", "")).strip(),
            "inference_form": str(cand.get("inferenceForm", "")).strip(),
            "prevents": str(cand.get("prevents", "")).strip(),
            "applies_when": str(cand.get("appliesWhen", "")).strip(),
            "anchor": ", ".join(sort_anchor_refs(anchors)),
            "status": "active",
        })
        by_form[iso] = rows[-1]
        by_id[mid] = rows[-1]
        issued.append(mid)
        appended += 1
        dispositions.append({"moveId": mid, "disposition": "new"})

    try:
        write_moves_atomic(root, rows)
    except OSError as exc:
                return fail_envelope("moves-add", root, "library-write-failed", str(exc))

    payload = {"requested": len(prepared), "appended": appended, "deduped": deduped,
               "superseded": superseded, "issued": issued, "dispositions": dispositions,
               "duplicates": duplicates}
    return EXIT_OK, envelope("moves-add", root, rep, payload)


def moves_list(root: Path, name_contains, status, anchor):
    rep = Report()
    if status is not None and status not in MOVE_STATUSES:
        return fail_envelope("moves-list", root, "input-enum",
                             "--status must be one of the durable values %s; run-relative "
                             "dispositions are not library state" % "/".join(MOVE_STATUSES))
    if anchor is not None and not (SOURCE_ID_RE.match(anchor) or QUALIFIED_SOURCE_RE.match(anchor)):
        return fail_envelope("moves-list", root, "input-enum",
                             "--anchor must match S-<nnn> or <topic-slug>.S-<nnn>")
    rows = load_moves(root)
    out = []
    for row in rows:
        if name_contains and name_contains.casefold() not in (row.get("name") or "").casefold():
            continue
        if status and (row.get("status") or "").strip() != status:
            continue
        if anchor and anchor not in [a.strip() for a in (row.get("anchor") or "").split(",")]:
            continue
        out.append({"moveId": row.get("move_id"), "name": row.get("name"),
                    "inferenceForm": row.get("inference_form"), "prevents": row.get("prevents"),
                    "appliesWhen": row.get("applies_when"), "anchor": row.get("anchor"),
                    "status": row.get("status")})
    size = moves_file_stats(root)
    payload = {
        "total": len(rows), "returned": len(out), "projection": True,
        "filters": {"nameContains": name_contains, "status": status, "anchor": anchor},
        "librarySize": size,
        "fullReadAllowed": size["lines"] <= SMALL_FILE_MAX_LINES and size["bytes"] <= SMALL_FILE_MAX_BYTES,
        "moves": out,
    }
    return EXIT_OK, envelope("moves-list", root, rep, payload)


# --------------------------------------------------------------------------
# probe-links — one transport seam, offline-tolerant, never test-invoked
# --------------------------------------------------------------------------

SOCKS_SCHEME_RE = re.compile(r"^socks[45][a-z]*://", re.I)
PROXY_ENV_VARS = ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy",
                  "HTTP_PROXY", "http_proxy")


def detect_socks_proxy() -> str | None:
    """stdlib urllib has no SOCKS support, so a socks5 egress proxy makes every
    probe fail. Naming it turns "all sources look dead" into an actionable
    diagnostic — the sources are not dead, the probe cannot leave the machine."""
    for var in PROXY_ENV_VARS:
        value = (os.environ.get(var) or "").strip()
        if value and SOCKS_SCHEME_RE.match(value):
            return "%s=%s" % (var, value)
    return None


#: RFC 3986 unreserved set — everything else in a query-parameter value is encoded.
_UNRESERVED = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~")


def _percent_encode(value: str) -> str:
    """Percent-encode a query-parameter value using only the RFC 3986 unreserved set.

    Doing this locally rather than via the standard library's URL-quoting helper is
    what lets `_http_get` keep the exact two-parameter signature the engine contract
    pins, while leaving no transport-library reference anywhere outside the seam.
    """
    out = []
    for byte in (value or "").encode("utf-8"):
        char = chr(byte)
        out.append(char if char in _UNRESERVED else "%%%02X" % byte)
    return "".join(out)


def _http_get(url: str, timeout: int) -> tuple:
    """THE ONLY TRANSPORT SEAM (C-30). No other urllib/socket call exists in this
    module, which is what makes "no test touches the network" mechanically assertable
    (C-33a scans for urllib/socket outside here).
    Returns (status_code | None, body_text | error_string)."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec - bounded
            status = getattr(response, "status", None) or response.getcode()
            body = response.read(65536).decode("utf-8", "replace")
            return status, body
    except urllib.error.HTTPError as exc:
        return exc.code, "HTTPError: %s" % exc
    except Exception as exc:  # noqa: BLE001 — offline tolerance is the contract (C-31)
        return None, "%s: %s" % (type(exc).__name__, exc)


def _probe_one(url: str) -> dict:
    status, body = _http_get(url, PROBE_TIMEOUT_SECONDS)
    if status is not None and 200 <= int(status) < 300:
        return {"url": url, "access": "live", "resolvedVia": "direct",
                "httpStatus": int(status), "snapshotTs": None, "error": None,
                "evidence": "direct fetch returned HTTP %s" % status}
    if status is not None:
        direct_error = "direct fetch returned HTTP %s" % status
    else:
        direct_error = "direct fetch could not run (%s)" % body[:120]
    snap_status, snap_body = _http_get(WAYBACK_AVAILABILITY + _percent_encode(url),
                                       PROBE_TIMEOUT_SECONDS)
    if snap_status is not None and 200 <= int(snap_status) < 300:
        try:
            data = json.loads(snap_body or "{}")
        except ValueError:
            data = {}
        closest = ((data.get("archived_snapshots") or {}).get("closest") or {})
        if closest.get("available") and closest.get("url"):
            ts = str(closest.get("timestamp") or "")
            return {"url": url, "access": "wayback:%s" % (ts or "unknown"),
                    "resolvedVia": "wayback", "httpStatus": int(status) if status else None,
                    "snapshotTs": ts or None, "error": None,
                    "evidence": "%s; archive snapshot %s" % (direct_error, closest["url"])}
    if status is not None:
        # A definitive HTTP verdict from the origin is evidence about the source.
        return {"url": url, "access": "dead" if int(status) == 404 else "unknown",
                "resolvedVia": "wayback", "httpStatus": int(status), "snapshotTs": None,
                "error": None,
                "evidence": "%s; archive availability returned no snapshot" % direct_error}
    # C-34: a transport failure is not a dead link.
    return {"url": url, "access": "unknown", "resolvedVia": None, "httpStatus": None,
            "snapshotTs": None, "error": body[:200],
            "evidence": "probe could not run: %s" % body[:160]}


def probe_links(root: Path, spec: dict):
    rep = Report()
    urls = spec.get("urls") or []
    if not isinstance(urls, list) or not urls:
                return fail_envelope("probe-links", root, "input-schema",
                               "probe-links needs a non-empty 'urls' list")
    results = [_probe_one(str(u)) for u in urls]
    online = any(r["access"] != "unknown" or r["httpStatus"] is not None for r in results)
    degraded = not online
    if degraded:
        rep.note("%s: no URL could be probed — this is NOT evidence that the sources are "
                 "dead; ground them with the host agent's own fetch/search tool and cite "
                 "that evidence in the verification column" % NO_ONLINE_CAPABILITY)
    proxy = detect_socks_proxy()
    if proxy:
        rep.note("stdlib urllib cannot traverse %s, so every probe degrades to "
                 "access=unknown; the probe is a corroborator, not the grounding path" % proxy)
    payload = {"probed": len(results), "online": online, "degraded": degraded,
               "results": results}
    return EXIT_OK, envelope("probe-links", root, rep, payload)


# --------------------------------------------------------------------------
# init
# --------------------------------------------------------------------------

def audit_skeleton() -> str:
    rows = []
    for check in ALL_CHECKS:
        method = "agent attestation" if check in SEMANTIC_CHECKS_PENDING else "engine"
        rows.append({"#": check, "check": "", "method": method, "result": "pending"})
    return render_table(AUDIT_COLUMNS, rows)


def archive_skeleton(slug: str, budget: int) -> str:
    template = """# Derivation: @@SLUG@@

Concept authority: `shared/definitions/derivation-definitions.md` — the record schemas,
provenance grades, chain rules C1-C7 and audit checks A1-A16 are defined there and
referenced here, never restated.

## Agent Identity

_The signature behind every `agent-prior` criterion and decision in this run. Recorded
once; a decision-claim is valid because it is signed and revisable, not because it is
evidentially compelled._

- agent: <host agent type and version>
- model: <model name/version as exposed by the host, or "unavailable">
- run-id: <stable run identifier>
- run-at: <UTC timestamp>
- topic: @@SLUG@@

## Sources

@@SOURCES@@

## Unverifiable Sources

_None yet. Every `unverified` source MUST be listed here with its reason — never dropped._

## Reasoning Moves Applied

_Cite `M-<nnn>` identities from `.specify/derive/moves.md`. A bare identity reference is
always legal. To restate a row, place `<!-- projection of moves.md#M-nnn -->` on the line
immediately above it; an unmarked or divergent restatement is rejected (A9)._

## Criteria

_Ranking grounds for Decision Points, one row per criterion (single-line cells).
`kind`: `constraint` (hard filter) | `preference` (ranking weight). `provenance`:
`source` (truth-claim — `owner` cites the S-row that grounds it) | `declared`
(stakeholder-stated — `owner` names who declared it) | `agent-prior` (signed
decision-claim — `owner` is the Agent Identity above; revisable by re-declaration,
never laundered into a truth-claim). `weight`: high/medium/low or a number.
`defeater`: what observation or re-declaration would overturn it._

@@CRITERIA@@

## Derivation Chain

_One `### D-<k>` block per step: `premises` / `leads` / `move` / `derivation` /
`conclusion` / `falsification` / `confidence` / `contested-with`._

## Termination

- condition: a
- steps: 0 / @@BUDGET@@

## Decision Points

_One `### DP-<k> <name>` block per selection: `question` / `candidates` (each annotated
`[S-nnn]` when grounded or `[ungrounded]`, separated by `;`) / `filters` (cite the D-k
and C-nnn that prune) / `ranking` (every ordering judgment cites >=1 C-nnn — an
uncited ranking is a preference wearing a truth-claim's clothes) / `selected` /
`alternates` (<=2, each with a switch trigger citing Q-k or C-nnn). Every field on a
single line._

## Derived Architecture

_One `### A-<k> <name>` block per element: `statement` / `derived-from` / `confidence` /
`open-questions`. `derived-from` is mandatory and must fully resolve. An element that
embeds a selection MAY cite `decisions: DP-<k>` instead of restating it._

## Open Questions

_One `### Q-<k>` block per gap: `question` / `why-undetermined` / `would-resolve` /
`discriminator`. Links to `A-<k>` are bidirectional._

## Self-Audit

@@AUDIT@@
"""
    return (template
            .replace("@@SLUG@@", slug)
            .replace("@@SOURCES@@", render_table(SOURCE_COLUMNS, []))
            .replace("@@CRITERIA@@", render_table(CRITERION_COLUMNS, []))
            .replace("@@BUDGET@@", str(budget))
            .replace("@@AUDIT@@", audit_skeleton()))


def do_init(root: Path, slug: str, force: bool, budget: int):
    rep = Report()
    if not _IDENTITY.match(slug or ""):
        return fail_envelope("init", root, "slug-grammar", "invalid topic slug %r" % slug)
    path = archive_path(root, slug)
    created = []
    clobbered = False
    backup = None
    if path.exists():
        if not force:
            return fail_envelope(
                "init", root, "archive-exists",
                "derivation archive already exists: %s — amend it in place, or pass --force "
                "to re-scaffold (the current content is kept as a .bak)" % path,
                locator=str(path))
        backup = str(path.with_suffix(".md.bak"))
        path.replace(backup)
        clobbered = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(archive_skeleton(slug, budget), encoding="utf-8")
    created.append(str(path.relative_to(root)))
    if not moves_path(root).is_file():
        moves_path(root).parent.mkdir(parents=True, exist_ok=True)
        moves_path(root).write_text(moves_file_text([]), encoding="utf-8")
        created.append(str(moves_path(root).relative_to(root)))
    payload = {"slug": slug, "archivePath": str(path), "movesPath": str(moves_path(root)),
               "created": created, "clobbered": clobbered, "backupPath": backup,
               "maxSteps": budget, "terminationCondition": None}
    return EXIT_OK, envelope("init", root, rep, payload)


# --------------------------------------------------------------------------
# validate
# --------------------------------------------------------------------------

def compute_title_mismatch(claimed: str, resolved: str) -> bool:
    """C-27/C-28: a mismatch is a two-title assertion; one title cannot establish it."""
    left, right = normalize_text(claimed), normalize_text(resolved)
    if left is None or right is None:
        return False
    return left != right


def access_valid(value: str) -> bool:
    return value in ACCESS_VALUES or value.startswith("wayback:")


def longest_banned_hit(haystack: str):
    """C-17: substring match, report only the LONGEST hit so one fragment is not
    counted twice under both 'best practice' and 'best practices'."""
    folded = (haystack or "").casefold()
    hits = [lit for lit in BANNED_JUSTIFICATIONS if lit.casefold() in folded]
    return max(hits, key=len) if hits else None


def validate_criteria_and_dps(rep, text, sources, steps, elements, questions):
    """A15 — the criterion / decision-point layer's mechanical half.

    Criteria are the grounds a Decision Point's ranking may cite; Decision Points
    are the enumerate -> filter -> rank -> select record the artifact owes for
    every product-level selection. The semantic half (rankings genuinely supported
    by their grounds; agent priors recorded as signed decision-claims, never as
    truth-claims) is A16 and is attested, not computed. Missing sections parse to
    zero rows, so archives predating this layer still validate.
    """
    criteria = parse_table(section(text, SEC_CRITERIA), CRITERION_COLUMNS)
    identity = section(text, SEC_IDENTITY).strip()
    source_ids = {(r.get("id") or "").strip() for r in sources}
    crit_ids = set()
    for row in criteria:
        cid = (row.get("id") or "").strip()
        if not CRITERION_ID_RE.match(cid):
            rep.error("A15", "criterion-id-malformed", cid or "(row without id)",
                      "criterion id %r must match C-<nnn>" % cid)
            continue
        if cid in crit_ids:
            rep.error("A15", "criterion-duplicate-id", cid, "criterion ids must be unique")
        crit_ids.add(cid)
        statement = (row.get("statement") or "").strip()
        if not statement or normalize_text(statement) in BARE_ATTESTATIONS:
            rep.error("A15", "criterion-statement-empty", cid,
                      "a criterion needs a substantive statement — an empty ground "
                      "cannot carry a ranking")
        kind = (row.get("kind") or "").strip()
        if kind not in CRITERION_KINDS:
            rep.error("A15", "criterion-kind-invalid", "%s.kind" % cid,
                      "kind %r is not one of %s" % (kind, "/".join(CRITERION_KINDS)))
        prov = (row.get("provenance") or "").strip()
        owner = (row.get("owner") or "").strip()
        if prov not in CRITERION_PROVENANCES:
            rep.error("A15", "criterion-provenance-invalid", "%s.provenance" % cid,
                      "provenance %r is not one of %s" % (prov, "/".join(CRITERION_PROVENANCES)))
        elif prov == "source":
            refs = re.findall(r"\bS-\d{3,}\b", owner)
            if not refs:
                rep.error("A15", "criterion-source-unresolved", "%s.owner" % cid,
                          "a source-grounded criterion is a truth-claim: owner must cite "
                          "the S-<nnn> row that grounds it")
            for ref in refs:
                if ref not in source_ids:
                    rep.error("A15", "criterion-source-unresolved",
                              "%s.owner:%s" % (cid, ref),
                              "%s has no row in %s" % (ref, SEC_SOURCES))
        elif prov == "agent-prior":
            if not owner or normalize_text(owner) in BARE_ATTESTATIONS:
                rep.error("A15", "agent-prior-without-owner", cid,
                          "an agent-prior criterion is a signed decision-claim: owner must "
                          "name the Agent Identity block (e.g. 'Agent Identity <run-id>')")
            if not identity:
                rep.error("A15", "agent-prior-without-identity", cid,
                          "agent-prior criterion %s exists but %s is empty — a signature "
                          "without a signer" % (cid, SEC_IDENTITY))
    dps = parse_blocks(section(text, SEC_DECISIONS), "DP")
    registries = {
        "S": source_ids,
        "D": {s["_id"] for s in steps},
        "A": {e["_id"] for e in elements},
        "Q": {q["_id"] for q in questions},
        "C": crit_ids,
    }
    for dp in dps:
        dpid = dp["_id"]
        for field in ("question", "candidates", "ranking", "selected"):
            value = (dp.get(field) or "").strip()
            if not value or normalize_text(value) in BARE_ATTESTATIONS:
                rep.error("A15", "dp-field-missing", "%s.%s" % (dpid, field),
                          "a decision point needs %s — a selection without the enumerated "
                          "grounds is an unrecorded preference" % field)
        candidates_raw = (dp.get("candidates") or "")
        selected = (dp.get("selected") or "").strip()
        if selected and candidates_raw:
            names = [re.sub(r"\[[^\]]*\]", "", c).strip()
                     for c in re.split(r";\s*", candidates_raw)]
            names = [normalize_text(n) for n in names if n.strip()]
            sel = normalize_text(selected)
            if not any(sel == n or (n and (sel in n or n in sel)) for n in names):
                rep.error("A15", "dp-selected-not-candidate", "%s.selected" % dpid,
                          "selected %r was not among the enumerated candidates — a "
                          "selection must come out of the enumeration, not bypass it"
                          % selected)
        ranking = (dp.get("ranking") or "")
        if ranking and not re.search(r"\bC-\d{3,}\b", ranking):
            rep.error("A15", "dp-ranking-without-criterion", "%s.ranking" % dpid,
                      "every ordering judgment must cite at least one criterion C-<nnn> — "
                      "an uncited ranking is a preference wearing a truth-claim's clothes")
        alternates_raw = (dp.get("alternates") or "").strip()
        if alternates_raw and normalize_text(alternates_raw) not in BARE_ATTESTATIONS:
            alts = [a.strip() for a in re.split(r";\s*", alternates_raw) if a.strip()]
            if len(alts) > DP_MAX_ALTERNATES:
                rep.error("A15", "dp-alternates-exceed-two", "%s.alternates" % dpid,
                          "at most %d alternates beside the selection (top-1..3 output "
                          "rule); found %d" % (DP_MAX_ALTERNATES, len(alts)))
            if not re.search(r"\b[QC]-\d+\b", alternates_raw):
                rep.error("A15", "dp-alternate-without-trigger", "%s.alternates" % dpid,
                          "an alternate needs a switch trigger citing a Q-<k> or C-<nnn> — "
                          "an alternate without a trigger is dead weight")
        for field, value in dp.items():
            if field.startswith("_") or not value:
                continue
            for prefix, num in re.findall(r"\b([SDAQC])-(\d+)\b", value):
                ref = "%s-%s" % (prefix, num)
                if ref not in registries.get(prefix, set()):
                    rep.error("A15", "dp-reference-unresolved",
                              "%s.%s:%s" % (dpid, field, ref),
                              "%s does not resolve to any recorded row" % ref)
    return len(criteria), len(dps)


def validate_artifact(root: Path, path: Path, budget: int):
    rep = Report()
    if not path.is_file():
        return error_envelope("validate", root, "archive-not-found",
                              "no derivation archive at %s" % path, locator=str(path),
                              exit_code=EXIT_NOT_FOUND)
    text = path.read_text(encoding="utf-8")
    slug = path.parent.name

    for heading in ARTIFACT_SECTIONS:
        if heading not in text:
            rep.error("A0", "audit-table-shape", heading,
                      "artifact is missing required section %s" % heading)

    sources = parse_table(section(text, SEC_SOURCES), SOURCE_COLUMNS)
    sources_by_id = {}
    for row in sources:
        sid = (row.get("id") or "").strip()
        if not SOURCE_ID_RE.match(sid):
            rep.error("A1", "grade-not-in-enum", sid or "<row>",
                      "source id must match S-<nnn>")
            continue
        sources_by_id[sid] = row
        grade = (row.get("grade") or "").strip()
        if grade not in GRADES:
            rep.error("A1", "grade-not-in-enum", "%s.grade" % sid,
                      "grade %r is not one of %s" % (grade, "/".join(GRADES)))
        access = (row.get("access") or "").strip()
        if not access_valid(access):
            rep.error("A1", "grade-not-in-enum", "%s.access" % sid,
                      "access %r is outside the enum (live / wayback:<ts> / dead / "
                      "paywalled / unknown)" % access)
        via = (row.get("resolved_via") or "").strip()
        if via and via not in RESOLVED_VIA:
            rep.error("A1", "grade-not-in-enum", "%s.resolved_via" % sid,
                      "resolved_via %r is not one of %s" % (via, "/".join(RESOLVED_VIA)))
        if access == "unknown" and grade != "unverified":
            rep.error("A1", "unknown-access-with-verified-grade", "%s.grade" % sid,
                      "access: unknown forces grade: unverified — an unprobed URL is not "
                      "evidence, and the honest grade is `unverified`")

        claimed_variants = [v.strip() for v in (row.get("claimed_title") or "").split("|") if v.strip()]
        resolved = (row.get("resolved_title") or "").strip()
        computed = any(compute_title_mismatch(v, resolved) for v in claimed_variants) \
            if resolved else False
        stated = (row.get("title_mismatch") or "").strip().lower()
        # C-29 is checked on the STATED value and before the recomputation check: a
        # mismatch is a two-title assertion, and this is the more specific diagnosis.
        # (Testing the computed value here would be dead code — C-28 forces
        # title_mismatch False whenever either title is absent.)
        if stated == "true" and (not claimed_variants or not resolved):
            rep.error("A1", "title-mismatch-without-both-titles", "%s.title_mismatch" % sid,
                      "title_mismatch is a two-title assertion: claimed_title and "
                      "resolved_title must both be non-empty")
        elif stated in ("true", "false"):
            if (stated == "true") != computed:
                rep.error("A1", "title-mismatch-asserted", "%s.title_mismatch" % sid,
                          "title_mismatch is engine-computed: stated %s but normalized "
                          "titles %s" % (stated, "differ" if computed else "match"))
        elif stated:
            rep.error("A1", "title-mismatch-asserted", "%s.title_mismatch" % sid,
                      "title_mismatch must be true or false")
        if not resolved:
            rep.warn("unresolved-title", "%s.resolved_title" % sid,
                     "no resolved_title recorded, so no mismatch can be asserted — "
                     "absence of evidence is not evidence of retitling")

        verification = (row.get("verification") or "").strip()
        # Bare-attestation is checked BEFORE the length floor: every member of the
        # closed set is under VERIFICATION_MIN_CODEPOINTS, so the length check would
        # always pre-empt it and the more specific diagnosis could never be reported.
        if normalize_text(verification) in BARE_ATTESTATIONS:
            rep.error("A1", "verification-bare-attestation", "%s.verification" % sid,
                      "a bare attestation is not evidence; the honest grade when there is "
                      "none is `unverified`")
        elif len(verification) < VERIFICATION_MIN_CODEPOINTS:
            rep.error("A1", "verification-too-short", "%s.verification" % sid,
                      "verification must cite concrete evidence (>= %d codepoints); the "
                      "honest grade when there is none is `unverified`"
                      % VERIFICATION_MIN_CODEPOINTS)
        elif not any(r.search(verification) for r in EVIDENCE_TOKEN_RES):
            rep.warn("verification-evidence-token-absent", "%s.verification" % sid,
                     "no recognizable evidence token (URL / HTTP status / snapshot "
                     "timestamp / search-result locator)")

    library = load_moves(root)
    lib_ids = check_library_invariants(rep, root, library)
    lib_by_id = {(r.get("move_id") or "").strip(): r for r in library}

    # ---- A9: cited moves, restated rows, superseded references -----------
    applied_body = section(text, SEC_MOVES_APPLIED)
    cited = set(re.findall(r"\bM-\d{3,}\b", applied_body))
    for mid in sorted(cited):
        if mid not in lib_ids:
            rep.error("A9", "move-not-in-library", mid,
                      "cited move %s has no library row — it never went through moves-add" % mid)
        elif (lib_by_id[mid].get("status") or "").strip() == "superseded":
            rep.error("A9", "superseded-move-applied", mid,
                      "superseded is terminal: the move is permanently un-citable, so a "
                      "known defect cannot be re-imported into the chain")
    applied_lines = applied_body.splitlines()
    for i, line in enumerate(applied_lines):
        m = RESTATED_MOVE_ROW_RE.match(line)
        if not m:
            continue
        mid = m.group(1)
        cells = split_cells(line)
        if len(cells) < len(MOVE_COLUMNS):
            # A run-relative disposition log (`move_id | disposition`) copies nothing
            # from the library — it is what `stats` reads for SC-003. Only a row that
            # actually carries the library's columns can be a stale projection.
            continue
        marker = PROJECTION_MARKER_RE.search(applied_lines[i - 1]) if i > 0 else None
        if not marker:
            rep.error("A9", "unmarked-move-copy", mid,
                      "a restated move row needs '<!-- projection of moves.md#%s -->' on the "
                      "line immediately above; a bare identity reference is always legal" % mid)
            continue
        if marker.group(1) != mid:
            rep.error("A9", "unmarked-move-copy", mid,
                      "the projection marker names %s but the row is %s" % (marker.group(1), mid))
            continue
        cells = split_cells(line)
        lib_row = lib_by_id.get(mid)
        if lib_row and len(cells) >= 3 and \
                normalize_text(cells[2]) != normalize_text(lib_row.get("inference_form", "")):
            rep.error("A9", "divergent-move-projection", mid,
                      "the projected inference_form diverges from the library row — the "
                      "library is the source of truth")
    # C-41 / A13: a row whose disposition column says `new` must resolve in the library.
    for row in parse_table(applied_body, ("move_id", "disposition")):
        if (row.get("disposition") or "").strip() == "new":
            mid = (row.get("move_id") or "").strip()
            if mid and mid not in lib_ids:
                rep.error("A13", "newly-issued-move-unresolved", mid,
                          "reported as newly issued this run but absent from the library — "
                          "it was hand-written into the artifact, not issued by moves-add")

    steps = parse_blocks(section(text, SEC_CHAIN), "D")
    step_by_id = {s["_id"]: s for s in steps}
    elements = parse_blocks(section(text, SEC_ARCHITECTURE), "A")
    questions = parse_blocks(section(text, SEC_QUESTIONS), "Q")
    q_by_id = {q["_id"]: q for q in questions}
    el_by_id = {e["_id"]: e for e in elements}

    # ---- degraded run (C-45/C-46/C-47/C-48) ------------------------------
    degraded = bool(sources) and not steps and \
        all((r.get("grade") or "").strip() == "unverified" for r in sources) and \
        all(normalize_text(r.get("verification", "")) == normalize_text(NO_ONLINE_CAPABILITY)
            for r in sources) and \
        not any((e.get("statement") or "").strip() for e in elements)
    if degraded:
        rep.warn("degraded-run", SEC_SOURCES,
                 "no source could be grounded, so no step may anchor and no architecture "
                 "is produced — an honest empty result, not a failure")
        rep.note("%s: degraded run, chain not built" % NO_ONLINE_CAPABILITY)

    # ---- C6 termination + budget ----------------------------------------
    term = section(text, SEC_TERMINATION)
    cm = re.search(r"^-\s*condition\s*:\s*(\S+)\s*$", term, re.M)
    condition = cm.group(1) if cm else ""
    if condition not in TERMINATION_CONDITIONS:
        rep.error("C6", "termination-condition-absent", SEC_TERMINATION,
                  "declare 'condition: a' (every in-scope element traced) or 'condition: b' "
                  "(the next premise has no verified source)")
    sm = re.search(r"^-\s*steps\s*:\s*(\d+)\s*/\s*(\d+)\s*$", term, re.M)
    if sm:
        declared_steps, declared_budget = int(sm.group(1)), int(sm.group(2))
        if declared_budget != budget:
            rep.error("C6", "step-budget-diverges", SEC_TERMINATION,
                      "declared budget %d but the effective --max-steps is %d; the declared "
                      "line is a report, never a second source of truth"
                      % (declared_budget, budget))
        if declared_steps != len(steps):
            rep.error("C6", "step-budget-diverges", "%s.steps" % SEC_TERMINATION,
                      "declared %d steps but the chain holds %d; the engine's count is "
                      "authoritative" % (declared_steps, len(steps)))
    if len(steps) > budget:
        rep.error("C6", "step-budget-exceeded", SEC_CHAIN,
                  "%d steps exceed the effective budget of %d — hitting the budget must be "
                  "reported, never silently truncated" % (len(steps), budget))
    elif budget and len(steps) == budget:
        rep.warn("step-budget-reached", SEC_CHAIN,
                 "the chain used the whole budget (%d of %d)" % (len(steps), budget))

    # ---- per-step rules --------------------------------------------------
    anchorable = 0
    for step in steps:
        sid = step["_id"]
        if not STEP_ID_RE.match(sid):
            rep.error("C1", "orphan-source-premise", sid, "step id must match D-<k>")
            continue
        k = int(sid.split("-")[1])
        premises = parse_id_list(step.get("premises", ""))
        leads = parse_id_list(step.get("leads", ""))

        moves = [m for m in parse_id_list(step.get("move", "")) if MOVE_ID_RE.match(m)]
        if len(moves) != 1:
            rep.error("C2", "move-count-not-one", "%s.move" % sid,
                      "exactly one move per step, found %d — zero is an unreasoned "
                      "assertion, two are two steps" % len(moves))
        for mid in moves:
            if mid not in lib_ids:
                rep.error("A9", "move-not-in-library", "%s.move:%s" % (sid, mid),
                          "step cites %s which has no library row" % mid)

        step_anchorable = True
        for prem in premises:
            if prem.startswith("S-"):
                row = sources_by_id.get(prem)
                if row is None:
                    rep.error("C1", "orphan-source-premise", "%s.premises:%s" % (sid, prem),
                              "premise %s has no row in %s" % (prem, SEC_SOURCES))
                    step_anchorable = False
                    continue
                grade = (row.get("grade") or "").strip()
                if grade not in ANCHORING_GRADES:
                    rep.error("C1", "premise-grade-ineligible", "%s.premises:%s" % (sid, prem),
                              "grade %r cannot anchor a step — only primary / "
                              "authoritative-secondary may; a finding aid belongs in `leads`"
                              % grade)
                    step_anchorable = False
                if compute_title_mismatch(row.get("claimed_title", ""),
                                          row.get("resolved_title", "")):
                    resolved = (row.get("resolved_title") or "").strip()
                    if resolved and resolved not in step.get("derivation", ""):
                        rep.error("A3", "resolved-title-not-cited",
                                  "%s.derivation:%s" % (sid, prem),
                                  "title_mismatch is true, so the derivation must cite the "
                                  "resolved title %r verbatim, not the claimed one" % resolved)
            elif prem.startswith("D-"):
                if prem not in step_by_id:
                    rep.error("C1", "orphan-source-premise", "%s.premises:%s" % (sid, prem),
                              "premise %s does not exist" % prem)
                    step_anchorable = False
                else:
                    j = int(prem.split("-")[1])
                    if j > k:
                        rep.error("C1", "forward-step-reference", "%s.premises:%s" % (sid, prem),
                                  "the chain is a DAG in step order: %s may not rest on %s"
                                  % (sid, prem))
                        step_anchorable = False
                    elif j == k:
                        rep.error("C1", "self-referential-step", "%s.premises:%s" % (sid, prem),
                                  "a step may not rest on itself")
                        step_anchorable = False
            else:
                rep.error("C1", "orphan-source-premise", "%s.premises:%s" % (sid, prem),
                          "a premise must be S-<nnn> or D-<k>")
                step_anchorable = False
        if step_anchorable and premises:
            anchorable += 1

        for lead in leads:
            if not lead.startswith("S-"):
                continue
            row = sources_by_id.get(lead)
            if row is None:
                rep.error("C1", "unresolved-lead", "%s.leads:%s" % (sid, lead),
                          "lead %s has no row in %s" % (lead, SEC_SOURCES))
                continue
            # C-23 covers premises AND leads: a retitled source must be cited by its
            # resolved title wherever it is referenced.
            if compute_title_mismatch(row.get("claimed_title", ""), row.get("resolved_title", "")):
                resolved = (row.get("resolved_title") or "").strip()
                if resolved and resolved not in step.get("derivation", ""):
                    rep.error("A3", "resolved-title-not-cited", "%s.derivation:%s" % (sid, lead),
                              "title_mismatch is true, so the derivation must cite the resolved "
                              "title %r verbatim even when the source is only a lead" % resolved)

        derivation = step.get("derivation", "")
        conclusion = step.get("conclusion", "")
        for field, value in (("derivation", derivation), ("conclusion", conclusion)):
            hit = longest_banned_hit(value)
            if hit:
                rep.error("C3", "banned-justification", "%s.%s" % (sid, field),
                          "%s contains %r — cite a verified source that says so, which turns "
                          "a banned phrase into an anchored premise" % (field, hit), value=hit)

        falsification = step.get("falsification", "")
        stripped = falsification.strip().lower()
        if not stripped or stripped in VACUOUS_FALSIFICATION:
            rep.error("C4", "falsification-vacuous-literal", "%s.falsification" % sid,
                      "falsification must state what observation would refute the conclusion")
        else:
            nf, nc = normalize_text(falsification), normalize_text(conclusion)
            if nf and nc and (nf == nc or (nf in nc or nc in nf) and
                              abs(len(nf) - len(nc)) <= 0.2 * max(len(nf), len(nc))):
                rep.error("C4", "falsification-restates-conclusion", "%s.falsification" % sid,
                          "a falsification restating the conclusion refutes nothing")

        if len(derivation.strip()) < DERIVATION_MIN_CODEPOINTS or \
                len([l for l in derivation.splitlines() if l.strip()]) < 1:
            rep.error("C7", "derivation-empty-or-short", "%s.derivation" % sid,
                      "derivation is under %d codepoints — a conclusion that merely restates "
                      "a source is a citation wearing a derivation's clothes"
                      % DERIVATION_MIN_CODEPOINTS)
        nc = normalize_text(conclusion)
        for row in sources:
            for title in (row.get("resolved_title"), row.get("claimed_title")):
                nt = normalize_text(title or "")
                if nt and nc and nt == nc:
                    rep.error("C7", "conclusion-equals-source-title", "%s.conclusion" % sid,
                              "conclusion is identical to source %s's title — conclusion "
                              "laundering" % row.get("id"))

        confidence = (step.get("confidence") or "").strip()
        if confidence not in CONFIDENCES:
            rep.error("C5", "confidence-not-in-enum", "%s.confidence" % sid,
                      "confidence %r is not one of %s" % (confidence, "/".join(CONFIDENCES)))

        if confidence == "contested":
            peers = parse_id_list(step.get("contested-with", ""))
            if not peers:
                rep.error("C5", "contested-without-link", sid,
                          "a contested step must name its counterpart — never pick a branch "
                          "silently or average the two")
            for peer in peers:
                other = step_by_id.get(peer)
                if other is None:
                    rep.error("C5", "contested-link-unresolved", "%s.contested-with:%s" % (sid, peer),
                              "contested-with %s does not exist" % peer)
                elif sid not in parse_id_list(other.get("contested-with", "")):
                    rep.error("C5", "contested-link-not-reciprocal",
                              "%s.contested-with:%s" % (sid, peer),
                              "contested-with must be reciprocal")
            routed = any(sid in (q.get("why-undetermined") or "") for q in questions)
            if not routed:
                rep.error("A10", "contested-not-routed", sid,
                          "a contested step must be routed into an open question's "
                          "why-undetermined, naming %s" % sid)

    # ---- C5 propagation --------------------------------------------------
    for step in steps:
        sid = step["_id"]
        confidence = (step.get("confidence") or "").strip()
        if confidence not in CONFIDENCE_RANK:
            continue
        premise_ranks = []
        for prem in parse_id_list(step.get("premises", "")):
            if not prem.startswith("D-"):
                continue
            prior = step_by_id.get(prem)
            if not prior:
                continue
            pc = (prior.get("confidence") or "").strip()
            if pc == "contested" and confidence == "derived":
                rep.error("C5", "contested-premise-in-derived-step", "%s.premises:%s" % (sid, prem),
                          "a derived-confidence step may not rest on a contested premise — "
                          "uncertainty propagates forward")
            if pc in CONFIDENCE_RANK:
                premise_ranks.append(CONFIDENCE_RANK[pc])
        if premise_ranks and CONFIDENCE_RANK[confidence] > min(premise_ranks):
            expected = [n for n, r in CONFIDENCE_RANK.items() if r == min(premise_ranks)][0]
            rep.error("C5", "step-confidence-above-premise-min", "%s.confidence" % sid,
                      "a step's confidence rank must be <= the minimum over its D- premises: "
                      "claims %r, upper bound %r" % (confidence, expected))

    # ---- A7 / A8 elements ------------------------------------------------
    for el in elements:
        aid = el["_id"]
        refs = parse_id_list(el.get("derived-from", ""))
        if not refs:
            rep.error("A7", "element-derived-from-missing", aid,
                      "every architecture element must trace to at least one derivation step "
                      "— an untraceable element is a preference wearing an architecture's clothes")
            continue
        ranks = []
        for ref in refs:
            step = step_by_id.get(ref)
            if step is None:
                rep.error("A7", "element-derived-from-unresolved", "%s.derived-from:%s" % (aid, ref),
                          "derived-from %s does not exist" % ref)
                continue
            sc = (step.get("confidence") or "").strip()
            if sc in CONFIDENCE_RANK:
                ranks.append(CONFIDENCE_RANK[sc])
        claimed = (el.get("confidence") or "").strip()
        if ranks and claimed in CONFIDENCE_RANK:
            floor = min(ranks)
            if CONFIDENCE_RANK[claimed] != floor:
                expected = [n for n, r in CONFIDENCE_RANK.items() if r == floor][0]
                rep.error("A8", "element-confidence-not-minimum", "%s.confidence" % aid,
                          "element confidence must EQUAL the minimum over its steps (not merely "
                          "be <= it): claims %r, expected %r" % (claimed, expected))
        for qref in parse_id_list(el.get("open-questions", "")):
            if qref not in q_by_id:
                rep.error("A10", "open-question-link-unresolved",
                          "%s.open-questions:%s" % (aid, qref),
                          "open question %s does not exist" % qref)

    blocked = set()
    for q in questions:
        qid = q["_id"]
        targets = parse_id_list(q.get("would-resolve", ""))
        for aid in targets:
            el = el_by_id.get(aid)
            if el is None:
                rep.error("A10", "open-question-link-unresolved",
                          "%s.would-resolve:%s" % (qid, aid),
                          "would-resolve %s does not exist" % aid)
            elif qid not in parse_id_list(el.get("open-questions", "")):
                rep.error("A10", "open-question-link-unresolved",
                          "%s.would-resolve:%s" % (qid, aid),
                          "Q ↔ A links must resolve in both directions: %s does not list %s"
                          % (aid, qid))
            else:
                blocked.add(aid)
        for field in ("question", "why-undetermined", "discriminator"):
            if not (q.get(field) or "").strip():
                rep.error("A10", "open-question-link-unresolved", "%s.%s" % (qid, field),
                          "an open question needs %s — a gap recorded without its "
                          "discriminator can never be closed" % field)
    for aid in blocked:
        el = el_by_id.get(aid)
        if el and (el.get("confidence") or "").strip() == "derived":
            rep.error("A10", "blocked-element-not-downgraded", "%s.confidence" % aid,
                      "an element blocked by an open question must be provisional or contested")

    # ---- A15: criteria & decision points --------------------------------
    criteria_total, dp_total = validate_criteria_and_dps(
        rep, text, sources, steps, elements, questions)

    # ---- A2: unverified sources must be recorded, never dropped ----------
    unverifiable = section(text, SEC_UNVERIFIABLE)
    for row in sources:
        if (row.get("grade") or "").strip() == "unverified":
            sid = (row.get("id") or "").strip()
            if sid and sid not in unverifiable:
                rep.error("A2", "unverified-source-unrecorded", sid,
                          "every unverified source must appear in %s with its reason — "
                          "dropping it turns a dead link into an invisible hole in the chain"
                          % SEC_UNVERIFIABLE)
    # secondary-sole-anchor (warning): structurally suspicious, semantically agent's call
    for step in steps:
        if (step.get("confidence") or "").strip() != "contested":
            continue
        grades = {(sources_by_id.get(p) or {}).get("grade", "").strip()
                  for p in parse_id_list(step.get("premises", "")) if p.startswith("S-")}
        if grades and "primary" not in grades:
            rep.warn("secondary-sole-anchor", step["_id"],
                     "a contested step with no primary premise — an authoritative-secondary "
                     "must not be the sole anchor for a claim a primary contradicts")

    # ---- degraded run must not carry anchored steps ----------------------
    if sources and not any((r.get("grade") or "").strip() in ANCHORING_GRADES for r in sources) \
            and steps:
        rep.error("C1", "premise-grade-ineligible", SEC_CHAIN,
                  "no source is anchoring-grade, so no step may exist — a degraded run stops "
                  "before the chain and reports the degradation")

    # ---- A0: the audit table itself -------------------------------------
    audit_body = section(text, SEC_AUDIT)
    audit_rows = parse_table(audit_body, AUDIT_COLUMNS)
    if AUDIT_HEADER not in audit_body:
        rep.error("A0", "audit-table-shape", SEC_AUDIT,
                  "the audit table header must be verbatim %r" % AUDIT_HEADER)
    ids = [(r.get("#") or "").strip() for r in audit_rows]
    if sorted(ids) != sorted(ALL_CHECKS):
        rep.error("A0", "audit-table-shape", SEC_AUDIT,
                  "the audit table must carry exactly A1..A16 (found %d rows)" % len(ids))
    derived_audit = rep.audit_engine()
    semantic_audit = {}
    for row in audit_rows:
        check = (row.get("#") or "").strip()
        result = (row.get("result") or "").strip()
        method = (row.get("method") or "").strip()
        if check in SEMANTIC_CHECKS_PENDING:
            if result not in ATTESTATION_RESULTS:
                rep.error("A0", "audit-result-diverges", "%s.%s" % (SEC_AUDIT, check),
                          "A11/A14/A16 result must be one of %s (agent attestation, never "
                          "inherited as pass); found %r" % ("/".join(ATTESTATION_RESULTS), result))
            semantic_audit[check] = result or "pending"
            if normalize_text(method) in (None, "engine", "n/a"):
                rep.warn("attestation-method-degenerate", "%s.%s.method" % (SEC_AUDIT, check),
                         "the method column for an attested check must be a checkable "
                         "sentence, not 'engine' / 'n/a' / empty")
        elif check in derived_audit:
            expected = derived_audit[check]
            if result != expected:
                rep.error("A0", "audit-result-diverges", "%s.%s" % (SEC_AUDIT, check),
                          "%s is engine-derived: artifact says %r, derived value is %r"
                          % (check, result, expected))
    derived_audit = rep.audit_engine()  # recompute: A0 findings may have changed it

    def access_bucket(value):
        """`wayback:<ts>` is one enum member with a parameter, not its own bucket."""
        v = (value or "").strip()
        return "wayback" if v.startswith("wayback:") else v

    def tally(items, key, enum, bucket=None):
        out = {v: 0 for v in enum}
        for it in items:
            k = (it.get(key) or "").strip()
            if bucket:
                k = bucket(k)
            out[k] = out.get(k, 0) + 1
        return out

    payload = {
        "file": str(path),
        "degraded": degraded,
        "sources": {
            "total": len(sources),
            "byGrade": tally(sources, "grade", GRADES),
            "byAccess": tally(sources, "access", ACCESS_BUCKETS, bucket=access_bucket),
            "titleMismatch": sum(1 for r in sources
                                 if compute_title_mismatch(r.get("claimed_title", ""),
                                                           r.get("resolved_title", ""))),
        },
        "steps": {
            "total": len(steps),
            "anchorable": anchorable,
            "byConfidence": tally(steps, "confidence", CONFIDENCES),
            "budget": budget,
            "budgetReached": bool(budget) and len(steps) >= budget,
        },
        "moves": {
            "cited": len(cited),
            "resolved": len([m for m in cited if m in lib_ids]),
            "missing": sorted(m for m in cited if m not in lib_ids),
        },
        "elements": {
            "total": len(elements),
            "byConfidence": tally(elements, "confidence", CONFIDENCES),
            "untraceable": sum(1 for e in elements if not parse_id_list(e.get("derived-from", ""))),
        },
        "criteria": {"total": criteria_total},
        "decisionPoints": {"total": dp_total},
        "openQuestions": {
            "total": len(questions),
            "brokenLinks": sorted({e["locator"] for e in rep.errors
                                   if e["code"] == "open-question-link-unresolved"}),
        },
        "audit": {"engine": derived_audit, "semantic": semantic_audit},
    }
    return (EXIT_OK if rep.ok else EXIT_INVALID), envelope("validate", root, rep, payload)


# --------------------------------------------------------------------------
# stats
# --------------------------------------------------------------------------

def do_stats(root: Path, path: Path | None):
    rep = Report()
    library = load_moves(root)
    ids = set()
    dup_ids = 0
    for row in library:
        mid = (row.get("move_id") or "").strip()
        if mid in ids:
            dup_ids += 1
        ids.add(mid)
    forms = {}
    dup_forms = 0
    for row in library:
        if (row.get("status") or "").strip() != "active":
            continue  # a superseded row and its active successor may share a shape (C-18)
        iso = slot_isomorphic_key(row.get("inference_form", ""))
        if iso in forms:
            dup_forms += 1
        forms[iso] = row
    if dup_ids or dup_forms:
        rep.error("A13", "moves-library-hand-edited", MOVES_FILENAME,
                  "library carries %d duplicate id(s) and %d duplicate slot-isomorphic "
                  "form(s)" % (dup_ids, dup_forms), value="duplicate-form")
    check_library_invariants(rep, root, library)

    archives = sorted(p.parent.name for p in derive_root(root).glob("*/%s" % ARCHIVE_FILENAME))
    last_run = None
    dispositions = {"new": 0, "reused": 0, "reinforced": 0}
    if path is not None and path.is_file():
        text = path.read_text(encoding="utf-8")
        for row in parse_table(section(text, SEC_MOVES_APPLIED), ("move_id", "disposition")):
            d = (row.get("disposition") or "").strip()
            if d in dispositions:
                dispositions[d] += 1
        stamp = _dt.datetime.fromtimestamp(path.stat().st_mtime, _dt.timezone.utc)
        last_run = {"slug": path.parent.name,
                    "generatedAt": stamp.strftime("%Y-%m-%dT%H:%M:%SZ")}

    payload = {
        "moves": {
            "total": len(library),
            "byStatus": {s: sum(1 for r in library if (r.get("status") or "").strip() == s)
                         for s in MOVE_STATUSES},
            "duplicateIds": dup_ids,
            "duplicateForms": dup_forms,
        },
        "dispositions": dispositions,
        "archives": {"total": len(archives), "topics": archives},
        "lastRun": last_run,
    }
    return (EXIT_OK if rep.ok else EXIT_INVALID), envelope("stats", root, rep, payload)


# --------------------------------------------------------------------------
# output rendering (C-17: one internal result, two renderings)
# --------------------------------------------------------------------------

def render_text(data: dict) -> None:
    print("%s %s — %s" % (data["action"], "OK" if data["ok"] else "FAIL", data["workspaceRoot"]))
    for err in data["errors"]:
        print("  error [%s/%s] %s — %s" % (err.get("rule") or "-", err["code"],
                                           err["locator"], err["message"]))
    for warn in data["warnings"]:
        print("  warn  [%s] %s — %s" % (warn["code"], warn["locator"], warn["message"]))
    for note in data["notes"]:
        print("  note  %s" % note)
    if data["semanticChecksPending"]:
        print("  semantic checks pending agent attestation: %s"
              % ", ".join(data["semanticChecksPending"]))
    payload = data["payload"]
    audit = payload.get("audit") or {}
    if audit:
        failed = [k for k, v in (audit.get("engine") or {}).items() if v != "pass"]
        print("  audit engine: %s" % ("all pass" if not failed else "FAILED " + ", ".join(failed)))
        print("  audit semantic: %s" % json.dumps(audit.get("semantic") or {}, ensure_ascii=False))
    print("  summary: %s" % json.dumps(
        {k: v for k, v in payload.items() if k not in ("moves", "results", "audit")},
        ensure_ascii=False, default=str))


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def load_json(path_str: str):
    path = Path(path_str)
    if not path.is_file():
        return None, "no such file: %s" % path
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return None, "cannot parse %s: %s" % (path, exc)
    if not isinstance(data, dict):
        return None, "%s must contain a JSON object" % path
    return data, None


class _UsageError(Exception):
    """Raised instead of argparse's own exit(2), so C-7/C-8 hold on the usage path."""


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # noqa: D102 - argparse hook
        raise _UsageError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(
        prog="derive-utils.py",
        description="Derivation engine for /speckit.derive — identity issuance, structural "
                    "validation, move-library dedup, link probing, counting.")
    parser.add_argument("--action", required=True,
                        choices=["init", "validate", "moves-list", "moves-add",
                                 "probe-links", "stats"])
    parser.add_argument("--workspace-root", default=".")
    parser.add_argument("--format", default="json", choices=["text", "json"])
    parser.add_argument("--slug", default=None, help="topic slug")
    parser.add_argument("--file", default=None,
                        help="validate/stats: archive path; moves-add: moves JSON; "
                             "probe-links: urls JSON")
    parser.add_argument("--force", action="store_true",
                        help="init: re-scaffold over an existing archive (a .bak is kept)")
    parser.add_argument("--max-steps", type=int, default=None,
                        help="derivation step budget (default: %d)" % DEFAULT_MAX_STEPS)
    parser.add_argument("--name-contains", dest="name_contains", default=None)
    parser.add_argument("--status", default=None, help="moves-list: active | superseded")
    parser.add_argument("--anchor", default=None)
    return parser


def resolve_target(root: Path, slug, file_arg, action, required=True):
    """C-10: --file and --slug are mutually exclusive. `validate` requires exactly
    one; `stats` accepts neither (library-wide stats)."""
    if slug and file_arg:
        return None, "give at most one of --slug or --file, not both"
    if not slug and not file_arg:
        if required:
            return None, "give exactly one of --slug or --file"
        return None, None
    if slug:
        if not _IDENTITY.match(slug):
            return None, "invalid topic slug %r" % slug
        return archive_path(root, slug), None
    return Path(file_arg), None


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except _UsageError as exc:
        # C-7: an unknown or missing --action is exit 1 with a JSON envelope whose
        # `action` is null — never argparse's bare-text exit 2.
        code, data = error_envelope(None, resolve_root(None), "usage-error", str(exc),
                                    exit_code=EXIT_USAGE)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return code
    root = resolve_root(args.workspace_root)
    as_json = args.format == "json"

    def emit(code, data):
        if as_json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            render_text(data)
        return code

    budget = DEFAULT_MAX_STEPS if args.max_steps is None else args.max_steps
    if budget <= 0:
        return emit(*fail_envelope(args.action, root, "max-steps-not-positive",
                                   "--max-steps must be a positive integer"))

    action = args.action

    if action == "init":
        if not args.slug:
            return emit(*fail_envelope(action, root, "missing-slug",
                                       "--action init requires --slug"))
        return emit(*do_init(root, args.slug, args.force, budget))

    if action == "validate":
        target, err = resolve_target(root, args.slug, args.file, action, required=True)
        if err:
            return emit(*fail_envelope(action, root, "target-ambiguous", err))
        return emit(*validate_artifact(root, target, budget))

    if action == "stats":
        target, err = resolve_target(root, args.slug, args.file, action, required=False)
        if err:
            return emit(*fail_envelope(action, root, "target-ambiguous", err))
        if target is not None and not target.is_file():
            return emit(*error_envelope(action, root, "archive-not-found",
                                        "no derivation archive at %s" % target,
                                        locator=str(target), exit_code=EXIT_NOT_FOUND))
        return emit(*do_stats(root, target))

    if action == "moves-list":
        return emit(*moves_list(root, args.name_contains, args.status, args.anchor))

    if action in ("moves-add", "probe-links"):
        if not args.file:
            return emit(*fail_envelope(action, root, "missing-file",
                                       "--action %s requires --file" % action))
        spec, err = load_json(args.file)
        if err:
            not_found = err.startswith("no such file")
            return emit(*error_envelope(
                action, root,
                "input-not-found" if not_found else "input-unparseable",
                err, locator=args.file,
                exit_code=EXIT_NOT_FOUND if not_found else EXIT_INPUT_ERROR))
        if action == "moves-add":
            return emit(*moves_add(root, spec))
        return emit(*probe_links(root, spec))

    return emit(EXIT_USAGE, envelope(action, root, Report(), {}, ok=False))


if __name__ == "__main__":
    sys.exit(main())
