#!/usr/bin/env bash

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../profile.d/00_vars.sh"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../profile.d/02_utils.sh"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/900_mock.sh"

work=$(mktemp -d)
trap 'rm -rf "${work}"' EXIT

# --- dump_stack: /proc on Linux, ps on macOS, no root required ---
output=$(dump_stack)
assert_contains "${output}" "[$$]" "dump_stack should include the current process"

# --- argument and target validation ---
output=$(mock_it 2>&1)
assert_eq "1" "$?" "mock_it should fail without a target"
assert_contains "${output}" "Usage: mock_it" "mock_it should print usage when the target is missing"

output=$(mock_it "${work}/missing" 2>&1)
assert_eq "1" "$?" "mock_it should fail when the target does not exist"

touch "${work}/tool"
output=$(mock_it "${work}/tool" 2>&1)
assert_eq "1" "$?" "mock_it should fail when <target>.ori is absent"
assert_contains "${output}" "not executable" "mock_it should report the missing .ori companion"

# --- exec <target>.ori with the remaining args, log under MOCK_LOG_DIR ---
cat >"${work}/tool.ori" <<'EOF'
#!/usr/bin/env bash
printf 'ori-ran:%s\n' "$*"
EOF
chmod +x "${work}/tool.ori"

log_dir="${work}/logs"
output=$(MOCK_LOG_DIR="${log_dir}" mock_it "${work}/tool" alpha beta)
assert_eq "ori-ran:alpha beta" "${output}" "mock_it should exec <target>.ori with the remaining args"

mock_log="${log_dir}/tool-mock.log"
assert_true "[[ -f '${mock_log}' ]]" "mock_it should write a log under MOCK_LOG_DIR"
assert_contains "$(cat "${mock_log}")" "=======" "mock log should carry the separator header"
assert_contains "$(cat "${mock_log}")" "[$$]" "mock log should contain the caller stack"

# --- unwritable MOCK_LOG_DIR falls back to TMPDIR (macOS non-root path) ---
fallback_tmp="${work}/tmp"
mkdir -p "${fallback_tmp}"
touch "${work}/not-a-dir"
output=$(MOCK_LOG_DIR="${work}/not-a-dir" TMPDIR="${fallback_tmp}" mock_it "${work}/tool" gamma)
assert_eq "ori-ran:gamma" "${output}" "mock_it should still exec when the log dir is unusable"
assert_true "[[ -f '${fallback_tmp}/tool-mock.log' ]]" "mock_it should fall back to TMPDIR when MOCK_LOG_DIR is unusable"

# --- bare command names resolve through PATH ---
mkdir -p "${work}/binpath"
cp "${work}/tool" "${work}/binpath/mytool"
cp "${work}/tool.ori" "${work}/binpath/mytool.ori"
chmod +x "${work}/binpath/mytool.ori"
output=$(PATH="${work}/binpath:${PATH}" MOCK_LOG_DIR="${log_dir}" mock_it mytool delta)
assert_eq "ori-ran:delta" "${output}" "mock_it should resolve bare command names through PATH"

print_summary
