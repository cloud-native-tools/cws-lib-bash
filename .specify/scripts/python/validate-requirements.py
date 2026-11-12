#!/usr/bin/env python3
"""validate-requirements.py — deterministic checker for a `requirements.md` artifact.

Program-First discipline (.specify/shared/guidelines/token-efficiency.md): the propositions checked
here are fixed, textual and decidable, so a program judges them and prints a verdict; an
agent MUST NOT re-derive them by reading the artifact and declaring a result.

Checks (this enumeration IS the pinned label set — the house pin extracts it from this
docstring with `^  ([A-Za-z][A-Za-z-]*)\\s{2,}`, so the two-space indent and the gap of at
least two spaces before each description are load-bearing, not cosmetic):
  id-contiguous   FR- and SC- definition ids each form one gapless sequence, per prefix and
                  never across prefixes; a zero-padding inconsistency (`FR-7` beside
                  `FR-007`) or a letter suffix (`FR-003a`) is a FORMAT violation and is
                  named as written — it is never normalized away, because normalizing hides
                  the author's numbering intent
  doc-order       definition rows appear in ascending numeric order. Anchored on DEFINITION
                  lines only, never on every id occurrence: cross-references legitimately
                  appear out of order, and anchoring on occurrences reports false violations
                  on a clean spec. The `## Clarifications` section is excluded for the same
                  reason — it is append-only history that quotes rows from before a
                  renumbering. BOTH anchors are load-bearing.
  ref-resolvable  every FR-nnn / SC-nnn / [[STR-nnn]] reference outside a code span resolves
                  to a definition; the STR check is bidirectional (a defined string nobody
                  cites is reported too); a Shared Strings `Consumed by` cell is
                  reverse-consistent with the rows it names
  marker-count    counts ACTIVE clarification markers — the colon is inside the pattern and a
                  backtick prefix is excluded, so a spec that merely discusses the marker is
                  not counted as carrying one
  dup-id          an id defined twice is an error, reported separately from ref-resolvable:
                  the two have opposite remedies (delete one, or add the missing definition)
  path-marker     every Success Criterion definition line carries `**Path**: final` or
                  `**Path**: supporting` as its LAST token, exactly once, and an `execution`-class
                  feature carries at least one `final` path. Owner of the rule: the `## Success
                  Criteria` `Path` contract in `.specify/shared/workflow/acceptance-hardening.md` § Closure
                  Verdict. Judged only on a spec that DECLARES its flow class
                  (`**Flow Class**: execution|expression` in the header block), and the reason is
                  **scope, not decidability**: the closure checker resolves an undeclared class to
                  `execution` (the strict side, 077 FR-004), so the class is always namable — what
                  this label declines is applying a new format rule to the whole existing corpus.
                  Every requirements.md in the checkout that carries no declaration would then be
                  reported as a format violation, which is a migration decision this rule does not
                  contain.

Skeleton criterion (checker-form C-12 — a semantic judgement, so it is written down here
rather than left to the reader): an artifact is skeleton-only when a requirement row still
carries an uppercase bracketed placeholder such as [SPEC], [REQUIREMENT NAME], [PLACEHOLDER],
[DATE], [REQUIREMENTS_KEY], [FEATURE_ID] or [FEATURE_NAME]. That state is reported as a fourth
`status` value; it does NOT get a fourth exit code.

Exit codes: 0 = no error (warnings allowed) / 1 = at least one error / 2 = file missing,
unparsable, or no content lines. Read-only: this script has no write point of any kind.

Usage: python3 validate-requirements.py <requirements.md> [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import clause_extract  # noqa: E402  (one implementation of the code-span/fence rules)
import declaration_reader  # noqa: E402  (the declaration layer's one read entry, same directory)

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INPUT = 2

STATUS_OK = "ok"
STATUS_ERROR = "error"
STATUS_MISSING = "missing"
STATUS_UNPARSABLE = "unparsable"
STATUS_EMPTY = "empty"
STATUS_SKELETON = "skeleton"

LABELS = ("id-contiguous", "doc-order", "ref-resolvable", "marker-count", "dup-id",
          "path-marker")

DEFINITION_RE = re.compile(r"^- \*\*(FR|SC)-(\d+)([a-z]?)\*\*")
STR_ROW_RE = re.compile(r"^\|\s*`(STR-\d+)`\s*\|")
STR_REF_RE = re.compile(r"\[\[(STR-\d+)\]\]")
FR_MENTION_RE = re.compile(r"\bFR-(\d{1,3})\b")
SC_MENTION_RE = re.compile(r"\bSC-(\d{1,3})\b")
MARKER_RE = re.compile(r"(?<!`)\[NEEDS CLARIFICATION:")
PLACEHOLDER_RE = re.compile(r"\[(?!NEEDS)[A-Z][A-Z_ ]{3,}\]|\[placeholder\]")
CLARIFICATIONS_HEADING_RE = re.compile(r"^##\s+Clarifications")
HEADING_RE = re.compile(r"^#{1,6}\s")

# --- the `Path` marker (Feature 081; owner: .specify/shared/workflow/acceptance-hardening.md) -------- #
# The marker is a line attribute, not a second table: both this checker and the closure checker
# anchor on the definition-line prefix and read the trailing token, so no separate list has to be
# kept in sync with the Success Criteria rows.
PATH_MARKER_RE = re.compile(r"\*\*Path\*\*")
PATH_TOKEN_RE = re.compile(r"\*\*Path\*\*\s*:\s*(\S+)\s*$")
FLOW_CLASS_RE = re.compile(r"^\*\*Flow Class\*\*\s*:\s*(\S+)\s*$")
# `EXECUTION_CLASS` is derived below from the `flow-class-classes` declaration; the literal that
# used to sit here was the second copy of the class axis (review 084 blocking #1).

#: Feature 084, batch 1 row 9: the `Path` closed set is a declaration-layer fact
#: (`.specify/shared/declarations/facts/success-criterion-path-values.yaml`). This checker carries no copy of
#: the member set — it reads it through the shared read entry, so a third value added to the
#: declaration changes what this rule refuses with no edit here, and a second tuple anywhere is the
#: defect the declaration exists to make impossible.
PATH_FACT = "success-criterion-path-values"


def _declared_path_values():
    """`(values, label)` for the `Path` closed set; `((), <STR-014 instance>)` when unreadable."""
    try:
        body = declaration_reader.load_fact(
            declaration_reader.find_repo(Path(__file__).resolve()), PATH_FACT)["body"]
        values = body.get("statement")
        if not isinstance(values, list) or not values:
            raise ValueError("statement is not a non-empty sequence")
        return tuple(str(value) for value in values), None
    except (declaration_reader.DeclarationError, TypeError, ValueError):
        return (), declaration_reader.absent_label(PATH_FACT)


PATH_VALUES, PATH_VALUES_LABEL = _declared_path_values()
PASS_PATH = PATH_VALUES[0] if PATH_VALUES else "final"


def _declared_flow_classes():
    """`(values, label)` for the `flow-class-classes` closed set; `((), <STR-014>)` when unreadable."""
    try:
        body = declaration_reader.load_fact(
            declaration_reader.find_repo(Path(__file__).resolve()), "flow-class-classes")["body"]
        values = body.get("statement")
        if not isinstance(values, list) or not values:
            raise ValueError("statement is not a non-empty sequence")
        return tuple(str(value) for value in values), None
    except (declaration_reader.DeclarationError, TypeError, ValueError):
        return (), declaration_reader.absent_label("flow-class-classes")


FLOW_CLASSES, FLOW_CLASSES_LABEL = _declared_flow_classes()
EXECUTION_CLASS = FLOW_CLASSES[0] if FLOW_CLASSES else "execution"
if FLOW_CLASSES_LABEL:
    sys.stderr.write("%s\n" % FLOW_CLASSES_LABEL)


class DomainUnavailable(Exception):
    """The `Path` closed set cannot be read, so the `path-marker` rule cannot be judged.

    Raised only when the artifact declares a flow class — a spec outside the closure system never
    needs the domain, so its judgement is unaffected by a missing declaration layer (FR-012). The
    caller renders :attr:`label` and maps it to an input error: a degraded read is never a pass.
    """

    def __init__(self, label):
        super().__init__(label)
        self.label = label


class Finding:
    __slots__ = ("line", "label", "text", "severity")

    def __init__(self, line, label, text, severity="error"):
        self.line = line
        self.label = label
        self.text = text
        self.severity = severity

    def render(self):
        return "%d: %s: %s" % (self.line, self.label, self.text)


def _scan_view(text):
    """Lines with fenced blocks blanked and inline code spans removed — the view used for
    every structural judgement. The originals are kept for message text."""
    return clause_extract.strip_fences(text.split("\n"))


def _definitions(lines):
    """(prefix, digits-as-written, number, suffix, line_no) for every definition row.

    The digits are kept as written because zero-padding is a FORMAT property: measuring it on
    the parsed integer would report `FR-001` as unpadded.
    """
    out = []
    for i, line in enumerate(lines):
        m = DEFINITION_RE.match(line)
        if m:
            out.append((m.group(1), m.group(2), int(m.group(2)), m.group(3), i + 1))
    return out


def _clarifications_start(lines):
    for i, line in enumerate(lines):
        if CLARIFICATIONS_HEADING_RE.match(line):
            return i
    return len(lines)


def check_id_contiguous(lines, defs):
    findings = []
    for prefix in ("FR", "SC"):
        rows = [(digits, n, suffix, ln) for p, digits, n, suffix, ln in defs if p == prefix]
        for digits, n, suffix, ln in rows:
            raw = "%s-%s%s" % (prefix, digits, suffix)
            if suffix:
                findings.append(Finding(
                    ln, "id-contiguous",
                    "%s carries a letter suffix, which this artifact's own edge cases judge a "
                    "format violation — fold it into the preceding id or renumber the tail; "
                    "it is reported as written, never normalized" % raw))
            elif len(digits) != 3:
                findings.append(Finding(
                    ln, "id-contiguous",
                    "%s is not zero-padded to three digits — write %s-%03d; the unpadded form "
                    "is a format violation and is not normalized away" % (raw, prefix, n)))
        numbers = sorted({n for digits, n, s, _ in rows if not s and len(digits) == 3})
        if not numbers:
            continue
        missing = [n for n in range(1, numbers[-1] + 1) if n not in numbers]
        for n in missing:
            first = next(ln for _, _, _, ln in rows)
            findings.append(Finding(
                first, "id-contiguous",
                "the %s sequence skips %s-%03d — either that row was deleted or it was never "
                "written; restore it or renumber the tail so the sequence is gapless"
                % (prefix, prefix, n)))
    return findings


def check_doc_order(lines, defs):
    findings = []
    limit = _clarifications_start(lines)
    for prefix in ("FR", "SC"):
        seq = [(n, ln) for p, digits, n, s, ln in defs
               if p == prefix and not s and len(digits) == 3 and ln - 1 < limit]
        for (a, la), (b, lb) in zip(seq, seq[1:]):
            if b < a:
                findings.append(Finding(
                    lb, "doc-order",
                    "ORDER BREAK: %s-%03d after %s-%03d — definition rows must ascend in "
                    "document order; move the row back above %s-%03d"
                    % (prefix, b, prefix, a, prefix, a)))
    return findings


def check_dup_id(defs):
    findings = []
    seen = {}
    for prefix, digits, n, suffix, ln in defs:
        if suffix:
            continue
        key = (prefix, n)
        if key in seen:
            findings.append(Finding(
                ln, "dup-id",
                "%s-%03d is defined twice (first at line %d) — delete one of the two rows; "
                "this is reported separately from an unresolvable reference because the "
                "remedies are opposite" % (prefix, n, seen[key])))
        else:
            seen[key] = ln
    return findings


def _shared_strings(lines):
    """Shared Strings table rows, matched on the fence-blanked ORIGINAL lines: the string id is
    written inside backticks by design, so a code-span-stripped view erases it."""
    rows = []
    for i, line in enumerate(lines):
        m = STR_ROW_RE.match(line)
        if m:
            rows.append((m.group(1), i + 1, line))
    return rows


def check_ref_resolvable(raw_lines, lines, defs, str_rows):
    findings = []
    defined_fr = {n for p, digits, n, s, _ in defs if p == "FR" and not s}
    defined_sc = {n for p, digits, n, s, _ in defs if p == "SC" and not s}
    defined_str = {sid for sid, _, _ in str_rows}
    referenced_str = set()

    for i, line in enumerate(lines):
        ln = i + 1
        for m in STR_REF_RE.finditer(clause_extract.strip_code_spans(line)):
            referenced_str.add(m.group(1))

    for i, line in enumerate(lines):
        ln = i + 1
        for rx, defined, prefix in ((FR_MENTION_RE, defined_fr, "FR"), (SC_MENTION_RE, defined_sc, "SC")):
            for m in rx.finditer(line):
                digits = m.group(1)
                if len(digits) != 3:
                    continue  # an unpadded form is id-contiguous's finding, not a dangling ref
                if int(digits) not in defined:
                    findings.append(Finding(
                        ln, "ref-resolvable",
                        "%s-%s is referenced here but never defined — add its definition row "
                        "or fix the reference" % (prefix, digits)))
        for m in STR_REF_RE.finditer(line):
            if m.group(1) not in defined_str:
                findings.append(Finding(
                    ln, "ref-resolvable",
                    "[[%s]] is referenced but the Shared Strings table does not define it — "
                    "add the row or fix the id" % m.group(1)))

    # reverse direction: a defined string nobody cites (C-14) — a warning, not an error
    for sid, ln, _ in str_rows:
        if sid not in referenced_str:
            findings.append(Finding(
                ln, "ref-resolvable",
                "%s is defined but never cited as [[%s]] — either cite it from the row that "
                "consumes it verbatim, or drop the row" % (sid, sid), severity="warning"))

    # Consumed-by reverse consistency (C-15)
    for sid, ln, row in str_rows:
        tail = "|".join(row.split("|")[3:])
        named = [("FR", d) for d in FR_MENTION_RE.findall(tail)]
        named += [("SC", d) for d in SC_MENTION_RE.findall(tail)]
        for prefix, digits in sorted(set(named)):
            if len(digits) != 3:
                continue
            target = next((j + 1 for j, l in enumerate(lines)
                           if l.startswith("- **%s-%s**" % (prefix, digits))), None)
            if target is None:
                continue
            if "[[%s]]" % sid not in lines[target - 1]:
                findings.append(Finding(
                    ln, "ref-resolvable",
                    "the `Consumed by` cell of %s names %s-%s, but that row does not cite "
                    "[[%s]] — re-typing the literal instead of citing the id is the drift this "
                    "check exists to catch" % (sid, prefix, digits, sid)))
    return findings


def check_marker_count(raw_lines):
    findings = []
    for i, line in enumerate(raw_lines):
        for _ in MARKER_RE.finditer(line):
            findings.append(Finding(
                i + 1, "marker-count",
                "an active [NEEDS CLARIFICATION: marker is still present — resolve it with "
                "/speckit.clarify and record the answer under ## Clarifications"))
    return findings


def _flow_class(lines):
    """The spec's declared flow class, or None when it declares none.

    Read from the header block's `**Flow Class**: <value>` line. Declaration only: this checker
    never infers a class from the content, because the closure rule's exemption is mechanical
    (`expression` is exempt from the `final >= 1` floor) and an inferred class would make the
    exemption a judgement call.
    """
    for line in lines:
        m = FLOW_CLASS_RE.match(line)
        if m:
            return m.group(1)
    return None


def check_path_marker(lines, defs, name):
    """Every SC definition line carries exactly one `**Path**` marker, as its last token."""
    findings = []
    if _flow_class(lines) is None:
        return findings  # outside the closure system — see this label's docstring scope note
    if not PATH_VALUES:
        # FR-012 / FR-013: the member set is a declaration and the layer is unreadable here. Judging
        # against an empty domain would refuse every value (a false red); skipping the rule would read
        # as a pass. The run therefore stops on the `declaration-absent` label, never on a traceback.
        raise DomainUnavailable(PATH_VALUES_LABEL)
    sc_rows = [(n, ln, lines[ln - 1]) for prefix, digits, n, suffix, ln in defs
               if prefix == "SC" and not suffix and len(digits) == 3]
    has_final = False
    # A marker that could not be read leaves its criterion's path unknown, so the class rule's
    # input is incomplete. Emitting the derived class finding as well would report one root cause
    # twice and point the author at the wrong line.
    parsed_cleanly = True
    for n, ln, line in sc_rows:
        label = "SC-%03d" % n
        occurrences = len(PATH_MARKER_RE.findall(line))
        if occurrences == 0:
            parsed_cleanly = False
            findings.append(Finding(
                ln, "path-marker",
                "%s in %s carries no `**Path**` marker — every success criterion states whether "
                "it proves the feature's main user journey (`**Path**: final`) or is supporting "
                "evidence (`**Path**: supporting`), written as the last token of its line"
                % (label, name)))
            continue
        if occurrences > 1:
            parsed_cleanly = False
            findings.append(Finding(
                ln, "path-marker",
                "%s in %s carries %d `**Path**` markers — the marker occurs exactly once per "
                "line; a second one is a defect, not a choice"
                % (label, name, occurrences)))
            continue
        token = PATH_TOKEN_RE.search(line)
        if token is None:
            parsed_cleanly = False
            findings.append(Finding(
                ln, "path-marker",
                "%s in %s carries its `**Path**` marker somewhere other than the last token — "
                "write `**Path**: final` or `**Path**: supporting` at the end of the line, so a "
                "parser needs no sentence analysis" % (label, name)))
            continue
        value = token.group(1)
        if value not in PATH_VALUES:
            parsed_cleanly = False
            findings.append(Finding(
                ln, "path-marker",
                "%s in %s declares `**Path**: %s`, outside the closed two-value domain (`final` / "
                "`supporting`); the value decides whether the criterion can refuse a verdict, so "
                "a third value has no meaning to fall back on" % (label, name, value)))
            continue
        if value == PASS_PATH:
            has_final = True
    if sc_rows and parsed_cleanly and not has_final and _flow_class(lines) == EXECUTION_CLASS:
        findings.append(Finding(
            sc_rows[0][1], "path-marker",
            "%s declares `**Flow Class**: execution` but no success criterion is on the `final` "
            "path — an `execution` feature MUST carry at least one `final`-path criterion, "
            "otherwise it has nothing that could make it acceptable however honest its "
            "`supporting` rows are" % name))
    return findings


def _skeleton(raw_lines, lines, defs):
    """Skeleton = the template was never filled in. Two shapes, both narrow on purpose so a real
    spec is never mistaken for one: a placeholder inside the first few lines (the title/header
    block), or a placeholder inside a definition row itself."""
    if not defs:
        return bool(raw_lines) and not any(l.strip() and not HEADING_RE.match(l) for l in lines)
    head = [l for l in lines[:6] if l.strip()]
    if any(PLACEHOLDER_RE.search(l) for l in head):
        return True
    return any(DEFINITION_RE.match(l) and PLACEHOLDER_RE.search(l) for l in lines)


def validate(path):
    """Run every check. Returns (status, findings, checks, scanned)."""
    p = Path(path)
    if not p.is_file():
        return STATUS_MISSING, [], [], {"lines": 0, "definition_rows": 0, "shared_strings": 0}
    try:
        text = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return STATUS_UNPARSABLE, [], [], {"lines": 0, "definition_rows": 0, "shared_strings": 0}

    raw_lines = clause_extract.strip_fences(text.split("\n"))
    lines = [clause_extract.strip_code_spans(l) for l in raw_lines]
    if not any(l.strip() for l in lines):
        return STATUS_EMPTY, [], [], {"lines": 0, "definition_rows": 0, "shared_strings": 0}

    defs = _definitions(lines)
    str_rows = _shared_strings(raw_lines)
    scanned = {"lines": len(text.split("\n")), "definition_rows": len(defs), "shared_strings": len(str_rows)}

    if _skeleton(raw_lines, lines, defs):
        return STATUS_SKELETON, [Finding(
            1, "skeleton",
            "%s still carries template placeholders — fill every requirement row before "
            "validating; a skeleton is reported as a status, not as a fourth exit code" % p.name
        )], [], scanned

    buckets = {
        "id-contiguous": check_id_contiguous(lines, defs),
        "doc-order": check_doc_order(lines, defs),
        "dup-id": check_dup_id(defs),
        "ref-resolvable": check_ref_resolvable(raw_lines, lines, defs, str_rows),
        "marker-count": check_marker_count(raw_lines),
        "path-marker": check_path_marker(lines, defs, p.name),
    }
    findings = [f for label in LABELS for f in buckets[label]]
    checks = [{"label": label, "status": "fail" if buckets[label] else "pass",
               "count": len(buckets[label])} for label in LABELS]
    status = STATUS_ERROR if any(f.severity == "error" for f in findings) else STATUS_OK
    return status, findings, checks, scanned


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

def main(argv=None) -> int:
    _sig_guard(argv, declared=['--json'])  # answer --version / reject an undeclared option
    parser = argparse.ArgumentParser(
        prog="validate-requirements.py",
        description="Judge the structural propositions of a requirements.md artifact.",
    )
    _sig_configure(parser)

    parser.add_argument("path", help="the requirements.md to check")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    try:
        status, findings, checks, scanned = validate(args.path)
    except DomainUnavailable as absent:
        # FR-012 / FR-013: the value domain this run would judge against is a declaration and the
        # layer is unreadable, so the verdict is an input error carrying the absent label — free
        # text, not a seventh label, and never a green result.
        print(absent.label, file=sys.stderr)
        print("validate-requirements: refusing to judge the `path-marker` rule against an absent "
              "closed set (declaration layer unreadable)", file=sys.stderr)
        return EXIT_INPUT
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")

    if args.json:
        print(json.dumps({
            "file": str(Path(args.path)),
            "status": status,
            "checks": checks,
            "errors": errors,
            "warnings": warnings,
            "scanned": scanned,
        }, ensure_ascii=False, indent=2))
    else:
        print("file: %s" % args.path)
        print("status: %s" % status)
        for c in checks:
            print("  [%s] %s (%d)" % (c["label"], c["status"], c["count"]))
        print("scanned: %d lines, %d definition rows, %d shared strings"
              % (scanned["lines"], scanned["definition_rows"], scanned["shared_strings"]))
        for f in findings:
            print(f.render())
        print("%d error(s), %d warning(s)" % (errors, warnings))

    if status in (STATUS_MISSING, STATUS_UNPARSABLE, STATUS_EMPTY):
        return EXIT_INPUT
    return EXIT_ERROR if errors else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
