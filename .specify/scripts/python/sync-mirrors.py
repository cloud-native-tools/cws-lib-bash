#!/usr/bin/env python3
"""Single-source mirror sync for spec-kit (P1, harvested from ai-website-cloner-template).

Canonical sources fan out to their runtime mirrors in one command:

  .specify/templates/            -> .specify/templates/   (excluding commands/, see below)
  skills/external/<name>/ -> .specify/skills/<name>/           (flat runtime layer;
                           discoverable by host agents via the one-level scan)
  skills/internal/<name>/ -> .specify/skills/internal/<name>/  (nested runtime layer;
                           never registered for discovery, consumed by /speckit.*
                           workflows via explicit paths)
  agents/               -> .specify/agents/templates/  (Agent Template layer; instances/
                           and execution/ are project-local, never mirrored)
  .specify/scripts/              -> .specify/scripts/
  .specify/shared/               -> .specify/shared/
  .specify/templates/commands/*  -> per-tool copies (delegated to regen-command-copies.py)

The .specify/templates/commands/ mirror is intentionally NO LONGER maintained:
per-tool command copies are generated directly from .specify/templates/commands/ by
regen-command-copies.py, so the subtree is excluded from the templates pair on
both sides.

A few mirrors are not plain copies: they carry one declared *projection* on top of
their source, because a mirror-side flag surface cannot live inside a copy that is an
exact replica of the source. ``PROJECTED_FILES`` below is the ONE declaration of that rule (contract
``contracts/mirror-projection.contract.md`` C-34, owner page
``.specify/shared/definitions/script-interface-definitions.md`` section
"projection declaration"). Every consumer -- this engine's check and write modes,
the mirror parity suite and ``script-interface-check.py --check-projection`` --
reads that table instead of keeping a second list.

Modes:
  --check   report drift, exit 2 if any (CI gate); never writes. A projected file
            is compared as ``mirror == project(source)``, every other file as
            byte equality, and each projected pair's line names its kind -- the
            two verdicts are never merged into one "mirrors agree" sentence.
  --only PATH  (repeatable) restrict the run to the given repo-relative path
            prefix (e.g. --only .specify/scripts/python/feedback-utils.py), so a
            feature-scoped sync never drags unrelated mirror drift into the
            change surface; the regen-command-copies delegation is skipped
            unless a prefix targets .specify/templates/commands/.

Write-mode failures are collected per file, never fatal mid-pass: an unwritable
mirror file (e.g. a root-owned leftover) is reported as FAIL, the remaining
files still sync, and the run ends with exit 1 plus a failure summary — a
stale mirror must never pass silently.

Junk entries (__pycache__, node_modules, .DS_Store) are ignored on both sides
and never copied.

Extra files that exist only in a mirror are never deleted (archive-not-delete
discipline), but for pairs marked STRICT below they FAIL --check. Rationale:
`specify init` distributes a framework tree by copying the canonical source over
the mirror (shutil.copytree(..., dirs_exist_ok=True)) — an additive merge that
never syncs mirror->source. So a mirror-only file is unreachable by init and can
never land in a downstream project, however correct it looks locally. Two valid
remedies, and the check deliberately does not presume which: add the missing
canonical source (if the file should ship), or delete the mirror copy (if it is
a superseded leftover).
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
# Guard: invoked via the .specify/scripts/python/ mirror copy, parents[2]
# resolves to `.specify` and every mirror target doubles into
# `.specify/.specify/` (stray-projection defect). A dir named `.specify`
# is never a repo root.
if REPO_ROOT.name == ".specify":
    REPO_ROOT = REPO_ROOT.parent

# (source, mirror, strict_extras, exclude_parts) pairs; source is canonical.
# strict_extras=True means a mirror-only file is an ERROR under --check: the tree
# is entirely framework-owned, so an unsourced file can never reach downstream
# projects via `specify init`. Both skills pairs are intentionally lenient
# because a project may legitimately keep its own local skills in the mirror.
# The skills source is two layers with DIFFERENT runtime shapes: external
# mirrors flat into .specify/skills/<name>/ (host discovery surface), internal
# mirrors nested into .specify/skills/internal/<name>/ (path-referenced only).
# exclude_parts are path components skipped on BOTH sides of the pair; the
# templates pair excludes commands/ because the .specify/templates/commands
# mirror is retired (per-tool copies come straight from .specify/templates/commands/
# via regen-command-copies.py). The external pair additionally releases
# `internal`: that name is the internal layer's RESERVED runtime namespace, so
# .specify/skills/internal/** is sibling-pair-owned, never an unsourced extra.
MIRROR_PAIRS = [
    ("templates", ".specify/templates", False, {"commands"}),
    ("skills/external", ".specify/skills", False, {"site", "internal"}),
    ("skills/internal", ".specify/skills/internal", False, {"site"}),
    ("agents", ".specify/agents/templates", False, set()),
    ("scripts", ".specify/scripts", True, set()),
    ("shared", ".specify/shared", False, set()),
]

IGNORE_NAMES = {"__pycache__", "node_modules", ".DS_Store", ".gitkeep"}

# --------------------------------------------------------------------------------------
# The projection declaration (C-34) -- the ONE statement of which mirrors are projected
# --------------------------------------------------------------------------------------

#: The name a consumer looks for before executing this module for its declaration.
PROJECTED_TABLE_NAME = "PROJECTED_FILES"

#: One row per projected mirror: ``(repo-relative mirror, kind, source)``. The mirror path
#: is the name a reader searches for, the kind decides which block is inserted and where,
#: and the source states the pair explicitly. The two kinds are the contract's CLOSED set
#: (C-34); a third MUST NOT appear here before that contract is revised.
PROJECTED_FILES = (
    (".specify/scripts/python/script_interface_cli.py",
     "python-version-bridge", ".specify/scripts/python/script_interface_cli.py"),
    (".specify/scripts/python/sync-mirrors.py",
     "python-version-bridge", ".specify/scripts/python/sync-mirrors.py"),
    (".specify/scripts/python/script-interface-check.py",
     "python-version-bridge", ".specify/scripts/python/script-interface-check.py"),
    (".specify/scripts/bash/check-prerequisites.sh",
     "bash-version-guard", ".specify/scripts/bash/check-prerequisites.sh"),
    (".specify/scripts/bash/generate-instructions.sh",
     "bash-version-guard", ".specify/scripts/bash/generate-instructions.sh"),
    (".specify/scripts/bash/run-tests.sh",
     "bash-version-guard", ".specify/scripts/bash/run-tests.sh"),
)

#: The kinds the declaration may carry, in the order the contract states them.
PROJECTION_KINDS = ("python-version-bridge", "bash-version-guard")

#: The per-pair strictness a projection MUST NOT disturb (C-37), read out of ``MIRROR_PAIRS``
#: itself so the declaration cannot carry a second, drifting copy of the flags. ``main()``
#: asserts this tuple at run time; the contract suite asserts it again from outside.
PROJECTION_STRICTNESS = tuple(
    (src_name, strict_extras) for src_name, _d, strict_extras, _e in MIRROR_PAIRS
)

#: The frame rule (C-38). A projected mirror MUST NOT claim byte identity with its source,
#: and the source MUST NOT claim to be the mirror's whole surface: the authoritative
#: statement lives in the contract and the owner page, never in either side's comments.
BYTE_IDENTITY_CLAIM = "byte-identical"
WHOLE_TRUTH_MARKERS = ("whole truth", "the only surface", "nothing but a copy")

#: The anchor each Python bridge is inserted BEFORE. Appended after this line the bridge
#: never runs; inserted later it loses to ``main()``.
PYTHON_ANCHOR = 'if __name__ == "__main__":'

#: The marker every projected mirror carries, exactly once (C-38). It sits INSIDE the
#: projected block, so the block produces it: the marker is greppable out of the mirror and
#: no hand ever writes it. It says "projected", never "identical to the source" -- a
#: byte-identity claim on a projected file is the false statement C-38 forbids.
MARKER_TEMPLATE = "projected mirror: source + {kind}; regenerate it, never hand-edit it"

#: The framework-version lookup the emitted Python bridge carries. It is TEXT handed to a
#: foreign interpreter in a foreign tree (C-36), so it may import nothing from this
#: repository; it re-derives the version itself, under the same bounded search and the same
#: constants as ``script_interface_cli.py`` (``pyproject.toml`` beside a ``.git`` entry, at
#: most ``MAX_UPWARD_LEVELS`` levels up). The contract suite asserts the two agree.
_VERSION_SEARCH_BLOCK = """\
_VERSION_SOURCE = "pyproject.toml"
_VERSION_QUOTES = chr(39) + chr(34)
_MAX_UPWARD_LEVELS = 12


def _bridge_version(start):
    _here = start.resolve()
    for _ in range(_MAX_UPWARD_LEVELS + 1):
        if (_here / _VERSION_SOURCE).is_file() and (_here / ".git").exists():
            try:
                _text = (_here / _VERSION_SOURCE).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return "unknown"
            _in_project = False
            for _raw in _text.splitlines():
                _line = _raw.strip()
                if not _line or _line.startswith("#"):
                    continue
                if _line.startswith("[") and _line.endswith("]"):
                    _in_project = _line == "[project]"
                    continue
                if not _in_project:
                    continue
                _key, _sep, _value = _line.partition("=")
                if _sep and _key.strip() == "version":
                    _value = _value.strip()
                    if len(_value) >= 2 and _value[0] == _value[-1] and _value[0] in _VERSION_QUOTES:
                        _value = _value[1:-1]
                    return _value or "unknown"
            return "unknown"
        if _here.parent == _here:
            return "unknown"
        _here = _here.parent
    return "unknown"
"""

#: The Python bridge: run-time ``--version``, zero side effects, exit 0 (C-7 / C-8 / C-36).
#: The flag is answered by scanning ``sys.argv`` BEFORE the script's own parser runs: several
#: of these scripts build ``argparse`` parsers with required subcommands, which would reject a
#: leading ``--version`` at exit 2 if the bridge deferred to them. The scan stops at the bare
#: ``--`` separator, so a token after it is never treated as the flag (C-9).
_PYTHON_BRIDGE_BODY = """\
def _bridge_main():
    import sys as _bridge_sys
    from pathlib import Path as _bridge_path

    _argv = list(_bridge_sys.argv[1:])
    if "--version" not in _argv:
        return
    if "--" in _argv and _argv.index("--version") > _argv.index("--"):
        return
    _invoked = _bridge_sys.argv[0] if _bridge_sys.argv[0] else "."
    _name = _bridge_path(_invoked).name or "script"
    print("%s %s" % (_name, _bridge_version(_bridge_path(_invoked).resolve().parent)))
    raise SystemExit(0)


_bridge_main()
del _bridge_main
"""


#: The sentinel ``script_interface_version_text`` carries where its body belongs (T076).
#:
#: The sourceable library owns the version line; a script that cannot source it -- a broken
#: ``common.sh`` beside it, a downstream copy without the library -- still has to answer
#: ``--version``. The guard block a ``bash-version-guard`` mirror carries is exactly that case,
#: so the rule fills this sentinel with the library function's own body rather than typing a
#: second copy of the search: the emitted guard and the library can then only change together.
PROJECTION_SENTINEL = "__SCRIPT_INTERFACE_VERSION_BODY__"


def _marker(kind):
    """The one marker line a ``kind`` projection puts in its mirror (C-38)."""
    return MARKER_TEMPLATE.format(kind=kind)


#: The sourceable bash library that defines ``script_interface_version_text``. The sentinel's
#: body is read from HERE for every guard projection: a consumer carries the guard by sourcing
#: the library, so the library -- never the consumer's own text -- holds the function.
GUARD_LIBRARY_SOURCE = ".specify/scripts/bash/script-interface.sh"


def version_text_function_body(source_text):
    """The body of ``script_interface_version_text`` as ``source_text`` defines it, or ``""``.

    Read by matching the function's definition line and its closing brace, then dropping the
    header and the brace: the result is the statements BETWEEN them, re-indented to the header's
    indentation plus one level so it can be dropped into any shell function verbatim. An empty
    answer means the source no longer ships the function -- a structural failure the caller
    reports, never one to paper over with a baked-in copy.
    """
    lines = source_text.splitlines()
    for index, line in enumerate(lines):
        if not line.lstrip().startswith("script_interface_version_text()"):
            continue
        indent = line[: len(line) - len(line.lstrip())]
        body = []
        for inner in lines[index + 1:]:
            if inner.strip() == "}":
                break
            body.append(inner)
        return "\n".join((indent + "    " + row[len(indent):].lstrip()
                          if row.strip() else "") for row in body)
    return ""


def python_version_bridge():
    """The block a ``python-version-bridge`` mirror carries immediately before its anchor."""
    header = [
        "# " + _marker("python-version-bridge"),
        "#",
        "# Emitted by `.specify/scripts/python/sync-mirrors.py`; the authority for this block is",
        "# `contracts/mirror-projection.contract.md` C-34 / C-36. It depends on nothing",
        "# that exists only in the source tree: it re-derives its own version line (C-36).",
        "",
    ]
    return "\n".join(header) + _VERSION_SEARCH_BLOCK + "\n" + _PYTHON_BRIDGE_BODY


def _bash_declaration(source_text):
    """The consumer's declared surface, read from its own `script_interface_guard define` call.

    The mirror answers `--help` before the consumer's guard runs, so the body it prints has to
    be the source's own declaration. A source with no define call yields empty fields and the
    body falls back to its generic wording.
    """
    import re

    out = {"usage": "", "effects": "", "codes": "", "options": ""}
    if not isinstance(source_text, str):
        return out
    match = re.search(
        r"script_interface_guard\s+define\b(?P<body>.*?)"
        r"(?:\n\s*script_interface_guard\s+guard\b|\Z)", source_text, re.S)
    if not match:
        return out
    body = match.group("body")
    for key in ("usage", "effects", "codes"):
        found = re.search(r'%s="([^"]*)"' % key, body)
        if found:
            out[key] = found.group(1)
    after = re.search(r"^\s*--\s+(.+)$", body, re.M)
    if after:
        tokens = [tok for tok in after.group(1).split()
                  if tok not in ("-h", "--help", "--version")]
        out["options"] = " ".join(tokens)
    return out


def _sq(text):
    """The text as one single-quoted bash word."""
    return "'" + str(text).replace("'", "'\\''") + "'"


def bash_version_guard(version_body, declaration=None):
    """The block a ``bash-version-guard`` mirror carries immediately after its shebang.

    Deliberately self-contained (C-36): it sources nothing. Two things make that possible, and
    both are the sentinel's business:

      * the version search is ``script_interface_version_text``'s own body, filled in through
        ``__SCRIPT_INTERFACE_VERSION_BODY__`` -- the library and the emitted guard are one
        text, never two copies that can drift. The function is DEFINED in the block, so a
        consumer that cannot find the library can still call it;
      * the help body is the SOURCE's own declaration, extracted at projection time
        (``declaration``): usage, declared options, side-effects and exit codes. The mirror
        answers ``--help`` before the consumer's guard runs, so a generic body here would hide
        the real usage (measured on ``check-prerequisites.sh``, whose review flags had
        disappeared). A downstream copy without the library is the case this body exists for.

    It answers ``--version`` / ``-h`` / ``--help`` before the script's own parsing, honours the
    bare ``--`` terminator and exits 0 when it answers. An undeclared option is NOT rejected
    here -- that rejection belongs to the script's own parser, and pre-empting it would change
    an existing interface. ``version_body`` empty means the source no longer defines the
    function, which ``project_source`` refuses rather than emitting a broken block.
    """
    declaration = declaration or {}
    usage = declaration.get("usage") or "[options]"
    effects = declaration.get("effects") or "none; the flags write nothing"
    codes = declaration.get("codes") or "0 the flag was answered; 2 an unrecognized option"
    options = [opt for opt in (declaration.get("options") or "").split()]
    lines = [
        "# " + _marker("bash-version-guard"),
        "#",
        "# Emitted by `.specify/scripts/python/sync-mirrors.py`; the authority for this block is",
        "# `contracts/mirror-projection.contract.md` C-34 / C-36. It depends on nothing",
        "# that exists only in the source tree: it re-derives its own version line (C-36).",
        "#",
        "# The guard block is the FIRST executable block of the script that carries it: above",
        "# every `source`, every `mkdir`, every `git` write and every manifest generation.",
        "# The insertion rule is owned by `.specify/shared/definitions/script-interface-definitions.md`.",
        "script_interface_version_text() {",
        "    __SCRIPT_INTERFACE_VERSION_BODY__",
        "}",
        "_script_interface_guard() {",
        "    local _arg _wanted=",
        "    local _stop=0",
        '    for _arg in "$@"; do',
        '        [ "$_stop" -eq 1 ] && continue',
        '        case "$_arg" in',
        "            --) _stop=1 ;;",
        '            -h|--help) [ -n "$_wanted" ] || _wanted=help ;;',
        '            --version) [ -n "$_wanted" ] || _wanted=version ;;',
        "        esac",
        "    done",
        '    case "$_wanted" in',
        "        help)",
        "            printf 'usage: %s %s\\n' \"${0##*/}\" " + _sq(usage),
        "            printf 'options:\\n'",
        "            printf '  -h, --help   print this help and exit\\n'",
        "            printf '  --version    print the script name and the framework version, then exit\\n'",
    ]
    for opt in options:
        lines.append("            printf '  %s\\n' " + _sq(opt))
    lines += [
        "            printf 'side-effects: %s\\n' " + _sq(effects),
        "            printf 'exit-codes: %s\\n' " + _sq(codes),
        "            exit 0 ;;",
        "        version)",
        '            script_interface_version_text "$0" "$(dirname -- "$0")"',
        "            exit 0 ;;",
        "    esac",
        "    return 0",
        "}",
        '_script_interface_guard "$@"',
    ]
    block = "\n".join(lines) + "\n"
    return block.replace("    " + PROJECTION_SENTINEL, version_body)

def project_source(source_text, kind):
    """Return ``(mirror_text, applied)`` -- the declared projection of ``source_text`` (C-34).

    ``applied`` is False when the rule refuses the pair (a missing anchor, a source that no
    longer defines ``script_interface_version_text`` for the sentinel to carry, or a kind outside
    the closed set), in which case the FIRST element is the reason rather than the source
    unchanged: C-34 forbids silently appending at end of file, and a caller that cannot tell
    "refused" from "nothing to do" would report a broken pair as ``ok``.

    Idempotent by construction: the block defines its own names, carries its own marker and
    never contains the anchor line, so a text that already carries it is returned unchanged.
    """
    if kind == "python-version-bridge":
        block = python_version_bridge()
        anchor_index = _anchor_line_index(source_text, PYTHON_ANCHOR)
        if anchor_index < 0:
            return ("the projection anchor %r is missing from the source" % PYTHON_ANCHOR,
                    False)
        if _carries_projection_block(source_text, block):
            return source_text, True
        lines = source_text.splitlines(keepends=True)
        head = "".join(lines[:anchor_index])
        tail = "".join(lines[anchor_index:])
        separator = "" if not head or head.endswith("\n\n") else "\n"
        return head + block + separator + tail, True
    if kind == "bash-version-guard":
        lines = source_text.splitlines(keepends=True)
        if not lines or not lines[0].startswith("#!"):
            return ("the projection anchor (a shebang line) is missing from the source", False)
        # The sentinel's body comes from the LIBRARY, never from the consumer's own text: a
        # consumer carries the guard by sourcing the library, so the library is the one file that
        # defines the function, and reading the consumer would find nothing to splice.
        try:
            library_text = (REPO_ROOT / GUARD_LIBRARY_SOURCE).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            return ("the projection sentinel has no body: %s is unreadable (%s)"
                    % (GUARD_LIBRARY_SOURCE, exc), False)
        version_body = version_text_function_body(library_text)
        if not version_body:
            return ("the projection sentinel has no body: %s does not define "
                    "script_interface_version_text()" % GUARD_LIBRARY_SOURCE, False)
        block = bash_version_guard(version_body, _bash_declaration(source_text))
        if _carries_projection_block(source_text, block):
            return source_text, True
        shebang = lines[0] if lines[0].endswith("\n") else lines[0] + "\n"
        return shebang + block + source_text[len(lines[0]):], True
    return ("unknown projection kind %r (the closed set is %s)"
            % (kind, " / ".join(PROJECTION_KINDS)), False)


def _anchor_line_index(text, anchor):
    """0-based line index of the line whose stripped text equals ``anchor``, or -1."""
    for index, line in enumerate(text.splitlines()):
        if line.strip() == anchor:
            return index
    return -1


def _carries_projection_block(text, block):
    """Whether ``text`` already carries ``block``'s marker line (C-38's exactly-one marker)."""
    marker = block.splitlines()[0].strip()
    # The marker line carries a leading `# ` comment prefix, so the comparison strips it on
    # both sides: a comparison against the bare marker text never matches, which would make
    # every projection re-insert its block.
    marker_body = marker.lstrip("#").strip()
    return any(line.strip().lstrip("#").strip() == marker_body for line in text.splitlines())


def _strip_projection_block(text, block):
    """``text`` with a carried ``block`` removed, or ``text`` itself when it carries none.

    A source that already runs the projection is the inverse of a hand-edited mirror: the
    block is reproduced by the rule, so carrying it does not change the verdict. Removing it
    first keeps ``project(source)`` idempotent for those pairs -- otherwise the detection
    returns the text UNCHANGED and the same pair reports drift on every run.

    The block is located by its OWN lines, leading marker comment included, and removed as a
    whole. Matching on the block's exact text (rather than on its first executable line plus a
    guessed end) is what makes removal the exact inverse of emission: the block's comment
    header is part of it, and a strip that left the header behind would re-insert the block on
    the next run.
    """
    lines = block.splitlines(keepends=True)
    body = [line.strip() for line in lines if line.strip()]
    if not body:
        return text
    text_lines = text.splitlines(keepends=True)
    start = -1
    for index in range(len(text_lines) - len(body) + 1):
        if all(text_lines[index + offset].strip() == body[offset]
               for offset in range(len(body))):
            start = index
            break
    if start < 0:
        return text
    return "".join(text_lines[:start]) + "".join(text_lines[start + len(body):])


def projected_mirrors():
    """``{mirror_path: (kind, source_path)}`` -- the declaration as consumers need it."""
    return {row[0]: (row[1], row[2]) for row in PROJECTED_FILES}


#: The last line each emitted block carries: the call that runs the guard, and the `del` that
#: retires the Python bridge. Both are emitted verbatim, so the end of a block is FOUND as text
#: rather than inferred from indentation — an inference would be a second, weaker copy of a fact
#: the emitted block already states.
_GUARD_CALL_LINE = '_script_interface_guard "$@"'
_BRIDGE_RETIRE_LINE = "del _bridge_main"


def _projection_block(projected_text):
    """The projected block cut out of an already-projected text, by its own marker and tail.

    The block opens at the marker comment every projection emits first (C-38) and closes at the
    line the block itself ends with. Nothing else is inferred, so the block's LENGTH is never a
    second fact that can drift from the emitted text.
    """
    lines = projected_text.splitlines(keepends=True)
    start = next((index for index, line in enumerate(lines)
                  if "projected mirror: source +" in line), -1)
    if start < 0:
        return ""
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].strip() in (_GUARD_CALL_LINE, _BRIDGE_RETIRE_LINE):
            end = index + 1
            break
    return "".join(lines[start:end])


def project_for(mirror_rel_path):
    """Return ``(expected_bytes, problem)`` for one repo-relative mirror path (C-35).

    ``expected_bytes`` is None when the path is not a declared mirror, or when the rule
    refuses the pair; ``problem`` carries the reason in the refused case and is None
    otherwise. "Not declared" and "refused" stay distinguishable on purpose: the first means
    byte equality applies, the second is a structural failure that must be printed.
    """
    entry = projected_mirrors().get(mirror_rel_path)
    if entry is None:
        return None, None
    kind, source_rel = entry
    try:
        source_text = (REPO_ROOT / source_rel).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return None, "%s (%s): the projection source %s is unreadable: %s" % (
            mirror_rel_path, kind, source_rel, exc)
    # A source may run the projection itself (a script whose own directory is the tree it
    # measures). Stripping it first keeps the rule idempotent; the emitted block is the same
    # either way, so a source that carries it and one that does not project identically.
    #
    # The block is taken from the DRY run: `project_source` is what owns the block per kind (the
    # guard's sentinel body is read there, from the library), so re-deriving it here would be a
    # second construction of the same block -- and a second construction is a second place to
    # drift. The dry run's `expected` is discarded; only the marker line is needed.
    dry, _applied = project_source(source_text, kind)
    if _applied:
        # The emitted block runs from its marker line to the end of the dry result's prefix.
        block = dry.splitlines(keepends=True)[1:2] and dry
        marker = _marker(kind)
        block_lines = dry.splitlines(keepends=True)
        start = next((i for i, line in enumerate(block_lines) if marker in line), 1)
        if kind == "bash-version-guard":
            stop = next(i for i in range(start, len(block_lines))
                        if block_lines[i].strip() == '_script_interface_guard "$@"') + 1
        else:
            stop = start + len(python_version_bridge().splitlines())
        block = "".join(block_lines[start:stop])
    else:
        block = python_version_bridge() if kind == "python-version-bridge" else ""
    expected, applied = project_source(_strip_projection_block(source_text, block), kind)
    if not applied:
        return None, "%s (%s): %s" % (mirror_rel_path, kind, expected)
    return expected.encode("utf-8"), None


def write_projected(target, expected):
    """Write one projected mirror; the single place a projected byte reaches the disk."""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(expected)



def frame_violations(source_text: str, mirror_text: str, kind: str) -> list:
    """The frame claims this pair must not make (C-38), as a list of reasons.

    A frame violation is not a styling note: a mirror that claims byte identity misleads the
    next reader into "fixing" the difference by copying the source over it, which silently
    deletes the flag surface. Both sides are checked.
    """
    problems = []
    marker = _marker(kind)
    # Only COMMENT lines are judged: the claim is a claim about the files, made in prose a
    # reader sees — a string literal or an identifier is a different thing. Reading comment
    # lines is also what keeps this scanner from flagging the vocabulary it looks for.
    for side, text in (("mirror", mirror_text), ("source", source_text)):
        comments = [line.lower() for line in text.splitlines()
                    if line.lstrip().startswith("#")]
        if side == "mirror" and any(BYTE_IDENTITY_CLAIM in line for line in comments):
            problems.append("the mirror claims %r of its source" % BYTE_IDENTITY_CLAIM)
        for claim in WHOLE_TRUTH_MARKERS:
            if any(claim in line for line in comments):
                problems.append("the %s claims to be %r" % (side, claim))
    # Read the marker back the way it is written: the emitted line carries a `# ` comment
    # prefix, so comparing against the bare marker text would count zero forever.
    marker_body = marker.lstrip("#").strip()
    carried = sum(1 for line in mirror_text.splitlines()
                  if line.strip().lstrip("#").strip() == marker_body)
    if carried != 1:
        problems.append("the mirror carries the %r marker %d time(s), not exactly once"
                        % (kind, carried))
    return problems


def iter_files(root: Path, exclude_parts=frozenset()):
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        if path.is_dir():
            continue
        if any(
            part in IGNORE_NAMES or part in exclude_parts
            for part in path.relative_to(root).parts
        ):
            continue
        yield path.relative_to(root)


def _file_in_sync(source_path: Path, mirror_path: Path) -> bool:
    """Whether the mirror already equals what ``--write`` would produce for it (C-35).

    A declared projected file is judged as ``mirror == project(source)``; every other file
    keeps byte equality. Keeping the distinction inside this one predicate is what stops
    ``--check`` and ``--write`` from disagreeing about what "in sync" means. A refused
    projection cannot satisfy byte equality either, so it is reported as drift and its
    reason is printed by ``main()``.
    """
    try:
        rel = mirror_path.relative_to(REPO_ROOT).as_posix()
    except ValueError:  # pragma: no cover - a tree outside the repo is not a mirror
        return filecmp.cmp(source_path, mirror_path, shallow=False)
    expected, _problem = project_for(rel)
    if expected is not None:
        try:
            return mirror_path.read_bytes() == expected
        except OSError:  # pragma: no cover - an unreadable mirror is drift, not a crash
            return False
    return filecmp.cmp(source_path, mirror_path, shallow=False)


def compare_pair(src: Path, dst: Path, exclude_parts=frozenset()):
    """Return (missing_in_dst, differing, extra_in_dst) relative paths.

    "Differing" is decided by ``_file_in_sync``: byte equality, except for a declared
    projected mirror, which is compared as ``mirror == project(source)`` (C-35).
    """
    src_files = set(iter_files(src, exclude_parts))
    dst_files = set(iter_files(dst, exclude_parts))
    missing = sorted(src_files - dst_files)
    extra = sorted(dst_files - src_files)
    differing = sorted(
        rel
        for rel in src_files & dst_files
        if not _file_in_sync(src / rel, dst / rel)
    )
    return missing, differing, extra


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

def main() -> int:
    _sig_guard(declared=['--check', '--write', '--only'])  # answer --version / reject an undeclared option
    parser = argparse.ArgumentParser(description=__doc__)
    _sig_configure(parser)

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="report drift, exit 2 if any")
    mode.add_argument("--write", action="store_true",
                      help="sync mirrors (default) (triggers the write)")
    parser.add_argument("--only", action="append", default=None, metavar="PATH",
                        help="restrict the run to this repo-relative path prefix "
                             "(repeatable); skips the regen-command-copies "
                             "delegation unless a prefix targets .specify/templates/commands/")
    args = parser.parse_args()
    check_only = args.check
    only = [p.strip().strip("/") for p in (args.only or []) if p.strip()]

    def pair_subprefixes(src_name: str) -> list[str] | None:
        """None = pair out of scope; list of sub-prefixes (empty str = whole pair)."""
        if not only:
            return [""]
        subs: list[str] = []
        for p in only:
            if p == src_name:
                subs.append("")
            elif p.startswith(src_name + "/"):
                subs.append(p[len(src_name) + 1:])
        return subs or None

    def in_scope(rel: Path, subs: list[str]) -> bool:
        rel_s = rel.as_posix()
        return any(not sp or rel_s == sp or rel_s.startswith(sp + "/")
                   for sp in subs)

    if only:
        matched = any(pair_subprefixes(src) for src, _d, _s, _e in MIRROR_PAIRS)
        regen_targeted = any(p == ".specify/templates/commands"
                             or p.startswith(".specify/templates/commands/") for p in only)
        if not matched and not regen_targeted:
            print(f"error: --only prefix matches no mirror pair or regen surface: "
                  f"{', '.join(only)}")
            return 2
        print(f"scope --only: {', '.join(only)}")

    drift = False
    orphans = False
    failures: list[tuple[str, str]] = []
    for src_name, dst_name, strict_extras, exclude_parts in MIRROR_PAIRS:
        subs = pair_subprefixes(src_name)
        if subs is None:
            continue
        src = REPO_ROOT / src_name
        dst = REPO_ROOT / dst_name
        if not src.exists():
            continue
        src_files = [f for f in iter_files(src, exclude_parts)
                     if in_scope(f, subs)]
        if not src_files:
            # placeholder-only source (e.g. an empty skills/external/): mirror is
            # canonical, skip
            print(f"skip  {src_name}/ (placeholder-only source; {dst_name}/ is canonical)")
            continue
        missing, differing, extra = compare_pair(src, dst, exclude_parts)
        missing = [r for r in missing if in_scope(r, subs)]
        differing = [r for r in differing if in_scope(r, subs)]
        extra = [r for r in extra if in_scope(r, subs)]
        # C-35: the projected half is reported under its OWN kind, never folded into one
        # "mirrors agree" sentence -- a reader must be able to tell why the two files differ
        # and which rule produced the mirror.
        declared = projected_mirrors()
        projected_here = [
            (dst / rel).relative_to(REPO_ROOT).as_posix()
            for rel in src_files
            if (dst / rel).relative_to(REPO_ROOT).as_posix() in declared
        ]
        plain_count = len(src_files) - len(projected_here)
        if not (missing or differing):
            print(f"ok    {src_name}/ == {dst_name}/ ({plain_count} files, byte-identical)")
        else:
            drift = True
            for rel in missing:
                print(f"MISS  {dst_name}/{rel}")
            for rel in differing:
                mirror_rel_s = (dst / rel).relative_to(REPO_ROOT).as_posix()
                label = "DIFF[projected]" if mirror_rel_s in declared else "DIFF"
                print(f"{label} {dst_name}/{rel}")
            if not check_only:
                synced = 0
                for rel in missing + differing:
                    target = dst / rel
                    mirror_rel_s = target.relative_to(REPO_ROOT).as_posix()
                    try:
                        expected, problem = project_for(mirror_rel_s)
                        if problem is not None:
                            failures.append((f"{dst_name}/{rel}", problem))
                            print(f"FAIL  {dst_name}/{rel}: {problem}")
                            continue
                        if expected is not None:
                            write_projected(target, expected)
                        else:
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(src / rel, target)
                        synced += 1
                    except OSError as exc:
                        failures.append((f"{dst_name}/{rel}", str(exc)))
                        print(f"FAIL  {dst_name}/{rel}: {exc}")
                if synced:
                    print(f"sync  {src_name}/ -> {dst_name}/ ({synced} files)")
        for mirror_rel_s in projected_here:
            kind, source_rel = declared[mirror_rel_s]
            expected, problem = project_for(mirror_rel_s)
            if problem is not None:
                failures.append((mirror_rel_s, problem))
                print(f"FAIL  {mirror_rel_s}: {problem}")
                verdict = "refused"
            else:
                # C-35: `ok` means the mirror's bytes EQUAL the projection. "the
                # projection could be computed" is not a verdict about the mirror --
                # a computable-but-stale pair is drift, and this line must not say ok.
                try:
                    in_sync = (REPO_ROOT / mirror_rel_s).read_bytes() == expected
                except OSError:
                    in_sync = False
                if in_sync:
                    verdict = "ok"
                else:
                    drift = True
                    verdict = "DIFF[projected]"
            print(f"projected[{kind}] {mirror_rel_s} <- {source_rel}: {verdict}")
        # Extras are never deleted (archive-not-delete discipline), but in a
        # strict tree they are a distribution defect, not a note.
        for rel in extra:
            if strict_extras:
                orphans = True
                print(f"ORPHAN {dst_name}/{rel} (no canonical {src_name}/ source)")
            else:
                print(f"note  extra file only in mirror: {dst_name}/{rel}")

    # Per-tool command copies: delegate to the existing canonical generator.
    regen = REPO_ROOT / ".specify/scripts/python/regen-command-copies.py"
    run_regen = not only or any(
        p == ".specify/templates/commands" or p.startswith(".specify/templates/commands/")
        for p in only)
    if run_regen:
        regen_args = [sys.executable, str(regen)] + (["--check"] if check_only else [])
        result = subprocess.run(regen_args, cwd=REPO_ROOT)
        if result.returncode != 0:
            drift = True

    if failures:
        print(
            f"\nSYNC FAILURES: {len(failures)} file(s) stayed stale — fix and re-run:"
        )
        for rel, err in failures:
            print(f"  FAIL {rel}: {err}")
        print(
            "  Remedy for root-owned mirrors: `sudo chown -R $USER <dir>`, then "
            "re-run `python3 .specify/scripts/python/sync-mirrors.py --write`"
        )
        return 1
    if check_only and orphans:
        print(
            "ORPHANS detected — a mirror-only file cannot be distributed by "
            "`specify init`, which only copies canonical source -> mirror.\n"
            "  Fix by either: (a) adding the canonical source (e.g. "
            ".specify/scripts/bash/<name>.sh) if the file should ship to downstream "
            "projects, or (b) deleting the mirror copy if it is a superseded "
            "leftover."
        )
    if check_only and drift:
        print("DRIFT detected — run: python3 .specify/scripts/python/sync-mirrors.py --write")
    if check_only and (drift or orphans):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
