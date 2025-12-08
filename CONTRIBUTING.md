# Contributing to cws-lib-bash

Thank you for considering contributing to cws-lib-bash! This document outlines the process and guidelines for contributing to this project.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for everyone.

## How to Contribute

### Reporting Issues

If you find a bug or have a feature request:

1. Search the existing issues to avoid duplicates
2. Open a new issue with a clear title and description
3. Include steps to reproduce if reporting a bug
4. Include your environment details (OS, shell version, etc.)

### Submitting Changes

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes following our coding standards
4. Add or update tests as needed
5. Ensure all tests pass
6. Update documentation as needed
7. Submit a pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/yourusername/cws-lib-bash.git
cd cws-lib-bash

# Run tests
./bin/cws_bash_test
```

## Coding Standards

- Function names use snake_case with domain prefix (e.g., `git_clone`)
- Always use `local` for function variables
- Use `${variable}` with braces for all variables
- Set defaults with `${var:-default}`
- Use `${RETURN_SUCCESS}` (0) and `${RETURN_FAILURE}` (1) for error handling
- Use `log` with appropriate log levels for messages

## Pull Request Process

1. Ensure all tests pass
2. Update documentation if needed
3. Update the CHANGELOG.md file with your changes under the Unreleased section
4. Pull requests will be reviewed by maintainers
5. Address any review feedback promptly

## Release Process

Releases are managed by the core team following semantic versioning principles.

## License

By contributing to this project, you agree that your contributions will be licensed under the project's MIT license.