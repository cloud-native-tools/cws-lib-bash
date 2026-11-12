#!/usr/bin/env python3
"""Git workflow observer — machine-observed facts for `.specify/workflow/git.md`.

Mechanism/policy split:
  * POLICY lives in `.specify/workflow/git.md` — the managed
    ``<!-- GIT_WORKFLOW_START -->`` … ``<!-- GIT_WORKFLOW_END -->`` block (model,
    branch roles, close-out discipline). This engine NEVER writes inside it: those
    declarations change only through the `git-utils` skill's Bootstrap flow with
    user confirmation.
  * MECHANISM lives here: read the state file plus live repository facts (trunk,
    remotes, observed feature-branch naming, close-out declaration presence) and
    refresh exactly one ``Observed facts (machine, dated)`` section between the
    engine's own ``<!-- GIT_OBSERVED_START -->`` / ``<!-- GIT_OBSERVED_END -->``
    markers. Only observable facts; the section is evidence for the user's next
    Bootstrap decision, never a declaration.

Hook (probe + handler mechanism, feature 056): registered in
``.specify/shared/definitions/probe-definitions.md`` as Handler ``h-git-workflow-observe``
(kind=engine, action ``observe``, non-blocking) bound at ``@point:situation``
scope ``all``. The situation engine (``.specify/scripts/python/trigger-utils.py``, action
``assess``) dispatches it after writing its telemetry row, so every situation
assessment refreshes the observations idempotently.

Usage:
  python3 git-workflow-observe.py --action observe [--check] [--json] [--workspace PATH]

Exit codes: 0 ok (updated / unchanged / skipped) · 1 usage · 2 input error ·
10 --check found a pending observation update (writes nothing).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 1
EXIT_INPUT_ERROR = 2
EXIT_CHECK_PENDING = 10

STATE_RELPATH = Path(".specify") / "workflow" / "git.md"
WF_START = "<!-- GIT_WORKFLOW_START -->"
WF_END = "<!-- GIT_WORKFLOW_END -->"
OBS_START = "<!-- GIT_OBSERVED_START -->"
OBS_END = "<!-- GIT_OBSERVED_END -->"
OBS_HEADING = "## Observed facts (machine, dated)"
GIT_TIMEOUT = 15

_HERE = Path(__file__).resolve()
_ROW_RE = re.compile(r"^- \*\*(?P<label>[^*]+)\*\*:\s*(?P<value>.*)$")
_TABLE_RE = re.compile(r"^\|(.+)\|$")
_ROLE_ROW_NAMES = ("MAIN", "PRE", "DEV")


def resolve_root(workspace):
    """Explicit --workspace > engine self-location (literal `.specify` ancestor) >
    nearest `.specify` CWD ancestor > CWD. The source copy under `.specify/scripts/python/`
    never self-matches this repository's own `.specify/` tree."""
    if workspace:
        root = Path(workspace).resolve()
        return root.parent if root.name == ".specify" else root
    for parent in _HERE.parents:
        if parent.name == ".specify":
            return parent.parent
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".specify").is_dir():
            return candidate
    return cwd


def _git(root, *args):
    try:
        proc = subprocess.run(["git", *args], cwd=str(root),
                              capture_output=True, text=True, timeout=GIT_TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return 1, ""
    return proc.returncode, proc.stdout


def _is_git_repo(root):
    rc, out = _git(root, "rev-parse", "--is-inside-work-tree")
    return rc == 0 and out.strip() == "true"


def _local_branches(root):
    rc, out = _git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads/")
    return [line.strip() for line in out.splitlines() if line.strip()] if rc == 0 else []


def _remotes(root):
    rc, out = _git(root, "remote")
    return sorted(line.strip() for line in out.splitlines() if line.strip()) if rc == 0 else []


def _backticks(text):
    return re.findall(r"`([^`]+)`", text or "")


def _norm_label(label):
    return label.strip().lstrip("⚠").strip().lower()


def _row(block, label):
    wanted = _norm_label(label)
    for line in block.splitlines():
        m = _ROW_RE.match(line)
        if m and _norm_label(m.group("label")) == wanted:
            return m.group("value").strip()
    return None


def _managed_block(text):
    if text.count(WF_START) != 1 or text.count(WF_END) != 1:
        return None
    start = text.index(WF_START) + len(WF_START)
    end = text.index(WF_END)
    return text[start:end] if start <= end else None


def _role_branches(block):
    names = []
    for line in block.splitlines():
        m = _TABLE_RE.match(line.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(1).split("|")]
        if len(cells) >= 2 and cells[0] in _ROLE_ROW_NAMES:
            names.extend(_backticks(cells[1]))
    return names


def _declared_branch_names(block):
    names = set()
    trunk = _row(block, "Trunk")
    if trunk:
        names.update(_backticks(trunk))
    names.update(_role_branches(block))
    return names


def _declared_remote_names(block):
    names = set()
    cell = _row(block, "Closeout remotes")
    if cell:
        spans = [s for s in _backticks(cell) if s not in ("-", "none", "—")]
        if spans:
            names.update(spans)
        else:
            names.update(p.strip().strip("`") for p in re.split(r"[,，]", cell) if p.strip())
    roles = _row(block, "Remote roles") or ""
    names.update(tok for tok in _backticks(roles) if re.match(r"^[A-Za-z0-9_-]+$", tok))
    return names


def _trunk_fact(block, branches):
    declared = _backticks(_row(block, "Trunk") or "")
    declared_trunk = declared[0] if declared else None
    if not declared_trunk:
        role_branches = _role_branches(block)
        declared_trunk = role_branches[0] if role_branches else None
    if declared_trunk:
        state = "present locally" if declared_trunk in branches else "NOT present locally"
        return "`%s` (declared; %s)" % (declared_trunk, state)
    for candidate in ("main", "master"):
        if candidate in branches:
            return "`%s` (no trunk declared; detected locally)" % candidate
    return "none detected (no declaration and neither `main` nor `master` exists locally)"


def _naming_fact(block, branches):
    excluded = _declared_branch_names(block) | {"main", "master"}
    candidates = sorted(b for b in branches if b not in excluded)
    if not candidates:
        return "none observed (no non-declared local branches)"
    numbered = [b for b in candidates if re.match(r"^\d+-.+", b)]
    example = numbered[0] if numbered else candidates[0]
    if numbered and len(numbered) * 2 >= len(candidates):
        return ("`NNN-<slug>` — %d/%d non-declared local branches are digit-prefixed "
                "(e.g. `%s`)" % (len(numbered), len(candidates), example))
    return ("no dominant numbered convention — %d/%d non-declared local branches are "
            "digit-prefixed (e.g. `%s`)" % (len(numbered), len(candidates), example))


def collect_facts(root, block):
    """(label, value) pairs describing observable facts; declaration values are only read."""
    facts = []
    if not _is_git_repo(root):
        facts.append(("Repository", "not a git repository — repository facts unavailable"))
    else:
        branches = _local_branches(root)
        facts.append(("Trunk", _trunk_fact(block, branches)))
        remotes = _remotes(root)
        facts.append(("Remotes", ", ".join("`%s`" % n for n in remotes) or "none configured"))
        present = set(remotes)
        declared = _declared_remote_names(block)
        missing = sorted(declared - present)
        extra = sorted(present - declared)
        facts.append((
            "Remotes vs declaration",
            "declared-but-missing: %s; present-but-undeclared: %s" % (
                ", ".join("`%s`" % n for n in missing) or "none",
                ", ".join("`%s`" % n for n in extra) or "none",
            )))
        facts.append(("Feature-branch naming", _naming_fact(block, branches)))
    facts.append(("Closeout declaration",
                  "present" if _row(block, "Closeout") is not None else "absent"))
    return facts


def _utc_now():
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _render_section(facts, observed_at):
    lines = [OBS_START, OBS_HEADING, "", "- **Observed at**: %s" % observed_at]
    lines.extend("- **%s**: %s" % (label, value) for label, value in facts)
    lines.extend([
        "",
        "These are machine observations, not declarations: the workflow model and branch "
        "declarations above change only through the `git-utils` skill's Bootstrap flow with "
        "user confirmation.",
        OBS_END,
    ])
    return "\n".join(lines)


def _fact_map(facts):
    return {label.lower(): " ".join(value.split()) for label, value in facts}


def _existing_fact_map(text):
    start = text.find(OBS_START)
    end = text.find(OBS_END)
    if start < 0 or end < start:
        return None
    found = {}
    for line in text[start:end].splitlines():
        m = _ROW_RE.match(line)
        if m and _norm_label(m.group("label")) != "observed at":
            found[_norm_label(m.group("label"))] = " ".join(m.group("value").split())
    return found


def _splice(text, section):
    """Replace the observed section, or insert it after the workflow block. None when
    the observed markers are present but unusable (write nothing, never repair)."""
    starts, ends = text.count(OBS_START), text.count(OBS_END)
    if starts or ends:
        if starts != 1 or ends != 1:
            return None
        start, end = text.index(OBS_START), text.index(OBS_END)
        if start > end:
            return None
        return text[:start] + section + text[end + len(OBS_END):]
    if text.count(WF_END) == 1:
        idx = text.index(WF_END) + len(WF_END)
        head, tail = text[:idx], text[idx:].lstrip("\n")
        composed = head + "\n\n" + section
        return composed + (("\n\n" + tail) if tail.strip() else "\n")
    return text.rstrip("\n") + "\n\n" + section + "\n"


def action_observe(root, check):
    path = root / STATE_RELPATH
    payload = {
        "action": "observe",
        "workspaceRoot": str(root),
        "stateFile": STATE_RELPATH.as_posix(),
        "changed": False,
        "wouldChange": False,
        "skipped": None,
        "facts": [],
    }
    if not path.is_file():
        payload["skipped"] = "workflow-state-file-absent"
        return EXIT_OK, payload
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        payload["skipped"] = "state-file-unreadable: %s" % (exc.strerror or exc)
        return EXIT_INPUT_ERROR, payload
    block = _managed_block(text)
    if block is None:
        payload["skipped"] = "workflow-block-unusable"
        return EXIT_OK, payload
    facts = collect_facts(root, block)
    payload["facts"] = [{"label": label, "value": value} for label, value in facts]
    if _existing_fact_map(text) == _fact_map(facts):
        return EXIT_OK, payload
    updated = _splice(text, _render_section(facts, _utc_now()))
    if updated is None:
        payload["skipped"] = "observed-markers-unusable"
        return EXIT_OK, payload
    if updated == text:
        return EXIT_OK, payload
    payload["wouldChange"] = True
    if check:
        return EXIT_CHECK_PENDING, payload
    tmp = path.with_name(path.name + ".observe-tmp")
    try:
        tmp.write_text(updated, encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        payload["skipped"] = "state-file-unwritable: %s" % (exc.strerror or exc)
        return EXIT_INPUT_ERROR, payload
    payload["changed"] = True
    return EXIT_OK, payload


def render_text(payload, code):
    if payload.get("skipped"):
        return "git-workflow-observe: skipped (%s) — %s" % (
            payload["skipped"], payload["stateFile"])
    if code == EXIT_CHECK_PENDING:
        head = "git-workflow-observe: pending update (--check writes nothing) — %s" % (
            payload["stateFile"])
    elif payload.get("changed"):
        head = "git-workflow-observe: observed facts updated — %s" % payload["stateFile"]
    else:
        head = "git-workflow-observe: unchanged — %s" % payload["stateFile"]
    lines = [head]
    lines.extend("  %s: %s" % (fact["label"], fact["value"])
                 for fact in payload.get("facts", []))
    return "\n".join(lines)


class _UsageError(Exception):
    """Raised instead of argparse's own exit(2) so the usage exit stays 1."""


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # noqa: D102 - argparse hook
        raise _UsageError(message)


def build_parser():
    parser = _Parser(
        prog="git-workflow-observe.py",
        description="Observe live repository facts and refresh only the machine-dated "
                    "'Observed facts' section of .specify/workflow/git.md; the declared "
                    "workflow block is never touched.",
    )
    _sig_configure(
        parser,
        effects="writes only the GIT_OBSERVED section of .specify/workflow/git.md under "
                "the resolved workspace; --check and --help/--version write nothing",
        codes="0 ok (updated / unchanged / skipped) · 1 usage · 2 input error · "
              "10 --check found a pending update (writes nothing)",
    )
    parser.add_argument("--action", required=True, choices=["observe"])
    parser.add_argument("--workspace", default=None,
                        help="project root (default: engine self-location, then the "
                             "nearest .specify ancestor of the CWD)")
    parser.add_argument("--check", action="store_true", default=False,
                        help="report whether an observation update is pending; write nothing")
    parser.add_argument("--json", action="store_true", default=False,
                        help="machine-readable JSON envelope on stdout")
    return parser


def emit(payload, code, as_json):
    if as_json:
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(render_text(payload, code) + "\n")


def main(argv=None):
    _sig_guard(argv, declared=["--action", "--workspace", "--check", "--json"],
               unknown_exit=EXIT_USAGE)
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except _UsageError as exc:
        payload = {"ok": False, "action": "observe", "error": str(exc)}
        emit(payload, EXIT_USAGE, "--json" in list(argv if argv is not None else sys.argv[1:]))
        return EXIT_USAGE
    root = resolve_root(args.workspace)
    code, payload = action_observe(root, args.check)
    payload["ok"] = code in (EXIT_OK, EXIT_CHECK_PENDING)
    emit(payload, code, args.json)
    return code


# --version, wired through the one version source (C-8).
import sys as _sig_sys  # noqa: E402
import pathlib as _sig_pathlib  # noqa: E402

_SIG_DIR = str(_sig_pathlib.Path(__file__).resolve().parent)
if _SIG_DIR not in _sig_sys.path:
    _sig_sys.path.insert(0, _SIG_DIR)
try:  # the helper owns the rule; a copy WITHOUT it still runs its action
    from script_interface_cli import configure_parser as _sig_configure  # noqa: E402
    from script_interface_cli import guard_argv as _sig_guard  # noqa: E402
except ImportError:  # a sandbox/handler copy carries the engine but not the helper
    def _sig_configure(parser, **_kwargs):
        return parser

    def _sig_guard(_argv=None, declared=None, **_kwargs):
        return None


if __name__ == "__main__":
    sys.exit(main())
