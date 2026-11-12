#!/usr/bin/env python3
"""Flow-class ledger engine (069a / 069b): reconcile, resolve and verify bindings.

The single owner of the execution/expression classification is
``.specify/shared/definitions/flow-class-definitions.md``; this engine never restates the
criteria or the values' meaning. It only:

* ``--action check`` — scan the repository inventory (``.specify/templates/commands/*.md``
  and ``skills/{external,internal}/*/SKILL.md``), parse the owner's per-unit
  ledger, and report every defect as one of the contracted finding kinds. The
  069a eight (``missing`` / ``unknown`` / ``duplicate`` / ``dual-class`` /
  ``invalid-class`` / ``row-malformed`` / ``neutral-unlisted`` /
  ``inventory-truncated``) keep their semantics; 069b adds ``ledger-truncated``,
  ``ledger-version-missing`` and ``mixed-oracle-class`` (contract
  ``contracts/ledger-reconciler.md`` C-1 / C-5 / C-7). The JSON also carries the
  ``coverage`` block, the ``red_kind`` bucket and the text face's anti-vacuous
  companion numbers (C-2 / C-3);
* ``--action lookup --unit-id <id>`` — return the registered class for a unit, or
  the default class plus the fixed "undeclared, running on the default" marker for
  a well-formed but unregistered unit. 077 adds the feature-line key family
  ``spec:<spec directory name>``: the class is read from the ``**Flow Class**``
  line in that spec's ``requirements.md`` head region (never inferred, never
  written into the per-unit ledger). Its record is field-for-field identical to a
  unit-key record, and an absent declaration yields the default class plus the
  advisory ``declaration-absent`` (exit 0, not a finding).
* ``--action isomorphism`` — parse the owner's isomorphism map (8 stages x 3
  faces) and its four non-isomorphism boundaries, then judge the 24 cells, the
  truthfulness of every enforcement annotation against the gate owner's
  ``(stage, face, blocking)`` rows, the boundary-to-face bindings, the closed
  medium-axis phrases and the code-type operator floor (069b contract
  ``contracts/isomorphism-map.md``).
* ``--action delegation`` — parse the command → skill delegation edges out of the
  command templates (069b contract C-8…C-10) and judge each edge against the
  owner ledger; a hand-maintained command→skill table is itself a finding.
* ``--action faces`` — parse the gate owner's six-face table (069b contract
  C-11 / C-12) and judge the count, id uniqueness, the single ``owner_pointer``
  binding per row, path/anchor resolvability and the absence of a second binding
  table.

All actions are read-only: no file is written or modified.

Exit codes (contracts ``flow-class-ledger.md`` C-13, ``isomorphism-map.md`` C-13
and ``ledger-reconciler.md`` C-3 / C-14):

* ``check``:  0 = zero findings, 1 = at least one finding, 2 = a named non-green
  state (``owner-unavailable`` when the owner document is missing or unparsable,
  ``framework-source-required`` when the repository is a client payload root).
  ``red_kind`` names that state with the fixed priority
  ``owner-unavailable`` > ``framework-source-required`` > ``parse-failure`` >
  ``gap`` > ``clean``;
* ``lookup``: 0 = resolved (including the default degradation and the
  ``declaration-absent`` advisory), 1 = a feature-line declaration carries an
  author error (``invalid-class`` / ``declaration-malformed`` /
  ``declaration-duplicate`` / ``declaration-misplaced`` — blocking, never merged
  into 2), 2 = malformed unit id / unreadable spec input or unparsable owner. An
  unparsable owner keeps the default class semantics, reports ``owner-unavailable``
  on stderr and leaves ``marker`` null — the two degradation labels are mutually
  exclusive (requirements FR-009 / FR-016);
* ``isomorphism`` / ``delegation`` / ``faces``: 0 = zero findings, 1 = at least
  one finding, 2 = input error (missing/unparsable owner or gate owner) or a
  payload root (``framework-source-required``). A payload root emits zero
  findings and never a green verdict.

Usage::

    python3 .specify/scripts/python/flow-class-check.py --action check [--repo <root>] [--format text|json]
    python3 .specify/scripts/python/flow-class-check.py --action lookup --unit-id <id> [--repo <root>] [--format text|json]
    python3 .specify/scripts/python/flow-class-check.py --action isomorphism [--repo <root>] [--format text|json]
    python3 .specify/scripts/python/flow-class-check.py --action delegation [--repo <root>] [--format text|json]
    python3 .specify/scripts/python/flow-class-check.py --action faces [--repo <root>] [--format text|json]

The ledger is parsed by header name, never by column position; a row whose cell
count or required values do not fit the declared grammar is reported as
``row-malformed`` and excluded from the unit set (it is not re-classified as
missing/unknown/invalid-class).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------- #
# Contract constants (literals are pinned copies of requirements.md § Shared Strings)
# --------------------------------------------------------------------------- #
CLASS_KEY = "flow_class"            # [[STR-003]]
DEFAULT_MARKER = "未声明·按默认"    # [[STR-004]]

# Feature 084, batch 1 rows 4-8: the five closed sets this engine compares against are
# declaration-layer facts (`.specify/shared/declarations/facts/flow-class-*.yaml`). The engine carries no copy of
# them — it reads each through the shared read entry, so adding one legal member to a declaration makes
# the gate accept it with no script edit (FR-007 (c), US2 acceptance 2) and a second tuple anywhere is
# the finding these reads exist to make impossible.
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import declaration_reader  # noqa: E402  (import follows the sys.path entry above)


def declared_sequence(slug):
    """`(values, label)` for one closed-set / table fact; `((), <STR-014 instance>)` when unreadable."""
    try:
        body = declaration_reader.load_fact(
            declaration_reader.find_repo(Path(__file__).resolve()), slug)["body"]
        values = body.get("statement")
        if not isinstance(values, list) or not values:
            raise ValueError("statement is not a non-empty sequence")
        return tuple(str(value) for value in values), None
    except (declaration_reader.DeclarationError, TypeError, ValueError):
        return (), declaration_reader.absent_label(slug)


CLASS_VALUES, CLASS_VALUES_LABEL = declared_sequence("flow-class-classes")
BASIS_VALUES, BASIS_VALUES_LABEL = declared_sequence("flow-class-basis")
NEUTRAL_CATEGORIES, NEUTRAL_CATEGORIES_LABEL = declared_sequence("flow-class-neutral-categories")
REQUIRED_LEDGER_COLUMNS, LEDGER_COLUMNS_LABEL = declared_sequence("flow-class-ledger-columns")


def declared_mapping(slug):
    """`(mapping, label)` for one mapping-shaped fact; `({}, <STR-014 instance>)` when unreadable."""
    try:
        body = declaration_reader.load_fact(
            declaration_reader.find_repo(Path(__file__).resolve()), slug)["body"]
        statement = body.get("statement")
        if not isinstance(statement, dict) or not statement:
            raise ValueError("statement is not a non-empty mapping")
        return dict(statement), None
    except (declaration_reader.DeclarationError, TypeError, ValueError):
        return {}, declaration_reader.absent_label(slug)


#: Feature 084, batch 2: the six-face gate's shape (section keyword + closed row count) and the
#: stage-operator table's header. Both are declarations; the engine carries no copy of either, and a
#: value read as empty leaves the corresponding check refusing to judge (see :func:`main`).
FACES_DECLARED, FACES_DECLARED_LABEL = declared_mapping("expression-gate-faces")
OPERATOR_COLUMNS, OPERATOR_COLUMNS_LABEL = declared_sequence("expression-stage-operator-table")
FACES_SECTION_KEYWORD = FACES_DECLARED.get("section_keyword")
try:
    FACES_EXPECTED = int(str(FACES_DECLARED.get("expected", "")).strip())
except (TypeError, ValueError):
    FACES_EXPECTED = None
#: A file that parsed but does not carry a usable pair is as unjudgeable as an absent one: the gate
#: would otherwise compare a row count against `None`, which reads as a shape finding rather than as
#: the `[[STR-014]]` degradation it is.
if not FACES_SECTION_KEYWORD or FACES_EXPECTED is None:
    FACES_DECLARED_LABEL = FACES_DECLARED_LABEL or declaration_reader.absent_label(
        "expression-gate-faces")

#: The operator table's columns, by position. A header that does not match this tuple is a gate-owner
#: error, and every row is then resolved by position — so the five column names exist once, in
#: `.specify/shared/declarations/facts/expression-stage-operator-table.yaml`, not again in this file.
if len(OPERATOR_COLUMNS) == 5:
    STEP_COLUMN, GATE_ID_COLUMN, OPERATOR_COLUMN, FACE_COLUMN, LEVEL_COLUMN = OPERATOR_COLUMNS
else:
    STEP_COLUMN = GATE_ID_COLUMN = OPERATOR_COLUMN = FACE_COLUMN = LEVEL_COLUMN = None
    OPERATOR_COLUMNS_LABEL = OPERATOR_COLUMNS_LABEL or declaration_reader.absent_label(
        "expression-stage-operator-table")

#: The declared class axis is ordered and `mixed-oracle` is its third member; both facts are ordered
#: closed sets, so the positions below are the declaration's, never a re-spelled name. An empty read
#: (unreadable layer) leaves these ``None`` and the CLI refuses to judge (see :func:`main`).
EXECUTION, EXPRESSION = CLASS_VALUES if len(CLASS_VALUES) == 2 else (None, None)
MIXED_ORACLE = BASIS_VALUES[2] if len(BASIS_VALUES) > 2 else None
DEFAULT_CLASS = EXECUTION

# Anti-vacuous floors: measured constants (2026-10-24), never derived at runtime.
FLOOR_COMMANDS = 27
FLOOR_SKILLS = 51
# 069b contract C-1: the parse-side anti-vacuous floor is derived from the
# inventory-side constants — floor((27 + 51) / 2) = 39 — never from the ledger
# under inspection and never from a third hand-written unit count. It is a
# materiality threshold, not a completeness judgement (completeness is
# ``matched == inventory_units and gaps == 0``); 77 parsed rows must stay above it
# so that deleting one row is a ``gap``, not a parse failure.
LEDGER_FLOOR = (FLOOR_COMMANDS + FLOOR_SKILLS) // 2

OWNER_REL = Path("shared") / "definitions" / "flow-class-definitions.md"
MIRROR_DIR_NAME = ".specify"
COMMANDS_REL = Path("templates") / "commands"
SKILLS_REL = Path("skills")
SKILL_LAYERS = ("external", "internal")

LEDGER_SECTION_KEYWORD = "逐流程台账"
NEUTRAL_SECTION_KEYWORD = "类中立清单"
# ``REQUIRED_LEDGER_COLUMNS`` is NOT defined here: feature 084 batch 1 row 7 moved the ledger's
# required column set to ``.specify/shared/declarations/facts/flow-class-ledger-columns.yaml`` and the read at
# the top of this module binds the same ordered tuple the header check compared before (T012). A
# local re-assignment would shadow that read and put the second copy back — this module refuses to
# judge when the read is empty (see :func:`main`), so no local fallback belongs here either.
REQUIRED_NEUTRAL_COLUMNS = ("unit_id", "category", "rationale")

UNIT_ID_RE = re.compile(r"^(?:/speckit\.[a-z0-9][a-z0-9-]*|skill:[a-z0-9][a-z0-9-]*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s")
SEPARATOR_CELL_RE = re.compile(r":?-{2,}:?")

# 069b contract C-5: the ledger version is declared once, in a fixed grammar.
LEDGER_VERSION_KEY = "台账版本"
LEDGER_VERSION_RE = re.compile(
    r"^\*\*%s\*\*\s*:\s*\d+\s*（\d{4}-\d{2}-\d{2}）\s*$" % LEDGER_VERSION_KEY
)

FINDING_KINDS = (
    # 069a's eight, semantics untouched (contract C-4).
    "missing",
    "unknown",
    "duplicate",
    "dual-class",
    "invalid-class",
    "row-malformed",
    "neutral-unlisted",
    "inventory-truncated",
    # 069b's additions to ``check`` (contract C-4: exactly three).
    "ledger-truncated",
    "ledger-version-missing",
    "mixed-oracle-class",
)

# 069b contract C-3: the two buckets are an exhaustive partition of ``check``'s
# kinds. Anything outside CHECK_GAP_KINDS is a parse failure, so
# ``red_kind == clean`` <=> ``findings == []`` holds by construction.
CHECK_GAP_KINDS = frozenset(
    {
        "missing",
        "unknown",
        "duplicate",
        "dual-class",
        "invalid-class",
        "neutral-unlisted",
        "mixed-oracle-class",
        "ledger-version-missing",
    }
)

RED_OWNER_UNAVAILABLE = "owner-unavailable"
RED_FRAMEWORK_SOURCE_REQUIRED = "framework-source-required"
RED_PARSE_FAILURE = "parse-failure"
RED_GAP = "gap"
RED_CLEAN = "clean"

DEGRADATION_LABEL = RED_OWNER_UNAVAILABLE


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def find_repo_root() -> Path:
    """Resolve the repository root from this script's own location.

    The canonical copy lives at ``<root>/scripts/python/flow-class-check.py`` and
    its runtime mirror at ``<root>/.specify/scripts/python/flow-class-check.py``;
    walking up to the nearest ancestor that contains ``.specify/`` (skipping a
    parent that *is* ``.specify``) resolves both to the same root. A directory
    named ``.specify`` is never the project root — it is the payload mirror.
    """
    here = Path(__file__).resolve()
    parents = list(here.parents)
    for parent in parents:
        if parent.name != MIRROR_DIR_NAME and (parent / MIRROR_DIR_NAME).is_dir():
            return parent
    for parent in parents:
        if parent.name == MIRROR_DIR_NAME:
            return parent.parent
    return parents[2] if len(parents) > 2 else here.parent


def owner_candidates(repo: Path) -> list[Path]:
    """Every place the owner document may live, in resolution order.

    Two hats: the framework source keeps the owner at ``<root>/shared/…``, while a
    client project receives the same payload at ``<proj>/.specify/shared/…``
    (distribution contract C-3 row 1). ``--repo`` may name either the source root
    or the payload root itself, so both shapes are tried and the first hit wins;
    only when neither exists is the owner genuinely unavailable.
    """
    roots = [repo]
    if repo.name != MIRROR_DIR_NAME:
        roots.append(repo / MIRROR_DIR_NAME)
    return [root / OWNER_REL for root in roots]


def checked_at() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def cells(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def is_separator(row: list[str]) -> bool:
    return bool(row) and all(SEPARATOR_CELL_RE.fullmatch(cell) for cell in row)


def section_with_offset(lines: list[str], keyword: str):
    """Return ``(heading_index, body_lines)`` for the first matching heading.

    The body stops at the next heading of the same or a higher level, so a later
    section's table can never be mistaken for this section's table. The heading
    index is returned so callers can report absolute 1-based line numbers
    (``heading_index + 2`` is the first body line).
    """
    for index, line in enumerate(lines):
        match = HEADING_RE.match(line)
        if not match or keyword not in line:
            continue
        level = len(match.group(1))
        body: list[str] = []
        for follow in lines[index + 1:]:
            follow_match = HEADING_RE.match(follow)
            if follow_match and len(follow_match.group(1)) <= level:
                break
            body.append(follow)
        return index, body
    return None, None


def section_body(lines: list[str], keyword: str):
    """Return the body lines of the first heading containing ``keyword``."""
    _index, body = section_with_offset(lines, keyword)
    return body


def first_table(lines: list[str]):
    """Return ``(header_cells, [(line_no, cells), ...])`` for the first table."""
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("|"):
            continue
        if index + 1 >= len(lines) or not lines[index + 1].lstrip().startswith("|"):
            continue
        header = cells(line)
        if not is_separator(cells(lines[index + 1])):
            continue
        rows: list[tuple[int, list[str]]] = []
        cursor = index + 2
        while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
            row = cells(lines[cursor])
            if not is_separator(row):
                rows.append((cursor + 1, row))
            cursor += 1
        return header, rows
    return None


class OwnerError(Exception):
    """The owner document itself cannot be parsed (a C-13 exit-2 condition)."""


class OwnerLedger:
    def __init__(self, rows, malformed, neutral_units, version_declarations):
        self.rows = rows                  # list[dict] with a "_line" key
        self.malformed = malformed        # list[dict] {line, unit_id, message}
        self.neutral_units = neutral_units  # set[str]
        self.version_declarations = version_declarations  # list[dict] {line, text}


# --------------------------------------------------------------------------- #
# owner parsing
# --------------------------------------------------------------------------- #
def parse_neutral_list(lines: list[str]) -> set[str]:
    """Parse the closed neutral list; a missing section/table yields an empty list.

    An unparsable neutral list is not an exit-2 condition — the checker then
    reports every ``neutral: yes`` row as ``neutral-unlisted`` rather than
    silently accepting the flag.
    """
    body = section_body(lines, NEUTRAL_SECTION_KEYWORD)
    if body is None:
        return set()
    table = first_table(body)
    if table is None:
        return set()
    header, rows = table
    names = [name for name in header]
    if any(column not in names for column in REQUIRED_NEUTRAL_COLUMNS):
        return set()
    index = {name: names.index(name) for name in names}
    units: set[str] = set()
    for _line_no, row in rows:
        if len(row) != len(names):
            continue
        record = {name: row[index[name]] for name in names}
        unit_id = record.get("unit_id", "")
        if not UNIT_ID_RE.fullmatch(unit_id):
            continue
        if record.get("category", "") not in NEUTRAL_CATEGORIES:
            continue
        if not record.get("rationale", "").strip():
            continue
        units.add(unit_id)
    return units


def parse_owner(repo: Path) -> OwnerLedger:
    candidates = owner_candidates(repo)
    owner_path = next((path for path in candidates if path.is_file()), None)
    if owner_path is None:
        raise OwnerError(
            "owner document unreadable: none of %s exists"
            % ", ".join(str(path) for path in candidates)
        )
    try:
        text = owner_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise OwnerError("owner document unreadable: %s (%s)" % (owner_path, exc))

    lines = text.splitlines()
    section_start, body = section_with_offset(lines, LEDGER_SECTION_KEYWORD)
    if body is None:
        raise OwnerError(
            "owner document has no %r section" % LEDGER_SECTION_KEYWORD
        )
    table = first_table(body)
    if table is None:
        raise OwnerError(
            "owner section %r has no parseable Markdown table" % LEDGER_SECTION_KEYWORD
        )
    header, raw_rows = table
    names = [name for name in header]
    missing_columns = [c for c in REQUIRED_LEDGER_COLUMNS if c not in names]
    if missing_columns:
        raise OwnerError(
            "ledger header lacks required column(s): %s (header=%r)"
            % (", ".join(missing_columns), names)
        )
    index = {name: names.index(name) for name in names}

    rows: list[dict] = []
    malformed: list[dict] = []
    for line_no, row in raw_rows:
        if len(row) != len(names):
            malformed.append(
                {
                    "line": line_no,
                    "unit_id": _canonical_or_none(row[0] if row else ""),
                    "message": "row has %d cell(s) but the header declares %d"
                    % (len(row), len(names)),
                }
            )
            continue
        record = {name: row[index[name]] for name in names}
        problem = _row_problem(record)
        if problem:
            malformed.append(
                {
                    "line": line_no,
                    "unit_id": _canonical_or_none(record.get("unit_id", "")),
                    "message": problem,
                }
            )
            continue
        record["_line"] = line_no
        rows.append(record)

    # 069b contract C-5: the version declaration lives once inside § 逐流程台账.
    # Counting it here (not as a ledger column) keeps the version signal single:
    # missing -> ``ledger-version-missing``; duplicated or malformed -> the
    # existing ``row-malformed`` (no new kind, counted as a parse error).
    version_declarations = [
        {"line": section_start + 2 + offset, "text": line.strip()}
        for offset, line in enumerate(body)
        if line.strip().startswith("**%s**" % LEDGER_VERSION_KEY)
    ]

    return OwnerLedger(rows, malformed, parse_neutral_list(lines), version_declarations)


def _canonical_or_none(unit_id: str):
    unit_id = (unit_id or "").strip()
    return unit_id if UNIT_ID_RE.fullmatch(unit_id) else None


def _row_problem(record: dict):
    """Return a structural problem for one row, or ``None`` when it parses.

    Structural, not semantic: an out-of-domain class value is well formed (it is
    reported as ``invalid-class``), while an empty required value or a
    non-canonical unit id is ``row-malformed``.
    """
    unit_id = record.get("unit_id", "").strip()
    if not UNIT_ID_RE.fullmatch(unit_id):
        return "non-canonical unit id %r" % unit_id
    if not record.get(CLASS_KEY, "").strip():
        return "empty %s value" % CLASS_KEY
    if not record.get("basis", "").strip():
        return "empty basis value"
    if record.get("basis", "").strip() not in BASIS_VALUES:
        return "basis %r is outside the closed set %r" % (
            record.get("basis", "").strip(),
            BASIS_VALUES,
        )
    neutral = record.get("neutral", "").strip().lower()
    if neutral not in ("", "yes"):
        return "neutral %r is outside the closed set ''/yes" % record.get("neutral", "")
    return None


# --------------------------------------------------------------------------- #
# inventory
# --------------------------------------------------------------------------- #
class Inventory:
    def __init__(self, commands: set[str], skills: set[str]):
        self.commands = commands
        self.skills = skills

    @property
    def units(self) -> set[str]:
        return self.commands | self.skills


def scan_inventory(repo: Path) -> Inventory:
    commands: set[str] = set()
    commands_dir = repo / COMMANDS_REL
    if commands_dir.is_dir():
        for path in commands_dir.glob("*.md"):
            if path.is_file():
                commands.add("/speckit.%s" % path.stem)

    skills: set[str] = set()
    for layer in SKILL_LAYERS:
        layer_dir = repo / SKILLS_REL / layer
        if not layer_dir.is_dir():
            continue
        for path in layer_dir.glob("*/SKILL.md"):
            if path.is_file():
                skills.add("skill:%s" % path.parent.name)
    return Inventory(commands, skills)


# --------------------------------------------------------------------------- #
# findings
# --------------------------------------------------------------------------- #
def finding(kind: str, unit_id=None, message: str = "", line=None) -> dict:
    record = {"kind": kind, "unit_id": unit_id, "message": message}
    if line is not None:
        record["line"] = line
    return record


def reconcile(repo: Path, inventory: Inventory, ledger: OwnerLedger) -> list[dict]:
    findings: list[dict] = []

    # C-5: exactly one version declaration inside § 逐流程台账.
    if not ledger.version_declarations:
        findings.append(
            finding(
                "ledger-version-missing",
                None,
                message="§ %s declares no `**%s**: <int>（<YYYY-MM-DD>）`"
                % (LEDGER_SECTION_KEYWORD, LEDGER_VERSION_KEY),
            )
        )
    else:
        first = ledger.version_declarations[0]
        if len(ledger.version_declarations) > 1:
            findings.append(
                finding(
                    "row-malformed",
                    None,
                    message="the `**%s**` declaration appears %d times (lines %r); "
                    "it MUST appear exactly once"
                    % (
                        LEDGER_VERSION_KEY,
                        len(ledger.version_declarations),
                        [item["line"] for item in ledger.version_declarations],
                    ),
                    line=first["line"],
                )
            )
        elif not LEDGER_VERSION_RE.match(first["text"]):
            findings.append(
                finding(
                    "row-malformed",
                    None,
                    message="the `**%s**` declaration does not match "
                    "`**%s**: <int>（<YYYY-MM-DD>）`: %r"
                    % (LEDGER_VERSION_KEY, LEDGER_VERSION_KEY, first["text"]),
                    line=first["line"],
                )
            )

    for item in ledger.malformed:
        findings.append(
            finding(
                "row-malformed",
                item["unit_id"],
                message=item["message"],
                line=item["line"],
            )
        )

    grouped: dict[str, list[dict]] = {}
    for row in ledger.rows:
        unit_id = row["unit_id"]
        grouped.setdefault(unit_id, []).append(row)
        if row[CLASS_KEY] not in CLASS_VALUES:
            findings.append(
                finding(
                    "invalid-class",
                    unit_id,
                    message="%s value %r is outside the closed set %r"
                    % (CLASS_KEY, row[CLASS_KEY], CLASS_VALUES),
                    line=row["_line"],
                )
            )
        # C-7: a mixed-oracle row is always execution (both oracles sign off);
        # the class is a ledger defect, never a per-case call for expression.
        if (
            row.get("basis", "").strip() == MIXED_ORACLE
            and row[CLASS_KEY] != EXECUTION
        ):
            findings.append(
                finding(
                    "mixed-oracle-class",
                    unit_id,
                    message="basis %r with %s %r — a mixed-oracle row MUST be %r"
                    % (MIXED_ORACLE, CLASS_KEY, row[CLASS_KEY], EXECUTION),
                    line=row["_line"],
                )
            )

    for unit_id, group in grouped.items():
        if len(group) < 2:
            continue
        values = {row[CLASS_KEY] for row in group if row[CLASS_KEY] in CLASS_VALUES}
        lines = [row["_line"] for row in group]
        if len(values) > 1:
            findings.append(
                finding(
                    "dual-class",
                    unit_id,
                    message="conflicting %s values %r on lines %r"
                    % (CLASS_KEY, sorted(values), lines),
                    line=lines[0],
                )
            )
        else:
            findings.append(
                finding(
                    "duplicate",
                    unit_id,
                    message="unit id appears on lines %r" % lines,
                    line=lines[0],
                )
            )

    reported_neutral: set[str] = set()
    for row in ledger.rows:
        unit_id = row["unit_id"]
        if row.get("neutral", "").strip().lower() != "yes":
            continue
        if unit_id in ledger.neutral_units or unit_id in reported_neutral:
            continue
        reported_neutral.add(unit_id)
        findings.append(
            finding(
                "neutral-unlisted",
                unit_id,
                message="neutral: yes outside the closed neutral list",
                line=row["_line"],
            )
        )

    ledger_units = set(grouped)
    inventory_units = inventory.units
    for unit_id in sorted(inventory_units - ledger_units):
        findings.append(
            finding("missing", unit_id, message="inventory unit has no ledger row")
        )
    for unit_id in sorted(ledger_units - inventory_units):
        findings.append(
            finding("unknown", unit_id, message="ledger unit is absent from the inventory")
        )

    if len(inventory.commands) < FLOOR_COMMANDS:
        findings.append(
            finding(
                "inventory-truncated",
                None,
                message="command inventory has %d unit(s), below the floor of %d"
                % (len(inventory.commands), FLOOR_COMMANDS),
            )
        )
    if len(inventory.skills) < FLOOR_SKILLS:
        findings.append(
            finding(
                "inventory-truncated",
                None,
                message="skill inventory has %d unit(s), below the floor of %d"
                % (len(inventory.skills), FLOOR_SKILLS),
            )
        )
    # C-1: the parse-side anti-vacuous floor. A ledger parsed into fewer rows
    # than the inventory-derived floor (including zero) is a parse failure, never
    # a green verdict; it must not be confused with a single deletion (77 rows).
    if len(ledger.rows) < LEDGER_FLOOR:
        findings.append(
            finding(
                "ledger-truncated",
                None,
                message="ledger parsed %d row(s), below the floor of %d "
                "derived from the inventory-side floors"
                % (len(ledger.rows), LEDGER_FLOOR),
            )
        )

    kinds_order = {kind: position for position, kind in enumerate(FINDING_KINDS)}
    findings.sort(
        key=lambda item: (
            kinds_order.get(item["kind"], len(FINDING_KINDS)),
            item.get("unit_id") or "",
            item.get("line") or 0,
        )
    )
    return findings


def coverage_block(inventory: Inventory, ledger: OwnerLedger, findings: list[dict]) -> dict:
    """Return the six contracted coverage integers (contract C-2).

    ``matched`` is ``|ledger units ∩ inventory units|`` — the anti-vacuous
    companion of ``findings == []``. ``gaps`` is exactly ``missing + unknown`` and
    ``parse_errors`` counts the ledger-side parse defects only
    (``row-malformed + ledger-truncated``); ``inventory-truncated`` belongs to the
    inventory side and is deliberately excluded from that sum (it still lands in
    the ``parse-failure`` bucket per C-3).
    """
    kinds = [item["kind"] for item in findings]
    ledger_units = {row["unit_id"] for row in ledger.rows}
    inventory_units = inventory.units
    return {
        "ledger_rows": len(ledger.rows),
        "inventory_units": len(inventory_units),
        "matched": len(ledger_units & inventory_units),
        "gaps": kinds.count("missing") + kinds.count("unknown"),
        "parse_errors": kinds.count("row-malformed") + kinds.count("ledger-truncated"),
        "floor": LEDGER_FLOOR,
    }


def red_kind_for(findings: list[dict]) -> str:
    """Return the bucket name for a measured ``check`` run (contract C-3).

    The two buckets are an exhaustive partition of ``check``'s finding kinds, so
    ``clean`` is returned exactly when there are no findings; a finding outside
    ``CHECK_GAP_KINDS`` can only mean a parse failure.
    """
    if not findings:
        return RED_CLEAN
    if all(item["kind"] in CHECK_GAP_KINDS for item in findings):
        return RED_GAP
    return RED_PARSE_FAILURE


# --------------------------------------------------------------------------- #
# actions
# --------------------------------------------------------------------------- #
def render_check_text(record: dict) -> str:
    coverage = record["coverage"] or {}
    companion = "matched=%s inventory_units=%s" % (
        coverage.get("matched", "n/a"),
        coverage.get("inventory_units", "n/a"),
    )
    lines = [
        "flow-class check: %d unit(s) scanned, %d finding(s) [%s, %s]"
        % (record["units"], len(record["findings"]), companion, record["red_kind"])
    ]
    if record["coverage"] is not None:
        lines.append(
            "coverage: ledger_rows=%d matched=%d inventory_units=%d gaps=%d "
            "parse_errors=%d floor=%d"
            % (
                coverage["ledger_rows"],
                coverage["matched"],
                coverage["inventory_units"],
                coverage["gaps"],
                coverage["parse_errors"],
                coverage["floor"],
            )
        )
    for item in record["findings"]:
        location = item.get("unit_id") or "-"
        if item.get("line"):
            location = "%s (line %d)" % (location, item["line"])
        lines.append("  [%s] %s — %s" % (item["kind"], location, item["message"]))
    return "\n".join(lines)


def check_record(stamp: str, repo: Path) -> dict:
    return {
        "action": "check",
        "checked_at": stamp,
        "repo": str(repo),
        "units": 0,
        "inventory": {
            "commands": 0,
            "skills": 0,
            "floors": {"commands": FLOOR_COMMANDS, "skills": FLOOR_SKILLS},
        },
        "coverage": None,
        "red_kind": None,
        "findings": [],
        "error": None,
    }


def check_input_error(
    record: dict, label: str, detail: str, output_format: str, code: int = 2
) -> int:
    """Emit a named non-green state: no findings, no green verdict (C-3 / C-14)."""
    record["error"] = {"label": label, "detail": detail}
    record["red_kind"] = label
    print("%s: %s" % (label, detail), file=sys.stderr)
    if output_format == "json":
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        print(render_check_text(record))
    return code


def action_check(repo: Path, output_format: str) -> int:
    stamp = checked_at()
    record = check_record(stamp, repo)

    # C-3 gives ``owner-unavailable`` the highest priority, so the owner is parsed
    # before the payload-root branch: a client project with no owner reports the
    # more specific label rather than ``framework-source-required``.
    try:
        ledger = parse_owner(repo)
    except OwnerError as exc:
        return check_input_error(record, RED_OWNER_UNAVAILABLE, str(exc), output_format)

    # C-14: ``check`` only runs in a framework source tree. A payload root (client
    # ``.specify/`` shape, or the payload directory itself) is a named state: zero
    # findings, exit 2, never a green verdict and never ``inventory-truncated``.
    if not is_framework_source(repo):
        return check_input_error(
            record,
            RED_FRAMEWORK_SOURCE_REQUIRED,
            "neither .specify/templates/commands/ nor a parseable skills/{external,internal}/ "
            "is present in %s" % repo,
            output_format,
        )

    inventory = scan_inventory(repo)
    record["units"] = len(inventory.units)
    record["inventory"] = {
        "commands": len(inventory.commands),
        "skills": len(inventory.skills),
        "floors": {"commands": FLOOR_COMMANDS, "skills": FLOOR_SKILLS},
    }
    record["findings"] = reconcile(repo, inventory, ledger)
    record["coverage"] = coverage_block(inventory, ledger, record["findings"])
    record["red_kind"] = red_kind_for(record["findings"])
    if output_format == "json":
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        print(render_check_text(record))
    return 1 if record["findings"] else 0


def render_lookup_text(record: dict) -> str:
    lines = [
        "unit_id: %s" % record["unit_id"],
        "%s: %s" % (
            CLASS_KEY,
            record[CLASS_KEY] if record[CLASS_KEY] is not None else "null",
        ),
        "%s: %s" % (
            FLOW_TYPE_KEY,
            record.get(FLOW_TYPE_KEY) if record.get(FLOW_TYPE_KEY) is not None else "null",
        ),
        "source: %s" % record["source"],
        "marker: %s" % (record["marker"] if record["marker"] is not None else "null"),
        "basis: %s" % (record["basis"] if record["basis"] is not None else "null"),
        "neutral: %s" % ("true" if record["neutral"] else "false"),
    ]
    return "\n".join(lines)


def emit_lookup(record: dict, output_format: str) -> None:
    if output_format == "json":
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        print(render_lookup_text(record))


def owner_degradation(unit_id: str, stamp: str, detail: str, output_format: str) -> int:
    """Degrade to the default class with the one closed label, exit 2.

    Used when the owner parses but cannot yield a *decided* class for this unit: a
    value outside ``CLASS_VALUES``, a duplicated row, or two rows that disagree.
    The payload therefore never presents a corrupted or ambiguous value as
    ``source: ledger``; ``marker`` stays null because the fixed undeclared marker
    is reserved for "owner parsed, unit simply not registered" (C-7), and the two
    degradation labels stay mutually exclusive.
    """
    record = default_lookup_record(unit_id, stamp)
    record["error"] = {"label": DEGRADATION_LABEL, "detail": detail}
    print("%s: %s" % (DEGRADATION_LABEL, detail), file=sys.stderr)
    emit_lookup(record, output_format)
    return 2


def default_lookup_record(unit_id: str, stamp: str) -> dict:
    return {
        "action": "lookup",
        "checked_at": stamp,
        "unit_id": unit_id,
        CLASS_KEY: DEFAULT_CLASS,
        FLOW_TYPE_KEY: None,
        "source": "default",
        "marker": None,
        "basis": None,
        "neutral": False,
        "error": None,
    }


# --------------------------------------------------------------------------- #
# 077: the feature-line key family (contracts/class-resolution.md)
# --------------------------------------------------------------------------- #
SPEC_KEY_RE = re.compile(r"^spec:([a-z0-9][a-z0-9-]*)$")
SPECS_DIR_REL = Path(".specify") / "specs"
SPECS_DIR_IN_PAYLOAD = Path("specs")
SPEC_REQUIREMENTS = "requirements.md"

# The declaration line: verbatim field name, half-width colon, exactly one space,
# one token, end of line (no trailing whitespace, no inline comment). The closed
# two-value set is judged separately so an out-of-set value is `invalid-class`
# rather than a shape error (data-model E3).
RELATED_FEATURE_HEADING = "## Related Feature"
DECLARATION_LINE_RE = re.compile(r"^\*\*Flow Class\*\*: ([^\s]+)$")
# Presence probe: field-shaped regardless of case, inner spacing or the colon
# that follows. Used to tell "the field is there but wrong" from "there is no
# field at all" (C-006: MUST NOT fall back to "absent"). Leading whitespace is
# tolerated here on purpose — a shifted line is a malformed field, not a missing one.
DECLARATION_PROBE_RE = re.compile(r"^\s*\*\*\s*flow\s+class\s*\*\*", re.IGNORECASE)
DECLARATION_ABSENT = "declaration-absent"

# The document type: a subordinate attribute of ``flow_class`` (owner:
# ``.specify/shared/definitions/flow-class-definitions.md`` § 文档类型). It is optional —
# a line that is absent leaves ``flow_type: null`` — but when present it is
# closed-set and only meaningful for ``expression`` lines; an ``execution`` line
# may carry only the explicit ``-``. Extending the set is an owner revision.
FLOW_TYPE_KEY = "flow_type"
#: Feature 084, batch 1 row 6: the document-type closed set is declared; `-` is its last member.
FLOW_TYPE_VALUES, FLOW_TYPE_LABEL = declared_sequence("flow-class-document-types")
FLOW_TYPE_NONE = FLOW_TYPE_VALUES[-1] if FLOW_TYPE_VALUES else None
FLOW_TYPE_LINE_RE = re.compile(r"^\*\*Flow Type\*\*: ([^\s]+)$")
FLOW_TYPE_PROBE_RE = re.compile(r"^\s*\*\*\s*flow\s+type\s*\*\*", re.IGNORECASE)


def spec_key_name(unit_id: str):
    """Return the spec-directory basename a ``spec:`` key carries, else ``None``.

    The family is closed: ``spec:`` + the spec directory basename, grammar
    ``^spec:[a-z0-9][a-z0-9-]*$``. A bare directory name, ``feature:<ID>`` and any
    ``/``-bearing path are *not* this family — they fall through to the existing
    unit-id judgement and keep its exit 2 (contract C-002). The basename (never a
    path, never a Feature id) is what lets the source tree and the payload tree
    resolve the same line to the same key (research.md R-2).
    """
    match = SPEC_KEY_RE.fullmatch(unit_id or "")
    return match.group(1) if match else None


def spec_requirements_path(repo: Path, name: str) -> Path:
    """Resolve ``<repo>/.specify/specs/<name>/requirements.md`` under both hats.

    ``--repo <proj>`` is the client-payload hat and reads
    ``<proj>/.specify/specs/…``; ``--repo <proj>/.specify`` names the payload
    root itself and degenerates to ``<repo>/specs/…`` (contract
    ``class-resolution.md`` C-003).
    """
    if repo.name == MIRROR_DIR_NAME:
        return repo / SPECS_DIR_IN_PAYLOAD / name / SPEC_REQUIREMENTS
    return repo / SPECS_DIR_REL / name / SPEC_REQUIREMENTS


def display_path(repo: Path, path: Path) -> str:
    """A repo-relative path when possible — diagnostics name the file the author edits."""
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def spec_input_error(repo: Path, unit_id: str, path: Path, stamp: str,
                     output_format: str, detail: str = "") -> int:
    """Exit 2 for a well-formed ``spec:`` key whose line cannot be read.

    Two registrations meet here (contracts/class-resolution.md C-003 / C-006):

    * the label is ``owner-unavailable``, not ``invalid-unit-id``. The key is
      legal — what is missing is the input it names (the spec directory, its
      ``requirements.md``, or a readable copy of it). Requirements FR-009 puts
      "key or input invalid (exit 2)" in the *same* degradation branch as an
      absent owner, and the dispatch payload's ``error`` slot is a closed
      two-value domain ``{owner-unavailable, -}``; a third label here would
      leave the driver's U4 without a branch (code review important-1). The
      distinguishing information moves into ``detail``.
    * ``flow_class`` is ``null``: an exit-2 record must never hand a consumer a
      decided class (C-003 / C-007 — a misspelled spec key would otherwise read
      as a firm ``execution``). ``source`` stays ``default`` because no
      declaration line was read, and ``error.label`` is what keeps that pair
      from being read as "not declared" (C-005, narrowed for this path).
    """
    detail = detail or ("spec input not found: %s" % display_path(repo, path))
    record = default_lookup_record(unit_id, stamp)
    record[CLASS_KEY] = None
    record["error"] = {"label": DEGRADATION_LABEL, "detail": detail}
    print("%s: %s" % (DEGRADATION_LABEL, detail), file=sys.stderr)
    emit_lookup(record, output_format)
    return 2


def parse_spec_declaration(text: str) -> dict:
    """Read the feature line's declaration; the class is never inferred.

    Outcomes, in the order they are judged (data-model E3):

    * ``declaration-duplicate`` — the field appears more than once anywhere in the
      file. Only the count is read; whether the two values agree is irrelevant
      (C-004). It outranks ``declaration-misplaced`` for the same root cause.
    * ``declaration-misplaced`` — the single field line sits after the first
      ``## Related Feature`` heading. Position only (C-005).
    * ``declaration-malformed`` — the field is present but the line is not the
      verbatim form: full-width colon, field-name case variant, trailing
      whitespace, inline comment, leading shift (C-006). It MUST NOT be read as
      "no field at all".
    * ``invalid-class`` — verbatim shape, value outside the closed set (C-009).
    * ``declared`` — verbatim shape with a closed-set value.
    * ``absent`` — no field-shaped line anywhere; the default path (C-008).

    Only the head region and only the verbatim grammar count — nothing here looks
    at the path, the file name, the extension, the body or the commit history
    (requirements FR-001 / contract C-002).
    """
    lines = text.splitlines()
    related_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith(RELATED_FEATURE_HEADING)
        ),
        None,
    )
    field_lines = [
        (index + 1, line)
        for index, line in enumerate(lines)
        if DECLARATION_PROBE_RE.match(line)
    ]

    if len(field_lines) > 1:
        first_line, _first_text = field_lines[0]
        second_line, second_text = field_lines[1]
        return {
            "status": "error",
            "code": "declaration-duplicate",
            "line": second_line,
            "value": declaration_value_fragment(second_text),
            "reason": "the field appears more than once — a second declaration is "
                      "a second source of truth",
            "also_line": first_line,
        }

    if len(field_lines) == 1:
        line_no, line = field_lines[0]
        if related_index is not None and (line_no - 1) > related_index:
            return {
                "status": "error",
                "code": "declaration-misplaced",
                "line": line_no,
                "value": declaration_value_fragment(line),
                "reason": "the declaration belongs in the head region, before "
                          "`%s`" % RELATED_FEATURE_HEADING,
                "also_line": None,
            }
        match = DECLARATION_LINE_RE.fullmatch(line)
        if not match:
            return {
                "status": "error",
                "code": "declaration-malformed",
                "line": line_no,
                "value": line.strip(),
                "reason": "the field must read exactly `**Flow Class**: <class>` — "
                          "half-width colon, one space, no trailing whitespace, no "
                          "inline comment",
                "also_line": None,
            }
        if match.group(1) not in CLASS_VALUES:
            return {
                "status": "error",
                "code": "invalid-class",
                "line": line_no,
                "value": match.group(1),
                "reason": "outside the closed set (%s)" % ", ".join(CLASS_VALUES),
                "also_line": None,
            }
        return {"status": "declared", "value": match.group(1), "line": line_no}

    return {"status": "absent"}


def parse_spec_flow_type(text: str, class_value) -> dict:
    """Read the optional ``**Flow Type**`` line; absent is legal, malformed is not.

    Same head-region and verbatim rules as the class line (owner:
    ``.specify/shared/definitions/flow-class-definitions.md`` § 文档类型). The type is
    subordinate: an ``execution`` line — or the default class when the class line
    is absent — accepts only the explicit ``-``. Author errors use the same exit 1
    as class errors; an absent line leaves ``flow_type: null``.
    """
    lines = text.splitlines()
    related_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith(RELATED_FEATURE_HEADING)
        ),
        None,
    )
    field_lines = [
        (index + 1, line)
        for index, line in enumerate(lines)
        if FLOW_TYPE_PROBE_RE.match(line)
    ]

    if len(field_lines) > 1:
        first_line, _first_text = field_lines[0]
        second_line, second_text = field_lines[1]
        return {
            "status": "error",
            "code": "flow-type-duplicate",
            "line": second_line,
            "value": flow_type_value_fragment(second_text),
            "reason": "the field appears more than once — a second declaration is "
                      "a second source of truth",
            "also_line": first_line,
        }

    if len(field_lines) == 1:
        line_no, line = field_lines[0]
        if related_index is not None and (line_no - 1) > related_index:
            return {
                "status": "error",
                "code": "flow-type-misplaced",
                "line": line_no,
                "value": flow_type_value_fragment(line),
                "reason": "the declaration belongs in the head region, before "
                          "`%s`" % RELATED_FEATURE_HEADING,
                "also_line": None,
            }
        match = FLOW_TYPE_LINE_RE.fullmatch(line)
        if not match:
            return {
                "status": "error",
                "code": "flow-type-malformed",
                "line": line_no,
                "value": line.strip(),
                "reason": "the field must read exactly `**Flow Type**: <type>` — "
                          "half-width colon, one space, no trailing whitespace, no "
                          "inline comment",
                "also_line": None,
            }
        value = match.group(1)
        if value not in FLOW_TYPE_VALUES:
            return {
                "status": "error",
                "code": "invalid-flow-type",
                "line": line_no,
                "value": value,
                "reason": "outside the closed set (%s)" % ", ".join(FLOW_TYPE_VALUES),
                "also_line": None,
            }
        effective_class = class_value if class_value is not None else DEFAULT_CLASS
        if effective_class == EXECUTION and value != FLOW_TYPE_NONE:
            return {
                "status": "error",
                "code": "flow-type-mismatch",
                "line": line_no,
                "value": value,
                "reason": "a document type is only meaningful for expression lines; "
                          "execution lines carry `%s`" % FLOW_TYPE_NONE,
                "also_line": None,
            }
        return {"status": "declared", "value": value, "line": line_no}

    return {"status": "absent"}


def flow_type_value_fragment(line: str) -> str:
    """The value (or the raw line) a diagnostic carries for an offending type field."""
    match = FLOW_TYPE_LINE_RE.fullmatch(line)
    if match:
        return match.group(1)
    return line.strip()


def declaration_value_fragment(line: str) -> str:
    """The value (or the raw line) a diagnostic carries for an offending field."""
    match = DECLARATION_LINE_RE.fullmatch(line)
    if match:
        return match.group(1)
    return line.strip()


def spec_declaration_error(repo: Path, unit_id: str, path: Path, declaration: dict,
                           stamp: str, output_format: str) -> int:
    """Exit 1: an author error in the declaration, never the exit-2 degradation.

    The record carries ``flow_class: null`` + ``source: declaration`` — a consumer
    that reads only the record must not see a decided class, and must not see the
    ``execution`` + ``default`` pair either (C-007). The diagnostic is one stderr
    line naming the file, the line and the offending value (C-008).
    """
    detail = "%s:%d carries '%s', %s" % (
        display_path(repo, path),
        declaration["line"],
        declaration["value"],
        declaration["reason"],
    )
    if declaration.get("also_line"):
        detail += " (first declared at %s:%d)" % (
            display_path(repo, path),
            declaration["also_line"],
        )
    record = default_lookup_record(unit_id, stamp)
    record[CLASS_KEY] = None
    record["source"] = "declaration"
    record["error"] = {"label": declaration["code"], "detail": detail}
    print("%s: %s" % (declaration["code"], detail), file=sys.stderr)
    emit_lookup(record, output_format)
    return 1


def spec_type_error(repo: Path, unit_id: str, path: Path, finding: dict,
                    stamp: str, output_format: str) -> int:
    """Exit 1: an author error in the optional ``**Flow Type**`` line.

    The record carries ``flow_class: null`` and ``flow_type: null`` — an
    undeclared pair must never be presented as decided (C-007's reading, applied
    to the subordinate axis). The diagnostic names the file, the line and the
    offending value, exactly like the class-line errors.
    """
    detail = "%s:%d carries '%s', %s" % (
        display_path(repo, path),
        finding["line"],
        finding["value"],
        finding["reason"],
    )
    if finding.get("also_line"):
        detail += " (first declared at %s:%d)" % (
            display_path(repo, path),
            finding["also_line"],
        )
    record = default_lookup_record(unit_id, stamp)
    record[CLASS_KEY] = None
    record["source"] = "declaration"
    record["error"] = {"label": finding["code"], "detail": detail}
    print("%s: %s" % (finding["code"], detail), file=sys.stderr)
    emit_lookup(record, output_format)
    return 1


def action_lookup_spec(repo: Path, unit_id: str, name: str, stamp: str,
                       output_format: str) -> int:
    """Resolve a feature line's class from its ``requirements.md`` declaration.

    Declared -> ``source: declaration`` with the declared value. No declaration ->
    the default class, ``source: default`` and the 069 marker, plus the advisory
    ``declaration-absent`` in ``error.label``: exit 0, not a finding, never part of
    a gate's pass/fail set. Author errors (duplicate / misplaced / malformed /
    invalid value) -> exit 1, never the exit-2 path (that path is reserved for
    mechanism absence, requirements FR-009). The advisory requires a parsable
    owner — this function only runs after ``parse_owner`` succeeded, so it can
    never coexist with ``owner-unavailable`` (requirements FR-004).
    """
    path = spec_requirements_path(repo, name)
    if not path.is_file():
        return spec_input_error(repo, unit_id, path, stamp, output_format)

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        # Same exit-2 registration as an absent file: the input cannot be read,
        # so no class is decided and the label is the closed degradation one.
        return spec_input_error(
            repo, unit_id, path, stamp, output_format,
            detail="spec requirements unreadable: %s (%s)"
                   % (display_path(repo, path), exc),
        )

    declaration = parse_spec_declaration(text)
    if declaration["status"] == "error":
        return spec_declaration_error(
            repo, unit_id, path, declaration, stamp, output_format
        )

    flow_type = parse_spec_flow_type(
        text,
        declaration["value"] if declaration["status"] == "declared" else None,
    )
    if flow_type["status"] == "error":
        return spec_type_error(repo, unit_id, path, flow_type, stamp, output_format)

    record = default_lookup_record(unit_id, stamp)
    if declaration["status"] == "declared":
        record[CLASS_KEY] = declaration["value"]
        record["source"] = "declaration"
    else:
        record["marker"] = DEFAULT_MARKER
        record["error"] = {
            "label": DECLARATION_ABSENT,
            "detail": (
                "no `**Flow Class**: <class>` line in the head region of %s; "
                "running on the default class" % display_path(repo, path)
            ),
        }
    if flow_type["status"] == "declared":
        record[FLOW_TYPE_KEY] = flow_type["value"]
    emit_lookup(record, output_format)
    return 0


def action_lookup(repo: Path, unit_id: str, output_format: str) -> int:
    stamp = checked_at()

    # contracts/class-resolution.md C-009 (registered change): the owner parses
    # *before* the key family, so an unavailable owner degrades every key — the
    # spec: family included — with the same label. The previous order judged the
    # key grammar first and reported invalid-unit-id for the same input; both are
    # exit 2 and change no gate (requirements FR-011 exemption ①). MUST NOT be
    # silently reverted to the old order.
    try:
        ledger = parse_owner(repo)
    except OwnerError as exc:
        return owner_degradation(unit_id, stamp, str(exc), output_format)

    name = spec_key_name(unit_id)
    if name is not None:
        # A feature line is resolved from its declaration line only; it is never
        # matched against § 逐流程台账, whose row set equals the framework unit
        # inventory (contract C-010).
        return action_lookup_spec(repo, unit_id, name, stamp, output_format)

    if not UNIT_ID_RE.fullmatch(unit_id or ""):
        record = default_lookup_record(unit_id, stamp)
        record["error"] = {
            "label": "invalid-unit-id",
            "detail": "expected /speckit.<stem> or skill:<dir>",
        }
        print(
            "invalid unit id %r: expected /speckit.<stem> or skill:<dir>" % unit_id,
            file=sys.stderr,
        )
        emit_lookup(record, output_format)
        return 2

    matches = [row for row in ledger.rows if row["unit_id"] == unit_id]
    if not matches:
        record = default_lookup_record(unit_id, stamp)
        record["marker"] = DEFAULT_MARKER
        emit_lookup(record, output_format)
        return 0

    if len(matches) > 1:
        values = {row[CLASS_KEY] for row in matches}
        kind = "dual-class" if len(values) > 1 else "duplicate"
        return owner_degradation(
            unit_id,
            stamp,
            "%s: unit %r has %d ledger rows (lines %r, values %r) — a decided class "
            "is unavailable"
            % (kind, unit_id, len(matches), [row["_line"] for row in matches],
               sorted(values)),
            output_format,
        )

    row = matches[0]
    if row[CLASS_KEY] not in CLASS_VALUES:
        return owner_degradation(
            unit_id,
            stamp,
            "invalid-class: unit %r carries %r, outside the closed set %r"
            % (unit_id, row[CLASS_KEY], CLASS_VALUES),
            output_format,
        )

    record = {
        "action": "lookup",
        "checked_at": stamp,
        "unit_id": unit_id,
        CLASS_KEY: row[CLASS_KEY],
        "source": "ledger",
        "marker": None,
        "basis": row["basis"],
        "neutral": unit_id in ledger.neutral_units,
        "error": None,
    }
    emit_lookup(record, output_format)
    return 0


# --------------------------------------------------------------------------- #
# 069b: isomorphism map action (contract contracts/isomorphism-map.md)
# --------------------------------------------------------------------------- #
GATES_OWNER_REL = Path("shared") / "workflow" / "expression-gates.md"
ROSTER_REL = Path("skills") / "external" / "sdd-loop-driver" / "scripts" / "loop-state.py"
MAP_SECTION_KEYWORD = "同构映射"
BOUNDARY_SECTION_KEYWORD = "不可同构边界"
FACE_SECTION_KEYWORD = "六面（封闭集）"
OPERATOR_SECTION_KEYWORD = "阶段算子表"

# Contract C-2 / C-8: the table headers, verbatim.
MAP_HEADER = (
    "阶段",
    "结构（实体 / 关系 / 边界）",
    "流程（阶段与门禁角色）",
    "逻辑（证据 / 契约 / 验收 / 版本 / 所有权）",
    "强制门禁",
    "强制门禁引用",
    "强制状态",
)
BOUNDARY_HEADER = ("边界", "不可互换的判定面", "为什么不能互换", "门禁处理")

# Contract C-4: the status column is a closed two-value set.
ENFORCED = "已强制"
DECLARED_UNENFORCED = "已声明未强制"
STATUS_VALUES = (ENFORCED, DECLARED_UNENFORCED)

# Contract C-5: an enforced row cites concrete gate-operator ids from the gate
# owner's `算子 id` column. The citation is the falsifiable unit: a missing,
# unknown, non-blocking or stage/face-mismatched reference is a finding. Free-text
# semantics stay with the review face (C-10) — the checker never claims to judge
# whether the 24 cells *mean* what they cite.
# ``GATE_ID_COLUMN`` is NOT defined here: feature 084 batch 2 moved the operator table's column set
# to ``.specify/shared/declarations/facts/expression-stage-operator-table.yaml`` and the positional read at the
# top of this module binds member 1 to that name (T014). A local re-assignment would put the second
# copy back.
GATE_REF_PREFIX = "gate:"
GATE_REF_COLUMN = "强制门禁引用"

# Contract C-11 / C-12: the closed phrase sets (case-insensitive).
CODE_OPERATORS = ("pytest", "--cov", "coverage", "go test", "mvn test", "npm test", "jest")
MEDIUM_PHRASES = ("按扩展名", "by extension", ".md 即", ".yaml 即")

ROSTER_START_RE = re.compile(r"^STAGE_ARTIFACTS\s*=\s*\{")
ROSTER_KEY_RE = re.compile(r'^ {4}"([a-z][a-z0-9_-]*)"\s*:\s*\{')
GATE_SPLIT_RE = re.compile(r"[、,，/+\s]+")
GATE_RESIDUAL_RE = re.compile(r"[\s`、,，。；;：:/+\-—（）()\[\]]+")


class RosterError(Exception):
    """The stage roster owner cannot be parsed (a C-13 exit-2 condition)."""


class GateOwnerError(Exception):
    """The gate owner cannot be parsed (a C-13 exit-2 condition)."""


def resolve_shared(repo: Path, rel: Path):
    """Resolve a ``.specify/shared/``-relative path in the framework source, then its mirror."""
    for root in (repo, repo / MIRROR_DIR_NAME):
        path = root / rel
        if path.is_file():
            return path
    return None


def parse_roster(repo: Path) -> list[str]:
    """Return the ``STAGE_ARTIFACTS`` top-level keys, statically parsed.

    The roster is the *owner* of the stage set: this action MUST NOT fall back to
    a built-in eight-stage list, so an empty or missing assignment is an input
    error rather than a silent default.
    """
    path = repo / ROSTER_REL
    if not path.is_file():
        raise RosterError("stage roster owner missing: %s" % (repo / ROSTER_REL))
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise RosterError("stage roster owner unreadable: %s (%s)" % (path, exc))

    start = next((i for i, line in enumerate(lines) if ROSTER_START_RE.match(line)), None)
    if start is None:
        raise RosterError("STAGE_ARTIFACTS assignment not found in %s" % path)
    stages: list[str] = []
    for follow in lines[start + 1:]:
        if follow and not follow.startswith(" "):
            break
        match = ROSTER_KEY_RE.match(follow)
        if match:
            stages.append(match.group(1))
    if not stages:
        raise RosterError("STAGE_ARTIFACTS has no top-level stage keys in %s" % path)
    return stages


class GateOwner:
    def __init__(self, faces, operators):
        self.faces = faces          # list[str] in table order
        self.operators = operators  # list[dict] with id / stage / face / blocking / operator

    @property
    def blocking_pairs(self):
        return {
            (row["stage"], row["face"]) for row in self.operators if row["blocking"]
        }

    @property
    def blocking_stages(self):
        return {row["stage"] for row in self.operators if row["blocking"]}

    @property
    def operators_by_id(self):
        return {row["id"]: row for row in self.operators}


def parse_gate_owner(repo: Path) -> GateOwner:
    path = resolve_shared(repo, GATES_OWNER_REL)
    if path is None:
        raise GateOwnerError("gate owner missing: %s" % (repo / GATES_OWNER_REL))
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise GateOwnerError("gate owner unreadable: %s (%s)" % (path, exc))

    face_body = section_body(lines, FACE_SECTION_KEYWORD)
    if face_body is None:
        raise GateOwnerError("gate owner has no %r section" % FACE_SECTION_KEYWORD)
    face_table = first_table(face_body)
    if face_table is None:
        raise GateOwnerError("gate owner § 六面 has no parseable table")
    face_header, face_rows = face_table
    if "face id" not in face_header:
        raise GateOwnerError("six-face table has no 'face id' column: %r" % (face_header,))
    face_index = face_header.index("face id")
    faces = [
        row[face_index].strip("` ")
        for _line, row in face_rows
        if len(row) == len(face_header) and row[face_index].strip("` ")
    ]
    if not faces:
        raise GateOwnerError("six-face table yielded no face ids")

    operator_body = section_body(lines, OPERATOR_SECTION_KEYWORD)
    if operator_body is None:
        raise GateOwnerError("gate owner has no %r section" % OPERATOR_SECTION_KEYWORD)
    operator_table = first_table(operator_body)
    if operator_table is None:
        raise GateOwnerError("gate owner § 阶段算子表 has no parseable table")
    op_header, op_rows = operator_table
    # The five column names are NOT spelled here: feature 084 batch 2 moved them to
    # `.specify/shared/declarations/facts/expression-stage-operator-table.yaml`, and the positional read at the
    # top of this module binds them in declaration order. The check keeps its shape — each required
    # column must be present in the header, and every row is then resolved by column name — so the
    # refusal message and the exit code are unchanged.
    required = (STEP_COLUMN, GATE_ID_COLUMN, OPERATOR_COLUMN, FACE_COLUMN, LEVEL_COLUMN)
    missing = [column for column in required if column not in op_header]
    if missing:
        raise GateOwnerError(
            "operator table lacks required column(s): %s (header=%r)"
            % (", ".join(missing), op_header)
        )
    operators = []
    seen_ids: set[str] = set()
    for line_no, row in op_rows:
        if len(row) != len(op_header):
            continue
        record = {column: row[op_header.index(column)] for column in required}
        gate_id = record[GATE_ID_COLUMN].strip("` ")
        if not gate_id:
            raise GateOwnerError(
                "operator row on line %d has an empty %r cell" % (line_no, GATE_ID_COLUMN)
            )
        if gate_id in seen_ids:
            raise GateOwnerError(
                "operator id %r appears more than once; a gate reference cannot resolve "
                "deterministically" % gate_id
            )
        seen_ids.add(gate_id)
        operators.append(
            {
                "id": gate_id,
                "stage": record[STEP_COLUMN].strip("` "),
                "face": record[FACE_COLUMN].strip("` "),
                "blocking": record[LEVEL_COLUMN].strip("` ").lower() == "blocking",
                "operator": record[OPERATOR_COLUMN],
            }
        )
    return GateOwner(faces, operators)


def parse_isomorphism_map(repo: Path):
    """Return ``(map_rows, boundary_rows_or_None)``; raise ``OwnerError`` on shape loss.

    A missing/unparsable map *table* is an input error (the checker has no
    subject). A missing boundary table is a finding rather than an input error:
    C-8 names the defect (``boundary-missing``) and the checker can still report
    the map half.
    """
    owner_path = next((path for path in owner_candidates(repo) if path.is_file()), None)
    if owner_path is None:
        raise OwnerError(
            "owner document unreadable: none of %s exists"
            % ", ".join(str(path) for path in owner_candidates(repo))
        )
    try:
        lines = owner_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise OwnerError("owner document unreadable: %s (%s)" % (owner_path, exc))

    map_body = section_body(lines, MAP_SECTION_KEYWORD)
    if map_body is None:
        raise OwnerError("owner document has no %r section" % MAP_SECTION_KEYWORD)
    map_table = first_table(map_body)
    if map_table is None:
        raise OwnerError("owner § 同构映射 has no parseable Markdown table")
    map_header, map_rows = map_table
    if tuple(map_header) != MAP_HEADER:
        raise OwnerError(
            "map header does not match contract C-2 verbatim: got %r" % (map_header,)
        )

    boundary_table = None
    boundary_body = section_body(lines, BOUNDARY_SECTION_KEYWORD)
    if boundary_body is not None:
        boundary_table = first_table(boundary_body)
    return map_rows, boundary_table


def iso_finding(kind: str, stage, message: str) -> dict:
    return {"kind": kind, "stage": stage, "message": message}


def gate_tokens(cell: str) -> list[str]:
    """Split a 强制门禁 cell into candidate tokens (backticks stripped)."""
    cleaned = cell.replace("`", " ")
    return [token for token in GATE_SPLIT_RE.split(cleaned) if token and token not in ("—", "-")]


def face_ids_in(text: str, faces) -> list[str]:
    found = []
    for face in sorted(faces, key=len, reverse=True):
        if re.search(r"(?<![a-z0-9-])%s(?![a-z0-9-])" % re.escape(face), text):
            found.append(face)
    return found


def cell_grammar_problem(cell: str):
    if cell.count("↔") != 1:
        return "expected exactly one '↔', found %d" % cell.count("↔")
    left, right = [part.strip() for part in cell.split("↔")]
    if not left.startswith("代码型："):
        return "left side does not start with '代码型：'"
    if not right.startswith("文档型："):
        return "right side does not start with '文档型：'"
    if len(left) < 8 or len(right) < 8:
        return "a side is shorter than 8 characters (left=%d, right=%d)" % (
            len(left),
            len(right),
        )
    return None


def medium_hits(cell: str) -> list[str]:
    normalized = re.sub(r"\s+", "", cell).lower()
    return [
        phrase
        for phrase in MEDIUM_PHRASES
        if re.sub(r"\s+", "", phrase).lower() in normalized
    ]


def gate_refs(cell: str, gates: GateOwner):
    """Return ``(resolved, problems)`` for one ``强制门禁引用`` cell.

    ``resolved`` is ``[(token, operator_row)]``; ``problems`` is
    ``[(kind, detail)]`` for tokens that are malformed or name no declared id.
    A reference resolves against the gate owner only — the single oracle that can
    say which ``(stage, face)`` an id belongs to and whether it blocks.
    """
    resolved = []
    problems = []
    operators_by_id = gates.operators_by_id
    for token in gate_tokens(cell):
        if not token.startswith(GATE_REF_PREFIX):
            problems.append(
                (
                    "gate-ref-malformed",
                    "%r is not a %r reference" % (token, GATE_REF_PREFIX + "<算子 id>"),
                )
            )
            continue
        gate_id = token[len(GATE_REF_PREFIX):]
        operator = operators_by_id.get(gate_id)
        if operator is None:
            problems.append(
                (
                    "gate-ref-unknown",
                    "%r names no operator id in the gate owner § 阶段算子表" % token,
                )
            )
            continue
        resolved.append((token, operator))
    return resolved, problems


def check_map(rows, roster: list[str], gates: GateOwner) -> list[dict]:
    findings: list[dict] = []
    face_columns = MAP_HEADER[1:4]
    blocking_pairs = gates.blocking_pairs
    blocking_stages = gates.blocking_stages

    stages: list[str] = []
    for line_no, row in rows:
        if len(row) != len(MAP_HEADER):
            findings.append(
                iso_finding(
                    "cell-malformed",
                    row[0].strip("` ") if row else None,
                    "map row on line %d has %d cell(s), expected %d"
                    % (line_no, len(row), len(MAP_HEADER)),
                )
            )
            continue
        stage = row[0].strip("` ")
        stages.append(stage)

        for column in face_columns:
            cell = row[MAP_HEADER.index(column)]
            problem = cell_grammar_problem(cell)
            if problem:
                findings.append(
                    iso_finding(
                        "cell-malformed",
                        stage,
                        "%s cell on line %d: %s" % (column, line_no, problem),
                    )
                )

        status = row[MAP_HEADER.index("强制状态")].strip("` ")
        gate_cell = row[MAP_HEADER.index("强制门禁")]
        ref_cell = row[MAP_HEADER.index(GATE_REF_COLUMN)]
        named = face_ids_in(gate_cell, gates.faces)
        candidates = gate_tokens(gate_cell)
        ref_candidates = gate_tokens(ref_cell)
        unknown = [token for token in candidates if token not in gates.faces]

        if status == ENFORCED:
            if not named:
                findings.append(
                    iso_finding(
                        "slogan-row",
                        stage,
                        "row claims enforcement but names no closed face id",
                    )
                )
            for face in unknown:
                findings.append(
                    iso_finding(
                        "gate-unknown",
                        stage,
                        "face id %r is outside the closed six-face set" % face,
                    )
                )
            for face in named:
                if (stage, face) not in blocking_pairs:
                    findings.append(
                        iso_finding(
                            "annotation-false-enforced",
                            stage,
                            "%r is claimed enforced but has no blocking operator at %r"
                            % (face, stage),
                        )
                    )
            if not ref_candidates:
                findings.append(
                    iso_finding(
                        "gate-ref-missing",
                        stage,
                        "row claims enforcement but carries no %r reference"
                        % (GATE_REF_PREFIX + "<算子 id>"),
                    )
                )
            resolved, problems = gate_refs(ref_cell, gates)
            for kind, detail in problems:
                findings.append(iso_finding(kind, stage, detail))
            covered: set[str] = set()
            for token, operator in resolved:
                if operator["stage"] != stage:
                    findings.append(
                        iso_finding(
                            "gate-ref-mismatch",
                            stage,
                            "%r resolves to stage %r, not this row's stage %r"
                            % (token, operator["stage"], stage),
                        )
                    )
                    continue
                if not operator["blocking"]:
                    findings.append(
                        iso_finding(
                            "gate-ref-not-blocking",
                            stage,
                            "%r resolves to an advisory operator at %r" % (token, stage),
                        )
                    )
                    continue
                if operator["face"] not in named:
                    findings.append(
                        iso_finding(
                            "gate-ref-mismatch",
                            stage,
                            "%r resolves to face %r, which this row does not claim"
                            % (token, operator["face"]),
                        )
                    )
                covered.add(operator["face"])
            for face in named:
                if face not in covered:
                    findings.append(
                        iso_finding(
                            "gate-ref-missing",
                            stage,
                            "%r has no resolving blocking %r reference"
                            % (face, GATE_REF_PREFIX + "<算子 id>"),
                        )
                    )
        elif status == DECLARED_UNENFORCED:
            if candidates or ref_candidates:
                findings.append(
                    iso_finding(
                        "status-invalid",
                        stage,
                        "已声明未强制 must leave 强制门禁 / 强制门禁引用 empty, found %r"
                        % (candidates + ref_candidates,),
                    )
                )
            if stage in blocking_stages:
                findings.append(
                    iso_finding(
                        "annotation-false-unenforced",
                        stage,
                        "stage %r has blocking operator(s) but is declared unenforced" % stage,
                    )
                )
        elif status:
            findings.append(
                iso_finding(
                    "status-invalid",
                    stage,
                    "强制状态 %r is outside the closed set %r" % (status, STATUS_VALUES),
                )
            )
        else:
            findings.append(
                iso_finding(
                    "slogan-row",
                    stage,
                    "row carries neither a closed face id nor the 已声明未强制 annotation",
                )
            )

    if len(rows) != len(roster):
        findings.append(
            iso_finding(
                "stage-set-mismatch",
                None,
                "map has %d data row(s), the roster has %d stage(s)" % (len(rows), len(roster)),
            )
        )
    if len(stages) != len(set(stages)) or set(stages) != set(roster):
        findings.append(
            iso_finding(
                "stage-set-mismatch",
                None,
                "map stage set %r does not equal the roster keys %r"
                % (sorted(set(stages)), sorted(roster)),
            )
        )

    for _line_no, row in rows:
        if len(row) != len(MAP_HEADER):
            continue
        for column in face_columns:
            hits = medium_hits(row[MAP_HEADER.index(column)])
            if hits:
                findings.append(
                    iso_finding(
                        "medium-axis-in-map",
                        row[0].strip("` "),
                        "%s cell uses a medium-axis phrase as the classification reason: %r"
                        % (column, hits),
                    )
                )
    return findings


def check_boundaries(boundary_table, gates: GateOwner) -> list[dict]:
    findings: list[dict] = []
    if boundary_table is None:
        return [
            iso_finding(
                "boundary-missing",
                None,
                "owner has no § %s table; all four boundaries are absent"
                % BOUNDARY_SECTION_KEYWORD,
            )
        ]
    header, rows = boundary_table
    if tuple(header) != BOUNDARY_HEADER:
        findings.append(
            iso_finding(
                "boundary-malformed",
                None,
                "boundary header does not match contract C-8 verbatim: got %r" % (header,),
            )
        )

    def column(name: str) -> int:
        return header.index(name) if name in header else BOUNDARY_HEADER.index(name)

    seen: list[str] = []
    for line_no, row in rows:
        if len(row) != len(BOUNDARY_HEADER):
            findings.append(
                iso_finding(
                    "boundary-malformed",
                    None,
                    "boundary row on line %d has %d cell(s), expected %d"
                    % (line_no, len(row), len(BOUNDARY_HEADER)),
                )
            )
            continue
        boundary = row[0].strip("` ")
        if boundary not in ("a", "b", "c", "d"):
            findings.append(
                iso_finding(
                    "boundary-missing",
                    None,
                    "unknown boundary id %r on line %d" % (boundary, line_no),
                )
            )
            continue
        seen.append(boundary)

        reason = row[column("为什么不能互换")].strip()
        if not reason:
            findings.append(
                iso_finding(
                    "boundary-malformed",
                    None,
                    "boundary %r has an empty 为什么不能互换 cell" % boundary,
                )
            )

        handling = row[column("门禁处理")].strip()
        named = face_ids_in(handling, gates.faces)
        if not named:
            findings.append(
                iso_finding(
                    "boundary-unbound",
                    None,
                    "boundary %r names no closed face id in 门禁处理" % boundary,
                )
            )
        else:
            residual = handling
            for face in named:
                residual = residual.replace(face, "")
            if len(GATE_RESIDUAL_RE.sub("", residual)) < 4:
                findings.append(
                    iso_finding(
                        "boundary-malformed",
                        None,
                        "boundary %r lists face id(s) but no handling explanation" % boundary,
                    )
                )

    for boundary in ("a", "b", "c", "d"):
        count = seen.count(boundary)
        if count == 0:
            findings.append(
                iso_finding("boundary-missing", None, "boundary %r is missing" % boundary)
            )
        elif count > 1:
            findings.append(
                iso_finding(
                    "boundary-missing",
                    None,
                    "boundary %r appears %d times" % (boundary, count),
                )
            )
    return findings


def check_code_operators(gates: GateOwner) -> list[dict]:
    findings: list[dict] = []
    for row in gates.operators:
        lowered = row["operator"].lower()
        for token in CODE_OPERATORS:
            if token in lowered:
                findings.append(
                    iso_finding(
                        "code-operator-in-expression-gates",
                        row["stage"],
                        "执行算子 carries the code-type operator %r: %r"
                        % (token, row["operator"]),
                    )
                )
                break
    return findings


def render_isomorphism_text(record: dict) -> str:
    lines = [
        "flow-class isomorphism: %d stage row(s), %d gate face(s), %d finding(s)"
        % (record["stages"], record["gates"], len(record["findings"]))
    ]
    for item in record["findings"]:
        location = item.get("stage") or "-"
        lines.append("  [%s] %s — %s" % (item["kind"], location, item["message"]))
    return "\n".join(lines)


def emit_isomorphism(record: dict, output_format: str, code: int) -> int:
    if output_format == "json":
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        if record["error"]:
            print("%s: %s" % (record["error"]["label"], record["error"]["detail"]))
        else:
            print(render_isomorphism_text(record))
    return code


def isomorphism_input_error(record: dict, label: str, detail: str, output_format: str) -> int:
    record["error"] = {"label": label, "detail": detail}
    print("%s: %s" % (label, detail), file=sys.stderr)
    return emit_isomorphism(record, output_format, 2)


def action_isomorphism(repo: Path, output_format: str) -> int:
    record = {
        "action": "isomorphism",
        "checked_at": checked_at(),
        "repo": str(repo),
        "stages": 0,
        "gates": 0,
        "findings": [],
        "error": None,
    }

    # C-13: this action only runs in a framework source tree. A payload root
    # (client `.specify/` shape) is an input error, never a green verdict.
    if not is_framework_source(repo):
        return isomorphism_input_error(
            record,
            "framework-source-required",
            "neither .specify/templates/commands/ nor a parseable skills/{external,internal}/ is present in %s"
            % repo,
            output_format,
        )

    try:
        roster = parse_roster(repo)
    except RosterError as exc:
        return isomorphism_input_error(record, "roster-unavailable", str(exc), output_format)

    try:
        gates = parse_gate_owner(repo)
    except GateOwnerError as exc:
        return isomorphism_input_error(
            record, "gate-owner-unavailable", str(exc), output_format
        )

    try:
        map_rows, boundary_table = parse_isomorphism_map(repo)
    except OwnerError as exc:
        return isomorphism_input_error(record, DEGRADATION_LABEL, str(exc), output_format)

    record["stages"] = len(map_rows)
    record["gates"] = len(gates.faces)

    findings: list[dict] = []
    findings.extend(check_map(map_rows, roster, gates))
    findings.extend(check_boundaries(boundary_table, gates))
    findings.extend(check_code_operators(gates))
    record["findings"] = findings
    return emit_isomorphism(record, output_format, 1 if findings else 0)


def is_framework_source(repo: Path) -> bool:
    if (repo / COMMANDS_REL).is_dir():
        return True
    for layer in SKILL_LAYERS:
        layer_dir = repo / SKILLS_REL / layer
        if layer_dir.is_dir() and any(layer_dir.glob("*/SKILL.md")):
            return True
    return False


def payload_root_label(repo: Path) -> str:
    """Name a non-framework root: owner-unavailable outranks the payload label.

    Contract C-14 / C-3: both are named non-green states. When the owner is also
    missing, the more specific ``owner-unavailable`` wins; otherwise the root is a
    client payload and ``framework-source-required`` is the state.
    """
    if any(path.is_file() for path in owner_candidates(repo)):
        return RED_FRAMEWORK_SOURCE_REQUIRED
    return RED_OWNER_UNAVAILABLE


def resolve_any(repo: Path, rel: str):
    """Resolve a repository-relative path in the source root, then the mirror."""
    for root in (repo, repo / MIRROR_DIR_NAME):
        candidate = root / rel
        if candidate.is_file():
            return candidate
    return None


def markdown_tables(lines: list[str]):
    """Yield ``(header_cells, [(line_no, cells), ...])`` for every Markdown table."""
    index = 0
    while index < len(lines):
        if not lines[index].lstrip().startswith("|"):
            index += 1
            continue
        if index + 1 >= len(lines) or not lines[index + 1].lstrip().startswith("|"):
            index += 1
            continue
        header = cells(lines[index])
        if not is_separator(cells(lines[index + 1])):
            index += 1
            continue
        rows: list[tuple[int, list[str]]] = []
        cursor = index + 2
        while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
            row = cells(lines[cursor])
            if not is_separator(row):
                rows.append((cursor + 1, row))
            cursor += 1
        yield header, rows
        index = cursor


# --------------------------------------------------------------------------- #
# 069b: delegation edges (contract contracts/ledger-reconciler.md C-8…C-10)
# --------------------------------------------------------------------------- #
# C-8: the declared grammar. The name class is the ledger's unit-id class, so a
# placeholder such as ``skills/<name>/SKILL.md`` can never become an edge.
DELEGATION_EDGE_RE = re.compile(
    r"(?:\.specify/)?skills/(?:external/|internal/)?([a-z0-9][a-z0-9-]*)/SKILL\.md"
)
DELEGATION_MIN_HAND_LIST_ROWS = 3
HAND_LIST_COMMAND_RE = re.compile(r"(?<![A-Za-z0-9_-])/speckit\.[a-z0-9][a-z0-9-]*")
HAND_LIST_SKILL_RE = re.compile(r"(?<![A-Za-z0-9_-])skill:[a-z0-9][a-z0-9-]*")
BACKTICK_TOKEN_RE = re.compile(r"`([^`]+)`")
PATH_LIKE_RE = re.compile(r"^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+$")

SPEC_DIR_REL = Path(".specify") / "specs" / "069b-isomorphism-migration-metrics"
S3_OWNER_PATHS_ASSIGN_RE = re.compile(r"^OWNER_PATHS\s*=\s*\((.*?)\)", re.S | re.M)


def formal_spec_artifacts(repo: Path) -> list[Path]:
    """This slice's formal artifacts — ``notes/`` records are not formal.

    Contract C-12 / C-9 close the scan scope at "this spec's formal artifacts";
    dated run records under ``notes/`` are evidence, not specification, and the
    fixtures never contain a spec directory at all.
    """
    spec = repo / SPEC_DIR_REL
    if not spec.is_dir():
        return []
    return [
        path
        for path in sorted(spec.rglob("*.md"))
        if path.is_file() and "notes" not in path.relative_to(spec).parts
    ]


def scope_markdown_files(repo: Path) -> list[Path]:
    """The closed scan scope: .specify/shared/, the command templates, skills/, the spec."""
    files: list[Path] = []
    for root_rel in (Path("shared"), COMMANDS_REL, SKILLS_REL):
        root = repo / root_rel
        if root.is_dir():
            files.extend(sorted(path for path in root.rglob("*.md") if path.is_file()))
    files.extend(formal_spec_artifacts(repo))
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in files:
        key = path.resolve()
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def s3_owner_paths() -> frozenset[str]:
    """Read the S3 comparison set from its owner engine's ``OWNER_PATHS`` literal.

    Contract C-12 excludes that set from the second-table scan. It is read from
    ``doc-consistency-check.py`` (the declared owner) instead of keeping a second
    copy here; an unreadable assignment degrades to an empty set, which only makes
    the scan *stricter* (more files checked), never more permissive.
    """
    engine = Path(__file__).resolve().parent / "doc-consistency-check.py"
    try:
        text = engine.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return frozenset()
    match = S3_OWNER_PATHS_ASSIGN_RE.search(text)
    if not match:
        return frozenset()
    return frozenset(re.findall(r"[\"']([^\"']+)[\"']", match.group(1)))


def ledger_class_map(ledger: OwnerLedger) -> dict[str, str]:
    classes: dict[str, str] = {}
    for row in ledger.rows:
        if row[CLASS_KEY] in CLASS_VALUES:
            classes[row["unit_id"]] = row[CLASS_KEY]
    return classes


def parse_delegation_edges(repo: Path):
    """Return ``(edges, commands_scanned)``; per-template de-duplication (C-8)."""
    commands_dir = repo / COMMANDS_REL
    if not commands_dir.is_dir():
        return [], 0
    paths = sorted(path for path in commands_dir.glob("*.md") if path.is_file())
    edges: list[dict] = []
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        command = "/speckit.%s" % path.stem
        seen: set[str] = set()
        for number, line in enumerate(lines, 1):
            for match in DELEGATION_EDGE_RE.finditer(line):
                name = match.group(1)
                if name in seen:
                    continue
                seen.add(name)
                edges.append(
                    {
                        "command": command,
                        "skill": "skill:%s" % name,
                        "source_line": number,
                    }
                )
    return edges, len(paths)


def judge_delegation(edges, classes, neutral_units):
    """Return ``(edge_records, findings)`` with the fixed verdict order (C-8)."""
    records: list[dict] = []
    findings: list[dict] = []
    for edge in edges:
        skill = edge["skill"]
        command_class = classes.get(edge["command"])
        skill_class = classes.get(skill)
        if skill not in classes:
            verdict = "unknown-skill"
        elif skill in neutral_units:
            # C-8 / C-10: a closed-list member is exempt whatever the two classes
            # are — the exemption is taken from the owner, never copied here.
            verdict = "neutral-exempt"
        elif command_class == skill_class:
            verdict = "same-class"
        else:
            verdict = "mismatch"
        records.append(
            dict(edge, command_class=command_class, skill_class=skill_class, verdict=verdict)
        )
        if verdict == "mismatch":
            findings.append(
                finding(
                    "delegation-mismatch",
                    edge["command"],
                    message="%s (%r) delegates to %s (%r) — a command and its delegated "
                    "skill MUST share one class"
                    % (edge["command"], command_class, skill, skill_class),
                    line=edge["source_line"],
                )
            )
        elif verdict == "unknown-skill":
            findings.append(
                finding(
                    "delegation-unknown-skill",
                    skill,
                    message="%s delegates to %s, which has no ledger row"
                    % (edge["command"], skill),
                    line=edge["source_line"],
                )
            )
    return records, findings


def scan_hand_lists(repo: Path) -> list[dict]:
    """C-9: a hand-maintained command→skill table outside the templates.

    A row counts as a pair when it carries a command id and a skill id; three such
    rows in one table are the contracted minimum. The command templates are the
    only legitimate place for delegation facts, so ``.specify/templates/commands/`` is
    skipped as a source and used as the parse side instead.
    """
    findings: list[dict] = []
    templates = (repo / COMMANDS_REL).resolve()
    for path in scope_markdown_files(repo):
        if path.resolve().parent == templates:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for header, rows in markdown_tables(lines):
            pairs = [
                line_no
                for line_no, row in rows
                if HAND_LIST_COMMAND_RE.search(" | ".join(row))
                and HAND_LIST_SKILL_RE.search(" | ".join(row))
            ]
            if len(pairs) < DELEGATION_MIN_HAND_LIST_ROWS:
                continue
            findings.append(
                finding(
                    "delegation-hand-list",
                    None,
                    message="%s carries a %d-row command→skill table; delegation MUST be "
                    "parsed from the templates, never maintained by hand"
                    % (path.relative_to(repo).as_posix(), len(pairs)),
                    line=pairs[0],
                )
            )
            break
    return findings


def render_delegation_text(record: dict) -> str:
    verdicts: dict[str, int] = {}
    for edge in record["edges"]:
        verdicts[edge["verdict"]] = verdicts.get(edge["verdict"], 0) + 1
    lines = [
        "flow-class delegation: %d template(s) scanned, %d edge(s), %d finding(s)"
        % (record["commands_scanned"], len(record["edges"]), len(record["findings"]))
    ]
    if verdicts:
        lines.append(
            "verdicts: "
            + ", ".join("%s=%d" % (key, verdicts[key]) for key in sorted(verdicts))
        )
    for item in record["findings"]:
        location = item.get("unit_id") or "-"
        if item.get("line"):
            location = "%s (line %d)" % (location, item["line"])
        lines.append("  [%s] %s — %s" % (item["kind"], location, item["message"]))
    return "\n".join(lines)


def emit_delegation(record: dict, output_format: str, code: int) -> int:
    if output_format == "json":
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        if record["error"]:
            print("%s: %s" % (record["error"]["label"], record["error"]["detail"]))
        else:
            print(render_delegation_text(record))
    return code


def action_delegation(repo: Path, output_format: str) -> int:
    record = {
        "action": "delegation",
        "checked_at": checked_at(),
        "repo": str(repo),
        "commands_scanned": 0,
        "edges": [],
        "findings": [],
        "error": None,
    }

    try:
        ledger = parse_owner(repo)
    except OwnerError as exc:
        record["error"] = {"label": RED_OWNER_UNAVAILABLE, "detail": str(exc)}
        print("%s: %s" % (RED_OWNER_UNAVAILABLE, exc), file=sys.stderr)
        return emit_delegation(record, output_format, 2)

    if not is_framework_source(repo):
        label = payload_root_label(repo)
        detail = (
            "neither .specify/templates/commands/ nor a parseable skills/{external,internal}/ "
            "is present in %s" % repo
        )
        record["error"] = {"label": label, "detail": detail}
        print("%s: %s" % (label, detail), file=sys.stderr)
        return emit_delegation(record, output_format, 2)

    edges, scanned = parse_delegation_edges(repo)
    records, findings = judge_delegation(
        edges, ledger_class_map(ledger), ledger.neutral_units
    )
    record["commands_scanned"] = scanned
    record["edges"] = records
    record["findings"] = scan_hand_lists(repo) + findings
    return emit_delegation(record, output_format, 1 if record["findings"] else 0)


# --------------------------------------------------------------------------- #
# 069b: six-face bindings (contract contracts/ledger-reconciler.md C-11 / C-12)
# --------------------------------------------------------------------------- #
# ``FACES_SECTION_KEYWORD`` / ``FACES_EXPECTED`` are NOT assigned here: feature 084 batch 2 moved the
# six-face gate's shape to ``.specify/shared/declarations/facts/expression-gate-faces.yaml`` and the read at the
# top of this module binds them (T014). A local re-assignment would shadow that read and put the second
# copy back — this module refuses to judge when the read is empty (see :func:`main`), so no local
# fallback belongs here either.
FACE_ID_COLUMN = "face id"
FACE_POINTER_COLUMN = "owner_pointer"


def pointer_bindings(cell: str) -> list[tuple[str, str | None]]:
    """Split one ``owner_pointer`` cell into ``(path, anchor)`` pairs (C-11).

    A cell joining several paths with ``+`` is still **one** binding; each segment
    carries its own optional ``§ <anchor>``.
    """
    bindings: list[tuple[str, str | None]] = []
    for segment in cell.split("+"):
        match = BACKTICK_TOKEN_RE.search(segment)
        if not match:
            continue
        path = match.group(1).strip()
        anchor = None
        if "§" in segment:
            tail = segment.split("§", 1)[1]
            anchor = BACKTICK_TOKEN_RE.sub("", tail)
            anchor = re.sub(r"[（(].*?[）)]", "", anchor).strip("` ").strip()
        bindings.append((path, anchor or None))
    return bindings


def anchor_matches(path: Path, anchor: str) -> bool:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return False
    for line in lines:
        match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if match and anchor in match.group(2):
            return True
    return False


def scan_second_face_tables(repo: Path, faces: list[str]) -> list[dict]:
    """C-12: no second table pairs ≥3 face ids with owner paths.

    The six-face table itself lives in the gate owner, which C-12 excludes by
    wording; the S3 comparison set is excluded per the contract and read from its
    owner instead of being copied.
    """
    findings: list[dict] = []
    gate_owner = resolve_shared(repo, GATES_OWNER_REL)
    gate_owner_resolved = gate_owner.resolve() if gate_owner is not None else None
    s3 = s3_owner_paths()
    for path in scope_markdown_files(repo):
        resolved = path.resolve()
        if resolved == gate_owner_resolved:
            continue
        if path.relative_to(repo).as_posix() in s3:
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for header, rows in markdown_tables(lines):
            hits = []
            for line_no, row in rows:
                text = " | ".join(row)
                named = face_ids_in(text, faces)
                paths = [
                    token
                    for token in BACKTICK_TOKEN_RE.findall(text)
                    if PATH_LIKE_RE.match(token.strip())
                ]
                if named and paths:
                    hits.append(line_no)
            if len(hits) < 3:
                continue
            findings.append(
                finding(
                    "faces-second-table",
                    None,
                    message="%s pairs %d face id(s) with owner paths outside § %s; the "
                    "face table is owned once by %s"
                    % (
                        path.relative_to(repo).as_posix(),
                        len(hits),
                        FACES_SECTION_KEYWORD,
                        GATES_OWNER_REL.as_posix(),
                    ),
                    line=hits[0],
                )
            )
            break
    return findings


def check_faces(repo: Path, header, rows) -> tuple[list[str], list[dict]]:
    """Return ``(face ids, findings)`` for the parsed six-face table (C-11)."""
    findings: list[dict] = []
    if FACE_ID_COLUMN not in header or FACE_POINTER_COLUMN not in header:
        raise GateOwnerError(
            "six-face table lacks the %r / %r column(s): header=%r"
            % (FACE_ID_COLUMN, FACE_POINTER_COLUMN, header)
        )
    face_index = header.index(FACE_ID_COLUMN)
    pointer_index = header.index(FACE_POINTER_COLUMN)

    if len(rows) != FACES_EXPECTED:
        findings.append(
            finding(
                "faces-count",
                None,
                message="§ %s carries %d data row(s); the closed set is exactly %d"
                % (FACES_SECTION_KEYWORD, len(rows), FACES_EXPECTED),
            )
        )

    face_ids: list[str] = []
    seen: dict[str, int] = {}
    for line_no, row in rows:
        if len(row) != len(header):
            findings.append(
                finding(
                    "faces-count",
                    None,
                    message="face row on line %d has %d cell(s); the header declares %d"
                    % (line_no, len(row), len(header)),
                    line=line_no,
                )
            )
            continue
        face_id = row[face_index].strip("` ")
        face_ids.append(face_id)
        if face_id in seen:
            findings.append(
                finding(
                    "faces-duplicate",
                    face_id,
                    message="face id %r appears on lines %d and %d"
                    % (face_id, seen[face_id], line_no),
                    line=line_no,
                )
            )
        else:
            seen[face_id] = line_no

        cell = row[pointer_index]
        if not cell.strip():
            findings.append(
                finding(
                    "faces-pointer-missing",
                    face_id,
                    message="face %r has an empty %s cell"
                    % (face_id, FACE_POINTER_COLUMN),
                    line=line_no,
                )
            )
            continue
        bindings = pointer_bindings(cell)
        if not bindings:
            findings.append(
                finding(
                    "faces-pointer-missing",
                    face_id,
                    message="face %r names no backticked path in its %s cell"
                    % (face_id, FACE_POINTER_COLUMN),
                    line=line_no,
                )
            )
            continue
        for rel, anchor in bindings:
            resolved = resolve_any(repo, rel)
            if resolved is None:
                findings.append(
                    finding(
                        "faces-unresolvable",
                        face_id,
                        message="face %r points at %r, which resolves in neither the "
                        "source root nor the %s mirror"
                        % (face_id, rel, MIRROR_DIR_NAME),
                        line=line_no,
                    )
                )
                continue
            if anchor and not anchor_matches(resolved, anchor):
                findings.append(
                    finding(
                        "faces-unresolvable",
                        face_id,
                        message="face %r anchor %r has no matching heading in %s"
                        % (face_id, anchor, rel),
                        line=line_no,
                    )
                )
    return face_ids, findings


def render_faces_text(record: dict) -> str:
    lines = [
        "flow-class faces: %d face(s) parsed, %d finding(s)"
        % (record["faces"], len(record["findings"]))
    ]
    for item in record["findings"]:
        location = item.get("unit_id") or "-"
        if item.get("line"):
            location = "%s (line %d)" % (location, item["line"])
        lines.append("  [%s] %s — %s" % (item["kind"], location, item["message"]))
    return "\n".join(lines)


def emit_faces(record: dict, output_format: str, code: int) -> int:
    if output_format == "json":
        print(json.dumps(record, ensure_ascii=False, indent=2))
    else:
        if record["error"]:
            print("%s: %s" % (record["error"]["label"], record["error"]["detail"]))
        else:
            print(render_faces_text(record))
    return code


def action_faces(repo: Path, output_format: str) -> int:
    record = {
        "action": "faces",
        "checked_at": checked_at(),
        "repo": str(repo),
        "faces": 0,
        "findings": [],
        "error": None,
    }

    if not is_framework_source(repo):
        label = payload_root_label(repo)
        detail = (
            "neither .specify/templates/commands/ nor a parseable skills/{external,internal}/ "
            "is present in %s" % repo
        )
        record["error"] = {"label": label, "detail": detail}
        print("%s: %s" % (label, detail), file=sys.stderr)
        return emit_faces(record, output_format, 2)

    path = resolve_shared(repo, GATES_OWNER_REL)
    if path is None:
        detail = "gate owner missing: %s" % (repo / GATES_OWNER_REL)
        record["error"] = {"label": "gate-owner-unavailable", "detail": detail}
        print("gate-owner-unavailable: %s" % detail, file=sys.stderr)
        return emit_faces(record, output_format, 2)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        detail = "gate owner unreadable: %s (%s)" % (path, exc)
        record["error"] = {"label": "gate-owner-unavailable", "detail": detail}
        print("gate-owner-unavailable: %s" % detail, file=sys.stderr)
        return emit_faces(record, output_format, 2)

    body = section_body(lines, FACES_SECTION_KEYWORD)
    if body is None:
        detail = "gate owner has no § %s section" % FACES_SECTION_KEYWORD
        record["error"] = {"label": "gate-owner-unavailable", "detail": detail}
        print("gate-owner-unavailable: %s" % detail, file=sys.stderr)
        return emit_faces(record, output_format, 2)
    table = first_table(body)
    if table is None:
        detail = "gate owner § %s has no parseable table" % FACES_SECTION_KEYWORD
        record["error"] = {"label": "gate-owner-unavailable", "detail": detail}
        print("gate-owner-unavailable: %s" % detail, file=sys.stderr)
        return emit_faces(record, output_format, 2)

    header, rows = table
    try:
        face_ids, findings = check_faces(repo, header, rows)
    except GateOwnerError as exc:
        record["error"] = {"label": "gate-owner-unavailable", "detail": str(exc)}
        print("gate-owner-unavailable: %s" % exc, file=sys.stderr)
        return emit_faces(record, output_format, 2)

    record["faces"] = len(rows)
    findings.extend(scan_second_face_tables(repo, face_ids))
    record["findings"] = findings
    return emit_faces(record, output_format, 1 if findings else 0)


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flow-class-check.py",
        description=(
            "Reconcile the flow-class ledger and resolve a unit's class "
            "(owner: .specify/shared/definitions/flow-class-definitions.md)."
        ),
    )
    _sig_configure(parser)

    parser.add_argument(
        "--action",
        required=True,
        choices=("check", "lookup", "isomorphism", "delegation", "faces"),
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="repository root to inspect (default: resolved from this script)",
    )
    parser.add_argument("--unit-id", default=None, help="unit id for --action lookup")
    parser.add_argument("--format", default="text", choices=("text", "json"))
    return parser


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
    _sig_guard(argv, declared=['--action', '--repo', '--unit-id', '--format'])  # answer --version / reject an undeclared option
    args = build_parser().parse_args(argv)
    repo = Path(args.repo).expanduser().resolve() if args.repo else find_repo_root()
    if not repo.is_dir():
        print("repository root is not a directory: %s" % repo, file=sys.stderr)
        return 2

    # Feature 084 / FR-012: the closed sets this engine compares against are declarations. A project
    # whose layer is missing cannot be judged — and MUST NOT be judged against values this script no
    # longer carries — so the degradation is an explicit exit-2 label naming each unreadable fact,
    # never a traceback and never a green verdict (C-049).
    labels = [label for label in (CLASS_VALUES_LABEL, BASIS_VALUES_LABEL, NEUTRAL_CATEGORIES_LABEL,
                                 LEDGER_COLUMNS_LABEL, FLOW_TYPE_LABEL,
                                 FACES_DECLARED_LABEL, OPERATOR_COLUMNS_LABEL) if label]
    if labels:
        for label in labels:
            print(label, file=sys.stderr)
        print("flow-class-check: refusing to judge against an absent closed set "
              "(declaration layer unreadable)", file=sys.stderr)
        return 2

    if args.action == "lookup":
        if not args.unit_id:
            print("--action lookup requires --unit-id <id>", file=sys.stderr)
            return 2
        return action_lookup(repo, args.unit_id, args.format)
    if args.action == "isomorphism":
        return action_isomorphism(repo, args.format)
    if args.action == "delegation":
        return action_delegation(repo, args.format)
    if args.action == "faces":
        return action_faces(repo, args.format)
    return action_check(repo, args.format)


if __name__ == "__main__":
    sys.exit(main())
