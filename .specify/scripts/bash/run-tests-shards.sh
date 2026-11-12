#!/usr/bin/env bash
# run-tests-shards.sh — run the test selection as N concurrent pytest processes.
#
# The host has no pytest-xdist, so `run-tests.sh --workers` always degrades to serial and the
# full suite costs ~11 minutes. This runner shards by TEST MODULE (not by node id: a command
# line of thousands of ids can exceed ARG_MAX) and runs the shards concurrently. The union of
# the shards is the same selection; the merged FAILED list is the same reading.
#
# Usage:
#   run-tests-shards.sh [-n N] [--names-out FILE] [pytest arguments...]
#
#   -n N            shard count (default: min(nproc, module count), capped at 16)
#   --names-out F   write the merged sorted FAILED node-id list to F
#
# side-effects: writes only the --names-out file; every other write is scratch under the
# sanctioned temp root and is removed on success and failure.
# exit-codes: 0 every shard passed; 1 at least one test failed; 2 an argument or environment error

set -uo pipefail

SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUARD_LIB="$SCRIPT_DIR/script-interface.sh"
if [ -f "$GUARD_LIB" ]; then
    # shellcheck source=/dev/null
    . "$GUARD_LIB"
    script_interface_guard define name="$0" \
        usage="[-n N] [--names-out FILE] [pytest arguments...]" \
        effects="runs the pytest selection as N concurrent processes; with --names-out also writes the merged FAILED list to that file; the flags write nothing" \
        codes="0 all shards passed; 1 at least one test failed; 2 an argument or environment error" \
        writes=--names-out \
        -- --names-out -n
    script_interface_guard guard "$@"
fi

SHARDS=""
NAMES_OUT=""
PASSTHRU=()
while [ "$#" -gt 0 ]; do
    case "$1" in
        -n) SHARDS="${2:-}"; shift 2 ;;
        -n*) SHARDS="${1#-n}"; shift ;;
        --names-out) NAMES_OUT="${2:-}"; shift 2 ;;
        --names-out=*) NAMES_OUT="${1#--names-out=}"; shift ;;
        --) shift; PASSTHRU+=("$@"); break ;;
        *) PASSTHRU+=("$1"); shift ;;
    esac
done

PY=""
REPO_VENV="$(CDPATH="" cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd)/.venv/bin/python"
for candidate in "${SPECKIT_PYTHON:-}" "$REPO_VENV" ".venv/bin/python" "/usr/bin/python3" "/usr/local/bin/python3" "python3" "python"; do
    [ -n "$candidate" ] || continue
    if "$candidate" -c "import pytest" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done
if [ -z "$PY" ]; then
    echo "error: no interpreter with pytest found; set SPECKIT_PYTHON" >&2
    exit 2
fi

MODULES="$("$PY" -m pytest --collect-only -q -p no:cacheprovider "${PASSTHRU[@]+"${PASSTHRU[@]}"}" 2>/dev/null \
    | sed 's/::.*//' | grep -E '\.py$' | sort -u)"
if [ -z "$MODULES" ]; then
    echo "error: the selection collected no test modules" >&2
    exit 2
fi
TOTAL_MODULES="$(printf '%s\n' "$MODULES" | wc -l | tr -d ' ')"

if [ -z "$SHARDS" ]; then
    SHARDS="$(nproc 2>/dev/null || echo 4)"
    [ "$SHARDS" -gt 16 ] && SHARDS=16
    [ "$SHARDS" -gt "$TOTAL_MODULES" ] && SHARDS="$TOTAL_MODULES"
fi
case "$SHARDS" in ''|*[!0-9]*) echo "error: -n needs a positive integer" >&2; exit 2 ;; esac
[ "$SHARDS" -ge 1 ] || { echo "error: -n needs a positive integer" >&2; exit 2; }

# Shard scratch lives under the workspace's sanctioned temp root (.specify/.tmp/, gitignored), never
# in bare system temp — same discipline the agent rules apply to agent-created scratch.
REPO_ROOT_FOR_TMP="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_BASE="$REPO_ROOT_FOR_TMP/.specify/.tmp/test-shards"
mkdir -p "$WORK_BASE" || exit 2
WORK="$WORK_BASE/run.$$"
mkdir -p "$WORK" || exit 2
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

# Round-robin the modules so each shard gets a mix of heavy and light files.
idx=0
while IFS= read -r module; do
    bucket=$((idx % SHARDS))
    printf '%s\n' "$module" >> "$WORK/shard.$bucket"
    idx=$((idx + 1))
done <<< "$MODULES"

pids=()
for i in $(seq 0 $((SHARDS - 1))); do
    [ -f "$WORK/shard.$i" ] || continue
    ( mapfile -t files < "$WORK/shard.$i"
      "$PY" -m pytest -q --tb=no -p no:cacheprovider "${files[@]}" > "$WORK/out.$i" 2>&1
      echo "$?" > "$WORK/rc.$i" ) &
    pids+=($!)
done
for pid in "${pids[@]}"; do wait "$pid"; done

status=0
for i in $(seq 0 $((SHARDS - 1))); do
    [ -f "$WORK/rc.$i" ] || continue
    [ "$(cat "$WORK/rc.$i")" -eq 0 ] || status=1
done

grep -h '^FAILED ' "$WORK"/out.* 2>/dev/null | sed 's/^FAILED //; s/ - .*//' | sort -u > "$WORK/failed"
FAILED_COUNT="$(wc -l < "$WORK/failed" | tr -d ' ')"
PASSED_LINE="$(grep -hoE '[0-9]+ passed' "$WORK"/out.* 2>/dev/null | awk '{s+=$1} END {print s+0}')"
echo "shards=$SHARDS modules=$TOTAL_MODULES passed=$PASSED_LINE failed=$FAILED_COUNT"
if [ "$FAILED_COUNT" -gt 0 ]; then
    cat "$WORK/failed"
fi
if [ -n "$NAMES_OUT" ]; then
    mkdir -p "$(dirname -- "$NAMES_OUT")"
    cat "$WORK/failed" > "$NAMES_OUT"
fi
exit "$status"
