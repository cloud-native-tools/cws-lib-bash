#!/bin/bash

# Test script for net_my_ip function
# This script tests all available IP service URLs and ranks them by reliability

# Source the network functions
source "${BASH_SOURCE%/*}/../profile.d/06_network.sh"

# Test individual URL function
test_url() {
    local url="$1"
    local timeout="${2:-3}"
    echo "Testing URL: $url"
    
    # Capture output and exit code
    local result
    result=$(net_my_ip "$url" "$timeout" 2>/dev/null)
    local exit_code=$?
    
    if [ $exit_code -eq 0 ] && [ -n "$result" ]; then
        echo "  ✓ SUCCESS: Got IP $result"
        return 0
    else
        echo "  ✗ FAILED: No valid IP returned"
        return 1
    fi
}

# Test function with invalid URL
test_invalid_url() {
    echo "Testing invalid URL..."
    local result
    result=$(net_my_ip "invalid-url-that-does-not-exist.com" 2>/dev/null)
    local exit_code=$?
    
    if [ $exit_code -ne 0 ] || [ -z "$result" ]; then
        echo "  ✓ SUCCESS: Invalid URL properly handled (exit code: $exit_code)"
        return 0
    else
        echo "  ✗ FAILED: Invalid URL should not return valid IP"
        return 1
    fi
}

# Test all URLs and collect results
test_all_urls() {
    local urls=(
        "cip.cc"
        "ipv4.seeip.org"
        "myip.ipip.net/"
        "api.ipify.org"
        "ifconfig.me"
        "ipinfo.io/ip"
        "ipx.sh"
        "ip.sb"
        "ident.me"
        "ifconfig.io"
        "httpbin.org/ip"
    )
    
    local successful_urls=()
    local failed_urls=()
    
    echo "Testing all IP service URLs..."
    echo "================================"
    
    for url in "${urls[@]}"; do
        if test_url "$url" 5; then
            successful_urls+=("$url")
        else
            failed_urls+=("$url")
        fi
        echo ""
    done
    
    echo "================================"
    echo "SUMMARY:"
    echo "Successful URLs (${#successful_urls[@]}):"
    for url in "${successful_urls[@]}"; do
        echo "  - $url"
    done
    
    echo ""
    echo "Failed URLs (${#failed_urls[@]}):"
    for url in "${failed_urls[@]}"; do
        echo "  - $url"
    done
    
    echo ""
    echo "Recommended URL order (successful ones first):"
    for url in "${successful_urls[@]}"; do
        echo "  \"$url\""
    done
    for url in "${failed_urls[@]}"; do
        echo "  \"$url\""
    done
}

# Test the default behavior (without specifying URL)
test_default_behavior() {
    echo "Testing default behavior (no URL specified)..."
    echo "=============================================="
    
    local result
    result=$(net_my_ip 2>/dev/null)
    local exit_code=$?
    
    if [ $exit_code -eq 0 ] && [ -n "$result" ]; then
        echo "✓ SUCCESS: Default behavior returned IP: $result"
        return 0
    else
        echo "✗ FAILED: Default behavior returned no valid IP"
        return 1
    fi
}

# Test function with timeout parameter
test_with_timeout() {
    echo "Testing with custom timeout (1 second)..."
    local result
    result=$(net_my_ip "" 1 2>/dev/null)
    local exit_code=$?
    
    if [ $exit_code -eq 0 ] && [ -n "$result" ]; then
        echo "  ✓ SUCCESS: Custom timeout worked, got IP: $result"
        return 0
    elif [ $exit_code -ne 0 ]; then
        echo "  ✓ ACCEPTABLE: Custom timeout may have caused failure (exit code: $exit_code)"
        return 0
    else
        echo "  ✗ UNEXPECTED: Empty result with zero exit code"
        return 1
    fi
}

# Main test execution
main() {
    echo "Net My IP Function Tests"
    echo "========================"
    echo ""
    
    # Test default behavior first
    test_default_behavior
    echo ""
    
    # Test with timeout
    test_with_timeout
    echo ""
    
    # Test invalid URL
    test_invalid_url
    echo ""
    
    # Test all individual URLs
    test_all_urls
}

# Run the tests
main "$@"
