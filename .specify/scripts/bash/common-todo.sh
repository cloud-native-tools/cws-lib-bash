#!/usr/bin/env bash
# common-todo.sh — Shared helper functions for /speckit.todo search-todo.sh script
# 
# This file provides reusable functions for:
# - Repository root discovery
# - JSON string escaping (RFC 8259)
# - Path normalization and validation
# - File encoding detection
# - Default exclude list management

set -euo pipefail

# ============================================================================
# Repository Root Discovery
# ============================================================================

# find_repo_root: Locates the git repository root or workspace root
# 
# Strategy:
# 1. If GIT_DIR is set, use it
# 2. Otherwise, walk up from pwd looking for .git directory
# 3. If no .git found, use current directory as fallback
#
# Returns: Prints absolute path to repository root
# Exit: 0 on success
find_repo_root() {
    local dir
    if [[ -n "${GIT_DIR:-}" ]]; then
        dir="$GIT_DIR"
    else
        dir="$(pwd)"
    fi
    
    while [[ "$dir" != "/" ]]; do
        if [[ -d "$dir/.git" ]]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    
    # No .git found, use current directory
    echo "$(pwd)"
    return 0
}

# ============================================================================
# JSON String Escaping (RFC 8259)
# ============================================================================

# json_escape_string: Escapes a string for JSON output per RFC 8259
#
# Handles:
# - Backslash → \\
# - Double quote → \"
# - Newline → \n
# - Carriage return → \r
# - Tab → \t
# - Control characters (0x00-0x1F) → \u00XX
#
# Arguments:
#   $1: String to escape
#
# Returns: Escaped string suitable for JSON output
json_escape_string() {
    local input="${1:-}"
    
    # Use printf to handle escape sequences
    # Order matters: escape backslashes first!
    input="${input//\\/\\\\}"
    input="${input//\"/\\\"}"
    input="${input//$'\n'/\\n}"
    input="${input//$'\r'/\\r}"
    input="${input//$'\t'/\\t}"
    
    # Handle other control characters (0x00-0x1F except those already handled)
    # Use Python for robust handling if available, otherwise use sed
    if command -v python3 &> /dev/null; then
        python3 -c "
import sys
import re

def escape_control(s):
    # Escape control characters 0x00-0x1F except \\n \\r \\t (already handled)
    result = []
    for ch in s:
        code = ord(ch)
        if code < 0x20 and ch not in '\n\r\t':
            result.append(f'\\\\u{code:04x}')
        else:
            result.append(ch)
    return ''.join(result)

sys.stdout.write(escape_control(sys.argv[1]))
" "$input"
    else
        # Fallback: just echo the input (may not handle all control chars)
        echo "$input"
    fi
}

# ============================================================================
# Path Normalization and Validation
# ============================================================================

# normalize_path: Converts a path to workspace-relative format
#
# Arguments:
#   $1: Absolute or relative path
#   $2: Workspace root (absolute path)
#
# Returns: Workspace-relative path (e.g., "src/api.py")
normalize_path() {
    local path="$1"
    local root="$2"
    
    # Remove workspace root prefix
    if [[ "$path" == "$root"/* ]]; then
        echo "${path#$root/}"
    else
        # Path is already relative or outside root
        echo "$path"
    fi
}

# validate_path_in_workspace: Checks if a path is within the workspace root
#
# Arguments:
#   $1: Path to validate
#   $2: Workspace root
#
# Returns: 0 if path is within workspace, 1 otherwise
validate_path_in_workspace() {
    local path="$(realpath -m "$1")"
    local root="$(realpath -m "$2")"
    
    if [[ "$path" == "$root"/* ]]; then
        return 0
    else
        return 1
    fi
}

# ============================================================================
# File Encoding Detection
# ============================================================================

# is_utf8_file: Checks if a file is valid UTF-8 text
#
# Arguments:
#   $1: File path
#
# Returns: 0 if UTF-8 text, 1 if binary or invalid UTF-8
is_utf8_file() {
    local file="$1"
    
    # Check if file is readable
    if [[ ! -r "$file" ]]; then
        return 1
    fi
    
    # Check if file is empty
    if [[ ! -s "$file" ]]; then
        return 0  # Empty files are considered UTF-8
    fi
    
    # Use file command to check encoding
    local file_type
    file_type=$(file -b --mime-encoding "$file" 2>/dev/null || echo "binary")
    
    case "$file_type" in
        utf-8|ascii|us-ascii|iso-8859-*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# ============================================================================
# Default Exclude List
# ============================================================================

# get_default_excludes: Returns the default exclude patterns
#
# These patterns match common directories that should not be scanned:
# - Version control: .git/, .svn/, .hg/
# - Dependencies: node_modules/, vendor/, .venv/, venv/
# - Build artifacts: __pycache__/, dist/, build/, target/
# - IDE files: .idea/, .vscode/
# - OS files: .DS_Store, Thumbs.db
get_default_excludes() {
    cat <<'EOF'
\.git/
\.svn/
\.hg/
node_modules/
vendor/
\.venv/
venv/
__pycache__/
dist/
build/
target/
\.idea/
\.vscode/
\.DS_Store
Thumbs\.db
EOF
}

# matches_exclude_pattern: Checks if a path matches any exclude pattern
#
# Arguments:
#   $1: Path to check
#   $2: Exclude patterns (newline-separated regex patterns)
#
# Returns: 0 if path matches any pattern, 1 otherwise
matches_exclude_pattern() {
    local path="$1"
    local patterns="$2"
    
    while IFS= read -r pattern; do
        [[ -z "$pattern" ]] && continue
        if echo "$path" | grep -qE "$pattern"; then
            return 0
        fi
    done <<< "$patterns"
    
    return 1
}

# ============================================================================
# File Size Check
# ============================================================================

# is_file_too_large: Checks if file exceeds maximum size threshold
#
# Arguments:
#   $1: File path
#   $2: Max size in bytes (default: 16MB = 16777216)
#
# Returns: 0 if file is too large, 1 if within limit
is_file_too_large() {
    local file="$1"
    local max_size="${2:-16777216}"  # 16MB default
    
    local file_size
    file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0)
    
    if (( file_size > max_size )); then
        return 0
    else
        return 1
    fi
}
