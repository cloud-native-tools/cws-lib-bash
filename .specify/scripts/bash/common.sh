#!/usr/bin/env bash
# Common functions and variables for all scripts

# Ensure the script runs in a UTF-8 locale to better support Unicode processing
ensure_utf8_locale() {
    # Always set to C.UTF-8 for consistent behavior across systems
    # C.UTF-8 is available on most modern Linux distributions and provides
    # a minimal, consistent UTF-8 environment without language-specific rules
    if locale -a 2>/dev/null | grep -qi '^C\.utf8\|^C\.UTF-8$'; then
        export LC_ALL=C.UTF-8
        export LANG=C.UTF-8
    elif locale -a 2>/dev/null | grep -qi '^en_US\.utf8\|^en_US\.UTF-8$'; then
        # Fallback to en_US.UTF-8 if C.UTF-8 is not available
        export LC_ALL=en_US.UTF-8
        export LANG=en_US.UTF-8
    else
        # If no UTF-8 locale is available, set minimal UTF-8 support
        export LC_ALL=C
        export LANG=C
        # Note: This may cause issues with non-ASCII characters, but it's the best we can do
    fi
    
    # Verify that the locale is actually UTF-8 capable
    if ! locale 2>/dev/null | grep -qi 'utf-8'; then
        echo "Warning: Unable to set UTF-8 locale. Unicode handling may be limited." >&2
    fi
}

# Unicode-aware slugify: keep letters and digits from all languages, replace others with '-'
# Usage: slugify_unicode "Some 标题 示例"  -> some-标题-示例
# Pure bash implementation - no external dependencies
slugify_unicode() {
    # Fallback (ASCII only) - pure bash implementation
    local input="$*"
    local result=""
    local prev_was_separator=0
    
    # Handle empty input
    if [ -z "$input" ]; then
        echo "feature"
        return 0
    fi
    
    # Convert to lowercase and process character by character
    # Note: This is ASCII-only but safe for all UTF-8 since we only modify ASCII ranges
    local i=0
    local len=${#input}
    
    while [ $i -lt $len ]; do
        local char="${input:$i:1}"
        
        # Check if character is alphanumeric (ASCII only check)
        # For non-ASCII UTF-8 characters, they will pass through unchanged
        case "$char" in
            [a-zA-Z0-9])
                # Alphanumeric character - add as lowercase
                if [ "$char" != "${char%[A-Z]*}" ]; then
                    # It's uppercase, convert to lowercase
                    char=$(printf "%s" "$char" | tr '[:upper:]' '[:lower:]')
                fi
                result="${result}${char}"
                prev_was_separator=0
                ;;
            *)
                # Non-alphanumeric character - treat as separator
                if [ $prev_was_separator -eq 0 ]; then
                    result="${result}-"
                    prev_was_separator=1
                fi
                ;;
        esac
        i=$((i + 1))
    done
    
    # Remove leading and trailing hyphens
    result="${result#-}"
    result="${result%-}"
    
    # Handle case where result is empty
    if [ -z "$result" ]; then
        result="feature"
    fi
    
    echo "$result"
}

# Get repository root, with fallback for non-git repositories
get_repo_root() {
    if git rev-parse --show-toplevel >/dev/null 2>&1; then
        git rev-parse --show-toplevel
    else
        # Fall back to script location for non-git repos
        local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        (cd "$script_dir/../../.." && pwd)
    fi
}

# Get current branch, with fallback for non-git repositories
get_current_branch() {
    # First check if SPECIFY_FEATURE environment variable is set
    if [[ -n "${SPECIFY_FEATURE:-}" ]]; then
        echo "$SPECIFY_FEATURE"
        return
    fi

    # Then check git if available
    if git rev-parse --abbrev-ref HEAD >/dev/null 2>&1; then
        git rev-parse --abbrev-ref HEAD
        return
    fi

    # For non-git repos, try to find the latest feature directory
    local repo_root=$(get_repo_root)
    local specs_dir="$repo_root/.specify/specs"

    if [[ -d "$specs_dir" ]]; then
        local latest_feature=""
        local highest=0

        for dir in "$specs_dir"/*; do
            if [[ -d "$dir" ]]; then
                local dirname=$(basename "$dir")
                if [[ "$dirname" =~ ^([0-9]{3})- ]]; then
                    local number=${BASH_REMATCH[1]}
                    number=$((10#$number))
                    if [[ "$number" -gt "$highest" ]]; then
                        highest=$number
                        latest_feature=$dirname
                    fi
                fi
            fi
        done

        if [[ -n "$latest_feature" ]]; then
            echo "$latest_feature"
            return
        fi
    fi

    echo "main"  # Final fallback
}

# Check if we have git available
has_git() {
    git rev-parse --show-toplevel >/dev/null 2>&1
}

check_feature_branch() {
    local branch="$1"
    local has_git_repo="$2"

    # For non-git repos, we can't enforce branch naming but still provide output
    if [[ "$has_git_repo" != "true" ]]; then
        echo "[specify] Warning: Git repository not detected; skipped branch validation" >&2
        return 0
    fi

    if [[ ! "$branch" =~ ^[0-9]{3}- ]]; then
        echo "ERROR: Not on a feature branch. Current branch: $branch" >&2
        echo "Feature branches should be named like: 001-feature-name" >&2
        return 1
    fi

    return 0
}

get_feature_dir() { echo "$1/.specify/specs/$2"; }

# Find feature directory by numeric prefix instead of exact branch match
# This allows multiple branches to work on the same spec (e.g., 004-fix-bug, 004-add-feature)
find_feature_dir_by_prefix() {
    local repo_root="$1"
    local branch_name="$2"
    local specs_dir="$repo_root/.specify/specs"

    # Extract numeric prefix from branch (e.g., "004" from "004-whatever")
    if [[ ! "$branch_name" =~ ^([0-9]{3})- ]]; then
        # If branch doesn't have numeric prefix, fall back to exact match
        echo "$specs_dir/$branch_name"
        return
    fi

    local prefix="${BASH_REMATCH[1]}"

    # Search for directories in .specify/specs/ that start with this prefix
    local matches=()
    if [[ -d "$specs_dir" ]]; then
        for dir in "$specs_dir"/"$prefix"-*; do
            if [[ -d "$dir" ]]; then
                matches+=("$(basename "$dir")")
            fi
        done
    fi

    # Handle results
    if [[ ${#matches[@]} -eq 0 ]]; then
        # No match found - return the branch name path (will fail later with clear error)
        echo "$specs_dir/$branch_name"
    elif [[ ${#matches[@]} -eq 1 ]]; then
        # Exactly one match - perfect!
        echo "$specs_dir/${matches[0]}"
    else
        # Multiple matches - this shouldn't happen with proper naming convention
        echo "ERROR: Multiple spec directories found with prefix '$prefix': ${matches[*]}" >&2
        echo "Please ensure only one spec directory exists per numeric prefix." >&2
        echo "$specs_dir/$branch_name"  # Return something to avoid breaking the script
    fi
}

get_feature_paths() {
    local repo_root=$(get_repo_root)
    local current_branch=$(get_current_branch)
    local has_git_repo="false"

    if has_git; then
        has_git_repo="true"
    fi

    # Use prefix-based lookup to support multiple branches per spec
    local feature_dir=$(find_feature_dir_by_prefix "$repo_root" "$current_branch")

    cat <<EOF
REPO_ROOT='$repo_root'
CURRENT_BRANCH='$current_branch'
HAS_GIT='$has_git_repo'
FEATURE_DIR='$feature_dir'
FEATURE_SPEC='$feature_dir/spec.md'
IMPL_PLAN='$feature_dir/plan.md'
TASKS='$feature_dir/tasks.md'
RESEARCH='$feature_dir/research.md'
DATA_MODEL='$feature_dir/data-model.md'
QUICKSTART='$feature_dir/quickstart.md'
CONTRACTS_DIR='$feature_dir/contracts'
EOF
}

check_file() { [[ -f "$1" ]] && echo "  ✓ $2" || echo "  ✗ $2"; }
check_dir() { [[ -d "$1" && -n $(ls -A "$1" 2>/dev/null) ]] && echo "  ✓ $2" || echo "  ✗ $2"; }


# Function: json_escape
# Description: Escapes a string for safe inclusion in JSON
# Usage: escaped=$(json_escape "$input")
# Parameters:
#   $1 - The input string to escape
# Returns:
#   The JSON-escaped string via stdout
json_escape() {
    local input="$1"
    local escaped=""
    local i=0
    local char
    
    # Process each character
    while [ $i -lt ${#input} ]; do
        char="${input:$i:1}"
        case "$char" in
            '"')  escaped="${escaped}\\\"";;
            '\\') escaped="${escaped}\\\\\\\\";;
            '/')  escaped="${escaped}\/";;
            $'\b') escaped="${escaped}\\b";;
            $'\f') escaped="${escaped}\\f";;
            $'\n') escaped="${escaped}\\n";;
            $'\r') escaped="${escaped}\\r";;
            $'\t') escaped="${escaped}\\t";;
            *) 
                # Check if character is a control character (ASCII 0-31)
                if [ "$(printf '%d' "'$char")" -lt 32 ]; then
                    # Convert to \uXXXX format
                    printf -v hex '%04x' "$(printf '%d' "'$char")"
                    escaped="${escaped}\\u${hex}"
                else
                    escaped="${escaped}${char}"
                fi
                ;;
        esac
        i=$((i + 1))
    done
    
    echo "$escaped"
}


# Function: safe_quote
# Description: Safely quotes a string so it can be used as a shell argument without interpretation
# Usage: safe_quoted=$(safe_quote "$input")
# Parameters:
#   $1 - The input string to quote
# Returns:
#   The safely quoted string via stdout
#   Exit code 1 if no input is provided
safe_quote() {
    local input="$1"
    
    # Check if input is provided
    if [ -z "$input" ]; then
        echo "Error: No input provided to safe_quote" >&2
        return 1
    fi
    
    # Use printf '%q' to safely quote the input
    # This handles all special characters including $, ", ', \, |, ;, &, *, ?, [, ], {, }, (, ), <, >, !, #, `, ~, ^, =, %, +, -, ., /, :, @
    printf '%q' "$input"
}


# Function: validate_input
# Description: Validates input length and basic structure
# Usage: validate_input "$input" || { echo "Invalid input"; exit 1; }
# Parameters:
#   $1 - The input string to validate
#   $2 - Maximum length (optional, defaults to 10000)
# Returns:
#   0 if input is valid, 1 if invalid
#   Error message via stderr if invalid
validate_input() {
    local input="$1"
    local max_length="${2:-10000}"
    
    # Check if input is provided
    if [ -z "$input" ]; then
        echo "Error: No input provided to validate_input" >&2
        return 1
    fi
    
    # Check input length
    local input_length="${#input}"
    if [ "$input_length" -gt "$max_length" ]; then
        echo "Error: Input exceeds maximum length of $max_length characters (actual length: $input_length)" >&2
        return 1
    fi
    
    # Basic validation passed
    return 0
}

# Function: is_valid_utf8
# Description: Checks if input contains valid UTF-8 sequences
# Usage: is_valid_utf8 "$input" || { echo "Invalid UTF-8"; exit 1; }
# Parameters:
#   $1 - The input string to validate
# Returns:
#   0 if input is valid UTF-8, 1 if invalid
# Note: This relies on the system's iconv command which should be available on most systems
is_valid_utf8() {
    local input="$1"
    
    # Check if input is provided
    if [ -z "$input" ]; then
        return 0  # Empty string is valid
    fi
    
    # Use iconv to validate UTF-8. If it fails, the input is not valid UTF-8
    if printf '%s' "$input" | iconv -f UTF-8 -t UTF-8 >/dev/null 2>&1; then
        return 0
    else
        echo "Error: Input contains invalid UTF-8 sequences" >&2
        return 1
    fi
}
