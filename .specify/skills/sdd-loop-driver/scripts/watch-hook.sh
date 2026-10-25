#!/usr/bin/env bash
# watch-hook.sh — remote-side hook wait for sdd-loop-driver.
#
# Run under the same identity as the runner (run-user), locally or via ssh:
#   ssh <alias> "su - <run-user> -c \
#     'bash --noprofile --norc -c \"bash .specify/scripts/watch-hook.sh <stage> <window> <deadline> <fifo> <done-json> <iter>\"'"
#
# Output: the event JSON (done file preferred over a FIFO line) or
# HOOK_TIMEOUT iter=<token>. The caller then runs watch-target.sh --once for the
# authoritative verdict.
#
# <iter> (or WATCH_ITER) is the per-window iteration token. Hosts such as Qoder
# reject byte-identical tool calls as a repeated-call loop, so every window MUST
# pass a literal, different token such as "<run>-w07". It is echoed on the
# timeout line only; the event JSON stays byte-identical for existing parsers.
set -u
stage="${1:-unknown}"
window="${2:-300}"
deadline="${3:-0}"
fifo="${4:-}"
donef="${5:-}"
iter="${6:-${WATCH_ITER:-na}}"

is_uint() { case "${1:-}" in ''|*[!0-9]*) return 1 ;; *) return 0 ;; esac; }
is_uint "$window" || window=300
is_uint "$deadline" || deadline=0
now=$(date +%s)
remaining="$window"
if [ "$deadline" -gt 0 ]; then
  left=$((deadline - now))
  [ "$left" -lt "$remaining" ] && remaining="$left"
fi
[ "$remaining" -lt 1 ] && remaining=1

# check-before-wait: an event written while ssh was down is not lost
if [ -n "$donef" ] && [ -s "$donef" ]; then
  cat "$donef"
  exit 0
fi

if [ -n "$fifo" ] && [ -p "$fifo" ]; then
  if read -t "$remaining" line <> "$fifo"; then
    if [ -n "$donef" ] && [ -s "$donef" ]; then
      cat "$donef"
    else
      printf 'HOOK_EVENT %s\n' "$line"
    fi
    exit 0
  fi
fi

echo "HOOK_TIMEOUT iter=$iter"
