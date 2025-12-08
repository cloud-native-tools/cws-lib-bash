# CWS-Lib-Bash

A Bash utility library for cloud-native environment operations, system management, and development workflows.

## Overview

CWS-Lib-Bash provides a comprehensive set of utility functions for common operations in cloud-native environments, making daily operations and development work more efficient. The library follows consistent design patterns and provides standardized approaches to common tasks.

## Features

- Modular design with function libraries organized by technology domain
- Cross-platform support for Linux and macOS systems
- Unified logging and error handling mechanisms
- Consistent naming conventions and coding style

## Project Structure

```
.
├── bin/              # Executable scripts for setting up and using the library
├── expect/           # Automation interaction scripts
├── profile.d/        # Core functionality loaded during shell initialization
└── scripts/          # Utility functions organized by technology domain
```

## Quick Start

### Installation

1. Clone the repository:

```bash
git clone https://github.com/cloud-native-tools/cws-lib-bash.git
cd cws-lib-bash
```

2. Run the installation script:

```bash
./bin/cws_bash_setup
```

### Usage

1. Load the library in the current shell session:

```bash
source ./bin/cws_bash_env
```

2. Or use `cws_bash_run` to execute commands:

```bash
./bin/cws_bash_run <function_name> [arguments...]
```

## Development Guidelines

- Function naming uses snake_case with domain prefix
- Use local variables with proper referencing (${variable})
- Use standard return codes (${RETURN_SUCCESS} and ${RETURN_FAILURE})
- Use logging functions (log info/notice/warn/error) to record important information

## License

[MIT License](LICENSE)

## Contributing

Contributions and issue reports are welcome. Please ensure you follow the project's coding style and development guidelines.

## Repository

https://github.com/cloud-native-tools/cws-lib-bash

