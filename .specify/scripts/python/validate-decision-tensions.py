#!/usr/bin/env python3
"""validate-decision-tensions.py — deterministic structural checker for Decision Tension Records.

Program-First discipline (.specify/shared/guidelines/token-efficiency.md): the propositions checked here
are fixed, textual and decidable, so a program judges them and prints a verdict; an agent MUST
NOT re-derive them by reading the plan and declaring a result. The record shape, the admissibility
criteria, the rejection forms and the load-bearing threshold are owned by
``.specify/shared/guidelines/decision-tension.md`` — this checker consumes them, it never restates them.

Checks (the closed six-label set; a record with one label yields at most one finding, and the
cross-label precedence is load-bearing):
  dtr-anchor                     the ``^## `` heading sequence contains the three consecutive
                                 entries ``## Constitution Check`` -> ``## Decision Tensions`` ->
                                 ``## Project Structure``
  dtr-section-missing            the plan carries no ``## Decision Tensions`` section, or the
                                 section carries no record while failing the ``N/A`` form (the
                                 literal ``N/A`` plus one explanation per load-bearing trigger,
                                 saying why that trigger does not hold). When it fires, ``dtr-anchor``
                                 is suppressed (the adjacency assertion necessarily reds, and one
                                 root cause is counted once)
  dtr-record-incomplete          a record does not carry each of the six field labels exactly
                                 once, or one of ``decision`` / ``antithesis`` /
                                 ``discriminating_evidence`` / ``revision_trigger`` is blank.
                                 A missing field label also suppresses ``expected-sacrifice-unmapped``
  dtr-tension-id                 every record heading begins with ``T-NNN`` (three digits), the
                                 identifiers are unique and increasing in document order
  dtr-rejected-form              the record hits the owner's closed rejection list (the literal
                                 ``expected_sacrifice: none`` or a blank sacrifice, an empty pole,
                                 the undecidable-wording list)
  expected-sacrifice-unmapped    ``expected_sacrifice`` does not resolve to a ``**SC-NNN Source**``
                                 entry of the same feature's ``requirements.md``

Every rule is live. The third cross-label precedence is the one that keeps the label counts
comparable to the sample count (FR-016 ③): a record whose ``expected_sacrifice`` is blank or the
literal ``none``, or whose ``binding_constraints`` misses a non-empty pole, reports ONLY
``dtr-rejected-form`` — ``dtr-record-incomplete`` and ``expected-sacrifice-unmapped`` are
suppressed, because an empty value has no decidable content and one root cause must not be
counted twice. Undecidable wording is a rejected form too, but it leaves the value parseable, so
the mapping verdict still runs beside it (a record can carry both labels).

Exit codes: 0 = no error (warnings allowed) / 1 = at least one error / 2 = input unreadable
(either file missing, undecodable, or without content lines). Read-only: no write point of any
kind, no resident process, standard library only.

Channel severity: the analyze channel's value domain is HIGH or 0 — a label either fired (HIGH)
or counted nothing (0), with no advisory or downgrade tier (``detection-and-severity.md`` § I).
That mapping is printed here, by the program, so the channel report records a verdict instead of
a table a consumer fills in: every finding carries ``severity=HIGH`` and every label carries its
own severity (HIGH when it fired, 0 when it did not).

Usage: python3 validate-decision-tensions.py --spec <spec-dir> [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INPUT = 2

STATUS_OK = "ok"
STATUS_ERROR = "error"
STATUS_UNREADABLE = "unreadable"

LABELS = (
    "dtr-anchor",
    "dtr-section-missing",
    "dtr-record-incomplete",
    "dtr-tension-id",
    "dtr-rejected-form",
    "expected-sacrifice-unmapped",
)

# The channel's value domain, and the single severity every label carries inside it
# (``detection-and-severity.md`` § I). A label that did not fire counts 0, never a lower tier.
CHANNEL_VALUE_DOMAIN = "HIGH-or-0"
CHANNEL_SEVERITY = "HIGH"

SECTION_HEADING = "## Decision Tensions"
ANCHOR_BEFORE = "## Constitution Check"
ANCHOR_AFTER = "## Project Structure"

# The mapping target: the requirements section holding ``**SC-NNN Source**`` entries (FR-010).
MEASUREMENT_SECTION = "### Measurement Sources & Collection Methods"

# The closed reference form ``<SC-NNN> Source <↓|↑>`` — the identifier, one space, the literal
# connective, then a mandatory direction token; anything after the token is free-form.
SACRIFICE_ID_RE = re.compile(r"SC-\d{3}")
SACRIFICE_CONNECTIVE = " Source "
DIRECTION_TOKENS = ("↓", "↑")
SOURCE_ENTRY_RE = re.compile(r"^[ \t]*(?:[-*+][ \t]+)?\*\*(SC-\d{3}) Source\*\*")

# ``binding_constraints`` carries its two poles as the two lines beneath the field label.
POLE_RE = re.compile(r"^-[ \t]*pole_(a|b)[ \t]*:[ \t]*(.*)$")

# The owner's undecidable-wording list (closed): replacing a trade-off with one of these phrases
# is a rejected form. Extending the list is an owner revision, never a local edit.
UNDECIDABLE_WORDING = ("要平衡", "综合考虑", "视情况而定")

# The literal that rejects the record outright (STR-002); a blank value is judged the same way.
NONE_LITERAL = "none"

# The ``N/A`` form: when the section carries no record, it must carry the literal ``N/A`` plus one
# explanation per load-bearing trigger, saying why that trigger does not hold. The trigger names are
# the owner's (``.specify/shared/guidelines/decision-tension.md`` § 承重门槛) — this checker reads them, it
# does not define them; extending the trigger set is an owner revision.
NA_LITERAL = "N/A"
NA_DOES_NOT_HOLD = "不成立"
LOAD_BEARING_TRIGGERS = ("不可逆", "跨团队", "高爆炸半径", "与宪法原则相关")
# One line justifies one trigger: naming a trigger on a line that also names another is a list,
# not a justification. The remainder must say why the trigger does not hold; a bare negation is
# not a reason, and this closed set is the mechanical line between the two (owner: the N/A
# grammar in ``.specify/shared/guidelines/decision-tension.md`` § 记录行文法).
NA_NEGATION_ONLY = ("不会", "不是", "没有", "否", "无", "不成立", "不存在")

# The ADR's ``tension_id`` reference slot (``docs/decisions/template.md`` § Alternatives): the
# slot label followed by a backticked ``T-NNN`` identifier. Read only on such a line, so an
# unrelated ``T-NNN`` mention elsewhere in the ADR never becomes a reference.
ADR_TENSION_ID_RE = re.compile(r"tension_id[^\n]*?`(T-\d{3})`")

# The six field labels, verbatim; the field set is closed by the owner (FR-002).
FIELD_NAMES = (
    "decision",
    "antithesis",
    "binding_constraints",
    "discriminating_evidence",
    "expected_sacrifice",
    "revision_trigger",
)
# The four fields whose blank value is a record-level incompleteness; ``expected_sacrifice`` and
# the two poles are judged as rejected forms (one root cause, one label).
VALUE_CHECKED_FIELDS = (
    "decision",
    "antithesis",
    "discriminating_evidence",
    "revision_trigger",
)

H2_RE = re.compile(r"^##\s")
H3_RE = re.compile(r"^###\s")
RECORD_HEADING_RE = re.compile(r"^###\s+(.*)$")
TENSION_ID_RE = re.compile(r"^T-\d{3}(?:\s|$)")
FIELD_RE = re.compile(r"^- \*\*([a-z_]+)\*\*:\s*(.*)$")


class Finding:
    __slots__ = ("line", "label", "text", "severity")

    def __init__(self, line, label, text, severity="error"):
        self.line = line
        self.label = label
        self.text = text
        self.severity = severity

    def render(self):
        return "%d: %s: %s" % (self.line, self.label, self.text)


class Record:
    """One ``### T-NNN`` sub-section: heading, absolute line number, field values."""

    __slots__ = ("tension_id", "line", "heading", "body", "fields")

    def __init__(self, heading, line):
        self.heading = heading
        self.line = line
        self.body = []
        token = heading.split()[0] if heading.split() else ""
        self.tension_id = token if TENSION_ID_RE.match(token) else None
        self.fields = {}

    def finalize(self):
        """Parse the field labels once the body is complete (bodies are appended in a scan)."""
        self._parse_fields()

    def _parse_fields(self):
        current = None
        for raw in self.body:
            m = FIELD_RE.match(raw)
            if m:
                name = m.group(1)
                entry = self.fields.setdefault(
                    name, {"inline": "", "continuation": [], "count": 0}
                )
                entry["inline"] = m.group(2).strip()
                entry["count"] += 1
                current = name
                continue
            if not raw.strip():
                current = None
                continue
            if current is not None and (raw.startswith("  ") or raw.startswith("\t")):
                self.fields[current]["continuation"].append(raw.strip())
            else:
                current = None

    def value(self, name):
        entry = self.fields.get(name)
        if entry is None:
            return ""
        chunks = [entry["inline"]] + entry["continuation"]
        return " ".join(chunk for chunk in chunks if chunk).strip()

    def count(self, name):
        entry = self.fields.get(name)
        return 0 if entry is None else entry["count"]

    def poles(self):
        """``{"a"|"b": value}`` for the pole lines carried under ``binding_constraints``.

        The record shape (``data-model.md`` E2) puts ``pole_a`` / ``pole_b`` on the two lines
        beneath the field label, so a pole written anywhere else is absent — the same reading the
        owner gives "行缺失或留空". A pole line repeated keeps its first value.
        """
        found = {}
        entry = self.fields.get("binding_constraints")
        if entry is None:
            return found
        for line in entry["continuation"]:
            match = POLE_RE.match(line.strip())
            if match:
                found.setdefault(match.group(1), match.group(2).strip())
        return found

    def field_text(self):
        """The record's field values as one string — the surface the wording list is matched on."""
        return " ".join(self.value(name) for name in FIELD_NAMES)


def _visible_lines(text):
    """Lines with fenced code blocks blanked — the same rule the record grammar declares."""
    out = []
    in_fence = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            out.append("")
            continue
        out.append("" if in_fence else raw)
    return out


def _h2_entries(lines):
    return [(index, line.rstrip()) for index, line in enumerate(lines) if H2_RE.match(line.rstrip())]


def _section_bounds(lines, section_index):
    end = len(lines)
    for index, heading in _h2_entries(lines):
        if index > section_index:
            end = index
            break
    return section_index + 1, end


def _records(lines, start, end):
    records = []
    current = None
    for index in range(start, end):
        line = lines[index]
        if H3_RE.match(line):
            if current is not None:
                current.finalize()
                records.append(current)
            m = RECORD_HEADING_RE.match(line.rstrip())
            current = Record(m.group(1).strip() if m else "", index + 1)
            continue
        if current is not None:
            current.body.append(line)
    if current is not None:
        current.finalize()
        records.append(current)
    return records


def parse_sacrifice(value):
    """Parse ``expected_sacrifice`` against the closed form ``<SC-NNN> Source <↓|↑>``.

    Returns ``(state, detail)``: ``state`` is ``"resolved"`` (detail = the identifier) or
    ``"unmapped"`` (detail = why). A value naming zero or several identifiers is unmapped — a
    multi-source "cost" has no single value (``contracts/measurement-binding.md`` C-2). The
    direction token is a record-level assertion: only membership in the two-value set is judged,
    never whether the direction matches the source's real semantics (C-1).
    """
    text = value.strip()
    identifiers = SACRIFICE_ID_RE.findall(text)
    if len(identifiers) != 1:
        return "unmapped", "binds %d SC-NNN identifiers; exactly one source is allowed" % len(
            identifiers
        )
    identifier = identifiers[0]
    if not text.startswith(identifier):
        return "unmapped", "does not begin with its %s identifier" % identifier
    remainder = text[len(identifier):]
    if remainder == SACRIFICE_CONNECTIVE.rstrip():
        return "unmapped", "direction token is missing or outside {%s}" % ", ".join(
            DIRECTION_TOKENS
        )
    if not remainder.startswith(SACRIFICE_CONNECTIVE):
        return "unmapped", "lacks the literal `%s` connective after %s" % (
            SACRIFICE_CONNECTIVE.strip(), identifier,
        )
    tail = remainder[len(SACRIFICE_CONNECTIVE):]
    if not tail or tail[0] not in DIRECTION_TOKENS:
        return "unmapped", "direction token is missing or outside {%s}" % ", ".join(
            DIRECTION_TOKENS
        )
    return "resolved", identifier


def _justified_trigger(line):
    """The load-bearing trigger this line justifies, or ``None`` when it justifies none.

    One line justifies one trigger. A line naming two or more triggers lists them instead of
    explaining any of them (the flat-sentence defect: four trigger names in one sentence, no
    reason attached to any), and the remainder left once the trigger name, the punctuation and the
    surrounding whitespace are removed must still say why — a bare negation is not a reason, and
    length is not the test (a short real reason passes).
    """
    hits = [trigger for trigger in LOAD_BEARING_TRIGGERS if trigger in line]
    if len(hits) != 1:
        return None
    remainder = line.replace(hits[0], "", 1).strip()
    remainder = remainder.strip("-—:：,，.。;；、!！?？()（）[]【】 \t")
    return hits[0] if remainder and remainder not in NA_NEGATION_ONLY else None


def na_verdict(section_lines):
    """Judge the ``N/A`` form of a section that carries no record; ``None`` means it holds.

    FR-011 (a) is fail-closed in both directions: a section that carries neither a ``T-NNN`` record
    nor the literal ``N/A`` is a missing record, and an ``N/A`` that does not justify the four
    load-bearing triggers one by one is a missing record too. The criterion is mechanical — the
    literal marker is present, the section says the triggers do not hold, and each trigger owns a
    distinct line whose remainder is an explanation of its own — so the checker never has to judge
    whether the plan "really" contains a load-bearing decision (FR-011 forbids asking it to).
    """
    block = [line for line in section_lines if line.strip()]
    if not any(line.strip().startswith(NA_LITERAL) for line in block):
        return "carries neither a `T-NNN` record nor the literal `%s`" % NA_LITERAL
    if not any(NA_DOES_NOT_HOLD in line for line in block):
        return "`%s` does not state that the four triggers do not hold" % NA_LITERAL
    justified = {trigger for trigger in (_justified_trigger(line) for line in block) if trigger}
    unjustified = [trigger for trigger in LOAD_BEARING_TRIGGERS if trigger not in justified]
    if unjustified:
        return "`%s` does not justify these triggers one by one: %s" % (
            NA_LITERAL, "、".join(unjustified),
        )
    return None


def measurement_sources(requirements_text):
    """The ``SC-NNN`` identifiers declared as ``**SC-NNN Source**`` in the requirements section.

    The section is the mapping target owned by the feature's ``requirements.md``; this function
    only collects its entry identifiers and never restates what the entries say.
    """
    sources = set()
    inside = False
    for line in _visible_lines(requirements_text):
        stripped = line.strip()
        if stripped == MEASUREMENT_SECTION.strip():
            inside = True
            continue
        if inside and re.match(r"^#{1,3}\s", stripped):
            inside = False
            continue
        if inside:
            match = SOURCE_ENTRY_RE.match(line)
            if match:
                sources.add(match.group(1))
    return sources


def index_records(plan_text):
    """Map ``tension_id`` -> ``{"line", "fields"}`` for every record in a plan.

    One parser, two consumers (``contracts/adr-reference.md`` C-2): this checker's identifier
    check and the ADR dangling-``tension_id`` contract test both call this function. A duplicate
    identifier keeps its first occurrence, so the index answers 'does this id resolve?' without
    hiding the duplicate (``dtr-tension-id`` reports it).
    """
    lines = _visible_lines(plan_text)
    section = None
    for index, heading in _h2_entries(lines):
        if heading == SECTION_HEADING:
            section = index
            break
    if section is None:
        return {}
    start, end = _section_bounds(lines, section)
    index = {}
    for record in _records(lines, start, end):
        if record.tension_id and record.tension_id not in index:
            index[record.tension_id] = {
                "line": record.line,
                "fields": {name: record.value(name) for name in record.fields},
            }
    return index


def link_verdict(adr_text, plan_text):
    """Judge one ADR's ``tension_id`` references against one plan; ``(status, dangling)``.

    ``contracts/adr-reference.md`` C-2 makes an unresolvable reference a broken-link **error**, and
    requires the resolution to reuse this module's record index so one parser serves both the
    identifier check and the link check. Returns ``("ok", [])`` when every reference resolves and
    ``("error", [identifiers])`` when any does not — the same value domain the checker's own exit
    code uses (``STATUS_OK`` / ``STATUS_ERROR``), so a caller reads the verdict, never prose.

    The declared call surface is the contract test over a fixture pair: this function adds no
    command, and the analyze channel never scans ``docs/decisions/`` (C-2). An ADR carrying no
    ``tension_id`` slot at all is not a broken link — the slot requirement is C-1's, judged by the
    ADR template test.
    """
    index = index_records(plan_text)
    dangling = []
    for line in _visible_lines(adr_text):
        for match in ADR_TENSION_ID_RE.finditer(line):
            identifier = match.group(1)
            if identifier not in index and identifier not in dangling:
                dangling.append(identifier)
    return (STATUS_ERROR if dangling else STATUS_OK), dangling


def _unreadable(spec, reason):
    return {
        "spec": str(spec),
        "status": STATUS_UNREADABLE,
        "checks": [{"label": label, "status": "pass", "count": 0, "severity": 0}
                   for label in LABELS],
        "findings": [],
        "channel": {"value_domain": CHANNEL_VALUE_DOMAIN, "high": 0},
        "reason": reason,
        "scanned": {"lines": 0, "records": 0},
    }


def validate(spec):
    """Judge one spec directory and return ``{spec,status,checks,findings,scanned[,reason]}``."""
    spec_path = Path(spec)
    plan_path = spec_path / "plan.md"
    requirements_path = spec_path / "requirements.md"

    texts = {}
    for path in (plan_path, requirements_path):
        if not path.is_file():
            return _unreadable(spec_path, "%s is missing" % path.name)
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return _unreadable(spec_path, "%s is not decodable text" % path.name)
        if not text.strip():
            return _unreadable(spec_path, "%s has no content lines" % path.name)
        texts[path.name] = text

    lines = _visible_lines(texts["plan.md"])
    entries = _h2_entries(lines)
    headings = [heading for _, heading in entries]
    section_index = None
    for index, heading in entries:
        if heading == SECTION_HEADING:
            section_index = index
            break

    buckets = {label: [] for label in LABELS}

    if section_index is None:
        buckets["dtr-section-missing"].append(Finding(
            1, "dtr-section-missing",
            "plan carries no `%s` section" % SECTION_HEADING,
        ))
        records = []
    else:
        anchor_ok = False
        if ANCHOR_BEFORE in headings:
            at = headings.index(ANCHOR_BEFORE)
            anchor_ok = (
                len(headings) > at + 2
                and headings[at + 1] == SECTION_HEADING
                and headings[at + 2] == ANCHOR_AFTER
            )
        if not anchor_ok:
            buckets["dtr-anchor"].append(Finding(
                1, "dtr-anchor",
                "`%s` is not the direct successor of `%s` followed by `%s`"
                % (SECTION_HEADING, ANCHOR_BEFORE, ANCHOR_AFTER),
            ))
        start, end = _section_bounds(lines, section_index)
        records = _records(lines, start, end)
        if not records:
            # No record: the section must declare the ``N/A`` form and justify it trigger by
            # trigger. Anything else is the same defect class as a missing section (FR-011 (a)):
            # a record-less plan that does not say why must not pass as a clean trivial plan.
            na_detail = na_verdict(lines[start:end])
            if na_detail is not None:
                buckets["dtr-section-missing"].append(Finding(
                    section_index + 1, "dtr-section-missing",
                    "`%s` section %s" % (SECTION_HEADING, na_detail),
                ))

    sources = measurement_sources(texts["requirements.md"])

    for position, record in enumerate(records, start=1):
        expected_id = "T-%03d" % position
        if record.tension_id is None:
            buckets["dtr-tension-id"].append(Finding(
                record.line, "dtr-tension-id",
                "record heading does not begin with a `T-NNN` identifier: %r" % record.heading,
            ))
        elif record.tension_id != expected_id:
            buckets["dtr-tension-id"].append(Finding(
                record.line, "dtr-tension-id",
                "expected %s in document order, found %s" % (expected_id, record.tension_id),
            ))

        missing = [name for name in FIELD_NAMES if record.count(name) == 0]
        duplicated = [name for name in FIELD_NAMES if record.count(name) > 1]
        blank = [
            name for name in VALUE_CHECKED_FIELDS
            if record.count(name) == 1 and not record.value(name)
        ]
        if missing or duplicated or blank:
            parts = []
            if missing:
                parts.append("missing field label(s): %s" % ", ".join(missing))
            if duplicated:
                parts.append("duplicated field label(s): %s" % ", ".join(duplicated))
            if blank:
                parts.append("blank value(s): %s" % ", ".join(blank))
            buckets["dtr-record-incomplete"].append(Finding(
                record.line, "dtr-record-incomplete", "; ".join(parts),
            ))
            # Precedence ②: a missing field label leaves no value to parse, so the mapping
            # verdict and the rejected-form verdict are both suppressed for this record.
            continue

        # Precedence ③: an empty value (or the literal ``none``) is a rejected form, judged
        # once — it suppresses both ``dtr-record-incomplete`` and ``expected-sacrifice-unmapped``.
        rejected = []
        sacrifice = record.value("expected_sacrifice")
        empty_value = False
        if sacrifice.strip() == NONE_LITERAL:
            rejected.append("`expected_sacrifice` is the literal `%s`" % NONE_LITERAL)
            empty_value = True
        elif not sacrifice.strip():
            rejected.append("`expected_sacrifice` is blank")
            empty_value = True
        poles = record.poles()
        for pole in ("a", "b"):
            if not poles.get(pole, "").strip():
                rejected.append("`binding_constraints` misses a non-empty `pole_%s`" % pole)
                empty_value = True
        wording = [phrase for phrase in UNDECIDABLE_WORDING if phrase in record.field_text()]
        if wording:
            rejected.append(
                "undecidable wording instead of a trade-off: %s" % ", ".join(wording)
            )
        if rejected:
            buckets["dtr-rejected-form"].append(Finding(
                record.line, "dtr-rejected-form", "; ".join(rejected),
            ))
            if empty_value:
                continue

        if sacrifice.strip():
            state, detail = parse_sacrifice(sacrifice)
            if state == "unmapped":
                buckets["expected-sacrifice-unmapped"].append(Finding(
                    record.line, "expected-sacrifice-unmapped",
                    "`expected_sacrifice` %s" % detail,
                ))
            elif detail not in sources:
                buckets["expected-sacrifice-unmapped"].append(Finding(
                    record.line, "expected-sacrifice-unmapped",
                    "`expected_sacrifice` names %s, which has no `**%s Source**` entry under "
                    "`%s` in requirements.md" % (detail, detail, MEASUREMENT_SECTION),
                ))

    findings = [finding for label in LABELS for finding in buckets[label]]
    checks = [
        {"label": label, "status": "fail" if buckets[label] else "pass",
         "count": len(buckets[label]),
         # The channel's value domain, printed by the program: a label that fired is HIGH, a
         # label that did not is 0. There is no advisory or downgrade tier between them.
         "severity": CHANNEL_SEVERITY if buckets[label] else 0}
        for label in LABELS
    ]
    status = STATUS_ERROR if any(f.severity == "error" for f in findings) else STATUS_OK
    return {
        "spec": str(spec_path),
        "status": status,
        "checks": checks,
        "findings": findings,
        "channel": {"value_domain": CHANNEL_VALUE_DOMAIN, "high": len(findings)},
        "scanned": {"lines": len(lines), "records": len(records)},
    }


# --version, wired through the one version source (C-8)
#
# `guard_argv()` answers `--version` (and rejects an undeclared option) BEFORE any parser
# reads the line, so it works for a flat argparse parser, for one whose subcommands are
# required, and for the two modules that read sys.argv by hand. It writes nothing and
# resolves `<script-name> <framework-version>` from the nearest pyproject.toml at run
# time — this file carries no version literal. `--help` is left to the module's own body.
import sys as _sig_sys  # noqa: E402
import pathlib as _sig_pathlib

_SIG_DIR = str(_sig_pathlib.Path(__file__).resolve().parent)
if _SIG_DIR not in _sig_sys.path:
    _sig_sys.path.insert(0, _SIG_DIR)
try:  # the helper owns the rule; an engine copied WITHOUT it still runs its actions
    from script_interface_cli import configure_parser as _sig_configure  # noqa: E402
    from script_interface_cli import guard_argv as _sig_guard  # noqa: E402
except ImportError:  # a sandbox/handler copy carries the engine but not the helper
    def _sig_configure(parser, **_kwargs):
        return parser

    def _sig_guard(_argv=None, declared=None, **_kwargs):
        return None

def main(argv=None):
    _sig_guard(argv, declared=['--spec', '--json'])  # answer --version / reject an undeclared option
    parser = argparse.ArgumentParser(
        prog="validate-decision-tensions.py",
        description="Judge the structural propositions of a plan's Decision Tension Records.",
    )
    _sig_configure(parser)

    parser.add_argument("--spec", required=True,
                        help="the spec directory holding plan.md and requirements.md")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    result = validate(args.spec)
    findings = result["findings"]
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")

    if args.json:
        print(json.dumps({
            "spec": result["spec"],
            "status": result["status"],
            "checks": result["checks"],
            "errors": errors,
            "warnings": warnings,
            "scanned": result["scanned"],
            "channel": result["channel"],
            "findings": [
                {"line": finding.line, "label": finding.label,
                 "severity": CHANNEL_SEVERITY, "text": finding.text}
                for finding in findings
            ],
        }, ensure_ascii=False, indent=2))
    else:
        print("spec: %s" % result["spec"])
        print("status: %s" % result["status"])
        for check in result["checks"]:
            print("  [%s] %s (%d)" % (check["label"], check["status"], check["count"]))
        print("scanned: %d lines, %d record(s)"
              % (result["scanned"]["lines"], result["scanned"]["records"]))
        print("channel: value_domain=%s, high=%d"
              % (result["channel"]["value_domain"], result["channel"]["high"]))
        if result.get("reason"):
            print("unreadable: %s" % result["reason"])
        for finding in findings:
            print("%s %s" % (CHANNEL_SEVERITY, finding.render()))
        print("%d error(s), %d warning(s)" % (errors, warnings))

    if result["status"] == STATUS_UNREADABLE:
        return EXIT_INPUT
    return EXIT_ERROR if errors else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
