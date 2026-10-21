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

# Size budget for the generated instruction file, in bytes. Host AI agent CLIs
# warn once the instruction chain they load reaches this size, so the generator
# reports it here instead of leaving the operator to relay the host's warning
# back into /speckit.instructions by hand. This constant is the ONLY definition
# of the number: the command template references the script's report and never
# restates the value.
INSTRUCTIONS_BUDGET_BYTES=32768

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

# Report the generated file's size against INSTRUCTIONS_BUDGET_BYTES, plus a
# per-section table comparing the live file against the rendered template.
# Advisory by design and always exit 0: this script runs inside `specify init`
# for every downstream project, so failing here would leave an over-budget
# project unable to initialize or refresh its instructions at all. Converging
# the file is /speckit.instructions Action 5's job (two routes: compress a
# framework section back to the template's own shape; promote an over-thick
# project-specific section to a docs/ owner document).
#
# The table is always emitted, not only over budget: Action 2 consumes it as
# the run's observation snapshot and Routes R1/R2 take their candidates from
# it, so measuring here is what keeps both routes from re-deriving sizes and
# classifications by eye. Its columns are the facts the routes branch on —
# `placeholder` (the template version still carries a `[...]` / `{{VAR}}`
# token, i.e. a scaffold the project is meant to fill) and `project-owned`
# (the template has no such heading at all).
report_instructions_budget() {
  local target="$1"
  local template="$2"
  local rendered
  rendered="$(mktemp)"
  render_template "$template" > "$rendered"
  local budget_out
  budget_out="$(python3 - "$target" "$rendered" "$INSTRUCTIONS_BUDGET_BYTES" <<'PYEOF'
import re
import sys

live_path, template_path, budget = sys.argv[1], sys.argv[2], int(sys.argv[3])
live_text = open(live_path, encoding="utf-8").read()
size = len(live_text.encode("utf-8"))
print("BUDGET: {} {} {}".format(size, budget, "over" if size >= budget else "within"))

PREAMBLE = "(before the first ## heading)"
# A bracket token followed by `(` is a Markdown link, not an unfilled scaffold;
# counting it would hide a genuine Route R1 candidate behind placeholder=yes.
PLACEHOLDER_RE = re.compile(r"\[[^\]\n]*\](?!\()|\{\{[A-Za-z0-9_]+\}\}")


# Same section granularity as the additive reconcile below, so the measurement
# and the injection logic cannot disagree about what counts as one section.
def sections(text):
    parts = re.split(r"(?m)^(## .+)$", text)
    out = [(PREAMBLE, parts[0])] if parts[0].strip() else []
    for i in range(1, len(parts) - 1, 2):
        out.append((parts[i].lstrip("# ").strip(), parts[i] + parts[i + 1]))
    return out


template_sections = dict(sections(open(template_path, encoding="utf-8").read()))

rows = []
for name, body in sections(live_text):
    live_bytes = len(body.encode("utf-8"))
    template_body = template_sections.get(name)
    template_bytes = len(template_body.encode("utf-8")) if template_body else 0
    delta = live_bytes - template_bytes
    rows.append((
        name,
        live_bytes,
        template_bytes,
        "{:+d}".format(delta) if delta else "0",
        "yes" if template_body and PLACEHOLDER_RE.search(template_body) else "no",
        "no" if template_body else "yes",
    ))
rows.sort(key=lambda row: row[1], reverse=True)

header = ("section", "live B", "tmpl B", "delta", "placeholder", "project-owned")
widths = [max([len(str(r[i])) for r in rows] + [len(header[i])]) for i in range(6)]


def row_line(cells):
    return "| " + " | ".join(str(c).ljust(w) for c, w in zip(cells, widths)) + " |"


print("ROW:" + row_line(header))
print("ROW:|" + "|".join("-" * (w + 2) for w in widths) + "|")
for row in rows:
    print("ROW:" + row_line(row))
PYEOF
  )"
  rm -f "$rendered"
  local size budget_n verdict
  size="$(printf '%s\n' "$budget_out" | sed -n 's/^BUDGET: \([0-9]*\) .*/\1/p')"
  budget_n="$(printf '%s\n' "$budget_out" | sed -n 's/^BUDGET: [0-9]* \([0-9]*\) .*/\1/p')"
  verdict="$(printf '%s\n' "$budget_out" | sed -n 's/^BUDGET: [0-9]* [0-9]* \(.*\)$/\1/p')"
  if [ "$verdict" = "over" ]; then
    log warning "Instructions size ${size} B has reached the ${budget_n} B budget (over by $((size - budget_n)) B). Section table, largest first:"
  else
    log info "Instructions size: ${size} B (budget ${budget_n} B, $((budget_n - size)) B headroom). Section table, largest first:"
  fi
  printf '%s\n' "$budget_out" | sed -n 's/^ROW://p'
  if [ "$verdict" = "over" ]; then
    log warning "Large instructions may impact agent performance. Run /speckit.instructions to converge the file (Action 5 owns both routes)."
  fi
}

# T007: Backup + establish refresh base + additive section reconcile
#
# Non-destructive policy: when instructions already exist, that file is the
# canonical refresh BASE. The script never renders the template over it and
# never modifies or removes existing sections (governance rules, recurring
# lessons, registries, and other hand-authored knowledge) — with one
# sanctioned exception: a legacy section that the template explicitly renamed
# (see SUPERSEDED_BY below) is stripped once its successor is present, so the
# stale block no longer needs a manual transcription-risky agent edit. It
# only writes a timestamped backup as a safety net. Deep section-by-section
# refresh — reconciling section CONTENT against current project reality —
# stays the /speckit.instructions command's job.
#
# Additive section reconcile (Constitution XI v1.10.0 mechanism fix,
# 2026-08-14): top-level sections present in the template but MISSING from
# the live file are injected verbatim (rendered, in template order). Before
# this, sections added to the template after a project's initial bootstrap
# (e.g. ## Dogfooding Practice, ## Spec Kit Framework Map) never propagated.
# Guarded by tests/contract/test_instructions_section_propagation.py.
#
# The template is used to bootstrap a brand-new file when none exists, and
# as the section-set reference for the reconcile above.
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

  # Additive section reconcile: inject template sections missing from the
  # live file. Existing sections are never touched — with ONE sanctioned
  # exception (F-E10): when the template replaces a legacy section with a
  # renamed successor (## Resource Registry → ## Skills & Tools), the script
  # itself strips the superseded block it knows the pairing for, instead of
  # leaving a manual, transcription-risky agent edit and a stale-registry
  # window. A timestamped backup of the pre-strip file was written above.
  # Idempotent by design.
  RENDERED_TEMPLATE="$(mktemp)"
  render_template "$TEMPLATE_FILE" > "$RENDERED_TEMPLATE"
  RECONCILE_OUTPUT="$(python3 - "$RENDERED_TEMPLATE" "$TARGET_FILE" <<'PYEOF'
import re
import sys

rendered_path, target_path = sys.argv[1], sys.argv[2]
template = open(rendered_path, encoding="utf-8").read()
live = open(target_path, encoding="utf-8").read()

parts = re.split(r"(?m)^(## .+)$", template)
sections = [(parts[i], parts[i + 1]) for i in range(1, len(parts) - 1, 2)]
live_headings = set(re.findall(r"(?m)^## .+$", live))
missing = [(h, b) for h, b in sections if h not in live_headings]

lines = live.rstrip("\n").split("\n")
if missing:
    template_order = [h for h, _ in sections]
    for heading, body in missing:
        later = set(template_order[template_order.index(heading) + 1:])
        insert_at = next((i for i, ln in enumerate(lines) if ln in later), None)
        block = (heading + body).strip("\n").split("\n") + [""]
        if insert_at is None:
            lines = (lines + [""] if lines else []) + block
        else:
            lines = lines[:insert_at] + block + lines[insert_at:]

# Supersession strip: successor present in the live file (pre-existing or
# just injected) → remove the specific legacy section(s) it replaced, from
# the heading through the line before the next top-level `## ` heading.
SUPERSEDED_BY = {"## Skills & Tools": ("## Resource Registry",)}
current_headings = set(re.findall(r"(?m)^## .+$", "\n".join(lines)))
stripped = []
for successor, legacy_headings in SUPERSEDED_BY.items():
    if successor not in current_headings:
        continue
    for legacy in legacy_headings:
        kept = []
        removed = False
        i = 0
        while i < len(lines):
            if lines[i].strip() == legacy:
                removed = True
                i += 1
                while i < len(lines) and not lines[i].startswith("## "):
                    i += 1
                while i < len(lines) and not lines[i].strip():
                    i += 1
                if kept and kept[-1].strip():
                    kept.append("")
                continue
            kept.append(lines[i])
            i += 1
        if removed:
            lines = kept
            stripped.append(legacy)

if missing or stripped:
    open(target_path, "w", encoding="utf-8").write("\n".join(lines).rstrip("\n") + "\n")
if missing:
    print("INJECTED: " + ", ".join(h.lstrip("# ").strip() for h, _ in missing))
if stripped:
    print("STRIPPED: " + ", ".join(s.lstrip("# ").strip() for s in stripped))
PYEOF
  )"
  rm -f "$RENDERED_TEMPLATE"
  INJECTED_SECTIONS="$(printf '%s\n' "$RECONCILE_OUTPUT" | sed -n 's/^INJECTED: //p')"
  STRIPPED_SECTIONS="$(printf '%s\n' "$RECONCILE_OUTPUT" | sed -n 's/^STRIPPED: //p')"
  if [ -n "$INJECTED_SECTIONS" ]; then
    log info "Injected missing template section(s): $INJECTED_SECTIONS"
  else
    log info "Section reconcile: live instructions already carry all template sections."
  fi
  if [ -n "$STRIPPED_SECTIONS" ]; then
    log info "Stripped superseded legacy section(s): $STRIPPED_SECTIONS (replaced by its successor; see backup above)"
  fi

  log info "The /speckit.instructions command reconciles each section against current"
  log info "project state and the latest template, and can recover content dropped by"
  log info "older versions from the .specify/instructions.md-* backup history."
else
  log info "Generating new instructions file from template..."
  render_template "$TEMPLATE_FILE" >"$TARGET_FILE"
fi

# One call site after the branch, so a first-time bootstrap reports its size too.
report_instructions_budget "$TARGET_FILE" "$TEMPLATE_FILE"

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

# Create the skills/tools explanation docs at .specify top level (create-only,
# never overwrite — same non-destructive policy as the glossary). These carry
# the no-registry discovery model; canonical sources live in .specify/templates/.
for doc_name in skills tools; do
  DOC_TEMPLATE=".specify/templates/${doc_name}.md"
  DOC_TARGET="$TARGET_DIR/${doc_name}.md"
  if [ -f "$DOC_TEMPLATE" ] && [ ! -f "$DOC_TARGET" ]; then
    render_template "$DOC_TEMPLATE" > "$DOC_TARGET"
    log info "Created $DOC_TARGET (non-destructive)"
  fi
done

# Cleanup deprecated AI tool artifacts
for deprecated_dir in .clinerules .lingma .trae; do
  if [ -d "$deprecated_dir" ]; then
    rm -rf "$deprecated_dir"
    log info "Removed deprecated $deprecated_dir directory"
  fi
done
for deprecated_file in .cursorrules; do
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

# .qoder — project_rules.md serves the Qoder IDE (old format) only; Qoder CLI
# (qodercli) reads the root AGENTS.md symlink instead and never loads this file.
mkdir -p .qoder
pushd .qoder >/dev/null
ln -sf ../.specify/instructions.md project_rules.md
popd >/dev/null

# .claude
mkdir -p .claude
pushd .claude >/dev/null
ln -sf ../.specify/instructions.md project_rules.md
popd >/dev/null

# .opencode
mkdir -p .opencode
pushd .opencode >/dev/null
ln -sf ../.specify/instructions.md instructions.md
popd >/dev/null

# Root level links
ln -sf .specify/instructions.md CLAUDE.md
ln -sf .specify/instructions.md QODER.md
ln -sf .specify/instructions.md AGENTS.md
ln -sf .specify/instructions.md HERMES.md

log success "Instructions generated/updated at $TARGET_FILE"
