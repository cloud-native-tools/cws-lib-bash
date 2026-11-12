#!/usr/bin/env bash
# Canonical test runner for spec-kit SDD baseline/regression tasks.
# Resolves the pytest interpreter once and fails loudly — pipe-safe, alias-proof.
#
# Execution model (owner: .specify/specs/086-efficient-test-execution/contracts/
# runner-contract-086.contract.md, clauses C-001…C-016; the design rationale and the
# measurements behind it are recorded in that feature's research.md R-1…R-6):
#
#   - The default is process parallelism (-n <effective> --dist load). The suite's cost is
#     subprocess/CPU bound, not latency bound, and the same tree measured 1031 s serial vs
#     202 s parallel (research.md B-1…B-3). A parallel run reports the same failure NAMES as
#     a serial run, which is why --names-out stays the comparison surface.
#   - Serial stays a complete, first-class run — never labelled degraded — through three
#     decided situations: --serial (explicit), a run already inside a parallel worker
#     (${PYTEST_XDIST_WORKER} set, so no second pool is forked), and an interpreter that
#     cannot import the engine (reason=no-xdist).
#   - Tests that are not parallel-safe are declared with the registered `serial` marker; the
#     parallel pass excludes them and a serial pass re-runs them. Both passes compose into ONE
#     failure-name list and ONE exit code, so a declared exception never splits a run.
#   - Two tiers exist and only two (098 tier-selection C-001…C-011): `fast` is the default and
#     excludes tests marked `slow`; `full` (the --full flag) runs every collected test. A caller
#     `-m` owns its selection in either accepted spelling, so the runner never emits a second
#     marker expression next to it (tier=caller). Paths and -k narrow INSIDE the tier and never
#     suppress it. The mode line discloses `tier=` and the measured `excluded_slow=` count; the
#     count is enumerated by the marker itself, never read from a list. When the fast tier's own
#     exclusion empties a non-empty caller selection, the run is a named error (exit 2), not a
#     silent green.
#
# --names-out <file>: additionally write the sorted, de-duplicated FAILED test-id list to
# <file> so baseline/regression comparisons become a name-level diff (comm -13 against the
# recorded baseline), not a count-level guess. The stderr line
#   # failed-name list written: <path> (<n> entries) passes=<k>
# makes an empty list distinguishable from a missing one, and a combined list from a
# single-pass one. Exit code still reflects the passes' own results.
set -euo pipefail


# script-interface: the sourceable guard block (086) lives in script-interface.sh.
# It sits above `source common.sh` and above every write, which is what keeps `--help` free.
# Authority: .specify/shared/definitions/script-interface-definitions.md section 4.
#
# `--pass-through` is this script's honest declaration: every argument that is not
# `--names-out` / a flag is forwarded to pytest, so a token like `-q` is an OPERAND of this
# script rather than a flag of its own. The guard therefore answers `-h`, `--help` and
# `--version` and leaves the rest of the line — including any unknown pytest flag — to
# pytest's own parser, exactly as before (FR-018: the forwarding interface is unchanged).
SCRIPT_INTERFACE_LIB="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/script-interface.sh"
if [ -f "$SCRIPT_INTERFACE_LIB" ]; then
    # shellcheck source=/dev/null
    . "$SCRIPT_INTERFACE_LIB"
    script_interface_guard define name="$0" passthrough \
        usage="[--names-out <file>] [--full] [pytest arguments...]" \
        effects="runs pytest in the caller's tree with the fast tier by default (slow-marked tests excluded; a caller -m owns its selection); with --names-out also writes the sorted FAILED test-id list to that file; the flags write nothing" \
        codes="0 pytest passed; pytest's own exit code otherwise; 2 an unrecognized option, a malformed --workers value, or an empty selection after tier exclusion" \
        writes=--names-out \
        -- --names-out --full
    script_interface_guard guard "$@"
fi

resolve_python() {
    # The repo's declared dev environment is resolved from THIS script's location, not from
    # the caller's cwd: a test case running in a temp dir must still find it.
    local repo_venv
    repo_venv="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)/.venv/bin/python"
    for candidate in "${SPECKIT_PYTHON:-}" "$repo_venv" ".venv/bin/python" "python3" "python"; do
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

# This script is a projected mirror pair (C-34/C-016): the mirror equals this source plus
# the declared projection. Re-project with `sync-mirrors.py --write --only scripts`; never
# hand-edit the mirror.

PY="$(resolve_python)"

NAMES_OUT=""
SERIAL_REQUESTED=0
FULL_REQUESTED=0
WORKERS_FLAG=""
ARGS=()
while [ $# -gt 0 ]; do
    case "$1" in
        --names-out) NAMES_OUT="${2:-}"; shift 2 ;;
        --serial) SERIAL_REQUESTED=1; shift ;;
        --full) FULL_REQUESTED=1; shift ;;
        --workers) WORKERS_FLAG="${2:-}"; shift 2 ;;
        --workers=*) WORKERS_FLAG="${1#--workers=}"; shift ;;
        *) ARGS+=("$1"); shift ;;
    esac
done

# A malformed worker value is a named error, never a silent fallback to one worker.
die_workers_error() {
    local source="$1" value="$2"
    echo "error: $source expects a positive integer or \"auto\", got \"$value\"" >&2
    echo "error: refusing to fall back to one worker silently (a typo would become a slow run that looks healthy)" >&2
    exit 2
}

# Caller-supplied worker switch (C-009): -n N, -nN, -n=N, --numprocesses N, --numprocesses=N.
# A caller-supplied scheduler is guarded the same way: the runner's default `--dist load`
# MUST NOT be appended on top of the caller's own `--dist` (C-009), or the mode line would
# report a scheduler the caller did not choose.
caller_has_workers=0
caller_has_dist=0
CALLER_DIST=""
arg_index=0
for arg in ${ARGS[@]+"${ARGS[@]}"}; do
    case "$arg" in
        --numprocesses|--numprocesses=*|-n|-n*|-n=*) caller_has_workers=1 ;;
        --dist=*) caller_has_dist=1; CALLER_DIST="${arg#--dist=}" ;;
        --dist) caller_has_dist=1; CALLER_DIST="${ARGS[$((arg_index + 1))]:-caller}" ;;
    esac
    arg_index=$((arg_index + 1))
done

# C-003: a caller-supplied marker expression owns the selection. Both accepted spellings are
# detected (`-m <expr>`, `-m=<expr>`); its presence suppresses the tier injection entirely,
# because the caller's single -m must never be rewritten, merged or joined by a second one.
caller_has_m=0
for arg in ${ARGS[@]+"${ARGS[@]}"}; do
    case "$arg" in
        -m|-m=*) caller_has_m=1 ;;
    esac
done

# C-008: validate the chosen worker value, flag first (C-007).
if [ -n "$WORKERS_FLAG" ]; then
    WORKERS_SOURCE="--workers"
    WORKERS_RAW="$WORKERS_FLAG"
elif [ -n "${SPECKIT_TEST_WORKERS:-}" ]; then
    WORKERS_SOURCE="SPECKIT_TEST_WORKERS"
    WORKERS_RAW="$SPECKIT_TEST_WORKERS"
else
    WORKERS_SOURCE=""
    WORKERS_RAW="auto"
fi

if [ "$WORKERS_RAW" = "auto" ]; then
    WORKERS_VERSION="$("$PY" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "")"
    case "$WORKERS_VERSION" in
        3.[0-8])
            # pytest-xdist 3.x requires Python >= 3.9: `auto` would expand to zero
            # workers and abort the whole run, so an old interpreter gets 1.
            WORKERS_N=1
            echo "# test runner: workers=1 ($WORKERS_RAW on Python $WORKERS_VERSION; xdist 3.x needs >= 3.9)" >&2
            ;;
        *)
            WORKERS_N="$WORKERS_RAW"
            ;;
    esac
elif [[ "$WORKERS_RAW" =~ ^[0-9]+$ ]] && [ "$WORKERS_RAW" -gt 0 ]; then
    WORKERS_N="$WORKERS_RAW"
else
    die_workers_error "$WORKERS_SOURCE" "$WORKERS_RAW"
fi

# Mode resolution (data-model.md SM-1). The caller's own -n is checked first because FR-004
# forbids a duplicate worker switch even when the resolved mode is serial.
MODE=""
SERIAL_REASON=""
XDIST_NOTE=""
NO_XDIST=0
if [ "$caller_has_workers" -eq 1 ]; then
    MODE="caller"
elif [ -n "${PYTEST_XDIST_WORKER:-}" ]; then
    # C-005: this process already runs inside a parallel worker; deriving a second pool
    # is the process-explosion failure mode, so run one process instead.
    MODE="serial"
    SERIAL_REASON="nested"
    XDIST_NOTE="PYTEST_XDIST_WORKER=${PYTEST_XDIST_WORKER}"
elif [ "$SERIAL_REQUESTED" -eq 1 ]; then
    MODE="serial"
    SERIAL_REASON="explicit"
elif ! "$PY" -c 'import xdist' >/dev/null 2>&1; then
    # C-006: no engine on this interpreter (e.g. a Python 3.8 downstream). Complete the
    # run serially and say what is missing; never error out and never run nothing.
    MODE="serial"
    SERIAL_REASON="no-xdist"
    NO_XDIST=1
else
    MODE="parallel"
fi

if [ "$MODE" = "parallel" ] && [ "$caller_has_workers" -eq 0 ]; then
    MODE_ARGS=(-n "$WORKERS_N")
    if [ "$caller_has_dist" -eq 0 ]; then
        MODE_ARGS+=(--dist load)
        MODE_NOTE="workers=$WORKERS_N dist=load"
    else
        MODE_NOTE="workers=$WORKERS_N dist=$CALLER_DIST"
    fi
elif [ "$MODE" = "caller" ]; then
    MODE_ARGS=()
    MODE_NOTE="workers=caller"
else
    MODE_ARGS=(-n0)
    MODE_NOTE="reason=$SERIAL_REASON"
fi

if [ "$NO_XDIST" -eq 1 ]; then
    MODE_NOTE="$MODE_NOTE detail=pytest-xdist-not-importable-by-$PY"
fi
if [ "$MODE" = "serial" ] && [ "$SERIAL_REASON" = "nested" ]; then
    MODE_NOTE="$MODE_NOTE detail=$XDIST_NOTE"
fi

# Tier resolution (098 C-001…C-003, data-model E-1). Exactly one of the three values:
# a caller -m wins over --full; otherwise --full wins over the fast default; a caller -m in
# either spelling suppresses the injection entirely (no second marker expression is emitted).
TIER=""
if [ "$caller_has_m" -eq 1 ]; then
    TIER="caller"
elif [ "$FULL_REQUESTED" -eq 1 ]; then
    TIER="full"
fi
if [ -z "$TIER" ]; then
    TIER="fast"
fi

# What the one-pass modes (serial / caller) inject for the fast tier: one marker expression,
# never a rewrite of the caller's own selection.
SINGLE_PASS_ARGS=()
TIER_DISPLAY=""
if [ "$TIER" = "fast" ]; then
    SINGLE_PASS_ARGS=(-m "not slow")
    TIER_DISPLAY='-m "not slow"'
fi

# C-009: the excluded count is measured by marker enumeration over the caller's selection,
# never read from a list. Same construction as the serial exception enumeration: -q/--quiet
# are normalised away so collect-only prints node ids, and every other caller argument is
# forwarded verbatim so paths and -k narrow the count exactly as they narrow the run.
collect_slow_count() {
    local collect_args=()
    local arg out status
    for arg in ${ARGS[@]+"${ARGS[@]}"}; do
        case "$arg" in
            -q|--quiet) ;;
            *) collect_args+=("$arg") ;;
        esac
    done
    set +e
    out="$("$PY" -m pytest --collect-only -q -m slow ${collect_args[@]+"${collect_args[@]}"} 2>/dev/null)"
    status=$?
    set -e
    if [ "$status" -eq 5 ] || [ -z "$out" ]; then
        printf '0\n'
        return 0
    fi
    printf '%s\n' "$out" | grep -cE '::' || true
}

EXCLUDED_SLOW=0
if [ "$TIER" = "fast" ]; then
    EXCLUDED_SLOW="$(collect_slow_count)"
fi

# C-011: the named empty-selection error. It fires only when the fast tier CAUSED the
# emptiness — the enumerated slow count is positive and the tier's own passes collected
# nothing (a single pass exiting 5, or both passes exiting 5). An empty selection the caller
# already asked for keeps pytest's exit 5, exactly as 086 C-012 has it.
fail_on_tier_emptiness() {
    local primary_status="$1" serial_status="$2" passes="$3"
    [ "$TIER" = "fast" ] || return 0
    [ "$EXCLUDED_SLOW" -gt 0 ] || return 0
    [ "$primary_status" -eq 5 ] || return 0
    if [ "$passes" -eq 2 ] && [ "$serial_status" -ne 5 ]; then
        return 0
    fi
    echo "# test runner: error=empty-selection-after-tier-exclusion tier=fast excluded_slow=$EXCLUDED_SLOW" >&2
    exit 2
}

# C-011: the declared serial exceptions, enumerated by the marker itself. The verbosity is
# pinned by rewriting any caller-supplied `-q`/`--quiet` into a no-op: pytest counts
# verbosity occurrences, so an un-normalised `-q` here on top of the caller's (`-qq`) makes
# collect-only print per-file counts (`file.py: 2`) instead of node ids. Node ids are what the
# enumeration needs, and every other caller argument is forwarded verbatim.
collect_serial_members() {
    local collect_args=()
    local arg
    for arg in ${ARGS[@]+"${ARGS[@]}"}; do
        case "$arg" in
            -q|--quiet) ;;
            *) collect_args+=("$arg") ;;
        esac
    done
    "$PY" -m pytest --collect-only -q -m serial ${collect_args[@]+"${collect_args[@]}"} 2>/dev/null \
        | grep -E '::' || true
}

# One pass over the caller's selection. Sets PASS_OUT and PASS_STATUS; the caller decides
# which pass's exit code 5 is normalized (C-012: the serial pass only).
run_pass() {
    set +e
    PASS_OUT="$("$PY" -m pytest "$@" ${ARGS[@]+"${ARGS[@]}"})"
    PASS_STATUS=$?
    set -e
    printf '%s\n' "$PASS_OUT"
}

write_names_out() {
    local k="$1"
    printf '%s\n' "$COMBINED_OUT" \
        | grep "^FAILED" | sed 's/^FAILED //;s/ - .*//' | sort -u > "$NAMES_OUT" || true
    echo "# failed-name list written: $NAMES_OUT ($(wc -l < "$NAMES_OUT" | tr -d ' ') entries) passes=$k" >&2
}

if [ "$MODE" = "serial" ]; then
    echo "# test runner: $PY -m pytest ${MODE_ARGS[*]} ${TIER_DISPLAY} ${ARGS[*]:-}" >&2
    echo "# test runner: mode=serial $MODE_NOTE tier=$TIER excluded_slow=$EXCLUDED_SLOW" >&2
    if [ -n "$NAMES_OUT" ]; then
        run_pass "${MODE_ARGS[@]}" ${SINGLE_PASS_ARGS[@]+"${SINGLE_PASS_ARGS[@]}"}
        COMBINED_OUT="$PASS_OUT"
        STATUS="$PASS_STATUS"
        fail_on_tier_emptiness "$STATUS" 5 1
        write_names_out 1
        exit "$STATUS"
    fi
    if [ "$TIER" != "fast" ]; then
        exec "$PY" -m pytest "${MODE_ARGS[@]}" ${ARGS[@]+"${ARGS[@]}"}
    fi
    set +e
    "$PY" -m pytest "${MODE_ARGS[@]}" "${SINGLE_PASS_ARGS[@]}" ${ARGS[@]+"${ARGS[@]}"}
    STATUS=$?
    set -e
    fail_on_tier_emptiness "$STATUS" 5 1
    exit "$STATUS"
fi

if [ "$MODE" = "caller" ]; then
    # The caller owns the worker count and the scheduling policy; we state the mode and
    # pass their selection through untouched. The tier still applies unless their own -m
    # resolved tier=caller (C-002: no caller -m and no --full is the fast tier, whatever
    # execution shape they chose).
    echo "# test runner: $PY -m pytest ${TIER_DISPLAY} ${ARGS[*]:-}" >&2
    echo "# test runner: mode=parallel workers=caller tier=$TIER excluded_slow=$EXCLUDED_SLOW" >&2
    if [ -n "$NAMES_OUT" ]; then
        run_pass ${SINGLE_PASS_ARGS[@]+"${SINGLE_PASS_ARGS[@]}"}
        COMBINED_OUT="$PASS_OUT"
        STATUS="$PASS_STATUS"
        fail_on_tier_emptiness "$STATUS" 5 1
        write_names_out 1
        exit "$STATUS"
    fi
    if [ "$TIER" != "fast" ]; then
        exec "$PY" -m pytest ${ARGS[@]+"${ARGS[@]}"}
    fi
    set +e
    "$PY" -m pytest "${SINGLE_PASS_ARGS[@]}" ${ARGS[@]+"${ARGS[@]}"}
    STATUS=$?
    set -e
    fail_on_tier_emptiness "$STATUS" 5 1
    exit "$STATUS"
fi

# Parallel mode (C-006/C-010/C-011): marked tests are excluded from the parallel pass and
# re-run in a serial pass; both passes feed one list and one exit code. A caller -m
# (tier=caller) runs as a single pass — composing the serial two-pass model on top of it
# would emit a second marker expression (C-003).
SERIAL_MEMBERS=""
PASSES=1
if [ "$TIER" != "caller" ]; then
    SERIAL_MEMBERS="$(collect_serial_members)"
    if [ -n "$SERIAL_MEMBERS" ]; then
        PASSES=2
        echo "# test runner exceptions: $(printf '%s\n' "$SERIAL_MEMBERS" | wc -l | tr -d ' ') declared serial test(s)" >&2
    fi
fi

# The primary pass's marker expression (C-006): fast composes "not serial and not slow"
# (or "not slow" without serial members); full keeps 086's expressions unchanged. The
# header states the expression the tier actually injects (C-010/E-7) and nothing else.
PRIMARY_EXPR=""
SERIAL_EXPR=""
PRIMARY_DISPLAY=""
if [ "$TIER" = "fast" ]; then
    if [ "$PASSES" -eq 2 ]; then
        PRIMARY_EXPR="not serial and not slow"
        SERIAL_EXPR="serial and not slow"
        PRIMARY_DISPLAY='-m "not serial and not slow"'
    else
        PRIMARY_DISPLAY='-m "not slow"'
    fi
elif [ "$PASSES" -eq 2 ]; then
    PRIMARY_EXPR="not serial"
    SERIAL_EXPR="serial"
fi

echo "# test runner: $PY -m pytest ${MODE_ARGS[*]} ${PRIMARY_DISPLAY} ${ARGS[*]:-}" >&2
echo "# test runner: mode=parallel $MODE_NOTE passes=$PASSES tier=$TIER excluded_slow=$EXCLUDED_SLOW" >&2

if [ -n "$NAMES_OUT" ]; then
    PARALLEL_STATUS=0
    SERIAL_RAW=0
    if [ "$PASSES" -eq 2 ]; then
        run_pass "${MODE_ARGS[@]}" -m "$PRIMARY_EXPR"
    else
        run_pass "${MODE_ARGS[@]}" ${SINGLE_PASS_ARGS[@]+"${SINGLE_PASS_ARGS[@]}"}
    fi
    COMBINED_OUT="$PASS_OUT"
    PARALLEL_STATUS="$PASS_STATUS"
    STATUS="$PASS_STATUS"
    if [ "$PASSES" -eq 2 ]; then
        run_pass -n0 -m "$SERIAL_EXPR"
        COMBINED_OUT="$COMBINED_OUT
$PASS_OUT"
        # C-012: an empty serial pass (pytest exit 5 = nothing collected) is success, and the
        # same "nothing collected" outcome on the parallel pass stays a failure. C-015: the
        # combined code is non-zero iff a pass FAILED — so the parallel outcome is the base
        # and the serial pass can only turn a zero into non-zero, never the other way round.
        SERIAL_RAW="$PASS_STATUS"
        SERIAL_STATUS="$PASS_STATUS"
        [ "$SERIAL_STATUS" -eq 5 ] && SERIAL_STATUS=0
        if [ "$PARALLEL_STATUS" -eq 5 ]; then
            STATUS=5
        elif [ "$SERIAL_STATUS" -ne 0 ]; then
            STATUS="$SERIAL_STATUS"
        else
            STATUS="$PARALLEL_STATUS"
        fi
    fi
    fail_on_tier_emptiness "$PARALLEL_STATUS" "$SERIAL_RAW" "$PASSES"
    write_names_out "$PASSES"
    exit "$STATUS"
fi

if [ "$PASSES" -eq 2 ]; then
    set +e
    "$PY" -m pytest "${MODE_ARGS[@]}" -m "$PRIMARY_EXPR" ${ARGS[@]+"${ARGS[@]}"}
    PARALLEL_STATUS=$?
    set -e
    set +e
    "$PY" -m pytest -n0 -m "$SERIAL_EXPR" ${ARGS[@]+"${ARGS[@]}"}
    SERIAL_STATUS=$?
    set -e
    SERIAL_RAW="$SERIAL_STATUS"
    [ "$SERIAL_STATUS" -eq 5 ] && SERIAL_STATUS=0
    fail_on_tier_emptiness "$PARALLEL_STATUS" "$SERIAL_RAW" 2
    if [ "$SERIAL_STATUS" -ne 0 ]; then
        exit "$SERIAL_STATUS"
    fi
    exit "$PARALLEL_STATUS"
fi

if [ "$TIER" != "fast" ]; then
    exec "$PY" -m pytest "${MODE_ARGS[@]}" ${ARGS[@]+"${ARGS[@]}"}
fi
set +e
"$PY" -m pytest "${MODE_ARGS[@]}" "${SINGLE_PASS_ARGS[@]}" ${ARGS[@]+"${ARGS[@]}"}
STATUS=$?
set -e
fail_on_tier_emptiness "$STATUS" 5 1
exit "$STATUS"
