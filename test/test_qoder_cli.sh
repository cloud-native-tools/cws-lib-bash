#!/usr/bin/env bash

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/311_qoder_cli.sh"

# `is_root` lives in profile.d and is not loaded by this isolated test; provide it
# so the yolo root-refusal path is exercised instead of erroring out.
function is_root() {
  [[ "$(id -u)" -eq 0 ]]
}

# --- Mock qodercli for standard mode tests ---
function qodercli() {
  printf '%s\n' "$*"
}

output=$(qoder_cli_dev "edit config")
assert_eq "--permission-mode accept_edits edit config" "${output}" "qoder_cli_dev should enable accept_edits and pass args"

output=$(qoder_cli_plan "review this change")
assert_eq "--permission-mode default review this change" "${output}" "qoder_cli_plan should enable default mode and pass args"

output=$(qoder_cli_auto "implement feature")
assert_eq "--permission-mode auto implement feature" "${output}" "qoder_cli_auto should enable auto mode and pass args"

output=$(qoder_cli_print "summarize")
assert_eq "--print summarize" "${output}" "qoder_cli_print should use non-interactive print mode and pass args"

output=$(qoder_cli_json "summarize")
assert_eq "--print --output-format json summarize" "${output}" "qoder_cli_json should print JSON output and pass args"

# --- Test qoder_cli_yolo root refusal (when running as root) ---
if [[ "$(id -u)" -eq 0 ]]; then
  output=$(qoder_cli_yolo "refactor all" 2>/dev/null)
  status=$?
  assert_eq "1" "${status}" "qoder_cli_yolo should refuse to run as root"
  assert_eq "" "${output}" "qoder_cli_yolo should produce no stdout when refused as root"
fi

# Override id to simulate non-root user for yolo command tests
function id() {
  if [[ "$1" == "-u" ]]; then
    echo "1000"
    return
  fi
  command id "$@"
}

# Primary: mock succeeds, --dangerously-skip-permissions is used
function qodercli() {
  printf '%s\n' "$*"
}

output=$(qoder_cli_yolo "refactor all")
assert_eq "--dangerously-skip-permissions refactor all" "${output}" "qoder_cli_yolo should skip permissions (primary) and pass args"

# Fallback: mock fails on --dangerously-skip-permissions, triggers || branch
function qodercli() {
  if [[ "$1" == "--dangerously-skip-permissions" ]]; then
    return 1
  fi
  printf '%s\n' "$*"
}

output=$(qoder_cli_yolo "refactor all")
assert_eq "--permission-mode bypass_permissions refactor all" "${output}" "qoder_cli_yolo should fallback to bypass_permissions"

# --- qoder_cli_prune: dry-run / --apply on an isolated home and tmp root ---
prune_home=$(mktemp -d)
prune_tmp=$(mktemp -d)
mkdir -p "${prune_home}/projects/p1/transcript" \
  "${prune_home}/logs/runs/old-run" \
  "${prune_home}/logs/runs/new-run" \
  "${prune_home}/logs/sessions/old-session"
printf 'x\n' >"${prune_home}/projects/p1/transcript/old.jsonl"
printf 'x\n' >"${prune_home}/projects/p1/transcript/new.jsonl"
touch -t 202001010000 "${prune_home}/projects/p1/transcript/old.jsonl"
touch -t 202001010000 "${prune_home}/logs/runs/old-run" "${prune_home}/logs/sessions/old-session"
printf 'x\n' >"${prune_tmp}/qoder-abcd-cwd"
printf 'x\n' >"${prune_tmp}/qoder-ef01-cwd"
touch -t 202001010000 "${prune_tmp}/qoder-abcd-cwd"
mkdir -p "${prune_tmp}/qodercli-natives-v1.0.1-agent" "${prune_tmp}/qodercli-natives-v9.9.99-agent"
touch -t 202001010000 "${prune_tmp}/qodercli-natives-v1.0.1-agent"

old_home="${QODER_CLI_HOME}"
old_tmp="${QODER_CLI_TMPDIR}"
QODER_CLI_HOME="${prune_home}"
QODER_CLI_TMPDIR="${prune_tmp}"

output=$(qoder_cli_prune)
assert_contains "${output}" "session_transcripts=1" "prune dry-run should count stale transcripts"
assert_contains "${output}" "run_logs=1" "prune dry-run should count stale run logs"
assert_contains "${output}" "session_dirs=1" "prune dry-run should count stale session dirs"
assert_contains "${output}" "tmp_markers=1" "prune dry-run should count stale tmp markers"
assert_contains "${output}" "stale_natives=1" "prune dry-run should count stale native caches"
assert_contains "${output}" "(dry-run)" "prune should report dry-run mode by default"
assert_true "[[ -f '${prune_home}/projects/p1/transcript/old.jsonl' ]]" "prune dry-run should not delete transcripts"

output=$(qoder_cli_prune --apply)
assert_contains "${output}" "(applied)" "prune should report applied mode with --apply"
assert_true "[[ ! -f '${prune_home}/projects/p1/transcript/old.jsonl' ]]" "prune --apply should delete stale transcripts"
assert_true "[[ -f '${prune_home}/projects/p1/transcript/new.jsonl' ]]" "prune --apply should keep fresh transcripts"
assert_true "[[ ! -d '${prune_home}/logs/runs/old-run' ]]" "prune --apply should delete stale run logs"
assert_true "[[ -d '${prune_home}/logs/runs/new-run' ]]" "prune --apply should keep fresh run logs"
assert_true "[[ ! -d '${prune_home}/logs/sessions/old-session' ]]" "prune --apply should delete stale session dirs"
assert_true "[[ ! -f '${prune_tmp}/qoder-abcd-cwd' ]]" "prune --apply should delete stale tmp markers"
assert_true "[[ -f '${prune_tmp}/qoder-ef01-cwd' ]]" "prune --apply should keep fresh tmp markers"
assert_true "[[ ! -d '${prune_tmp}/qodercli-natives-v1.0.1-agent' ]]" "prune --apply should delete stale native caches"
assert_true "[[ -d '${prune_tmp}/qodercli-natives-v9.9.99-agent' ]]" "prune --apply should keep the newest native caches"

QODER_CLI_HOME="${prune_home}.missing"
output=$(qoder_cli_prune 2>/dev/null)
status=$?
assert_eq "1" "${status}" "prune should fail when the qodercli home is missing"

QODER_CLI_HOME="${old_home}"
QODER_CLI_TMPDIR="${old_tmp}"
rm -rf "${prune_home}" "${prune_tmp}"

print_summary
