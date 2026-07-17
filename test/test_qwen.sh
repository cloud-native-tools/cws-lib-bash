#!/usr/bin/env bash

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/311_qwen.sh"

# Primary: mock succeeds with --dangerously-skip-permissions
function qwen() {
  printf '%s\n' "$*"
}

output=$(qwen_dev "fix shellcheck")
assert_eq "--permission-mode acceptEdits fix shellcheck" "${output}" "qwen_dev should enable acceptEdits and pass args"

output=$(qwen_yolo "run tests")
assert_eq "--dangerously-skip-permissions run tests" "${output}" "qwen_yolo should skip permissions (primary) and pass args"

# Fallback: mock fails on --dangerously-skip-permissions, triggers || branch
function qwen() {
  if [[ "$1" == "--dangerously-skip-permissions" ]]; then
    return 1
  fi
  printf '%s\n' "$*"
}

output=$(qwen_yolo "run tests")
assert_eq "--permission-mode bypassPermissions run tests" "${output}" "qwen_yolo should fallback to bypassPermissions"

# Restore simple mock for remaining tests
function qwen() {
  printf '%s\n' "$*"
}

output=$(qwen_print "summarize")
assert_eq "--print summarize" "${output}" "qwen_print should use print mode and pass args"

output=$(qwen_json "summarize")
assert_eq "--print --output-format json summarize" "${output}" "qwen_json should print JSON output and pass args"

print_summary
