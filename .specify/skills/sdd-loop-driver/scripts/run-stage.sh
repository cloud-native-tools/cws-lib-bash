#!/usr/bin/env bash
# run-stage.sh — executable detached stage runner for sdd-loop-driver.
#
# Launch it with the documented detach recipe (inside a driver shell):
#   setsid nohup bash run-stage.sh ... > runner.log 2>&1 < /dev/null &
#   # or on macOS without setsid:
#   nohup bash run-stage.sh ... > runner.log 2>&1 < /dev/null &
#   disown
#
# The runner writes the four-piece evidence (PID + start token, atomic status,
# log, heartbeat) and projects runner_pid/cli_pid into the Line Registry.  The
# CLI child is itself nohup'd so a SIGHUP sent to the driver's process group
# cannot terminate the stage.  Read-only with respect to the project tree.
#
# Exit codes: the CLI child's exit code, or 2 for usage errors.

set -u

EXIT_USAGE=2

LINE_ID=""
RUN_ID=""
STAGE=""
REGISTRY_DIR=""
WORKTREE=""
PROMPT=""
STATUS_FILE=""
LOG_FILE=""
HEARTBEAT=""
PID_FILE=""
COMMAND=""
SENTINEL=""
DEADLINE_EPOCH=0
ENGINE=""
ENGINE_PYTHON="python3"
HEARTBEAT_INTERVAL=1

usage() {
  cat <<'EOF'
run-stage.sh — detached stage runner (writes four-piece evidence + registry)

  run-stage.sh --line-id ID --run-id RUN --stage STAGE \
               --registry DIR --command CMD \
               --pid-file P --status-file S --log L --heartbeat H \
               --engine FILE \
               [--worktree DIR] [--prompt FILE] [--sentinel STAGE-DONE] \
               [--deadline-epoch E] [--engine-python PY] \
               [--heartbeat-interval N]

The command's stdout/stderr are appended to --log.  On exit the runner writes
`exit=<rc> at=<epoch> sentinel=<0|1> line= run= stage= event=status` atomically.
EOF
}

die_usage() {
  printf 'run-stage: %s\n' "$*" >&2
  exit "$EXIT_USAGE"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --line-id) [ "$#" -ge 2 ] || die_usage "--line-id needs a value"; LINE_ID="$2"; shift 2 ;;
    --run-id) [ "$#" -ge 2 ] || die_usage "--run-id needs a value"; RUN_ID="$2"; shift 2 ;;
    --stage) [ "$#" -ge 2 ] || die_usage "--stage needs a value"; STAGE="$2"; shift 2 ;;
    --registry) [ "$#" -ge 2 ] || die_usage "--registry needs a value"; REGISTRY_DIR="$2"; shift 2 ;;
    --worktree) [ "$#" -ge 2 ] || die_usage "--worktree needs a value"; WORKTREE="$2"; shift 2 ;;
    --prompt) [ "$#" -ge 2 ] || die_usage "--prompt needs a value"; PROMPT="$2"; shift 2 ;;
    --pid-file) [ "$#" -ge 2 ] || die_usage "--pid-file needs a value"; PID_FILE="$2"; shift 2 ;;
    --status-file) [ "$#" -ge 2 ] || die_usage "--status-file needs a value"; STATUS_FILE="$2"; shift 2 ;;
    --log) [ "$#" -ge 2 ] || die_usage "--log needs a value"; LOG_FILE="$2"; shift 2 ;;
    --heartbeat) [ "$#" -ge 2 ] || die_usage "--heartbeat needs a value"; HEARTBEAT="$2"; shift 2 ;;
    --command) [ "$#" -ge 2 ] || die_usage "--command needs a value"; COMMAND="$2"; shift 2 ;;
    --sentinel) [ "$#" -ge 2 ] || die_usage "--sentinel needs a value"; SENTINEL="$2"; shift 2 ;;
    --deadline-epoch) [ "$#" -ge 2 ] || die_usage "--deadline-epoch needs a value"; DEADLINE_EPOCH="$2"; shift 2 ;;
    --engine) [ "$#" -ge 2 ] || die_usage "--engine needs a value"; ENGINE="$2"; shift 2 ;;
    --engine-python) [ "$#" -ge 2 ] || die_usage "--engine-python needs a value"; ENGINE_PYTHON="$2"; shift 2 ;;
    --heartbeat-interval) [ "$#" -ge 2 ] || die_usage "--heartbeat-interval needs a value"; HEARTBEAT_INTERVAL="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die_usage "unknown argument: $1" ;;
  esac
done

for required in LINE_ID RUN_ID STAGE REGISTRY_DIR COMMAND PID_FILE STATUS_FILE LOG_FILE HEARTBEAT ENGINE; do
  eval "value=\${$required}"
  [ -n "$value" ] || die_usage "--$(printf '%s' "$required" | tr '[:upper:]_' '[:lower:]-') is required"
done

now_epoch() { date +%s; }

process_start_token() {
  local pid="$1" token=""
  if [ -r "/proc/$pid/stat" ]; then
    token=$(awk '{print $22}' "/proc/$pid/stat" 2>/dev/null)
  else
    token=$(ps -p "$pid" -o lstart= 2>/dev/null | tr '\n' ' ' \
      | tr -s '[:space:]' ' ' | sed 's/^ //; s/ $//')
  fi
  printf '%s' "$token"
}

process_stat_state() {
  local pid="$1" stat=""
  if [ -r "/proc/$pid/stat" ]; then
    stat=$(awk '{print $3}' "/proc/$pid/stat" 2>/dev/null)
  else
    stat=$(ps -p "$pid" -o stat= 2>/dev/null | awk 'NR==1{print $1}')
  fi
  printf '%s' "$stat"
}

write_atomic() {
  local target="$1" payload="$2"
  printf '%s\n' "$payload" > "$target.tmp.$$" && mv "$target.tmp.$$" "$target"
}

mkdir -p "$(dirname "$PID_FILE")" "$(dirname "$STATUS_FILE")" \
         "$(dirname "$LOG_FILE")" "$(dirname "$HEARTBEAT")" || exit "$EXIT_USAGE"
[ -n "$WORKTREE" ] || WORKTREE="$PWD"
if [ -n "$ENGINE" ] && [ ! -f "$ENGINE" ]; then
  die_usage "engine not found: $ENGINE"
fi

RUNNER_PID=$$
RUNNER_TOKEN=$(process_start_token "$RUNNER_PID")
printf 'at=%s line=%s run=%s stage=%s event=heartbeat\n' "$(now_epoch)" \
  "$LINE_ID" "$RUN_ID" "$STAGE" > "$HEARTBEAT"

# The CLI child ignores SIGHUP as well; a driver-group kill must not reach it.
nohup bash -c "$COMMAND" >> "$LOG_FILE" 2>&1 < /dev/null &
CLI_PID=$!
CLI_TOKEN=$(process_start_token "$CLI_PID")
printf 'pid=%s start=%s at=%s line=%s run=%s stage=%s event=pid\n' \
  "$CLI_PID" "$CLI_TOKEN" "$(now_epoch)" "$LINE_ID" "$RUN_ID" "$STAGE" > "$PID_FILE"

if [ -n "$ENGINE" ]; then
  update_out="${STATUS_FILE}.registry-update.out"
  if ! SPECIFY_LINE_REGISTRY_DIR="$REGISTRY_DIR" \
       "$ENGINE_PYTHON" "$ENGINE" --action update \
         --line-id "$LINE_ID" --stage "$STAGE" \
         --runner-pid "$RUNNER_PID" --runner-start-token "$RUNNER_TOKEN" \
         --cli-pid "$CLI_PID" --cli-start-token "$CLI_TOKEN" \
         --status-path "$STATUS_FILE" --log-path "$LOG_FILE" \
         --heartbeat-path "$HEARTBEAT" \
         --last-event u2-dispatch > "$update_out" 2>&1; then
    {
      printf 'ANOMALY: registry-update-failed\n'
      cat "$update_out" 2>/dev/null
    } >> "$LOG_FILE"
    kill "$CLI_PID" 2>/dev/null || true
    wait "$CLI_PID" 2>/dev/null || true
    write_atomic "$STATUS_FILE" \
      "exit=4 at=$(now_epoch) sentinel=0 line=$LINE_ID run=$RUN_ID stage=$STAGE event=status"
    exit 4
  fi
  rm -f "$update_out"
fi

(
  while kill -0 "$RUNNER_PID" 2>/dev/null; do
    write_atomic "$HEARTBEAT" \
      "at=$(now_epoch) line=$LINE_ID run=$RUN_ID stage=$STAGE event=heartbeat"
    sleep "$HEARTBEAT_INTERVAL"
  done
) &
HEARTBEAT_PID=$!

rc=0
while kill -0 "$CLI_PID" 2>/dev/null; do
  case "$(process_stat_state "$CLI_PID")" in
    Z*) break ;;
  esac
  if [ "$DEADLINE_EPOCH" -gt 0 ] && [ "$(now_epoch)" -ge "$DEADLINE_EPOCH" ]; then
    kill "$CLI_PID" 2>/dev/null || true
    rc=124
    break
  fi
  sleep 0.2
done
if [ "$rc" -eq 0 ]; then
  wait "$CLI_PID"
  rc=$?
else
  wait "$CLI_PID" 2>/dev/null || true
fi
kill "$HEARTBEAT_PID" 2>/dev/null || true
wait "$HEARTBEAT_PID" 2>/dev/null || true

last=""
if [ -f "$LOG_FILE" ]; then
  last=$(tail -n 50 "$LOG_FILE" 2>/dev/null | awk 'NF { value=$0 } END { print value }' \
    | tr -d '\r' | sed 's/[[:space:]]*$//')
fi
sentinel_seen=0
if [ -n "$SENTINEL" ] && [ "$last" = "$SENTINEL" ]; then
  sentinel_seen=1
fi
write_atomic "$STATUS_FILE" \
  "exit=$rc at=$(now_epoch) sentinel=$sentinel_seen line=$LINE_ID run=$RUN_ID stage=$STAGE event=status"
exit "$rc"
