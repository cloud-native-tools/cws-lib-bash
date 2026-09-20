# Browser Utils — Qoder Guide

**Tier**: 2 (Playwright) or Tier 3 (MCP Connector + Chrome Extension)

Qoder IDE has access to the `browser-use` MCP server, enabling Tier 3 browser
automation. Tier 2 (Playwright) is the default path; use Tier 3 when the task
needs the user's real desktop Chrome (existing login state, extensions).

## Strategy Selection

1. **Default to Tier 2**: Use Playwright via Bash for general automation and testing
2. **Use Tier 3 when real desktop Chrome is needed**: If `navigate_page`, `take_snapshot`, `click`, etc. are available in the tool list and the task needs the user's actual browser profile → **use Tier 3**

## Tier 2: Playwright (Default)

```bash
cd ${SKILL_HOME}/scripts/js && node run.js /tmp/playwright-test-*.js
```

Follow the standard Tier 2 workflow from [SKILL.md](../SKILL.md). Launch focus-safe: resolve the
rung with `${SKILL_HOME}/scripts/focus-safe-launch.py` first — F0 (headless) is the default, so a
run never takes focus away from the user's own work. Ladder owner:
[focus-safe-launch.md](./focus-safe-launch.md).

## Tier 3: MCP Browser-Use

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

## Known Pitfalls

- **Tier 3 takes over the user's live Chrome**: `navigate_page` / `select_page` change the user's own tabs and bring that window forward — this path cannot be made focus-safe, because reusing the real session is its whole purpose. Announce that the run will take over their live browser **before** the first navigation, and prefer Tier 2 / F0 unless the task genuinely needs the user's session or extensions ([focus-safe-launch.md](./focus-safe-launch.md) § Tier 3)
- **MCP server not started**: If `browser-use` tools are not in the tool list, the MCP server may not be running. Fall back to Tier 2
- **Chrome not running**: Tier 3 requires Chrome with the browser-use extension to be running on the desktop
- **Stale uids**: After any page-changing action (navigation, modal open), take a new snapshot before the next action
- **Large snapshots**: Complex pages may produce very large snapshot text; use `evaluate_script` with targeted queries

## Capability Notes

- **Supported (Tier 2)**: Full Playwright automation as the default path
- **Supported (Tier 3)**: MCP browser-use tools, real Chrome browser operation, a11y tree snapshots, screenshot capture, JS evaluation, multi-tab management
- **Limited**: MCP session persistence depends on Chrome profile configuration; large page snapshots may consume context window
- **Unsupported**: Tier 1 (built-in browser) — Qoder does not embed a browser component
