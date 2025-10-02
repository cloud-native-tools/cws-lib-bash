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
function specify_install(){
  log info "Installing Specify kit from GitHub repository..."
  if ! have pip3; then
    log error "pip3 command not found. Please install pip3 first."
    return "${RETURN_FAILURE:-1}"
  fi

  if pip3 install git+https://github.com/github/spec-kit.git; then
    log notice "Specify kit installed successfully"
    return "${RETURN_SUCCESS:-0}"
  else
    log error "Failed to install Specify kit"
    return "${RETURN_FAILURE:-1}"
  fi
}

# Check Specify dependencies and ensure installation
function specify_check(){
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
function specify_init(){
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

# Initialize a Specify project with Claude AI
function specify_init_claude_project(){
  local project_name=${1:-.}
  specify_init claude "${project_name}"
}

# Initialize a Specify project with Gemini AI
function specify_init_gemini_project(){
  local project_name=${1:-.}
  specify_init gemini "${project_name}"
}

# Initialize a Specify project with Copilot AI
function specify_init_copilot_project(){
  local project_name=${1:-.}
  specify_init copilot "${project_name}"
}

# Initialize a Specify project with Cursor AI
function specify_init_cursor_project(){
  local project_name=${1:-.}
  specify_init cursor "${project_name}"
}

# Initialize a Specify project with Qwen Code
function specify_init_qwen_project(){
  local project_name=${1:-.}
  specify_init qwen "${project_name}"
}
