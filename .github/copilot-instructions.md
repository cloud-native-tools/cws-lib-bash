# CWS-Lib-Bash Guidelines

A Bash library providing utility functions for cloud-native operations.

## Structure

- `/bin/`: Executable scripts
- `/expect/`: Expect scripts
- `/profile.d/`: Core shell initialization
- `/scripts/`: Domain-specific utilities

## Function Style

- Use `snake_case` names with domain prefix (e.g., `git_clone`)
- Format: `function name() { ... }`
- Parameter validation required
- Single responsibility per function

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

## Variables

- Use lowercase with underscores
- `local` for ALL function variables
- Use `${variable}` with braces
- Default optional parameters: `${var:-default}`

## Error Handling

- Use `${RETURN_SUCCESS}` (0) and `${RETURN_FAILURE}` (1)
- Validate required parameters
- Use `|| return ${RETURN_FAILURE}` pattern

## Logging

- Use `log` with levels: `info`, `notice`, `warn`, `error`, `fatal`
- Include descriptive messages
- Include usage in error messages

## Cross-Platform

Consider macOS vs Linux differences:
```bash
if command -v nproc >/dev/null 2>&1; then
  nproc  # Linux
elif command -v sysctl >/dev/null 2>&1 && [[ "$(uname)" == "Darwin" ]]; then
  sysctl -n hw.ncpu  # macOS
else
  echo "1"  # Default
fi
```

## When Adding Functions

1. Place in appropriate domain file
2. Follow domain prefix convention
3. Use `function name() { ... }` format
4. Use `local` for variables
5. Validate parameters
6. Provide default values
7. Use proper error handling
8. Consider cross-platform compatibility
9. Document purpose and usage
10. Handle edge cases