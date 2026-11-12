#!/usr/bin/env bash
# dispatch.sh — visible external-subagent dispatch (Spec Kit reference implementation).
#
# Implements the External Dispatch Visibility Contract defined in
# .specify/shared/definitions/subagent-definitions.md. It replaces the silent anti-pattern:
#
#   qodercli -p "<prompt>" > agent.log 2>&1 &   # buffered until exit -> zero progress signal
#
# by streaming agent CLI events (--output-format stream-json) through a compacting
# filter, producing a real-time artifact triplet per dispatched agent:
#
#   <log-dir>/<label>.live.log   compact progress lines (tailable / monitorable)
#   <log-dir>/<label>.jsonl      raw stream-json events (forensics)
#   <log-dir>/<label>.status     "<label> exit=<code>" recorded at completion
#
# Usage:
#   dispatch.sh <label> <workdir> <prompt-file> [-- <extra cli args>]
#
# Environment overrides:
#   DISPATCH_CLI        agent CLI binary          (default: qodercli; claude also works)
#   DISPATCH_LOG_DIR    artifact directory        (default: .specify/agents/execution/logs,
#                                                  which .specify/.gitignore already ignores;
#                                                  falls back to $HOME/tmp/spec-kit/dispatch
#                                                  when that tree is unavailable)
#   DISPATCH_FILTER     stream filter script      (default: <this script's dir>/stream-filter.py)
#   DISPATCH_CLI_FLAGS  non-interactive CLI flags (default: "-p --output-format stream-json
#                       --dangerously-skip-permissions" — valid for qodercli and claude)
#
# Exit code: the agent CLI's exit code (via PIPESTATUS), also recorded in .status.
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
    printf 'usage: %s\n' 'dispatch.sh <label> <workdir> <prompt-file> [-- <extra cli args>]'
    printf 'options:\n'
    printf '  -h, --help   print this help and exit\n'
    printf '  --version    print the script name and the framework version, then exit\n'
    printf ''side-effects:' %s\n' "writes the dispatched run's JSONL and live log under the workdir; a flag-only invocation writes nothing"
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

set -uo pipefail

if [[ $# -lt 3 ]]; then
  echo "usage: dispatch.sh <label> <workdir> <prompt-file> [-- <extra cli args>]" >&2
  exit 2
fi

LABEL="$1"
WORKDIR="$2"
PROMPT_FILE="$3"
shift 3
[[ "${1:-}" == "--" ]] && shift

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI="${DISPATCH_CLI:-qodercli}"
# Default to the tracked-repo runtime-log location documented in
# .specify/shared/definitions/agent-definitions.md (git-ignored via .specify/.gitignore), so the
# visibility triplet lands where every consumer expects it. Outside a Spec Kit tree the
# temp-dir fallback keeps the script usable.
if [[ -n "${DISPATCH_LOG_DIR:-}" ]]; then
  LOG_DIR="${DISPATCH_LOG_DIR}"
elif [[ -d ".specify/agents/execution" ]]; then
  LOG_DIR=".specify/agents/execution/logs"
else
  LOG_DIR="$HOME/tmp/spec-kit/dispatch"
fi
FILTER="${DISPATCH_FILTER:-${SCRIPT_DIR}/stream-filter.py}"
CLI_FLAGS="${DISPATCH_CLI_FLAGS:--p --output-format stream-json --dangerously-skip-permissions}"

mkdir -p "${LOG_DIR}"
cd "${WORKDIR}" || exit 1

# stream-json -> raw jsonl (tee) -> compact progress lines (filter) -> live log + stdout
# shellcheck disable=SC2086
"${CLI}" ${CLI_FLAGS} "$@" "$(cat "${PROMPT_FILE}")" 2>&1 \
  | tee "${LOG_DIR}/${LABEL}.jsonl" \
  | python3 -u "${FILTER}" "${LABEL}" \
  | tee "${LOG_DIR}/${LABEL}.live.log"

rc=${PIPESTATUS[0]}
echo "${LABEL} exit=${rc}" | tee "${LOG_DIR}/${LABEL}.status"
exit "${rc}"
