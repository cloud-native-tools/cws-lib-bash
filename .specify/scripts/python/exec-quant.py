#!/usr/bin/env python3
"""exec-quant.py — Agent+LLM execution quant recording engine (Feature 059; v2 in 061).

Recording Only: every completed execution of a covered unit (the same unit
semantics as run-determination) lands ONE quant record — agent program fields,
LLM detail fields, quality fields — into the engine-owned durable store
``.specify/memory/exec-quant/``. Each entry is its own timestamp-named file
under ``records/`` or ``scores/``: concurrent branches then append different
files instead of colliding on one shared tracked file. Legacy
``records.jsonl`` / ``scores.jsonl`` stores stay readable (read-only
fallback); new writes never touch them.

v2 (Feature 061): schema_version=2, ``unit_type=agent`` via ``agent:<slug>``,
the ``collect-dispatch`` action (one record per external dispatch label), an
11-field ``config`` group, ``quality.exit_code`` and the ``configured``
provenance. Unit records (``collect``) keep 059 semantics and additionally gain
an all-``not_evaluated`` config group.

Design adjudications live in the feature plans (059 D1–D12; 061 E6); behavior
truth is this file. Law of the record (data-model §1.1): every measurable field
is either a ``{"value", "provenance"}`` object or the literal ``not_evaluated``
— zero null, zero empty string, zero missing key. A quantity with no source is
never guessed (测量而非印象).

Non-blocking (059 FR-012, 061 FR-018): any failure path exits 1 with a message
on stderr and never raises into the caller's run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

ACTIONS = ("collect", "list-records", "score", "collect-dispatch", "args-manifest")

# Argument manifest (063 C-22): per-action required/source classification.
# "required" = flags this engine itself validates as required for the action;
# "source" = this engine's DECLARED run-evidence input set (undeclared = []).
# `--action args-manifest` verifies every listed flag against build_parser()'s
# LIVE option strings before emitting — the parser stays the single source of
# truth; the compile-embeds renderer consumes this and holds no table of its
# own (063 C-21). Note: `collect` synthesizes a run-id when absent (existing
# 059 semantics, untouched by 063 C-24 — that clause is scoped to
# run-determination's (unit_id, run_id) lock), so --run-id is declared SOURCE,
# not required.
ARG_MANIFEST = {
    "collect": {"required": ["--unit-id"], "source": ["--run-id"]},
    "list-records": {"required": [], "source": ["--since", "--format"]},
    "score": {"required": ["--unit-id", "--run-id", "--score"],
              "source": ["--note"]},
    "collect-dispatch": {"required": ["--unit-id", "--run-id", "--snapshot",
                                      "--config-id"],
                         "source": []},
    "args-manifest": {"required": [], "source": []},
}

KIND = "speckit.exec-quant"  # [[STR-001]]
SCHEMA_VERSION = 2
NOT_EVALUATED = "not_evaluated"  # [[STR-002]]
PROVENANCES = ("measured", "carried", "user-given", "configured")
UNIT_TYPES = ("command", "skill", "custom-unit", "agent")
RESOLUTIONS = ("explicit", "adopted", "synthesized")
AGENT_RESOLUTIONS = ("resolved", "ambiguous", "unresolved")

SNAPSHOT_KIND = "speckit.execution-config-snapshot"
SNAPSHOT_SCHEMA_VERSION = 1

#: Exactly the 11 config-group fields (061 C-EQ-04). Order is the write order.
CONFIG_FIELDS = ("config_id", "source_chain", "method_requested", "method_resolved",
                 "mode", "cli", "model", "reasoning_effort", "context_window",
                 "extra_flags", "snapshot")

#: plan D2 single adjudication: adoption window for a same-unit determination
#: record when the caller passes no --run-id (bounded against stale binding).
RECENT_WINDOW_MINUTES = 90

#: data-model V5: single-record serialization cap.
RECORD_SIZE_CAP_BYTES = 64 * 1024

STORAGE_REL = Path(".specify") / "memory" / "exec-quant"
RECORDS_DIR_NAME = "records"
SCORES_DIR_NAME = "scores"
LEGACY_RECORDS_NAME = "records.jsonl"
LEGACY_SCORES_NAME = "scores.jsonl"
LOCK_NAME = ".write.lock"
DEFAULT_DISPATCH_LOG_DIR = Path(".specify") / "agents" / "execution" / "logs"

_UNIT_ID_RE = re.compile(
    r"^(?:/speckit\.[a-z0-9][a-z0-9._-]*"
    r"|skill:[a-z0-9][a-z0-9._-]*"
    r"|custom:[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*"
    r"|agent:[a-z0-9][a-z0-9._-]*)$"
)

#: D8 known host-CLI process-name patterns (framework-supported agents).
HOST_CLI_PATTERNS = ("qodercli", "claude", "codex", "copilot", "opencode", "hermes")

#: D6 endpoint whitelist: only these variable names are read, values origin-only.
ENDPOINT_ENV_NAMES = (
    "ANTHROPIC_BASE_URL", "ANTHROPIC_URL", "OPENAI_BASE_URL", "OPENAI_URL",
    "ALIYUN_ANTHROPIC_COMPATIBLE_URL", "ALIYUN_OPENAI_COMPATIBLE_URL",
    "DASHSCOPE_API_URL", "CLAUDE_ALIBABA_BASE_URL", "CLAUDE_OFFICIAL_BASE_URL",
)

#: D9 value-level credential shapes masked before write (defense in depth on
#: top of the D6 whitelist collection; hits are replaced in place).
CREDENTIAL_PATTERNS = tuple(
    (name, re.compile(pattern))
    for name, pattern in (
        ("sk_style_key", r"(?i)\b(?:sk|pk)-[A-Za-z0-9_-]{16,}\b"),
        ("aws_access_key", r"\bAKIA[0-9A-Z]{16}\b"),
        ("bearer_token", r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"),
        ("slack_token", r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
        ("github_token", r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
        ("google_api_key", r"\bAIza[0-9A-Za-z_\-]{30,}\b"),
        ("url_userinfo", r"[A-Za-z][A-Za-z0-9+.\-]*://[^\s/:@]+:[^\s/@]+@"),
        ("kv_assignment",
         r"(?i)\b(?:api[_-]?key|secret|token|authorization|password)\b\s*[:=]\s*['\"]?[^\s'\"]{8,}"),
    )
)


class ExecQuantError(Exception):
    """Engine failure surfaced as exit 1 with a stderr message."""


class InputError(ExecQuantError):
    """Usage error surfaced as exit 2."""


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sibling_engine(filename: str):
    """Load a sibling engine from this file's own directory (two-hats-safe:
    self-location fires only on a literal component of the resolved path)."""
    path = Path(__file__).resolve().parent / filename
    if not path.is_file():
        raise ExecQuantError(f"sibling engine not found beside this one: {path}")
    import importlib.util
    name = "_eq_" + filename.replace("-", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ExecQuantError(f"cannot load sibling engine: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def resolve_workspace_root(explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit).resolve()
    try:
        memory = sibling_engine("memory-utils.py")
    except ExecQuantError:
        return Path.cwd().resolve()
    return memory.resolve_workspace_root(None)


def validate_unit_id(unit_id: str) -> bool:
    return bool(unit_id) and bool(_UNIT_ID_RE.match(unit_id.strip()))


def unit_type_of(unit_id: str) -> str:
    uid = (unit_id or "").strip()
    if uid.startswith("/speckit."):
        return "command"
    if uid.startswith("skill:"):
        return "skill"
    if uid.startswith("custom:"):
        return "custom-unit"
    if uid.startswith("agent:"):
        return "agent"
    raise InputError(
        f"invalid --unit-id: {unit_id!r} — expected /speckit.<command>, "
        f"skill:<name>, custom:<owner>/<name> or agent:<slug>")


def storage_dir(workspace_root: Path) -> Path:
    return workspace_root / STORAGE_REL


def records_dir(workspace_root: Path) -> Path:
    return storage_dir(workspace_root) / RECORDS_DIR_NAME


def scores_dir(workspace_root: Path) -> Path:
    return storage_dir(workspace_root) / SCORES_DIR_NAME


def bootstrap_storage(workspace_root: Path) -> Tuple[Path, Path]:
    try:
        records = records_dir(workspace_root)
        scores = scores_dir(workspace_root)
        records.mkdir(parents=True, exist_ok=True)
        scores.mkdir(parents=True, exist_ok=True)
        return records, scores
    except OSError as exc:
        raise ExecQuantError(f"cannot bootstrap the exec-quant store: {exc}") from exc


def entry_filename(stamp: Optional[datetime] = None) -> str:
    stamp = stamp or datetime.now(timezone.utc)
    return f"{stamp.strftime('%Y%m%dT%H%M%S%fZ')}-{uuid.uuid4().hex[:8]}.json"


def write_entry(directory: Path, entry: Dict[str, Any]) -> Path:
    """One entry per timestamp-named file; tmp+rename keeps readers whole."""
    target = directory / entry_filename()
    temporary = directory / (".tmp-" + uuid.uuid4().hex + ".part")
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        os.replace(temporary, target)
    except OSError as exc:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise ExecQuantError(f"cannot write {target}: {exc}") from exc
    return target


def read_entry_files(directory: Path) -> List[Dict[str, Any]]:
    if not directory.is_dir():
        return []
    entries = []
    for path in sorted(directory.glob("*.json")):
        try:
            node = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(node, dict):
            entries.append(node)
    return entries


# ---------------------------------------------------------------------------
# run identity (plan D2)
# ---------------------------------------------------------------------------

def _parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    text = value.strip()
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None


def load_determinations_for_unit(workspace_root: Path, unit_id: str) -> List[Dict[str, Any]]:
    """Read-only access to the adjacent engine's records (FR-015: no writes)."""
    try:
        rd = sibling_engine("run-determination.py")
        found = rd.load_determinations(workspace_root, unit_id)
    except Exception:
        return []
    records = []
    for item in found or []:
        record = item.get("record") if isinstance(item, dict) else None
        if isinstance(record, dict) and record.get("kind") == "speckit.run-determination":
            records.append(record)
    return records


def resolve_run_identity(workspace_root: Path, unit_id: str,
                         explicit_run_id: Optional[str]
                         ) -> Tuple[str, str, Optional[Dict[str, Any]]]:
    """Return (run_id, resolution, determination_record)."""
    determinations = load_determinations_for_unit(workspace_root, unit_id)
    if explicit_run_id:
        exact = next((r for r in determinations if r.get("run_id") == explicit_run_id), None)
        return explicit_run_id, "explicit", exact
    now = datetime.now(timezone.utc)
    window = timedelta(minutes=RECENT_WINDOW_MINUTES)
    recent = []
    for record in determinations:
        stamp = _parse_iso(record.get("determined_at"))
        if stamp is not None and timedelta(0) <= now - stamp <= window:
            recent.append((stamp, record.get("run_id") or "", record))
    if recent:
        recent.sort(key=lambda item: (item[0], item[1]))
        _, run_id, record = recent[-1]
        if run_id:
            return run_id, "adopted", record
    return "{}-{}".format(_slug(unit_id), now.strftime("%Y%m%dT%H%M%SZ")), "synthesized", None


def _slug(unit_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", unit_id.strip().lower()).strip("-")


# ---------------------------------------------------------------------------
# agent collection (D8)
# ---------------------------------------------------------------------------

def _proc_file(pid: int, name: str) -> Optional[str]:
    try:
        return (Path("/proc") / str(pid) / name).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _proc_argv(pid: int) -> List[str]:
    raw = _proc_file(pid, "cmdline")
    if raw is None:
        return []
    return [part for part in raw.split("\x00") if part]


def _proc_ppid(pid: int) -> Optional[int]:
    stat = _proc_file(pid, "stat")
    if not stat:
        return None
    tail = stat[stat.rfind(")") + 1:].split() if ")" in stat else []
    try:
        return int(tail[1])
    except (IndexError, ValueError):
        return None


def _proc_cwd(pid: int) -> Optional[str]:
    try:
        return os.readlink(f"/proc/{pid}/cwd")
    except OSError:
        return None


def _matches_host(name: str) -> bool:
    lowered = name.lower()
    return any(pattern in lowered for pattern in HOST_CLI_PATTERNS)


def _candidate_names(pid: int) -> List[str]:
    argv = _proc_argv(pid)
    names = []
    if argv:
        names.append(Path(argv[0]).name)
    comm = _proc_file(pid, "comm")
    if comm:
        names.append(comm.strip())
    return [n for n in names if n]


def probe_version(binary: str) -> Optional[str]:
    """<binary> --version with a bounded timeout; never guessed (D8)."""
    executable = binary
    if not os.path.isfile(executable):
        executable = shutil.which(binary) or ""
    if not executable:
        return None
    try:
        result = subprocess.run([executable, "--version"], capture_output=True,
                                text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    for line in (result.stdout or "").splitlines() + (result.stderr or "").splitlines():
        line = line.strip()
        if line:
            return line[:200]
    return None


def collect_agent() -> Tuple[Dict[str, Any], Optional[int], Optional[str]]:
    """Walk the parent chain; attribute the host CLI without guessing."""
    group: Dict[str, Any] = {key: NOT_EVALUATED
                             for key in ("name", "version", "binary", "argv", "cwd")}
    group["resolution"] = "unresolved"
    if not os.path.isdir("/proc"):
        return group, None, None
    matches: List[Tuple[int, str, List[str]]] = []
    seen = set()
    pid = os.getppid()
    while pid and pid > 1 and pid not in seen:
        seen.add(pid)
        names = _candidate_names(pid)
        hit = next((n for n in names if _matches_host(n)), None)
        if hit:
            matches.append((pid, hit, _proc_argv(pid)))
        pid = _proc_ppid(pid) or 0
    if not matches:
        return group, None, None
    distinct = {name for _, name, _ in matches}
    if len(distinct) > 1:
        group["resolution"] = "ambiguous"
        return group, None, None
    pid, name, argv = matches[0]
    group["resolution"] = "resolved"
    group["name"] = {"value": name, "provenance": "measured"}
    if argv:
        group["binary"] = {"value": argv[0], "provenance": "measured"}
        rest = argv[1:]
        if rest:
            group["argv"] = {"value": rest, "provenance": "measured"}
        version = probe_version(argv[0])
        if version:
            group["version"] = {"value": version, "provenance": "measured"}
    cwd = _proc_cwd(pid)
    if cwd:
        group["cwd"] = {"value": cwd, "provenance": "measured"}
    return group, pid, name


# ---------------------------------------------------------------------------
# LLM collection (D6 + D7)
# ---------------------------------------------------------------------------

def _read_environ(pid: Optional[int]) -> Dict[str, str]:
    if pid is not None:
        raw = _proc_file(pid, "environ")
        if raw is not None:
            mapping = {}
            for chunk in raw.split("\x00"):
                if "=" in chunk:
                    key, _, value = chunk.partition("=")
                    mapping[key] = value
            return mapping
    return dict(os.environ)


def _url_origin(value: str) -> Optional[str]:
    """scheme://host[:port] only — path, query and credentials stripped (D6)."""
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return None
    if not parsed.scheme or not parsed.hostname:
        return None
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = host if parsed.port is None else f"{host}:{parsed.port}"
    return f"{parsed.scheme}://{netloc}"


def collect_endpoint_candidates(pid: Optional[int]) -> Dict[str, Any]:
    env = _read_environ(pid)
    mapping = {}
    for name in ENDPOINT_ENV_NAMES:
        value = env.get(name, "").strip()
        if not value:
            continue
        origin = _url_origin(value)
        if origin:
            mapping[name] = origin
    return mapping if mapping else NOT_EVALUATED


def collect_connection_evidence(pid: Optional[int]) -> Dict[str, Any]:
    """Established remote ip:port of connections owned by the host pid (no
    DNS, no effectiveness verdict — evidence only, D6)."""
    if pid is None or shutil.which("ss") is None:
        return NOT_EVALUATED
    try:
        result = subprocess.run(["ss", "-tnp"], capture_output=True, text=True,
                                timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return NOT_EVALUATED
    peers: List[str] = []
    for line in (result.stdout or "").splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0] != "ESTAB":
            continue
        owner = " ".join(parts[5:])
        if re.search(rf"\bpid={pid}\b", owner):
            peer = parts[4]
            if peer and peer not in peers:
                peers.append(peer)
    return {"value": peers, "provenance": "measured"} if peers else NOT_EVALUATED


def qoder_settings_path() -> Path:
    return Path.home() / ".qoder" / "settings.json"


def qoder_settings_llm() -> Dict[str, Any]:
    """Measured Qoder settings leaves (D7), independent of the parent chain."""
    group: Dict[str, Any] = {
        "model": NOT_EVALUATED, "context_window": NOT_EVALUATED,
        "reasoning_effort": NOT_EVALUATED, "config_source": NOT_EVALUATED,
    }
    path = qoder_settings_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return group
    group["config_source"] = {"value": str(path), "provenance": "measured"}
    model = data.get("model") if isinstance(data, dict) else None
    model_name = model.get("name") if isinstance(model, dict) else None
    preferences = model.get("preferences") if isinstance(model, dict) else None
    own = preferences.get(model_name) if isinstance(preferences, dict) else None
    if isinstance(model_name, str) and model_name:
        group["model"] = {"value": model_name, "provenance": "measured"}
    if isinstance(own, dict):
        window = own.get("contextWindow")
        if isinstance(window, int) and not isinstance(window, bool) and window > 0:
            group["context_window"] = {"value": window, "provenance": "measured"}
        reasoning = own.get("reasoning")
        effort = reasoning.get("effort") if isinstance(reasoning, dict) else None
        if isinstance(effort, str) and effort:
            group["reasoning_effort"] = {"value": effort, "provenance": "measured"}
    return group


def collect_llm(agent: Dict[str, Any], pid: Optional[int]) -> Dict[str, Any]:
    group: Dict[str, Any] = {
        "model": NOT_EVALUATED, "context_window": NOT_EVALUATED,
        "reasoning_effort": NOT_EVALUATED, "config_source": NOT_EVALUATED,
        "endpoint_candidates": NOT_EVALUATED, "connection_evidence": NOT_EVALUATED,
    }
    if agent.get("resolution") != "resolved":
        return group
    host_name = ""
    name = agent.get("name")
    if isinstance(name, dict):
        host_name = str(name.get("value") or "")
    group["endpoint_candidates"] = collect_endpoint_candidates(pid)
    group["connection_evidence"] = collect_connection_evidence(pid)
    if "qodercli" not in host_name.lower():
        return group
    group.update(qoder_settings_llm())
    return group


# ---------------------------------------------------------------------------
# quality carried fields (A6 + D5)
# ---------------------------------------------------------------------------

def collect_quality(record: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    group: Dict[str, Any] = {
        "elapsed_ms": NOT_EVALUATED, "tokens": NOT_EVALUATED,
        "errors": NOT_EVALUATED, "satisfaction": NOT_EVALUATED,
        "exit_code": NOT_EVALUATED,
    }
    if not record:
        return group
    axes = record.get("axes") if isinstance(record.get("axes"), dict) else {}

    elapsed = ((axes.get("elapsed") or {}).get("measurement") or {}).get("ms")
    if isinstance(elapsed, int) and not isinstance(elapsed, bool) and elapsed >= 0:
        group["elapsed_ms"] = {"value": elapsed, "provenance": "carried"}

    total = ((axes.get("token_consumption") or {}).get("measurement") or {}).get("total_tokens")
    if isinstance(total, int) and not isinstance(total, bool) and total >= 0:
        group["tokens"] = {"value": total, "provenance": "carried"}

    verdict = (axes.get("satisfaction") or {}).get("verdict")
    if verdict and verdict != NOT_EVALUATED:
        group["satisfaction"] = {"value": verdict, "provenance": "carried"}

    errors: List[Dict[str, Any]] = []
    diff = ((axes.get("artifact_correctness") or {}).get("failed_set_diff")) or {}
    if diff.get("status") in ("empty", "non_empty"):
        count = diff.get("added_count")
        if not isinstance(count, int) or isinstance(count, bool):
            count = len(diff.get("added") or [])
        errors.append({"source": "run-determination.failed_set_diff", "count": count})
    red = (axes.get("satisfaction") or {}).get("unresolved_red") or {}
    if red.get("present") == "true":
        errors.append({"source": "run-determination.unresolved_red", "count": 1})
    if errors:
        group["errors"] = errors
    return group


def collect_qualification(record: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    value = record.get("qualification") if record else None
    if isinstance(value, str) and value:
        return {"value": value, "provenance": "carried"}
    return NOT_EVALUATED


# ---------------------------------------------------------------------------
# record assembly + defenses (D9)
# ---------------------------------------------------------------------------

def build_record(workspace_root: Path, unit_id: str, unit_type: str,
                 explicit_run_id: Optional[str]) -> Dict[str, Any]:
    run_id, resolution, determination = resolve_run_identity(
        workspace_root, unit_id, explicit_run_id)
    return assemble_record(unit_id, unit_type, run_id, resolution, determination)


def empty_config_group() -> Dict[str, Any]:
    return {field: NOT_EVALUATED for field in CONFIG_FIELDS}


def assemble_record(unit_id: str, unit_type: str, run_id: str, resolution: str,
                    determination: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    agent, host_pid, _host_name = collect_agent()
    synthesized = resolution == "synthesized"
    record = {
        "kind": KIND,
        "schema_version": SCHEMA_VERSION,
        "unit_id": unit_id,
        "unit_type": unit_type,
        "run_id": run_id,
        "run_id_resolution": resolution,
        "collected_at": now_iso(),
        "agent": agent,
        "config": empty_config_group(),
        "llm": collect_llm(agent, host_pid),
        "quality": collect_quality(None if synthesized else determination),
        "qualification": (NOT_EVALUATED if synthesized
                          else collect_qualification(determination)),
        "truncated": [],
    }
    return record


def mask_credentials(node: Any) -> Any:
    if isinstance(node, str):
        for name, pattern in CREDENTIAL_PATTERNS:
            if pattern.search(node):
                node = pattern.sub(f"[masked-credential:{name}]", node)
        return node
    if isinstance(node, dict):
        return {key: mask_credentials(value) for key, value in node.items()}
    if isinstance(node, list):
        return [mask_credentials(item) for item in node]
    return node


def _longest_string(container: Any, path: str
                    ) -> Optional[Tuple[Any, Any, str, str, int]]:
    best = None
    if isinstance(container, dict):
        items = container.items()
    elif isinstance(container, list):
        items = enumerate(container)
    else:
        return best
    for key, value in items:
        child_path = f"{path}.{key}" if isinstance(container, dict) else f"{path}[{key}]"
        if isinstance(value, str):
            if best is None or len(value) > best[4]:
                best = (container, key, child_path, value, len(value))
        else:
            nested = _longest_string(value, child_path)
            if nested and (best is None or nested[4] > best[4]):
                best = nested
    return best


def enforce_size_cap(record: Dict[str, Any]) -> List[str]:
    """Halve the largest string field until the serialization fits (V5)."""
    truncated: List[str] = []
    while True:
        blob = json.dumps(record, ensure_ascii=False).encode("utf-8")
        if len(blob) <= RECORD_SIZE_CAP_BYTES:
            return truncated
        target = _longest_string(record, "$")
        if target is None or target[4] <= 8:
            return truncated
        container, key, path, value, _ = target
        container[key] = value[:len(value) // 2]
        if path not in truncated:
            truncated.append(path)


def existing_record(workspace_root: Path, unit_id: str, run_id: str) -> bool:
    return any(record.get("unit_id") == unit_id and record.get("run_id") == run_id
               for record in load_records(workspace_root))


# ---------------------------------------------------------------------------
# dispatch records (Feature 061, C-EQ-03..C-EQ-07)
# ---------------------------------------------------------------------------

def load_snapshot(path_value: str, workspace_root: Path,
                  expected_config_id: str) -> Tuple[Dict[str, Any], Path]:
    candidate = Path(path_value)
    if not candidate.is_absolute():
        candidate = workspace_root / candidate
    try:
        data = json.loads(candidate.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ExecQuantError(f"cannot read config snapshot {candidate}: {exc}") from exc
    if not isinstance(data, dict):
        raise ExecQuantError(f"config snapshot is not a JSON object: {candidate}")
    if data.get("kind") != SNAPSHOT_KIND:
        raise ExecQuantError(
            f"config snapshot kind mismatch: expected {SNAPSHOT_KIND!r}, "
            f"got {data.get('kind')!r}")
    if data.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise ExecQuantError(
            f"config snapshot schema_version mismatch: expected "
            f"{SNAPSHOT_SCHEMA_VERSION}, got {data.get('schema_version')!r}")
    effective = data.get("effective")
    if not isinstance(effective, dict):
        raise ExecQuantError("config snapshot has no 'effective' object")
    canonical = json.dumps(effective, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    recomputed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    if recomputed != data.get("config_id"):
        raise ExecQuantError(
            "config snapshot integrity check failed: recomputed config_id "
            f"{recomputed} does not match snapshot config_id {data.get('config_id')!r}")
    if recomputed != expected_config_id:
        raise ExecQuantError(
            f"--config-id {expected_config_id!r} does not match the current "
            f"resolution ({recomputed}); no record written")
    return data, candidate


def dispatch_config(snapshot: Dict[str, Any], config_id: str,
                    snapshot_rel: str) -> Dict[str, Any]:
    effective = snapshot.get("effective") or {}
    quant = effective.get("quantification") if isinstance(effective.get("quantification"), dict) else {}

    def leaf(name: str) -> Any:
        value = effective.get(name)
        return NOT_EVALUATED if value in (None, "") else value

    method_requested = quant.get("requested")
    method_resolved = quant.get("resolved")
    source_chain = snapshot.get("source_chain")
    return {
        "config_id": config_id,
        "source_chain": source_chain if isinstance(source_chain, dict) else {},
        "method_requested": method_requested or NOT_EVALUATED,
        "method_resolved": method_resolved or NOT_EVALUATED,
        "mode": leaf("mode"),
        "cli": leaf("cli"),
        "model": leaf("model"),
        "reasoning_effort": leaf("reasoning_effort"),
        "context_window": leaf("context_window"),
        "extra_flags": leaf("extra_flags"),
        "snapshot": snapshot_rel,
    }


def dispatch_llm(effective: Dict[str, Any], config_id: str,
                 resolved: str) -> Dict[str, Any]:
    group: Dict[str, Any] = {
        "model": NOT_EVALUATED, "context_window": NOT_EVALUATED,
        "reasoning_effort": NOT_EVALUATED, "config_source": NOT_EVALUATED,
        "endpoint_candidates": NOT_EVALUATED, "connection_evidence": NOT_EVALUATED,
    }
    if resolved == "declared":
        for field in ("model", "reasoning_effort", "context_window"):
            value = effective.get(field)
            if value not in (None, ""):
                group[field] = {"value": value, "provenance": "configured"}
        group["config_source"] = {"value": f"execution-config:{config_id}",
                                  "provenance": "configured"}
    elif resolved == "qoder-settings":
        group.update(qoder_settings_llm())
    return group


def _iter_json_objects(path: Path):
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            node = json.loads(line)
        except ValueError:
            continue
        if isinstance(node, dict):
            yield node


def _find_int_fields(node: Any, names: Tuple[str, ...],
                     found: Dict[str, int]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in names and isinstance(value, int) and not isinstance(value, bool):
                found[key] = value
            _find_int_fields(value, names, found)
    elif isinstance(node, list):
        for item in node:
            _find_int_fields(item, names, found)


def _last_duration_ms(path: Path) -> Optional[int]:
    last = None
    for obj in _iter_json_objects(path):
        found: Dict[str, int] = {}
        _find_int_fields(obj, ("duration_ms",), found)
        if "duration_ms" in found:
            last = found["duration_ms"]
    return last


def _last_token_total(path: Path) -> Optional[int]:
    last = None
    for obj in _iter_json_objects(path):
        found: Dict[str, int] = {}
        _find_int_fields(obj, ("input_tokens", "output_tokens"), found)
        if "input_tokens" in found and "output_tokens" in found:
            last = found["input_tokens"] + found["output_tokens"]
    return last


_EXIT_RE = re.compile(r"exit=(-?\d+)")


def _read_exit_code(path: Path) -> Optional[int]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    matches = _EXIT_RE.findall(text)
    if not matches:
        return None
    try:
        return int(matches[-1])
    except ValueError:
        return None


def dispatch_quality(snapshot: Dict[str, Any], log_dir: Path, label: str) -> Dict[str, Any]:
    group: Dict[str, Any] = {
        "exit_code": NOT_EVALUATED, "elapsed_ms": NOT_EVALUATED,
        "tokens": NOT_EVALUATED, "errors": NOT_EVALUATED,
        "satisfaction": NOT_EVALUATED,
    }
    status_path = log_dir / f"{label}.status"
    exit_code = _read_exit_code(status_path)
    if exit_code is not None:
        group["exit_code"] = {"value": exit_code, "provenance": "measured"}
        group["errors"] = ([] if exit_code == 0
                           else [{"source": "dispatch.exit_code", "count": 1}])
    jsonl_path = log_dir / f"{label}.jsonl"
    duration = _last_duration_ms(jsonl_path)
    if duration is not None and duration >= 0:
        group["elapsed_ms"] = {"value": duration, "provenance": "measured"}
    elif status_path.is_file():
        resolved = _parse_iso(snapshot.get("resolved_at"))
        try:
            mtime = status_path.stat().st_mtime
        except OSError:
            mtime = None
        if resolved is not None and mtime is not None:
            delta = (datetime.fromtimestamp(mtime, timezone.utc)
                     - resolved).total_seconds() * 1000
            if delta >= 0:
                group["elapsed_ms"] = {"value": int(round(delta)),
                                       "provenance": "measured"}
    tokens = _last_token_total(jsonl_path)
    if tokens is not None and tokens >= 0:
        group["tokens"] = {"value": tokens, "provenance": "measured"}
    return group


def assemble_dispatch_record(unit_id: str, run_id: str, snapshot: Dict[str, Any],
                             snapshot_rel: str, log_dir: Path) -> Dict[str, Any]:
    effective = snapshot.get("effective") or {}
    quant = effective.get("quantification") if isinstance(
        effective.get("quantification"), dict) else {}
    resolved = quant.get("resolved") or NOT_EVALUATED
    agent, _pid, _host = collect_agent()
    config_id = snapshot.get("config_id")
    return {
        "kind": KIND,
        "schema_version": SCHEMA_VERSION,
        "unit_id": unit_id,
        "unit_type": "agent",
        "run_id": run_id,
        "run_id_resolution": "explicit",
        "collected_at": now_iso(),
        "agent": agent,
        "config": dispatch_config(snapshot, config_id, snapshot_rel),
        "llm": dispatch_llm(effective, config_id, resolved),
        "quality": dispatch_quality(snapshot, log_dir, run_id),
        "qualification": NOT_EVALUATED,
        "truncated": [],
    }


def append_record_locked(workspace_root: Path, record: Dict[str, Any],
                         unit_id: str, run_id: str) -> Optional[Path]:
    """Check-then-write under one POSIX flock (C-EQ-07).

    Entries are separate files, so the lock now serializes only the duplicate
    check instead of sheltering a shared append target. On platforms without
    ``fcntl`` the operation degrades to the same sequence without claiming
    atomicity.
    """
    lock_path = storage_dir(workspace_root) / LOCK_NAME
    lock_handle = None
    locked = False
    try:
        lock_handle = lock_path.open("a", encoding="utf-8")
        try:
            import fcntl
            fcntl.flock(lock_handle, fcntl.LOCK_EX)
            locked = True
        except ImportError:  # documented non-POSIX degradation
            locked = False
        if existing_record(workspace_root, unit_id, run_id):
            return None
        return write_entry(records_dir(workspace_root), record)
    finally:
        if lock_handle is not None:
            if locked:
                try:
                    import fcntl
                    fcntl.flock(lock_handle, fcntl.LOCK_UN)
                except Exception:
                    pass
            lock_handle.close()


def normalize_record_view(record: Dict[str, Any]) -> Dict[str, Any]:
    """v1 records participate read-only via an output-only shape upgrade."""
    config = record.get("config")
    if isinstance(config, dict):
        record["config"] = {field: config.get(field, NOT_EVALUATED)
                            for field in CONFIG_FIELDS}
    else:
        record["config"] = empty_config_group()
    quality = record.get("quality")
    if isinstance(quality, dict) and "exit_code" not in quality:
        quality["exit_code"] = NOT_EVALUATED
    return record


# ---------------------------------------------------------------------------
# actions
# ---------------------------------------------------------------------------

def action_collect(args: argparse.Namespace) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    unit_id = (args.unit_id or "").strip()
    if not validate_unit_id(unit_id):
        raise InputError(f"invalid --unit-id: {args.unit_id!r}")
    resolved_type = unit_type_of(unit_id)
    if resolved_type == "agent":
        raise InputError(
            "collect does not accept agent: units — agent records are written "
            "only by collect-dispatch")
    if args.unit_type and args.unit_type != resolved_type:
        raise InputError(
            f"--unit-type {args.unit_type!r} contradicts the unit-id form "
            f"{unit_id!r} (expected {resolved_type!r})")
    records_store, _scores_store = bootstrap_storage(workspace_root)
    run_id, resolution, determination = resolve_run_identity(
        workspace_root, unit_id, args.run_id)
    record = assemble_record(unit_id, resolved_type, run_id, resolution, determination)
    record = mask_credentials(record)
    truncated = enforce_size_cap(record)
    record["truncated"] = truncated
    target = append_record_locked(workspace_root, record, unit_id, run_id)
    if target is None:
        print(f"exec-quant: duplicate record for ({unit_id}, {run_id}); "
              f"no second row written -> {records_store}")
        return 0
    print(f"exec-quant: recorded {unit_id} run={record['run_id']} "
          f"resolution={resolution} -> {target}")
    return 0


def action_collect_dispatch(args: argparse.Namespace) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    unit_id = (args.unit_id or "").strip()
    if not unit_id.startswith("agent:") or not validate_unit_id(unit_id):
        raise InputError(
            "collect-dispatch requires --unit-id agent:<slug> "
            "(agent records only describe external dispatches)")
    if args.unit_type and args.unit_type != "agent":
        raise InputError(
            f"--unit-type {args.unit_type!r} contradicts the agent unit id {unit_id!r}")
    if not args.run_id:
        raise InputError("collect-dispatch requires --run-id <dispatch-label>")
    if not args.snapshot:
        raise InputError("collect-dispatch requires --snapshot <path>")
    if not args.config_id:
        raise InputError("collect-dispatch requires --config-id <id>")
    snapshot, snapshot_path = load_snapshot(args.snapshot, workspace_root,
                                            args.config_id)
    log_dir_value = snapshot.get("log_dir") or DEFAULT_DISPATCH_LOG_DIR.as_posix()
    log_dir = Path(str(log_dir_value))
    if not log_dir.is_absolute():
        log_dir = workspace_root / log_dir
    try:
        snapshot_rel = snapshot_path.resolve().relative_to(
            workspace_root.resolve()).as_posix()
    except ValueError:
        snapshot_rel = snapshot_path.as_posix()
    records_store, _scores_store = bootstrap_storage(workspace_root)
    record = assemble_dispatch_record(unit_id, args.run_id, snapshot, snapshot_rel,
                                      log_dir)
    record = mask_credentials(record)
    truncated = enforce_size_cap(record)
    record["truncated"] = truncated
    target = append_record_locked(workspace_root, record, unit_id, args.run_id)
    if target is None:
        print(f"exec-quant: duplicate record for ({unit_id}, {args.run_id}); "
              f"no second row written -> {records_store}")
        return 0
    print(f"exec-quant: recorded {unit_id} run={args.run_id} "
          f"config_id={record['config']['config_id']} -> {target}")
    return 0


def _parse_since(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            stamp = datetime.strptime(text, fmt)
            return stamp.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        raise InputError(f"invalid --since: {value!r} (expected ISO date or timestamp)")


def _field_text(node: Any) -> str:
    if node == NOT_EVALUATED:
        return "-"
    if isinstance(node, dict):
        return str(node.get("value"))
    return str(node)


def load_records(workspace_root: Path) -> List[Dict[str, Any]]:
    base = storage_dir(workspace_root)
    return (read_jsonl_safe(base / LEGACY_RECORDS_NAME)
            + read_entry_files(base / RECORDS_DIR_NAME))


def load_scores(workspace_root: Path) -> List[Dict[str, Any]]:
    base = storage_dir(workspace_root)
    return (read_jsonl_safe(base / LEGACY_SCORES_NAME)
            + read_entry_files(base / SCORES_DIR_NAME))


def load_store(workspace_root: Path):
    return load_records(workspace_root), load_scores(workspace_root)


def read_jsonl_safe(path: Path) -> List[Dict[str, Any]]:
    if not path.is_file():
        return []
    entries = []
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict):
                    entries.append(entry)
    except OSError:
        return []
    return entries


def action_list_records(args: argparse.Namespace) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    since = _parse_since(args.since)
    if args.format not in ("text", "json"):
        raise InputError(f"invalid --format: {args.format!r}")
    records, scores = load_store(workspace_root)
    joined: List[Dict[str, Any]] = []
    for record in records:
        if args.unit_id and record.get("unit_id") != args.unit_id:
            continue
        if args.unit_type and record.get("unit_type") != args.unit_type:
            continue
        if args.run_id and record.get("run_id") != args.run_id:
            continue
        if args.config_id:
            config = record.get("config")
            if not isinstance(config, dict) or config.get("config_id") != args.config_id:
                continue
        collected = _parse_iso(record.get("collected_at"))
        if since and collected and collected < since:
            continue
        matches = [s for s in scores
                   if s.get("unit_id") == record.get("unit_id")
                   and s.get("run_id") == record.get("run_id")]
        matches.sort(key=lambda s: (str(s.get("scored_at") or ""),))
        entry = normalize_record_view(dict(record))
        entry["scores"] = matches
        joined.append(entry)
    if args.format == "json":
        print(json.dumps(joined, ensure_ascii=False, indent=2))
        return 0
    for entry in joined:
        latest = entry["scores"][-1] if entry["scores"] else None
        quality = entry.get("quality") or {}
        agent = entry.get("agent") or {}
        llm = entry.get("llm") or {}
        endpoints = llm.get("endpoint_candidates")
        endpoint_count = len(endpoints) if isinstance(endpoints, dict) else 0
        print(f"{entry.get('unit_id')} type={entry.get('unit_type')} "
              f"run={entry.get('run_id')} resolution={entry.get('run_id_resolution')} "
              f"collected={entry.get('collected_at')}")
        print(f"  agent: resolution={agent.get('resolution')} "
              f"name={_field_text(agent.get('name'))} "
              f"version={_field_text(agent.get('version'))}")
        print(f"  llm: model={_field_text(llm.get('model'))} "
              f"context_window={_field_text(llm.get('context_window'))} "
              f"effort={_field_text(llm.get('reasoning_effort'))} "
              f"endpoints={endpoint_count}")
        print(f"  quality: elapsed_ms={_field_text(quality.get('elapsed_ms'))} "
              f"tokens={_field_text(quality.get('tokens'))} "
              f"satisfaction={_field_text(quality.get('satisfaction'))} "
              f"qualification={_field_text(entry.get('qualification'))}")
        if latest:
            print(f"  score: {latest.get('score')} "
                  f"provenance={latest.get('provenance')} "
                  f"at={latest.get('scored_at')}"
                  + (f" note={latest.get('note')}" if latest.get("note") else ""))
    print(f"exec-quant: {len(joined)} record(s) listed", file=sys.stderr)
    return 0


def action_score(args: argparse.Namespace) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    unit_id = (args.unit_id or "").strip()
    if not validate_unit_id(unit_id):
        raise InputError(f"invalid --unit-id: {args.unit_id!r}")
    if not args.run_id:
        raise InputError("score requires --run-id (the record being scored)")
    if args.score is None:
        raise InputError("score requires --score (1-5)")
    if not (1 <= args.score <= 5):
        raise InputError(f"--score must be within 1-5, got {args.score}")
    target = next((r for r in load_records(workspace_root)
                   if r.get("unit_id") == unit_id and r.get("run_id") == args.run_id), None)
    if target is None:
        raise InputError(
            f"no record for ({unit_id}, {args.run_id}) — score appends to an "
            f"existing record, run collect first")
    entry = {
        "kind": KIND,
        "entry_type": "score",
        "unit_id": unit_id,
        "unit_type": target.get("unit_type"),
        "run_id": args.run_id,
        "score": args.score,
        "scored_at": now_iso(),
        "provenance": "user-given",
    }
    if args.note:
        entry["note"] = args.note
    target_file = write_entry(scores_dir(workspace_root), entry)
    print(f"exec-quant: scored {unit_id} run={args.run_id} "
          f"score={args.score} provenance=user-given -> {target_file}")
    return 0


USAGE_LINE = ("usage: exec-quant.py --action {" + ",".join(ACTIONS) + "} "
              "[--unit-id ID] [--unit-type TYPE] [--run-id ID] [--score 1-5] "
              "[--note TEXT] [--since DATE] [--snapshot PATH] [--config-id ID] "
              "[--format text|json] [--workspace-root PATH]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="exec-quant.py", allow_abbrev=False)
    parser.add_argument("--workspace-root", default=None)
    parser.add_argument("--action", required=True,
                        choices=["collect", "list-records", "score",
                                 "collect-dispatch", "args-manifest"])
    parser.add_argument("--unit-id", default=None)
    parser.add_argument("--unit-type", default=None, choices=list(UNIT_TYPES))
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--score", type=int, default=None)
    parser.add_argument("--note", default=None)
    parser.add_argument("--since", default=None)
    parser.add_argument("--snapshot", default=None)
    parser.add_argument("--config-id", dest="config_id", default=None)
    parser.add_argument("--format", default="text", choices=["text", "json"])
    return parser


def action_args_manifest(args: argparse.Namespace) -> int:
    """C-22 (063): machine-readable per-action argument manifest, BUILT FROM
    this engine's own parser — every classified flag is verified against the
    live parser's option strings before emitting. Pure query face: no
    workspace access, no write."""
    parser = build_parser()
    live = {opt for act in parser._actions for opt in act.option_strings}
    manifest: Dict[str, Any] = {}
    for action in ACTIONS:
        spec = ARG_MANIFEST.get(action)
        if spec is None:
            raise InputError(f"args-manifest: action {action!r} has no manifest spec")
        for key in ("required", "source"):
            unknown = [f for f in spec[key] if f not in live]
            if unknown:
                raise InputError(
                    f"args-manifest: {action} {key} flags are not options of "
                    f"this engine's parser: {unknown}")
        manifest[action] = {"required": list(spec["required"]),
                            "source": list(spec["source"])}
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.action == "collect":
            return action_collect(args)
        if args.action == "collect-dispatch":
            return action_collect_dispatch(args)
        if args.action == "list-records":
            return action_list_records(args)
        if args.action == "args-manifest":
            return action_args_manifest(args)
        return action_score(args)
    except InputError as exc:
        print(USAGE_LINE, file=sys.stderr)
        print(f"exec-quant: usage error: {exc}", file=sys.stderr)
        return 2
    except ExecQuantError as exc:
        print(f"exec-quant: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # non-blocking guarantee: never raise into the caller
        print(f"exec-quant: unexpected failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
