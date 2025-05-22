# CWS-Lib-Bash Guidelines

## Code Generation
- Reference README.md if present
- Create TODO.md for multi-step tasks before generating code
- Skip error fixes for large files
- Documentation in English
- Comments and logs in English

## Core Structure
- `/bin/`: Executable scripts
- `/expect/`: Expect scripts for automation
- `/profile.d/`: Shell initialization
- `/scripts/`: Domain-specific utilities

## Function Guidelines
- **Naming**: Use `snake_case` with domain prefix (e.g., `git_clone`)
- **Format**: `function name() { ... }`
- **Variables**: Always use `local` for function variables
- **Parameters**: Validate empty values, provide defaults when appropriate
- **Error Handling**: Use `${RETURN_SUCCESS}` (0) and `${RETURN_FAILURE}` (1)

## Function Example
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

## Sourcing Behavior
- Files in `/scripts/` are automatically sourced
- Encapsulate logic in functions
- No direct execution outside functions

## Variable Guidelines
- Use lowercase with underscores
- Always use `${variable}` with braces
- Set defaults with `${var:-default}`

## Logging
- Use `log` with levels: `info`, `notice`, `warn`, `error`, `fatal`
- Include descriptive messages and usage in errors

## Command Availability
- Test with `have` function:
```bash
if ! have expect; then
  log error "expect command not found"
  return ${RETURN_FAILURE}
fi
```