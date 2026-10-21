#!/usr/bin/env python3
"""Goal definition engine for `/speckit.goal` (requirement 037, Feature 041).

The command owns the interaction; this engine owns the deterministic parts —
identity grammar, the three-part structure, the lifecycle table, change history,
and archive enumeration. Fixed rules belong in a program, not in a model
(Constitution Principle XII / token-efficiency Program-First).

A Goal is composed of exactly three parts: objective narrative, zero-or-more
verifiable success criteria, and lifecycle state. Identity is the directory name;
timestamps are change-traceability metadata, never a fourth part.

Concept authority: .specify/shared/definitions/goal-definitions.md (read-only).
File contract:  .specify/specs/037-goal-registry/contracts/goal-definition.contract.md

Actions, grouped by whether they write:

Read group (zero writes):
  list
  validate        <path|slug>
  check-statement <statement>
  targets         <slug> --list | --check STATEMENT
  run-checks      <team-slug> [--target T-nnn | <goal-slug>.T-nnn]

Write group (mutates one definition file):
  create    <slug> --objective TEXT [--title TEXT] [--criterion TEXT ...] [--boundary TEXT ...]
  status    <slug> --set STATE
  objective <slug> --set TEXT
  criteria  <slug> --criterion TEXT ... | --clear
  targets   <slug> --add TEXT | --set STATE --id T-nnn
  migrate   <team-slug> [--keep-inline/--drop-inline]

Exit codes: 0 ok | 2 input error | 3 not found | 4 validation failed | 5 blocked
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_INPUT_ERROR = 2
EXIT_NOT_FOUND = 3
EXIT_INVALID = 4
#: 053 FR-033 — a run-precondition check judged the run blocked. The next free code: the
#: four above keep their existing meanings byte for byte, so one code never carries two
#: meanings across actions, and the 0/2 branches `.specify/templates/commands/team.md` already has
#: keep working unchanged.
EXIT_BLOCKED = 5

ARCHIVE_DIRNAME = ".specify/goal"
DEFINITION_FILENAME = "goal.md"
SUMMARY_DIRNAME = "summary"

#: Exactly three, per the concept authority. `superseded` is deliberately absent.
LIFECYCLE_STATES = ("active", "achieved", "abandoned")
TERMINAL_STATES = ("achieved", "abandoned")

#: FR-003 — the same grammar the summary generator enforces; no second mechanism.
_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")

NO_CRITERIA_MARKER = "None provided."

_SECTION_OBJECTIVE = "## Objective"
_SECTION_CRITERIA = "## Success Criteria"
_SECTION_BOUNDARIES = "## Boundaries"
_SECTION_HISTORY = "## History"
_SECTION_TARGETS = "## Targets"

_TITLE_LINE = re.compile(r"^#\s+Goal:\s*(.+?)\s*$", re.M)

#: Target (038): run-assignable scope slices under a goal. [[STR-002]] three states.
TARGET_STATES = ("open", "done", "dropped")
TARGET_IDENTITY = re.compile(r"^T-\d{3}$")
_TARGET_ROW = re.compile(r"^\| (T-\d{3}) \| (.+) \| (open|done|dropped) \|$")
_TARGETS_HEADER = "| ID | Target | Status |"
_TARGETS_SEPARATOR = "|----|--------|--------|"

#: Legal Target lifecycle moves (FR-006); terminal→terminal is deliberately absent.
TARGET_LEGAL_TRANSITIONS = {
    ("open", "done"),
    ("open", "dropped"),
    ("done", "open"),
    ("dropped", "open"),
}

#: GD-2 — an objective states an outcome. Numbered/bulleted steps are a task list.
_TASKLIST = re.compile(r"(?m)^\s*(?:\d+[.)]\s+|[-*+]\s+)")
_STEP_VERBS = ("首先", "然后", "接着", "step 1", "then ", "next, ")

#: GD-2 — phased wording is a plan's timeline wearing an outcome's clothes. Ordinal-
#: qualified on purpose: a bare 阶段/phase is ordinary domain vocabulary, so matching
#: it would reject legitimate objectives (and every `migrate` of an inline goal).
_PHASED = re.compile(
    r"分阶段|阶段\s*[一二三四五六七八九十\d]|第\s*[一二三四五六七八九十\d]+\s*(?:阶段|步)"
    r"|phase\s*\d|stage\s*\d",
    re.IGNORECASE,
)

#: What `targets <slug> --check` judges. Declared on every verdict so a green is never
#: read as broader than it is; `check-statement`'s narrower "shape-only" is the sibling.
TARGET_CHECK_SCOPE = "shape+criteria-restatement"

#: GD-3 — one goal, one objective. Conjunctions joining independent clauses.
_COMPOSITE = re.compile(
    r"\b(?:and also|and additionally|as well as|;\s*also)\b|并且还|同时还|以及另外",
    re.IGNORECASE,
)


class GoalError(Exception):
    """Raised for any rejection the contract defines."""


class GoalNotFound(GoalError):
    """Raised when a referenced target identity does not exist (exit code 3)."""


class GoalInvalid(GoalError):
    """Raised when a definition exists but cannot be interpreted (exit code 4).

    Kept distinct from GoalNotFound and from a bad argument so that the three tiers 053's
    run-checks contract requires — blocked / input error / definition unusable — stay
    mutually distinguishable instead of collapsing onto one code.
    """


#: STR-004 (053 FR-032) — a check whose precondition does not hold, or which raised, is
#: reported as NOT evaluated. Never `ok`: a check that did not run must not report green,
#: which is the exact shape this feature exists to remove. Single definition point.
NOT_EVALUATED = "not-evaluated"

#: The five run-precondition checks, in reporting order (053 FR-029). `name` says which
#: check ran; `verdict` says what it concluded. Four of these five names are ALSO verdict
#: literals below in preview_target_check — an accident of vocabulary, not an invariant, so
#: nothing may rely on the two fields being interchangeable (053 C-10).
RUN_CHECK_NAMES = (
    "goal-binding", "dangling", "target-terminal", "cross-goal", "goal-terminal",
)

#: Verdicts that stop a run. `input-error` is deliberately absent: a malformed argument is
#: the input tier (exit 2), not a block (exit 5).
BLOCKING_VERDICTS = frozenset({
    "no-goal-definition", "dangling", "target-terminal", "cross-goal", "goal-terminal",
})

#: preview_target_check's own evaluation order, as check ids: binding, then the reference
#: grammar, then cross-goal, goal-terminal, dangling, target-terminal. The top-level verdict
#: is the first non-ok in THIS order, which is what makes the five-check array a faithful
#: projection of the authoritative gate rather than a second opinion beside it.
_TOP_VERDICT_ORDER = (1, 4, 5, 2, 3)


# --------------------------------------------------------------------------
# identity
# --------------------------------------------------------------------------

def is_valid_identity(slug: str) -> bool:
    """Grammar plus path-segment safety."""
    if not slug or slug in (".", ".."):
        return False
    if "/" in slug or "\\" in slug:
        return False
    return bool(_IDENTITY.match(slug))


def archive_root(repo_root: Path) -> Path:
    return Path(repo_root) / ARCHIVE_DIRNAME


def definition_path(repo_root: Path, slug: str) -> Path:
    return archive_root(repo_root) / slug / DEFINITION_FILENAME


def summary_dir(repo_root: Path, slug: str) -> Path:
    """The derived subtree — the only surface a refresh may write."""
    return archive_root(repo_root) / slug / SUMMARY_DIRNAME


# --------------------------------------------------------------------------
# lifecycle
# --------------------------------------------------------------------------

def transition_allowed(current: str, target: str) -> bool:
    if current not in LIFECYCLE_STATES or target not in LIFECYCLE_STATES:
        return False
    if current == target:
        return True
    return current == "active" and target in TERMINAL_STATES


def target_transition_allowed(current: str, target: str) -> bool:
    """Target lifecycle (FR-006): exactly the four moves in the legal set."""
    if current not in TARGET_STATES or target not in TARGET_STATES:
        return False
    return (current, target) in TARGET_LEGAL_TRANSITIONS


# --------------------------------------------------------------------------
# objective shape
# --------------------------------------------------------------------------

def _bad_shape(text: str) -> str | None:
    """Shared GD-2/GD-3 detection — one grammar for objectives and target slices."""
    if (_TASKLIST.search(text) or _PHASED.search(text)
            or any(v in text.lower() for v in _STEP_VERBS)):
        return "GD-2"
    if _COMPOSITE.search(text):
        return "GD-3"
    return None


def _reject_bad_objective(objective: str) -> None:
    text = objective.strip()
    if not text:
        raise GoalError("objective is empty; a goal MUST state a desired outcome")
    kind = _bad_shape(text)
    if kind == "GD-2":
        raise GoalError(
            "GD-2 violation: the objective reads as a task list or plan. State the "
            "desired end outcome instead of the steps to reach it."
        )
    if kind == "GD-3":
        raise GoalError(
            "GD-3 violation: the objective bundles more than one objective. Split it "
            "into separate goal identities, each with its own directory and lifecycle."
        )


def _reject_bad_target_statement(statement: str) -> None:
    """Same-source GD-2/GD-3 detection at slice scale (FR-003, SC-003)."""
    text = statement.strip()
    if not text:
        raise GoalError("target statement is empty; a slice MUST state a sub-outcome")
    kind = _bad_shape(text)
    if kind == "GD-2":
        raise GoalError(
            "GD-2 violation: the target reads as a task list or steps. Rewrite it as a "
            "sub-outcome direction — what holds when the slice is done, not how to get there."
        )
    if kind == "GD-3":
        raise GoalError(
            "GD-3 violation: the target bundles more than one sub-outcome. Split it so "
            "each slice is independently judgeable — one slice, one sub-outcome."
        )


def _normalize(text: str) -> str:
    """D5 normalization: lowercase, keep only letters/digits/CJK."""
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text.lower())


# --------------------------------------------------------------------------
# targets data layer (038)
# --------------------------------------------------------------------------

def _next_target_id(targets: list[dict]) -> str:
    """Monotone max+1; terminal identities are never reused (FR-005)."""
    highest = 0
    for row in targets:
        match = TARGET_IDENTITY.match(row["id"])
        if match:
            highest = max(highest, int(row["id"][2:]))
    return f"T-{highest + 1:03d}"


def _render_targets_table(targets: list[dict]) -> str:
    """D3 grammar: fixed header, rows sorted by ID ascending."""
    rows = [f"| {t['id']} | {t['statement']} | {t['status']} |"
            for t in sorted(targets, key=lambda t: t["id"])]
    return "\n".join([_TARGETS_HEADER, _TARGETS_SEPARATOR] + rows)


def _parse_targets_text(text: str) -> list[dict]:
    """Parse the table body; rows not matching the grammar are skipped here —
    validate_goal is the surface that flags them."""
    targets: list[dict] = []
    for line in (text or "").splitlines():
        match = _TARGET_ROW.match(line.strip())
        if match:
            targets.append({"id": match.group(1), "statement": match.group(2),
                            "status": match.group(3)})
    return targets


# --------------------------------------------------------------------------
# read / write
# --------------------------------------------------------------------------

def _today() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")


def _render(objective: str, criteria: list[str], status: str, created: str,
            updated: str, history: list[str], title: str,
            targets: list[dict] | None = None,
            boundaries: list[str] | None = None) -> str:
    if criteria:
        body = "\n".join(f"{i}. {c}" for i, c in enumerate(criteria, 1))
    else:
        body = NO_CRITERIA_MARKER
    hist = "\n".join(history)
    # Section absent entirely when the goal has no boundaries / no targets
    # (SC-002: byte-identical to the pre-annex rendering).
    boundaries_block = (f"{_SECTION_BOUNDARIES}\n\n"
                        + "\n".join(f"- {b}" for b in boundaries) + "\n\n"
                        if boundaries else "")
    targets_block = (f"{_SECTION_TARGETS}\n\n{_render_targets_table(targets)}\n\n"
                     if targets else "")
    return (
        f"---\nstatus: {status}\ncreated: {created}\nupdated: {updated}\n---\n\n"
        f"# Goal: {title}\n\n"
        f"{_SECTION_OBJECTIVE}\n\n{objective.strip()}\n\n"
        f"{_SECTION_CRITERIA}\n\n{body}\n\n"
        f"{boundaries_block}"
        f"{targets_block}"
        f"{_SECTION_HISTORY}\n\n{hist}\n"
    )


def _split_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, parts[2]


def _section(body: str, heading: str) -> str:
    lines = body.split("\n")
    out: list[str] = []
    inside = False
    for line in lines:
        if line.strip() == heading:
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if inside:
            out.append(line)
    return "\n".join(out).strip()


def _parse_bullets(raw: str) -> list[str]:
    """Parse a `- ` bullet annex; blank lines carry no entry."""
    out: list[str] = []
    for line in (raw or "").splitlines():
        stripped = re.sub(r"^\s*[-*+]\s*", "", line).strip()
        if stripped:
            out.append(stripped)
    return out


def _title_from_body(body: str) -> str:
    match = _TITLE_LINE.search(body)
    return match.group(1).strip() if match else ""


#: 053 FR-035 — the criterion-subject reference form. Single definition point; the literal
#: itself is owned by .specify/shared/definitions/goal-definitions.md § 判据主体指代形 (Criterion
#: Subject Reference), which also states the two failure tiers and the conflict rule below.
SUBJECT_REF = re.compile(r"\[subjects:\s*([^\]]+)\]")
#: The only machine-decidable member-enumeration marker: a brace expansion holding a comma.
#: A PROSE enumeration ("所有绘图技能") carries no marker at all and is therefore NOT
#: detected — the owner document states that boundary explicitly instead of claiming
#: coverage it does not have, which is what the artifact/behavior clause split forbids.
BRACE_ENUM = re.compile(r"\{[^}]*,[^}]*\}")

#: STR-010 and its two siblings. Distinct prefixes, because "the path is not there" and
#: "the path is there and matches nothing" have opposite remedies; both exit 4, so the
#: prefix is what tells them apart.
SUBJECT_PROBLEM_PREFIXES = {
    "missing": "SUBJECT MISSING:",
    "empty": "SUBJECT EMPTY:",
    "conflict": "SUBJECT CONFLICT:",
}
#: Closed state vocabulary of derive_subjects. `absent` is the state every pre-existing
#: pure-enumeration criterion stays in, which is what keeps their parse byte-identical.
SUBJECT_STATES = ("absent", "ok", "missing", "empty", "conflict")

_WILDCARD_CHARS = "*?["


def _repo_root_for(path: Path) -> Path:
    """The repository root a definition path lives under, or the cwd if none does."""
    for parent in Path(path).resolve().parents:
        if (parent / ".specify").is_dir():
            return parent
    return Path.cwd()


def _glob_literal_prefix(pattern: str, repo_root: Path) -> Path:
    """The leading wildcard-free part of a glob — what "the path does not exist" means."""
    segments = []
    for segment in pattern.replace("\\", "/").split("/"):
        if any(ch in segment for ch in _WILDCARD_CHARS):
            break
        segments.append(segment)
    return repo_root.joinpath(*segments) if segments else repo_root


def derive_subjects(criterion: str, repo_root: Path) -> dict:
    """The subject set one criterion's reference form derives to, at parse time.

    Returns {"glob", "paths", "state"} with state in SUBJECT_STATES. Deriving the set here
    rather than trusting members retyped into the criterion text is the whole point: a
    derived set cannot go stale, which is the churn this repository's own goal History shows
    (the same criterion rewritten from six skills to seven and back as the directory moved).

    An empty derivation is NOT a pass — "every one of zero subjects satisfies this" is
    vacuously true — so it is reported, and separately from a glob whose literal prefix does
    not exist, because the two have opposite remedies.
    """
    repo_root = Path(repo_root)
    matches = SUBJECT_REF.findall(criterion)
    if not matches:
        return {"glob": None, "paths": [], "state": "absent"}
    pattern = matches[0].strip()
    if len(matches) > 1 or BRACE_ENUM.search(criterion):
        return {"glob": pattern, "paths": [], "state": "conflict"}
    if not _glob_literal_prefix(pattern, repo_root).exists():
        return {"glob": pattern, "paths": [], "state": "missing"}
    paths = sorted({p.relative_to(repo_root).as_posix() for p in repo_root.glob(pattern)})
    return {"glob": pattern, "paths": paths, "state": "ok" if paths else "empty"}


def _subject_problems(criteria: list, repo_root: Path) -> list:
    problems = []
    for index, criterion in enumerate(criteria, start=1):
        derived = derive_subjects(criterion, repo_root)
        state = derived["state"]
        if state == "absent" or state == "ok":
            continue
        glob = f"[subjects: {derived['glob']}]"
        if state == "conflict":
            problems.append(
                f"{SUBJECT_PROBLEM_PREFIXES['conflict']} criterion {index} carries both the "
                f"reference form {glob} and a brace-expanded member list — one subject set "
                "must have one source, so drop the retyped members or drop the reference")
        elif state == "missing":
            problems.append(
                f"{SUBJECT_PROBLEM_PREFIXES['missing']} criterion {index} references {glob}, "
                "whose literal prefix does not exist in the repository — a reference that "
                "denotes nothing is not the same fact as one denoting an empty set; fix the "
                "glob or restore the directory")
        elif state == "empty":
            problems.append(
                f"{SUBJECT_PROBLEM_PREFIXES['empty']} criterion {index} references {glob}, "
                "which exists but matches nothing — an empty subject set would make 'every "
                "subject satisfies this' vacuously true; widen the glob or populate the "
                "directory")
    return problems


def parse_goal(path: Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    meta, body = _split_frontmatter(text)
    raw_criteria = _section(body, _SECTION_CRITERIA)
    criteria: list[str] = []
    if raw_criteria and raw_criteria.strip() != NO_CRITERIA_MARKER:
        for line in raw_criteria.splitlines():
            stripped = re.sub(r"^\s*(?:\d+[.)]|[-*+])\s*", "", line).strip()
            if stripped:
                criteria.append(stripped)
    return {
        "slug": Path(path).parent.name,
        # Parsed back so an unrelated write never downgrades a --title to the slug.
        "title": _title_from_body(body) or Path(path).parent.name,
        "status": meta.get("status", ""),
        "created": meta.get("created", ""),
        "updated": meta.get("updated", ""),
        "objective": _section(body, _SECTION_OBJECTIVE),
        "criteria": criteria,
        "history": _section(body, _SECTION_HISTORY),
        "criteria_count": len(criteria),
        "boundaries": _parse_bullets(_section(body, _SECTION_BOUNDARIES)),
        "targets": _parse_targets_text(_section(body, _SECTION_TARGETS)),
        # 053 FR-035: subject sets derived at parse time, one entry per criterion that
        # carries a reference form. A pure-enumeration criterion derives nothing, so this
        # list is empty for every definition that predates the form.
        "subjects": [
            derived for derived in
            (derive_subjects(c, _repo_root_for(path)) for c in criteria)
            if derived["state"] != "absent"
        ],
    }


def validate_goal(path: Path, repo_root: Path | None = None) -> tuple[bool, list[str]]:
    path = Path(path)
    problems: list[str] = []
    if not path.is_file():
        return False, [f"definition not found: {path}"]
    text = path.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(text)

    slug = path.parent.name
    if not is_valid_identity(slug):
        problems.append(f"identity {slug!r} violates the grammar or path-safety rule")

    status = meta.get("status", "")
    if status not in LIFECYCLE_STATES:
        problems.append(
            f"status {status!r} is outside the valid set {LIFECYCLE_STATES}"
        )
    for field in ("created", "updated"):
        if not meta.get(field):
            problems.append(f"frontmatter is missing {field}")

    for heading in (_SECTION_OBJECTIVE, _SECTION_CRITERIA, _SECTION_HISTORY):
        if heading not in body:
            problems.append(f"required section missing: {heading}")

    if _SECTION_OBJECTIVE in body and not _section(body, _SECTION_OBJECTIVE):
        problems.append("## Objective is empty")

    if _SECTION_CRITERIA in body:
        raw = _section(body, _SECTION_CRITERIA)
        if not raw:
            problems.append(
                "## Success Criteria is empty; an empty set requires the explicit "
                f"{NO_CRITERIA_MARKER!r} marker"
            )

    if _SECTION_TARGETS in body:
        problems.extend(_validate_targets_section(_section(body, _SECTION_TARGETS)))

    # 053 FR-035/FR-036: the criterion-subject reference form. The criteria list comes from
    # parse_goal rather than a second extraction here, so validation and parsing can never
    # disagree about which criteria exist.
    root = Path(repo_root) if repo_root is not None else _repo_root_for(path)
    problems.extend(_subject_problems(parse_goal(path)["criteria"], root))
    return (not problems), problems


def _validate_targets_section(raw: str) -> list[str]:
    """data-model.md §Entity 1 Validation Rules (038). Section present ⇒ checked."""
    problems: list[str] = []
    lines = [line for line in (raw or "").splitlines() if line.strip()]
    if not lines:
        problems.append(
            "## Targets section is empty; the correct form for a goal without "
            "targets is the section being absent entirely (空表格非法)"
        )
        return problems
    if lines[0].strip() != _TARGETS_HEADER:
        problems.append(
            "## Targets table header is wrong — the section MUST be rendered by the "
            "engine; hand edits are violations (结构由引擎渲染,手写即违规)"
        )
    rows = lines[1:]
    if rows and rows[0].strip().startswith("|---"):
        rows = rows[1:]
    seen: list[int] = []
    for row in rows:
        match = _TARGET_ROW.match(row.strip())
        if not match:
            problems.append(
                f"## Targets row does not match the render grammar ({row.strip()!r}) — "
                "结构由引擎渲染,手写即违规"
            )
            continue
        seen.append(int(match.group(1)[2:]))
    if lines[0].strip() == _TARGETS_HEADER and not seen and not any(
            p.startswith("## Targets row") for p in problems):
        problems.append(
            "## Targets table is empty (header without rows); a goal without targets "
            "carries no section at all"
        )
    if len(seen) != len(set(seen)):
        problems.append("## Targets contains duplicate identities (节内唯一)")
    for prev, cur in zip(seen, seen[1:]):
        if cur <= prev:
            problems.append(
                f"## Targets identities are not monotone (T-{cur:03d} after "
                f"T-{prev:03d}); identities are issued max+1 and never reused"
            )
            break
    return problems


# --------------------------------------------------------------------------
# actions
# --------------------------------------------------------------------------

def create_goal(repo_root: Path, slug: str, objective: str,
                criteria: list[str] | None = None, *,
                title: str | None = None,
                boundaries: list[str] | None = None) -> Path:
    if not is_valid_identity(slug):
        raise GoalError(
            f"identity {slug!r} is invalid: the first character must be alphanumeric, "
            "the rest limited to [A-Za-z0-9_.-], and it must be a safe path segment"
        )
    _reject_bad_objective(objective)
    path = definition_path(repo_root, slug)
    if path.exists():
        raise GoalError(
            f"goal {slug!r} already exists at {path}; use the modify path "
            "(`objective` / `status` / `criteria`) — the existing definition is never "
            "overwritten"
        )
    today = _today()
    # Identity stays the slug; the title is presentation and collapses to one line.
    heading = " ".join((title or "").split()) or slug
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _render(objective, list(criteria or []), "active", today, today,
                [f"- {today} — created."], heading,
                boundaries=[b.strip() for b in (boundaries or []) if b.strip()] or None),
        encoding="utf-8",
    )
    return path


def set_status(path: Path, target: str) -> Path:
    path = Path(path)
    data = parse_goal(path)
    current = data["status"]
    if not transition_allowed(current, target):
        raise GoalError(
            f"transition {current!r} -> {target!r} is not defined; terminal goals are "
            "retained and never reopened"
        )
    today = _today()
    history = [line for line in data["history"].splitlines() if line.strip()]
    history.append(f"- {today} — status {current} -> {target}.")
    path.write_text(
        _render(data["objective"], data["criteria"], target, data["created"],
                today, history, data["title"], data["targets"], data["boundaries"]),
        encoding="utf-8",
    )
    return path


def set_objective(path: Path, objective: str) -> Path:
    """Deliberate objective replacement — `set_criteria`'s change discipline:
    the prior value stays traceable, `updated` bumps, terminal goals stay read-only."""
    path = Path(path)
    data = parse_goal(path)
    _assert_goal_mutable(data, "the objective cannot be replaced")
    _reject_bad_objective(objective)
    today = _today()
    history = [line for line in data["history"].splitlines() if line.strip()]
    previous = " ".join(data["objective"].split())
    history.append(f"- {today} — objective changed; prior value: {previous}")
    path.write_text(
        _render(objective, data["criteria"], data["status"], data["created"],
                today, history, data["title"], data["targets"], data["boundaries"]),
        encoding="utf-8",
    )
    return path


def set_criteria(path: Path, criteria: list[str]) -> Path:
    """FR-005: the prior value stays traceable in History, never silently replaced."""
    path = Path(path)
    data = parse_goal(path)
    today = _today()
    history = [line for line in data["history"].splitlines() if line.strip()]
    previous = data["criteria"] or [NO_CRITERIA_MARKER]
    history.append(
        f"- {today} — criteria changed; prior value: " + " | ".join(previous)
    )
    path.write_text(
        _render(data["objective"], list(criteria), data["status"], data["created"],
                today, history, data["title"], data["targets"], data["boundaries"]),
        encoding="utf-8",
    )
    return path


def _assert_goal_mutable(data: dict,
                         consequence: str = "targets cannot be added or transitioned") -> None:
    """Terminal goals are read-only — no new targets, no transitions (038)."""
    if data["status"] in TERMINAL_STATES:
        raise GoalError(
            f"goal is in terminal state {data['status']!r} and read-only "
            f"(终态 goal 只读); {consequence}"
        )


def _validate_target_statement(data: dict, statement: str) -> None:
    """Same-source statement validation shared by --add and --check (042 C-1):
    GD-2/GD-3 shape plus criteria-restatement — one grammar, zero forks."""
    _reject_bad_target_statement(statement)
    normalized = _normalize(statement.strip())
    for criterion in data["criteria"]:
        if normalized == _normalize(criterion):
            raise GoalError(
                "target statement is normalized-equal to a success criterion; the "
                "criteria axis is authoritative — rewrite the slice as a scope cut "
                "(判据权威互斥,改写为范围切片)"
            )


def add_target(path: Path, statement: str) -> str:
    """Authorize a new open Target; returns the issued identity (D6 history)."""
    path = Path(path)
    data = parse_goal(path)
    _assert_goal_mutable(data)
    _validate_target_statement(data, statement)
    statement = statement.strip()
    targets = data["targets"]
    tid = _next_target_id(targets)
    targets.append({"id": tid, "statement": statement, "status": "open"})
    today = _today()
    history = [line for line in data["history"].splitlines() if line.strip()]
    history.append(f"- {today} target {tid} added: {statement}")
    path.write_text(
        _render(data["objective"], data["criteria"], data["status"], data["created"],
                today, history, data["title"], targets, data["boundaries"]),
        encoding="utf-8",
    )
    return tid


def set_target_status(path: Path, tid: str, new_status: str) -> Path:
    """Apply one legal Target transition; no-op on equal state, never silent history."""
    path = Path(path)
    data = parse_goal(path)
    _assert_goal_mutable(data)
    targets = data["targets"]
    row = next((t for t in targets if t["id"] == tid), None)
    if row is None:
        raise GoalNotFound(f"target {tid} not found in goal {data['slug']!r}")
    current = row["status"]
    if current == new_status:
        return path  # contract §2: no-op, exit 0, no history line
    if not target_transition_allowed(current, new_status):
        raise GoalError(
            f"transition {current} -> {new_status} is not in the legal set "
            f"{sorted(TARGET_LEGAL_TRANSITIONS)}; legal moves: "
            "open→done, open→dropped, done→open, dropped→open"
        )
    row["status"] = new_status
    today = _today()
    history = [line for line in data["history"].splitlines() if line.strip()]
    history.append(f"- {today} target {tid} {current}→{new_status}")
    path.write_text(
        _render(data["objective"], data["criteria"], data["status"], data["created"],
                today, history, data["title"], targets, data["boundaries"]),
        encoding="utf-8",
    )
    return path


def resolve_team_goal_identity(repo_root: Path, team_slug: str) -> tuple[str | None, str]:
    """Two-level goal identity resolution (036 §10.1) — explicit `goal_slug`
    wins, else the team slug when it names an archived definition. No third
    level (038 contract §2.1)."""
    team_md = Path(repo_root) / ".specify/teams" / team_slug / "team.md"
    if not team_md.is_file():
        raise GoalNotFound(f"team not found: {team_slug}")
    meta, _ = _split_frontmatter(team_md.read_text(encoding="utf-8"))
    declared = str(meta.get("goal_slug") or "").strip()
    if declared:
        return declared, "explicit"
    if definition_path(repo_root, team_slug).is_file():
        return team_slug, "inferred"
    return None, "none"


_QUALIFIED_TARGET = re.compile(r"^([A-Za-z0-9][A-Za-z0-9_.\-]*)\.(T-\d{3})$")


def preview_target_check(repo_root: Path, team_slug: str, reference: str) -> dict:
    """The deterministic core of run --target preview validation (038 contract §2).

    Read-only: parses, never writes. The verdict dict carries everything the
    command's gate disclosure needs (goal_slug, identity_kind, statement, status).
    """
    goal_slug, identity_kind = resolve_team_goal_identity(repo_root, team_slug)
    base = {"goal_slug": goal_slug, "identity_kind": identity_kind}
    if goal_slug is None:
        return {**base, "verdict": "no-goal-definition",
                "message": ("Target 依赖 goal 定义——该团队没有绑定的 goal 定义;"
                            "先经 /speckit.goal migrate 将内联 goal 落为定义")}

    qualified = _QUALIFIED_TARGET.match(reference)
    if qualified:
        prefix, tid = qualified.groups()
        if prefix != goal_slug:
            return {**base, "verdict": "cross-goal",
                    "message": (f"跨 goal 引用 {reference!r}:绑定 goal 为 "
                                f"{goal_slug!r},绑定轴不可越界(FR-012)")}
    elif TARGET_IDENTITY.match(reference):
        tid = reference
    else:
        return {**base, "verdict": "input-error",
                "message": (f"引用 {reference!r} 不符合文法 T-<nnn> 或 "
                            "<goal-slug>.T-<nnn>")}

    goal_path = definition_path(repo_root, goal_slug)
    if not goal_path.is_file():
        return {**base, "verdict": "no-goal-definition",
                "message": (f"绑定 goal {goal_slug!r} 无定义文件;先经 "
                            "/speckit.goal migrate 落为定义")}
    data = parse_goal(goal_path)
    if data["status"] in TERMINAL_STATES:
        return {**base, "verdict": "goal-terminal",
                "message": (f"goal {goal_slug!r} 处于终态 {data['status']!r},"
                            "终态 goal 只读,拒绝指派")}
    row = next((t for t in data["targets"] if t["id"] == tid), None)
    if row is None:
        return {**base, "verdict": "dangling",
                "message": (f"悬空引用 {tid}:goal {goal_slug!r} 无此 Target;"
                            "先经 /speckit.goal targets --add 添加")}
    if row["status"] in ("done", "dropped"):
        return {**base, "verdict": "target-terminal", "status": row["status"],
                "statement": row["statement"],
                "message": (f"Target {tid} 处于终态 {row['status']!r},run 停止——"
                            "复核二分:属实则返回报告结束;证据不符则经 "
                            f"/speckit.goal targets --set open --id {tid} 重开后"
                            "重新发起 run。不提供终态执行旁路")}
    return {**base, "verdict": "ok", "status": row["status"],
            "statement": row["statement"], "target_id": tid, "message": ""}


def resolve_effective_target(team_md_path: Path, explicit_target: str | None = None) -> dict:
    """Resolve the effective run Target (042 contract §C-1): explicit --target
    > team.md `focus_target` > none.

    Pure resolution — never judges: the effective value (when not None) is fed
    to preview_target_check for the unchanged five-check pass. `source=none`
    (no explicit target, no declared field) keeps field-less teams
    byte-equivalent to pre-042 behavior. A malformed `focus_target` is a
    configuration error: input-error stop, never silently ignored, never
    degraded to none."""
    team_md_path = Path(team_md_path)
    if not team_md_path.is_file():
        raise GoalNotFound(f"team not found: {team_md_path}")
    meta, _ = _split_frontmatter(team_md_path.read_text(encoding="utf-8"))
    raw_focus = meta.get("focus_target")
    declared_focus = str(raw_focus).strip() if raw_focus is not None else None
    if explicit_target:
        return {"effective": explicit_target, "source": "explicit",
                "declared_focus": declared_focus or None}
    if declared_focus is not None and not TARGET_IDENTITY.match(declared_focus):
        return {"effective": None, "source": "input-error",
                "declared_focus": declared_focus,
                "message": ("input-error: focus_target 值 " f"{declared_focus!r} 不符合文法 "
                            "T-<nnn>(配置错误,停止——不静默忽略、不降级为无;经 "
                            "improve-team 修正字段)")}
    if declared_focus:
        return {"effective": declared_focus, "source": "team-default",
                "declared_focus": declared_focus}
    return {"effective": None, "source": "none", "declared_focus": None}


# --------------------------------------------------------------------------
# 053 run-checks — the five run-precondition checks, one call, zero writes
# --------------------------------------------------------------------------

def _check(cid: int, name: str, verdict: str, message: str = "") -> dict:
    return {"id": cid, "name": name, "verdict": verdict, "message": message}


def _goal_binding_check(ctx: dict) -> tuple[str, str]:
    """① Is a goal definition bound to this team, and does the file exist?"""
    goal_slug, _kind = resolve_team_goal_identity(ctx["repo_root"], ctx["team_slug"])
    if goal_slug is None:
        return "no-goal-definition", (
            "该团队没有绑定的 goal 定义;先经 /speckit.goal migrate 将内联 goal 落为定义")
    if not definition_path(ctx["repo_root"], goal_slug).is_file():
        return "no-goal-definition", (
            f"绑定 goal {goal_slug!r} 无定义文件;先经 /speckit.goal migrate 落为定义")
    return "ok", ""


def _dangling_check(ctx: dict) -> tuple[str, str]:
    """② Does the referenced Target exist in the bound goal's `## Targets`?"""
    if ctx["tid"] is None:
        return NOT_EVALUATED, "无有效 Target 引用,悬空检查无判定主体"
    if ctx["goal_data"] is None:
        return NOT_EVALUATED, "无 goal 定义可查,悬空检查无判定主体"
    row = next((t for t in ctx["goal_data"]["targets"] if t["id"] == ctx["tid"]), None)
    if row is None:
        return "dangling", (
            f"悬空引用 {ctx['tid']}:goal {ctx['goal_slug']!r} 无此 Target;"
            "先经 /speckit.goal targets --add 添加")
    return "ok", ""


def _target_terminal_check(ctx: dict) -> tuple[str, str]:
    """③ Is the referenced Target already in a terminal state?"""
    if ctx["tid"] is None:
        return NOT_EVALUATED, "无有效 Target 引用,终态引用检查无判定主体"
    if ctx["goal_data"] is None:
        return NOT_EVALUATED, "无 goal 定义可查,终态引用检查无判定主体"
    row = next((t for t in ctx["goal_data"]["targets"] if t["id"] == ctx["tid"]), None)
    if row is None:
        return NOT_EVALUATED, f"Target {ctx['tid']} 不存在,其状态无从判定(见悬空检查)"
    if row["status"] in ("done", "dropped"):
        return "target-terminal", (
            f"Target {ctx['tid']} 处于终态 {row['status']!r},run 停止——复核二分:属实则返回"
            f"报告结束;证据不符则经 /speckit.goal targets --set open --id {ctx['tid']} 重开后"
            "重新发起 run。不提供终态执行旁路")
    return "ok", ""


def _cross_goal_check(ctx: dict) -> tuple[str, str]:
    """④ Does a QUALIFIED reference cross the binding axis?"""
    if ctx["grammar"] != "qualified":
        # A local-form `T-<nnn>` carries no prefix, so no cross-goal question arises. This is
        # a check with no subject, not a check that passed — reporting `ok` here would claim
        # a comparison ran that never did.
        return NOT_EVALUATED, (
            "引用不是限定形 <goal-slug>.T-<nnn>,无跨 goal 前缀可比"
            if ctx["grammar"] == "local" else "无有效 Target 引用,跨 goal 检查无判定主体")
    if ctx["prefix"] != ctx["goal_slug"]:
        return "cross-goal", (
            f"跨 goal 引用 {ctx['reference']!r}:绑定 goal 为 {ctx['goal_slug']!r},"
            "绑定轴不可越界")
    return "ok", ""


def _goal_terminal_check(ctx: dict) -> tuple[str, str]:
    """⑤ Is the bound goal itself in a terminal lifecycle state?"""
    if ctx["goal_data"] is None:
        return NOT_EVALUATED, "无 goal 定义可读,goal 终态检查无判定主体"
    if ctx["goal_data"]["status"] in TERMINAL_STATES:
        return "goal-terminal", (
            f"goal {ctx['goal_slug']!r} 处于终态 {ctx['goal_data']['status']!r},"
            "终态 goal 只读,拒绝指派")
    return "ok", ""


#: Reporting order == id order. Each entry is called under its own guard, because one check
#: raising must leave the other four reported rather than swallowing the whole verdict.
_RUN_CHECK_FUNCTIONS = (
    _goal_binding_check, _dangling_check, _target_terminal_check,
    _cross_goal_check, _goal_terminal_check,
)


def _compose_verdict(checks: list, grammar: str) -> str:
    """The top-level verdict projected from the five, in the gate's own priority order.

    The reference grammar is judged before any of the five, exactly as preview_target_check
    judges it, so an unusable reference is `input-error` and not a projection of the array.
    """
    if grammar in ("input-error", "invalid"):
        return "input-error"
    by_id = {c["id"]: c for c in checks}
    for cid in _TOP_VERDICT_ORDER:
        verdict = by_id[cid]["verdict"]
        if verdict not in ("ok", NOT_EVALUATED):
            return verdict
    return "ok"


def run_checks(repo_root: Path, team_slug: str, explicit_target: str | None = None) -> dict:
    """The five run-precondition checks for one team, in ONE call. Zero writes.

    Every verdict comes from the engine's own code path — resolve_team_goal_identity,
    definition_path, parse_goal, TERMINAL_STATES, _QUALIFIED_TARGET, TARGET_IDENTITY and
    resolve_effective_target — and where a reference is in play the top-level verdict is
    `preview_target_check`'s own, verbatim. So this action reports the gate run mode already
    trusts; it does not re-decide it, and it defines no grammar of its own.

    A check whose precondition does not hold is NOT_EVALUATED, never `ok`, and each check is
    guarded separately so one raising leaves the other four reported.

    Blocking is target-scoped for ① goal-binding and NOT for ⑤ goal-terminal, because that
    is what the recorded rule says: team.md's check 1 states that a team with no goal
    definition stops only when a --target was given ("不指定 --target 时一切照旧"), while
    check 5 ("终态 goal 只读") is a property of the goal and carries no such scoping.

    This binary has no EXIT_USAGE=1, so an argparse usage failure exits 2 and cannot be told
    apart from an in-body input error. run-checks does not depend on that distinction: a
    usage failure never reaches this function, and every input error it can itself produce
    is the `input-error` verdict, which maps to exit 2 for either cause alike.
    """
    repo_root = Path(repo_root)
    team_md = repo_root / ".specify/teams" / team_slug / "team.md"
    if not team_md.is_file():
        raise GoalNotFound(f"team not found: {team_slug}")

    resolution = resolve_effective_target(team_md, explicit_target)
    reference = resolution["effective"]

    grammar, prefix, tid = "none", None, None
    if resolution["source"] == "input-error":
        grammar = "input-error"
    elif reference is not None:
        if TARGET_IDENTITY.match(reference):
            grammar, tid = "local", reference
        else:
            qualified = _QUALIFIED_TARGET.match(reference)
            if qualified:
                grammar = "qualified"
                prefix, tid = qualified.groups()
            else:
                # Matches neither grammar. This is a distinct state from "no reference at
                # all": preview_target_check reports it as `input-error` and stops, so the
                # projection must too — folding it into `none` would exit 0 on an argument
                # the engine rejects, which is a green verdict on a run that cannot happen.
                grammar = "invalid"

    goal_slug, identity_kind = resolve_team_goal_identity(repo_root, team_slug)
    goal_data = None
    if goal_slug is not None:
        path = definition_path(repo_root, goal_slug)
        if path.is_file():
            try:
                goal_data = parse_goal(path)
            except GoalError as exc:
                raise GoalInvalid(
                    f"goal definition {goal_slug!r} cannot be parsed: {exc}") from exc
            if goal_data["status"] not in LIFECYCLE_STATES:
                raise GoalInvalid(
                    f"goal definition {goal_slug!r} declares status "
                    f"{goal_data['status']!r}, outside the lifecycle set {LIFECYCLE_STATES} "
                    "— the goal-terminal check has no decidable subject")

    ctx = {
        "repo_root": repo_root, "team_slug": team_slug, "team_md": team_md,
        "resolution": resolution, "reference": reference, "grammar": grammar,
        "prefix": prefix, "tid": tid, "goal_slug": goal_slug,
        "identity_kind": identity_kind, "goal_data": goal_data,
    }

    checks = []
    for index, check_fn in enumerate(_RUN_CHECK_FUNCTIONS):
        try:
            verdict, message = check_fn(ctx)
        except Exception as exc:      # one check failing must not swallow the other four
            verdict = NOT_EVALUATED
            message = f"{RUN_CHECK_NAMES[index]} 检查自身失败,未得出判定:{exc}"
        checks.append(_check(index + 1, RUN_CHECK_NAMES[index], verdict, message))

    # The authoritative gate decides the top-level verdict whenever it can run; the
    # projection is the fallback for the two cases it cannot (no reference at all, or a
    # reference whose grammar failed before any check had a subject).
    verdict = None
    if grammar in ("local", "qualified"):
        try:
            verdict = preview_target_check(repo_root, team_slug, reference)["verdict"]
        except GoalError:
            verdict = None
    if verdict is None:
        verdict = _compose_verdict(checks, grammar)

    blocked = False
    for check in checks:
        if check["verdict"] not in BLOCKING_VERDICTS:
            continue
        if check["id"] == 1 and grammar == "none":
            continue        # team.md check 1: no --target, 一切照旧 — informational only
        blocked = True
    if verdict == "input-error":
        blocked = False     # a bad argument is the input tier, not a block

    return {
        "team_slug": team_slug,
        "goal_slug": goal_slug,
        "identity_kind": identity_kind,
        "resolution": {k: resolution.get(k) for k in ("effective", "source", "declared_focus")},
        "checks": checks,
        "verdict": verdict,
        "blocked": blocked,
    }


def migrate_team(repo_root: Path, team_slug: str, *, keep_inline: bool = True) -> tuple[Path, str]:
    """Derive a goal definition from a team's inline goal and switch it to a reference.

    Per-team and optional (FR-016..FR-019). The inline goal is kept by default —
    removal is the user's choice, never forced. Semantics are preserved: the objective
    the team resolved before migration is the objective the definition carries after.
    """
    team_md = Path(repo_root) / ".specify/teams" / team_slug / "team.md"
    if not team_md.is_file():
        raise GoalError(f"team not found: {team_md}")
    text = team_md.read_text(encoding="utf-8")
    fm, body = _split_frontmatter(text)

    inline = str(fm.get("goal") or "").strip()
    if not inline:
        raise GoalError(f"team {team_slug!r} has no inline goal to migrate")

    # objective = first sentence/line of the inline goal; criteria = 成功标准/success lines
    objective = " ".join(inline.split())
    criteria: list[str] = []
    goal_body = _section(body, "## Goal")
    for line in goal_body.splitlines():
        stripped = re.sub(r"^\s*(?:\d+[.)]|[-*+])\s*", "", line).strip()
        if stripped and re.search(r"成功标准|success crit|criteri|判据|阈值|threshold", stripped, re.I):
            criteria.append(stripped)

    identity = str(fm.get("goal_slug") or team_slug)
    if definition_path(repo_root, identity).exists():
        raise GoalError(
            f"a definition for {identity!r} already exists; migration would overwrite it — "
            "resolve manually via the modify path"
        )
    created = create_goal(repo_root, identity, objective, criteria)

    # set goal_slug on the team, preserving the rest of the file verbatim
    if "goal_slug:" in text:
        new_text = re.sub(r"(?m)^goal_slug:.*$", f"goal_slug: {identity}", text)
    else:
        # insert right after the `goal:` line (or its folded block's first line)
        new_text = re.sub(r"(?m)^(goal:.*\n(?:\s+.*\n)*)", r"\1" + f"goal_slug: {identity}\n",
                          text, count=1)
        if "goal_slug:" not in new_text:  # no goal line matched; append to frontmatter
            new_text = text.replace("---\n", f"---\ngoal_slug: {identity}\n", 1)
    if not keep_inline:
        # the caller explicitly opted to drop the inline copy
        new_text = re.sub(r"(?m)^goal:.*(?:\n\s+.*)*\n", "", new_text, count=1)
    team_md.write_text(new_text, encoding="utf-8")
    return created, identity


def list_goals(repo_root: Path) -> list[dict]:
    root = archive_root(repo_root)
    if not root.is_dir():
        return []
    rows = []
    for child in sorted(root.iterdir()):
        definition = child / DEFINITION_FILENAME
        if child.is_dir() and definition.is_file():
            data = parse_goal(definition)
            rows.append({
                "slug": data["slug"],
                "status": data["status"],
                "criteria_count": data["criteria_count"],
                "updated": data["updated"],
            })
    return rows


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _resolve(repo_root: Path, target: str) -> Path:
    candidate = Path(target)
    if candidate.is_file():
        return candidate
    return definition_path(repo_root, target)


def main(argv: list[str] | None = None) -> int:
    # Shared flags are attached to BOTH the top-level parser and every subparser. That does
    # NOT make them position-independent, and the comment here used to claim it did: argparse
    # lets a subparser overwrite a namespace attribute the top level already set, so
    # `goal-utils.py --json list` silently emits the human form and `--repo-root X list`
    # silently resolves to the cwd. Measured 2026-10-04 (both orders compared through _emit).
    # Pass these flags AFTER the action. Fixing the precedence would change behavior for all
    # ten actions, which is outside 053's declared scope — escalated as research.md A-9 of
    # spec 053-machine-decidable-artifacts, and pinned as measured by test_run_checks.py C-11
    # so it cannot change silently in either direction.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo-root", default=None, help="repository root (default: cwd)")
    common.add_argument("--json", action="store_true", help="machine-readable output")

    parser = argparse.ArgumentParser(
        description="Goal definition engine for /speckit.goal.",
        parents=[common],
    )
    sub = parser.add_subparsers(dest="action", required=True)

    p_create = sub.add_parser("create", parents=[common],
                              help="write: archive a new goal definition")
    p_create.add_argument("slug")
    p_create.add_argument("--objective", required=True)
    p_create.add_argument("--title", default=None, metavar="TEXT",
                          help="human-readable heading; falls back to the slug")
    p_create.add_argument("--criterion", action="append", default=[])
    p_create.add_argument("--boundary", action="append", default=[], metavar="TEXT",
                          help="an explicit exclusion, rendered under ## Boundaries")

    p_validate = sub.add_parser("validate", parents=[common],
                                help="read: validate one definition")
    p_validate.add_argument("target", help="goal slug or path to goal.md")

    p_check_stmt = sub.add_parser(
        "check-statement", parents=[common],
        help="read: standalone dry-run shape validation of one Target statement "
             "(GD-2/GD-3); requires NO goal — usable before `create`")
    p_check_stmt.add_argument("statement", help="candidate Target statement")

    sub.add_parser("list", parents=[common], help="read: enumerate the archive")

    p_status = sub.add_parser("status", parents=[common],
                              help="write: change lifecycle state")
    p_status.add_argument("slug")
    p_status.add_argument("--set", dest="target_state", required=True,
                          choices=LIFECYCLE_STATES)

    p_objective = sub.add_parser("objective", parents=[common],
                                 help="write: replace the objective, recording the prior value")
    p_objective.add_argument("slug")
    p_objective.add_argument("--set", dest="new_objective", required=True, metavar="TEXT",
                             help="the replacement objective (outcome-shaped; GD-2/GD-3 apply)")

    p_criteria = sub.add_parser(
        "criteria", parents=[common],
        help="write: replace criteria, recording the prior value "
             "(destructive when emptied via --clear)")
    p_criteria.add_argument("slug")
    p_criteria.add_argument("--criterion", action="append", default=[])
    p_criteria.add_argument("--clear", dest="clear_criteria", action="store_true",
                            help="deliberately empty the criteria set — overwrites the "
                                 f"existing criteria with {NO_CRITERIA_MARKER!r}")

    p_migrate = sub.add_parser("migrate", parents=[common],
                               help="write: derive a definition from a team's inline goal "
                                    "and reference it")
    p_migrate.add_argument("team_slug")
    p_migrate.add_argument("--drop-inline", action="store_true",
                           help="remove the team's inline goal after migrating (default: keep)")

    p_targets = sub.add_parser("targets", parents=[common],
                               help="read (--list/--check) | write (--add/--set): the "
                                    "Targets of one goal (038)")
    p_targets.add_argument("slug")
    p_targets.add_argument("--add", dest="add_statement", default=None,
                           metavar="STATEMENT", help="append a new open Target")
    p_targets.add_argument("--check", dest="check_statement", default=None,
                           metavar="STATEMENT",
                           help="dry-run statement validation; zero writes (042)")
    p_targets.add_argument("--list", dest="list_targets", action="store_true",
                           help="list every Target, machine-parseable lines")
    p_targets.add_argument("--set", dest="set_state", default=None,
                           choices=TARGET_STATES, help="transition one Target")
    p_targets.add_argument("--id", dest="target_id", default=None,
                           metavar="T-NNN", help="Target identity paired with --set")

    p_run_checks = sub.add_parser(
        "run-checks", parents=[common],
        help="read: the five run-precondition checks for one team, in a single call "
             "(zero writes; 053)")
    p_run_checks.add_argument("team_slug", metavar="<team-slug>",
                              help="team directory name under .specify/teams/")
    p_run_checks.add_argument("--target", dest="run_target", default=None,
                              metavar="T-NNN",
                              help="T-<nnn> or <goal-slug>.T-<nnn>; omit to resolve via "
                                   "team.md focus_target")

    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root or ".").resolve()

    try:
        if args.action == "create":
            path = create_goal(repo_root, args.slug, args.objective, args.criterion,
                               title=args.title, boundaries=args.boundary)
            result = {"created": str(path.relative_to(repo_root))}
        elif args.action == "validate":
            path = _resolve(repo_root, args.target)
            ok, problems = validate_goal(path, repo_root)
            result = {"valid": ok, "problems": problems, "path": str(path)}
            if not ok:
                _emit(result, args.json)
                return EXIT_INVALID
        elif args.action == "list":
            result = {"goals": list_goals(repo_root)}
        elif args.action == "status":
            path = _resolve(repo_root, args.slug)
            if not path.is_file():
                _emit({"error": f"goal not found: {args.slug}"}, args.json)
                return EXIT_NOT_FOUND
            set_status(path, args.target_state)
            result = {"slug": args.slug, "status": args.target_state}
        elif args.action == "objective":
            path = _resolve(repo_root, args.slug)
            if not path.is_file():
                _emit({"error": f"goal not found: {args.slug}"}, args.json)
                return EXIT_NOT_FOUND
            set_objective(path, args.new_objective)
            result = {"slug": args.slug,
                      "objective": " ".join(args.new_objective.split())}
        elif args.action == "criteria":
            path = _resolve(repo_root, args.slug)
            if not path.is_file():
                _emit({"error": f"goal not found: {args.slug}"}, args.json)
                return EXIT_NOT_FOUND
            # Exit 2, never a read fallback: `criteria` is a write, so an argument-less
            # call is a malformed write — silently downgrading it to a read would hide
            # the dropped flag and leave the caller believing the criteria were shown.
            if not args.criterion and not args.clear_criteria:
                _emit({"error": "criteria replaces the whole set: pass --criterion at "
                                "least once, or --clear to empty it deliberately. "
                                "An argument-less call would overwrite the existing "
                                "criteria with an empty set."}, args.json)
                return EXIT_INPUT_ERROR
            set_criteria(path, list(args.criterion))
            result = {"slug": args.slug, "criteria": list(args.criterion),
                      "cleared": bool(args.clear_criteria)}
        elif args.action == "migrate":
            created, identity = migrate_team(
                repo_root, args.team_slug, keep_inline=not args.drop_inline)
            result = {"migrated_team": args.team_slug, "goal_slug": identity,
                      "created": str(created.relative_to(repo_root)),
                      "inline_kept": not args.drop_inline}
        elif args.action == "check-statement":
            # Standalone pre-creation path (F-E12): `targets <slug> --check`
            # needs an existing goal (exit 3 without one), which made the
            # dry-run unusable exactly when it is most needed — before
            # `create`. This runs the SAME-source shape grammar
            # (_reject_bad_target_statement: GD-2/GD-3, zero writes); the
            # criteria-restatement comparison needs the goal's criteria and
            # stays with `targets <slug> --check` after creation.
            try:
                _reject_bad_target_statement(args.statement)
            except GoalError as exc:
                _emit({"verdict": "rejected", "error": str(exc),
                       "scope": "shape-only"}, args.json)
                return EXIT_INPUT_ERROR
            result = {"verdict": "ok", "scope": "shape-only",
                      "note": "criteria-restatement check requires the goal's "
                              "criteria — run `targets <slug> --check` after "
                              "creation for the full verdict"}
        elif args.action == "targets":
            path = definition_path(repo_root, args.slug)
            if not path.is_file():
                _emit({"error": f"goal not found: {args.slug} — to validate a "
                                "statement BEFORE the goal exists, use "
                                "`check-statement \"<statement>\"` "
                                "(shape-only: GD-2/GD-3)"}, args.json)
                return EXIT_NOT_FOUND
            chosen = [args.add_statement is not None, args.list_targets,
                      args.set_state is not None, args.check_statement is not None]
            if sum(chosen) != 1:
                _emit({"error": "targets expects exactly one of --add / --check / --list / --set"},
                      args.json)
                return EXIT_INPUT_ERROR
            if args.check_statement is not None:
                # 042 dry-run: same-source validation as --add, zero writes.
                data = parse_goal(path)
                if data["status"] in TERMINAL_STATES:
                    _emit({"verdict": "goal-terminal",
                           "error": f"goal is in terminal state {data['status']!r} "
                                    "(终态 goal 只读); a proposal has nowhere to land"},
                          args.json)
                    return EXIT_INVALID
                try:
                    _validate_target_statement(data, args.check_statement)
                except GoalError as exc:
                    _emit({"verdict": "rejected", "error": str(exc),
                           "scope": TARGET_CHECK_SCOPE}, args.json)
                    return EXIT_INPUT_ERROR
                result = {"slug": args.slug, "verdict": "ok",
                          "scope": TARGET_CHECK_SCOPE}
            elif args.list_targets:
                targets = parse_goal(path)["targets"]
                if args.json:
                    result = {"targets": targets}
                else:
                    for row in targets:
                        print(f"{row['id']}\t{row['status']}\t{row['statement']}")
                    return EXIT_OK
            elif args.add_statement is not None:
                tid = add_target(path, args.add_statement)
                result = {"slug": args.slug, "added": tid}
            else:  # --set
                if not args.target_id:
                    _emit({"error": "--set must be paired with --id"}, args.json)
                    return EXIT_INPUT_ERROR
                set_target_status(path, args.target_id, args.set_state)
                result = {"slug": args.slug, "id": args.target_id,
                          "status": args.set_state}
        elif args.action == "run-checks":
            payload = run_checks(repo_root, args.team_slug, args.run_target)
            _emit(payload, args.json)
            if payload["verdict"] == "input-error":
                return EXIT_INPUT_ERROR
            return EXIT_BLOCKED if payload["blocked"] else EXIT_OK
        else:  # pragma: no cover - argparse guards this
            parser.error(f"unknown action {args.action}")
    except GoalNotFound as exc:
        _emit({"error": str(exc)}, args.json)
        return EXIT_NOT_FOUND
    except GoalInvalid as exc:
        # The definition exists but cannot be interpreted, which is neither a bad argument
        # (2) nor a blocked run (5): 053 C-18 requires the three tiers be distinguishable.
        _emit({"error": str(exc)}, args.json)
        return EXIT_INVALID
    except GoalError as exc:
        _emit({"error": str(exc)}, args.json)
        return EXIT_INPUT_ERROR

    _emit(result, args.json)
    return EXIT_OK


def _emit(payload: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if "error" in payload:
        print(f"error: {payload['error']}", file=sys.stderr)
        return
    if "goals" in payload:
        if not payload["goals"]:
            print("(archive is empty)")
        for row in payload["goals"]:
            print(f"{row['slug']:<32} {row['status']:<10} "
                  f"criteria={row['criteria_count']:<3} updated={row['updated']}")
        return
    if "problems" in payload:
        print("valid" if payload["valid"] else "INVALID")
        for problem in payload["problems"]:
            print(f"  - {problem}")
        return
    if "checks" in payload and "team_slug" in payload:
        res = payload.get("resolution") or {}
        print(f"team: {payload['team_slug']}   goal: {payload['goal_slug']}   "
              f"identity: {payload['identity_kind']}")
        print(f"target: {res.get('effective')}   source: {res.get('source')}   "
              f"declared focus: {res.get('declared_focus')}")
        for row in payload["checks"]:
            tail = f" — {row['message']}" if row["message"] else ""
            print(f"  {row['id']}. {row['name']:<16} {row['verdict']}{tail}")
        print(f"verdict: {payload['verdict']}   blocked: "
              f"{str(payload['blocked']).lower()}")
        return
    for key, value in payload.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    raise SystemExit(main())
