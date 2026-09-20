#!/usr/bin/env python3
"""build-summary-input.py — derive a summarize-project input form from team artifacts.

Contract: team-project-form (defined in the framework repo, spec 036)
Mapping single source of truth: `../references/summary-mapping.md`

The invoked skill (`summarize-project`) only accepts a user-authored form and blocks
with exit 3 when its R-tier fields are missing. This script plays the form author so
that a team never has to: it folds every tracked artifact of every team sharing a goal
into one form, deterministically, with no model in the loop.

Indexing is dual:
  * `.specify/teams/<team-slug>/`             team index — run info (read-only here)
  * `.specify/goal/<goal-slug>/summary/`      goal index — the sole complete summary

The goal archive holds both faces of one object: `<goal-slug>/goal.md` is the authored
definition and is NEVER written here; `<goal-slug>/summary/` is the derived subtree and
is the only surface this script may touch.

Exit codes: 0 form written | 2 input error | 3 no execution material (declined).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - environment guard
    print("PyYAML is required", file=sys.stderr)
    raise SystemExit(2)

EXIT_OK, EXIT_INPUT_ERROR, EXIT_NO_MATERIAL = 0, 2, 3
# FR-035 — another refresh of the same goal holds the lock; this one stands down
# rather than racing it. Reported so the caller can record a status line.
EXIT_SERIALIZED = 4
# A lock older than this is treated as abandoned by a dead run.
LOCK_STALE_SECONDS = 900

# FG-10 / §6.2 — the DDL identifier grammar, enforced upstream by entity_ids
DDL_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")

# WS-6 — provenance that is not tracked in version control
INADMISSIBLE_PREFIXES = (
    ".specify/teams/.work/",
    ".specify/agents/execution/logs/",
)
# WS-7 — tracked execution-layer paths are admissible despite the layer
ADMISSIBLE_EXECUTION_PREFIXES = (
    ".specify/agents/execution/configs/",
    ".specify/agents/execution/scripts/",
)

LEDGER_STATES = {"completed", "in-progress", "delayed", "not-started", "unknown"}

# Source literal → the four-state palette the invoked skill normalizes on
STATE_TO_SOURCE_LITERAL = {
    "completed": "已完成",
    "in-progress": "进行中",
    "delayed": "延期",
    "not-started": "未开始",
    "unknown": "",  # empty → the engine records `unknown`, never 0%
}

# §3 — per-pattern phase unit label
PHASE_UNIT = {
    "continuous": "cycle",
    "iteration": "generation",
    "serial": "stage",
    "parallel": "batch",
}

# FR-029 / FG-9 — completed and archived items stay in the data layer but are
# aggregated in presentation once a phase exceeds this many of them.
AGGREGATE_COMPLETED_ABOVE = 3


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------


def fail(message: str, code: int) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def split_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---"):
        return {}
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        return {}
    raw = parts[0][3:]
    try:
        loaded = yaml.safe_load(raw)
    except yaml.YAMLError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def is_admissible_provenance(path: str) -> bool:
    """WS-5 / WS-6 / WS-7."""
    if not path:
        return False
    if path.startswith(ADMISSIBLE_EXECUTION_PREFIXES):
        return True
    if path.startswith(INADMISSIBLE_PREFIXES):
        return False
    if path.startswith(("/", "~", "../")):
        return False
    return True


def inferred_item_id(title: str, phase_ref: str) -> str:
    """FR-027 — derived identity must be hashed; a CJK title is not a legal id."""
    digest = hashlib.sha256(f"{title}\x00{phase_ref}".encode()).hexdigest()[:8]
    return f"TIX-{digest}"


def namespaced(team_slug: str, identifier: str) -> str:
    """FG-15 — `entity_ids` is global, so per-team ids must carry the team."""
    return f"{team_slug}.{identifier}"


# --------------------------------------------------------------------------
# Team discovery and goal identity
# --------------------------------------------------------------------------


class Team:
    def __init__(self, directory: Path, frontmatter: dict[str, Any]) -> None:
        self.dir = directory
        self.fm = frontmatter
        self.slug: str = str(frontmatter.get("slug") or directory.name)
        self.name: str = str(frontmatter.get("name") or self.slug)
        self.pattern: str = str(frontmatter.get("pattern") or "continuous")
        self.description: str = str(frontmatter.get("description") or "")
        self.goal_text: str = " ".join(str(frontmatter.get("goal") or "").split())

    @property
    def goal_identity(self) -> tuple[str, str]:
        """FG-13 — explicit `goal_slug` wins, else the team slug marked inferred."""
        declared = self.fm.get("goal_slug")
        if declared:
            return str(declared), "explicit"
        return self.slug, "inferred"

    @property
    def territory(self) -> dict[str, Any] | None:
        """Team-level scope (FR-035). None means UNDECLARED — never conflated with empty.

        Path lists are normalised (brace-expanded, canonicalised); `non_path` carries
        typed {type, target} entries that are listed for arbitration, never intersected.
        """
        raw = self.fm.get("territory")
        if not isinstance(raw, dict):
            return None
        return {
            "write": sorted(expand_scopes(raw.get("write") or [])),
            "read": sorted(expand_scopes(raw.get("read") or [])),
            "forbidden": sorted(expand_scopes(raw.get("forbidden") or [])),
            "non_path": list(raw.get("non_path") or []),
        }

    @property
    def ledger(self) -> Path:
        return self.dir / "items.jsonl"

    @property
    def run_reports(self) -> list[Path]:
        return sorted((self.dir / "runs").glob("*-report.md"))

    def has_material(self) -> bool:
        return self.ledger.is_file() or bool(self.run_reports)


def discover_teams(teams_root: Path) -> list[Team]:
    teams: list[Team] = []
    for team_md in sorted(teams_root.glob("*/team.md")):
        if team_md.parent.name.startswith("."):
            continue
        fm = split_frontmatter(team_md.read_text(encoding="utf-8"))
        teams.append(Team(team_md.parent, fm))
    return teams


def resolve_goal(teams: list[Team], *, goal: str | None, team_slug: str | None) -> tuple[str, str, list[Team]]:
    """Return (goal_slug, identity_kind, contributing_teams) — FG-13 / FG-14."""
    if team_slug:
        match = [t for t in teams if t.slug == team_slug]
        if not match:
            fail(f"unknown team slug: {team_slug}", EXIT_INPUT_ERROR)
        goal_slug, kind = match[0].goal_identity
    else:
        goal_slug, kind = str(goal), "explicit"
        if not any(t.goal_identity[0] == goal_slug for t in teams):
            fail(f"no team resolves to goal: {goal_slug}", EXIT_INPUT_ERROR)

    if not DDL_IDENTIFIER.match(goal_slug) or goal_slug in {".", ".."} or "/" in goal_slug:
        fail(f"goal identity {goal_slug!r} is not a legal identifier/path segment", EXIT_INPUT_ERROR)

    members = sorted(
        (t for t in teams if t.goal_identity[0] == goal_slug), key=lambda t: t.slug
    )
    # A team never summarizes in isolation; the kind reported is the triggering
    # team's, but an explicit declaration anywhere makes the goal explicit.
    if any(t.goal_identity[1] == "explicit" for t in members):
        kind = "explicit"
    return goal_slug, kind, members


# --------------------------------------------------------------------------
# Ledger fold and run-report backfill
# --------------------------------------------------------------------------


def fold_ledger(team: Team, gaps: list[str]) -> list[dict[str, Any]]:
    """IL-2 — last event per item_id wins. Returns rows in id order."""
    if not team.ledger.is_file():
        return []
    events: list[dict[str, Any]] = []
    for lineno, line in enumerate(team.ledger.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            gaps.append(f"{team.slug}: unparseable ledger line {lineno} skipped")
            continue
        if not isinstance(row, dict) or "item_id" not in row:
            gaps.append(f"{team.slug}: ledger line {lineno} lacks item_id, skipped")
            continue
        events.append(row)

    folded: dict[str, dict[str, Any]] = {}
    superseded: set[str] = set()
    for row in sorted(events, key=lambda r: str(r.get("ts") or "")):
        folded[str(row["item_id"])] = row
        if row.get("supersedes"):
            superseded.add(str(row["supersedes"]))
    # §6.3 step 3 — an item that crossed identity forms collapses to one record
    for stale in superseded:
        folded.pop(stale, None)
    return [folded[k] for k in sorted(folded)]


REPORT_OUTCOME = re.compile(r"^- \*\*Outcome\*\*:\s*(.+?)\s*$", re.M)
REPORT_FINISHED = re.compile(r"\*\*Finished\*\*:\s*(\d{4}-\d{2}-\d{2})")
REPORT_STARTED = re.compile(r"\*\*Started\*\*:\s*(\d{4}-\d{2}-\d{2})")
# Continuous teams write a "Cycle Report" carrying `**UTC**:` instead of the
# Report contract's Started/Finished pair — both shapes exist in practice.
REPORT_UTC = re.compile(r"\*\*UTC\*\*:\s*(\d{4}-\d{2}-\d{2})")
# The `runs/<UTC-timestamp>-report.md` filename convention is mandated for every
# run, so it is the most reliable deterministic date source of all.
REPORT_FILENAME_STAMP = re.compile(r"^(\d{4})(\d{2})(\d{2})T\d{6}Z-report\.md$")
DELIVERABLE_ROW = re.compile(r"^\|\s*(?!Artifact)([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", re.M)


def report_date(report: Path, text: str) -> str:
    """Extract a run date, tolerating every report shape actually in use."""
    for pattern in (REPORT_FINISHED, REPORT_STARTED, REPORT_UTC):
        match = pattern.search(text)
        if match:
            return match.group(1)
    stamp = REPORT_FILENAME_STAMP.match(report.name)
    if stamp:
        return f"{stamp.group(1)}-{stamp.group(2)}-{stamp.group(3)}"
    return ""


def backfill_from_reports(team: Team, gaps: list[str]) -> list[dict[str, Any]]:
    """FR-025 / FG-3 — targeted extraction of the fixed Report contract sections.

    Only used for history that predates the ledger. Identities are inferred and
    marked as such; nothing here is presented as precise.
    """
    rows: list[dict[str, Any]] = []
    for index, report in enumerate(team.run_reports, 1):
        text = report.read_text(encoding="utf-8")
        rel = f".specify/teams/{team.slug}/runs/{report.name}"
        outcome_match = REPORT_OUTCOME.search(text)
        outcome = outcome_match.group(1) if outcome_match else ""
        stamp = report_date(report, text)
        phase_ref = f"PH-{index:04d}"
        state = "completed" if outcome.strip().strip("*") in {"completed", "converged"} else "unknown"

        if not outcome_match:
            gaps.append(
                f"{team.slug}: {report.name} does not follow the documented Report contract "
                f"(no **Outcome** field); item state recorded as unknown rather than guessed"
            )

        deliverables = [
            m.group(1).strip()
            for m in DELIVERABLE_ROW.finditer(text.split("## Deliverables", 1)[-1].split("##", 2)[0])
            if m.group(1).strip() and "---" not in m.group(1)
        ] if "## Deliverables" in text else []

        if not deliverables:
            gaps.append(f"{team.slug}: {report.name} declares no deliverables; run recorded as one item")
            deliverables = [f"run {report.name.split('-')[0]}"]

        for title in deliverables:
            rows.append(
                {
                    "item_id": inferred_item_id(title, phase_ref),
                    "title": title,
                    "phase_ref": phase_ref,
                    "state": state,
                    "provenance": rel,
                    "ts": stamp,
                    "identity": "inferred",
                }
            )
    return rows


# --------------------------------------------------------------------------
# Goal-level entity assembly
# --------------------------------------------------------------------------

CRITERIA_SPLIT = re.compile(r"[;；]|(?<=[。.])\s*")


#: The goal archive. Read-only from this script — `goal-utils.py` is its only writer.
ARCHIVE_DIRNAME = ".specify/goal"

#: 038 — the ## Targets row grammar; identical to goal-utils' render grammar (D3).
_TARGET_ROW = re.compile(r"^\| (T-\d{3}) \| (.+) \| (open|done|dropped) \|$")


def _parse_targets_section(raw: str) -> list[dict[str, str]]:
    """Rows not matching the engine grammar are skipped — validate owns flagging."""
    targets: list[dict[str, str]] = []
    for line in (raw or "").splitlines():
        match = _TARGET_ROW.match(line.strip())
        if match:
            targets.append({"id": match.group(1), "statement": match.group(2),
                            "status": match.group(3)})
    return targets


def load_goal_definition(repo_root: Path, goal_slug: str) -> dict[str, Any] | None:
    """Read the archived definition's objective and criteria, or None if absent.

    This parses locally rather than importing `scripts/python/goal-utils.py`:
    the two files live in different mirrored trees (`skills/` and `scripts/`) at
    different relative depths, so a cross-tree import breaks once installed into a
    consuming project. The reader is deliberately minimal and read-only —
    `goal-utils.py` stays the single writer and the single validator.
    """
    path = repo_root / ARCHIVE_DIRNAME / goal_slug / "goal.md"
    if not path.is_file():
        return None
    text = path.read_text(encoding="utf-8")
    body = text.split("---", 2)[2] if text.startswith("---") else text

    def section(heading: str) -> str:
        out: list[str] = []
        inside = False
        for line in body.split("\n"):
            if line.strip() == heading:
                inside = True
                continue
            if inside and line.startswith("## "):
                break
            if inside:
                out.append(line)
        return "\n".join(out).strip()

    raw = section("## Success Criteria")
    criteria: list[str] = []
    if raw and raw.strip() != "None provided.":
        for line in raw.splitlines():
            stripped = re.sub(r"^\s*(?:\d+[.)]|[-*+])\s*", "", line).strip()
            if stripped:
                criteria.append(stripped)
    return {
        "relpath": f"{ARCHIVE_DIRNAME}/{goal_slug}/goal.md",
        "objective": " ".join(section("## Objective").split()),
        "criteria": criteria,
        "targets": _parse_targets_section(section("## Targets")),
    }


def fold_targets_axis(per_team_items: dict[str, list[dict[str, Any]]],
                      authored_targets: list[dict[str, str]], goal_slug: str,
                      gaps: list[str]) -> dict[str, Any]:
    """038 / D4 — fold optional `target_ref` ledger fields into the slice axis.

    Single pass over already-folded rows (last-event-wins semantics is inherited
    from fold_ledger, untouched). Invalid refs degrade to the goal as a whole and
    are counted + declared (FR-014). The axis is reported separately from the
    criteria axis and never derives `achieved` (SC-005).
    """
    valid = {t["id"] for t in authored_targets}
    attributed: dict[str, list[dict[str, Any]]] = {tid: [] for tid in valid}
    invalid_refs = 0
    unattributed = 0
    for rows in per_team_items.values():
        for row in rows:
            ref = row.get("target_ref")
            if ref in (None, ""):
                unattributed += 1
            elif isinstance(ref, str) and ref in valid:
                attributed[ref].append(row)
            else:
                invalid_refs += 1

    items: list[dict[str, Any]] = []
    for target in sorted(authored_targets, key=lambda t: t["id"]):
        rows = attributed[target["id"]]
        completed = sum(1 for r in rows if str(r.get("state")) == "completed")
        pending = False
        if target["status"] == "open" and rows and completed == len(rows):
            pending = True
            gaps.append(
                f"待批准完成(FR-015):Target {target['id']} authored 仍 open,"
                "但归属条目全部 completed——批准请经 /speckit.goal "
                f"targets --set done --id {target['id']};折叠流程不自动翻转任何一侧"
            )
        elif target["status"] == "done" and rows and completed < len(rows):
            pending = True
            gaps.append(
                f"复核提示(FR-015):Target {target['id']} authored 为 done,"
                f"但归属条目未全部 completed({completed}/{len(rows)})——请复核证据"
            )
        items.append({
            "id": target["id"],
            "statement": target["statement"],
            "authored_status": target["status"],
            "attributed_items": len(rows),
            "completed_items": completed,
            "pending_approval": pending,
        })

    done_count = sum(1 for t in authored_targets if t["status"] == "done")
    if invalid_refs:
        gaps.append(
            f"无效归属(FR-014):{invalid_refs} 行 target_ref 指向不存在的 Target 身份,"
            "已按 goal 整体降级计入并声明,未臆造 Target"
        )
    return {
        "goal_slug": goal_slug,
        "axis_note": "切片轴(范围覆盖度)——与判据轴分列,不推导 achieved",
        "items": items,
        "coverage": f"{done_count}/{len(authored_targets)} done",
        "unattributed_to_target": unattributed,
        "invalid_refs": invalid_refs,
    }


def extract_milestones(goal_text: str) -> list[str]:
    """FR-003 — the goal's verifiable success criteria become milestones."""
    if not goal_text:
        return []
    tail = goal_text
    for marker in ("成功标准", "成功判据", "Success criteria", "success criteria"):
        if marker in tail:
            tail = tail.split(marker, 1)[1].lstrip(":： ")
            break
    else:
        return []
    criteria = [c.strip(" 。.;；") for c in CRITERIA_SPLIT.split(tail)]
    return [c for c in criteria if len(c) >= 4][:12]


def resolve_person_name(repo_root: Path, agent_ref: str) -> str | None:
    """FR-004 — instance definition wins over template."""
    for sub in ("instances", "templates"):
        candidate = repo_root / ".specify/agents" / sub / f"{agent_ref}.agent.md"
        if candidate.is_file():
            name = split_frontmatter(candidate.read_text(encoding="utf-8")).get("name")
            if name:
                return str(name)
    return None


def _brace_expand(pattern: str) -> list[str]:
    """Expand one level of `{a,b,c}` alternation, recursively for multiple groups."""
    start = pattern.find("{")
    if start == -1:
        return [pattern]
    depth = 0
    for i in range(start, len(pattern)):
        if pattern[i] == "{":
            depth += 1
        elif pattern[i] == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    else:
        return [pattern]  # unbalanced; treat literally
    head, options, tail = pattern[:start], pattern[start + 1:end], pattern[end + 1:]
    out: list[str] = []
    for opt in options.split(","):
        out.extend(_brace_expand(head + opt + tail))
    return out


def normalize_scope(pattern: str) -> str:
    """Canonicalise one path pattern: drop ./, resolve . and .. textually, drop trailing /.

    Globs (`*`, `**`, `?`) are retained as patterns, never expanded against the disk.
    """
    p = pattern.strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    parts: list[str] = []
    for seg in p.split("/"):
        if seg in ("", "."):
            continue
        if seg == ".." and parts and parts[-1] != "..":
            parts.pop()
            continue
        parts.append(seg)
    norm = "/".join(parts)
    return norm.rstrip("/")


def expand_scopes(patterns: list[str]) -> set[str]:
    out: set[str] = set()
    for pattern in patterns:
        for expanded in _brace_expand(str(pattern)):
            norm = normalize_scope(expanded)
            if norm:
                out.add(norm)
    return out


def _glob_prefix(pattern: str) -> str:
    """The path portion before the first glob metacharacter."""
    cut = len(pattern)
    for i, ch in enumerate(pattern):
        if ch in "*?[":
            cut = i
            break
    prefix = pattern[:cut]
    return prefix.rstrip("/") if "/" in prefix else prefix


def _is_ancestor_or_equal(a: str, b: str) -> bool:
    """True when path `a` equals `b` or is a component-wise ancestor of `b`."""
    if a == b:
        return True
    if a == "":
        return True  # an empty prefix (bare glob) matches anywhere
    ap, bp = a.split("/"), b.split("/")
    return len(ap) <= len(bp) and bp[:len(ap)] == ap


def scopes_overlap(a: str, b: str) -> bool:
    """Conservative overlap: prefixes nest either way.

    Errs toward reporting overlap (never misses a real write collision), which is the
    safe direction for a mechanism whose whole point is preventing two teams from
    competing for the same write set. `a/**` and `a/b/c.md` therefore overlap.
    """
    pa, pb = _glob_prefix(normalize_scope(a)), _glob_prefix(normalize_scope(b))
    return _is_ancestor_or_equal(pa, pb) or _is_ancestor_or_equal(pb, pa)


def _write_intersections(wa: list[str], wb: list[str]) -> list[list[str]]:
    return [[x, y] for x in wa for y in wb if scopes_overlap(x, y)]


def overlap_verdict(team_a: str, terr_a: dict[str, Any] | None,
                    team_b: str, terr_b: dict[str, Any] | None) -> dict[str, Any]:
    """Verdict for one unordered team pair (OV-1..OV-5).

    `no-overlap` requires BOTH teams to declare a non-empty path-shaped write scope.
    A team that declares nothing (territory None) or declares no write paths gives
    `undecidable` — never conflated with `no-overlap` (FR-042).
    """
    base = {"pair": sorted([team_a, team_b])}
    if terr_a is None or terr_b is None:
        undeclared = [t for t, terr in ((team_a, terr_a), (team_b, terr_b)) if terr is None]
        return {**base, "verdict": "undecidable", "kind": "undeclared",
                "entries": [], "note": f"范围未声明,无法判定重叠:{', '.join(undeclared)}"}
    intersections = _write_intersections(terr_a["write"], terr_b["write"])
    if intersections:
        return {**base, "verdict": "overlap", "kind": "write-write",
                "entries": intersections}
    if terr_a["non_path"] and terr_b["non_path"] and not (terr_a["write"] and terr_b["write"]):
        return {**base, "verdict": "undecidable", "kind": "non-path",
                "entries": [], "non_path_pairs": [terr_a["non_path"], terr_b["non_path"]],
                "note": "仅非路径维度声明,如实并列供人裁定,机制不判定等价(FR-036)"}
    if not terr_a["write"] or not terr_b["write"]:
        empty = [t for t, terr in ((team_a, terr_a), (team_b, terr_b)) if not terr["write"]]
        return {**base, "verdict": "undecidable", "kind": "no-write-scope",
                "entries": [], "note": f"无路径形 Write Scope,无法判定重叠:{', '.join(empty)}"}
    return {**base, "verdict": "no-overlap", "kind": "write-write", "entries": []}


def detect_overlaps(teams: list[Team]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            findings.append(
                overlap_verdict(teams[i].slug, teams[i].territory,
                                teams[j].slug, teams[j].territory)
            )
    return findings


def containment_violations(team_write: list[str], member_write: list[str]) -> list[str]:
    """TT-6 — member write scopes that escape the team-level write scope."""
    team = sorted(expand_scopes(team_write))
    out: list[str] = []
    for m in sorted(expand_scopes(member_write)):
        if not any(scopes_overlap(m, t) and _is_ancestor_or_equal(_glob_prefix(t), _glob_prefix(m))
                   for t in team):
            out.append(m)
    return out


def build_roster(teams: list[Team]) -> list[dict[str, Any]]:
    """RO-1..RO-4 — one derived row per team; regenerated wholesale."""
    roster: list[dict[str, Any]] = []
    for team in sorted(teams, key=lambda t: t.slug):
        _, identity_type = team.goal_identity
        roster.append({
            "team": team.slug,
            "territory": team.territory,          # None when undeclared
            "identity_type": identity_type,       # explicit | inferred
            "advancing": team.has_material(),
            "participation": "active",
        })
    return roster


def render_roster_md(goal_slug: str, roster: list[dict[str, Any]],
                     overlaps: list[dict[str, Any]], contested: list[dict[str, Any]]) -> str:
    """Human-readable derived roster (FR-033). Regenerated wholesale each refresh."""
    lines = [
        f"# Goal roster — {goal_slug}",
        "",
        "> 派生产物,每次刷新整体重算;请勿手工编辑。团队↔goal 绑定是单向的,",
        "> 本名册不改变 goal 定义。",
        "",
        "## 参与团队",
        "",
        "| 团队 | 身份 | 是否推进 | 声明的 Write Scope |",
        "|------|------|---------|--------------------|",
    ]
    for row in roster:
        terr = row.get("territory")
        write = "、".join(terr["write"]) if terr and terr["write"] else (
            "(空)" if terr else "**未声明**"
        )
        lines.append(
            f"| {row['team']} | {row['identity_type']} | "
            f"{'是' if row['advancing'] else '否'} | {write} |"
        )
    lines += ["", "## 重叠检测", ""]
    if not overlaps:
        lines.append("- 单团队或无可比对范围,未发起检测。")
    for f in overlaps:
        detail = f.get("note", "")
        if f["verdict"] == "overlap":
            paths = sorted({p for pair in f["entries"] for p in pair})
            detail = "写重叠于 " + "、".join(paths)
        lines.append(f"- **{f['verdict']}** {f['pair'][0]} ↔ {f['pair'][1]}:{detail}")
    lines += ["", "## 争用区(须归给唯一团队或转禁写区)", ""]
    if not contested:
        lines.append("- 无。")
    for f in contested:
        paths = sorted({p for pair in f["entries"] for p in pair})
        lines.append(f"- {f['pair'][0]} 与 {f['pair'][1]}:{'、'.join(paths)}")
    return "\n".join(lines) + "\n"


def build_form(repo_root: Path, goal_slug: str, kind: str, teams: list[Team],
               baseline: str | None) -> tuple[dict[str, Any], list[str], dict[str, Any]]:
    gaps: list[str] = []
    inferred_fields: list[dict[str, str]] = []

    per_team_items: dict[str, list[dict[str, Any]]] = {}
    for team in teams:
        rows = fold_ledger(team, gaps)
        if not rows:
            rows = backfill_from_reports(team, gaps)
            if rows:
                gaps.append(
                    f"{team.slug}: no item ledger; history backfilled from runs/ with inferred identities"
                )
        per_team_items[team.slug] = rows

    if not any(per_team_items.values()):
        return {}, gaps, {"declined": True}

    if kind == "inferred":
        inferred_fields.append(
            {
                "field": "project.project_name",
                "inferred_from": "团队未声明 goal_slug,以 team slug 回填 goal 身份(FR-034)",
            }
        )

    # baseline: latest event timestamp across the goal (FG-6, never the clock)
    stamps = sorted(
        str(r.get("ts") or "")[:10]
        for rows in per_team_items.values()
        for r in rows
        if r.get("ts")
    )
    baseline_date = baseline or (stamps[-1] if stamps else "")
    if not baseline_date:
        gaps.append("no ledger/report timestamp available for the baseline date")

    phases: list[dict[str, Any]] = []
    work_items: list[dict[str, Any]] = []
    people: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    seen_people: set[str] = set()
    completed_per_phase: dict[str, int] = {}
    order = 0

    for team in teams:
        rows = per_team_items[team.slug]
        unit = PHASE_UNIT.get(team.pattern, "phase")

        # phases — FG-16, namespaced so different patterns never share a sequence
        for phase_ref in sorted({str(r.get("phase_ref") or "PH-0001") for r in rows}):
            order += 1
            phases.append(
                {
                    "phase_id": namespaced(team.slug, phase_ref),
                    "phase_name": f"{team.slug} · {unit} {phase_ref.split('-')[-1].lstrip('0') or '1'}",
                    "phase_order": order,
                }
            )

        # people — union across teams, deduped on agent slug
        for member in team.fm.get("members") or []:
            if not isinstance(member, dict):
                continue
            agent_ref = str(member.get("agent") or "").strip()
            if not agent_ref or agent_ref in seen_people:
                continue
            seen_people.add(agent_ref)
            resolved = resolve_person_name(repo_root, agent_ref)
            if resolved is None:
                gaps.append(f"{team.slug}: agent definition {agent_ref} unresolved; owner recorded as 未记录")
                inferred_fields.append(
                    {"field": f"people[{agent_ref}].owner_name",
                     "inferred_from": "名册引用的 agent 定义未找到,按 FR-004 记为未记录"}
                )
            people.append(
                {
                    "owner_id": agent_ref,
                    "owner_name": resolved or "未记录",
                    "owner_role": str(member.get("role") or "未记录"),
                }
            )

        # work items — FG-15 prefixing carries attribution (FG-17)
        for row in rows:
            provenance = str(row.get("provenance") or "")
            if not is_admissible_provenance(provenance):
                gaps.append(
                    f"{team.slug}: item {row.get('item_id')} provenance is untracked "
                    f"({provenance}); item degraded to unknown without a source"
                )
                continue
            state = str(row.get("state") or "unknown")
            if state not in LEDGER_STATES:
                gaps.append(f"{team.slug}: item {row.get('item_id')} state {state!r} unrecognized → unknown")
                state = "unknown"
            phase_id = namespaced(team.slug, str(row.get("phase_ref") or "PH-0001"))
            if state == "completed":
                completed_per_phase[phase_id] = completed_per_phase.get(phase_id, 0) + 1
            entry: dict[str, Any] = {
                "item_id": namespaced(team.slug, str(row["item_id"])),
                "item_name": str(row.get("title") or row["item_id"]),
                "phase_id": phase_id,
                "status": STATE_TO_SOURCE_LITERAL.get(state, ""),
                "source": provenance,
            }
            if row.get("identity") == "inferred":
                inferred_fields.append(
                    {"field": f"work_items[{entry['item_id']}].item_id",
                     "inferred_from": "台账发放显式 ID 之前的历史条目,身份由标题+阶段派生(FR-027)"}
                )
            if row.get("excluded_reason"):
                entry["progress_source"] = f"excluded: {row['excluded_reason']}"
            work_items.append(entry)

        sources.append(
            {
                "source_id": f"S-{len(sources) + 1:04d}",
                "source_kind": "user-form",
                "source_ref": f".specify/teams/{team.slug}/",
                "covers": ["work_items", "phases", "people"],
            }
        )

    # ------------------------------------------------------------------
    # goal narrative + milestones (FR-008 / FR-010 / FR-012 / FR-013)
    #
    # The archived definition is authoritative when present; otherwise the
    # pre-037 inline behaviour is preserved byte-for-byte so existing teams keep
    # working with zero edits.
    # ------------------------------------------------------------------
    definition = load_goal_definition(repo_root, goal_slug)
    inline_texts = {t.goal_text for t in teams if t.goal_text}
    goal_meta: dict[str, Any] = {}

    if definition:
        goal_text = definition["objective"]
        criteria = list(definition["criteria"])
        milestone_source = definition["relpath"]
        goal_meta["goal_source"] = "definition"
        goal_meta["goal_definition"] = definition["relpath"]
        # FR-012 — the definition wins, and the divergence is surfaced, not hidden.
        divergent = sorted(t.slug for t in teams if t.goal_text and t.goal_text != goal_text)
        if divergent:
            gaps.append(
                "团队内联 goal 与被引用的定义不一致,以定义为权威(FR-012);"
                f"不一致的团队:{', '.join(divergent)}"
            )
    else:
        goal_text = next((t.goal_text for t in teams if t.goal_text), "")
        criteria = extract_milestones(goal_text)
        milestone_source = f".specify/teams/{teams[0].slug}/team.md"
        goal_meta["goal_source"] = "inline"
        # FR-010 — a declared identity with no definition is a broken reference.
        # Reported only once the project has adopted the concept (the archive
        # exists), so a pure-036 project that never defined a goal is untouched.
        if (repo_root / ARCHIVE_DIRNAME).is_dir():
            declared = sorted(t.slug for t in teams if t.fm.get("goal_slug"))
            if declared:
                gaps.append(
                    f"断链引用(FR-010):团队 {', '.join(declared)} 声明了 goal_slug "
                    f"'{goal_slug}',但 {ARCHIVE_DIRNAME}/{goal_slug}/goal.md 不存在;"
                    "已回退到内联目标,未降级为空目标"
                )
        # GI-4 — without a definition, differing inline wordings need arbitration.
        if len(inline_texts) > 1:
            gaps.append(
                "同一 goal_slug 下各团队的 goal 正文不一致,以显式声明为准(GI-4);差异记入元信息供人裁决"
            )

    anchor = work_items[0]["item_id"] if work_items else None
    milestones = [
        {
            "milestone_id": f"MS-{i:04d}",
            "milestone_name": text[:60],
            **({"anchor_item_id": anchor} if anchor else {}),
            "source": milestone_source,
        }
        for i, text in enumerate(criteria, 1)
    ]
    criteria_count = len(milestones)
    # ------------------------------------------------------------------
    # 038 — authored-done Targets join the milestones group carrying their
    # own source marker; the distinction from the criteria projection rides
    # the existing `source` column (D7) — summarize-project stays untouched.
    # ------------------------------------------------------------------
    done_targets = [
        t for t in (definition or {}).get("targets", []) if t["status"] == "done"
    ]
    for target in sorted(done_targets, key=lambda t: t["id"]):
        milestones.append(
            {
                "milestone_id": f"MS-{len(milestones) + 1:04d}",
                "milestone_name": target["statement"][:60],
                **({"anchor_item_id": anchor} if anchor else {}),
                "status": "achieved",
                "source": f"goal-target:{goal_slug}/goal.md#{target['id']}",
            }
        )
    if not milestones:
        if definition:
            # GD-8 — an empty criteria set is legal; declare it, never invent one.
            gaps.append(
                "该 goal 的定义未提供可验证判据(None provided.),里程碑组为空"
                "(依赖 work_items 满足 R 档组级约束)"
            )
        else:
            gaps.append("goal 正文未声明可验证成功判据,里程碑组为空(依赖 work_items 满足 R 档组级约束)")
    elif criteria_count == 0 and done_targets:
        gaps.append(
            "判据为空而存在 done Target(FR-016):里程碑组由 Target 来源条目填充,"
            "来源标记 " + ", ".join(
                f"goal-target:{goal_slug}/goal.md#{t['id']}" for t in done_targets)
        )

    # coverage — FG-8, always emitted
    truncated = sum(c for c in completed_per_phase.values() if c > AGGREGATE_COMPLETED_ABOVE)
    excluded = sum(1 for w in work_items if str(w.get("progress_source", "")).startswith("excluded:"))
    form: dict[str, Any] = {
        "schema": "project-input/v1",
        "project": {
            "project_name": goal_slug,
            "project_desc": (goal_text[:180] if goal_text else ""),
            "baseline_date": baseline_date,
            "repos": [],  # FG-5 — repository derivation stays opt-in and unused
        },
        "phases": phases,
        "work_items": work_items,
        "milestones": milestones,
        "people": people,
        "features": [],
        "sources": sources,
        "coverage": {
            "candidate_total": sum(len(v) for v in per_team_items.values()),
            "excluded": excluded,
            "granularity_truncated": truncated,
            "unattributed": 0,
            "source_label": "团队条目台账 items.jsonl",
        },
    }
    # ------------------------------------------------------------------
    # 038 — the slice axis. Only when the archived definition carries a
    # ## Targets section; a targetless goal's form stays byte-identical (SC-002).
    # ------------------------------------------------------------------
    if definition and definition.get("targets"):
        form["targets"] = fold_targets_axis(
            per_team_items, definition["targets"], goal_slug, gaps)
    # ------------------------------------------------------------------
    # multi-team coordination (FR-033..FR-042): derived roster + overlap findings.
    # Detection rides this refresh — no second trigger. It only reports; the
    # coordination round and any team.md write are a separate, human-ratified step.
    # ------------------------------------------------------------------
    roster = build_roster(teams)
    overlaps = detect_overlaps(teams)
    contested = [f for f in overlaps if f["verdict"] == "overlap"]
    for f in contested:
        paths = sorted({p for pair in f["entries"] for p in pair})
        gaps.append(
            f"写重叠(争用区,FR-037/FR-038):团队 {f['pair'][0]} 与 {f['pair'][1]} "
            f"的 Write Scope 相交于 {', '.join(paths)};须归给唯一团队或转为禁写区,"
            "MUST NOT 停留在双方都可写"
        )
    for f in overlaps:
        if f["verdict"] == "undecidable" and f["kind"] == "undeclared":
            gaps.append(f"范围未声明,无法判定重叠(FR-042):{f.get('note', '')}")
    goal_meta["roster"] = roster
    goal_meta["overlaps"] = overlaps
    goal_meta["contested_areas"] = contested

    meta = {
        "goal_slug": goal_slug,
        "goal_identity": kind,
        "contributing_teams": [t.slug for t in teams],
        "inferred_fields": inferred_fields,
        "material_gaps": gaps,
        "declined": False,
        **goal_meta,
    }
    return form, gaps, meta


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive a summarize-project input form from team artifacts."
    )
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--goal", help="aggregate every team declaring this goal_slug")
    selector.add_argument("--team", help="resolve this team's goal, then aggregate that goal")
    parser.add_argument("--out", help="form destination (default: <delivery_dir>/data/project-input.yaml)")
    parser.add_argument("--baseline", help="baseline date (default: latest ledger/report timestamp)")
    parser.add_argument("--repo-root", default=".", help="repository root (default: cwd)")
    parser.add_argument("--json", action="store_true", help="emit a machine-readable generation report")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    teams_root = repo_root / ".specify/teams"
    if not teams_root.is_dir():
        fail(f"no teams directory at {teams_root}", EXIT_INPUT_ERROR)

    teams = discover_teams(teams_root)
    if not teams:
        fail("no persisted teams found", EXIT_INPUT_ERROR)

    goal_slug, kind, members = resolve_goal(teams, goal=args.goal, team_slug=args.team)
    if not any(t.has_material() for t in members):
        report = {
            "status": "declined(no-material)",
            "goal_slug": goal_slug,
            "goal_identity": kind,
            "contributing_teams": [t.slug for t in members],
            "reason": "该 goal 下所有团队既无条目台账也无运行报告,拒绝出总结",
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return EXIT_NO_MATERIAL

    form, gaps, meta = build_form(repo_root, goal_slug, kind, members, args.baseline)
    if meta.get("declined"):
        print(
            json.dumps(
                {
                    "status": "declined(no-material)",
                    "goal_slug": goal_slug,
                    "material_gaps": gaps,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return EXIT_NO_MATERIAL

    delivery_dir = repo_root / ".specify/goal" / goal_slug / "summary"
    out_path = Path(args.out) if args.out else delivery_dir / "data/project-input.yaml"
    if not out_path.is_absolute():
        out_path = repo_root / out_path

    # FR-019 — a deliberate goal edit is recorded, not silently absorbed. The prior
    # form is consulted ONLY to detect the change; the ledger stays authoritative
    # for accumulation, so this never makes the derived form a source of truth.
    if out_path.is_file():
        try:
            previous = yaml.safe_load(out_path.read_text(encoding="utf-8")) or {}
            prior_desc = str((previous.get("project") or {}).get("project_desc") or "")
        except yaml.YAMLError:
            prior_desc = ""
        current_desc = str(form["project"]["project_desc"])
        if prior_desc and prior_desc != current_desc:
            note = (
                "goal 叙述自上次总结以来发生变更(FR-019):历史工作项保留,"
                f"前值『{prior_desc[:60]}』→ 现值『{current_desc[:60]}』"
            )
            gaps.append(note)
            meta["goal_changed"] = True
            meta["goal_desc_previous"] = prior_desc
            meta["material_gaps"] = gaps

    out_path.parent.mkdir(parents=True, exist_ok=True)  # FG-11 — only here

    # FR-035 / WS-13 — serialize concurrent refreshes of one goal directory and make
    # the write atomic, so a refresh either lands complete or leaves the previous
    # summary intact. A half-written delivery directory is a prohibited state.
    lock_path = out_path.parent / ".refresh.lock"
    lock_handle = None
    try:
        lock_handle = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        stale = False
        try:
            stale = (time.time() - lock_path.stat().st_mtime) > LOCK_STALE_SECONDS
        except OSError:
            stale = True
        if not stale:
            print(
                json.dumps(
                    {
                        "status": "skipped(serialized)",
                        "goal_slug": goal_slug,
                        "reason": (
                            "另一次针对同一 goal 的刷新正在进行,本次按 FR-035 串行化让位;"
                            "调用方应在其运行报告中记录状态行"
                        ),
                        "lock": str(lock_path),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return EXIT_SERIALIZED
        lock_path.unlink(missing_ok=True)
        lock_handle = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)

    try:
        os.write(lock_handle, str(os.getpid()).encode())
        os.close(lock_handle)
        lock_handle = None

        rendered = yaml.safe_dump(
            form, allow_unicode=True, sort_keys=False, default_flow_style=False, width=100
        )
        tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
        tmp_path.write_text(rendered, encoding="utf-8")
        os.replace(tmp_path, out_path)  # atomic within the same directory

        # Derived roster (FR-033/FR-034) lands beside the form, inside the same lock.
        # It always belongs in the goal's canonical summary/ subtree, even when --out
        # redirects the form elsewhere, so ensure that directory exists first.
        delivery_dir.mkdir(parents=True, exist_ok=True)
        roster_path = delivery_dir / "roster.md"
        roster_md = render_roster_md(goal_slug, meta.get("roster", []),
                                     meta.get("overlaps", []), meta.get("contested_areas", []))
        roster_tmp = roster_path.with_suffix(".md.tmp")
        roster_tmp.write_text(roster_md, encoding="utf-8")
        os.replace(roster_tmp, roster_path)
    finally:
        if lock_handle is not None:
            os.close(lock_handle)
        lock_path.unlink(missing_ok=True)

    report = {
        "status": "produced",
        "form": str(out_path.relative_to(repo_root)) if out_path.is_relative_to(repo_root) else str(out_path),
        "delivery_dir": str(delivery_dir.relative_to(repo_root)),
        **meta,
        "entity_counts": {
            k: len(form[k])
            for k in ("phases", "work_items", "milestones", "people", "features", "sources")
        },
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"form written: {report['form']}")
        print(f"goal: {goal_slug} ({kind}) ← teams: {', '.join(meta['contributing_teams'])}")
        for gap in gaps:
            print(f"  gap: {gap}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
