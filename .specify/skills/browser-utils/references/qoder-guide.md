# Browser Utils — Qoder Guide

**Tier**: 2 (MCP Connector + Chrome Extension) or Tier 3 (Playwright)

Qoder IDE has access to the `browser-use` MCP server, enabling Tier 2 browser
automation. When the MCP server is available, prefer Tier 2 over Tier 3.

## Strategy Selection

1. **Check for `browser-use` MCP tools**: If `navigate_page`, `take_snapshot`, `click`, etc. are available in the tool list → **use Tier 2**
2. **Fallback to Tier 3**: If MCP tools are unavailable → use Playwright via Bash

## Tier 2: MCP Browser-Use (Preferred)

### Tool Mapping

| Operation | MCP Tool |
|-----------|----------|
| Navigate to URL | `navigate_page` with `url` and `type="url"` |
| Get page structure | `take_snapshot` (returns a11y tree with element uids) |
| Click element | `click` with `uid` from snapshot |
| Fill input | `fill` with `uid` and `value` |
| Press key | `press_key` with `key` (e.g. "Enter") |
| Screenshot | `take_screenshot` with `filePath` and `fullPage` |
| Wait for content | `wait_for` with `text` and `timeout` |
| Execute JS | `evaluate_script` with `function` (JS function body) |
| List tabs | `list_pages` |
| Switch tab | `select_page` |

### Best Practices

- Always `take_snapshot` before acting — uids are ephemeral and change after page updates
- Use `wait_for` for dynamic content instead of guessing timing
- Save screenshots to `/tmp/` for debugging
- Use `evaluate_script` for bulk data extraction (faster than multiple click/fill operations)

### Workflow Example

```
# 1. Navigate
navigate_page(url="https://example.com")

# 2. Snapshot to find elements
take_snapshot()

# 3. Act on element by uid
click(uid="<button-uid>")

# 4. Verify
take_screenshot(filePath="/tmp/result.png", fullPage=true)
```

For the complete tool reference, see [mcp-browser-tools.md](./mcp-browser-tools.md).

## Tier 3: Playwright (Fallback)

When MCP tools are unavailable, use Playwright via Bash:

```bash
cd ${SKILL_HOME}/scripts/js && node run.js /tmp/playwright-test-*.js
```

Follow the standard Tier 3 workflow from [SKILL.md](../SKILL.md).

## Known Pitfalls

- **MCP server not started**: If `browser-use` tools are not in the tool list, the MCP server may not be running. Fall back to Tier 3
- **Chrome not running**: Tier 2 requires Chrome with the browser-use extension to be running on the desktop
- **Stale uids**: After any page-changing action (navigation, modal open), take a new snapshot before the next action
- **Large snapshots**: Complex pages may produce very large snapshot text; use `evaluate_script` with targeted queries

## Capability Notes

- **Supported (Tier 2)**: MCP browser-use tools, real Chrome browser operation, a11y tree snapshots, screenshot capture, JS evaluation, multi-tab management
- **Supported (Tier 3)**: Full Playwright automation as fallback
- **Limited**: MCP session persistence depends on Chrome profile configuration; large page snapshots may consume context window
- **Unsupported**: Tier 1 (built-in browser) — Qoder does not embed a browser component
