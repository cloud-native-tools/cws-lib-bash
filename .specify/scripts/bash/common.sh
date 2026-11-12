#!/usr/bin/env bash
# Common functions and variables for all scripts

# ---------------------------------------------------------------------------------------
# Script-interface surface (feature 086). Everything below the guard is this file's BODY and
# runs only when the file is executed, never when it is sourced: sourcing is how every other
# script in this directory obtains these helpers, so a sourcing that ran the body would be the
# wrong act twice over — it would also end the caller, because the dependency check below exits.
#
# The guard sits ahead of the host-library load and of that dependency check, or `--help` would
# be answered by a non-zero exit instead of by the usage and its labels.
#
# That this file HAS an entry point is measured, not assumed: run without a flag, it loads the
# host shell library, checks the dependency and returns 0 — the same work it does for every
# caller, in a subshell, so that a missing dependency is reported without ending the caller.
#
# Authority: .specify/shared/definitions/script-interface-definitions.md sections 3 and 4.
# ---------------------------------------------------------------------------------------

# The executable half: what this file does when it is run.
_script_interface_library_body() {
  # Source shared environment configurations
  [ -f "${CWS_LIB_BASH_HOME}/bin/cws_bash_env" ] && source "${CWS_LIB_BASH_HOME}/bin/cws_bash_env"

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

    return 0
  }

  if ! check_dependency; then
    echo "Dependency check failed. Initializing dependencies are required." >&2
    exit 1
  fi
}

# The guard block every applicable script carries: at file scope, ahead of the body and ahead of
# every write. It answers `-h`, `--help` and `--version` (exit 0) and rejects an undeclared `-*`
# token (exit 2) before anything else happens. The library provides the scan; this consumer only
# declares its own surface and which kind of file it is.
_SCRIPT_INTERFACE_READ_IN=1
SCRIPT_INTERFACE_LIB="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/script-interface.sh"
# Direct execution only: when this file is SOURCED, "$@" belongs to the caller and must never be
# read here, or a caller passing --help would be answered and ended by its own helper library.
if [ -f "$SCRIPT_INTERFACE_LIB" ]; then
    # shellcheck source=/dev/null
    . "$SCRIPT_INTERFACE_LIB"
    # The guard answers for THIS file only when THIS file is the program. When it is sourced,
    # "$@" belongs to the caller: reading it here would answer the caller's flags and end it.
    if [ "${BASH_SOURCE[0]}" = "$0" ]; then
        script_interface_guard entry
        script_interface_guard define name="$0" \
            usage="(no options; sourceable helper library)" \
            effects="defines helper functions only; sourcing it writes nothing" \
            codes="0 the library was sourced; 1 a host dependency is missing; 2 an unrecognized option" \
            writes=--help \
            --
        script_interface_guard guard "$@"
    fi
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
    # If branch doesn't have numeric prefix, fall back to latest spec directory.
    local latest_feature=""
    local highest=0
    if [[ -d $specs_dir ]]; then
      for dir in "$specs_dir"/*; do
        if [[ -d $dir ]]; then
          local dirname=$(basename "$dir")
          if [[ $dirname =~ ^([0-9]+)- ]]; then
            local number=${BASH_REMATCH[1]}
            number=$((10#$number))
            if [[ $number -gt $highest ]]; then
              highest=$number
              latest_feature=$dirname
            fi
          fi
        fi
      done
    fi
    if [[ -n $latest_feature ]]; then
      echo "$specs_dir/$latest_feature"
    else
      echo "$specs_dir/$branch_name"
    fi
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

  if is_git_repo; then
    has_git_repo="true"
  fi

  # Extract REQUIREMENT_ID from branch name (NOT feature name)
  # Branch name format: NNN-requirement-name (e.g., 003-speckit-agents-command)
  # This is the requirement/spec key identifier, NOT the feature name
  # Feature metadata (ID, name) must be retrieved from .specify/features.md
  local requirement_id=""
  if [[ $current_branch =~ ^([0-9]+)- ]]; then
      requirement_id="${BASH_REMATCH[1]}"
  fi

  # Use prefix-based lookup to support multiple branches per spec
  local feature_dir=$(find_feature_dir_by_prefix "$repo_root" "$current_branch")
  if [[ -d $feature_dir ]]; then
    current_branch=$(basename "$feature_dir")
  fi

  cat <<EOF
REPO_ROOT='$repo_root'
CURRENT_BRANCH='$current_branch'
BRANCH_RESOLVED_FROM_SPEC_DIR=true
REQUIREMENT_ID='$requirement_id'
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
  # Check if current locale is already UTF-8
  if [ "$(locale charmap 2>/dev/null)" = "UTF-8" ]; then
    return 0
  fi

  local utf8_locale=""
  if type locale >/dev/null 2>&1; then
    local locales
    locales=$(locale -a 2>/dev/null)
    
    # Try en_US.UTF-8 or en_US.utf8
    utf8_locale=$(echo "$locales" | grep -i -e '^en_US\.utf8$' -e '^en_US\.utf-8$' | head -n 1)
    
    # Fallback to C.UTF-8 or C.utf8
    if [ -z "$utf8_locale" ]; then
      utf8_locale=$(echo "$locales" | grep -i -e '^C\.utf8$' -e '^C\.utf-8$' | head -n 1)
    fi
    
    # Fallback to any UTF-8 locale
    if [ -z "$utf8_locale" ]; then
      utf8_locale=$(echo "$locales" | grep -i -e 'utf8' -e 'utf-8' | head -n 1)
    fi
  fi

  if [ -n "$utf8_locale" ]; then
    export LANG="$utf8_locale"
    export LC_ALL="$utf8_locale"
  else
    export LANG=C
    export LC_ALL=C
  fi
}

# The library-link: run the body when this file is executed; publish the helpers listed here when
# it is sourced. The list is this file's public surface — nothing else crosses the subshell, and a
# helper added below without being listed here is not published.
_script_interface_library_link \
  check_feature_branch get_feature_dir find_feature_dir_by_prefix get_feature_paths \
  git_repo_root git_current_branch is_git_repo gitignore_add_pattern gitignore_ensure_exists escape_sed \
  check_file check_dir safe_quote validate_input is_valid_utf8 validate_skill_name \
  create_skill_structure report_error report_success ensure_utf8_locale check_dependency
