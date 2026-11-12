#!/usr/bin/env bash
# hook-stop.sh — Qoder CLI Stop hook template for sdd-loop-driver.
#
# The CLI passes a JSON event on stdin. This hook persists it atomically and
# tries to wake a FIFO reader. It is an EARLY completion signal only: the
# runner's exit record and the stage sentinel remain authoritative.
#
# Environment (set by the runner):
#   HOOK_EVENT_DIR  directory for event/done artifacts (default $HOME/tmp/sdd-loop-hook)
#   HOOK_STAGE      line/stage label
#   HOOK_FIFO       optional FIFO path (default <dir>/hook-done-<stage>.fifo)
#
# Emitted by `.specify/scripts/python/sync-mirrors.py`; the authority for this block is
# `contracts/mirror-projection.contract.md` C-34 / C-36. It depends on nothing
# that exists only in the source tree: it re-derives its own version line (C-36).
_script_interface_guard() {
    _sig_name="${0##*/}"
    _sig_stop=0
    for _sig_arg in "$@"; do
        if [ "$_sig_stop" -eq 1 ]; then continue; fi
        case "$_sig_arg" in
            --) _sig_stop=1 ;;
            -h|--help) return 0 ;;
            --version)
                _sig_dir="$(dirname -- "$0")"
                case "$_sig_dir" in /*) ;; *) _sig_dir="./$_sig_dir" ;; esac
                _sig_ver="unknown"
                _sig_level=0
                while [ -d "$_sig_dir" ] && [ "$_sig_level" -le 12 ]; do
                    if [ -f "$_sig_dir/pyproject.toml" ] && [ -e "$_sig_dir/.git" ]; then
                        _sig_ver="$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$_sig_dir/pyproject.toml" 2>/dev/null | head -n 1)"
                        [ -n "$_sig_ver" ] || _sig_ver="unknown"
                        break
                    fi
                    if [ "$_sig_dir" = "/" ]; then break; fi
                    _sig_dir="$(dirname -- "$_sig_dir")"
                    _sig_level=$((_sig_level + 1))
                done
                printf '%s %s\n' "$_sig_name" "$_sig_ver"
                exit 0 ;;
        esac
    done
    return 0
}
_script_interface_guard "$@"

# script-interface:86:begin (feature 086 -- generated; the rule is owned by
# `.specify/shared/definitions/script-interface-definitions.md`, its bash half by
# `.specify/scripts/bash/script-interface.sh` and `.specify/scripts/python/sync-mirrors.py`. No rule of its own.)
_sig_usage() {
    printf 'usage: %s\n' 'hook-stop.sh [arguments]'
    printf 'options:\n'
    printf '  -h, --help   print this help and exit\n'
    printf '  --version    print the script name and the framework version, then exit\n'
    printf ''side-effects:' %s\n' 'appends one event line under the hook event directory; a flag-only invocation writes nothing'
    printf ''exit-codes:' %s\n' '0 success; 1 a documented check failed; 2 argument or environment error'
}

_sig_answers() {
    _sig_want=""
    _sig_stop=0
    for _sig_tok in "$@"; do
        if [ "$_sig_stop" -eq 1 ]; then continue; fi
        case "$_sig_tok" in
            --) _sig_stop=1 ;;
            -h|--help) [ -n "$_sig_want" ] || _sig_want=help ;;
            --version) [ -n "$_sig_want" ] || _sig_want=version ;;
            -*)
                case "  " in
                    *" $_sig_tok "*) ;;
                    *)
                        if [ -z "" ]; then
                            printf 'error: unrecognized option: %s\n' "$_sig_tok" >&2
                            _sig_usage >&2
                            exit 2
                        fi
                        ;;
                esac
                ;;
        esac
    done
    case "$_sig_want" in
        help) _sig_usage; exit 0 ;;
    esac
    return 0
}

_sig_answers "$@"
set -u
# script-interface:86:end

set -u
dir="${HOOK_EVENT_DIR:-$HOME/tmp/sdd-loop-hook}"
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
