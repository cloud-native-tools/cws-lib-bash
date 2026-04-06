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
DEBUG_MODE=false
TOOL_NAME=""
TOOL_TYPE=""
ACTION=""
ARGS=()

i=1
while [ $i -le $# ]; do
    arg="${!i}"
    case "$arg" in
        --json)
            JSON_MODE=true
            ;;
        --debug)
            DEBUG_MODE=true
            ;;
        --name|-n)
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
            TOOL_NAME="$next_arg"
            ;;
        --type|-t)
            if [ $((i + 1)) -gt $# ]; then
                echo "Error: --type requires a value" >&2
                exit 1
            fi
            i=$((i + 1))
            next_arg="${!i}"
            if [[ "$next_arg" == --* ]]; then
                echo "Error: --type requires a value" >&2
                exit 1
            fi
            TOOL_TYPE="$next_arg"
            ;;
        --action|-a)
            if [ $((i + 1)) -gt $# ]; then
                echo "Error: --action requires a value" >&2
                exit 1
            fi
            i=$((i + 1))
            next_arg="${!i}"
            if [[ "$next_arg" == --* ]]; then
                echo "Error: --action requires a value" >&2
                exit 1
            fi
            ACTION="$next_arg"
            ;;
        --help|-h)
            echo "Usage: $0 [--json] [--debug] [--name <name>] [--type <type>] [--action <action>] [<tool_name>]"
            echo ""
            echo "Options:"
            echo "  --json                  Output in JSON format"
            echo "  --debug                 Output diagnostics to stderr"
            echo "  --name, -n <name>       Tool name"
            echo "  --type, -t <type>       Tool type (mcp-call|project-script|system-binary|shell-function)"
            echo "  --action, -a <action>   Action to perform (find|create|list)"
            echo "  --help, -h              Show this help message"
            echo ""
            echo "Actions:"
            echo "  find                    Find a tool by name and return its record"
            echo "  create                  Create a new tool record if not exists"
            echo "  list                    List all available tools"
            echo ""
            echo "Examples:"
            echo "  $0 --name mytool --action find"
            echo "  $0 --name mytool --type mcp-call --action create"
            echo "  $0 --action list"
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

# If tool name not set via flag, try positional argument
if [ -z "$TOOL_NAME" ] && [ -n "$POSITIONAL_INPUT" ]; then
    TOOL_NAME="$POSITIONAL_INPUT"
fi

# Set default action
if [ -z "$ACTION" ]; then
    if [ -n "$TOOL_NAME" ]; then
        ACTION="find"
    else
        ACTION="list"
    fi
fi

# Set root dir
if git rev-parse --show-toplevel >/dev/null 2>&1; then
    ROOT_DIR=$(git rev-parse --show-toplevel)
else
    # Fallback: assume script is in scripts/bash (depth 2)
    ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
fi

# Set tools memory directory
TOOLS_MEMORY_DIR="$ROOT_DIR/.specify/memory/tools"

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

format_tool_id() {
    local canonical_path="$1"
    echo "<TOOL:${canonical_path}>"
}

ensure_tool_id_in_record() {
    local record_file="$1"
    local tool_id="$2"

    if grep -q '^\*\*Tool ID\*\*:' "$record_file"; then
        return 0
    fi

    awk -v id="$tool_id" '
        {
            print $0
            if ($0 ~ /^\*\*Source Identifier\*\*:/) {
                print "**Tool ID**: " id
            }
        }
    ' "$record_file" > "$record_file.tmp" && mv "$record_file.tmp" "$record_file"
}

# Validate tool type if provided
validate_tool_type() {
    local type="$1"
    case "$type" in
        mcp-call|project-script|system-binary|shell-function)
            return 0
            ;;
        *)
            report_error "Invalid tool type '$type'. Must be one of: mcp-call, project-script, system-binary, shell-function" "$JSON_MODE"
            return 1
            ;;
    esac
}

debug_log() {
    if [ "$DEBUG_MODE" = true ]; then
        echo "[create-new-tools][debug] $*" >&2
    fi
}

json_diagnostic() {
    local json_file="$1"
    python3 - "$json_file" <<'PYEOF'
import json
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(encoding="utf-8")
try:
    json.loads(text)
except json.JSONDecodeError as exc:
    start = max(exc.pos - 120, 0)
    end = min(exc.pos + 120, len(text))
    excerpt = text[start:end].replace("\n", "\\n")
    print(
        json.dumps(
            {
                "message": exc.msg,
                "line": exc.lineno,
                "column": exc.colno,
                "position": exc.pos,
                "excerpt": excerpt,
            },
            ensure_ascii=False,
        )
    )
    sys.exit(1)
PYEOF
}

print_prefixed_file() {
    local prefix="$1"
    local file_path="$2"

    if [ -s "$file_path" ]; then
        sed "s/^/${prefix}/" "$file_path" >&2
    fi
}

# Refresh all tools and get JSON output
refresh_all_tools_json() {
    local refresh_script="$SCRIPT_DIR/refresh-tools.sh"
    if [ ! -f "$refresh_script" ]; then
        report_error "refresh-tools.sh not found at $refresh_script" "$JSON_MODE"
        exit 1
    fi

    local stdout_file stderr_file status validation
    stdout_file=$(mktemp)
    stderr_file=$(mktemp)
    status=0

    if [ "$DEBUG_MODE" = true ]; then
        REFRESH_TOOLS_DEBUG=1 "$refresh_script" --mcp --system --shell --project --json --debug >"$stdout_file" 2>"$stderr_file" || status=$?
    else
        "$refresh_script" --mcp --system --shell --project --json >"$stdout_file" 2>"$stderr_file" || status=$?
    fi

    if [ "$DEBUG_MODE" = true ]; then
        print_prefixed_file "[create-new-tools][refresh-tools] " "$stderr_file"
    fi

    if [ "$status" -ne 0 ]; then
        debug_log "refresh-tools.sh failed with exit code $status"
        rm -f "$stdout_file" "$stderr_file"
        return $status
    fi

    if ! validation=$(json_diagnostic "$stdout_file"); then
        debug_log "invalid JSON from refresh-tools.sh: $validation"
        if [ "$DEBUG_MODE" = true ]; then
            print_prefixed_file "[create-new-tools][raw-refresh-json] " "$stdout_file"
        fi
        rm -f "$stdout_file" "$stderr_file"
        return 1
    fi

    cat "$stdout_file"
    rm -f "$stdout_file" "$stderr_file"
}

# Parse JSON and find tool by name
find_tool_in_json() {
    local tool_name="$1"
    local json_data="$2"

    local json_file
    json_file=$(mktemp)
    printf '%s' "$json_data" > "$json_file"

    python3 - "$tool_name" "$json_file" "$DEBUG_MODE" << 'PYTHON_SCRIPT'
import sys
import json
from pathlib import Path

tool_name = sys.argv[1]
json_path = Path(sys.argv[2])
debug_mode = sys.argv[3] == "true"
json_data = json_path.read_text(encoding="utf-8")

try:
    data = json.loads(json_data)
except json.JSONDecodeError as exc:
    if debug_mode:
        start = max(exc.pos - 120, 0)
        end = min(exc.pos + 120, len(json_data))
        excerpt = json_data[start:end].replace("\n", "\\n")
        print(
            f"[create-new-tools][debug] JSON parse failed at line {exc.lineno}, column {exc.colno}: {exc.msg}",
            file=sys.stderr,
        )
        print(f"[create-new-tools][debug] Raw excerpt: {excerpt}", file=sys.stderr)
    sys.exit(1)

# Flatten all tool sources into a single list
all_tools = []

# Handle different JSON structures from refresh-tools.sh
if isinstance(data, dict):
    if isinstance(data.get('tools'), list):
        all_tools.extend(tool for tool in data.get('tools', []) if isinstance(tool, dict))

    # Check for MCP tools structure (with servers array)
    if 'servers' in data:
        for server in data.get('servers', []):
            if isinstance(server, dict) and 'tools' in server:
                for tool in server.get('tools', []):
                    if isinstance(tool, dict):
                        tool['source_type'] = 'mcp-call'
                        tool['server_name'] = server.get('name', 'unknown')
                        all_tools.append(tool)
    
    # Check for system tools structure (with binaries array)
    if 'binaries' in data:
        for binary in data.get('binaries', []):
            if isinstance(binary, dict):
                binary['source_type'] = 'system-binary'
                all_tools.append(binary)
    
    # Check for shell functions (list at top level)
    if 'functions' in data:
        for func in data.get('functions', []):
            if isinstance(func, dict):
                func['source_type'] = 'shell-function'
                all_tools.append(func)
    
    # Check for project scripts (list at top level)
    if 'scripts' in data:
        for script in data.get('scripts', []):
            if isinstance(script, dict):
                script['source_type'] = 'project-script'
                all_tools.append(script)
    
    # Also check simple keys: mcp, system, shell, project
    for source_type in ['mcp', 'system', 'shell', 'project']:
        tools = data.get(source_type, [])
        if isinstance(tools, list):
            for tool in tools:
                if isinstance(tool, dict):
                    tool['source_type'] = source_type
                    all_tools.append(tool)

elif isinstance(data, list):
    # If data is already a list, use it directly
    all_tools = data

# Search for tool by name (exact match first, then partial)
found_tools = []
for tool in all_tools:
    name = tool.get('name', '')
    if name == tool_name:
        found_tools.insert(0, tool)  # Exact match at front
    elif tool_name.lower() in name.lower():
        found_tools.append(tool)

if not found_tools:
    result = {
        "status": "not_found",
        "tool_name": tool_name,
        "message": f"No tool found matching '{tool_name}'"
    }
elif len(found_tools) == 1:
    result = {
        "status": "found",
        "tool": found_tools[0],
        "message": f"Found tool: {found_tools[0].get('name')}"
    }
else:
    # Multiple matches - return all with source info
    result = {
        "status": "multiple_matches",
        "tools": found_tools,
        "message": f"Found {len(found_tools)} tools matching '{tool_name}'. Please specify source type."
    }

print(json.dumps(result, indent=2))
PYTHON_SCRIPT
    local ret=$?
    rm -f "$json_file"
    return $ret
}

# Get template file for tool type
get_template_file() {
    local tool_type="$1"
    local template_name=""
    
    case "$tool_type" in
        mcp-call)
            template_name="tool-mcp-call-template.md"
            ;;
        project-script)
            template_name="tool-project-script-template.md"
            ;;
        system-binary)
            template_name="tool-system-binary-template.md"
            ;;
        shell-function)
            template_name="tool-shell-function-template.md"
            ;;
    esac
    
    # Check template locations
    if [ -f "$ROOT_DIR/.specify/templates/$template_name" ]; then
        echo "$ROOT_DIR/.specify/templates/$template_name"
    elif [ -f "$ROOT_DIR/templates/$template_name" ]; then
        echo "$ROOT_DIR/templates/$template_name"
    else
        echo ""
    fi
}

# Create tool record from template
create_tool_record() {
    local tool_name="$1"
    local tool_type="$2"
    local source_identifier="$3"
    local description="$4"
    
    mkdir -p "$TOOLS_MEMORY_DIR"
    
    local template_file
    template_file=$(get_template_file "$tool_type")
    
    if [ -z "$template_file" ]; then
        report_error "Template not found for tool type '$tool_type'" "$JSON_MODE"
        exit 1
    fi
    
    local record_file="$TOOLS_MEMORY_DIR/${tool_name}.md"
    local canonical_path
    canonical_path=$(to_workspace_relative "$record_file")
    local tool_id
    tool_id=$(format_tool_id "$canonical_path")
    local date_today
    date_today=$(date +%Y-%m-%d)
    
    # Replace placeholders in template
    sed -e "s/\[TOOL NAME\]/$tool_name/g" \
        -e "s/\[TOOL TYPE\]/$tool_type/g" \
        -e "s/\[SOURCE IDENTIFIER\]/$source_identifier/g" \
        -e "s|\[TOOL ID\]|$tool_id|g" \
        -e "s|\[RESOURCE ID\]|$tool_id|g" \
        -e "s|\[CANONICAL PATH\]|$canonical_path|g" \
        -e "s/\[YYYY-MM-DD\]/$date_today/g" \
        -e "s/\[Short, user-friendly description of what .* and when to use it\]/$description/g" \
        "$template_file" > "$record_file"
    
    echo "$record_file|$canonical_path|$tool_id"
}

# List all available tools
list_all_tools() {
    local json_data
    if ! json_data=$(refresh_all_tools_json); then
        report_error "Failed to refresh tool inventory" "$JSON_MODE"
        return 1
    fi
    
    # Create Python script to format output
    local py_script
    py_script=$(mktemp)
    cat > "$py_script" << 'PYEOF'
import sys
import json

json_data = sys.stdin.read()

try:
    data = json.loads(json_data)
except json.JSONDecodeError:
    print(json.dumps({"error": "Invalid JSON from refresh-tools.sh"}))
    sys.exit(1)

# Flatten all tool sources
all_tools = []

# Handle different JSON structures from refresh-tools.sh
if isinstance(data, dict) and isinstance(data.get('tools'), list):
    all_tools.extend(tool for tool in data.get('tools', []) if isinstance(tool, dict))
elif isinstance(data, dict):
    # Check for MCP tools structure (with servers array)
    if 'servers' in data:
        for server in data.get('servers', []):
            if isinstance(server, dict) and 'tools' in server:
                for tool in server.get('tools', []):
                    if isinstance(tool, dict):
                        tool['source_type'] = 'mcp-call'
                        tool['server_name'] = server.get('name', 'unknown')
                        all_tools.append(tool)
    
    # Check for system tools structure (with binaries array)
    if 'binaries' in data:
        for binary in data.get('binaries', []):
            if isinstance(binary, dict):
                binary['source_type'] = 'system-binary'
                all_tools.append(binary)
    
    # Check for shell functions (list at top level)
    if 'functions' in data:
        for func in data.get('functions', []):
            if isinstance(func, dict):
                func['source_type'] = 'shell-function'
                all_tools.append(func)
    
    # Check for project scripts (list at top level)
    if 'scripts' in data:
        for script in data.get('scripts', []):
            if isinstance(script, dict):
                script['source_type'] = 'project-script'
                all_tools.append(script)

# Format output
if len(all_tools) == 0:
    print("No tools found. Make sure refresh-tools.sh is working correctly.")
else:
    print(f"Found {len(all_tools)} tools:\n")
    for tool in all_tools:
        name = tool.get('name', 'unknown')
        source_type = tool.get('source_type', 'unknown')
        desc = tool.get('description', 'No description')[:100]
        print(f"  - {name} ({source_type})")
        print(f"    {desc}")
        print()
PYEOF
    
    # Execute Python script with JSON data
    echo "$json_data" | python3 "$py_script"
    local ret=$?
    
    # Cleanup
    rm -f "$py_script"
    
    return $ret
}

# Main logic
case "$ACTION" in
    list)
        list_all_tools
        ;;
    find|create)
        if [ -z "$TOOL_NAME" ]; then
            report_error "Tool name is required for action '$ACTION'" "$JSON_MODE"
            exit 1
        fi
        
        # Refresh and get all tools
        if ! json_data=$(refresh_all_tools_json); then
            report_error "Failed to refresh tool inventory" "$JSON_MODE"
            exit 1
        fi
        
        # Find tool in JSON data
        if ! find_result=$(find_tool_in_json "$TOOL_NAME" "$json_data"); then
            report_error "Invalid JSON from refresh-tools.sh" "$JSON_MODE"
            exit 1
        fi
        
        if [ "$ACTION" = "find" ]; then
            echo "$find_result"
            exit 0
        fi

        # Check if we need to create a new record
        if [ "$ACTION" = "create" ]; then
            status=$(echo "$find_result" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status',''))")
            
            if [ "$status" = "not_found" ]; then
                if [ -z "$TOOL_TYPE" ]; then
                    report_error "Tool type is required when creating a new tool. Use --type <type>" "$JSON_MODE"
                    exit 1
                fi
                
                validate_tool_type "$TOOL_TYPE" || exit 1
                
                # Extract source identifier from tool name or use default
                source_identifier="$TOOL_NAME"
                description="Tool for $TOOL_NAME"
                
                creation_output=$(create_tool_record "$TOOL_NAME" "$TOOL_TYPE" "$source_identifier" "$description")
                record_file="${creation_output%%|*}"
                rest="${creation_output#*|}"
                canonical_path="${rest%%|*}"
                tool_id="${rest#*|}"
                
                if [ "$JSON_MODE" = true ]; then
                    echo "{\"status\": \"created\", \"record_file\": \"$record_file\", \"canonical_path\": \"$canonical_path\", \"tool_id\": \"$tool_id\"}"
                else
                    echo "Created tool record: $record_file"
                    echo "tool_id: $tool_id"
                fi
            elif [ "$status" = "found" ] || [ "$status" = "multiple_matches" ]; then
                resolved_tool_name=$(echo "$find_result" | python3 -c "import sys,json; data=json.load(sys.stdin); print((data.get('tool') or {}).get('name',''))" 2>/dev/null || true)
                if [ -z "$resolved_tool_name" ]; then
                    resolved_tool_name="$TOOL_NAME"
                fi

                record_file="$TOOLS_MEMORY_DIR/${resolved_tool_name}.md"
                canonical_path=".specify/memory/tools/${resolved_tool_name}.md"
                tool_id=$(format_tool_id "$canonical_path")

                if [ -f "$record_file" ]; then
                    ensure_tool_id_in_record "$record_file" "$tool_id"
                fi

                if [ "$JSON_MODE" = true ]; then
                    echo "{\"status\": \"exists\", \"message\": \"Tool record already exists or multiple matches found\", \"record_file\": \"$record_file\", \"canonical_path\": \"$canonical_path\", \"tool_id\": \"$tool_id\"}"
                else
                    echo "Tool already exists or multiple matches found. Use --type to disambiguate."
                    echo "tool_id: $tool_id"
                fi
            fi
        fi
        ;;
    *)
        report_error "Unknown action '$ACTION'. Use: find, create, or list" "$JSON_MODE"
        exit 1
        ;;
esac
