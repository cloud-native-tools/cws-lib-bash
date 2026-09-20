#!/usr/bin/env python3
"""site-memory.py — deterministic engine for browser-utils site memory.

Manages the per-site memory directories under `${SKILL_HOME}/site/<host[:port]>/`:
state machine (exploration → optimization → validation → sealed), operation
records (JSONL, redaction enforced at write time), request recipes and
validation evidence. Agent-neutral: plain JSON files, stdlib-only, all three
automation tiers call this CLI the same way. See references/site-memory.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

STATES = ("exploration", "optimization", "validation", "sealed")

SENSITIVE_HEADER_NAMES = {"cookie", "authorization", "x-csrf-token", "x-xsrf-token"}
SENSITIVE_HEADER_SUBSTRINGS = ("token", "signature", "secret")

PLACEHOLDER_RE = re.compile(r"^<[^<>]+>$")
BEARER_RE = re.compile(r"^Bearer\s+\S+", re.IGNORECASE)
COOKIE_PAIR_RE = re.compile(r"^\w[\w-]*=.+;\s*\w[\w-]*=.+", re.DOTALL)
HIGH_ENTROPY_RE = re.compile(r"^[A-Za-z0-9+/=_-]{16,}$")

TRANSITION_GATES = {
    "optimization": "records_complete",
    "validation": "recipe_valid",
    "sealed": "validation_passed",
}


class CliError(Exception):
    def __init__(self, message, code=1, **extra):
        super().__init__(message)
        self.code = code
        self.extra = extra


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")


def site_root(args) -> Path:
    return Path(args.skill_home).resolve() / "site"


def site_dir(args, site: str) -> Path:
    return site_root(args) / site


def derive_site(url: str) -> str:
    parsed = urlparse(url if "://" in url else "https://" + url)
    host = (parsed.hostname or "").lower()
    if not host:
        raise CliError(f"cannot derive host from url: {url}", code=2)
    port = parsed.port
    if port and port not in (80, 443):
        return f"{host}:{port}"
    return host


def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_state(args, site: str) -> dict | None:
    path = site_dir(args, site) / "state.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("state") not in STATES:
        return None
    return data


def write_state(args, site: str, state: dict) -> None:
    atomic_write_json(site_dir(args, site) / "state.json", state)


# ------------------------------------------------------------- action: init


def action_init(args) -> dict:
    site = args.site or derive_site(args.url)
    sdir = site_dir(args, site)
    state_path = sdir / "state.json"
    if state_path.is_file() and read_state(args, site) is not None:
        return {
            "ok": True, "site": site, "dir": str(sdir),
            "state": read_state(args, site)["state"], "created": False,
        }
    sdir.mkdir(parents=True, exist_ok=True)
    state = {
        "site": site,
        "state": "exploration",
        "updated_at": utc_now(),
        "history": [
            {"from": None, "to": "exploration", "at": utc_now(), "evidence": "init"}
        ],
    }
    write_state(args, site, state)
    return {
        "ok": True, "site": site, "dir": str(sdir),
        "state": "exploration", "created": True,
    }


# -------------------------------------------------------- action: get-state


def action_get_state(args) -> dict:
    state = read_state(args, args.site)
    if state is None:
        return {"ok": True, "site": args.site, "state": None, "memory": "absent"}
    sdir = site_dir(args, args.site)
    records_dir = sdir / "records"
    tasks = sorted(p.stem for p in records_dir.glob("*.jsonl")) if records_dir.is_dir() else []
    return {
        "ok": True,
        "site": args.site,
        "state": state["state"],
        "updated_at": state.get("updated_at"),
        "history": state.get("history", []),
        "recipe_present": (sdir / "recipe.json").is_file(),
        "records": tasks,
    }


# ---------------------------------------------------- redaction enforcement


def is_sensitive_header(name: str) -> bool:
    lowered = name.lower()
    return lowered in SENSITIVE_HEADER_NAMES or any(
        sub in lowered for sub in SENSITIVE_HEADER_SUBSTRINGS
    )


def is_dynamic_field(name: str) -> bool:
    lowered = name.lower()
    return any(sub in lowered for sub in ("token", "signature", "secret", "requestid", "request_id"))


def check_value_redacted(field_path: str, value) -> None:
    if not isinstance(value, str):
        return
    if PLACEHOLDER_RE.match(value):
        return
    if BEARER_RE.match(value):
        raise CliError(f"raw credential value rejected at {field_path} (Bearer prefix)")
    if COOKIE_PAIR_RE.match(value):
        raise CliError(f"raw credential value rejected at {field_path} (cookie pair form)")
    if HIGH_ENTROPY_RE.match(value):
        raise CliError(f"raw credential value rejected at {field_path} (high-entropy value)")


def enforce_redaction(record: dict) -> None:
    headers = record.get("headers") or {}
    for name, value in headers.items():
        if is_sensitive_header(name):
            check_value_redacted(f"headers.{name}", value)
    for key in ("body_template", "params_template"):
        body = record.get(key) or {}
        for name, value in body.items():
            if is_dynamic_field(name):
                check_value_redacted(f"{key}.{name}", value)


# ------------------------------------------------------- record validation


RECORD_REQUIRED = ("seq", "at", "kind", "ok")


def validate_record_schema(record: dict) -> None:
    missing = [k for k in RECORD_REQUIRED if k not in record]
    if missing:
        raise CliError(f"record missing required fields: {missing}", code=2)
    kind = record["kind"]
    if kind == "dom":
        extra = [k for k in ("action", "target") if k not in record]
    elif kind == "network":
        extra = [k for k in ("method", "url", "response_shape") if k not in record]
        shape = record.get("response_shape")
        if not extra and not (
            isinstance(shape, dict)
            and isinstance(shape.get("status"), int)
            and isinstance(shape.get("json_keys"), list)
        ):
            extra.append("response_shape{status:int,json_keys:list}")
    else:
        raise CliError(f"record kind must be dom|network, got {kind!r}", code=2)
    if extra:
        raise CliError(f"record kind={kind} missing required fields: {extra}", code=2)
    if record["ok"] is False and not record.get("error"):
        raise CliError("failed record (ok=false) must carry an error field", code=2)


def records_file(args, site: str, task: str) -> Path:
    return site_dir(args, site) / "records" / f"{task}.jsonl"


def read_records(args, site: str, task: str) -> list[dict]:
    path = records_file(args, site, task)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    records = []
    for line in lines:
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


# ----------------------------------------------------- action: append-record


def action_append_record(args) -> dict:
    if read_state(args, args.site) is None:
        raise CliError(f"site {args.site} has no memory; run --action init first", code=2)
    try:
        record = json.loads(args.record)
    except ValueError as exc:
        raise CliError(f"--record is not valid JSON: {exc}", code=2)
    validate_record_schema(record)
    enforce_redaction(record)
    existing = read_records(args, args.site, args.task)
    expected_seq = len(existing) + 1
    if record["seq"] != expected_seq:
        raise CliError(
            f"record seq must continue at {expected_seq}, got {record['seq']}"
        )
    path = records_file(args, args.site, args.task)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return {"ok": True, "seq": record["seq"], "file": f"records/{args.task}.jsonl"}


# -------------------------------------------------- action: validate-records


def completeness(args, site: str, task: str) -> dict:
    records = read_records(args, site, task)
    missing = []
    counts = {"dom": 0, "network": 0, "failed": 0}
    if not records:
        missing.append(f"records/{task}.jsonl absent or empty")
    for index, record in enumerate(records, start=1):
        try:
            validate_record_schema(record)
        except CliError as exc:
            missing.append(f"record {index}: {exc}")
            continue
        counts[record["kind"]] += 1
        if record["ok"] is False:
            counts["failed"] += 1
        if record["seq"] != index:
            missing.append(f"record seq gap at position {index}")
    if records and counts["network"] == 0:
        missing.append("no network record present")
    return {
        "ok": True,
        "complete": not missing,
        "missing": missing,
        "counts": counts,
    }


def action_validate_records(args) -> dict:
    return completeness(args, args.site, args.task)


# --------------------------------------------------------- recipe validation


def validate_recipe_schema(args, site: str, recipe: dict) -> None:
    for key in ("task", "distilled_from", "distilled_at", "steps"):
        if key not in recipe:
            raise CliError(f"recipe missing required field: {key}", code=2)
    source = site_dir(args, site) / recipe["distilled_from"]
    if not source.is_file():
        raise CliError(
            f"recipe distilled_from points at missing file: {recipe['distilled_from']}",
            code=2,
        )
    steps = recipe["steps"]
    if not isinstance(steps, list) or not steps:
        raise CliError("recipe steps must be a non-empty array", code=2)
    for index, step in enumerate(steps, start=1):
        if step.get("n") != index:
            raise CliError(f"recipe step n must be {index}, got {step.get('n')}", code=2)
        stype = step.get("type")
        if stype == "request":
            missing = [k for k in ("method", "url", "expect") if k not in step]
            expect = step.get("expect")
            if not missing and not (
                isinstance(expect, dict)
                and isinstance(expect.get("status"), int)
                and isinstance(expect.get("json_keys"), list)
            ):
                missing.append("expect{status:int,json_keys:list}")
            if missing:
                raise CliError(f"request step {index} missing: {missing}", code=2)
        elif stype == "page":
            if not step.get("reason"):
                raise CliError(f"page step {index} must carry a non-empty reason", code=2)
            if not step.get("action"):
                raise CliError(f"page step {index} must carry an action", code=2)
        else:
            raise CliError(f"step {index} type must be request|page, got {stype!r}", code=2)


def action_write_recipe(args) -> dict:
    if read_state(args, args.site) is None:
        raise CliError(f"site {args.site} has no memory; run --action init first", code=2)
    try:
        recipe = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CliError(f"--file not readable JSON: {exc}", code=2)
    validate_recipe_schema(args, args.site, recipe)
    atomic_write_json(site_dir(args, args.site) / "recipe.json", recipe)
    page_steps = sum(1 for s in recipe["steps"] if s["type"] == "page")
    return {"ok": True, "steps": len(recipe["steps"]), "page_steps": page_steps}


# ------------------------------------------------------------ state machine


def latest_validation_verdict(args, site: str) -> str | None:
    vdir = site_dir(args, site) / "validation"
    if not vdir.is_dir():
        return None
    files = sorted(vdir.glob("*.json"))
    for path in reversed(files):
        try:
            evidence = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        verdict = evidence.get("verdict")
        if verdict in ("pass", "fail"):
            return verdict
    return None


def check_transition_gate(args, site: str, task: str | None, target: str) -> None:
    gate = TRANSITION_GATES.get(target)
    if gate == "records_complete":
        task_name = task or _single_task(args, site)
        verdict = completeness(args, site, task_name)
        if not verdict["complete"]:
            raise CliError(
                f"transition to optimization denied; records incomplete: {verdict['missing']}"
            )
    elif gate == "recipe_valid":
        recipe_path = site_dir(args, site) / "recipe.json"
        try:
            recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise CliError(f"transition to validation denied; recipe invalid: {exc}")
        validate_recipe_schema(args, site, recipe)
    elif gate == "validation_passed":
        if latest_validation_verdict(args, site) != "pass":
            raise CliError(
                "transition to sealed denied; no passing validation evidence found"
            )


def _single_task(args, site: str) -> str:
    records_dir = site_dir(args, site) / "records"
    tasks = sorted(p.stem for p in records_dir.glob("*.jsonl")) if records_dir.is_dir() else []
    if len(tasks) != 1:
        raise CliError(
            f"--task required to evaluate records completeness (found tasks: {tasks})",
            code=2,
        )
    return tasks[0]


ALLOWED_FORWARD = {
    "exploration": {"optimization"},
    "optimization": {"validation"},
    "validation": {"sealed"},
    "sealed": set(),
}


def do_transition(args, site: str, state: dict, target: str, evidence: str | None) -> dict:
    current = state["state"]
    if target not in STATES:
        raise CliError(f"unknown target state {target!r}; states: {STATES}", code=2)
    if target == current:
        raise CliError(f"already in state {target}")
    rollback = target == "optimization" and current in ("validation", "sealed")
    if rollback:
        if not evidence:
            raise CliError(
                "rollback to optimization requires --evidence (failure reason or drift proof)",
                code=2,
            )
    else:
        allowed = ALLOWED_FORWARD.get(current, set())
        if target not in allowed:
            legal = sorted(allowed)
            if current in ("validation", "sealed"):
                legal.append("optimization (rollback)")
            raise CliError(
                f"illegal transition {current} -> {target}; "
                f"legal targets from {current}: {legal}"
            )
        check_transition_gate(args, site, getattr(args, "task", None), target)
    state["state"] = target
    state["updated_at"] = utc_now()
    state.setdefault("history", []).append(
        {
            "from": current,
            "to": target,
            "at": utc_now(),
            "evidence": evidence or f"gate:{TRANSITION_GATES.get(target, 'n/a')}",
        }
    )
    write_state(args, site, state)
    return {"ok": True, "from": current, "to": target}


def action_transition(args) -> dict:
    state = read_state(args, args.site)
    if state is None:
        raise CliError(f"site {args.site} has no memory; run --action init first", code=2)
    return do_transition(args, args.site, state, args.to, args.evidence)


# ------------------------------------------------- action: record-validation


def validate_evidence_schema(evidence: dict) -> None:
    for key in ("run_id", "task", "verdict", "steps_total", "steps_passed", "failures", "at"):
        if key not in evidence:
            raise CliError(f"evidence missing required field: {key}", code=2)
    if evidence["verdict"] not in ("pass", "fail"):
        raise CliError("evidence verdict must be pass|fail", code=2)
    if evidence["verdict"] == "fail" and not evidence["failures"]:
        raise CliError("verdict=fail requires a non-empty failures array", code=2)
    if evidence["verdict"] == "pass" and (
        evidence["failures"] or evidence["steps_passed"] != evidence["steps_total"]
    ):
        raise CliError(
            "verdict=pass requires failures empty and steps_passed == steps_total",
            code=2,
        )


def action_record_validation(args) -> dict:
    state = read_state(args, args.site)
    if state is None:
        raise CliError(f"site {args.site} has no memory; run --action init first", code=2)
    try:
        evidence = json.loads(Path(args.file).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CliError(f"--file not readable JSON: {exc}", code=2)
    validate_evidence_schema(evidence)
    vdir = site_dir(args, args.site) / "validation"
    atomic_write_json(vdir / f"{evidence['run_id']}.json", evidence)
    verdict = evidence["verdict"]
    current = state["state"]
    target = "sealed" if verdict == "pass" else "optimization"
    result = {"ok": True, "verdict": verdict, "evidence": f"validation/{evidence['run_id']}.json"}
    try:
        moved = do_transition(
            args, args.site, state, target,
            evidence=f"validation/{evidence['run_id']}.json",
        )
        result["state"] = moved["to"]
    except CliError as exc:
        # Evidence stays on disk; only the state move is refused.
        result["state"] = current
        result["transition_error"] = str(exc)
    return result


# ------------------------------------------------------------------ CLI main


ACTIONS = {
    "init": action_init,
    "get-state": action_get_state,
    "append-record": action_append_record,
    "validate-records": action_validate_records,
    "write-recipe": action_write_recipe,
    "record-validation": action_record_validation,
    "transition": action_transition,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", required=True, choices=sorted(ACTIONS))
    parser.add_argument("--skill-home", default=".")
    parser.add_argument("--url")
    parser.add_argument("--site")
    parser.add_argument("--task")
    parser.add_argument("--record")
    parser.add_argument("--file")
    parser.add_argument("--to")
    parser.add_argument("--evidence")
    parser.add_argument("--format", default="json", choices=("json", "text"))
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.action == "init" and not (args.url or args.site):
        emit({"ok": False, "error": "init requires --url or --site"})
        return 2
    if args.action != "init" and not args.site:
        emit({"ok": False, "error": f"{args.action} requires --site"})
        return 2
    try:
        emit(ACTIONS[args.action](args))
        return 0
    except CliError as exc:
        payload = {"ok": False, "error": str(exc)}
        payload.update(exc.extra)
        emit(payload)
        return exc.code


if __name__ == "__main__":
    sys.exit(main())
