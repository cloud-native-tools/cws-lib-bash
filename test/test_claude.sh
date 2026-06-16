#!/usr/bin/env bash

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/claude.sh"

function claude() {
  printf '%s\n' "$*"
}

output=$(claude_dev "fix shellcheck")
assert_eq "--permission-mode acceptEdits fix shellcheck" "${output}" "claude_dev should enable acceptEdits and pass args"

output=$(claude_plan "review this change")
assert_eq "--permission-mode plan review this change" "${output}" "claude_plan should enable plan mode and pass args"

output=$(claude_auto "implement feature")
assert_eq "--permission-mode auto implement feature" "${output}" "claude_auto should enable auto mode and pass args"

output=$(claude_yolo "run tests")
assert_eq "--dangerously-skip-permissions run tests" "${output}" "claude_yolo should skip permissions and pass args"

output=$(claude_print "summarize")
assert_eq "--print summarize" "${output}" "claude_print should use non-interactive print mode and pass args"

output=$(claude_json "summarize")
assert_eq "--print --output-format json summarize" "${output}" "claude_json should print JSON output and pass args"

print_summary
