#!/usr/bin/env bash

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/qoder_cli.sh"

# Primary: mock succeeds
function qoder() {
  printf '%s\n' "$*"
}

output=$(qoder_cli_dev "edit config")
assert_eq "--permission-mode acceptEdits edit config" "${output}" "qoder_cli_dev should enable acceptEdits and pass args"

output=$(qoder_cli_yolo "refactor all")
assert_eq "--dangerously-skip-permissions refactor all" "${output}" "qoder_cli_yolo should skip permissions (primary) and pass args"

# Fallback: mock fails on --dangerously-skip-permissions, triggers || branch
function qoder() {
  if [[ "$1" == "--dangerously-skip-permissions" ]]; then
    return 1
  fi
  printf '%s\n' "$*"
}

output=$(qoder_cli_yolo "refactor all")
assert_eq "--permission-mode bypassPermissions refactor all" "${output}" "qoder_cli_yolo should fallback to bypassPermissions"

print_summary
