#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/common.sh" ]; then
    # shellcheck source=/dev/null
    source "$SCRIPT_DIR/common.sh"
    ensure_utf8_locale || true
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
            i=$((i + 1))
            SKILL_NAME="${!i}"
            ;;
        --description|--desc|-d)
            i=$((i + 1))
            DESCRIPTION="${!i}"
            ;;
        --output-dir|-o)
            i=$((i + 1))
            CUSTOM_OUTPUT_DIR="${!i}"
            ;;
        --help|-h)
            echo "Usage: $0 [--json] [--refresh-only] [--name <name>] [--description <desc>] [--output-dir <dir>] [<name - desc>]"
            exit 0
            ;;
        *)
            ARGS+=("$arg")
            ;;
    esac
    i=$((i + 1))
done

POSITIONAL_INPUT="${ARGS[*]}"
if [ -z "$SKILL_NAME" ] && [[ "$POSITIONAL_INPUT" == *" - "* ]]; then
    SKILL_NAME="${POSITIONAL_INPUT%% - *}"
    if [ -z "$DESCRIPTION" ]; then
        DESCRIPTION="${POSITIONAL_INPUT#* - }"
    fi
elif [ -n "$POSITIONAL_INPUT" ] && [ -z "$DESCRIPTION" ]; then
    DESCRIPTION="$POSITIONAL_INPUT"
fi

if [ -n "$DESCRIPTION" ] && [ ! -t 0 ]; then
    STDIN_INPUT=$(cat)
    if [ -n "$STDIN_INPUT" ]; then
        DESCRIPTION="$DESCRIPTION"$'\n\n'"$STDIN_INPUT"
    fi
fi

if git rev-parse --show-toplevel >/dev/null 2>&1; then
    ROOT_DIR=$(git rev-parse --show-toplevel)
else
    ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

if [ -n "$CUSTOM_OUTPUT_DIR" ]; then
    SKILLS_DIR="$CUSTOM_OUTPUT_DIR"
else
    SKILLS_DIR="$ROOT_DIR/.github/skills"
fi

to_workspace_relative() {
    local path="$1"
    python3 - "$ROOT_DIR" "$path" << 'PYEOF'
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
target = Path(sys.argv[2]).resolve()
print(target.relative_to(root).as_posix())
PYEOF
}

format_skill_id() {
    local canonical_path="$1"
    echo "<SKILL:${canonical_path}>"
}

refresh_tools_for_target() {
    local target_dir="$1"
    local tools_dir="$target_dir/tools"
    mkdir -p "$tools_dir"

    if [ -f "$SCRIPT_DIR/refresh-tools.sh" ]; then
        "$SCRIPT_DIR/refresh-tools.sh" --mcp --json > "$tools_dir/mcp.json"
        "$SCRIPT_DIR/refresh-tools.sh" --system --json > "$tools_dir/system.json"
        "$SCRIPT_DIR/refresh-tools.sh" --shell --json > "$tools_dir/shell.json"
        "$SCRIPT_DIR/refresh-tools.sh" --project --json > "$tools_dir/project.json"
    fi
}

ensure_skill_id_in_file() {
    local skill_file="$1"
    local skill_id="$2"
    python3 - "$skill_file" "$skill_id" << 'PYEOF'
from pathlib import Path
import sys

skill_file = Path(sys.argv[1])
skill_id = sys.argv[2]
if not skill_file.exists():
    raise SystemExit(0)

content = skill_file.read_text(encoding="utf-8")
lines = content.splitlines()
if any(line.startswith("skill_id:") for line in lines):
    raise SystemExit(0)

if lines and lines[0].strip() == "---":
    end = 1
    while end < len(lines) and lines[end].strip() != "---":
        end += 1
    lines.insert(end, f'skill_id: "{skill_id}"')
    skill_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
else:
    skill_file.write_text(f'skill_id: "{skill_id}"\n' + content, encoding="utf-8")
PYEOF
}

emit_json() {
    local status="$1"
    local message="$2"
    local extra="$3"
    local safe_message="${message//\"/\\\"}"
    if [ "$JSON_MODE" = true ]; then
        if [ -n "$extra" ]; then
            echo "{\"status\":\"$status\",\"message\":\"$safe_message\",$extra}"
        else
            echo "{\"status\":\"$status\",\"message\":\"$safe_message\"}"
        fi
    else
        echo "$message"
    fi
}

mkdir -p "$SKILLS_DIR"

if [ "$REFRESH_ONLY" = true ]; then
    if [ -n "$SKILL_NAME" ]; then
        target="$SKILLS_DIR/$SKILL_NAME"
        if [ ! -d "$target" ]; then
            report_error "Skill directory not found at $target" "$JSON_MODE"
            exit 1
        fi
        refresh_tools_for_target "$target"
        skill_file="$target/SKILL.md"
        if [ -f "$skill_file" ]; then
            canonical_path=$(to_workspace_relative "$skill_file")
            skill_id=$(format_skill_id "$canonical_path")
            ensure_skill_id_in_file "$skill_file" "$skill_id"
        fi
    else
        for skill_dir in "$SKILLS_DIR"/*; do
            if [ -d "$skill_dir" ]; then
                refresh_tools_for_target "$skill_dir"
                skill_file="$skill_dir/SKILL.md"
                if [ -f "$skill_file" ]; then
                    canonical_path=$(to_workspace_relative "$skill_file")
                    skill_id=$(format_skill_id "$canonical_path")
                    ensure_skill_id_in_file "$skill_file" "$skill_id"
                fi
            fi
        done
    fi

    emit_json "refreshed" "Skill tools refreshed" "\"skills_dir\":\"$SKILLS_DIR\""
    exit 0
fi

if [ -z "$SKILL_NAME" ]; then
    report_error "Skill name is required. Use --name <name> or '<name> - <description>'" "$JSON_MODE"
    exit 1
fi

if ! validate_skill_name "$SKILL_NAME"; then
    report_error "Invalid skill name '$SKILL_NAME'. Use alphanumeric, hyphens, underscores only." "$JSON_MODE"
    exit 1
fi

if [ -z "$DESCRIPTION" ]; then
    DESCRIPTION="Skill for $SKILL_NAME"
fi

TARGET_DIR="$SKILLS_DIR/$SKILL_NAME"
SKILL_FILE="$TARGET_DIR/SKILL.md"

if [ -d "$TARGET_DIR" ]; then
    refresh_tools_for_target "$TARGET_DIR"
    canonical_path=$(to_workspace_relative "$SKILL_FILE")
    skill_id=$(format_skill_id "$canonical_path")
    ensure_skill_id_in_file "$SKILL_FILE" "$skill_id"
    emit_json "refreshed" "Skill already exists, refreshed tools" "\"SKILL_DIR\":\"$TARGET_DIR\",\"SKILL_FILE\":\"$SKILL_FILE\",\"SKILL_ID\":\"$skill_id\",\"canonical_path\":\"$canonical_path\""
    exit 0
fi

create_skill_structure "$TARGET_DIR"
refresh_tools_for_target "$TARGET_DIR"

if [ -f "$ROOT_DIR/.specify/templates/skills-template.md" ]; then
    TEMPLATE_FILE="$ROOT_DIR/.specify/templates/skills-template.md"
elif [ -f "$ROOT_DIR/templates/skills-template.md" ]; then
    TEMPLATE_FILE="$ROOT_DIR/templates/skills-template.md"
else
    report_error "skills-template.md not found" "$JSON_MODE"
    exit 1
fi

canonical_path=$(to_workspace_relative "$SKILL_FILE")
skill_id=$(format_skill_id "$canonical_path")

python3 - "$TEMPLATE_FILE" "$SKILL_FILE" "$SKILL_NAME" "$DESCRIPTION" "$skill_id" << 'PYEOF'
from pathlib import Path
import sys

template_file, output_file, skill_name, description, skill_id = sys.argv[1:6]
template = Path(template_file).read_text(encoding="utf-8")
content = (
    template.replace("{{SKILL_NAME}}", skill_name)
    .replace("{{DESCRIPTION}}", description)
    .replace("{{SKILL_ID}}", skill_id)
)
Path(output_file).write_text(content, encoding="utf-8")
PYEOF

emit_json "created" "Skill created successfully" "\"SKILL_DIR\":\"$TARGET_DIR\",\"SKILL_FILE\":\"$SKILL_FILE\",\"SKILL_NAME\":\"$SKILL_NAME\",\"SKILL_DESCRIPTION\":\"${DESCRIPTION//\"/\\\"}\",\"SKILL_ID\":\"$skill_id\",\"canonical_path\":\"$canonical_path\""