#!/usr/bin/env bash

set -e

# Plan implementation for Spec Kit - pure bash, no external dependencies
# This script implements the /speckit.plan command workflow

# Parse command line arguments
JSON_MODE=false
USER_INPUT=""
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
        --input)
            USER_INPUT="$2"
            shift 2
            ;;
        *)
            # If we have unprocessed arguments and no --input flag was used,
            # treat all remaining args as user input
            if [ -z "$USER_INPUT" ]; then
                USER_INPUT="$*"
            fi
            break
            ;;
    esac
done

if $HELP_MODE; then
    cat <<EOF
Usage: $0 [--json] [--input "user input"] [user input...]

Options:
  --json          Output results in JSON format
  --input         Specify user input (alternative to positional args)
  --help|-h       Show this help message

This script implements the /speckit.plan command for Spec Kit.
It handles complex Unicode and special characters safely without external dependencies.

Examples:
  $0 --json "Handle special chars like \$, \", ', \\ and Unicode like 世界 👋"
  $0 --input "Complex prompt with | & ; * ? [ ] { } ( ) < > ! #" 
EOF
    exit 0
fi

# Get script directory and load common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Ensure UTF-8 locale for better Unicode handling
ensure_utf8_locale || true

# Validate user input if provided
if [ -n "$USER_INPUT" ]; then
    validate_input "$USER_INPUT" 10000 || {
        echo "Error: Invalid user input" >&2
        exit 1
    }
    is_valid_utf8 "$USER_INPUT" || {
        echo "Warning: User input may contain invalid UTF-8 sequences" >&2
    }
fi

# Get all paths and variables from common functions
eval $(get_feature_paths)

# Check if we're on a proper feature branch (only for git repos)
check_feature_branch "$CURRENT_BRANCH" "$HAS_GIT" || exit 1

# Ensure the feature directory exists
mkdir -p "$FEATURE_DIR"

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

# Phase 0: Handle user input and research requirements
# Extract unknowns from Technical Context that need clarification
handle_research_phase() {
    local feature_spec="$1"
    local research_file="$2"
    
    echo "Starting Phase 0: Research"
    
    # Create research.md if it doesn't exist
    if [[ ! -f "$research_file" ]]; then
        cat > "$research_file" <<EOF
# Research Findings

**Branch**: $CURRENT_BRANCH | **Date**: $(date '+%Y-%m-%d')

## Summary of Research

This document contains findings from research conducted to resolve uncertainties in the technical context.

EOF
    fi
    
    # For our specific use case (complex Unicode and special characters),
    # we need to research safe handling approaches
    
    # Add research findings for special character handling
    if grep -q "NEEDS CLARIFICATION" "$feature_spec" 2>/dev/null; then
        echo "Researching safe input handling for special characters and Unicode..."
        
        # Append research findings
        cat >> "$research_file" <<EOF

## Decision: Safe Input Handling for Special Characters and Unicode

**Decision**: Use pure bash with careful quoting and escaping mechanisms
**Rationale**: Eliminates external dependencies while maintaining security and Unicode support
**Alternatives considered**: 
- Python subprocess module: Requires Python dependency
- Perl with Unicode support: Requires Perl dependency  
- External shell escaping tools: Adds complexity and dependencies

## Decision: UTF-8 Locale Handling

**Decision**: Force C.UTF-8 or en_US.UTF-8 locale when available
**Rationale**: Ensures consistent Unicode behavior across different systems
**Alternatives considered**: 
- Rely on system default: Inconsistent across environments
- No locale setting: May cause Unicode issues on some systems

EOF
    fi
    
    echo "Phase 0: Research completed"
}

# Phase 1: Generate design artifacts
handle_design_phase() {
    local feature_spec="$1"
    local data_model_file="$2"
    local contracts_dir="$3"
    local quickstart_file="$4"
    
    echo "Starting Phase 1: Design & Contracts"
    
    # Create data-model.md
    if [[ ! -f "$data_model_file" ]]; then
        cat > "$data_model_file" <<EOF
# Data Model

**Branch**: $CURRENT_BRANCH | **Date**: $(date '+%Y-%m-%d')

## Entities

### UserPrompt
- **Description**: A string of text provided by the user
- **Fields**:
  - content: string (UTF-8 encoded, may contain any characters)
  - length: integer (validated against maximum length)
- **Validation Rules**:
  - Must be valid UTF-8
  - Maximum length: 10000 characters
  - No injection attempts detected (handled at processing layer)

EOF
    fi
    
    # Create contracts directory
    mkdir -p "$contracts_dir"
    
    # Create quickstart.md
    if [[ ! -f "$quickstart_file" ]]; then
        cat > "$quickstart_file" <<EOF
# Quick Start Guide

**Branch**: $CURRENT_BRANCH | **Date**: $(date '+%Y-%m-%d')

## Core Validation Scenarios

### Test 1: Special Characters
Run: ./scripts/bash/execute-plan.sh "echo \"Price is \\$100 & it's 50% off!\" | grep '50%'"
Expected: Command executes safely without shell interpretation

### Test 2: Unicode Characters  
Run: ./scripts/bash/execute-plan.sh "echo \"Hello 世界! 👋\""
Expected: Command outputs exact Unicode string

### Test 3: Combined Input
Run: ./scripts/bash/execute-plan.sh "echo \"The price in 中国 is \\$100 & it's 50% off! 🎉\""
Expected: Command handles both special chars and Unicode correctly

## Implementation Notes

- All user input is validated with validate_input() function
- UTF-8 validation performed with is_valid_utf8() function  
- Safe quoting handled by safe_quote() function
- No external dependencies (pure bash only)
- JSON output properly escaped with json_escape() function

EOF
    fi
    
    echo "Phase 1: Design & Contracts completed"
}

# Main execution flow
main() {
    echo "Executing /speckit.plan workflow for branch: $CURRENT_BRANCH"
    
    # Load feature spec if it exists
    if [[ -f "$FEATURE_SPEC" ]]; then
        echo "Loaded feature spec: $FEATURE_SPEC"
    else
        echo "Warning: Feature spec not found at $FEATURE_SPEC"
    fi
    
    # Load constitution if it exists
    CONSTITUTION_FILE="$REPO_ROOT/.specify/memory/constitution.md"
    if [[ -f "$CONSTITUTION_FILE" ]]; then
        echo "Loaded constitution: $CONSTITUTION_FILE"
    else
        echo "Warning: Constitution file not found at $CONSTITUTION_FILE"
    fi
    
    # Execute Phase 0: Research
    handle_research_phase "$FEATURE_SPEC" "$RESEARCH"
    
    # Execute Phase 1: Design & Contracts  
    handle_design_phase "$FEATURE_SPEC" "$DATA_MODEL" "$CONTRACTS_DIR" "$QUICKSTART"
    
    # Update agent context (for bash agent)
    AGENT_CONTEXT_SCRIPT="$SCRIPT_DIR/update-agent-context.sh"
    if [[ -f "$AGENT_CONTEXT_SCRIPT" ]]; then
        echo "Updating agent context..."
        "$AGENT_CONTEXT_SCRIPT" "bash" || echo "Agent context update failed (non-fatal)"
    fi
    
    # Output results
    if $JSON_MODE; then
        printf '{"FEATURE_SPEC":"%s","IMPL_PLAN":"%s","SPECS_DIR":"%s","BRANCH":"%s","HAS_GIT":"%s","USER_INPUT":"%s"}\n' \
            "$(json_escape "$FEATURE_SPEC")" \
            "$(json_escape "$IMPL_PLAN")" \
            "$(json_escape "$FEATURE_DIR")" \
            "$(json_escape "$CURRENT_BRANCH")" \
            "$HAS_GIT" \
            "$(json_escape "$USER_INPUT")"
    else
        echo "FEATURE_SPEC: $FEATURE_SPEC"
        echo "IMPL_PLAN: $IMPL_PLAN" 
        echo "SPECS_DIR: $FEATURE_DIR"
        echo "BRANCH: $CURRENT_BRANCH"
        echo "HAS_GIT: $HAS_GIT"
        if [ -n "$USER_INPUT" ]; then
            echo "USER_INPUT: $USER_INPUT"
        fi
        echo ""
        echo "Plan workflow completed successfully!"
        echo "Generated artifacts:"
        echo "  - $RESEARCH"
        echo "  - $DATA_MODEL" 
        echo "  - $QUICKSTART"
        echo "  - $CONTRACTS_DIR/"
    fi
}

# Run main function
main
