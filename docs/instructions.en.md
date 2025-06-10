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
├── expect/           # Automation interaction scripts
├── profile.d/        # Core functionality loaded during shell initialization
└── scripts/          # Utility functions organized by technology domain
    ├── ansible/      # Ansible-related functions
    ├── docker/       # Docker operation functions
    ├── git/          # Git version control functions
    ├── k8s/          # Kubernetes management functions
    ├── network/      # Network utility functions
    ├── os/           # Operating system related functions
    └── utils/        # General utility functions
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
    return ${RETURN_FAILURE:-1}
  fi

  if git clone "${url}" "${dir}"; then
    log info "Successfully cloned ${url} to ${dir}"
    return ${RETURN_SUCCESS:-0}
  else
    log error "Failed to clone ${url}"
    return ${RETURN_FAILURE:-1}
  fi
}
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

if ! have kubectl; then
  log error "kubectl command not found"
  return ${RETURN_FAILURE}
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

### Kubernetes Operations

- `k8s_apply_manifest` - Apply Kubernetes manifest
- `k8s_get_pods` - Get Pod list
- `k8s_wait_for_ready` - Wait for resources to be ready

### Network Tools

- `network_test_connectivity` - Test network connectivity
- `network_get_ip` - Get IP address
- `network_port_check` - Check port status

## Best Practices

### Error Handling

1. Always check function return codes
2. Provide meaningful error messages
3. Use appropriate log levels

### Performance Optimization

1. Avoid unnecessary external command calls
2. Use Bash built-in features
3. Cache repeatedly calculated results

### Security Considerations

1. Validate input parameters
2. Avoid code injection
3. Use quotes to protect variables

## Debugging and Testing

### Enable Debug Mode

```bash
export CWS_DEBUG=true
source ./bin/cws_env
```

### Test Functions

```bash
# Test individual function
./bin/cws_run git_clone_into /tmp/test https://github.com/example/repo.git

# Check return code
echo $?
```

## Extension Development

### Adding New Functions

1. **Create function files in the appropriate `scripts/` subdirectory**
2. **Follow naming conventions and coding standards**
3. **Add appropriate documentation and examples**
4. **Test various usage scenarios for functions**

### Creating New Modules

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

## Troubleshooting

### Common Issues

**Function Not Found:**

- Ensure bin/cws_env is properly sourced
- Check if function file is in scripts/ directory
- Verify function name spelling

**Permission Issues:**

- Check script execution permissions
- Ensure access to relevant files/directories

**Missing Dependencies:**

- Use `have` function to check required commands
- Install missing tools and dependencies

## Contributing Guide

1. Fork the project repository
2. Create feature branch
3. Follow coding standards
4. Add tests and documentation
5. Submit Pull Request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
