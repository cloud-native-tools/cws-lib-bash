#!/usr/bin/env python3
"""integrate-lines.py — executable integration coordinator for 064.

Executes the WI-14 per-line sequence for every runnable entry of
`integration-plan`: rebase onto the trunk -> quality gate -> merge ->
integration-record -> archive-runtime -> `git worktree remove` (never --force).
Mirrors run once per batch, after all lines, never per line (WI-11).

The quality gate defaults to the closure checker (`closure-acceptance-check.py`,
081 / GW-03): the judgement runs at the **feature line's closure** — one line
carries a feature's whole slice set, so this step judges once per line and never
per slice merge; slice merges are the review gate's. The spec directory is read
from the registry row, never inferred from the branch: the line's `branch` yields
the feature id (its leading three digits), `.specify/features.md` under the
line's worktree yields the `Spec Path` cell for that id, and the directory is that
cell joined to the worktree (the gate runs with `cwd` = the worktree). A branch
without a feature id, a missing registry row, an empty or `-` `Spec Path` cell and
a resolved directory that does not exist are input errors — recorded as
`closure-input-error` while the line stays `completed`, never silently skipped and
never replaced by an invented `.specify/specs/<branch>`. Only the checker's exit 1
(a `block`) records `closure-blocked` and lands the line `blocked`; the failed
result is recorded **while the line is still `completed`**, because
`integration-record` refuses anything else, and only then does the transition
follow. `--gate-cmd` keeps overriding the command, and a caller-supplied gate keeps
its own historical `quality-gate` reason — it is not the closure verdict, so it
must not borrow the closure vocabulary.

Stdlib only.  Exit codes: 0 all merged, 2 usage/validation, 3 one or more
lines failed or the batch mirror failed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_FAILED = 3
SKILL_SCRIPTS = Path(__file__).resolve().parent

CHECKER_REL = ".specify/scripts/python/closure-acceptance-check.py"
FEATURES_REL = Path(".specify") / "features.md"
FEATURE_ID_RE = re.compile(r"^(\d{3})")
#: Cells that carry no content; a dash is how the registry spells "nothing here".
EMPTY_CELLS = ("", "-", "--", "—", "–")

REASON_CLOSURE_BLOCKED = "closure-blocked"
REASON_CLOSURE_INPUT_ERROR = "closure-input-error"
REASON_QUALITY_GATE = "quality-gate"


class GateInputError(Exception):
    """The feature line's spec directory cannot be resolved. Exit-2 class (GW-03)."""


def run(cmd, cwd=None, env=None):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)


def git(repo: Path, *args: str):
    return run(["git", "-C", str(repo), *args])


def engine(reg: Path, action: str, *args: str):
    cmd = [
        sys.executable, str(SKILL_SCRIPTS / "line-registry.py"),
        "--action", action, *args,
    ]
    env = os.environ.copy()
    env["SPECIFY_LINE_REGISTRY_DIR"] = str(reg)
    proc = run(cmd, env=env)
    if proc.returncode != 0:
        raise RuntimeError(
            f"engine {action} failed rc={proc.returncode}: {proc.stdout.strip()} {proc.stderr.strip()}"
        )
    return json.loads(proc.stdout)


def read_entry(reg: Path, line_id: str) -> dict:
    return json.loads((reg / f"{line_id}.json").read_text(encoding="utf-8"))


def git_path_exists(repo: Path, marker: str) -> bool:
    proc = git(repo, "rev-parse", "--git-path", marker)
    if proc.returncode != 0:
        return False
    path = Path(proc.stdout.strip())
    if not path.is_absolute():
        path = repo / path
    return path.exists()


def _result(line_id: str, status: str, **extra) -> dict:
    payload = {"line_id": line_id, "status": status, "archive_calls": 0}
    payload.update(extra)
    return payload


def _record_failed(reg: Path, line_id: str, reason: str) -> None:
    engine(reg, "integration-record", "--line-id", line_id, "--result", "failed",
           "--reason", reason)


def _mark_retained(reg: Path, line_id: str) -> None:
    engine(reg, "update", "--line-id", line_id, "--worktree-retained", "true")


# ---------------------------------------------------------------- the closure gate (GW-03)


def feature_id_of(branch: str) -> str:
    """The feature id is the branch's leading three digits — nothing else infers it."""
    match = FEATURE_ID_RE.match(branch or "")
    if not match:
        raise GateInputError(
            "branch %r carries no leading three-digit feature id (line branch)" % (branch,)
        )
    return match.group(1)


def registry_spec_path_cell(registry: Path, feature_id: str) -> str:
    """The `Spec Path` cell of the registry row whose `ID` is the feature id."""
    if not registry.is_file():
        raise GateInputError("feature registry not found: %s" % registry)
    header = None
    for raw in registry.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            header = None
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if all(set(cell) <= set("-: ") for cell in cells):
            continue  # the separator row
        if "ID" not in header or "Spec Path" not in header:
            continue
        if len(cells) <= max(header.index("ID"), header.index("Spec Path")):
            continue
        if cells[header.index("ID")] != feature_id:
            continue
        return cells[header.index("Spec Path")]
    raise GateInputError(
        "no registry row with ID=%r in %s" % (feature_id, registry)
    )


def resolve_spec_dir(entry: dict, worktree: Path) -> Path:
    """The feature line's spec directory: registry row → `Spec Path` cell → the worktree."""
    line_id = entry.get("line_id")
    feature_id = feature_id_of(entry.get("branch") or "")
    cell = registry_spec_path_cell(worktree / FEATURES_REL, feature_id)
    if cell.strip() in EMPTY_CELLS:
        raise GateInputError(
            "registry row ID=%s carries an empty Spec Path cell (line %s)"
            % (feature_id, line_id)
        )
    candidate = Path(cell.strip())
    if not candidate.is_absolute():
        # The gate runs with cwd = the worktree, so a repository-relative cell is joined to the
        # worktree — never to the driver's own directory.
        candidate = worktree / candidate
    spec_dir = candidate if candidate.is_dir() else candidate.parent
    if not spec_dir.is_dir():
        raise GateInputError(
            "spec directory not found for feature %s: %s (line %s)"
            % (feature_id, spec_dir, line_id)
        )
    return spec_dir


def build_gate_cmd(worktree: Path, spec_dir: Path) -> str:
    """The checker invocation, spelled the way the other two call sites spell it."""
    relative = os.path.relpath(spec_dir, worktree)
    return "python3 %s --spec-dir %s" % (CHECKER_REL, shlex.quote(relative))


def _quality_gate(reg: Path, wt: Path, entry: dict, gate_cmd: str,
                  closure_gate: bool):
    """The one gate execution site. Returns a failed result, or None when the gate passes."""
    gate = run(["bash", "-c", gate_cmd], cwd=wt)
    if gate.returncode == 0:
        return None
    line_id = entry["line_id"]
    detail = (gate.stdout + gate.stderr).strip()[-2000:]
    if closure_gate and gate.returncode == 1:
        # `block` at the feature line's closure. The order is a constraint, not a style:
        # `integration-record` refuses a line that is not `completed`, so the failed result is
        # recorded while the line is still completed — which also clears `merge_ready` — and the
        # transition to `blocked` follows it. Marking first loses both the reason and the result.
        _record_failed(reg, line_id, REASON_CLOSURE_BLOCKED)
        engine(reg, "update", "--line-id", line_id, "--state", "blocked",
               "--reason", REASON_CLOSURE_BLOCKED)
        return _result(line_id, "failed", reason=REASON_CLOSURE_BLOCKED, detail=detail)
    reason = REASON_CLOSURE_INPUT_ERROR if closure_gate and gate.returncode == 2 else REASON_QUALITY_GATE
    # Exit 2 is an input error, not a quality failure: record the distinct reason and leave the
    # line's state alone — it is neither marked `blocked` nor moved anywhere else.
    _record_failed(reg, line_id, reason)
    return _result(line_id, "failed", reason=reason, detail=detail)


def integrate_line(repo: Path, trunk: str, reg: Path, archive: Path, entry: dict,
                   gate_cmd: str | None) -> dict:
    line_id = entry["line_id"]
    worktree = entry.get("worktree_path")
    if not worktree:
        _record_failed(reg, line_id, "missing-worktree")
        return _result(line_id, "failed", reason="missing-worktree")
    wt = Path(worktree)
    if not wt.exists():
        _record_failed(reg, line_id, "worktree-missing")
        return _result(line_id, "failed", reason="worktree-missing")

    if git_path_exists(wt, "rebase-merge") or git_path_exists(wt, "rebase-apply"):
        _record_failed(reg, line_id, "rebase-in-progress")
        return _result(line_id, "failed", reason="rebase-in-progress")

    rebased = git(wt, "rebase", trunk)
    if rebased.returncode != 0:
        if git_path_exists(wt, "rebase-merge") or git_path_exists(wt, "rebase-apply"):
            git(wt, "rebase", "--abort")
        _record_failed(reg, line_id, "rebase")
        return _result(line_id, "failed", reason="rebase", detail=rebased.stderr.strip())

    closure_gate = gate_cmd is None
    if closure_gate:
        try:
            spec_dir = resolve_spec_dir(entry, wt)
        except GateInputError as exc:
            _record_failed(reg, line_id, REASON_CLOSURE_INPUT_ERROR)
            return _result(line_id, "failed", reason=REASON_CLOSURE_INPUT_ERROR,
                           detail=str(exc))
        gate_cmd = build_gate_cmd(wt, spec_dir)
    failed = _quality_gate(reg, wt, entry, gate_cmd, closure_gate)
    if failed is not None:
        return failed

    head = git(wt, "rev-parse", "HEAD")
    if head.returncode != 0:
        _record_failed(reg, line_id, "head")
        return _result(line_id, "failed", reason="head")
    merged = git(repo, "merge", "--ff-only", head.stdout.strip())
    if merged.returncode != 0:
        if git_path_exists(repo, "MERGE_HEAD"):
            git(repo, "merge", "--abort")
        _record_failed(reg, line_id, "merge")
        return _result(line_id, "failed", reason="merge", detail=merged.stderr.strip())

    commit = git(repo, "rev-parse", "HEAD").stdout.strip()
    engine(reg, "integration-record", "--line-id", line_id, "--result", "merged",
           "--commit", commit)
    result = _result(line_id, "merged", commit=commit, worktree_removed=False)

    try:
        engine(reg, "archive-runtime", "--line-id", line_id,
               "--worktree", str(wt), "--dest", str(archive))
        result["archive_calls"] = 1
    except RuntimeError as exc:
        result.setdefault("warnings", []).append(f"archive-runtime: {exc}")
        _mark_retained(reg, line_id)
        return result

    removed = git(repo, "worktree", "remove", str(wt))
    if removed.returncode != 0:
        result.setdefault("warnings", []).append(
            f"worktree remove failed (retained): {removed.stderr.strip()}"
        )
        _mark_retained(reg, line_id)
    else:
        result["worktree_removed"] = True
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="integrate-lines.py")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--trunk", required=True)
    parser.add_argument("--registry", required=True)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--gate-cmd")
    parser.add_argument("--mirror-cmd")
    parser.add_argument("--lines", help="comma-separated subset; default is the full plan")
    args = parser.parse_args(argv)

    repo = Path(args.repo).expanduser().resolve()
    reg = Path(args.registry).expanduser().resolve()
    archive = Path(args.archive).expanduser().resolve()
    if not repo.is_dir():
        print(json.dumps({"ok": False, "error": f"repo not found: {repo}"}))
        return EXIT_USAGE
    if not reg.is_dir():
        print(json.dumps({"ok": False, "error": f"registry not found: {reg}"}))
        return EXIT_USAGE

    current = git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if current.returncode != 0 or current.stdout.strip() != args.trunk:
        print(json.dumps({
            "ok": False,
            "error": (
                f"repository is not checked out on trunk {args.trunk!r} "
                f"(actual: {current.stdout.strip() or 'unknown'}); refusing to switch branches"
            ),
        }))
        return EXIT_USAGE
    if (git_path_exists(repo, "MERGE_HEAD") or git_path_exists(repo, "rebase-merge")
            or git_path_exists(repo, "rebase-apply")):
        print(json.dumps({
            "ok": False,
            "error": "repository already has a merge/rebase in progress; refusing to integrate",
        }))
        return EXIT_USAGE

    try:
        plan = engine(reg, "integration-plan")
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return EXIT_FAILED

    selected = None
    if args.lines:
        selected = [item.strip() for item in args.lines.split(",") if item.strip()]
    entries = sorted(
        (item for item in plan if item.get("order")),
        key=lambda item: item["order"],
    )
    if selected is not None:
        unknown = sorted(set(selected) - {item["line_id"] for item in entries})
        if unknown:
            print(json.dumps({"ok": False, "error": f"lines not runnable: {unknown}"}))
            return EXIT_USAGE
        entries = [item for item in entries if item["line_id"] in selected]

    results = [
        _result(item["line_id"], "blocked", blocked_by=item.get("blocked_by") or [])
        for item in plan if not item.get("order")
    ]
    for item in entries:
        entry = read_entry(reg, item["line_id"])
        results.append(integrate_line(repo, args.trunk, reg, archive, entry, args.gate_cmd))

    mirror_calls = 0
    mirror_failed = False
    if args.mirror_cmd:
        mirror = run(["bash", "-c", args.mirror_cmd], cwd=repo)
        mirror_calls = 1
        if mirror.returncode != 0:
            mirror_failed = True
            results.append(_result("__mirrors__", "failed", reason="mirror-batch",
                                   detail=(mirror.stdout + mirror.stderr).strip()[-2000:]))

    failed = [row for row in results if row["status"] == "failed"]
    summary = {
        "ok": not failed and not mirror_failed,
        "trunk": args.trunk,
        "results": results,
        "archive_calls": sum(row["archive_calls"] for row in results),
        "mirror_calls": mirror_calls,
        "failed": len(failed),
    }
    print(json.dumps(summary, sort_keys=True))
    return EXIT_OK if summary["ok"] else EXIT_FAILED


#
# Emitted by `.specify/scripts/python/sync-mirrors.py`; the authority for this block is
# `contracts/mirror-projection.contract.md` C-34 / C-36. It depends on nothing
# that exists only in the source tree: it re-derives its own version line (C-36).
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
# script-interface:86:begin (feature 086 -- generated; the rule is owned by
# `.specify/shared/definitions/script-interface-definitions.md`, its executable form by
# `.specify/scripts/python/script_interface_cli.py`. This block owns no rule of its own.)
import sys as _sig_sys
import pathlib as _sig_pathlib

_SIG_OWNER = _sig_pathlib.Path(__file__).resolve().parent
while not ((_SIG_OWNER / 'pyproject.toml').is_file()
           and (_SIG_OWNER / '.git').exists()) and _SIG_OWNER.parent != _SIG_OWNER:
    _SIG_OWNER = _SIG_OWNER.parent
_SIG_OWNER = str(_SIG_OWNER / 'scripts' / 'python')
if _SIG_OWNER not in _sig_sys.path:
    _sig_sys.path.insert(0, _SIG_OWNER)

_SIG_SCRIPT = '.specify/skills/sdd-loop-driver/scripts/integrate-lines.py'
_SIG_DECLARED = ('--archive', '--gate-cmd', '--lines', '--mirror-cmd', '--registry', '--repo', '--trunk')
_SIG_HELP = (
    'usage: integrate-lines.py [options]\n'
    'options:\n'
    '  --archive\n  --gate-cmd\n  --lines\n  --mirror-cmd\n  --registry\n  --repo\n  --trunk\n'
    '  -h, --help    print this help and exit\n'
    '  --version     print the script name and the framework version, then exit\n'
    +
    'side-effects:' + ' ' + 'writes only through the options it documents; a flag-only invocation writes nothing' + '\n'
    +
    'exit-codes:' + ' ' + '0 success; 1 a documented check failed; 2 argument or environment error' + '\n'
)


def _sig_guard(argv):
    # Answer the flags and reject an undeclared option before any parsing or write.
    # RULES are asked of the owner (script_interface_cli.guard_argv), never restated:
    # the declared vocabulary and the flag forms are its, and C-9 (a recognized option
    # never rescues an unrecognized one) is its judgement. What stays local is the help
    # BODY, because its operand sentence is this script's own.
    try:
        import script_interface_cli as _sig  # noqa: E402 -- deferred: a copied script may lack it
    except ImportError:  # skill-local or sandbox copy: the module's own parser still runs
        return list(argv)
    line = list(argv)
    try:
        _sig.guard_argv(line, declared=_SIG_DECLARED)
    except SystemExit as answered:  # what guard_argv raises; _sig_sys.exit IS SystemExit
        if answered.code == 0:
            raise
        # The owner prints the rejection line and this script's help body is appended after
        # it, so the reader sees the vocabulary and not only the refusal.
        _sig_sys.stderr.write(_SIG_HELP)
        raise _sig_sys.exit(answered.code)
    stop = line.index('--') if '--' in line else len(line)
    if '-h' in line[:stop] or '--help' in line[:stop]:
        _sig_sys.stdout.write(_SIG_HELP)
        raise _sig_sys.exit(0)
    return line

if __name__ == "__main__":
    _sig_sys.argv = [_sig_sys.argv[0]] + _sig_guard(_sig_sys.argv[1:])
# script-interface:86:end

if __name__ == "__main__":
    sys.exit(main())
