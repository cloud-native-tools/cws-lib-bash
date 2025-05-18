# CWS-Lib-Bash Guidelines

A Bash library providing utility functions for cloud-native operations.

## Structure

- `/bin/`: Executable scripts
- `/expect/`: Expect scripts
- `/profile.d/`: Core shell initialization
- `/scripts/`: Domain-specific utilities

## Function Guidelines

- Organization:
  - Place in appropriate domain file
  - Follow domain prefix convention (e.g., `git_clone`)
- Naming and Format:
  - Use `snake_case` names with domain prefix
  - Format: `function name() { ... }`
  - Single responsibility per function
- Variables and Parameters:
  - Use `local` for ALL function variables
  - Provide default values when appropriate
  - Parameters without default values must be validated for empty values
- Error Handling:
  - Use `${RETURN_SUCCESS}` (0) and `${RETURN_FAILURE}` (1)
  - Use `|| return ${RETURN_FAILURE}` pattern
- Best Practices:
  - Consider cross-platform compatibility
  - Document purpose and usage
  - Handle edge cases

Example:
```bash
function git_clone_into() {
  local dir=${1}
  local url=${2}
  if [ -z "${dir}" ] || [ -z "${url}" ]; then
    log error "Usage: git_clone_into <dir> <url>"
    return ${RETURN_FAILURE:-1}
  fi
  # Implementation
}
```

## Script Sourcing Behavior

- All files in `/scripts/` are automatically sourced in `.bashrc`
- Do not include directly executed code outside of function definitions
- All executable logic must be encapsulated in functions
- Use initialization checks if needed:
  ```bash
  # Check dependencies when script is sourced
  function domain_check_dependencies() {
    # Implementation
  }
  
  # Then call at the end of the file with proper error handling
  domain_check_dependencies || return ${RETURN_FAILURE:-1}
  ```
- This prevents unintentional execution when scripts are sourced

## Variables

- Use lowercase with underscores
- `local` for ALL function variables
- Use `${variable}` with braces
- Default optional parameters: `${var:-default}`
- Parameters without default values must be validated for empty values

## Error Handling

- Use `${RETURN_SUCCESS}` (0) and `${RETURN_FAILURE}` (1)
- Validate required parameters
- Use `|| return ${RETURN_FAILURE}` pattern

## Logging

- Use `log` with levels: `info`, `notice`, `warn`, `error`, `fatal`
- Include descriptive messages
- Include usage in error messages
- Use appropriate log levels for different message types:
  - `log error` for exception and error information
  - `log warn` for warning messages
  - `log notice` for important highlighted information
  - `log info` for general informational messages
  - `log fatal` for critical errors requiring immediate termination

## Command Availability

- Use `have` function to test if commands are available
- Example usage:
```bash
if ! have expect; then
  log error "expect command not found, please install expect first"
  return ${RETURN_FAILURE}
fi
```