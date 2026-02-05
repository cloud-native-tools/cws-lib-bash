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

function test_json_escape() {
    local input="$1"
    local expected="$2"
    local desc="$3"

    local actual
    actual=$(json_escape "$input")

    if [ "$actual" == "$expected" ]; then
        log_test_result "true" "$desc"
    else
        log_test_result "false" "$desc. Expected: '$expected', Got: '$actual'"
    fi
}

echo "Running tests for json_escape..."

# Basic strings
test_json_escape "hello" "hello" "Simple string"
test_json_escape "hello world" "hello world" "String with spaces"

# Special characters
test_json_escape 'My "Title"' 'My \"Title\"' "String with double quotes"
test_json_escape 'C:\Windows' 'C:\\Windows' "String with backslash"
test_json_escape 'Path/To/File' 'Path\/To\/File' "String with forward slash"

# Newlines need special handling in reading args, but let's try direct passing
newline_str="Line 1
Line 2"
test_json_escape "$newline_str" 'Line 1\nLine 2' "String with newline"

# Tab
tab_str="$(printf 'col1\tcol2')"
test_json_escape "$tab_str" 'col1\tcol2' "String with tab"

# Complex mix
complex_str='Say "Hello"
to world'
test_json_escape "$complex_str" 'Say \"Hello\"\nto world' "Mixed special characters"

echo "------------------------------------------------"
echo "Tests completed: $passed_tests/$total_tests passed."

if [ "$failed_tests" -eq 0 ]; then
    exit 0
else
    exit 1
fi
