# CWS-Lib-Bash Development Guide

## Project Overview

CWS-Lib-Bash is a Bash utility library for cloud-native environment operations, system management, and development workflows. This library provides a comprehensive set of utility functions for common operations in cloud-native environments, making daily operations and development work more efficient.

## Core Features

- **Modular Design**: Function libraries organized by technology domain
- **Cross-platform Compatibility**: Support for Linux and macOS systems
- **Unified Logging**: Standardized logging and error handling mechanisms
- **Consistent Coding Style**: Unified naming conventions and code structure
- **Automated Interaction**: Support for scripted interaction operations

## Project Structure

```
cws-lib-bash/
├── bin/              # Executable scripts
│   ├── cws_env      # Environment initialization script
│   ├── cws_run      # Command execution entry point
│   └── cws_setup    # Installation setup script
├── expect/          # Automated interaction scripts
├── profile.d/       # Core functionality loaded during shell initialization
└── scripts/         # Utility functions organized by technology domain
```

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/cloud-native-tools/cws-lib-bash.git
cd cws-lib-bash

# Run installation script
./bin/cws_setup
```

### Usage

```bash
# Load library in current shell session
source ./bin/cws_env

# Or use cws_run to execute commands
./bin/cws_run <function_name> [arguments...]
```

## Function Development Standards

### Naming Rules

- Use `snake_case` format with domain prefix
- Function format: `function name() { ... }`
- Variables: Always use `local` declaration for function variables
- Parameter validation: Check for empty values, provide defaults

### Error Handling

```bash
# Use standard return codes
return ${RETURN_SUCCESS:-0}  # Success
return ${RETURN_FAILURE:-1}  # Failure

# Example function
function git_clone_into() {
  local dir=${1}
  local url=${2}
  if [ -z "${dir}" ] || [ -z "${url}" ]; then
    log error "Usage: git_clone_into <dir> <url>"
    return ${RETURN_FAILURE:-1}
  fi
  # Implementation logic
}
```

### Logging

```bash
# Supported log levels
log info "General information"
log notice "Notice information"
log warn "Warning information"
log error "Error information"
log fatal "Fatal error"
```

### Tool Availability Check

```bash
# Check if command is available
if ! have docker; then
  log error "Docker command not found"
  return ${RETURN_FAILURE:-1}
fi
```

## Common Function Modules

### Git Operations

- `git_clone_into` - Clone repository to specified directory
- `git_current_branch` - Get current branch name
- `git_is_clean` - Check if working directory is clean

### Docker Operations

- `docker_build_image` - Build Docker image
- `docker_run_container` - Run container
- `docker_cleanup` - Clean up unused resources

### Network Tools

- `network_test_connectivity` - Test network connectivity
- `network_get_ip` - Get IP address
- `network_port_check` - Check port status

## Extension Development

### Adding New Function Modules

```bash
# Create new function module
mkdir scripts/mymodule

# Add function file
cat > scripts/mymodule/functions.sh << 'EOF'
#!/bin/bash

function mymodule_do_something() {
  local param=${1}
  if [ -z "${param}" ]; then
    log error "Usage: mymodule_do_something <param>"
    return ${RETURN_FAILURE:-1}
  fi

  log info "Processing ${param}"
  return ${RETURN_SUCCESS:-0}
}
EOF
```

### Usage Examples

```bash
# Test single function
./bin/cws_run git_clone_into /tmp/test https://github.com/example/repo.git

# Check return code
echo $?
```

## Code Generation Standards

- Reference project README.md for basic information
- Create TODO.md file for complex tasks to plan steps
- Use scripts for complex file operations
- Use Chinese for documentation, English for code comments
- Split code files when exceeding 1000 lines
