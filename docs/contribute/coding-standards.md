# Coding Standards

Authoritative coding rules for cws-lib-bash. Entry point:
[CONTRIBUTING.md](../../CONTRIBUTING.md).

## Naming & style

- Function names use snake_case with domain prefix (e.g., `git_clone`)
- Always use `local` for function variables
- Use `${variable}` with braces for all variables
- Set defaults with `${var:-default}`

## Error handling & logging

- Use `${RETURN_SUCCESS}` (0) and `${RETURN_FAILURE}` (1) for error handling
- Use `log` with appropriate log levels (info/notice/warn/error) for messages

## Development setup

```bash
# Clone your fork
git clone https://github.com/yourusername/cws-lib-bash.git
cd cws-lib-bash

# Run tests
./bin/cws_bash_test
```
