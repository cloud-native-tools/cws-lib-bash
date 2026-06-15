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
    SKILLS_DIR="$ROOT_DIR/.specify/skills"
fi

PRIMARY_COPY_STATUS="failed"
OVERALL_STATUS="failed"
MIGRATION_STATE="not-needed"
GITHUB_ENTRY_STATUS="skipped"
GITHUB_ENTRY_MODE="none"
GITHUB_ENTRY_REASON="not-applicable"

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

emit_conflict_error() {
    local message="$1"
    if [ "$JSON_MODE" = true ]; then
        local safe_message="${message//\"/\\\"}"
        echo "{\"status\":\"error\",\"code\":\"conflict-entry-path\",\"message\":\"$safe_message\"}"
    else
        echo "Error: $message" >&2
    fi
}

supports_github_entrypoint() {
    [ -d "$ROOT_DIR/.github" ] || [ -d "$ROOT_DIR/.git" ]
}

mark_placeholder_entrypoint() {
    local entry_path="$1"
    local target_path="$2"
    mkdir -p "$entry_path"
    cat > "$entry_path/README.md" <<EOF
# Skill Compatibility Entrypoint

This directory is a compatibility entrypoint.

- Primary skill location: $target_path
- Mode: placeholder

Use the primary copy from ".specify/skills" as the source of truth.
EOF
    echo "$target_path" > "$entry_path/.specify-skill-placeholder"
}

create_github_entrypoint() {
    local skill_name="$1"
    local primary_path="$2"
    local entry_path="$ROOT_DIR/.github/skills/$skill_name"

    GITHUB_ENTRY_REASON=""

    mkdir -p "$(dirname "$entry_path")"

    if [ -L "$ROOT_DIR/.github/skills" ]; then
        local parent_real=""
        local primary_parent_real=""
        parent_real=$(realpath -m "$ROOT_DIR/.github/skills" 2>/dev/null || true)
        primary_parent_real=$(realpath -m "$(dirname "$primary_path")" 2>/dev/null || true)
        if [ -n "$parent_real" ] && [ "$parent_real" = "$primary_parent_real" ]; then
            GITHUB_ENTRY_STATUS="skipped"
            GITHUB_ENTRY_MODE="symlink"
            GITHUB_ENTRY_REASON="parent-already-linked"
            return 0
        fi
    fi

    if [ -L "$entry_path" ]; then
        local link_target=""
        link_target=$(readlink "$entry_path" 2>/dev/null || true)
        if [ "$link_target" = "$primary_path" ]; then
            GITHUB_ENTRY_STATUS="skipped"
            GITHUB_ENTRY_MODE="symlink"
            GITHUB_ENTRY_REASON="already-linked"
            return 0
        fi
        rm -f "$entry_path"
    elif [ -e "$entry_path" ]; then
        GITHUB_ENTRY_STATUS="conflict"
        GITHUB_ENTRY_MODE="none"
        GITHUB_ENTRY_REASON="conflict-entry-path"
        return 1
    fi

    if [ "${SPECIFY_FORCE_PLACEHOLDER:-0}" != "1" ] && ln -s "$primary_path" "$entry_path" 2>/dev/null; then
        GITHUB_ENTRY_STATUS="created"
        GITHUB_ENTRY_MODE="symlink"
        GITHUB_ENTRY_REASON=""
        return 0
    fi

    mark_placeholder_entrypoint "$entry_path" "$primary_path"
    GITHUB_ENTRY_STATUS="created"
    GITHUB_ENTRY_MODE="placeholder"
    GITHUB_ENTRY_REASON="symlink-not-supported"
    return 0
}

migrate_legacy_github_dir() {
    local skill_name="$1"
    local primary_path="$2"
    local legacy_path="$ROOT_DIR/.github/skills/$skill_name"

    if [ ! -d "$legacy_path" ] || [ -L "$legacy_path" ]; then
        MIGRATION_STATE="not-needed"
        return 0
    fi

    local primary_existed=false
    if [ -d "$primary_path" ]; then
        primary_existed=true
    else
        mkdir -p "$primary_path"
    fi

    local backup_root="$ROOT_DIR/.specify/skills/.migration-backups"
    local timestamp
    timestamp=$(date +%Y%m%d%H%M%S)
    local backup_path="$backup_root/${skill_name}-${timestamp}"
    if [ "${SPECIFY_FORCE_BACKUP_FAIL:-0}" = "1" ]; then
        MIGRATION_STATE="manual-required"
        OVERALL_STATUS="partial-success"
        GITHUB_ENTRY_STATUS="failed"
        GITHUB_ENTRY_MODE="none"
        GITHUB_ENTRY_REASON="backup-failed"
        return 0
    fi

    if ! mkdir -p "$backup_root" 2>/dev/null; then
        MIGRATION_STATE="manual-required"
        OVERALL_STATUS="partial-success"
        GITHUB_ENTRY_STATUS="failed"
        GITHUB_ENTRY_MODE="none"
        GITHUB_ENTRY_REASON="backup-failed"
        return 0
    fi

    if ! cp -a "$legacy_path" "$backup_path" 2>/dev/null; then
        MIGRATION_STATE="manual-required"
        OVERALL_STATUS="partial-success"
        GITHUB_ENTRY_STATUS="failed"
        GITHUB_ENTRY_MODE="none"
        GITHUB_ENTRY_REASON="backup-failed"
        return 0
    fi

    shopt -s dotglob nullglob
    local legacy_entries=("$legacy_path"/*)
    shopt -u dotglob nullglob
    if [ ${#legacy_entries[@]} -gt 0 ]; then
        if ! mv -f "${legacy_entries[@]}" "$primary_path"/ 2>/dev/null; then
            MIGRATION_STATE="manual-required"
            OVERALL_STATUS="partial-success"
            GITHUB_ENTRY_STATUS="failed"
            GITHUB_ENTRY_MODE="none"
            GITHUB_ENTRY_REASON="move-legacy-failed"
            return 0
        fi
    fi

    if ! rm -rf "$legacy_path" 2>/dev/null; then
        MIGRATION_STATE="manual-required"
        OVERALL_STATUS="partial-success"
        GITHUB_ENTRY_STATUS="failed"
        GITHUB_ENTRY_MODE="none"
        GITHUB_ENTRY_REASON="delete-legacy-failed"
        return 0
    fi

    if [ "$primary_existed" = false ]; then
        PRIMARY_COPY_STATUS="created"
    fi
    MIGRATION_STATE="completed"
    return 0
}

mkdir -p "$SKILLS_DIR"

if [ "$REFRESH_ONLY" = true ]; then
    if [ -n "$SKILL_NAME" ]; then
        target="$SKILLS_DIR/$SKILL_NAME"
        if [ ! -d "$target" ]; then
            report_error "Skill directory not found at $target" "$JSON_MODE"
            exit 1
        fi
        skill_file="$target/SKILL.md"
        if [ -f "$skill_file" ]; then
            canonical_path=$(to_workspace_relative "$skill_file")
            skill_id=$(format_skill_id "$canonical_path")
            ensure_skill_id_in_file "$skill_file" "$skill_id"
        fi
    else
        for skill_dir in "$SKILLS_DIR"/*; do
            if [ -d "$skill_dir" ]; then
                skill_file="$skill_dir/SKILL.md"
                if [ -f "$skill_file" ]; then
                    canonical_path=$(to_workspace_relative "$skill_file")
                    skill_id=$(format_skill_id "$canonical_path")
                    ensure_skill_id_in_file "$skill_file" "$skill_id"
                fi
            fi
        done
    fi

    emit_json "refreshed" "Skill metadata refreshed" "\"skills_dir\":\"$SKILLS_DIR\""
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

if [ -z "$CUSTOM_OUTPUT_DIR" ] && supports_github_entrypoint; then
    migrate_legacy_github_dir "$SKILL_NAME" "$TARGET_DIR"
fi

if [ -d "$TARGET_DIR" ]; then
    canonical_path=$(to_workspace_relative "$SKILL_FILE")
    skill_id=$(format_skill_id "$canonical_path")
    ensure_skill_id_in_file "$SKILL_FILE" "$skill_id"
    if [ "$PRIMARY_COPY_STATUS" != "created" ]; then
        PRIMARY_COPY_STATUS="reused"
    fi

    if [ "$MIGRATION_STATE" = "manual-required" ]; then
        GITHUB_ENTRY_STATUS="failed"
        GITHUB_ENTRY_MODE="none"
        if [ -z "$GITHUB_ENTRY_REASON" ] || [ "$GITHUB_ENTRY_REASON" = "not-applicable" ]; then
            GITHUB_ENTRY_REASON="manual-required"
        fi
        OVERALL_STATUS="partial-success"
    elif [ -z "$CUSTOM_OUTPUT_DIR" ] && supports_github_entrypoint; then
        if ! create_github_entrypoint "$SKILL_NAME" "$TARGET_DIR"; then
            OVERALL_STATUS="failed"
            emit_conflict_error "Conflict on compatibility entry path: $ROOT_DIR/.github/skills/$SKILL_NAME"
            exit 1
        fi
    else
        GITHUB_ENTRY_STATUS="skipped"
        GITHUB_ENTRY_MODE="none"
        GITHUB_ENTRY_REASON="unsupported-or-custom-output"
    fi

    if [ "$OVERALL_STATUS" = "failed" ]; then
        OVERALL_STATUS="success"
    fi

    emit_json "refreshed" "Skill already exists, refreshed tools" "\"SKILL_DIR\":\"$TARGET_DIR\",\"SKILL_FILE\":\"$SKILL_FILE\",\"SKILL_ID\":\"$skill_id\",\"canonical_path\":\"$canonical_path\",\"primary_copy_status\":\"$PRIMARY_COPY_STATUS\",\"overall_status\":\"$OVERALL_STATUS\",\"migration_state\":\"$MIGRATION_STATE\",\"entrypoint_github_status\":\"$GITHUB_ENTRY_STATUS\",\"entrypoint_github_mode\":\"$GITHUB_ENTRY_MODE\",\"entrypoint_github_reason\":\"$GITHUB_ENTRY_REASON\""
    exit 0
fi

create_skill_structure "$TARGET_DIR"

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

PRIMARY_COPY_STATUS="created"

if [ "$MIGRATION_STATE" = "manual-required" ]; then
    GITHUB_ENTRY_STATUS="failed"
    GITHUB_ENTRY_MODE="none"
    if [ -z "$GITHUB_ENTRY_REASON" ] || [ "$GITHUB_ENTRY_REASON" = "not-applicable" ]; then
        GITHUB_ENTRY_REASON="manual-required"
    fi
    OVERALL_STATUS="partial-success"
elif [ -z "$CUSTOM_OUTPUT_DIR" ] && supports_github_entrypoint; then
    if ! create_github_entrypoint "$SKILL_NAME" "$TARGET_DIR"; then
        emit_conflict_error "Conflict on compatibility entry path: $ROOT_DIR/.github/skills/$SKILL_NAME"
        exit 1
    fi
else
    GITHUB_ENTRY_STATUS="skipped"
    GITHUB_ENTRY_MODE="none"
    GITHUB_ENTRY_REASON="unsupported-or-custom-output"
fi

if [ "$OVERALL_STATUS" = "failed" ]; then
    if [ "$GITHUB_ENTRY_STATUS" = "failed" ]; then
        OVERALL_STATUS="partial-success"
    else
        OVERALL_STATUS="success"
    fi
fi

emit_json "created" "Skill created successfully" "\"SKILL_DIR\":\"$TARGET_DIR\",\"SKILL_FILE\":\"$SKILL_FILE\",\"SKILL_NAME\":\"$SKILL_NAME\",\"SKILL_DESCRIPTION\":\"${DESCRIPTION//\"/\\\"}\",\"SKILL_ID\":\"$skill_id\",\"canonical_path\":\"$canonical_path\",\"primary_copy_status\":\"$PRIMARY_COPY_STATUS\",\"overall_status\":\"$OVERALL_STATUS\",\"migration_state\":\"$MIGRATION_STATE\",\"entrypoint_github_status\":\"$GITHUB_ENTRY_STATUS\",\"entrypoint_github_mode\":\"$GITHUB_ENTRY_MODE\",\"entrypoint_github_reason\":\"$GITHUB_ENTRY_REASON\""