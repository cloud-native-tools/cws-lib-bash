# CWS-Lib-Bash

A Bash utility library for cloud-native environment operations, system
management, and development workflows.

## Overview

CWS-Lib-Bash provides utility functions for common operations in cloud-native
environments — Docker, Kubernetes, package managers, networking, Git, language
toolchains, cloud infrastructure, and AI tooling — with consistent design
patterns. See the full [feature catalog](docs/concepts/feature-domains.md)
and [ARCHITECTURE.md](ARCHITECTURE.md).

## Project Structure

```
.
├── bin/              # Executable scripts for setting up and using the library
├── profile.d/        # Core functionality loaded during shell initialization
├── scripts/          # Utility functions organized by technology domain
└── docs/             # Documentation (see index below)
```

## Quick Start

```bash
git clone https://github.com/cloud-native-tools/cws-lib-bash.git
cd cws-lib-bash
./bin/cws_bash_setup            # install
source ./bin/cws_bash_env       # load into current shell
./bin/cws_bash_run <function_name> [arguments...]   # or one-shot call
```

## Documentation

- [Concepts](docs/concepts/index.md) — what & why, feature domains
- [Tutorials](docs/tutorials/index.md) — learning path
- [Tasks](docs/tasks/index.md) — step-by-step guides
- [Reference](docs/reference/index.md) — exact specs
- [Decisions](docs/decisions/index.md) — ADRs
- [Contribute](docs/contribute/index.md) — contributor guides
- [Notes](docs/notes/index.md) — temporary notes

## Contributing

Contributions and issue reports are welcome — see
[CONTRIBUTING.md](CONTRIBUTING.md) and the
[coding standards](docs/contribute/coding-standards.md).

## License

[MIT License](LICENSE) · https://github.com/cloud-native-tools/cws-lib-bash
