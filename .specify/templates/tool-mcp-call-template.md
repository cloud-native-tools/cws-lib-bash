# Tool Record: [TOOL NAME]

**Tool Name**: [TOOL NAME]  
**Tool Type**: `mcp-call`  
**Source Identifier**: [MCP SERVER NAME]  
**Tool ID**: [TOOL ID]  
**Aliases**: [comma-separated aliases, optional]  
**Status**: [Draft | Verified | Deprecated]  
**Last Updated**: [YYYY-MM-DD]

## Description

[Short, user-friendly description of what this tool does and when to use it]

## Resource ID

- Canonical ID: `[RESOURCE ID]`
- Canonical Path: `[CANONICAL PATH]`

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
- [Rate limits, permission requirements, or error behavior]

## Examples

### Example Input

```json
{
  "tool": "[TOOL NAME]",
  "arguments": {
    "[param]": "value"
  }
}
```

### Example Output

```json
{
  "result": {
    "[field]": "value"
  }
}
```

## Discovery Metadata

- **Discovery Method**: [auto-discovery | manual-entry | imported]
- **Discovery Source**: [mcp server | local system | current shell | workspace scripts]
- **Verification Status**: [unverified | verified]
- **Notes**: [Any additional context]

使用[TOOL PARAMETERS]调用[TOOL NAME]工具
