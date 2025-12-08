#!/bin/bash

# Test script for net_valid_ipv4 function
# This script tests various valid and invalid IPv4 addresses to ensure
# the net_valid_ipv4 function works correctly

# Source the environment and network functions
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
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

function test_case() {
    local ip="$1"
    local expected="$2"
    local description="$3"
    
    total_tests=$((total_tests + 1))
    
    printf "Test %2d: %-35s " "${total_tests}" "${description}"
    
    if net_valid_ipv4 "${ip}"; then
        actual="valid"
    else
        actual="invalid"
    fi
    
    if [ "${actual}" = "${expected}" ]; then
        printf "[${GREEN}PASS${NC}] %s\n" "${ip}"
        passed_tests=$((passed_tests + 1))
    else
        printf "[${RED}FAIL${NC}] %s (expected: %s, got: %s)\n" "${ip}" "${expected}" "${actual}"
        failed_tests=$((failed_tests + 1))
    fi
}

function print_summary() {
    echo
    echo "==============================================="
    echo "Test Summary:"
    echo "  Total tests: ${total_tests}"
    printf "  Passed: ${GREEN}%d${NC}\n" "${passed_tests}"
    printf "  Failed: ${RED}%d${NC}\n" "${failed_tests}"
    echo "==============================================="
    
    if [ "${failed_tests}" -eq 0 ]; then
        printf "${GREEN}All tests passed!${NC}\n"
        return 0
    else
        printf "${RED}Some tests failed!${NC}\n"
        return 1
    fi
}

echo "Testing net_valid_ipv4 function..."
echo "==============================================="

# Valid IPv4 addresses
test_case "192.168.1.1" "valid" "Standard private IP"
test_case "10.0.0.1" "valid" "Class A private IP"
test_case "172.16.0.1" "valid" "Class B private IP"
test_case "127.0.0.1" "valid" "Loopback address"
test_case "0.0.0.0" "valid" "All zeros"
test_case "255.255.255.255" "valid" "All 255s (broadcast)"
test_case "8.8.8.8" "valid" "Google DNS"
test_case "1.1.1.1" "valid" "Cloudflare DNS"
test_case "203.0.113.1" "valid" "TEST-NET-3"
test_case "198.51.100.1" "valid" "TEST-NET-2"
test_case "192.0.2.1" "valid" "TEST-NET-1"
test_case "169.254.1.1" "valid" "Link-local"
test_case "224.0.0.1" "valid" "Multicast"
test_case "239.255.255.255" "valid" "Multicast boundary"

# Edge cases - valid
test_case "0.0.0.1" "valid" "Min with 1"
test_case "255.0.0.0" "valid" "Max first octet"
test_case "1.2.3.4" "valid" "Simple sequence"

# Invalid IPv4 addresses - format issues
test_case "256.1.1.1" "invalid" "First octet > 255"
test_case "1.256.1.1" "invalid" "Second octet > 255"
test_case "1.1.256.1" "invalid" "Third octet > 255"
test_case "1.1.1.256" "invalid" "Fourth octet > 255"
test_case "300.300.300.300" "invalid" "All octets > 255"
test_case "192.168.1" "invalid" "Missing octet"
test_case "192.168.1.1.1" "invalid" "Extra octet"
test_case "192.168..1" "invalid" "Empty octet"
test_case ".192.168.1.1" "invalid" "Leading dot"
test_case "192.168.1.1." "invalid" "Trailing dot"
test_case "192.168.1.1.." "invalid" "Double trailing dot"

# Invalid IPv4 addresses - character issues
test_case "192.168.1.a" "invalid" "Letter in octet"
test_case "192.168.1.-1" "invalid" "Negative number"
test_case "192.168.1.01" "invalid" "Leading zero (2 digits)"
test_case "192.168.1.001" "invalid" "Leading zeros (3 digits)"
test_case "192.168.01.1" "invalid" "Leading zero in 3rd octet"
test_case "01.168.1.1" "invalid" "Leading zero in 1st octet"
test_case "192 168 1 1" "invalid" "Spaces instead of dots"
test_case "192,168,1,1" "invalid" "Commas instead of dots"
test_case "192-168-1-1" "invalid" "Hyphens instead of dots"

# Invalid IPv4 addresses - empty and special cases
test_case "" "invalid" "Empty string"
test_case " " "invalid" "Single space"
test_case "..." "invalid" "Only dots"
test_case "192.168.1.1 " "invalid" "Trailing space"
test_case " 192.168.1.1" "invalid" "Leading space"
test_case "192. 168.1.1" "invalid" "Space in middle"

# Invalid IPv4 addresses - very long numbers
test_case "1921681111111111111111111111111.1.1.1" "invalid" "Extremely long first octet"
test_case "192.1681111111111111111111111111111.1.1" "invalid" "Extremely long second octet"

# Invalid IPv4 addresses - special characters
test_case "192.168.1.1#" "invalid" "Hash character"
test_case "192.168.1.1@" "invalid" "At symbol"
test_case "192.168.1.1%" "invalid" "Percent symbol"
test_case "192.168.1.1$" "invalid" "Dollar symbol"

# Edge cases with leading zeros (should be invalid per function logic)
test_case "192.168.001.1" "invalid" "Leading zeros in third octet"
test_case "0192.168.1.1" "invalid" "Leading zero making 4-digit number"

print_summary
exit $?
