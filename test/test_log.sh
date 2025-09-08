#!/bin/bash

# Test script for log and log_with_context functions
# Source the utility functions

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../profile.d/00_vars.sh"
source "${SCRIPT_DIR}/../profile.d/02_utils.sh"

# Colors for test output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CLEAR='\033[0m'

test_count=0
passed_count=0
failed_count=0

function test_result() {
  local test_name="$1"
  local expected_code="$2"
  local actual_code="$3"
  
  test_count=$((test_count + 1))
  
  if [ "${actual_code}" -eq "${expected_code}" ]; then
    echo -e "${GREEN}✓ PASS${CLEAR}: ${test_name}"
    passed_count=$((passed_count + 1))
  else
    echo -e "${RED}✗ FAIL${CLEAR}: ${test_name} (expected: ${expected_code}, actual: ${actual_code})"
    failed_count=$((failed_count + 1))
  fi
}

echo -e "${BLUE}=== Testing log function ===${CLEAR}"

echo "Testing basic log levels..."
log info "This is an info message"
test_result "log info" 0 $?

log warn "This is a warning message"
test_result "log warn" 0 $?

log error "This is an error message"
test_result "log error" 0 $?

log notice "This is a notice message"
test_result "log notice" 0 $?

log debug "This is a debug message (may not show unless CWS_DEBUG is enabled)"
test_result "log debug" 0 $?

log plain "This is a plain message"
test_result "log plain" 0 $?

log color "${GREEN}This is a colored message${CLEAR}"
test_result "log color" 0 $?

echo
echo -e "${BLUE}=== Testing log_with_context function ===${CLEAR}"

echo "Testing valid log_with_context calls..."
log_with_context info "TEST_CONTEXT" "This is an info message with context"
test_result "log_with_context with valid parameters" 0 $?

log_with_context warn "DATABASE" "Connection timeout occurred"
test_result "log_with_context warn with context" 0 $?

log_with_context error "API_CLIENT" "Request failed with status 500"
test_result "log_with_context error with context" 0 $?

log_with_context notice "STARTUP" "Service initialized successfully"
test_result "log_with_context notice with context" 0 $?

echo
echo "Testing log_with_context with multiple message parameters..."
log_with_context info "MULTI_PARAM" "Processing file" "config.json" "with size" "1024 bytes"
test_result "log_with_context with multiple parameters" 0 $?

echo
echo "Testing log_with_context error conditions..."

# Test missing level parameter
echo "Testing missing level parameter..."
log_with_context 2>/dev/null
test_result "log_with_context with no parameters" 1 $?

# Test missing context parameter
echo "Testing missing context parameter..."
log_with_context info 2>/dev/null
test_result "log_with_context with missing context" 1 $?

# Test empty level parameter
echo "Testing empty level parameter..."
log_with_context "" "CONTEXT" "message" 2>/dev/null
test_result "log_with_context with empty level" 1 $?

# Test empty context parameter
echo "Testing empty context parameter..."
log_with_context info "" "message" 2>/dev/null
test_result "log_with_context with empty context" 1 $?

echo
echo "Testing debug mode..."
echo "Current CWS_DEBUG status: ${CWS_DEBUG:-not set}"

# Test with debug enabled
export CWS_DEBUG=true
log_with_context debug "DEBUG_TEST" "This debug message should be visible"
test_result "log_with_context debug with CWS_DEBUG enabled" 0 $?

# Test with debug disabled
unset CWS_DEBUG
log_with_context debug "DEBUG_TEST" "This debug message should be hidden"
test_result "log_with_context debug with CWS_DEBUG disabled" 0 $?

echo
echo -e "${BLUE}=== Test Results Summary ===${CLEAR}"
echo "Total tests: ${test_count}"
echo -e "Passed: ${GREEN}${passed_count}${CLEAR}"
echo -e "Failed: ${RED}${failed_count}${CLEAR}"

if [ "${failed_count}" -eq 0 ]; then
  echo -e "${GREEN}All tests passed!${CLEAR}"
  exit 0
else
  echo -e "${RED}Some tests failed.${CLEAR}"
  exit 1
fi
