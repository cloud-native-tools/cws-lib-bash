#!/usr/bin/env python3
"""SDD routing / authorization engine (Feature 074, slice 074a-authorized-routing).

One read-only, stdlib-only engine. It never writes a file, and it never creates a second copy
of a fact another surface owns.

Actions landed here by slice `074a-authorized-routing`:

    route       classify one write-bearing change into one of the three verdicts the
                owner document declares
    authorize   resolve the effective SDD invocation authorization for one (team, seat)
    golden      judge every row of the owner document's golden case table

--action route
--------------
    python3 .specify/scripts/python/sdd-route.py --action route \
        --nature <change_nature> --traceability <traceability> \
        --blast-radius <blast_radius> --reversibility <reversibility> \
        --complexity <complexity> [--rationale TEXT] [--actor ID] \
        [--recorded-at STAMP] [--owner-doc PATH] [--format json|text]

Every input flag is optional on purpose: an absent flag is a missing input, and a missing
input is an adjudicate verdict ([[STR-006]]), never a defaulted one. A value outside the
declared closed domain is ambiguous, likewise adjudicate. `--rationale` carries the
non-empty rationale a `definition-class` bounded correction requires; absent or blank, that
is a missing input.

--action golden
---------------
    python3 .specify/scripts/python/sdd-route.py --action golden [--owner-doc PATH] [--format json|text]

It parses the owner document's § Golden case table and judges every row, in table order. A
row that does not match its expected verdict / reason code is reported as a judged finding
in the payload (`match: false`) and still exits 0: a mismatch is a produced judgement, not
an engine failure, and this exit alphabet has exactly two meanings (see below).

--action authorize
------------------
    python3 .specify/scripts/python/sdd-route.py --action authorize \
        --agent <agent-definition.md> --team <team-slug> --seat <seat-slug> [--format json|text]

It reads exactly two sources: the agent definition's frontmatter (the agent half) and
`.specify/teams/<team-slug>/team.md`, resolved from the working directory (the seat half). Both
coordinates are required — the policy resolves by (team, seat), so a payload carrying only the
seat cannot satisfy the predicate.

Owner pointers (cited, never restated here):

  * the routing rule's four owned facts — the five inputs' closed value domains, the
    three-value verdict table, the fixed precedence and the reason-code vocabulary — plus the
    golden case table: `.specify/shared/definitions/sdd-routing-definitions.md`, the only surface that
    writes them out. This engine reads them from that document at run time and carries no
    copy of them: no domain list, no condition-to-verdict mapping, no precedence order, no
    reason-code literal, no verdict literal. What it does carry is the *interface* — the five
    input identifiers, the condition identifiers, and the named value handles that document
    declares — because a predicate has to be addressed by some name;
  * the closed value set, the absent-key default, and the framework-only (never
    host-rendered) status of the authorization key: NEUTRAL_AGENT_METADATA_KEYS /
    NEUTRAL_AGENT_FRAMEWORK_KEYS in src/specify_cli/__init__.py;
  * the seat-side block map in team.md and its malformed/dangling rules:
    .specify/skills/internal/create-team/references/create-mode.md, section "Persisted team.md schema";
  * the two-half AND, the refused-but-not-an-error exit alphabet, and the requirement that a
    refusal be recheckable: `.specify/specs/074a-authorized-routing/contracts/
    hierarchy-and-authorization.md`, clauses C-6, C-7, C-8 and C-14;
  * the routing decision's mechanics, the exit alphabet and the golden table's shape:
    `.specify/specs/074a-authorized-routing/contracts/routing-decision.md`, clauses C-23,
    C-24, C-28 and C-29.

Exit alphabet — exactly two meanings, and no third:

  0  a verdict was produced. An allow and a refusal are both verdicts (`authorize`); the
     adjudicate verdict is a verdict as well (`route`), so an adjudication can never be
     confused with "the engine broke"; a golden row that does not match is likewise a produced
     judgement. A refusal is carried by the record's verdict / reason / failed_half fields,
     never by the process status, because a caller that must record a decision cannot also
     read it as an engine failure.
  2  malformed or unreadable input — a missing coordinate, an unreadable or frontmatter-less
     file, a flow-style seat map, a seat entry matching no roster member, a declared value
     outside the closed set, or an owner document one of whose machine-readable surfaces
     cannot be read. Malformed input is never a policy or routing value.

The engine never reads a clock: two evaluations of the same inputs must be byte-identical
(C-24), so `recorded_at` is carried through from `--recorded-at` and defaults to null. It
resolves the owner document from its own location, never by walking up to an ancestor
directory — the two-hats trap, where a "nearest ancestor holding .specify/" heuristic
self-matches inside the framework repository and resolves the caller's work onto the
framework's own tree.

Stdlib-only on purpose: the engine must run wherever the project's Python runs, with no spec-kit
installation and no third-party import.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_INPUT_ERROR = 2

#: [[STR-001]] — the neutral metadata key carrying SDD invocation capability / seat policy.
ALLOW_KEY = "sdd-invocation"
#: [[STR-010]] — the `team.md` frontmatter map keyed by seat slug.
SEATS_KEY = "seats"
#: [[STR-002]] / [[STR-003]] — the two literals the key set's owner enumerates. They are
#: *consumed* here, not defined here: the closed set's owner is NEUTRAL_AGENT_METADATA_KEYS
#: (src/specify_cli/__init__.py), and a value outside it is malformed input.
ALLOW = "allowed"
DENY = "forbidden"
CLOSED_VALUES = (ALLOW, DENY)

#: Roster keys a seat slug may resolve against (create-mode.md § Persisted team.md schema).
ROSTER_KEYS = ("agent", "role", "slug")


class InputError(Exception):
    """Malformed or unreadable input — the only condition that exits 2."""


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"cannot read {path}: {exc.strerror or exc}") from exc


def _frontmatter(lines: list, path: Path) -> list:
    """The lines between the leading `---` fence and its closing twin."""
    if not lines or lines[0].strip() != "---":
        raise InputError(f"{path}: no frontmatter block (the file must open with '---')")
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines[1:index]
    raise InputError(f"{path}: unterminated frontmatter block")


def _top_level(lines: list, key: str):
    """`(index, inline_value)` of a top-level frontmatter key, or `(None, None)`."""
    for index, line in enumerate(lines):
        if not line.strip() or line[:1] in (" ", "\t"):
            continue
        name, sep, value = line.partition(":")
        if sep and name.strip() == key:
            return index, value.strip()
    return None, None


def _indented_block(lines: list, start: int) -> list:
    """The indented lines following `lines[start]`, up to the next top-level line."""
    block = []
    for line in lines[start + 1 :]:
        if line.strip() and line[:1] not in (" ", "\t"):
            break
        block.append(line)
    return block


# ---------------------------------------------------------------------------
# Seat side (team.md)
# ---------------------------------------------------------------------------


def _parse_seat_map(lines: list, path: Path, seat_slug: str):
    """The block `seats:` map as `{slug: {key: value}}`; `None` when the map is absent.

    Block style only. A flow-style / inline map is malformed input and is refused with the seat
    under resolution named — never parsed "as well as it can" and never degraded to a policy
    value.
    """
    index, inline = _top_level(lines, SEATS_KEY)
    if index is None:
        return None
    if inline:
        raise InputError(
            f"{path}: '{SEATS_KEY}' is a flow-style map ({inline!r}); only a block map keyed "
            f"by seat slug is accepted (seat under resolution: {seat_slug!r})"
        )
    entries: dict = {}
    current = None
    seat_indent = None
    for line in _indented_block(lines, index):
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("-"):
            raise InputError(
                f"{path}: '{SEATS_KEY}' must be a block map keyed by seat slug; a sequence "
                f"entry is malformed input (seat under resolution: {seat_slug!r}): {stripped!r}"
            )
        name, sep, value = stripped.partition(":")
        if not sep:
            raise InputError(
                f"{path}: malformed line inside '{SEATS_KEY}' (seat under resolution: "
                f"{seat_slug!r}): {stripped!r}"
            )
        indent = len(line) - len(line.lstrip(" \t"))
        if seat_indent is None:
            seat_indent = indent
        if indent == seat_indent:
            current = name.strip()
            if not current:
                raise InputError(
                    f"{path}: '{SEATS_KEY}' carries an empty seat slug (seat under "
                    f"resolution: {seat_slug!r})"
                )
            if value.strip():
                raise InputError(
                    f"{path}: seat {current!r} declares an inline value ({value.strip()!r}); "
                    f"each seat MUST be a block entry carrying '{ALLOW_KEY}' inside it"
                )
            entries.setdefault(current, {})
        else:
            if current is None:
                raise InputError(
                    f"{path}: indented line before any seat slug inside '{SEATS_KEY}' (seat "
                    f"under resolution: {seat_slug!r}): {stripped!r}"
                )
            entries[current][name.strip()] = value.strip()
    return entries


def _roster_ids(lines: list, path: Path, seat_slug: str) -> set:
    """Every identifier a seat slug may resolve to (member `agent` / `role` / `slug` values)."""
    index, inline = _top_level(lines, "members")
    if index is None or inline:
        raise InputError(
            f"{path}: no block 'members' roster, so a seat entry cannot be checked for "
            f"dangling membership (seat under resolution: {seat_slug!r})"
        )
    ids = set()
    for line in _indented_block(lines, index):
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            stripped = stripped[2:]
        name, sep, value = stripped.partition(":")
        if not sep:
            continue
        name = name.strip()
        value = value.strip()
        if name in ROSTER_KEYS and value:
            ids.add(value)
    return ids


def _resolve_agent_half(agent_path: Path):
    """`(value, supplying)` for the agent definition half; an absent key means deny."""
    lines = _frontmatter(_read(agent_path).splitlines(), agent_path)
    index, inline = _top_level(lines, ALLOW_KEY)
    if index is None:
        return DENY, {"source": "absent-key"}
    value = inline.strip().strip('"').strip("'")
    if value not in CLOSED_VALUES:
        raise InputError(
            f"{agent_path}: {ALLOW_KEY} = {value!r} is outside the closed value set owned by "
            f"NEUTRAL_AGENT_METADATA_KEYS (src/specify_cli/__init__.py)"
        )
    return value, {"source": "declared"}


def _resolve_seat_half(root: Path, team_slug: str, seat_slug: str):
    """`(value, supplying, team_md_path)`; an absent map / entry / key means deny."""
    team_path = root / ".specify" / "teams" / team_slug / "team.md"
    if not team_path.is_file():
        raise InputError(
            f"{team_path}: team slug {team_slug!r} does not resolve to a persisted team "
            f"definition"
        )
    lines = _frontmatter(_read(team_path).splitlines(), team_path)
    seats = _parse_seat_map(lines, team_path, seat_slug)
    roster = _roster_ids(lines, team_path, seat_slug)
    if seats is None:
        return DENY, {"source": "absent-map"}, team_path
    for key in seats:
        if key not in roster:
            raise InputError(
                f"{team_path}: seat entry {key!r} matches no roster member — reported as "
                f"dangling rather than ignored (seat under resolution: {seat_slug!r})"
            )
    if seat_slug not in seats:
        return DENY, {"source": "absent-entry"}, team_path
    entry = seats[seat_slug]
    if ALLOW_KEY not in entry:
        return DENY, {"source": "absent-key"}, team_path
    value = entry[ALLOW_KEY].strip().strip('"').strip("'")
    if value not in CLOSED_VALUES:
        raise InputError(
            f"{team_path}: seats[{seat_slug!r}].{ALLOW_KEY} = {value!r} is outside the closed "
            f"value set owned by NEUTRAL_AGENT_METADATA_KEYS (src/specify_cli/__init__.py)"
        )
    return value, {"source": "declared"}, team_path


# ---------------------------------------------------------------------------
# Action: authorize
# ---------------------------------------------------------------------------

_REASON = {
    "allowed": "both halves allow SDD invocation: the agent definition declares the capability "
    "and the seat policy allows it",
    "agent": "the agent half does not allow SDD invocation (absent key or explicit refusal; the "
    "owner's absent-key default is deny)",
    "seat": "the seat half does not allow SDD invocation (absent map, absent entry for this "
    "seat, or explicit refusal)",
    "both": "neither half allows SDD invocation: the agent definition and the seat policy both "
    "deny",
}


def action_authorize(args) -> int:
    if not args.agent:
        raise InputError("--agent is required: the authorization resolves two halves")
    if not args.team:
        raise InputError(
            "--team is required: the seat policy resolves by (team, seat), so a payload "
            "carrying only the seat cannot satisfy the predicate"
        )
    if not args.seat:
        raise InputError("--seat is required: the seat policy resolves by (team, seat)")

    agent_path = Path(args.agent)
    agent_value, agent_supplying = _resolve_agent_half(agent_path)
    seat_value, seat_supplying, team_path = _resolve_seat_half(
        Path.cwd(), args.team, args.seat
    )

    effective = ALLOW if (agent_value == ALLOW and seat_value == ALLOW) else DENY
    if effective == ALLOW:
        failed_half = None
    elif agent_value != ALLOW and seat_value != ALLOW:
        failed_half = "both"
    elif agent_value != ALLOW:
        failed_half = "agent"
    else:
        failed_half = "seat"

    record = {
        "action": "authorize",
        "agent_capability": agent_value,
        "seat_policy": seat_value,
        "effective": effective,
        "verdict": effective,
        "reason": _REASON[failed_half or "allowed"],
        "failed_half": failed_half,
        "team_slug": args.team,
        "seat_slug": args.seat,
        "supplying": {
            "agent": agent_supplying["source"],
            "seat": seat_supplying["source"],
        },
        "sources": {
            "agent": str(agent_path.resolve()),
            "team": str(team_path.resolve()),
        },
    }

    if args.format == "text":
        print(f"agent_capability: {record['agent_capability']} ({agent_supplying['source']})")
        print(f"seat_policy:      {record['seat_policy']} ({seat_supplying['source']})")
        print(f"effective:        {record['effective']}")
        print(f"verdict:          {record['verdict']}")
        print(f"failed_half:      {record['failed_half'] or '-'}")
        print(f"reason:           {record['reason']}")
        print(f"team / seat:      {record['team_slug']} / {record['seat_slug']}")
        print(f"agent source:     {record['sources']['agent']}")
        print(f"team source:      {record['sources']['team']}")
    else:
        print(json.dumps(record, indent=2, ensure_ascii=False))
    return EXIT_OK


# ---------------------------------------------------------------------------
# Owner document (.specify/shared/definitions/sdd-routing-definitions.md)
#
# Every fact the routing decision consumes is read here, at run time. Nothing below
# restates a value domain, a condition-to-verdict mapping, the precedence order or a
# reason code: those four are the owner document's, and a copy in this file would be a
# second landing place (one-source-of-truth).
# ---------------------------------------------------------------------------

#: The five input identifiers the owner document's § Inputs table declares. They are the
#: *interface* (the table's first column), not a fact: the values, their domains and what
#: they mean live in the document.
INPUT_NATURE = "change_nature"
INPUT_TRACEABILITY = "traceability"
INPUT_BLAST_RADIUS = "blast_radius"
INPUT_REVERSIBILITY = "reversibility"
INPUT_COMPLEXITY = "complexity"

#: The condition identifiers this engine can evaluate. The owner document's § Verdict table
#: and § Reason codes bind them to verdicts; that binding is *its* data, never this file's.
CONDITIONS = (
    "input-conflicting",
    "input-ambiguous",
    "input-missing",
    "bounded-correction-recorded",
    "complexity-low",
    "reversal-reversible",
    "blast-local",
    "traceability-not-required",
    "nature-preserves",
    "complexity-high",
    "reversal-hard",
    "blast-cross-cutting",
    "traceability-required",
    "nature-feature",
)

REQUIRED_SURFACES = (
    "Inputs",
    "Definition-class default",
    "Verdict table",
    "Precedence",
    "Conflict set",
    "Reason codes",
)

ABSENT_CELLS = ("", "—", "-", "--")


def _owner_doc_path(args) -> Path:
    """The owner document: `--owner-doc`, else resolved from this file's own location."""
    explicit = getattr(args, "owner_doc", None)
    if explicit:
        return Path(explicit)
    here = Path(__file__).resolve()
    bases = [here.parents[2]]
    if len(here.parents) > 3:
        bases.append(here.parents[3])
    for base in bases:
        for candidate in (
            base / "shared" / "definitions" / "sdd-routing-definitions.md",
            base / ".specify" / "shared" / "definitions" / "sdd-routing-definitions.md",
        ):
            if candidate.is_file():
                return candidate
    return bases[0] / "shared" / "definitions" / "sdd-routing-definitions.md"


def _sections(text: str) -> dict:
    """Map every level-2 heading to its body (level-3 headings stay in the body)."""
    sections: dict = {}
    current = None
    buffer: list = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buffer).strip()
            current = line[3:].strip()
            buffer = []
        elif current is not None:
            buffer.append(line)
    if current is not None:
        sections[current] = "\n".join(buffer).strip()
    return sections


def _table_rows(body: str) -> list:
    """Markdown table rows as cell lists; separator rows dropped."""
    rows = []
    for line in body.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            continue
        cells = [cell.strip() for cell in stripped[1:-1].split("|")]
        if all(set(cell) <= set("-: ") for cell in cells):
            continue
        rows.append(cells)
    return rows


def _bare(cell: str) -> str:
    return cell.strip().strip("`").strip()


def _requires(owner_text: str, path: Path) -> dict:
    sections = _sections(owner_text)
    missing = [name for name in REQUIRED_SURFACES if name not in sections]
    if missing:
        raise InputError(
            f"{path}: the owner document lacks the surface(s) {missing} — the engine reads its "
            f"facts from there and carries no copy, so it cannot judge without them"
        )
    return sections


def _parse_inputs(body: str, path: Path) -> dict:
    inputs: dict = {}
    for row in _table_rows(body):
        if len(row) < 3:
            continue
        tokens = re.findall(r"`([^`]+)`", row[0])
        if not tokens:
            continue
        flag = next((token for token in tokens if token.startswith("--")), None)
        input_id = tokens[0]
        if flag is None:
            continue
        domain = tuple(_bare(part) for part in row[2].split("/") if _bare(part))
        if len(domain) < 2:
            raise InputError(
                f"{path}: § Inputs row {input_id!r} declares no closed domain of two or more "
                f"values; an open domain makes the verdict undecidable"
            )
        inputs[input_id] = {"flag": flag, "domain": domain}
    if len(inputs) != 5:
        raise InputError(
            f"{path}: § Inputs declares {len(inputs)} machine-readable input rows; the "
            f"decision consumes exactly five declared inputs"
        )
    for role in (INPUT_NATURE, INPUT_TRACEABILITY, INPUT_BLAST_RADIUS, INPUT_REVERSIBILITY, INPUT_COMPLEXITY):
        if role not in inputs:
            raise InputError(f"{path}: § Inputs declares no {role!r} input row")
    return inputs


def _machine_line(body: str, marker: str, path: Path) -> str:
    for line in body.splitlines():
        if marker in line:
            return line
    raise InputError(
        f"{path}: the owner document declares no machine-readable line carrying {marker!r}; the "
        f"engine reads that surface at run time and carries no copy of it"
    )


def _parse_tiers(body: str, path: Path) -> dict:
    line = _machine_line(body, "机读面（层级分档）", path)
    segments = re.split(r"[；;]", line.split("：", 1)[-1])
    tiers = {}
    for key, label in (("high", "高"), ("low", "低")):
        segment = next((part for part in segments if label in part), None)
        if segment is None:
            raise InputError(
                f"{path}: the tier-partition line names no {label!r} side: {line!r}"
            )
        values = tuple(_bare(token) for token in re.findall(r"`([^`]+)`", segment))
        if not values:
            raise InputError(f"{path}: the tier-partition {label!r} side lists no tier: {line!r}")
        tiers[key] = values
    return tiers


def _parse_values(body: str, path: Path) -> dict:
    """The named value handles: `- `name` = `value`` bullets under the value-semantics marker."""
    lines = body.splitlines()
    start = next((i for i, line in enumerate(lines) if "机读面（取值语义" in line), None)
    if start is None:
        raise InputError(
            f"{path}: the owner document declares no '机读面（取值语义）' block; the engine reads "
            f"its named value handles from there and carries no copy of them"
        )
    values: dict = {}
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("- "):
            break
        tokens = re.findall(r"`([^`]+)`", stripped)
        if len(tokens) != 2:
            raise InputError(
                f"{path}: a value-semantics bullet MUST read `- `name` = `value``: {stripped!r}"
            )
        values[tokens[0]] = tokens[1]
    required = (
        "definition_class",
        "feature_nature",
        "traceability_required",
        "traceability_not_required",
        "plain_local",
        "cross_cutting",
        "bounded_correction",
        "definition_class_default",
        "reversal_hard",
        "reversal_reversible",
    )
    missing = [name for name in required if name not in values]
    if missing:
        raise InputError(
            f"{path}: the value-semantics block does not name {missing}; every condition "
            f"predicate addresses its value through one of those handles"
        )
    return values


def _parse_verdicts(body: str, path: Path) -> dict:
    verdicts: dict = {}
    for row in _table_rows(body):
        if len(row) < 3:
            continue
        conditions = tuple(_bare(token) for token in re.findall(r"`([^`]+)`", row[2]))
        if not conditions:
            continue  # header or a non-data row: a verdict row always names its conditions
        verdict = _bare(row[0])
        mode = _bare(row[1]).lower()
        if mode not in ("any", "all"):
            raise InputError(
                f"{path}: verdict {verdict!r} declares combination mode {mode!r}; only 'any' or "
                f"'all' is decidable"
            )
        unknown = [condition for condition in conditions if condition not in CONDITIONS]
        if unknown:
            raise InputError(
                f"{path}: verdict {verdict!r} binds unknown condition id(s) {unknown}; the "
                f"engine evaluates a closed set of condition ids and refuses to guess"
            )
        verdicts[verdict] = {"mode": mode, "conditions": conditions}
    if len(verdicts) != 3:
        raise InputError(f"{path}: § Verdict table declares {len(verdicts)} verdict rows, not 3")
    return verdicts


def _parse_precedence(body: str, path: Path) -> tuple:
    line = _machine_line(body, "机读面（优先级", path)
    order = tuple(_bare(token) for token in re.findall(r"`([^`]+)`", line))
    if len(order) < 2:
        raise InputError(
            f"{path}: the precedence line lists fewer than two verdicts: {line!r}"
        )
    return order


def _parse_reasons(body: str, path: Path) -> list:
    reasons = []
    for row in _table_rows(body):
        if len(row) < 4 or not row[0].strip().isdigit():
            continue
        condition = _bare(row[3])
        if condition not in ABSENT_CELLS and condition not in CONDITIONS:
            raise InputError(
                f"{path}: reason code {_bare(row[1])!r} binds unknown condition id {condition!r}"
            )
        reasons.append(
            {
                "order": int(row[0].strip()),
                "code": _bare(row[1]),
                "verdict": _bare(row[2]),
                "condition": None if condition in ABSENT_CELLS else condition,
            }
        )
    if not reasons:
        raise InputError(f"{path}: § Reason codes declares no reason-code row")
    reasons.sort(key=lambda row: row["order"])
    return reasons


def _parse_conflicts(body: str, inputs: dict, path: Path) -> list:
    conflicts = []
    for row in _table_rows(body):
        if len(row) < 2:
            continue
        terms = []
        for token in re.findall(r"`([^`]+)`", row[1]):
            name, sep, value = token.partition("=")
            if not sep:
                raise InputError(
                    f"{path}: a conflict-set term MUST read `input=value`: {token!r}"
                )
            name = name.strip()
            if name not in inputs:
                raise InputError(
                    f"{path}: the conflict set names unknown input {name!r} (declared inputs: "
                    f"{sorted(inputs)})"
                )
            terms.append((name, value.strip()))
        if terms:
            conflicts.append(terms)
    return conflicts


def _parse_golden(body: str, inputs: dict, path: Path) -> list:
    rows = _table_rows(body)
    if not rows:
        return []
    header = rows[0]
    columns = {input_id: header.index(input_id) for input_id in inputs if input_id in header}
    unknown = [input_id for input_id in inputs if input_id not in columns]
    if unknown:
        raise InputError(
            f"{path}: the golden table's header carries no column for {unknown}"
        )
    rationale_at = next(
        (index for index, cell in enumerate(header) if "rationale" in cell.lower()), None
    )
    cases = []
    for row in rows[1:]:
        if len(row) != len(header):
            raise InputError(
                f"{path}: golden row {row[0]!r} has {len(row)} cells against a {len(header)}-cell "
                f"header; a shifted row would be judged against the wrong column"
            )
        declared = {
            input_id: (None if row[index] in ABSENT_CELLS else _bare(row[index]))
            for input_id, index in columns.items()
        }
        rationale = None
        if rationale_at is not None and row[rationale_at] not in ABSENT_CELLS:
            rationale = row[rationale_at].strip()
        cases.append(
            {
                "case_id": _bare(row[0]),
                "inputs": declared,
                "rationale": rationale,
                "expected_verdict": _bare(row[-3]),
                "expected_reason_code": _bare(row[-2]),
                "face": row[-1],
            }
        )
    return cases


def _load_owner(path: Path) -> dict:
    text = _read(path)
    sections = _requires(text, path)
    inputs = _parse_inputs(sections["Inputs"], path)
    tiers = _parse_tiers(sections["Inputs"], path)
    values = _parse_values(sections["Inputs"], path)
    verdicts = _parse_verdicts(sections["Verdict table"], path)
    precedence = _parse_precedence(sections["Precedence"], path)
    reasons = _parse_reasons(sections["Reason codes"], path)
    conflicts = _parse_conflicts(sections["Conflict set"], inputs, path)
    golden_body = sections.get("Golden case table")
    golden = None if golden_body is None else _parse_golden(golden_body, inputs, path)

    unknown = [verdict for verdict in precedence if verdict not in verdicts]
    if unknown:
        raise InputError(
            f"{path}: the precedence orders verdict(s) {unknown} that § Verdict table does not "
            f"declare"
        )
    for verdict in precedence:
        if not any(row["verdict"] == verdict for row in reasons):
            raise InputError(
                f"{path}: verdict {verdict!r} has no reason code in § Reason codes, so a verdict "
                f"of that kind could carry no reason code"
            )
    return {
        "path": str(path.resolve()),
        "inputs": inputs,
        "tiers": tiers,
        "values": values,
        "verdicts": verdicts,
        "precedence": precedence,
        "reasons": reasons,
        "conflicts": conflicts,
        "golden": golden,
    }


# ---------------------------------------------------------------------------
# The decision
# ---------------------------------------------------------------------------


def _declared_inputs(owner: dict, args) -> dict:
    declared = {}
    for input_id, spec in owner["inputs"].items():
        attribute = spec["flag"].lstrip("-").replace("-", "_")
        value = getattr(args, attribute, None)
        declared[input_id] = None if value is None else str(value).strip()
    return declared


def _effective_blast_radius(owner: dict, declared: dict):
    """C-20: the definition-class default and the bounded-correction escape.

    A plain local radius is not accepted as equivalent for a `definition-class` change (the
    default applies), and the bounded-correction value is not a local radius outside the
    definition surface. Both rules are the contract's (C-20); the values they mention are
    named by the owner document, never spelled here.
    """
    values = owner["values"]
    nature = declared.get(INPUT_NATURE)
    declared_radius = declared.get(INPUT_BLAST_RADIUS)
    if nature == values["definition_class"]:
        if declared_radius == values["bounded_correction"]:
            return values["bounded_correction"]
        return values["definition_class_default"]
    if declared_radius == values["bounded_correction"]:
        return values["definition_class_default"]
    return declared_radius


def _decide(owner: dict, declared: dict, rationale):
    """One decision: the verdict, its reason code and every triggered condition id."""
    values = owner["values"]
    effective = _effective_blast_radius(owner, declared)

    absent = [input_id for input_id, value in declared.items() if value in (None, "")]
    bounded_declared = declared.get(INPUT_BLAST_RADIUS) == values["bounded_correction"]
    if bounded_declared and not (rationale or "").strip():
        absent.append(f"{INPUT_BLAST_RADIUS}.rationale")
    ambiguous = [
        input_id
        for input_id, value in declared.items()
        if value not in (None, "") and value not in owner["inputs"][input_id]["domain"]
    ]
    conflicting = any(
        all(declared.get(name) == wanted for name, wanted in combination)
        for combination in owner["conflicts"]
    )

    nature = declared.get(INPUT_NATURE)
    checks = {
        "input-conflicting": bool(conflicting),
        "input-ambiguous": bool(ambiguous),
        "input-missing": bool(absent),
        "bounded-correction-recorded": (
            bool(rationale)
            if nature == values["definition_class"]
            else True
        ),
        "complexity-low": declared.get(INPUT_COMPLEXITY) in owner["tiers"]["low"],
        "reversal-reversible": declared.get(INPUT_REVERSIBILITY) == values["reversal_reversible"],
        "blast-local": effective in (values["plain_local"], values["bounded_correction"]),
        "traceability-not-required": (
            declared.get(INPUT_TRACEABILITY) == values["traceability_not_required"]
        ),
        "nature-preserves": nature not in (None, "") and nature != values["feature_nature"],
        "complexity-high": declared.get(INPUT_COMPLEXITY) in owner["tiers"]["high"],
        "reversal-hard": declared.get(INPUT_REVERSIBILITY) == values["reversal_hard"],
        "blast-cross-cutting": effective == values["cross_cutting"],
        "traceability-required": declared.get(INPUT_TRACEABILITY) == values["traceability_required"],
        "nature-feature": nature == values["feature_nature"],
    }

    verdict = None
    for candidate in owner["precedence"]:
        row = owner["verdicts"][candidate]
        held = [checks[condition] for condition in row["conditions"]]
        if (all(held) if row["mode"] == "all" else any(held)):
            verdict = candidate
            break
    if verdict is None:
        raise InputError(
            f"{owner['path']}: the verdict table classifies none of the declared inputs "
            f"(inputs={declared}); the owner document's branches do not cover this combination"
        )

    reason_code = None
    for row in owner["reasons"]:
        if row["verdict"] != verdict:
            continue
        if row["condition"] is None or checks[row["condition"]]:
            reason_code = row["code"]
            break
    if reason_code is None:
        raise InputError(
            f"{owner['path']}: no reason code for verdict {verdict!r} matched the triggered "
            f"conditions; every verdict must carry one"
        )

    order = []
    for candidate in owner["precedence"]:
        for condition in owner["verdicts"][candidate]["conditions"]:
            if condition not in order:
                order.append(condition)
    for row in owner["reasons"]:
        if row["condition"] and row["condition"] not in order:
            order.append(row["condition"])
    triggered = [condition for condition in order if checks[condition]]

    return {
        "verdict": verdict,
        "reason_code": reason_code,
        "triggered_conditions": triggered,
        "effective_blast_radius": effective,
        "absent": absent,
        "ambiguous": ambiguous,
    }


# ---------------------------------------------------------------------------
# Action: route
# ---------------------------------------------------------------------------


def action_route(args) -> int:
    owner = _load_owner(_owner_doc_path(args))
    declared = _declared_inputs(owner, args)
    rationale = (getattr(args, "rationale", None) or "").strip() or None
    decision = _decide(owner, declared, rationale)

    record = {
        "action": "route",
        "owner_document": owner["path"],
        "verdict": decision["verdict"],
        "reason_code": decision["reason_code"],
        "triggered_conditions": decision["triggered_conditions"],
        "inputs": {input_id: declared[input_id] for input_id in owner["inputs"]},
        "effective_blast_radius": decision["effective_blast_radius"],
        "bounded_correction_rationale": rationale,
        "absent_inputs": decision["absent"],
        "ambiguous_inputs": decision["ambiguous"],
        "actor": getattr(args, "actor", None),
        "recorded_at": getattr(args, "recorded_at", None),
        "override": None,
    }

    if args.format == "text":
        print(f"verdict:            {record['verdict']}")
        print(f"reason_code:        {record['reason_code']}")
        print(f"effective_radius:   {record['effective_blast_radius']}")
        print(f"triggered:          {', '.join(record['triggered_conditions']) or '-'}")
        for input_id, value in record["inputs"].items():
            print(f"input {input_id}: {value if value is not None else '-'}")
        if record["absent_inputs"]:
            print(f"absent:             {', '.join(record['absent_inputs'])}")
        if record["ambiguous_inputs"]:
            print(f"ambiguous:          {', '.join(record['ambiguous_inputs'])}")
        print(f"owner document:     {record['owner_document']}")
    else:
        print(json.dumps(record, indent=2, ensure_ascii=False))
    return EXIT_OK


# ---------------------------------------------------------------------------
# Action: golden
# ---------------------------------------------------------------------------


def action_golden(args) -> int:
    owner = _load_owner(_owner_doc_path(args))
    if owner["golden"] is None:
        raise InputError(
            f"{owner['path']}: the owner document declares no § Golden case table — the golden "
            f"judge reads its rows from there and carries no copy of them"
        )
    cases = owner["golden"]
    if not cases:
        raise InputError(
            f"{owner['path']}: § Golden case table declares no case row — the judge would "
            f"judge nothing"
        )

    judged = []
    for case in cases:
        decision = _decide(owner, case["inputs"], case["rationale"])
        judged.append(
            {
                "case_id": case["case_id"],
                "inputs": case["inputs"],
                "rationale": case["rationale"],
                "expected_verdict": case["expected_verdict"],
                "expected_reason_code": case["expected_reason_code"],
                "actual_verdict": decision["verdict"],
                "actual_reason_code": decision["reason_code"],
                "triggered_conditions": decision["triggered_conditions"],
                "effective_blast_radius": decision["effective_blast_radius"],
                "match": (
                    decision["verdict"] == case["expected_verdict"]
                    and decision["reason_code"] == case["expected_reason_code"]
                ),
                "face": case["face"],
            }
        )

    payload = {
        "action": "golden",
        "owner_document": owner["path"],
        "case_count": len(judged),
        "all_match": all(case["match"] for case in judged),
        "cases": judged,
    }

    if args.format == "text":
        for case in payload["cases"]:
            mark = "ok  " if case["match"] else "DIFF"
            print(
                f"{mark} {case['case_id']}: {case['actual_verdict']} / "
                f"{case['actual_reason_code']} (expected {case['expected_verdict']} / "
                f"{case['expected_reason_code']})"
            )
        print(f"{payload['case_count']} cases, all_match={payload['all_match']}")
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return EXIT_OK


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdd-route.py",
        description=(
            "Read-only SDD routing / authorization engine (slice 074a-authorized-routing). "
            "Exit 0 for any produced verdict or judged row, 2 for malformed or unreadable input."
        ),
    )
    parser.add_argument("--action", required=True, choices=("route", "authorize", "golden"))
    parser.add_argument("--agent", help="agent definition (.agent.md) carrying the capability")
    parser.add_argument("--team", help="team slug — the first authorization coordinate")
    parser.add_argument("--seat", help="seat slug — the second authorization coordinate")
    parser.add_argument("--nature", help="declared change_nature value")
    parser.add_argument("--traceability", help="declared traceability value")
    parser.add_argument("--blast-radius", help="declared blast_radius value")
    parser.add_argument("--reversibility", help="declared reversibility value")
    parser.add_argument("--complexity", help="declared complexity tier")
    parser.add_argument(
        "--rationale",
        help="the non-empty rationale a bounded definition correction requires",
    )
    parser.add_argument("--actor", help="the unit that made the declaration (recorded, not judged)")
    parser.add_argument(
        "--recorded-at",
        help="timestamp the record carries; the engine never reads a clock itself",
    )
    parser.add_argument(
        "--owner-doc",
        help="the routing owner document (default: resolved from this script's own location)",
    )
    parser.add_argument("--format", choices=("json", "text"), default="json")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.action == "route":
            return action_route(args)
        if args.action == "authorize":
            return action_authorize(args)
        if args.action == "golden":
            return action_golden(args)
        raise InputError(f"unhandled action {args.action!r}")
    except InputError as exc:
        print(f"sdd-route: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR


if __name__ == "__main__":
    sys.exit(main())
