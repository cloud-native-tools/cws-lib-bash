#!/usr/bin/env bash
# watch-target.sh — unified, read-only watch primitive for sdd-loop-driver.
#
# One call blocks for a bounded window, samples signals cheaply, and returns as
# soon as a terminal verdict is reached. Window expiry returns RUNNING, never
# TIMEOUT; only the stage deadline produces TIMEOUT.
#
# Signals are positive evidence only:
#   completion  = exact sentinel last line (necessary) or exit record rc=0
#   liveness    = pid file + kill -0 (plus /proc start-ticks / zombie check)
#   progress    = log tail; heartbeat proves the runner shell is alive
# Absence (process gone, pgrep zero matches, quiet log) is never completion.
#
# The watcher's watch path NEVER kills processes, writes project state, or
# mutates the tree; --self-test only cleans up its own fixtures.

set -u

SELF="$0"

EXIT_DONE=0
EXIT_RUNNING=10
EXIT_ANOMALY=11
EXIT_FAILED=12
EXIT_DEAD=13
EXIT_TIMEOUT=14
EXIT_INCOMPLETE=15
EXIT_NO_SIGNAL=16
EXIT_USAGE=2

usage() {
  cat <<'EOF'
watch-target.sh — bounded long-poll watcher (read-only)

Single target:
  watch-target.sh --label L --pid-file P --status-file S --log G \
                  [--sentinel STAGE-DONE] [--heartbeat H] [--raw-stream PATH] \
                  [--hook-fifo F | --hook-done F] \
                  [--line-id ID --run-id RUN] [--stage STAGE] [--meta FILE] \
                  [--registry DIR] [--iter TOKEN] \
                  [--lease-ttl N --lease-renew-cmd CMD --lease-renew-interval N] \

                  [--deadline-epoch E | --timeout T] \
                  [--window N] [--interval N] [--start-grace N] \
                  [--deadline-grace N] [--heartbeat-max-age N] [--once] [--verbose]

--iter TOKEN tags THIS invocation and is echoed as iter= on WATCH and EVIDENCE
(default: na). A multi-window watch repeats the same command by design, and
hosts such as Qoder reject byte-identical tool calls as a repeated-call loop;
every window MUST carry a literal, different token such as "<run>-w07". Write
the token literally: substitutions like $(date +%s) or $$ are expanded only
after the host has compared the command text, so they do not change the
signature. The token never affects any verdict or exit code.

--raw-stream PATH reports stream=na|absent|growing|idle on the WATCH line and
raw=<path> bytes=<n> on EVIDENCE; raw growth is visibility only and never
participates in any verdict. The sentinel is still read from --log only.

Manifest (one target per line: label|pid|status|log|sentinel|heartbeat|deadline):
  watch-target.sh --manifest FILE [--window N] [--interval N] [--start-grace N]

  Use '-' for an empty manifest field. Paths must not contain '|'.
  In manifest mode, every line is reported and the exit code is the highest
  severity among terminal verdicts.

Verdicts / exit codes:
  0 DONE           sentinel or clean exit record; still requires independent U4 check
  10 RUNNING       no terminal signal; re-enter another window immediately
  11 ANOMALY       final line is ANOMALY: ... (process ended / exit record present)
  12 FAILED        exit record has non-zero rc
  13 DEAD          pid recorded but process dead, zombie, or pid reused
  14 TIMEOUT       stage deadline reached (the only timeout source)
  15 INCOMPLETE    exit rc=0 but sentinel missing (fake-done candidate)
  16 NO_SIGNAL     no pid/status within start grace
  2 USAGE          bad arguments

Defaults: window=200s, interval=3s, start-grace=30s, deadline-grace=120s,
heartbeat-max-age=120s. --deadline-grace N keeps sampling for N seconds after
the stage deadline; a late status/sentinel reclassifies to DONE/FAILED before
TIMEOUT. TIMEOUT is a budget verdict, not a death certificate: a live
pid/heartbeat must be rechecked with --once before any stop decision.
The default window is <= ttl/3 for the default 600s driver lease. Pass
--lease-ttl N to enforce the window <= N/3 rule (it fails when the window is
larger and no --lease-renew-cmd is given); --lease-renew-cmd refreshes the
lease heartbeat inside the window (--lease-renew-interval defaults to 60s).
With --registry DIR (or SPECIFY_LINE_REGISTRY_DIR), the watcher consumes only
the PID registered for --line-id and verifies its start token (Linux start
ticks, macOS `ps -p <pid> -o lstart=`) plus branch when registered.
Set the host tool timeout to window + deadline-grace + 30s so the watcher can
return first; with the defaults that is 200 + 120 + 30 = 350s.
--timeout T is relative to THIS invocation; for multi-window stages pass
--deadline-epoch (absolute stage deadline) instead, or each window resets it.
The watcher must run as the same identity as the runner (kill -0 permission).
--hook-fifo F: block on F for each interval instead of sleep; a line is an
              early completion signal only (hook=observed), never a verdict.
--hook-done F: a non-empty F is a persistent early signal (same rule).
Both are supplementary: sentinel/status/exit-record remain authoritative.
--self-test runs zero-match / dead / zombie / pid-reuse / fake-done /
anomaly / exit-code / timeout / hook / manifest / registry-identity / lease-window /
iteration-token regression cases.

EOF
}

die_usage() {
  printf 'watch-target: %s\n' "$*" >&2
  usage >&2
  exit "$EXIT_USAGE"
}

is_uint() {
  case "${1:-}" in
    ''|*[!0-9]*) return 1 ;;
    *) return 0 ;;
  esac
}

now_epoch() { date +%s; }

file_mtime() {
  stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0
}

one_line() {
  printf '%s' "${1:-}" | tr '\n\r' '  ' | cut -c1-300
}

LABEL="line"
PID_FILE=""
STATUS_FILE=""
LOG_FILE=""
SENTINEL=""
HEARTBEAT=""
DEADLINE_EPOCH=0
TIMEOUT=""
WINDOW=200
INTERVAL=3
START_GRACE=30
DEADLINE_GRACE=120
HEARTBEAT_MAX_AGE=120
HOOK_FIFO=""
HOOK_DONE=""
HOOK_EVENT_SEEN=0
ONCE=0
MANIFEST=""
VERBOSE=0
SELF_TEST=0
START_EPOCH=0
LINE_ID=""
RUN_ID=""
STAGE=""
META=""
ITER=""
REGISTRY_DIR="${SPECIFY_LINE_REGISTRY_DIR:-}"
LEASE_TTL=""
LEASE_RENEW_CMD=""
LEASE_RENEW_INTERVAL=60
LAST_LEASE_RENEW=0
RAW_STREAM=""
RAW_PREV_SIZE=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --label) [ "$#" -ge 2 ] || die_usage "--label needs a value"; LABEL="$2"; shift 2 ;;
    --pid-file) [ "$#" -ge 2 ] || die_usage "--pid-file needs a value"; PID_FILE="$2"; shift 2 ;;
    --status-file) [ "$#" -ge 2 ] || die_usage "--status-file needs a value"; STATUS_FILE="$2"; shift 2 ;;
    --log) [ "$#" -ge 2 ] || die_usage "--log needs a value"; LOG_FILE="$2"; shift 2 ;;
    --sentinel) [ "$#" -ge 2 ] || die_usage "--sentinel needs a value"; SENTINEL="$2"; shift 2 ;;
    --heartbeat) [ "$#" -ge 2 ] || die_usage "--heartbeat needs a value"; HEARTBEAT="$2"; shift 2 ;;
    --raw-stream) [ "$#" -ge 2 ] || die_usage "--raw-stream needs a value"; RAW_STREAM="$2"; shift 2 ;;
    --hook-fifo) [ "$#" -ge 2 ] || die_usage "--hook-fifo needs a value"; HOOK_FIFO="$2"; shift 2 ;;
    --hook-done) [ "$#" -ge 2 ] || die_usage "--hook-done needs a value"; HOOK_DONE="$2"; shift 2 ;;

    --deadline-epoch) [ "$#" -ge 2 ] || die_usage "--deadline-epoch needs a value"; DEADLINE_EPOCH="$2"; shift 2 ;;
    --timeout) [ "$#" -ge 2 ] || die_usage "--timeout needs a value"; TIMEOUT="$2"; shift 2 ;;
    --window) [ "$#" -ge 2 ] || die_usage "--window needs a value"; WINDOW="$2"; shift 2 ;;
    --interval) [ "$#" -ge 2 ] || die_usage "--interval needs a value"; INTERVAL="$2"; shift 2 ;;
    --start-grace) [ "$#" -ge 2 ] || die_usage "--start-grace needs a value"; START_GRACE="$2"; shift 2 ;;
    --deadline-grace) [ "$#" -ge 2 ] || die_usage "--deadline-grace needs a value"; DEADLINE_GRACE="$2"; shift 2 ;;
    --heartbeat-max-age) [ "$#" -ge 2 ] || die_usage "--heartbeat-max-age needs a value"; HEARTBEAT_MAX_AGE="$2"; shift 2 ;;
    --manifest) [ "$#" -ge 2 ] || die_usage "--manifest needs a value"; MANIFEST="$2"; shift 2 ;;
    --line-id) [ "$#" -ge 2 ] || die_usage "--line-id needs a value"; LINE_ID="$2"; shift 2 ;;
    --run-id) [ "$#" -ge 2 ] || die_usage "--run-id needs a value"; RUN_ID="$2"; shift 2 ;;
    --stage) [ "$#" -ge 2 ] || die_usage "--stage needs a value"; STAGE="$2"; shift 2 ;;
    --meta) [ "$#" -ge 2 ] || die_usage "--meta needs a value"; META="$2"; shift 2 ;;
    --iter) [ "$#" -ge 2 ] || die_usage "--iter needs a value"; ITER="$2"; shift 2 ;;
    --registry) [ "$#" -ge 2 ] || die_usage "--registry needs a value"; REGISTRY_DIR="$2"; shift 2 ;;
    --lease-ttl) [ "$#" -ge 2 ] || die_usage "--lease-ttl needs a value"; LEASE_TTL="$2"; shift 2 ;;
    --lease-renew-cmd) [ "$#" -ge 2 ] || die_usage "--lease-renew-cmd needs a value"; LEASE_RENEW_CMD="$2"; shift 2 ;;
    --lease-renew-interval) [ "$#" -ge 2 ] || die_usage "--lease-renew-interval needs a value"; LEASE_RENEW_INTERVAL="$2"; shift 2 ;;
    --once) ONCE=1; shift ;;
    --verbose) VERBOSE=1; shift ;;
    --self-test) SELF_TEST=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die_usage "unknown argument: $1" ;;
  esac
done

for name in WINDOW INTERVAL START_GRACE DEADLINE_GRACE HEARTBEAT_MAX_AGE LEASE_RENEW_INTERVAL; do
  value="${!name}"
  is_uint "$value" || die_usage "$name must be a non-negative integer, got '$value'"
done
if [ -n "$LINE_ID" ] || [ -n "$RUN_ID" ]; then
  [ -n "$LINE_ID" ] && [ -n "$RUN_ID" ] || die_usage "--line-id and --run-id must be provided together"
fi
if [ -n "$REGISTRY_DIR" ] && [ -z "$LINE_ID" ]; then
  die_usage "--registry requires --line-id (registry identity is line-scoped)"
fi
[ "$INTERVAL" -gt 0 ] || die_usage "--interval must be > 0"
if [ -n "$LEASE_TTL" ]; then
  is_uint "$LEASE_TTL" && [ "$LEASE_TTL" -gt 0 ] || die_usage "--lease-ttl must be a positive integer"
  lease_max=$((LEASE_TTL / 3))
  [ "$lease_max" -gt 0 ] || lease_max=1
  if [ -z "$LEASE_RENEW_CMD" ] && [ "$WINDOW" -gt "$lease_max" ]; then
    die_usage "window ${WINDOW}s exceeds lease ttl/3 (${lease_max}s); pass --window <= ${lease_max} or --lease-renew-cmd"
  fi
fi
if [ -n "$MANIFEST" ] && { [ -n "$HOOK_FIFO" ] || [ -n "$HOOK_DONE" ]; }; then
  die_usage "hook flags are single-target only"
fi

if [ -n "$TIMEOUT" ]; then
  is_uint "$TIMEOUT" || die_usage "--timeout must be a non-negative integer"
  [ "$DEADLINE_EPOCH" -eq 0 ] || die_usage "use either --timeout or --deadline-epoch, not both"
fi
is_uint "$DEADLINE_EPOCH" || die_usage "--deadline-epoch must be a non-negative integer"

P_PID=""
P_START=""
P_CLASS=""
P_PRESENT=0
S_CLASS=""
M_CLASS=""
M_EXISTS=0
M_SENT=""
H_CLASS=""
HB_EXISTS=0
CC=""

classify_pair() {
  local carrier_line="$1" carrier_run="$2"
  if [ -z "$LINE_ID" ] && [ -z "$RUN_ID" ]; then
    CC="legacy"; return 0
  fi
  if [ -z "$carrier_line" ] || [ -z "$carrier_run" ]; then
    CC="unattributed"; return 0
  fi
  if [ "$carrier_line" != "$LINE_ID" ]; then
    CC="foreign"; return 0
  fi
  if [ "$carrier_run" != "$RUN_ID" ]; then
    CC="stale-run"; return 0
  fi
  CC="own"
}

line_field_of() {
  printf '%s' "$1" | sed -n 's/.*[[:space:]]line=\([^[:space:]]*\).*/\1/p' | head -n 1
}

run_field_of() {
  printf '%s' "$1" | sed -n 's/.*[[:space:]]run=\([^[:space:]]*\).*/\1/p' | head -n 1
}

json_field() {
  printf '%s' "$1" | sed -n "s/.*\"$2\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" | head -n 1
}

read_meta_file() {
  local f="$1" ml=""
  M_CLASS=""; M_EXISTS=0; M_SENT=""
  [ -n "$f" ] && [ -f "$f" ] || return 0
  M_EXISTS=1
  ml=$(tail -n 20 "$f" 2>/dev/null | awk 'NF { last=$0 } END { print last }')
  [ -n "$ml" ] || return 0
  classify_pair "$(json_field "$ml" line_id)" "$(json_field "$ml" run_id)"
  M_CLASS="$CC"
  M_SENT=$(printf '%s' "$ml" | sed -n 's/.*"sentinel_seen"[[:space:]]*:[[:space:]]*\([01]\).*/\1/p')
}

read_heartbeat_envelope() {
  local f="$1" hl=""
  H_CLASS=""; HB_EXISTS=0
  [ -n "$f" ] && [ -f "$f" ] || return 0
  HB_EXISTS=1
  hl=$(tail -n 5 "$f" 2>/dev/null | awk 'NF { last=$0 } END { print last }')
  classify_pair "$(line_field_of "$hl")" "$(run_field_of "$hl")"
  H_CLASS="$CC"
}

REG_STATE="off"
REG_RUNNER_PID=""
REG_RUNNER_START=""
REG_CLI_PID=""
REG_CLI_START=""
REG_WORKTREE=""
REG_BRANCH=""

read_registry_entry() {
  REG_STATE="off"; REG_RUNNER_PID=""; REG_RUNNER_START=""
  REG_CLI_PID=""; REG_CLI_START=""
  REG_WORKTREE=""; REG_BRANCH=""
  [ -n "$LINE_ID" ] && [ -n "$REGISTRY_DIR" ] || return 0
  local entry="$REGISTRY_DIR/$LINE_ID.json" text
  if [ ! -f "$entry" ]; then
    REG_STATE="missing"
    return 0
  fi
  if ! text=$(cat "$entry" 2>/dev/null); then
    REG_STATE="missing"
    return 0
  fi
  REG_STATE="present"
  REG_RUNNER_PID=$(printf '%s\n' "$text" | sed -n 's/.*"runner_pid"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' | head -n 1)
  REG_RUNNER_START=$(json_field "$text" runner_start_token)
  REG_CLI_PID=$(printf '%s\n' "$text" | sed -n 's/.*"cli_pid"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' | head -n 1)
  REG_CLI_START=$(json_field "$text" cli_start_token)
  REG_WORKTREE=$(json_field "$text" worktree_path)
  REG_BRANCH=$(json_field "$text" branch)
  return 0
}

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

read_pid_file() {
  local f="$1" pid="" start="" pl=""
  P_PID=""; P_START=""; P_CLASS=""; P_PRESENT=0
  [ -n "$f" ] && [ -f "$f" ] || return 0
  P_PRESENT=1
  pid=$(sed -n 's/^pid=\([0-9][0-9]*\).*/\1/p' "$f" | head -n 1)
  start=$(sed -n 's/.*start=\([0-9][0-9]*\).*/\1/p' "$f" | head -n 1)
  if [ -z "$pid" ]; then
    pid=$(awk 'NR==1{print $1}' "$f" 2>/dev/null)
    case "$pid" in ''|*[!0-9]*) pid="" ;; esac
  fi
  P_PID="$pid"
  P_START="$start"
  pl=$(grep -m 1 '^pid=' "$f" 2>/dev/null || true)
  [ -n "$pl" ] || pl=$(head -n 1 "$f" 2>/dev/null || true)
  classify_pair "$(line_field_of "$pl")" "$(run_field_of "$pl")"
  P_CLASS="$CC"
}

PID_STATE="missing"

is_alive() {
  local pid="$1" expected="$2" state actual
  PID_STATE="missing"
  [ -n "$pid" ] || return 1
  if ! kill -0 "$pid" 2>/dev/null; then
    PID_STATE="dead"
    return 1
  fi
  state=$(process_stat_state "$pid")
  case "$state" in
    Z*) PID_STATE="zombie"; return 1 ;;
  esac
  if [ -n "$expected" ]; then
    actual=$(process_start_token "$pid")
    if [ -n "$actual" ] && [ "$actual" != "$expected" ]; then
      PID_STATE="reused"
      return 1
    fi
  fi
  PID_STATE="alive"
  return 0
}

S_EXISTS=0
S_RC=""
S_SENT=""
S_CLASS=""

read_status_file() {
  local f="$1" line=""
  S_EXISTS=0; S_RC=""; S_SENT=""; S_CLASS=""
  [ -n "$f" ] && [ -f "$f" ] || return 0
  line=$(grep -m 1 '^exit=' "$f" 2>/dev/null || true)
  [ -n "$line" ] || return 0
  S_EXISTS=1
  S_RC=$(printf '%s\n' "$line" | sed -n 's/^exit=\([0-9][0-9]*\).*/\1/p')
  S_SENT=$(printf '%s\n' "$line" | sed -n 's/.*sentinel=\([01]\).*/\1/p')
  is_uint "$S_RC" || S_RC=0
  classify_pair "$(line_field_of "$line")" "$(run_field_of "$line")"
  S_CLASS="$CC"
}

last_nonempty_line() {
  local f="$1" line=""
  [ -n "$f" ] && [ -f "$f" ] || { printf ''; return 0; }
  line=$(tail -n 50 "$f" 2>/dev/null | awk 'NF { last=$0 } END { print last }')
  printf '%s' "$line" | tr -d '\r' | sed 's/[[:space:]]*$//'
}

V_LABEL=""; V_VERDICT=""; V_CODE=0; V_REASON=""
V_PID=""; V_HB=""; V_HOOK="none"; V_SENT=""; V_RC=""; V_LAST=""; V_STATUS_RAW=""; V_ELAPSED=0; V_ANOMALY="no"; V_ATTR="legacy"; V_AT=""
V_STREAM="na"; V_RAW_BYTES=0


evaluate() {
  local label="$1" pidf="$2" statf="$3" logf="$4" sent="$5" hbf="$6" dl="$7"
  local now pid start pid_alive=0 pid_state="missing" hb_state="na" sent_state="na"
  local last="" anomaly=0 s_exists=0 s_rc="" s_sent=""
  local verdict="RUNNING" code="$EXIT_RUNNING" reason="" age=0 mt=0 size=""
  local pid_class="" status_class="" log_class="" sent_own=0

  now=$(now_epoch)
  read_pid_file "$pidf"; pid="$P_PID"; start="$P_START"; pid_class="$P_CLASS"
  if [ -n "$LINE_ID" ] && [ "$pid_class" != "own" ]; then
    pid=""; start=""
  fi
  read_registry_entry
  registry_identity=""
  if [ "$REG_STATE" = "present" ]; then
    if [ -n "$REG_RUNNER_PID" ] || [ -n "$REG_CLI_PID" ]; then
      if [ -n "$pid" ] && [ "$pid" = "$REG_RUNNER_PID" ]; then
        # The registry token is authoritative even when the pid file lacks one.
        [ -n "$REG_RUNNER_START" ] && start="$REG_RUNNER_START"
      elif [ -n "$pid" ] && [ "$pid" = "$REG_CLI_PID" ]; then
        [ -n "$REG_CLI_START" ] && start="$REG_CLI_START"
      elif [ -n "$pid" ]; then
        pid=""; start=""; registry_identity="unregistered"
      fi
    elif [ -n "$pid" ]; then
      # A registered line with no registered PID has no identity evidence;
      # an ambient pid file must never be trusted (pre-dispatch entry).
      pid=""; start=""; registry_identity="unregistered"
    fi
  elif [ "$REG_STATE" = "missing" ] && [ -n "$pid" ]; then
    pid=""; start=""; registry_identity="unregistered"
  fi
  if [ -n "$pid" ]; then
    if is_alive "$pid" "$start"; then pid_alive=1; fi
    pid_state="$PID_STATE"
  elif [ -n "$registry_identity" ]; then
    pid_state="$registry_identity"
  fi
  if [ "$pid_alive" -eq 1 ] && [ "$REG_STATE" = "present" ] && [ -n "$REG_BRANCH" ]; then
    if [ -z "$REG_WORKTREE" ] || [ ! -d "$REG_WORKTREE" ]; then
      # A registered branch that cannot be verified is not a trusted identity.
      pid_alive=0
      pid_state="branch-mismatch"
    elif command -v git >/dev/null 2>&1; then
      actual_branch=$(git -C "$REG_WORKTREE" rev-parse --abbrev-ref HEAD 2>/dev/null || true)
      if [ -n "$actual_branch" ] && [ "$actual_branch" != "$REG_BRANCH" ]; then
        pid_alive=0
        pid_state="branch-mismatch"
      fi
    fi
  fi

  read_status_file "$statf"; s_exists="$S_EXISTS"; s_rc="$S_RC"; s_sent="$S_SENT"; status_class="$S_CLASS"
  if [ -n "$LINE_ID" ] && [ "$status_class" != "own" ]; then
    s_exists=0; s_rc=""; s_sent=""
  fi
  read_meta_file "$META"
  read_heartbeat_envelope "$hbf"
  last=$(last_nonempty_line "$logf")
  if [ "$M_EXISTS" -eq 1 ]; then
    log_class="$M_CLASS"
  elif [ "$S_EXISTS" -eq 1 ]; then
    log_class="$status_class"
  else
    log_class="unattributed"
  fi
  case "$last" in
    ANOMALY:*)
      if [ -z "$LINE_ID" ] || [ "$log_class" = "own" ]; then anomaly=1; fi
      ;;
  esac

  if [ -n "$sent" ]; then
    if [ -z "$LINE_ID" ]; then
      if [ "$last" = "$sent" ] || [ "$s_sent" = "1" ]; then
        sent_state="yes"
      else
        sent_state="no"
      fi
    else
      if [ "$s_exists" -eq 1 ] && [ "$s_sent" = "1" ]; then
        sent_own=1
      elif [ "$M_EXISTS" -eq 1 ] && [ "$M_CLASS" = "own" ] && [ "$M_SENT" = "1" ] && [ "$last" = "$sent" ]; then
        sent_own=1
      elif [ "$s_exists" -eq 1 ] && [ "$M_EXISTS" -eq 0 ] && [ "$last" = "$sent" ]; then
        sent_own=1
      fi
      [ "$sent_own" -eq 1 ] && sent_state="yes" || sent_state="no"
    fi
  fi

  if [ -n "$hbf" ]; then
    if [ -f "$hbf" ]; then
      mt=$(file_mtime "$hbf")
      if is_uint "$mt" && [ "$mt" -gt 0 ]; then
        age=$((now - mt))
        if [ -n "$LINE_ID" ] && [ "$H_CLASS" != "own" ]; then
          hb_state="na"
        elif [ "$age" -gt "$HEARTBEAT_MAX_AGE" ]; then hb_state="stale"; else hb_state="fresh"; fi
      else
        hb_state="missing"
      fi
    else
      hb_state="missing"
    fi
  fi

  # Hook events are an early signal only; they never decide a verdict.
  local hook_state="none"
  if [ -n "$HOOK_DONE" ] && [ -s "$HOOK_DONE" ]; then HOOK_EVENT_SEEN=1; fi
  [ "$HOOK_EVENT_SEEN" -eq 1 ] && hook_state="observed"

  if [ "$s_exists" -eq 1 ]; then
    if [ -n "$sent" ]; then
      if [ "$anomaly" -eq 1 ]; then
        verdict="ANOMALY"; code="$EXIT_ANOMALY"; reason="anomaly-line"
      elif [ "$sent_state" = "yes" ]; then
        verdict="DONE"; code="$EXIT_DONE"; reason="exit-record-sentinel"
      elif is_uint "$s_rc" && [ "$s_rc" -ne 0 ]; then
        verdict="FAILED"; code="$EXIT_FAILED"; reason="exit-record-rc"
      else
        verdict="INCOMPLETE"; code="$EXIT_INCOMPLETE"; reason="exit-record-no-sentinel"
      fi
    else
      if [ "$anomaly" -eq 1 ]; then
        verdict="ANOMALY"; code="$EXIT_ANOMALY"; reason="anomaly-line"
      elif is_uint "$s_rc" && [ "$s_rc" -ne 0 ]; then
        verdict="FAILED"; code="$EXIT_FAILED"; reason="exit-record-rc"
      else
        verdict="DONE"; code="$EXIT_DONE"; reason="exit-record-ok"
      fi
    fi
  else
    if [ -n "$sent" ] && [ "$sent_state" = "yes" ]; then
      verdict="DONE"; code="$EXIT_DONE"; reason="sentinel"
    elif [ "$anomaly" -eq 1 ] && [ "$pid_alive" -eq 0 ]; then
      verdict="ANOMALY"; code="$EXIT_ANOMALY"; reason="anomaly-line"
    elif [ "$pid_state" = "dead" ] || [ "$pid_state" = "zombie" ] || [ "$pid_state" = "reused" ] \
         || [ "$pid_state" = "unregistered" ] || [ "$pid_state" = "branch-mismatch" ]; then
      verdict="DEAD"; code="$EXIT_DEAD"; reason="pid-$pid_state"
    elif [ "$pid_state" = "alive" ]; then
      verdict="RUNNING"; code="$EXIT_RUNNING"; reason="alive"
    else
      if [ "$((now - START_EPOCH))" -ge "$START_GRACE" ]; then
        verdict="NO_SIGNAL"; code="$EXIT_NO_SIGNAL"; reason="pid-missing"
      else
        verdict="RUNNING"; code="$EXIT_RUNNING"; reason="starting"
      fi
    fi
  fi

  if { [ "$verdict" = "RUNNING" ] || [ "$verdict" = "NO_SIGNAL" ]; } \
     && is_uint "$dl" && [ "$dl" -gt 0 ] && [ "$now" -ge "$dl" ]; then
    verdict="TIMEOUT"; code="$EXIT_TIMEOUT"; reason="deadline"
  fi

  V_LABEL="$label"; V_VERDICT="$verdict"; V_CODE="$code"; V_REASON="$reason"
  V_ITER=$(one_line "${ITER:-na}")
  V_PID="$pid_state"; V_HB="$hb_state"; V_HOOK="$hook_state"; V_SENT="$sent_state"
  V_RC="${s_rc:-na}"; V_LAST="$last"; V_STATUS_RAW=""
  [ "$anomaly" -eq 1 ] && V_ANOMALY="observed" || V_ANOMALY="no"
  [ "$s_exists" -eq 1 ] && V_STATUS_RAW="exit=$s_rc sentinel=${s_sent:-na}"
  if [ -z "$LINE_ID" ]; then
    V_ATTR="legacy"
  elif [ "$S_EXISTS" -eq 1 ]; then
    V_ATTR="$status_class"
  elif [ "$M_EXISTS" -eq 1 ]; then
    V_ATTR="$M_CLASS"
  elif [ "$HB_EXISTS" -eq 1 ]; then
    V_ATTR="$H_CLASS"
  elif [ "$P_PRESENT" -eq 1 ]; then
    V_ATTR="$pid_class"
  else
    V_ATTR="unattributed"
  fi
  V_STREAM="na"; V_RAW_BYTES=0
  if [ -n "$RAW_STREAM" ]; then
    if [ ! -f "$RAW_STREAM" ]; then
      V_STREAM="absent"
    else
      size=$(wc -c < "$RAW_STREAM" 2>/dev/null | tr -d ' ')
      case "$size" in ''|*[!0-9]*) size=0 ;; esac
      V_RAW_BYTES="$size"
      if [ -n "$RAW_PREV_SIZE" ] && [ "$size" -gt "$RAW_PREV_SIZE" ]; then
        V_STREAM="growing"
      else
        V_STREAM="idle"
      fi
      RAW_PREV_SIZE="$size"
    fi
  fi
  V_ELAPSED=$((now - START_EPOCH))
  V_AT="$now"
}

format_verdict() {
  printf 'WATCH label=%s verdict=%s pid=%s heartbeat=%s hook=%s anomaly=%s sentinel=%s rc=%s elapsed=%s reason=%s stream=%s line=%s run=%s stage=%s event=watcher-verdict at=%s attribution=%s iter=%s' \
    "$V_LABEL" "$V_VERDICT" "$V_PID" "$V_HB" "$V_HOOK" "$V_ANOMALY" "$V_SENT" "$V_RC" "$V_ELAPSED" "$V_REASON" "$V_STREAM" \
    "$LINE_ID" "$RUN_ID" "$STAGE" "$V_AT" "$V_ATTR" "$V_ITER"

}

format_evidence() {
  local last raw_extra=""
  last=$(one_line "$V_LAST" | tr '"' "'")
  if [ -n "$RAW_STREAM" ]; then
    raw_extra=" raw=$RAW_STREAM bytes=$V_RAW_BYTES"
  fi
  printf 'EVIDENCE label=%s last="%s" status="%s" line=%s run=%s stage=%s event=watcher-verdict at=%s attribution=%s%s iter=%s' \
    "$V_LABEL" "$last" "$V_STATUS_RAW" "$LINE_ID" "$RUN_ID" "$STAGE" "$V_AT" "$V_ATTR" "$raw_extra" "$V_ITER"
}

emit_single() {
  format_verdict; printf '\n'
  if [ "$V_CODE" -ne "$EXIT_RUNNING" ] || [ "$VERBOSE" -eq 1 ]; then
    format_evidence; printf '\n'
  fi
}

normalize_field() {
  if [ "$1" = "-" ]; then printf ''; else printf '%s' "$1"; fi
}

maybe_renew_lease() {
  [ -n "$LEASE_RENEW_CMD" ] || return 0
  local now
  now=$(now_epoch)
  if [ "$LAST_LEASE_RENEW" -eq 0 ] || [ "$((now - LAST_LEASE_RENEW))" -ge "$LEASE_RENEW_INTERVAL" ]; then
    bash -c "$LEASE_RENEW_CMD" >/dev/null 2>&1 || true
    LAST_LEASE_RENEW=$now
  fi
}

run_single() {
  START_EPOCH=$(now_epoch)
  if [ -n "$TIMEOUT" ]; then DEADLINE_EPOCH=$((START_EPOCH + TIMEOUT)); fi
  [ "$ONCE" -eq 1 ] && WINDOW=0
  local window_end=$((START_EPOCH + WINDOW)) grace_end=0 grace_used=0 now remaining sleep_for
  if [ "$ONCE" -eq 0 ] && [ "$DEADLINE_EPOCH" -gt 0 ] && [ "$DEADLINE_GRACE" -gt 0 ]; then
    grace_end=$((DEADLINE_EPOCH + DEADLINE_GRACE))
    # A deadline call must sample through the deadline (and its grace) even
    # when the polling window is shorter: the first evaluation can cross the
    # window boundary under load and return RUNNING before the deadline is
    # ever observed.
    [ "$window_end" -lt "$grace_end" ] && window_end=$grace_end
  fi
  while :; do
    maybe_renew_lease
    evaluate "$LABEL" "$PID_FILE" "$STATUS_FILE" "$LOG_FILE" "$SENTINEL" "$HEARTBEAT" "$DEADLINE_EPOCH"
    now=$(now_epoch)
    if [ "$V_CODE" -eq "$EXIT_TIMEOUT" ] && [ "$grace_end" -gt 0 ] && [ "$now" -lt "$grace_end" ]; then
      # Deadline reached but the process may still complete: keep sampling
      # through the grace window instead of returning TIMEOUT immediately.
      grace_used=1
    elif [ "$V_CODE" -ne "$EXIT_RUNNING" ]; then
      [ "$grace_used" -eq 1 ] && [ "$V_CODE" -eq "$EXIT_TIMEOUT" ] && V_REASON="deadline-grace-expired"
      emit_single
      exit "$V_CODE"
    fi
    now=$(now_epoch)
    if [ "$now" -ge "$window_end" ]; then
      emit_single
      exit "$EXIT_RUNNING"
    fi
    remaining=$((window_end - now))
    sleep_for=$INTERVAL
    [ "$sleep_for" -gt "$remaining" ] && sleep_for=$remaining
    if [ -n "$HOOK_FIFO" ] && [ -p "$HOOK_FIFO" ] && [ "$sleep_for" -gt 0 ]; then
      if read -t "$sleep_for" _hook_line <> "$HOOK_FIFO"; then
        HOOK_EVENT_SEEN=1
      fi
    else
      [ "$sleep_for" -gt 0 ] && sleep "$sleep_for"
    fi
  done
}

severity() {
  case "$1" in
    "$EXIT_ANOMALY") echo 9 ;;
    "$EXIT_FAILED") echo 8 ;;
    "$EXIT_DEAD") echo 7 ;;
    "$EXIT_INCOMPLETE") echo 6 ;;
    "$EXIT_TIMEOUT") echo 5 ;;
    "$EXIT_NO_SIGNAL") echo 4 ;;
    "$EXIT_DONE") echo 3 ;;
    *) echo 1 ;;
  esac
}

run_manifest() {
  local file="$1"
  [ -f "$file" ] || die_usage "manifest not found: $file"
  M_LABEL=(); M_PID=(); M_STATUS=(); M_LOG=(); M_SENT=(); M_HB=(); M_DL=()
  local a b c d e f g
  while IFS='|' read -r a b c d e f g; do
    case "${a:-}" in ''|\#*) continue ;; esac
    M_LABEL+=("$a")
    M_PID+=("$(normalize_field "${b:-}")")
    M_STATUS+=("$(normalize_field "${c:-}")")
    M_LOG+=("$(normalize_field "${d:-}")")
    M_SENT+=("$(normalize_field "${e:-}")")
    M_HB+=("$(normalize_field "${f:-}")")
    M_DL+=("$(normalize_field "${g:-}")")
  done < "$file"
  [ "${#M_LABEL[@]}" -gt 0 ] || die_usage "manifest has no targets"

  START_EPOCH=$(now_epoch)
  [ "$ONCE" -eq 1 ] && WINDOW=0
  local window_end=$((START_EPOCH + WINDOW)) now remaining sleep_for i
  local -a result_lines evidence_lines
  local any_terminal worst worst_sev sev
  while :; do
    maybe_renew_lease
    result_lines=(); evidence_lines=(); any_terminal=0; worst="$EXIT_RUNNING"; worst_sev=1
    for i in "${!M_LABEL[@]}"; do
      local dl="${M_DL[$i]}"
      is_uint "$dl" || dl=0
      evaluate "${M_LABEL[$i]}" "${M_PID[$i]}" "${M_STATUS[$i]}" "${M_LOG[$i]}" \
        "${M_SENT[$i]}" "${M_HB[$i]}" "$dl"
      result_lines+=("$(format_verdict)")
      [ "$V_CODE" -ne "$EXIT_RUNNING" ] && evidence_lines+=("$(format_evidence)")
      if [ "$V_CODE" -ne "$EXIT_RUNNING" ]; then
        any_terminal=1
        sev=$(severity "$V_CODE")
        if [ "$sev" -gt "$worst_sev" ]; then worst_sev=$sev; worst="$V_CODE"; fi
      fi
    done
    if [ "$any_terminal" -eq 1 ]; then
      for i in "${!result_lines[@]}"; do printf '%s\n' "${result_lines[$i]}"; done
      for i in "${!evidence_lines[@]}"; do printf '%s\n' "${evidence_lines[$i]}"; done
      exit "$worst"
    fi
    now=$(now_epoch)
    if [ "$now" -ge "$window_end" ]; then
      for i in "${!result_lines[@]}"; do printf '%s\n' "${result_lines[$i]}"; done
      exit "$EXIT_RUNNING"
    fi
    remaining=$((window_end - now))
    sleep_for=$INTERVAL
    [ "$sleep_for" -gt "$remaining" ] && sleep_for=$remaining
    [ "$sleep_for" -gt 0 ] && sleep "$sleep_for"
  done
}

# ---------------------------------------------------------------- self-test

ST_TMP=""
ST_SPAWNED=()

cleanup_selftest() {
  local p
  if [ -n "${ST_TMP:-}" ]; then
    for p in "${ST_SPAWNED[@]:-}"; do
      [ -n "$p" ] && kill "$p" 2>/dev/null
    done
    rm -rf "$ST_TMP"
  fi
}

self_test() {
  local pass=0 fail=0
  mkdir -p "$HOME/tmp"
  ST_TMP=$(mktemp -d "$HOME/tmp/watch-target-selftest.XXXXXX") || {
    echo "SELF-TEST: cannot create temp dir" >&2
    return 1
  }
  ST_SPAWNED=()
  trap cleanup_selftest EXIT

  ok() { pass=$((pass + 1)); printf 'ok %s\n' "$1"; }
  bad() { fail=$((fail + 1)); printf 'FAIL %s — %s\n' "$1" "$2" >&2; }

  check() {
    local name="$1" want_rc="$2" want_verdict="$3" rc="$4" out="$5"
    if [ "$rc" -ne "$want_rc" ]; then
      bad "$name" "exit $rc != $want_rc; output: $out"
    elif ! printf '%s\n' "$out" | grep -q "verdict=$want_verdict"; then
      bad "$name" "missing verdict=$want_verdict; output: $out"
    else
      ok "$name"
    fi
  }

  check_attr() {
    local name="$1" want_rc="$2" want_verdict="$3" want_attr="$4" r="$5"
    local rc="${r%%$'\n'*}" out="${r#*$'\n'}"
    if [ "$rc" -ne "$want_rc" ]; then
      bad "$name" "exit $rc != $want_rc; output: $out"
    elif ! printf '%s\n' "$out" | grep -q "verdict=$want_verdict"; then
      bad "$name" "missing verdict=$want_verdict; output: $out"
    elif ! printf '%s\n' "$out" | grep -q "attribution=$want_attr"; then
      bad "$name" "missing attribution=$want_attr; output: $out"
    else
      ok "$name"
    fi
  }

  check_hook() {
    local name="$1" want="$2" out="$3"
    if printf '%s\n' "$out" | grep -q "hook=$want"; then
      ok "$name"
    else
      bad "$name" "missing hook=$want; output: $out"

    fi
  }

  watch() {
    local out rc
    out=$("$SELF" "$@" 2>&1); rc=$?
    printf '%s\n' "$rc"
    printf '%s\n' "$out"
  }

  local base="$ST_TMP/base"
  local self_dir
  self_dir=$(cd "$(dirname "$SELF")" && pwd)
  mkdir -p "$base"

  # 1. DONE via exit record + sentinel
  printf 'working\nPLAN-DONE\n' > "$base/log1"
  printf 'exit=0 at=1 sentinel=1\n' > "$base/status1"
  : > "$base/pid1"
  local r; r=$(watch --label 'done' --pid-file "$base/pid1" --status-file "$base/status1" \
    --log "$base/log1" --sentinel PLAN-DONE --window 1 --start-grace 0)
  check 'done' 0 DONE "${r%%$'\n'*}" "${r#*$'\n'}"

  # 2. exit rc=0 but no sentinel => INCOMPLETE (fake-done)
  printf 'working\n' > "$base/log2"
  printf 'exit=0 at=1 sentinel=0\n' > "$base/status2"
  r=$(watch --label fake --pid-file "$base/pid1" --status-file "$base/status2" \
    --log "$base/log2" --sentinel PLAN-DONE --window 1 --start-grace 0)
  check fake-done 15 INCOMPLETE "${r%%$'\n'*}" "${r#*$'\n'}"

  # 3. anomaly line
  printf 'ANOMALY: spec conflict\n' > "$base/log3"
  printf 'exit=0 at=1 sentinel=0\n' > "$base/status3"
  r=$(watch --label anomaly --pid-file "$base/pid1" --status-file "$base/status3" \
    --log "$base/log3" --sentinel PLAN-DONE --window 1 --start-grace 0)
  check anomaly 11 ANOMALY "${r%%$'\n'*}" "${r#*$'\n'}"

  # 4. non-zero exit
  printf 'boom\n' > "$base/log4"
  printf 'exit=2 at=1 sentinel=0\n' > "$base/status4"
  r=$(watch --label failed --pid-file "$base/pid1" --status-file "$base/status4" \
    --log "$base/log4" --sentinel PLAN-DONE --window 1 --start-grace 0)
  check failed 12 FAILED "${r%%$'\n'*}" "${r#*$'\n'}"

  # 4b. contradictory record: sentinel flag set but final line is ANOMALY => fail safe
  printf 'ANOMALY: contract contradiction\n' > "$base/log4b"
  printf 'exit=0 at=1 sentinel=1\n' > "$base/status4b"
  r=$(watch --label contradiction --pid-file "$base/pid1" --status-file "$base/status4b" \
    --log "$base/log4b" --sentinel PLAN-DONE --window 1 --start-grace 0)
  check anomaly-precedence 11 ANOMALY "${r%%$'\n'*}" "${r#*$'\n'}"

  # 5. dead pid, no exit record (fixed unused pid: no reuse race)
  printf 'pid=999999 start=\n' > "$base/pid5"
  r=$(watch --label dead --pid-file "$base/pid5" --status-file "$base/none5" \
    --log "$base/none5" --sentinel PLAN-DONE --window 1 --start-grace 0)
  check dead 13 DEAD "${r%%$'\n'*}" "${r#*$'\n'}"

  # 6. running process, no terminal signal (long-lived so later cases keep a live pid)
  sleep 30 & local live=$!
  disown "$live" 2>/dev/null || true
  ST_SPAWNED+=("$live")
  local ticks=""
  [ -r "/proc/$live/stat" ] && ticks=$(awk '{print $22}' "/proc/$live/stat")
  printf 'pid=%s start=%s\n' "$live" "$ticks" > "$base/pid6"
  r=$(watch --label running --pid-file "$base/pid6" --status-file "$base/none6" \
    --log "$base/none6" --sentinel PLAN-DONE --window 1 --interval 1 --start-grace 0)
  check running 10 RUNNING "${r%%$'\n'*}" "${r#*$'\n'}"

  # 7. stage deadline => TIMEOUT, not window expiry
  r=$(watch --label timeout --pid-file "$base/pid6" --status-file "$base/none6" \
    --log "$base/none6" --sentinel PLAN-DONE --timeout 1 --deadline-grace 0 \
    --window 3 --interval 1 --start-grace 0)
  check timeout 14 TIMEOUT "${r%%$'\n'*}" "${r#*$'\n'}"

  # 7b. late completion inside the deadline grace => DONE, not TIMEOUT
  : > "$base/late.log"
  ( sleep 2; printf 'exit=0 at=%s sentinel=1\n' "$(date +%s)" > "$base/late.status"; \
    printf 'PLAN-DONE\n' > "$base/late.log" ) &
  local late_writer=$!
  ST_SPAWNED+=("$late_writer")
  r=$(watch --label late --pid-file "$base/pid6" --status-file "$base/late.status" \
    --log "$base/late.log" --sentinel PLAN-DONE --timeout 1 --deadline-grace 4 \
    --window 1 --interval 1 --start-grace 0)
  wait "$late_writer" 2>/dev/null || true
  check late-completion 0 DONE "${r%%$'\n'*}" "${r#*$'\n'}"

  # 7c. grace expires without a status => TIMEOUT with an explicit reason
  r=$(watch --label grace-timeout --pid-file "$base/pid6" --status-file "$base/none6" \
    --log "$base/none6" --sentinel PLAN-DONE --timeout 1 --deadline-grace 2 \
    --window 1 --interval 1 --start-grace 0)
  check grace-timeout 14 TIMEOUT "${r%%$'\n'*}" "${r#*$'\n'}"
  printf '%s\n' "${r#*$'\n'}" | grep -q 'reason=deadline-grace-expired' \
    || bad "grace-timeout-reason" "grace expiry reason missing: ${r#*$'\n'}"

  # 7d. a polling window shorter than the deadline+grace must not return
  # RUNNING before the deadline is observed (load-independent regression pin)
  r=$(watch --label zero-window --pid-file "$base/pid6" --status-file "$base/none6" \
    --log "$base/none6" --sentinel PLAN-DONE --timeout 1 --deadline-grace 2 \
    --window 0 --interval 1 --start-grace 0)
  check zero-window 14 TIMEOUT "${r%%$'\n'*}" "${r#*$'\n'}"

  # 8. no signals at all => NO_SIGNAL (zero-match path must not fake completion)
  r=$(watch --label nosignal --pid-file "$base/none8" --status-file "$base/none8" \
    --log "$base/none8" --sentinel PLAN-DONE --window 0 --start-grace 0)
  check no-signal 16 NO_SIGNAL "${r%%$'\n'*}" "${r#*$'\n'}"

  # 9. stale heartbeat with live pid => RUNNING + heartbeat=stale
  printf 'pid=%s start=%s\n' "$live" "$ticks" > "$base/pid9"
  : > "$base/hb9"
  touch -t 200001010000 "$base/hb9" 2>/dev/null || true
  r=$(watch --label stale-hb --pid-file "$base/pid9" --status-file "$base/none9" \
    --log "$base/none9" --sentinel PLAN-DONE --heartbeat "$base/hb9" \
    --heartbeat-max-age 1 --window 0 --start-grace 0)
  check stale-heartbeat 10 RUNNING "${r%%$'\n'*}" "${r#*$'\n'}"
  printf '%s\n' "${r#*$'\n'}" | grep -q 'heartbeat=stale' || bad "stale-heartbeat-flag" "heartbeat not stale: $r"

  # 10. pid reuse guard: live PID whose recorded start token is wrong
  printf 'pid=%s start=1\n' "$$" > "$base/pid10"
  r=$(watch --label reused --pid-file "$base/pid10" --status-file "$base/none10" \
    --log "$base/none10" --sentinel PLAN-DONE --window 1 --start-grace 0)
  check pid-reuse 13 DEAD "${r%%$'\n'*}" "${r#*$'\n'}"

  # 10b. zombie process (requires a non-reaping parent; /proc or ps stat check)
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$base/zpid" <<'PY' &
import os, sys, time
pid = os.fork()
if pid == 0:
    os._exit(0)
with open(sys.argv[1], "w") as f:
    f.write(str(pid))
time.sleep(3)
PY
    local zparent=$!
    disown "$zparent" 2>/dev/null || true
    ST_SPAWNED+=("$zparent")
    local i=0
    while [ ! -s "$base/zpid" ] && [ "$i" -lt 50 ]; do sleep 0.1; i=$((i+1)); done
    local zpid
    zpid=$(cat "$base/zpid" 2>/dev/null || true)
    printf 'pid=%s start=\n' "$zpid" > "$base/zpid10b"
    r=$(watch --label zombie --pid-file "$base/zpid10b" --status-file "$base/none10b" \
      --log "$base/none10b" --sentinel PLAN-DONE --window 1 --start-grace 0)
    check zombie 13 DEAD "${r%%$'\n'*}" "${r#*$'\n'}"
  else
    printf 'skip zombie (python3 not found)\n'
  fi

  # 11. sentinel without exit record
  printf 'PLAN-DONE\n' > "$base/log11"
  r=$(watch --label sentinel --pid-file "$base/pid5" --status-file "$base/none11" \
    --log "$base/log11" --sentinel PLAN-DONE --window 0 --start-grace 0)
  check sentinel-only 0 DONE "${r%%$'\n'*}" "${r#*$'\n'}"

  # 12. async-script mode: exit rc=0, no sentinel configured
  printf 'finished\n' > "$base/log12"
  printf 'exit=0 at=1 sentinel=0\n' > "$base/status12"
  r=$(watch --label async --pid-file "$base/pid1" --status-file "$base/status12" \
    --log "$base/log12" --window 0 --start-grace 0)
  check async-exit-ok 0 DONE "${r%%$'\n'*}" "${r#*$'\n'}"

  # 13. manifest: one DONE + one RUNNING, both reported (fresh live PID)
  sleep 30 & local manifest_live=$!
  disown "$manifest_live" 2>/dev/null || true
  ST_SPAWNED+=("$manifest_live")
  local manifest_ticks
  manifest_ticks=$(process_start_token "$manifest_live")
  printf 'pid=%s start=%s\n' "$manifest_live" "$manifest_ticks" > "$base/pidm2"
  printf 'PLAN-DONE\n' > "$base/logm1"
  printf 'exit=0 at=1 sentinel=1\n' > "$base/statusm1"
  printf 'm1|%s|%s|%s|PLAN-DONE|-|0\nm2|%s|-|-|PLAN-DONE|-|0\n' \
    "$base/pid1" "$base/statusm1" "$base/logm1" "$base/pidm2" > "$base/manifest"
  r=$(watch --manifest "$base/manifest" --window 1 --interval 1 --start-grace 0)
  local mrc="${r%%$'\n'*}" mout="${r#*$'\n'}"
  if [ "$mrc" -ne 0 ] || ! printf '%s\n' "$mout" | grep -q 'label=m1 verdict=DONE' \
     || ! printf '%s\n' "$mout" | grep -q 'label=m2 verdict=RUNNING'; then
    bad "manifest" "rc=$mrc out=$mout"
  else
    ok "manifest"
  fi

  # 13b. attribution: own / foreign / stale-run / unattributed / legacy
  sleep 8 & local attr_live=$!
  disown "$attr_live" 2>/dev/null || true
  ST_SPAWNED+=("$attr_live")
  local attr_ticks=""
  [ -r "/proc/$attr_live/stat" ] && attr_ticks=$(awk '{print $22}' "/proc/$attr_live/stat")
  printf 'PLAN-DONE\n' > "$base/logattr"
  printf 'exit=0 at=1 sentinel=1 line=L1 run=R1 stage=plan event=status\n' > "$base/statusattr"
  printf 'pid=%s start=%s at=1 line=L1 run=R1 stage=plan event=pid\n' "$attr_live" "$attr_ticks" > "$base/pidattr"
  printf 'at=1 line=L1 run=R1 stage=plan event=heartbeat\n' > "$base/hbattr"
  printf '{"line_id":"L1","run_id":"R1","stage":"plan","event":"log-terminal","at":1,"sentinel_seen":1,"exit":0}\n' > "$base/metaattr"
  r=$(watch --label attr-own --line-id L1 --run-id R1 \
    --pid-file "$base/pidattr" --status-file "$base/statusattr" --log "$base/logattr" \
    --sentinel PLAN-DONE --heartbeat "$base/hbattr" --meta "$base/metaattr" --window 0 --start-grace 0)
  check_attr "attribution-own" 0 DONE own "$r"

  printf 'exit=0 at=1 sentinel=1 line=L2 run=R2 stage=plan event=status\n' > "$base/statusforeign"
  printf '{"line_id":"L2","run_id":"R2","stage":"plan","event":"log-terminal","at":1,"sentinel_seen":1,"exit":0}\n' > "$base/metaforeign"
  r=$(watch --label attr-foreign --line-id L1 --run-id R1 \
    --pid-file "$base/pidattr" --status-file "$base/statusforeign" --log "$base/logattr" \
    --sentinel PLAN-DONE --heartbeat "$base/hbattr" --meta "$base/metaforeign" --window 0 --start-grace 0)
  check_attr "attribution-foreign-not-consumed" 10 RUNNING foreign "$r"

  printf 'exit=0 at=1 sentinel=1 line=L1 run=R0 stage=plan event=status\n' > "$base/statusstale"
  printf '{"line_id":"L1","run_id":"R0","stage":"plan","event":"log-terminal","at":1,"sentinel_seen":1,"exit":0}\n' > "$base/metastale"
  r=$(watch --label attr-stale --line-id L1 --run-id R1 \
    --pid-file "$base/pidattr" --status-file "$base/statusstale" --log "$base/logattr" \
    --sentinel PLAN-DONE --heartbeat "$base/hbattr" --meta "$base/metastale" --window 0 --start-grace 0)
  check_attr "attribution-stale-run" 10 RUNNING stale-run "$r"

  printf 'exit=0 at=1 sentinel=1\n' > "$base/statusunattr"
  r=$(watch --label attr-unattr --line-id L1 --run-id R1 \
    --pid-file "$base/pidattr" --status-file "$base/statusunattr" --log "$base/logattr" \
    --sentinel PLAN-DONE --heartbeat "$base/hbattr" --window 0 --start-grace 0)
  check_attr "attribution-unattributed" 10 RUNNING unattributed "$r"

  r=$(watch --label attr-legacy --pid-file "$base/pidattr" --status-file "$base/statusattr" \
    --log "$base/logattr" --sentinel PLAN-DONE --heartbeat "$base/hbattr" --window 0 --start-grace 0)
  check_attr "attribution-legacy" 0 DONE legacy "$r"

  # 13c. lease renewal hook fires inside a watch window
  : > "$base/renewed"
  r=$(watch --label lease-renew --line-id L1 --run-id R1 \
    --pid-file "$base/pidattr" --status-file "$base/none13" --log "$base/none13" \
    --sentinel PLAN-DONE --window 2 --interval 1 --start-grace 0 \
    --lease-renew-cmd "printf x >> '$base/renewed'" --lease-renew-interval 1)
  local renew_rc="${r%%$'\n'*}"
  if [ "$renew_rc" -eq 10 ] && [ -s "$base/renewed" ]; then
    ok "lease-renew-hook"
  else
    bad "lease-renew-hook" "rc=$renew_rc renewed=$(wc -c < "$base/renewed" 2>/dev/null || echo 0)"
  fi

  # 13d. registry identity: registered PID + token is consumed, a different
  # PID is refused, and a missing registry entry is never trusted.
  local reg="$ST_TMP/registry"
  mkdir -p "$reg"
  local reg_token
  reg_token=$(process_start_token "$$")
  printf '{"line_id":"L1","run_id":"R1","runner_pid":%s,"runner_start_token":"%s"}\n' \
    "$$" "$reg_token" > "$reg/L1.json"
  printf 'pid=%s start=%s at=1 line=L1 run=R1 stage=plan event=pid\n' "$$" "$reg_token" > "$base/pidreg"
  r=$(watch --label reg-ok --line-id L1 --run-id R1 --registry "$reg" \
    --pid-file "$base/pidreg" --status-file "$base/nonereg" --log "$base/nonereg" \
    --sentinel PLAN-DONE --window 0 --start-grace 0)
  check reg-identity 10 RUNNING "${r%%$'\n'*}" "${r#*$'\n'}"
  printf 'pid=1 start=%s at=1 line=L1 run=R1 stage=plan event=pid\n' "$reg_token" > "$base/pidregbad"
  r=$(watch --label reg-foreign --line-id L1 --run-id R1 --registry "$reg" \
    --pid-file "$base/pidregbad" --status-file "$base/nonereg" --log "$base/nonereg" \
    --sentinel PLAN-DONE --window 1 --start-grace 0)
  check reg-unregistered 13 DEAD "${r%%$'\n'*}" "${r#*$'\n'}"
  rm -f "$reg/L1.json"
  r=$(watch --label reg-missing --line-id L1 --run-id R1 --registry "$reg" \
    --pid-file "$base/pidreg" --status-file "$base/nonereg" --log "$base/nonereg" \
    --sentinel PLAN-DONE --window 1 --start-grace 0)
  check reg-missing 13 DEAD "${r%%$'\n'*}" "${r#*$'\n'}"

  # 13e. lease window gate: window > ttl/3 without a renewal hook fails fast
  r=$(watch --label lease-window --lease-ttl 600 --window 201 \
    --pid-file "$base/pid6" --status-file "$base/none13e" --log "$base/none13e" \
    --sentinel PLAN-DONE --start-grace 0)
  if [ "${r%%$'\n'*}" -eq 2 ] && printf '%s\n' "${r#*$'\n'}" | grep -q 'ttl/3'; then
    ok "lease-window-over-ttl"
  else
    bad "lease-window-over-ttl" "rc=${r%%$'\n'*} out=${r#*$'\n'}"
  fi

  # 14. demonstrate the pgrep -c zero-match trap (regression knowledge; the
  # 14. hook done file: observed is an early signal, DONE still comes from the
  # exit record + sentinel
  printf 'PLAN-DONE\n' > "$base/log14"
  printf 'exit=0 at=1 sentinel=1\n' > "$base/status14"
  printf '{"hook_event_name":"Stop"}\n' > "$base/done14"
  r=$(watch --label hookdone --pid-file "$base/pid1" --status-file "$base/status14" \
    --log "$base/log14" --sentinel PLAN-DONE --hook-done "$base/done14" \
    --window 0 --start-grace 0)
  check hook-done 0 DONE "${r%%$'\n'*}" "${r#*$'\n'}"
  check_hook hook-done-flag observed "${r#*$'\n'}"

  # 15. hook FIFO event wakes the wait; it never fabricates a verdict
  if command -v mkfifo >/dev/null 2>&1; then
    sleep 5 & local hlive=$!
    disown "$hlive" 2>/dev/null || true
    ST_SPAWNED+=("$hlive")
    local hticks=""
    [ -r "/proc/$hlive/stat" ] && hticks=$(awk '{print $22}' "/proc/$hlive/stat")
    printf 'pid=%s start=%s\n' "$hlive" "$hticks" > "$base/pid15"
    mkfifo "$base/hook15.fifo"
    ( sleep 0.5; printf 'STOP test 1\n' > "$base/hook15.fifo" ) &
    local hwriter=$!
    disown "$hwriter" 2>/dev/null || true
    ST_SPAWNED+=("$hwriter")
    r=$(watch --label hookfifo --pid-file "$base/pid15" --status-file "$base/none15" \
      --log "$base/none15" --sentinel PLAN-DONE --hook-fifo "$base/hook15.fifo" \
      --window 2 --interval 1 --start-grace 0)
    check hook-fifo 10 RUNNING "${r%%$'\n'*}" "${r#*$'\n'}"
    check_hook hook-fifo-flag observed "${r#*$'\n'}"
  else
    printf 'skip hook-fifo (mkfifo not found)\n'
  fi

    # 16. demonstrate the pgrep -c zero-match trap (regression knowledge; the

  # watcher itself never uses pgrep for liveness)
  if command -v pgrep >/dev/null 2>&1; then
    local zero
    zero=$(pgrep -c '__watch_target_no_such_process__' 2>/dev/null || echo 0)
    if [ "$zero" = "0" ] || [ "$zero" = "$(printf '0\n0')" ]; then
      ok "pgrep-zero-match-trap-reproduced"
    else
      bad "pgrep-zero-match-trap-reproduced" "expected zero-match output, got: $zero"
    fi
  fi

  # 16. stream: non-terminal sentinel wording never yields DONE
  if command -v python3 >/dev/null 2>&1; then
    printf '%s\n' '{"type":"assistant","message":{"content":[{"type":"text","text":"mentions PLAN-DONE but is not terminal"}]}}' \
      > "$base/raw-nonterminal.jsonl"
    python3 "$self_dir/derive-live-log.py" --events "$base/raw-nonterminal.jsonl" \
      --out "$base/live-nonterminal.log"
    printf 'exit=0 at=1 sentinel=0\n' > "$base/status-nonterminal"
    r=$(watch --label stream-nonterminal --pid-file "$base/pid1" \
      --status-file "$base/status-nonterminal" --log "$base/live-nonterminal.log" \
      --sentinel PLAN-DONE --raw-stream "$base/raw-nonterminal.jsonl" \
      --window 0 --start-grace 0)
    check stream-nonterminal-sentinel 15 INCOMPLETE "${r%%$'\n'*}" "${r#*$'\n'}"
    printf '%s\n' "${r#*$'\n'}" | grep -q 'stream=' \
      || bad "stream-visibility" "stream field missing: $r"
    r=$(watch --label stream-progress --pid-file "$base/none15p" \
      --status-file "$base/none15p" --log "$base/live-nonterminal.log" \
      --sentinel PLAN-DONE --raw-stream "$base/raw-nonterminal.jsonl" \
      --window 0 --start-grace 0)
    if [ "${r%%$'\n'*}" -ne 16 ] \
       || printf '%s\n' "${r#*$'\n'}" | grep -q 'verdict=DONE'; then
      bad "stream-progress-not-done" "progress/raw produced a terminal verdict: $r"
    else
      ok "stream-progress-not-done"
    fi

    # 17. stream: terminal result sentinel yields DONE from the live log only
    printf '%s\n' '{"type":"result","subtype":"success","is_error":false,"result":"finished\nPLAN-DONE"}' \
      > "$base/raw-result.jsonl"
    python3 "$self_dir/derive-live-log.py" --events "$base/raw-result.jsonl" \
      --out "$base/live-result.log"
    r=$(watch --label stream-result --pid-file "$base/none15" \
      --status-file "$base/none15" --log "$base/live-result.log" \
      --sentinel PLAN-DONE --raw-stream "$base/raw-result.jsonl" \
      --window 0 --start-grace 0)
    check stream-result-sentinel 0 DONE "${r%%$'\n'*}" "${r#*$'\n'}"

    # 18. stream: derivation failure without a terminal result never fakes DONE
    printf '%s\n' 'not json at all' \
      '{"type":"assistant","message":{"content":[{"type":"text","text":"still no result"}]}}' \
      > "$base/raw-malformed.jsonl"
    python3 "$self_dir/derive-live-log.py" --events "$base/raw-malformed.jsonl" \
      --out "$base/live-malformed.log"
    if python3 "$self_dir/derive-live-log.py" --events "$base/raw-malformed.jsonl" \
         --finish >/dev/null 2>&1; then
      bad "stream-derive-failure" "finish unexpectedly recovered a result"
    fi
    printf 'exit=0 at=1 sentinel=0\n' > "$base/status-malformed"
    r=$(watch --label stream-malformed --pid-file "$base/pid1" \
      --status-file "$base/status-malformed" --log "$base/live-malformed.log" \
      --sentinel PLAN-DONE --window 0 --start-grace 0)
    check stream-derive-failure 15 INCOMPLETE "${r%%$'\n'*}" "${r#*$'\n'}"
  else
    printf 'skip stream-nonterminal-sentinel (python3 not found)\n'
    printf 'skip stream-result-sentinel (python3 not found)\n'
    printf 'skip stream-derive-failure (python3 not found)\n'
  fi

  # 19. detached runner survives the launching shell exit
  cat > "$base/detached-writer.sh" <<'EOS'
#!/usr/bin/env bash
sleep 1
printf 'exit=0 at=1 sentinel=1\n' > "$1/status-stream-detached"
printf 'PLAN-DONE\n' > "$1/log-stream-detached.log"
EOS
  chmod +x "$base/detached-writer.sh"
  bash -c 'nohup bash "$1" "$2" </dev/null >/dev/null 2>&1 &' _ \
    "$base/detached-writer.sh" "$base"
  r=$(watch --label stream-detached --pid-file "$base/none18" \
    --status-file "$base/status-stream-detached" --log "$base/log-stream-detached.log" \
    --sentinel PLAN-DONE --window 8 --interval 1 --start-grace 4)
  check stream-detached-survives 0 DONE "${r%%$'\n'*}" "${r#*$'\n'}"

  # 20. per-window iteration token is echoed and never changes the verdict
  local it1 it2 irc1 irc2 iout1 iout2
  it1=$(watch --label iter-token --status-file "$base/status1" --log "$base/log1" \
    --sentinel PLAN-DONE --once --iter "run42-w01")
  irc1=${it1%%$'\n'*}; iout1=${it1#*$'\n'}
  it2=$(watch --label iter-token --status-file "$base/status1" --log "$base/log1" \
    --sentinel PLAN-DONE --once --iter "run42-w02")
  irc2=${it2%%$'\n'*}; iout2=${it2#*$'\n'}
  if [ "$irc1" -eq 0 ] && [ "$irc2" -eq 0 ] \
     && printf '%s\n' "$iout1" | grep -q 'iter=run42-w01' \
     && printf '%s\n' "$iout1" | grep -q 'verdict=DONE' \
     && printf '%s\n' "$iout2" | grep -q 'iter=run42-w02' \
     && printf '%s\n' "$iout2" | grep -q 'verdict=DONE' \
     && [ "$iout1" != "$iout2" ]; then
    ok iter-token-signature
  else
    bad iter-token-signature "rc1=$irc1 rc2=$irc2 tokens missing or output identical"
  fi

  if [ "$fail" -eq 0 ]; then
    printf 'SELF-TEST: %s passed, 0 failed\n' "$pass"
    return 0
  fi
  printf 'SELF-TEST: %s passed, %s failed\n' "$pass" "$fail" >&2
  return 1
}

if [ "$SELF_TEST" -eq 1 ]; then
  self_test
  exit $?
fi

if [ -n "$MANIFEST" ]; then
  [ -z "$PID_FILE$STATUS_FILE$LOG_FILE" ] || die_usage "use --manifest or single-target flags, not both"
  run_manifest "$MANIFEST"
else
  [ -n "$PID_FILE$STATUS_FILE$LOG_FILE" ] || die_usage "at least one of --pid-file/--status-file/--log is required"
  run_single
fi
