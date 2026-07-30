# Browser Utils — Claude Code Guide

**Tier**: 3 (Playwright headless automation)

Claude Code does not have a built-in browser or `browser-use` MCP access by default.
Use the Playwright script execution path for all browser automation tasks.

## Tool Mapping

| Operation | Claude Code Tool/Method |
|-----------|------------------------|
| Run Playwright script | `Bash` tool: `cd ${SKILL_HOME}/scripts/js && node run.js /tmp/playwright-test-*.js` |
| Take screenshot | `Bash` tool to execute, then `Read` tool to view the screenshot image file |
| Auto-detect dev servers | `Bash` tool: `cd ${SKILL_HOME}/scripts/js && node -e "require('./lib/helpers').detectDevServers()..."` |
| Write test scripts | `Write` tool to create scripts at `/tmp/playwright-test-*.js` |
| Install dependencies | `Bash` tool: `cd ${SKILL_HOME}/scripts/js && npm run setup` |

## Best Practices

- Always use `headless: false` by default — Claude Code can render visible browser windows
- Write scripts to `/tmp/` exclusively; never write test files to the skill directory
- Use `Bash` tool with `timeout: 30000` for Playwright operations that may hang
- Use `run_in_background: true` for long-running server processes
- After taking screenshots, use `Read` tool on the image file to visually inspect results

## Known Pitfalls

- **Strategy selection**: Claude Code always falls to Tier 3. Do not attempt to use `browser-use` MCP tools unless the MCP server is explicitly configured
- **Run mode first**: Decide Mode 1 (clean test browser) vs Mode 2 (real Chrome profile) before writing a script (SKILL.md § Run Mode Selection). For Mode 2, use `AskUserQuestion` to confirm the profile when login state is ambiguous, and preflight the profile with `Bash` (`ps aux | grep user-data-dir=...`) — a running Chrome on the profile makes the launch hand off and exit
- **WebFetch vs Playwright**: `WebFetch` tool does NOT support `file://` URLs or JavaScript-rendered pages. Always use Playwright via `Bash` for local file testing
- **Timeout on slow renders**: Playwright `waitForSelector` may exceed the default Bash 2-minute timeout. Set explicit `timeout` parameter on the Bash call
- **Background server management**: When starting dev servers, use `run_in_background: true`. The server process must be stopped manually after testing
- **Screenshot paths**: Screenshots saved to absolute paths work; relative paths resolve against the Bash working directory, not the project root

## Capability Notes

- **Supported**: Full Playwright automation (Tier 3), visible browser mode, screenshot capture and visual inspection, background task management, parallel test execution via Agent tool
- **Limited**: Cannot interact with browser UI directly (no mouse/keyboard outside of Playwright scripts); large screenshot files may be slow to read; no `browser-use` MCP access
- **Unsupported**: Tier 1 (built-in browser); Tier 2 (MCP connector) unless explicitly configured; real-time browser streaming; clipboard access from within Playwright
