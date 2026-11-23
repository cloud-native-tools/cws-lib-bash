#!/bin/bash

# shellcheck disable=SC2119,SC2120  # public helper forwards caller args; ensure installs with defaults

# Spec Kit family — independent of the ai-harness family in 313_ai_harness.sh.
# `specify` is Spec Kit's own console entrypoint. specify_install delegates to
# spec-kit's own install.sh (pip/python by default; uv only behind install.sh's
# --uv opt-in), so no uv is required by this helper.

# Ensure the Spec Kit CLI is installed and that `specify` really is Spec Kit.
# A stale or shadowed binary (for example an ai-harness era shim) is detected by
# asking it to identify itself; never assume a bare `specify` is Spec Kit.
function specify_ensure() {
  if have specify && specify --version 2>/dev/null | grep -qi "specify-cli"; then
    return "${RETURN_SUCCESS:-0}"
  fi
  if have specify; then
    log warn "'specify' on PATH is not the Spec Kit CLI; installing the Spec Kit CLI"
  else
    log warn "Specify command not found, attempting to install..."
  fi
  if ! specify_install; then
    log error "Failed to install Spec Kit"
    return "${RETURN_FAILURE:-1}"
  fi
  hash -r
  if have specify && specify --version 2>/dev/null | grep -qi "specify-cli"; then
    return "${RETURN_SUCCESS:-0}"
  fi
  log error "'specify' on PATH is still not the Spec Kit CLI; remove the conflicting binary or put the Spec Kit install first on PATH"
  return "${RETURN_FAILURE:-1}"
}

# Install or upgrade Spec Kit by delegating to spec-kit's own install.sh
#
# DUAL DUTY: specify has no self-update subcommand, so this function is both
# the cold-start INSTALL path and the UPGRADE path — install.sh performs a
# clean reinstall, and its python ladder prefers the existing installation's
# python (upgrade-in-place) when no --python / cwd .venv pins the destination.
#
# Ownership contract: the install.sh at the spec-kit repo root is the SINGLE
# owner of cold-start install logic — python resolution ladder, source
# ordering, pip index pairing, uv opt-in, and post-install verification all
# live there. This wrapper only LOCATES or FETCHES that script and delegates;
# it must not re-implement any of that logic. The source list below is a
# fetch-only copy used to obtain a checkout (and thus install.sh) — the
# authoritative install order lives in install.sh.
#
# Usage: specify_install [install.sh args...]
#   e.g. specify_install --python /path/to/python
#        specify_install --intranet-only
#   forwarded verbatim to install.sh (see `bash install.sh --help` there)
#
# Locate order:
#   1. ${SPECIFY_INSTALL_SH} — explicit path to an install.sh (any local
#      spec-kit checkout); use this to avoid the network entirely
#   2. shallow clone of the first reachable source below into a temp dir
#
# Exit codes: install.sh exit codes propagate (0 ok | 2 missing prerequisite
# | 3 no viable source x index | 5 verification failed); failure to even
# obtain the script returns RETURN_FAILURE.
function specify_install() {
  log info "Installing Spec Kit (delegating to spec-kit install.sh)..."

  local script=""

  # 1. Explicit override: any local spec-kit checkout's install.sh
  if [[ -n "${SPECIFY_INSTALL_SH:-}" ]]; then
    if [[ -f "${SPECIFY_INSTALL_SH}" ]]; then
      script="${SPECIFY_INSTALL_SH}"
      log info "Using installer from SPECIFY_INSTALL_SH: ${script}"
    else
      log warn "SPECIFY_INSTALL_SH set but not found: ${SPECIFY_INSTALL_SH}; falling back to clone"
    fi
  fi

  # 2. Fetch-only fallback: shallow-clone the first reachable repo and use
  #    its install.sh. The intranet-first order mirrors install.sh's
  #    authoritative order, but this list exists ONLY to obtain the script.
  local tmp_dir=""
  if [[ -z "${script}" ]]; then
    if ! have git; then
      log error "git command not found. Install git first, or set SPECIFY_INSTALL_SH to a local install.sh."
      return "${RETURN_FAILURE:-1}"
    fi

    # Entry format: "<repo url>|<branch>|<hostname>"
    local sources=(
      "https://gitlab.alibaba-inc.com/cloud-native-ai/spec-kit.git|master|gitlab.alibaba-inc.com"
      "https://gitee.com/cloud-native-ai/spec-kit.git|master|gitee.com"
      "https://github.com/cloud-native-ai/spec-kit.git|master|github.com"
    )

    tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/specify-install.XXXXXX")" || {
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
      if git clone --depth 1 --branch "${branch}" "${url}" "${tmp_dir}/spec-kit" >/dev/null 2>&1; then
        cloned=true
        log notice "Fetched spec-kit checkout from ${hostname}"
        break
      fi
      log warn "Clone from ${hostname} failed, trying next source..."
    done

    if [[ "${cloned}" != true ]]; then
      rm -rf "${tmp_dir}"
      log error "Failed to fetch install.sh from all available sources (set SPECIFY_INSTALL_SH to use a local copy)"
      return "${RETURN_FAILURE:-1}"
    fi

    script="${tmp_dir}/spec-kit/install.sh"
    if [[ ! -f "${script}" ]]; then
      rm -rf "${tmp_dir}"
      log error "Fetched checkout has no install.sh at repo root (too old spec-kit?)"
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
    log notice "Spec Kit installed successfully (via ${script})"
    return "${RETURN_SUCCESS:-0}"
  fi
  log error "Spec Kit installer failed with exit code ${rc}"
  return "${rc}"
}

# Uninstall Spec Kit
function specify_uninstall() {
  log info "Uninstalling Spec Kit..."
  if ! have pip3; then
    log error "pip3 command not found. Please install pip3 first."
    return "${RETURN_FAILURE:-1}"
  fi

  if pip3 uninstall -y specify-cli; then
    log notice "Spec Kit uninstalled successfully"
    return "${RETURN_SUCCESS:-0}"
  else
    log warn "Failed to uninstall Spec Kit (it might not be installed)"
    return "${RETURN_SUCCESS:-0}"
  fi
}

# Check Spec Kit dependencies and ensure installation
function specify_check() {
  # Ensure Spec Kit is installed
  if ! specify_ensure; then
    return "${RETURN_FAILURE:-1}"
  fi

  # Call specify check to verify all required tools are available
  log info "Checking Spec Kit dependencies..."
  if specify check; then
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

  # Ensure Spec Kit is available
  if ! specify_ensure; then
    return "${RETURN_FAILURE:-1}"
  fi

  log info "Initializing Spec Kit project with AI tool: ${ai_tool}, project name: ${project_name}"

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
        if ! specify init "${project_name}" --ai "${tool}" --script sh --no-git --force --skip-tls --ignore-agent-tools; then
          log error "Failed to initialize Spec Kit project for AI tool: ${tool}"
          return "${RETURN_FAILURE:-1}"
        fi
      elif ! specify init "${project_name}" --ai "${tool}" --script sh --no-git --force --skip-tls; then
        log error "Failed to initialize Spec Kit project for AI tool: ${tool}"
        return "${RETURN_FAILURE:-1}"
      fi
    done

    log notice "Spec Kit project initialized successfully for all AI tools"
    return "${RETURN_SUCCESS:-0}"
  fi

  if [ "${ignore_agent_tools}" = "true" ]; then
    if specify init "${project_name}" --ai "${ai_tool}" --script sh --no-git --force --skip-tls --ignore-agent-tools; then
      log notice "Spec Kit project initialized successfully"
      return "${RETURN_SUCCESS:-0}"
    fi
  elif specify init "${project_name}" --ai "${ai_tool}" --script sh --no-git --force --skip-tls; then
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

function specify_deinit() {
  local ai_tool=${1:-all}

  case "${ai_tool}" in
  all)
    rm -rfv .github/prompts/speckit.*.prompt.md
    rm -rfv .qoder/commands/speckit.*.md
    rm -rfv .opencode/command/speckit.*.md
    ;;
  copilot)
    rm -rfv .github/prompts/speckit.*.prompt.md
    ;;
  qoder)
    rm -rfv .qoder/commands/speckit.*.md
    ;;
  opencode)
    rm -rfv .opencode/command/speckit.*.md
    ;;
  *)
    log error "Usage: specify_deinit [copilot|qoder|opencode|all]"
    return "${RETURN_FAILURE:-1}"
    ;;
  esac

  rm -rfv .specify/memory/features .specify/memory/features.md
  rm -rfv .specify/scripts .specify/templates
}
