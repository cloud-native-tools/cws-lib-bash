#!/usr/bin/env bash

source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
source "$(dirname "${BASH_SOURCE[0]}")/../profile.d/00_vars.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../profile.d/02_utils.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/vscode.sh"

TEST_TMPDIR=$(mktemp -d)

function cleanup() {
  unset -f mv 2>/dev/null || true
  rm -rf "${TEST_TMPDIR}"
}

trap cleanup EXIT

log_header "Testing vscode workspace helpers"

mv() {
  command mv -v "$@"
}

workspace_file="${TEST_TMPDIR}/work.code-workspace"

resolved_workspace_file=$(_vscode_workspace_ensure_file "${workspace_file}")
assert_eq "${workspace_file}" "${resolved_workspace_file}" "ensure_file should return a clean workspace path"
assert_true "[[ -f \"${workspace_file}\" ]]" "ensure_file should create the workspace file"

add_folder_output=$(vscode_workspace_add_folder "${workspace_file}" "${TEST_TMPDIR}")
add_folder_status=$?
assert_eq "0" "${add_folder_status}" "add_folder should succeed with a verbose mv wrapper"
assert_eq "" "${add_folder_output}" "add_folder should not leak mv output to stdout"

added_folder=$(jq -r '.folders[0].path' "${workspace_file}")
assert_eq "${TEST_TMPDIR}" "${added_folder}" "add_folder should persist the requested folder"

print_summary