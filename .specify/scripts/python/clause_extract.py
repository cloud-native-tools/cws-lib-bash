#!/usr/bin/env python3
"""clause_extract.py — read-only extractor for contract clause syntax.

Program-First (程序优先): the clause-form rules are fixed, textual and decidable, so they
live here as a program rather than as prose an agent re-derives per run. The single source
of truth for WHAT the rules are is `.specify/shared/definitions/contract-clause-definitions.md`
(条款语法 owner); this module is its executable counterpart and MUST NOT grow a second,
divergent reading of any rule.

It owns no verdicts: it reports forms, ids, block bodies and citation groups, and leaves
"covered / uncovered" to `account-clause-coverage.py` and "resolvable claim" to
`validate-tasks.py`.

Functions (the same `^  name  description` shape the house docstring convention uses):
  form_of            classify one contract file into exactly one of the six owner forms
  md_forms_hit       which of the three positive Markdown forms match (mutual-exclusion probe)
  extract_clauses    clause ids in document order
  clause_blocks      (id, body) pairs, body bounded per owner doc § 4.1
  parentheticals     well-formed balanced groups (ASCII + full-width, same-width nesting)
  malformed_parentheticals  cross-width / unpaired spans — reported, never cited
  clause_citations   id -> set of FR ids from that clause's citation group (owner doc § 4.2)
  resolvable         whether a clause id exists in a given contract file
  unparseable_names  files that yield no clause id — named, never silently counted as covered

Read-only by contract (FR-005): this module opens files for reading only and has no write
point of any kind. Stdlib only — no PyYAML (plan D-2); the hand-parse precedent in this repo
is `.specify/scripts/python/gate-check.py`'s own gate-file reader.

Usage: python3 clause_extract.py <contract-file> [<contract-file> ...]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

FORMS = (
    "md-bold-closed",
    "md-bold-paren",
    "md-heading",
    "yaml-openapi",
    "yaml-assertions",
    "md-none",
)

CLOSED_RE = re.compile(r"\*\*C-\d+(?:\.\d+)*\*\*")
OPEN_BOLD_RE = re.compile(r"\*\*C-\d+")
HEADING_RE = re.compile(r"^#{1,6}\s+C-\d+", re.M)
HEADING_LINE_RE = re.compile(r"^#{1,6}\s")
LIST_PREFIX = r"^\s*(?:[-*+]\s+)?"
MARKER_CLOSED_RE = re.compile(LIST_PREFIX + r"\*\*(C-\d+(?:\.\d+)*)\*\*")
MARKER_OPEN_RE = re.compile(LIST_PREFIX + r"\*\*(C-\d+(?:\.\d+)*)")
MARKER_HEADING_RE = re.compile(r"^#{1,6}\s+(C-\d+(?:\.\d+)*)")
# A clause may also be declared as the FIRST cell of a Markdown table row. An id in any
# other cell is a cross-reference to another contract's clause, not a declaration.
MARKER_TABLE_RE = re.compile(r"^\s*\|\s*\*\*(C-\d+(?:\.\d+)*)\*\*\s*\|")
METHOD_KEY_RE = re.compile(r"^\s{4}(?:get|post|put|delete|patch|head|options):\s*$", re.M)
ASSERTION_ID_RE = re.compile(r"^\s+-\s+id:\s*(\S+)", re.M)
FR_SC_IN_GROUP_RE = re.compile(r"(?:FR|SC)-\d")
FR_RANGE_RE = re.compile(r"FR-0*(\d{1,3})(?:…|\.\.\.|-)FR-0*(\d{1,3})")
FR_SINGLE_RE = re.compile(r"FR-0*(\d{1,3})")

YAML_SUFFIXES = (".yaml", ".yml")


# --------------------------------------------------------------------------- #
# text helpers
# --------------------------------------------------------------------------- #

def _read(path) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def strip_fences(lines):
    """Blank out every line inside a ``` fence (the fence lines themselves included)."""
    out = []
    inside = False
    for line in lines:
        if line.lstrip().startswith("```"):
            inside = not inside
            out.append("")
            continue
        out.append("" if inside else line)
    return out


def strip_code_spans(text: str) -> str:
    """Drop the CONTENT of each balanced inline code span, per CommonMark: a span opens with
    a run of N backticks and closes at the next run of exactly N. An unclosed run is literal.

    Parsing by single-backtick parity inverts after an inline fence marker, which is how a
    real trailing citation once got swallowed and an FR showed zero coverage.
    """
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "`":
            out.append(text[i])
            i += 1
            continue
        j = i
        while j < n and text[j] == "`":
            j += 1
        run = j - i
        k = j
        close = -1
        while k < n:
            if text[k] == "`":
                m = k
                while m < n and text[m] == "`":
                    m += 1
                if m - k == run:
                    close = k
                    break
                k = m
            else:
                k += 1
        if close < 0:
            out.append(text[i:j])
            i = j
        else:
            i = close + run
    return "".join(out)


OPEN_DELIMITERS = {"(": ")", "（": "）"}
CLOSE_DELIMITERS = {")": "(", "）": "（"}


def _without_spans(text: str, start: int, end: int, spans):
    """The slice text[start:end] with every malformed span fully inside it removed."""
    cut = []
    for s, e in spans:
        if s >= start and e <= end:
            cut.append((s, e))
    if not cut:
        return text[start:end]
    out = []
    cursor = start
    for s, e in sorted(cut):
        if s < cursor:
            continue
        out.append(text[cursor:s])
        cursor = e
    out.append(text[cursor:end])
    return "".join(out)


def _scan_parentheticals(text: str):
    """(well-formed group contents, malformed raw spans).

    Delimiter set and rules are owned by `.specify/shared/definitions/contract-clause-definitions.md`
    § 4 rule 2: an opener is `(` or `（`, its closer is `)` or `）`, nesting MUST match
    within one width, and a cross-width pairing or an unpaired delimiter is a malformed
    group reported here — never a citation, never a mention. Only the outermost balanced
    group is emitted (the existing one-level-nesting semantics).
    """
    groups = []
    malformed_spans = []
    stack = []  # (opener char, index)
    for i, ch in enumerate(text):
        if ch in OPEN_DELIMITERS:
            stack.append((ch, i))
            continue
        if ch not in CLOSE_DELIMITERS:
            continue
        if not stack:
            malformed_spans.append((i, i + 1))
            continue
        opener, start = stack[-1]
        if OPEN_DELIMITERS[opener] != ch:
            # cross-width pairing: the span is malformed as a whole
            stack.pop()
            malformed_spans.append((start, i + 1))
            continue
        stack.pop()
        if not stack:
            groups.append(_without_spans(text, start + 1, i, malformed_spans))
    if stack:
        # every opener still on the stack is unpaired; the outermost span is one malformed
        # group (inner unmatched openers are part of that same span)
        malformed_spans.append((stack[0][1], len(text)))
        stack.clear()
    return groups, [text[s:e] for s, e in malformed_spans]


def parentheticals(text: str):
    """Well-formed balanced parenthetical groups, tolerating one nesting level.

    Accepts both delimiter widths (owner doc § 4 rule 2). A cross-width or unpaired
    delimiter is malformed and is reported by `malformed_parentheticals()` instead.
    """
    return _scan_parentheticals(text)[0]


def malformed_parentheticals(text: str):
    """Raw spans of malformed groups (cross-width pairing or unpaired delimiter).

    Owner doc § 4 rule 2: a malformed group is its own outcome — never a citation and
    never a mention.
    """
    return _scan_parentheticals(text)[1]


# --------------------------------------------------------------------------- #
# form detection
# --------------------------------------------------------------------------- #

def md_forms_hit(path):
    """Which of the three positive Markdown forms match this file (mutual-exclusion probe)."""
    text = _read(path)
    hits = []
    closed = bool(CLOSED_RE.search(text))
    if closed:
        hits.append("md-bold-closed")
    elif OPEN_BOLD_RE.search(text):
        hits.append("md-bold-paren")
    if HEADING_RE.search(text):
        hits.append("md-heading")
    return hits


def form_of(path) -> str:
    p = Path(path)
    text = _read(p)
    if p.suffix.lower() in YAML_SUFFIXES:
        if "openapi:" in text and "paths:" in text:
            return "yaml-openapi"
        if ASSERTION_ID_RE.search(text):
            return "yaml-assertions"
        return "yaml-assertions" if "- id:" in text else "md-none"
    hits = md_forms_hit(p)
    if "md-bold-closed" in hits:
        return "md-bold-closed"
    if "md-bold-paren" in hits:
        return "md-bold-paren"
    if "md-heading" in hits:
        return "md-heading"
    return "md-none"


# --------------------------------------------------------------------------- #
# extraction
# --------------------------------------------------------------------------- #

def clause_blocks(path):
    """(clause_id, body) pairs. Body runs from the marker line to the next marker OR the next
    section heading, whichever comes first; fenced lines are excluded (owner doc § 4.1)."""
    p = Path(path)
    if p.suffix.lower() in YAML_SUFFIXES:
        return []
    lines = strip_fences(_read(p).split("\n"))
    form = form_of(p)
    if form == "md-heading":
        markers = (MARKER_HEADING_RE,)
    elif form == "md-bold-closed":
        markers = (MARKER_CLOSED_RE, MARKER_TABLE_RE)
    elif form == "md-bold-paren":
        markers = (MARKER_OPEN_RE,)
    else:
        return []

    def match_at(line):
        for rx in markers:
            m = rx.match(line)
            if m:
                return m, rx is MARKER_TABLE_RE
        return None, False

    starts = []
    for i, line in enumerate(lines):
        m, is_row = match_at(line)
        if m:
            starts.append((i, m.group(1), is_row))
    blocks = []
    for idx, (s, cid, is_row) in enumerate(starts):
        if is_row:
            blocks.append((cid, lines[s]))          # a table row is self-contained
            continue
        nxt = starts[idx + 1][0] if idx + 1 < len(starts) else len(lines)
        headings = [h for h in range(s + 1, nxt) if HEADING_LINE_RE.match(lines[h])]
        end = min(headings) if headings else nxt
        blocks.append((cid, "\n".join(lines[s:end])))
    return blocks


def extract_clauses(path):
    """Clause ids in document order (method keys for OpenAPI, `- id:` values for assertions)."""
    p = Path(path)
    text = _read(p)
    if p.suffix.lower() in YAML_SUFFIXES:
        if "openapi:" in text and "paths:" in text:
            return [m.group(0).strip().rstrip(":") for m in METHOD_KEY_RE.finditer(text)]
        return list(ASSERTION_ID_RE.findall(text))
    return [cid for cid, _ in clause_blocks(p)]


def clause_citations(path):
    """clause_id -> set of FR ids from that clause's citation group (owner doc § 4.2).

    The group is the LAST parenthetical in the block that contains an FR/SC id. Ids anywhere
    else in the block are mentions, not citations. Ranges expand; nested sub-item suffixes
    such as `(FR-018(a))` survive; inline code spans are stripped first.
    """
    cites = {}
    for cid, body in clause_blocks(path):
        clean = strip_code_spans(body)
        groups = [g for g in parentheticals(clean) if FR_SC_IN_GROUP_RE.search(g)]
        found = set()
        if groups:
            g = groups[-1]
            for a, b in FR_RANGE_RE.findall(g):
                lo, hi = sorted((int(a), int(b)))
                found.update("FR-%03d" % i for i in range(lo, hi + 1))
            plain = FR_RANGE_RE.sub("", g)
            for num in FR_SINGLE_RE.findall(plain):
                found.add("FR-%03d" % int(num))
        cites[cid] = found
    return cites


def resolvable(path, clause_id) -> bool:
    return clause_id in extract_clauses(path)


def unparseable_names(paths):
    """Names of files that yield no clause id — the named disposition (C-13/C-15/C-26).

    A file that contributes zero clauses is reported, never silently counted as covered;
    that is what keeps '0 because right' distinguishable from '0 because blind'.
    """
    return [Path(p).name for p in paths if not extract_clauses(p)]


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv) -> int:
    if not argv:
        print("usage: clause_extract.py <contract-file> [...]", file=sys.stderr)
        return 2
    for arg in argv:
        p = Path(arg)
        if not p.is_file():
            print("%s: not a file" % arg, file=sys.stderr)
            return 2
        ids = extract_clauses(p)
        print("%s\tform=%s\tclauses=%d" % (p.name, form_of(p), len(ids)))
        for cid in ids:
            print("  %s" % cid)
        for name in unparseable_names([p]):
            print("  UNPARSABLE-NAMED: %s" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
