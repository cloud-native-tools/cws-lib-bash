# CWS-Lib-Bash Copilot Instructions

## Project Overview

CWS-Lib-Bash is a comprehensive Bash library that provides utility functions for cloud-native operations, system administration, and development workflows. The library organizes functions into domain-specific files and follows consistent patterns for function definitions, error handling, logging, and documentation.

## Repository Structure

- `/bin/`: Contains executable scripts for setting up and using the library
- `/expect/`: Expect scripts for automation
- `/profile.d/`: Core functionality loaded during shell initialization
- `/scripts/`: Domain-specific utility functions organized by tool or technology

## Coding Conventions

### Function Naming and Style

- Use `snake_case` for function names (e.g., `git_clone`, `file_extract`)
- Prefix functions with their domain name (e.g., `git_`, `k8s_`, `file_`)
- Keep functions focused on a single responsibility
- Group related functions in the same file
- **IMPORTANT**: Always define functions using the format `function name() { ... }` 
- All functions should have proper parameter validation

Example:
```bash
function git_clone_into() {
  local dir=${1}
  local url=${2}
  if [ -z "${dir}" ] || [ -z "${url}" ]; then
    log error "Usage: git_clone_into <dir> <url>"
    return ${RETURN_FAILURE:-1}
  fi

  if [ ! -d "${dir}" ]; then
    mkdir -p "${dir}"
  fi
  shift 2
  git -C "${dir}" clone --progress -j$(get_core_count) --recurse-submodules ${url} "$@"
}
```

### Variable Conventions

- Use lowercase with underscores for variable names
- **IMPORTANT**: Use `local` for ALL variables inside functions
- Quote variable references with curly braces: `${variable}`
- **IMPORTANT**: For functions with multiple parameters, provide default values for all parameters after the first one
- Default variables when appropriate: `${variable:-default}`

Example:
```bash
function domain_operation() {
  local required_param=${1}
  local optional_param=${2:-"default_value"}
  local another_param=${3:-10}
  
  if [ -z "${required_param}" ]; then
    log error "Usage: domain_operation <required_param> [optional_param] [another_param]"
    return ${RETURN_FAILURE:-1}
  fi
  
  # Function implementation
}
```

### Error Handling

- Use `${RETURN_SUCCESS}` (0) and `${RETURN_FAILURE}` (1) for function returns
- Provide default values for these constants: `${RETURN_FAILURE:-1}`
- Validate required parameters and return with error if missing
- Use `|| return ${RETURN_FAILURE}` pattern for command error checking

Example:
```bash
if [ -z "${target}" ]; then
  log error "Usage: function_name <target>"
  return ${RETURN_FAILURE:-1}
fi

command || return ${RETURN_FAILURE:-1}
```

### Logging

- Use the `log` function with appropriate levels: `info`, `notice`, `warn`, `error`, `fatal`
- Include descriptive messages that explain what happened
- For error messages, include usage information when appropriate

Example:
```bash
log info "update in ${PWD}"
log error "Usage: git_clone <url>"
log notice "Git remote setup complete at [${repo}]"
```

### Documentation

- Add a brief comment for complex logic sections
- Document parameters with usage examples for public functions
- Include usage information in error messages

## Common Patterns

### Parameter Validation

```bash
function domain_action() {
  local target=${1}
  local options=${2:-"default"}
  local count=${3:-10}
  
  if [ -z "${target}" ]; then
    log error "Usage: domain_action <target> [options] [count]"
    return ${RETURN_FAILURE:-1}
  fi
  
  # Function implementation
}
```

### Cross-Platform Compatibility

Consider macOS vs Linux differences:
```bash
if command -v nproc >/dev/null 2>&1; then
  nproc  # Linux
elif command -v sysctl >/dev/null 2>&1 && [[ "$(uname)" == "Darwin" ]]; then
  sysctl -n hw.ncpu  # macOS
else
  echo "1"  # Default fallback
fi
```

### Directory Navigation Safety

```bash
pushd "${directory}" >/dev/null 2>&1 || return ${RETURN_FAILURE:-1}
# Operations
popd >/dev/null 2>&1 || return ${RETURN_FAILURE:-1}
```

### Safe Command Execution

```bash
if ! command args >/dev/null 2>&1; then
  log error "Failed to execute command"
  return ${RETURN_FAILURE:-1}
fi
```

## When Adding New Functions

1. Place functions in the appropriate domain file in `/scripts/` or create a new one if needed
2. Follow the naming convention of the domain prefix (e.g., `git_`, `k8s_`)
3. Define the function using the format `function name() { ... }`
4. Declare ALL variables inside the function with `local`
5. Validate all required parameters
6. Provide default values for optional parameters
7. Use proper error handling with descriptive messages
8. Implement cross-platform compatibility where needed
9. Document the function's purpose and usage
10. Handle edge cases and provide safe defaults
11. If an existing function implements the required functionality, call that function instead of reimplementing it.

## Common Constants

- `${RETURN_SUCCESS}`: 0
- `${RETURN_FAILURE}`: 1
- Log levels: `info`, `notice`, `warn`, `error`, `fatal`

When enhancing or extending this library, maintain consistency with these patterns and conventions to ensure high-quality, maintainable code.