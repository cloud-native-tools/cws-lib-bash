#!/usr/bin/env python3
"""line-registry.py — environment Line Registry / envelope / lifecycle engine.

064.  Python 3.8+ stdlib only.  One file owns the file-based state:

  * per-line registry entry   $REGISTRY/<line_id>.json   (atomic replace)
  * same-line lock            $REGISTRY/<line_id>.lock   (fcntl.flock)
  * ownership manifest        $REGISTRY/manifests/<line_id>.json
  * driver lease              $REGISTRY/<line_id>.driver.lock
  * stage reservation         $REGISTRY/reservations/<line_id>.<stage>.json

Exit codes: 0 ok, 2 usage/validation, 3 held by an active resource,
4 identity cannot be computed, 6 registry I/O or corruption.
"""
from __future__ import annotations

import argparse
import contextlib
import errno
import fcntl
import hashlib
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1
EXIT_OK = 0
EXIT_USAGE = 2
EXIT_HELD = 3
EXIT_NO_IDENTITY = 4
EXIT_IO = 6

LINE_ID_RE = re.compile(r"^[a-z0-9][A-Za-z0-9-]{7,63}$")
RUN_ID_RE = re.compile(r"^r[0-9]{8}T[0-9]{6}Z-[0-9a-f]{4}$")
SLUG_RE = re.compile(r"[^a-z0-9]+")

STATE_VALUES = {"active", "waiting", "stalled", "completed", "orphaned", "stale", "closed"}
ACTIVE_STATES = {"active", "waiting"}
HOLDING_STATES = {"active", "completed"}
EVENT_VALUES = {
    "prompt", "pid", "heartbeat", "status", "log-start", "log-terminal",
    "watcher-verdict", "monitor", "registry-update", "integration",
}
ATTRIBUTION_VALUES = {"own", "foreign", "stale-run", "unattributed", "legacy"}
WAITING_REASONS = {"ownership-overlap", "concurrency-cap"}
INTEGRATION_RESULTS = {"merged", "failed"}
DEFAULT_TTL = 600
DEFAULT_LOCK_TIMEOUT = 10.0
DEFAULT_PORT_START = 39000
DEFAULT_BLOCK_SIZE = 20
DEFAULT_CONCURRENCY_CAP = 4
RUNTIME_RECORD_DIRS = (
    Path(".specify") / "memory" / "feedback",
    Path(".specify") / "memory" / "session",
    Path(".specify") / "memory" / "knowledge",
    Path(".specify") / "memory" / "exec-quant",
)

ACTIONS = {
    "register", "update", "deregister", "list", "resolve-message",
    "verify-identity", "classify-remote", "reattach-brief",
    "lease-acquire", "lease-renew", "lease-release", "lease-break",
    "reserve", "reservation-status", "reservation-break",
    "orphan-check", "ownership-check", "release-ownership", "promote-waiting",
    "integration-enqueue", "integration-plan", "integration-record",
    "allocate-resources", "archive-runtime",
}


class EngineError(Exception):
    def __init__(self, code: int, message: str, **extra):
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra


class LockTimeout(EngineError):
    def __init__(self, path: Path, timeout: float):
        super().__init__(
            EXIT_HELD,
            f"timed out after {timeout}s waiting for lock {path}",
            path=str(path),
        )


class RegistryIOError(EngineError):
    def __init__(self, path: Path, message: str):
        super().__init__(EXIT_IO, message, path=str(path))


# ---------------------------------------------------------------- primitives


def now_epoch() -> int:
    return int(time.time())


def now_iso(at: int | None = None) -> str:
    return datetime.fromtimestamp(at if at is not None else time.time(), timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def utc_stamp(at: float | None = None) -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(at if at is not None else time.time()))


def slugify(value: str, limit: int = 20) -> str:
    slug = SLUG_RE.sub("-", str(value).lower()).strip("-")
    slug = slug[:limit].strip("-")
    return slug or "line"


def generate_line_id(project_dir: Path, now: float | None = None) -> str:
    return f"{slugify(Path(project_dir).name)}-{utc_stamp(now)}-{secrets.token_hex(2)}"


def generate_run_id(now: float | None = None) -> str:
    return f"r{utc_stamp(now)}-{secrets.token_hex(2)}"


def resolve_registry_dir() -> Path:
    override = os.environ.get("SPECIFY_LINE_REGISTRY_DIR")
    if override:
        return Path(override).expanduser().resolve()
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        return Path(xdg).expanduser().resolve() / "spec-kit" / "lines"
    home = Path(os.environ.get("HOME", "~")).expanduser().resolve()
    return home / ".local" / "state" / "spec-kit" / "lines"


def resolve_runtime_dir() -> Path:
    override = os.environ.get("SPECIFY_LINE_RUNTIME_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(os.environ.get("HOME", "~")).expanduser().resolve()


def ensure_registry_dir(path: Path) -> None:
    try:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError as exc:
        raise RegistryIOError(path, f"cannot create registry dir: {exc}")
    if not os.access(path, os.W_OK | os.X_OK):
        raise RegistryIOError(path, "registry dir is not writable")


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        _fsync_dir(path.parent)
    except OSError as exc:
        with contextlib.suppress(OSError):
            tmp.unlink()
        raise RegistryIOError(path, f"cannot write registry entry: {exc}")


def exclusive_write_json(path: Path, data: dict) -> None:
    """Atomic create that refuses to overwrite (V-LR-2)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError:
            raise EngineError(EXIT_USAGE, f"line already exists: {path}", path=str(path))
        _fsync_dir(path.parent)
    except OSError as exc:
        raise RegistryIOError(path, f"cannot create registry entry: {exc}")
    finally:
        with contextlib.suppress(OSError):
            tmp.unlink()


def read_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise RegistryIOError(path, f"unreadable registry JSON: {exc}")
    if not isinstance(data, dict):
        raise RegistryIOError(path, "registry entry is not a JSON object")
    return data


def read_json_optional(path: Path) -> dict | None:
    try:
        return read_json(path)
    except FileNotFoundError:
        return None


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
    try:
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
            fh.flush()
            os.fsync(fh.fileno())
    except OSError as exc:
        raise RegistryIOError(path, f"cannot append history: {exc}")


@contextlib.contextmanager
def line_lock(lock_path: Path, timeout: float = DEFAULT_LOCK_TIMEOUT):
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock_path, "a+")
    deadline = time.time() + timeout
    try:
        while True:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    raise
                if time.time() >= deadline:
                    raise LockTimeout(lock_path, timeout)
                time.sleep(0.05)
        yield
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        fh.close()


def entry_path(reg: Path, line_id: str) -> Path:
    return reg / f"{line_id}.json"


def lock_path(reg: Path, line_id: str) -> Path:
    return reg / f"{line_id}.lock"


def manifest_path(reg: Path, line_id: str) -> Path:
    return reg / "manifests" / f"{line_id}.json"


def lease_path(reg: Path, line_id: str) -> Path:
    return reg / f"{line_id}.driver.lock"


def lease_history_path(reg: Path, line_id: str) -> Path:
    return reg / f"{line_id}.lease-history.jsonl"


def reservation_path(reg: Path, line_id: str, stage: str) -> Path:
    return reg / "reservations" / f"{line_id}.{stage}.json"


def reservation_history_path(reg: Path, line_id: str, stage: str) -> Path:
    return reg / "reservations" / f"{line_id}.{stage}.reservation-history.jsonl"


# ---------------------------------------------------------------- process identity


def process_start_token(pid: int) -> str | None:
    if pid <= 0:
        return None
    stat_path = Path(f"/proc/{pid}/stat")
    if stat_path.exists():
        try:
            fields = stat_path.read_text(encoding="utf-8", errors="replace").split()
            if len(fields) > 21:
                return fields[21]
        except OSError:
            pass
    try:
        proc = subprocess.run(
            ["ps", "-p", str(pid), "-o", "lstart="],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    token = " ".join(proc.stdout.split())
    return token or None


def process_alive(pid: int | None, token: str | None = None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    if token:
        actual = process_start_token(pid)
        if actual is not None and actual != token:
            return False
    return True


def process_cwd(pid: int) -> Path | None:
    link = f"/proc/{pid}/cwd"
    try:
        target = os.readlink(link)
    except OSError:
        return None
    try:
        return Path(target).resolve()
    except (OSError, RuntimeError):
        return Path(os.path.abspath(target))


def branch_of(repo: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    value = proc.stdout.strip()
    return value or None


# ---------------------------------------------------------------- validation


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EngineError(EXIT_USAGE, message)


def validate_line_id(line_id: str) -> str:
    require(bool(line_id) and bool(LINE_ID_RE.match(line_id)), f"invalid line_id: {line_id!r}")
    return line_id


def validate_run_id(run_id: str) -> str:
    require(bool(run_id) and bool(RUN_ID_RE.match(run_id)), f"invalid run_id: {run_id!r}")
    return run_id


def validate_state(state: str) -> str:
    require(state in STATE_VALUES, f"invalid state: {state!r} (expected one of {sorted(STATE_VALUES)})")
    return state


def _check_abs(path_value: str, field: str) -> None:
    require(bool(path_value), f"{field} is required")
    require(os.path.isabs(path_value), f"{field} must be an absolute path: {path_value!r}")


def _validate_remote(remote: dict) -> None:
    require(isinstance(remote, dict), "remote must be a JSON object")
    for key in ("alias", "run_user", "remote_root"):
        require(bool(remote.get(key)), f"remote.{key} is required")


def _validate_runtime_paths(entry: dict) -> None:
    stage = entry.get("stage")
    if not stage:
        return
    for key in ("prompt_path", "status_path", "log_path", "heartbeat_path"):
        value = entry.get(key)
        _check_abs(value or "", key)


def _default_runtime_paths(entry: dict) -> None:
    stage = entry.get("stage")
    if not stage:
        return
    runtime = resolve_runtime_dir()
    line_id = entry["line_id"]
    defaults = {
        "prompt_path": runtime / f"prompt-{line_id}-{stage}.md",
        "status_path": runtime / f"status-{line_id}-{stage}",
        "log_path": runtime / f"log-{line_id}-{stage}.log",
        "heartbeat_path": runtime / f"heartbeat-{line_id}-{stage}.log",
    }
    for key, value in defaults.items():
        entry.setdefault(key, str(value))
    meta = entry.get("meta_paths")
    if not isinstance(meta, dict):
        meta = {}
    meta.setdefault("prompt", str(runtime / f"prompt-{line_id}-{stage}.md.meta.json"))
    meta.setdefault("log", str(runtime / f"log-{line_id}-{stage}.log.meta.jsonl"))
    entry["meta_paths"] = meta


def validate_entry(entry: dict) -> dict:
    for field in ("line_id", "run_id", "project_dir", "repo_root", "driver_session", "cli", "state"):
        require(bool(entry.get(field)), f"required field missing: {field}")
    validate_line_id(entry["line_id"])
    validate_run_id(entry["run_id"])
    validate_state(entry["state"])
    _check_abs(entry["project_dir"], "project_dir")
    _check_abs(entry["repo_root"], "repo_root")
    state = entry["state"]
    if state == "waiting":
        reason = entry.get("waiting_reason")
        require(reason in WAITING_REASONS, f"waiting requires waiting_reason in {sorted(WAITING_REASONS)}")
        require(bool(entry.get("queued_at")), "waiting requires queued_at")
        if reason == "ownership-overlap":
            require(bool(entry.get("holder_line_id")), "ownership-overlap waiting requires holder_line_id")
    if state == "closed":
        require(bool(entry.get("closed_at")), "closed requires closed_at")
    if entry.get("remote") is not None:
        _validate_remote(entry["remote"])
    if entry.get("integration_result") is not None:
        result = entry["integration_result"]
        require(isinstance(result, dict), "integration_result must be an object")
        require(result.get("status") in INTEGRATION_RESULTS,
                f"integration_result.status must be one of {sorted(INTEGRATION_RESULTS)}")
    worktree = entry.get("worktree_path")
    if worktree:
        resolved = Path(worktree).resolve()
        for key in ("repo_root", "project_dir"):
            root = Path(entry[key]).resolve()
            require(resolved != root and root not in resolved.parents,
                    f"worktree_path must be outside {key}: {worktree}")
    for pid_field, token_field in (
        ("runner_pid", "runner_start_token"),
        ("cli_pid", "cli_start_token"),
    ):
        if entry.get(pid_field) is not None:
            require(entry.get(token_field) is not None,
                    f"{pid_field} requires {token_field}")
    if entry["state"] == "active" and entry.get("stage"):
        _validate_runtime_paths(entry)
        require(entry.get("runner_pid") is not None, "dispatched active entry requires runner_pid")
        require(entry.get("cli_pid") is not None, "dispatched active entry requires cli_pid")
    return entry


def check_spine_consistency(entry: dict, spine_path: str | None) -> None:
    if not spine_path:
        return
    path = Path(spine_path)
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^\s*state\s*[:=]\s*([A-Za-z_-]+)", text, re.MULTILINE)
    if not match:
        return
    spine_state = match.group(1)
    mapping = {
        "active": {"running", "retrying"},
        "stalled": {"stalled"},
        "completed": {"done"},
    }
    if entry["state"] in mapping and spine_state not in mapping[entry["state"]]:
        raise EngineError(
            EXIT_USAGE,
            f"registry state {entry['state']!r} contradicts spine state {spine_state!r}",
            spine=str(path),
        )


# ---------------------------------------------------------------- command context


class Context:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.reg = resolve_registry_dir()

    def load(self, line_id: str, *, optional: bool = False) -> dict | None:
        path = entry_path(self.reg, line_id)
        try:
            return read_json(path)
        except FileNotFoundError:
            if optional:
                return None
            raise EngineError(EXIT_NO_IDENTITY, f"registry entry not found: {path}", path=str(path))

    def mutate(self, line_id: str, mutate):
        ensure_registry_dir(self.reg)
        with line_lock(lock_path(self.reg, line_id)):
            entry = self.load(line_id)
            mutate(entry)
            entry["updated_at"] = now_iso()
            validate_entry(entry)
            atomic_write_json(entry_path(self.reg, line_id), entry)
            return entry


def emit(payload, code: int = EXIT_OK) -> int:
    print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    return code


def fail_from(exc: EngineError) -> int:
    payload = {"ok": False, "error": {"message": exc.message, "code": exc.code, **exc.extra}}
    if exc.code == EXIT_USAGE:
        print(json.dumps(payload, sort_keys=True, ensure_ascii=False), file=sys.stderr)
    else:
        print(json.dumps(payload, sort_keys=True, ensure_ascii=False))
    return exc.code


# ---------------------------------------------------------------- actions: lifecycle


def action_register(ctx: Context) -> int:
    args = ctx.args
    ensure_registry_dir(ctx.reg)
    require(bool(args.project_dir), "register requires --project-dir")
    require(bool(args.repo_root), "register requires --repo-root")
    project_dir = Path(args.project_dir).expanduser().resolve()
    repo_root = Path(args.repo_root).expanduser().resolve()
    require(project_dir.is_absolute(), "project_dir must be absolute")
    require(repo_root.is_absolute(), "repo_root must be absolute")
    line_id = validate_line_id(args.line_id or generate_line_id(project_dir))
    run_id = validate_run_id(args.run_id or generate_run_id())
    state = args.state or "active"
    validate_state(state)
    require(state in {"active", "waiting"}, "register state must be active or waiting")
    driver_session = args.driver_session or os.environ.get("SPECIFY_DRIVER_SESSION") or f"pid:{os.getppid()}"
    cli = args.cli or os.environ.get("DISPATCH_CLI") or "qodercli"
    at = now_iso()
    entry = {
        "schema_version": SCHEMA_VERSION,
        "line_id": line_id,
        "run_id": run_id,
        "project_dir": str(project_dir),
        "repo_root": str(repo_root),
        "driver_session": driver_session,
        "cli": cli,
        "state": state,
        "last_event": "registered",
        "created_at": at,
        "claimed_ns": time.time_ns(),
        "updated_at": at,
        "run_history": [],
    }
    if args.worktree_path:
        entry["worktree_path"] = str(Path(args.worktree_path).expanduser().resolve())
    if args.branch:
        entry["branch"] = args.branch
    if args.base_sha:
        entry["base_sha"] = args.base_sha
    if args.write_line:
        require(bool(entry.get("worktree_path")), "--write-line requires --worktree-path")
        require(bool(entry.get("branch")), "--write-line requires --branch")
        require(bool(entry.get("base_sha")), "--write-line requires --base-sha")
    entry["write_line"] = bool(args.write_line or args.manifest or args.owned_paths)
    if state == "waiting":
        entry["waiting_reason"] = args.waiting_reason or "ownership-overlap"
        entry["queued_at"] = args.queued_at or at
        if entry["waiting_reason"] == "ownership-overlap":
            require(bool(args.holder_line_id), "--holder-line-id required for ownership-overlap")
            entry["holder_line_id"] = args.holder_line_id
    manifest_view = None
    if args.manifest:
        manifest = load_manifest(Path(args.manifest), line_id, repo_root)
        entry["owned_paths"] = list(manifest["owned_paths"])
        entry["ownership_manifest_path"] = str(Path(args.manifest).resolve())
        # Registration is a fresh claim: a caller-supplied released_at must
        # not turn the new line into a non-blocking owner.
        for key in ("released_at", "release_reason", "evidence_ref"):
            manifest.pop(key, None)
        manifest["claimed_at"] = entry["created_at"]
        manifest["claimed_ns"] = entry["claimed_ns"]
        manifest_view = manifest
    elif args.owned_paths:
        raw_paths = json.loads(args.owned_paths)
        require(isinstance(raw_paths, list), "owned_paths must be a JSON array")
        entry["owned_paths"] = [normalize_path(p, repo_root) for p in raw_paths]
        manifest_view = {
            "line_id": line_id,
            "owned_paths": list(entry["owned_paths"]),
            "read_only_paths": [],
            "forbidden_paths": [],
        }
    if args.remote:
        entry["remote"] = json.loads(args.remote)
    if args.resources:
        entry["resources"] = json.loads(args.resources)
    if args.spine:
        entry["spine_path"] = str(Path(args.spine).expanduser().resolve())
    validate_entry(entry)
    if entry["state"] == "active" and manifest_view is not None:
        _raise_if_ownership_conflict(ctx, entry, manifest_view)
    if entry.get("worktree_path"):
        _ensure_unique_worktree(ctx.reg, entry["worktree_path"], line_id)
    exclusive_write_json(entry_path(ctx.reg, line_id), entry)
    if args.manifest and manifest_view is not None \
            and not manifest_path(ctx.reg, line_id).exists():
        atomic_write_json(manifest_path(ctx.reg, line_id), manifest_view)
    return emit(entry)


def _apply_update(entry: dict, args: argparse.Namespace) -> None:
    previous_run = entry.get("run_id")
    scalar = {
        "stage": "stage",
        "state": "state",
        "last_event": "last_event",
        "driver_session": "driver_session",
        "cli": "cli",
        "worktree_path": "worktree_path",
        "branch": "branch",
        "base_sha": "base_sha",
        "waiting_reason": "waiting_reason",
        "holder_line_id": "holder_line_id",
        "queued_at": "queued_at",
        "ready_for_merge_at": "ready_for_merge_at",
        "prompt_path": "prompt_path",
        "status_path": "status_path",
        "log_path": "log_path",
        "heartbeat_path": "heartbeat_path",
        "spine_path": "spine_path",
    }
    for flag, key in scalar.items():
        value = getattr(args, flag, None)
        if value is not None:
            entry[key] = value
    if args.run_id:
        validate_run_id(args.run_id)
        if previous_run and args.run_id != previous_run:
            history = entry.setdefault("run_history", [])
            history.append({
                "run_id": previous_run,
                "started_at": entry.get("created_at") or entry.get("updated_at") or now_iso(),
                "ended_at": now_iso(),
                "outcome": "superseded",
            })
        entry["run_id"] = args.run_id
    if args.state is not None:
        validate_state(args.state)
        require(args.state != "closed", "use deregister to close a line")
        if args.state == "active":
            for key in ("waiting_reason", "holder_line_id", "queued_at"):
                entry.pop(key, None)
    for pid_field, token_field in (
        ("runner_pid", "runner_start_token"),
        ("cli_pid", "cli_start_token"),
    ):
        pid = getattr(args, pid_field)
        token = getattr(args, token_field)
        if pid is not None:
            pid = int(pid)
            entry[pid_field] = pid
            if token is None:
                token = process_start_token(pid)
                require(token is not None, f"cannot derive start token for {pid_field}={pid}; pass {token_field}")
            entry[token_field] = token
        elif token is not None:
            entry[token_field] = token
    bools = {
        "merge_ready": args.merge_ready,
        "worktree_retained": args.worktree_retained,
    }
    for key, raw in bools.items():
        if raw is not None:
            entry[key] = _parse_bool(raw)
    json_fields = {
        "meta_paths": args.meta_json,
        "resources": args.resources,
        "remote": args.remote,
        "owned_paths": args.owned_paths,
    }
    for key, raw in json_fields.items():
        if raw is not None:
            entry[key] = json.loads(raw)
    if args.stage:
        _default_runtime_paths(entry)
    if args.merge_ready is not None:
        merge_ready = _parse_bool(args.merge_ready)
        if merge_ready:
            require(entry.get("state") == "completed", "merge_ready requires state=completed")
            entry.setdefault("ready_for_merge_at", now_iso())
        else:
            entry.pop("ready_for_merge_at", None)


def _parse_bool(raw) -> bool:
    if isinstance(raw, bool):
        return raw
    value = str(raw).strip().lower()
    require(value in {"true", "false", "1", "0", "yes", "no"},
            f"invalid boolean: {raw!r}")
    return value in {"true", "1", "yes"}


def action_update(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    entry = ctx.load(line_id)

    def mutate(data):
        previous_state = data.get("state")
        data_previous = dict(data)
        _apply_update(data, args)
        require(previous_state != "closed" or data.get("state") == "closed",
                "closed is terminal; a new attempt requires a new line")
        if args.owned_paths is not None:
            raw_paths = json.loads(args.owned_paths)
            require(isinstance(raw_paths, list), "owned_paths must be a JSON array")
            require(bool(raw_paths), "owned_paths cannot be emptied; use release-ownership")
            require(_manifest_for_entry(ctx.reg, data) is None,
                    "owned_paths are owned by the manifest; use ownership-check to change them")
            data["owned_paths"] = [
                normalize_path(p, Path(data["repo_root"])) for p in raw_paths
            ]
            if data.get("state") == "active":
                view = {
                    "line_id": line_id,
                    "owned_paths": list(data["owned_paths"]),
                    "read_only_paths": [],
                    "forbidden_paths": [],
                }
                _raise_if_ownership_conflict(ctx, data, view)
        if args.worktree_path is not None:
            new_worktree = (
                str(Path(args.worktree_path).expanduser().resolve())
                if args.worktree_path else ""
            )
            previous_worktree = data_previous.get("worktree_path")
            require(not previous_worktree or new_worktree == previous_worktree,
                    "worktree_path is immutable once set; register a new line instead")
            data["worktree_path"] = new_worktree
        for key in ("branch", "base_sha"):
            if getattr(args, key) is not None and data_previous.get(key) is not None:
                require(getattr(args, key) == data_previous.get(key),
                        f"{key} is immutable once set")
        if data.get("state") == "active" and previous_state != "active":
            require(previous_state in {"waiting", "stalled"},
                    f"cannot transition from {previous_state!r} to active; "
                    "closed/stale/orphaned/completed are not revivable")
            # Every path into active must pass the ownership gate, not just
            # ownership-check / promote-waiting (P0-01 bypass found in review).
            if _entry_released(ctx, data):
                # A released write line must re-acquire via ownership-check
                # (which clears released_at / records a new claim) before it
                # can become active again.
                raise EngineError(
                    EXIT_HELD,
                    "ownership was released; re-acquire with ownership-check before becoming active",
                    line_id=line_id,
                )
            manifest = _entry_manifest_view(ctx, data)
            if manifest is not None:
                _raise_if_ownership_conflict(ctx, data, manifest)
        if data.get("worktree_path"):
            _ensure_unique_worktree(ctx.reg, data["worktree_path"], line_id)
        if args.spine:
            check_spine_consistency(data, args.spine)
        elif data.get("spine_path"):
            check_spine_consistency(data, data["spine_path"])

    return emit(ctx.mutate(line_id, mutate))


def action_deregister(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    require(bool(args.reason), "deregister requires --reason")

    def mutate(entry):
        previous = entry.get("state")
        if args.reason == "stale-cleanup":
            # Stale cleanup marks the line stale; it never closes it and never
            # releases ownership. Only an explicit release-ownership (with
            # evidence) or a merged integration + U6 close unblocks waiters.
            if previous == "closed":
                return
            entry["state"] = "stale"
            entry.setdefault("stale_at", now_iso())
            entry["stale_from_state"] = previous
            entry["last_event"] = "stale-marked"
            return
        if (entry.get("worktree_path") and previous == "completed"
                and not entry.get("integration_result") and args.reason != "abandoned"):
            raise EngineError(
                EXIT_USAGE,
                "U6 requires an integration_result before closing a write line "
                "(or --reason abandoned)",
            )
        entry["state"] = "closed"
        entry["closed_at"] = now_iso()
        entry["last_event"] = args.reason
        entry.pop("waiting_reason", None)
        entry.pop("holder_line_id", None)
        entry["lease"] = None
        worktree = entry.get("worktree_path")
        merged = ((entry.get("integration_result") or {}).get("status") == "merged")
        if args.worktree_retained is not None:
            entry["worktree_retained"] = _parse_bool(args.worktree_retained)
        elif worktree:
            entry["worktree_retained"] = bool(Path(worktree).exists()) and not merged
        entry.setdefault("run_history", []).append({
            "run_id": entry["run_id"],
            "started_at": entry.get("created_at") or now_iso(),
            "ended_at": now_iso(),
            "outcome": args.reason,
        })

    entry = ctx.mutate(line_id, mutate)
    if entry.get("state") == "closed":
        _release_resources_for_line(ctx.reg, line_id, reason=args.reason)
    return emit(entry)


def _release_resources_for_line(reg: Path, line_id: str, reason: str) -> None:
    lease = lease_path(reg, line_id)
    if lease.exists():
        record = read_json_optional(lease)
        append_jsonl(lease_history_path(reg, line_id), {
            "event": "released", "reason": reason, "at": now_iso(), "holder": record,
        })
        with contextlib.suppress(OSError):
            lease.unlink()
    reservations = reg / "reservations"
    if reservations.exists():
        for path in sorted(reservations.glob(f"{line_id}.*.json")):
            if ".reservation-history" in path.name:
                continue
            stage = path.name[len(line_id) + 1:-len(".json")]
            try:
                append_jsonl(
                    reservation_history_path(reg, line_id, stage),
                    {"event": "released", "reason": reason, "at": now_iso()},
                )
            except RegistryIOError:
                pass
            with contextlib.suppress(OSError):
                path.unlink()


def action_list(ctx: Context) -> int:
    args = ctx.args
    ensure_registry_dir(ctx.reg)
    summaries = []
    for path in sorted(ctx.reg.glob("*.json")):
        entry = read_json(path)
        if args.active and entry.get("state") not in ACTIVE_STATES:
            continue
        summaries.append({
            "line_id": entry.get("line_id"),
            "run_id": entry.get("run_id"),
            "project_dir": entry.get("project_dir"),
            "branch": entry.get("branch"),
            "stage": entry.get("stage"),
            "state": entry.get("state"),
            "updated_at": entry.get("updated_at"),
        })
    return emit(summaries)


# ---------------------------------------------------------------- envelope / ingress


LINE_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_-])([a-z0-9][A-Za-z0-9-]{7,63})(?![A-Za-z0-9_-])")
GENERATED_LINE_SHAPE = re.compile(r"^[a-z0-9][A-Za-z0-9-]*-[0-9]{8}T[0-9]{6}Z-[0-9a-f]{4}$")


def classify_envelope(
    carrier_line: str | None,
    carrier_run: str | None,
    target_line: str | None,
    target_run: str | None,
) -> str:
    if not target_line and not target_run:
        return "legacy"
    if not carrier_line or not carrier_run:
        return "unattributed"
    if carrier_line != target_line:
        return "foreign"
    if carrier_run != target_run:
        return "stale-run"
    return "own"


def decide_ingress(active_count: int, match_count: int, identified: bool, clarified: bool) -> str:
    if active_count == 0:
        return "no-active"
    if match_count == 1:
        return "route"
    if identified and match_count == 0 and active_count == 1:
        return "no-match"
    if active_count == 1:
        return "route"
    return "ambiguous-stop" if clarified else "clarify"


def _active_entries(ctx: Context) -> list[dict]:
    ensure_registry_dir(ctx.reg)
    entries = []
    for path in sorted(ctx.reg.glob("*.json")):
        entry = read_json(path)
        if entry.get("state") in ACTIVE_STATES:
            entries.append(entry)
    return sorted(entries, key=lambda e: e["line_id"])


def _contains_path(message: str, value: str | None) -> bool:
    if not value:
        return False
    candidates = {value, str(Path(value))}
    for candidate in candidates:
        if not candidate:
            continue
        idx = message.find(candidate)
        while idx != -1:
            end = idx + len(candidate)
            if end >= len(message) or not (message[end].isalnum() or message[end] == "_"):
                return True
            idx = message.find(candidate, idx + 1)
    return False


def _contains_branch(message: str, branch: str | None) -> bool:
    if not branch:
        return False
    return re.search(rf"(?<![A-Za-z0-9_/-]){re.escape(branch)}(?![A-Za-z0-9_/-])", message) is not None


def _candidate(entry: dict) -> dict:
    return {
        "line_id": entry.get("line_id"),
        "project_dir": entry.get("project_dir"),
        "branch": entry.get("branch") or "-",
        "stage": entry.get("stage") or "-",
        "state": entry.get("state"),
    }


def _clarification_question(candidates: list[dict]) -> str:
    parts = []
    for index, candidate in enumerate(candidates, 1):
        parts.append(
            f"{index}) line_id={candidate['line_id']} project={candidate['project_dir']} "
            f"branch={candidate['branch']} stage={candidate['stage']} state={candidate['state']}"
        )
    return "请确认这条消息属于哪条线路：" + "；".join(parts) + "？"


def action_resolve_message(ctx: Context) -> int:
    args = ctx.args
    message = args.message or ""
    require(bool(message.strip()), "resolve-message requires --message")
    active = _active_entries(ctx)
    active_ids = {entry["line_id"] for entry in active}
    tokens = LINE_TOKEN_RE.findall(message)
    token_hits = {token for token in tokens if token in active_ids}
    shape_tokens = [token for token in tokens if GENERATED_LINE_SHAPE.match(token)]
    matched = set(token_hits)
    if not shape_tokens:
        for entry in active:
            if _contains_path(message, entry.get("project_dir")) or _contains_path(
                message, entry.get("repo_root")
            ) or _contains_branch(message, entry.get("branch")):
                matched.add(entry["line_id"])
    identified = bool(shape_tokens) or bool(matched)
    decision = decide_ingress(len(active), len(matched), identified, args.clarified)
    candidates = [_candidate(entry) for entry in active]
    payload = {
        "decision": decision,
        "message": message,
        "active_count": len(active),
        "candidates": candidates,
    }
    if decision == "route":
        if matched:
            payload["target_line_id"] = sorted(matched)[0]
        else:
            require(len(active) == 1, "route without a unique match")
            payload["target_line_id"] = active[0]["line_id"]
    elif decision == "clarify":
        payload["question"] = _clarification_question(candidates)
    elif decision == "ambiguous-stop":
        payload["candidates"] = candidates
    elif decision == "no-match":
        payload["requested"] = sorted(shape_tokens)
    return emit(payload)


# ---------------------------------------------------------------- identity


def _identity_process(pid, token) -> dict:
    if pid is None:
        return {"pid": None, "alive": False, "start_token_match": None}
    pid = int(pid)
    alive = process_alive(pid)
    actual = process_start_token(pid) if alive else None
    match = None
    if token is not None and actual is not None:
        match = str(actual) == str(token)
    return {"pid": pid, "alive": alive, "start_token_match": match}


def _status_summary(path_value: str | None) -> dict:
    summary = {"path": path_value, "exists": False, "exit": None, "sentinel": None}
    if not path_value:
        return summary
    path = Path(path_value)
    if not path.exists():
        return summary
    summary["exists"] = True
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^exit=([0-9]+)", text, re.MULTILINE)
    if match:
        summary["exit"] = int(match.group(1))
    match = re.search(r"sentinel=([01])", text)
    if match:
        summary["sentinel"] = int(match.group(1))
    return summary


def _last_line(path_value: str | None) -> str | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else None


def _cursor(path_value: str | None) -> str | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8", errors="replace").strip() or None


def _heartbeat_age(path_value: str | None):
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    return max(0, now_epoch() - int(path.stat().st_mtime))


def _pid_path(entry: dict) -> str | None:
    status = entry.get("status_path")
    if not status:
        return None
    path = Path(status)
    if path.name.startswith("status-"):
        return str(path.with_name("pid-" + path.name[len("status-"):]))
    return None


def _local_identity(entry: dict) -> dict:
    runner = _identity_process(entry.get("runner_pid"), entry.get("runner_start_token"))
    cli = _identity_process(entry.get("cli_pid"), entry.get("cli_start_token"))
    cwd_check = "unsupported"
    if runner.get("pid") and runner.get("alive"):
        actual_cwd = process_cwd(runner["pid"])
        if actual_cwd is not None:
            expected = [
                Path(value).resolve()
                for value in (entry.get("worktree_path"), entry.get("project_dir"), entry.get("repo_root"))
                if value
            ]
            cwd_check = "ok" if any(
                actual_cwd == expected_path or expected_path in actual_cwd.parents
                for expected_path in expected
            ) else "mismatch"
    branch_check = "skipped"
    if entry.get("branch"):
        repo = entry.get("worktree_path") or entry.get("repo_root")
        actual_branch = branch_of(Path(repo)) if repo else None
        if actual_branch is not None:
            branch_check = "ok" if actual_branch == entry["branch"] else "mismatch"
    identity = classify_identity(runner, cli, cwd_check, branch_check)
    status = _status_summary(entry.get("status_path"))
    return {
        "identity": identity,
        "runner": runner,
        "cli": cli,
        "cwd_check": cwd_check,
        "branch_check": branch_check,
        "status": status,
    }


def classify_identity(runner: dict, cli: dict, cwd_check: str, branch_check: str) -> str:
    if not runner.get("pid") and not cli.get("pid"):
        return "unknown"
    if runner.get("pid") and not runner.get("alive"):
        return "dead"
    if runner.get("start_token_match") is False:
        return "mismatch"
    if cli.get("pid") and not cli.get("alive"):
        return "mismatch"
    if cli.get("start_token_match") is False:
        return "mismatch"
    if cwd_check == "mismatch" or branch_check == "mismatch":
        return "mismatch"
    return "ok"


def classify_remote_probe(probe: dict) -> str:
    if probe.get("unreachable") or probe.get("ssh_error"):
        return "remote-unreachable"
    return probe.get("identity") or "unknown"


def _branch_hint(identity: str, status: dict, reservation: dict | None) -> str:
    if identity == "remote-unreachable":
        return "stalled"
    if status.get("exists") and status.get("exit") == 0 and status.get("sentinel") == 1:
        return "done"
    if identity == "dead":
        return "dead"
    if identity in {"ok", "unknown"} and reservation:
        return "running"
    if identity == "ok":
        return "running"
    return "stalled"


def action_verify_identity(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    probe = None
    if args.probe_json:
        raw = args.probe_json
        probe_path = Path(raw)
        if probe_path.exists():
            probe = read_json(probe_path)
        else:
            try:
                probe = json.loads(raw)
            except json.JSONDecodeError:
                raise EngineError(EXIT_NO_IDENTITY, f"probe JSON unavailable: {raw}")
    if isinstance(probe, dict):
        if probe.get("unreachable") or probe.get("ssh_error") or probe.get("identity") == "remote-unreachable":
            return emit({
                "line_id": line_id,
                "identity": "remote-unreachable",
                "reason": probe.get("reason") or "ssh-unreachable",
                "branch_hint": "stalled",
            })
        if "identity" in probe:
            payload = dict(probe)
            payload.setdefault("line_id", line_id)
            payload.setdefault("branch_hint", "stalled" if classify_remote_probe(probe) == "remote-unreachable" else None)
            return emit(payload)
    entry = ctx.load(line_id)
    local = _local_identity(entry)
    reservation = read_json_optional(reservation_path(ctx.reg, line_id, entry.get("stage") or ""))
    lease = read_json_optional(lease_path(ctx.reg, line_id))
    payload = {
        "line_id": line_id,
        "run_id": entry.get("run_id"),
        "identity": local["identity"],
        "runner": local["runner"],
        "cli": local["cli"],
        "cwd_check": local["cwd_check"],
        "branch_check": local["branch_check"],
        "reservation": reservation,
        "lease": lease,
        "evidence": {
            "status": local["status"],
            "log": {
                "path": entry.get("log_path"),
                "exists": bool(entry.get("log_path") and Path(entry["log_path"]).exists()),
                "last_line": _last_line(entry.get("log_path")),
            },
            "heartbeat": {
                "path": entry.get("heartbeat_path"),
                "exists": bool(entry.get("heartbeat_path") and Path(entry["heartbeat_path"]).exists()),
                "age_seconds": _heartbeat_age(entry.get("heartbeat_path")),
            },
            "pid": {
                "path": _pid_path(entry),
                "exists": bool(_pid_path(entry) and Path(_pid_path(entry)).exists()),
            },
        },
        "branch_hint": _branch_hint(local["identity"], local["status"], reservation),
    }
    return emit(payload)


# ---------------------------------------------------------------- ownership / queue / resources


def topological_layers(nodes: list[str], edges: dict[str, set[str]]) -> list[list[str]]:
    remaining = set(nodes)
    layers: list[list[str]] = []
    while remaining:
        layer = sorted(node for node in remaining if not (edges.get(node, set()) & remaining))
        if not layer:
            raise EngineError(EXIT_IO, "dependency cycle detected: " + ", ".join(sorted(remaining)))
        layers.append(layer)
        remaining -= set(layer)
    return layers


def conflict_name(existing: set[str], basename: str, line_id: str) -> tuple[str, bool]:
    if basename not in existing:
        return basename, False
    index = 1
    while True:
        candidate = f"{basename}.{line_id}.{index}"
        if candidate not in existing:
            return candidate, True
        index += 1


def allocate_port_block(used: list[tuple[int, int]], start: int, size: int) -> tuple[int, int]:
    candidate = start
    for range_start, range_end in sorted(used):
        if candidate + size - 1 < range_start:
            break
        if candidate > range_end:
            continue
        candidate = range_end + 1
    return candidate, candidate + size - 1


def _manifest_for_entry(reg: Path, entry: dict) -> dict | None:
    candidates = [manifest_path(reg, entry["line_id"])]
    if entry.get("ownership_manifest_path"):
        candidates.append(Path(entry["ownership_manifest_path"]))
    for path in candidates:
        data = read_json_optional(path)
        if data is not None:
            return data
    return None


def _manifest_conflicts(self_manifest: dict, other_manifest: dict, other_line: str) -> list[dict]:
    conflicts = []
    self_owned = self_manifest.get("owned_paths", [])
    self_readonly = self_manifest.get("read_only_paths", []) + self_manifest.get("forbidden_paths", [])
    other_owned = other_manifest.get("owned_paths", [])
    other_readonly = other_manifest.get("read_only_paths", []) + other_manifest.get("forbidden_paths", [])

    def record(path, other_path, kind):
        conflicts.append({
            "line_id": other_line, "path": path, "other_path": other_path, "kind": kind,
        })

    for a in self_owned:
        for b in other_owned:
            if paths_overlap(a, b):
                record(a, b, "write-write")
        for b in other_readonly:
            if paths_overlap(a, b):
                record(a, b, "write-readonly")
    for a in self_readonly:
        for b in other_owned:
            if paths_overlap(a, b):
                record(a, b, "readonly-write")
    return conflicts


def _ownership_release_record(reg: Path, line_id: str) -> dict | None:
    """Last explicit release (with evidence) from the ownership history."""
    history = reg / f"{line_id}.ownership-history.jsonl"
    if not history.exists():
        return None
    try:
        lines = history.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("event") == "released" and record.get("evidence_ref"):
            return record
    return None


def _entry_manifest_view(ctx: Context, entry: dict) -> dict | None:
    """Manifest file, or the entry's owned_paths projection when the file is absent.

    Falling back to the projection closes the "delete the manifest to stop
    blocking" hole: ownership declared at registration still blocks.
    """
    manifest = _manifest_for_entry(ctx.reg, entry)
    if manifest is not None:
        return manifest
    owned = entry.get("owned_paths")
    if owned:
        root = Path(entry.get("repo_root") or ".")
        return {
            "line_id": entry["line_id"],
            "owned_paths": [normalize_path(p, root) for p in owned],
            "read_only_paths": [],
            "forbidden_paths": [],
        }
    return None


def _entry_released(ctx: Context, entry: dict) -> bool:
    """Released = the stored manifest is released, or (no manifest file) a
    release record exists. The owned_paths projection must not mask a release."""
    manifest_file = _manifest_for_entry(ctx.reg, entry)
    if manifest_file is not None:
        return bool(manifest_file.get("released_at"))
    return _ownership_release_record(ctx.reg, entry["line_id"]) is not None


def _closure_is_evidenced(entry: dict) -> bool:
    """A closed line releases overlap only after a merged integration."""
    return (entry.get("integration_result") or {}).get("status") == "merged"


def _ownership_conflicts(ctx: Context, self_entry: dict, self_manifest: dict) -> tuple[list[dict], list[dict]]:
    conflicts: list[dict] = []
    competitors: list[dict] = []
    for path in sorted(ctx.reg.glob("*.json")):
        entry = read_json(path)
        if entry.get("line_id") == self_entry.get("line_id"):
            continue
        manifest_file = _manifest_for_entry(ctx.reg, entry)
        other_manifest = _entry_manifest_view(ctx, entry)
        if other_manifest is None:
            continue
        if manifest_file is not None:
            # A re-acquisition (ownership-check) clears released_at, so the
            # stored manifest is the current claim; old release history must
            # not unblock a holder that is active again. An *active* line with
            # a released manifest is inconsistent and keeps blocking (fail-safe).
            if manifest_file.get("released_at") and entry.get("state") != "active":
                continue
        elif _ownership_release_record(ctx.reg, entry["line_id"]):
            continue
        if entry.get("state") == "closed" and _closure_is_evidenced(entry):
            continue
        # stale/orphaned and any closed line without explicit release or merged
        # evidence keep blocking: stale-cleanup is not an implicit release (FR-021).
        found = _manifest_conflicts(self_manifest, other_manifest, entry["line_id"])
        if found:
            conflicts.extend(found)
            competitors.append(entry)
    return conflicts, competitors


def _claim_key(ctx: Context, entry: dict) -> tuple[int, str]:
    """FIFO key of the current claim: a re-acquired manifest restarts its slot.

    Nanosecond resolution (claimed_ns) keeps ordering deterministic when
    several claims happen inside one ISO-second.
    """
    manifest = _manifest_for_entry(ctx.reg, entry) or {}
    claimed_ns = manifest.get("claimed_ns")
    if not isinstance(claimed_ns, int):
        claimed_ns = entry.get("claimed_ns")
    if isinstance(claimed_ns, int):
        return (claimed_ns, entry["line_id"])
    epoch = _iso_epoch(entry.get("created_at")) or 0
    return (int(epoch * 1_000_000_000), entry["line_id"])


def _raise_if_ownership_conflict(ctx: Context, entry: dict, manifest: dict) -> None:
    """Every path that makes a line active passes this gate.

    The current claim holder may (re)enter active even while later claimants
    wait; a later claimant is refused. This mirrors ownership-check's FIFO.
    """
    conflicts, competitors = _ownership_conflicts(ctx, entry, manifest)
    if not conflicts:
        return
    # An already-active owner is never preempted by a later ownership claim,
    # even if the claimant has an older creation/claim timestamp.
    active_competitors = [item for item in competitors if item.get("state") == "active"]
    if active_competitors:
        raise EngineError(
            EXIT_HELD,
            f"ownership overlap with active line {active_competitors[0]['line_id']}",
            holder_line_id=active_competitors[0]["line_id"],
            conflicts=conflicts[:10],
        )
    earliest = min(competitors + [entry], key=lambda item: _claim_key(ctx, item))
    if earliest["line_id"] == entry["line_id"]:
        return
    raise EngineError(
        EXIT_HELD,
        f"ownership overlap with line {earliest['line_id']}",
        holder_line_id=earliest["line_id"],
        conflicts=conflicts[:10],
    )


def _ensure_unique_worktree(reg: Path, worktree: str, line_id: str) -> None:
    target = str(Path(worktree).expanduser().resolve())
    for path in reg.glob("*.json"):
        entry = read_json(path)
        if entry.get("line_id") == line_id:
            continue
        if entry.get("state") == "closed" and not entry.get("worktree_retained"):
            continue
        existing = entry.get("worktree_path")
        if existing and str(Path(existing).resolve()) == target:
            raise EngineError(
                EXIT_USAGE,
                f"worktree target already owned by line {entry.get('line_id')}: {target}",
                path=target,
            )


def action_ownership_check(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    require(bool(args.manifest), "ownership-check requires --manifest")
    entry = ctx.load(line_id)
    require(entry.get("state") not in {"closed", "stale", "orphaned"},
            f"cannot re-acquire ownership from state {entry.get('state')!r}; dispose or register a new line")
    manifest = load_manifest(Path(args.manifest), line_id, Path(entry["repo_root"]))
    # ownership-check is a claim: it re-acquires a previously released
    # manifest, so the stale released_at/evidence must not keep it unlocked.
    manifest["claimed_at"] = now_iso()
    manifest["claimed_ns"] = time.time_ns()
    for key in ("released_at", "release_reason", "evidence_ref"):
        manifest.pop(key, None)
    ensure_registry_dir(ctx.reg)
    atomic_write_json(manifest_path(ctx.reg, line_id), manifest)
    append_jsonl(ctx.reg / f"{line_id}.ownership-history.jsonl", {
        "event": "acquired", "at": manifest["claimed_at"],
    })
    conflicts, competitors = _ownership_conflicts(ctx, entry, manifest)
    decision = "proceed"
    holder = None
    if conflicts:
        earliest = min(
            competitors + [entry],
            key=lambda item: _claim_key(ctx, item),
        )
        if earliest["line_id"] != line_id:
            decision = "waiting"
            holder = earliest["line_id"]

    def mutate(data):
        data["owned_paths"] = list(manifest["owned_paths"])
        data["ownership_manifest_path"] = str(Path(args.manifest).resolve())
        data["last_event"] = "ownership-checked"
        if decision == "waiting":
            data["state"] = "waiting"
            data["waiting_reason"] = "ownership-overlap"
            data["holder_line_id"] = holder
            data["queued_at"] = now_iso()
            data["last_event"] = "waiting-ownership-overlap"
        elif data.get("state") == "waiting" and data.get("waiting_reason") == "ownership-overlap":
            # No implicit promotion: a waiting line only becomes active through
            # the explicit promote-waiting action after the gate below passes.
            data["last_event"] = "ownership-clear-awaiting-promotion"

    updated = ctx.mutate(line_id, mutate)
    payload = {
        "line_id": line_id,
        "overlaps": conflicts,
        "decision": decision,
        "state": updated["state"],
    }
    if updated["state"] == "waiting":
        payload["promotion_required"] = True
    if holder:
        payload["holder_line_id"] = holder
    return emit(payload)


def action_release_ownership(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    require(bool(args.reason), "release-ownership requires --reason")
    require(bool(args.evidence_ref), "release-ownership requires --evidence-ref")
    entry = ctx.load(line_id)
    manifest = _manifest_for_entry(ctx.reg, entry)
    if manifest is not None:
        manifest["released_at"] = now_iso()
        manifest["release_reason"] = args.reason
        manifest["evidence_ref"] = args.evidence_ref
        atomic_write_json(manifest_path(ctx.reg, line_id), manifest)
    append_jsonl(ctx.reg / f"{line_id}.ownership-history.jsonl", {
        "event": "released", "reason": args.reason,
        "evidence_ref": args.evidence_ref, "at": now_iso(),
    })

    def mutate(data):
        data["last_event"] = "ownership-released"
        data["ownership_released_at"] = now_iso()
        if data.get("state") in {"stale", "orphaned"}:
            # Explicit disposition closes a stale/orphaned line; the manifest
            # release above is what unblocks overlapping waiters.
            data["state"] = "closed"
            data["closed_at"] = now_iso()
            worktree = data.get("worktree_path")
            if worktree:
                merged = (data.get("integration_result") or {}).get("status") == "merged"
                data["worktree_retained"] = bool(Path(worktree).exists()) and not merged
        elif data.get("state") in {"active", "waiting"}:
            # A line that gave up its paths must stop being a writer; explicit
            # U5/U6 disposition follows. This prevents an active line from
            # coexisting with the next owner of the same paths.
            data["state"] = "stalled"
            for key in ("waiting_reason", "holder_line_id", "queued_at"):
                data.pop(key, None)

    updated = ctx.mutate(line_id, mutate)
    if updated.get("state") == "closed":
        _release_resources_for_line(ctx.reg, line_id, reason=args.reason)
    return emit({
        "line_id": line_id, "released": True,
        "reason": args.reason, "state": updated["state"],
    })


def action_promote_waiting(ctx: Context) -> int:
    line_id = validate_line_id(ctx.args.line_id or "")
    entry = ctx.load(line_id)
    require(entry.get("state") == "waiting", f"line {line_id} is not waiting (state={entry.get('state')})")
    manifest = _entry_manifest_view(ctx, entry)
    if _entry_released(ctx, entry):
        return emit({
            "line_id": line_id, "promoted": False, "reason": "ownership-released",
        }, code=EXIT_HELD)
    if manifest is None and entry.get("waiting_reason") == "ownership-overlap":
        return emit({
            "line_id": line_id, "promoted": False, "reason": "manifest-missing",
        }, code=EXIT_HELD)
    if manifest is not None:
        conflicts, competitors = _ownership_conflicts(ctx, entry, manifest)
        if conflicts:
            earliest = min(competitors + [entry], key=lambda item: _claim_key(ctx, item))
            if earliest["line_id"] != line_id:
                return emit({
                    "line_id": line_id, "promoted": False, "reason": "ownership-overlap",
                    "holder_line_id": earliest["line_id"],
                }, code=EXIT_HELD)
    cap = int(os.environ.get("SPECIFY_LINE_CONCURRENCY_CAP", DEFAULT_CONCURRENCY_CAP))
    active = [
        read_json(path) for path in ctx.reg.glob("*.json")
        if read_json(path).get("line_id") != line_id
        and read_json(path).get("state") == "active"
        and read_json(path).get("stage")
    ]
    if len(active) >= cap:
        return emit({"line_id": line_id, "promoted": False, "reason": "concurrency-cap"}, code=EXIT_HELD)

    def mutate(data):
        data["state"] = "active"
        for key in ("waiting_reason", "holder_line_id", "queued_at"):
            data.pop(key, None)
        data["last_event"] = "promoted"

    return emit(ctx.mutate(line_id, mutate))


def action_integration_enqueue(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    entry = ctx.load(line_id)
    require(entry.get("state") == "completed", "integration-enqueue requires state=completed")

    def mutate(data):
        data["merge_ready"] = True
        data["ready_for_merge_at"] = args.at or now_iso()
        data["last_event"] = "integration-enqueued"

    return emit(ctx.mutate(line_id, mutate))


def action_integration_plan(ctx: Context) -> int:
    ensure_registry_dir(ctx.reg)
    entries = {}
    for path in sorted(ctx.reg.glob("*.json")):
        entry = read_json(path)
        entries[entry["line_id"]] = entry
    queued = {
        line_id: entry for line_id, entry in entries.items()
        if entry.get("state") == "completed" and entry.get("merge_ready")
    }
    dependencies: dict[str, set[str]] = {}
    blocked_by: dict[str, set[str]] = {}
    for line_id, entry in queued.items():
        manifest = _manifest_for_entry(ctx.reg, entry) or {}
        deps = manifest.get("integration_depends_on", []) or []
        dependencies[line_id] = set()
        blocked_by[line_id] = set()
        for dep in deps:
            require(dep in entries, f"integration_depends_on references unknown line: {dep}")
            dep_entry = entries[dep]
            merged = (dep_entry.get("integration_result") or {}).get("status") == "merged"
            if merged:
                continue
            if dep in queued:
                dependencies[line_id].add(dep)
            else:
                blocked_by[line_id].add(dep)
    changed = True
    while changed:
        changed = False
        for line_id in list(queued):
            if blocked_by[line_id]:
                continue
            for dep in dependencies[line_id]:
                if dep in blocked_by and blocked_by[dep]:
                    blocked_by[line_id].add(dep)
                    changed = True
                    break
    runnable = [line_id for line_id in queued if not blocked_by[line_id]]
    layers = topological_layers(
        runnable, {line_id: dependencies[line_id] & set(runnable) for line_id in runnable}
    )
    output = []
    order = 0
    for layer_index, layer in enumerate(layers):
        for line_id in sorted(
            layer, key=lambda item: (queued[item].get("ready_for_merge_at") or "", item)
        ):
            order += 1
            output.append({
                "order": order,
                "line_id": line_id,
                "ready_for_merge_at": queued[line_id].get("ready_for_merge_at"),
                "layer": layer_index,
                "depends_on": sorted(dependencies[line_id]),
                "blocked_by": [],
            })
    for line_id in sorted(line_id for line_id in queued if blocked_by[line_id]):
        output.append({
            "order": None,
            "line_id": line_id,
            "ready_for_merge_at": queued[line_id].get("ready_for_merge_at"),
            "layer": None,
            "depends_on": sorted(dependencies[line_id]),
            "blocked_by": sorted(blocked_by[line_id]),
        })
    return emit(output)


def action_integration_record(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    require(args.result in INTEGRATION_RESULTS,
            f"--result must be one of {sorted(INTEGRATION_RESULTS)}")
    if args.result == "merged":
        require(bool(args.commit), "merged result requires --commit")
    else:
        require(bool(args.reason), "failed result requires --reason")
    entry = ctx.load(line_id)
    require(entry.get("state") == "completed", "integration-record requires state=completed")
    if args.result == "merged":
        repo = Path(entry["repo_root"])
        probe = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--git-dir"],
            capture_output=True, text=True, timeout=5,
        )
        ownership_line = bool(
            entry.get("write_line") or entry.get("owned_paths") or entry.get("worktree_path")
        )
        if probe.returncode != 0 and ownership_line:
            require(False,
                    f"merged integration for a write line requires a git repo_root: {repo}")
        if probe.returncode == 0:
            exists = subprocess.run(
                ["git", "-C", str(repo), "cat-file", "-e", f"{args.commit}^{{commit}}"],
                capture_output=True, text=True, timeout=5,
            )
            require(exists.returncode == 0,
                    f"merged commit does not exist in repo: {args.commit}")
            reachable = subprocess.run(
                ["git", "-C", str(repo), "merge-base", "--is-ancestor",
                 args.commit, "HEAD"],
                capture_output=True, text=True, timeout=5,
            )
            require(reachable.returncode == 0,
                    f"merged commit is not reachable from HEAD: {args.commit}")
            if ownership_line:
                worktree = entry.get("worktree_path")
                require(bool(worktree) and Path(worktree).exists(),
                        "merged write line requires its retained worktree for containment verification")
                require(Path(worktree).resolve() != repo.resolve(),
                        "merged write line worktree must not be the repo root itself")
                if entry.get("branch"):
                    actual_branch = subprocess.run(
                        ["git", "-C", worktree, "rev-parse", "--abbrev-ref", "HEAD"],
                        capture_output=True, text=True, timeout=5,
                    )
                    require(actual_branch.returncode == 0
                            and actual_branch.stdout.strip() == entry["branch"],
                            "merged write line worktree branch does not match the registered branch")
                line_head = subprocess.run(
                    ["git", "-C", worktree, "rev-parse", "HEAD"],
                    capture_output=True, text=True, timeout=5,
                )
                require(line_head.returncode == 0 and bool(line_head.stdout.strip()),
                        "cannot verify the line worktree HEAD")
                contains = subprocess.run(
                    ["git", "-C", str(repo), "merge-base", "--is-ancestor",
                     line_head.stdout.strip(), args.commit],
                    capture_output=True, text=True, timeout=5,
                )
                require(contains.returncode == 0,
                        "merged commit does not contain the line worktree HEAD")

    def mutate(data):
        data["integration_result"] = {
            "status": args.result,
            "at": now_iso(),
            "commit": args.commit,
            "reason": args.reason,
        }
        data["merge_ready"] = False
        data.pop("ready_for_merge_at", None)
        data["last_event"] = f"integration-{args.result}"

    return emit(ctx.mutate(line_id, mutate))


def action_allocate_resources(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    entry = ctx.load(line_id)
    require(entry.get("state") == "active",
            f"allocate-resources requires state=active (state={entry.get('state')})")
    cap = int(args.cap or os.environ.get("SPECIFY_LINE_CONCURRENCY_CAP", DEFAULT_CONCURRENCY_CAP))
    start = int(args.port_range_start or DEFAULT_PORT_START)
    block = int(args.block_size or DEFAULT_BLOCK_SIZE)
    require(cap > 0, "--cap must be positive")
    require(block > 0, "--block-size must be positive")
    others = []
    for path in sorted(ctx.reg.glob("*.json")):
        other = read_json(path)
        if other.get("line_id") == line_id:
            continue
        if other.get("state") == "active" and other.get("stage"):
            others.append(other)
    if len(others) >= cap:
        def mark_waiting(data):
            data["state"] = "waiting"
            data["waiting_reason"] = "concurrency-cap"
            data["queued_at"] = now_iso()
            data["last_event"] = "waiting-concurrency-cap"

        updated = ctx.mutate(line_id, mark_waiting)
        return emit({
            "line_id": line_id, "waiting": True, "reason": "concurrency-cap",
            "active_count": len(others), "cap": cap, "state": updated["state"],
        }, code=EXIT_HELD)
    used = []
    for other in others:
        ports = (other.get("resources") or {}).get("ports")
        if isinstance(ports, list) and len(ports) == 2:
            used.append((int(ports[0]), int(ports[1])))
    port_start, port_end = allocate_port_block(used, start, block)
    repo = Path(entry["repo_root"])
    runtime_root = repo / ".specify" / ".tmp" / "sdd-loop"
    cache_dir = runtime_root / "cache" / line_id
    tmp_dir = runtime_root / "tmp" / line_id
    resources = {
        "ports": [port_start, port_end],
        "cache_dir": str(cache_dir),
        "tmp_dir": str(tmp_dir),
        "active_count": len(others) + 1,
        "cap": cap,
    }

    def mutate(data):
        data["resources"] = resources
        data["last_event"] = "resources-allocated"

    ctx.mutate(line_id, mutate)
    return emit({"line_id": line_id, "waiting": False, "resources": resources})


def _iter_runtime_files(worktree: Path):
    for relative in RUNTIME_RECORD_DIRS:
        root = worktree / relative
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                yield path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def action_archive_runtime(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    require(bool(args.worktree), "archive-runtime requires --worktree")
    require(bool(args.dest), "archive-runtime requires --dest")
    worktree = Path(args.worktree).expanduser().resolve()
    dest = Path(args.dest).expanduser().resolve()
    require(worktree.exists(), f"worktree not found: {worktree}")
    require(dest != worktree and worktree not in dest.parents,
            "archive destination must be outside the worktree")
    dest.mkdir(parents=True, exist_ok=True)
    existing = {path.name for path in dest.iterdir() if path.is_file()}
    records = []
    for source in _iter_runtime_files(worktree):
        archived_name, conflict = conflict_name(existing, source.name, line_id)
        existing.add(archived_name)
        target = dest / archived_name
        shutil.copy2(source, target)
        source_hash = _sha256(source)
        target_hash = _sha256(target)
        if source_hash != target_hash:
            raise RegistryIOError(target, "archived file hash mismatch")
        records.append({
            "original": str(source.relative_to(worktree)),
            "archived_name": archived_name,
            "sha256": source_hash,
            "conflict": conflict,
        })
    manifest = {
        "line_id": line_id,
        "run_id": args.run_id,
        "source_worktree": str(worktree),
        "dest_dir": str(dest),
        "files": records,
        "created_at": now_iso(),
    }
    atomic_write_json(dest / f"runtime-archive-{line_id}.json", manifest)
    return emit(manifest)


# ---------------------------------------------------------------- lease / reservation / reattach


def _iso_epoch(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        ).timestamp()
    except ValueError:
        return None


def lease_max_interval(ttl_seconds: int) -> int:
    return max(1, int(ttl_seconds) // 3)


def classify_lease_status(
    heartbeat_age: int,
    ttl_seconds: int,
    pid_alive: bool | None,
    token_match: bool | None,
    local: bool,
) -> str:
    if heartbeat_age < ttl_seconds:
        if not local:
            return "live"
        if pid_alive and token_match is not False:
            return "live"
        return "expired"
    if local and pid_alive and token_match:
        return "suspected-alive"
    return "expired"


def reservation_attach_decision(
    reservation: dict, run_id: str, pid_alive: bool, token_match: bool | None
) -> str:
    if reservation.get("run_id") == run_id and pid_alive and token_match is not False:
        return "attach"
    return "refuse"


def _lease_status(lease: dict) -> dict:
    heartbeat = _iso_epoch(lease.get("heartbeat_at"))
    ttl = int(lease.get("ttl_seconds") or DEFAULT_TTL)
    age = int(now_epoch() - heartbeat) if heartbeat is not None else ttl + 1
    local = lease.get("host") == socket.gethostname()
    pid = lease.get("holder_pid")
    token = lease.get("holder_start_token")
    pid_alive = process_alive(int(pid)) if local and pid else None
    token_match = None
    if local and pid and pid_alive and token:
        actual = process_start_token(int(pid))
        token_match = (actual == token) if actual is not None else None
    state = classify_lease_status(age, ttl, pid_alive, token_match, local)
    return {
        "holder_state": state,
        "heartbeat_age_seconds": age,
        "pid_alive": pid_alive,
        "token_match": token_match,
        "local": local,
    }


def _project_lease(ctx: Context, line_id: str, lease: dict | None, event: str) -> None:
    def mutate(data):
        data["lease"] = lease
        data["last_event"] = event

    try:
        ctx.mutate(line_id, mutate)
    except EngineError:
        raise


def action_lease_acquire(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    require(bool(args.session), "lease-acquire requires --session")
    require(bool(args.pid), "lease-acquire requires --pid")
    require(args.ttl is None or int(args.ttl) > 0, "--ttl must be positive")
    entry = ctx.load(line_id)
    require(entry.get("state") not in {"closed", "stale", "orphaned"},
            f"cannot lease a {entry.get('state')} line")
    ensure_registry_dir(ctx.reg)
    ttl = int(args.ttl or DEFAULT_TTL)
    pid = int(args.pid)
    token = args.start_token or process_start_token(pid)
    require(token is not None, "cannot derive holder start token; pass --start-token")
    host = args.host or socket.gethostname()
    at = now_iso()
    lease = {
        "line_id": line_id,
        "holder_session": args.session,
        "holder_pid": pid,
        "holder_start_token": token,
        "host": host,
        "acquired_at": at,
        "heartbeat_at": at,
        "ttl_seconds": ttl,
    }
    path = lease_path(ctx.reg, line_id)
    payload = json.dumps(lease, sort_keys=True, ensure_ascii=False) + "\n"
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        existing = read_json(path)
        status = _lease_status(existing)
        append_jsonl(lease_history_path(ctx.reg, line_id), {
            "event": "refused", "session": args.session, "at": now_iso(), **status,
        })
        return emit({
            "acquired": False,
            "line_id": line_id,
            "holder": existing,
            **status,
            "requires_break": True,
        }, code=EXIT_HELD)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        _fsync_dir(path.parent)
    except OSError as exc:
        with contextlib.suppress(OSError):
            path.unlink()
        raise RegistryIOError(path, f"cannot create lease: {exc}")
    append_jsonl(lease_history_path(ctx.reg, line_id), {
        "event": "acquired", "session": args.session, "at": at, "ttl_seconds": ttl,
    })
    try:
        _project_lease(ctx, line_id, lease, "lease-acquired")
    except EngineError:
        with contextlib.suppress(OSError):
            path.unlink()
        raise
    return emit(lease)


def action_lease_renew(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    require(bool(args.session), "lease-renew requires --session")
    path = lease_path(ctx.reg, line_id)
    lease = read_json_optional(path)
    if lease is None:
        return emit({"renewed": False, "error": "no active lease"}, code=EXIT_HELD)
    if lease.get("holder_session") != args.session:
        return emit({"renewed": False, "error": "session is not the lease holder"}, code=EXIT_HELD)
    previous = _iso_epoch(lease.get("heartbeat_at"))
    now = now_epoch()
    interval = int(now - previous) if previous is not None else None
    ttl = int(lease.get("ttl_seconds") or DEFAULT_TTL)
    max_interval = lease_max_interval(ttl)
    lease["heartbeat_at"] = now_iso(now)
    atomic_write_json(path, lease)
    cadence_ok = interval is not None and interval <= max_interval
    append_jsonl(lease_history_path(ctx.reg, line_id), {
        "event": "renewed", "session": args.session, "at": lease["heartbeat_at"],
        "interval_seconds": interval, "cadence_ok": cadence_ok,
    })
    if not cadence_ok:
        violation = {
            "event": "lease-cadence-violation", "session": args.session,
            "at": lease["heartbeat_at"], "interval_seconds": interval,
            "max_interval_seconds": max_interval,
        }
        append_jsonl(lease_history_path(ctx.reg, line_id), violation)
        lease["last_cadence_violation"] = violation
        _project_lease(ctx, line_id, lease, "lease-cadence-violation")
    else:
        _project_lease(ctx, line_id, lease, "lease-renewed")
    payload = dict(lease)
    payload.update({
        "renewed": True,
        "interval_seconds": interval,
        "max_interval_seconds": max_interval,
        "cadence_ok": cadence_ok,
    })
    return emit(payload)


def action_lease_release(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    require(bool(args.session), "lease-release requires --session")
    path = lease_path(ctx.reg, line_id)
    lease = read_json_optional(path)
    if lease is None:
        return emit({"released": False, "error": "no active lease"}, code=EXIT_HELD)
    if lease.get("holder_session") != args.session:
        return emit({"released": False, "error": "session is not the lease holder"}, code=EXIT_HELD)
    append_jsonl(lease_history_path(ctx.reg, line_id), {
        "event": "released", "session": args.session, "at": now_iso(),
    })
    with contextlib.suppress(OSError):
        path.unlink()
    _project_lease(ctx, line_id, None, "lease-released")
    return emit({"released": True, "line_id": line_id})


def action_lease_break(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    require(bool(args.reason), "lease-break requires --reason")
    require(bool(args.evidence_ref), "lease-break requires --evidence-ref")
    path = lease_path(ctx.reg, line_id)
    lease = read_json_optional(path)
    if lease is None:
        return emit({"broken": False, "reason": "no active lease"})
    status = _lease_status(lease)
    state = status["holder_state"]
    if state == "live":
        return emit({
            "broken": False, "error": "lease holder is live", **status,
        }, code=EXIT_HELD)
    if state == "suspected-alive" and not args.override:
        return emit({
            "broken": False,
            "error": "suspected-alive requires --override",
            **status,
        }, code=EXIT_HELD)
    append_jsonl(lease_history_path(ctx.reg, line_id), {
        "event": "broken",
        "reason": args.reason,
        "evidence_ref": args.evidence_ref,
        "override": bool(args.override),
        "at": now_iso(),
        "holder": lease,
        **status,
    })
    with contextlib.suppress(OSError):
        path.unlink()
    _project_lease(ctx, line_id, None, "lease-broken")
    payload = {
        "broken": True,
        "line_id": line_id,
        "reason": args.reason,
        "evidence_ref": args.evidence_ref,
        "override": bool(args.override),
        **status,
    }
    return emit(payload)


def action_classify_remote(ctx: Context) -> int:
    args = ctx.args
    require(bool(args.probe_json), "classify-remote requires --probe-json")
    probe_path = Path(args.probe_json)
    if probe_path.exists():
        probe = read_json(probe_path)
    else:
        try:
            probe = json.loads(args.probe_json)
        except json.JSONDecodeError:
            raise EngineError(EXIT_USAGE, f"invalid probe JSON: {args.probe_json}")
    identity = classify_remote_probe(probe)
    return emit({
        "identity": identity,
        "reason": probe.get("reason") or ("ssh-unreachable" if identity == "remote-unreachable" else None),
    })


def action_reserve(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    require(bool(args.stage), "reserve requires --stage")
    require(bool(args.run_id), "reserve requires --run-id")
    require(bool(args.pid), "reserve requires --pid")
    validate_run_id(args.run_id)
    entry = ctx.load(line_id)
    require(entry.get("state") not in {"closed", "stale", "orphaned"},
            f"cannot reserve a stage for a {entry.get('state')} line")
    ensure_registry_dir(ctx.reg)
    pid = int(args.pid)
    token = args.start_token or process_start_token(pid)
    require(token is not None, "cannot derive reservation start token; pass --start-token")
    reservation = {
        "line_id": line_id,
        "stage": args.stage,
        "run_id": args.run_id,
        "pid": pid,
        "start_token": token,
        "host": args.host or socket.gethostname(),
        "started_at": now_iso(),
    }
    path = reservation_path(ctx.reg, line_id, args.stage)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(reservation, sort_keys=True, ensure_ascii=False) + "\n"
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        existing = read_json(path)
        pid_alive = process_alive(int(existing.get("pid") or 0))
        token_match = None
        if pid_alive and existing.get("start_token"):
            token_match = process_start_token(int(existing["pid"])) == existing["start_token"]
        decision = reservation_attach_decision(existing, args.run_id, pid_alive, token_match)
        if decision == "attach":
            return emit({"action": "attach", "reservation": existing})
        return emit({"action": "refuse", "reservation": existing}, code=EXIT_HELD)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        _fsync_dir(path.parent)
    except OSError as exc:
        with contextlib.suppress(OSError):
            path.unlink()
        raise RegistryIOError(path, f"cannot create reservation: {exc}")
    return emit({"action": "created", "reservation": reservation})


def action_reservation_status(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    require(bool(args.stage), "reservation-status requires --stage")
    path = reservation_path(ctx.reg, line_id, args.stage)
    reservation = read_json_optional(path)
    if reservation is None:
        return emit({"found": False, "line_id": line_id, "stage": args.stage})
    return emit({"found": True, "reservation": reservation})


def action_reservation_break(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    require(bool(args.stage), "reservation-break requires --stage")
    require(bool(args.reason), "reservation-break requires --reason")
    require(bool(args.evidence_ref), "reservation-break requires --evidence-ref")
    path = reservation_path(ctx.reg, line_id, args.stage)
    reservation = read_json_optional(path)
    if reservation is None:
        return emit({"broken": False, "reason": "no reservation"})
    pid = int(reservation.get("pid") or 0)
    pid_alive = process_alive(pid)
    token_match = None
    if pid_alive and reservation.get("start_token"):
        token_match = process_start_token(pid) == reservation["start_token"]
    if pid_alive and token_match is not False:
        return emit({
            "broken": False, "error": "reservation holder is live",
            "reservation": reservation,
        }, code=EXIT_HELD)
    append_jsonl(reservation_history_path(ctx.reg, line_id, args.stage), {
        "event": "broken",
        "reason": args.reason,
        "evidence_ref": args.evidence_ref,
        "at": now_iso(),
        "reservation": reservation,
    })
    with contextlib.suppress(OSError):
        path.unlink()
    return emit({
        "broken": True, "line_id": line_id, "stage": args.stage,
        "reason": args.reason, "evidence_ref": args.evidence_ref,
    })


def action_orphan_check(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    entry = ctx.load(line_id, optional=True)
    evidence: list[str] = []
    orphaned = False
    if entry is None:
        orphaned = True
        evidence.append("registry-missing")
        reservation_dir = ctx.reg / "reservations"
        if reservation_dir.exists() and list(reservation_dir.glob(f"{line_id}.*.json")):
            evidence.append("reservation-without-registry")
        return emit({"line_id": line_id, "orphaned": orphaned, "evidence": evidence})
    state = entry.get("state")
    files = {
        "status": entry.get("status_path"),
        "log": entry.get("log_path"),
        "heartbeat": entry.get("heartbeat_path"),
        "pid": _pid_path(entry),
    }
    present = [name for name, value in files.items() if value and Path(value).exists()]
    if state in {"closed", "stale", "orphaned"}:
        if entry.get("runner_pid") and process_alive(int(entry["runner_pid"]),
                                                     entry.get("runner_start_token")):
            orphaned = True
            evidence.append("process-alive-while-closed")
    elif state == "active" and entry.get("stage"):
        reservation = read_json_optional(reservation_path(ctx.reg, line_id, entry["stage"]))
        if reservation is None and not present:
            orphaned = True
            evidence.append("line-evidence-missing")
        elif reservation is not None and reservation.get("run_id") != entry.get("run_id"):
            orphaned = True
            evidence.append("reservation-run-mismatch")
    if present:
        evidence.extend(f"present:{name}" for name in present)
    payload = {"line_id": line_id, "orphaned": orphaned, "evidence": evidence}
    if orphaned and args.mark:
        require(state not in {"closed", "stale", "orphaned"},
                f"cannot mark orphaned from state {state!r}")

        def mutate(data):
            data["state"] = "orphaned"
            data["orphaned_at"] = now_iso()
            data["orphan_evidence"] = evidence
            data["last_event"] = "orphan-marked"

        payload["state"] = ctx.mutate(line_id, mutate)["state"]
        payload["marked"] = True
    return emit(payload)


def action_reattach_brief(ctx: Context) -> int:
    args = ctx.args
    line_id = validate_line_id(args.line_id or "")
    entry = ctx.load(line_id)
    local = _local_identity(entry)
    reservation = read_json_optional(reservation_path(ctx.reg, line_id, entry.get("stage") or ""))
    lease = read_json_optional(lease_path(ctx.reg, line_id))
    spine_path = entry.get("spine_path")
    spine = {"path": spine_path, "exists": bool(spine_path and Path(spine_path).exists())}
    if spine["exists"]:
        text = Path(spine_path).read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^\s*state\s*[:=]\s*([A-Za-z_-]+)", text, re.MULTILINE)
        spine["state"] = match.group(1) if match else None
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        spine["last_line"] = lines[-1] if lines else None
    return emit({
        "line_id": line_id,
        "run_id": entry.get("run_id"),
        "registry": {
            "state": entry.get("state"),
            "stage": entry.get("stage"),
            "worktree_path": entry.get("worktree_path"),
            "branch": entry.get("branch"),
            "runner_pid": entry.get("runner_pid"),
            "cli_pid": entry.get("cli_pid"),
        },
        "spine": spine,
        "evidence": {
            "status": local["status"],
            "log": {
                "path": entry.get("log_path"),
                "exists": bool(entry.get("log_path") and Path(entry["log_path"]).exists()),
                "last_line": _last_line(entry.get("log_path")),
            },
            "heartbeat": {
                "path": entry.get("heartbeat_path"),
                "exists": bool(entry.get("heartbeat_path") and Path(entry["heartbeat_path"]).exists()),
                "age_seconds": _heartbeat_age(entry.get("heartbeat_path")),
            },
            "pid": {
                "path": _pid_path(entry),
                "exists": bool(_pid_path(entry) and Path(_pid_path(entry)).exists()),
            },
        },
        "reservation": reservation,
        "lease": lease,
        "identity": local["identity"],
        "branch_hint": _branch_hint(local["identity"], local["status"], reservation),
        "snapshot_required": True,
    })


# ---------------------------------------------------------------- manifests


def normalize_path(raw: str, repo_root: Path) -> str:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        resolved = path.absolute()
    text = str(resolved)
    if len(text) > 1:
        text = text.rstrip(os.sep)
    return text


def paths_overlap(a: str, b: str) -> bool:
    if a == b:
        return True
    a_prefix = a + os.sep
    b_prefix = b + os.sep
    return a.startswith(b_prefix) or b.startswith(a_prefix)


def load_manifest(path: Path, line_id: str, repo_root: Path) -> dict:
    data = read_json(path)
    require(data.get("line_id") == line_id, f"manifest line_id {data.get('line_id')!r} != {line_id!r}")
    for key in ("owned_paths", "read_only_paths", "forbidden_paths"):
        require(isinstance(data.get(key, []), list), f"manifest {key} must be a list")
    owned = [normalize_path(p, repo_root) for p in data.get("owned_paths", [])]
    read_only = [normalize_path(p, repo_root) for p in data.get("read_only_paths", [])]
    forbidden = [normalize_path(p, repo_root) for p in data.get("forbidden_paths", [])]
    for path in owned:
        require(not any(paths_overlap(path, f) for f in forbidden),
                f"owned path overlaps forbidden path: {path}")
    depends = data.get("integration_depends_on", [])
    require(isinstance(depends, list), "integration_depends_on must be a list")
    data.update({
        "schema_version": data.get("schema_version", SCHEMA_VERSION),
        "line_id": line_id,
        "owned_paths": owned,
        "read_only_paths": read_only,
        "forbidden_paths": forbidden,
        "integration_depends_on": depends,
        "declared_at": data.get("declared_at") or now_iso(),
    })
    return data


# ---------------------------------------------------------------- dispatch


UNIMPLEMENTED = set()

DISPATCH = {
    "register": action_register,
    "update": action_update,
    "deregister": action_deregister,
    "list": action_list,
    "resolve-message": action_resolve_message,
    "verify-identity": action_verify_identity,
    "classify-remote": action_classify_remote,
    "reattach-brief": action_reattach_brief,
    "lease-acquire": action_lease_acquire,
    "lease-renew": action_lease_renew,
    "lease-release": action_lease_release,
    "lease-break": action_lease_break,
    "reserve": action_reserve,
    "reservation-status": action_reservation_status,
    "reservation-break": action_reservation_break,
    "orphan-check": action_orphan_check,
    "ownership-check": action_ownership_check,
    "release-ownership": action_release_ownership,
    "promote-waiting": action_promote_waiting,
    "integration-enqueue": action_integration_enqueue,
    "integration-plan": action_integration_plan,
    "integration-record": action_integration_record,
    "allocate-resources": action_allocate_resources,
    "archive-runtime": action_archive_runtime,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="line-registry.py", add_help=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--format", default="json", choices=["json"])
    parser.add_argument("--line-id")
    parser.add_argument("--run-id")
    parser.add_argument("--project-dir")
    parser.add_argument("--repo-root")
    parser.add_argument("--state")
    parser.add_argument("--manifest")
    parser.add_argument("--write-line", action="store_true", default=False)
    parser.add_argument("--stage")
    parser.add_argument("--last-event")
    parser.add_argument("--driver-session")
    parser.add_argument("--cli")
    parser.add_argument("--worktree-path")
    parser.add_argument("--branch")
    parser.add_argument("--base-sha")
    parser.add_argument("--spine")
    parser.add_argument("--pid")
    parser.add_argument("--start-token")
    parser.add_argument("--runner-pid")
    parser.add_argument("--runner-start-token")
    parser.add_argument("--cli-pid")
    parser.add_argument("--cli-start-token")
    parser.add_argument("--prompt-path")
    parser.add_argument("--status-path")
    parser.add_argument("--log-path")
    parser.add_argument("--heartbeat-path")
    parser.add_argument("--meta-json")
    parser.add_argument("--waiting-reason")
    parser.add_argument("--holder-line-id")
    parser.add_argument("--queued-at")
    parser.add_argument("--merge-ready")
    parser.add_argument("--ready-for-merge-at")
    parser.add_argument("--worktree-retained")
    parser.add_argument("--resources")
    parser.add_argument("--remote")
    parser.add_argument("--owned-paths")
    parser.add_argument("--reason")
    parser.add_argument("--evidence-ref")
    parser.add_argument("--message")
    parser.add_argument("--clarified", action="store_true", default=False)
    parser.add_argument("--probe-json")
    parser.add_argument("--session")
    parser.add_argument("--ttl")
    parser.add_argument("--override", action="store_true", default=False)
    parser.add_argument("--host")
    parser.add_argument("--worktree")
    parser.add_argument("--dest")
    parser.add_argument("--port-range-start")
    parser.add_argument("--block-size")
    parser.add_argument("--cap")
    parser.add_argument("--result")
    parser.add_argument("--commit")
    parser.add_argument("--at")
    parser.add_argument("--label")
    parser.add_argument("--active", action="store_true", default=False)
    parser.add_argument("--all", action="store_true", default=False)
    parser.add_argument("--mark", action="store_true", default=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.action not in ACTIONS:
        return fail_from(EngineError(EXIT_USAGE, f"unknown action: {args.action}"))
    handler = DISPATCH.get(args.action)
    if handler is None:
        return fail_from(EngineError(
            EXIT_USAGE, f"action not implemented yet: {args.action}",
        ))
    ctx = Context(args)
    ownership_actions = {
        "register", "deregister", "ownership-check", "release-ownership",
        "promote-waiting", "integration-record", "allocate-resources",
        "orphan-check",
    }
    needs_ownership_lock = args.action in ownership_actions or (
        args.action == "update" and (
            args.state == "active"
            or args.owned_paths is not None
            or args.worktree_path is not None
        )
    )
    try:
        if needs_ownership_lock:
            # Cross-line gate + write must be atomic: otherwise two concurrent
            # registrations can both observe "no conflict" (P0 audit TOCTOU).
            ensure_registry_dir(ctx.reg)
            with line_lock(ctx.reg / ".ownership.lock"):
                return handler(ctx)
        return handler(ctx)
    except EngineError as exc:
        return fail_from(exc)
    except json.JSONDecodeError as exc:
        return fail_from(EngineError(EXIT_USAGE, f"invalid JSON argument: {exc}"))
    except (OSError, ValueError) as exc:
        return fail_from(RegistryIOError(resolve_registry_dir(), str(exc)))


if __name__ == "__main__":
    sys.exit(main())
