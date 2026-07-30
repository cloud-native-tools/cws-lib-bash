#!/usr/bin/env bash

# collect-history.sh — thin wrapper around history-utils.py for /speckit.history.
# Resolves the repo root and forwards all arguments to the Python engine, which
# locates / extracts / tracks the current tool's conversation history.
#
# Usage:
#   collect-history.sh --json                         # default action: locate
#   collect-history.sh --action extract --tool claude --json
#   collect-history.sh --action manifest-update --tool claude --sids-file <f> --json

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

# Resolve repo root (git first, then by script location)
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

# Prefer the runtime python copy under .specify, fall back to the source tree
SPECIFY_PY_DIR="$ROOT_DIR/.specify/scripts/python"
if [ -f "$SPECIFY_PY_DIR/history-utils.py" ]; then
  PY_SCRIPTS_DIR="$SPECIFY_PY_DIR"
else
  PY_SCRIPTS_DIR="$ROOT_DIR/scripts/python"
fi

HISTORY_UTILS_SCRIPT="$PY_SCRIPTS_DIR/history-utils.py"

if [ ! -f "$HISTORY_UTILS_SCRIPT" ]; then
  echo "history-utils.py not found (looked in $PY_SCRIPTS_DIR)" >&2
  exit 1
fi

# Pick a python interpreter
PY_BIN="${PYTHON:-python3}"
command -v "$PY_BIN" >/dev/null 2>&1 || PY_BIN=python

# Always pin the project root so the engine resolves paths deterministically,
# unless the caller already specified one.
case " $* " in
  *" --project "*) PROJECT_ARGS=() ;;
  *)               PROJECT_ARGS=(--project "$ROOT_DIR") ;;
esac

exec "$PY_BIN" "$HISTORY_UTILS_SCRIPT" "${PROJECT_ARGS[@]}" "$@"
