# CWS-Lib-Bash Guidelines

## Code Generation
- Refer to the contents of the README.md file in the project directory to understand the basic information of the project. If there is a docs directory in the project root directory, refer to the contents within it.
- For complex tasks, create a TODO.md file first to list the plan and steps, then execute step by step. Update the corresponding records in the TODO.md document each time a step is completed, and check whether all items in TODO.md are completed after the task is finished.
- Generate documentation in English, and use English for code comments and logs.

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
