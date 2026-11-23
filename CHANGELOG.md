# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Initial project setup with core bash library structure
- Module organization for different technology domains
- Standard utility functions for common operations
- Environment setup and initialization scripts
- Cross-platform compatibility layer for Linux and macOS
- Logging and error handling framework

### Changed
- Split the ai-harness and Spec Kit shell helpers: `ah_*` (and `ai_harness_*`) drive ai-harness; `specify_*` drives the independent Spec Kit CLI through spec-kit's own `install.sh` (pip/python by default; uv only behind install.sh's `--uv` opt-in, so this helper needs no uv) and verifies that `specify` identifies as Spec Kit. `specify_init_all` no longer runs `ai-harness init` (which printed `/ah.*` commands), and `ah_uninstall` no longer removes the Spec Kit `specify-cli` package.
- Aligned `313_ai_harness.sh` with `313_specify.sh`: same function set, order and logic with only names swapped. The ai-harness install override is now `AI_HARNESS_INSTALL_SH` (was the cross-project `SPECIFY_INSTALL_SH`), and `ah_ensure` verifies that `ai-harness` identifies as ai-harness.

### Deprecated

### Removed

### Fixed
- Hardened `git_switch` so repositories with submodules can switch branch/tag cleanly after stale submodule metadata is removed, and added regression coverage for this flow

### Security