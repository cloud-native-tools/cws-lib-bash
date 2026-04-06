#!/usr/bin/env bash

# Load common helpers for Unicode support and shared functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/common.sh" ]; then
  # shellcheck source=/dev/null
  source "$SCRIPT_DIR/common.sh"
  ensure_utf8_locale || true
else
  echo "Failed to load common.sh, spec-kit framework not installed correctly" >&2
  exit 1
fi

set -e

# Set root dir
if git rev-parse --show-toplevel >/dev/null 2>&1; then
  ROOT_DIR=$(git rev-parse --show-toplevel)
else
  case "$SCRIPT_DIR" in
    */.specify/scripts/bash)
      ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"
      ;;
    *)
      ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
      ;;
  esac
fi

SPECIFY_PY_DIR="$ROOT_DIR/.specify/scripts/python"

if [ -f "$SPECIFY_PY_DIR/tools-utils.py" ]; then
  PY_SCRIPTS_DIR="$SPECIFY_PY_DIR"
else
  PY_SCRIPTS_DIR="$ROOT_DIR/scripts/python"
fi

TOOLS_UTILS_SCRIPT="$PY_SCRIPTS_DIR/tools-utils.py"

for required in "$TOOLS_UTILS_SCRIPT"; do
  if [ ! -f "$required" ]; then
    echo "Required script not found: $required" >&2
    exit 1
  fi
done

QUERY_MCP=false
QUERY_SYSTEM=false
QUERY_SHELL=false
QUERY_PROJECT=false
JSON_MODE=false
DEBUG_MODE=false

usage() {
  cat >&2 <<EOF
Usage: $0 [--mcp] [--system] [--shell] [--project] [--json] [--debug]

Options:
  --mcp      Query MCP tools
  --system   Query system binaries
  --shell    Query shell functions
  --project  Query project scripts
  --json     Emit a unified JSON payload for the selected sources
  --debug    Emit diagnostics to stderr while keeping stdout JSON-only
EOF
  exit 1
}

debug_log() {
  if [ "$DEBUG_MODE" = true ] || [ -n "${REFRESH_TOOLS_DEBUG:-}" ]; then
    echo "[refresh-tools][debug] $*" >&2
  fi
}

json_diagnostic() {
  local json_file="$1"
  python3 - "$json_file" <<'PYEOF'
import json
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
try:
    json.loads(text)
except json.JSONDecodeError as exc:
    start = max(exc.pos - 120, 0)
    end = min(exc.pos + 120, len(text))
    excerpt = text[start:end].replace("\n", "\\n")
    print(
        json.dumps(
            {
                "message": exc.msg,
                "line": exc.lineno,
                "column": exc.colno,
                "position": exc.pos,
                "excerpt": excerpt,
            },
            ensure_ascii=False,
        )
    )
    sys.exit(1)
PYEOF
}

print_prefixed_file() {
  local prefix="$1"
  local file_path="$2"

  if [ -s "$file_path" ]; then
    sed "s/^/${prefix}/" "$file_path" >&2
  fi
}

run_json_command() {
  local source_name="$1"
  local default_json="$2"
  shift 2

  local stdout_file stderr_file status validation
  stdout_file=$(mktemp)
  stderr_file=$(mktemp)
  status=0

  if "$@" >"$stdout_file" 2>"$stderr_file"; then
    status=0
  else
    status=$?
  fi

  if [ "$status" -ne 0 ]; then
    echo "[refresh-tools] Warning: source '$source_name' exited with code $status; using empty fallback payload" >&2
    debug_log "failed command ($source_name): $*"
    print_prefixed_file "[refresh-tools][stderr][$source_name] " "$stderr_file"
    printf '%s\n' "$default_json" >"$stdout_file"
  elif ! validation=$(json_diagnostic "$stdout_file"); then
    echo "[refresh-tools] Warning: source '$source_name' emitted invalid JSON; using empty fallback payload" >&2
    debug_log "invalid JSON diagnostics ($source_name): $validation"
    print_prefixed_file "[refresh-tools][stderr][$source_name] " "$stderr_file"
    if [ "$DEBUG_MODE" = true ] || [ -n "${REFRESH_TOOLS_DEBUG:-}" ]; then
      print_prefixed_file "[refresh-tools][stdout][$source_name] " "$stdout_file"
    fi
    printf '%s\n' "$default_json" >"$stdout_file"
  elif [ "$DEBUG_MODE" = true ] || [ -n "${REFRESH_TOOLS_DEBUG:-}" ]; then
    print_prefixed_file "[refresh-tools][stderr][$source_name] " "$stderr_file"
  fi

  cat "$stdout_file"
  rm -f "$stdout_file" "$stderr_file"
}

get_mcp_tools_json() {
  run_json_command "mcp" '{"timestamp": null, "count": 0, "servers": [], "note": "MCP discovery unavailable"}' \
    python3 "$TOOLS_UTILS_SCRIPT" --action list --type mcp
}

get_system_binaries_json() {
  run_json_command "system" '{"os_release": "", "kernel": "", "binaries": []}' \
    python3 "$TOOLS_UTILS_SCRIPT" --action list --type system
}

get_shell_function_json() {
  run_json_command "shell" '[]' \
    python3 "$TOOLS_UTILS_SCRIPT" --action list --type shell --functions-only
}

get_project_scripts_json() {
  run_json_command "project" '[]' \
    python3 "$TOOLS_UTILS_SCRIPT" --action list --type project --root-dir "$ROOT_DIR"
}

emit_unified_json() {
  local tmp_dir="$1"
  python3 - "$tmp_dir" "$QUERY_MCP" "$QUERY_SYSTEM" "$QUERY_SHELL" "$QUERY_PROJECT" <<'PYEOF'
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path


def load(name: str):
    path = Path(sys.argv[1]) / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


query_mcp = sys.argv[2] == "true"
query_system = sys.argv[3] == "true"
query_shell = sys.argv[4] == "true"
query_project = sys.argv[5] == "true"

mcp_payload = load("mcp") if query_mcp else None
system_payload = load("system") if query_system else None
shell_payload = load("shell") if query_shell else None
project_payload = load("project") if query_project else None

tools = []
sources = []

if query_mcp:
    sources.append("mcp")
    for server in (mcp_payload or {}).get("servers", []):
        server_name = server.get("name", "unknown")
        for tool in server.get("tools", []):
            normalized = dict(tool)
            normalized.update(
                {
                    "sourceType": "mcp",
                    "sourceName": server_name,
                    "canonicalName": f"mcp:{server_name}:{tool.get('name', 'unknown')}",
                    "serverName": server_name,
                }
            )
            tools.append(normalized)

if query_system:
    sources.append("system")
    for binary in (system_payload or {}).get("binaries", []):
        name = binary.get("name", "unknown")
        path = binary.get("path", "")
        tools.append(
            {
                **binary,
                "description": f"System binary at {path}" if path else "System binary",
                "sourceType": "system",
                "sourceName": name,
                "canonicalName": f"system:{name}",
            }
        )

if query_shell:
    sources.append("shell")
    for func in shell_payload or []:
        name = func.get("name", "unknown")
        tools.append(
            {
                **func,
                "description": func.get("description", "Shell function"),
                "sourceType": "shell",
                "sourceName": name,
                "canonicalName": f"shell:{name}",
            }
        )

if query_project:
    sources.append("project")
    for script in project_payload or []:
        name = script.get("name", "unknown")
        path = script.get("path", name)
        tools.append(
            {
                **script,
                "sourceType": "project",
                "sourceName": path,
                "canonicalName": f"project:{path}",
            }
        )

payload = {
    "timestamp": datetime.now().isoformat(),
    "sources": sources,
    "tools": tools,
    "mcp_servers": (mcp_payload or {}).get("servers", []) if query_mcp else [],
    "system_binaries": (system_payload or {}).get("binaries", []) if query_system else [],
    "shell_functions": shell_payload or [] if query_shell else [],
    "project_scripts": project_payload or [] if query_project else [],
}

print(json.dumps(payload, ensure_ascii=False, indent=2))
PYEOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --mcp)
      QUERY_MCP=true
      shift
      ;;
    --system)
      QUERY_SYSTEM=true
      shift
      ;;
    --shell)
      QUERY_SHELL=true
      shift
      ;;
    --project)
      QUERY_PROJECT=true
      shift
      ;;
    --json)
      JSON_MODE=true
      shift
      ;;
    --debug)
      DEBUG_MODE=true
      shift
      ;;
    *)
      usage
      ;;
  esac
done

if [ "$QUERY_MCP" = false ] && [ "$QUERY_SYSTEM" = false ] && [ "$QUERY_SHELL" = false ] && [ "$QUERY_PROJECT" = false ]; then
  usage
fi

if [ "$JSON_MODE" = true ]; then
  tmp_dir=$(mktemp -d)
  trap 'rm -rf "$tmp_dir"' EXIT

  if [ "$QUERY_MCP" = true ]; then
    get_mcp_tools_json >"$tmp_dir/mcp.json"
  fi
  if [ "$QUERY_SYSTEM" = true ]; then
    get_system_binaries_json >"$tmp_dir/system.json"
  fi
  if [ "$QUERY_SHELL" = true ]; then
    get_shell_function_json >"$tmp_dir/shell.json"
  fi
  if [ "$QUERY_PROJECT" = true ]; then
    get_project_scripts_json >"$tmp_dir/project.json"
  fi

  emit_unified_json "$tmp_dir"
  exit 0
fi

if [ "$QUERY_MCP" = true ]; then
  get_mcp_tools_json
fi
if [ "$QUERY_SYSTEM" = true ]; then
  get_system_binaries_json
fi
if [ "$QUERY_SHELL" = true ]; then
  get_shell_function_json
fi
if [ "$QUERY_PROJECT" = true ]; then
  get_project_scripts_json
fi
