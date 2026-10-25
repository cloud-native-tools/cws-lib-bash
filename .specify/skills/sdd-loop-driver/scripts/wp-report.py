#!/usr/bin/env python3
"""Coordination report and metrics for Feature 070 Work Packages.

The report is derived from the line state spine only: the ``wp-plan`` /
``wp-plan-amendment`` fences (the effective plan) and the append-only
``wp-ledger`` fence. Metric definitions are owned by
``contracts/observability-and-retry.md`` (OR-04…OR-13); the schema projection
is ``data-model.md`` E11.

Standard library only, Python 3.8+. The script never writes the spine and
never copies raw transcripts. A metric whose source record is missing is the
literal string ``not_evaluated`` — never zero, an estimate, or another stage's
value.
"""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

SCHEMA_VERSION = 1
CANONICAL_STAGES = 8
NOT_EVALUATED = "not_evaluated"
HASH_EXCLUDED_KEYS = ("plan_hash", "slot_cap_requested", "slot_cap_ceiling")

PLAN_BEGIN = re.compile(r"<!--\s*wp-plan:begin\s+(.*?)-->")
PLAN_END = re.compile(r"<!--\s*wp-plan:end\s*-->")
AMENDMENT_BEGIN = re.compile(r"<!--\s*wp-plan-amendment:begin\s+(.*?)-->")
AMENDMENT_END = re.compile(r"<!--\s*wp-plan-amendment:end\s*-->")
LEDGER_BEGIN = re.compile(r"<!--\s*wp-ledger:begin\s*-->")
LEDGER_END = re.compile(r"<!--\s*wp-ledger:end\s*-->")
ATTRIBUTE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)")
LINE_ID_HEADER = re.compile(r"(?m)^\s*`?line_id`?\s*[:=]\s*(\S+)")
RUN_ID_HEADER = re.compile(r"(?m)^\s*`?run_id`?\s*[:=]\s*(\S+)")

KNOWN_EVENTS = (
    "plan",
    "dispatch",
    "settle",
    "verdict",
    "retry",
    "integrate",
    "stage-close",
    "wp_failed",
)


class InputError(Exception):
    """Unreadable, unparseable, or invalid input (exit 2)."""


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise InputError("cannot read %s: %s" % (path, exc))


def _fence_body(text, begin_match, end_pattern, label):
    end_match = end_pattern.search(text, begin_match.end())
    if end_match is None:
        raise InputError("unterminated %s fence" % label)
    return text[begin_match.end() : end_match.start()]


def _attributes(header):
    return dict(ATTRIBUTE.findall(header or ""))


def parse_plan_fences(spine_text):
    fences = []
    for match in PLAN_BEGIN.finditer(spine_text or ""):
        attributes = _attributes(match.group(1))
        try:
            stage = attributes["stage"]
            stage_attempt = int(attributes["stage_attempt"])
        except (KeyError, ValueError):
            raise InputError("malformed wp-plan fence header: %r" % match.group(1))
        body = _fence_body(spine_text, match, PLAN_END, "wp-plan")
        try:
            plan = json.loads(body)
        except ValueError as exc:
            raise InputError("wp-plan fence body is not valid JSON: %s" % exc)
        if not isinstance(plan, dict):
            raise InputError("wp-plan fence body must be a JSON object")
        fences.append(
            {"stage": stage, "stage_attempt": stage_attempt, "plan": plan}
        )
    return fences


def parse_amendment_fences(spine_text):
    fences = []
    for match in AMENDMENT_BEGIN.finditer(spine_text or ""):
        attributes = _attributes(match.group(1))
        try:
            stage = attributes["stage"]
            stage_attempt = int(attributes["stage_attempt"])
            seq = int(attributes["seq"])
        except (KeyError, ValueError):
            raise InputError(
                "malformed wp-plan-amendment fence header: %r" % match.group(1)
            )
        body = _fence_body(spine_text, match, AMENDMENT_END, "wp-plan-amendment")
        try:
            amendment = json.loads(body)
        except ValueError as exc:
            raise InputError(
                "wp-plan-amendment fence body is not valid JSON: %s" % exc
            )
        if not isinstance(amendment, dict):
            raise InputError("wp-plan-amendment fence body must be a JSON object")
        fences.append(
            {
                "stage": stage,
                "stage_attempt": stage_attempt,
                "seq": seq,
                "amendment": amendment,
            }
        )
    return fences


def parse_ledger(spine_text):
    events = []
    for match in LEDGER_BEGIN.finditer(spine_text or ""):
        body = _fence_body(spine_text, match, LEDGER_END, "wp-ledger")
        for line in body.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except ValueError as exc:
                raise InputError("wp-ledger line is not valid JSON: %s" % exc)
            if not isinstance(event, dict):
                raise InputError("wp-ledger line must be a JSON object")
            events.append(event)
    return events


def read_spine(path):
    text = _read_text(path)
    return {
        "text": text,
        "plan_fences": parse_plan_fences(text),
        "amendments": parse_amendment_fences(text),
        "ledger": parse_ledger(text),
    }


def _attempt_value(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _stage_of(wp_id):
    if not isinstance(wp_id, str) or "-wp" not in wp_id:
        return None
    return wp_id.split("-wp", 1)[0]


def _plan_for_attempt(document, stage, attempt):
    candidates = [
        fence
        for fence in document["plan_fences"]
        if fence["stage"] == stage and fence["stage_attempt"] == attempt
    ]
    if not candidates:
        return None
    return candidates[-1]["plan"]


def _amendments_for_attempt(document, stage, attempt):
    return [
        fence
        for fence in document["amendments"]
        if fence["stage"] == stage and fence["stage_attempt"] == attempt
    ]


def _effective_plan(plan, amendments):
    effective = copy.deepcopy(plan)
    for fence in sorted(
        amendments, key=lambda item: item.get("seq", 0)
    ):
        amendment = fence["amendment"]
        packages = effective.get("packages") or []
        by_id = {
            package.get("wp_id"): offset
            for offset, package in enumerate(packages)
        }
        for record in amendment.get("packages", []):
            wp_id = record.get("wp_id")
            copied = copy.deepcopy(record)
            if wp_id in by_id:
                packages[by_id[wp_id]] = copied
            else:
                by_id[wp_id] = len(packages)
                packages.append(copied)
        effective["packages"] = packages
        if amendment.get("plan_hash"):
            effective["plan_hash"] = amendment["plan_hash"]
    return effective


def _target_attempt(document, stage, requested):
    if requested is not None:
        return requested
    attempts = []
    for fence in document["plan_fences"]:
        if fence["stage"] == stage:
            attempts.append(fence["stage_attempt"])
    for event in document["ledger"]:
        if event.get("event") == "plan" and event.get("stage") == stage:
            value = _attempt_value(event.get("stage_attempt"))
            if value is not None:
                attempts.append(value)
        if event.get("event") == "dispatch" and _stage_of(
            event.get("wp_id")
        ) == stage:
            value = _attempt_value(event.get("stage_attempt"))
            if value is not None:
                attempts.append(value)
    return max(attempts) if attempts else 1


def _attempt_records(document):
    """Pair dispatch → settle → verdict in ledger order.

    ``settle`` and ``verdict`` events carry no stage attempt (E4); they attach
    to the oldest matching dispatch record that is not yet paired, which is the
    attempt that produced them because the ledger is append-only.
    """
    records = {}
    integrations = {}
    closes = {}
    active_stage = None
    sequence = 0

    def first_unsettled(wp_id):
        for record in records.get(wp_id, []):
            if record["settle"] is None:
                return record
        return None

    def first_unverdicted(wp_id):
        candidates = records.get(wp_id, [])
        with_settle = [
            record
            for record in candidates
            if record["settle"] is not None and record["verdict"] is None
        ]
        if with_settle:
            return with_settle[0]
        for record in candidates:
            if record["verdict"] is None:
                return record
        return None

    def latest(wp_id):
        candidates = records.get(wp_id, [])
        return candidates[-1] if candidates else None

    for event in document["ledger"]:
        kind = event.get("event")
        if kind not in KNOWN_EVENTS:
            continue
        if kind == "plan":
            stage = event.get("stage")
            if isinstance(stage, str) and stage:
                active_stage = stage
        elif kind == "dispatch":
            wp_id = event.get("wp_id")
            stage = _stage_of(wp_id)
            if stage:
                active_stage = stage
            sequence += 1
            record = {
                "wp_id": wp_id,
                "stage": stage,
                "stage_attempt": _attempt_value(event.get("stage_attempt")),
                "wp_attempt": _attempt_value(event.get("wp_attempt")),
                "dispatch": event,
                "settle": None,
                "verdict": None,
                "retry": False,
                "failed": False,
                "sequence": sequence,
            }
            records.setdefault(wp_id, []).append(record)
        elif kind == "settle":
            record = first_unsettled(event.get("wp_id"))
            if record is not None:
                record["settle"] = event
        elif kind == "verdict":
            record = first_unverdicted(event.get("wp_id"))
            if record is not None:
                record["verdict"] = event
        elif kind == "retry":
            record = latest(event.get("wp_id"))
            if record is not None:
                record["retry"] = True
        elif kind == "wp_failed":
            record = latest(event.get("wp_id"))
            if record is not None:
                record["failed"] = True
        elif kind in ("integrate", "stage-close"):
            attempt = _attempt_value(event.get("stage_attempt"))
            if active_stage is None or attempt is None:
                continue
            bucket = integrations if kind == "integrate" else closes
            bucket.setdefault((active_stage, attempt), []).append(event)
    return records, integrations, closes


def _duration(record):
    start = record["dispatch"].get("started_at")
    settle = record["settle"]
    end = settle.get("ended_at") if settle else None
    if not (_is_number(start) and _is_number(end)):
        return None
    if end < start:
        return None
    return end - start


def _verified_record(records, wp_id, attempt):
    candidates = [
        record
        for record in records.get(wp_id, [])
        if record["stage_attempt"] == attempt
        and record["verdict"] is not None
        and record["verdict"].get("verdict") == "pass"
    ]
    return candidates[-1] if candidates else None


def _target_records(records, stage, attempt):
    return [
        record
        for wp_id in records
        for record in records[wp_id]
        if record["stage"] == stage and record["stage_attempt"] == attempt
    ]


def _as_int(value):
    return value if _is_number(value) else None


def _wall_clock(records, u4_at):
    dispatches = [record["dispatch"] for record in records]
    if not dispatches:
        return NOT_EVALUATED
    starts = [event.get("started_at") for event in dispatches]
    if any(not _is_number(start) for start in starts):
        return NOT_EVALUATED
    if not _is_number(u4_at):
        return NOT_EVALUATED
    first = min(starts)
    if u4_at < first:
        return NOT_EVALUATED
    return u4_at - first


def _packages_for_critical_path(effective_plan):
    if not effective_plan:
        return None
    packages = [
        package
        for package in effective_plan.get("packages", [])
        if not package.get("superseded_by")
    ]
    return packages or None


def _critical_path(packages, records, attempt):
    if not packages:
        return NOT_EVALUATED
    by_id = {}
    for package in packages:
        wp_id = package.get("wp_id")
        if not wp_id:
            return NOT_EVALUATED
        verified = _verified_record(records, wp_id, attempt)
        duration = _duration(verified) if verified else None
        if duration is None:
            return NOT_EVALUATED
        by_id[wp_id] = {
            "duration": duration,
            "depends_on": package.get("depends_on") or [],
        }
    order = []
    visiting = set()
    visited = set()

    def visit(node):
        if node in visited:
            return True
        if node in visiting:
            return False
        visiting.add(node)
        for dependency in by_id[node]["depends_on"]:
            if dependency not in by_id:
                return False
            if not visit(dependency):
                return False
        visiting.discard(node)
        visited.add(node)
        order.append(node)
        return True

    for node in sorted(by_id):
        if not visit(node):
            return NOT_EVALUATED
    longest = {}
    for node in order:
        best = 0
        for dependency in by_id[node]["depends_on"]:
            best = max(best, longest[dependency])
        longest[node] = by_id[node]["duration"] + best
    return max(longest.values()) if longest else NOT_EVALUATED


def _max_concurrent(records):
    intervals = []
    for record in records:
        start = record["dispatch"].get("started_at")
        settle = record["settle"]
        end = settle.get("ended_at") if settle else None
        if not (_is_number(start) and _is_number(end)) or end < start:
            return NOT_EVALUATED
        intervals.append((start, end))
    if not intervals:
        return NOT_EVALUATED
    points = []
    for start, end in intervals:
        points.append((start, 1))
        points.append((end, -1))
    # Half-open intervals: an end at t does not overlap a start at t.
    points.sort(key=lambda item: (item[0], item[1]))
    running = 0
    maximum = 0
    for _, delta in points:
        running += delta
        maximum = max(maximum, running)
    return maximum


def _parallelism_efficiency(
    packages, records, attempt, wall_clock, max_concurrent
):
    if not packages:
        return NOT_EVALUATED
    durations = []
    for package in packages:
        verified = _verified_record(records, package.get("wp_id"), attempt)
        duration = _duration(verified) if verified else None
        if duration is None:
            return NOT_EVALUATED
        durations.append(duration)
    if not _is_number(wall_clock) or wall_clock <= 0:
        return NOT_EVALUATED
    if not _is_number(max_concurrent) or max_concurrent <= 0:
        return NOT_EVALUATED
    return sum(durations) / (wall_clock * max_concurrent)


def _stage_attempt_pairs(records):
    pairs = set()
    for wp_records in records.values():
        for record in wp_records:
            if record["stage"] and record["stage_attempt"] is not None:
                pairs.add((record["stage"], record["stage_attempt"]))
    return len(pairs)


def _integration_order(packages, integrations, stage, attempt):
    events = integrations.get((stage, attempt), [])
    if events:
        order = events[-1].get("order")
        if isinstance(order, list) and all(
            isinstance(item, str) for item in order
        ):
            return list(order)
    if not packages:
        return NOT_EVALUATED
    by_id = {
        package["wp_id"]: package
        for package in packages
        if package.get("wp_id")
    }
    indegree = {
        node: len(package.get("depends_on") or [])
        for node, package in by_id.items()
    }
    if any(
        dependency not in by_id
        for package in by_id.values()
        for dependency in (package.get("depends_on") or [])
    ):
        return NOT_EVALUATED
    depth = {node: 0 for node in by_id}
    ready = sorted(node for node, count in indegree.items() if count == 0)
    seen = 0
    while ready:
        node = ready.pop(0)
        seen += 1
        for other, package in by_id.items():
            if node in (package.get("depends_on") or []):
                depth[other] = max(depth[other], depth[node] + 1)
                indegree[other] -= 1
                if indegree[other] == 0:
                    ready.append(other)
        ready.sort()
    if seen != len(by_id):
        return NOT_EVALUATED
    return [
        node
        for _, node in sorted(
            (depth[node], node) for node in by_id
        )
    ]


def _dispatch_order(records):
    ordered = sorted(
        records,
        key=lambda record: (
            _attempt_value(record["dispatch"].get("dispatch_order")) or 0,
            record["sequence"],
        ),
    )
    return [record["wp_id"] for record in ordered]


def _token_cost(records):
    dispatches = [record["dispatch"] for record in records]
    if not dispatches:
        return NOT_EVALUATED
    values = [event.get("token_cost") for event in dispatches]
    if not all(_is_number(value) for value in values):
        return NOT_EVALUATED
    return sum(values)


def _decision_fields(effective_plan, plan_events):
    plan = effective_plan or {}
    decision = plan.get("decision")
    pattern = plan.get("pattern")
    slot_cap = plan.get("slot_cap")
    if isinstance(decision, str) and isinstance(pattern, str) and _is_number(
        slot_cap
    ):
        return decision, pattern, slot_cap
    if plan_events:
        latest = plan_events[-1]
        if not isinstance(decision, str):
            decision = latest.get("decision")
        if not isinstance(pattern, str):
            pattern = latest.get("pattern")
        if not _is_number(slot_cap):
            slot_cap = latest.get("slot_cap")
    decision = decision if isinstance(decision, str) else NOT_EVALUATED
    pattern = pattern if isinstance(pattern, str) else NOT_EVALUATED
    slot_cap = slot_cap if _is_number(slot_cap) else NOT_EVALUATED
    return decision, pattern, slot_cap


def _line_identity(document, effective_plan, spine_path):
    line_id = (effective_plan or {}).get("line_id")
    run_id = (effective_plan or {}).get("run_id")
    if not isinstance(line_id, str) or not line_id:
        match = LINE_ID_HEADER.search(document["text"])
        line_id = match.group(1) if match else Path(spine_path).stem
    if not isinstance(run_id, str) or not run_id:
        match = RUN_ID_HEADER.search(document["text"])
        run_id = match.group(1) if match else NOT_EVALUATED
    return line_id, run_id


def _verdicts(records):
    items = []
    for record in records:
        event = record["verdict"]
        if event is None:
            continue
        items.append(
            {
                "wp_id": record["wp_id"],
                "wp_attempt": record["wp_attempt"],
                "verdict": event.get("verdict"),
                "verifier_execution": event.get("verifier_execution"),
                "evidence_ptr": event.get("evidence_ptr"),
                "at": event.get("at"),
            }
        )
    items.sort(
        key=lambda item: (
            item["wp_id"] or "",
            item["wp_attempt"] if item["wp_attempt"] is not None else 0,
        )
    )
    return items


def _evidence_refs(plan_events, records):
    refs = set()
    for event in plan_events:
        pointer = event.get("gate_evidence")
        if isinstance(pointer, str) and pointer:
            refs.add(pointer)
    for record in records:
        if record["settle"]:
            pointer = record["settle"].get("result_ptr")
            if isinstance(pointer, str) and pointer:
                refs.add(pointer)
        if record["verdict"]:
            pointer = record["verdict"].get("evidence_ptr")
            if isinstance(pointer, str) and pointer:
                refs.add(pointer)
    return sorted(refs)


def build_report(document, stage, attempt, spine_path, args):
    plan = _plan_for_attempt(document, stage, attempt)
    amendments = _amendments_for_attempt(document, stage, attempt)
    effective_plan = _effective_plan(plan, amendments) if plan else None
    packages = _packages_for_critical_path(effective_plan)

    records, integrations, closes = _attempt_records(document)
    target = _target_records(records, stage, attempt)
    plan_events = [
        event
        for event in document["ledger"]
        if event.get("event") == "plan"
        and event.get("stage") == stage
        and _attempt_value(event.get("stage_attempt")) == attempt
    ]

    u4_at = args.stage_u4_at
    if u4_at is None:
        close_events = closes.get((stage, attempt), [])
        if close_events:
            candidate = close_events[-1].get("stage_u4_at")
            if _is_number(candidate):
                u4_at = candidate

    wall_clock = _wall_clock(target, u4_at)
    critical_path = _critical_path(packages, records, attempt)
    max_concurrent = _max_concurrent(target)
    efficiency = _parallelism_efficiency(
        packages, records, attempt, wall_clock, max_concurrent
    )

    stage_attempts = _stage_attempt_pairs(records)
    stage_executions = stage_attempts / CANONICAL_STAGES
    retries_package = sum(1 for record in target if record["retry"])
    retries_stage = attempt - 1

    manual_interventions = (
        args.manual_interventions
        if args.manual_interventions is not None
        else NOT_EVALUATED
    )
    sessions = args.sessions if args.sessions is not None else NOT_EVALUATED
    if (
        _is_number(manual_interventions)
        and _is_number(sessions)
        and sessions > 0
    ):
        intervention_rate = manual_interventions / sessions
    else:
        intervention_rate = NOT_EVALUATED

    decision, pattern, slot_cap = _decision_fields(effective_plan, plan_events)
    line_id, run_id = _line_identity(document, effective_plan, spine_path)

    report = {
        "schema_version": SCHEMA_VERSION,
        "line_id": line_id,
        "run_id": run_id,
        "stage": stage,
        "stage_attempt": attempt,
        "decision": decision,
        "pattern": pattern,
        "slot_cap": slot_cap,
        "dispatch_order": _dispatch_order(target),
        "integration_order": _integration_order(
            packages, integrations, stage, attempt
        ),
        "wall_clock_seconds": wall_clock,
        "critical_path_seconds": critical_path,
        "parallelism_efficiency": efficiency,
        "max_concurrent": max_concurrent,
        "overlap": _is_number(max_concurrent) and max_concurrent >= 2,
        "retries_package": retries_package,
        "retries_stage": retries_stage,
        "stage_attempts": stage_attempts,
        "canonical_stages": CANONICAL_STAGES,
        "stage_executions_per_canonical": stage_executions,
        "manual_interventions": manual_interventions,
        "sessions": sessions,
        "manual_interventions_per_session": intervention_rate,
        "token_cost": _token_cost(target),
        "verdicts": _verdicts(target),
        "evidence_refs": _evidence_refs(plan_events, target),
    }
    return report


def _format_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "none"
    return str(value)


METRIC_ROWS = (
    "decision",
    "pattern",
    "slot_cap",
    "wall_clock_seconds",
    "critical_path_seconds",
    "parallelism_efficiency",
    "max_concurrent",
    "overlap",
    "retries_package",
    "retries_stage",
    "stage_attempts",
    "canonical_stages",
    "stage_executions_per_canonical",
    "manual_interventions",
    "sessions",
    "manual_interventions_per_session",
    "token_cost",
)


def render_markdown(report):
    lines = [
        "# Stage coordination report — %s %s a%s"
        % (report["line_id"], report["stage"], report["stage_attempt"]),
        "",
        "Derived from the line state spine. Metrics with a missing source are "
        "`%s`." % NOT_EVALUATED,
        "",
        "| Metric | Value |",
        "|---|---|",
    ]
    for key in METRIC_ROWS:
        lines.append("| %s | %s |" % (key, _format_value(report[key])))
    lines += ["", "## Dispatch order", ""]
    if report["dispatch_order"]:
        lines += [
            "%d. %s" % (index, wp_id)
            for index, wp_id in enumerate(report["dispatch_order"], start=1)
        ]
    else:
        lines.append("`%s`" % NOT_EVALUATED)
    lines += ["", "## Integration order", ""]
    if isinstance(report["integration_order"], list):
        lines += ["- %s" % wp_id for wp_id in report["integration_order"]]
    else:
        lines.append("`%s`" % NOT_EVALUATED)
    lines += [
        "",
        "## Verdicts",
        "",
        "| Package | Attempt | Verdict | Evidence |",
        "|---|---|---|---|",
    ]
    if report["verdicts"]:
        for item in report["verdicts"]:
            lines.append(
                "| %s | %s | %s | %s |"
                % (
                    item["wp_id"],
                    _format_value(item["wp_attempt"]),
                    _format_value(item["verdict"]),
                    item["evidence_ptr"] or NOT_EVALUATED,
                )
            )
    else:
        lines.append("| %s | %s | %s | %s |" % (
            NOT_EVALUATED,
            NOT_EVALUATED,
            NOT_EVALUATED,
            NOT_EVALUATED,
        ))
    lines += ["", "## Evidence paths", ""]
    if report["evidence_refs"]:
        lines += ["- %s" % path for path in report["evidence_refs"]]
    else:
        lines.append("- `%s`" % NOT_EVALUATED)
    lines.append("")
    return "\n".join(lines)


def write_reports(report, out_dir):
    directory = Path(out_dir)
    stem = "%s-%s-a%s-coordination" % (
        report["line_id"],
        report["stage"],
        report["stage_attempt"],
    )
    try:
        directory.mkdir(parents=True, exist_ok=True)
        json_path = directory / (stem + ".json")
        md_path = directory / (stem + ".md")
        json_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        md_path.write_text(render_markdown(report), encoding="utf-8")
    except OSError as exc:
        raise InputError("cannot write report: %s" % exc)
    return md_path, json_path


def run(args):
    document = read_spine(args.spine)
    attempt = _target_attempt(document, args.stage, args.stage_attempt)
    if attempt < 1:
        raise InputError("--stage-attempt must be >= 1")
    report = build_report(document, args.stage, attempt, args.spine, args)
    write_reports(report, args.out_dir)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Derive a Feature 070 stage coordination report from the spine."
    )
    parser.add_argument("--spine", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--stage-attempt", type=int, default=None)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--stage-u4-at", type=int, default=None)
    parser.add_argument("--manual-interventions", type=int, default=None)
    parser.add_argument("--sessions", type=int, default=None)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.stage_attempt is not None and args.stage_attempt < 1:
        parser.error("--stage-attempt must be >= 1")
    if (
        args.manual_interventions is not None
        and args.manual_interventions < 0
    ):
        parser.error("--manual-interventions must be >= 0")
    if args.sessions is not None and args.sessions < 0:
        parser.error("--sessions must be >= 0")
    try:
        return run(args)
    except InputError as exc:
        sys.stderr.write("wp-report.py: %s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
