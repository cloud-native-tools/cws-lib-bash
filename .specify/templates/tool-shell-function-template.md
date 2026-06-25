# Tool Record: [TOOL NAME]

**Tool Name**: [TOOL NAME]  
**Tool Type**: `shell-function`  
**Source Identifier**: [FUNCTION NAME]  
**Tool ID**: [TOOL ID]  
**Aliases**: [comma-separated aliases, optional]  
**Status**: [Draft | Verified | Deprecated]  
**Discovery Origin**: [manual-entry | discovery-assisted | imported]  
**Last Updated**: [YYYY-MM-DD]

## Scope

**Availability**: Shell-session-level — available only after the function is loaded into the current shell context.  
**Typical Sources**: Predefined shell functions sourced via `source` or `.` from files like `~/.bashrc`, `~/.bash_profile`, `~/.zshrc`, or project-local `.envrc` / `activate` scripts.  
**Portability**: Tied to the shell session and its configuration; the function disappears when the session ends or when a new shell is started without sourcing the definition file. Availability depends on which dotfiles or activation scripts the user has sourced.  
**Source Identifier Convention**: The function name as it appears in the shell (e.g., `my_deploy_func`), discoverable via `compgen -A function` or `declare -F`.

## Description

[Short, user-friendly description of what this shell function does and when to use it]

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
- [Shell session requirements]
- [Variables modified by the function]

## Examples

### Example Input

```json
{
  "tool": "[TOOL NAME]",
  "io": {
    "input_channel": "command-line",
    "invocation_mode": "shell-environment",
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
- **Discovery Source**: current shell session (compgen -A function)
- **Verification Status**: [unverified | verified]
- **Notes**: [Any additional context]

Invoke shell function [TOOL NAME]
