# CWS-Lib-Bash

A Bash utility library for cloud-native environment operations, system management, and development workflows.

## Overview

CWS-Lib-Bash provides a comprehensive set of utility functions for common operations in cloud-native environments, making daily operations and development work more efficient. The library follows consistent design patterns and provides standardized approaches to common tasks.

## Features

### Functional Features

- **Core Framework**: Core environment initialization, logging, and utility functions.
- **Docker Support**: Utilities for Docker container and image management.
- **Kubernetes Operations**: Helpers for kubectl, Helm, and cluster management.
- **Package Management**: Unified interface for system package managers (apt, yum, rpm).
- **Network Utilities**: Tools for network connectivity testing and diagnostics.
- **Git Operations**: Enhancements for Git workflow and repository management.
- **Language Runtimes**: Setup and management for Python, Java, Go, GCC, Rust, and related toolchains.
- **System Administration**: System-level maintenance, performance profiling, and configuration tools.
- **Text & Data Processing**: Utilities for JSON/YAML parsing and string manipulation.
- **Cloud Infrastructure**: Utilities for cloud providers (Alibaba Cloud) and IaC (Terraform).
- **Virtualization**: VM lifecycle management via QEMU and libvirt.
- **AI Tool Integration**: Setup and management for AI coding assistants and specification tooling.
- **Development Environment**: IDE workspace setup and developer tool management.
- **Security & Cryptography**: TLS certificate generation, CA management, and cryptographic operations.
- **Remote Automation**: Automated terminal interactions and configuration management via Ansible and Expect.

### Non-functional Features

- **Cross-Platform Compatibility**: Support for both Linux and macOS environments.
- **Test Automation**: Automated testing framework for Bash scripts.
- **Function Reference Documentation**: Auto-generated reference documentation for all library functions. *(Draft)*
- **Dependency Validation**: Systematic tracking and validation of external command dependencies. *(Draft)*

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

