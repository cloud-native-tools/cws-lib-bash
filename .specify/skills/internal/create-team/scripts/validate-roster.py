#!/usr/bin/env python3
"""Creation-time reporter-seat roster guard (088-speckit-visualization).

Judges ONE persisted roster against the reporter-seat obligation
(`reporter-seat.contract.md` C-16 / C-17 / C-21; a contract fragment is
reached by name — a shipped file carries no spec-directory path, because that
directory is one repository's development doc and is not distributed with the
framework). It is a creation-time check with a closed defect set: a
roster either satisfies the obligation, carries exactly one named defect, or
could not be read at all.

What it judges (and nothing else):

* **C-16 structural set, closed at three names.** ``absent-seat`` (no
  ``role: reporter`` member), ``unresolvable-agent`` (the seat's ``agent``
  resolves to neither a shipped Agent Template nor a seat instance that
  references one) and ``two-seats`` (two or more ``role: reporter`` members —
  the seat's cardinality is at most one, `data-model.md` E1 / INV-03). A fourth
  structural class MUST NOT be added here.
* **C-17 recorded reason.** ``reporting-reason`` makes a seat-less roster
  conforming and is echoed, so a recorded omission stays distinguishable from a
  forgotten seat. ``all-lanes-in-session-single-interval`` and
  ``host-cannot-host-reporter`` are its closed domain; a value outside it is
  the one non-structural defect this script owns (``out-of-domain-reason``),
  reported instead of — never in addition to — a structural verdict, because a
  roster carrying a malformed reason was never judged.

Exit codes (C-16): ``0`` the roster satisfies the obligation; ``1`` one named
defect; ``2`` input error (file missing, frontmatter unparsable). The script
performs ZERO writes and imports only the standard library (C-21).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

EXIT_OK = 0
EXIT_DEFECT = 1
EXIT_INPUT_ERROR = 2

#: C-16's closed structural set. One name per class, each tellable apart.
DEFECT_ABSENT_SEAT = "absent-seat"
DEFECT_UNRESOLVABLE_AGENT = "unresolvable-agent"
DEFECT_TWO_SEATS = "two-seats"

#: C-17's defect — the one non-structural class, owned by the reason's domain.
DEFECT_OUT_OF_DOMAIN_REASON = "out-of-domain-reason"

#: The seat literal C-16 fixes; every defect line MUST name it.
SEAT_ROLE = "reporter"

#: C-17's closed reason set.
REASONS = (
    "all-lanes-in-session-single-interval",
    "host-cannot-host-reporter",
)

#: The shipped Template store and the seat-instance store (the two places an agent name may resolve).
TEMPLATE_STORE = Path("agents")
INSTANCE_STORE = Path(".specify") / "agents" / "templates"

_TOP_KEY = re.compile(r"^([A-Za-z0-9_.-]+):(.*)$")
_ITEM_KEY = re.compile(r"^\s{2,}-\s+([A-Za-z0-9_.-]+):(.*)$")
_FIELD_KEY = re.compile(r"^\s+([A-Za-z0-9_.-]+):(.*)$")


# --------------------------------------------------------------------------- #
# parsing — a deliberately narrow reader for the roster frontmatter the schema owns
# --------------------------------------------------------------------------- #
def split_frontmatter(text: str) -> str | None:
    """Return the frontmatter body without its delimiters, or ``None`` when the file has none."""
    if not text.startswith("---"):
        return None
    lines = text.splitlines()
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index])
    return None


def _strip_comment(value: str) -> str:
    """Drop a trailing ``# …`` comment from an unquoted scalar, preserving a ``#`` inside quotes or brackets."""
    out: list[str] = []
    quote = ""
    depth = 0
    for char in value:
        if quote:
            out.append(char)
            if char == quote:
                quote = ""
            continue
        if char in "\"'":
            quote = char
            out.append(char)
            continue
        if char in "[":
            depth += 1
        elif char in "]":
            depth = max(0, depth - 1)
        elif char == "#" and depth == 0:
            break
        out.append(char)
    return "".join(out).strip()


def _unquote(value: str) -> str:
    value = _strip_comment(value)
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(body: str) -> dict[str, Any]:
    """Parse the roster frontmatter into ``{top-level key: value}``.

    ``members`` becomes a list of item dicts; a nested mapping (such as
    ``reporting-territory:``) becomes a nested dict. Scalars keep their
    unquoted text. An unparsable block raises ``ValueError`` so the caller can
    exit 2 rather than guess (C-16 ``unparsable``).
    """
    data: dict[str, Any] = {}
    current_top: str | None = None
    member: dict[str, Any] | None = None
    nested: dict[str, Any] | None = None
    nested_key: str | None = None
    folded: str | None = None

    for raw in body.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if folded is not None:
            # A block scalar (``key: >`` / ``key: |``) continues on every following INDENTED line, whether the key is
            # top-level or a member field. The guard never needs its content, so the lines are consumed, not read.
            if raw.startswith((" ", "\t")):
                continue
            folded = None
        item = _ITEM_KEY.match(raw)
        if item and current_top == "members":
            member = {item.group(1): _unquote(item.group(2))}
            data["members"].append(member)
            nested, nested_key = None, None
            continue
        top = _TOP_KEY.match(raw)
        if top:
            current_top = top.group(1)
            value = _strip_comment(top.group(2))
            member = None
            nested, nested_key = (None, None)
            if value in (">", "|", ">-", "|-", ">+", "|+"):
                folded = current_top
                value = ""
            if value == "":
                data[current_top] = [] if current_top == "members" else {}
            else:
                data[current_top] = _unquote(value)
            continue
        if current_top is None:
            raise ValueError("frontmatter content before any top-level key")
        container = data.get(current_top)
        if isinstance(container, dict) and nested is container and raw.startswith(("    ", "\t")):
            # A block sequence or deeper mapping under a nested key (``territory.write:`` → ``- <path>``). Its entries
            # are never needed by this guard: only `config.reporting-reason` and the members' own fields are read, and
            # both sit at a depth this branch cannot reach.
            continue
        field = _FIELD_KEY.match(raw)
        if not field:
            raise ValueError("unrecognised frontmatter line: %r" % raw)
        key, value = field.group(1), _strip_comment(field.group(2))
        if value in (">", "|", ">-", "|-", ">+", "|+"):
            folded = key
            value = ""
        if member is not None:
            if value.strip() == "":
                nested, nested_key = {}, key
                member[key] = nested
            else:
                member[key] = _unquote(value)
                nested, nested_key = None, None
            continue
        container = data.get(current_top)
        if isinstance(container, dict) and value.strip() == "":
            # A nested mapping under a top-level key (``config:`` → ``reporting-reason:``).
            nested, nested_key = container, key
            continue
        if isinstance(container, dict):
            container[key] = _unquote(value)
            continue
        raise ValueError("unrecognised frontmatter nesting: %r" % raw)
    return data


def _seat_members(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [m for m in members if str(m.get("role", "")).strip() == SEAT_ROLE]


# --------------------------------------------------------------------------- #
# resolution
# --------------------------------------------------------------------------- #
def _candidate_roots(roster: Path) -> list[Path]:
    """The directories an ``agent`` name may resolve under: the roster's ancestors plus the cwd."""
    roots: list[Path] = []
    for parent in roster.resolve().parents:
        roots.append(parent)
    cwd = Path.cwd().resolve()
    if cwd not in roots:
        roots.append(cwd)
    return roots


def agent_resolves(agent: str, roster: Path) -> bool:
    """True when ``agent`` names a shipped Agent Template or a seat instance in either of the two stores."""
    name = agent.strip()
    if not name:
        return False
    stems = (name, name[: -len(".agent.md")] if name.endswith(".agent.md") else name)
    for root in _candidate_roots(roster):
        for store in (TEMPLATE_STORE, INSTANCE_STORE):
            base = root / store
            if not base.is_dir():
                continue
            for stem in stems:
                for suffix in (".agent.md", ".md"):
                    if (base / (stem + suffix)).is_file():
                        return True
    return False


# --------------------------------------------------------------------------- #
# judgement
# --------------------------------------------------------------------------- #
def _slug(data: dict[str, Any], roster: Path) -> str:
    slug = str(data.get("slug") or "").strip()
    return slug or roster.parent.name


def judge(path: Path) -> tuple[int, str]:
    """Return ``(exit code, one line of output)`` for one roster path."""
    if not path.is_file():
        return EXIT_INPUT_ERROR, "input error: roster file not found: %s" % path
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return EXIT_INPUT_ERROR, "input error: roster unreadable: %s (%s)" % (path, exc)
    body = split_frontmatter(text)
    if body is None:
        return EXIT_INPUT_ERROR, "input error: no frontmatter block in %s" % path
    try:
        data = parse_frontmatter(body)
    except ValueError as exc:
        return EXIT_INPUT_ERROR, "input error: frontmatter unparsable in %s (%s)" % (path, exc)

    slug = _slug(data, path)
    raw_config = data.get("config")
    config = raw_config if isinstance(raw_config, dict) else {}
    reason = str(config.get("reporting-reason") or "").strip()

    # C-17 first: a recorded reason decides conformance on its own, and its domain is checked before any
    # structural verdict, so a malformed record is never silently folded into a structural defect.
    if reason:
        if reason not in REASONS:
            return EXIT_DEFECT, (
                "%s: team %s — the recorded reporting-reason %r is outside the closed set %s"
                % (DEFECT_OUT_OF_DOMAIN_REASON, slug, reason, " | ".join(REASONS))
            )
        seats = _seat_members(data.get("members") or [])
        if len(seats) > 1:
            return EXIT_DEFECT, (
                "%s: team %s — %d %s seats carry two or more members; the seat's cardinality is at most one"
                % (DEFECT_TWO_SEATS, slug, len(seats), SEAT_ROLE)
            )
        return EXIT_OK, (
            "conforming: team %s records reporting-reason=%s — the reporting duty is carried by the"
            " orchestrating session itself" % (slug, reason)
        )

    members = data.get("members") or []
    if not isinstance(members, list):
        return EXIT_INPUT_ERROR, "input error: members must be a list in %s" % path
    seats = _seat_members(members)
    if not seats:
        return EXIT_DEFECT, (
            "%s: team %s — no members[] row carries role: %s, and no reporting-reason is recorded"
            % (DEFECT_ABSENT_SEAT, slug, SEAT_ROLE)
        )
    if len(seats) > 1:
        return EXIT_DEFECT, (
            "%s: team %s — %d %s seats carry two or more members; the seat's cardinality is at most one"
            % (DEFECT_TWO_SEATS, slug, len(seats), SEAT_ROLE)
        )
    agent = str(seats[0].get("agent") or "").strip()
    if not agent_resolves(agent, path):
        return EXIT_DEFECT, (
            "%s: team %s — the %s seat's agent %r resolves to neither a shipped Agent Template under %s/ nor"
            " a seat instance under %s/"
            % (DEFECT_UNRESOLVABLE_AGENT, slug, SEAT_ROLE, agent, TEMPLATE_STORE, INSTANCE_STORE)
        )
    return EXIT_OK, "conforming: team %s carries exactly one %s seat (agent: %s)" % (slug, SEAT_ROLE, agent)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Judge a roster against the reporter-seat obligation (087).")
    parser.add_argument("team_file", help="path to the roster's team.md")
    args = parser.parse_args(argv)
    code, line = judge(Path(args.team_file))
    print(line)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
