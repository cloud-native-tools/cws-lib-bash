#!/usr/bin/env bash

set -e

# Load common helpers
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/common.sh" ]; then
    # shellcheck source=/dev/null
    source "$SCRIPT_DIR/common.sh"
    ensure_utf8_locale || true
fi

# Function to find repository root
find_repo_root() {
    local dir="$1"
    while [ "$dir" != "/" ]; do
        if [ -d "$dir/.git" ] || [ -d "$dir/.specify" ]; then
            echo "$dir"
            return 0
        fi
        dir="$(dirname "$dir")"
    done
    return 1
}

# Get repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if git rev-parse --show-toplevel >/dev/null 2>&1; then
    REPO_ROOT=$(git rev-parse --show-toplevel)
else
    REPO_ROOT="$(find_repo_root "$SCRIPT_DIR")"
    if [ -z "$REPO_ROOT" ]; then
        echo "Error: Could not determine repository root." >&2
        exit 1
    fi
fi

cd "$REPO_ROOT"

FEATURE_INDEX="$REPO_ROOT/.specify/memory/feature-index.md"
FEATURES_DIR="$REPO_ROOT/.specify/memory/features"
SPECS_DIR="$REPO_ROOT/.specify/specs"

# Ensure directories exist
mkdir -p "$FEATURES_DIR"

# Function to get project name
get_project_name() {
    if [ -f "$REPO_ROOT/README.md" ]; then
        # Try to extract project name from README title
        local readme_title
        readme_title=$(grep -E "^# " "$REPO_ROOT/README.md" | head -1 | sed 's/^# //')
        if [ -n "$readme_title" ]; then
            echo "$readme_title"
            return
        fi
    fi
    # Fallback to directory name
    basename "$REPO_ROOT"
}

# Function to count total features
count_features() {
    local count=0
    if [ -d "$SPECS_DIR" ]; then
        for dir in "$SPECS_DIR"/*; do
            [ -d "$dir" ] || continue
            dirname=$(basename "$dir")
            if [[ "$dirname" =~ ^[0-9]{3}- ]]; then
                ((count++))
            fi
        done
    fi
    echo "$count"
}

# Function to generate feature entries table
generate_feature_entries() {
    local entries=""
    local first=true
    
    if [ -d "$SPECS_DIR" ]; then
        # Sort directories numerically by feature ID
        for dir in $(find "$SPECS_DIR" -maxdepth 1 -type d -name "[0-9][0-9][0-9]-*" | sort -V); do
            [ -d "$dir" ] || continue
            dirname=$(basename "$dir")
            
            # Extract feature ID and name
            if [[ "$dirname" =~ ^([0-9]{3})-(.*) ]]; then
                local feature_id="${BASH_REMATCH[1]}"
                local feature_name="${BASH_REMATCH[2]//-/ }"
                # Capitalize first letter of each word
                feature_name=$(echo "$feature_name" | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2))}1')
                
                # Get spec path
                local spec_path=".specify/specs/$dirname/spec.md"
                if [ ! -f "$spec_path" ]; then
                    spec_path="(Not yet created)"
                fi
                
                # Get last updated date (use file modification time or today)
                local last_updated="2025-11-21"  # Default to today
                if [ -f "$spec_path" ] && [ "$spec_path" != "(Not yet created)" ]; then
                    last_updated=$(stat -c %y "$spec_path" 2>/dev/null | cut -d' ' -f1 || echo "2025-11-21")
                fi
                
                # Determine status
                local status="Draft"
                if [ -f "$spec_path" ] && [ "$spec_path" != "(Not yet created)" ]; then
                    # Check if spec file has been filled (not just template)
                    if grep -q "Feature Specification:" "$spec_path" 2>/dev/null; then
                        status="Planned"
                    fi
                fi
                
                # Get description from spec file if available
                local description="Feature $feature_id"
                if [ -f "$spec_path" ] && [ "$spec_path" != "(Not yet created)" ]; then
                    # Try to extract description from spec file
                    if grep -q "## User Scenarios & Testing" "$spec_path" 2>/dev/null; then
                        description="Specification completed for feature $feature_id"
                    fi
                fi
                
                # Add to entries
                if [ "$first" = true ]; then
                    entries="| $feature_id | $feature_name | $description | $status | $spec_path | $last_updated |"
                    first=false
                else
                    entries="$entries"$'\n'"| $feature_id | $feature_name | $description | $status | $spec_path | $last_updated |"
                fi
            fi
        done
    fi
    
    if [ -z "$entries" ]; then
        entries="<!-- No features found -->"
    fi
    
    echo "$entries"
}

# Main execution
PROJECT_NAME=$(get_project_name)
LAST_UPDATED_DATE=$(date +%Y-%m-%d)
FEATURE_COUNT=$(count_features)
FEATURE_ENTRIES=$(generate_feature_entries)

# Create/update feature index
cat > "$FEATURE_INDEX" << EOF
# $PROJECT_NAME Feature Index

**Last Updated**: $LAST_UPDATED_DATE
**Total Features**: $FEATURE_COUNT

## Features

$FEATURE_ENTRIES

## Feature Entry Format

Each feature entry should follow this format in the table:

| ID | Name | Description | Status | Spec Path | Last Updated |
|----|------|-------------|--------|-----------|--------------|
| 001 | Feature Name | Brief description of the feature | Draft | .specify/specs/001-feature-name/spec.md | 2025-11-21 |

### Column Definitions

| Column | Description |
|--------|-------------|
| ID | Sequential three-digit feature identifier (001, 002, etc.) |
| Name | Short feature name (2-4 words) describing the feature |
| Description | Brief summary of the feature's purpose and scope |
| Status | Current implementation status (Draft, Planned, Implemented, Ready for Review, Completed) |
| Spec Path | Path to specification file or "(Not yet created)" if not yet created |
| Last Updated | When the feature entry was last modified (YYYY-MM-DD format) |

## Template Usage Instructions

This template contains placeholder tokens in square brackets (e.g., \`[PROJECT_NAME]\`, \`[FEATURE_COUNT]\`). 
When generating the actual feature index:

1. Replace \`[PROJECT_NAME]\` with the actual project name
2. Replace \`[LAST_UPDATED_DATE]\` with current date in YYYY-MM-DD format
3. Replace \`[FEATURE_COUNT]\` with the actual number of features
4. Replace \`[FEATURE_ENTRIES]\` with the complete Markdown table containing all feature entries
5. Each individual feature entry should have its placeholders replaced accordingly:
   - \`[FEATURE_ID]\`: Sequential three-digit ID
   - \`[FEATURE_NAME]\`: Short descriptive name (2-4 words)
   - \`[FEATURE_DESCRIPTION]\`: Brief feature description
   - \`[FEATURE_STATUS]\`: Current status (Draft, Planned, etc.)
   - \`[SPEC_PATH]\`: Path to spec file or "(Not yet created)"
   - \`[FEATURE_LAST_UPDATED]\`: Feature-specific last updated date

Ensure all placeholder tokens are replaced before finalizing the feature index.
EOF

echo "Feature index updated: $FEATURE_INDEX"
echo "Total features: $FEATURE_COUNT"