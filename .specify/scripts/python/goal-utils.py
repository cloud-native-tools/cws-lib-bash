#!/usr/bin/env python3
"""Goal definition engine for `/speckit.goal` (requirement 037, Feature 041).

The command owns the interaction; this engine owns the deterministic parts —
identity grammar, the three-part structure, the lifecycle table, change history,
and archive enumeration. Fixed rules belong in a program, not in a model
(Constitution Principle XII / token-efficiency Program-First).

A Goal is composed of exactly three parts: objective narrative, zero-or-more
verifiable success criteria, and lifecycle state. Identity is the directory name;
timestamps are change-traceability metadata, never a fourth part.

Concept authority: shared/definitions/goal-definitions.md (read-only).
File contract:  .specify/specs/037-goal-registry/contracts/goal-definition.contract.md

Actions:
  create   <slug> --objective TEXT [--criterion TEXT ...]
  validate <path|slug>
  list
  status   <slug> --set STATE
  criteria <slug> --criterion TEXT ...
  migrate  <team-slug> [--keep-inline/--drop-inline]
  targets  <slug> --add TEXT | --list | --set STATE --id T-nnn

Exit codes: 0 ok | 2 input error | 3 not found | 4 validation failed
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
_SECTION_HISTORY = "## History"
_SECTION_TARGETS = "## Targets"

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

#: GD-3 — one goal, one objective. Conjunctions joining independent clauses.
_COMPOSITE = re.compile(
    r"\b(?:and also|and additionally|as well as|;\s*also)\b|并且还|同时还|以及另外",
    re.IGNORECASE,
)


class GoalError(Exception):
    """Raised for any rejection the contract defines."""


class GoalNotFound(GoalError):
    """Raised when a referenced target identity does not exist (exit code 3)."""


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
    if _TASKLIST.search(text) or any(v in text.lower() for v in _STEP_VERBS):
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
            targets: list[dict] | None = None) -> str:
    if criteria:
        body = "\n".join(f"{i}. {c}" for i, c in enumerate(criteria, 1))
    else:
        body = NO_CRITERIA_MARKER
    hist = "\n".join(history)
    # Section absent entirely when the goal has no targets (SC-002: byte-identical).
    targets_block = (f"{_SECTION_TARGETS}\n\n{_render_targets_table(targets)}\n\n"
                     if targets else "")
    return (
        f"---\nstatus: {status}\ncreated: {created}\nupdated: {updated}\n---\n\n"
        f"# Goal: {title}\n\n"
        f"{_SECTION_OBJECTIVE}\n\n{objective.strip()}\n\n"
        f"{_SECTION_CRITERIA}\n\n{body}\n\n"
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
        "status": meta.get("status", ""),
        "created": meta.get("created", ""),
        "updated": meta.get("updated", ""),
        "objective": _section(body, _SECTION_OBJECTIVE),
        "criteria": criteria,
        "history": _section(body, _SECTION_HISTORY),
        "criteria_count": len(criteria),
        "targets": _parse_targets_text(_section(body, _SECTION_TARGETS)),
    }


def validate_goal(path: Path) -> tuple[bool, list[str]]:
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
                criteria: list[str] | None = None) -> Path:
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
            "(`status` / `criteria`) — the existing definition is never overwritten"
        )
    today = _today()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _render(objective, list(criteria or []), "active", today, today,
                [f"- {today} — created."], slug),
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
                today, history, data["slug"], data["targets"]),
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
                today, history, data["slug"], data["targets"]),
        encoding="utf-8",
    )
    return path


def _assert_goal_mutable(data: dict) -> None:
    """Terminal goals are read-only — no new targets, no transitions (038)."""
    if data["status"] in TERMINAL_STATES:
        raise GoalError(
            f"goal is in terminal state {data['status']!r} and read-only "
            "(终态 goal 只读); targets cannot be added or transitioned"
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
                today, history, data["slug"], targets),
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
                today, history, data["slug"], targets),
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
    # Shared flags are attached to BOTH the top-level parser and every subparser, so
    # `goal-utils.py create x --json` and `goal-utils.py --json create x` both work.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo-root", default=None, help="repository root (default: cwd)")
    common.add_argument("--json", action="store_true", help="machine-readable output")

    parser = argparse.ArgumentParser(
        description="Goal definition engine for /speckit.goal.",
        parents=[common],
    )
    sub = parser.add_subparsers(dest="action", required=True)

    p_create = sub.add_parser("create", parents=[common],
                              help="archive a new goal definition")
    p_create.add_argument("slug")
    p_create.add_argument("--objective", required=True)
    p_create.add_argument("--criterion", action="append", default=[])

    p_validate = sub.add_parser("validate", parents=[common],
                                help="validate one definition")
    p_validate.add_argument("target", help="goal slug or path to goal.md")

    p_check_stmt = sub.add_parser(
        "check-statement", parents=[common],
        help="standalone dry-run shape validation of one Target statement "
             "(GD-2/GD-3); requires NO goal — usable before `create`")
    p_check_stmt.add_argument("statement", help="candidate Target statement")

    sub.add_parser("list", parents=[common], help="enumerate the archive")

    p_status = sub.add_parser("status", parents=[common], help="change lifecycle state")
    p_status.add_argument("slug")
    p_status.add_argument("--set", dest="target_state", required=True,
                          choices=LIFECYCLE_STATES)

    p_criteria = sub.add_parser("criteria", parents=[common],
                               help="replace criteria, recording the prior value")
    p_criteria.add_argument("slug")
    p_criteria.add_argument("--criterion", action="append", default=[])

    p_migrate = sub.add_parser("migrate", parents=[common],
                               help="derive a definition from a team's inline goal and reference it")
    p_migrate.add_argument("team_slug")
    p_migrate.add_argument("--drop-inline", action="store_true",
                           help="remove the team's inline goal after migrating (default: keep)")

    p_targets = sub.add_parser("targets", parents=[common],
                               help="authorize/list/transition Targets of one goal (038)")
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

    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root or ".").resolve()

    try:
        if args.action == "create":
            path = create_goal(repo_root, args.slug, args.objective, args.criterion)
            result = {"created": str(path.relative_to(repo_root))}
        elif args.action == "validate":
            path = _resolve(repo_root, args.target)
            ok, problems = validate_goal(path)
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
        elif args.action == "criteria":
            path = _resolve(repo_root, args.slug)
            if not path.is_file():
                _emit({"error": f"goal not found: {args.slug}"}, args.json)
                return EXIT_NOT_FOUND
            set_criteria(path, args.criterion)
            result = {"slug": args.slug, "criteria": args.criterion}
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
                    _emit({"verdict": "rejected", "error": str(exc)}, args.json)
                    return EXIT_INPUT_ERROR
                result = {"slug": args.slug, "verdict": "ok"}
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
        else:  # pragma: no cover - argparse guards this
            parser.error(f"unknown action {args.action}")
    except GoalNotFound as exc:
        _emit({"error": str(exc)}, args.json)
        return EXIT_NOT_FOUND
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
    for key, value in payload.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    raise SystemExit(main())
