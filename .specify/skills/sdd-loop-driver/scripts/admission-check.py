#!/usr/bin/env python3
"""admission-check.py — deterministic fast-lane admission gate.

Seven mechanically measured criteria (a)-(g) decide whether a medium feature
may skip ``checklist`` while keeping ``analyze`` and ``review``. Every value is
derived from artifacts; there is no self-attestation. Any unreadable input is a
input error (exit 2); any criterion that cannot be proven is a rejection
(fail-closed, exit 1).

Exit codes:
  0 = admissible (fast-lane)
  1 = rejected (full-chain)
  2 = input or parse error

Standard library only, Python >= 3.8. The script is self-contained and never
reads the framework runtime scripts tree.
"""

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import time

FR_MIN = 8
FR_MAX = 120
TASK_MIN = 10
TASK_MAX = 160

FR_PATTERN = re.compile(r"^- \*\*FR-[0-9]{3}\*\*:")
TASK_NARROW = re.compile(r"^- \[[ xX]\] T[0-9]{3}")
TASK_WIDE = re.compile(r"^- \[[ xX>~]\] T[0-9]{3}")
OPT_IN = "fast-lane=opt-in"
SKIP_VALUE = "skipped(fast-lane)"
SKIP_MARKER = "checklist=" + SKIP_VALUE

ENGINE_PREFIXES = (
    ".specify/templates/",
    "src/",
    ".specify/scripts/",
    ".specify/templates/commands/",
    "skills/internal/",
)
DEPENDENCY_MANIFESTS = {
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "Pipfile", "Pipfile.lock", "poetry.lock", "uv.lock",
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "go.mod", "Cargo.toml", "Cargo.lock",
}
SENSITIVE_PATH_TOKENS = (
    "auth", "credential", "secret", "password", "passwd", "token",
    "delete", "migration", "release", "publish", "confirm",
)
SENSITIVE_CONTENT = [
    re.compile(r"password\s*=", re.IGNORECASE),
    re.compile(r"passwd\s*=", re.IGNORECASE),
    re.compile(r"secret\s*=", re.IGNORECASE),
    re.compile(r"api[_-]?key\s*=", re.IGNORECASE),
    re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"\brm\s+-rf\b"),
    re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
]
CODE_EXTENSIONS = (".py", ".sh", ".bash", ".js", ".ts", ".go", ".rs", ".rb")
NETWORK_CONTENT = [
    re.compile(r"\brequests\.(get|post|put|delete|patch|head)\s*\("),
    re.compile(r"\bhttpx\."),
    re.compile(r"\burllib\.request\b"),
    re.compile(r"\bfetch\s*\("),
    re.compile(r"\bopenai\b", re.IGNORECASE),
    re.compile(r"\banthropic\b", re.IGNORECASE),
    re.compile(r"\bapi\.openai\.com\b"),
]
MANIFEST_LINE = re.compile(r"^([A-Za-z0-9._-]+)\|([^\s|]+)$")
RELATED_PATTERN = re.compile(r"Related Feature\**[ \t]*[:：][ \t]*([0-9]{3})")


class InputError(Exception):
    pass


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise InputError("cannot read %s: %s" % (path, exc))


def git(project, *args):
    completed = subprocess.run(
        ["git", "-C", project] + list(args),
        capture_output=True, text=True,
    )
    if completed.returncode != 0:
        raise InputError("git %s failed: %s" % (" ".join(args), completed.stderr.strip()))
    return completed.stdout


def changed_paths(project, base):
    names = set()
    committed = git(project, "diff", "--name-only", "--diff-filter=ACMR",
                    "%s..HEAD" % base)
    for line in committed.splitlines():
        if line.strip():
            names.add(line.strip())
    status = git(project, "status", "--porcelain")
    for line in status.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path:
            names.add(path.strip())
    return sorted(names)


def added_paths(project, base):
    names = set()
    committed = git(project, "diff", "--name-only", "--diff-filter=A", "%s..HEAD" % base)
    for line in committed.splitlines():
        if line.strip():
            names.add(line.strip())
    status = git(project, "status", "--porcelain")
    for line in status.splitlines():
        if line.startswith("?? "):
            names.add(line[3:].strip())
    return sorted(names)


def added_lines(project, base, paths):
    lines = []
    try:
        diff = git(project, "diff", "-U0", "%s..HEAD" % base)
    except InputError:
        diff = ""
    for line in diff.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            lines.append(line[1:])
    tracked = set()
    try:
        tracked = set(git(project, "ls-files").splitlines())
    except InputError:
        pass
    for rel in paths:
        full = os.path.join(project, rel)
        if rel in tracked or not os.path.isfile(full):
            continue
        try:
            with open(full, "r", encoding="utf-8", errors="ignore") as handle:
                lines.extend(handle.read().splitlines())
        except OSError:
            continue
    return lines


def criterion_a(requirements_text, tasks_text):
    fr_count = sum(1 for line in requirements_text.splitlines()
                   if FR_PATTERN.match(line))
    task_count = sum(1 for line in tasks_text.splitlines()
                     if TASK_NARROW.match(line))
    ok = FR_MIN <= fr_count <= FR_MAX and TASK_MIN <= task_count <= TASK_MAX
    evidence = ("FR definitions=%d in [%d,%d]; task rows (narrow)=%d in [%d,%d]"
                % (fr_count, FR_MIN, FR_MAX, task_count, TASK_MIN, TASK_MAX))
    return fr_count, task_count, ok, evidence


def criterion_b(paths):
    hit = [path for path in paths if path == ".specify/constitution.md"]
    return not hit, ("constitution touched: %s" % hit if hit
                     else "constitution untouched in base..HEAD + worktree")


def criterion_c(project, base, paths):
    engine = [path for path in paths if path.startswith(ENGINE_PREFIXES)]
    if engine:
        return False, "engine/template path touched: %s" % engine
    new_skills = [path for path in added_paths(project, base)
                  if path.startswith("skills/external/")]
    if new_skills:
        return False, "new skill path added: %s" % new_skills
    manifests = [path for path in paths
                 if os.path.basename(path) in DEPENDENCY_MANIFESTS]
    if manifests:
        return False, "dependency manifest touched: %s" % manifests
    code_paths = [path for path in paths if path.endswith(CODE_EXTENSIONS)]
    for line in added_lines(project, base, code_paths):
        for pattern in NETWORK_CONTENT:
            if pattern.search(line):
                return False, "network/model API trace in added code: %s" % line.strip()
    return True, "no engine/template/skill/dependency/network surface touched"


def criterion_d(project, base, paths):
    hits = []
    for path in paths:
        lowered = path.lower()
        if any(token in lowered for token in SENSITIVE_PATH_TOKENS):
            hits.append(path)
    if hits:
        return False, "sensitive path touched: %s" % hits
    for line in added_lines(project, base, paths):
        for pattern in SENSITIVE_CONTENT:
            if pattern.search(line):
                return False, "sensitive content in added line: %s" % line.strip()
    return True, "no sensitive surface touched"


def criterion_e(project, manifest_path, expected_branch):
    text = read_file(manifest_path)
    records = []
    errors = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.count("|") != 1:
            errors.append("record must carry exactly one '|': %r" % raw)
            continue
        match = MANIFEST_LINE.match(line)
        if not match:
            errors.append("record violates the line syntax: %r" % raw)
            continue
        records.append((match.group(1), match.group(2)))
    if errors:
        return False, "; ".join(errors)
    if len(records) != 1:
        return False, "expected exactly one line record, got %d" % len(records)
    branch = records[0][1]
    if branch != expected_branch:
        return False, "manifest branch %s != expected branch %s" % (branch, expected_branch)
    current = git(project, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if current != expected_branch:
        return False, "current branch %s != expected branch %s" % (current, expected_branch)
    return True, "single line record for branch %s" % expected_branch


def criterion_f(project, requirements_text):
    if "[NEEDS CLARIFICATION:" in requirements_text:
        return False, "active [NEEDS CLARIFICATION: marker present"
    has_clarifications = "## Clarifications" in requirements_text
    has_session = re.search(r"^### Session\b", requirements_text, re.MULTILINE)
    if not (has_clarifications and has_session):
        return False, "clarify not recorded (missing Clarifications Session)"
    match = RELATED_PATTERN.search(requirements_text)
    if not match:
        return False, "Related Feature binding not declared"
    feature_id = match.group(1)
    registry = os.path.join(project, ".specify", "features.md")
    details_root = pathlib.Path(project, ".specify", "features")
    details = sorted(details_root.glob(feature_id + "-*.md"))
    detail = details[0] if details else details_root / (feature_id + "-<slug>.md")
    if not os.path.isfile(registry):
        return False, "feature registry missing: %s" % registry
    if feature_id not in read_file(registry):
        return False, "Related Feature %s not present in the registry" % feature_id
    if not os.path.isfile(detail):
        return False, "Related Feature detail missing: %s" % detail
    return True, "clarify complete; Related Feature %s resolved" % feature_id


def criterion_g(checklist_text):
    checked = sum(1 for line in checklist_text.splitlines()
                  if line.strip().startswith("- [X]"))
    open_items = sum(1 for line in checklist_text.splitlines()
                     if line.strip().startswith("- [ ]"))
    if checked == 0:
        return False, "requirements checklist has zero checked items"
    if open_items:
        return False, "requirements checklist has %d unchecked item(s)" % open_items
    return True, "requirements checklist complete (%d checked)" % checked


def decide(args):
    for path in (args.requirements, args.tasks, args.checklists,
                 args.entry_evidence, args.lines_manifest):
        if not os.path.isfile(path):
            raise InputError("missing input file: %s" % path)
    git(args.project, "rev-parse", "--verify", args.base_ref + "^{commit}")

    requirements_text = read_file(args.requirements)
    tasks_text = read_file(args.tasks)
    checklist_text = read_file(args.checklists)
    entry_text = read_file(args.entry_evidence)
    paths = changed_paths(args.project, args.base_ref)

    fr_count, task_count, a_ok, a_evidence = criterion_a(requirements_text, tasks_text)
    criteria = [
        {"id": "a", "verdict": "pass" if a_ok else "fail", "evidence": a_evidence},
    ]
    for cid, (ok, evidence) in (
        ("b", criterion_b(paths)),
        ("c", criterion_c(args.project, args.base_ref, paths)),
        ("d", criterion_d(args.project, args.base_ref, paths)),
        ("e", criterion_e(args.project, args.lines_manifest, args.expected_branch)),
        ("f", criterion_f(args.project, requirements_text)),
        ("g", criterion_g(checklist_text)),
    ):
        criteria.append({"id": cid,
                         "verdict": "pass" if ok else "fail",
                         "evidence": evidence})

    reasons = ["criterion %s failed" % item["id"]
               for item in criteria if item["verdict"] == "fail"]
    if OPT_IN not in entry_text:
        reasons.append("entry evidence does not carry fast-lane=opt-in")
    fast_lane = not reasons
    return {
        "decision": "fast-lane" if fast_lane else "full-chain",
        "entry_evidence": entry_text.strip(),
        "criteria": criteria,
        "measured": {"fr_count": fr_count, "task_count": task_count},
        "lines_manifest_ptr": args.lines_manifest,
        "decided_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checklist": SKIP_VALUE if fast_lane else "executed",
        "checklist_marker": SKIP_MARKER if fast_lane else "checklist=executed",
        "reasons": reasons,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Deterministic fast-lane admission gate (063).")
    parser.add_argument("--project", required=True)
    parser.add_argument("--base-ref", required=True)
    parser.add_argument("--requirements", required=True)
    parser.add_argument("--tasks", required=True)
    parser.add_argument("--checklists", required=True)
    parser.add_argument("--entry-evidence", required=True)
    parser.add_argument("--lines-manifest", required=True)
    parser.add_argument("--expected-branch", required=True)
    parser.add_argument("--json-out", default="")
    args = parser.parse_args(argv)

    try:
        record = decide(args)
    except InputError as exc:
        print("admission-check: input error: %s" % exc, file=sys.stderr)
        return 2

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    print(json.dumps(record, ensure_ascii=False))
    return 0 if record["decision"] == "fast-lane" else 1


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

_SIG_SCRIPT = '.specify/skills/sdd-loop-driver/scripts/admission-check.py'
_SIG_DECLARED = ('--base-ref', '--checklists', '--entry-evidence', '--expected-branch', '--json-out', '--lines-manifest', '--project', '--requirements', '--tasks')
_SIG_HELP = (
    'usage: admission-check.py [options]\n'
    'options:\n'
    '  --base-ref\n  --checklists\n  --entry-evidence\n  --expected-branch\n  --json-out\n  --lines-manifest\n  --project\n  --requirements\n  --tasks\n'
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
