# CWS-Lib-Bash Function Library Guide

## Project Overview

CWS-Lib-Bash is a Bash utility library for cloud-native environment operations, system management, and development workflows. This library provides a comprehensive set of utility functions for common operations in cloud-native environments, making daily operations and development work more efficient.

## Core Features

- Modular function library design organized by technology domain
- Cross-platform compatibility for Linux and macOS systems
- Unified logging and error handling mechanisms
- Consistent naming conventions and coding style
- Automation interaction script support
- Standardized return codes and error handling

## Project Structure

```
cws-lib-bash/
├── bin/              # Executable scripts for setting up and using the library
│   ├── cws_env      # Environment initialization script
│   ├── cws_run      # Command execution entry script
│   └── cws_setup    # Installation setup script
// ...rest of code...
```

## Getting Started

### Installation Steps

1. **Clone the repository:**

   ```bash
   git clone https://github.com/cloud-native-tools/cws-lib-bash.git
   cd cws-lib-bash
   ```

2. **Run the installation script:**
   ```bash
   ./bin/cws_setup
   ```

### Usage Methods

1. **Load the library in the current shell session:**

   ```bash
   source ./bin/cws_env
   ```

2. **Or use `cws_run` to execute commands:**
   ```bash
   ./bin/cws_run <function_name> [arguments...]
   ```

## Function Development Guidelines

### Naming Rules

- Use `snake_case` format with domain prefix (e.g., `git_clone`, `docker_build`)
- Function format: `function name() { ... }`
- Variables: Always use `local` declaration for function internal variables
- Parameters: Validate empty values, provide defaults when appropriate

### Error Handling

- Use `${RETURN_SUCCESS}` (0) and `${RETURN_FAILURE}` (1)
- Pass function execution results through return codes
- Use descriptive error messages

### Function Example

```bash
function git_clone_into() {
  local dir=${1}
  local url=${2}
  if [ -z "${dir}" ] || [ -z "${url}" ]; then
    log error "Usage: git_clone_into <dir> <url>"
// ...rest of code...
```

## Import Behavior

- Files in `/scripts/` directory are automatically imported
- Encapsulate logic in functions
- Do not execute code directly outside functions
- Use modular design, organize functions by functional domain

## Variable Guidelines

- Use lowercase letters and underscores
- Always use `${variable}` format with braces
- Use `${var:-default}` to set default values
- Declare local variables with `local`

## Logging

Use the `log` function with the following levels:

- `log info` - General information
- `log notice` - Notice items
- `log warn` - Warning information
- `log error` - Error information
- `log fatal` - Fatal errors

Examples:

```bash
log info "Starting deployment process"
log warn "Configuration file not found, using defaults"
log error "Failed to connect to database"
```

## Command Availability Check

Use the `have` function for tool availability testing:

```bash
if ! have docker; then
  log error "Docker command not found"
  return ${RETURN_FAILURE}
fi

// ...rest of code...
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

### Kubernetes Operations

- `k8s_apply_manifest` - Apply Kubernetes manifest
- `k8s_get_pods` - Get Pod list
- `k8s_wait_for_ready` - Wait for resources to be ready

### Network Tools

- `network_test_connectivity` - Test network connectivity
- `network_get_ip` - Get IP address
- `network_port_check` - Check port status

# Test individual function
./bin/cws_run git_clone_into /tmp/test https://github.com/example/repo.git

# Check return code
echo $?
```

## Extension Development

### Adding New Functions

// ...rest of code...
```bash
# Create new functional module
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

  # Implementation here
  log info "Processing ${param}"
  return ${RETURN_SUCCESS:-0}
}
EOF
```
