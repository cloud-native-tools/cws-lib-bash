#!/usr/bin/env bash

source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
source "$(dirname "${BASH_SOURCE[0]}")/../profile.d/00_vars.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../profile.d/02_utils.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/312_vscode.sh"

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

vscode_workspace_add_folder "${workspace_file}" "${TEST_TMPDIR}" >/dev/null
folder_count=$(jq -r '.folders | length' "${workspace_file}")
assert_eq "1" "${folder_count}" "add_folder should not duplicate an existing folder path"

mkdir -p "${TEST_TMPDIR}/proj-a" "${TEST_TMPDIR}/proj-b"
vscode_workspace_setup "${workspace_file}" "${TEST_TMPDIR}" >/dev/null
mkdir -p "${TEST_TMPDIR}/proj-c"
vscode_workspace_setup "${workspace_file}" "${TEST_TMPDIR}" >/dev/null
total_count=$(jq -r '[.folders[].path] | length' "${workspace_file}")
distinct_count=$(jq -r '[.folders[].path] | unique | length' "${workspace_file}")
assert_eq "${distinct_count}" "${total_count}" "workspace_setup re-runs should not duplicate folder paths"

print_summary