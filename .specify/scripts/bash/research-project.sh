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

# Parse command line arguments
JSON_MODE=false
ARGS=()

for arg in "$@"; do
    case "$arg" in
        --json) 
            JSON_MODE=true 
            ;;
        --help|-h) 
            echo "Usage: $0 [--json]"
            echo "  --json    Output results in JSON format"
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

# Ensure the feature directory exists
mkdir -p "$REQUIREMENTS_DIR"

# --- NEW: Research Gathering ---

get_md_title() {
    local file="$1"
    # Read first 5 lines (head -n 5) and look for first header
    local header=$(head -n 5 "$file" | grep -m 1 "^#\{1,\} ")
    if [ -n "$header" ]; then
        # Remove leading hashes and whitespace
        echo "$header" | sed 's/^#\{1,\}[[:space:]]*//'
    else
        echo "(No title)"
    fi
}

# Collect docs
# Find markdown files, applying specific inclusion/exclusion rules
DOC_PATHS=()

# Helper to check exclusion and add to array
add_doc_path() {
    local path="$1"
    # Exclusion list
    if [[ "$path" == "CLAUDE.md" ]] || \
       [[ "$path" == "QWEN.md" ]] || \
       [[ "$path" == ".github/copilot-instructions.md" ]] || \
       [[ "$path" == ".ai/instructions.md" ]]; then
       return
    fi
    
    if [ -f "$path" ]; then
        # Avoid duplicates
        for e in "${DOC_PATHS[@]}"; do [[ "$e" == "$path" ]] && return 0; done
        DOC_PATHS+=("$path")
    fi
}

# 1. Project Root Docs (Restricted set)
for f in README.md CONTRIBUTING.md BUILDING.md; do
    add_doc_path "$f"
done

# 2. docs/ folder (recursive find for .md files)
if [ -d "docs" ]; then
    while IFS= read -r f; do
        add_doc_path "$f"
    done < <(find docs -name "*.md" | sort)
fi

# 3. Memory (Constitution and Feature Index)
if [ -d ".specify/memory" ]; then
    add_doc_path ".specify/memory/constitution.md"
    add_doc_path ".specify/memory/features.md"
fi

# 4. Current Feature Spec (if likely planning)
if [ -f "$FEATURE_SPEC" ]; then
    add_doc_path "$FEATURE_SPEC"
fi

# Build Human Readable DOC_LIST (path: title)
DOC_LIST=""
for path in "${DOC_PATHS[@]}"; do
    title=$(get_md_title "$path")
    DOC_LIST+="$path: $title"$'\n'
done

# Output results
if $JSON_MODE; then
    # Use python to format JSON correctly
    export FEATURE_SPEC IMPL_PLAN REQUIREMENTS_DIR CURRENT_BRANCH HAS_GIT
    export DOC_PATHS_STR=$(printf "%s\n" "${DOC_PATHS[@]}")
    python3 -c "
import json, os, re

def get_md_title(filepath):
    try:
        if not os.path.exists(filepath):
            return '(No title)'
        
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        # 1. Try to find a header in the first 5 lines
        for i in range(min(5, len(lines))):
            line = lines[i]
            # Match line starting with one or more # followed by space
            if re.match(r'^#+\s+', line):
                    return re.sub(r'^#+\s*', '', line).strip()
        
        # 2. Fallback: Take first 3 non-empty lines
        non_empty_lines = [line.strip() for line in lines if line.strip()]
        if non_empty_lines:
            return ' '.join(non_empty_lines[:3])
            
        return '(No title)'
    except Exception:
        return '(No title)'

doc_paths_str = os.environ.get('DOC_PATHS_STR', '')
doc_paths = [p for p in doc_paths_str.split('\n') if p]

available_docs = []
for p in doc_paths:
    available_docs.append({
        'path': p, 
        'title': get_md_title(p)
    })

data = {
    'FEATURE_SPEC': os.environ.get('FEATURE_SPEC'),
    'IMPL_PLAN': os.environ.get('IMPL_PLAN'),
    'SPECS_DIR': os.environ.get('REQUIREMENTS_DIR'),
    'BRANCH': os.environ.get('CURRENT_BRANCH'),
    'HAS_GIT': os.environ.get('HAS_GIT'),
    'AVAILABLE_DOCS': available_docs
}
print(json.dumps(data, ensure_ascii=False))
"
else
    echo "FEATURE_SPEC: $FEATURE_SPEC"
    echo "IMPL_PLAN: $IMPL_PLAN" 
    echo "SPECS_DIR: $REQUIREMENTS_DIR"
    echo "BRANCH: $CURRENT_BRANCH"
    echo "HAS_GIT: $HAS_GIT"
    echo "AVAILABLE_DOCS:"
    echo "$DOC_LIST"
fi
