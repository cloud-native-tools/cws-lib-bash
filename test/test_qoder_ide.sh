#!/usr/bin/env bash

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../profile.d/00_vars.sh"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../profile.d/02_utils.sh"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/qoder_ide.sh"

TEST_TMPDIR=$(mktemp -d)

function cleanup() {
  unset -f mv 2>/dev/null || true
  rm -rf "${TEST_TMPDIR}"
}

trap cleanup EXIT

log_header "Testing qoder ide workspace helpers"

mv() {
  command mv -v "$@"
}

workspace_file="${TEST_TMPDIR}/work.code-workspace"

resolved_workspace_file=$(_qoder_ide_workspace_ensure_file "${workspace_file}")
assert_eq "${workspace_file}" "${resolved_workspace_file}" "ensure_file should return a clean workspace path"
assert_true "[[ -f \"${workspace_file}\" ]]" "ensure_file should create the workspace file"

add_folder_output=$(qoder_ide_workspace_add_folder "${workspace_file}" "${TEST_TMPDIR}")
add_folder_status=$?
assert_eq "0" "${add_folder_status}" "add_folder should succeed with a verbose mv wrapper"
assert_eq "" "${add_folder_output}" "add_folder should not leak mv output to stdout"

added_folder=$(jq -r '.folders[0].path' "${workspace_file}")
assert_eq "${TEST_TMPDIR}" "${added_folder}" "add_folder should persist the requested folder"

log_header "Testing qoder ide bin discovery"

# Mock find to simulate qoder-server remote-cli presence
unset -f find 2>/dev/null || true

# When .qoder-server exists, qoder_ide_bin should find remote-cli/qoder
function find() {
  if [[ "$1" == "${HOME}/.qoder-server" ]] || [[ "$1" == "/root/.qoder-server" ]]; then
    echo "/mock/qoder-server/bin/test123/bin/remote-cli/qoder"
    return
  fi
  command find "$@"
}

ide_bin=$(qoder_ide_bin)
assert_eq "/mock/qoder-server/bin/test123/bin/remote-cli/qoder" "${ide_bin}" "qoder_ide_bin should find remote-cli in .qoder-server"

# Cleanup mock
unset -f find 2>/dev/null || true

print_summary
