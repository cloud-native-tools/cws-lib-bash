#!/usr/bin/env bash

# Test script for debug_on() and debug_off() functions

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/.." && pwd)"

# shellcheck source=bin/cws_bash_test
source "${project_root}/bin/cws_bash_test"
# shellcheck source=bin/cws_bash_env
source "${project_root}/bin/cws_bash_env"

log_header "Testing debug_on() / debug_off() state restoration"

TMP_DEBUG_LOG=$(mktemp)
TMP_STDERR_LOG=$(mktemp)
ORIGINAL_PS4=${PS4-}

function cleanup_debug_test() {
  rm -f "${TMP_DEBUG_LOG}" "${TMP_STDERR_LOG}"
}
trap cleanup_debug_test EXIT

: >"${TMP_DEBUG_LOG}"
: >"${TMP_STDERR_LOG}"
{
  debug_on "${TMP_DEBUG_LOG}"
  echo "debug stderr message" >&2
  debug_off
  echo "restored stderr message" >&2

  if [ "${PS4-}" != "${ORIGINAL_PS4}" ]; then
    echo "PS4 was not restored" >&2
    exit 1
  fi

  case $- in
    *x*)
      echo "xtrace should be disabled after debug_off" >&2
      exit 1
      ;;
  esac
} 2>"${TMP_STDERR_LOG}"
status=$?
assert_eq "0" "${status}" "debug_off should restore PS4 and disabled xtrace state"

grep -q "debug stderr message" "${TMP_DEBUG_LOG}"
assert_success "debug_on should redirect stderr to the requested log file"

grep -q "restored stderr message" "${TMP_STDERR_LOG}"
assert_success "debug_off should restore the original stderr destination"

: >"${TMP_DEBUG_LOG}"
: >"${TMP_STDERR_LOG}"
xtrace_restored=0
set -x
{
  debug_on "${TMP_DEBUG_LOG}"
  echo "debug stderr message with existing xtrace" >&2
  debug_off

  case $- in
    *x*) xtrace_restored=1 ;;
    *) xtrace_restored=0 ;;
  esac
  set +x
} 2>"${TMP_STDERR_LOG}"
assert_eq "1" "${xtrace_restored}" "debug_off should preserve a pre-existing xtrace state"
assert_eq "${ORIGINAL_PS4}" "${PS4-}" "debug_off should restore PS4 after preserving xtrace"

grep -q "debug stderr message with existing xtrace" "${TMP_DEBUG_LOG}"
assert_success "debug_on should still redirect stderr when xtrace was already enabled"

print_summary
