#!/usr/bin/env python3
"""pre-analyze-check.py — deterministic cross-artifact gate before analyze.

Runs at the driver's U4 for requirements / plan / tasks and blocks the analyze
dispatch on mechanical drift: duplicate or dangling IDs, count claims that
disagree with the actual definitions, and blockedBy targets that do not exist.
Dead backticked paths are reported as advisories (deliverables may legitimately
not exist yet) and only block under ``--strict``.

Formal artifacts only: notes/, review.md and verification.md are dated records
and are never scanned for live consistency.

Exit codes:
  0 = pass (no blocking findings)
  1 = fail (at least one blocking finding)
  2 = input or parse error

Standard library only, Python >= 3.8. Self-contained; never reads the
framework runtime scripts tree.
"""

import argparse
import json
import os
import re
import sys
import time

FORMAL_NAMES = (
    "requirements.md", "plan.md", "tasks.md", "data-model.md",
    "quickstart.md", "research.md", "feature-ref.md",
)
FORMAL_GLOBS = ("contracts", "checklists")
SKIP_HEADING = re.compile(
    r"(?i)repair record|repair log|history|changelog|修订|变更记录|修复记录")
HEADING = re.compile(r"^(#{1,6})\s+")

FR_DEF = re.compile(r"^- \*\*FR-(\d{3})\*\*:")
SC_DEF = re.compile(r"^- \*\*SC-(\d{3})\*\*:")
TASK_DEF = re.compile(r"^- \[[ xX>~]\] (T\d{3})")
CLAUSE_DEF = re.compile(r"^- \*\*([A-Z]{2,4}-\d{2})\b")
FR_REF = re.compile(r"\bFR-(\d{3})\b")
SC_REF = re.compile(r"\bSC-(\d{3})\b")
CLAUSE_REF = re.compile(r"\b([A-Z]{2,4}-\d{2})\b")
NON_CLAUSE_PREFIXES = {"FR", "SC", "SHA", "ISO", "UTF"}
BLOCKED_BY = re.compile(r"\[blockedBy:\s*([^\]]+)\]")
TASK_TOKEN = re.compile(r"^T\d{3}$")

COUNT_CLAIMS = (
    ("FR", re.compile(r"(?<![\w-])(\d{1,3})\s*FR\b")),
    ("SC", re.compile(r"(?<![\w-])(\d{1,3})\s*SC\b")),
    ("tasks", re.compile(r"(?<![\w-])(\d{1,3})\s*(?:tasks?|条任务|个任务|任务行|task rows)\b")),
)
HISTORICAL_LINE = re.compile(
    r"→|->|\bvs\b|\bfrom\b|\bprevious\b|\bwas\b|\brebaseline|\bre-baseline|"
    r"原|前值|修复|变更|迁移|drift|\brepair(?:ed)?\b|应为|instead|"
    r"\b[0-9a-f]{7,40}\b")
COUNT_SKIP_LINE = re.compile(
    r"(?i)\bgiven\b|\bwhen\b|\bthen\b|fixture|夹具|示例|例如|举例|e\.g\.|"
    r"interval|区间|范围|threshold|ceiling|上限|下限|端点")

BACKTICK = re.compile(r"`([^`\n]+)`")
PATH_TOKEN = re.compile(r"^[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)+/?$")
PATH_ROOTS = (
    ".specify/", "skills/", ".specify/shared/", ".specify/templates/",
    "src/", "agents/", "tests/", "docs/", "feedback/",
)

STAGES = {
    "requirements": ("requirements.md",),
    "plan": ("requirements.md", "plan.md"),
    "tasks": ("requirements.md", "plan.md", "tasks.md"),
}


class InputError(Exception):
    pass


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise InputError("cannot read %s: %s" % (path, exc))


def formal_files(spec_dir):
    files = []
    for name in FORMAL_NAMES:
        path = os.path.join(spec_dir, name)
        if os.path.isfile(path):
            files.append(path)
    for folder in FORMAL_GLOBS:
        root = os.path.join(spec_dir, folder)
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root)):
            path = os.path.join(root, name)
            if os.path.isfile(path) and name.endswith(".md"):
                files.append(path)
    return files


def live_lines(text):
    """Yield (line_no, line) outside dated/history sections."""
    skip_level = None
    for number, line in enumerate(text.splitlines(), 1):
        heading = HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            if skip_level is not None and level <= skip_level:
                skip_level = None
            if skip_level is None and SKIP_HEADING.search(line):
                skip_level = level
                continue
        if skip_level is not None:
            continue
        yield number, line


def definitions(files, spec_dir):
    fr, sc, tasks, clauses = {}, {}, {}, {}
    duplicates = []
    for path in files:
        rel = os.path.relpath(path, spec_dir).replace(os.sep, "/")
        owner = ("requirements.md" if rel == "requirements.md" else
                 "tasks.md" if rel == "tasks.md" else
                 "contracts" if rel.startswith("contracts/") else "")
        for number, line in live_lines(read_file(path)):
            if owner == "requirements.md":
                match = FR_DEF.match(line)
                if match:
                    key = "FR-" + match.group(1)
                    if key in fr:
                        duplicates.append((path, number, key, fr[key]))
                    else:
                        fr[key] = (path, number)
                    continue
                match = SC_DEF.match(line)
                if match:
                    key = "SC-" + match.group(1)
                    if key in sc:
                        duplicates.append((path, number, key, sc[key]))
                    else:
                        sc[key] = (path, number)
                    continue
            if owner == "tasks.md":
                match = TASK_DEF.match(line)
                if match:
                    key = match.group(1)
                    if key in tasks:
                        duplicates.append((path, number, key, tasks[key]))
                    else:
                        tasks[key] = (path, number)
                    continue
            if owner == "contracts":
                match = CLAUSE_DEF.match(line)
                if match:
                    key = match.group(1)
                    if key in clauses:
                        duplicates.append((path, number, key, clauses[key]))
                    else:
                        clauses[key] = (path, number)
    return fr, sc, tasks, clauses, duplicates


def add(findings, check, severity, path, line, message):
    findings.append({
        "check": check, "severity": severity,
        "path": path, "line": line, "message": message,
    })


def check_references(files, fr, sc, clauses, findings, spec_dir):
    has_clauses = bool(clauses)
    local_prefixes = {key.split("-", 1)[0] for key in clauses}
    for path in files:
        rel = os.path.relpath(path, spec_dir)
        for number, line in live_lines(read_file(path)):
            for match in FR_REF.finditer(line):
                key = "FR-" + match.group(1)
                if key not in fr:
                    add(findings, "dangling-id", "error", rel, number,
                        "references %s which is not defined" % key)
            for match in SC_REF.finditer(line):
                key = "SC-" + match.group(1)
                if key not in sc:
                    add(findings, "dangling-id", "error", rel, number,
                        "references %s which is not defined" % key)
            if not has_clauses:
                continue
            for match in CLAUSE_REF.finditer(line):
                key = match.group(1)
                prefix = key.split("-", 1)[0]
                if prefix in NON_CLAUSE_PREFIXES or key in clauses:
                    continue
                if prefix in local_prefixes:
                    add(findings, "dangling-id", "error", rel, number,
                        "references contract clause %s which is not defined" % key)
                else:
                    add(findings, "external-clause", "advisory", rel, number,
                        "references contract clause %s from an external namespace" % key)


def check_blocked_by(spec_dir, tasks, findings):
    path = os.path.join(spec_dir, "tasks.md")
    if not os.path.isfile(path):
        return
    for number, line in live_lines(read_file(path)):
        for match in BLOCKED_BY.finditer(line):
            for token in match.group(1).split(","):
                token = token.strip()
                if not token or not TASK_TOKEN.match(token):
                    add(findings, "blocked-by", "advisory", "tasks.md", number,
                        "non-concrete blockedBy token %r" % token)
                    continue
                if token not in tasks:
                    add(findings, "blocked-by", "error", "tasks.md", number,
                        "blockedBy target %s is not defined" % token)


def in_range(line, start, end):
    before = line[max(0, start - 6):start]
    after = line[end:end + 6]
    return bool(re.search(r"\d\s*[–\-/]\s*$", before)
                or re.match(r"^\s*[–\-/]\s*\d", after))


def check_counts(files, fr, sc, tasks, findings, spec_dir):
    actual = {"FR": len(fr), "SC": len(sc), "tasks": len(tasks) or None}
    for path in files:
        rel = os.path.relpath(path, spec_dir)
        for number, line in live_lines(read_file(path)):
            if HISTORICAL_LINE.search(line) or COUNT_SKIP_LINE.search(line):
                continue
            for kind, pattern in COUNT_CLAIMS:
                expected = actual[kind]
                if expected is None:
                    continue
                for match in pattern.finditer(line):
                    if in_range(line, match.start(), match.end()):
                        continue
                    claimed = int(match.group(1))
                    if claimed != expected:
                        add(findings, "count-claim", "error", rel, number,
                            "claims %d %s but the artifacts define %d"
                            % (claimed, kind, expected))


def check_paths(files, findings, spec_dir, repo):
    if not repo:
        return
    spec_rel = os.path.relpath(spec_dir, repo).replace(os.sep, "/")
    for path in files:
        rel = os.path.relpath(path, spec_dir)
        for number, line in live_lines(read_file(path)):
            for match in BACKTICK.finditer(line):
                token = match.group(1).strip()
                if not PATH_TOKEN.match(token):
                    continue
                if not token.startswith(PATH_ROOTS):
                    continue
                if spec_rel and (token == spec_rel or token.startswith(spec_rel + "/")):
                    continue
                if os.path.exists(os.path.join(repo, token)):
                    continue
                add(findings, "missing-path", "advisory", rel, number,
                    "path does not exist under the repo: %s" % token)


def apply_waivers(findings, waivers):
    waived = 0
    for finding in findings:
        key = "%s:%s:%d" % (finding["check"], finding["path"], finding["line"])
        if key in waivers:
            finding["waived"] = True
            waived += 1
    return waived


def run(args):
    spec_dir = os.path.abspath(args.spec_dir)
    if not os.path.isdir(spec_dir):
        raise InputError("spec dir not found: %s" % spec_dir)
    for name in STAGES[args.stage]:
        if not os.path.isfile(os.path.join(spec_dir, name)):
            raise InputError("%s stage requires %s" % (args.stage, name))
    repo = os.path.abspath(args.repo) if args.repo else ""

    files = formal_files(spec_dir)
    fr, sc, tasks, clauses, duplicates = definitions(files, spec_dir)
    findings = []
    for path, number, key, first in duplicates:
        add(findings, "duplicate-id", "error", os.path.relpath(path, spec_dir),
            number, "duplicates %s first defined at %s:%d"
            % (key, os.path.relpath(first[0], spec_dir), first[1]))
    check_references(files, fr, sc, clauses, findings, spec_dir)
    check_blocked_by(spec_dir, tasks, findings)
    check_counts(files, fr, sc, tasks, findings, spec_dir)
    check_paths(files, findings, spec_dir, repo)

    waivers = set(args.waive or [])
    waived = apply_waivers(findings, waivers)
    blocking = [f for f in findings
                if not f.get("waived")
                and (f["severity"] == "error"
                     or (args.strict and f["severity"] == "advisory"))]
    errors = sum(1 for f in blocking if f["severity"] == "error")
    advisories = sum(1 for f in findings
                     if f["severity"] == "advisory" and not f.get("waived"))
    record = {
        "stage": args.stage,
        "decision": "fail" if blocking else "pass",
        "findings": findings,
        "summary": {
            "errors": errors,
            "advisories": advisories,
            "waived": waived,
            "fr": len(fr), "sc": len(sc), "tasks": len(tasks),
            "clauses": len(clauses), "files": len(files),
        },
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Deterministic cross-artifact gate before analyze.")
    parser.add_argument("--spec-dir", required=True)
    parser.add_argument("--stage", choices=tuple(STAGES), default="tasks")
    parser.add_argument("--repo", default="",
                        help="repo root for declared-path existence checks")
    parser.add_argument("--strict", action="store_true",
                        help="treat missing-path advisories as blocking")
    parser.add_argument("--waive", action="append", default=[],
                        metavar="CHECK:REL_PATH:LINE")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args(argv)

    try:
        record = run(args)
    except InputError as exc:
        print("pre-analyze-check: input error: %s" % exc, file=sys.stderr)
        return 2

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    print(json.dumps(record, ensure_ascii=False))
    summary = record["summary"]
    print("pre-analyze-check: stage=%s decision=%s errors=%d advisories=%d waived=%d"
          % (record["stage"], record["decision"], summary["errors"],
             summary["advisories"], summary["waived"]), file=sys.stderr)
    return 0 if record["decision"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
