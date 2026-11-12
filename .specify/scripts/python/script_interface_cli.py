#!/usr/bin/env python3
"""Shared script-interface helper: one rule table, one version source, for every `*.py` script.

Owner of the *rule*: `.specify/shared/definitions/script-interface-definitions.md`. This module is the
Python half of that rule's executable form (the bash half is `.specify/scripts/bash/script-interface.sh`).
It owns exactly two things:

1. **The constants table** (`RULE` and its parts) that both the *emitted* rule and the
   *executed* rule read, so `--emit-rule` and the classifier cannot drift (C-21). Every name in
   here is read out of the owner page by the guard; nothing here is a hand-typed second list.
2. **The version text and its single source**: `<script-name> <framework-version>`, where
   `<framework-version>` is resolved from a `pyproject.toml` at run time and never carried as a
   literal (C-8). An unreachable file yields the literal `unknown` and still exits 0.

Usage:
  python3 .specify/scripts/python/script_interface_cli.py --version
  python3 .specify/scripts/python/script_interface_cli.py --help
  python3 .specify/scripts/python/script_interface_cli.py --emit-rule

Exit codes:
  0  the requested surface answered (help, version, or the emitted rule)
  2  an unrecognised option (rejected by argparse, before any action)

As a library, the consumer surface is:

  from script_interface_cli import configure_parser, VersionAction, version_text
  configure_parser(parser)                                        # the two help labels
  VersionAction.attach(parser)                                    # top parser
  for sub in subparsers.choices.values():                          # AND every subparser
      VersionAction.attach(sub)
  version_text("my-script.py")  ->  "my-script.py 0.0.22"  |  "my-script.py unknown"

`configure_parser(parser)` writes the two labels `argparse` cannot (`side-effects:`,
`exit-codes:`) into the epilog and leaves everything else alone; `usage` and `options` come
from `argparse` itself. A script with something specific to say passes `effects=` / `codes=`.

`parser.add_argument("--version", action=VersionAction)` is the same thing spelled out; the
CLASS is what travels, never an instance — argparse re-instantiates whatever it receives by
calling it with its own resolved kwargs, so a pre-built instance raises `TypeError`.

The pre-parse guard below exists because `argparse` on a parser with
`add_subparsers(required=True)` rejects a leading `--version` at exit 2 before any action can
run: `VersionAction` must therefore sit on the top parser AND on every subparser, and a script
that reads `sys.argv` by hand needs `preparse_version_guard()` instead.

Read-only: this module writes nothing. Importing it has no side effect.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

# --------------------------------------------------------------------------------------
# The constants table (one owner: C-21's `--emit-rule` and the classifier read THIS object)
# --------------------------------------------------------------------------------------

#: Exit code an unknown option must produce. C-9: non-zero, before the main action.
UNKNOWN_OPTION_EXIT = 2

#: Exit code every flag surface must produce on success. C-7 / C-8.
FLAG_EXIT = 0

#: The literal a script prints when no `pyproject.toml` is reachable. C-8 / C-18: an
#: OBSERVATION, not a violation — the exit code stays 0.
UNKNOWN_VERSION = "unknown"

#: The four mandatory labels of a help body (C-7). Asserted as four separate labels, never
#: as one blob: a help text that says only "usage" MUST NOT satisfy the clause.
LABELS = ("usage", "options", "side-effects", "exit-codes")

#: The flag forms every applicable script answers (C-7 / C-8). `-h` and `--help` are one
#: behaviour, which is why the bash guard merges them into a single arm.
FLAG_FORMS = ("-h", "--help", "--version")

#: The only token that ends option scanning (C-9: a token after it is NOT an unknown option).
SEPARATOR = "--"

#: The version line's shape, as a format string (C-8).
VERSION_LINE = "{script_name} {version}"

#: Where the version value comes from: a file name, resolved at run time (C-8).
VERSION_SOURCE = "pyproject.toml"

#: How many directory levels up from a script the search may go. The search is bounded and
#: terminates at the enclosing repository root, so a copy can never read a foreign checkout.
MAX_UPWARD_LEVELS = 12

#: The closed set of OBSERVATIONS a classification row can carry (`observed`): the run wrote
#: its marker at a real action position, the run reached the file and it acted nowhere, the
#: run never wrote its marker at all, or no run of the file's own code was possible (C-3's
#: one undecidable case, kept out of the compliant count by C-12).
OBSERVATIONS = (
    "position-weighted",
    "marker-fired",
    "marker-silent",
    "unevaluated:no-instrumentable-position",
    "unevaluated:load-failure",
    "unevaluated:unnamed-observation",
)

#: The closed set of `basis` values a classification can carry (E-2, data-model.md).
EXEMPT_BASIS = (
    "entry-point-marker",
    "entry-point-side-effect",
    # The marker DID fire, and the file still wrote nothing: the class is applicable by the
    # run's own observation, not by the absence of a position (which is no observation at all
    # and is reported as the `probe-inconclusive` finding instead).
    "marker-fired",
    "no-entry-point",
    "imported-only",
    "projected-mirror",
    "mirror-unpaired",
    "declared-exception",
)

#: The closed set of structural findings (C-13 / C-17). Each is exit 1, never a pass.
FINDINGS = (
    "candidate-not-collected",
    "exception-unverifiable",
    "probe-unavailable",
    "probe-budget-exhausted",
    "probe-inconclusive",
    "projection-mismatch",
)

#: The `## Declared Exceptions` table's columns (C-30), one row per registered script.
EXCEPTION_COLUMNS = ("path", "skill", "unsatisfied clause", "handling")

#: The literal an empty exception register carries (C-30).
EXCEPTION_EMPTY_LITERAL = "none"

#: C-30's four recomputation limbs, in the order the report names them. The owner page's
#: `## Declared Exceptions` section DECLARES them; this tuple is the engine's executing
#: spelling of the same four, and `--emit-rule` publishes it so the page's own guard can
#: compare the two directions instead of trusting either.
EXCEPTION_LIMBS = ("path-exists", "under-external-skill", "skill-declares-external",
                   "four-columns-present")

#: C-3's three forbidden criteria, as the report's closed vocabulary for naming them. Naming
#: a criterion is a REFUSAL: the classifier consults none of the three, and the emitted reason
#: says what each would have claimed instead of an observation.
FORBIDDEN_CRITERIA = ("top-level-statements", "shebang-word", "self-description")

#: Which observation decided a file's class (C-3 / C-6 / C-12). The first is the only one
#: C-3 accepts as a criterion; inheritance is C-6's, and `unevaluated` is the state C-12
#: forbids counting as compliant.
DECIDED_BY = ("run-semantics", "inherited-from-source", "unevaluated")

#: The closed set of sentences an exemption may rest on. A file is exempt because one of
#: these was OBSERVED by running it, never because its source looks a certain way (C-3/C-4).
EXEMPT_SENTENCE = (
    "no entry point fires when the file is executed",
    "the file is only ever imported or sourced",
    "the mirror copy inherits its source's class",
    "the script is registered in the declared exceptions table",
)


def rule_table() -> dict:
    """Return the emitted rule as a JSON-ready dict with the eight keys C-21 fixes.

    This function, and nothing else, is the bridge between the executed rule and the
    emitted rule: the checker's `--emit-rule` mode serialises exactly this object.
    """
    return {
        "labels": list(LABELS),
        "flag_forms": list(FLAG_FORMS),
        "separator": SEPARATOR,
        "version_line": VERSION_LINE,
        "version_source": VERSION_SOURCE,
        "exempt_basis": list(EXEMPT_BASIS),
        "findings": list(FINDINGS),
        "exceptions": list(EXCEPTION_COLUMNS),
        "exception_limbs": list(EXCEPTION_LIMBS),
        "forbidden_criteria": list(FORBIDDEN_CRITERIA),
        "decided_by": list(DECIDED_BY),
        "observations": list(OBSERVATIONS),
    }


# --------------------------------------------------------------------------------------
# The version source (C-8 / C-36: self-sufficient, bounded, never a literal)
# --------------------------------------------------------------------------------------


def find_repo_root(start: Optional[Path] = None) -> Optional[Path]:
    """Return the nearest ancestor of `start` that looks like a repository root.

    A repository root is the nearest ancestor that contains a `pyproject.toml` AND a
    `.git` entry (directory or file — a `git worktree` writes a file). Both conditions are
    required: `pyproject.toml` alone lets a script copied into an unrelated directory read
    the HOST checkout's version, which is the measured failure mode R4 records.

    The search is bounded by `MAX_UPWARD_LEVELS` and never leaves the filesystem root. It
    stops at the first match, so a nested vendored tree's own `pyproject.toml` wins over an
    outer one — that is deliberate: the enclosing project owns its version.

    Returns `None` when no such directory exists, which the caller reports as `unknown`.
    """
    here = Path(start) if start is not None else Path(__file__).resolve().parent
    try:
        here = here.resolve()
    except OSError:  # pragma: no cover - a vanished cwd is not a classification input
        return None
    for _ in range(MAX_UPWARD_LEVELS + 1):
        if (here / VERSION_SOURCE).is_file() and (here / ".git").exists():
            return here
        if here.parent == here:
            return None
        here = here.parent
    return None


def read_version(root: Optional[Path]) -> Optional[str]:
    """Read the `version` field of `<root>/pyproject.toml`, or `None`.

    Deliberately a tiny parser rather than `tomllib` (`>=3.11` only): the project declares
    `requires-python = ">=3.8"`, so this module MUST import nothing newer than 3.8 provides.
    Only a top-level `version = "..."` line is considered, under a `[project]` table, which
    is the shape every packaging backend in this repository emits.
    """
    if root is None:
        return None
    path = Path(root) / VERSION_SOURCE
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    in_project = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            in_project = line == "[project]"
            continue
        if not in_project:
            continue
        key, sep, value = line.partition("=")
        if not sep or key.strip() != "version":
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value or None
    return None


def resolve_version(start: Optional[Path] = None) -> str:
    """Return the framework version for a script located near `start`, or `unknown`.

    `unknown` is a first-class answer (C-8): the caller prints it and exits 0.
    """
    return read_version(find_repo_root(start)) or UNKNOWN_VERSION


def version_text(script_name: str, start: Optional[Path] = None) -> str:
    """Return the one-line `--version` body for `script_name` (C-8).

    `script_name` is the file's own name, never a hard-coded string and never a path: the
    line is `<script-name> <framework-version>` so a caller can parse it without knowing
    which script it invoked.
    """
    name = Path(script_name).name
    return VERSION_LINE.format(script_name=name, version=resolve_version(start))


def print_version(script_name: str, start: Optional[Path] = None, stream=None) -> int:
    """Print the version line and return the success exit code (C-8: exit 0)."""
    out = sys.stdout if stream is None else stream
    print(version_text(script_name, start), file=out)
    return FLAG_EXIT


# --------------------------------------------------------------------------------------
# The help labels (C-7's four labels — `usage` and `options` come from argparse itself)
# --------------------------------------------------------------------------------------

#: The honest, generic `side-effects` sentence. It is TRUE of every script in this tree that
#: has not overridden it: a declared-option invocation writes only where the OPTION says, and
#: a flag-only invocation writes nothing at all (C-10). A script whose flags do write passes
#: its own sentence through `configure_parser(effects=...)` rather than inheriting this one.
DEFAULT_EFFECTS = (
    "writes only through the options it documents; "
    "a flag-only invocation writes nothing"
)

#: The honest, generic `exit-codes` sentence, in the same spirit as `DEFAULT_EFFECTS`.
DEFAULT_CODES = (
    "0 success; 1 a documented check failed; 2 argument or environment error"
)

#: The label lines' own spellings. The owner page fixes the LABELS (uppercase above); these
#: are the two letters a reader sees, and they are the strings the marker test below looks for.
SIDE_EFFECTS_LABEL = "side-effects:"
EXIT_CODES_LABEL = "exit-codes:"


def help_labels(effects: Optional[str] = None, codes: Optional[str] = None) -> str:
    """The two label lines a help body owes, as one tail-of-body text (C-7).

    `argparse` prints `usage` and `options` itself, so only these two are ours to write. They
    are kept as two separate LINES rather than one sentence, because C-7 asserts the four
    labels as four separate assertions and a merged body is exactly what it forbids.
    """
    return "%s %s\n%s %s" % (
        SIDE_EFFECTS_LABEL, effects if effects is not None else DEFAULT_EFFECTS,
        EXIT_CODES_LABEL, codes if codes is not None else DEFAULT_CODES,
    )


def configure_parser(parser: argparse.ArgumentParser,
                     effects: Optional[str] = None,
                     codes: Optional[str] = None) -> argparse.ArgumentParser:
    """Give `parser` the two help labels it cannot give itself (C-7), and return it.

    One call, placed right after the parser is constructed:

        parser = argparse.ArgumentParser(description="...")
        configure_parser(parser)
        parser.add_argument(...)

    An `epilog` already set by the caller is KEPT and the labels are appended after it: this
    function exists to add a surface, never to replace one, so an existing exit-code paragraph
    stays exactly where its author put it. Everything already declared on the parser — every
    option, the usage synopsis, the description — is untouched, which is what keeps the clause
    a strictly additive change to 36 scripts instead of a rewrite of their interfaces.
    """
    labels = help_labels(effects, codes)
    existing = parser.epilog
    # `RawDescriptionHelpFormatter` keeps the two labels on their own lines. It is only safe to
    # set when the caller chose the default formatter; a caller that picked another one keeps
    # its choice, and argparse joins the epilog onto the option block instead of wrapping it
    # inside a description paragraph, so the labels still land on their own lines.
    if parser.formatter_class is argparse.HelpFormatter:
        parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.epilog = (existing.rstrip("\n") + "\n" + labels) if existing else labels
    return parser


# --------------------------------------------------------------------------------------
# The help labels for a HAND-ROLLED body (`_HELP = """..."""`), filled at run time
# --------------------------------------------------------------------------------------

def fill_help_labels(help_text: str, effects: Optional[str] = None,
                     codes: Optional[str] = None,
                     update: Optional[Iterable[str]] = None) -> str:
    """Append the two missing label lines to a hand-rolled help BODY (C-7).

    A hand-rolled body is a string literal; `configure_parser` cannot reach it. This function
    is the reachable form: it is CALLED with that body, so what it returns is assignable back
    to the very name the body was bound to. It is additive by construction — the body's
    existing lines are untouched and the two labels go at the end — and idempotent, so calling
    it on a body that already carries both labels changes nothing.

    A body that carries a label with its own text keeps it: a script with something specific to
    say about its exit codes has said it, and this function does not overwrite a statement.

    `update` names the module-level variables whose CURRENT value is the body; `update=None`
    means none, and the return value is the caller's to assign.
    """
    body = help_text.rstrip("\n")
    if not body.strip():
        return ""                          # an empty body stays empty: nothing to append to
    frame = sys._getframe(1)  # noqa: SLF001 - the caller's module globals are the target
    for name in update or ():
        # The body does not live in an argument at the call site: the module that calls the
        # guard names the variable, so the filled body is written back where its own help path
        # reads it. A name the module does not bind is skipped rather than created.
        current = frame.f_globals.get(name)
        if isinstance(current, str) and current.strip():
            body = current.rstrip("\n")
    present = {line.strip().split(":", 1)[0] + ":" for line in body.splitlines()}
    for label, value in ((SIDE_EFFECTS_LABEL, effects), (EXIT_CODES_LABEL, codes)):
        if label in present:
            continue
        body += "\n%s %s" % (label, value if value is not None else (
            DEFAULT_EFFECTS if label == SIDE_EFFECTS_LABEL else DEFAULT_CODES))
        present.add(label)
    for name in update or ():
        # The bound value carries the trailing newline a printed body wants; the return value
        # carries it too, so both consumers of this function print the same bytes.
        if name in frame.f_globals:
            frame.f_globals[name] = body + "\n"
    return body + "\n"


# --------------------------------------------------------------------------------------
# The argparse surface (C-8 / R4: top parser AND every subparser)
# --------------------------------------------------------------------------------------


class VersionAction(argparse.Action):
    """`--version` as an argparse action that reads the version at run time.

    Why not `action="version"`: argparse dispatches that string to `_VersionAction`, which
    prints a CONSTANT given at parser-construction time — exactly the literal this contract
    forbids. Why an action at all rather than a check in `main()`: a parser built with
    `add_subparsers(required=True)` rejects a leading `--version` at exit 2 (the
    required-subparsers trap, measured on `goal-utils.py`); an action declared on the parser
    fires during parsing, before the required subcommand is demanded.

    Register it on the top parser AND on every subparser — the action object is stateless,
    so one instance serves all of them. The signature below accepts everything argparse
    passes when it instantiates an action by CLASS (`parser.add_argument("--version",
    action=VersionAction)`), so both spellings work:

        parser.add_argument("--version", action=VersionAction)    # class form
        parser.add_argument("--version", action=VersionAction())  # instance form
    """

    def __init__(self, option_strings=("--version",), dest="version", nargs=0,
                 const=None, default=None, type=None, choices=None, required=False,
                 help="print the script name and the framework version, then exit",
                 metavar=None, **kwargs) -> None:
        super().__init__(option_strings=list(option_strings), dest=dest, nargs=nargs,
                         const=const, default=default, type=type, choices=choices,
                         required=required, help=help, metavar=metavar, **kwargs)

    @classmethod
    def attach(cls, parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
        """Register one `--version` action on `parser` (idempotent).

        A pre-built action INSTANCE cannot be handed to `add_argument`, because argparse
        re-instantiates whatever it receives by calling it with its own resolved kwargs —
        which turns an instance into "call `__call__` (dest, option_strings)" and raises
        `TypeError`. The class form is therefore the only correct one, and this helper is
        how the class travels: `VersionAction.attach(parser)` here, or
        `parser.add_argument("--version", action=VersionAction)` spelled out.
        """
        for action in parser._actions:  # noqa: SLF001 - argparse exposes no public query
            if isinstance(action, cls):
                return parser
        parser.add_argument("--version", action=cls)
        return parser

    def __call__(self, parser, namespace, values, option_string=None):  # noqa: D401
        argv0 = sys.argv[0] if sys.argv and sys.argv[0] else parser.prog
        start = Path(argv0).resolve().parent
        print_version(argv0, start)
        parser.exit(FLAG_EXIT)


def add_version_argument(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Attach the run-time `--version` action to `parser` (idempotent).

    Thin alias over `VersionAction.attach` so a consumer has one name to remember.
    """
    return VersionAction.attach(parser)


def attach_to_parser_tree(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Attach `--version` to `parser` AND every subparser reachable from it (C-8, R4).

    The required-subparsers trap is why this exists as one call: a parser built with
    `add_subparsers(required=True)` rejects `--version` at exit 2 unless the action is also
    declared on the subparser about to be dispatched to. A consumer that remembers the top
    parser and forgets the subparsers has a bug that only shows on the shape it forgot — so
    the traversal is a helper, not a line of advice. Nested subparsers are walked to any
    depth, and `attach` is idempotent, so calling this twice costs nothing.
    """
    VersionAction.attach(parser)
    for action in parser._actions:  # noqa: SLF001 - argparse exposes no public query
        if isinstance(action, argparse._SubParsersAction):  # noqa: SLF001
            for sub in action.choices.values():
                attach_to_parser_tree(sub)
    return parser


#: The separator a version line splits on: exactly one space between name and version.
VERSION_SPLIT = " "


def version_line_matches(line: str, script_name: str) -> bool:
    """Whether `line` is a well-formed `<script-name> <framework-version>` (C-8)."""
    parts = line.strip().split(VERSION_SPLIT)
    if len(parts) != 2 or not parts[1]:
        return False
    return Path(parts[0]).name == Path(script_name).name


def console_script_name(argv0: Optional[str] = None) -> str:
    """The name a script prints in its version line: the file's own basename (C-8).

    `sys.argv[0]` is the script as the caller spelled it — `./x.py`, `x.py`, or an absolute
    path. The version line carries only the basename, so a caller can parse it without
    knowing how the script was invoked.
    """
    raw = sys.argv[0] if argv0 is None else argv0
    name = Path(raw).name if raw else ""
    return name or "script"


#: The one spelling of the version flag (C-8). The bridges `sync-mirrors.py` emits carry the
#: same literal; the contract suite asserts the two agree.
VERSION_FLAG = "--version"

#: Comments a version PROBE plants inside the declaration region of a copy. They are the only
#: channel a source-scanning consumer has to ask "and what would `--version` answer?", because
#: the named flag is already spent on the probe that answers it. Deliberately odd spellings: a
#: source can never carry them, so a probe's cut can never remove a real option.
PROBE_RESERVE_MARKERS = ("# __sig-probe-reserve:begin", "# __sig-probe-reserve:end")


def guard_argv(argv: Optional[Sequence[str]] = None,
               declared: Optional[Iterable[str]] = None,
               text: Optional[str] = None,
               unknown_exit: int = UNKNOWN_OPTION_EXIT) -> None:
    """The one-call pre-parse guard a hand-rolled or late-parsing script puts at its top.

    Every script T060 backfilled calls it as the first statement of `main()`, in one of two
    shapes:

        _sig_guard(argv, declared=['--check', '--write'])   # spelled out
        _sig_guard(text=__doc__)                      # a hand-rolled help body

    It answers `--version` (exit 0), rejects an undeclared `-*` token (exit 2) and otherwise
    returns, leaving `sys.argv` untouched. `--help` is NOT answered here: a hand-rolled
    parser owns its own help body, and pre-empting it would change an existing interface
    (FR-018).

    `text` names a second, source-side job: it is the source of the module calling the guard,
    which this module turns into a help LABEL FILLER. `configure_parser` already gives an
    argparse script its four help labels; a hand-rolled help body is text this module cannot
    reach, so the guard reaches it through the source. `text` never supplies the option
    vocabulary: a hand-rolled script states its own in `declared`, and guessing one from
    source text would judge a token by a spelling nobody made a contract about.
    """
    preparse_version_guard(argv, declared=declared, text=text, unknown_exit=unknown_exit)


# --------------------------------------------------------------------------------------
# The pre-parse guard (C-9: for scripts whose parser is not, or not yet, argparse)
# --------------------------------------------------------------------------------------


def preparse_version_guard(argv: Optional[Iterable[str]] = None,
                           script_name: Optional[str] = None,
                           stream=None,
                           declared: Optional[Iterable[str]] = None,
                           text: Optional[str] = None,
                           unknown_exit: int = UNKNOWN_OPTION_EXIT) -> None:
    """Answer `--version` (and reject an unknown option) BEFORE any parser reads `argv`.

    Two situations need this: a script that reads `sys.argv` by hand (no argparse at all),
    and a script that builds its parser late. Calling it at the top of `main()` gives the
    same observable surface as `VersionAction` without requiring the parser to exist yet.

    Scanning stops at the bare `--` separator, so an argument after it is never treated as
    an unknown option (C-9). A token that is a known option never rescues an unknown one:
    every `-*` token before the separator is judged on its own.

    `--help` / `-h` are deliberately NOT handled here — a hand-rolled parser usually has
    its own help path, and swallowing it would change an existing interface (FR-018). They
    are also not REJECTED: a guard that refused `--help` would break the very interface it
    exists to protect, so they are skipped and left to the module's own parser.

    `declared` is the script's own option vocabulary — every option its parser accepts. It
    MUST be supplied by a script that HAS options, or the guard would refuse a legal one
    (measured on `sync-mirrors.py --check` while landing T060). A script with no options
    passes nothing, and then every `-*` token is undeclared, which is the truthful answer.

    The scan judges the WHOLE line before answering anything, which is C-9's sharp leg:
    `--help --bogus` and `--version --bogus` are both red, because a recognized token in
    the same line never rescues an unknown one. Answering while scanning left-to-right would
    let `--version --bogus` pass, so the line is judged first and answered second.

    `text`, when given, is the module's own source: see `guard_argv`.
    """
    source = text
    args: List[str] = list(sys.argv[1:] if argv is None else argv)
    name = script_name or (sys.argv[0] if sys.argv and sys.argv[0] else "script")
    err = sys.stderr if stream is None else stream
    known = set(declared or ())
    unjudged = args[:args.index(SEPARATOR)] if SEPARATOR in args else args
    for token in unjudged:
        if token in ("-h", "--help", VERSION_FLAG):
            continue                       # the module's own parser answers help
        # `--opt=value` is the same declared option as `--opt`; judge the name, not the pair.
        head = token.split("=", 1)[0] if token.startswith("--") and "=" in token else token
        looks_like_option = (token.startswith("-") and token != "-"
                             and not any(ch.isspace() for ch in token))
        if (looks_like_option and token not in known
                    and head not in known
                    and not (len(token) > 1 and token[1].isdigit())):
            print("error: unrecognized option: %s" % token, file=err)
            raise SystemExit(unknown_exit)
    if source is not None:
        # Judged before answered, never inside the scan: the fill runs exactly when the guard
        # returns to the caller, i.e. on the path where the module's own help body will print.
        fill_help_labels(source, update=["_HELP"])
    if VERSION_FLAG in unjudged:
        print_version(name)
        raise SystemExit(FLAG_EXIT)


# --------------------------------------------------------------------------------------
# Self-surface (this module is itself an applicable script: it obeys the contract it ships)
# --------------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="script_interface_cli.py",
        description="Shared script-interface helper: the rule table and the version source.",
        add_help=True,
    )
    configure_parser(
        parser,
        effects="none; reads %s and prints; a flag-only invocation writes nothing"
                % VERSION_SOURCE,
        codes="0 a flag or the emitted rule answered; 2 an unrecognized option",
    )
    parser.add_argument("--emit-rule", action="store_true",
                        help="print the constants table this helper owns, as JSON, then exit")
    add_version_argument(parser)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    line = list(sys.argv[1:] if argv is None else argv)
    # C-9's rescue leg: an undeclared token is refused BEFORE `--help` is answered, so
    # `--help --bogus` and `--bogus --help` are both red. argparse alone answers help while it
    # scans, which is exactly the lenient shape the clause forbids.
    preparse_version_guard(line, declared=("--emit-rule",), text=None)
    parser = build_parser()
    args = parser.parse_args(line)
    if args.emit_rule:
        import json
        print(json.dumps(rule_table(), indent=2, sort_keys=True))
        return FLAG_EXIT
    parser.print_help()
    return FLAG_EXIT


if __name__ == "__main__":
    sys.exit(main())
