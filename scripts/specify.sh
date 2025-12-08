#!/bin/bash

# Ensure Specify kit is installed and available
function specify_ensure() {
  if ! have specify; then
    log warn "Specify command not found, attempting to install..."
    if ! specify_install; then
      log error "Failed to install Specify kit"
      return "${RETURN_FAILURE:-1}"
    fi
  fi
  return "${RETURN_SUCCESS:-0}"
}

# Install Specify kit from GitHub repository
function specify_install() {
  log info "Installing Specify kit from multiple sources..."
  if ! have pip3; then
    log error "pip3 command not found. Please install pip3 first."
    return "${RETURN_FAILURE:-1}"
  fi

  # Uninstall any existing Specify kit first
  log info "Uninstalling existing Specify kit (if any)..."
  specify_uninstall

  # Define installation sources in order of preference
  local sources=(
    "git+https://gitlab.alibaba-inc.com/cloud-native-ai/spec-kit.git@master"
    "git+https://gitee.com/cloud-native-ai/spec-kit.git@master"
    "git+https://github.com/cloud-native-ai/spec-kit.git@master"
    "git+https://github.com/github/spec-kit.git@main"
  )

  # Test and try each source in order
  for source in "${sources[@]}"; do
    log info "Trying to install from: ${source}"

    # Extract hostname from the source URL for network testing
    local hostname=""
    if [[ ${source} == *"gitlab.alibaba-inc.com"* ]]; then
      hostname="gitlab.alibaba-inc.com"
    elif [[ ${source} == *"gitee.com"* ]]; then
      hostname="gitee.com"
    elif [[ ${source} == *"github.com"* ]]; then
      hostname="github.com"
    fi

    # Test network connectivity if we can extract a hostname
    if [ -n "${hostname}" ]; then
      log info "Testing network connectivity to ${hostname}..."
      if ! net_ping "${hostname}"; then
        log warn "Network connectivity to ${hostname} failed, skipping this source"
        continue
      fi
      log info "Network connectivity to ${hostname} successful"
    fi

    # Try to install from this source with timeout
    if pip3 install --timeout 20 "${source}"; then
      log notice "Specify kit installed successfully from ${source}"
      return "${RETURN_SUCCESS:-0}"
    else
      log warn "Failed to install from ${source}, trying next source..."
    fi
  done

  log error "Failed to install Specify kit from all available sources"
  return "${RETURN_FAILURE:-1}"
}

# Uninstall Specify kit
function specify_uninstall() {
  log info "Uninstalling Specify kit..."
  if ! have pip3; then
    log error "pip3 command not found. Please install pip3 first."
    return "${RETURN_FAILURE:-1}"
  fi

  if pip3 uninstall -y specify-cli; then
    log notice "Specify kit uninstalled successfully"
    return "${RETURN_SUCCESS:-0}"
  else
    log warn "Failed to uninstall Specify kit (it might not be installed)"
    return "${RETURN_SUCCESS:-0}"
  fi
}

# Check Specify dependencies and ensure installation
function specify_check() {
  # Ensure Specify is installed
  if ! specify_ensure; then
    return "${RETURN_FAILURE:-1}"
  fi

  # Call specify check to verify all required tools are available
  log info "Checking Specify dependencies..."
  if specify check; then
    log notice "Specify dependencies check passed"
    return "${RETURN_SUCCESS:-0}"
  else
    log error "Specify dependencies check failed"
    return "${RETURN_FAILURE:-1}"
  fi
}

# Initialize a new Specify project
# Usage: specify_init <ai_tool> [project_name]
# Available AI tools: claude, gemini, copilot, cursor, qwen, opencode, codex, windsurf, kilocode, auggie, roo
function specify_init() {
  local ai_tool=${1}
  local project_name=${2:-.}

  # Validate AI tool parameter
  if [ -z "${ai_tool}" ]; then
    log error "Usage: specify_init <ai_tool> [project_name]"
    log error "Available AI tools: claude, gemini, copilot, cursor, qwen, opencode, codex, windsurf, kilocode, auggie, roo"
    return "${RETURN_FAILURE:-1}"
  fi

  # Ensure Specify is available
  if ! specify_ensure; then
    return "${RETURN_FAILURE:-1}"
  fi

  log info "Initializing Specify project with AI tool: ${ai_tool}, project name: ${project_name}"
  if specify init "${project_name}" --ai "${ai_tool}" --script sh --no-git --force --skip-tls; then
    log notice "Specify project initialized successfully"
    return "${RETURN_SUCCESS:-0}"
  else
    log error "Failed to initialize Specify project"
    return "${RETURN_FAILURE:-1}"
  fi
}

function specify_deinit() {
  rm -rfv .github/prompts/speckit.*.prompt.md
  rm -rfv .specify/
}

# Initialize a Specify project with Claude AI
function specify_init_claude_project() {
  local project_name=${1:-.}
  specify_init claude "${project_name}"
}

# Initialize a Specify project with Gemini AI
function specify_init_gemini_project() {
  local project_name=${1:-.}
  specify_init gemini "${project_name}"
}

# Initialize a Specify project with Copilot AI
function specify_init_copilot_project() {
  local project_name=${1:-.}
  specify_init copilot "${project_name}"
}

# Initialize a Specify project with Cursor AI
function specify_init_cursor_project() {
  local project_name=${1:-.}
  specify_init cursor "${project_name}"
}

# Initialize a Specify project with Qwen Code
function specify_init_qwen_project() {
  local project_name=${1:-.}
  specify_init qwen "${project_name}"
}
