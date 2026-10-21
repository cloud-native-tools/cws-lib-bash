#!/usr/bin/env python3
"""decomposition-check.py — deterministic large-feature decomposition gate.

Two decision points share the ceilings of the fast-lane medium interval
(``FR_CEILING`` = FR_MAX, ``TASK_CEILING`` = TASK_MAX):

  plan   at plan entry: > FR_CEILING requirement definitions -> split-required
  tasks  at tasks U4:   > FR_CEILING FR definitions or
                        > TASK_CEILING task rows -> split-required

Every value is derived from the artifacts; there is no self-attestation.
An unreadable or empty input is an input error (exit 2).

Exit codes:
  0 = proceed (fits the single-feature interval)
  1 = split-required (decompose before the next stage)
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

FR_CEILING = 30
TASK_CEILING = 40
FR_PATTERN = re.compile(r"^- \*\*FR-[0-9]{3}\*\*:")
TASK_PATTERN = re.compile(r"^- \[[ xX>~]\] T[0-9]{3}")


class InputError(Exception):
    pass


def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise InputError("cannot read %s: %s" % (path, exc))


def count_fr(text):
    return sum(1 for line in text.splitlines() if FR_PATTERN.match(line))


def count_tasks(text):
    return sum(1 for line in text.splitlines() if TASK_PATTERN.match(line))


def measure(mode, requirements_path, tasks_path):
    if not os.path.isfile(requirements_path):
        raise InputError("missing requirements file: %s" % requirements_path)
    fr_count = count_fr(read_file(requirements_path))
    if fr_count == 0:
        raise InputError("no FR definitions (^- **FR-NNN**:) in %s" % requirements_path)

    task_count = None
    if mode == "tasks":
        if not tasks_path:
            raise InputError("--mode tasks requires --tasks")
        if not os.path.isfile(tasks_path):
            raise InputError("missing tasks file: %s" % tasks_path)
        task_count = count_tasks(read_file(tasks_path))
        if task_count == 0:
            raise InputError("no task rows (^- [x] TNNN) in %s" % tasks_path)

    reasons = []
    if fr_count > FR_CEILING:
        reasons.append("FR definitions=%d exceeds ceiling %d" % (fr_count, FR_CEILING))
    if task_count is not None and task_count > TASK_CEILING:
        reasons.append("task rows=%d exceeds ceiling %d" % (task_count, TASK_CEILING))

    return {
        "mode": mode,
        "decision": "split-required" if reasons else "proceed",
        "measured": {
            "fr_count": fr_count,
            "task_count": task_count,
            "fr_ceiling": FR_CEILING,
            "task_ceiling": TASK_CEILING,
        },
        "reasons": reasons,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Deterministic large-feature decomposition gate.")
    parser.add_argument("--mode", choices=("plan", "tasks"), default="plan",
                        help="decision point: plan entry or tasks U4")
    parser.add_argument("--requirements", required=True)
    parser.add_argument("--tasks", default="")
    parser.add_argument("--json-out", default="")
    args = parser.parse_args(argv)

    try:
        record = measure(args.mode, args.requirements, args.tasks)
    except InputError as exc:
        print("decomposition-check: input error: %s" % exc, file=sys.stderr)
        return 2

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(record, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    print(json.dumps(record, ensure_ascii=False))
    return 0 if record["decision"] == "proceed" else 1


if __name__ == "__main__":
    sys.exit(main())
