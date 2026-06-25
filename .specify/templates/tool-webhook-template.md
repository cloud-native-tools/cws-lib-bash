# Tool Record: [TOOL NAME]

**Tool Name**: [TOOL NAME]  
**Tool Type**: `webhook`  
**Source Identifier**: [WEBHOOK URL ENDPOINT]  
**Tool ID**: [TOOL ID]  
**Aliases**: [comma-separated aliases, optional]  
**Status**: [Draft | Verified | Deprecated]  
**Discovery Origin**: [manual-entry | discovery-assisted | imported]  
**Last Updated**: [YYYY-MM-DD]

## Scope

**Availability**: Network-level — available wherever HTTP connectivity to the target server exists.  
**Typical Sources**: HTTP endpoints exposed by CI/CD systems, internal automation platforms, SaaS integrations, or custom web services. Invoked by sending an HTTP request (typically POST) to a URL endpoint.  
**Portability**: Not tied to a specific machine, project, or shell session. Accessibility depends on network reachability (firewall, VPN), endpoint availability (server uptime), and authentication credentials. The same webhook can be invoked from any environment that has network access and valid credentials.  
**Source Identifier Convention**: The full URL of the webhook endpoint (e.g., `https://ci.example.com/api/trigger-build`).

## Description

[Short, user-friendly description of what this webhook does and when to use it]

## Resource ID

- Canonical ID: `[RESOURCE ID]`
- Canonical Path: `[CANONICAL PATH]`

## Invocation & I/O Contract

- **HTTP Method**: `[GET | POST | PUT | DELETE]`
- **Content-Type**: `[application/json | application/x-www-form-urlencoded | text/plain]`
- **Auth Method**: `[none | bearer | basic | header-key]`
- **Auth Header/Key Name**: `[e.g., Authorization, X-API-Key]`
- **Input Channel**: `http-request`
- **Invocation Mode**: `http`
- **Output Mode**: `[json | plain-log-lines]`
- **Timeout**: `[timeout in seconds, e.g., 30]`

## Parameters

| Name | Type | Required | Location | Description | Default |
|------|------|----------|----------|-------------|---------|
| [param] | [type] | [yes/no] | [body/query/header/path] | [purpose] | [default or empty] |

## Returns

| Name | Type | Description |
|------|------|-------------|
| [field] | [type] | [meaning of return field] |

## Usage Notes

- [Authentication requirements — what credentials are needed and how to provide them]
- [Network prerequisites — VPN, firewall rules, DNS resolution]
- [Rate limiting — request frequency constraints imposed by the server]
- [Idempotency — whether repeated calls produce the same result or trigger duplicate operations]
- [SSL/TLS — certificate verification requirements]
- [Timeout behavior — what happens when the server does not respond within the timeout period]

## Examples

### Example Input

```json
{
  "tool": "[TOOL NAME]",
  "io": {
    "http_method": "POST",
    "content_type": "application/json",
    "auth_method": "bearer",
    "input_channel": "http-request",
    "invocation_mode": "http",
    "output_mode": "json",
    "timeout": 30
  },
  "url": "[WEBHOOK URL]",
  "headers": {
    "Authorization": "Bearer [TOKEN]"
  },
  "body": {
    "[param]": "value"
  }
}
```

### Example Output

```json
{
  "output_mode": "json",
  "status_code": 200,
  "result": {
    "[field]": "value"
  }
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
- **Discovery Source**: manual configuration
- **Verification Status**: [unverified | verified]
- **Notes**: [Any additional context]

Invoke webhook [TOOL NAME] via HTTP request
