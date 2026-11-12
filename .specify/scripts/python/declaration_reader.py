#!/usr/bin/env python3
"""The one YAML-subset parser for the declaration layer (`.specify/shared/declarations/`).

Feature 084 (harness triple structure). Contracts: `contracts/shared-reader.contract.md`
C-052…C-059 and `contracts/declaration-schema.contract.md` C-008…C-010.

**Why this file exists.** The failure the layer removes is "the same rule implemented twice": a value that
lives in an engine constant and again in prose drifts, and nobody sees it drift. A *shared read entry* is
what turns a second implementation into a visible defect instead of a style remark — every consumer engine
imports this module, so a parser written anywhere else is a finding (`C-058`'s boundary guard).

**Surface.** Importable (every consumer is invoked as ``python3 .specify/scripts/python/<name>.py``, so this
script's own directory is ``sys.path[0]``) and callable for humans:

    python3 .specify/scripts/python/declaration_reader.py --action list --repo .
    python3 .specify/scripts/python/declaration_reader.py --action get --fact <fact-slug> --repo .

Functions: :func:`load_contract`, :func:`load_fact`, :func:`load_facts`, :func:`load_exclusions`,
:func:`normalize_path`, plus the two helpers a consumer engine needs to reach the layer at all:
:func:`find_repo` (the root that holds it, in whichever of the three copies this invocation lives) and
:func:`absent_label` (the `STR-014` instance a degraded read prints).

**Error discipline (C-055/C-056).** Every failure raises one typed error, :class:`DeclarationError`. When
the failing input is a *finding* the error carries the finding template id (`STR-010` for a construct
outside the subset, `STR-014` for an absent declaration); the caller renders it verbatim and maps it to an
exit code. When the input is merely unreadable the id is ``None`` and the caller maps it to the exit-2 input
error. A legacy project without the declaration layer travels through the **same** error with
``degraded=True`` — never a bespoke exception, never an exception type of this module's own invention.
No function in this module prints; only :func:`main` does.

**The subset** (the grammar itself, owned here per C-054): block mappings, block sequences, scalars
(plain / single-quoted / double-quoted), whole-line and trailing comments, and two-space indentation.
``[]`` and ``{}`` are allowed only as empty values. Anchors, aliases, explicit tags, multiple documents,
block scalars (``|`` and ``>``) and every flow collection are **refused**, never parsed on a best-effort
basis: "mostly works" is a contract violation, not a lenient success.

**Not a proof of anything else.** This module parses and loads. It does not judge a declaration: required
keys, slug/stem agreement, duplicate slugs, anchor resolvability, dispositions and completeness are
`.specify/scripts/python/harness-triple-check.py`'s judgements, because they need the whole file set in view.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

#: The layer's location in the framework source, and its mirror form in a client project (C-001, C-010).
DECLARATIONS_DIR = ".specify/shared/declarations"
DECLARATIONS_MIRROR = ".specify/shared/declarations"
MIRROR_PREFIX = ".specify/"

#: Tokens a consumer's read point is greppable by (C-055).
READ_ENTRY = "declaration_reader"

#: Finding ids this module can raise. They are ids, not template text: the text is owned by
#: `requirements.md` § Shared Strings and is rendered by the caller.
SUBSET_FINDING = "STR-010"
ABSENT_FINDING = "STR-014"

#: The absent-declaration **code** (`STR-014`'s instance form). A consumer engine labels its degraded
#: read with :func:`absent_label` instead of re-spelling the text, the way `harness-triple-check.py`
#: carries the six finding codes next to the owner's name.
ABSENT_CODE = "declaration-absent"

#: Constructs that are outside the subset, with the reason the refusal names.
_FORBIDDEN_FLOW = ("[", "{")
_FORBIDDEN_MARKERS = {
    "&": "an anchor",
    "*": "an alias",
    "!": "an explicit tag",
    "|": "a block scalar",
    ">": "a block scalar",
}


class DeclarationError(Exception):
    """One typed error for every failure in this module.

    ``template`` is the finding id the caller must render (``None`` = input error, exit 2);
    ``degraded`` marks the legacy-project case, whose exit-2 label is an input error rather than a finding;
    ``slug`` names the fact when one is involved.
    """

    def __init__(self, detail, template=None, path=None, slug=None, degraded=False):
        super().__init__(detail)
        self.detail = detail
        self.template = template
        self.path = path
        self.slug = slug
        self.degraded = degraded

    def __str__(self):
        return self.detail


def normalize_path(value):
    """C-057 — strip exactly one optional leading ``.specify/`` and return a repo-relative value.

    This is the single place the three-copy problem is solved (`research.md` § R3): the framework source,
    this repository's mirror, and a client project's rewritten copy all name the same object, so a
    declaration written in source form is valid in all three.
    """
    text = str(value).strip()
    if text.startswith(MIRROR_PREFIX):
        return text[len(MIRROR_PREFIX):]
    return text


def absent_label(slug):
    """The `STR-014` instance a consumer engine prints when the declaration for ``slug`` is absent.

    One rendering, here, so five engines do not each spell the label: the template text is owned by
    `requirements.md` § Shared Strings, and this function is the only place the code is concatenated
    with its argument. The label is a **reading of the wiring**, never a pass (FR-012 / C-049).
    """
    return "%s: %s" % (ABSENT_CODE, slug)


def find_repo(start=None):
    """The repository root that holds the layer, walking up from ``start`` (a file or a directory).

    Every engine this feature touches exists in three physical copies — the framework source, this
    repository's byte-identical mirror, and a client project's ``.specify/`` copy — so the root is the
    nearest ancestor holding ``.specify/shared/declarations`` (source form) or ``.specify/shared/declarations``
    (mirror form), in that order per :func:`layer_dir`. This is a **read-only** lookup: nothing is
    written, so a nested tree next to a copy cannot misdirect a write the way a workspace-state
    resolution can. When no ancestor holds a layer the nearest root-shaped ancestor is returned and
    :func:`layer_dir` raises the degraded error, which is the caller's exit-2 label (C-056).
    """
    here = Path(start) if start is not None else Path(__file__)
    here = here.resolve()
    anchor = here if here.is_dir() else here.parent
    for parent in (anchor, ) + tuple(anchor.parents):
        for candidate in (parent / DECLARATIONS_DIR, parent / DECLARATIONS_MIRROR):
            if candidate.is_dir():
                return parent
    for parent in (anchor, ) + tuple(anchor.parents):
        if (parent / "scripts" / "python").is_dir():
            return parent
    return anchor


# --------------------------------------------------------------------------- #
# the subset grammar
# --------------------------------------------------------------------------- #
def _tokens(text, source):
    """`[(indent, text, lineno)]` for the non-blank, non-comment lines of a subset document."""
    tokens = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped in ("---", "..."):
            raise DeclarationError(
                "%s:%d: multiple documents are outside the subset" % (source, lineno),
                SUBSET_FINDING, source)
        head = raw[: len(raw) - len(raw.lstrip(" \t"))]
        if "\t" in head:
            raise DeclarationError(
                "%s:%d: tabs are outside the subset (two-space indentation only)" % (source, lineno),
                SUBSET_FINDING, source)
        indent = len(head)
        if indent % 2:
            raise DeclarationError(
                "%s:%d: indentation must be a multiple of two spaces" % (source, lineno),
                SUBSET_FINDING, source)
        tokens.append([indent, stripped, lineno])
        # `- key: value` is a sequence item holding a mapping: split it into the item marker and the
        # first mapping entry, so the parser has one shape to handle instead of two.
        if stripped.startswith("- ") and _looks_like_mapping(stripped[2:]):
            tokens[-1][1] = "-"
            tokens.append([indent + 2, stripped[2:].strip(), lineno])
    return tokens


def _looks_like_mapping(text):
    """`key: value` / `key:` — a mapping entry, not a bare scalar."""
    if not text or text[0] in "'\"[{" or text.startswith("#"):
        return False
    colon = text.find(":")
    if colon <= 0:
        return False
    return colon == len(text) - 1 or text[colon + 1] == " "


def _strip_comment(text):
    """Drop a trailing ``# …`` comment that is not inside a quoted scalar."""
    quote = None
    for index, char in enumerate(text):
        if quote:
            if char == quote:
                quote = None
            continue
        if char in "'\"":
            quote = char
            continue
        if char == "#" and index and text[index - 1] in " \t":
            return text[:index].rstrip()
    return text.rstrip()


def _scalar(text, source, lineno):
    """One scalar, or the empty value. Refuses everything the subset excludes."""
    value = _strip_comment(text.strip())
    if not value:
        return None
    if value == "[]":
        return []
    if value == "{}":
        return {}
    if value[0] in _FORBIDDEN_FLOW:
        raise DeclarationError(
            "%s:%d: flow collections are outside the subset (only the empty forms are allowed)"
            % (source, lineno), SUBSET_FINDING, source)
    if value[0] in _FORBIDDEN_MARKERS:
        raise DeclarationError(
            "%s:%d: %s is outside the subset"
            % (source, lineno, _FORBIDDEN_MARKERS[value[0]]), SUBSET_FINDING, source)
    if value[:2] in ("|-", ">-", "|+", ">+"):
        raise DeclarationError(
            "%s:%d: a block scalar is outside the subset" % (source, lineno), SUBSET_FINDING, source)
    if value[0] == '"':
        if len(value) < 2 or value[-1] != '"':
            raise DeclarationError(
                "%s:%d: unterminated double-quoted scalar" % (source, lineno), SUBSET_FINDING, source)
        return _unescape(value[1:-1])
    if value[0] == "'":
        if len(value) < 2 or value[-1] != "'":
            raise DeclarationError(
                "%s:%d: unterminated single-quoted scalar" % (source, lineno), SUBSET_FINDING, source)
        return value[1:-1].replace("''", "'")
    if value[-1] == '"' or value[-1] == "'":
        raise DeclarationError(
            "%s:%d: an unbalanced quote at the end of a plain scalar" % (source, lineno),
            SUBSET_FINDING, source)
    return value


def _unescape(text):
    out = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text):
            out.append(text[index + 1])
            index += 2
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _parse_block(tokens, index, indent, source):
    """Parse one block at ``indent``; returns ``(value, next_index)``."""
    if index >= len(tokens):
        return None, index
    is_sequence = tokens[index][1] == "-" or tokens[index][1].startswith("- ")
    value = [] if is_sequence else {}
    while index < len(tokens):
        line_indent, text, lineno = tokens[index]
        if line_indent < indent:
            break
        if line_indent > indent:
            raise DeclarationError(
                "%s:%d: unexpected indentation" % (source, lineno), SUBSET_FINDING, source)
        if is_sequence:
            if not text.startswith("-"):
                raise DeclarationError(
                    "%s:%d: a sequence mixes items with mapping keys" % (source, lineno),
                    SUBSET_FINDING, source)
            remainder = text[1:].strip()
            index += 1
            if remainder:
                value.append(_scalar(remainder, source, lineno))
                continue
            if index < len(tokens) and tokens[index][0] > indent:
                item, index = _parse_block(tokens, index, tokens[index][0], source)
            else:
                item = None
            value.append(item)
            continue
        if text == "-" or text.startswith("- "):
            raise DeclarationError(
                "%s:%d: a mapping mixes keys with sequence items" % (source, lineno),
                SUBSET_FINDING, source)
        if not _looks_like_mapping(text):
            raise DeclarationError(
                "%s:%d: expected `key: value`" % (source, lineno), SUBSET_FINDING, source)
        key, _, rest = text.partition(":")
        key = key.strip()
        if not key:
            raise DeclarationError(
                "%s:%d: empty key" % (source, lineno), SUBSET_FINDING, source)
        if key in value:
            raise DeclarationError(
                "%s:%d: duplicate key %r" % (source, lineno, key), SUBSET_FINDING, source)
        index += 1
        rest = rest.strip()
        if rest:
            value[key] = _scalar(rest, source, lineno)
            continue
        if index < len(tokens) and tokens[index][0] > indent:
            value[key], index = _parse_block(tokens, index, tokens[index][0], source)
        else:
            value[key] = None
    return value, index


def parse_subset(text, source="<string>"):
    """Parse one document written in the allowed subset. The single implementation (C-054/C-058)."""
    tokens = _tokens(text, source)
    if not tokens:
        return None
    if tokens[0][0] != 0:
        raise DeclarationError(
            "%s:%d: the document must start at column 0" % (source, tokens[0][2]),
            SUBSET_FINDING, source)
    value, index = _parse_block(tokens, 0, 0, source)
    if index != len(tokens):
        raise DeclarationError(
            "%s:%d: trailing content after the document" % (source, tokens[index][2]),
            SUBSET_FINDING, source)
    return value


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #
def layer_dir(repo):
    """The layer's directory, framework-source form first, mirror form second (C-001/C-010)."""
    root = Path(repo)
    for candidate in (root / DECLARATIONS_DIR, root / DECLARATIONS_MIRROR):
        if candidate.is_dir():
            return candidate
    raise DeclarationError(
        "declaration layer absent: missing directory %s/" % DECLARATIONS_MIRROR,
        template=None, path=DECLARATIONS_MIRROR + "/", degraded=True)


def _relative(path, repo):
    """Repo-relative POSIX path of a file inside ``repo``; the mirror form is normalized away."""
    try:
        return normalize_path(str(Path(path).resolve().relative_to(Path(repo).resolve())))
    except ValueError:
        return normalize_path(str(path))


def _read(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as error:
        raise DeclarationError(
            "%s: unreadable (%s)" % (path, error.strerror or error), template=None, path=str(path))


def load_contract(repo):
    """`contract.yaml` as a mapping. Value-domain questions are answered from here, never re-spelled."""
    path = layer_dir(repo) / "contract.yaml"
    if not path.is_file():
        raise DeclarationError(
            "declaration layer has no contract.yaml: %s" % _relative(path, repo),
            template=None, path=_relative(path, repo), degraded=True)
    value = parse_subset(_read(path), _relative(path, repo))
    if not isinstance(value, dict):
        raise DeclarationError(
            "%s: the contract must be a mapping" % _relative(path, repo),
            template=None, path=_relative(path, repo))
    return value


def load_facts(repo, collect_errors=None):
    """Every fact declaration, sorted by path. Non-``.yaml`` entries (e.g. ``.gitkeep``) are ignored.

    ``collect_errors`` (a list) turns a *finding-bearing* parse error into an entry in that list and
    moves on to the next file, so one declaration outside the subset does not hide every other one. An
    unreadable file, or any error without a finding id, still raises: those are input errors and a
    caller must not continue past them.
    """
    directory = layer_dir(repo) / "facts"
    facts = []
    if not directory.is_dir():
        return facts
    for path in sorted(directory.glob("*.yaml")):
        rel = _relative(path, repo)
        try:
            body = parse_subset(_read(path), rel)
        except DeclarationError as error:
            if collect_errors is not None and error.template:
                collect_errors.append(error)
                continue
            raise
        if not isinstance(body, dict):
            raise DeclarationError(
                "%s: a fact declaration must be a mapping" % rel, template=None, path=rel)
        facts.append({"path": rel, "body": body, "stem": path.stem})
    return facts


def load_fact(repo, slug):
    """One fact declaration by slug; an absent one is the `STR-014` finding, not a silent None."""
    for fact in load_facts(repo):
        if str(fact["body"].get("fact", "")).strip() == slug:
            return fact
    raise DeclarationError(
        "no declaration for fact %r" % slug, template=ABSENT_FINDING, slug=slug)


def load_exclusions(repo):
    """Every exclusion row, sorted by file then by row order — the reason is carried by the file name."""
    directory = layer_dir(repo) / "exclusions"
    rows = []
    if not directory.is_dir():
        return rows
    for path in sorted(directory.glob("*.yaml")):
        rel = _relative(path, repo)
        body = parse_subset(_read(path), rel)
        if body is None:
            continue
        if not isinstance(body, list):
            raise DeclarationError(
                "%s: an exclusion file is a sequence of rows" % rel, template=None, path=rel)
        for row in body:
            if not isinstance(row, dict):
                raise DeclarationError(
                    "%s: an exclusion row must be a mapping" % rel, template=None, path=rel)
            rows.append({"path": rel, "reason": path.stem, "body": row})
    return rows


# --------------------------------------------------------------------------- #
# CLI (for humans and for the contract test; the functions above are the real surface)
# --------------------------------------------------------------------------- #

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
    _sig_guard(argv, declared=['--action', '--fact', '--repo'])  # answer --version / reject an undeclared option
    parser = argparse.ArgumentParser(
        description="Read the declaration layer through its one subset parser.")
    _sig_configure(parser)

    parser.add_argument("--action", choices=("list", "get"), default="list",
                        help="`list` every declaration, or `get` one fact by slug")
    parser.add_argument("--fact", default=None, help="the fact slug for `--action get`")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[2]),
                        help="repository root (default: resolved from this script's own location)")
    args = parser.parse_args(argv)

    try:
        if args.action == "get":
            if not args.fact:
                parser.error("--action get needs --fact <fact-slug>")
            payload = load_fact(args.repo, args.fact)
        else:
            payload = {
                "contract": sorted(load_contract(args.repo)),
                "facts": load_facts(args.repo),
                "exclusions": load_exclusions(args.repo),
            }
    except DeclarationError as error:
        # The caller owns the exit code (C-055), and this CLI is one: an error carrying a finding id is
        # a judgement about a declaration (`1`), anything else — including the degraded layer — is an
        # input error (`2`, C-056). The message is free text here; the finding text is the checker's.
        print(str(error), file=sys.stderr)
        return 1 if error.template else 2

    # One rendering, not two: the CLI is a human/debug door and the functions above are the real
    # surface (C-053), so a second shape would be a second thing to keep in step with the loaders.
    print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
