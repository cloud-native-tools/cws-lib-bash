#!/usr/bin/env bash

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/311_opencode.sh"

# Primary: mock succeeds with --yolo
function opencode() {
  printf '%s\n' "$*"
}

output=$(opencode_dev "fix lint")
assert_eq "--auto-approve fix lint" "${output}" "opencode_dev should enable auto-approve and pass args"

# --- Test opencode_yolo root refusal (when running as root) ---
if [[ "$(id -u)" -eq 0 ]]; then
  output=$(opencode_yolo "deploy app" 2>/dev/null)
  status=$?
  assert_eq "1" "${status}" "opencode_yolo should refuse to run as root"
  assert_eq "" "${output}" "opencode_yolo should produce no stdout when refused as root"
fi

# Override id to simulate non-root user for yolo command tests
function id() {
  if [[ "$1" == "-u" ]]; then
    echo "1000"
    return
  fi
  command id "$@"
}

output=$(opencode_yolo "deploy app")
assert_eq "--yolo deploy app" "${output}" "opencode_yolo should use --yolo (primary) and pass args"

# Fallback: mock fails on --yolo, triggers || branch
function opencode() {
  if [[ "$1" == "--yolo" ]]; then
    return 1
  fi
  printf '%s\n' "$*"
}

output=$(opencode_yolo "deploy app")
assert_eq "--auto-approve deploy app" "${output}" "opencode_yolo should fallback to --auto-approve"

# Restore simple mock for remaining tests
function opencode() {
  printf '%s\n' "$*"
}

output=$(opencode_auto "implement feature")
assert_eq "--auto-approve implement feature" "${output}" "opencode_auto should auto-approve and pass args"

output=$(opencode_print "summarize")
assert_eq "run summarize" "${output}" "opencode_print should use non-interactive run mode and pass args"

output=$(opencode_json "summarize")
assert_eq "run --format json summarize" "${output}" "opencode_json should output JSON via run and pass args"

print_summary
