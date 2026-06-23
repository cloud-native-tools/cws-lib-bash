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
# Available AI tools: all, claude, copilot, qwen, qoder, opencode
function specify_init() {
  local ai_tool=${1}
  local project_name=${2:-.}
  local ignore_agent_tools=${3:-false}

  # Validate AI tool parameter
  if [ -z "${ai_tool}" ]; then
    log error "Usage: specify_init <ai_tool> [project_name]"
    log error "Available AI tools: all, claude, copilot, qwen, qoder, opencode"
    return "${RETURN_FAILURE:-1}"
  fi

  case "${ai_tool}" in
  all | claude | copilot | opencode | qwen | qoder )
    ;;
  *)
    log error "Unsupported AI tool: ${ai_tool}"
    log error "Available AI tools: all, claude, copilot, qwen, qoder, opencode"
    return "${RETURN_FAILURE:-1}"
    ;;
  esac

  # Ensure Specify is available
  if ! specify_ensure; then
    return "${RETURN_FAILURE:-1}"
  fi

  log info "Initializing Specify project with AI tool: ${ai_tool}, project name: ${project_name}"

  if [ "${ai_tool}" = "all" ]; then
    local tools=(claude copilot opencode qwen qoder)
    local tool=""
    local tool_ignore_agent_tools=false

    for tool in "${tools[@]}"; do
      tool_ignore_agent_tools=false
      case "${tool}" in
      claude | opencode | qwen | qoder)
        tool_ignore_agent_tools=true
        ;;
      esac

      if [ "${tool_ignore_agent_tools}" = "true" ]; then
        if ! specify init "${project_name}" --ai "${tool}" --script sh --no-git --force --skip-tls --ignore-agent-tools; then
          log error "Failed to initialize Specify project for AI tool: ${tool}"
          return "${RETURN_FAILURE:-1}"
        fi
      elif ! specify init "${project_name}" --ai "${tool}" --script sh --no-git --force --skip-tls; then
        log error "Failed to initialize Specify project for AI tool: ${tool}"
        return "${RETURN_FAILURE:-1}"
      fi
    done

    log notice "Specify project initialized successfully for all AI tools"
    return "${RETURN_SUCCESS:-0}"
  fi

  if [ "${ignore_agent_tools}" = "true" ]; then
    if specify init "${project_name}" --ai "${ai_tool}" --script sh --no-git --force --skip-tls --ignore-agent-tools; then
      log notice "Specify project initialized successfully"
      return "${RETURN_SUCCESS:-0}"
    fi
  elif specify init "${project_name}" --ai "${ai_tool}" --script sh --no-git --force --skip-tls; then
    log notice "Specify project initialized successfully"
    return "${RETURN_SUCCESS:-0}"
  fi

  log error "Failed to initialize Specify project"
  return "${RETURN_FAILURE:-1}"
}

# Initialize a Specify project with Copilot AI
function specify_init_copilot() {
  local project_name=${1:-.}
  specify_init copilot "${project_name}"
}

# Initialize a Specify project with Qwen Code
function specify_init_qwen_code() {
  local project_name=${1:-.}
  specify_init qwen "${project_name}" true
}

# Initialize a Specify project with Qoder
function specify_init_qoder() {
  local project_name=${1:-.}
  specify_init qoder "${project_name}" true
}

# Initialize a Specify project with OpenCode
function specify_init_opencode() {
  local project_name=${1:-.}
  specify_init opencode "${project_name}" true
}

# Initialize a Specify project with claude code
function specify_init_claude() {
  local project_name=${1:-.}
  specify_init claude "${project_name}" true
}

# Initialize a Specify project with all AI agent tools
function specify_init_all() {
  local project_name=${1:-.}
  specify_init all "${project_name}" true
}

function specify_deinit() {
  local ai_tool=${1:-all}

  case "${ai_tool}" in
  all)
    rm -rfv .github/prompts/speckit.*.prompt.md
    rm -rfv .qwen/commands/speckit.*.toml
    rm -rfv .qoder/commands/speckit.*.md
    rm -rfv .opencode/command/speckit.*.md
    ;;
  copilot)
    rm -rfv .github/prompts/speckit.*.prompt.md
    ;;
  qwen)
    rm -rfv .qwen/commands/speckit.*.toml
    ;;
  qoder)
    rm -rfv .qoder/commands/speckit.*.md
    ;;
  opencode)
    rm -rfv .opencode/command/speckit.*.md
    ;;
  *)
    log error "Usage: specify_deinit [copilot|qwen|qoder|opencode|all]"
    return "${RETURN_FAILURE:-1}"
    ;;
  esac

  rm -rfv .specify/memory/features .specify/memory/features.md
  rm -rfv .specify/scripts .specify/templates
}