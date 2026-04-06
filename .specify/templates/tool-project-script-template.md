# Tool Record: [TOOL NAME]

**Tool Name**: [TOOL NAME]  
**Tool Type**: `project-script`  
**Source Identifier**: [SCRIPT PATH RELATIVE TO PROJECT ROOT]  
**Tool ID**: [TOOL ID]  
**Aliases**: [comma-separated aliases, optional]  
**Status**: [Draft | Verified | Deprecated]  
**Last Updated**: [YYYY-MM-DD]

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

## Discovery Metadata

- **Discovery Method**: [auto-discovery | manual-entry | imported]
- **Discovery Source**: workspace scripts directory
- **Verification Status**: [unverified | verified]
- **Notes**: [Any additional context]

使用所选参数执行项目脚本 [TOOL NAME]
