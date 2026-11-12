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
    printf 'usage: %s\n' 'watch-hook.sh [arguments]'
    printf 'options:\n'
    printf '  -h, --help   print this help and exit\n'
    printf '  --version    print the script name and the framework version, then exit\n'
    printf ''side-effects:' %s\n' 'read-only; a flag-only invocation writes nothing'
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
