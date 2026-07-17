#!/usr/bin/env bash

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/311_codex.sh"

function codex() {
  printf '%s\n' "$*"
}

output=$(codex_dev "fix bug")
assert_eq "--approval-mode suggest fix bug" "${output}" "codex_dev should use suggest approval mode and pass args"

output=$(codex_yolo "run tests")
assert_eq "--approval-mode full-auto run tests" "${output}" "codex_yolo should use full-auto approval mode and pass args"

output=$(codex_print "summarize")
assert_eq "--quiet summarize" "${output}" "codex_print should use quiet mode and pass args"

print_summary
