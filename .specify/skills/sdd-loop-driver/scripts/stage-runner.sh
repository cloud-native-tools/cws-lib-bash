#!/usr/bin/env bash
# stage-runner.sh — parameterized stage runner for sdd-loop-driver.
#
# Runs one stage CLI under the stream-json pipeline by default: the raw event
# stream is preserved, a compact live log is derived incrementally, and the
# four-piece evidence set (pid / status / log / heartbeat) plus a runner log is
# written. The runner never detaches itself; the dispatch recipe supplies nohup
# with stdin </dev/null and stdout/stderr redirection.
#
# Degradation is explicit: an auto probe that finds no --output-format support
# records progress=degraded reason=cli-lacks-stream; a derivation failure first
# recovers the terminal result from the raw stream, then falls back to the raw
# text, and otherwise leaves sentinel=0 (INCOMPLETE, never a fabricated DONE).
#
# Exit code equals the CLI exit code. Python 3 (stdlib only) is required for
# the derivation step.

set -u

usage() {
  cat <<'EOF'
stage-runner.sh — run one stage CLI with raw stream evidence and a live log

Usage:
  stage-runner.sh --cli PATH --cli-args "ARGS" --project-dir DIR \
                  --prompt-file FILE --sentinel STAGE-DONE --line LINE \
                  --stage STAGE --state-dir DIR [--mode auto|stream|buffered] \
                  [--detached yes|no]

Writes pid-<line>-<stage>, status-<line>-<stage>, log-<line>-<stage>.log,
heartbeat-<line>-<stage>.log and runner-log-<line>-<stage>.log under
--state-dir. Stream mode also writes raw-<line>-<stage>.jsonl and the receive
timestamp sidecar raw-<line>-<stage>.ts.jsonl.

status fields: exit, at, sentinel, progress=stream|buffered|degraded,
detached=yes|no. --detached no also writes unprotected=true and a reason.

Exit code equals the CLI exit code. The runner does NOT detach itself; launch
it under nohup with stdin </dev/null and output redirection (dispatch recipe).
EOF
}

die_usage() {
  printf 'stage-runner: %s\n' "$*" >&2
  usage >&2
  exit 2
}

CLI=""
CLI_ARGS=""
PROJECT_DIR="."
PROMPT_FILE="/dev/null"
SENTINEL=""
LINE="line"
STAGE="stage"
STATE_DIR=""
MODE="auto"
DETACHED="yes"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --cli) [ "$#" -ge 2 ] || die_usage "--cli needs a value"; CLI="$2"; shift 2 ;;
    --cli-args) [ "$#" -ge 2 ] || die_usage "--cli-args needs a value"; CLI_ARGS="$2"; shift 2 ;;
    --project-dir) [ "$#" -ge 2 ] || die_usage "--project-dir needs a value"; PROJECT_DIR="$2"; shift 2 ;;
    --prompt-file) [ "$#" -ge 2 ] || die_usage "--prompt-file needs a value"; PROMPT_FILE="$2"; shift 2 ;;
    --sentinel) [ "$#" -ge 2 ] || die_usage "--sentinel needs a value"; SENTINEL="$2"; shift 2 ;;
    --line) [ "$#" -ge 2 ] || die_usage "--line needs a value"; LINE="$2"; shift 2 ;;
    --stage) [ "$#" -ge 2 ] || die_usage "--stage needs a value"; STAGE="$2"; shift 2 ;;
    --state-dir) [ "$#" -ge 2 ] || die_usage "--state-dir needs a value"; STATE_DIR="$2"; shift 2 ;;
    --mode) [ "$#" -ge 2 ] || die_usage "--mode needs a value"; MODE="$2"; shift 2 ;;
    --detached) [ "$#" -ge 2 ] || die_usage "--detached needs a value"; DETACHED="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die_usage "unknown argument: $1" ;;
  esac
done

[ -n "$CLI" ] || die_usage "--cli is required"
[ -n "$STATE_DIR" ] || die_usage "--state-dir is required"
[ -n "$SENTINEL" ] || die_usage "--sentinel is required"
case "$MODE" in auto|stream|buffered) ;; *) die_usage "--mode must be auto|stream|buffered" ;; esac
case "$DETACHED" in yes|no) ;; *) die_usage "--detached must be yes|no" ;; esac

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
DERIVE="$SCRIPT_DIR/derive-live-log.py"
mkdir -p "$STATE_DIR"

pidf="$STATE_DIR/pid-$LINE-$STAGE"
statusf="$STATE_DIR/status-$LINE-$STAGE"
live="$STATE_DIR/log-$LINE-$STAGE.log"
hb="$STATE_DIR/heartbeat-$LINE-$STAGE.log"
raw="$STATE_DIR/raw-$LINE-$STAGE.jsonl"
tsfile="$STATE_DIR/raw-$LINE-$STAGE.ts.jsonl"
runnerlog="$STATE_DIR/runner-log-$LINE-$STAGE.log"

: > "$runnerlog"
: > "$live"

now_epoch() { date +%s; }

atomic_write() {
  local tmp="$1.tmp.$$"
  printf '%s\n' "$2" > "$tmp" && mv "$tmp" "$1"
}

runner_pid=$$
start_token=""
if [ -r "/proc/$runner_pid/stat" ]; then
  start_token=$(awk '{print $22}' "/proc/$runner_pid/stat" 2>/dev/null || true)
else
  start_token=$(ps -p "$runner_pid" -o lstart= 2>/dev/null | tr '\n' ' ' \
    | tr -s '[:space:]' ' ' | sed 's/^ //; s/ $//')
fi
atomic_write "$pidf" "pid=$runner_pid start=$start_token at=$(now_epoch) line=$LINE stage=$STAGE event=pid"
atomic_write "$hb" "at=$(now_epoch) line=$LINE stage=$STAGE event=heartbeat"

( while kill -0 "$runner_pid" 2>/dev/null; do
    atomic_write "$hb" "at=$(now_epoch) line=$LINE stage=$STAGE event=heartbeat"
    sleep 30
  done ) >/dev/null 2>&1 &
hb_pid=$!
disown "$hb_pid" 2>/dev/null || true

split_args() {
  local text="$1" current="" quote="" char index=0 out=()
  while [ "$index" -lt "${#text}" ]; do
    char="${text:$index:1}"
    if [ -n "$quote" ]; then
      if [ "$char" = "$quote" ]; then quote=""; else current="$current$char"; fi
    else
      case "$char" in
        "'"|'"') quote="$char" ;;
        ' '|$'\t') if [ -n "$current" ]; then out+=("$current"); current=""; fi ;;
        *) current="$current$char" ;;
      esac
    fi
    index=$((index + 1))
  done
  [ -n "$current" ] && out+=("$current")
  printf '%s\n' "${out[@]}"
}

ARGS=()
if [ -n "$CLI_ARGS" ]; then
  while IFS= read -r arg; do ARGS+=("$arg"); done < <(split_args "$CLI_ARGS")
fi

progress="stream"
reason=""
effective_mode="$MODE"
if [ "$effective_mode" = "auto" ]; then
  if "$CLI" --help 2>&1 | grep -q -- '--output-format'; then
    effective_mode="stream"
  else
    effective_mode="buffered"
    progress="degraded"
    reason="cli-lacks-stream"
  fi
elif [ "$effective_mode" = "buffered" ]; then
  progress="buffered"
fi

last_nonempty() {
  local file="$1"
  [ -f "$file" ] || { printf ''; return 0; }
  tail -n 50 "$file" 2>/dev/null | awk 'NF { last=$0 } END { print last }' \
    | tr -d '\r' | sed 's/[[:space:]]*$//'
}

cd_ok=1
cd "$PROJECT_DIR" 2>/dev/null || {
  cd_ok=0
  rc=127
  progress="degraded"
  reason="project-dir-missing"
}

rc=0
if [ "$cd_ok" -eq 0 ]; then
  :
elif [ "$effective_mode" = "stream" ]; then
  : > "$raw"
  : > "$tsfile"
  "$CLI" "${ARGS[@]+"${ARGS[@]}"}" --output-format stream-json < "$PROMPT_FILE" \
    2>> "$runnerlog" | \
  while IFS= read -r event_line || [ -n "$event_line" ]; do
    seq=$((${seq:-0} + 1))
    {
      printf '%s\n' "$event_line" >> "$raw"
      printf '{"seq":%d,"at":%s}\n' "$seq" "$(now_epoch)" >> "$tsfile"
    }
    printf '%s\n' "$event_line"
  done | \
  "/usr/bin/env" python3 "$DERIVE" --out "$live"
  pipe_status=("${PIPESTATUS[@]}")
  rc=${pipe_status[0]}
  derive_rc=${pipe_status[2]}

  if [ "$derive_rc" -ne 0 ]; then
    if recovered=$(python3 "$DERIVE" --events "$raw" --finish 2>> "$runnerlog") \
       && [ -n "$recovered" ]; then
      printf '%s\n' "$recovered" >> "$live"
      progress="degraded"
      reason="derivation-recovered"
    else
      raw_last=$(last_nonempty "$raw")
      if [ "$raw_last" = "$SENTINEL" ]; then
        cp "$raw" "$live"
        progress="degraded"
        reason="buffered-fallback"
      else
        progress="degraded"
        reason="derivation-failed"
      fi
    fi
  fi

  if [ "$(last_nonempty "$live")" != "$SENTINEL" ]; then
    live_last=$(last_nonempty "$live")
    raw_last=$(last_nonempty "$raw")
    if [ -z "$live_last" ] && [ "$raw_last" = "$SENTINEL" ]; then
      cp "$raw" "$live"
      progress="degraded"
      reason="buffered-fallback"
    fi
  fi
else
  "$CLI" "${ARGS[@]+"${ARGS[@]}"}" < "$PROMPT_FILE" > "$live" 2>> "$runnerlog"
  rc=$?
fi

sent=0
[ "$(last_nonempty "$live")" = "$SENTINEL" ] && sent=1

kill "$hb_pid" 2>/dev/null || true
unprotected=""
if [ "$DETACHED" = "no" ]; then
  unprotected=" unprotected=true unprotected_reason=started-without-nohup-detachment"
fi
reason_field=""
[ -n "$reason" ] && reason_field=" reason=$reason"
atomic_write "$statusf" "exit=$rc at=$(now_epoch) sentinel=$sent line=$LINE stage=$STAGE event=status progress=$progress$reason_field detached=$DETACHED$unprotected"

exit "$rc"
