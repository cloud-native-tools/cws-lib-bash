#!/usr/bin/env bash
# Common functions and variables for all scripts

# Source shared environment configurations
[ -f "${CWS_LIB_BASH_HOME}/bin/cws_bash_env" ] && source "${CWS_LIB_BASH_HOME}/bin/cws_bash_env"
[ -f "${CWS_LIB_PYTHON_HOME}/bin/cws_py_env" ] && source "${CWS_LIB_PYTHON_HOME}/bin/cws_py_env"

check_dependency() {
  if ! command -v git &> /dev/null; then
    echo "Error: git is not installed." >&2
    return 1
  fi

  if [ -z "${CWS_LIB_BASH_HOME}" ]; then
    echo "Error: CWS_LIB_BASH_HOME environment variable is not set." >&2
    return 1
  fi

  if [ ! -f "${CWS_LIB_BASH_HOME}/bin/cws_bash_env" ]; then
    echo "Error: cws-lib-bash is not correctly installed. File not found: ${CWS_LIB_BASH_HOME}/bin/cws_bash_env" >&2
    return 1
  fi

  if [ -z "${CWS_LIB_PYTHON_HOME}" ]; then
    echo "Error: CWS_LIB_PYTHON_HOME environment variable is not set." >&2
    return 1
  fi

  if [ ! -f "${CWS_LIB_PYTHON_HOME}/bin/cws_py_env" ]; then
    echo "Error: cws-lib-python is not correctly installed. File not found: ${CWS_LIB_PYTHON_HOME}/bin/cws_py_env" >&2
    return 1
  fi
  
  return 0
}

if ! check_dependency; then
    echo "Dependency check failed. Initializing dependencies are required." >&2
    exit 1
fi


check_feature_branch() {
  local branch="$1"
  local has_git_repo="$2"

  # For non-git repos, we can't enforce branch naming but still provide output
  if [[ $has_git_repo != "true" ]]; then
    echo "[specify] Warning: Git repository not detected; skipped branch validation" >&2
    return 0
  fi

  if [[ ! $branch =~ ^[0-9]+- ]]; then
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
  if [[ ! $branch_name =~ ^([0-9]+)- ]]; then
    # If branch doesn't have numeric prefix, fall back to exact match
    echo "$specs_dir/$branch_name"
    return
  fi

  local prefix="${BASH_REMATCH[1]}"

  # Search for directories in .specify/specs/ that start with this prefix
  local matches=()
  if [[ -d $specs_dir ]]; then
    for dir in "$specs_dir"/"$prefix"-*; do
      if [[ -d $dir ]]; then
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
    echo "$specs_dir/$branch_name" # Return something to avoid breaking the script
  fi
}

get_feature_paths() {
  local repo_root=$(git_repo_root)
  local current_branch=$(git_current_branch)
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
REQUIREMENTS_DIR='$feature_dir'
FEATURE_SPEC='$feature_dir/requirements.md'
IMPL_PLAN='$feature_dir/plan.md'
TASKS='$feature_dir/tasks.md'
RESEARCH='$feature_dir/research.md'
DATA_MODEL='$feature_dir/data-model.md'
QUICKSTART='$feature_dir/quickstart.md'
CONTRACTS_DIR='$feature_dir/contracts'
EOF
}

check_file() { [[ -f $1 ]] && echo "  ✓ $2" || echo "  ✗ $2"; }
check_dir() { [[ -d $1 && -n $(ls -A "$1" 2>/dev/null) ]] && echo "  ✓ $2" || echo "  ✗ $2"; }

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
    return 0 # Empty string is valid
  fi

  # Use iconv to validate UTF-8. If it fails, the input is not valid UTF-8
  if printf '%s' "$input" | iconv -f UTF-8 -t UTF-8 >/dev/null 2>&1; then
    return 0
  else
    echo "Error: Input contains invalid UTF-8 sequences" >&2
    return 1
  fi
}

# --- Skill Management Functions ---

# Validate skill name
# Returns 0 if valid, 1 if invalid
validate_skill_name() {
  local name="$1"
  if [[ ! $name =~ ^[a-zA-Z0-9_-]+$ ]]; then
    return 1
  fi
  return 0
}

# Create standard skill directory structure
# Usage: create_skill_structure "skill_path"
create_skill_structure() {
  local skill_path="$1"

  mkdir -p "$skill_path"
  mkdir -p "$skill_path/scripts"
  mkdir -p "$skill_path/references"
  mkdir -p "$skill_path/assets"
}

# Report error
# Usage: report_error "message" [json_mode]
report_error() {
  local message="$1"
  local json_mode="${2:-false}"

  if [ "$json_mode" = true ]; then
    # Escape quotes in message
    local safe_msg="${message//\"/\\\"}"
    echo "{\"status\": \"error\", \"message\": \"$safe_msg\"}"
  else
    echo "Error: $message" >&2
  fi
}

# Report success
# Usage: report_success "message" [data_fragment] [json_mode]
# data_fragment should be valid JSON key-value pairs, e.g. '"path": "/foo"'
report_success() {
  local message="$1"
  local data="$2"
  local json_mode="${3:-false}"

  if [ "$json_mode" = true ]; then
    local safe_msg="${message//\"/\\\"}"
    if [ -n "$data" ]; then
      echo "{\"status\": \"success\", \"message\": \"$safe_msg\", $data}"
    else
      echo "{\"status\": \"success\", \"message\": \"$safe_msg\"}"
    fi
  else
    echo "$message"
  fi
}


ensure_utf8_locale() {
  export LANG=en_US.UTF-8
  export LC_ALL=en_US.UTF-8
}


