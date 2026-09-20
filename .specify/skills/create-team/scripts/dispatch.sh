#!/usr/bin/env bash
# dispatch.sh — visible external-subagent dispatch (Spec Kit reference implementation).
#
# Implements the External Dispatch Visibility Contract defined in
# shared/definitions/subagent-definitions.md. It replaces the silent anti-pattern:
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
#                                                  falls back to ${TMPDIR:-/tmp}/spec-kit-dispatch
#                                                  when that tree is unavailable)
#   DISPATCH_FILTER     stream filter script      (default: <this script's dir>/stream-filter.py)
#   DISPATCH_CLI_FLAGS  non-interactive CLI flags (default: "-p --output-format stream-json
#                       --dangerously-skip-permissions" — valid for qodercli and claude)
#
# Exit code: the agent CLI's exit code (via PIPESTATUS), also recorded in .status.
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
# shared/definitions/agent-definitions.md (git-ignored via .specify/.gitignore), so the
# visibility triplet lands where every consumer expects it. Outside a Spec Kit tree the
# temp-dir fallback keeps the script usable.
if [[ -n "${DISPATCH_LOG_DIR:-}" ]]; then
  LOG_DIR="${DISPATCH_LOG_DIR}"
elif [[ -d ".specify/agents/execution" ]]; then
  LOG_DIR=".specify/agents/execution/logs"
else
  LOG_DIR="${TMPDIR:-/tmp}/spec-kit-dispatch"
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
