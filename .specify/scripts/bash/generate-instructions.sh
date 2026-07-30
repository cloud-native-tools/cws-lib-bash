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

TARGET_FILE=".specify/instructions.md"
TARGET_DIR=".specify"

mkdir -p "$TARGET_DIR"

# Generate JSON tool manifests
TOOLS_DIR="$TARGET_DIR/tools"
mkdir -p "$TOOLS_DIR"
if [ -f "$SCRIPT_DIR/refresh-tools.sh" ]; then
  log info "Generating tool JSON manifests..."
  "$SCRIPT_DIR/refresh-tools.sh" --system --json > "$TOOLS_DIR/system.json"
  "$SCRIPT_DIR/refresh-tools.sh" --shell --json > "$TOOLS_DIR/shell.json"
  "$SCRIPT_DIR/refresh-tools.sh" --project --json > "$TOOLS_DIR/project.json"
  gitignore_add_pattern ".specify/tools/*.json" "$REPO_ROOT/.gitignore"
else
  log warning "refresh-tools.sh not found, skipping tool JSON manifest generation."
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

# T007: Backup + establish refresh base
#
# Non-destructive policy: when instructions already exist, that file is the
# canonical refresh BASE. The script never renders the template over it and
# never discards non-"Project Overview" sections (governance rules, recurring
# lessons, registries, and other hand-authored knowledge). It only writes a
# timestamped backup as a safety net. The full section-by-section refresh —
# reconciling each section against current project reality and the latest
# template structure — is performed by the /speckit.instructions command.
#
# The template is used ONLY to bootstrap a brand-new file when none exists.
#
# Backups are NON-CLOBBERING and fully timestamped (down to the second). An
# older date-only name was overwritten by a second run on the same day, which
# could destroy a pristine pre-damage copy. Preserving every generation keeps
# the .specify/instructions.md-* history intact so a project damaged by an
# older overwriting version can recover lost content via /speckit.instructions.
if [ -f "$TARGET_FILE" ]; then
  BACKUP_FILE="${TARGET_FILE}-$(date '+%Y-%m-%d-%H%M%S')"
  # Guard against a collision within the same second (never overwrite history).
  if [ -e "$BACKUP_FILE" ]; then
    BACKUP_FILE="${BACKUP_FILE}-$$"
  fi
  log info "Backing up existing instructions to $BACKUP_FILE"
  cp "$TARGET_FILE" "$BACKUP_FILE"
  # Keep the accumulating local backups out of version control.
  gitignore_add_pattern ".specify/instructions.md-*" "$REPO_ROOT/.gitignore"

  log info "Existing instructions kept as the refresh base (not overwritten)."
  log info "The /speckit.instructions command reconciles each section against current"
  log info "project state and the latest template, and can recover content dropped by"
  log info "older versions from the .specify/instructions.md-* backup history."
else
  log info "Generating new instructions file from template..."
  render_template "$TEMPLATE_FILE" >"$TARGET_FILE"
fi

# Initialize the project glossary (non-destructive; create only if absent).
# The glossary anchors project vocabulary and corrects voice/dictated input;
# it is loaded ambiently by every /speckit.* command via the Documentation Map.
GLOSSARY_ENGINE="$SCRIPT_DIR/../python/glossary-utils.py"
GLOSSARY_TEMPLATE=".specify/templates/glossary-template.md"
if [ -f "$GLOSSARY_ENGINE" ] && [ -f "$GLOSSARY_TEMPLATE" ]; then
  if python3 "$GLOSSARY_ENGINE" --action init --from-template "$GLOSSARY_TEMPLATE" >/dev/null 2>&1; then
    log info "Ensured project glossary at .specify/memory/glossary.md (non-destructive)"
  else
    log warning "Glossary init skipped (engine returned non-zero)"
  fi
else
  log warning "Glossary engine or template not found; skipping glossary initialization"
fi

# Cleanup deprecated AI tool artifacts
for deprecated_dir in .clinerules .lingma .trae; do
  if [ -d "$deprecated_dir" ]; then
    rm -rf "$deprecated_dir"
    log info "Removed deprecated $deprecated_dir directory"
  fi
done
for deprecated_file in IFLOW.md .cursorrules; do
  if [ -L "$deprecated_file" ] || [ -f "$deprecated_file" ]; then
    rm -f "$deprecated_file"
    log info "Removed deprecated $deprecated_file"
  fi
done

# T010: Symlinks
log info "Updating symlinks for AI tools..."

# .github
mkdir -p .github
pushd .github >/dev/null
ln -sf ../.specify/instructions.md copilot-instructions.md
popd >/dev/null

# .qoder
mkdir -p .qoder
pushd .qoder >/dev/null
ln -sf ../.specify/instructions.md project_rules.md
popd >/dev/null

# .claude
mkdir -p .claude
pushd .claude >/dev/null
ln -sf ../.specify/instructions.md project_rules.md
popd >/dev/null

# Root level links
ln -sf .specify/instructions.md QWEN.md
ln -sf .specify/instructions.md CLAUDE.md
ln -sf .specify/instructions.md QODER.md
ln -sf .specify/instructions.md AGENTS.md

log success "Instructions generated/updated at $TARGET_FILE"
