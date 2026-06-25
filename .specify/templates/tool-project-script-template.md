# Tool Record: [TOOL NAME]

**Tool Name**: [TOOL NAME]  
**Tool Type**: `project-script`  
**Source Identifier**: [SCRIPT PATH RELATIVE TO PROJECT ROOT]  
**Tool ID**: [TOOL ID]  
**Aliases**: [comma-separated aliases, optional]  
**Status**: [Draft | Verified | Deprecated]  
**Discovery Origin**: [manual-entry | discovery-assisted | imported]  
**Last Updated**: [YYYY-MM-DD]

## Scope

**Availability**: Project-level — available only within the current project workspace.  
**Typical Sources**: Scripts bundled with the project (e.g., `scripts/bash/*.sh`, `scripts/python/*.py`, `.specify/scripts/`).  
**Portability**: Tied to the project repository; not available outside the project root. Moving to a different machine requires cloning or copying the project.  
**Source Identifier Convention**: Path relative to the project root (e.g., `scripts/bash/build-docs.sh`).

## Description

[Short, user-friendly description of what this script does and when to use it]

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
- [Environment variables required]
- [Runtime dependencies]

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
- **Discovery Source**: workspace scripts directory
- **Verification Status**: [unverified | verified]
- **Notes**: [Any additional context]

Execute project script [TOOL NAME] with selected parameters
