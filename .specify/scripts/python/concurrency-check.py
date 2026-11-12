#!/usr/bin/env python3
"""The concurrency judgement engine (feature 093-concurrency-by-default).

The one program that turns the concurrency declaration facts into verdicts. It is
read-only over the repository, standard-library only, and writes nothing except the
file named by ``--json-out``.

Contracts this engine implements (clause ids are owned by
``.specify/specs/093-concurrency-by-default/contracts/judgement-engine.contract.md``):

* C-019 — ``-h`` / ``--help`` and ``--version`` answer without acting; an undeclared
  option exits 2 before any action; the exit taxonomy is exactly 0 = pass,
  1 = a documented check failed, 2 = input or environment error.
* C-020 — exactly five read-only actions: ``classify`` / ``serial-reason`` /
  ``reading`` / ``coverage`` / ``capability``.
* C-021 — every action accepts ``--repo <root>`` (default resolved from this file's
  own location, never an ancestor walk) and ``--json-out <file>`` (the only write);
  the three record-judging actions require ``--record <file>`` and an action invoked
  without its record flag exits 2.
* C-022 — every action emits the JSON envelope ``action`` / ``decision`` /
  ``findings`` / ``measured`` / ``checked_at``; a ``not-applicable`` decision is
  distinguishable from ``pass``.

The facts are read through ``.specify/scripts/python/declaration_reader.py`` (the single
declaration read entry); no class name, root pattern, code vocabulary or threshold is
carried in this file as a second definition.

Usage:
  python3 .specify/scripts/python/concurrency-check.py <action> [options]

  actions:
    classify       map execution bodies to their declared class (needs no record)
    serial-reason  judge one serial-reason record (needs --record)
    reading        judge one concurrency reading record (needs --record)
    coverage       judge per-stage decomposition coverage and goal-target partitions
    capability     judge dispatch capability and the coordinator verdict (needs --record)

  options:
    --repo PATH        repository root whose .specify/shared/declarations/ is read
                       (default: resolved from this script's own location)
    --record PATH      the record to judge (serial-reason / reading / capability)
    --json-out PATH    write the judgement envelope here (the only write)
    --stage NAME       coverage: judge one stage from decomposition-coverage.yaml
    --goal SLUG        coverage: judge one goal's target partition
    --ceiling N        reading/coverage: the slot cap ceiling at call time
                       (default: read from wp-gate.py's declared default)

Exit codes:
  0  the judgement passed
  1  a documented check failed (decision ``fail``)
  2  input or environment error, or no owner verdict readable
     (decision ``owner-unavailable`` / ``not-applicable``)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_NAME = "concurrency-check.py"

#: C-020's closed action set. A sixth action MUST NOT be added without a clause revision.
ACTIONS = ("classify", "serial-reason", "reading", "coverage", "capability")

#: The three record-judging actions (C-021). The other two take no record flag.
RECORD_ACTIONS = ("serial-reason", "reading", "capability")

#: E-4's closed pattern domain (data-model.md). Two literals, because the pattern is a
#: record field, not a declaration-layer value.
PATTERNS = ("concurrent", "serial")

#: Tool names that constitute a dispatch tool (FR-021(a), [[STR-004]]). The concept's
#: definition owner is ``.specify/shared/definitions/subagent-definitions.md``; this set is the
#: engine's executable spelling of the host tool names that create sibling executors.
DISPATCH_TOOLS = frozenset({"agent", "task", "subagent", "dispatch", "spawn_agent"})

#: Marker words an explicit handoff declaration carries (FR-021(b)); matched
#: case-insensitively in the body text.
HANDOFF_MARKERS = ("handoff", "hands off", "hand-off", "移交派发", "移交")

#: Marker words an external-process declaration carries (FR-021(c) / C-094).
EXTERNAL_PROCESS_MARKERS = (
    "external-process", "external process", "subprocess", "child process",
    "外部进程", "子进程", "stage-runner",
)


# --------------------------------------------------------------------------- #
# the script-interface helper (C-019 / Constitution XXI)
# --------------------------------------------------------------------------- #
_SIG_DIR = str(Path(__file__).resolve().parent)
if _SIG_DIR not in sys.path:
    sys.path.insert(0, _SIG_DIR)
try:  # the helper owns the rule; a sandbox copy without it still runs the actions
    from script_interface_cli import configure_parser as _sig_configure
    from script_interface_cli import guard_argv as _sig_guard
except ImportError:  # pragma: no cover - a handler copy carries the engine but not the helper
    def _sig_configure(parser, **_kwargs):
        return parser

    def _sig_guard(_argv=None, declared=None, **_kwargs):
        return None

# --------------------------------------------------------------------------- #
# the declaration read entry (the single fact reader)
# --------------------------------------------------------------------------- #
try:
    import declaration_reader
except ImportError:  # pragma: no cover - defensive; the sibling always ships together
    declaration_reader = None


class EngineInputError(Exception):
    """An input or environment error (exit 2) with a stable code for the envelope."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


# --------------------------------------------------------------------------- #
# repository resolution (C-021 / T023 — never an ancestor walk)
# --------------------------------------------------------------------------- #
def default_repo():
    """The repository root derived from this engine's own location.

    Framework source form: ``<root>/scripts/python/concurrency-check.py``.
    Mirror form: ``<root>/.specify/scripts/python/concurrency-check.py`` — the literal
    ``.specify`` component directly above ``.specify/scripts/`` is stripped. This is the
    F-093-002 path trap's required shape: a worktree that itself lives under
    ``.specify/.tmp/...`` still resolves to the worktree root, because the component
    below ``.specify/scripts/`` is what is read, never the first ``.specify`` anywhere above.
    """
    parts = Path(__file__).resolve().parts
    if len(parts) >= 3 and parts[-3:-1] == ("scripts", "python"):
        root = Path(*parts[:-3])
        if root.name == ".specify":
            root = root.parent
        return root
    return Path(__file__).resolve().parent


def resolve_repo(value):
    """The ``--repo`` root as given (never walked), or the derived default."""
    root = Path(value) if value else default_repo()
    root = root.resolve()
    if not root.is_dir():
        raise EngineInputError("repo-unavailable", "repo root does not exist: %s" % root)
    return root


# --------------------------------------------------------------------------- #
# fact loading
# --------------------------------------------------------------------------- #
def load_fact(repo, slug):
    """One fact body through the declaration reader; absence is the typed exit-2 case."""
    if declaration_reader is None:
        raise EngineInputError("declaration-reader-unavailable",
                               "declaration_reader.py is not importable beside this engine")
    try:
        return declaration_reader.load_fact(repo, slug)["body"]
    except declaration_reader.DeclarationError as error:
        raise EngineInputError("owner-unavailable", str(error))


def fact_statement(body, slug):
    statement = body.get("statement")
    if not isinstance(statement, dict):
        raise EngineInputError(
            "owner-unavailable", "fact %r carries no readable statement mapping" % slug)
    return statement


def load_record(path):
    """Parse a record through the same block subset the declaration layer accepts (T109).

    A run cannot smuggle a shape the declaration layer would reject: the record is
    parsed by ``declaration_reader.parse_subset``, the single subset implementation.
    """
    if declaration_reader is None:
        raise EngineInputError("declaration-reader-unavailable",
                               "declaration_reader.py is not importable beside this engine")
    if not path:
        raise EngineInputError("record-required", "--record is required for this action")
    record_path = Path(path)
    try:
        text = record_path.read_text(encoding="utf-8")
    except OSError as error:
        raise EngineInputError(
            "record-unreadable", "cannot read record %s (%s)" % (path, error.strerror or error))
    try:
        body = declaration_reader.parse_subset(text, str(record_path))
    except declaration_reader.DeclarationError as error:
        raise EngineInputError("record-outside-subset", str(error))
    if not isinstance(body, dict):
        raise EngineInputError(
            "record-malformed",
            "record %s must be a block mapping (block-subset/v1), got %s"
            % (path, type(body).__name__))
    return body


# --------------------------------------------------------------------------- #
# the judgement envelope (C-022)
# --------------------------------------------------------------------------- #
def finding(code, subject, message, evidence_ptr="", **detail):
    """One finding: the four mandatory fields plus optional comparison detail (T097)."""
    item = {
        "code": code,
        "subject": subject,
        "message": message,
        "evidence_ptr": evidence_ptr,
    }
    item.update(detail)
    return item


def envelope(action, decision, findings, measured, **extra):
    """The stable envelope C-022 fixes. ``checked_at`` is ISO-8601 UTC."""
    body = {
        "action": action,
        "decision": decision,
        "findings": findings,
        "measured": measured,
        "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    body.update(extra)
    return body


def emit(envelope_body, json_out):
    """Write the envelope to ``--json-out`` (the only write) or print it to stdout."""
    text = json.dumps(envelope_body, ensure_ascii=False, indent=2, sort_keys=True)
    if json_out:
        out = Path(json_out)
        try:
            out.write_text(text + "\n", encoding="utf-8")
        except OSError as error:
            raise EngineInputError(
                "json-out-unwritable",
                "cannot write --json-out %s (%s)" % (out, error.strerror or error))
        print("%s: decision=%s findings=%d -> %s"
              % (envelope_body["action"], envelope_body["decision"],
                 len(envelope_body["findings"]), out))
    else:
        print(text)


def decision_exit(decision):
    """The exit taxonomy (C-019): pass 0, fail 1, owner-unavailable / input 2."""
    if decision == "pass":
        return 0
    if decision == "fail":
        return 1
    return 2


# --------------------------------------------------------------------------- #
# actions (stubs until each row group lands; the dispatch table itself is C-020)
# --------------------------------------------------------------------------- #
def _not_implemented(action):
    return envelope(
        action, "fail",
        [finding("not-implemented", action, "action %r is not implemented yet" % action)],
        {})


# --------------------------------------------------------------------------- #
# enumeration and body reading (classify)
# --------------------------------------------------------------------------- #
def expand_braces(pattern):
    """Expand ``{a,b}`` alternatives in a declaration pattern (one level, nested-safe)."""
    match = re.search(r"\{([^{}]+)\}", pattern)
    if not match:
        return [pattern]
    expanded = []
    for option in match.group(1).split(","):
        expanded.extend(
            expand_braces(pattern[:match.start()] + option.strip() + pattern[match.end():]))
    return expanded


def expand_root_pattern(pattern):
    """``[(base, selector)]`` for one declaration pattern.

    The roots fact declares PATH PATTERNS, never counts (V-4). Two placeholder forms
    occur: ``<name>/`` (a directory child) and ``<stem>.md`` (a file-glob child); a
    literal ``*`` segment is a glob as written. The engine expands whatever the fact
    says and hard-codes no root path.
    """
    selectors = []
    for alternative in expand_braces(str(pattern).strip()):
        alternative = alternative.rstrip("/")
        placeholder = re.search(r"<[^>]+>", alternative)
        if placeholder:
            head = alternative[:placeholder.start()].rstrip("/")
            rest = alternative[placeholder.end():]
            if not rest:
                selectors.append((head or ".", "dir"))
            else:
                selectors.append((head or ".", "*" + rest))
            continue
        base, _, last = alternative.rpartition("/")
        selectors.append((base or ".", last))
    return selectors


def enumerate_root(repo, root):
    """Enumerate one root's members: ``[(relative-path, is_dir, base)]``, sorted."""
    members = []
    exclusions = [str(layer).strip().rstrip("/")
                  for layer in (root.get("excluded_layers") or [])]
    for base, selector in expand_root_pattern(root.get("pattern", "")):
        base_path = repo / base
        if not base_path.is_dir():
            continue
        if selector == "dir":
            candidates = sorted(p for p in base_path.iterdir() if p.is_dir())
        else:
            candidates = sorted(p for p in base_path.glob(selector) if p.is_file())
        for path in candidates:
            if path.name.startswith(".") or path.name == "__pycache__":
                continue
            rel = path.relative_to(repo).as_posix()
            if any(rel == layer or rel.startswith(layer + "/") for layer in exclusions):
                continue
            members.append((rel, path.is_dir(), base))
    return sorted(members)


def read_body_text(repo, rel, is_dir):
    """The body's own text: the file itself, or every markdown file of a directory member."""
    path = repo / rel
    try:
        if not is_dir:
            return path.read_text(encoding="utf-8")
        chunks = []
        for markdown in sorted(path.rglob("*.md")):
            chunks.append(markdown.read_text(encoding="utf-8"))
        return "\n".join(chunks)
    except (OSError, UnicodeDecodeError) as error:
        raise EngineInputError(
            "body-unreadable", "cannot read body %s (%s)" % (rel, error))


def frontmatter_value(text, key):
    """One scalar from the leading ``---`` frontmatter block, or ``None``."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        head, sep, value = line.partition(":")
        if sep and head.strip() == key:
            return value.strip().strip("\"'")
    return None


def resolve_anchor(repo, anchor):
    """``(path, fragment, resolved, detail)`` for a class ``owner_anchor`` value.

    A file path or a ``path#fragment`` pair. Resolution: the file exists (framework
    source form first, then its ``.specify/`` projection) and, when a fragment is
    given, a heading line carries it (``# class-<fragment>``-style section) or an
    explicit ``{#<fragment>}`` / ``id="<fragment>"`` marker does. An unresolvable
    anchor is reported, never assumed to hold the obligation.
    """
    text = str(anchor or "").strip()
    if not text:
        return "", "", False, "no owner_anchor declared"
    path_text, _, fragment = text.partition("#")
    candidates = [repo / path_text]
    if path_text.startswith(".specify/"):
        candidates.append(repo / path_text[len(".specify/"):])
    else:
        candidates.append(repo / ".specify" / path_text)
    target = next((c for c in candidates if c.is_file()), None)
    if target is None:
        return path_text, fragment, False, "anchor file does not resolve: %s" % path_text
    if not fragment:
        return path_text, fragment, True, "anchor file resolves"
    try:
        anchor_text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return path_text, fragment, False, "anchor file unreadable: %s" % path_text
    heading = re.compile(r"^#{1,6}\s+.*%s.*$" % re.escape(fragment), re.MULTILINE)
    marker = re.compile(r"(\{#%s\}|id=[\"']%s[\"'])" % (re.escape(fragment), re.escape(fragment)))
    if heading.search(anchor_text):
        return path_text, fragment, True, "anchor heading resolves: #%s" % fragment
    if marker.search(anchor_text):
        return path_text, fragment, True, "anchor marker resolves: #%s" % fragment
    return path_text, fragment, False, "anchor section #%s not found in %s" % (fragment, path_text)


def resolve_body_class(root_id, body_text, rule_rows, class_names):
    """SM-3's class resolution for one body under one root.

    Returns ``(class_name, finding_code, detail)``. A single decision-rule row for the
    root assigns its class. Multiple rows require the body's declared produced shape
    (frontmatter ``produced-shape``); the shape must select exactly one row, else the
    body is ``uncovered`` (undecidable) or ``ambiguous`` (two class members). No rule
    row is ``uncovered``. Nothing falls into a catch-all member (C-024).
    """
    rows = [row for row in rule_rows if str(row.get("root_id", "")).strip() == root_id]
    if not rows:
        return None, "uncovered", "no decision-rule row for root %r" % root_id
    if len(rows) == 1:
        name = str(rows[0].get("class", "")).strip()
        if name not in class_names:
            return None, "class-unknown", "rule names class %r absent from the class table" % name
        return name, None, "single decision-rule row"
    shape = frontmatter_value(body_text, "produced-shape") or frontmatter_value(
        body_text, "produced_shape")
    if not shape:
        return None, "uncovered", (
            "%d decision-rule rows for root %r and no readable produced-shape" % (len(rows), root_id))
    matching = [row for row in rows
                if str(row.get("produced_shape", "")).strip() == shape]
    if len(matching) == 1:
        name = str(matching[0].get("class", "")).strip()
        if name not in class_names:
            return None, "class-unknown", "rule names class %r absent from the class table" % name
        return name, None, "produced shape %r selects one row" % shape
    if len(matching) > 1:
        names = [str(row.get("class", "")).strip() for row in matching]
        return None, "ambiguous", (
            "produced shape %r matches %d class members: %s" % (shape, len(matching), names))
    return None, "uncovered", "produced shape %r matches no decision-rule row" % shape


def action_classify(repo, args):
    """C-023…C-026: enumerate the five roots and judge every body's class and obligation."""
    roots_statement = fact_statement(load_fact(repo, "executor-enumeration-roots"),
                                     "executor-enumeration-roots")
    class_statement = fact_statement(load_fact(repo, "concurrency-class"),
                                     "concurrency-class")
    classes = class_statement.get("classes") or []
    class_names = {str(c.get("name", "")).strip() for c in classes if isinstance(c, dict)}
    class_table = {str(c.get("name", "")).strip(): c for c in classes if isinstance(c, dict)}
    rule_rows = class_statement.get("decision_rule") or []
    roots = roots_statement.get("roots") or []

    findings = []
    root_id_set = {str(root.get("root_id", "")).strip()
                   for root in roots if isinstance(root, dict)}
    root_id_set.discard("")
    class_root_set = set()
    for entry in classes:
        if not isinstance(entry, dict):
            continue
        for root_id in entry.get("applies_to") or []:
            class_root_set.add(str(root_id).strip())
    # C-015's drift guard must survive a silent enumeration change: the class table's
    # applies_to surface and the decision rule are independent readers of the root set,
    # so a dropped root — or a rule naming a class outside the member set — is red even
    # when the enumeration yields no body to exercise it.
    for root_id in sorted(root_id_set - class_root_set):
        findings.append(finding(
            "uncovered", "roots",
            "root %r carries no class applies_to entry: the class table and the roots "
            "fact disagree" % root_id,
            ".specify/shared/declarations/facts/executor-enumeration-roots.yaml",
            compared=[sorted(root_id_set), sorted(class_root_set)]))
    for root_id in sorted(class_root_set - root_id_set):
        findings.append(finding(
            "uncovered", "roots",
            "the class table applies to root %r which the roots fact does not declare"
            % root_id, ".specify/shared/declarations/facts/executor-enumeration-roots.yaml",
            compared=[sorted(class_root_set), sorted(root_id_set)]))
    for row in rule_rows:
        if not isinstance(row, dict):
            continue
        row_class = str(row.get("class", "")).strip()
        row_root = str(row.get("root_id", "")).strip()
        if row_class and row_class not in class_names:
            findings.append(finding(
                "class-unknown", "decision-rule",
                "the decision rule names class %r, absent from the closed class table %s"
                % (row_class, sorted(class_names)),
                ".specify/shared/declarations/facts/concurrency-class.yaml",
                compared=[row_class, sorted(class_names)]))
        if row_root and row_root not in root_id_set:
            findings.append(finding(
                "uncovered", "decision-rule",
                "the decision rule names root %r, absent from the enumeration roots %s"
                % (row_root, sorted(root_id_set)),
                ".specify/shared/declarations/facts/executor-enumeration-roots.yaml",
                compared=[row_root, sorted(root_id_set)]))
    measured_roots = {}
    measured_bodies = []
    for root in roots:
        if not isinstance(root, dict):
            continue
        root_id = str(root.get("root_id", "")).strip()
        members = enumerate_root(repo, root)
        by_base = {}
        for rel, _is_dir, base in members:
            by_base[base] = by_base.get(base, 0) + 1
        measured_roots[root_id] = {
            "pattern": str(root.get("pattern", "")),
            "member_count": len(members),
            "by_base": by_base,
            "member_ids": [rel for rel, _d, _b in members],
        }
        applies = [str(c.get("name", "")).strip() for c in classes
                   if isinstance(c, dict) and root_id in (c.get("applies_to") or [])]
        for rel, is_dir, _base in members:
            body_text = read_body_text(repo, rel, is_dir)
            name, problem, detail = resolve_body_class(
                root_id, body_text, rule_rows, class_names)
            body_id = "%s/%s" % (root_id, rel)
            record = {"unit": body_id, "path": rel, "root": root_id,
                      "class": name, "resolution": detail}
            if problem:
                findings.append(finding(
                    problem, body_id, detail, rel,
                    compared=[applies, [str(r.get("class", "")) for r in rule_rows
                                        if str(r.get("root_id", "")) == root_id]]))
                measured_bodies.append(record)
                continue
            if applies and name not in applies:
                findings.append(finding(
                    "class-disagreement", body_id,
                    "applies_to %s and the decision rule %r disagree" % (applies, name),
                    rel, compared=[applies, name]))
            # obligation presence (C-025): the body's own text or the class's owner anchor
            entry = class_table.get(name, {})
            anchor = str(entry.get("owner_anchor", ""))
            anchor_path, fragment, anchor_ok, anchor_detail = resolve_anchor(repo, anchor)
            tokens = [name, anchor, anchor_path,
                      fragment and "#" + fragment, fragment]
            in_body = any(token and token in body_text for token in tokens)
            source = ("both" if (in_body and anchor_ok) else
                      "body-text" if in_body else
                      "owner-anchor" if anchor_ok else "none")
            record.update({
                "obligation": {
                    "class_obligation": str(entry.get("obligation", "")),
                    "in_body": in_body,
                    "anchor_resolves": anchor_ok,
                    "anchor": anchor,
                    "anchor_detail": anchor_detail,
                    "source": source,
                }
            })
            if source == "none":
                findings.append(finding(
                    "obligation-missing", body_id,
                    "class %r obligation is readable neither in the body nor at %r (%s)"
                    % (name, anchor, anchor_detail), rel,
                    compared=[name, anchor]))
            measured_bodies.append(record)

    if not roots:
        findings.append(finding("uncovered", "roots", "the roots fact declares no roots"))
    decision = "fail" if findings else "pass"
    measured = {
        "roots": measured_roots,
        "root_counts": {root_id: values["member_count"]
                        for root_id, values in measured_roots.items()},
        "total_bodies": sum(r["member_count"] for r in measured_roots.values()),
        "bodies": measured_bodies,
    }
    return envelope("classify", decision, findings, measured)


# --------------------------------------------------------------------------- #
# serial-reason judgement (C-027…C-030, T051–T056)
# --------------------------------------------------------------------------- #
#: The simplicity / controllability / history family FR-009 forbids as a serial reason.
SIMPLICITY_FAMILY = re.compile(
    r"(simpl|简单|controllable|可控|histor|历史上|clean|cleanliness|speed|faster|更快|速度)",
    re.IGNORECASE)


def resolves_in(repo, value):
    """Whether a recorded pointer names a file inside the repository (source or mirror)."""
    text = str(value or "").strip()
    if not text or text == ".":
        return False
    candidates = [repo / text]
    if text.startswith(".specify/"):
        candidates.append(repo / text[len(".specify/"):])
    else:
        candidates.append(repo / ".specify" / text)
    return any(candidate.is_file() for candidate in candidates)


def numeric_reading(value):
    """A slot/budget reading as an int, or ``None`` when the value is not one."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and re.fullmatch(r"-?\d+", value.strip()):
        return int(value.strip())
    return None


def judge_evidence(repo, code_entry, evidence):
    """C-029: one code's evidence judged against its own declared form.

    Returns ``None`` when the evidence matches, or ``(reason, detail)`` when it does
    not. A bare string (including ``.``) never satisfies any form.
    """
    form = str(code_entry.get("evidence_form", "")).strip()
    if not isinstance(evidence, dict):
        return "evidence-form-mismatch", (
            "evidence for %r must be a structured reading of form %r, not a bare value"
            % (code_entry.get("code"), form))
    if form == "dependency-edge":
        predecessor = str(evidence.get("predecessor_id")
                          or evidence.get("predecessor") or "").strip()
        verdict_ptr = evidence.get("verdict_ptr")
        if not predecessor:
            return "evidence-form-mismatch", (
                "dependency-edge needs a resolvable predecessor unit id")
        if not resolves_in(repo, verdict_ptr):
            return "evidence-form-mismatch", (
                "dependency-edge needs a completion verdict pointer that resolves "
                "(got %r)" % verdict_ptr)
        return None
    if form == "write-conflict":
        paths = evidence.get("paths")
        if not isinstance(paths, list) or not paths:
            return "evidence-form-mismatch", (
                "write-conflict needs the intersecting file-level path set")
        for entry in paths:
            text = str(entry).strip()
            last = text.rstrip("/").rsplit("/", 1)[-1]
            if text.endswith("/") or "." not in last or not resolves_in(repo, text):
                return "evidence-form-mismatch", (
                    "write-conflict paths are resolving file-level paths (got %r)"
                    % entry)
        return None
    if form == "host-probe":
        probe = str(evidence.get("probe", "")).strip()
        landing = evidence.get("landing")
        if not probe:
            return "evidence-form-mismatch", "host-probe needs the probe reading"
        if not resolves_in(repo, landing):
            return "evidence-form-mismatch", (
                "host-probe needs its landing point to resolve (got %r)" % landing)
        return None
    if form == "budget-readings":
        for side in ("before", "after"):
            reading = evidence.get(side)
            if not isinstance(reading, dict):
                return "evidence-form-mismatch", (
                    "budget-reserve needs %s/after slot and budget readings" % side)
            if numeric_reading(reading.get("slots")) is None or \
                    numeric_reading(reading.get("budget")) is None:
                return "evidence-form-mismatch", (
                    "budget-reserve needs numeric slots and budget in the %s reading" % side)
        return None
    if form == "unit-set":
        units = evidence.get("units")
        if not isinstance(units, list) or len(units) > 1:
            return "evidence-form-mismatch", (
                "a factual code needs the enumerated representable unit set (size 0 or 1)")
        extra = str(code_entry.get("evidence_extra_field", "")).strip()
        if extra and not str(evidence.get(extra, "")).strip():
            return "evidence-form-mismatch", (
                "%s needs the declared extra evidence field %r"
                % (code_entry.get("code"), extra))
        return None
    return "evidence-form-mismatch", "no judgeable evidence form %r" % form


def action_serial_reason(repo, args):
    """C-027…C-030: validate one serial-reason record against the closed vocabulary."""
    statement = fact_statement(load_fact(repo, "serial-reason"), "serial-reason")
    catalogue = [entry for entry in (statement.get("codes") or []) if isinstance(entry, dict)]
    by_code = {str(entry.get("code", "")).strip(): entry for entry in catalogue}
    declared_order = [str(entry.get("code", "")).strip() for entry in catalogue]
    condition_index = [str(c).strip() for c in (statement.get("condition_index") or [])]

    record = load_record(args.record)
    record_ref = str(args.record)
    findings = []

    pattern = str(record.get("pattern", "")).strip()
    if pattern not in PATTERNS:
        findings.append(finding(
            "form-reason-inconsistent", record_ref,
            "pattern must be one of %s (got %r)" % (list(PATTERNS), pattern),
            record_ref + "#pattern"))

    raw_codes = record.get("codes")
    if raw_codes is None:
        raw_codes = []
    if not isinstance(raw_codes, list):
        findings.append(finding(
            "form-reason-inconsistent", record_ref,
            "codes must be an ordered list (got %r)" % type(raw_codes).__name__,
            record_ref + "#codes"))
        raw_codes = []
    codes = [str(item).strip() for item in raw_codes]

    seen = set()
    for position, code in enumerate(codes):
        ptr = "%s#codes[%d]" % (record_ref, position)
        if code in seen:
            findings.append(finding(
                "code-duplicate", record_ref,
                "code %r is duplicated; the list MUST NOT repeat a member" % code, ptr,
                kind="inconsistency", record_code=code, record=record_ref))
            continue
        seen.add(code)
        if code not in by_code:
            family = ("; simplicity, controllability and history are never codes "
                      "(FR-009)" if SIMPLICITY_FAMILY.search(code) else "")
            findings.append(finding(
                "code-unknown", record_ref,
                "code %r is outside the closed vocabulary %s%s"
                % (code, declared_order, family),
                ptr, kind="inconsistency", record_code=code, record=record_ref,
                compared=[code, declared_order]))

    for field in ("reason", "rationale", "justification"):
        prose = record.get(field)
        if isinstance(prose, str) and SIMPLICITY_FAMILY.search(prose):
            findings.append(finding(
                "prose-reason-not-a-code", record_ref,
                "%s %r is not a reason code; the closed vocabulary is %s"
                % (field, prose, declared_order),
                "%s#%s" % (record_ref, field), kind="inconsistency",
                record_code=prose, record=record_ref, compared=[prose, declared_order]))

    known_positions = [declared_order.index(code) for code in codes if code in by_code]
    if known_positions != sorted(known_positions):
        findings.append(finding(
            "code-order-violation", record_ref,
            "codes are not in the declared order %s (got %s)"
            % (declared_order, codes),
            record_ref + "#codes", kind="inconsistency", record=record_ref,
            compared=[codes, declared_order]))

    if pattern == "concurrent" and codes:
        findings.append(finding(
            "form-reason-inconsistent", record_ref,
            "pattern=concurrent carries a non-empty code list %s" % codes,
            record_ref + "#codes", record=record_ref, compared=[pattern, codes]))
    if pattern == "serial" and not codes:
        findings.append(finding(
            "form-reason-inconsistent", record_ref,
            "pattern=serial carries an empty code list", record_ref + "#codes",
            record=record_ref, compared=[pattern, codes]))

    # C-028 — the condition<->code bijection, both ways, over the condition-bound group
    bound_conditions = []
    for entry in catalogue:
        if str(entry.get("group", "")).strip() != "condition-bound":
            continue
        bound_conditions.append(str(entry.get("condition", "")).strip())
    missing_codes = [cond for cond in condition_index if cond not in bound_conditions]
    missing_conditions = [entry.get("code") for entry in catalogue
                          if str(entry.get("group", "")).strip() == "condition-bound"
                          and str(entry.get("condition", "")).strip() not in condition_index]
    if missing_codes or missing_conditions:
        findings.append(finding(
            "bijection-gap", "serial-reason",
            "condition<->code bijection is short: conditions without a code %s; "
            "condition-bound codes without a condition %s"
            % (missing_codes, missing_conditions), ".specify/shared/declarations/facts/serial-reason.yaml",
            kind="inconsistency", compared=[condition_index, bound_conditions]))

    evidence = record.get("evidence")
    evidence_map = evidence if isinstance(evidence, dict) else {}
    if evidence is not None and not isinstance(evidence, dict):
        findings.append(finding(
            "evidence-form-mismatch", record_ref,
            "evidence must be a per-code mapping (got %r)" % type(evidence).__name__,
            record_ref + "#evidence"))
        evidence_map = {}
    for code in codes:
        entry = by_code.get(code)
        if entry is None:
            continue
        evidence_ptr = "%s#evidence.%s" % (record_ref, code)
        if code not in evidence_map:
            findings.append(finding(
                "evidence-missing", record_ref,
                "no evidence for code %r (its condition is %s)"
                % (code, entry.get("condition", "none")),
                evidence_ptr, kind="inconsistency", record_code=code,
                condition=entry.get("condition", ""), record=record_ref))
            continue
        problem = judge_evidence(repo, entry, evidence_map[code])
        if problem is not None:
            findings.append(finding(
                problem[0], record_ref, "%s: %s" % (code, problem[1]), evidence_ptr,
                kind="inconsistency", record_code=code,
                condition=entry.get("condition", ""), record=record_ref))

    measured = {
        "pattern": pattern,
        "codes_declared": len(codes),
        "codes": codes,
        "declared_order": declared_order,
        "groups": statement.get("groups"),
        "condition_index": condition_index,
        "evidence_forms": {code: by_code[code].get("evidence_form")
                           for code in codes if code in by_code},
    }
    return envelope("serial-reason",
                    "fail" if findings else "pass", findings, measured)


# --------------------------------------------------------------------------- #
# concurrency reading (C-031…C-034, T074–T077)
# --------------------------------------------------------------------------- #
NOT_EVALUATED = "not_evaluated"


def epoch_seconds(value):
    """An interval endpoint as epoch seconds, or ``None`` when it is not one."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value or "").strip()
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    try:
        stamp = datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None
    return int(stamp.replace(tzinfo=timezone.utc).timestamp())


def maximum_overlap(intervals):
    """C-031: the maximum count of simultaneously open half-open intervals.

    ``[dispatched_at, settled_at)``; at equal epoch seconds a settle is applied
    before a dispatch, so touching intervals do not overlap (the fact's tie-break).
    """
    events = []
    for start, end in intervals:
        events.append((start, 1, "dispatch"))
        events.append((end, 0, "settle"))
    events.sort()
    current = 0
    peak = 0
    for _moment, _order, kind in events:
        current += 1 if kind == "dispatch" else -1
        peak = max(peak, current)
    return peak


def read_gate_ceiling(repo, override):
    """C-034: the ceiling from ``wp-gate.py``'s declared default, or the explicit flag.

    The ceiling's owner is the gate script, not the repository under judgement: the
    declaration is read from ``--repo`` first (a client project may carry its own
    ``.specify`` projection) and then from this engine's own tree, so a fixture that
    copies only ``.specify/shared/declarations/`` still reads the owner's default. The engine
    carries no numeric ceiling of its own; when neither the call-time override nor
    the gate script's declaration is readable, that is an input error.
    """
    if override is not None:
        return int(override), "--ceiling at call time"
    roots = [repo]
    own = default_repo()
    if own != repo:
        roots.append(own)
    for base in roots:
        for rel in (".specify/skills/sdd-loop-driver/scripts/wp-gate.py",
                    ".specify/skills/sdd-loop-driver/scripts/wp-gate.py"):
            path = base / rel
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            match = re.search(
                r'"--slot-cap-ceiling"[^)]*?default\s*=\s*(\d+)', text)
            if match:
                where = rel if base == repo else "%s (engine tree)" % rel
                return int(match.group(1)), "%s declared default" % where
    raise EngineInputError(
        "ceiling-unavailable",
        "no --ceiling given and wp-gate.py's --slot-cap-ceiling default is not readable")


def action_reading(repo, args):
    """C-031…C-034: judge one run record's concurrency reading."""
    slot_statement = fact_statement(
        load_fact(repo, "concurrency-slot-and-reserve"), "concurrency-slot-and-reserve")
    record = load_record(args.record)
    record_ref = str(args.record)
    findings = []

    units = record.get("units")
    if units is not None and not isinstance(units, list):
        # A present-but-non-list units field is a malformed record, never "no units":
        # treating it as empty let a concurrency claim hide its units and pass at
        # effective=0 (C-032's claim rule bypassed).
        findings.append(finding(
            "record-malformed", record_ref,
            "units must be a list (got %r)" % type(units).__name__,
            record_ref + "#units"))
        unit_list = []
    else:
        unit_list = units if isinstance(units, list) else []
    intervals = []
    missing = []
    for position, unit in enumerate(unit_list):
        if not isinstance(unit, dict):
            findings.append(finding(
                "record-malformed", record_ref,
                "units[%d] is not a mapping" % position, "%s#units[%d]" % (record_ref, position)))
            continue
        unit_id = str(unit.get("unit_id", "")).strip() or "units[%d]" % position
        start = epoch_seconds(unit.get("dispatched_at"))
        end = epoch_seconds(unit.get("settled_at"))
        dispatched = (unit.get("dispatched_at") is not None
                      or unit.get("settled_at") is not None
                      or bool(str(unit.get("executor_id", "")).strip()))
        if dispatched and (start is None or end is None):
            missing.append(unit_id)
            continue
        if start is not None and end is not None:
            intervals.append((start, end))

    if missing:
        effective = NOT_EVALUATED
    else:
        effective = maximum_overlap(intervals) if intervals else 0

    requested = record.get("requested")
    requested_numeric = numeric_reading(requested)
    declared_effective = record.get("effective")
    declared_numeric = numeric_reading(declared_effective)
    effective_reason = record.get("effective_reason")
    # C-033's triple is judged as (requested, effective, effective_reason), but the
    # effective member is the computed interval overlap, not a record field: the
    # record supplies requested and effective_reason, and the reason is required
    # exactly when the computed effective falls short of min(requested, bound).
    missing_fields = [] if requested is not None else ["requested"]
    if missing_fields:
        findings.append(finding(
            "reading-incomplete", record_ref,
            "the reading triple is incomplete; missing: %s" % missing_fields,
            record_ref + "#reading", compared=[[requested, effective, effective_reason]]))

    claim = (requested_numeric is not None and requested_numeric >= 2) \
        or str(record.get("pattern", "")).strip() == "concurrent"
    if missing and claim:
        for unit_id in missing:
            findings.append(finding(
                "reading-not-evaluated", unit_id,
                "a dispatched unit has no complete dispatch/settle interval, so "
                "effective is the literal %r" % NOT_EVALUATED, record_ref))

    if declared_numeric is not None:
        if effective != NOT_EVALUATED and declared_numeric != effective:
            findings.append(finding(
                "effective-mismatch", record_ref,
                "the record declares effective=%d but the interval overlap computes %d"
                % (declared_numeric, effective), record_ref + "#effective",
                kind="inconsistency", compared=[declared_numeric, effective],
                record=record_ref))
    elif str(declared_effective).strip() == NOT_EVALUATED and isinstance(effective, int):
        findings.append(finding(
            "effective-mismatch", record_ref,
            "the record declares effective=not_evaluated but the intervals compute %d"
            % effective, record_ref + "#effective",
            kind="inconsistency", compared=[declared_effective, effective],
            record=record_ref))

    slot_cap = numeric_reading(slot_statement.get("slot_cap_default"))
    reserve = numeric_reading(slot_statement.get("verifier_reserve"))
    ceiling, ceiling_source = read_gate_ceiling(repo, args.ceiling)
    remaining = numeric_reading(record.get("remaining_budget"))
    operands = [value for value in (slot_cap, ceiling, remaining) if value is not None]
    bound = min(operands) if operands else None
    available = (bound - reserve) if (bound is not None and reserve is not None) else None
    measured_bound = {
        "slot_cap": slot_cap,
        "ceiling": ceiling,
        "ceiling_source": ceiling_source,
        "remaining_budget": remaining if remaining is not None else NOT_EVALUATED,
        "min_formula": "min(slot_cap, ceiling, remaining_budget)",
        "min": bound,
        "verifier_reserve": reserve,
        "effective_available": available,
    }
    if isinstance(effective, int) and bound is not None:
        reason_text = str(effective_reason or "").strip()
        # The shortfall threshold is what the run could actually have used: a run
        # that requests less than the bound and achieves its request has no
        # shortfall, so the comparison is against min(requested, bound).
        threshold = bound if requested_numeric is None else min(requested_numeric, bound)
        if effective < threshold and not reason_text:
            findings.append(finding(
                "reading-incomplete", record_ref,
                "effective=%d is below min(requested, slot_cap, ceiling, remaining)=%d "
                "and carries no named effective_reason" % (effective, threshold),
                record_ref + "#effective_reason", compared=[effective, threshold]))
        if effective > bound:
            findings.append(finding(
                "bound-violation", record_ref,
                "effective=%d exceeds min(slot_cap, ceiling, remaining)=%d"
                % (effective, bound), record_ref + "#effective",
                kind="inconsistency", compared=[effective, bound], record=record_ref))

    measured = {
        "effective": effective,
        "requested": requested,
        "units_counted": len(intervals),
        "units_missing_interval": missing,
        "intervals": [{"start": start, "end": end} for start, end in intervals],
        "bound": measured_bound,
    }
    return envelope("reading", "fail" if findings else "pass", findings, measured)


# --------------------------------------------------------------------------- #
# decomposition coverage and goal-target partition (C-035/C-036, T113, T119)
# --------------------------------------------------------------------------- #
#: The document surfaces where a competing "which stages decompose" rule could live.
#: Tests and fixtures are assertions over the rule, not sources of it, and are excluded.
FOURTH_SOURCE_SURFACES = (
    "shared", "skills", "templates", "agents", "docs/reference",
    ".specify/skills", ".specify/shared", ".specify/templates", ".specify/memory",
)
FOURTH_SOURCE_EXTRA = (".specify/instructions.md",)


def tracked_files(repo):
    """Tracked files when ``repo`` is itself the git root; a walk otherwise.

    A fixture under a parent checkout must not inherit the parent's index: when
    ``rev-parse --show-toplevel`` is not the given root, the walk is the honest source.
    """
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], cwd=str(repo), check=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        top_path = Path(top.stdout.decode("utf-8", "replace").strip()).resolve()
        if top_path != Path(repo).resolve():
            return None
        result = subprocess.run(
            ["git", "ls-files", "-z"], cwd=str(repo), check=True,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        names = [name for name in result.stdout.decode("utf-8", "replace").split("\0") if name]
        return names
    except (OSError, subprocess.CalledProcessError):
        return None


def read_spine_project_config(repo, keys):
    """``[(spine path, {key: raw value})]`` for every state spine carrying one of ``keys``."""
    spines = []
    state_dir = repo / ".specify" / "state"
    if not state_dir.is_dir():
        return spines
    for path in sorted(state_dir.glob("*.md")):
        values = {}
        in_config = False
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line in lines:
            if re.match(r"^project_config:\s*$", line):
                in_config = True
                continue
            if in_config:
                if line and not line.startswith((" ", "\t")):
                    break
                match = re.match(r"^  ([A-Za-z0-9_]+):\s*(.*)$", line)
                if match:
                    values[match.group(1)] = match.group(2).strip()
        if any(key in values for key in keys):
            spines.append((path.relative_to(repo).as_posix(), values))
    return spines


def parse_spine_list(value):
    """A spine value ``[plan, implement]`` or ``a=auto`` form as a list, or ``None``."""
    text = str(value or "").strip()
    if text.startswith("[") and text.endswith("]"):
        return [item.strip().strip("\"'") for item in text[1:-1].split(",") if item.strip()]
    return [text] if text else []


def find_fourth_sources(repo, keys, allowed):
    """Files that assign one of the spine keys outside the fact and the spines (C-036)."""
    assignment = re.compile(
        r"^\s*[-*]?\s*(%s)\s*:" % "|".join(re.escape(key) for key in keys))
    hits = []
    names = tracked_files(repo)
    if names is None:
        names = []
        for surface in FOURTH_SOURCE_SURFACES:
            base = repo / surface
            if base.is_dir():
                names.extend(p.relative_to(repo).as_posix() for p in base.rglob("*")
                             if p.is_file())
        names.extend(FOURTH_SOURCE_EXTRA)
    for name in names:
        if name in allowed:
            continue
        if not (name.endswith((".md", ".yaml", ".yml", ".py", ".sh", ".txt"))):
            continue
        in_surface = any(name == surface or name.startswith(surface + "/")
                         for surface in FOURTH_SOURCE_SURFACES) or \
            name in FOURTH_SOURCE_EXTRA or name.startswith(".specify/state/")
        if not in_surface:
            continue
        path = repo / name
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            match = assignment.match(line)
            if match:
                hits.append({"file": name, "line": line_number, "key": match.group(1)})
    return hits


def read_goal_targets(repo):
    """``[(goal slug, [(target id, status)])]`` from the anchoring goal definitions."""
    goals = []
    anchoring = repo / ".specify" / "anchoring"
    if not anchoring.is_dir():
        return goals
    for goal_dir in sorted(p for p in anchoring.iterdir() if p.is_dir()):
        goal_file = goal_dir / "goal.md"
        if not goal_file.is_file():
            continue
        targets = []
        in_targets = False
        try:
            lines = goal_file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line in lines:
            if re.match(r"^##\s+Targets\s*$", line):
                in_targets = True
                continue
            if in_targets and line.startswith("## "):
                break
            if not in_targets:
                continue
            match = re.match(r"^\|\s*(T-[0-9]+)\s*\|\s*(.*?)\s*\|\s*([A-Za-z]+)\s*\|", line)
            if match:
                targets.append((match.group(1), match.group(3).lower()))
        goals.append((goal_dir.name, targets))
    return goals


def action_coverage(repo, args):
    """C-035/C-036: per-stage coverage, the spine relation and goal-target partitions."""
    statement = fact_statement(
        load_fact(repo, "decomposition-coverage"), "decomposition-coverage")
    slot_statement = fact_statement(
        load_fact(repo, "concurrency-slot-and-reserve"), "concurrency-slot-and-reserve")
    stages = [entry for entry in (statement.get("stages") or []) if isinstance(entry, dict)]
    coverage_values = [str(value).strip() for value in (statement.get("coverage_values") or [])]
    spine_relation = statement.get("spine_relation") or {}
    spine_keys = list(spine_relation.keys())
    fourth_source_rule = str(statement.get("fourth_source_of_stage_coverage", "defect"))

    findings = []
    by_stage = {str(entry.get("stage", "")).strip(): entry for entry in stages}
    selected = stages
    if args.stage:
        if args.stage not in by_stage:
            findings.append(finding(
                "coverage-undeclared", args.stage,
                "stage %r is not declared in decomposition-coverage.yaml" % args.stage,
                ".specify/shared/declarations/facts/decomposition-coverage.yaml"))
        selected = [by_stage[args.stage]] if args.stage in by_stage else []

    max_turns_budget = (slot_statement.get("unit_budget") or {})
    cell_statement = {}
    for entry in selected:
        stage = str(entry.get("stage", "")).strip()
        coverage = str(entry.get("coverage", "")).strip()
        cell = {"coverage": coverage}
        if coverage_values and coverage not in coverage_values:
            cell["decision"] = "invalid-coverage-value"
            findings.append(finding(
                "coverage-undeclared", stage,
                "coverage %r is outside the closed values %s" % (coverage, coverage_values),
                ".specify/shared/declarations/facts/decomposition-coverage.yaml"))
        elif coverage == "off":
            decision = entry.get("decision") or entry.get("decision_reason")
            if decision:
                cell["decision"] = "disabled"
                cell["decision_record"] = str(decision)
            else:
                cell["decision"] = "coverage-undeclared"
                findings.append(finding(
                    "coverage-undeclared", stage,
                    "stage %r stays serial (coverage=off) with no named decision record"
                    % stage, ".specify/shared/declarations/facts/decomposition-coverage.yaml"))
        elif coverage == "on":
            cell["decision"] = "covered"
            if entry.get("concurrency_source"):
                cell["concurrency_source"] = entry.get("concurrency_source")
        else:
            cell["decision"] = "covered-by-default"
            if statement.get("single_package_decision_required"):
                cell["single_package_decision_required"] = True
        cell_statement[stage] = cell

    allowed = {".specify/shared/declarations/facts/decomposition-coverage.yaml",
               ".specify/shared/declarations/facts/decomposition-coverage.yaml",
               ".specify/shared/declarations/facts/concurrency-slot-and-reserve.yaml"}
    spines = read_spine_project_config(repo, spine_keys)
    # Every state spine IS the projection surface (one per feature line, each a run-scoped
    # projection), so a key inside `.specify/state/**` is never a "fourth place"; a fourth
    # place is an authored document outside the fact and the spines.
    state_dir = repo / ".specify" / "state"
    if state_dir.is_dir():
        allowed.update(p.relative_to(repo).as_posix() for p in state_dir.glob("*.md"))
    allowed.update(path for path, _values in spines)
    fourth = find_fourth_sources(
        repo, spine_keys + ["decomposition_stages", "decomposition_slot_cap"], allowed)
    for hit in fourth:
        findings.append(finding(
            "fourth-source", hit["file"],
            "a fourth source of 'which stages decompose' is readable at %s:%d (%s); the "
            "fact is the owner and the spine keys are its projections (%s)"
            % (hit["file"], hit["line"], hit["key"], fourth_source_rule),
            "%s:%d" % (hit["file"], hit["line"]), compared=[spine_keys, hit["key"]]))

    feature_opt_out = False
    spine_report = []
    slot_cap = numeric_reading(slot_statement.get("slot_cap_default"))
    for path, values in spines:
        relation = {"spine": path, "keys": {}, "relation": "projection"}
        for key in spine_keys:
            if key not in values:
                continue
            relation["keys"][key] = values[key]
        decomposition = str(values.get(spine_keys[0], "")).strip().strip("\"'") \
            if spine_keys else ""
        if decomposition == "off":
            feature_opt_out = True
        stages_key = spine_keys[1] if len(spine_keys) > 1 else None
        if stages_key and stages_key in values:
            projected = parse_spine_list(values[stages_key])
            if projected:
                missing = [stage for stage in by_stage if stage not in projected]
                relation["stages_not_projected"] = missing
        slot_key = spine_keys[2] if len(spine_keys) > 2 else None
        if slot_key and numeric_reading(values.get(slot_key)) is not None and slot_cap:
            relation["slot_cap_matches_fact"] = (
                numeric_reading(values.get(slot_key)) == slot_cap)
        spine_report.append(relation)
    if feature_opt_out:
        for cell in cell_statement.values():
            cell["feature_opt_out"] = "disabled"

    ceiling, ceiling_source = read_gate_ceiling(repo, args.ceiling)
    reserve = numeric_reading(slot_statement.get("verifier_reserve")) or 0
    operands = [value for value in (slot_cap, ceiling) if value is not None]
    bound = min(operands) if operands else None
    available = (bound - reserve) if bound is not None else None
    degradation = str(slot_statement.get("degradation_rule", ""))
    reason_match = re.search(r"([a-z][a-z-]+) code", degradation)
    degrade_code = reason_match.group(1) if reason_match else "budget-reserve"

    goals_report = []
    for goal, targets in read_goal_targets(repo):
        if args.goal and goal != args.goal:
            continue
        open_targets = [target for target, status in targets if status == "open"]
        record = {
            "goal": goal,
            "targets": len(targets),
            "open_targets": open_targets,
            "stage_coverage": {stage: cell["decision"]
                               for stage, cell in cell_statement.items()},
        }
        if len(open_targets) >= 2 and available is not None:
            if available < 2:
                record["packages"] = []
                record["serial_reason"] = degrade_code
                record["effective_available"] = available
            else:
                record["effective_available"] = available
                record["packages"] = [open_targets[i:i + available]
                                      for i in range(0, len(open_targets), available)]
        else:
            record["packages"] = [open_targets] if open_targets else []
        goals_report.append(record)

    measured = {
        "stages": cell_statement,
        "spine_relation": spine_report,
        "bound": {
            "slot_cap": slot_cap,
            "ceiling": ceiling,
            "ceiling_source": ceiling_source,
            "verifier_reserve": reserve,
            "effective_available": available,
        },
        "goals": goals_report,
        "unit_budget": max_turns_budget,
    }
    return envelope("coverage", "fail" if findings else "pass", findings, measured)


# --------------------------------------------------------------------------- #
# dispatch capability (C-037…C-040, T095–T097)
# --------------------------------------------------------------------------- #
def frontmatter_list(text, key):
    """One flow-list frontmatter value (``capability-tools: [Read, Grep]``), or ``None``."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        head, sep, value = line.partition(":")
        if not sep or head.strip() != key:
            continue
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            return [item.strip().strip("\"'") for item in value[1:-1].split(",")
                    if item.strip()]
        return [value.strip().strip("\"'")] if value else []
    return None


def classify_capability(tools, body_text):
    """C-037's three-way test over the existing frontmatter list and the body text."""
    tool_names = {str(tool).strip().lower() for tool in (tools or [])}
    if any(tool in DISPATCH_TOOLS or "dispatch" in tool for tool in tool_names):
        return "dispatch-capable", "a dispatch tool is present in capability-tools"
    lowered = body_text.lower()
    if any(marker in lowered for marker in HANDOFF_MARKERS):
        return "handoff-declared", "the body declares an explicit handoff"
    if any(marker in lowered for marker in EXTERNAL_PROCESS_MARKERS):
        return "external-process", "the body declares an external-process form"
    return "incapable", "no dispatch tool, handoff or external-process form is declared"


def action_capability(repo, args):
    """C-037…C-040: the static capability sweep plus the coordinator verdict."""
    verdict_body = load_fact(repo, "coordinator-dispatch-verdict")
    verdict_statement = fact_statement(verdict_body, "coordinator-dispatch-verdict")
    allowed = [str(value).strip() for value in (verdict_statement.get("allowed_values") or [])]
    verdict = str(verdict_statement.get("verdict", "")).strip()

    findings = []
    measured = {
        "verdict_fact": ".specify/shared/declarations/facts/coordinator-dispatch-verdict.yaml",
        "verdict_allowed_values": allowed,
        "agents": [],
    }
    # The owner's ruling gates the whole action: an unadjudicated (or absent) verdict
    # is owner-unavailable before the record is even parsed, never a default.
    if not verdict or verdict not in allowed:
        return envelope(
            "capability", "owner-unavailable",
            [finding(
                "owner-unavailable", measured["verdict_fact"],
                "no adjudicated verdict readable (decision_state=%r, verdict=%r); the "
                "allowed values are %s — the owner's ruling is required, never a default"
                % (verdict_statement.get("decision_state"), verdict or None, allowed),
                measured["verdict_fact"])],
            measured, verdict=None)

    record = load_record(args.record)
    record_ref = str(args.record)
    measured["record"] = record_ref

    measured["verdict"] = verdict
    agents_dir = repo / "agents"
    for path in sorted(agents_dir.glob("*.agent.md")) if agents_dir.is_dir() else []:
        text = path.read_text(encoding="utf-8")
        tools = frontmatter_list(text, "capability-tools")
        name, detail = classify_capability(tools, text)
        rel = path.relative_to(repo).as_posix()
        measured["agents"].append({
            "body": rel,
            "reading": "capability-tools",
            "capability_tools": tools,
            "verdict": name,
            "detail": detail,
        })

    declared_body = str(record.get("body") or record.get("declared_body") or "").strip()
    declared_units = numeric_reading(record.get("declared_units"))
    if declared_body:
        body_path = repo / declared_body
        if not body_path.is_file():
            findings.append(finding(
                "body-unavailable", declared_body,
                "the record names a body that does not resolve", declared_body))
        else:
            text = body_path.read_text(encoding="utf-8")
            tools = frontmatter_list(text, "capability-tools")
            name, detail = classify_capability(tools, text)
            if declared_units is not None and declared_units >= 2 and name == "incapable":
                findings.append(finding(
                    "declaration-execution-mismatch", declared_body,
                    "the record declares %d units while the body's capability-tools lacks a "
                    "dispatch tool and no handoff is declared (%s)" % (declared_units, detail),
                    declared_body, kind="inconsistency",
                    compared=[{"declared_units": declared_units},
                              {"capability_tools": tools, "verdict": name}],
                    record=record_ref))

    units = record.get("units")
    if isinstance(units, list) and len(units) >= 2:
        executor_ids = set()
        pairs = []
        complete = True
        for position, unit in enumerate(units):
            if not isinstance(unit, dict):
                complete = False
                continue
            executor_ids.add(str(unit.get("executor_id", "")).strip())
            start = epoch_seconds(unit.get("dispatched_at"))
            end = epoch_seconds(unit.get("settled_at"))
            if start is None or end is None:
                complete = False
                continue
            pairs.append((start, end))
        measured["record_units"] = {
            "count": len(units),
            "executor_ids": sorted(executor_ids),
            "intervals_complete": complete,
            "max_overlap": maximum_overlap(pairs) if complete and pairs else NOT_EVALUATED,
        }
        if complete and len(executor_ids) == 1 and "" not in executor_ids \
                and maximum_overlap(pairs) <= 1:
            findings.append(finding(
                "declaration-execution-mismatch", record_ref,
                "the run record shows %d units all executed by %r with no interval "
                "overlap (max overlap %d): a declared-parallel run executed serially"
                % (len(units), next(iter(executor_ids)), maximum_overlap(pairs)),
                record_ref + "#units", kind="inconsistency",
                compared=[{"declared_units": len(units)},
                          {"executor_ids": sorted(executor_ids)}],
                record=record_ref))

    return envelope("capability", "fail" if findings else "pass",
                    findings, measured, verdict=verdict)


DISPATCH = {
    "classify": action_classify,
    "serial-reason": action_serial_reason,
    "reading": action_reading,
    "coverage": action_coverage,
    "capability": action_capability,
}


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser():
    parser = argparse.ArgumentParser(
        prog=SCRIPT_NAME,
        description=(
            "The concurrency judgement engine: classify bodies, judge serial reasons, "
            "readings, per-stage coverage and dispatch capability from the declaration "
            "facts (owner: .specify/shared/declarations/facts/)."
        ),
    )
    _sig_configure(
        parser,
        effects="reads the repository; writes only the file named by --json-out",
        codes="0 the judgement passed; 1 a documented check failed; "
              "2 input or environment error, or no owner verdict readable",
    )
    parser.add_argument("action", choices=ACTIONS,
                        help="the read-only action to run")
    parser.add_argument("--repo", default=None,
                        help="repository root whose .specify/shared/declarations/ is read "
                             "(default: resolved from this script's own location)")
    parser.add_argument("--record", default=None,
                        help="the record to judge (serial-reason / reading / capability)")
    parser.add_argument("--json-out", default=None,
                        help="write the judgement envelope here (the only write)")
    parser.add_argument("--stage", default=None,
                        help="coverage: judge one stage from decomposition-coverage.yaml")
    parser.add_argument("--goal", default=None,
                        help="coverage: judge one goal's target partition")
    parser.add_argument("--ceiling", type=int, default=None,
                        help="reading/coverage: the slot cap ceiling at call time "
                             "(default: read from wp-gate.py's declared default)")
    return parser


def main(argv=None):
    line = list(sys.argv[1:] if argv is None else argv)
    _sig_guard(line, declared=["--repo", "--record", "--json-out", "--stage",
                               "--goal", "--ceiling"])
    parser = build_parser()
    args = parser.parse_args(line)

    json_out = args.json_out
    try:
        repo = resolve_repo(args.repo)
        if args.action in RECORD_ACTIONS and not args.record:
            raise EngineInputError(
                "record-required", "action %r requires --record <file>" % args.action)
        if args.action not in RECORD_ACTIONS and args.record:
            raise EngineInputError(
                "record-not-applicable",
                "action %r takes no --record flag (C-021)" % args.action)
        result = DISPATCH[args.action](repo, args)
    except EngineInputError as error:
        decision = ("owner-unavailable" if error.code == "owner-unavailable"
                    else "not-applicable")
        result = envelope(args.action, decision,
                          [finding(error.code, str(args.repo or ""), error.message)],
                          {})
        try:
            emit(result, json_out)
        except EngineInputError as emit_error:
            print("error: %s" % emit_error.message, file=sys.stderr)
        return 2
    try:
        emit(result, json_out)
    except EngineInputError as emit_error:
        print("error: %s" % emit_error.message, file=sys.stderr)
        return 2
    return decision_exit(result["decision"])


if __name__ == "__main__":
    sys.exit(main())
