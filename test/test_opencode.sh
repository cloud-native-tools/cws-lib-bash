#!/usr/bin/env bash

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/opencode.sh"

# Primary: mock succeeds with --yolo
function opencode() {
  printf '%s\n' "$*"
}

output=$(opencode_dev "fix lint")
assert_eq "--auto-approve fix lint" "${output}" "opencode_dev should enable auto-approve and pass args"

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

print_summary
