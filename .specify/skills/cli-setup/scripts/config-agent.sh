#!/usr/bin/env bash
set -euo pipefail

# FR-016: Self-compute SKILL_HOME and SKILL_WORKDIR
SKILL_HOME="${SKILL_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd -P)}"
SKILL_WORKDIR="${SKILL_WORKDIR:-$(pwd -P)}"

# Active configuration state directory
CONFIG_AGENT_STATE_DIR="${SKILL_WORKDIR}/.agent-config"
CONFIG_AGENT_STATE_FILE="${CONFIG_AGENT_STATE_DIR}/active.json"

# ============================================================
# Four-Tuple Registry
# Format: tool|model|provider|url_var|key_var|protocol
# protocol: anthropic | openai
# ============================================================
CONFIG_AGENT_TUPLES=(
  # --- claude (Anthropic protocol) ---
  # Note: claude-opus-* models are NOT available on bailian.
  # claude-opus-4-8 is idealab-only; claude-opus-4-7 has no provider and is excluded.
  "claude|claude-opus-4-8|idealab|CLAUDE_OFFICIAL_BASE_URL|ANTHROPIC_AUTH_TOKEN|anthropic"
  "claude|qwen3.7-max|bailian|ALIYUN_ANTHROPIC_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|anthropic"
  "claude|qwen3.7-plus|bailian|ALIYUN_ANTHROPIC_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|anthropic"
  "claude|deepseek-v4-pro|bailian|ALIYUN_ANTHROPIC_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|anthropic"
  "claude|deepseek-v4-flash|bailian|ALIYUN_ANTHROPIC_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|anthropic"
  "claude|glm-5.2|bailian|ALIYUN_ANTHROPIC_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|anthropic"
  "claude|kimi-k2.7-code|bailian|ALIYUN_ANTHROPIC_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|anthropic"
  # --- codex (OpenAI protocol) ---
  "codex|qwen3-coder-plus|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "codex|qwen3.7-max|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "codex|qwen3.7-plus|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "codex|deepseek-v4-pro|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "codex|deepseek-v4-flash|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "codex|glm-5.2|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "codex|kimi-k2.7-code|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  # --- qwen (OpenAI protocol) ---
  "qwen|qwen3-coder-plus|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "qwen|qwen3.7-max|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "qwen|qwen3.7-plus|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "qwen|deepseek-v4-pro|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "qwen|deepseek-v4-flash|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "qwen|glm-5.2|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "qwen|kimi-k2.7-code|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  # --- qoder (OpenAI protocol) ---
  "qoder|qwen3-coder-plus|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "qoder|qwen3.7-max|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "qoder|qwen3.7-plus|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "qoder|deepseek-v4-pro|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "qoder|deepseek-v4-flash|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "qoder|glm-5.2|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "qoder|kimi-k2.7-code|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  # --- iflow (OpenAI protocol) ---
  "iflow|qwen3-coder-plus|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "iflow|qwen3.7-max|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "iflow|qwen3.7-plus|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "iflow|deepseek-v4-pro|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "iflow|deepseek-v4-flash|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "iflow|glm-5.2|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "iflow|kimi-k2.7-code|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  # --- opencode (OpenAI protocol) ---
  "opencode|qwen3-coder-plus|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "opencode|qwen3.7-max|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "opencode|qwen3.7-plus|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "opencode|deepseek-v4-pro|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "opencode|deepseek-v4-flash|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "opencode|glm-5.2|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
  "opencode|kimi-k2.7-code|bailian|ALIYUN_OPENAI_COMPATIBLE_URL|ALIYUN_BAILIAN_API_KEY|openai"
)

# Tool CLI binary names
declare -A CONFIG_AGENT_CLI=(
  [claude]="claude" [codex]="codex" [qwen]="qwen"
  [qoder]="qoder" [iflow]="iflow" [opencode]="opencode"
)

# Tool install commands
declare -A CONFIG_AGENT_INSTALL_CMD=(
  [claude]="npm install -g @anthropic-ai/claude-code"
  [codex]="npm install -g @openai/codex"
  [qwen]="npm install -g @qwen-code/qwen-code"
  [qoder]="curl -fsSL https://qoder.com/install | bash"
  [iflow]="npm install -g @iflow-ai/iflow-cli"
  [opencode]="brew install opencode 2>/dev/null || go install github.com/sst/opencode@latest"
)

# ============================================================
# Unified Env-Var Flow (024-agent-env-config)
# ------------------------------------------------------------
# A single set of skill-layer variables (AGENT_API_KEY, AGENT_MODEL,
# AGENT_BASE_URL, AGENT_ANTHROPIC_BASE_URL) is validated, read, and
# secondary-assigned into each tool's own config file. Scope: the six
# API-key CLIs. Copilot and Hermes Agent are out of scope (subscription/OAuth).
# ============================================================

# In-scope tools for the unified env-var flow.
CONFIG_AGENT_ENV_TOOLS=(claude codex qwen qoder iflow opencode)

# Profile registry: name|protocol|url_source|config_path|format
#   protocol   : anthropic | openai
#   url_source : anthropic_base_url (claude) | base_url (others)
#   config_path: path relative to $HOME
#   format     : json | toml | dotenv
CONFIG_AGENT_ENV_PROFILES=(
  "claude|anthropic|anthropic_base_url|.claude/settings.json|json"
  "codex|openai|base_url|.codex/config.toml|toml"
  "qwen|openai|base_url|.qwen/.env|dotenv"
  "qoder|openai|base_url|.qoder/config.json|json"
  "iflow|openai|base_url|.iflow/settings.json|json"
  "opencode|openai|base_url|.config/opencode/config.json|json"
)

# ============================================================
# Shared low-level helpers (unified env-var flow)
# ============================================================

# Trim leading/trailing whitespace.
_ca_trim() {
  local s="${1:-}"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "${s}"
}

# Ensure the parent directory of a file path exists.
_ca_ensure_dir() {
  local d
  d="$(dirname "$1")"
  [[ -d "${d}" ]] || mkdir -p "${d}"
}

# Return 0 iff the argument starts with an http(s):// scheme.
_ca_url_has_scheme() {
  [[ "${1:-}" =~ ^https?:// ]]
}

# Idempotently upsert KEY=VALUE into a dotenv file, preserving other lines.
# Usage: _ca_dotenv_upsert <file> <KEY> <VALUE>
_ca_dotenv_upsert() {
  local file="$1" k="$2" v="$3"
  _ca_ensure_dir "${file}"
  CA_K="${k}" CA_V="${v}" python3 - "${file}" <<'PY'
import os, sys
path = sys.argv[1]
k = os.environ["CA_K"]; v = os.environ["CA_V"]
prefix = k + "="
try:
    with open(path) as fh:
        lines = fh.read().splitlines()
except FileNotFoundError:
    lines = []
out = []
done = False
for ln in lines:
    if ln.startswith(prefix):
        if not done:
            out.append(prefix + v); done = True
        # drop any duplicate occurrences
    else:
        out.append(ln)
if not done:
    out.append(prefix + v)
with open(path, "w") as fh:
    fh.write("\n".join(out) + ("\n" if out else ""))
PY
}

# Deep-merge a JSON object into a file, preserving unrelated keys.
# The merge object is supplied via the _CA_MERGE_JSON environment variable
# (a JSON string). Fails (non-zero) if the existing file is not valid JSON.
# Usage: _CA_MERGE_JSON='{...}' _ca_json_merge <file>
_ca_json_merge() {
  local file="$1"
  _ca_ensure_dir "${file}"
  _CA_MERGE_JSON="${_CA_MERGE_JSON:-}" python3 - "${file}" <<'PY'
import json, os, sys
path = sys.argv[1]
merge = json.loads(os.environ.get("_CA_MERGE_JSON") or "{}")
base = {}
if os.path.exists(path) and os.path.getsize(path) > 0:
    with open(path) as fh:
        base = json.load(fh)
def deep(a, b):
    for key, val in b.items():
        if isinstance(val, dict) and isinstance(a.get(key), dict):
            deep(a[key], val)
        else:
            a[key] = val
    return a
deep(base, merge)
with open(path, "w") as fh:
    json.dump(base, fh, indent=2)
PY
}

# Write the codex managed TOML block (regenerated deterministically).
# Usage: _ca_toml_write_block <file> <model> <provider> <url>
_ca_toml_write_block() {
  local file="$1" model="$2" provider="$3" url="$4"
  _ca_ensure_dir "${file}"
  cat >"${file}" <<EOF
model = "${model}"
model_provider = "${provider}"

[model_providers.${provider}]
name = "${provider}"
base_url = "${url}"
env_key = "CODEX_API_KEY"
wire_api = "responses"
EOF
}

# ============================================================
# Helpers
# ============================================================

_config_agent_log() {
  local level="$1"; shift
  local msg="$*"
  local color=""
  case "${level}" in
    info)  color="\033[0;36m" ;;
    ok)    color="\033[0;32m" ;;
    warn)  color="\033[1;33m" ;;
    error) color="\033[0;31m" ;;
  esac
  printf "${color}[%s]\033[0m %s\n" "${level}" "${msg}"
}

_config_agent_get_tuple_field() {
  local tuple="$1"
  local field="$2"
  echo "${tuple}" | cut -d'|' -f"${field}"
}

_config_agent_find_tuple() {
  local tool="$1" model="$2" provider="$3"
  for tuple in "${CONFIG_AGENT_TUPLES[@]}"; do
    local t=$(_config_agent_get_tuple_field "${tuple}" 1)
    local m=$(_config_agent_get_tuple_field "${tuple}" 2)
    local p=$(_config_agent_get_tuple_field "${tuple}" 3)
    if [[ "${t}" == "${tool}" && "${m}" == "${model}" && "${p}" == "${provider}" ]]; then
      echo "${tuple}"
      return 0
    fi
  done
  return 1
}

_config_agent_resolve_var() {
  local varname="$1"
  local value="${!varname:-}"
  echo "${value}"
}

_config_agent_is_available() {
  local tuple="$1"
  local url_var=$(_config_agent_get_tuple_field "${tuple}" 4)
  local key_var=$(_config_agent_get_tuple_field "${tuple}" 5)
  local url_val=$(_config_agent_resolve_var "${url_var}")
  local key_val=$(_config_agent_resolve_var "${key_var}")
  [[ -n "${url_val}" && -n "${key_val}" ]]
}

_config_agent_ensure_state() {
  mkdir -p "${CONFIG_AGENT_STATE_DIR}"
  if [[ ! -f "${CONFIG_AGENT_STATE_FILE}" ]]; then
    echo '{}' > "${CONFIG_AGENT_STATE_FILE}"
  fi
}

_config_agent_read_state() {
  _config_agent_ensure_state
  cat "${CONFIG_AGENT_STATE_FILE}"
}

_config_agent_write_state() {
  local json="$1"
  _config_agent_ensure_state
  echo "${json}" > "${CONFIG_AGENT_STATE_FILE}"
}

# ============================================================
# Public Functions
# ============================================================

# List supported/available four-tuples
# Usage: config_agent_list [--all]
config_agent_list() {
  local show_all=false
  [[ "${1:-}" == "--all" ]] && show_all=true

  _config_agent_log info "Four-tuple list (${show_all:+all}${show_all:-available})"
  printf "%-8s %-20s %-10s %-10s %-40s %s\n" "TOOL" "MODEL" "PROVIDER" "PROTOCOL" "URL_VAR" "STATUS"
  printf "%s\n" "----------------------------------------------------------------------------------------"

  for tuple in "${CONFIG_AGENT_TUPLES[@]}"; do
    local tool=$(_config_agent_get_tuple_field "${tuple}" 1)
    local model=$(_config_agent_get_tuple_field "${tuple}" 2)
    local provider=$(_config_agent_get_tuple_field "${tuple}" 3)
    local url_var=$(_config_agent_get_tuple_field "${tuple}" 4)
    local protocol=$(_config_agent_get_tuple_field "${tuple}" 6)

    local status="unavailable"
    if _config_agent_is_available "${tuple}"; then
      status="available"
    fi

    if ! ${show_all} && [[ "${status}" == "unavailable" ]]; then
      continue
    fi

    printf "%-8s %-20s %-10s %-10s %-40s %s\n" "${tool}" "${model}" "${provider}" "${protocol}" "${url_var}" "${status}"
  done
}

# Validate a four-tuple
# Usage: config_agent_validate <tool> <model> <provider>
config_agent_validate() {
  local tool="${1:-}"
  local model="${2:-}"
  local provider="${3:-}"

  if [[ -z "${tool}" || -z "${model}" || -z "${provider}" ]]; then
    _config_agent_log error "Usage: config_agent_validate <tool> <model> <provider>"
    return 1
  fi

  local tuple
  tuple=$(_config_agent_find_tuple "${tool}" "${model}" "${provider}") || {
    _config_agent_log error "Unsupported four-tuple: (${tool}, ${model}, ${provider})"
    _config_agent_log info "Run 'config_agent_list --all' to see supported tuples"
    return 1
  }

  if ! _config_agent_is_available "${tuple}"; then
    local url_var=$(_config_agent_get_tuple_field "${tuple}" 4)
    local key_var=$(_config_agent_get_tuple_field "${tuple}" 5)
    _config_agent_log error "Four-tuple supported but credentials unavailable"
    _config_agent_log info "Missing: ${url_var} or ${key_var}"
    return 1
  fi

  _config_agent_log ok "Valid: (${tool}, ${model}, ${provider})"
  return 0
}

# Install a tool CLI
# Usage: config_agent_install <tool>
config_agent_install() {
  local tool="${1:-}"
  if [[ -z "${tool}" ]]; then
    _config_agent_log error "Usage: config_agent_install <tool>"
    _config_agent_log info "Tools: claude, codex, qwen, qoder, iflow, opencode"
    return 1
  fi

  local cli="${CONFIG_AGENT_CLI[${tool}]:-}"
  if [[ -z "${cli}" ]]; then
    _config_agent_log error "Unknown tool: ${tool}"
    return 1
  fi

  if command -v "${cli}" &>/dev/null; then
    _config_agent_log ok "${tool} CLI already installed: $(command -v "${cli}")"
    return 0
  fi

  local cmd="${CONFIG_AGENT_INSTALL_CMD[${tool}]:-}"
  if [[ -z "${cmd}" ]]; then
    _config_agent_log error "No install command for tool: ${tool}"
    return 1
  fi

  _config_agent_log info "Installing ${tool} CLI..."
  eval "${cmd}"
  local rc=$?
  if [[ ${rc} -eq 0 ]]; then
    _config_agent_log ok "${tool} CLI installed successfully"
  else
    _config_agent_log error "${tool} CLI installation failed (exit code: ${rc})"
  fi
  return ${rc}
}

# Configure a tool with a four-tuple (enforces mutual exclusion)
# Usage: config_agent_configure <tool> <model> <provider>
config_agent_configure() {
  local tool="${1:-}"
  local model="${2:-}"
  local provider="${3:-}"

  if [[ -z "${tool}" || -z "${model}" || -z "${provider}" ]]; then
    _config_agent_log error "Usage: config_agent_configure <tool> <model> <provider>"
    return 1
  fi

  # Validate
  config_agent_validate "${tool}" "${model}" "${provider}" || return 1

  local tuple
  tuple=$(_config_agent_find_tuple "${tool}" "${model}" "${provider}")
  local url_var=$(_config_agent_get_tuple_field "${tuple}" 4)
  local key_var=$(_config_agent_get_tuple_field "${tuple}" 5)

  local url_val=$(_config_agent_resolve_var "${url_var}")
  local key_val=$(_config_agent_resolve_var "${key_var}")

  # Mutual exclusion: check existing binding for this tool
  local state
  state=$(_config_agent_read_state)
  local existing
  existing=$(echo "${state}" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    t = d.get('${tool}', {})
    if t:
        print(f\"{t.get('model','')} {t.get('provider','')}\")
except: pass
" 2>/dev/null || echo "")

  if [[ -n "${existing}" ]]; then
    _config_agent_log warn "Replacing existing binding for ${tool}: ${existing}"
  fi

  # Write tool-specific config
  case "${tool}" in
    claude)  _config_agent_write_claude "${model}" "${url_val}" "${key_val}" ;;
    codex)   _config_agent_write_codex "${model}" "${provider}" "${url_val}" "${key_val}" ;;
    qwen)    _config_agent_write_qwen "${model}" "${url_val}" "${key_val}" ;;
    qoder)   _config_agent_write_qoder "${model}" "${url_val}" "${key_val}" ;;
    iflow)   _config_agent_write_iflow "${model}" "${url_val}" "${key_val}" ;;
    opencode) _config_agent_write_opencode "${model}" "${provider}" "${url_val}" "${key_val}" ;;
  esac

  # Update active state (mutual exclusion enforced by overwriting tool key)
  local new_state
  new_state=$(echo "${state}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
d['${tool}'] = {'model': '${model}', 'provider': '${provider}', 'url_var': '${url_var}', 'key_var': '${key_var}'}
json.dump(d, sys.stdout, indent=2)
" 2>/dev/null || echo "{\"${tool}\": {\"model\": \"${model}\", \"provider\": \"${provider}\"}}")

  _config_agent_write_state "${new_state}"
  _config_agent_log ok "Configured: (${tool}, ${model}, ${provider})"
}

# Show active configuration
# Usage: config_agent_show [tool]
config_agent_show() {
  local tool="${1:-}"
  local state
  state=$(_config_agent_read_state)

  if [[ -n "${tool}" ]]; then
    echo "${state}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
t = d.get('${tool}')
if t:
    print(f\"  ${tool}: model={t['model']}, provider={t['provider']}\")
else:
    print(f'  ${tool}: not configured')
" 2>/dev/null
    return
  fi

  _config_agent_log info "Active configurations:"
  echo "${state}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
if not d:
    print('  (none)')
for tool, cfg in sorted(d.items()):
    print(f\"  {tool}: model={cfg.get('model','?')}, provider={cfg.get('provider','?')}\")
" 2>/dev/null
}

# Start a tool with a permission mode
# Usage: config_agent_start <tool> [dev|yolo]
config_agent_start() {
  local tool="${1:-}"
  local mode="${2:-dev}"

  if [[ -z "${tool}" ]]; then
    _config_agent_log error "Usage: config_agent_start <tool> [dev|yolo]"
    return 1
  fi

  if [[ "${mode}" != "dev" && "${mode}" != "yolo" ]]; then
    _config_agent_log error "Invalid mode: ${mode} (use 'dev' or 'yolo')"
    return 1
  fi

  local cli="${CONFIG_AGENT_CLI[${tool}]:-}"
  if [[ -z "${cli}" ]]; then
    _config_agent_log error "Unknown tool: ${tool}"
    return 1
  fi

  if ! command -v "${cli}" &>/dev/null; then
    _config_agent_log error "${tool} CLI not installed. Run: config_agent_install ${tool}"
    return 1
  fi

  # Check if configured
  local state
  state=$(_config_agent_read_state)
  local configured
  configured=$(echo "${state}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('yes' if '${tool}' in d else 'no')
" 2>/dev/null || echo "no")

  if [[ "${configured}" == "no" ]]; then
    _config_agent_log warn "${tool} is not configured. Run: config_agent_configure ${tool} <model> <provider>"
  fi

  _config_agent_log info "Starting ${tool} in ${mode} mode..."

  case "${tool}|${mode}" in
    claude|dev)    claude --permission-mode acceptEdits "$@" ;;
    claude|yolo)   claude --dangerously-skip-permissions "$@" || claude --permission-mode bypassPermissions "$@" ;;
    codex|dev)     codex --approval-mode suggest "$@" ;;
    codex|yolo)    codex --approval-mode full-auto "$@" ;;
    qwen|dev)      qwen --permission-mode acceptEdits "$@" ;;
    qwen|yolo)     qwen --dangerously-skip-permissions "$@" || qwen --permission-mode bypassPermissions "$@" ;;
    qoder|dev)    qoder --permission-mode acceptEdits "$@" ;;
    qoder|yolo)    qoder --dangerously-skip-permissions "$@" || qoder --permission-mode bypassPermissions "$@" ;;
    iflow|dev)     iflow --permission-mode acceptEdits "$@" ;;
    iflow|yolo)    iflow --dangerously-skip-permissions "$@" || iflow --permission-mode bypassPermissions "$@" ;;
    opencode|dev)  opencode --auto-approve "$@" ;;
    opencode|yolo) opencode --yolo "$@" || opencode --auto-approve "$@" ;;
    *)
      _config_agent_log error "Unknown tool/mode combination: ${tool}/${mode}"
      return 1
      ;;
  esac
}

# ============================================================
# Tool-specific config writers
# ============================================================

_config_agent_write_claude() {
  local model="$1" url="$2" key="$3"
  local path="${HOME}/.claude/settings.json"
  _ca_ensure_dir "${path}"
  CA_URL="${url}" CA_KEY="${key}" CA_MODEL="${model}" python3 - "${path}" <<'PY'
import json, os, sys
path = sys.argv[1]
settings = {}
if os.path.exists(path) and os.path.getsize(path) > 0:
    with open(path) as fh:
        settings = json.load(fh)
env = settings.setdefault("env", {})
env.pop("ANTHROPIC_API_KEY", None)
env["ANTHROPIC_BASE_URL"] = os.environ["CA_URL"]
env["ANTHROPIC_AUTH_TOKEN"] = os.environ["CA_KEY"]
env["ANTHROPIC_MODEL"] = os.environ["CA_MODEL"]
env["ANTHROPIC_SMALL_FAST_MODEL"] = os.environ["CA_MODEL"]
with open(path, "w") as fh:
    json.dump(settings, fh, indent=2)
PY
  local rc=$?
  if [[ ${rc} -ne 0 ]]; then return 1; fi
  chmod 600 "${path}" 2>/dev/null || true
  return 0
}

_config_agent_write_codex() {
  local model="$1" provider="$2" url="$3" key="$4"
  local cfg="${HOME}/.codex/config.toml" auth="${HOME}/.codex/auth.json"
  _ca_toml_write_block "${cfg}" "${model}" "${provider}" "${url}" || return 1
  _CA_MERGE_JSON="$(CA_KEY="${key}" python3 -c 'import json,os; print(json.dumps({"OPENAI_API_KEY": os.environ["CA_KEY"]}))')" _ca_json_merge "${auth}" || return 1
  chmod 600 "${auth}" 2>/dev/null || true
  export CODEX_API_KEY="${key}"
  return 0
}

_config_agent_write_qwen() {
  local model="$1" url="$2" key="$3"
  local path="${HOME}/.qwen/.env"
  _ca_ensure_dir "${path}"
  _ca_dotenv_upsert "${path}" OPENAI_API_KEY "${key}" || return 1
  _ca_dotenv_upsert "${path}" OPENAI_BASE_URL "${url}" || return 1
  _ca_dotenv_upsert "${path}" OPENAI_MODEL "${model}" || return 1
  chmod 600 "${path}" 2>/dev/null || true
  export OPENAI_API_KEY="${key}" OPENAI_BASE_URL="${url}" OPENAI_MODEL="${model}"
  return 0
}

_config_agent_write_qoder() {
  local model="$1" url="$2" key="$3"
  local path="${HOME}/.qoder/config.json"
  _CA_MERGE_JSON="$(CA_MODEL="${model}" CA_URL="${url}" CA_KEY="${key}" python3 -c 'import json, os; print(json.dumps({"provider": "openai", "model": os.environ["CA_MODEL"], "apiKey": os.environ["CA_KEY"], "baseURL": os.environ["CA_URL"]}))')" _ca_json_merge "${path}" || return 1
  chmod 600 "${path}" 2>/dev/null || true
  return 0
}

_config_agent_write_iflow() {
  local model="$1" url="$2" key="$3"
  local path="${HOME}/.iflow/settings.json"
  _CA_MERGE_JSON="$(CA_MODEL="${model}" CA_URL="${url}" CA_KEY="${key}" python3 -c 'import json, os; print(json.dumps({"selectedAuthType": "openai-compatible", "apiKey": os.environ["CA_KEY"], "baseUrl": os.environ["CA_URL"], "modelName": os.environ["CA_MODEL"]}))')" _ca_json_merge "${path}" || return 1
  chmod 600 "${path}" 2>/dev/null || true
  return 0
}

_config_agent_write_opencode() {
  local model="$1" provider="$2" url="$3" key="$4"
  local path="${HOME}/.config/opencode/config.json"
  _CA_MERGE_JSON="$(CA_PROVIDER="${provider}" CA_MODEL="${model}" CA_URL="${url}" CA_KEY="${key}" python3 -c '
import json, os
p = os.environ["CA_PROVIDER"]; m = os.environ["CA_MODEL"]
print(json.dumps({
    "$schema": "https://opencode.ai/config.json",
    "provider": {
        p: {
            "npm": "@ai-sdk/openai-compatible",
            "name": p,
            "options": {"baseURL": os.environ["CA_URL"], "apiKey": os.environ["CA_KEY"]},
            "models": {m: {"name": m, "attachment": True}},
        }
    },
}))')" _ca_json_merge "${path}" || return 1
  chmod 600 "${path}" 2>/dev/null || true
  return 0
}

# ============================================================
# Unified Env-Var Flow — orchestration (validate / apply)
# ============================================================

# Return 0 iff "claude" is EXPLICITLY named among the arguments (not via --all).
# An explicit claude target makes AGENT_ANTHROPIC_BASE_URL mandatory.
_config_agent_env_is_claude_explicit() {
  local a
  for a in "$@"; do
    if [[ "${a}" == "claude" ]]; then return 0; fi
  done
  return 1
}

# Parse target arguments into a space-separated tool list on stdout.
# No args or "--all" => all six tools. Unknown tool => return 3 (no output).
_config_agent_env_parse_targets() {
  if [[ $# -eq 0 || "${1:-}" == "--all" ]]; then
    echo "${CONFIG_AGENT_ENV_TOOLS[*]}"
    return 0
  fi
  local a t ok out=()
  for a in "$@"; do
    ok=0
    for t in "${CONFIG_AGENT_ENV_TOOLS[@]}"; do
      if [[ "${a}" == "${t}" ]]; then ok=1; break; fi
    done
    if [[ ${ok} -eq 0 ]]; then return 3; fi
    out+=("${a}")
  done
  echo "${out[*]}"
  return 0
}

# Collect every offending unified variable. Prints one line per offender:
#   "missing <VAR>" | "malformed <VAR>". No output => all valid.
# Usage: _config_agent_env_collect_offenders <require_anthro:0|1>
_config_agent_env_collect_offenders() {
  local require_anthro="$1" v val
  for v in AGENT_API_KEY AGENT_MODEL; do
    val="$(_ca_trim "${!v:-}")"
    if [[ -z "${val}" ]]; then echo "missing ${v}"; fi
  done
  val="$(_ca_trim "${AGENT_BASE_URL:-}")"
  if [[ -z "${val}" ]]; then
    echo "missing AGENT_BASE_URL"
  elif ! _ca_url_has_scheme "${val}"; then
    echo "malformed AGENT_BASE_URL"
  fi
  if [[ "${require_anthro}" == "1" ]]; then
    val="$(_ca_trim "${AGENT_ANTHROPIC_BASE_URL:-}")"
    if [[ -z "${val}" ]]; then
      echo "missing AGENT_ANTHROPIC_BASE_URL"
    elif ! _ca_url_has_scheme "${val}"; then
      echo "malformed AGENT_ANTHROPIC_BASE_URL"
    fi
  fi
  return 0
}

# Print grouped Missing/Malformed offender report (secret-free).
_config_agent_env_report_offenders() {
  local offenders="$1" missing malformed
  missing="$(echo "${offenders}" | awk '$1=="missing"{printf "%s%s", sep, $2; sep=", "}')"
  malformed="$(echo "${offenders}" | awk '$1=="malformed"{printf "%s%s", sep, $2; sep=", "}')"
  if [[ -n "${missing}" ]]; then _config_agent_log error "Missing required variables: ${missing}"; fi
  if [[ -n "${malformed}" ]]; then _config_agent_log error "Malformed variables: ${malformed}"; fi
  _config_agent_log error "No configuration written."
  return 0
}

# Validate unified env vars for the target set. Writes nothing.
# Exit: 0 valid | 1 offenders present | 3 unknown tool.
config_agent_env_validate() {
  local targets
  if ! targets=$(_config_agent_env_parse_targets "$@"); then
    _config_agent_log error "Unknown/unsupported tool requested."
    _config_agent_log info "Supported tools: ${CONFIG_AGENT_ENV_TOOLS[*]}"
    return 3
  fi
  local require_anthro=0
  if _config_agent_env_is_claude_explicit "$@"; then require_anthro=1; fi
  local offenders
  offenders="$(_config_agent_env_collect_offenders "${require_anthro}")"
  if [[ -n "${offenders}" ]]; then
    _config_agent_env_report_offenders "${offenders}"
    return 1
  fi
  _config_agent_log ok "All required variables present and well-formed."
  return 0
}

# Apply unified env vars to each target tool's own config file.
# Exit: 0 all configured/validly skipped | 1 validation failed (no writes)
#     | 2 one or more tools failed | 3 unknown tool.
config_agent_env_apply() {
  local targets
  if ! targets=$(_config_agent_env_parse_targets "$@"); then
    _config_agent_log error "Unknown/unsupported tool requested."
    _config_agent_log info "Supported tools: ${CONFIG_AGENT_ENV_TOOLS[*]}"
    return 3
  fi
  local require_anthro=0
  if _config_agent_env_is_claude_explicit "$@"; then require_anthro=1; fi

  # Validation gate — fail fast, write nothing.
  local offenders
  offenders="$(_config_agent_env_collect_offenders "${require_anthro}")"
  if [[ -n "${offenders}" ]]; then
    _config_agent_env_report_offenders "${offenders}"
    return 1
  fi

  # Read values (secret held only in locals; never echoed).
  local key model url anthro
  key="$(_ca_trim "${AGENT_API_KEY}")"
  model="$(_ca_trim "${AGENT_MODEL}")"
  url="$(_ca_trim "${AGENT_BASE_URL}")"
  anthro="$(_ca_trim "${AGENT_ANTHROPIC_BASE_URL:-}")"

  local failed=0 tool
  for tool in ${targets}; do
    case "${tool}" in
      claude)
        if [[ -z "${anthro}" ]]; then
          _config_agent_log warn "$(printf '%-8s skipped     (AGENT_ANTHROPIC_BASE_URL not set)' claude)"
          continue
        fi
        if _config_agent_write_claude "${model}" "${anthro}" "${key}"; then
          _config_agent_log ok "$(printf '%-8s configured  (~/.claude/settings.json)' claude)"
        else
          _config_agent_log error "$(printf '%-8s failed      (write error)' claude)"; failed=1
        fi
        ;;
      codex)
        if _config_agent_write_codex "${model}" "agent" "${url}" "${key}"; then
          _config_agent_log ok "$(printf '%-8s configured  (~/.codex/config.toml, ~/.codex/auth.json)' codex)"
        else
          _config_agent_log error "$(printf '%-8s failed      (write error)' codex)"; failed=1
        fi
        ;;
      qwen)
        if _config_agent_write_qwen "${model}" "${url}" "${key}"; then
          _config_agent_log ok "$(printf '%-8s configured  (~/.qwen/.env)' qwen)"
        else
          _config_agent_log error "$(printf '%-8s failed      (write error)' qwen)"; failed=1
        fi
        ;;
      qoder)
        if _config_agent_write_qoder "${model}" "${url}" "${key}"; then
          _config_agent_log ok "$(printf '%-8s configured  (~/.qoder/config.json)' qoder)"
        else
          _config_agent_log error "$(printf '%-8s failed      (write error)' qoder)"; failed=1
        fi
        ;;
      iflow)
        if _config_agent_write_iflow "${model}" "${url}" "${key}"; then
          _config_agent_log ok "$(printf '%-8s configured  (~/.iflow/settings.json)' iflow)"
        else
          _config_agent_log error "$(printf '%-8s failed      (write error)' iflow)"; failed=1
        fi
        ;;
      opencode)
        if _config_agent_write_opencode "${model}" "agent" "${url}" "${key}"; then
          _config_agent_log ok "$(printf '%-8s configured  (~/.config/opencode/config.json)' opencode)"
        else
          _config_agent_log error "$(printf '%-8s failed      (write error)' opencode)"; failed=1
        fi
        ;;
    esac
  done

  if [[ ${failed} -eq 1 ]]; then return 2; fi
  return 0
}
