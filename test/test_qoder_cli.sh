#!/usr/bin/env bash

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/311_qoder_cli.sh"

# --- Mock qodercli for standard mode tests ---
function qodercli() {
  printf '%s\n' "$*"
}

output=$(qoder_cli_dev "edit config")
assert_eq "--permission-mode accept_edits edit config" "${output}" "qoder_cli_dev should enable accept_edits and pass args"

output=$(qoder_cli_plan "review this change")
assert_eq "--permission-mode default review this change" "${output}" "qoder_cli_plan should enable default mode and pass args"

output=$(qoder_cli_auto "implement feature")
assert_eq "--permission-mode auto implement feature" "${output}" "qoder_cli_auto should enable auto mode and pass args"

output=$(qoder_cli_print "summarize")
assert_eq "--print summarize" "${output}" "qoder_cli_print should use non-interactive print mode and pass args"

output=$(qoder_cli_json "summarize")
assert_eq "--print --output-format json summarize" "${output}" "qoder_cli_json should print JSON output and pass args"

# --- Test qoder_cli_yolo root refusal (when running as root) ---
if [[ "$(id -u)" -eq 0 ]]; then
  output=$(qoder_cli_yolo "refactor all" 2>/dev/null)
  status=$?
  assert_eq "1" "${status}" "qoder_cli_yolo should refuse to run as root"
  assert_eq "" "${output}" "qoder_cli_yolo should produce no stdout when refused as root"
fi

# Override id to simulate non-root user for yolo command tests
function id() {
  if [[ "$1" == "-u" ]]; then
    echo "1000"
    return
  fi
  command id "$@"
}

# Primary: mock succeeds, --dangerously-skip-permissions is used
function qodercli() {
  printf '%s\n' "$*"
}

output=$(qoder_cli_yolo "refactor all")
assert_eq "--dangerously-skip-permissions refactor all" "${output}" "qoder_cli_yolo should skip permissions (primary) and pass args"

# Fallback: mock fails on --dangerously-skip-permissions, triggers || branch
function qodercli() {
  if [[ "$1" == "--dangerously-skip-permissions" ]]; then
    return 1
  fi
  printf '%s\n' "$*"
}

output=$(qoder_cli_yolo "refactor all")
assert_eq "--permission-mode bypass_permissions refactor all" "${output}" "qoder_cli_yolo should fallback to bypass_permissions"

print_summary
