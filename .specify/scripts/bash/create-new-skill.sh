#!/usr/bin/env bash

set -e

# Load common helpers for Unicode support and shared functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/common.sh" ]; then
    # shellcheck source=/dev/null
    source "$SCRIPT_DIR/common.sh"
    # Ensure UTF-8 locale for better Unicode handling
    ensure_utf8_locale || true
fi

# Fallback: if common.sh wasn't sourced or locale still isn't UTF-8, set a UTF-8 locale
if ! locale 2>/dev/null | grep -qi 'utf-8'; then
    if locale -a 2>/dev/null | grep -qi '^C\.utf8\|^C\.UTF-8$'; then
        export LC_ALL=C.UTF-8
        export LANG=C.UTF-8
    elif locale -a 2>/dev/null | grep -qi '^en_US\.utf8\|^en_US\.UTF-8$'; then
        export LC_ALL=en_US.UTF-8
        export LANG=en_US.UTF-8
    fi
fi

JSON_MODE=false
REFRESH_ONLY=false
SKILL_NAME=""
DESCRIPTION=""
CUSTOM_OUTPUT_DIR=""
ARGS=()

i=1
while [ $i -le $# ]; do
    arg="${!i}"
    case "$arg" in
        --json)
            JSON_MODE=true
            ;;
        --refresh-only)
            REFRESH_ONLY=true
            ;;
        --name)
            if [ $((i + 1)) -gt $# ]; then
                echo "Error: --name requires a value" >&2
                exit 1
            fi
            i=$((i + 1))
            next_arg="${!i}"
            if [[ "$next_arg" == --* ]]; then
                echo "Error: --name requires a value" >&2
                exit 1
            fi
            SKILL_NAME="$next_arg"
            ;;
        --description|--desc|-d)
            if [ $((i + 1)) -gt $# ]; then
                echo "Error: --description requires a value" >&2
                exit 1
            fi
            i=$((i + 1))
            next_arg="${!i}"
            if [[ "$next_arg" == --* ]]; then
                echo "Error: --description requires a value" >&2
                exit 1
            fi
            DESCRIPTION="$next_arg"
            ;;
        --output-dir|-o)
            if [ $((i + 1)) -gt $# ]; then
                echo "Error: --output-dir requires a value" >&2
                exit 1
            fi
            i=$((i + 1))
            next_arg="${!i}"
            if [[ "$next_arg" == --* ]]; then
                echo "Error: --output-dir requires a value" >&2
                exit 1
            fi
            CUSTOM_OUTPUT_DIR="$next_arg"
            ;;
        --help|-h)
            echo "Usage: $0 [--json] [--name <name>] [--description <desc>] [--output-dir <dir>] [<skill_string>]"
            echo ""
            echo "Options:"
            echo "  --json                  Output in JSON format"
            echo "  --refresh-only          Refresh tools for existing skills only"
            echo "  --name <name>           Skill name"
            echo "  --description, -d <desc> Skill description"
            echo "  --output-dir, -o <dir>  Custom output directory"
            echo "  --help, -h              Show this help message"
            echo ""
            echo "Behavior:"
            echo "  - If skill_string is provided in format 'Name - Description', it parses name and description."
            echo "  - Otherwise, positional arguments are treated as description if name is provided via flag."
            echo "  - With --refresh-only, only refresh tools for existing skills and exit."
            echo ""
            exit 0
            ;;
        *)
            ARGS+=("$arg")
            ;;
    esac
    i=$((i + 1))
done

POSITIONAL_INPUT="${ARGS[*]}"

# Try to parse 'Name - Description' from positional input if name not set
IS_NAME_DESC_FORMAT=false
if [ -z "$SKILL_NAME" ] && [[ "$POSITIONAL_INPUT" == *" - "* ]]; then
    SKILL_NAME="${POSITIONAL_INPUT%% - *}"
    if [ -z "$DESCRIPTION" ]; then
        DESCRIPTION="${POSITIONAL_INPUT#* - }"
    fi
    IS_NAME_DESC_FORMAT=true
fi

if [ "$IS_NAME_DESC_FORMAT" = false ] && [ -n "$POSITIONAL_INPUT" ]; then
    if [ -z "$DESCRIPTION" ]; then
        DESCRIPTION="$POSITIONAL_INPUT"
    else
        DESCRIPTION="$DESCRIPTION $POSITIONAL_INPUT"
    fi
fi

# Read from stdin if available, regardless of arguments
STDIN_INPUT=""
if [ ! -t 0 ]; then
    STDIN_INPUT=$(cat)
fi

# Combine arguments and stdin
if [ -n "$DESCRIPTION" ] && [ -n "$STDIN_INPUT" ]; then
    # Both provided: use newline separator
    DESCRIPTION="$DESCRIPTION"$'\n\n'"$STDIN_INPUT"
elif [ -z "$DESCRIPTION" ] && [ -n "$STDIN_INPUT" ]; then
    # Only stdin provided
    DESCRIPTION="$STDIN_INPUT"
fi

# Set root dir
if git rev-parse --show-toplevel >/dev/null 2>&1; then
    ROOT_DIR=$(git rev-parse --show-toplevel)
else
    # Fallback: assume script is in scripts/bash (depth 2)
    ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

# Determine target directory
if [ -n "$CUSTOM_OUTPUT_DIR" ]; then
    SKILLS_DIR="$CUSTOM_OUTPUT_DIR"
else
    SKILLS_DIR="$ROOT_DIR/.github/skills"
fi

refresh_tools_for_target() {
    local tools_dir="$TARGET_DIR/tools"
    mkdir -p "$tools_dir"

    if [ -f "$SCRIPT_DIR/refresh-tools.sh" ]; then
        "$SCRIPT_DIR/refresh-tools.sh" --mcp --format markdown > "$tools_dir/mcp.md"
        "$SCRIPT_DIR/refresh-tools.sh" --system --format markdown > "$tools_dir/system.md"
        "$SCRIPT_DIR/refresh-tools.sh" --shell --format markdown > "$tools_dir/shell.md"
        "$SCRIPT_DIR/refresh-tools.sh" --project --format markdown > "$tools_dir/project.md"

        # Add generated tools docs to .gitignore
        REPO_ROOT="$(git_repo_root)"
        if [[ "$TARGET_DIR" == "$REPO_ROOT/"* ]]; then
            REL_TARGET_DIR="${TARGET_DIR#$REPO_ROOT/}"
            gitignore_add_pattern "$REL_TARGET_DIR/tools/*.md" "$REPO_ROOT/.gitignore"
        else
            gitignore_add_pattern "$TARGET_DIR/tools/*.md" "$REPO_ROOT/.gitignore"
        fi
    else
        echo "Warning: refresh-tools.sh not found, skipping tools documentation generation." >&2
    fi
}

# Auto-switch to refresh mode if no skill name determined (implies empty or invalid format)
if [ -z "$SKILL_NAME" ] && [ "$REFRESH_ONLY" = false ]; then
    REFRESH_ONLY=true
    REFRESH_REASON="Notice: Input did not match required formats (Name - Description) or flags. Refreshed existing skills instead."
fi

if [ "$REFRESH_ONLY" = true ]; then
    if [ ! -d "$SKILLS_DIR" ]; then
        report_error "Skills directory not found at $SKILLS_DIR" "$JSON_MODE"
        exit 1
    fi

    if [ -n "$SKILL_NAME" ]; then
        TARGET_DIR="$SKILLS_DIR/$SKILL_NAME"
        if [ ! -d "$TARGET_DIR" ]; then
            report_error "Skill directory not found at $TARGET_DIR" "$JSON_MODE"
            exit 1
        fi
        REFRESH_SINGLE=true
        refresh_tools_for_target
    fi

    # Refresh all skills
    for skill_dir in "$SKILLS_DIR"/*; do
        if [ -d "$skill_dir" ]; then
            TARGET_DIR="$skill_dir"
            refresh_tools_for_target
        fi
    done

    if [ -n "$REFRESH_REASON" ]; then
        echo "$REFRESH_REASON"
    fi
    
    echo "All skills refreshed in $SKILLS_DIR"
    exit 0
fi

# Validate inputs
if [ -z "$SKILL_NAME" ]; then
    report_error "Skill name is required. Use --name <name> or 'speckit.skills name - desc'" "$JSON_MODE"
    exit 1
fi

# Validate name
if ! validate_skill_name "$SKILL_NAME"; then
    report_error "Invalid skill name '$SKILL_NAME'. Use alphanumeric, hyphens, underscores only." "$JSON_MODE"
    exit 1
fi

# Default description if empty
if [ -z "$DESCRIPTION" ]; then
    DESCRIPTION="Skill for $SKILL_NAME"
fi

TARGET_DIR="$SKILLS_DIR/$SKILL_NAME"
SKILL_FILE="$TARGET_DIR/SKILL.md"

# Check if already exists
if [ -d "$TARGET_DIR" ]; then
    report_error "Skill directory already exists at $TARGET_DIR" "$JSON_MODE"
    exit 1
fi

# Create directory structure
create_skill_structure "$TARGET_DIR"

# Create tools directory and populate it
refresh_tools_for_target

# Detect template path
if [ -f "$ROOT_DIR/.specify/templates/skills-template.md" ]; then
    TEMPLATE_FILE="$ROOT_DIR/.specify/templates/skills-template.md"
elif [ -f "$ROOT_DIR/templates/skills-template.md" ]; then
    TEMPLATE_FILE="$ROOT_DIR/templates/skills-template.md"
else
    # Fallback default
    TEMPLATE_FILE="$ROOT_DIR/templates/skills-template.md"
fi
