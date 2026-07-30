#!/usr/bin/env bash
# Canonical test runner for spec-kit SDD baseline/regression tasks.
# Resolves the pytest interpreter once and fails loudly — pipe-safe, alias-proof.
set -euo pipefail

resolve_python() {
    for candidate in "${SPECKIT_PYTHON:-}" ".venv/bin/python" "python3" "python"; do
        [ -n "$candidate" ] || continue
        if command -v "$candidate" >/dev/null 2>&1 || [ -x "$candidate" ]; then
            if "$candidate" -m pytest --version >/dev/null 2>&1; then
                echo "$candidate"
                return 0
            fi
        fi
    done
    echo "error: no interpreter with pytest found (tried SPECKIT_PYTHON, .venv/bin/python, python3, python)" >&2
    return 1
}

PY="$(resolve_python)"

# --names-out <file>: additionally write the sorted FAILED test-id list to <file>
# so baseline/regression comparisons become a name-level diff (comm -13), not a
# count-level guess. Exit code still reflects pytest's own result.
NAMES_OUT=""
ARGS=()
while [ $# -gt 0 ]; do
    case "$1" in
        --names-out) NAMES_OUT="$2"; shift 2 ;;
        *) ARGS+=("$1"); shift ;;
    esac
done

echo "# test runner: $PY -m pytest ${ARGS[*]:-}" >&2
if [ -n "$NAMES_OUT" ]; then
    set +e
    OUT="$("$PY" -m pytest "${ARGS[@]+"${ARGS[@]}"}")"
    STATUS=$?
    set -e
    printf '%s\n' "$OUT"
    printf '%s\n' "$OUT" | grep "^FAILED" | sed 's/^FAILED //;s/ - .*//' | sort > "$NAMES_OUT" || true
    echo "# failed-name list written: $NAMES_OUT ($(wc -l < "$NAMES_OUT") entries)" >&2
    exit "$STATUS"
fi
exec "$PY" -m pytest "${ARGS[@]+"${ARGS[@]}"}"
