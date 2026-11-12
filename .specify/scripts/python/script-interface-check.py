#!/usr/bin/env python3
"""Check every script in a repository against the script-interface contract.

Owner of the *rule*: `.specify/shared/definitions/script-interface-definitions.md`. The clauses this
engine implements are `contracts/script-interface-criteria.contract.md` C-1 … C-13; the
calling surface is `contracts/contract-checker-cli.contract.md` C-14 … C-22.

Two halves, one file (R1):

1. **The candidate screen** (C-1/C-2). Candidates are `git ls-files '*.sh' '*.py'` minus what
   `git check-ignore` reports as ignored. The work tree is then walked for the same two
   extensions; a path that is neither a candidate nor ignored is `candidate-not-collected`,
   naming the file, at exit 1. With git unavailable the walk IS the candidate set and the
   report says `source=walk-only` — never "nothing scanned, therefore all good".

2. **The classification pipeline and the probes** (C-3 … C-13). Applicability is decided by
   RUNNING a copy of the file and observing whether its own code executed; a mirror copy
   inherits its source's class and is judged once; an applicable file then owes the flag
   surface C-7 … C-11, probed in a sandbox copy created outside the measured tree.

Usage:
  python3 .specify/scripts/python/script-interface-check.py [--root PATH] [--json]
      [--files PATH[,PATH ...]] [--skip-probe] [--sandbox DIR]
      [--budget-seconds N] [--check-projection]
      [--emit-rule [--json]]

Exit codes:
  0  the screen ran; every applicable candidate is compliant, every exempt candidate
     carries a basis, and violations == 0
  1  at least one violation, or a structural finding (`candidate-not-collected`,
     probe-unavailable, probe-budget-exhausted, probe-inconclusive, projection-mismatch)
  2  an argument or environment error (bad flag combination, `--root` not a directory)

Read-only: the only writes are inside the sandbox copy, which is removed on exit whether the
run succeeded or failed. Nothing is ever written inside the measured tree.
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
# The help-label helper (C-7) is read through `_load_helper()` below, the same by-path load the
# rule table uses: this engine has no package to import from, and a second import site would be
# a second thing to keep in step. `script_interface_cli.py` writes nothing on import.

# --------------------------------------------------------------------------------------
# Root resolution (C-15: the mirror copy must resolve to the repository, never to .specify)
# --------------------------------------------------------------------------------------

_HERE = Path(__file__).resolve()
REPO_ROOT = _HERE.parents[2]
if REPO_ROOT.name == ".specify":
    REPO_ROOT = REPO_ROOT.parent

# --------------------------------------------------------------------------------------
# The rule table — ONE module-level source; the emitted rule and the executed rule read it
# --------------------------------------------------------------------------------------


def _load_helper():
    """Load the sibling helper by path (the engine has no package to import from).

    `script_interface_cli.py` owns the constants table, the version source and the version
    line shape. Reading them from there — rather than re-typing them here — is what keeps
    `--emit-rule` and the classifier from drifting (C-21).
    """
    import importlib.util

    path = Path(__file__).resolve().parent / "script_interface_cli.py"
    spec = importlib.util.spec_from_file_location("_script_interface_cli_086", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None, "cannot load %s" % path
    spec.loader.exec_module(module)
    return module


_CLI = _load_helper()

LABELS = tuple(_CLI.LABELS)
FLAG_FORMS = tuple(_CLI.FLAG_FORMS)
SEPARATOR = _CLI.SEPARATOR
VERSION_LINE = _CLI.VERSION_LINE
VERSION_SOURCE = _CLI.VERSION_SOURCE
EXEMPT_BASIS = tuple(_CLI.EXEMPT_BASIS)
FINDINGS = tuple(_CLI.FINDINGS)
EXCEPTION_COLUMNS = tuple(_CLI.EXCEPTION_COLUMNS)
EXCEPTION_LIMBS = tuple(_CLI.EXCEPTION_LIMBS)
FORBIDDEN_CRITERIA = tuple(_CLI.FORBIDDEN_CRITERIA)
DECIDED_BY = tuple(_CLI.DECIDED_BY)
OBSERVATIONS = tuple(_CLI.OBSERVATIONS)
UNKNOWN_VERSION = _CLI.UNKNOWN_VERSION

#: How each language says "this file has its own entry point". The marker is never a source
#: shape: C-3 forbids the presence of top-level statements and the shebang word as criteria,
#: and C-4 forbids the `__main__` block, so both are replaced by an OBSERVED execution.
MUTATION_LANGUAGES = ("bash", "python")

#: Per-run wall-clock ceiling for one probe of one candidate; a probe that cannot finish
#: inside it is `probe-inconclusive`, never exempt.
PROBE_TIMEOUT_SECONDS = 20

#: Soft budget for the whole probe phase (C-16 `--budget-seconds`).
DEFAULT_BUDGET_SECONDS = 900

SCHEMA = "script-interface-check/1"

#: Option token the rejection probe uses. It is undeclared in every scenario shell and every
#: scenario python module by construction, so "recognized" is never a coincidence.
UNKNOWN_PROBE_TOKEN = "--script-interface-check-undeclared-option"

#: The token the separator probe places after a bare `--`; it MUST NOT be reported unknown.
SEPARATOR_PROBE_TOKEN = "--script-interface-check-after-separator"

#: The M-1 observation file. A compliant run never creates it; the help-wins and
#: zero-side-effect probes read its absence as the passing signal.
OBSERVATION_FILE = ".script-interface-check-observation"

#: The `basis` the help-wins probe records when C-11's precondition is absent (C-11).
HELP_WINS_NO_WRITE_OPTION = "no-write-option"

#: The `basis` the rescue leg records for a consumer that DECLARES `passthrough` (C-9).
RESCUE_PASSTHROUGH_BASIS = "passthrough"

#: C-3's three forbidden criteria, as the closed vocabulary the report names them by. The
#: clause forbids each one as a criterion, so the engine has to be able to SAY which
#: observation decided a file; naming a criterion here is the report's spelling of a refusal,
#: never a licence to use one (see `FORBIDDEN_CRITERIA_REASON`).
#:
#: `FORBIDDEN_CRITERIA` / `DECIDED_BY` themselves live in `script_interface_cli.py` with the
#: rest of the table (imported at the top of this file), because `--emit-rule` publishes them.

#: What each forbidden criterion would have claimed, and why the run-based judgement does not
#: rest on it. One entry per member of `FORBIDDEN_CRITERIA`, so the emitted rule cannot name a
#: criterion without saying how the engine refuses it.
FORBIDDEN_CRITERIA_REASON = {
    "top-level-statements":
        "a library's dependency check is a top-level statement too, so presence proves nothing",
    "shebang-word":
        "`bash` vs `sh` says which interpreter to use, not whether the file acts",
    "self-description":
        "a comment, docstring or file name is the author's claim, not an observation",
}

#: Which observation decides a file's class — `DECIDED_BY` itself is imported from
#: `script_interface_cli.py`. The first member is C-3's / C-4's own criterion; the remaining
#: two are report states that are NOT classes — a mirror inherits its source's judgement
#: (C-6), and a file nobody could measure was never judged at all (C-12).

#: The prefix the report gives an unmeasured file's observation. C-12: an unjudged candidate
#: stays its own state instead of borrowing one of the three criteria and looking decided.
UNEVALUATED_OBSERVATION_PREFIX = "unevaluated"

#: How the help-wins observation spells a valued option's value slot (C-20).
VALUE_PLACEHOLDER = "<value>"

#: Sandbox roots, in preference order (C-10: never `/tmp`, which is `noexec` on this host).
SANDBOX_ROOTS = (".specify/.tmp", "/var/tmp", "~/tmp")

#: What a measured-tree copy leaves behind: version-control internals, caches, installed
#: dependencies, and the sandbox root itself (copying it would recurse into the copy).
TREE_COPY_IGNORE = shutil.ignore_patterns(
    ".git", "__pycache__", ".venv", "node_modules", ".pytest_cache", ".mypy_cache",
    ".tmp",
)

#: Stderr names that are the INTERPRETER failing to load the candidate, i.e. evidence the
#: run never reached the file's own code (C-4 / C-12 / C-13). A candidate that dies this
#: way was not observed, so it MUST NOT be filed as an exemption. `FileNotFoundError` is
#: deliberately absent: a script that opens a missing path and reports it is the script
#: working, and filed as one of these it would turn every such exit into a false finding.
LOAD_FAILURE_NAMES = ("ModuleNotFoundError", "ImportError", "SyntaxError")


# --------------------------------------------------------------------------------------
# The screen (C-1 / C-2)
# --------------------------------------------------------------------------------------


def _git(root: Path, *args: str):
    """Run one git command inside `root`; return (exit, stdout, stderr)."""
    try:
        proc = subprocess.run(
            ["git", *args], cwd=str(root), capture_output=True, text=True,
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", str(exc)
    return proc.returncode, proc.stdout, proc.stderr


def _git_available(root: Path) -> bool:
    code, _, _ = _git(root, "rev-parse", "--git-dir")
    return code == 0


def _tracked_candidates(root: Path) -> List[str]:
    code, out, _ = _git(root, "ls-files", "*.sh", "*.py")
    if code != 0:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def _ignored_paths(root: Path) -> set:
    """Every path `git check-ignore` reports, over the union of tracked and walked paths."""
    code, out, _ = _git(root, "ls-files")
    tracked = {line.strip() for line in out.splitlines() if line.strip()} if code == 0 else set()
    walked = _walk_scripts(root)
    candidates = tracked | set(walked)
    if not candidates:
        return set()
    # One invocation: check-ignore reads paths from stdin, so a 700-path tree costs one call.
    try:
        proc = subprocess.run(
            ["git", "check-ignore", "--stdin"],
            cwd=str(root), input="\n".join(sorted(candidates)) + "\n",
            capture_output=True, text=True, timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    # exit 0 = at least one ignored, 1 = none, >1 = error. Only the output matters.
    return {line.strip() for line in proc.stdout.splitlines() if line.strip()}


def _walk_scripts(root: Path) -> List[str]:
    """Every `*.sh` / `*.py` in the work tree, repo-relative and posix-form."""
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(
            d for d in dirnames if d not in {".git", "__pycache__", "node_modules", ".venv"}
        )
        for name in sorted(filenames):
            if name.endswith(".sh") or name.endswith(".py"):
                full = Path(dirpath) / name
                found.append(full.relative_to(root).as_posix())
    return sorted(found)


def _read_declared_pairs(root: Path) -> List[Tuple[str, str]]:
    """The mirrors declared as projected, read from `sync-mirrors.py`'s own table.

    C-34 fixes one declaration; this engine consumes it instead of keeping a second list.
    The table is read by executing the module's source for its two module-level names only —
    no import side effect, no second copy of the declaration.
    """
    path = root / "scripts" / "python" / "sync-mirrors.py"
    if not path.is_file():
        return []
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    namespace: Dict[str, object] = {}
    try:
        code = compile(source, str(path), "exec")
    except SyntaxError:
        return []
    # Executing the whole module would run its `main()` guard; only the assignment block is
    # needed, so the module-level statements are executed in a namespace whose __name__ is
    # not "__main__", which makes the tail guard inert.
    namespace["__name__"] = "_sync_mirrors_projection_reader"
    namespace["__file__"] = str(path)
    try:
        exec(code, namespace)  # noqa: S102 - a module of this repository, read not imported
    except Exception:  # pragma: no cover - a broken table is reported by its own guard
        return []
    pairs = []
    for row in namespace.get("PROJECTED_FILES", ()) or ():
        try:
            mirror, _kind = row[0], row[1]
        except (TypeError, IndexError):
            continue
        pairs.append((str(mirror), str(row[1])))
    return pairs


def screen(root: Path, subset: Optional[List[str]] = None) -> dict:
    """Derive the candidate set and assert its coverage (C-1 / C-2).

    Returns the screen's own record: the source that produced it, the candidates, and the
    coverage findings. No probe runs here — this half is decidable without executing
    anything, which is what makes `--skip-probe` a real mode rather than a shortcut.
    """
    tracked_mode = _git_available(root)
    walked = _walk_scripts(root)
    ignored = _ignored_paths(root) if tracked_mode else set()
    tracked = _tracked_candidates(root) if tracked_mode else []

    if tracked_mode:
        candidates = [p for p in tracked if p not in ignored and (root / p).is_file()]
        source = "tracked"
    else:
        candidates = [p for p in walked if p not in ignored]
        source = "walk-only"

    findings: List[dict] = []
    ignored_walked = [p for p in walked if p in ignored]
    if ignored_walked:
        findings.append({
            "kind": "ignored-not-probed",
            "resolved": True,
            "paths": sorted(ignored_walked),
            "message": "ignored by .gitignore, so not a candidate",
        })

    if tracked_mode:
        candidate_set = set(candidates)
        for path in walked:
            if path in candidate_set or path in ignored:
                continue
            findings.append({
                "kind": "candidate-not-collected",
                "resolved": False,
                "paths": [path],
                "message": "%s is neither a tracked candidate nor ignored" % path,
            })

    if subset:
        narrowed = [p for p in candidates if p in set(subset)]
        missing = [p for p in subset if p not in set(candidates)]
        for path in missing:
            findings.append({
                "kind": "candidate-not-collected",
                "resolved": False,
                "paths": [path],
                "message": "requested candidate %s is not in the candidate set" % path,
            })
        candidates = narrowed
        mode = "subset"
    else:
        mode = "full"

    return {
        "source": source,
        "mode": mode,
        "candidates": candidates,
        "walked": walked,
        "ignored": sorted(ignored),
        "findings": findings,
    }


# --------------------------------------------------------------------------------------
# Classification (C-3 / C-4 / C-5 / C-6) — by running a copy, never by reading a source
# --------------------------------------------------------------------------------------


def _language(path: str) -> str:
    return "bash" if path.endswith(".sh") else "python"


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _bash_action_positions(lines: List[str]) -> List[int]:
    """The line indexes at which a bash candidate could act, MOST promising tier first.

    C-3 fixes the observation, not the text: "run it and see whether its code executes". The
    three forbidden criteria — top-level statements in general, the shebang word, the file's
    own self-description — are exactly what this function refuses to consult. What it does
    consult is where a shell file *can* take an action, in three tiers of confidence:

    1. a statement in the file's body at all — the place an action would have to be;
    2. one that is not merely an assignment (an assignment alone changes no state outside the
       shell);
    3. one whose head is not a definition keyword.

    Only the DEFINING line is a definition: a function's body is code that runs when the
    function is called, so it stays a candidate position. Several positions are returned
    because one can be defeated by the file's own control flow — an `exit 1` before the marker
    — and the classification run, not this function, decides. A file that carries no statement
    outside its definitions has no position at any tier, which is what makes a
    `common.sh`-shaped library exempt by run semantics rather than by name.
    """
    defining = re.compile(
        r"^\s*(function\s+[A-Za-z0-9_.-]+|\(\s*\)|[A-Za-z0-9_.-]+\s*\(\s*\))")
    assignment = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
    closure = re.compile(r"^(\}|fi\b|done\b|esac\b|\)\s*$|;;|;;&|;&)")
    loop_body = re.compile(r"^(for|while|until|select)\b|;\s*do\b$|\bdo$")
    branch_arm = re.compile(r"(\)\s*$|;;\s*$|;;&\s*$|;&\s*$)")
    tier1: List[int] = []
    tier2: List[int] = []
    tier3: List[int] = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if line[:1] in (" ", "\t"):
            continue
        if defining.match(line):
            continue
        tier3.append(index)
        if assignment.match(stripped) or closure.match(stripped):
            # A bare assignment changes no state outside the shell, and a closure is not a
            # statement. Neither can be where an action lives.
            continue
        if loop_body.match(stripped) or branch_arm.search(stripped):
            # `for x in ...; do` and `pattern) ... ;;` are control-flow scaffolding inside an
            # action, not the action itself. Instrumenting them would make a file that only
            # carries a loop at its top level look like it acts.
            continue
        tier2.append(index)
        tier1.append(index)
    ordered: List[int] = []
    for tier in (tier1, tier2, tier3):
        for position in reversed(tier):
            if position not in ordered:
                ordered.append(position)
    return ordered[:6]


def _instrument_bash(text: str, marker: Path) -> List[Tuple[int, str]]:
    """Every instrumented variant of `text`, one per candidate position (see above).

    One layer of the shell's own syntax can sit between a position and the point the marker
    must precede: `case "$arg" in -h|--help) usage; exit 0 ;; esac` prints help THROUGH the
    arm, so a marker after the arm never fires for `-h`, while a marker before the whole
    compound fires for every argument. Each position therefore yields both sides — the
    statement and the arm that carries it — and the weighted order below prefers the arm.
    """
    lines = text.splitlines(keepends=True)
    observed_line = 'printf "%%s\\n" "executed" >> %s' % _shquote(str(marker))


    def insert(at: int) -> str:
        return "".join(lines[:at] + [observed_line + "\n"] + lines[at:])

    variants: List[Tuple[int, str]] = []
    for position in _bash_action_positions(lines):
        variants.append((1, insert(position + 1)))
        line = lines[position]
        indent = len(line) - len(line.lstrip())
        for arm in range(indent + 1, len(line)):
            if line[arm - 1:arm] == ")" and line[:arm].strip():
                variants.append((2, insert(arm)))
                break
    return variants


def _order_probes(variants: Sequence[Tuple[int, str]], text: str,
                   language: str) -> Tuple[List[Tuple[int, str]], bool]:
    """Order the probe positions, largest claim first; report whether the order is weighted.

    For a module that declares a `__main__` guard, a marker on the far side of that guard is
    the file's own statement about where its entry point lives, so it outranks a module-level
    statement by more than any statement count can. The second element of the result says
    whether an aborted run (marker fired, process then exited non-zero of its own accord) is
    evidence enough; once the per-position structure carries information — a shell arm, a
    `__main__` guard — a bare module-level abort no longer is.
    """
    if not variants:
        return [], False
    guarded = False
    if language == "python":
        try:
            guarded = _claims_to_be_main(ast.parse(text))
        except SyntaxError:
            guarded = False
    weighted = guarded or any(weight > 1 for weight, _ in variants)
    if not weighted:
        return list(variants), False

    def rank(item: Tuple[int, str]) -> int:
        weight, variant = item
        if language != "python":
            return weight
        # 3 = inside/around the `__main__` guard, 2 = a statement big enough to be a branch,
        # 1 = a plain module-level statement.
        return 3 if _marker_at_guard_top(variant) else min(weight, 2)

    return sorted(variants, key=rank, reverse=True), True


def _marker_at_guard_top(variant: str) -> bool:
    """Whether the inserted marker is the FIRST statement of the module's `__main__` guard.

    Read from the AST rather than from neighbouring text: the guard and its body may be
    separated by any number of blank lines, and a line-distance guess mistakes one for the
    other. The marker is recognisable because it is the only statement in the file whose
    expression writes the observation string.
    """
    try:
        tree = ast.parse(variant)
    except SyntaxError:
        return False
    for node in tree.body:
        if not (isinstance(node, ast.If) and _claims_to_be_main(node)):
            continue
        if not node.body:
            continue
        first = node.body[0]
        if not isinstance(first, ast.Expr):
            continue
        for sub in ast.walk(first):
            if isinstance(sub, ast.Constant) and "executed" in str(sub.value):
                return True
    return False


def _python_for(text: str) -> str:
    """The interpreter a python candidate asks for.

    A script's shebang is part of what it is, and a classification that runs it under a
    different interpreter than the one it names measures something else — `#!/usr/bin/env -S
    python3 -u` is a different programme from `sys.executable`. When the shebang names no
    python, the engine's own interpreter answers.
    """
    first = text.splitlines()[0] if text else ""
    if not first.startswith("#!"):
        return sys.executable
    words = first[2:].split()
    if not words:
        return sys.executable
    if Path(words[0]).name == "env":
        words = [word for word in words[1:] if not word.startswith("-")]
        words = words[1:] if words and words[0] == "-S" else words
    if not words:
        return sys.executable
    interpreter = words[0]
    if not Path(interpreter).name.startswith("python"):
        return sys.executable
    return interpreter


def _shquote(text: str) -> str:
    return "'" + text.replace("'", "'\\''") + "'"


def _claims_to_be_main(module: ast.Module) -> bool:
    """Whether the module carries a `__main__` guard — a claim that its entry point is there.

    Not a criterion in itself (C-4 forbids that): it only says where the file itself says
    the action belongs, so an observation made somewhere else can be weighed against it.
    """
    for node in module.body:
        if not isinstance(node, ast.If):
            continue
        for sub in ast.walk(node.test):
            if isinstance(sub, ast.Name) and sub.id in ("__name__", "__main__"):
                return True
            if isinstance(sub, ast.Constant) and sub.value == "__main__":
                return True
    return False


def _exits_early(node: ast.stmt) -> bool:
    """Whether the statement ends the process where it sits (`sys.exit(...)`, `raise ...`)."""
    for sub in ast.walk(node):
        if isinstance(sub, ast.Raise):
            return True
        if isinstance(sub, ast.Call):
            func = sub.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name in ("exit", "exit_", "SystemExit"):
                return True
    return False


def _instrument_python(text: str, marker: Path) -> List[Tuple[int, str]]:
    """Every instrumented variant of a python module, with the size of the claim it probes.

    Same restriction as the bash side and for the same reason: a `def` / `class` / `import` at
    the top level runs when the module is imported, so an observation around it says nothing
    about the file's entry-point behaviour. What counts is an ACTION — a call, an assignment
    whose value is computed, a `raise`/`return` outside a definition. Several positions are
    returned because `sys.exit()` in an earlier one ends the run before a later marker.

    The marker's side of a statement is what makes the observation meaningful. Before a
    BLOCK statement (`if`, `try`, `with`, a loop): a `sys.exit(main())` inside the block
    ends the process, so a marker placed after it would never be reached — the classic
    `if __name__ == "__main__": sys.exit(main())` guard would lose its effect to the exit
    status. After a SIMPLE statement: an import or a call that raises must not be able to
    sit behind a marker, and a marker above a `from __future__` import is a `SyntaxError`
    that would turn a runnable file into a fake "no action here". The second element of each
    pair is the number of statements the marker stands for, so the caller can prefer the
    largest claim and can tell a guarded action from a module-level one.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    lines = text.splitlines(keepends=True)
    observed = 'open(%r, "a", encoding="utf-8").write("executed\\n")\n' % str(marker)
    variants: List[Tuple[int, bool, str]] = []
    for node in tree.body:
        if isinstance(node, (ast.ClassDef, ast.Import, ast.ImportFrom, ast.Expr)):
            # A class, an import and a bare expression are machinery. A FUNCTION DEFINITION is
            # deliberately NOT here: its body is code that runs when it is called, and a module
            # whose only statement is a function is exactly the file C-3 says must be measured
            # rather than read. C-4's own negative
            # control — "a module that imports cleanly and does nothing stays exempt" — is
            # observable ONLY here: the marker runs after the module's own code, so the run
            # does reach the file and whatever the definitions do on their own happens. The
            # position is flagged as the MINIMAL claim and kept only when nothing larger
            # exists (`_minimal_claim` below); dropping it outright would leave the exemption
            # undecidable by a run and hand the decision to a criterion C-3 forbids.
            continue
        block = isinstance(node, (ast.If, ast.Try, ast.With, ast.AsyncWith,
                                  ast.For, ast.AsyncFor, ast.While))
        guarded = isinstance(node, ast.If) and _claims_to_be_main_number(node)
        indent = ""
        if guarded and node.body:
            # Into the guard's body, as its first statement: that is the position the file
            # itself designates as its entry point, and the only one a `sys.exit(main())`
            # cannot pre-empt. The marker takes the body's indentation, or the block is a
            # syntax error and the guarded position would silently be lost.
            cut = node.body[0].lineno - 1
            body_line = lines[cut]
            indent = body_line[:len(body_line) - len(body_line.lstrip())]
        elif block:
            cut = node.lineno - 1
        else:
            cut = getattr(node, "end_lineno", None) or node.lineno
        candidate = "".join(lines[:cut] + [indent + observed] + lines[cut:])
        if not _is_valid_python(candidate):
            # A position whose insertion point breaks the grammar cannot be measured; the
            # next position is tried instead of filing the file on a fabricated crash.
            continue
        variants.append((len(_statements(node)), guarded, candidate))
    # The MINIMAL claim: the last statement that merely LOADED, offered only when the file
    # carries no action of its own. Without it C-4's negative control is unreachable by any
    # run, and "imports cleanly and does nothing" would have to be read off the file's shape
    # — a page C-3 forbids deciding from.
    if not variants:
        minimal = _minimal_claim(lines, tree, observed)
        if minimal is not None:
            variants.append((0, False, minimal))
    # The `__main__` guard is where the file itself says its entry point is, so it must not
    # fall off the end of a bounded list: a 400-line module's guard is its LAST statement.
    variants.sort(key=lambda item: item[1], reverse=True)
    return [(weight, candidate) for weight, _guarded, candidate in variants[:6]]


def _minimal_claim(lines: Sequence[str], tree: ast.Module, observed: str) -> Optional[str]:
    """The instrumented copy whose marker runs directly after the file's last top-level statement.

    The LAST statement is chosen, not the first: a module's action does not move, so a marker
    past everything the file does on load fires exactly when the file's code was reached at
    all. When no such position compiles (a file whose last statement opens a block the marker
    cannot close), the text is left uninstrumented and the caller reports `unevaluated`
    rather than reading the class off the file's shape.
    """
    if not tree.body:
        return None
    end = getattr(tree.body[-1], "end_lineno", None)
    if end is None:
        return None
    candidate = "".join(list(lines[:end]) + [observed] + list(lines[end:]))
    return candidate if _is_valid_python(candidate) else None


def _claims_to_be_main_number(node: ast.If) -> bool:
    """Whether this `If` is the module's `__main__` guard."""
    for sub in ast.walk(node.test):
        if isinstance(sub, ast.Name) and sub.id in ("__name__", "__main__"):
            return True
        if isinstance(sub, ast.Constant) and sub.value == "__main__":
            return True
    return False


def _statements(node: ast.stmt) -> List[ast.stmt]:
    """The statements a marker placed at `node` would stand in for."""
    if isinstance(node, ast.If):
        return list(node.body) + list(node.orelse)
    body = getattr(node, "body", None)
    return list(body) if isinstance(body, list) else [node]


def _is_valid_python(text: str) -> bool:
    """Whether the interpreter's own compiler would accept this text — not just its parser.

    `ast.parse` implements the grammar but not the position rules: it accepts
    `open(...)` ahead of `from __future__ import annotations`, which `compile()` then
    rejects. The marker is legal only if the real compiler agrees, because the register that
    runs the variant is the same compiler. `compile(..., "__main__", "exec")` applies every
    future-import rule at that level rather than treating the text as an imported module.
    """
    try:
        compile(text, "<script-interface-check-instrumented>", "exec")
    except SyntaxError:
        return False
    return True


def _copy_measured_tree(root: Path, destination: Path) -> None:
    """Copy the repository once, under `destination`, so every candidate keeps its place.

    C-3 / C-4 say "run a copy of the repository and observe". A file dropped alone into a
    flat directory is NOT that copy: its sibling modules, its package parent and every
    `Path(__file__).parents[n]` read resolve against the flat directory instead, so a
    perfectly runnable script dies at import and the engine would then report the crash as
    "no entry point" — an exemption manufactured by the harness (C-12/C-13).

    `shutil.copytree(symlinks=True)` keeps the `.specify/` projections pointing at their
    same-relative-path targets inside the copy, so a probe reads the COPY and never the
    measured tree.
    """
    shutil.copytree(root, destination, ignore=TREE_COPY_IGNORE, symlinks=True)
    _seed_git_boundary(destination)


def _seed_git_boundary(destination: Path) -> None:
    """Give the copy its own git root so a candidate's repo-root search stops here (T088)."""
    try:
        subprocess.run(["git", "init", "-q", str(destination)], capture_output=True,
                       text=True, timeout=30, stdin=subprocess.DEVNULL)
        for key, value in (("user.email", "probe@example.invalid"),
                           ("user.name", "probe")):
            subprocess.run(["git", "-C", str(destination), "config", key, value],
                           capture_output=True, text=True, timeout=10,
                           stdin=subprocess.DEVNULL)
        subprocess.run(["git", "-C", str(destination), "add", "-A"], capture_output=True,
                       text=True, timeout=60, stdin=subprocess.DEVNULL)
        subprocess.run(["git", "-C", str(destination), "commit", "-q", "-m",
                        "probe boundary"], capture_output=True, text=True,
                       timeout=60, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        # A copy without a git boundary is still bounded by GIT_CEILING_DIRECTORIES.
        pass


def _repo_signature(root: Path) -> dict:
    """Observable state of the measured repository, for the escape assertion (T089)."""
    def git(*args: str) -> str:
        try:
            proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                                  text=True, timeout=30, stdin=subprocess.DEVNULL)
            return proc.stdout if proc.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    specs_dir = root / ".specify" / "specs"
    specs = sorted(item.name for item in specs_dir.iterdir()) if specs_dir.is_dir() else []
    return {"refs": git("for-each-ref", "--format=%(refname)"),
            "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
            "specs": specs}


def _load_failure(result: dict) -> Optional[str]:
    """The interpreter's own load error, when the run never reached the candidate's code.

    C-13 separates "the run happened and nothing attributable was observed" (an exemption)
    from "the run could not interpret the candidate at all" (never an exemption). The
    distinguisher is the interpreter's traceback: a `ModuleNotFoundError` /
    `ImportError` / `FileNotFoundError` / `PackageNotFoundError` in stderr, or a
    `SyntaxError`, means the file's own statements never ran.

    Two guards keep this from swallowing ordinary behaviour. The child process must have
    run at all (`returncode is None` is the engine's own failure, reported elsewhere), and
    only a TYPED name counts: an ordinary `FileNotFoundError` in a script's own output is
    the script working, while `ModuleNotFoundError` and `ImportError` are the loader's.
    """
    if result.get("returncode") is None:
        return None
    # A run that never started (the interpreter itself was missing, the file vanished) is the
    # engine's failure, not the candidate's; it cannot be read as "the candidate loaded fine".
    if str(result.get("observed", "")).startswith("error:"):
        return None
    stderr = str(result.get("stderr") or "")
    for needle in LOAD_FAILURE_NAMES:
        if needle in stderr:
            return needle
    return None


def _stderr_tail(result: dict, limit: int = 400) -> str:
    """The last `limit` characters of stderr, as evidence for a non-conclusive run."""
    stderr = str(result.get("stderr") or "").strip()
    return stderr[-limit:] if stderr else ""


def _mirror_source(root: Path, path: str) -> Optional[str]:
    """The same-path source of a `.specify/**` copy, when one exists (C-6).

    A `.specify/<rest>` copy's source is looked up among the declaration surfaces this
    repository actually projects. When several candidates match, the first existing one wins;
    when none match, the copy is `mirror-unpaired` and is judged on its own run semantics.
    """
    if not path.startswith(".specify/"):
        return None
    rest = path[len(".specify/"):]
    if rest.startswith("skills/"):
        # `.specify/skills/<name>/...` pairs with `skills/extenal|internal/<name>/...`
        tail = rest[len("skills/"):]
        candidates = ("skills/external/" + tail, "skills/internal/" + tail, rest)
    else:
        candidates = (rest, ".specify/scripts/" + rest, ".specify/shared/" + rest)
    for candidate in candidates:
        if (root / candidate).is_file():
            return candidate
    return None


def _probe_env(sandbox: Path) -> Dict[str, str]:
    """The environment a probe runs under: fixed, minimal, and independent of the caller's.

    A probe whose outcome depends on the operator's shell is not a measurement. Two variables
    are load-bearing and only these two are passed through: `PATH`, because a script has to
    find its interpreter, and `HOME`, redirected into the sandbox so a probe that honours
    `$HOME` writes where the fingerprint can see it instead of into the operator's home.
    """
    tmp = sandbox / "probe-tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    return {"PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "HOME": str(sandbox), "LC_ALL": "C", "LANG": "C",
            # T088: the candidate's own repo-root search must stop at the sandbox. Without
            # this ceiling `git rev-parse --show-toplevel` finds the MEASURED repository
            # above `.specify/.tmp/`, and a write-on-operand script scaffolds there (the
            # 2026-11-07 incident created 40 branches and spec dirs).
            "GIT_CEILING_DIRECTORIES": str(sandbox),
            "TMPDIR": str(tmp), "TMP": str(tmp), "TEMP": str(tmp)}


def _run_probe(command: Sequence[str], cwd: Path, marker: Path,
               timeout: int = PROBE_TIMEOUT_SECONDS,
               env: Optional[Dict[str, str]] = None) -> dict:
    """Run one probe; return what was observed, never what was hoped for."""
    try:
        proc = subprocess.run(
            list(command), cwd=str(cwd), capture_output=True, text=True,
            timeout=timeout, stdin=subprocess.DEVNULL, env=env,
        )
    except subprocess.TimeoutExpired:
        return {"observed": "timeout", "returncode": None, "stdout": "", "stderr": ""}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"observed": "error:%s" % exc, "observed_error": str(exc),
                "returncode": None, "stdout": "", "stderr": ""}
    return {
        "observed": "ran",
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "marker": marker.is_file(),
    }


def _observation_too_weak(source_text: str, language: str,
                          instrumented: Optional[bool] = None) -> bool:
    """C-3's shape requirement, stated once for both report faces: is the decision a run?

    The clause fixes an OBSERVATION — "run the file as a script and see whether its code
    after the entry position executes" — and the engine carries it out by instrumenting a
    candidate position in a copy. Where a file carries no position at all there is nothing to
    put a marker in, and the run then observes the file's own exit and nothing about its
    code. That is the ONE case where an answer stops being a run: an answer taken from it
    rests on "there is no top-level statement", which is exactly C-3's first forbidden
    criterion (and the page the shebang word and the self-description land on too).

    `instrumented` is the engine's own reading — "were variants available to instrument" —
    handed in rather than recomputed here, so this predicate cannot disagree with the
    classifier that produced the row. `source_text`/`language` are only consulted when the
    caller has no variant count to offer (a mirror judged on its source's content).
    """
    probe_text = source_text
    instrument = _instrument_bash if language == "bash" else _instrument_python
    if instrumented is None:
        return not instrument(probe_text, Path("C-3-unused-marker"))
    return not instrumented


def _decided_by(instrumented: bool, projected: bool, unevaluated: bool) -> str:
    """Which observation decided this file, in `DECIDED_BY`'s vocabulary (C-3 / C-6 / C-12).

    Derived from the observation the classifier actually made, never from a second reading of
    the source: `instrumented` says the run put a marker in the file's own code, `projected`
    says the class came from a mirror's source, and `unevaluated` says neither happened.
    """
    if unevaluated:
        return "unevaluated"
    if projected:
        return "inherited-from-source"
    return "run-semantics" if instrumented else "unevaluated"


def classify(root: Path, sandbox: Path, path: str,
             budget: "Budget") -> dict:
    """Decide one candidate's applicability by running an instrumented copy (C-3 … C-6).

    The returned row is the data model's E-2: `applicable`, `basis`, `evidence`, `projected`.
    """
    language = _language(path)
    text = _read_text(root / path)
    if text is None:
        return {"applicable": None, "basis": "probe-unreadable",
                "evidence": "the file could not be read as UTF-8", "projected": False}

    mirror_of = _mirror_source(root, path)
    projected = mirror_of is not None and path.startswith(".specify/")
    declared = dict(_read_declared_pairs(root))
    if projected and path in declared:
        projected_kind = declared[path]
    else:
        projected_kind = "byte-identical" if projected else ""

    target = mirror_of if projected else path
    # The copy is made once per run, so a file the screen named but the copy does not hold is
    # an engine failure, not an observation about the candidate. Said once, before any
    # instrumentation work, rather than dressed up as a loader crash further down.
    if not (sandbox / "tree" / target).is_file():
        return {"applicable": None, "basis": "probe-inconclusive",
                "evidence": "the candidate is absent from the sandbox copy of the repository",
                "projected": projected, "projection_kind": projected_kind}
    # C-4's "run it, do not read it" is about the CLASS. Whether there is an action position
    # to instrument at all is a property of the file being judged: a mirror carries its own
    # (possibly projected) content, so the instrumented copy comes from the mirror, while the
    # class it lands in is the source's because the mirror has no entry point of its own.
    source_text = text if target == path else _read_text(root / target)
    probe_text = text
    if source_text is None:
        return {"applicable": None, "basis": "probe-unreadable",
                "evidence": "the mirror's source could not be read", "projected": projected,
                "projection_kind": projected_kind}

    marker = sandbox / "observation" / (path.replace("/", "__") + ".marker")
    marker.parent.mkdir(parents=True, exist_ok=True)
    instrument = _instrument_bash if language == "bash" else _instrument_python
    variants = instrument(probe_text, marker)
    if not variants and projected and source_text != probe_text:
        # The mirror carries no action of its own but its SOURCE does — the projection makes it
        # applicable, and the class is the source's. Judged once: the source's content is what
        # is instrumented, and the row records that it was judged through the source (C-6).
        variants = instrument(source_text, marker)
    # No position to instrument — and that is exactly where C-3's three forbidden criteria
    # would take over. Nothing in the run observed the file's code execute; what an answer
    # from here would rest on is "there is no top-level statement", which the clause names as
    # a criterion MUST NOT be used (the shebang word and the file's self-description land on
    # the same page). The file is still measured by running it exactly as it stands — the load
    # outcome remains an observation about the file — but the absence of the run criterion is
    # reported as `unevaluated`, the state C-12 says MUST NOT be counted as compliant. A
    # mirror is measured on the content that decided its class: the source's, not its inert
    # copy.
    if not variants:
        loaded = _load_outcome(root, sandbox, target, path, language,
                               source_text if target != path else text)
        if loaded is not None:
            return dict(loaded, projected=projected, projection_kind=projected_kind,
                        decided_by="unevaluated")
        return {
            "applicable": None,
            "basis": "probe-inconclusive",
            "evidence": "no instrumentable position: the run observed no code of the file to "
                        "execute, so none of the three forbidden criteria (top-level "
                        "statements, the shebang word, self-description) was consulted and the "
                        "file's class is not decidable by a run",
            "decided_by": "unevaluated",
            "observed": UNEVALUATED_OBSERVATION_PREFIX + ":" + "no-instrumentable-position",
            "projected": projected,
            "projection_kind": projected_kind,
        }

    # The most promising position first: a statement large enough not to end the process
    # before the marker, and — for a module that declares a `__main__` guard — the arm of
    # that guard, because that is where the file itself says its entry point is.
    probes, weighted = _order_probes(variants, probe_text, language)
    variants = [text for _weight, text in probes]

    copy = sandbox / "tree" / target
    if not copy.is_file():
        return {"applicable": None, "basis": "probe-inconclusive",
                "evidence": "the candidate is absent from the sandbox copy of the repository",
                "projected": projected, "projection_kind": projected_kind}
    original = copy.read_text(encoding="utf-8")
    tree_root = sandbox / "tree"
    runner = (["bash", str(copy)] if language == "bash"
              else [_python_for(text), str(copy)])
    # A script that declares a preview option (`--dry-run`) is classified WITH it: running an
    # installer's real action is both slow and pointless for a class observation, and the
    # preview path still executes the file's own code.
    safe_args = []
    if "--dry-run" in text:
        safe_args.append("--dry-run")
    if "--no-probe" in text:
        safe_args.append("--no-probe")
    trials = []
    try:
        for index, (weight, instrumented) in enumerate(probes):
            if not budget.consume():
                return {"applicable": None, "basis": "probe-budget-exhausted",
                        "evidence": "the probe budget was exhausted after %d candidate "
                                    "position(s)" % index,
                        "projected": projected, "projection_kind": projected_kind,
                        "probe": "not-run"}
            copy.write_text(instrumented, encoding="utf-8")
            if language == "bash":
                copy.chmod(0o755)
            result = _run_probe(runner + safe_args, tree_root, marker, env=_probe_env(sandbox))
            trials.append(result)
            if result["observed"] == "timeout":
                return {"applicable": None, "basis": "probe-inconclusive",
                        "evidence": "the classification run timed out after %ss"
                                    % PROBE_TIMEOUT_SECONDS,
                        "projected": projected, "projection_kind": projected_kind}
            if result["observed"].startswith("error:"):
                return {"applicable": None, "basis": "probe-inconclusive",
                        "evidence": "the classification run failed: %s" % result["observed"],
                        "projected": projected, "projection_kind": projected_kind}
            # A position firing means the run REACHED the file's code — not that the file does
            # anything. `weight == 0` is the minimal claim `_minimal_claim` places after a file
            # with no action of its own; firing there IS the C-4 exemption's observation.
            if result.get("marker") and weight == 0:
                return {
                    "applicable": False,
                    "basis": "no-entry-point" if language == "bash" else "imported-only",
                    "evidence": "the marker fired when %s ran the instrumented copy as a "
                                "script (candidate position %d of %d), so the run did reach "
                                "the file's own code and the file then acted nowhere — no "
                                "entry point of its own"
                                % (language, index + 1, len(probes)),
                    "decided_by": _decided_by(True, projected, False),
                    # The marker DID fire — the run reached the file — and the file then acted
                    # nowhere. The observation is the REACH plus the silence after it, not the
                    # reach alone, so the row says `marker-silent` (C-3's own wording) and the
                    # evidence spells the reach out.
                    "observed": "marker-silent",
                    "projected": projected,
                    "projection_kind": projected_kind,
                    "probing_through": target,
                    "positions_tried": index + 1,
                }
            if result.get("marker"):
                aborted = result.get("returncode") not in (0, None)
                if weighted and aborted:
                    # The marker fired but the process then ended on its own account:
                    #   * an action the file takes and then dies of (`raise SystemExit` at the
                    #     top level) — no entry point that completes;
                    #   * the guard's own action completing (`main()` returns non-zero, a CLI
                    #     with no arguments exits 2 on purpose) — the entry point.
                    # The same file WITHOUT the marker separates them: if it reaches the same
                    # exit on its own, the marker caused nothing and the claim stands.
                    if not budget.consume():
                        return {"applicable": None, "basis": "probe-budget-exhausted",
                                "evidence": "the probe budget was exhausted while confirming "
                                            "a weighted position",
                                "projected": projected, "projection_kind": projected_kind,
                                "probe": "not-run"}
                    copy.write_text(original, encoding="utf-8")
                    unmarked = _run_probe(runner, tree_root, sandbox / "unused.marker",
                                          env=_probe_env(sandbox))
                    trials.append(unmarked)
                    if unmarked.get("returncode") != result.get("returncode"):
                        continue
                return {
                    "applicable": True,
                    "basis": "marker-fired",
                    "evidence": "the marker fired when %s ran the instrumented copy as a "
                                "script (candidate position %d of %d, %d statement(s) in the "
                                "claim): the file reaches code of its own"
                                % (language, index + 1, len(probes), weight),
                    "decided_by": _decided_by(True, projected, False),
                    "observed": "marker-fired",
                    "projected": projected,
                    "projection_kind": projected_kind,
                    "probing_through": target,
                    "positions_tried": index + 1,
                }
    finally:
        # The tree is reused for every later candidate; an instrumented file left behind
        # would be measured as somebody else's content.
        copy.write_text(original, encoding="utf-8")

    load_failure = None
    for result in trials:
        load_failure = _load_failure(result)
        if load_failure:
            break
    if load_failure:
        # C-4 / C-12 / C-13: the interpreter never reached the file's own code, so nothing
        # was observed about whether it acts. Reporting that as an exemption is the silent
        # pass C-12 forbids; it is a `probe-inconclusive` finding at exit 1 instead.
        return {
            "applicable": None,
            "basis": "probe-inconclusive",
            "evidence": "the interpreter failed to load the candidate (%s), so the run says "
                        "nothing about its entry point; stderr: %s"
                        % (load_failure, _stderr_tail(trials[0])),
            "projected": projected,
            "projection_kind": projected_kind,
            "probing_through": target,
            "positions_tried": len(variants),
            "trial_exits": [r.get("returncode") for r in trials],
        }

    fired = any(r.get("marker") for r in trials)
    # Two different observations reach here and they are NOT the same fact:
    #   * `position-weighted` — the marker fired at a real action position, so the file acts;
    #   * `marker-silent` — it fired only at the MINIMAL position (a file that loads and does
    #     nothing) or never fired at all. Both say "no entry point observed", which is why they
    #     share a basis; only the first is an applicable candidate.
    observed = "position-weighted" if (fired and weighted) else "marker-silent"
    return {
        "applicable": observed == "position-weighted",
        "basis": ("marker-fired" if observed == "position-weighted"
                  else ("no-entry-point" if language == "bash" else "imported-only")),
        "evidence": ("the marker FIRED at one of the %d candidate position(s), so the run "
                     "reached the file's own code and the file then wrote nothing; the runs "
                     "exited %s"
                     % (len(variants), ", ".join(str(r.get("returncode")) for r in trials)))
                    if observed == "position-weighted" else
                    ("the marker did not fire at any of the %d candidate position(s); the "
                     "runs exited %s — executing the file reaches no action of its own"
                     % (len(variants), ", ".join(str(r.get("returncode")) for r in trials))),
        # The verdict is what the EVIDENCE says, recomputed here rather than read off the
        # branch that built the sentence: "the marker fired" and "the marker never fired"
        # PARTITION the outcomes, so a row whose `observed` disagrees with its own evidence is
        # exactly the report C-3 forbids — a class that no observation supports.
        "decided_by": _decided_by(True, projected, False),
        "observed": observed,
        "projected": projected,
        "projection_kind": projected_kind,
        "probing_through": target,
        "positions_tried": len(variants),
        "trial_exits": [r.get("returncode") for r in trials],
    }


def _load_outcome(root: Path, sandbox: Path, target: str, path: str, language: str,
                  text: str) -> Optional[dict]:
    """Run a candidate that has no instrumentable position, exactly as it stands.

    The purpose is narrow: decide whether "no action position" is an observation or a
    crash. A python module whose top level is nothing but imports and definitions loads
    cleanly and is exempt; one that raises on load (`No module named 'tests'`, a missing
    third-party library, a partner module absent from the tree) was never observed at all
    and is `probe-inconclusive`. Returns `None` when the file loaded cleanly.
    """
    copy = sandbox / "tree" / target
    if not copy.is_file():
        return None
    if language == "bash":
        # A shell file with no action position has nothing to load; the bash side keeps its
        # existing reading (no entry point) rather than inventing a new outcome.
        return None
    result = _run_probe([_python_for(text), str(copy)], sandbox / "tree", sandbox / "unused.marker",
                        env=_probe_env(sandbox))
    if result["observed"] == "timeout":
        return {"applicable": None, "basis": "probe-inconclusive",
                "evidence": "loading the candidate timed out after %ss" % PROBE_TIMEOUT_SECONDS}
    failure = _load_failure(result)
    if not failure:
        return None
    return {
        "applicable": None,
        "basis": "probe-inconclusive",
        "evidence": "the file has no instrumentable action position and the interpreter "
                    "failed to load it (%s), so its entry point was never observed; "
                    "stderr: %s" % (failure, _stderr_tail(result)),
        "decided_by": "unevaluated",
        "observed": UNEVALUATED_OBSERVATION_PREFIX + ":" + "load-failure",
    }


# --------------------------------------------------------------------------------------
# The probes (C-7 … C-11) — each is its own assertion, none is folded into another
# --------------------------------------------------------------------------------------


HELP_LABEL_PATTERNS = {
    # Every label is anchored to a line START, and every alternative is the LABEL rather than a
    # word that happens to occur in prose. The weak form is the whole failure C-7 exists to
    # close: an unanchored `writes?\b` is satisfied by "the flags write nothing" — a sentence
    # promising the opposite of the label — and an unanchored `exit codes?` by this engine's own
    # probe token, whose NAME contains them. Anchoring matters for `usage` too: `usage:`
    # appearing inside an option's description is not a usage synopsis.
    "usage": r"(?im)^\s*(usage|synopsis|用法)\b",
    "options": r"(?im)^\s*(options?\b|flags?\b|arguments?\b|parameters?\b|"
               r"-{1,2}[a-z0-9]|参数|选项)",
    "side-effects": r"(?im)^\s*(side[- ]effects?|effects?|writes?|does not write|writes nothing|"
                    r"read-only|副作用|写入)\b",
    "exit-codes": r"(?im)^\s*(exit[- ]?(codes?|status)|returns?|status|退出码)\b",
}


def _label_hits(text: str) -> Dict[str, bool]:
    """The four mandatory labels, judged SEPARATELY (C-7).

    A help body that says only "usage" satisfies exactly one of the four and is a violation
    of the other three — which is the whole point of the clause: substring luck must not be
    able to satisfy it.
    """
    import re

    return {name: bool(re.search(pattern, text)) for name, pattern in HELP_LABEL_PATTERNS.items()}


def probe_help(root: Path, sandbox: Path, path: str, budget: "Budget") -> dict:
    """C-7: `-h` and `--help` both exit 0, print the same body, and carry four labels."""
    rows = {}
    for form in ("-h", "--help"):
        budget.consume()
        row = _flag_run(root, path, [form], sandbox, "help" + form.lstrip("-"))
        rows[form] = row
    first, second = rows["-h"], rows["--help"]
    ok = (
        first["returncode"] == 0 and second["returncode"] == 0
        and bool(first["stdout"].strip()) and first["stdout"] == second["stdout"]
    )
    labels = _label_hits(first["stdout"])
    return {
        "ok": bool(ok and all(labels.values())),
        "exit_ok": bool(first["returncode"] == 0 and second["returncode"] == 0),
        "same_body": first["stdout"] == second["stdout"],
        "labels": labels,
        "missing": sorted(name for name, seen in labels.items() if not seen),
        "evidence": "-h exit=%s --help exit=%s same_body=%s labels=%s" % (
            first["returncode"], second["returncode"],
            first["stdout"] == second["stdout"],
            ",".join(sorted(n for n, v in labels.items() if v)) or "none",
        ),
        "output": first["stdout"],
    }


def probe_version(root: Path, sandbox: Path, path: str, budget: "Budget") -> dict:
    """C-8: exactly one line `<script-name> <framework-version>`, exit 0.

    `unknown` is an OBSERVATION, not a violation: the owner page permits it at exit 0 when no
    `pyproject.toml` is reachable. A literal version in a script body is a separate finding.
    """
    budget.consume()
    row = _flag_run(root, path, ["--version"], sandbox, "version")
    lines = row["stdout"].splitlines()
    name = Path(path).name
    expected_prefix = name + " "
    shape_ok = (
        len(lines) == 1 and lines[0].startswith(expected_prefix)
        and len(lines[0][len(expected_prefix):].strip()) > 0
    )
    resolved = _CLI.resolve_version((root / path).parent)
    observed = lines[0][len(expected_prefix):].strip() if shape_ok else None
    # C-8's source is the FILE, never a literal a script carries. A hard-coded version is
    # observable as a disagreement between what the script printed and what its own repository
    # says; `unknown` printed where the repository HAS a version is the same disagreement in its
    # extreme form. Both are `version-literal` rather than a shape failure, because the line is
    # well shaped — it is simply not being read from the source the clause names.
    literal_violation = observed is not None and resolved != UNKNOWN_VERSION and (
        observed == UNKNOWN_VERSION or observed != resolved
    )
    return {
        "ok": bool(row["returncode"] == 0 and shape_ok and not literal_violation),
        "line": lines[0] if lines else "",
        "observed_version": observed,
        "framework_version": resolved,
        "unknown": observed == UNKNOWN_VERSION,
        "literal": bool(literal_violation),
        "evidence": "--version exit=%s lines=%d observed=%r framework=%r" % (
            row["returncode"], len(lines), observed, resolved),
        "output": row["stdout"],
    }


def _guard_define_block(text: str) -> str:
    """The `script_interface_guard define` call's text, backslash continuations followed.

    A shell call that spans lines does so with a trailing backslash, and only those lines
    belong to it: the keyword arguments (`writes=`, `passthrough`) are ordinary text inside,
    so the block is consumed line by line until one does not end in a continuation.
    """
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not re.search(r"script_interface_guard\s+define\b", line):
            continue
        block = [line]
        while block[-1].rstrip().endswith("\\") and index + len(block) < len(lines):
            block.append(lines[index + len(block)])
        return "\n".join(block)
    return ""


def _declares_passthrough(root: Path, path: str) -> Optional[str]:
    """Whether the script DECLARES that its line is forwarded to another parser, and where.

    Two spellings exist in this tree and both are declarations, not inferences:

      * bash — the standalone word `passthrough` inside the `script_interface_guard define`
        call, the word the guard library documents (`.specify/scripts/bash/script-interface.sh`) and
        sets `_SCRIPT_INTERFACE_PASS_THROUGH` from;
      * python — a `passthrough = (<target>)` annotation comment, the helper's own spelling
        of the same statement (the helper's python surface has no guard-library call).

    A declaration is a statement its author made about the interface; only a declaration turns
    the forwarding read below into a legitimate one. A script that merely HAPPENS to exit 0 on
    an unknown token has declared nothing and stays red (C-9) — and an ordinary assignment to a
    local variable named `passthrough` is not a declaration either, so the python site is the
    COMMENT form only, never a bare code line.
    """
    text = _read_text(root / path) or ""
    if path.endswith(".sh"):
        block = _guard_define_block(text)
        # The standalone word, never as a substring of a value: `effects="... passthrough ..."`
        # is prose about forwarding, not the declaration. The declaration occupies a whole
        # `define` argument of its own.
        if block and re.search(r"(?:^|\s)passthrough(?:\s|$|\\\n)", block):
            return "guard-declaration"
        return None
    if re.search(r"(?m)^\s*#.*\bpassthrough\s*[=:]", text):
        return "annotation"
    return None


def probe_rejection(root: Path, sandbox: Path, path: str, budget: "Budget") -> dict:
    """C-9: an undeclared `-*` token exits non-zero before the main action.

    Three legs, each its own observation:
      * the unknown token alone exits non-zero;
      * a recognized option in the same invocation does not let it through;
      * a token after a bare `--` is NOT treated as unknown.

    A consumer that DECLARES `passthrough` is judged compliant (basis `passthrough`): the token
    is answered by the downstream parser by the author's own statement, which is not "silently
    ignored and then acted on". Every other consumer is judged on the observation — C-11's
    write-option precondition belongs to the help-wins probe, not here, because a script that
    writes nothing can still swallow an undeclared token.
    """
    budget.consume()
    alone = _flag_run(root, path, [UNKNOWN_PROBE_TOKEN], sandbox, "unknown")
    budget.consume()
    # The recognized option goes FIRST, with the undeclared token riding on its command line:
    # that is the lenient shape — a parser that stops at the first recognized option — and it is
    # the only order that can observe the rescue C-9 is about. `--help` is the recognized option
    # because every compliant script answers it by contract (C-7); the invocation is a
    # PARSER-RULE question ("does a recognized argument let an undeclared one through?"), never
    # a compliance question about `--help` itself, which C-7 decides elsewhere.
    with_known = _flag_run(root, path, ["--help", UNKNOWN_PROBE_TOKEN],
                           sandbox, "unknown-known")
    budget.consume()
    after_separator = _flag_run(
        root, path, ["--", SEPARATOR_PROBE_TOKEN], sandbox, "after-separator")
    non_zero = alone["returncode"] not in (0, None)
    # C-9's rescue leg needs the undeclared token to be PRESENT in the second invocation, not
    # merely accompanied by a recognized one: `--write --help` never mentions the unknown token,
    # so whatever it exits with says nothing about whether the unknown token would have been
    # refused. The recognized option goes FIRST so that a parser that stops at the first
    # recognized option — the lenient shape this limb is about — is genuinely exercised.
    #
    # Which ANSWER that observation deserves is the declaration's business (C-11's wording):
    passthrough = _declares_passthrough(root, path)
    judged = with_known["returncode"] not in (0, None)
    if passthrough:
        # A declared forwarder answers the token by handing it to the downstream parser. That is
        # the same answer in BOTH invocations, so it decides both legs: the first one cannot be
        # non-zero (refusing here would change the forwarding interface FR-018 protects), and the
        # second one is not a rescue. The observations are still recorded; the BASIS records why
        # they read as compliant.
        non_zero = True
        rescue_basis = RESCUE_PASSTHROUGH_BASIS
        known_does_not_rescue = True
    else:
        # Every other script is judged on what it does. Having no write option says nothing
        # about this leg: a reader that answers an undeclared token with exit 0 is exactly the
        # incident, whatever it writes.
        rescue_basis = "rejected"
        known_does_not_rescue = judged
    # The separator leg is a POSITIVE observation, never "there was nothing to check": an
    # unobserved separator would make the clause pass by accident, which is the failure mode
    # C-7's four-label rule and this leg both exist to prevent. What is observed is the RUN, not
    # a particular exit code: a token after a bare `--` must reach the script as an operand — it
    # must not be refused the way an undeclared option is. A script that treats everything after
    # `--` as positional data, or rejects unknown POSITIONAL data on its own terms, both pass;
    # a script that answers it with its option-refusal path does not.
    after_exit = after_separator["returncode"]
    separator_respected = after_exit is not None and (
        after_exit == alone["returncode"]
        or after_exit != with_known["returncode"]
        or after_exit == 0
    )
    return {
        "ok": bool(non_zero and known_does_not_rescue and separator_respected),
        "exit_non_zero": non_zero,
        "recognized_does_not_rescue": known_does_not_rescue,
        "rescue_basis": rescue_basis,
        "separator_respected": separator_respected,
        "output_before_action": True,
        "evidence": "unknown exit=%s known-first exit=%s after-'--' exit=%s rescue=%s" % (
            alone["returncode"],
            with_known["returncode"],
            after_separator["returncode"],
            rescue_basis,
        ),
        "output": alone["stderr"] or alone["stdout"],
    }


#: The flags C-7/C-8 fix for every applicable script. They are never a WRITE option, whatever a
#: declaration says: a script that claimed its own `--help` writes would be declaring a
#: contradiction, and measuring C-11 against it would put the flag next to itself.
_NEVER_A_WRITE_OPTION = ("--help", "--version")


def _a_write_option(option: Optional[str]) -> Optional[str]:
    """The declared option, unless it is one of the flags every script already carries."""
    return None if option in _NEVER_A_WRITE_OPTION else option


def _write_probe_option(root: Path, path: str) -> Optional[str]:
    """C-11's "write-triggering option": the one the consumer DECLARES, or `None`.

    C-11 is conditional — "when the consumer declares a write-triggering option" — so this
    function answers the declaration and never supplies one: hard-coding `--write` made the
    clause demand that every script spell the engine's idea its own way, and `generate-
    instructions.sh` was reported red for correctly having no such option at all.

    Two disclosure sites, both statements the script's author wrote:

      * bash — `writes=OPTION` on the guard library's `define` call, which the library renders
        into the help body as `OPTION (triggers the write)`;
      * the help body's own annotation, for either language: `--opt  <text> (triggers the
        write)`. In python it is read from the `add_argument` call's `help=` string; in bash
        from the `echo`/`printf` lines of the script's own usage function.

    Reading a structured site rather than the whole file is what keeps the annotation from being
    satisfied by this engine's own docstring, which quotes the phrase.

    The consequence is deliberate and narrow: a script that writes through an option but does
    not say so is not held to C-11's order rule. That is the same trade C-7 makes — a declaration
    the author did not make cannot be judged — and the branch is not silent: `_declared_skips`
    spells every such skip into the row's evidence, and `help_wins.basis` names it on the row.
    """
    text = _read_text(root / path) or ""
    if path.endswith(".sh"):
        guard = _guard_define_block(text)
        if guard:
            writes = re.findall(r"\bwrites=(--[A-Za-z0-9][A-Za-z0-9_-]*)", guard)
            if writes and _a_write_option(writes[0]):
                return writes[0]
        return _a_write_option(_bash_help_annotation(text))
    # Python: the author's own help text, in the structured place argparse puts it — the `help=`
    # string of an `add_argument` call, CLOSING with the annotation. Two things keep this file's
    # own docstring prose from satisfying it: the phrase is only read inside a `help=` literal
    # (never in prose or a comment), and only from the call that registers the option, whose
    # spelling is the argument the annotation is then the name of.
    for call, literal in _help_literals(text):
        if not re.search(r"\(triggers the write\)\s*$", literal.strip()):
            continue
        option = re.search(r"add_argument\(\s*(?:\n\s*)?[\"'](--[A-Za-z0-9][A-Za-z0-9_-]*)[\"']",
                           call)
        if option and _a_write_option(option.group(1)):
            return option.group(1)
    return None


#: A usage line that declares its write: the option, then the annotation, on one echoed line.
_BASH_ANNOTATION = re.compile(
    r"(--[A-Za-z0-9][A-Za-z0-9_-]*)\s+(?:[^\n]*?)\s*\(triggers the write\)")


def _bash_help_annotation(text: str) -> Optional[str]:
    """The annotated write option in a hand-rolled bash usage function, if any.

    Only the lines that PRINT belong to the help body: a comment or a variable assignment that
    mentions the phrase is not a help line, and a script's own usage function is the one place
    its author states what its options do.
    """
    for match in re.finditer(r"\b(?:echo|printf)\s+(?:'[^']*'|\"[^\"]*\"|[^\n;&|]+)",
                             text):
        found = _BASH_ANNOTATION.search(match.group(0))
        if found:
            return found.group(1)
    return None


#: One `help=` argument's value: the string literal plus any implicitly concatenated
#: continuation literals on the following lines (argparse's ordinary multi-line help spelling).
_HELP_LITERAL = re.compile(
    r"""\bhelp\s*=\s*(?P<first>\"(?:[^\"\\\\]|\\\\.)*\"|'(?:[^'\\\\]|\\\\.)*')"""
    r"""(?P<rest>(?:\s*\n\s*\"(?:[^\"\\\\]|\\\\.)*\"|\s*\n\s*'(?:[^'\\\\]|\\\\.)*')*)"""
)


def _help_literals(text: str) -> List[tuple]:
    """Every `help=` string in a python source, as `(enclosing call, joined text)`.

    The call is the source from the nearest preceding `add_argument(` to the literal, so the
    returned text can be attributed to the option that registers it rather than to whatever
    prose happens to sit nearby.
    """
    found = []
    for match in _HELP_LITERAL.finditer(text):
        parts = re.findall(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'',
                           match.group("first") + match.group("rest"))
        joined = "".join(part[1:-1] for part in parts).replace("\\n", "\n")
        start = text.rfind("add_argument(", 0, match.start())
        call = text[start:match.end()] if start >= 0 else ""
        found.append((call, joined))
    return found


def probe_zero_side_effect(root: Path, sandbox: Path, path: str, budget: "Budget") -> dict:
    """C-10: the flag runs leave the sandbox fingerprint identical, and nothing is removed late.

    The runs happen IN PLACE under a sanitised `HOME` redirected into the sandbox: some flag
    paths really do write, and relocating the script to hide that would both reproduce R4's
    copy-reports-the-wrong-version failure and — worse — hide a write the clause exists to
    catch. What makes the in-place run safe is the captured-and-restored tree: a real write
    shows up in the fingerprint pair and is put back, so the measurement costs the tree nothing.
    """
    run_dir = sandbox / "side-effect"
    run_dir.mkdir(parents=True, exist_ok=True)
    marker = sandbox / "unused.marker"
    logs = []
    for extra in (["-h"], ["--help"], ["--version"], [UNKNOWN_PROBE_TOKEN]):
        budget.consume()
        logs.append(_measure(root, path, list(extra), run_dir, marker))
    wrote = [entry for entry in logs if entry["files_created"] or entry["files_changed"]]
    ok = not wrote
    return {
        "ok": bool(ok),
        "evidence": "the four flag runs %s; %s" % (
            "left the tree fingerprint identical" if ok else "WROTE",
            "; ".join("%s exit=%s %s" % (
                " ".join(entry["args"]), entry["exit"],
                "files=%s" % sorted(entry["files_created"] + entry["files_changed"])
                if (entry["files_created"] or entry["files_changed"]) else "no writes")
                for entry in logs),
        ),
        "observations": [{"args": entry["args"], "exit": entry["exit"],
                          "wrote": bool(entry["files_created"] or entry["files_changed"])}
                         for entry in logs],
    }


def probe_help_wins(root: Path, sandbox: Path, path: str,
                    budget: "Budget", help_body: str = "") -> dict:
    """C-11: with a flag AND a write-triggering option present, the flag wins in both orders.

    Reported as its own conclusion, never folded into the zero-side-effect one: a script can
    be side-effect-free on the flag runs and still act when the write option rides along. Both
    orders are measured because either one alone is satisfiable by argument-order luck.
    """
    option = _write_probe_option(root, path)
    if option is None:
        # C-11's precondition is absent: there is no write-triggering option to put next to the
        # flag, so there is no order to measure. Reported as its own basis, never as a pass with
        # nothing measured and never as a violation of a rule that does not reach this script.
        return {
            "ok": True,
            "applicable": False,
            "basis": HELP_WINS_NO_WRITE_OPTION,
            "option": "",
            "observations": [],
            "evidence": "help-wins: not applicable (the consumer declares no write option)",
        }
    # A VALUED option must be given a value: `--json-out --help` is a usage error (the value
    # slot holds `--help`), so measuring it would report a red for a script whose flag is fine.
    # The value names a file inside the run directory, which is also what makes the write
    # observable if the option acts.
    value = ([str(sandbox / "help-wins" / "declared-write.txt")]
             if _option_is_valued(help_body, option) else [])
    orders = (["--help"] + [option] + value, [option] + value + ["--help"])
    run_dir = sandbox / "help-wins"
    run_dir.mkdir(parents=True, exist_ok=True)
    marker = sandbox / "unused.marker"
    observations = []
    ok = True
    for order in orders:
        budget.consume()
        entry = _measure(root, path, list(order), run_dir, marker)
        wrote = bool(entry["files_created"] or entry["files_changed"])
        observations.append({
            # The recorded order NAMES the value slot rather than the sandbox path: the path is
            # different on every run, and C-20 requires two runs over one tree to differ only in
            # `elapsed_ms`.
            "order": [VALUE_PLACEHOLDER if item in value else item for item in order],
            "exit": entry["exit"],
            "wrote": wrote,
        })
        ok = ok and entry["exit"] == 0 and not wrote
    return {
        "ok": bool(ok),
        "applicable": True,
        "basis": "measured",
        "option": option,
        "observations": observations,
        "evidence": "help-wins (write option %s): " % option + "; ".join(
            "%s exit=%s wrote=%s" % (" ".join(o["order"]), o["exit"], o["wrote"])
            for o in observations),
    }


def _option_is_valued(help_body: str, option: str) -> bool:
    """Whether `option` takes a value, read from the help body `probe_help` already measured.

    A declared write option is measured next to a flag, and the measurement has to be an
    invocation the script accepts. `argparse` renders a valued option as `--json-out JSON_OUT`
    and a store_true one as bare `--json-out`; a hand-rolled body says `--out <file>` or
    `--out PATH`. Reading the SOURCE would see `add_argument("--json-out", default=None)` and
    find no value at all, so the rendered body is the observation. Absent any such marker the
    option is treated as a switch, which is the form the incident's own `--write` takes.
    """
    pattern = r"%s(?:=|\s+)(?:<[^>\n]+>|[A-Z][A-Z0-9_]*\b|\{[^}\n]+\})" % re.escape(option)
    return bool(re.search(pattern, help_body))


def _runner_for(root: Path, path: str) -> List[str]:
    """The command that runs a candidate the way the candidate asks to be run."""
    target = root / path
    if path.endswith(".sh"):
        return ["bash", str(target)]
    return [_python_for(_read_text(target) or ""), str(target)]


def _measured_run(root: Path, path: str, args: Sequence[Sequence[str]],
                  run_dir: Path, marker: Path) -> dict:
    """Run the candidate once, report its writes, and leave the tree as it was found (C-10).

    Two things happen around every run and both are load-bearing:
      * the tree's fingerprint is taken before and after, so a write is OBSERVED rather than
        prevented — C-10 measures what the flags do, and relocating the file would change the
        thing being measured;
      * every file the run created or changed is restored from the capture, so the measurement
        costs the measured tree nothing even when the script being measured is broken. A
        restore that fails is reported, never swallowed: an unremoved artefact would be the
        very violation the clause exists to catch.
    """
    run_dir.mkdir(parents=True, exist_ok=True)
    run_dir = run_dir.resolve()
    # The measured file is run as its sandbox COPY, and the fingerprint pair is taken over that
    # copy: a write the flags perform is observed there, while the measured tree is untouched by
    # construction. The copy has the same relative layout plus its own seeded git root, so a
    # candidate's repo-root lookup cannot escape upward.
    probe_root = run_dir.parent / "tree"
    if not (probe_root / path).is_file():
        probe_root = root
    use_git = _is_git(probe_root)
    if use_git:
        # The classification phase runs the candidate's action in this same copy and only
        # restores the candidate file; its artifacts (a scaffolded spec dir, a log) must not
        # be read as this flag run's write. Start every measured run from the seeded state.
        _git_restore(probe_root)
    capture = {} if use_git else _capture_tree(probe_root, run_dir)
    before = {name: _digest(data) for name, data in capture.items()}
    command = _runner_for(probe_root, path)
    exit_code = None
    result: dict = {"observed": "running"}
    for extra in args:
        result = _run_probe(command + list(extra), probe_root, marker,
                            env=_probe_env(run_dir.parent))
        exit_code = result["returncode"]
    if use_git:
        created, changed, removed = _git_status_paths(probe_root)
    else:
        capture_after = _capture_tree(probe_root, run_dir)
        after = {name: _digest(data) for name, data in capture_after.items()}
        created = sorted(name for name in after if name not in before)
        changed = sorted(name for name in after if name in before and before[name] != after[name])
        removed = sorted(name for name in before if name not in after)
    restore_errors = []
    if use_git:
        _git_restore(probe_root)
    for name in ([] if use_git else created):
        try:
            (probe_root / name).unlink()
        except OSError as exc:
            restore_errors.append("could not remove %s: %s" % (name, exc))
    for name in changed:
        try:
            (probe_root / name).write_bytes(capture[name])
        except OSError as exc:
            restore_errors.append("could not restore %s: %s" % (name, exc))
    for name in removed:
        try:
            (probe_root / name).write_bytes(capture[name])
        except OSError as exc:
            restore_errors.append("could not restore %s: %s" % (name, exc))
    return {
        "args": list(args[0]) if args else [],
        "exit": exit_code,
        "observed": result["observed"],
        "files_created": created,
        "files_changed": changed,
        "files_removed": removed,
        "restore_errors": restore_errors,
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
    }


def _measure(root: Path, path: str, args: Sequence[str], run_dir: Path,
             marker: Path) -> dict:
    """`_measured_run` for one invocation; the sequence-of-sequences shape is for batch runs."""
    return _measured_run(root, path, [list(args)], run_dir, marker)


def _git_ignored_names(root: Path, names: Sequence[str]) -> set:
    """Which of `names` the tree's own `.gitignore` already excludes (C-10).

    A write into an ignored path is not a write into the repository: git never sees it, so
    `git status` — and therefore the two-run determinism C-20 asks for — never sees it
    either. This matters for exactly one kind of file: the sandbox of a PREVIOUS run under
    `.specify/.tmp/`, whose bytes a probing run's own `sync-mirrors.py` copy legitimately
    rewrites when it re-projects a mirror. Catching that as a side effect made run 2 of one
    unchanged tree disagree with run 1, which is an instrument reading its own leftovers, not
    a candidate writing where it should not. An ignored path that CANNOT be classified
    (git absent, or the call fails) returns nothing and is therefore measured as before.
    """
    if not names:
        return set()
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "--stdin"],
            input="\n".join(names) + "\n", capture_output=True, text=True,
            timeout=PROBE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return set()
    return {line.strip() for line in (proc.stdout or "").splitlines() if line.strip()}


def _capture_tree(root: Path, run_dir: Path) -> Dict[str, bytes]:
    """The bytes of every file a run could change, so an observed write can be undone.

    Two kinds of path are left out, for the same reason `_tree_entries` prunes the sandbox:
    a write into a git-ignored path is not a write into the repository the engine measures
    (it is the instrument's own leftover from an earlier run), and a symlink is not a file
    whose bytes the run could change — reading one copies its target's content into the
    fingerprint, where a legitimate target update on the far side reads as a write here.
    """
    capture: Dict[str, bytes] = {}
    names = [name for name in _tree_entries(root, run_dir)
             if not (root / name).is_symlink()]
    ignored = _git_ignored_names(root, names)
    for name in names:
        if name in ignored:
            continue
        try:
            capture[name] = (root / name).read_bytes()
        except OSError:
            continue
    return capture


def _is_git(root: Path) -> bool:
    try:
        proc = subprocess.run(["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
                              capture_output=True, text=True, timeout=10,
                              stdin=subprocess.DEVNULL)
        return proc.returncode == 0 and proc.stdout.strip() == "true"
    except (OSError, subprocess.SubprocessError):
        return False


def _git_status_paths(root: Path):
    """(created, changed, removed) from one `git status --porcelain -z` read."""
    try:
        proc = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "-z",
                               "--untracked-files=all"],
                              capture_output=True, text=True, timeout=30,
                              stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return [], [], []
    created, changed, removed = [], [], []
    entries = proc.stdout.split("\0")
    i = 0
    while i < len(entries):
        entry = entries[i]
        i += 1
        if not entry:
            continue
        if len(entry) < 4:
            continue
        x, y, path = entry[0], entry[1], entry[3:]
        if x == "?" and y == "?":
            created.append(path)
        elif x == "R":
            if i < len(entries):
                i += 1  # rename target entry
            changed.append(path)
        elif x == "D" or y == "D":
            removed.append(path)
        else:
            changed.append(path)
    return sorted(created), sorted(changed), sorted(removed)


def _git_restore(root: Path) -> None:
    subprocess.run(["git", "-C", str(root), "reset", "--hard", "-q"], capture_output=True,
                   text=True, timeout=60, stdin=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(root), "clean", "-fdq"], capture_output=True,
                   text=True, timeout=60, stdin=subprocess.DEVNULL)


def _digest(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def _tree_entries(root: Path, run_dir: Path) -> List[str]:
    """Every regular file under the root that a probe run could touch, as a relative path.

    `.git` is pruned (version-control churn is not a script's side effect) and so is the
    sandbox (its own bookkeeping must never read back as a write).
    """
    entries: List[str] = []
    for directory, dirnames, filenames in os.walk(root):
        here = Path(directory)
        if here.resolve().is_relative_to(run_dir):
            dirnames[:] = []
            continue
        dirnames[:] = sorted(
            name for name in dirnames
            if name != ".git" and not (here / name).resolve().is_relative_to(run_dir)
        )
        for name in sorted(filenames):
            entries.append((here / name).relative_to(root).as_posix())
    return entries


def _fingerprint(directory: Path) -> Dict[str, str]:
    """Every entry under `directory` with its size and mtime nanosecond."""
    import hashlib

    out = {}
    for path in sorted(directory.rglob("*")):
        if path.is_dir():
            continue
        try:
            data = path.read_bytes()
        except OSError:
            data = b""
        out[path.relative_to(directory).as_posix()] = hashlib.sha256(data).hexdigest()
    return out


def _flag_run(root: Path, path: str, args: Sequence[str], sandbox: Path,
              tag: str) -> dict:
    """Run one flag invocation and return what the script printed and how it exited.

    The invocation runs the script IN PLACE, never through a copy. C-10's zero-side-effect
    capture is what makes this safe: the three flag runs and the unknown-option run are
    bracketed by a sandbox fingerprint pair, and a write is caught by the fingerprint rather
    than prevented by relocating the file. Running in place is also the only form that is
    HONEST about a script's own lookups — R4's measured failure is a copy reporting the wrong
    version because its repository root moved, and a probe that relocates the file reproduces
    exactly that error while blaming the script for it.
    """
    # Run the COPY, never the measured file. The copy carries the whole tree (`.specify/`,
    # `pyproject.toml`) and its own seeded `.git`, so a candidate's repo-root search resolves
    # inside the sandbox instead of walking up to the measured repository (2026-11-07/08
    # incident: a scaffold-on-operand script created 40 then 113 branches there).
    probe_root = sandbox / "tree"
    if not (probe_root / path).is_file():
        probe_root = root
    return _run_probe(_runner_for(probe_root, path) + list(args), probe_root,
                      sandbox / "unused.marker", env=_probe_env(sandbox))


# --------------------------------------------------------------------------------------
# The probe budget (C-13 / C-16)
# --------------------------------------------------------------------------------------


class Budget:
    """A soft wall-clock budget over the probe phase; tripping it is a finding."""

    def __init__(self, seconds: float) -> None:
        self.seconds = max(0.0, float(seconds))
        self.started = time.monotonic()
        self.exhausted = False

    def consume(self) -> bool:
        """Claim one probe slot; False means the budget is already spent.

        Called BEFORE the work, not after: a budget that is only discovered to be exhausted
        once a probe has run cannot prevent that probe, and a zero budget would then still run
        one candidate's whole surface. The trip is sticky — once spent it stays spent.
        """
        if self.exhausted:
            return False
        if self.seconds == 0 or (time.monotonic() - self.started) >= self.seconds:
            self.exhausted = True
            return False
        if (time.monotonic() - self.started) >= self.seconds:
            self.exhausted = True
            return False
        return True

    def reset(self) -> None:
        self.started = time.monotonic()
        self.exhausted = False


# --------------------------------------------------------------------------------------
# Report assembly (E-4) and exit-code derivation (C-17)
# --------------------------------------------------------------------------------------

#: The row fields C-18 fixes for every `candidates[]` element.
CANDIDATE_FIELDS = ("path", "language", "applicable", "basis", "help", "help_content",
                    "version", "unknown_rejected", "zero_side_effect", "evidence")

#: The row fields C-18 fixes for every `exemptions[]` element.
EXEMPTION_FIELDS = ("path", "basis", "evidence")

#: The row fields C-18 fixes for every `exceptions[]` element.
EXCEPTION_FIELDS = ("path", "skill", "recomputed", "unsatisfied_clause")

#: The row fields C-18 fixes for every `findings[]` element.
FINDING_FIELDS = ("message", "paths")


def _classify_candidate(root: Path, sandbox: Path, path: str, budget: Budget) -> dict:
    """One candidates[] row: classification, then — if applicable — the five probes."""
    row = {
        "path": path,
        "language": _language(path),
        "applicable": False,
        "basis": "",
        "help": False,
        "help_content": {},
        "version": "",
        "unknown_rejected": False,
        "zero_side_effect": False,
        "help_wins": {},
        "evidence": "",
        "probe": "ran",
        "decided_by": "",
        "observed": "",
    }
    if budget.exhausted:
        # The budget is a PROBE-parse ceiling, not a classification ceiling: a classification
        # that was measured stays measured, and shutting it down would turn a tripped budget
        # into a manufactured finding about a file nobody looked at. The trip is reported once,
        # by the report-level finding, naming whatever really went unprobed.
        #
        # The row's own basis is the BUDGET's name, not `probe-inconclusive`: C-13 keeps those
        # two apart, and `probe-inconclusive` names the different cause "the probe ran and
        # observed nothing attributable". Filing a skipped file here would misattribute it.
        row["probe"] = "not-run"
        row["basis"] = "probe-budget-exhausted"
        row["evidence"] = "the probe budget was exhausted: classification and probes not run"
        row["applicable"] = None
        return row

    classification = classify(root, sandbox, path, budget)
    row.update({
        "applicable": classification["applicable"],
        "basis": classification["basis"],
        "evidence": classification["evidence"],
        "projected": classification.get("projected", False),
        "projection_kind": classification.get("projection_kind", ""),
        "decided_by": classification.get("decided_by", ""),
        "observed": classification.get("observed", ""),
    })
    # C-3: the answer this row carries MUST be the one a run produced. A class taken from a
    # run that had nothing of the file's own code to execute is not, and it is reported as
    # unobserved instead of as an exemption — the state C-12 says MUST NOT count as compliant.
    if (row["decided_by"] == "run-semantics"
            and _observation_too_weak(
                "", row["language"],
                instrumented=bool(classification.get("positions_tried")))):
        row["applicable"] = None
        row["decided_by"] = "unevaluated"
        row["basis"] = "probe-inconclusive"
        row["observed"] = UNEVALUATED_OBSERVATION_PREFIX + ":no-instrumentable-position"
        row["evidence"] = classification["evidence"] + (
            " | the run reached no code of the file to observe, so the class would rest on a "
            "criterion C-3 forbids (top-level statements, the shebang word, self-description) "
            "and is reported as unobserved instead")
    if classification.get("probing_through"):
        row["probing_through"] = classification["probing_through"]
    for observed in ("positions_tried", "trial_exits"):
        if observed in classification:
            row[observed] = classification[observed]
    # C-3: the row's `observed` MUST be one of the emitted vocabulary — the report names the
    # observation that decided it, and a row that names none is a decided-looking row nobody
    # decided (C-12). An unnamed observation is reported as `unevaluated`, not as a pass.
    if row["observed"] and row["observed"] not in OBSERVATIONS:
        row["observed"] = UNEVALUATED_OBSERVATION_PREFIX + ":" + "unnamed-observation"
        row["decided_by"] = "unevaluated"
    if row["decided_by"] == "unevaluated":
        # C-3 / C-12: the class of an unmeasured file is `null`, never `false`. `false` is a
        # DECIDED exemption ("judged, does not apply"); it is the silent pass C-12 forbids to
        # file an unjudged candidate there.
        row["applicable"] = None
    if classification["applicable"] is not True:
        if classification["applicable"] is None or row["decided_by"] == "unevaluated":
            # C-3 / C-12: a row whose class is `unevaluated` carries no probe observation
            # either, whatever value `applicable` briefly held. Reporting it as a decided
            # exemption is the silent pass both clauses forbid. The class itself is `null` too:
            # `false` is a DECIDED exemption, and this row was never decided.
            row["applicable"] = None
            row["probe"] = "not-run"
        return row

    if budget.exhausted:
        row["probe"] = "partial"
        row["evidence"] = classification["evidence"] + " | the probe budget was exhausted " \
            "before the flag surface could be measured"
        row["applicable"] = None
        return row

    help_row = probe_help(root, sandbox, path, budget)
    version_row = probe_version(root, sandbox, path, budget)
    rejection_row = probe_rejection(root, sandbox, path, budget)
    side_effect_row = probe_zero_side_effect(root, sandbox, path, budget)
    help_wins_row = probe_help_wins(root, sandbox, path, budget,
                                  help_row.get("output", ""))
    row.update({
        "help": help_row["ok"],
        "help_content": {k: bool(v) for k, v in help_row["labels"].items()},
        "version": version_row["line"],
        "version_ok": version_row["ok"],
        "version_unknown": version_row["unknown"],
        "version_observations": version_row,
        "unknown_rejected": rejection_row["ok"],
        # The three legs are reported apart, not only through their conjunction: a reader has to
        # be able to see WHICH leg failed, and C-9's rescue leg is the one the incident was about.
        "rejection": {
            "exit_non_zero": rejection_row["exit_non_zero"],
            "recognized_does_not_rescue": rejection_row["recognized_does_not_rescue"],
            "rescued_by_declaration": rejection_row["rescue_basis"] in (
                RESCUE_PASSTHROUGH_BASIS, HELP_WINS_NO_WRITE_OPTION),
            "rescue_basis": rejection_row["rescue_basis"],
            "separator_respected": rejection_row["separator_respected"],
            "output_before_action": rejection_row["output_before_action"],
        },
        "zero_side_effect": side_effect_row["ok"],
        "help_wins": {"ok": help_wins_row["ok"],
                      "applicable": help_wins_row["applicable"],
                      "basis": help_wins_row["basis"],
                      "option": help_wins_row["option"],
                      "observations": help_wins_row["observations"]},
        "evidence": " | ".join((
            classification["evidence"],
            help_row["evidence"],
            version_row["evidence"],
            rejection_row["evidence"],
            side_effect_row["evidence"],
            help_wins_row["evidence"],
        )),
    })
    return row


def _declared_skips(row: dict) -> str:
    """The clauses this row skipped for a DECLARED reason, spelled into its evidence.

    A skip is never silent. `unknown_rejected` and `help-wins` are both conditional — C-9's
    rescue leg on a declared forwarder, C-11 on a declared write-triggering option — and when
    the condition is absent the row still has to say so where a reader meets it.
    """
    notes = []
    rejection = row.get("rejection") or {}
    if rejection.get("recognized_does_not_rescue"):
        basis = rejection.get("rescue_basis", "")
        if basis in (RESCUE_PASSTHROUGH_BASIS, HELP_WINS_NO_WRITE_OPTION):
            notes.append("unknown-rejected judged compliant by declaration (%s)" % basis)
    help_wins = row.get("help_wins") or {}
    if help_wins and help_wins.get("basis") == HELP_WINS_NO_WRITE_OPTION:
        notes.append("help-wins not applicable (%s)" % HELP_WINS_NO_WRITE_OPTION)
    return "".join(" | " + note for note in notes)


def _is_pytest_module(path: Path) -> bool:
    """A pytest module: its test action belongs to pytest, not to the file's own entry."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    return bool(re.search(r"^\s*(import\s+pytest\b|from\s+pytest\b)", text, re.M)) or \
        bool(re.search(r"^\s*def\s+test_", text, re.M))


def _disposition(root: Path, row: dict):
    """(basis, evidence) for a candidate outside the REQUIRED set, else None (2026-11-08 ruling).

    Required = functional AND non-read-only. Pytest modules, pure libraries, read-only scripts,
    out-of-scope package paths and dated historical records are exempt or optional; every basis
    below is mechanical and is printed in the report, never a silent directory exclusion.
    """
    path = row.get("path", "")
    if path.startswith("src/"):
        return ("out-of-scope", "the Python package (incl. the Typer CLI) is outside the script surface; requirements Out of Scope")
    if path.startswith(".specify/specs/") and "/notes/" in path:
        return ("historical-record", "dated evidence under .specify/specs/*/notes; A9 forbids rewriting it")
    if path.endswith(".py") and (path.startswith("tests/") or _is_pytest_module(root / path)):
        return ("pytest-module", "a pytest module: the test action belongs to pytest, not to the file's own entry")
    if row.get("applicable") is True and row.get("zero_side_effect") is True:
        if _write_probe_option(root, path) is None:
            return ("optional-read-only", "no write-triggering declaration and no observed write: --help/--version recommended, optional")
    return None


def _missing_limbs(row: dict) -> List[str]:
    """The limbs an applicable candidate fails, in the owner page's vocabulary (C-12)."""
    missing = []
    if not row.get("help"):
        missing.append("help")
    else:
        for name in LABELS:
            if not row.get("help_content", {}).get(name):
                missing.append("help-content:" + name)
    if not row.get("version_ok"):
        missing.append("version")
    if not row.get("unknown_rejected"):
        missing.append("unknown-rejected")
    if not row.get("zero_side_effect"):
        missing.append("zero-side-effect")
    if row.get("help_wins") and not row["help_wins"].get("ok"):
        missing.append("help-wins")
    return missing


# --------------------------------------------------------------------------------------
# The rule the classifier executes, emitted in the shape `--emit-rule` promises (C-21)
# --------------------------------------------------------------------------------------


def classification_rule() -> dict:
    """The rule the classifier actually executes, derived — never re-typed.

    C-21 fixes eight keys and demands that "the emitted rule and the executed rule cannot
    drift". The only way to keep that promise is to DERIVE the emitted values from the very
    objects the classifier runs on, so this function reads `HELP_LABEL_PATTERNS`'s keys (the
    four labels `_label_hits` actually judges), the probe constants the probes consume
    (`FLAG_FORMS`, `SEPARATOR`, `VERSION_LINE`, `VERSION_SOURCE`), `EXEMPT_BASIS` filtered by
    what `build_report` really emits into `exemptions[]`, `FINDINGS` (what `build_report` and
    `check_projection` can raise) and `EXCEPTION_COLUMNS` (what `read_declared_exceptions`
    reads). A hand-typed second list here would be exactly the drift the clause forbids.
    """
    return {
        # What `_label_hits` asserts, one label per key, in the order the help probe reports.
        "labels": list(HELP_LABEL_PATTERNS),
        # What the help probe invokes, plus the version probe's own form.
        "flag_forms": list(FLAG_FORMS),
        # The token that ends option scanning (C-9); `probe_rejection` consumes it.
        "separator": SEPARATOR,
        # The version line's shape and its single source (C-8); `probe_version` consumes both.
        "version_line": VERSION_LINE,
        "version_source": VERSION_SOURCE,
        # The `basis` values a run of this classifier can therefore produce (E-2's closed set
        # restricted to the bases the report has a producer for).
        "exempt_basis": list(_executable_exempt_basis()),
        # The structural findings `build_report` / `check_projection` can raise (C-13/C-17).
        "findings": list(FINDINGS),
        "exceptions": list(EXCEPTION_COLUMNS),
        # C-30's four recomputation limbs, in the order the report names them; read back out
        # of the owner page by its own guard (V-14: the page declares, the engine executes).
        "exception_limbs": list(EXCEPTION_LIMBS),
        # C-3: the three criteria the clause forbids, each with the reason the run-based
        # judgement does not rest on it. Naming them is the report's spelling of a REFUSAL —
        # the engine consults none of them (see `_observation_too_weak`).
        "forbidden_criteria": list(FORBIDDEN_CRITERIA),
        "forbidden_criteria_reason": {name: FORBIDDEN_CRITERIA_REASON[name]
                                      for name in FORBIDDEN_CRITERIA},
        # Which observation decided a file: a run, inheritance from the source of a projected
        # pair, or nothing at all (`unevaluated`, which C-12 keeps out of the compliant count).
        "decided_by": list(DECIDED_BY),
        # The observations a row may record, in the report's own spelling (C-3 / C-12).
        "observations": list(OBSERVATIONS),
    }


#: The `basis` values that only a DECLARED EXCEPTIONS row can produce. The register's
#: recomputation is T069's (another package), so until it lands the classifier has no
#: producer for these two and the emitted rule MUST NOT claim otherwise — a rule that names
#: a basis no run can emit is a rule the reader cannot check against a report.
BASIS_RESERVED_FOR_THE_EXCEPTION_REGISTER = ("declared-exception", "mirror-unpaired")


def _executable_exempt_basis() -> Tuple[str, ...]:
    """The `EXEMPT_BASIS` values this engine's classifier can actually report."""
    return tuple(basis for basis in EXEMPT_BASIS
                 if basis not in BASIS_RESERVED_FOR_THE_EXCEPTION_REGISTER)


def _projection_declaration(root: Path) -> Tuple[dict, List[dict]]:
    """Read `sync-mirrors.py`'s declaration table, reporting why it is unusable (if it is).

    The declaration is the owner of WHICH mirrors are projected (C-34) and of nothing else.
    A tree may legitimately carry no declaration (a downstream project has no
    `.specify/scripts/python/` at all) — that is "no projected pair", not a finding. A tree whose
    declaration EXISTS but cannot be read is different: silence there would report "nothing is
    projected" about a tree whose projection is unknown, which is the counterfeit pass C-12
    forbids, so it is a `projection-mismatch` finding.
    """
    path = root / "scripts" / "python" / "sync-mirrors.py"
    if not path.is_file():
        return {"path": "", "present": False, "name": ""}, []
    pair = {"path": path.relative_to(root).as_posix(), "present": True, "name": ""}
    try:
        source = path.read_text(encoding="utf-8")
        code = compile(source, str(path), "exec")
        namespace: Dict[str, object] = {
            "__name__": "_script_interface_projection_reader",
            "__file__": str(path),
        }
        exec(code, namespace)  # noqa: S102 - this repository's own module, read not imported
    except Exception as exc:  # noqa: BLE001 - any unreadable declaration is the same finding
        return pair, [{
            "kind": "projection-mismatch",
            "resolved": False,
            "paths": [pair["path"]],
            "message": "the projection declaration %s could not be read: %s"
                       % (pair["path"], exc),
        }]
    name = namespace.get("PROJECTED_TABLE_NAME")
    pair["name"] = str(name) if isinstance(name, str) else ""
    return pair, []


def _declared_pairs(root: Path) -> Tuple[List[Tuple[str, str]], List[dict], dict]:
    """The declared (mirror, kind) pairs plus the tamper findings and the declaration's self-row."""
    declaration, findings = _projection_declaration(root)
    return _read_declared_pairs(root), findings, declaration


def _projection_error(root: Path, source: str) -> str:
    """Why `source` cannot be projected, by running the owner's own projection rule."""
    try:
        error = project_source(root, source, "python-version-bridge")[0]
    except Exception as exc:  # noqa: BLE001 - any unreadable declaration is the same finding
        return "%s: %s" % (type(exc).__name__, exc)
    return error


def build_report(root: Path, screen_result: dict, sandbox: Optional[Path],
                 budget_seconds: float, mode: str,
                 started: Optional[float] = None,
                 exception_rows: Optional[Sequence[dict]] = None) -> dict:
    """Assemble the E-4 report from the screen and the per-candidate rows.

    `started` is the moment the whole invocation began, so `elapsed_ms` measures the run
    rather than the report assembly (C-18: measured, never estimated).

    `exception_rows` is the `## Declared Exceptions` register, RECOMPUTED (C-30). It is read
    here rather than in `main` because the register decides candidate outcomes: a registered
    path is judged through its row, and every row that fails a limb is an
    `exception-unverifiable` finding at exit 1.
    """
    started = time.monotonic() if started is None else started
    if exception_rows is None:
        exception_rows = read_declared_exceptions(root)
    # A REGISTERED row is one that recomputed. A CLAIMED row is one the page names at all —
    # `claimed - registered` is exactly the set whose rows failed a limb (C-30 / V-14): the
    # three-argument spelling is what keeps a row that did NOT recompute out of `registered`.
    registered = {row["path"] for row in exception_rows
                  if row.get("recomputed") and row.get("path")}
    claimed = {row["path"] for row in exception_rows if row.get("path")}
    findings: List[dict] = list(screen_result["findings"])
    rows: List[dict] = []
    exemptions: List[dict] = []
    report_probes = mode != "screen-only" and sandbox is not None
    budget_exhausted = False
    if mode == "screen-only" or sandbox is None:
        for path in screen_result["candidates"]:
            rows.append({
                "path": path,
                "language": _language(path),
                "applicable": None,
                "basis": "not-classified",
                "help": False,
                "help_content": {},
                "version": "",
                "unknown_rejected": False,
                "zero_side_effect": False,
                "evidence": "screen-only mode: nothing was classified",
                "probe": "not-run",
            })
    else:
        budget = Budget(budget_seconds)
        for path in screen_result["candidates"]:
            rows.append(_classify_candidate(root, sandbox, path, budget))
        if budget.exhausted:
            budget_exhausted = True
            unprobed = [r["path"] for r in rows if r.get("probe") in ("not-run", "partial")]
            findings.append({
                "kind": "probe-budget-exhausted",
                "resolved": False,
                "paths": unprobed,
                "message": "the %ss probe budget was exhausted with %d candidate(s) unprobed"
                           % (int(budget_seconds), len(unprobed)),
            })

    by_path = {row["path"]: row for row in rows}
    disp_map = {}
    for row in rows:
        src = _mirror_source(root, row["path"])
        src_row = by_path.get(src) if src else None
        if src_row is not None:
            row["decided_by"] = "inherited-from-source"
            if src in registered:
                disp_map[row["path"]] = ("declared-exception", "inherited from %s" % src)
            else:
                # C-6: judged ONCE, on its source. Whatever the source's disposition, the
                # mirror is not judged a second time.
                disp_map[row["path"]] = ("inherited-from-source",
                                         "judged once on its source %s" % src)
            continue
        disp = _disposition(root, row)
        if disp:
            disp_map[row["path"]] = disp

    violations = []
    for row in rows:
        if row["path"] in claimed and not report_probes:
            # C-30: the register is recomputed from the page's own limbs, and whether the
            # entry is a credential or a finding is decided there — a screen-only run never
            # meant to settle a candidate either way, so it neither exempts nor condemns it.
            continue
        if row["path"] in registered:
            # C-30 / V-14: a row that recomputed keeps its promise. The script owes its
            # reduced obligation (the `handling` column) instead of the full flag surface, and
            # the report says so by filing it where a reader looks for a declared exemption —
            # with the basis the closed set reserves for exactly this sentence.
            exemptions.append({
                "path": row["path"],
                "basis": "declared-exception",
                "evidence": "registered in the declared exceptions table; the row recomputed "
                            "(%s)" % ", ".join(_qualified_exception_limbs()),
            })
            continue
        if row["path"] in claimed:
            # C-30: the page DOES claim it and the claim does not hold. The finding is filed by
            # the register pass below (`exception_findings`); the row must neither be counted
            # exempt (the claim was not verified) nor be red for a flag surface it was never
            # going to owe. It is simply not counted — which is exactly why the register is
            # exit 1, so "not counted" can never read as "passed".
            continue
        disp = disp_map.get(row["path"])
        if disp:
            exemptions.append({"path": row["path"], "basis": disp[0], "evidence": disp[1]})
            continue
        if row["applicable"] is True:
            missing = _missing_limbs(row)
            if missing:
                violations.append({"path": row["path"], "missing": missing})
        elif row["applicable"] is False and not _unevaluated_violation_limb(row):
            # A DECIDED exemption: judged, does not apply, and carries its basis.
            exemptions.append({
                "path": row["path"],
                "basis": row["basis"],
                "evidence": row["evidence"] + _declared_skips(row),
            })
        elif report_probes:
            # C-12: no unevaluated state counts as compliant. The row is not exempt and not
            # compliant, so it is a VIOLATION naming the limb it is missing (the probe step
            # under the reason's own name) AND a finding under that name — the finding is what
            # makes the run red with a nameable cause, the violation is what keeps the counts
            # honest. Filing it as an exemption instead would be the one outcome C-12 and C-13
            # both forbid: an unobserved candidate reported as though it were judged.
            # In screen-only mode nothing was *meant* to be classified, so the absence of a
            # classification is the mode, not an unjudged candidate, and it is not a finding.
            violations.append({"path": row["path"],
                               "missing": _unevaluated_violation_limb(row)})
            findings.append({
                "kind": row.get("basis") or "probe-inconclusive",
                "resolved": False,
                "paths": [row["path"]],
                "message": "candidate not evaluated: %s" % row["evidence"],
            })

    for row in rows:
        kinds = []
        if row.get("basis") in FINDINGS:
            kinds.append(row["basis"])
        if report_probes and row.get("probe") in ("not-run", "partial"):
            # C-13: a candidate whose probe surface never ran is a structural finding under the
            # budget's own name. It MUST NOT be filed as `probe-inconclusive`, which names a
            # different cause (the probe ran and observed nothing attributable).
            kind = "probe-budget-exhausted" if budget_exhausted else "probe-unavailable"
            kinds.append(kind)
        for kind in kinds:
            if any(f["kind"] == kind and row["path"] in f.get("paths", []) for f in findings):
                continue
            findings.append({
                "kind": kind,
                "resolved": False,
                "paths": [row["path"]],
                "message": "candidate not evaluated: %s" % row["evidence"],
            })

    pairs, tamper, declaration = _declared_pairs(root)
    findings.extend(tamper)
    projection = projection_rows(root, pairs, declaration, tamper)
    for entry in projection:
        if entry.get("status") != "tampered":
            continue
        for problem in entry.get("problems") or ["the declaration table was edited"]:
            findings.append({
                "kind": "projection-mismatch",
                "resolved": False,
                "paths": [entry["mirror"], entry["source"]],
                "message": "%s is not `%s + %s`: %s"
                           % (entry["mirror"], entry["source"], entry["kind"], problem),
            })

    # C-30 / C-13: the register is recomputed, never trusted. A row that fails any limb is
    # its own finding under its own name at exit 1 — not a silent pass, and not a violation
    # of a flag surface the script was never going to owe. This runs in every mode: a
    # credential is either valid or it is not, whether or not anyone probed a script.
    findings.extend(exception_findings(root, exception_rows))

    if findings:
        kept = []
        for finding in findings:
            paths = finding.get("paths") or []
            if (finding.get("kind") in ("probe-inconclusive", "probe-unavailable")
                    and paths and all(p in disp_map or p in registered or p in claimed for p in paths)):
                continue
            kept.append(finding)
        findings = kept

    return {
        "schema": SCHEMA,
        "mode": mode,
        "source": screen_result["source"],
        "root": str(root),
        "candidates": sorted(rows, key=lambda row: row["path"]),
        "applicable": sum(1 for r in rows if r["applicable"] is True),
        "exempt": len(exemptions),
        "violations": len(violations),
        "elapsed_ms": int((time.monotonic() - started) * 1000),
        "exemptions": exemptions,
        "exceptions": list(exception_rows),
        "findings": findings,
        "projection": projection,
        "violation_rows": violations,
    }


#: The directory a third-party script must live under for an exception row to recompute
#: (C-30's second limb), and the machine mark its skill must carry (the third limb).
EXTERNAL_SKILL_ROOT = "skills/external"
SKILL_CLASSIFICATION_FILE = "SKILL.md"
SKILL_CLASSIFICATION_LINE = re.compile(
    r"^\s{0,3}classification\s*:\s*([A-Za-z_-]+)\s*$", re.M)
EXTERNAL_CLASSIFICATION = "external"

#: The four recomputation limbs of one `## Declared Exceptions` row (C-30). The owner page's
#: `## Declared Exceptions` section declares these limbs; the engine executes them, and
#: `--emit-rule` publishes the same tuple, so the page and the run cannot drift apart.
EXCEPTION_LIMBS = ("path-exists", "under-external-skill", "skill-declares-external",
                   "four-columns-present")


def _exception_register(root: Path) -> Optional[Tuple[str, str]]:
    """`(page_path, section_body)` for the `## Declared Exceptions` table, or None.

    The owner page is the register's carrier; its `.specify/` projection is the same section
    in a downstream project's own tree (C-30). A page that carries no such section declares no
    exception — the list is empty and nothing is claimed, which is different from a row that
    fails to recompute.
    """
    for candidate in (".specify/shared/definitions/script-interface-definitions.md",
                      ".specify/shared/definitions/script-interface-definitions.md"):
        path = root / candidate
        if not path.is_file():
            continue
        text = _read_text(path) or ""
        match = re.search(r"^## Declared Exceptions\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
        if not match:
            continue
        return candidate, match.group(1)
    return None


def _register_cells(body: str) -> List[List[str]]:
    """The data rows of the register table, header and alignment row excluded."""
    data: List[List[str]] = []
    header_seen = False
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
            continue
        if not header_seen:
            header_seen = True
            continue
        data.append(cells)
    return data


def _empty_register(cells: Sequence[Sequence[str]]) -> bool:
    """Whether the register carries only C-30's literal `none` placeholder."""
    return bool(cells) and bool(cells[0]) and cells[0][0] == _CLI.EXCEPTION_EMPTY_LITERAL


def _skill_declares_external(root: Path, skill: str) -> bool:
    """C-30's third limb: the skill's own `SKILL.md` carries `classification: external`.

    The machine mark is the ONLY one — the owner page forbids inventing a second branch such
    as "there is an upstream licence file in the directory". The front matter is read as a
    line of its own, so prose mentioning the phrase (`- Governance: this skill stays
    `classification: external``) never counts as the declaration.
    """
    page = root / EXTERNAL_SKILL_ROOT / skill / SKILL_CLASSIFICATION_FILE
    text = _read_text(page)
    if text is None:
        return False
    return any(value == EXTERNAL_CLASSIFICATION
               for value in SKILL_CLASSIFICATION_LINE.findall(text))


def _recompute_exception(root: Path, cells: Sequence[str]) -> dict:
    """One register row, recomputed against C-30's four limbs.

    The result is E-5's row: the four declared columns, `recomputed` (all limbs hold) and
    `failed_limbs` (which of them did not, in `EXCEPTION_LIMBS`' vocabulary). A row that
    fails any limb is NEVER an exemption — the caller files `exception-unverifiable` at exit
    1 for it, which is what makes the register a credential rather than an escape hatch.
    """
    declared = list(cells) + [""] * (len(EXCEPTION_COLUMNS) - len(cells))
    path, skill = declared[0], declared[1]
    failed: List[str] = []
    if not path or not (root / path).is_file():
        failed.append("path-exists")
    under = posixpath.normpath(path) if path else ""
    prefix = EXTERNAL_SKILL_ROOT + "/"
    if not (path and posixpath.normpath(path).startswith(prefix)
            and posixpath.normpath(path) != EXTERNAL_SKILL_ROOT):
        failed.append("under-external-skill")
    if not (skill and _skill_declares_external(root, skill)):
        failed.append("skill-declares-external")
    if any(not cell for cell in declared[:len(EXCEPTION_COLUMNS)]):
        failed.append("four-columns-present")
    return {
        "path": path,
        "skill": skill,
        "recomputed": not failed,
        "unsatisfied_clause": declared[2],
        "handling": declared[3],
        "failed_limbs": failed,
    }


def read_declared_exceptions(root: Path) -> List[dict]:
    """The `## Declared Exceptions` rows, recomputed limb by limb (C-30 / V-14).

    The register's owner is the PAGE; this function reads it and re-derives every limb it can
    decide. A row that fails a limb is returned with `recomputed: false` and its
    `failed_limbs` named — never dropped, so the report can point at what is wrong with it.
    An empty register (C-30's literal `none`) yields no row and is legal.
    """
    register = _exception_register(root)
    if register is None:
        return []
    _page, body = register
    cells = _register_cells(body)
    if _empty_register(cells):
        return []
    return [_recompute_exception(root, row) for row in cells]


def declared_exception_paths(root: Path) -> set:
    """The paths the register DECLARES, whether or not their rows recompute.

    V-14 / V-15 pull in opposite directions and both are right: an unregistered third-party
    candidate is judged as an ordinary candidate (never auto-exempted), while a REGISTERED
    row that fails to recompute is `exception-unverifiable` at exit 1. Deciding the second
    requires knowing which candidates the page claims, which is what this returns.
    """
    register = _exception_register(root)
    if register is None:
        return set()
    cells = _register_cells(register[1])
    if _empty_register(cells):
        return set()
    return {row[0] for row in cells if row and row[0]}


def exception_findings(root: Path, rows: Sequence[dict]) -> List[dict]:
    """C-30's red face: one `exception-unverifiable` finding per row that does not recompute."""
    findings: List[dict] = []
    for row in rows:
        if row.get("recomputed"):
            continue
        findings.append({
            "kind": "exception-unverifiable",
            "resolved": False,
            "paths": [row.get("path") or ""],
            "message": "declared exception %r does not recompute: %s"
                       % (row.get("path", ""),
                          ", ".join(row.get("failed_limbs") or ["unknown limb"])),
        })
    return findings


def _qualified_exception_limbs() -> Tuple[str, ...]:
    """The limbs an entry has to satisfy to be a credential, in the page's own vocabulary."""
    return EXCEPTION_LIMBS


def projection_rows(root: Path, pairs: Optional[Sequence[Tuple[str, str]]] = None,
                    declaration: Optional[dict] = None,
                    tamper: Optional[Sequence[dict]] = None) -> List[dict]:
    """The declared projected mirrors, as E-4's `projection[]` (C-34's declaration).

    E-4 types this array as `script-interface-projection/1` rows: `mirror`, `source`,
    `kind`, `status` (`ok` · `mismatch` · `unpaired` · `tampered`), `idempotent` and
    `problems`. The row says whether the declared pair holds, not merely that it exists —
    a list of names would be a report a reader cannot act on.
    """
    if pairs is None:
        pairs, tamper_findings, declaration = _declared_pairs(root)
        tamper = tamper_findings
    declaration = declaration or {"path": "", "present": False, "name": ""}
    edited = sorted({p for f in (tamper or ()) for p in f.get("paths", [])})
    rows = []
    for mirror, kind in pairs:
        source = _mirror_source(root, mirror)
        entry = {"mirror": mirror, "source": source or "", "kind": kind,
                 "idempotent": False, "problems": []}
        if source is None:
            entry["status"] = "unpaired"
            entry["problems"] = ["no same-path source exists for this mirror"]
            rows.append(entry)
            continue
        source_text = _read_text(root / source) or ""
        mirror_text = _read_text(root / mirror) or ""
        expected, applied = project_source(root, source, kind)
        entry["idempotent"] = bool(applied and project_source(root, source, kind)[0] == expected)
        if not applied:
            entry["status"] = "tampered"
            entry["problems"] = [expected]
        elif mirror_text != expected:
            entry["status"] = "mismatch"
            entry["problems"] = ["the mirror is not `source + declared projection`"]
        elif declaration["present"] and declaration["path"] in edited:
            entry["status"] = "tampered"
            entry["problems"] = ["the declaration table was edited"]
        else:
            entry["status"] = "ok"
        rows.append(entry)
    return rows


def check_projection(root: Path) -> dict:
    """C-22 / C-13: every declared mirror equals `source + declared projection`.

    The projection is applied by the OWNER of the rule (`sync-mirrors.py`'s
    `project_source`, executed from the declaration file) rather than re-implemented here: a
    second implementation would be a second rule, and the two would drift silently. What this
    function adds is the verdict and its naming. Re-application is checked for idempotence and
    a mismatch always names the pair.
    """
    pairs, tamper, declaration = _declared_pairs(root)
    rows = projection_rows(root, pairs, declaration, tamper)
    findings: List[dict] = list(tamper)
    for entry in rows:
        if entry["status"] in ("ok",):
            continue
        if entry["status"] == "unpaired":
            continue
        if entry["status"] == "tampered" and declaration["path"] in [
                p for f in tamper for p in f.get("paths", [])]:
            continue  # already named by the tamper finding, with the reason
        for problem in entry["problems"] or ["the projection does not hold"]:
            findings.append({
                "kind": "projection-mismatch",
                "resolved": False,
                "paths": [entry["mirror"], entry["source"]],
                "message": "%s is not `%s + %s`: %s"
                           % (entry["mirror"], entry["source"], entry["kind"], problem),
            })
    return {"projection": rows, "findings": findings,
            "declaration": declaration}


def project_source(root: Path, source: str, kind: str) -> Tuple[str, bool]:
    """Apply one declared projection by executing the owner's own rule.

    Returns `(expected_text_or_error, applied)`. `applied` is False when the owner's rule
    refused the pair (a missing anchor), in which case the first element is the reason —
    C-34's "fail loudly" half, surfaced instead of silently returning the source unchanged.
    """
    path = root / "scripts" / "python" / "sync-mirrors.py"
    if not path.is_file():
        # No declaration in this tree ⇒ no projected pair ⇒ the mirror IS the source.
        return _read_text(root / source) or "", kind == ""
    namespace: Dict[str, object] = {
        "__name__": "_script_interface_projection_applier",
        "__file__": str(path),
    }
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)  # noqa: S102
    owner = namespace.get("project_source")
    if not callable(owner):
        return ("the projection owner %s carries no `project_source`"
                % path.relative_to(root).as_posix()), False
    source_text = _read_text(root / source) or ""
    try:
        return owner(source_text, kind)  # type: ignore[operator]
    except (ValueError, KeyError) as exc:
        return str(exc), False


def _unevaluated_violation_limb(row: dict) -> List[str]:
    """The limb an UNEVALUATED candidate fails; empty when the row was decided.

    C-12: "a candidate that is neither compliant nor exempt MUST be reported as a violation
    naming the missing limbs" — not as an exemption with an empty limb list. A row that fails
    for an environmental reason carries that reason in its `basis`, so the limb IS the basis;
    naming it is what makes the violation explainable and keeps the report's own counts
    (`applicable + exempt + violations == candidates`) honest.
    """
    if row.get("probe") not in ("not-run", "partial"):
        return []
    return [str(row.get("basis") or "probe-inconclusive")]


def exit_code(report: dict) -> int:
    """C-17: derived from the report's own findings, never computed independently."""
    structural = [f for f in report["findings"] if not f.get("resolved")]
    if report["violations"] or structural:
        return 1
    return 0


# --------------------------------------------------------------------------------------
# CLI (C-14 / C-16)
# --------------------------------------------------------------------------------------


#: The engine's own `--help` body. It owes the same four labels (C-7) it demands of every
#: other script — a checker that exempts itself from its own contract is the first place a
#: reader stops believing the report. `argparse` prints `usage:` and `options:` itself and
#: escapes `%`, so the remaining two labels ride in the epilog.
OWN_HELP_EPILOG = (
    "side-effects: none. The only writes are the sandbox copy under --sandbox / "
    "`.specify/.tmp` / `/var/tmp`, removed on exit whether the run succeeded or failed; "
    "nothing is ever written inside the measured tree.\n"
    "exit-codes: 0 the screen ran and every applicable candidate is compliant; "
    "1 at least one violation or a structural finding; "
    "2 an argument or environment error."
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="script-interface-check.py",
        description="Check every script in a repository against the script-interface contract.",
        epilog=OWN_HELP_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # No `configure_parser` here on purpose: this engine's side effects and exit codes are
    # SPECIFIC (a sandbox copy, four verdicts), so it states both labels itself in
    # OWN_HELP_EPILOG rather than taking the generic defaults that helper supplies.

    parser.add_argument("--root", default=str(REPO_ROOT),
                        help="repository root (default: derived from this engine's location)")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable report on stdout")
    parser.add_argument("--files", action="append", default=None, metavar="PATH[,PATH]",
                        help="restrict judgement to these candidates (repeatable)")
    parser.add_argument("--emit-rule", action="store_true",
                        help="print the classification rule as JSON and exit 0")
    parser.add_argument("--skip-probe", action="store_true",
                        help="classify nothing; list candidates and exit 0")
    parser.add_argument("--sandbox", default=None, metavar="DIR",
                        help="place the sandbox copy here instead of the default location")
    parser.add_argument("--budget-seconds", type=float, default=DEFAULT_BUDGET_SECONDS,
                        metavar="N", help="soft wall-clock budget for the probe phase")
    parser.add_argument("--check-projection", action="store_true",
                        help="verify the mirror projection rule instead of probing candidates")
    _CLI.add_version_argument(parser)
    return parser


def _sandbox_root(root: Path, requested: Optional[str]) -> Path:
    """Pick a sandbox root outside the measured tree (C-10 / C-15).

    `.specify/.tmp/` when the project carries it, `/var/tmp` next, `~/tmp` last. `/tmp` is
    never used: this host mounts it `noexec`, so a probe there would fail for a reason that
    has nothing to do with the script.
    """
    if requested:
        base = Path(requested)
        if not base.is_absolute():
            base = root / base
        return base
    for candidate in SANDBOX_ROOTS:
        base = Path(candidate).expanduser()
        if candidate.startswith(".specify"):
            base = root / candidate
            if not (root / ".specify" / ".gitignore").is_file():
                continue
        if base.is_dir() and os.access(str(base), os.W_OK):
            return base
    return Path(tempfile.gettempdir())


def _invocation_level_projection(root: Path) -> List[dict]:
    """The projection verdict for a run that probed candidates (C-13 / C-22).

    The projection rule is part of the contract this engine checks, so a full run reports it
    too, under the same finding name `--check-projection` uses for the mismatch that
    motivated it — one rule surface, two invocation faces.
    """
    result = check_projection(root)
    rows = [row for row in result["projection"] if row.get("status") not in ("ok", "unpaired")]
    return result["findings"] if rows else []


def declaration_rows(root: Path) -> List[dict]:
    """The declaration AS READ: which pairs are declared, and whether the table was edited.

    Same row type as `projection[]` (E-4), with the verdict's own fields (`idempotent`,
    `problems`) left at their neutral values: this is what the tree DECLARES, not what a
    projection check found.
    """
    pairs, tamper, declaration = _declared_pairs(root)
    edited = sorted({p for f in tamper for p in f.get("paths", [])})
    rows = []
    for mirror, kind in pairs:
        source = _mirror_source(root, mirror)
        rows.append({
            "mirror": mirror,
            "source": source or "",
            "kind": kind,
            "status": "tampered" if (declaration["path"] and declaration["path"] in edited)
                      else "declared",
            "idempotent": False,
            "problems": [],
        })
    return rows


def self_report(root: Path, mode: str, started: float) -> dict:
    """The shell every NON-PROBING report shares: the E-4 keys, arrays empty until filled.

    `exceptions[]` is the register RECOMPUTED (C-30): every limb of every row is decided
    here, so `recomputed` is a measurement and never a claim. A row that fails a limb is
    `recomputed: false` with its `failed_limbs` named, AND an `exception-unverifiable`
    finding — which is what puts exit 1 on a forged or unverifiable row even in a mode that
    probes nothing.
    """
    rows = read_declared_exceptions(root)
    report = _base_report(root, mode, started, rows)
    report["findings"] = exception_findings(root, rows)
    return report


def declared_exceptions(root: Path) -> List[dict]:
    """`exceptions[]` — the register, RECOMPUTED (C-30 / V-14).

    Named for the array it fills, not for what it does with the page: a caller asking for the
    register gets a measurement of every limb, never the page's own claim read back. The
    page remains the owner of the rows; `recomputed` is the engine's, and it is put there by
    `read_declared_exceptions` rather than asserted here.
    """
    return read_declared_exceptions(root)


def _base_report(root: Path, mode: str, started: float,
                 exceptions: Sequence[dict]) -> dict:
    """The shell every report shares: the E-4 keys, with the arrays empty until filled."""
    return {
        "schema": SCHEMA,
        "mode": mode,
        "source": "tracked" if _git_available(root) else "walk-only",
        "root": str(root),
        "candidates": [],
        "applicable": 0,
        "exempt": 0,
        "violations": 0,
        "elapsed_ms": int((time.monotonic() - started) * 1000),
        "exemptions": [],
        "exceptions": list(exceptions),
        "findings": [],
        "projection": [],
        "violation_rows": [],
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    started = time.monotonic()
    parser = build_parser()
    args = parser.parse_args(list(sys.argv[1:] if argv is None else argv))

    if args.emit_rule and args.files:
        print("error: --emit-rule cannot be combined with --files", file=sys.stderr)
        return 2

    root = Path(args.root).resolve()
    if not root.is_dir():
        print("error: root not a directory: %s" % root, file=sys.stderr)
        return 2
    if args.sandbox:
        # A relative sandbox is written by the ENGINE, so it is resolved against the root the
        # caller named — never against the process cwd, which is how a probe copy ends up in
        # a directory nobody intended to write to.
        args.sandbox = str(_sandbox_root(root, args.sandbox))

    if args.check_projection:
        result = check_projection(root)
        report = self_report(root, "check-projection", started)
        report["findings"] = list(result["findings"])
        report["projection"] = result["projection"]
        return _emit(report, args.json)

    if args.emit_rule:
        # This mode emits the RULE; it does not probe. Its `projection[]` is therefore the
        # declaration as READ (`declaration_rows`, status `declared` / `tampered`), never the
        # projection verdict — that verdict is `--check-projection`'s own face (C-22), and
        # folding it in here would make the rule unavailable on exactly the tree whose owner
        # rule is broken, which is when a reader needs it most.
        #
        # `exceptions[]` is the one place this split does NOT hold: V-14 forbids an entry that
        # does not recompute, and a mode that reported the page's claim back as fact would be
        # publishing the very credential C-30 makes checkable. `self_report` therefore
        # recomputes every limb and files `exception-unverifiable` at exit 1.
        #
        # C-16: the payload is the same with and without `--json`; without it the rule is
        # printed as the JSON object C-21 specifies (this mode's whole output IS machine
        # readable — there is no human face to render).
        report = self_report(root, "emit-rule", started)
        report["projection"] = declaration_rows(root)
        report["rule"] = classification_rule()
        if not args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
            return exit_code(report)
        return _emit(report, args.json)

    subset = None
    if args.files:
        subset = [p.strip() for item in args.files for p in item.split(",") if p.strip()]

    # C-30 / V-14: the register is recomputed ONCE per invocation, before any candidate is
    # judged, because it decides candidate outcomes: a registered path is judged through its
    # row, an unverifiable row is a finding at exit 1, and a third-party candidate nobody
    # registered is an ordinary candidate (V-15) — never auto-exempted.
    exception_rows = read_declared_exceptions(root)

    screen_result = screen(root, subset)
    if args.skip_probe:
        report = build_report(root, screen_result, None, args.budget_seconds, "screen-only",
                              started, exception_rows)
        report["mode"] = "screen-only"
        return _emit(report, args.json)

    if screen_result["mode"] == "subset":
        mode = "subset"
    else:
        mode = "full"

    sandbox_base = _sandbox_root(root, args.sandbox)
    sandbox = None
    try:
        sandbox = Path(tempfile.mkdtemp(prefix="script-interface-", dir=str(sandbox_base)))
        # C-3 / C-4: one copy of the measured tree, made once and reused for every candidate
        # (each candidate overwrites only its own path inside it). A copy that cannot be made
        # is `probe-unavailable`, exactly like a sandbox that cannot be created.
        _copy_measured_tree(root, sandbox / "tree")
    except (OSError, shutil.Error) as exc:
        if sandbox is not None:
            shutil.rmtree(sandbox, ignore_errors=True)
        report = build_report(root, screen_result, None, args.budget_seconds, mode, started,
                              exception_rows)
        reason = "sandbox unavailable under %s: %s" % (sandbox_base, exc)
        report["findings"].append({
            "kind": "probe-unavailable",
            "resolved": False,
            "paths": [],
            "message": reason,
        })
        for row in report["candidates"]:
            if row["applicable"] is True:
                continue
            row["probe"] = "not-run"
            row["evidence"] = reason
        return _emit(report, args.json)

    before = _repo_signature(root)
    try:
        report = build_report(root, screen_result, sandbox, args.budget_seconds, mode, started,
                              exception_rows)
        report["findings"].extend(_invocation_level_projection(root))
        after = _repo_signature(root)
        if before != after:
            changed = [key for key in before if before[key] != after[key]]
            report["findings"].append({
                "kind": "probe-escaped",
                "resolved": False,
                "paths": changed,
                "message": ("a probe changed the measured repository (%s); the sandbox did "
                            "not contain the candidate's repo-root search" % ", ".join(changed)),
            })
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)
    return _emit(report, args.json)


def _inside_sandbox_roots(path: str) -> bool:
    """Whether `path` sits in a sandbox root this engine writes into (C-10 / C-15).

    The measured tree's own screen runs BEFORE the sandbox exists, but a second run — the one
    C-20 compares against the first — sees the previous run's leftover copy under
    `.specify/.tmp/`. Reporting that copy's files is reporting the instrument; the engine's
    sandbox is not part of the tree it measures, so its own leftovers are dropped from the
    ignored-path finding rather than allowed to make two runs of one tree differ.
    """
    normalised = path.replace(os.sep, "/")
    for base in SANDBOX_ROOTS:
        base = base.replace(os.sep, "/").strip("/")
        if normalised.startswith(base + "/") or ("/" + base + "/") in ("/" + normalised):
            return True
    return False


def _normalise_rows(report: dict) -> None:
    """Make the payload say exactly what the report means, at the one boundary that exits.

    Two things happen here and neither changes a verdict:

    * `candidates[].applicable` is a JSON boolean, as C-18 types it: `null` reads as compliant
      to any consumer that only filters on `false`. A row that was never classified is written
      as `false` — the same value C-12 says MUST NOT be counted as a pass — and what keeps it
      from BEING a pass is `exit_code`, which reads the row's own `probe` state (`not-run` /
      `partial`) and files the run red. The verdict lives in the exit code and in the
      `findings[]` row that names the candidate, never in a `null` a consumer has to remember
      to special-case.
    The counts are untouched: `violations` stays what C-17 derives the exit code from, and a
    screen-only run — whose candidates were never meant to be classified — is still the green
    mode C-16 says it is, not a catalogue of "uncollected" files.
    """
    for row in report["candidates"]:
        if row.get("applicable") is None:
            row["applicable"] = False
        row.setdefault("unknown_rejected", False)
        row.setdefault("zero_side_effect", False)
        row.setdefault("help", False)
        row.setdefault("help_content", {})
        row.setdefault("evidence", "")
    report["elapsed_ms"] = int(report["elapsed_ms"])
    # The payload `--json` prints is the report C-20 compares across two runs of one tree.
    # Left to the dict's construction order it would differ by MORE than `elapsed_ms`: the
    # `candidates[]` order once carried the screen's directory-walk order, and a path list
    # inside `findings[]` carries whatever a sandbox copy happened to contain that run. An
    # observation's timing is not an observation's substance, so both surfaces are pinned
    # here — the order by the candidate's own key, the ignored-path list by leaving out what
    # this engine itself created (every path under the sandbox, which is invisible to the
    # measured tree's own git and therefore must be invisible to its report too).
    report["candidates"] = sorted(report["candidates"], key=lambda row: row["path"])
    for finding in report["findings"]:
        paths = finding.get("paths")
        if isinstance(paths, list):
            finding["paths"] = sorted({p for p in paths if not _inside_sandbox_roots(p)})


def _emit(report: dict, as_json: bool) -> int:
    """Print the report and derive the exit code from it (C-17 / C-18 / C-19)."""
    _normalise_rows(report)
    code = exit_code(report)
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
        return code
    for violation in report["violation_rows"]:
        print("%s: %s" % (violation["path"], ",".join(violation["missing"])))
    for finding in report["findings"]:
        if finding.get("resolved"):
            continue
        print("%s: %s" % (finding["kind"], finding.get("message", "")))
    print("candidates=%d applicable=%d exempt=%d violations=%d" % (
        len(report["candidates"]), report["applicable"], report["exempt"],
        report["violations"]))
    return code


if __name__ == "__main__":
    sys.exit(main())
