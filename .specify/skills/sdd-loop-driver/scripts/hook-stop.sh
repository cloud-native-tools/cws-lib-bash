#!/usr/bin/env bash
# hook-stop.sh — Qoder CLI Stop hook template for sdd-loop-driver.
#
# The CLI passes a JSON event on stdin. This hook persists it atomically and
# tries to wake a FIFO reader. It is an EARLY completion signal only: the
# runner's exit record and the stage sentinel remain authoritative.
#
# Environment (set by the runner):
#   HOOK_EVENT_DIR  directory for event/done artifacts (default /tmp/sdd-loop-hook)
#   HOOK_STAGE      line/stage label
#   HOOK_FIFO       optional FIFO path (default <dir>/hook-done-<stage>.fifo)
set -u
dir="${HOOK_EVENT_DIR:-/tmp/sdd-loop-hook}"
stage="${HOOK_STAGE:-unknown}"
fifo="${HOOK_FIFO:-$dir/hook-done-$stage.fifo}"
eventf="$dir/hook-event-$stage.json"
mkdir -p "$dir" 2>/dev/null || true
umask 077
input=$(cat 2>/dev/null || true)
ts=$(date +%s)
tmp="$eventf.tmp.$$"
{
  printf '{"stage":"%s","ts":%s,"hook_event":' "$stage" "$ts"
  printf '%s' "${input:-null}"
  printf '}\n'
} > "$tmp" 2>/dev/null && mv "$tmp" "$eventf" 2>/dev/null || rm -f "$tmp"
# The FIFO write is best-effort: timeout prevents a writer from hanging when
# no reader is attached (macOS without timeout simply skips it; the JSON is
# the durable signal and the watcher checks it before waiting).
if [ -p "$fifo" ] && command -v timeout >/dev/null 2>&1; then
  ( printf 'STOP %s %s\n' "$stage" "$ts" | timeout 5 tee "$fifo" >/dev/null 2>&1 ) &
fi
exit 0
