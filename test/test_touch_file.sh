#!/bin/bash

# Source the environment
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/.." && pwd)"
source "${project_root}/bin/cws_bash_env"

# Test counters
total_tests=0
passed_tests=0
failed_tests=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

function log_test_result() {
    local passed="$1"
    local desc="$2"
    if [ "$passed" == "true" ]; then
        echo -e "${GREEN}[PASS]${NC} $desc"
        passed_tests=$((passed_tests + 1))
    else
        echo -e "${RED}[FAIL]${NC} $desc"
        failed_tests=$((failed_tests + 1))
    fi
    total_tests=$((total_tests + 1))
}

# Isolated sandbox for all file operations
sandbox_dir="$(mktemp -d)"
trap 'rm -rf "${sandbox_dir}"' EXIT

echo "Running tests for touch_file..."

# 1. No argument -> failure
if touch_file >/dev/null 2>&1; then
    log_test_result "false" "No argument returns failure"
else
    log_test_result "true" "No argument returns failure"
fi

# 2. Empty string argument -> failure
if touch_file "" >/dev/null 2>&1; then
    log_test_result "false" "Empty path returns failure"
else
    log_test_result "true" "Empty path returns failure"
fi

# 3. Create a simple file in an existing directory
target="${sandbox_dir}/simple.txt"
if touch_file "${target}" >/dev/null 2>&1 && [ -f "${target}" ]; then
    log_test_result "true" "Create file in existing directory"
else
    log_test_result "false" "Create file in existing directory"
fi

# 4. Create a file with missing parent directories
target="${sandbox_dir}/a/b/c/nested.txt"
if touch_file "${target}" >/dev/null 2>&1 && [ -f "${target}" ]; then
    log_test_result "true" "Create parent directories recursively"
else
    log_test_result "false" "Create parent directories recursively"
fi

# 5. Existing file keeps its content (no truncation, unlike mv-overwrite)
target="${sandbox_dir}/keep_content.txt"
echo "important data" >"${target}"
if touch_file "${target}" >/dev/null 2>&1 && [ "$(cat "${target}")" == "important data" ]; then
    log_test_result "true" "Existing file content is preserved"
else
    log_test_result "false" "Existing file content is preserved"
fi

# 6. Existing file gets its mtime updated (real touch semantics)
target="${sandbox_dir}/mtime.txt"
echo "data" >"${target}"
# Backdate the file to year 2000 (GNU and BSD touch syntax)
touch -d '2000-01-01 00:00:00' "${target}" 2>/dev/null || touch -t 200001010000 "${target}"
now=$(date +%s)
touch_file "${target}" >/dev/null 2>&1
if is_macos; then
    mtime=$(stat -f "%m" "${target}")
else
    mtime=$(stat -c "%Y" "${target}")
fi
if [ "${mtime}" -ge "${now}" ]; then
    log_test_result "true" "Existing file timestamp is updated"
else
    log_test_result "false" "Existing file timestamp is updated. Expected mtime >= ${now}, Got: ${mtime}"
fi

# 7. Target is a directory -> failure
if touch_file "${sandbox_dir}" >/dev/null 2>&1; then
    log_test_result "false" "Directory target returns failure"
else
    log_test_result "true" "Directory target returns failure"
fi

# 8. Multiple files in one call
f1="${sandbox_dir}/multi/one.txt"
f2="${sandbox_dir}/multi/two.txt"
if touch_file "${f1}" "${f2}" >/dev/null 2>&1 && [ -f "${f1}" ] && [ -f "${f2}" ]; then
    log_test_result "true" "Multiple files in one call"
else
    log_test_result "false" "Multiple files in one call"
fi

# 9. Path containing spaces
target="${sandbox_dir}/dir with spaces/file name.txt"
if touch_file "${target}" >/dev/null 2>&1 && [ -f "${target}" ]; then
    log_test_result "true" "Path with spaces"
else
    log_test_result "false" "Path with spaces"
fi

# 10. No stray temp files left behind in the working directory
(
    cd "${sandbox_dir}" || exit 1
    touch_file "local_file.txt" >/dev/null 2>&1
)
if [ -e "${sandbox_dir}/.tmp_file" ]; then
    log_test_result "false" "No stray .tmp_file left behind"
else
    log_test_result "true" "No stray .tmp_file left behind"
fi

echo "------------------------------------------------"
echo "Tests completed: $passed_tests/$total_tests passed."

if [ "$failed_tests" -eq 0 ]; then
    exit 0
else
    exit 1
fi
