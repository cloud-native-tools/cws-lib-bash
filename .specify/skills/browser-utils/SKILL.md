---
name: browser-utils
description: |
  Browser automation and web application testing with Playwright.
  Supports both JavaScript (Node.js) and Python execution patterns.
  Auto-detects dev servers, manages server lifecycle, writes test scripts,
  takes screenshots, tests responsive design, validates UX, automates browser tasks.
  Use when the user mentions "browser", "Playwright", "web test", "screenshot",
  "automation", "responsive", "headless", "form fill", "login flow", "broken links",
  "浏览器", "网页测试", "截图", "自动化", "响应式测试", "表单填写",
  "UI测试", "端到端测试", "E2E测试"
skill_id: "<SKILL:.specify/skills/browser-utils/SKILL.md>"
---

# Browser Utilities

## Overview

General-purpose browser automation and web application testing skill powered by Playwright. This skill consolidates two complementary approaches:

- **JavaScript Automation** (via Node.js) -- Auto-detects dev servers, writes custom Playwright scripts to `/tmp`, executes via a universal runner (`run.js`). Best for quick automation, screenshots, responsive testing, login flows, form filling, link checking, and any ad-hoc browser task.
- **Python Testing** (via `sync_playwright`) -- Manages server lifecycle with `with_server.py`, supports multiple simultaneous servers, reconnaissance-then-action pattern. Best for structured testing of local web applications, capturing browser logs, and element discovery.

Both approaches share the same Chromium browser managed by Playwright.

## Decision Tree

```
User task --> Quick automation or screenshot?
    |-- Yes --> Use JavaScript Automation (see section below)
    '-- No --> Need server lifecycle management?
        |-- Yes --> Use Python Testing (see section below)
        '-- No --> Either works:
                   - JS for Node.js projects
                   - Python for Python projects
```

## Setup

### JavaScript Setup

```bash
cd ${SKILL_HOME}/scripts/js && npm run setup
```

This installs Playwright and Chromium browser. Only needed once.

### Python Setup

```bash
pip install playwright && playwright install chromium
```

## JavaScript Automation

General-purpose browser automation via Node.js. Write custom Playwright code for any automation task and execute it via the universal executor.

**CRITICAL WORKFLOW - Follow these steps in order:**

1. **Auto-detect dev servers** - For localhost testing, ALWAYS run server detection FIRST:

   ```bash
   cd ${SKILL_HOME}/scripts/js && node -e "require('./lib/helpers').detectDevServers().then(servers => console.log(JSON.stringify(servers)))"
   ```

   - If **1 server found**: Use it automatically, inform user
   - If **multiple servers found**: Ask user which one to test
   - If **no servers found**: Ask for URL or offer to help start dev server

2. **Write scripts to /tmp** - NEVER write test files to skill directory; always use `/tmp/playwright-test-*.js`

3. **Use visible browser by default** - Always use `headless: false` unless user specifically requests headless mode

4. **Parameterize URLs** - Always make URLs configurable via environment variable or constant at top of script

### How It Works

1. You describe what you want to test/automate
2. The skill auto-detects running dev servers (or asks for URL if testing external site)
3. Custom Playwright code is written in `/tmp/playwright-test-*.js` (won't clutter your project)
4. Executed via: `cd ${SKILL_HOME}/scripts/js && node run.js /tmp/playwright-test-*.js`
5. Results displayed in real-time, browser window visible for debugging
6. Test files auto-cleaned from /tmp by your OS

### Execution Pattern

**Step 1: Detect dev servers (for localhost testing)**

```bash
cd ${SKILL_HOME}/scripts/js && node -e "require('./lib/helpers').detectDevServers().then(s => console.log(JSON.stringify(s)))"
```

**Step 2: Write test script to /tmp with URL parameter**

```javascript
// /tmp/playwright-test-page.js
const { chromium } = require('playwright');

// Parameterized URL (detected or user-provided)
const TARGET_URL = 'http://localhost:3001'; // <-- Auto-detected or from user

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto(TARGET_URL);
  console.log('Page loaded:', await page.title());

  await page.screenshot({ path: '/tmp/screenshot.png', fullPage: true });
  console.log('Screenshot saved to /tmp/screenshot.png');

  await browser.close();
})();
```

**Step 3: Execute from skill directory**

```bash
cd ${SKILL_HOME}/scripts/js && node run.js /tmp/playwright-test-page.js
```

### Common JS Patterns

#### Test a Page (Multiple Viewports)

```javascript
// /tmp/playwright-test-responsive.js
const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:3001'; // Auto-detected

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 100 });
  const page = await browser.newPage();

  // Desktop test
  await page.setViewportSize({ width: 1920, height: 1080 });
  await page.goto(TARGET_URL);
  console.log('Desktop - Title:', await page.title());
  await page.screenshot({ path: '/tmp/desktop.png', fullPage: true });

  // Mobile test
  await page.setViewportSize({ width: 375, height: 667 });
  await page.screenshot({ path: '/tmp/mobile.png', fullPage: true });

  await browser.close();
})();
```

#### Test Login Flow

```javascript
// /tmp/playwright-test-login.js
const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:3001'; // Auto-detected

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto(`${TARGET_URL}/login`);

  await page.fill('input[name="email"]', 'test@example.com');
  await page.fill('input[name="password"]', 'password123');
  await page.click('button[type="submit"]');

  // Wait for redirect
  await page.waitForURL('**/dashboard');
  console.log('Login successful, redirected to dashboard');

  await browser.close();
})();
```

#### Fill and Submit Form

```javascript
// /tmp/playwright-test-form.js
const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:3001'; // Auto-detected

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 50 });
  const page = await browser.newPage();

  await page.goto(`${TARGET_URL}/contact`);

  await page.fill('input[name="name"]', 'John Doe');
  await page.fill('input[name="email"]', 'john@example.com');
  await page.fill('textarea[name="message"]', 'Test message');
  await page.click('button[type="submit"]');

  // Verify submission
  await page.waitForSelector('.success-message');
  console.log('Form submitted successfully');

  await browser.close();
})();
```

#### Check for Broken Links

```javascript
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto('http://localhost:3000');

  const links = await page.locator('a[href^="http"]').all();
  const results = { working: 0, broken: [] };

  for (const link of links) {
    const href = await link.getAttribute('href');
    try {
      const response = await page.request.head(href);
      if (response.ok()) {
        results.working++;
      } else {
        results.broken.push({ url: href, status: response.status() });
      }
    } catch (e) {
      results.broken.push({ url: href, error: e.message });
    }
  }

  console.log(`Working links: ${results.working}`);
  console.log(`Broken links:`, results.broken);

  await browser.close();
})();
```

#### Take Screenshot with Error Handling

```javascript
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    await page.goto('http://localhost:3000', {
      waitUntil: 'networkidle',
      timeout: 10000,
    });

    await page.screenshot({
      path: '/tmp/screenshot.png',
      fullPage: true,
    });

    console.log('Screenshot saved to /tmp/screenshot.png');
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();
```

#### Test Responsive Design

```javascript
// /tmp/playwright-test-responsive-full.js
const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:3001'; // Auto-detected

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  const viewports = [
    { name: 'Desktop', width: 1920, height: 1080 },
    { name: 'Tablet', width: 768, height: 1024 },
    { name: 'Mobile', width: 375, height: 667 },
  ];

  for (const viewport of viewports) {
    console.log(
      `Testing ${viewport.name} (${viewport.width}x${viewport.height})`,
    );

    await page.setViewportSize({
      width: viewport.width,
      height: viewport.height,
    });

    await page.goto(TARGET_URL);
    await page.waitForTimeout(1000);

    await page.screenshot({
      path: `/tmp/${viewport.name.toLowerCase()}.png`,
      fullPage: true,
    });
  }

  console.log('All viewports tested');
  await browser.close();
})();
```

### Inline Execution (Simple Tasks)

For quick one-off tasks, you can execute code inline without creating files:

```bash
# Take a quick screenshot
cd ${SKILL_HOME}/scripts/js && node run.js "
const browser = await chromium.launch({ headless: false });
const page = await browser.newPage();
await page.goto('http://localhost:3001');
await page.screenshot({ path: '/tmp/quick-screenshot.png', fullPage: true });
console.log('Screenshot saved');
await browser.close();
"
```

**When to use inline vs files:**

- **Inline**: Quick one-off tasks (screenshot, check if element exists, get page title)
- **Files**: Complex tests, responsive design checks, anything user might want to re-run

### Available Helpers

Optional utility functions in `${SKILL_HOME}/scripts/js/lib/helpers.js`:

```javascript
const helpers = require('./lib/helpers');

// Detect running dev servers (CRITICAL - use this first!)
const servers = await helpers.detectDevServers();
console.log('Found servers:', servers);

// Safe click with retry
await helpers.safeClick(page, 'button.submit', { retries: 3 });

// Safe type with clear
await helpers.safeType(page, '#username', 'testuser');

// Take timestamped screenshot
await helpers.takeScreenshot(page, 'test-result');

// Handle cookie banners
await helpers.handleCookieBanner(page);

// Extract table data
const data = await helpers.extractTableData(page, 'table.results');
```

See `${SKILL_HOME}/scripts/js/lib/helpers.js` for full list.

### Custom HTTP Headers

Configure custom headers for all HTTP requests via environment variables. Useful for:

- Identifying automated traffic to your backend
- Getting LLM-optimized responses (e.g., plain text errors instead of styled HTML)
- Adding authentication tokens globally

#### Single Header (Common Case)

```bash
PW_HEADER_NAME=X-Automated-By PW_HEADER_VALUE=playwright-skill \
  cd ${SKILL_HOME}/scripts/js && node run.js /tmp/my-script.js
```

#### Multiple Headers (JSON Format)

```bash
PW_EXTRA_HEADERS='{"X-Automated-By":"playwright-skill","X-Debug":"true"}' \
  cd ${SKILL_HOME}/scripts/js && node run.js /tmp/my-script.js
```

#### How It Works

Headers are automatically applied when using `helpers.createContext()`:

```javascript
const context = await helpers.createContext(browser);
const page = await context.newPage();
// All requests from this page include your custom headers
```

For scripts using raw Playwright API, use the injected `getContextOptionsWithHeaders()`:

```javascript
const context = await browser.newContext(
  getContextOptionsWithHeaders({ viewport: { width: 1920, height: 1080 } }),
);
```

### JS Tips

- **CRITICAL: Detect servers FIRST** - Always run `detectDevServers()` before writing test code for localhost testing
- **Custom headers** - Use `PW_HEADER_NAME`/`PW_HEADER_VALUE` env vars to identify automated traffic to your backend
- **Use /tmp for test files** - Write to `/tmp/playwright-test-*.js`, never to skill directory or user's project
- **Parameterize URLs** - Put detected/provided URL in a `TARGET_URL` constant at the top of every script
- **DEFAULT: Visible browser** - Always use `headless: false` unless user explicitly asks for headless mode
- **Headless mode** - Only use `headless: true` when user specifically requests "headless" or "background" execution
- **Slow down:** Use `slowMo: 100` to make actions visible and easier to follow
- **Wait strategies:** Use `waitForURL`, `waitForSelector`, `waitForLoadState` instead of fixed timeouts
- **Error handling:** Always use try-catch for robust automation
- **Console output:** Use `console.log()` to track progress and show what's happening

## Python Testing

Write native Python Playwright scripts to test local web applications.

**Helper Scripts Available**:
- `${SKILL_HOME}/scripts/python/with_server.py` - Manages server lifecycle (supports multiple servers)

**Always run scripts with `--help` first** to see usage. DO NOT read the source until you try running the script first and find that a customized solution is absolutely necessary. These scripts can be very large and thus pollute your context window. They exist to be called directly as black-box scripts rather than ingested into your context window.

### Decision Tree: Static vs Dynamic

```
User task --> Is it static HTML?
    |-- Yes --> Read HTML file directly to identify selectors
    |           |-- Success --> Write Playwright script using selectors
    |           '-- Fails/Incomplete --> Treat as dynamic (below)
    |
    '-- No (dynamic webapp) --> Is the server already running?
        |-- No --> Run: python ${SKILL_HOME}/scripts/python/with_server.py --help
        |          Then use the helper + write simplified Playwright script
        |
        '-- Yes --> Reconnaissance-then-action:
            1. Navigate and wait for networkidle
            2. Take screenshot or inspect DOM
            3. Identify selectors from rendered state
            4. Execute actions with discovered selectors
```

### Using with_server.py

To start a server, run `--help` first, then use the helper:

**Single server:**
```bash
python ${SKILL_HOME}/scripts/python/with_server.py --server "npm run dev" --port 5173 -- python your_automation.py
```

**Multiple servers (e.g., backend + frontend):**
```bash
python ${SKILL_HOME}/scripts/python/with_server.py \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python your_automation.py
```

To create an automation script, include only Playwright logic (servers are managed automatically):
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True) # Always launch chromium in headless mode
    page = browser.new_page()
    page.goto('http://localhost:5173') # Server already running and ready
    page.wait_for_load_state('networkidle') # CRITICAL: Wait for JS to execute
    # ... your automation logic
    browser.close()
```

### Reconnaissance-Then-Action Pattern

1. **Inspect rendered DOM**:
   ```python
   page.screenshot(path='/tmp/inspect.png', full_page=True)
   content = page.content()
   page.locator('button').all()
   ```

2. **Identify selectors** from inspection results

3. **Execute actions** using discovered selectors

### Common Pitfalls

- **Don't** inspect the DOM before waiting for `networkidle` on dynamic apps
- **Do** wait for `page.wait_for_load_state('networkidle')` before inspection

### Python Best Practices

- **Use bundled scripts as black boxes** - To accomplish a task, consider whether one of the scripts available in `${SKILL_HOME}/scripts/python/` can help. These scripts handle common, complex workflows reliably without cluttering the context window. Use `--help` to see usage, then invoke directly.
- Use `sync_playwright()` for synchronous scripts
- Always close the browser when done
- Use descriptive selectors: `text=`, `role=`, CSS selectors, or IDs
- Add appropriate waits: `page.wait_for_selector()` or `page.wait_for_timeout()`

### Python Examples

Reference examples in `${SKILL_HOME}/examples/`:

- `element_discovery.py` - Discovering buttons, links, and inputs on a page
- `static_html_automation.py` - Using file:// URLs for local HTML
- `console_logging.py` - Capturing console logs during automation

## Common Patterns

Cross-language patterns applicable to both JavaScript and Python approaches.

### Taking Screenshots

**JavaScript:**
```javascript
await page.screenshot({ path: '/tmp/screenshot.png', fullPage: true });
// Element screenshot
await page.locator('.chart').screenshot({ path: '/tmp/chart.png' });
```

**Python:**
```python
page.screenshot(path='/tmp/screenshot.png', full_page=True)
# Element screenshot
page.locator('.chart').screenshot(path='/tmp/chart.png')
```

### Responsive Design Testing

**JavaScript:**
```javascript
const viewports = [
  { name: 'Desktop', width: 1920, height: 1080 },
  { name: 'Tablet', width: 768, height: 1024 },
  { name: 'Mobile', width: 375, height: 667 },
];

for (const vp of viewports) {
  await page.setViewportSize({ width: vp.width, height: vp.height });
  await page.goto(TARGET_URL);
  await page.screenshot({ path: `/tmp/${vp.name.toLowerCase()}.png`, fullPage: true });
}
```

**Python:**
```python
viewports = [
    ('desktop', 1920, 1080),
    ('tablet', 768, 1024),
    ('mobile', 375, 667),
]

for name, w, h in viewports:
    page.set_viewport_size({'width': w, 'height': h})
    page.goto(target_url)
    page.screenshot(path=f'/tmp/{name}.png', full_page=True)
```

### Form Filling and Submission

**JavaScript:**
```javascript
await page.fill('input[name="name"]', 'John Doe');
await page.fill('input[name="email"]', 'john@example.com');
await page.fill('textarea[name="message"]', 'Test message');
await page.click('button[type="submit"]');
await page.waitForSelector('.success-message');
```

**Python:**
```python
page.fill('input[name="name"]', 'John Doe')
page.fill('input[name="email"]', 'john@example.com')
page.fill('textarea[name="message"]', 'Test message')
page.click('button[type="submit"]')
page.wait_for_selector('.success-message')
```

### Error Handling

**JavaScript:**
```javascript
try {
  await page.goto(url, { waitUntil: 'networkidle', timeout: 10000 });
  // ... automation logic
} catch (error) {
  console.error('Error:', error.message);
  await page.screenshot({ path: '/tmp/error-screenshot.png' });
} finally {
  await browser.close();
}
```

**Python:**
```python
try:
    page.goto(url, wait_until='networkidle', timeout=10000)
    # ... automation logic
except Exception as e:
    print(f'Error: {e}')
    page.screenshot(path='/tmp/error-screenshot.png')
finally:
    browser.close()
```

## Advanced Usage

For comprehensive Playwright API documentation, see `${SKILL_HOME}/references/playwright-api.md`:

- Selectors & Locators best practices
- Network interception & API mocking
- Authentication & session management
- Visual regression testing
- Mobile device emulation
- Performance testing
- Debugging techniques
- CI/CD integration
- Page Object Model patterns
- Data-driven testing
- Accessibility testing

## Troubleshooting

### JavaScript Issues

**Playwright not installed:**
```bash
cd ${SKILL_HOME}/scripts/js && npm run setup
```

**Module not found:**
Ensure running from skill directory via `run.js` wrapper.

**Browser doesn't open:**
Check `headless: false` and ensure display is available.

**Element not found:**
Add wait: `await page.waitForSelector('.element', { timeout: 10000 })`

### Python Issues

**Playwright not installed:**
```bash
pip install playwright && playwright install chromium
```

**Server not starting:**
Check port availability and increase timeout:
```bash
python ${SKILL_HOME}/scripts/python/with_server.py --server "npm run dev" --port 5173 --timeout 60 -- python test.py
```

**DOM not ready:**
Always wait for `networkidle` before inspecting dynamic apps:
```python
page.wait_for_load_state('networkidle')
```

### General Issues

**Chromium not found:**
```bash
playwright install chromium
```

**Timeout errors:**
Increase timeout values, check network conditions, verify the target URL is reachable.

**Flaky results:**
Use proper waiting strategies (`waitForSelector`, `waitForURL`, `waitForLoadState`) instead of fixed timeouts (`waitForTimeout`).

## Path Conventions

This Skill follows the canonical path conventions:

- Use `${SKILL_HOME}/<relative-path>` for every Skill-owned resource reference.
- Use `${SKILL_WORKDIR}/<relative-path>` for every runtime/user-facing path.
- Never embed agent-specific install paths.

## Resources

| Directory | Contents |
|-----------|----------|
| `${SKILL_HOME}/scripts/js/` | `run.js` universal executor, `package.json`, `lib/helpers.js` |
| `${SKILL_HOME}/scripts/python/` | `with_server.py` server lifecycle manager |
| `${SKILL_HOME}/references/` | `playwright-api.md` comprehensive API reference |
| `${SKILL_HOME}/examples/` | Python example scripts (element discovery, static HTML, console logging) |

## Dependencies

- **JavaScript path**: Node.js (>=14.0.0), Playwright npm package (`^1.57.0`), Chromium browser
- **Python path**: Python (>=3.8), `playwright` Python package, Chromium browser
- **Shared**: Chromium browser (installed via `playwright install chromium`)

## Agent-Specific Configuration

### Step 1: Identify Executing Agent

Before executing this skill's workflow, identify which AI agent you are:

| Agent | Detection Signals |
|-------|-------------------|
| **Claude Code** | System prompt contains "Claude Code"; tools include `Agent`, `Edit`, `Bash`, `Read`; `.claude/` directory exists |
| **GitHub Copilot** | Running in VS Code Copilot Chat context; `.github/copilot-instructions.md` loaded; tools include `workspace edit`, `@terminal` |
| **Qoder CLI** | `.qoder/` directory exists; `QODER.md` instructions loaded |
| **opencode** | `.opencode/` directory exists |
| **Qwen Code** | `QWEN.md` instructions loaded; `.qwen/` directory exists |
| **Codex CLI** | `.codex/` directory exists |
| **Hermes Agent** | `.hermes/` directory exists |
| **iFlow** | `.iflow/` directory exists |

If you cannot identify your agent, skip Step 2 and proceed with the standard workflow.

### Step 2: Load Agent-Specific Guidance

If you identified your agent in Step 1, check if a guide exists at:

```
${SKILL_HOME}/references/<agent-slug>-guide.md
```

Where `<agent-slug>` is: `claude-code`, `copilot`, `qoder`, `opencode`, `qwen`, `codex`, `hermes`, or `iflow`.

If the guide exists, read it and apply the agent-specific tool mappings, best practices, and pitfall avoidances during execution. If no guide exists for your agent, proceed with the standard workflow.

### Step 3: Capture Execution Feedback

If you encounter an agent-specific obstacle during execution (e.g., a tool call is unavailable, output format doesn't match expectations, a workaround was needed), generate a feedback document at:

```
.specify/memory/feedback/browser-utils-<agent-slug>-<YYYY-MM-DDTHH-MM-SS>.md
```

The feedback document MUST contain:

```markdown
# Agent Execution Feedback

**Source**: browser-utils
**Agent**: <agent-slug>
**Timestamp**: <ISO-8601>
**Outcome**: <success-with-workaround | partial-failure | full-failure>

## Obstacle
[Description of the agent-specific issue encountered]

## Workaround Applied
[What was done to work around the issue, if anything]

## Suggested Improvement
[Specific change to the skill or reference document that would prevent this issue]
```

Only generate feedback when a genuine agent-specific obstacle was encountered.
