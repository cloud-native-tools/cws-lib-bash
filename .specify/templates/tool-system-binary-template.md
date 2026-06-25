# Tool Record: [TOOL NAME]

**Tool Name**: [TOOL NAME]  
**Tool Type**: `system-binary`  
**Source Identifier**: [BINARY PATH or COMMAND NAME]  
**Tool ID**: [TOOL ID]  
**Aliases**: [comma-separated aliases, optional]  
**Status**: [Draft | Verified | Deprecated]  
**Discovery Origin**: [manual-entry | discovery-assisted | imported]  
**Last Updated**: [YYYY-MM-DD]

## Scope

**Availability**: System-level — available system-wide to all users and sessions via the `PATH`.  
**Typical Sources**: Executable binaries or scripts installed by the OS package manager (apt, yum, brew, etc.), language-level package managers (pip, npm -g, cargo install), or placed manually in `/usr/bin/`, `/usr/local/bin/`, etc.  
**Portability**: May be tied to a specific OS distribution or package ecosystem. A binary available on Ubuntu may not exist on Alpine or macOS, and vice versa. Version and feature sets can differ across distributions.  
**Source Identifier Convention**: Absolute path to the binary (e.g., `/usr/bin/jq`) or the command name if unique in `PATH` (e.g., `jq`), discoverable via `which` or `shutil.which`.

## Description

[Short, user-friendly description of what this binary does and when to use it]

## Resource ID

- Canonical ID: `[RESOURCE ID]`
- Canonical Path: `[CANONICAL PATH]`

## Invocation & I/O Contract

- **Input Channel**: `[command-line | stdin]`
- **Invocation Mode**: `[command-line | shell-environment]`
- **Output Mode**: `[json | plain-log-lines]`

## Parameters

| Name | Type | Required | Description | Default |
|------|------|----------|-------------|---------|
| [param] | [type] | [yes/no] | [purpose] | [default or empty] |

## Returns

| Name | Type | Description |
|------|------|-------------|
| [field] | [type] | [meaning of return field] |

## Usage Notes

- [Any constraints, preconditions, or special handling]
- [Required system packages]
- [Platform-specific behavior]

## Examples

### Example Input

```json
{
  "tool": "[TOOL NAME]",
  "io": {
    "input_channel": "command-line",
    "invocation_mode": "command-line",
    "output_mode": "json"
  },
  "arguments": {
    "[param]": "value"
  },
  "stdin": "[optional stdin content when input_channel=stdin]"
}
```

### Example Output

```json
{
  "output_mode": "json",
  "result": {
    "[field]": "value"
  },
  "stdout": "[optional plain log lines when output_mode=plain-log-lines]"
}
```

## Behavioral Rules

<!--
  Each behavioral rule MUST be a markdown bullet prefixed with an RFC 2119 keyword:
  - MUST: Absolute requirement — the agent must follow this rule in every invocation.
  - MUST NOT: Absolute prohibition — the agent must never violate this constraint.
  - SHOULD: Recommended practice — the agent follows this unless a justified exception applies.
  - SHOULD NOT: Discouraged practice — the agent avoids this unless a justified exception applies.
  
  These rules are authoritative: the AI agent MUST use them instead of its built-in
  knowledge about the tool. Add, remove, or modify rules via /speckit.tools.
-->

- [MUST | MUST NOT | SHOULD | SHOULD NOT] [constraint text describing the behavioral rule]

## Discovery Metadata

- **Discovery Method**: [auto-discovery | manual-entry | imported]
- **Discovery Source**: system PATH (shutil.which)
- **Verification Status**: [unverified | verified]
- **Notes**: [Any additional context]

Execute system binary [TOOL NAME]
