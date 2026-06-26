# Browser Utils — GitHub Copilot Guide

## Tool Mapping

| Operation | Copilot Tool/Method |
|-----------|---------------------|
| Run Playwright script | `@terminal`: `cd <skill-path>/scripts/js && node run.js /tmp/playwright-test-*.js` |
| Take screenshot | `@terminal` to execute Playwright, then manually open the image file in VS Code |
| Auto-detect dev servers | `@terminal`: `node -e "require('./lib/helpers').detectDevServers()..."` |
| Write test scripts | Workspace edit to create scripts at `/tmp/playwright-test-*.js` |
| Install dependencies | `@terminal`: `cd <skill-path>/scripts/js && npm run setup` |

## Best Practices

- Prefer `headless: true` mode — Copilot runs in IDE context where visible browsers may not display properly
- Use `@terminal` for all shell commands; Copilot Chat cannot execute commands directly
- Keep Playwright scripts simple — Copilot has limited ability to debug complex async flows
- Save screenshots to a known location and tell the user to open them manually in VS Code

## Known Pitfalls

- **No background tasks**: Copilot cannot manage background processes. If a dev server needs to run, instruct the user to start it in a separate terminal first
- **Terminal output truncation**: Long `@terminal` output may be truncated in Copilot Chat. Use `| tail -50` for verbose commands
- **Path resolution**: `${SKILL_HOME}` must be resolved manually — Copilot does not have a `Read` tool equivalent that resolves symlinks. Use the full physical path
- **No screenshot viewing in chat**: Copilot Chat cannot display image files. Screenshots must be opened separately in the VS Code editor

## Capability Notes

- **Supported**: Script generation via workspace edit, terminal command execution, file creation
- **Limited**: No background task management; no direct image viewing in chat; terminal output may be truncated
- **Unsupported**: Visible browser mode in IDE context; real-time script debugging; parallel test execution
