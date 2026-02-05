#!/bin/bash
set -e

# Load common helpers for Unicode support and shared functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/common.sh" ]; then
    # shellcheck source=/dev/null
    source "$SCRIPT_DIR/common.sh"
    # Ensure UTF-8 locale for better Unicode handling
    ensure_utf8_locale || true
fi

if ! command -v log &>/dev/null; then
  function log() { echo "[$1] $2"; }
fi

PROJECT_ROOT="$PWD"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
CURRENT_DATE="$(date +%Y-%m-%d)"
REPO_ROOT="$(git_repo_root)"

TEMPLATE_FILE=".specify/templates/instructions-template.md"
# Detect template path (User perspective vs Source perspective)
if [ ! -f ".specify/templates/instructions-template.md" ]; then
  log error "Template file not found at $TEMPLATE_FILE. Please create it or copy it from defaults. "
  exit 1
fi

TARGET_FILE=".ai/instructions.md"
TARGET_DIR=".ai"

mkdir -p "$TARGET_DIR"

# Generate tools documentation
TOOLS_DIR="$TARGET_DIR/tools"
mkdir -p "$TOOLS_DIR"
if [ -f "$SCRIPT_DIR/refresh-tools.sh" ]; then
  log info "Generating tools documentation..."
  "$SCRIPT_DIR/refresh-tools.sh" --mcp --format markdown > "$TOOLS_DIR/mcp.md"
  "$SCRIPT_DIR/refresh-tools.sh" --system --format markdown > "$TOOLS_DIR/system.md"
  "$SCRIPT_DIR/refresh-tools.sh" --shell --format markdown > "$TOOLS_DIR/shell.md"
  "$SCRIPT_DIR/refresh-tools.sh" --project --format markdown > "$TOOLS_DIR/project.md"
  gitignore_add_pattern ".ai/tools/*.md" "$REPO_ROOT/.gitignore"
else
  log warning "refresh-tools.sh not found, skipping tools documentation generation."
fi

SAFE_PROJECT_NAME=$(escape_sed "$PROJECT_NAME")
SAFE_PROJECT_ROOT=$(escape_sed "$PROJECT_ROOT")
SAFE_DATE=$(escape_sed "$CURRENT_DATE")

# Function to render template
render_template() {
  local input_file="$1"
  sed -e "s/{{PROJECT_NAME}}/$SAFE_PROJECT_NAME/g" \
    -e "s/{{PROJECT_ROOT}}/$SAFE_PROJECT_ROOT/g" \
    -e "s/{{DATE}}/$SAFE_DATE/g" \
    "$input_file"
}

# Function to extract section body: Text between `## Header` and the CA start of next header `##` or `#`
extract_section_body() {
  local file="$1"
  local header_pattern="$2"

  # Check if header exists
  if ! grep -q "$header_pattern" "$file"; then
    return 0
  fi

  # Find start line
  local start_line=$(grep -n "$header_pattern" "$file" | head -1 | cut -d: -f1)

  # Start reading from the line AFTER the header
  local body_start=$((start_line + 1))

  # Print from body_start until next line starting with #
  # We use awk to print lines until we see a line starting with top-level header '#'
  # Note: This implies we only preserve top-level content blocks properly if they are delimited by headings
  tail -n "+$body_start" "$file" | awk '/^#/ { exit } { print }'
}

# T007: Backup
if [ -f "$TARGET_FILE" ]; then
  BACKUP_FILE="${TARGET_FILE}-$(date '+%Y-%m-%d')"
  log info "Backing up existing instructions to $BACKUP_FILE"
  cp "$TARGET_FILE" "$BACKUP_FILE"

  log info "Performing Smart Fusion..."

  # T008/T009: Smart Fusion Logic
  # 1. Render the NEW template to a temp file
  TEMP_NEW=$(mktemp)
  render_template "$TEMPLATE_FILE" >"$TEMP_NEW"

  # 2. Extract "Project Overview" from OLD file (Preserve user context)
  OLD_OVERVIEW=$(extract_section_body "$BACKUP_FILE" "^## Project Overview")

  # 3. Construct the fused file
  if [ ! -z "$OLD_OVERVIEW" ] && [ "$OLD_OVERVIEW" != "" ]; then
    log info "Preserving existing Project Overview..."
    FUSED_FILE=$(mktemp)

    # Methodology: Replace contents of "## Project Overview" in TEMP_NEW

    # Print header
    awk '/^## Project Overview/ { print; exit }' "$TEMP_NEW" >"$FUSED_FILE"

    # Append old content
    echo "$OLD_OVERVIEW" >>"$FUSED_FILE"

    # Find start of NEXT section in TEMP_NEW
    OVERVIEW_LINE=$(grep -n "^## Project Overview" "$TEMP_NEW" | cut -d: -f1)
    NEXT_SECTION_REL=$(tail -n "+$((OVERVIEW_LINE + 1))" "$TEMP_NEW" | grep -n "^#" | head -1 | cut -d: -f1)

    if [ ! -z "$NEXT_SECTION_REL" ]; then
      ABS_NEXT_LINE=$((OVERVIEW_LINE + NEXT_SECTION_REL))
      tail -n "+$ABS_NEXT_LINE" "$TEMP_NEW" >>"$FUSED_FILE"
    fi

    mv "$FUSED_FILE" "$TARGET_FILE"
  else
    log info "No existing Project Overview found or empty. Using template default."
    mv "$TEMP_NEW" "$TARGET_FILE"
  fi

  rm -f "$TEMP_NEW"

else
  log info "Generating new instructions file from template..."
  render_template "$TEMPLATE_FILE" >"$TARGET_FILE"
fi

# T010: Symlinks
log info "Updating symlinks for AI tools..."

# .clinerules
mkdir -p .clinerules
pushd .clinerules >/dev/null
ln -sf ../.ai/instructions.md project_rules.md
popd >/dev/null

# .github
mkdir -p .github
pushd .github >/dev/null
ln -sf ../.ai/instructions.md copilot-instructions.md
popd >/dev/null

# .lingma
mkdir -p .lingma/rules
pushd .lingma/rules >/dev/null
ln -sf ../../.ai/instructions.md project_rule.md
popd >/dev/null

# .trae
mkdir -p .trae/rules
pushd .trae/rules >/dev/null
ln -sf ../../.ai/instructions.md project_rules.md
popd >/dev/null

# .qoder
mkdir -p .qoder
pushd .qoder >/dev/null
ln -sf ../.ai/instructions.md project_rules.md
popd >/dev/null

# Root level links
ln -sf .ai/instructions.md QWEN.md
ln -sf .ai/instructions.md CLAUDE.md
ln -sf .ai/instructions.md IFLOW.md

log success "Instructions generated/updated at $TARGET_FILE"
