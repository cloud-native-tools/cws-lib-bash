#!/usr/bin/env bash

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/iflow.sh"

# Primary: mock succeeds
function iflow() {
  printf '%s\n' "$*"
}

output=$(iflow_dev "fix typo")
assert_eq "--permission-mode acceptEdits fix typo" "${output}" "iflow_dev should enable acceptEdits and pass args"

output=$(iflow_yolo "run all")
assert_eq "--dangerously-skip-permissions run all" "${output}" "iflow_yolo should skip permissions (primary) and pass args"

# Fallback: mock fails on --dangerously-skip-permissions, triggers || branch
function iflow() {
  if [[ "$1" == "--dangerously-skip-permissions" ]]; then
    return 1
  fi
  printf '%s\n' "$*"
}

output=$(iflow_yolo "run all")
assert_eq "--permission-mode bypassPermissions run all" "${output}" "iflow_yolo should fallback to bypassPermissions"

print_summary
