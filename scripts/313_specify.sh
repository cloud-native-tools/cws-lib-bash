#!/bin/bash

# Spec Kit family — independent of the ai-harness family in 313_ai_harness.sh.
# `specify` is Spec Kit's own console entrypoint and `ai-harness` is the
# harness; the two projects are independent. This family resolves Spec Kit by
# identity rather than by bare command name, so a stale or shadowed `specify`
# belonging to another tool can never be mistaken for it. Resolution order:
#   1. SPECIFY_CLI_BIN — explicit path to a Spec Kit CLI executable
#   2. ${SPECIFY_CLI_HOME:-$HOME/.local/share/spec-kit}/venv/bin/specify
#      (created by specify_install)
#   3. a `specify` on PATH whose `--version` identifies `specify-cli`
#   4. uvx --from git+<source> specify (on-demand; source probed from the org
#      mirrors, override with SPECIFY_CLI_SOURCE)
#
# ai-harness equivalents: ai_harness_* / ah_* in 313_ai_harness.sh.

function specify_cli_home() {
  printf '%s\n' "${SPECIFY_CLI_HOME:-${HOME}/.local/share/spec-kit}"
}

# A `specify` on PATH is accepted only when it identifies itself as Spec Kit.
function specify_cli_path_bin() {
  local candidate=""
  candidate="$(command -v specify 2>/dev/null || true)"
  if [[ -z "${candidate}" || ! -x "${candidate}" ]]; then
    return "${RETURN_FAILURE:-1}"
  fi
  if "${candidate}" --version 2>/dev/null | grep -qi "specify-cli"; then
    printf '%s\n' "${candidate}"
    return "${RETURN_SUCCESS:-0}"
  fi
  return "${RETURN_FAILURE:-1}"
}

function specify_cli_bin() {
  if [[ -n "${SPECIFY_CLI_BIN:-}" ]]; then
    if [[ -x "${SPECIFY_CLI_BIN}" ]]; then
      printf '%s\n' "${SPECIFY_CLI_BIN}"
      return "${RETURN_SUCCESS:-0}"
    fi
    return "${RETURN_FAILURE:-1}"
  fi
  local home=""
  home="$(specify_cli_home)"
  if [[ -x "${home}/venv/bin/specify" ]]; then
    printf '%s\n' "${home}/venv/bin/specify"
    return "${RETURN_SUCCESS:-0}"
  fi
  local path_bin=""
  if path_bin="$(specify_cli_path_bin)"; then
    printf '%s\n' "${path_bin}"
    return "${RETURN_SUCCESS:-0}"
  fi
  return "${RETURN_FAILURE:-1}"
}

# Probe the org mirrors in the same order as the ai-harness installer.
function specify_cli_source() {
  if [[ -n "${SPECIFY_CLI_SOURCE:-}" ]]; then
    printf '%s\n' "${SPECIFY_CLI_SOURCE}"
    return "${RETURN_SUCCESS:-0}"
  fi
  if ! have net_ping; then
    log error "net_ping is unavailable; set SPECIFY_CLI_SOURCE to a git URL"
    return "${RETURN_FAILURE:-1}"
  fi
  local sources=(
    "https://gitlab.alibaba-inc.com/cloud-native-ai/spec-kit.git|gitlab.alibaba-inc.com"
    "https://gitee.com/cloud-native-ai/spec-kit.git|gitee.com"
    "https://github.com/cloud-native-ai/spec-kit.git|github.com"
  )
  local entry url host
  for entry in "${sources[@]}"; do
    url="${entry%%|*}"
    host="${entry##*|}"
    if net_ping "${host}"; then
      printf '%s@master\n' "${url}"
      return "${RETURN_SUCCESS:-0}"
    fi
    log warn "Network connectivity to ${host} failed, skipping this Spec Kit source"
  done
  log error "No reachable Spec Kit source; set SPECIFY_CLI_SOURCE to a git URL"
  return "${RETURN_FAILURE:-1}"
}

# Run the Spec Kit CLI without going through the ai-harness `specify` alias.
function specify_cli_run() {
  local bin=""
  if bin="$(specify_cli_bin)"; then
    "${bin}" "$@"
    return $?
  fi
  if ! have uvx; then
    log error "Spec Kit CLI not found: set SPECIFY_CLI_BIN, run specify_install, or install uv (uvx)"
    return "${RETURN_FAILURE:-1}"
  fi
  local source=""
  source="$(specify_cli_source)" || return "${RETURN_FAILURE:-1}"
  log info "Running Spec Kit via uvx from ${source}"
  uvx --from "git+${source}" specify "$@"
}

# Ensure a Spec Kit CLI path exists (explicit binary, dedicated venv, or uvx).
function specify_ensure() {
  if specify_cli_bin >/dev/null 2>&1; then
    return "${RETURN_SUCCESS:-0}"
  fi
  if have uvx; then
    return "${RETURN_SUCCESS:-0}"
  fi
  log error "Spec Kit CLI unavailable: set SPECIFY_CLI_BIN, run specify_install, or install uv (uvx)"
  return "${RETURN_FAILURE:-1}"
}

# Install the Spec Kit CLI into a dedicated venv (no global `specify` shim, so
# the ai-harness legacy alias is untouched).
function specify_install() {
  if ! have uv; then
    log error "uv is required to install Spec Kit: https://docs.astral.sh/uv/"
    return "${RETURN_FAILURE:-1}"
  fi
  local source=""
  source="$(specify_cli_source)" || return "${RETURN_FAILURE:-1}"
  local home=""
  home="$(specify_cli_home)"
  local venv="${home}/venv"
  if ! mkdir -p "${home}"; then
    log error "Cannot create ${home}"
    return "${RETURN_FAILURE:-1}"
  fi
  if [[ ! -x "${venv}/bin/python" ]]; then
    log info "Creating Spec Kit virtual environment: ${venv}"
    if ! uv venv "${venv}" --python "${SPECIFY_CLI_PYTHON:-python3}"; then
      log error "Failed to create ${venv}"
      return "${RETURN_FAILURE:-1}"
    fi
  fi
  log info "Installing Spec Kit CLI from ${source}"
  if ! uv pip install --python "${venv}/bin/python" "git+${source}"; then
    log error "Failed to install Spec Kit CLI"
    return "${RETURN_FAILURE:-1}"
  fi
  log notice "Spec Kit CLI installed: ${venv}/bin/specify"
}

function specify_uninstall() {
  local home=""
  home="$(specify_cli_home)"
  if [[ -d "${home}" ]]; then
    rm -rfv "${home}"
    log notice "Spec Kit CLI environment removed: ${home}"
  else
    log warn "Spec Kit CLI environment not found at ${home}"
  fi
  if [[ -n "${SPECIFY_CLI_BIN:-}" ]]; then
    log info "SPECIFY_CLI_BIN points outside ${home}; it was not removed"
  fi
  return "${RETURN_SUCCESS:-0}"
}

# Check Spec Kit dependencies via the Spec Kit CLI.
function specify_check() {
  if ! specify_ensure; then
    return "${RETURN_FAILURE:-1}"
  fi
  log info "Checking Spec Kit dependencies..."
  if specify_cli_run check; then
    log notice "Spec Kit dependencies check passed"
    return "${RETURN_SUCCESS:-0}"
  else
    log error "Spec Kit dependencies check failed"
    return "${RETURN_FAILURE:-1}"
  fi
}

# Initialize a new Spec Kit project
# Usage: specify_init <ai_tool> [project_name]
# Available AI tools: all, claude, copilot, qoder, opencode
function specify_init() {
  local ai_tool=${1}
  local project_name=${2:-.}
  local ignore_agent_tools=${3:-false}

  # Validate AI tool parameter
  if [ -z "${ai_tool}" ]; then
    log error "Usage: specify_init <ai_tool> [project_name]"
    log error "Available AI tools: all, claude, copilot, qoder, opencode"
    return "${RETURN_FAILURE:-1}"
  fi

  case "${ai_tool}" in
  all | claude | copilot | opencode | qoder)
    ;;
  *)
    log error "Unsupported AI tool: ${ai_tool}"
    log error "Available AI tools: all, claude, copilot, qoder, opencode"
    return "${RETURN_FAILURE:-1}"
    ;;
  esac

  if ! specify_ensure; then
    return "${RETURN_FAILURE:-1}"
  fi

  log info "Initializing Spec Kit project with AI tool: ${ai_tool}, project name: ${project_name}"

  local base_args=(init "${project_name}" --script sh --no-git --force --skip-tls)
  if [ "${ai_tool}" = "all" ]; then
    local tools=(claude copilot opencode qoder)
    local tool=""
    local tool_args=()

    for tool in "${tools[@]}"; do
      tool_args=("${base_args[@]}" --ai "${tool}")
      case "${tool}" in
      claude | opencode | qoder)
        tool_args+=(--ignore-agent-tools)
        ;;
      esac

      if ! specify_cli_run "${tool_args[@]}"; then
        log error "Failed to initialize Spec Kit project for AI tool: ${tool}"
        return "${RETURN_FAILURE:-1}"
      fi
    done

    log notice "Spec Kit project initialized successfully for all AI tools"
    return "${RETURN_SUCCESS:-0}"
  fi

  local args=("${base_args[@]}" --ai "${ai_tool}")
  if [ "${ignore_agent_tools}" = "true" ]; then
    args+=(--ignore-agent-tools)
  fi

  if specify_cli_run "${args[@]}"; then
    log notice "Spec Kit project initialized successfully"
    return "${RETURN_SUCCESS:-0}"
  fi

  log error "Failed to initialize Spec Kit project"
  return "${RETURN_FAILURE:-1}"
}

# Initialize a Spec Kit project with Copilot AI
function specify_init_copilot() {
  local project_name=${1:-.}
  specify_init copilot "${project_name}"
}

# Initialize a Spec Kit project with Qoder
function specify_init_qoder() {
  local project_name=${1:-.}
  specify_init qoder "${project_name}" true
}

# Initialize a Spec Kit project with OpenCode
function specify_init_opencode() {
  local project_name=${1:-.}
  specify_init opencode "${project_name}" true
}

# Initialize a Spec Kit project with claude code
function specify_init_claude() {
  local project_name=${1:-.}
  specify_init claude "${project_name}" true
}

# Initialize a Spec Kit project with all AI agent tools
function specify_init_all() {
  local project_name=${1:-.}
  specify_init all "${project_name}" true
}

# Remove the per-tool /speckit.* command copies. `.specify/` is project-owned
# (scripts/templates/memory/specs) and is deliberately kept.
function specify_deinit() {
  local ai_tool=${1:-all}

  case "${ai_tool}" in
  all)
    rm -rfv .github/prompts/speckit.*.prompt.md
    rm -rfv .claude/commands/speckit.*.md
    rm -rfv .codex/commands/speckit.*.md
    rm -rfv .hermes/commands/speckit.*.md
    rm -rfv .opencode/command/speckit.*.md
    rm -rfv .qoder/commands/speckit.*.md
    ;;
  copilot)
    rm -rfv .github/prompts/speckit.*.prompt.md
    ;;
  claude)
    rm -rfv .claude/commands/speckit.*.md
    ;;
  codex)
    rm -rfv .codex/commands/speckit.*.md
    ;;
  hermes)
    rm -rfv .hermes/commands/speckit.*.md
    ;;
  opencode)
    rm -rfv .opencode/command/speckit.*.md
    ;;
  qoder)
    rm -rfv .qoder/commands/speckit.*.md
    ;;
  *)
    log error "Usage: specify_deinit [claude|codex|copilot|hermes|opencode|qoder|all]"
    return "${RETURN_FAILURE:-1}"
    ;;
  esac

  log notice "Spec Kit agent command copies removed; .specify/ is project-owned and kept"
}
