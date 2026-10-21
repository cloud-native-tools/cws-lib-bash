#!/usr/bin/env python3
"""execution-config.py — deterministic subagent CLI configuration resolver (Feature 061).

Behavior owner of ``.specify/specs/061-subagent-cli-config/contracts/execution-config-cli.md``
(C-EC-01..C-EC-15). stdlib-only; Python 3.8+.

Actions: ``resolve`` / ``validate`` / ``list-configs``.
Exit contract: 0 success; 2 usage/input/configuration error; 1 unexpected or I/O error.

Layer precedence: ``_defaults.yaml`` < ``configs/<slug>.yaml`` < inline parameters.
The effective config always contains the eight keys ``mode / cli / model /
reasoning_effort / context_window / extra_flags / log_dir / quantification``; a cleared
or absent value field is ``null``. The CLI capability matrix below is the single runtime
owner (other documents reference it, never copy it).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ACTIONS = ("resolve", "validate", "list-configs")
MODES = ("native", "virtual", "external")
METHODS = ("auto", "declared", "qoder-settings", "none")
VALUE_FIELDS = ("model", "reasoning_effort", "context_window", "extra_flags", "log_dir")
EFFECTIVE_KEYS = ("mode", "cli", "model", "reasoning_effort", "context_window",
                  "extra_flags", "log_dir", "quantification")
CLEAR_SENTINELS = ("", "auto")

DEFAULTS_REL = Path(".specify") / "agents" / "execution" / "configs" / "_defaults.yaml"
CONFIGS_REL = Path(".specify") / "agents" / "execution" / "configs"
LOGS_REL = Path(".specify") / "agents" / "execution" / "logs"
SNAPSHOT_KIND = "speckit.execution-config-snapshot"
SNAPSHOT_SCHEMA_VERSION = 1

#: Single runtime owner of the CLI capability matrix (FR-008). Documents reference
#: this table; they never copy it.
CAPABILITY_MATRIX: Dict[str, Dict[str, Any]] = {
    "qodercli": {
        "external": True,
        "flags": {"model": True, "reasoning_effort": True, "context_window": True},
        "quantification_methods": ["qoder-settings", "declared", "none"],
        "reason": "",
    },
    "claude": {
        "external": True,
        "flags": {"model": False, "reasoning_effort": False, "context_window": False},
        "quantification_methods": ["declared", "none"],
        "reason": "model/reasoning-effort/context-window flags are not verified in this repo",
    },
    "codex": {
        "external": False,
        "flags": {"model": False, "reasoning_effort": False, "context_window": False},
        "quantification_methods": ["none"],
        "reason": "external stream-json dispatch is not verified",
    },
    "opencode": {
        "external": False,
        "flags": {"model": False, "reasoning_effort": False, "context_window": False},
        "quantification_methods": ["none"],
        "reason": "external stream-json dispatch is not verified",
    },
}

MANAGED_FLAG_PREFIXES = ("--model", "--reasoning-effort", "--context-window")


class ConfigError(Exception):
    """Unexpected or I/O failure surfaced as exit 1."""


class InputError(ConfigError):
    """Usage/input/configuration error surfaced as exit 2."""


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sibling_engine(filename: str):
    path = Path(__file__).resolve().parent / filename
    if not path.is_file():
        raise ConfigError(f"sibling engine not found beside this one: {path}")
    import importlib.util
    name = "_ec_" + filename.replace("-", "_").replace(".py", "")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ConfigError(f"cannot load sibling engine: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def resolve_workspace_root(explicit: Optional[str]) -> Path:
    if explicit:
        return Path(explicit).resolve()
    script = Path(__file__).resolve()
    parts = script.parts
    for i, part in enumerate(parts):
        if part == ".specify" and i + 1 < len(parts) and parts[i + 1] == "scripts":
            return Path(*parts[:i])
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if (candidate / ".specify").is_dir():
            return candidate
    return cwd


def rel_posix(path: Path, workspace_root: Path) -> str:
    try:
        return path.relative_to(workspace_root).as_posix()
    except ValueError:
        return path.as_posix()


# ---------------------------------------------------------------------------
# minimal YAML subset (C-EC-03)
# ---------------------------------------------------------------------------

def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_yaml_subset(path: Path) -> Dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"cannot read config file {path}: {exc}") from exc
    values: Dict[str, Any] = {}
    quantification: Dict[str, str] = {}
    in_quantification = False
    seen_quantification = False
    for lineno, raw in enumerate(text.splitlines(), 1):
        location = f"{path}:{lineno}"
        if "\t" in raw:
            raise InputError(f"{location}: tab characters are not allowed")
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        if stripped == "-" or stripped.startswith("- "):
            raise InputError(f"{location}: YAML list syntax is not supported")
        if ":" not in raw:
            raise InputError(f"{location}: expected 'key: value'")
        key, _, rest = raw.partition(":")
        key = key.strip()
        value = rest.strip()
        if indent == 0:
            in_quantification = False
            if not key:
                raise InputError(f"{location}: empty key")
            if key == "quantification":
                if seen_quantification:
                    raise InputError(f"{location}: duplicate 'quantification' section")
                if value:
                    raise InputError(f"{location}: 'quantification' must be a nested section")
                seen_quantification = True
                in_quantification = True
                continue
            if key in values:
                raise InputError(f"{location}: duplicate key {key!r}")
            if value.startswith("["):
                raise InputError(f"{location}: YAML list syntax is not supported")
            values[key] = _strip_quotes(value)
        else:
            if indent != 2:
                raise InputError(f"{location}: nesting deeper than one level is not supported")
            if not in_quantification:
                raise InputError(
                    f"{location}: nested key {key!r} without an active 'quantification:' section")
            if key != "method":
                raise InputError(
                    f"{location}: 'quantification' only allows the 'method' key, got {key!r}")
            if "method" in quantification:
                raise InputError(f"{location}: duplicate key 'method'")
            if value.startswith("["):
                raise InputError(f"{location}: YAML list syntax is not supported")
            quantification["method"] = _strip_quotes(value)
    if seen_quantification:
        values["quantification"] = quantification
    return values


# ---------------------------------------------------------------------------
# layer validation (C-EC-04 / V1–V9)
# ---------------------------------------------------------------------------

def _reject_managed_flags(extra_flags: str) -> Optional[str]:
    if "\n" in extra_flags or "\r" in extra_flags:
        return "extra_flags must be a single line"
    try:
        tokens = shlex.split(extra_flags)
    except ValueError as exc:
        return f"extra_flags cannot be tokenized: {exc}"
    for token in tokens:
        if token == "-m" or (token.startswith("-m") and not token.startswith("--")):
            return f"extra_flags must not contain the managed flag {token!r}"
        if token in MANAGED_FLAG_PREFIXES or any(
                token.startswith(prefix + "=") for prefix in MANAGED_FLAG_PREFIXES):
            return f"extra_flags must not contain the managed flag {token!r}"
    return None


def validate_layer(values: Dict[str, Any], layer: str, agent: str,
                   workspace_root: Path) -> List[str]:
    errors: List[str] = []
    allowed = {"mode", "cli", "model", "reasoning_effort", "context_window",
               "extra_flags", "log_dir", "quantification"}
    if layer == "agent-config":
        allowed = allowed | {"agent"}
    for key in values:
        if key not in allowed:
            errors.append(f"unknown key {key!r} in {layer} layer (allowed: {', '.join(sorted(allowed))})")
    if "agent" in values:
        if layer != "agent-config":
            errors.append(f"key 'agent' is not allowed in the {layer} layer")
        elif values["agent"] != agent:
            errors.append(
                f"agent config declares agent={values['agent']!r} but resolve was asked for {agent!r}")
    if "mode" in values and values["mode"] not in MODES:
        errors.append(f"invalid mode {values['mode']!r} (allowed: {', '.join(MODES)})")
    if "cli" in values:
        cli = values["cli"]
        if not isinstance(cli, str) or not cli.strip():
            errors.append("cli must be a non-empty string")
    for field in ("model", "reasoning_effort"):
        if field in values and values[field] in (None, ""):
            continue
    if "context_window" in values:
        raw = values["context_window"]
        if raw not in CLEAR_SENTINELS:
            if not re.fullmatch(r"[0-9]+", str(raw)) or int(raw) <= 0:
                errors.append(
                    f"context_window must be a positive integer (got {raw!r})")
    if "extra_flags" in values:
        raw = values["extra_flags"]
        if raw not in CLEAR_SENTINELS:
            problem = _reject_managed_flags(str(raw))
            if problem:
                errors.append(problem)
    if "log_dir" in values:
        raw = values["log_dir"]
        if raw not in CLEAR_SENTINELS:
            try:
                logs_root = (workspace_root / LOGS_REL).resolve()
                candidate = Path(raw)
                resolved = ((workspace_root / candidate) if not candidate.is_absolute()
                            else candidate).resolve()
                resolved.relative_to(logs_root)
            except (OSError, ValueError):
                errors.append(
                    f"log_dir must resolve inside {LOGS_REL.as_posix()} (got {raw!r})")
    if "quantification" in values:
        quant = values["quantification"]
        if not isinstance(quant, dict):
            errors.append("quantification must be a nested section")
        else:
            for key in quant:
                if key != "method":
                    errors.append(f"quantification only allows 'method' (got {key!r})")
            if "method" in quant and quant["method"] not in METHODS:
                errors.append(
                    f"invalid quantification.method {quant['method']!r} "
                    f"(allowed: {', '.join(METHODS)})")
    return errors


def normalize_log_dir(raw: str, workspace_root: Path) -> str:
    candidate = Path(raw)
    resolved = ((workspace_root / candidate) if not candidate.is_absolute()
                else candidate).resolve()
    return rel_posix(resolved, workspace_root)


def load_layer(path: Path, layer: str, agent: str, workspace_root: Path,
               required: bool) -> Optional[Dict[str, Any]]:
    if not path.is_file():
        if required:
            raise InputError(
                f"defaults layer missing: {path} — run 'specify init' to seed it from "
                f".specify/templates/execution-config-defaults.yaml, or restore the file")
        return None
    values = parse_yaml_subset(path)
    errors = validate_layer(values, layer, agent, workspace_root)
    if errors:
        raise InputError(f"{path}: " + "; ".join(errors))
    return values


# ---------------------------------------------------------------------------
# host detection
# ---------------------------------------------------------------------------

def detect_host_cli(explicit: Optional[str]) -> str:
    if explicit:
        return explicit.strip().lower()
    env = os.environ.get("SPECKIT_HOST_CLI", "").strip()
    if env:
        return env.lower()
    try:
        module = sibling_engine("exec-quant.py")
        group, _pid, name = module.collect_agent()
        if group.get("resolution") == "resolved" and name:
            return str(name).lower()
    except Exception:
        pass
    return "unknown"


# ---------------------------------------------------------------------------
# resolution pipeline
# ---------------------------------------------------------------------------

def _is_clear(raw: Any) -> bool:
    return raw is None or raw in CLEAR_SENTINELS


def _converted(field: str, raw: Any, workspace_root: Path) -> Any:
    if _is_clear(raw):
        return None
    if field == "context_window":
        return int(raw)
    if field == "log_dir":
        return normalize_log_dir(str(raw), workspace_root)
    return raw


def _layer_path(path: Optional[Path], workspace_root: Path) -> Optional[str]:
    return rel_posix(path, workspace_root) if path is not None else None


def evaluate(agent: str, workspace_root: Path, inline: Dict[str, Any],
             host_cli: str) -> Dict[str, Any]:
    defaults_path = workspace_root / DEFAULTS_REL
    agent_path = workspace_root / CONFIGS_REL / f"{agent}.yaml"

    defaults_values = load_layer(defaults_path, "defaults", agent, workspace_root,
                                 required=True)
    agent_values = load_layer(agent_path, "agent-config", agent, workspace_root,
                              required=False)
    inline_values = dict(inline)
    inline_errors = validate_layer(inline_values, "inline", agent, workspace_root)
    if inline_errors:
        raise InputError("inline parameters: " + "; ".join(inline_errors))

    assert defaults_values is not None
    # --- identity conflicts between the declaring layers (defaults never conflicts)
    agent_mode = agent_values.get("mode") if agent_values else None
    inline_mode = inline_values.get("mode")
    if agent_mode is not None and inline_mode is not None and agent_mode != inline_mode:
        raise InputError(f"conflicting field 'mode': agent-config={agent_mode!r} "
                         f"inline={inline_mode!r}")
    agent_cli = agent_values.get("cli") if agent_values else None
    inline_cli = inline_values.get("cli")
    if agent_cli is not None and inline_cli is not None and agent_cli != inline_cli:
        raise InputError(f"conflicting field 'cli': agent-config={agent_cli!r} "
                         f"inline={inline_cli!r}")

    explicit_cli = inline_cli if inline_cli is not None else agent_cli
    defaults_skipped = (explicit_cli is not None
                        and defaults_values.get("cli") is not None
                        and explicit_cli != defaults_values.get("cli"))
    participating_defaults = {} if defaults_skipped else dict(defaults_values)

    # --- explicit override detection (agent + inline only)
    override_layers = [layer for layer in (agent_values or {}, inline_values)]
    override_exists = any(
        not _is_clear(layer.get(field))
        for layer in override_layers for field in VALUE_FIELDS
        if field in layer)

    explicit_mode = inline_mode if inline_mode is not None else agent_mode
    if explicit_mode is not None:
        mode = explicit_mode
        if mode in ("native", "virtual"):
            if explicit_cli is not None:
                raise InputError(
                    f"field 'cli' ({explicit_cli!r}) contradicts mode {mode!r}: "
                    f"cli applies to external dispatch only; declare mode: external")
            if override_exists:
                raise InputError(
                    f"mode {mode!r} cannot carry override fields — declare mode: external")
    elif override_exists:
        mode = "external"
    elif "mode" in participating_defaults:
        mode = participating_defaults["mode"]
    else:
        mode = "native"

    if mode == "external":
        cli = explicit_cli if explicit_cli is not None else participating_defaults.get("cli")
        if not cli:
            raise InputError(
                f"field 'cli' is required for mode 'external' "
                f"(supported CLIs: {', '.join(sorted(CAPABILITY_MATRIX))})")
    else:
        cli = explicit_cli if explicit_cli is not None else participating_defaults.get("cli")

    # --- merge value fields with clear sentinels
    effective_values: Dict[str, Any] = {field: None for field in VALUE_FIELDS}
    source_chain: Dict[str, Dict[str, Any]] = {}
    field_sources: Dict[str, Tuple[str, Optional[Path]]] = {}
    for layer_name, layer_values, layer_path_ in (
            ("defaults", participating_defaults, defaults_path if not defaults_skipped else None),
            ("agent-config", agent_values or {}, agent_path if agent_values is not None else None),
            ("inline", inline_values, None)):
        for field in VALUE_FIELDS:
            if field not in layer_values:
                continue
            raw = layer_values[field]
            if _is_clear(raw):
                effective_values[field] = None
                field_sources.pop(field, None)
            else:
                effective_values[field] = _converted(field, raw, workspace_root)
                field_sources[field] = (layer_name, layer_path_)

    # --- mode / cli source chain
    if explicit_mode is not None:
        mode_layer, mode_path = (("inline", None) if inline_mode is not None
                                 else ("agent-config", agent_path))
    elif mode == "external" and override_exists:
        mode_layer, mode_path = ("derived", None)
    elif "mode" in participating_defaults:
        mode_layer, mode_path = ("defaults", defaults_path)
    else:
        mode_layer, mode_path = ("derived", None)

    if cli is not None:
        if explicit_cli is not None:
            cli_layer, cli_path = (("inline", None) if inline_cli is not None
                                   else ("agent-config", agent_path))
        elif "cli" in participating_defaults:
            cli_layer, cli_path = ("defaults", defaults_path)
        else:  # pragma: no cover - defensive; mode external already rejects null cli
            cli_layer, cli_path = ("derived", None)
    else:
        cli_layer, cli_path = (None, None)

    # --- quantification requested/resolved (C-EC-09)
    if "quantification" in inline_values and "method" in inline_values["quantification"]:
        requested = inline_values["quantification"]["method"]
        method_layer, method_path = ("inline", None)
    elif (agent_values and "quantification" in agent_values
          and "method" in agent_values["quantification"]):
        requested = agent_values["quantification"]["method"]
        method_layer, method_path = ("agent-config", agent_path)
    elif (not defaults_skipped and "quantification" in participating_defaults
          and "method" in participating_defaults["quantification"]):
        requested = participating_defaults["quantification"]["method"]
        method_layer, method_path = ("defaults", defaults_path)
    else:
        requested = "auto"
        method_layer, method_path = ("derived", None)

    warnings: List[str] = []
    if requested != "auto":
        resolved = requested
    elif mode == "external" and override_exists:
        resolved = "declared"
    elif mode == "external" and cli == "qodercli":
        resolved = "qoder-settings"
    elif mode in ("native", "virtual") and host_cli == "qodercli":
        resolved = "qoder-settings"
    else:
        resolved = "none"
        warnings.append(
            "quantification resolved to 'none' (no declarative override and no qoder host)")

    # --- capability matrix (resolved method only; requested=auto is never rejected)
    if cli is not None:
        profile = CAPABILITY_MATRIX.get(str(cli))
        if profile is None:
            raise InputError(
                f"unknown cli {cli!r} (supported CLIs: "
                f"{', '.join(sorted(CAPABILITY_MATRIX))})")
        if mode == "external" and not profile["external"]:
            raise InputError(
                f"cli {cli!r} does not support external dispatch "
                f"(supported external CLIs: "
                f"{', '.join(sorted(name for name, row in CAPABILITY_MATRIX.items() if row['external']))}); "
                f"reason: {profile['reason']}")
        for field in ("model", "reasoning_effort", "context_window"):
            if effective_values[field] is not None and not profile["flags"][field]:
                rows = [name for name, row in CAPABILITY_MATRIX.items()
                        if row["flags"][field]]
                raise InputError(
                    f"field {field!r} is not supported by cli {cli!r} "
                    f"(supported CLIs for {field}: {', '.join(sorted(rows)) or 'none'})")
        if resolved not in profile["quantification_methods"]:
            raise InputError(
                f"quantification method {resolved!r} is not supported by cli {cli!r} "
                f"(supported: {', '.join(profile['quantification_methods'])})")

    if resolved == "declared":
        missing = [field for field in ("model", "reasoning_effort", "context_window")
                   if effective_values[field] is None]
        if missing:
            raise InputError(
                "quantification.method 'declared' requires model, reasoning_effort "
                f"and context_window; missing: {', '.join(missing)}")
    if resolved == "qoder-settings":
        supported = ((mode == "external" and cli == "qodercli")
                     or (mode in ("native", "virtual") and host_cli == "qodercli"))
        if not supported:
            raise InputError(
                "quantification.method 'qoder-settings' requires a qodercli host or "
                "external dispatch through qodercli")

    effective: Dict[str, Any] = {
        "mode": mode,
        "cli": cli,
        "model": effective_values["model"],
        "reasoning_effort": effective_values["reasoning_effort"],
        "context_window": effective_values["context_window"],
        "extra_flags": effective_values["extra_flags"],
        "log_dir": effective_values["log_dir"],
        "quantification": {"requested": requested, "resolved": resolved},
    }

    # --- source chain covers every non-null effective field + quantification.method
    for field, (layer_name, layer_path_) in field_sources.items():
        entry: Dict[str, Any] = {"layer": layer_name}
        if layer_path_ is not None:
            entry["path"] = _layer_path(layer_path_, workspace_root)
        source_chain[field] = entry
    source_chain["mode"] = {"layer": mode_layer}
    if mode_path is not None:
        source_chain["mode"]["path"] = _layer_path(mode_path, workspace_root)
    if cli_layer is not None:
        entry = {"layer": cli_layer}
        if cli_path is not None:
            entry["path"] = _layer_path(cli_path, workspace_root)
        source_chain["cli"] = entry
    entry = {"layer": method_layer}
    if method_path is not None:
        entry["path"] = _layer_path(method_path, workspace_root)
    source_chain["quantification.method"] = entry

    # --- cli_args (C-EC-10)
    cli_args: List[str] = []
    if mode == "external":
        for flag, field in (("--model", "model"),
                            ("--reasoning-effort", "reasoning_effort"),
                            ("--context-window", "context_window")):
            if effective_values[field] is not None:
                cli_args += [flag, str(effective_values[field])]
        if effective_values["extra_flags"]:
            cli_args += shlex.split(effective_values["extra_flags"])

    canonical = json.dumps(effective, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False)
    config_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    return {
        "agent": agent,
        "config_id": config_id,
        "effective": effective,
        "source_chain": source_chain,
        "skipped_layers": ["defaults"] if defaults_skipped else [],
        "cli_args": cli_args,
        "requires_external": mode == "external",
        "quantification": {"requested": requested, "resolved": resolved},
        "warnings": warnings,
    }


def write_snapshot(result: Dict[str, Any], workspace_root: Path) -> str:
    logs_root = workspace_root / LOGS_REL
    snapshot_dir = logs_root / "config-snapshots"
    snapshot_path = snapshot_dir / f"{result['config_id']}.json"
    document = {
        "kind": SNAPSHOT_KIND,
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "config_id": result["config_id"],
        "resolved_at": now_iso(),
        "agent": result["agent"],
        "effective": result["effective"],
        "source_chain": result["source_chain"],
        "skipped_layers": result["skipped_layers"],
        "requires_external": result["requires_external"],
        "cli_args": result["cli_args"],
        "log_dir": result["effective"]["log_dir"] or LOGS_REL.as_posix(),
    }
    try:
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".snapshot-", dir=str(snapshot_dir))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temp_name, snapshot_path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
    except OSError as exc:
        raise ConfigError(f"cannot write config snapshot {snapshot_path}: {exc}") from exc
    return rel_posix(snapshot_path, workspace_root)


# ---------------------------------------------------------------------------
# inline parameters
# ---------------------------------------------------------------------------

INLINE_MAP = (
    ("mode", "mode"),
    ("cli", "cli"),
    ("model", "model"),
    ("reasoning_effort", "reasoning_effort"),
    ("context_window", "context_window"),
    ("extra_flags", "extra_flags"),
    ("log_dir", "log_dir"),
)
INLINE_METHOD_ARG = "quantification_method"


def inline_layer(args: argparse.Namespace) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    for arg_name, field in INLINE_MAP:
        raw = getattr(args, arg_name)
        if raw is not None:
            values[field] = raw
    method = getattr(args, INLINE_METHOD_ARG)
    if method is not None:
        values["quantification"] = {"method": method}
    return values


# ---------------------------------------------------------------------------
# actions
# ---------------------------------------------------------------------------

def action_resolve(args: argparse.Namespace) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    agent = (args.agent or "").strip()
    if not agent:
        raise InputError("resolve requires --agent <slug>")
    host_cli = detect_host_cli(args.host_cli)
    result = evaluate(agent, workspace_root, inline_layer(args), host_cli)
    result["snapshot"] = write_snapshot(result, workspace_root)
    for warning in result["warnings"]:
        print(f"execution-config: warning: {warning}", file=sys.stderr)
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    effective = result["effective"]
    print(f"agent: {result['agent']}")
    print(f"config_id: {result['config_id']}")
    print(f"mode: {effective['mode']}  cli: {effective['cli']}")
    print(f"model: {effective['model']}  reasoning_effort: {effective['reasoning_effort']}  "
          f"context_window: {effective['context_window']}")
    print(f"requires_external: {str(result['requires_external']).lower()}")
    print(f"quantification: requested={effective['quantification']['requested']} "
          f"resolved={effective['quantification']['resolved']}")
    print(f"cli_args: {' '.join(result['cli_args'])}")
    print(f"skipped_layers: {', '.join(result['skipped_layers']) or '-'}")
    print(f"snapshot: {result['snapshot']}")
    for field, entry in result["source_chain"].items():
        suffix = f" ({entry['path']})" if entry.get("path") else ""
        print(f"  {field} <- {entry['layer']}{suffix}")
    return 0


def action_validate(args: argparse.Namespace) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    agent = (args.agent or "").strip()
    if not agent:
        raise InputError("validate requires --agent <slug>")
    result: Dict[str, Any] = {"target": agent, "valid": False, "errors": []}
    try:
        host_cli = detect_host_cli(args.host_cli)
        evaluate(agent, workspace_root, inline_layer(args), host_cli)
        result["valid"] = True
    except InputError as exc:
        result["errors"] = [str(exc)]
    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"target: {agent}")
        print(f"valid: {str(result['valid']).lower()}")
        for error in result["errors"]:
            print(f"  error: {error}")
    return 0 if result["valid"] else 2


def action_list_configs(args: argparse.Namespace) -> int:
    workspace_root = resolve_workspace_root(args.workspace_root)
    configs_dir = workspace_root / CONFIGS_REL
    defaults_path = workspace_root / DEFAULTS_REL
    if not defaults_path.is_file():
        raise InputError(
            f"defaults layer missing: {defaults_path} — run 'specify init' to seed it from "
            f".specify/templates/execution-config-defaults.yaml, or restore the file")
    entries: List[Dict[str, Any]] = []
    try:
        files = sorted(configs_dir.glob("*.yaml"))
    except OSError as exc:
        raise ConfigError(f"cannot scan {configs_dir}: {exc}") from exc
    host_cli = detect_host_cli(args.host_cli)
    for path in files:
        if path.name == "_defaults.yaml":
            continue
        slug = path.stem
        entry: Dict[str, Any] = {"file": path.name, "agent": slug, "valid": False,
                                 "errors": []}
        try:
            evaluate(slug, workspace_root, {}, host_cli)
            entry["valid"] = True
        except InputError as exc:
            entry["errors"] = [str(exc)]
        entries.append(entry)
    if args.format == "json":
        print(json.dumps({"configs": entries}, ensure_ascii=False, indent=2))
        return 0
    for entry in entries:
        status = "ok" if entry["valid"] else "invalid"
        print(f"{entry['file']}  agent={entry['agent']}  {status}")
        for error in entry["errors"]:
            print(f"  error: {error}")
    return 0


USAGE_LINE = ("usage: execution-config.py --action {" + ",".join(ACTIONS) + "} "
              "--agent SLUG [--mode MODE] [--cli CLI] [--model MODEL] "
              "[--reasoning-effort EFFORT] [--context-window N] "
              "[--extra-flags FLAGS] [--log-dir DIR] "
              "[--quantification-method METHOD] [--host-cli CLI] "
              "[--workspace-root PATH] [--format text|json]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="execution-config.py", allow_abbrev=False)
    parser.add_argument("--workspace-root", default=None)
    parser.add_argument("--action", required=True, choices=list(ACTIONS))
    parser.add_argument("--agent", default=None)
    parser.add_argument("--mode", default=None)
    parser.add_argument("--cli", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--reasoning-effort", dest="reasoning_effort", default=None)
    parser.add_argument("--context-window", dest="context_window", default=None)
    parser.add_argument("--extra-flags", dest="extra_flags", default=None)
    parser.add_argument("--log-dir", dest="log_dir", default=None)
    parser.add_argument("--quantification-method", dest="quantification_method",
                        default=None)
    parser.add_argument("--host-cli", dest="host_cli", default=None)
    parser.add_argument("--format", default="text", choices=["text", "json"])
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.action == "resolve":
            return action_resolve(args)
        if args.action == "validate":
            return action_validate(args)
        return action_list_configs(args)
    except InputError as exc:
        print(USAGE_LINE, file=sys.stderr)
        print(f"execution-config: configuration error: {exc}", file=sys.stderr)
        return 2
    except ConfigError as exc:
        print(f"execution-config: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # never raise into the caller's dispatch path
        print(f"execution-config: unexpected failure: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
