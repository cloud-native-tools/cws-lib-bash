#!/usr/bin/env bash

# Feature context detection utility
# Extracts feature ID from branch name or directory structure

set -e

# Load common helpers for Unicode support and shared functions

# script-interface: the sourceable guard block (086) lives in script-interface.sh
# It sits above this script's own parsing and above `source common.sh`: a shared
# library's top-level checks would otherwise turn `--help` into a non-zero exit, and
# the flags must win over any write. Authority: .specify/shared/definitions/
# script-interface-definitions.md section 4.
SCRIPT_INTERFACE_LIB="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/script-interface.sh"
if [ -f "$SCRIPT_INTERFACE_LIB" ]; then
    # shellcheck source=/dev/null
    . "$SCRIPT_INTERFACE_LIB"
    script_interface_guard entry
    script_interface_guard define name="$0" \
        usage="(no options)" \
        effects="prints the current feature id; writes nothing" \
        codes="0 an id was printed; 1 no id was found; 2 an unrecognized option" \
        writes=--help \
        --
    script_interface_guard guard "$@"
fi

main() {


    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$SCRIPT_DIR/common.sh" ]; then
        # shellcheck source=/dev/null
        source "$SCRIPT_DIR/common.sh"
        # Ensure UTF-8 locale for better Unicode handling
        ensure_utf8_locale || true
    fi

    # Function to extract feature ID from current branch name
    extract_feature_id_from_branch() {
        if command -v git >/dev/null 2>&1; then
            if git rev-parse --git-dir >/dev/null 2>&1; then
                local branch_name
                branch_name=$(git symbolic-ref --short HEAD 2>/dev/null || git rev-parse --short HEAD 2>/dev/null)
                # Extract 3-digit ID from branch name pattern ###-feature-name
                if [[ "$branch_name" =~ ^([0-9]{3})- ]]; then
                    echo "${BASH_REMATCH[1]}"
                    return 0
                fi
            fi
        fi
        return 1
    }

    # Function to extract feature ID from current directory
    extract_feature_id_from_directory() {
        local current_dir
        current_dir=$(pwd)

        # Look for .specify/specs/###-feature-name pattern
        if [[ "$current_dir" =~ \.specify/specs/([0-9]{3})- ]]; then
            echo "${BASH_REMATCH[1]}"
            return 0
        fi

        # Look for feature directory in parent paths
        local parent_dir="$current_dir"
        while [ "$parent_dir" != "/" ]; do
            if [[ "$parent_dir" =~ \.specify/specs/([0-9]{3})- ]]; then
                echo "${BASH_REMATCH[1]}"
                return 0
            fi
            parent_dir=$(dirname "$parent_dir")
        done

        return 1
    }

    # Function to detect feature context and return feature ID
    detect_feature_context() {
        # Try branch name first
        if feature_id=$(extract_feature_id_from_branch); then
            echo "$feature_id"
            return 0
        fi

        # Try directory structure
        if feature_id=$(extract_feature_id_from_directory); then
            echo "$feature_id"
            return 0
        fi

        return 1
    }

    # Main execution - if called directly, output feature ID
    if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
        if feature_id=$(detect_feature_context); then
            echo "$feature_id"
            exit 0
        else
            exit 1
        fi
    fi

}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi
