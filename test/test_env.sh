#!/usr/bin/env bash

# Test script for env_append() and env_prune() functions
#
# This script tests both functions to ensure they correctly:
# - env_append: Appends new values to environment variables, prevents duplicates, handles custom separators
# - env_prune: Removes duplicate values from environment variables, handles custom separators
# - Both: Validate required parameters and handle edge cases

# Source the functions we need to test
source "$(dirname "${BASH_SOURCE[0]}")/../profile.d/00_vars.sh"
source "$(dirname "${BASH_SOURCE[0]}")/../profile.d/02_utils.sh"

# Test counter
TEST_COUNT=0
PASSED_COUNT=0
FAILED_COUNT=0

# Test helper functions
function test_start() {
  local test_name=$1
  ((TEST_COUNT++))
  echo "Test ${TEST_COUNT}: ${test_name}"
}

function test_assert_equal() {
  local expected=$1
  local actual=$2
  local message=$3
  
  if [ "${expected}" = "${actual}" ]; then
    echo "  ✓ ${message}"
    ((PASSED_COUNT++))
  else
    echo "  ✗ ${message}"
    echo "    Expected: '${expected}'"
    echo "    Actual: '${actual}'"
    ((FAILED_COUNT++))
  fi
}

function test_assert_success() {
  local exit_code=$1
  local message=$2
  
  if [ ${exit_code} -eq 0 ]; then
    echo "  ✓ ${message}"
    ((PASSED_COUNT++))
  else
    echo "  ✗ ${message}"
    echo "    Expected exit code 0, got ${exit_code}"
    ((FAILED_COUNT++))
  fi
}

function test_assert_failure() {
  local exit_code=$1
  local message=$2
  
  if [ ${exit_code} -ne 0 ]; then
    echo "  ✓ ${message}"
    ((PASSED_COUNT++))
  else
    echo "  ✗ ${message}"
    echo "    Expected non-zero exit code, got ${exit_code}"
    ((FAILED_COUNT++))
  fi
}

function cleanup_test_env() {
  unset TEST_PATH
  unset TEST_EMPTY
  unset TEST_CUSTOM_SEP
  unset TEST_SINGLE
  unset TEST_ALL_DUPS
  unset TEST_EMPTY_ITEMS
  unset TEST_COMPLEX
  unset TEST_WORKFLOW
}

echo "=========================================="
echo "Testing env_append() function"
echo "=========================================="

# Test 1: Basic functionality - append to empty environment variable
test_start "env_append - Basic append to empty environment variable"
cleanup_test_env
env_append TEST_PATH "/usr/bin"
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "/usr/bin" "${TEST_PATH}" "Should set environment variable to new value"

# Test 2: Append to existing environment variable
test_start "env_append - Append to existing environment variable"
cleanup_test_env
export TEST_PATH="/usr/bin"
env_append TEST_PATH "/usr/local/bin"
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "/usr/local/bin:/usr/bin" "${TEST_PATH}" "Should prepend new value with separator"

# Test 3: Prevent duplicate values
test_start "env_append - Prevent duplicate values"
cleanup_test_env
export TEST_PATH="/usr/bin:/usr/local/bin"
env_append TEST_PATH "/usr/bin"
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "/usr/bin:/usr/local/bin" "${TEST_PATH}" "Should not add duplicate value"

# Test 4: Custom separator
test_start "env_append - Custom separator"
cleanup_test_env
export TEST_CUSTOM_SEP="a,b,c"
env_append TEST_CUSTOM_SEP "d" ","
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "d,a,b,c" "${TEST_CUSTOM_SEP}" "Should use custom separator"

# Test 5: Prevent duplicate with custom separator
test_start "env_append - Prevent duplicate with custom separator"
cleanup_test_env
export TEST_CUSTOM_SEP="a,b,c"
env_append TEST_CUSTOM_SEP "b" ","
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "a,b,c" "${TEST_CUSTOM_SEP}" "Should not add duplicate value with custom separator"

# Test 6: Missing required parameter - env_name
test_start "env_append - Missing env_name parameter"
cleanup_test_env
env_append "" "/usr/bin" 2>/dev/null
exit_code=$?
test_assert_failure ${exit_code} "Should fail when env_name is empty"

# Test 7: Missing required parameter - new_value
test_start "env_append - Missing new_value parameter"
cleanup_test_env
env_append TEST_PATH "" 2>/dev/null
exit_code=$?
test_assert_failure ${exit_code} "Should fail when new_value is empty"

# Test 8: Complex path handling
test_start "env_append - Complex path handling with spaces and special characters"
cleanup_test_env
export TEST_PATH="/usr/bin:/usr/local/bin"
env_append TEST_PATH "/opt/my app/bin"
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "/opt/my app/bin:/usr/bin:/usr/local/bin" "${TEST_PATH}" "Should handle paths with spaces"

# Test 9: Multiple appends
test_start "env_append - Multiple appends"
cleanup_test_env
env_append TEST_PATH "/first"
env_append TEST_PATH "/second"
env_append TEST_PATH "/third"
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "/third:/second:/first" "${TEST_PATH}" "Should handle multiple appends correctly"

# Test 10: Append same value multiple times
test_start "env_append - Append same value multiple times"
cleanup_test_env
export TEST_PATH="/usr/bin"
env_append TEST_PATH "/usr/local/bin"
env_append TEST_PATH "/usr/local/bin"
env_append TEST_PATH "/usr/local/bin"
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "/usr/local/bin:/usr/bin" "${TEST_PATH}" "Should only contain unique values"

# Test 11: Edge case - single character values
test_start "env_append - Single character values"
cleanup_test_env
export TEST_PATH="a:b:c"
env_append TEST_PATH "d"
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "d:a:b:c" "${TEST_PATH}" "Should handle single character values"

# Test 12: Edge case - values containing separator in custom separator context
test_start "env_append - Values containing separator in custom separator context"
cleanup_test_env
export TEST_CUSTOM_SEP="item1|item2"
env_append TEST_CUSTOM_SEP "item:with:colons" "|"
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "item:with:colons|item1|item2" "${TEST_CUSTOM_SEP}" "Should handle values containing different separator"

echo ""
echo "=========================================="
echo "Testing env_prune() function"
echo "=========================================="

# Test 13: env_prune - Basic deduplication
test_start "env_prune - Basic deduplication"
cleanup_test_env
export TEST_PATH="/usr/bin:/usr/local/bin:/usr/bin:/opt/bin:/usr/local/bin"
env_prune TEST_PATH
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "/usr/bin:/usr/local/bin:/opt/bin" "${TEST_PATH}" "Should remove duplicates while preserving order"

# Test 14: env_prune - Empty environment variable
test_start "env_prune - Empty environment variable"
cleanup_test_env
unset TEST_EMPTY
env_prune TEST_EMPTY
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "" "${TEST_EMPTY}" "Should handle empty variable gracefully"

# Test 15: env_prune - Custom separator
test_start "env_prune - Custom separator"
cleanup_test_env
export TEST_CUSTOM_SEP="a,b,c,a,d,b,e"
env_prune TEST_CUSTOM_SEP ","
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "a,b,c,d,e" "${TEST_CUSTOM_SEP}" "Should remove duplicates with custom separator"

# Test 16: env_prune - Missing env_name parameter
test_start "env_prune - Missing env_name parameter"
cleanup_test_env
env_prune "" 2>/dev/null
exit_code=$?
test_assert_failure ${exit_code} "Should fail when env_name is empty"

# Test 17: env_prune - Single item
test_start "env_prune - Single item"
cleanup_test_env
export TEST_SINGLE="/single/path"
env_prune TEST_SINGLE
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "/single/path" "${TEST_SINGLE}" "Should handle single item correctly"

# Test 18: env_prune - All duplicates
test_start "env_prune - All duplicates"
cleanup_test_env
export TEST_ALL_DUPS="/same:/same:/same:/same"
env_prune TEST_ALL_DUPS
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "/same" "${TEST_ALL_DUPS}" "Should reduce all duplicates to single item"

# Test 19: env_prune - Empty items handling
test_start "env_prune - Empty items handling"
cleanup_test_env
export TEST_EMPTY_ITEMS="/usr/bin::/usr/local/bin:::/opt/bin:"
env_prune TEST_EMPTY_ITEMS
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "/usr/bin:/usr/local/bin:/opt/bin" "${TEST_EMPTY_ITEMS}" "Should remove empty items"

# Test 20: env_prune - Complex real-world scenario
test_start "env_prune - Complex real-world scenario"
cleanup_test_env
export TEST_COMPLEX="/usr/bin:/usr/local/bin:/opt/bin:/usr/bin:/usr/local/sbin:/opt/bin:/usr/sbin:/usr/bin"
env_prune TEST_COMPLEX
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "/usr/bin:/usr/local/bin:/opt/bin:/usr/local/sbin:/usr/sbin" "${TEST_COMPLEX}" "Should handle complex real-world duplicates"

# Test 21: env_prune - No duplicates (should remain unchanged)
test_start "env_prune - No duplicates"
cleanup_test_env
export TEST_PATH="/usr/bin:/usr/local/bin:/opt/bin"
original_value="${TEST_PATH}"
env_prune TEST_PATH
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "${original_value}" "${TEST_PATH}" "Should remain unchanged when no duplicates exist"

# Test 22: env_prune - Leading and trailing empty items
test_start "env_prune - Leading and trailing empty items"
cleanup_test_env
export TEST_PATH=":/usr/bin:/usr/local/bin:"
env_prune TEST_PATH
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "/usr/bin:/usr/local/bin" "${TEST_PATH}" "Should remove leading and trailing empty items"

echo ""
echo "=========================================="
echo "Testing combined env_append and env_prune workflow"
echo "=========================================="

# Test 23: Combined env_append and env_prune workflow
test_start "Combined env_append and env_prune workflow"
cleanup_test_env
export TEST_WORKFLOW="/usr/bin:/usr/bin:/usr/local/bin"
env_prune TEST_WORKFLOW  # First clean existing duplicates
env_append TEST_WORKFLOW "/opt/bin"  # Then append new unique value
env_append TEST_WORKFLOW "/usr/bin"  # Try to append existing (should be ignored)
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "/opt/bin:/usr/bin:/usr/local/bin" "${TEST_WORKFLOW}" "Should work well with env_append"

# Test 24: Complex workflow with custom separator
test_start "Complex workflow with custom separator"
cleanup_test_env
export TEST_WORKFLOW="a;b;a;c;b;d"
env_prune TEST_WORKFLOW ";"
env_append TEST_WORKFLOW "e" ";"
env_append TEST_WORKFLOW "a" ";"  # Should be ignored as duplicate
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "e;a;b;c;d" "${TEST_WORKFLOW}" "Should handle complex workflow with custom separator"

# Test 25: Real-world PATH manipulation scenario
test_start "Real-world PATH manipulation scenario"
cleanup_test_env
export TEST_PATH="/usr/bin:/bin:/usr/sbin:/sbin:/usr/bin:/bin"
echo "  Original PATH: ${TEST_PATH}"
env_prune TEST_PATH
echo "  After pruning: ${TEST_PATH}"
env_append TEST_PATH "/usr/local/bin"
echo "  After adding /usr/local/bin: ${TEST_PATH}"
env_append TEST_PATH "/opt/homebrew/bin"
echo "  After adding /opt/homebrew/bin: ${TEST_PATH}"
env_append TEST_PATH "/usr/bin"  # Try to add duplicate
echo "  After trying to add duplicate /usr/bin: ${TEST_PATH}"
exit_code=$?
test_assert_success ${exit_code} "Function should succeed"
test_assert_equal "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" "${TEST_PATH}" "Should handle real-world PATH scenario"

# Cleanup
cleanup_test_env

# Print summary
echo
echo "==============================================="
echo "Test Summary:"
echo "  Total tests: ${TEST_COUNT}"
echo "  Passed: ${PASSED_COUNT}"
echo "  Failed: ${FAILED_COUNT}"
echo "==============================================="

if [ ${FAILED_COUNT} -eq 0 ]; then
  echo "✓ All tests passed!"
  exit 0
else
  echo "✗ ${FAILED_COUNT} test(s) failed!"
  exit 1
fi
