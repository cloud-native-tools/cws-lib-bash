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

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INPUT = 2

STATUS_OK = "ok"
STATUS_ERROR = "error"
STATUS_MISSING = "missing"
STATUS_UNPARSABLE = "unparsable"
STATUS_EMPTY = "empty"
STATUS_SKELETON = "skeleton"

LABELS = ("id-contiguous", "doc-order", "ref-resolvable", "marker-count", "dup-id")

DEFINITION_RE = re.compile(r"^- \*\*(FR|SC)-(\d+)([a-z]?)\*\*")
STR_ROW_RE = re.compile(r"^\|\s*`(STR-\d+)`\s*\|")
STR_REF_RE = re.compile(r"\[\[(STR-\d+)\]\]")
FR_MENTION_RE = re.compile(r"\bFR-(\d{1,3})\b")
SC_MENTION_RE = re.compile(r"\bSC-(\d{1,3})\b")
MARKER_RE = re.compile(r"(?<!`)\[NEEDS CLARIFICATION:")
PLACEHOLDER_RE = re.compile(r"\[(?!NEEDS)[A-Z][A-Z_ ]{3,}\]|\[placeholder\]")
CLARIFICATIONS_HEADING_RE = re.compile(r"^##\s+Clarifications")
HEADING_RE = re.compile(r"^#{1,6}\s")


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
    }
    findings = [f for label in LABELS for f in buckets[label]]
    checks = [{"label": label, "status": "fail" if buckets[label] else "pass",
               "count": len(buckets[label])} for label in LABELS]
    status = STATUS_ERROR if any(f.severity == "error" for f in findings) else STATUS_OK
    return status, findings, checks, scanned


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="validate-requirements.py",
        description="Judge the structural propositions of a requirements.md artifact.",
    )
    parser.add_argument("path", help="the requirements.md to check")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    status, findings, checks, scanned = validate(args.path)
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
