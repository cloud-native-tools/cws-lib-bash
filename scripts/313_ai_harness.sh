#!/bin/bash

# shellcheck disable=SC2119,SC2120  # public helper forwards caller args; ensure installs with defaults

# ai-harness family — independent of the Spec Kit family in 313_specify.sh.
# This file mirrors 313_specify.sh: same function set, order and logic; only
# the prefix and the CLI/tool names differ. `ai-harness` is ai-harness's own
# console entrypoint; `specify` belongs to the independent Spec Kit project.

# Shared agent-CLI user:group helper (not part of either CLI family).
# The host operator account and the container run account are different
# identities, so the target follows the runtime form rather than the host user:
#   - container (image run account): CWS_DEVELOP_USER, default develop
#   - docker host (physical/VM):     agent
# is_container comes from profile.d/02_probe.sh, which is loaded before scripts/.
function specify_user() {
  local user="agent"
  local group="agent"
  if is_container; then
    user="${CWS_DEVELOP_USER:-develop}"
    group="${CWS_DEVELOP_GROUP:-${user}}"
  fi
  echo "${user}:${group}"
}

# Ensure the ai-harness CLI is installed and that `ai-harness` really is
# ai-harness. A stale or shadowed binary is detected by asking it to identify
# itself; never assume a bare `ai-harness` is the right CLI.
function ah_ensure() {
  if have ai-harness && ai-harness --version 2>/dev/null | grep -qi "ai-harness-cli"; then
    return "${RETURN_SUCCESS:-0}"
  fi
  if have ai-harness; then
    log warn "'ai-harness' on PATH is not the ai-harness CLI; installing ai-harness"
  else
    log warn "ai-harness command not found, attempting to install..."
  fi
  if ! ah_install; then
    log error "Failed to install ai-harness"
    return "${RETURN_FAILURE:-1}"
  fi
  hash -r
  if have ai-harness && ai-harness --version 2>/dev/null | grep -qi "ai-harness-cli"; then
    return "${RETURN_SUCCESS:-0}"
  fi
  log error "'ai-harness' on PATH is still not the ai-harness CLI; remove the conflicting binary or put the ai-harness install first on PATH"
  return "${RETURN_FAILURE:-1}"
}

# Install or upgrade ai-harness by delegating to ai-harness's own install.sh
#
# DUAL DUTY: ai-harness has no self-update subcommand, so this function is both
# the cold-start INSTALL path and the UPGRADE path — install.sh performs a
# clean reinstall, and its python ladder prefers the existing installation's
# python (upgrade-in-place) when no --python / cwd .venv pins the destination.
#
# Ownership contract: the install.sh at the ai-harness repo root is the SINGLE
# owner of cold-start install logic — python resolution ladder, source
# ordering, pip index pairing, uv opt-in, and post-install verification all
# live there. This wrapper only LOCATES or FETCHES that script and delegates;
# it must not re-implement any of that logic. The source list below is a
# fetch-only copy used to obtain a checkout (and thus install.sh) — the
# authoritative install order lives in install.sh.
#
# Usage: ah_install [install.sh args...]
#   e.g. ah_install --python /path/to/python
#        ah_install --intranet-only
#   forwarded verbatim to install.sh (see `bash install.sh --help` there)
#
# Locate order:
#   1. ${AI_HARNESS_INSTALL_SH} — explicit path to an install.sh (any local
#      ai-harness checkout); use this to avoid the network entirely
#   2. shallow clone of the first reachable source below into a temp dir
#
# Exit codes: install.sh exit codes propagate (0 ok | 2 missing prerequisite
# | 3 no viable source x index | 5 verification failed); failure to even
# obtain the script returns RETURN_FAILURE.
function ah_install() {
  log info "Installing ai-harness (delegating to ai-harness install.sh)..."

  local script=""

  # 1. Explicit override: any local ai-harness checkout's install.sh
  if [[ -n "${AI_HARNESS_INSTALL_SH:-}" ]]; then
    if [[ -f "${AI_HARNESS_INSTALL_SH}" ]]; then
      script="${AI_HARNESS_INSTALL_SH}"
      log info "Using installer from AI_HARNESS_INSTALL_SH: ${script}"
    else
      log warn "AI_HARNESS_INSTALL_SH set but not found: ${AI_HARNESS_INSTALL_SH}; falling back to clone"
    fi
  fi

  # 2. Fetch-only fallback: shallow-clone the first reachable repo and use
  #    its install.sh. The intranet-first order mirrors install.sh's
  #    authoritative order, but this list exists ONLY to obtain the script.
  local tmp_dir=""
  if [[ -z "${script}" ]]; then
    if ! have git; then
      log error "git command not found. Install git first, or set AI_HARNESS_INSTALL_SH to a local install.sh."
      return "${RETURN_FAILURE:-1}"
    fi

    # Entry format: "<repo url>|<branch>|<hostname>"
    local sources=(
      "https://gitlab.alibaba-inc.com/cloud-native-ai/ai-harness.git|master|gitlab.alibaba-inc.com"
      "https://gitee.com/cloud-native-ai/ai-harness.git|master|gitee.com"
      "https://github.com/cloud-native-ai/ai-harness.git|master|github.com"
    )

    tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/ai-harness-install.XXXXXX")" || {
      log error "Failed to create temp directory"
      return "${RETURN_FAILURE:-1}"
    }

    local entry url branch hostname cloned=false
    for entry in "${sources[@]}"; do
      url="${entry%%|*}"
      branch="${entry#*|}"
      branch="${branch%%|*}"
      hostname="${entry##*|}"

      log info "Trying to fetch install.sh from: ${hostname}"
      if ! net_ping "${hostname}"; then
        log warn "Network connectivity to ${hostname} failed, skipping this source"
        continue
      fi
      if git clone --depth 1 --branch "${branch}" "${url}" "${tmp_dir}/ai-harness" >/dev/null 2>&1; then
        cloned=true
        log notice "Fetched ai-harness checkout from ${hostname}"
        break
      fi
      log warn "Clone from ${hostname} failed, trying next source..."
    done

    if [[ "${cloned}" != true ]]; then
      rm -rf "${tmp_dir}"
      log error "Failed to fetch install.sh from all available sources (set AI_HARNESS_INSTALL_SH to use a local copy)"
      return "${RETURN_FAILURE:-1}"
    fi

    script="${tmp_dir}/ai-harness/install.sh"
    if [[ ! -f "${script}" ]]; then
      rm -rf "${tmp_dir}"
      log error "Fetched checkout has no install.sh at repo root (too old ai-harness?)"
      return "${RETURN_FAILURE:-1}"
    fi
  fi

  # Delegate: all install logic (python ladder, index pairing, source
  # fallback, verification) runs inside install.sh, in the CURRENT working
  # directory so its $PWD/.venv detection applies.
  log info "Delegating to installer: bash ${script} $*"
  local rc=0
  bash "${script}" "$@" || rc=$?

  if [[ -n "${tmp_dir}" ]]; then
    rm -rf "${tmp_dir}"
  fi

  if [[ ${rc} -eq 0 ]]; then
    log notice "ai-harness installed successfully (via ${script})"
    return "${RETURN_SUCCESS:-0}"
  fi
  log error "ai-harness installer failed with exit code ${rc}"
  return "${rc}"
}

# Uninstall ai-harness
function ah_uninstall() {
  log info "Uninstalling ai-harness..."
  if ! have pip3; then
    log error "pip3 command not found. Please install pip3 first."
    return "${RETURN_FAILURE:-1}"
  fi

  if pip3 uninstall -y ai-harness-cli ai-engine-cli; then
    log notice "ai-harness uninstalled successfully"
    return "${RETURN_SUCCESS:-0}"
  else
    log warn "Failed to uninstall ai-harness (it might not be installed)"
    return "${RETURN_SUCCESS:-0}"
  fi
}

# Check ai-harness dependencies and ensure installation
function ah_check() {
  # Ensure ai-harness is installed
  if ! ah_ensure; then
    return "${RETURN_FAILURE:-1}"
  fi

  # Call ai-harness check to verify all required tools are available
  log info "Checking ai-harness dependencies..."
  if ai-harness check; then
    log notice "ai-harness dependencies check passed"
    return "${RETURN_SUCCESS:-0}"
  else
    log error "ai-harness dependencies check failed"
    return "${RETURN_FAILURE:-1}"
  fi
}

# Initialize a new ai-harness project
# Usage: ah_init <ai_tool> [project_name]
# Available AI tools: all, claude, copilot, qoder, opencode
function ah_init() {
  local ai_tool=${1}
  local project_name=${2:-.}
  local ignore_agent_tools=${3:-false}

  # Validate AI tool parameter
  if [ -z "${ai_tool}" ]; then
    log error "Usage: ah_init <ai_tool> [project_name]"
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

  # Ensure ai-harness is available
  if ! ah_ensure; then
    return "${RETURN_FAILURE:-1}"
  fi

  log info "Initializing ai-harness project with AI tool: ${ai_tool}, project name: ${project_name}"

  if [ "${ai_tool}" = "all" ]; then
    local tools=(claude copilot opencode qoder)
    local tool=""
    local tool_ignore_agent_tools=false

    for tool in "${tools[@]}"; do
      tool_ignore_agent_tools=false
      case "${tool}" in
      claude | opencode | qoder)
        tool_ignore_agent_tools=true
        ;;
      esac

      if [ "${tool_ignore_agent_tools}" = "true" ]; then
        if ! ai-harness init "${project_name}" --ai "${tool}" --script sh --no-git --force --skip-tls --ignore-agent-tools; then
          log error "Failed to initialize ai-harness project for AI tool: ${tool}"
          return "${RETURN_FAILURE:-1}"
        fi
      elif ! ai-harness init "${project_name}" --ai "${tool}" --script sh --no-git --force --skip-tls; then
        log error "Failed to initialize ai-harness project for AI tool: ${tool}"
        return "${RETURN_FAILURE:-1}"
      fi
    done

    log notice "ai-harness project initialized successfully for all AI tools"
    return "${RETURN_SUCCESS:-0}"
  fi

  if [ "${ignore_agent_tools}" = "true" ]; then
    if ai-harness init "${project_name}" --ai "${ai_tool}" --script sh --no-git --force --skip-tls --ignore-agent-tools; then
      log notice "ai-harness project initialized successfully"
      return "${RETURN_SUCCESS:-0}"
    fi
  elif ai-harness init "${project_name}" --ai "${ai_tool}" --script sh --no-git --force --skip-tls; then
    log notice "ai-harness project initialized successfully"
    return "${RETURN_SUCCESS:-0}"
  fi

  log error "Failed to initialize ai-harness project"
  return "${RETURN_FAILURE:-1}"
}

# Initialize an ai-harness project with Copilot AI
function ah_init_copilot() {
  local project_name=${1:-.}
  ah_init copilot "${project_name}"
}

# Initialize an ai-harness project with Qoder
function ah_init_qoder() {
  local project_name=${1:-.}
  ah_init qoder "${project_name}" true
}

# Initialize an ai-harness project with OpenCode
function ah_init_opencode() {
  local project_name=${1:-.}
  ah_init opencode "${project_name}" true
}

# Initialize an ai-harness project with claude code
function ah_init_claude() {
  local project_name=${1:-.}
  ah_init claude "${project_name}" true
}

# Initialize an ai-harness project with all AI agent tools
function ah_init_all() {
  local project_name=${1:-.}
  ah_init all "${project_name}" true
}

function ah_deinit() {
  local ai_tool=${1:-all}

  case "${ai_tool}" in
  all)
    rm -rfv .github/prompts/ah.*.prompt.md
    rm -rfv .qoder/commands/ah.*.md
    rm -rfv .opencode/command/ah.*.md
    ;;
  copilot)
    rm -rfv .github/prompts/ah.*.prompt.md
    ;;
  qoder)
    rm -rfv .qoder/commands/ah.*.md
    ;;
  opencode)
    rm -rfv .opencode/command/ah.*.md
    ;;
  *)
    log error "Usage: ah_deinit [copilot|qoder|opencode|all]"
    return "${RETURN_FAILURE:-1}"
    ;;
  esac

  rm -rfv .ah/memory/features .ah/memory/features.md
  rm -rfv .ah/scripts .ah/templates
}

# Backward-compatible long names (same behavior as the short family above).
function ai_harness_ensure() {
  ah_ensure "$@"
}

function ai_harness_install() {
  ah_install "$@"
}
