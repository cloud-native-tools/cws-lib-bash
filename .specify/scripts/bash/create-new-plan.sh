#!/usr/bin/env bash

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
        usage="[--json] [--force] [<feature_description>]" \
        effects="scaffolds .specify/specs/<feature>/plan.md (and amends it in place with --force); the flags write nothing" \
        codes="0 created or answered; 1 a prerequisite is missing; 2 an unrecognized option" \
        writes=--force \
        -- --json --force
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

    # Parse command line arguments
    JSON_MODE=false
    FORCE=false
    ARGS=()

    for arg in "$@"; do
        case "$arg" in
            --json) 
                JSON_MODE=true 
                ;;
            --force) 
                FORCE=true 
                ;;
            --help|-h) 
                echo "Usage: $0 [--json] [--force]"
                echo "  --json    Output results in JSON format"
                echo "  --force   Overwrite an existing plan.md (in-place amend is preferred)"
                echo "  --help    Show this help message"
                exit 0 
                ;;
            *) 
                ARGS+=("$arg") 
                ;;
        esac
    done

    # Get script directory and load common functions
    SCRIPT_DIR="$(CDPATH="" cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    source "$SCRIPT_DIR/common.sh"

    # Ensure UTF-8 locale for better Unicode handling
    ensure_utf8_locale || true

    # Get all paths and variables from common functions
    eval $(get_feature_paths)

    # Check if we're on a proper feature branch (only for git repos)
    check_feature_branch "$CURRENT_BRANCH" "$HAS_GIT" || exit 1


    # Ensure the feature directory exists. It sits BELOW the argument scan on purpose: the tree
    # is part of the main action, and C-11 measures that `--help --force` writes nothing.
    mkdir -p "$REQUIREMENTS_DIR"

    # Guard: never clobber an existing plan.md (in-place amend ≠ re-scaffold).
    if [[ -f "$IMPL_PLAN" && "$FORCE" != "true" ]]; then
        echo "Error: $IMPL_PLAN already exists." >&2
        echo "Amend it in place instead of re-scaffolding, or pass --force to overwrite." >&2
        exit 1
    fi

    # Copy plan template if it exists
    TEMPLATE="$REPO_ROOT/.specify/templates/plan-template.md"
    if [[ -f "$TEMPLATE" ]]; then
        cp "$TEMPLATE" "$IMPL_PLAN"
        echo "Copied plan template to $IMPL_PLAN"
    else
        echo "Warning: Plan template not found at $TEMPLATE"
        # Create a basic plan file if template doesn't exist
        touch "$IMPL_PLAN"
    fi

    # Output results
    if $JSON_MODE; then
        printf '{"FEATURE_SPEC":"%s","IMPL_PLAN":"%s","SPECS_DIR":"%s","BRANCH":"%s","HAS_GIT":"%s"}\n' \
            "$FEATURE_SPEC" "$IMPL_PLAN" "$REQUIREMENTS_DIR" "$CURRENT_BRANCH" "$HAS_GIT"
    else
        echo "FEATURE_SPEC: $FEATURE_SPEC"
        echo "IMPL_PLAN: $IMPL_PLAN" 
        echo "SPECS_DIR: $REQUIREMENTS_DIR"
        echo "BRANCH: $CURRENT_BRANCH"
        echo "HAS_GIT: $HAS_GIT"
    fi

}

if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    main "$@"
fi
