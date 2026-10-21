#!/usr/bin/env python3
"""Audit the per-line full-suite test budget ledger.

The ledger is the ``<!-- test-budget:begin -->`` … ``<!-- test-budget:end -->``
JSONL fence inside the line state spine. ``<spec-dir>/test-evidence/*.jsonl``
only carries E3 targeted evidence; it is never a ledger source.

Checks: exactly two full-suite slots per line (baseline + closure), no third
slot, in-slot reruns only after closure, explicit out-of-slot exceptions,
environment failures that consume no slot, name-level closure comparison,
missing evidence reported as ``unknown`` (never zero), optional stage-log scan
for unaccounted full runs, and per-stage ``stage-status`` completeness over the
full applicable-stage denominator (a missing or empty evidence file stays in the
denominator and reports ``unknown``).

Exit codes: 0 pass, 1 audit failure, 2 input or parse error.

Python >= 3.8, standard library only.
"""

import argparse
import json
import re
import shlex
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_FAIL = 1
EXIT_INPUT = 2

SLOTS = ("baseline", "closure", "in-slot-rerun",
         "out-of-slot-exception", "environment-failure")
E3_STAGES = ("clarify", "plan", "tasks", "checklist", "analyze", "review")
SKIP_STATUS = "not-applicable-skipped-stage"
SKIP_MARKER = "checklist=skipped(fast-lane)"
RUNNER_TOKEN = "run-tests.sh"
VALUE_FLAGS = ("--names-out", "-m", "-k", "--maxfail", "-p", "--rootdir", "-c")


class InputError(Exception):
    pass


def is_na(value):
    return value in (None, "", "na", "NA", "unknown", "Unknown")


def as_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.lstrip("-").isdigit():
            return int(text)
    return None


def read_fence(path):
    text = Path(path).read_text(encoding="utf-8")
    start_marker = "<!-- test-budget:begin -->"
    end_marker = "<!-- test-budget:end -->"
    start = text.find(start_marker)
    if start < 0:
        raise InputError("missing %s fence in %s" % (start_marker, path))
    end = text.find(end_marker, start + len(start_marker))
    if end < 0:
        raise InputError("missing %s terminator in %s" % (end_marker, path))
    rows = []
    for line_number, line in enumerate(
            text[start + len(start_marker):end].splitlines(), 1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            row = json.loads(stripped)
        except ValueError as error:
            raise InputError("unparseable ledger line %d: %s" % (line_number, error))
        if not isinstance(row, dict):
            raise InputError("ledger line %d is not a JSON object" % line_number)
        rows.append(row)
    return text, rows


def parse_admission(text):
    match = re.search(r"^##\s+Admission\b.*$", text, re.MULTILINE)
    if not match:
        return None
    rest = text[match.end():]
    following = re.search(r"^##\s+", rest, re.MULTILINE)
    block = rest[:following.start()] if following else rest
    values = {}
    for line in block.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def admission_problem(admission, spine_text):
    if admission is None:
        return "missing E1 admission record"
    if admission.get("decision") != "fast-lane":
        return "E1 decision is not fast-lane"
    if "fast-lane=opt-in" not in admission.get("entry_evidence", ""):
        return "E1 entry_evidence lacks the opt-in literal"
    if not admission.get("decided_at"):
        return "E1 decided_at missing"
    if SKIP_MARKER not in spine_text:
        return "state spine lacks %s" % SKIP_MARKER
    return None


def name_level_compare(value):
    if not isinstance(value, str) or is_na(value):
        return False
    if "comm -13" in value:
        return True
    stripped = value.strip()
    if stripped.startswith("[") and stripped.endswith("]"):
        try:
            return isinstance(json.loads(stripped), list)
        except ValueError:
            return False
    return "new failures:" in value


def check_ledger(rows, stage_check, violations, unknown):
    if not rows:
        violations.append("ledger fence has no records")
        return {"baseline": 0, "closure": 0, "reruns": 0,
                "exceptions": 0, "environment_failures": 0}
    counts = {"baseline": 0, "closure": 0, "reruns": 0,
              "exceptions": 0, "environment_failures": 0}
    closure_seen = False
    previous_seq = 0
    for index, row in enumerate(rows, 1):
        slot = row.get("slot")
        seq = as_int(row.get("seq"))
        label = "row %d" % index
        if seq is None or seq <= 0:
            violations.append("%s: seq missing or not positive" % label)
        elif seq <= previous_seq:
            violations.append("%s: seq is not strictly increasing" % label)
        else:
            previous_seq = seq
        if slot not in SLOTS:
            violations.append("%s: unknown slot %r" % (label, slot))
            continue
        for field in ("stage", "purpose", "trigger", "at", "command",
                      "selection_basis", "rc"):
            if row.get(field) in (None, ""):
                violations.append("%s: missing %s" % (label, field))
        if "merge_source" in row and not is_na(row.get("merge_source")):
            if is_na(row.get("merged_at")):
                violations.append("%s: merge_source without merged_at" % label)

        if slot == "baseline":
            counts["baseline"] += 1
            if counts["baseline"] > 1:
                violations.append("%s: a second baseline slot is not allowed" % label)
            _check_full_slot(row, label, violations, unknown, closure=False)
        elif slot == "closure":
            counts["closure"] += 1
            closure_seen = True
            if counts["closure"] > 1:
                violations.append("%s: a second closure slot is not allowed" % label)
            _check_full_slot(row, label, violations, unknown, closure=True)
        elif slot == "in-slot-rerun":
            counts["reruns"] += 1
            if not closure_seen:
                violations.append("%s: in-slot-rerun before closure" % label)
            if row.get("trigger") in (None, "", "scheduled"):
                violations.append("%s: in-slot-rerun lacks a trigger" % label)
            if is_na(row.get("evidence_ptr")):
                violations.append("%s: in-slot-rerun lacks evidence_ptr" % label)
        elif slot == "out-of-slot-exception":
            counts["exceptions"] += 1
            if row.get("exception_reason") in (None, "", "na"):
                violations.append("%s: out-of-slot-exception lacks exception_reason"
                                  % label)
            if is_na(row.get("evidence_ptr")):
                violations.append("%s: out-of-slot-exception lacks evidence_ptr"
                                  % label)
        elif slot == "environment-failure":
            counts["environment_failures"] += 1
            if row.get("environment_evidence") in (None, "", "na"):
                violations.append("%s: environment-failure lacks environment_evidence"
                                  % label)

    if counts["baseline"] != 1:
        violations.append("expected exactly 1 baseline slot, found %d"
                          % counts["baseline"])
    if stage_check == "closure":
        if counts["closure"] != 1:
            violations.append("closure check requires exactly 1 closure slot, found %d"
                              % counts["closure"])
    elif counts["closure"] > 1:
        violations.append("expected at most 1 closure slot, found %d"
                          % counts["closure"])
    return counts


def _check_full_slot(row, label, violations, unknown, closure):
    if is_na(row.get("failed_names_path")):
        violations.append("%s: missing failed_names_path" % label)
    passed = as_int(row.get("passed"))
    failed = as_int(row.get("failed"))
    if passed is None or failed is None:
        unknown[0] += 1
        violations.append("%s: passed/failed evidence missing (unknown)" % label)
    if closure and not name_level_compare(row.get("baseline_compare")):
        violations.append("%s: closure baseline_compare is not a name-level diff"
                          % label)


def command_suffix(line):
    index = line.find(RUNNER_TOKEN)
    if index < 0:
        return None
    rest = line[index + len(RUNNER_TOKEN):]
    try:
        tokens = shlex.split(rest, posix=True)
    except ValueError:
        tokens = rest.split()
    positional = []
    skip_next = False
    for token in tokens:
        if skip_next:
            skip_next = False
            continue
        if token in VALUE_FLAGS:
            skip_next = True
            continue
        if token.startswith("-"):
            continue
        positional.append(token)
    if positional:
        return None
    return " ".join(rest.split())


def scan_logs(logs_dir, ledger_rows, violations, unknown):
    root = Path(logs_dir)
    if not root.is_dir():
        unknown[0] += 1
        violations.append("logs directory missing (unknown, not zero)")
        return
    logs = sorted(root.rglob("*.log"))
    if not logs:
        unknown[0] += 1
        violations.append("no stage logs found (unknown, not zero)")
        return
    ledger = {}
    for row in ledger_rows:
        suffix = command_suffix(str(row.get("command", "")))
        if suffix is not None:
            ledger[suffix] = ledger.get(suffix, 0) + 1
    for path in logs:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            unknown[0] += 1
            violations.append("unreadable stage log %s (unknown)" % path)
            continue
        for line in content.splitlines():
            suffix = command_suffix(line)
            if suffix is None:
                continue
            if ledger.get(suffix, 0) > 0:
                ledger[suffix] -= 1
            else:
                violations.append("unaccounted full run in %s: %s"
                                  % (path.name, suffix))


def load_evidence(spec_dir, violations, unknown):
    root = Path(spec_dir) / "test-evidence"
    evidence = {}
    if not root.is_dir():
        return evidence
    for path in sorted(root.glob("*.jsonl")):
        stage = path.stem
        if stage not in E3_STAGES:
            continue
        rows = []
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rows.append(json.loads(line))
        except (OSError, ValueError) as error:
            unknown[0] += 1
            violations.append("%s evidence unreadable (unknown): %s" % (stage, error))
            continue
        evidence[stage] = rows
    return evidence


def stage_status_complete(row):
    if not isinstance(row, dict):
        return False
    if row.get("row_type") != "stage-status":
        return False
    status = row.get("status")
    if status == "ran":
        required = ("command", "selection_basis", "sufficiency", "evidence_ptr",
                    "baseline")
        if any(row.get(field) in (None, "") for field in required):
            return False
        if not isinstance(row.get("selected_paths"), list):
            return False
        if not isinstance(row.get("new_failures"), list):
            return False
        if as_int(row.get("rc")) is None:
            return False
        if as_int(row.get("passed")) is None or as_int(row.get("failed")) is None:
            return False
        return True
    if status == "not-run-docs-only":
        if any(row.get(field) in (None, "") for field in
               ("selection_basis", "evidence_ptr")):
            return False
        changed = row.get("changed_paths")
        return isinstance(changed, list) and len(changed) > 0
    if status == "empty-selection-escalated":
        if any(row.get(field) in (None, "") for field in
               ("selection_basis", "sufficiency", "evidence_ptr")):
            return False
        return isinstance(row.get("selected_paths"), list)
    return False


def check_stages(evidence, spine_text, violations, unknown):
    admission = parse_admission(spine_text)
    problem = admission_problem(admission, spine_text)
    stages = 0
    complete = 0
    for stage in E3_STAGES:
        rows = evidence.get(stage)
        if rows is None:
            stages += 1
            unknown[0] += 1
            violations.append(
                "%s: stage evidence file missing; counted in the completeness "
                "denominator (unknown)" % stage)
            continue
        status_rows = [row for row in rows if row.get("row_type") == "stage-status"]
        if any(row.get("status") == SKIP_STATUS for row in status_rows):
            if stage != "checklist":
                stages += 1
                unknown[0] += 1
                violations.append("%s: skipped-stage status outside checklist" % stage)
                continue
            if problem:
                stages += 1
                unknown[0] += 1
                violations.append("fast-lane skip untrusted for %s: %s"
                                  % (stage, problem))
                continue
            continue
        stages += 1
        if len(status_rows) != 1:
            unknown[0] += 1
            violations.append("%s: expected exactly one stage-status row, found %d "
                              "(unknown)" % (stage, len(status_rows)))
            continue
        if stage_status_complete(status_rows[0]):
            complete += 1
        else:
            unknown[0] += 1
            violations.append("%s: stage-status evidence is incomplete (unknown)"
                              % stage)
    return stages, complete


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Audit the test-budget ledger in the line state spine.")
    parser.add_argument("--spine", required=True,
                        help="line state spine carrying the test-budget JSONL fence")
    parser.add_argument("--spec-dir", required=True,
                        help="feature dir; test-evidence/ carries E3 only (never the ledger)")
    parser.add_argument("--logs-dir",
                        help="optional stage log dir scanned for unaccounted full runs")
    parser.add_argument("--stage-check", choices=("implement", "closure"), default=None,
                        help="implement allows zero closure; closure requires both slots")
    args = parser.parse_args(argv)

    try:
        spine_text, rows = read_fence(args.spine)
    except (OSError, InputError) as error:
        print("status=error reason=%s" % error, file=sys.stderr)
        return EXIT_INPUT

    violations = []
    unknown = [0]
    counts = check_ledger(rows, args.stage_check, violations, unknown)
    if args.logs_dir:
        scan_logs(args.logs_dir, rows, violations, unknown)
    evidence = load_evidence(args.spec_dir, violations, unknown)
    stages, complete = check_stages(evidence, spine_text, violations, unknown)

    print("slots=baseline:%d closure:%d reruns=%d exceptions=%d unknown=%d "
          "environment_failures=%d" % (
              counts["baseline"], counts["closure"], counts["reruns"],
              counts["exceptions"], unknown[0], counts["environment_failures"]))
    print("stages=%d complete=%d" % (stages, complete))
    if violations:
        print("status=fail")
        for violation in violations:
            print("reason=%s" % violation)
        return EXIT_FAIL
    print("status=ok")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
