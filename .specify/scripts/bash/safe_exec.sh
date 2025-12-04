#!/usr/bin/env bash

set -e

# Safe command execution script for handling complex prompts and Unicode
# This script implements the requirements from the 003-support-complex-unicode feature

# Load common helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Ensure UTF-8 locale
ensure_utf8_locale || true

# Function to validate input
validate_input() {
    local input="$1"
    local max_length="${2:-10000}"
    
    if [ -z "$input" ]; then
        echo "Error: No input provided" >&2
        return 1
    fi
    
    local input_length="${#input}"
    if [ "$input_length" -gt "$max_length" ]; then
        echo "Error: Input exceeds maximum length of $max_length characters (actual length: $input_length)" >&2
        return 1
    fi
    
    # Basic UTF-8 validation
    if ! printf '%s' "$input" | iconv -f UTF-8 -t UTF-8 >/dev/null 2>&1; then
        echo "Error: Input contains invalid UTF-8 sequences" >&2
        return 1
    fi
    
    return 0
}

# Function to safely quote input
safe_quote() {
    local input="$1"
    if [ -z "$input" ]; then
        echo "Error: No input provided to safe_quote" >&2
        return 1
    fi
    printf '%q' "$input"
}

# Parse arguments
JSON_MODE=false
HELP_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --json)
            JSON_MODE=true
            shift
            ;;
        --help|-h)
            HELP_MODE=true
            shift
            ;;
        *)
            echo "Error: Unknown argument $1" >&2
            exit 1
            ;;
    esac
done

if $HELP_MODE; then
    cat <<EOF
Usage: $0 [--json]

Execute a command safely from stdin, handling special characters and Unicode correctly.

Options:
  --json          Output results in JSON format
  --help|-h       Show this help message

Examples:
  echo 'echo "Price is \$100 & it'\''s 50% off!"' | $0
  echo 'echo "Hello 世界! 👋"' | $0 --json
EOF
    exit 0
fi

# Read command from stdin
read -r user_input

# Validate input
if ! validate_input "$user_input" 10000; then
    exit 1
fi

# Execute command safely
if $JSON_MODE; then
    # Capture output and errors
    temp_stdout=$(mktemp)
    temp_stderr=$(mktemp)
    temp_exit_code=$(mktemp)
    
    # Execute command and capture everything
    if bash -c "$user_input" > "$temp_stdout" 2> "$temp_stderr"; then
        echo 0 > "$temp_exit_code"
    else
        echo $? > "$temp_exit_code"
    fi
    
    # Output JSON
    stdout_escaped=$(json_escape "$(cat "$temp_stdout")")
    stderr_escaped=$(json_escape "$(cat "$temp_stderr")")
    exit_code=$(cat "$temp_exit_code")
    
    printf '{"command_executed":true,"stdout":"%s","stderr":"%s","exit_code":%s}\n' \
        "$stdout_escaped" "$stderr_escaped" "$exit_code"
    
    # Cleanup
    rm -f "$temp_stdout" "$temp_stderr" "$temp_exit_code"
else
    # Execute directly and let output go to stdout/stderr
    bash -c "$user_input"
fi