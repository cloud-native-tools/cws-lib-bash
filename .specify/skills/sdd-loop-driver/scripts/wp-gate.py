#!/usr/bin/env python3
"""wp-gate.py — deterministic Work Package decomposition gate.

Reads a Work Package plan from a line state spine (or from ``--plan-json`` for
fixture use), validates it, and emits the WG-04 JSON verdict. It never
dispatches, never writes the spine, and never modifies the plan. The only file
it writes is the optional ``--json-out`` evidence record.

The plan and its amendments are fences in the existing line state spine:

    <!-- wp-plan:begin stage=<stage> stage_attempt=<n> -->
    <!-- wp-plan-amendment:begin stage=<stage> stage_attempt=<n> seq=<n> -->
    <!-- wp-ledger:begin --> ... <!-- wp-ledger:end -->

Exit codes:
  0 = admit or single-package
  1 = reject (plan-level findings)
  2 = input, parse, or I/O error, or a check the gate cannot evaluate
      (the driver treats exit 2 as decomposition-unavailable, never as a
      plan rejection)

Standard library only, Python >= 3.8.
"""

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import time

SCHEMA_VERSION = 1
STAGES = ("plan", "implement", "review", "analyze", "clarify")
DECISIONS = ("decomposed", "single-package", "disabled", "fallback")
GATE_VERDICTS = ("admit", "single-package", "no-gate-run")
RULES = (
    "decompose-plan-v1",
    "decompose-implement-v1",
    "decompose-review-v1",
    "decompose-investigation-v1",
)
PATTERNS = ("parallel", "serial", "iteration")
KINDS = ("read-only", "write")
BOUNDED_UNITS = ("tasks", "clauses", "artifacts", "acceptance")
CHECK_NAMES = ("plan", "preflight", "retry")
TIE_BREAK = "wp_id-lexicographic"
HASH_EXCLUDED_KEYS = ("plan_hash", "slot_cap_requested", "slot_cap_ceiling")
# WG-13 advisories do not block dispatch; every other finding is blocking.
ADVISORY_CODES = ("not-beneficial",)

PLAN_BEGIN = re.compile(r"<!--\s*wp-plan:begin\s+(.*?)-->")
PLAN_END = re.compile(r"<!--\s*wp-plan:end\s*-->")
AMENDMENT_BEGIN = re.compile(r"<!--\s*wp-plan-amendment:begin\s+(.*?)-->")
AMENDMENT_END = re.compile(r"<!--\s*wp-plan-amendment:end\s*-->")
LEDGER_BEGIN = re.compile(r"<!--\s*wp-ledger:begin\s*-->")
LEDGER_END = re.compile(r"<!--\s*wp-ledger:end\s*-->")
ATTRIBUTE = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=([^\s]+)")
HEX_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")


class InputError(Exception):
    """Unreadable, unparseable, or incomplete input (exit 2)."""


def _read_text(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise InputError("cannot read %s: %s" % (path, exc))


def _read_json_object(path, label):
    text = _read_text(path)
    try:
        value = json.loads(text)
    except ValueError as exc:
        raise InputError("%s is not valid JSON: %s" % (label, exc))
    if not isinstance(value, dict):
        raise InputError("%s must be a JSON object" % label)
    return value


def _attributes(header):
    return dict(ATTRIBUTE.findall(header or ""))


def _fence_body(text, begin_match, end_pattern, label):
    end_match = end_pattern.search(text, begin_match.end())
    if end_match is None:
        raise InputError("unterminated %s fence" % label)
    return text[begin_match.end():end_match.start()]


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


def _attempt_value(event):
    value = event.get("stage_attempt")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def highest_stage_attempt(document):
    attempts = []
    for fence in document.get("plan_fences", []):
        attempts.append(fence["stage_attempt"])
    for fence in document.get("amendments", []):
        attempts.append(fence["stage_attempt"])
    for event in document.get("ledger", []):
        value = _attempt_value(event)
        if value is not None:
            attempts.append(value)
    return max(attempts) if attempts else 0


def effective_plan(plan, amendments):
    """Apply amendment bodies (raw dicts) in ``seq`` order.

    A package record whose ``wp_id`` exists replaces that record; a new
    ``wp_id`` is appended. The latest amendment's ``plan_hash`` becomes the
    effective recorded hash.
    """
    effective = copy.deepcopy(plan)
    for amendment in sorted(amendments, key=lambda body: body.get("seq", 0)):
        packages = effective.get("packages") or []
        by_id = {package.get("wp_id"): package for package in packages}
        for record in amendment.get("packages", []):
            wp_id = record.get("wp_id")
            copied = copy.deepcopy(record)
            if wp_id in by_id:
                index = next(
                    offset
                    for offset, package in enumerate(packages)
                    if package.get("wp_id") == wp_id
                )
                packages[index] = copied
            else:
                packages.append(copied)
            by_id[wp_id] = copied
        effective["packages"] = packages
        effective["plan_hash"] = amendment.get("plan_hash")
    return effective


def _is_timestamp_key(key):
    return key == "at" or key.endswith("_at")


def _strip_hash_exclusions(value):
    if isinstance(value, dict):
        return {
            key: _strip_hash_exclusions(item)
            for key, item in value.items()
            if key not in HASH_EXCLUDED_KEYS and not _is_timestamp_key(key)
        }
    if isinstance(value, list):
        return [_strip_hash_exclusions(item) for item in value]
    return value


def canonical_plan_hash(plan):
    body = _strip_hash_exclusions(plan)
    encoded = json.dumps(
        body, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _is_text(value):
    return isinstance(value, str) and value.strip() != ""


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_string_list(value):
    return isinstance(value, list) and all(_is_text(item) for item in value)


def _finding(code, wp_id=None, detail=""):
    return {"code": code, "wp_id": wp_id, "detail": detail}


def _sort_findings(findings):
    return sorted(
        findings, key=lambda item: (item["code"], item["wp_id"] or "", item["detail"])
    )


def _schema_check_package(package, plan_stage, index):
    findings = []
    label = "packages[%d]" % index
    if not isinstance(package, dict):
        return [_finding("schema-missing", None, "%s is not an object" % label)]
    wp_id = package.get("wp_id")
    if not _is_text(wp_id):
        findings.append(_finding("schema-missing", None, "%s.wp_id" % label))
        wp_id = None
    expected = (
        ("objective", _is_text),
        ("stage", lambda value: _is_text(value) and value == plan_stage),
        ("kind", lambda value: value in KINDS),
        ("source_refs", _is_string_list),
        ("inputs", lambda value: isinstance(value, list) and _is_string_list(value)),
        ("outputs", lambda value: _is_string_list(value) and bool(value)),
        ("owned_paths", lambda value: isinstance(value, list) and _is_string_list(value)),
        (
            "read_only_paths",
            lambda value: isinstance(value, list) and _is_string_list(value),
        ),
        ("depends_on", lambda value: isinstance(value, list) and _is_string_list(value)),
        ("parallel_safe", lambda value: isinstance(value, bool)),
        ("max_turns", lambda value: _is_int(value) and value > 0),
        ("bounded_by", lambda value: isinstance(value, dict)),
        ("acceptance", lambda value: isinstance(value, list) and bool(value)),
        ("sentinel", _is_text),
        ("evidence", _is_text),
        ("seat", lambda value: isinstance(value, dict)),
        ("resources", lambda value: isinstance(value, dict)),
    )
    for field, predicate in expected:
        if field not in package or not predicate(package[field]):
            findings.append(
                _finding("schema-missing", wp_id, "%s.%s" % (label, field))
            )
    if "intermediate_outputs" in package and not (
        isinstance(package["intermediate_outputs"], list)
        and _is_string_list(package["intermediate_outputs"])
    ):
        findings.append(
            _finding(
                "schema-missing", wp_id, "%s.intermediate_outputs" % label
            )
        )
    bounded = package.get("bounded_by")
    if isinstance(bounded, dict):
        if bounded.get("unit") not in BOUNDED_UNITS:
            findings.append(
                _finding("schema-missing", wp_id, "%s.bounded_by.unit" % label)
            )
        count = bounded.get("count")
        # WG-09 owns the non-positive value; WG-06 only rejects a wrong type.
        if not _is_int(count):
            findings.append(
                _finding("schema-missing", wp_id, "%s.bounded_by.count" % label)
            )
    acceptance = package.get("acceptance")
    if isinstance(acceptance, list) and acceptance:
        seen = set()
        for offset, criterion in enumerate(acceptance):
            if not isinstance(criterion, dict):
                findings.append(
                    _finding(
                        "schema-missing",
                        wp_id,
                        "%s.acceptance[%d]" % (label, offset),
                    )
                )
                continue
            for key in ("id", "check", "evidence"):
                if not _is_text(criterion.get(key)):
                    findings.append(
                        _finding(
                            "schema-missing",
                            wp_id,
                            "%s.acceptance[%d].%s" % (label, offset, key),
                        )
                    )
            criterion_id = criterion.get("id")
            if _is_text(criterion_id):
                if criterion_id in seen:
                    findings.append(
                        _finding(
                            "schema-missing",
                            wp_id,
                            "%s.acceptance duplicate id %s" % (label, criterion_id),
                        )
                    )
                seen.add(criterion_id)
    seat = package.get("seat")
    if isinstance(seat, dict):
        for key in ("role", "stage", "type"):
            if not _is_text(seat.get(key)):
                findings.append(
                    _finding("schema-missing", wp_id, "%s.seat.%s" % (label, key))
                )
    resources = package.get("resources")
    if isinstance(resources, dict):
        for key in ("ports", "tmp_dir", "cache_dir"):
            value = resources.get(key)
            if not _is_text(value):
                findings.append(
                    _finding(
                        "schema-missing", wp_id, "%s.resources.%s" % (label, key)
                    )
                )
        shared = resources.get("shared_readonly")
        if not (isinstance(shared, list) and _is_string_list(shared)):
            findings.append(
                _finding(
                    "schema-missing",
                    wp_id,
                    "%s.resources.shared_readonly" % label,
                )
            )
    superseded = package.get("superseded_by")
    if superseded is not None and not _is_string_list(superseded):
        findings.append(
            _finding("schema-missing", wp_id, "%s.superseded_by" % label)
        )
    return findings


def validate_plan_schema(plan, stage, stage_attempt=None):
    """Required-field, type, and closed-enum checks (WG-06, V-PLAN.1/2)."""
    findings = []
    if not isinstance(plan, dict):
        return [_finding("schema-missing", None, "plan is not an object")]

    required = (
        ("schema_version", lambda value: value == SCHEMA_VERSION),
        ("line_id", _is_text),
        ("run_id", _is_text),
        ("stage", lambda value: value in STAGES),
        ("stage_attempt", lambda value: _is_int(value) and value >= 1),
        ("decision", lambda value: value in DECISIONS),
        ("gate_verdict", lambda value: value in GATE_VERDICTS),
        ("reason", _is_text),
        ("rule", lambda value: value is None or value in RULES),
        (
            "source_artifacts",
            lambda value: isinstance(value, list) and _is_string_list(value),
        ),
        ("required_outputs", lambda value: _is_string_list(value)),
        ("integrator_outputs", lambda value: isinstance(value, list) and _is_string_list(value)),
        # WG-11 owns the closed pattern set and reports pattern-mismatch,
        # including the excluded `continuous` value.
        ("pattern", _is_text),
        ("tie_break", lambda value: value == TIE_BREAK),
        # WG-16 (preflight) owns the 1..ceiling bound; WG-06 checks the type only.
        ("slot_cap", lambda value: _is_int(value)),
        ("packages", lambda value: isinstance(value, list) and bool(value)),
        ("plan_hash", lambda value: _is_text(value) and bool(HEX_HASH.match(value))),
    )
    for field, predicate in required:
        if field not in plan or not predicate(plan[field]):
            findings.append(_finding("schema-missing", None, "plan.%s" % field))

    if plan.get("stage") != stage:
        findings.append(
            _finding(
                "schema-missing",
                None,
                "plan.stage %r does not match --stage %r" % (plan.get("stage"), stage),
            )
        )
    if stage_attempt is not None and plan.get("stage_attempt") != stage_attempt:
        findings.append(
            _finding(
                "schema-missing",
                None,
                "plan.stage_attempt %r does not match the selected attempt %r"
                % (plan.get("stage_attempt"), stage_attempt),
            )
        )

    pattern = plan.get("pattern")
    repair_loop = plan.get("repair_loop")
    # WG-11 owns the complete-repair_loop requirement for pattern=iteration;
    # the conditional field remains a schema violation in every other pattern.
    if pattern != "iteration" and repair_loop is not None:
        findings.append(
            _finding(
                "schema-missing",
                None,
                "plan.repair_loop is only valid with pattern=iteration",
            )
        )

    required_outputs = plan.get("required_outputs")
    integrator_outputs = plan.get("integrator_outputs")
    if (
        isinstance(required_outputs, list)
        and _is_string_list(required_outputs)
        and isinstance(integrator_outputs, list)
        and _is_string_list(integrator_outputs)
    ):
        for output in integrator_outputs:
            if output not in required_outputs:
                findings.append(
                    _finding(
                        "schema-missing",
                        None,
                        "integrator_outputs entry is not in required_outputs: %s"
                        % output,
                    )
                )

    decision = plan.get("decision")
    packages = plan.get("packages")
    if isinstance(packages, list) and packages:
        if decision == "decomposed":
            if plan.get("rule") is None:
                findings.append(
                    _finding("schema-missing", None, "decomposed requires rule")
                )
            if len(packages) < 2:
                findings.append(
                    _finding(
                        "schema-missing",
                        None,
                        "decomposed requires at least two packages",
                    )
                )
            if not plan.get("source_artifacts"):
                findings.append(
                    _finding(
                        "schema-missing",
                        None,
                        "decomposed requires source_artifacts",
                    )
                )
            if not plan.get("required_outputs"):
                findings.append(
                    _finding(
                        "schema-missing",
                        None,
                        "decomposed requires required_outputs",
                    )
                )
            if plan.get("gate_verdict") != "admit":
                findings.append(
                    _finding(
                        "schema-missing",
                        None,
                        "decomposed requires gate_verdict=admit",
                    )
                )
        elif decision in ("single-package", "disabled", "fallback"):
            expected_verdict = (
                "single-package" if decision == "single-package" else "no-gate-run"
            )
            if plan.get("rule") is not None:
                findings.append(
                    _finding(
                        "schema-missing", None, "%s requires rule=null" % decision
                    )
                )
            if len(packages) != 1:
                findings.append(
                    _finding(
                        "schema-missing",
                        None,
                        "%s requires exactly one package" % decision,
                    )
                )
            if plan.get("integrator_outputs"):
                findings.append(
                    _finding(
                        "schema-missing",
                        None,
                        "%s requires integrator_outputs=[]" % decision,
                    )
                )
            if plan.get("gate_verdict") != expected_verdict:
                findings.append(
                    _finding(
                        "schema-missing",
                        None,
                        "%s requires gate_verdict=%s"
                        % (decision, expected_verdict),
                    )
                )

    if isinstance(packages, list):
        for index, package in enumerate(packages):
            findings.extend(_schema_check_package(package, stage, index))
    return findings


def _known_dependency_graph(packages):
    ids = {package["wp_id"] for package in packages}
    return {
        package["wp_id"]: sorted(
            {dep for dep in package["depends_on"] if dep in ids}
        )
        for package in packages
    }


def _has_path(graph, start, target):
    pending = list(graph.get(start, []))
    seen = set()
    while pending:
        node = pending.pop()
        if node == target:
            return True
        if node in seen:
            continue
        seen.add(node)
        pending.extend(graph.get(node, []))
    return False


def _independent(graph, left, right):
    return not _has_path(graph, left, right) and not _has_path(
        graph, right, left
    )


def _independent_read_only_pair(packages, graph):
    read_only = [
        package["wp_id"]
        for package in packages
        if package["kind"] == "read-only"
    ]
    for offset, left in enumerate(read_only):
        for right in read_only[offset + 1:]:
            if _independent(graph, left, right):
                return True
    return False


def _graph_findings(packages):
    """WG-07 graph checks plus the WP-04 deterministic layers."""
    findings = []
    counts = {}
    for package in packages:
        counts[package["wp_id"]] = counts.get(package["wp_id"], 0) + 1
    duplicates = sorted(
        wp_id for wp_id, count in counts.items() if count > 1
    )
    for wp_id in duplicates:
        findings.append(_finding("dup-wp-id", wp_id, "duplicate wp_id"))

    known_ids = set(counts)
    dangling = []
    for package in packages:
        for dep in package["depends_on"]:
            if dep not in known_ids:
                dangling.append(dep)
                findings.append(
                    _finding(
                        "dangling-dep",
                        package["wp_id"],
                        "unknown dependency %s" % dep,
                    )
                )

    if duplicates:
        return findings, []

    graph = _known_dependency_graph(packages)
    indegree = {
        node: len(dependencies) for node, dependencies in graph.items()
    }
    ready = sorted(node for node, count in indegree.items() if count == 0)
    order = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for other, dependencies in graph.items():
            if node in dependencies:
                indegree[other] -= 1
                if indegree[other] == 0:
                    ready.append(other)
        ready.sort()
    if len(order) < len(graph):
        remaining = sorted(set(graph) - set(order))
        findings.append(
            _finding(
                "cycle",
                None,
                "dependency cycle among: %s" % ", ".join(remaining),
            )
        )
        return findings, []
    if dangling:
        return findings, []

    depth = {}
    for node in order:
        dependencies = [dep for dep in graph[node] if dep in depth]
        depth[node] = (
            0
            if not dependencies
            else 1 + max(depth[dep] for dep in dependencies)
        )
    layers = []
    if depth:
        for level in range(max(depth.values()) + 1):
            layers.append(
                sorted(node for node, value in depth.items() if value == level)
            )
    return findings, layers


def _consumed_by_dependent(packages, producer, output):
    reverse = {}
    for package in packages:
        for dep in package["depends_on"]:
            reverse.setdefault(dep, []).append(package["wp_id"])
    inputs = {package["wp_id"]: package["inputs"] for package in packages}
    pending = list(reverse.get(producer, []))
    seen = set()
    while pending:
        node = pending.pop()
        if node in seen:
            continue
        seen.add(node)
        if output in inputs.get(node, []):
            return True
        pending.extend(reverse.get(node, []))
    return False


def _output_findings(plan, packages):
    """WG-08 output coverage; integrator_outputs are excluded, not package-owned."""
    findings = []
    required = plan["required_outputs"]
    integrator = plan["integrator_outputs"]
    if not required:
        # E2 leaves required_outputs empty for non-decomposed decisions.
        return findings
    integrator_set = set(integrator)
    owners = {}
    for package in packages:
        for output in package["outputs"]:
            owners.setdefault(output, []).append(package["wp_id"])
    for output in required:
        if output in integrator_set:
            continue
        claimants = sorted(owners.get(output, []))
        if not claimants:
            findings.append(
                _finding(
                    "orphan-output",
                    None,
                    "required output owned by no package: %s" % output,
                )
            )
        else:
            for claimant in claimants[1:]:
                findings.append(
                    _finding(
                        "duplicate-output",
                        claimant,
                        "required output claimed by multiple packages: %s"
                        % output,
                    )
                )
    for package in packages:
        intermediates = package.get("intermediate_outputs") or []
        for output in package["outputs"]:
            if output in integrator_set:
                findings.append(
                    _finding(
                        "duplicate-output",
                        package["wp_id"],
                        "package claims integrator output: %s" % output,
                    )
                )
            elif output not in required and output not in intermediates:
                findings.append(
                    _finding(
                        "orphan-output",
                        package["wp_id"],
                        "output is neither required nor intermediate: %s"
                        % output,
                    )
                )
        for output in intermediates:
            if not _consumed_by_dependent(
                packages, package["wp_id"], output
            ):
                findings.append(
                    _finding(
                        "orphan-output",
                        package["wp_id"],
                        "intermediate output is not consumed by a dependent: %s"
                        % output,
                    )
                )
    return findings


def _kind_findings(packages):
    findings = []
    for package in packages:
        wp_id = package["wp_id"]
        kind = package["kind"]
        if kind == "read-only" and package["owned_paths"]:
            findings.append(
                _finding("kind-mismatch", wp_id, "read-only package owns paths")
            )
        elif kind == "write" and not package["owned_paths"]:
            findings.append(
                _finding("kind-mismatch", wp_id, "write package owns no paths")
            )
        if kind == "write" and package["parallel_safe"]:
            findings.append(
                _finding(
                    "kind-mismatch", wp_id, "write package is parallel_safe"
                )
            )
    return findings


def _bounded_findings(packages):
    findings = []
    for package in packages:
        bounded = package["bounded_by"]
        unit = bounded["unit"]
        count = bounded["count"]
        if not (_is_int(count) and count > 0):
            findings.append(
                _finding(
                    "unbounded",
                    package["wp_id"],
                    "bounded_by.count must be a positive integer",
                )
            )
        elif unit == "tasks" and count > 8:
            findings.append(
                _finding(
                    "unbounded",
                    package["wp_id"],
                    "tasks bound %d exceeds 8" % count,
                )
            )
        elif unit == "clauses" and count > 40:
            findings.append(
                _finding(
                    "unbounded",
                    package["wp_id"],
                    "clauses bound %d exceeds 40" % count,
                )
            )
    return findings


def _complete_repair_loop(plan):
    repair = plan.get("repair_loop")
    return (
        isinstance(repair, dict)
        and _is_int(repair.get("max_iterations"))
        and repair.get("max_iterations") > 0
        and _is_text(repair.get("stop_condition"))
        and _is_text(repair.get("findings_source"))
    )


def _pattern_findings(plan, packages, graph):
    """WG-11 pattern/graph compatibility."""
    findings = []
    pattern = plan.get("pattern")
    if pattern not in PATTERNS:
        findings.append(
            _finding(
                "pattern-mismatch",
                None,
                "pattern %r is not in the closed set %s"
                % (pattern, "/".join(PATTERNS)),
            )
        )
        return findings
    if pattern == "iteration":
        if not _complete_repair_loop(plan):
            findings.append(
                _finding(
                    "pattern-mismatch",
                    None,
                    "iteration requires a complete repair_loop",
                )
            )
        return findings
    if pattern == "parallel":
        if len(packages) < 2:
            findings.append(
                _finding(
                    "pattern-mismatch",
                    None,
                    "parallel requires at least two packages",
                )
            )
        for package in packages:
            if package["kind"] == "write":
                findings.append(
                    _finding(
                        "pattern-mismatch",
                        package["wp_id"],
                        "parallel cannot include a write package",
                    )
                )
            if not package["parallel_safe"]:
                findings.append(
                    _finding(
                        "pattern-mismatch",
                        package["wp_id"],
                        "parallel requires parallel_safe packages",
                    )
                )
        if len(packages) >= 2:
            ids = sorted(graph)
            for offset, left in enumerate(ids):
                for right in ids[offset + 1:]:
                    if not _independent(graph, left, right):
                        findings.append(
                            _finding(
                                "pattern-mismatch",
                                right,
                                "parallel requires independent packages "
                                "(dependency with %s)" % left,
                            )
                        )
    if pattern == "serial":
        if all(
            package["kind"] == "read-only" for package in packages
        ) and _independent_read_only_pair(packages, graph):
            findings.append(
                _finding(
                    "pattern-mismatch",
                    None,
                    "independent read-only packages require pattern=parallel",
                )
            )
    return findings


def _beneficial(plan, packages, graph, layers):
    """WG-13 benefit test; budgets are the declared max_turns weights."""
    if len(packages) < 2:
        return False
    if plan.get("slot_cap", 1) >= 2 and _independent_read_only_pair(
        packages, graph
    ):
        return True
    weights = {
        package["wp_id"]: package["max_turns"] for package in packages
    }
    if layers:
        critical = {}
        for layer in layers:
            for node in layer:
                dependencies = [
                    dep for dep in graph.get(node, []) if dep in critical
                ]
                critical[node] = weights[node] + (
                    max(critical[dep] for dep in dependencies)
                    if dependencies
                    else 0
                )
        if max(critical.values()) < sum(weights.values()):
            return True
    if plan.get("pattern") == "iteration" and _complete_repair_loop(plan):
        return True
    return False


def _select_plan(document, stage, stage_attempt):
    matches = [
        fence
        for fence in document["plan_fences"]
        if fence["stage"] == stage and fence["stage_attempt"] == stage_attempt
    ]
    if not matches:
        raise InputError(
            "no wp-plan fence for stage '%s' stage_attempt %s"
            % (stage, stage_attempt)
        )
    if len(matches) > 1:
        raise InputError(
            "duplicate wp-plan fences for stage '%s' stage_attempt %s"
            % (stage, stage_attempt)
        )
    return matches[0]["plan"]


def _amendments_for(document, stage, stage_attempt):
    selected = [
        fence["amendment"]
        for fence in document["amendments"]
        if fence["stage"] == stage and fence["stage_attempt"] == stage_attempt
    ]
    seen = set()
    for amendment in selected:
        seq = amendment.get("seq")
        if not _is_int(seq) or seq < 1:
            raise InputError("wp-plan-amendment lacks a positive integer seq")
        if seq in seen:
            raise InputError("duplicate wp-plan-amendment seq %s" % seq)
        seen.add(seq)
    return sorted(selected, key=lambda body: body["seq"])


def _amendment_hash_findings(base_plan_hash, amendments):
    findings = []
    current = base_plan_hash
    for amendment in sorted(amendments, key=lambda body: body["seq"]):
        recorded_supersedes = amendment.get("supersedes_plan_hash")
        if recorded_supersedes != current:
            findings.append(
                _finding(
                    "plan-hash-mismatch",
                    None,
                    "amendment seq %s supersedes %r, effective hash is %r"
                    % (amendment["seq"], recorded_supersedes, current),
                )
            )
        current = amendment.get("plan_hash")
    return findings


def _normalize_repo_path(value, repo_root):
    """064 Ownership Manifest normalization: repo-relative, realpath, no trailing sep."""
    expanded = os.path.expanduser(value)
    if not os.path.isabs(expanded):
        expanded = os.path.join(repo_root, expanded)
    normalized = os.path.realpath(expanded)
    if normalized != os.sep:
        normalized = normalized.rstrip(os.sep)
    return normalized


def _path_covers(parent, child):
    if parent == child:
        return True
    prefix = parent if parent.endswith(os.sep) else parent + os.sep
    return child.startswith(prefix)


def _paths_overlap(left, right):
    return _path_covers(left, right) or _path_covers(right, left)


def _path_set(values, repo_root):
    return sorted(
        {
            _normalize_repo_path(value, repo_root)
            for value in values or []
            if _is_text(value)
        }
    )


def _load_manifest(path, repo_root):
    manifest = _read_json_object(path, "--manifest")
    for key in ("owned_paths", "read_only_paths", "forbidden_paths"):
        value = manifest.get(key, [])
        if not (isinstance(value, list) and _is_string_list(value)):
            raise InputError("manifest.%s must be a string array" % key)
    return {
        "owned": _path_set(manifest.get("owned_paths", []), repo_root),
        "read_only": _path_set(manifest.get("read_only_paths", []), repo_root),
        "forbidden": _path_set(manifest.get("forbidden_paths", []), repo_root),
    }


def _write_territory(package, repo_root):
    return _path_set(package.get("owned_paths"), repo_root)


def _read_territory(package, repo_root):
    return _path_set(package.get("read_only_paths"), repo_root)


def _concurrent_candidates(packages, graph, slot_cap):
    """Read-only packages that can overlap an independent peer under the slot cap."""
    if not (_is_int(slot_cap) and slot_cap >= 2):
        return set()
    candidates = set()
    for package in packages:
        if package.get("kind") != "read-only":
            continue
        wp_id = package["wp_id"]
        for other in packages:
            if other["wp_id"] == wp_id:
                continue
            if _independent(graph, wp_id, other["wp_id"]):
                candidates.add(wp_id)
                break
    return candidates


def _resources_isolated(package):
    resources = package.get("resources") or {}
    for key in ("ports", "tmp_dir", "cache_dir"):
        value = resources.get(key)
        if _is_text(value) and value != "none":
            return True
    shared = resources.get("shared_readonly")
    return isinstance(shared, list) and bool(shared)


def _append_unique(findings, finding):
    if finding not in findings:
        findings.append(finding)


def _preflight_findings(plan, packages, graph, manifest, slot_ceiling, repo_root):
    """WG-14 manifest coverage/forbidden, WG-15 territories, WG-16 slot cap/isolation."""
    findings = []
    for package in packages:
        wp_id = package["wp_id"]
        owned = _write_territory(package, repo_root)
        for raw in package.get("owned_paths") or []:
            path = _normalize_repo_path(raw, repo_root)
            if not any(
                _path_covers(entry, path) for entry in manifest["owned"]
            ):
                findings.append(
                    _finding(
                        "manifest-uncovered",
                        wp_id,
                        "owned path is not covered by the manifest: %s" % raw,
                    )
                )
        for raw in list(package.get("owned_paths") or []) + list(
            package.get("read_only_paths") or []
        ):
            path = _normalize_repo_path(raw, repo_root)
            if any(
                _paths_overlap(entry, path)
                for entry in manifest["forbidden"]
            ):
                findings.append(
                    _finding(
                        "manifest-forbidden",
                        wp_id,
                        "path hits a forbidden manifest entry: %s" % raw,
                    )
                )

    for offset, left in enumerate(packages):
        for right in packages[offset + 1:]:
            left_id = left["wp_id"]
            right_id = right["wp_id"]
            if not _independent(graph, left_id, right_id):
                continue
            owner_id = min(left_id, right_id)
            left_write = _write_territory(left, repo_root)
            right_write = _write_territory(right, repo_root)
            left_read = _read_territory(left, repo_root)
            right_read = _read_territory(right, repo_root)

            if any(
                _paths_overlap(a, b)
                for a in left_write
                for b in right_write
            ):
                _append_unique(
                    findings,
                    _finding(
                        "write-write-unordered",
                        owner_id,
                        "unordered write territories overlap: %s / %s"
                        % (left_id, right_id),
                    ),
                )
                _append_unique(
                    findings,
                    _finding(
                        "path-overlap",
                        owner_id,
                        "unordered write territories overlap: %s / %s"
                        % (left_id, right_id),
                    ),
                )
            if any(
                _paths_overlap(a, b)
                for a in left_write
                for b in right_read
            ):
                _append_unique(
                    findings,
                    _finding(
                        "read-write-unordered",
                        left_id,
                        "%s reads %s's write territory"
                        % (right_id, left_id),
                    ),
                )
                _append_unique(
                    findings,
                    _finding(
                        "path-overlap",
                        owner_id,
                        "%s reads %s's write territory"
                        % (right_id, left_id),
                    ),
                )
            if any(
                _paths_overlap(b, a)
                for b in right_write
                for a in left_read
            ):
                _append_unique(
                    findings,
                    _finding(
                        "read-write-unordered",
                        right_id,
                        "%s reads %s's write territory"
                        % (left_id, right_id),
                    ),
                )
                _append_unique(
                    findings,
                    _finding(
                        "path-overlap",
                        owner_id,
                        "%s reads %s's write territory"
                        % (left_id, right_id),
                    ),
                )

    slot_cap = plan.get("slot_cap")
    if not (
        _is_int(slot_cap) and 1 <= slot_cap <= slot_ceiling
    ):
        findings.append(
            _finding(
                "slot-cap-exceeded",
                None,
                "slot_cap %r is outside 1..%d" % (slot_cap, slot_ceiling),
            )
        )
    candidates = _concurrent_candidates(packages, graph, slot_cap)
    for package in packages:
        if package["wp_id"] in candidates and not _resources_isolated(package):
            findings.append(
                _finding(
                    "isolation-missing",
                    package["wp_id"],
                    "concurrently dispatchable package declares no isolated "
                    "port, temporary directory, cache directory, or shared "
                    "read-only resource",
                )
            )
    return findings


CHILD_ID = re.compile(r"^(?P<parent>.+)-[a-z]$")
RETRY_TOPOLOGIES = (
    "parallel-native",
    "serial-native",
    "detached-runner",
    "split-serial-children",
)
RETRY_CHANGES = ("scope", "budget", "topology")
DISPATCH_EVIDENCE_TEXT = re.compile(
    r"\b(turns?|turn_count|budget[-_ ]exhausted|output[-_ ]tokens?)\b",
    re.IGNORECASE,
)
DISPATCH_EVIDENCE_KEYS = (
    "turns",
    "turn_count",
    "budget_exhausted",
    "output_tokens",
    "output_token_evidence",
)


def _dispatch_count(events, attempt, wp_id):
    return sum(
        1
        for event in events
        if event.get("event") == "dispatch"
        and _attempt_value(event) == attempt
        and event.get("wp_id") == wp_id
    )


def _retry_delta_for(amendments, events, wp_id, wp_attempt):
    candidates = [
        amendment
        for amendment in amendments
        if amendment.get("wp_id") == wp_id
        and amendment.get("wp_attempt") == wp_attempt
        and isinstance(amendment.get("retry_delta"), dict)
    ]
    if candidates:
        chosen = max(candidates, key=lambda body: body.get("seq", 0))
        return chosen["retry_delta"], chosen
    retries = [
        event
        for event in events
        if event.get("event") == "retry"
        and event.get("wp_id") == wp_id
        and event.get("wp_attempt") == wp_attempt
        and isinstance(event.get("retry_delta"), dict)
    ]
    if retries:
        return retries[-1]["retry_delta"], None
    return None, None


def _split_children(delta):
    scope = delta.get("scope") if isinstance(delta, dict) else None
    if not isinstance(scope, dict) or "split_into" not in scope:
        return None
    children = scope.get("split_into")
    if not (
        isinstance(children, list)
        and len(children) >= 2
        and _is_string_list(children)
    ):
        return []
    return children


def _evidence_is_dispatch_level(reference, spine_path, repo_root):
    candidates = []
    if os.path.isabs(reference):
        candidates.append(reference)
    else:
        if spine_path:
            candidates.append(
                os.path.join(
                    os.path.dirname(os.path.abspath(spine_path)), reference
                )
            )
        if repo_root:
            candidates.append(os.path.join(repo_root, reference))
        candidates.append(os.path.join(os.getcwd(), reference))
    for candidate in candidates:
        if not os.path.isfile(candidate):
            continue
        try:
            text = _read_text(candidate)
        except InputError:
            return False
        if DISPATCH_EVIDENCE_TEXT.search(text):
            return True
        try:
            body = json.loads(text)
        except ValueError:
            body = None
        if isinstance(body, dict):
            return any(key in body for key in DISPATCH_EVIDENCE_KEYS)
        return False
    return False


def _retry_invalid(detail):
    return _finding("retry-delta-invalid", None, detail)


def _retry_unchanged(detail):
    return _finding("retry-unchanged", None, detail)


def _retry_exhausted(detail):
    return _finding("retry-exhausted", None, detail)


def _validate_scope(delta, wp_id, amendments, current_amendment):
    scope = delta.get("scope")
    if not isinstance(scope, dict):
        return [_retry_invalid("scope change lacks a scope object")]
    children = _split_children(delta)
    if children is not None:
        if not children:
            return [
                _retry_invalid("split_into must list at least two child ids")
            ]
        if len(set(children)) != len(children):
            return [_retry_invalid("split child ids must be distinct")]
        for child in children:
            if not child.startswith(wp_id + "-"):
                return [
                    _retry_invalid(
                        "split child id %s does not extend %s" % (child, wp_id)
                    )
                ]
        records = {}
        for amendment in amendments:
            for record in amendment.get("packages", []):
                if (
                    isinstance(record, dict)
                    and record.get("wp_id") in children
                ):
                    records[record["wp_id"]] = record
        output_sets = []
        for child in children:
            record = records.get(child)
            if record is None:
                return [
                    _retry_invalid(
                        "split child %s has no package record" % child
                    )
                ]
            outputs = record.get("outputs")
            if not (
                isinstance(outputs, list)
                and outputs
                and _is_string_list(outputs)
            ):
                return [
                    _retry_invalid(
                        "split child %s has no outputs" % child
                    )
                ]
            output_sets.append(set(outputs))
        for offset, left in enumerate(output_sets):
            for right in output_sets[offset + 1:]:
                if left & right:
                    return [
                        _retry_invalid(
                            "split children must have distinct outputs"
                        )
                    ]
        for amendment in amendments:
            if amendment is current_amendment:
                continue
            if amendment.get("wp_id") == wp_id:
                prior = _split_children(
                    amendment.get("retry_delta") or {}
                )
                if prior is not None:
                    return [
                        _retry_exhausted(
                            "a lineage may be split only once"
                        )
                    ]
        return []

    from_count = scope.get("from_count")
    to_count = scope.get("to_count")
    if not (
        _is_int(from_count)
        and from_count > 0
        and _is_int(to_count)
        and to_count > 0
    ):
        return [
            _retry_invalid(
                "scope change lacks positive integer from_count/to_count"
            )
        ]
    if (
        scope.get("from_unit") not in BOUNDED_UNITS
        or scope.get("to_unit") not in BOUNDED_UNITS
    ):
        return [_retry_invalid("scope change uses an unknown bounded unit")]
    if to_count >= from_count:
        return [
            _retry_invalid(
                "scope change must strictly decrease bounded_by.count "
                "or split into children"
            )
        ]
    return []


def _validate_budget(delta, spine_path, repo_root):
    budget = delta.get("budget")
    if not isinstance(budget, dict):
        return [_retry_invalid("budget change lacks a budget object")]
    from_turns = budget.get("from_max_turns")
    to_turns = budget.get("to_max_turns")
    if not (
        _is_int(from_turns)
        and from_turns > 0
        and _is_int(to_turns)
        and to_turns > 0
    ):
        return [
            _retry_invalid(
                "budget change lacks positive integer max_turns values"
            )
        ]
    if to_turns == from_turns:
        return [
            _retry_unchanged(
                "an identical same-budget rerun is not a material delta"
            )
        ]
    if to_turns < from_turns:
        return [
            _retry_invalid("budget change must strictly increase max_turns")
        ]
    reference = budget.get("evidence_ref")
    if not _is_text(reference):
        return [_retry_invalid("budget change lacks evidence_ref")]
    if not _evidence_is_dispatch_level(reference, spine_path, repo_root):
        return [
            _retry_invalid(
                "budget evidence_ref does not resolve to dispatch-level "
                "evidence"
            )
        ]
    return []


def _validate_topology(delta):
    topology = delta.get("topology")
    if not isinstance(topology, dict):
        return [_retry_invalid("topology change lacks a topology object")]
    source = topology.get("from")
    target = topology.get("to")
    if source not in RETRY_TOPOLOGIES or target not in RETRY_TOPOLOGIES:
        return [
            _retry_invalid(
                "topology values must be in the closed set %s"
                % "/".join(RETRY_TOPOLOGIES)
            )
        ]
    if source == target:
        return [_retry_invalid("topology change must change the dispatch form")]
    return []


def _validate_retry_delta(
    delta, wp_id, amendments, current_amendment, spine_path, repo_root
):
    findings = []
    reason = delta.get("reason")
    changed = delta.get("changed")
    if not _is_text(reason):
        findings.append(_retry_invalid("retry delta lacks a reason"))
    if not (
        isinstance(changed, list)
        and changed
        and all(item in RETRY_CHANGES for item in changed)
    ):
        findings.append(
            _retry_invalid(
                "changed must be a non-empty subset of scope|budget|topology"
            )
        )
        return findings
    changed_set = set(changed)
    if "scope" in changed_set:
        findings.extend(
            _validate_scope(
                delta, wp_id, amendments, current_amendment
            )
        )
    if "budget" in changed_set:
        findings.extend(_validate_budget(delta, spine_path, repo_root))
    if "topology" in changed_set:
        findings.extend(_validate_topology(delta))
    return findings


def _retry_findings(
    args, plan, amendments, document, attempt, spine_path, repo_root
):
    events = document.get("ledger", []) if document else []
    wp_id = args.wp_id
    requested = args.wp_attempt
    if not (_is_int(requested) and requested >= 1):
        raise InputError("--wp-attempt must be a positive integer")
    packages = {
        package["wp_id"]: package
        for package in plan.get("packages", [])
        if isinstance(package, dict) and _is_text(package.get("wp_id"))
    }
    child = CHILD_ID.match(wp_id)
    if child:
        parent_id = child.group("parent")
        if wp_id not in packages:
            return [
                _retry_invalid(
                    "split child is not present in the effective plan"
                )
            ], 0
        parent_record = packages.get(parent_id)
        if parent_record is None:
            return [
                _retry_invalid(
                    "lineage parent is not present in the effective plan"
                )
            ], 0
        superseded = parent_record.get("superseded_by") or []
        if superseded and wp_id not in superseded:
            return [
                _retry_invalid(
                    "child is not listed by the parent's superseded_by"
                )
            ], 0
        parent_count = _dispatch_count(events, attempt, parent_id)
        own_count = _dispatch_count(events, attempt, wp_id)
        if own_count >= 1:
            return [
                _retry_exhausted(
                    "a split child receives no automatic retry"
                )
            ], own_count
        if parent_count >= 2:
            return [
                _retry_exhausted(
                    "the lineage is already at two attempts"
                )
            ], own_count
        if requested >= 3:
            return [_retry_exhausted("attempt 3 is rejected")], own_count
        expected = parent_count + 1
        if requested != expected:
            return [
                _retry_invalid(
                    "a split child's sole dispatch must carry the parent's "
                    "retry attempt (%d)" % expected
                )
            ], own_count
        delta, _current = _retry_delta_for(
            amendments, events, wp_id, requested
        )
        if delta is not None:
            return [
                _retry_exhausted(
                    "a split child is never split again or retried"
                )
            ], own_count
        return [], own_count

    if wp_id not in packages:
        return [
            _finding(
                "schema-missing",
                wp_id,
                "wp_id is not present in the effective plan",
            )
        ], 0
    own_count = _dispatch_count(events, attempt, wp_id)
    if own_count >= 2:
        return [
            _retry_exhausted("the package is already at two attempts")
        ], own_count
    if requested >= 3:
        return [_retry_exhausted("attempt 3 is rejected")], own_count
    if own_count == 0 and requested == 1:
        return [], own_count
    if requested <= own_count:
        return [
            _retry_unchanged("the attempt was already dispatched")
        ], own_count
    if requested != own_count + 1:
        return [
            _retry_invalid(
                "attempts must be consecutive; expected attempt %d"
                % (own_count + 1)
            )
        ], own_count
    delta, current_amendment = _retry_delta_for(
        amendments, events, wp_id, requested
    )
    if delta is None:
        return [
            _retry_unchanged("a second attempt without a material delta")
        ], own_count
    return (
        _validate_retry_delta(
            delta,
            wp_id,
            amendments,
            current_amendment,
            spine_path,
            repo_root,
        ),
        own_count,
    )


def _load_plan(args, document):
    stage = args.stage
    if args.plan_json:
        plan = _read_json_object(args.plan_json, "--plan-json")
        amendments = []
        if args.stage_attempt is not None:
            attempt = args.stage_attempt
        elif document is not None and highest_stage_attempt(document) > 0:
            attempt = highest_stage_attempt(document)
        else:
            attempt = plan.get("stage_attempt")
        return plan, [], attempt, plan.get("plan_hash")
    attempt = args.stage_attempt
    if attempt is None:
        attempt = highest_stage_attempt(document)
        if attempt <= 0:
            raise InputError("spine contains no plan fence or stage attempt")
    plan = _select_plan(document, stage, attempt)
    base_plan_hash = plan.get("plan_hash")
    amendments = _amendments_for(document, stage, attempt)
    effective = effective_plan(plan, amendments)
    return effective, amendments, attempt, base_plan_hash


def _emit(record, json_out):
    text = json.dumps(record, ensure_ascii=False)
    if json_out:
        try:
            with open(json_out, "w", encoding="utf-8") as handle:
                handle.write(text + "\n")
        except OSError as exc:
            raise InputError("cannot write --json-out %s: %s" % (json_out, exc))
    print(text)


def _plan_findings(plan, args, attempt, base_plan_hash, amendments):
    findings = validate_plan_schema(plan, args.stage, attempt)
    schema_failed = any(
        finding["code"] == "schema-missing" for finding in findings
    )
    packages = plan.get("packages") if isinstance(plan, dict) else None
    layers = []
    graph = {}
    if not findings and isinstance(packages, list):
        graph_findings, layers = _graph_findings(packages)
        findings.extend(graph_findings)
        findings.extend(_output_findings(plan, packages))
        findings.extend(_kind_findings(packages))
        findings.extend(_bounded_findings(packages))
        graph = _known_dependency_graph(packages)
        findings.extend(_pattern_findings(plan, packages, graph))
        findings.extend(_amendment_hash_findings(base_plan_hash, amendments))
        recomputed = canonical_plan_hash(plan)
        recorded_hash = plan.get("plan_hash")
        if recorded_hash != recomputed:
            findings.append(
                _finding(
                    "plan-hash-mismatch",
                    None,
                    "recorded %r, recomputed %r" % (recorded_hash, recomputed),
                )
            )
    else:
        recomputed = canonical_plan_hash(plan) if isinstance(plan, dict) else ""
    return findings, layers, graph, schema_failed, recomputed


def _finalize_plan_verdict(plan, findings, graph, layers):
    blocking = [
        finding
        for finding in findings
        if finding["code"] not in ADVISORY_CODES
    ]
    advisory = []
    packages = plan.get("packages") if isinstance(plan, dict) else None
    if (
        not blocking
        and plan.get("decision") == "decomposed"
        and isinstance(packages, list)
        and len(packages) >= 2
        and not _beneficial(plan, packages, graph, layers)
    ):
        advisory.append(
            _finding(
                "not-beneficial",
                None,
                "not-beneficial: no independent read-only pair with "
                "slot_cap>=2, the budget-weighted critical path is not "
                "shorter than the budget sum, and no bounded repair loop "
                "applies",
            )
        )
    findings = _sort_findings(findings + advisory)
    if blocking:
        verdict = "reject"
    elif plan.get("decision") in ("single-package", "disabled", "fallback"):
        verdict = "single-package"
    elif advisory:
        verdict = "single-package"
    else:
        verdict = "admit"
    return findings, verdict


def run(args):
    if not args.spine and not args.plan_json:
        raise InputError("one of --spine or --plan-json is required")
    document = read_spine(args.spine) if args.spine else None

    plan, amendments, attempt, base_plan_hash = _load_plan(args, document)
    repo_root = os.path.realpath(args.repo or os.getcwd())

    if args.check == "retry":
        if not args.wp_id:
            raise InputError("--check retry requires --wp-id")
        if args.wp_attempt is None:
            raise InputError("--check retry requires --wp-attempt")
        findings, dispatch_count = _retry_findings(
            args, plan, amendments, document, attempt, args.spine, repo_root
        )
        findings = _sort_findings(findings)
        verdict = "reject" if findings else "admit"
        record = {
            "schema_version": SCHEMA_VERSION,
            "check": args.check,
            "stage": args.stage,
            "verdict": verdict,
            "findings": findings,
            "plan_hash": canonical_plan_hash(plan),
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "evidence_ptr": args.json_out or None,
            "dispatch_layers": [],
            "integration_order": [],
            "dispatch_count": dispatch_count,
            "wp_id": args.wp_id,
            "wp_attempt": args.wp_attempt,
        }
        _emit(record, args.json_out)
        return 0 if verdict == "admit" else 1

    packages = plan.get("packages") if isinstance(plan, dict) else None
    manifest = None
    if args.check == "preflight":
        if (
            isinstance(packages, list)
            and any(
                isinstance(package, dict) and package.get("owned_paths")
                for package in packages
            )
            and not args.manifest
        ):
            raise InputError(
                "--manifest is required by --check preflight when a package "
                "owns paths"
            )
        manifest = (
            _load_manifest(args.manifest, repo_root)
            if args.manifest
            else {"owned": [], "read_only": [], "forbidden": []}
        )

    findings, layers, graph, schema_failed, recomputed = _plan_findings(
        plan, args, attempt, base_plan_hash, amendments
    )
    if args.check == "preflight" and not schema_failed:
        findings.extend(
            _preflight_findings(
                plan,
                packages,
                graph,
                manifest,
                args.slot_cap_ceiling,
                repo_root,
            )
        )
    findings, verdict = _finalize_plan_verdict(
        plan, findings, graph, layers
    )

    record = {
        "schema_version": SCHEMA_VERSION,
        "check": args.check,
        "stage": args.stage,
        "verdict": verdict,
        "findings": findings,
        "plan_hash": recomputed,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evidence_ptr": args.json_out or None,
        "dispatch_layers": layers,
        "integration_order": [
            wp_id for layer in layers for wp_id in layer
        ],
    }
    _emit(record, args.json_out)
    return 0 if verdict in ("admit", "single-package") else 1


def build_parser():
    parser = argparse.ArgumentParser(
        description="Deterministic Work Package decomposition gate."
    )
    parser.add_argument("--spine", default="", help="line state spine path")
    parser.add_argument("--stage", required=True, help="canonical stage name")
    parser.add_argument("--check", required=True, choices=CHECK_NAMES)
    parser.add_argument("--plan-json", default="", help="plan body fixture path")
    parser.add_argument("--manifest", default="", help="064 Ownership Manifest path")
    parser.add_argument("--repo", default="", help="repository root for path normalization")
    parser.add_argument("--slot-cap-ceiling", type=int, default=4)
    parser.add_argument("--stage-attempt", type=int, default=None)
    parser.add_argument("--wp-id", default="")
    parser.add_argument("--wp-attempt", type=int, default=None)
    parser.add_argument("--json-out", default="")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except InputError as exc:
        print("wp-gate: input error: %s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
