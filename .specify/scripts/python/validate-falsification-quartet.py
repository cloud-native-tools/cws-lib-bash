#!/usr/bin/env python3
"""validate-falsification-quartet.py — deterministic verdict for a falsification quartet (Feature 076).

The quartet turns "the falsification attempt ran" from a claim into a fact the artifact can
distinguish. The owner of the field semantics and of the rejection rules is
``.specify/shared/guidelines/critique-and-self-critique.md`` § 产出形态:四元组; this checker consumes them
and prints a verdict, it never restates them.

Payload form: the four literal keys ``attempt`` / ``exit_code`` / ``observation`` /
``would_go_red_if``, each appearing exactly once, the value on the same line or in an indented
continuation of that key. A key may stand at the start of a line or behind a markdown list marker
(``- `` / ``* `` / ``+ ``) or heading prefix (``## ``); an INDENTED key is not a key — it belongs to
the value above it.

Closed rejection reason set (data-model.md E6; no seventh value exists):
  missing-field            one of the four keys does not appear (a key appearing more than once is
                           read the same way: the field is not present exactly once, so it cannot
                           be read unambiguously — the reason set has no duplicate-field member)
  empty-field              the key appears but its value (inline plus indented continuation) is blank
  exit-code-not-integer    ``exit_code`` is not an integer
  observation-not-raw      ``observation`` does not begin with the literal ``raw:`` marker
  tautology                ``would_go_red_if`` does not carry both halves: the split point is the
                           FIRST occurrence of the literal ``red:`` (a later ``red:`` never moves
                           it); at least one backtick span must precede it (the named input that was
                           broken) and at least one must follow it (an assertion name, a check
                           label or a non-zero exit code)
  input-unreadable         the payload cannot be read (exit 2, disposed as a rejection)

The checker MUST NOT replay ``attempt`` and MUST NOT judge whether it is replayable — replay and
replayability belong to SI-6 and the reviewer, so the closed set carries no
``attempt-not-replayable``. It judges shape only: a ``raw:`` prefix can be forged and a red result
cannot be proven from the shape; both stay disclosed non-blocking limitations of the owner.

Exit codes: 0 = accepted / 1 = rejected / 2 = payload unreadable (also a rejection).
Read-only: standard library only, no write point, no resident process.

Usage: python3 validate-falsification-quartet.py <payload.md> [--json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

EXIT_ACCEPTED = 0
EXIT_REJECTED = 1
EXIT_UNREADABLE = 2

STATUS_ACCEPTED = "accepted"
STATUS_REJECTED = "rejected"

REASONS = (
    "missing-field",
    "empty-field",
    "exit-code-not-integer",
    "observation-not-raw",
    "tautology",
    "input-unreadable",
)

# The closed quartet (owner: .specify/shared/guidelines/critique-and-self-critique.md).
KEYS = ("attempt", "exit_code", "observation", "would_go_red_if")

KEY_RE = re.compile(r"^(?:[-*+][ \t]+|#{1,6}[ \t]+)?(%s)[ \t]*:[ \t]*(.*)$" % "|".join(KEYS))
INTEGER_RE = re.compile(r"^[+-]?\d+$")

RAW_MARKER = "raw:"
RED_MARKER = "red:"
BACKTICK = "`"


class Verdict:
    """One judgment: status, reason (None when accepted) and the detail naming the failure."""

    __slots__ = ("status", "reason", "detail")

    def __init__(self, status, reason=None, detail=""):
        self.status = status
        self.reason = reason
        self.detail = detail

    def as_dict(self, payload_path):
        return {
            "payload": str(payload_path),
            "status": self.status,
            "reason": self.reason,
            "detail": self.detail,
        }


def accepted():
    return Verdict(STATUS_ACCEPTED, None, "all four fields present, decidable and non-vacuous")


def rejected(reason, detail):
    assert reason in REASONS, "reason %r is outside the closed set" % (reason,)
    return Verdict(STATUS_REJECTED, reason, detail)


def unreadable(path, why):
    return Verdict(STATUS_REJECTED, "input-unreadable", "payload is unreadable (%s): %s" % (path, why))


def read_payload(path):
    """Return ``(verdict, text)``; ``verdict`` is not None when the payload cannot be read."""
    target = Path(path)
    if not target.is_file():
        return unreadable(path, "no such file"), None
    try:
        text = target.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        return unreadable(path, "not decodable text (%s)" % exc.__class__.__name__), None
    if not text.strip():
        return unreadable(path, "no content lines"), None
    return None, text


def parse_fields(text):
    """``name -> value`` for the quartet keys; a repeated key keeps every occurrence in order.

    Values are the inline remainder plus any indented continuation lines beneath the key, which is
    the payload grammar the owner declares. A key may stand alone or behind a markdown list marker
    (``- `` / ``* `` / ``+ ``) or a heading prefix (``## ``) — SI-4 payloads are markdown, so an
    indented bullet list is an ordinary shape and rejecting it would record a payload that did run
    its falsification attempt as having no attempt. What the anchor forbids is an INDENTED key: an
    indented line belongs to the value above it, which keeps the continuation rule unambiguous.
    """
    fields = {}
    current = None
    for raw in text.splitlines():
        match = KEY_RE.match(raw)
        if match:
            name, value = match.group(1), match.group(2)
            fields.setdefault(name, []).append([value.strip()])
            current = name
            continue
        if not raw.strip():
            current = None
            continue
        if current is not None and (raw[:1].isspace()):
            fields[current][-1].append(raw.strip())
            continue
        current = None
    return {name: [" ".join(parts).strip() for parts in occurrences]
            for name, occurrences in fields.items()}


def judge(text):
    """Judge one payload body and return a :class:`Verdict`."""
    fields = parse_fields(text)

    # 1. missing-field — a key that does not appear exactly once cannot be read unambiguously.
    for name in KEYS:
        occurrences = fields.get(name, [])
        if not occurrences:
            return rejected("missing-field", "missing field: %s (the quartet requires it once)" % name)
        if len(occurrences) > 1:
            return rejected(
                "missing-field",
                "field %s appears %d times; exactly one occurrence is required"
                % (name, len(occurrences)),
            )

    values = {name: fields[name][0] for name in KEYS}

    # 2. empty-field — the key is present but carries no value.
    for name in KEYS:
        if not values[name]:
            return rejected("empty-field", "empty field: %s carries no value" % name)

    # 3. exit-code-not-integer.
    exit_code = values["exit_code"]
    if not INTEGER_RE.match(exit_code):
        return rejected(
            "exit-code-not-integer",
            "exit_code is not an integer: %r" % exit_code,
        )

    # 4. observation-not-raw — the literal marker is the mechanical proxy for 「not a paraphrase」.
    observation = values["observation"]
    if not observation.startswith(RAW_MARKER):
        return rejected(
            "observation-not-raw",
            "observation does not begin with the literal `%s` marker (it reads as a paraphrase, "
            "not a raw excerpt): %r" % (RAW_MARKER, observation),
        )

    # 5. tautology — both halves of would_go_red_if, split at the FIRST `red:` only.
    verdict = judge_would_go_red_if(values["would_go_red_if"])
    if verdict is not None:
        return verdict

    return accepted()


def judge_would_go_red_if(value):
    """The anti-vacuity shape; returns a rejection verdict or None when both halves are present."""
    position = value.find(RED_MARKER)
    if position < 0:
        return rejected(
            "tautology",
            "would_go_red_if carries no `%s` marker, so neither half can be read" % RED_MARKER,
        )
    input_half = value[:position]
    signal_half = value[position + len(RED_MARKER):]
    if input_half.count(BACKTICK) < 2:
        return rejected(
            "tautology",
            "would_go_red_if has no backtick span before the first `%s`, so the named input that "
            "was broken is missing" % RED_MARKER,
        )
    if signal_half.count(BACKTICK) < 2:
        return rejected(
            "tautology",
            "would_go_red_if has no backtick span after the first `%s`, so the signal half names "
            "no assertion, check label or non-zero exit code" % RED_MARKER,
        )
    return None


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

def main(argv=None):
    _sig_guard(argv, declared=['--json'])  # answer --version / reject an undeclared option
    parser = argparse.ArgumentParser(
        prog="validate-falsification-quartet.py",
        description="Judge one falsification-quartet payload and print the verdict.",
    )
    _sig_configure(parser)

    parser.add_argument("payload", help="the payload file carrying the four literal keys")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])

    failure, text = read_payload(args.payload)
    verdict = failure if failure is not None else judge(text)

    if args.json:
        print(json.dumps(verdict.as_dict(args.payload), ensure_ascii=False, indent=2))
    else:
        print("payload: %s" % args.payload)
        print("status: %s" % verdict.status)
        if verdict.reason:
            print("reason: %s" % verdict.reason)
        print("detail: %s" % verdict.detail)

    if verdict.reason == "input-unreadable":
        return EXIT_UNREADABLE
    return EXIT_ACCEPTED if verdict.status == STATUS_ACCEPTED else EXIT_REJECTED


if __name__ == "__main__":
    sys.exit(main())
