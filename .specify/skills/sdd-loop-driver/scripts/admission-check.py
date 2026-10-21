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
import re
import subprocess
import sys
import time

FR_MIN = 8
FR_MAX = 30
TASK_MIN = 10
TASK_MAX = 40

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
    hit = [path for path in paths if path == ".specify/memory/constitution.md"]
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
    registry = os.path.join(project, ".specify", "memory", "features.md")
    detail = os.path.join(project, ".specify", "memory", "features", feature_id + ".md")
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


if __name__ == "__main__":
    sys.exit(main())
