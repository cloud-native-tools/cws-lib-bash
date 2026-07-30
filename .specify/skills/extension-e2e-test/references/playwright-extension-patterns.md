# Playwright Chrome Extension Testing Patterns

Complete code patterns for testing each Chrome extension surface with Playwright.
All patterns assume the extension is loaded via `launchPersistentContext` with
`--load-extension` (see SKILL.md Step 3).

## Table of Contents

1. [Extension Launch & Teardown](#1-extension-launch--teardown)
2. [Service Worker Testing](#2-service-worker-testing)
3. [Popup Page Testing](#3-popup-page-testing)
4. [Options Page Testing](#4-options-page-testing)
5. [Content Script Testing](#5-content-script-testing)
6. [Keyboard Command Testing](#6-keyboard-command-testing)
7. [Chrome Storage Testing](#7-chrome-storage-testing)
8. [Multi-Tab Testing](#8-multi-tab-testing)
9. [CDP Session — bringToFront](#9-cdp-session--bringtofront)
10. [Login State Reuse](#10-login-state-reuse)
11. [Network Mocking (Read-only Safety)](#11-network-mocking-read-only-safety)
12. [Prerequisite Service Checks](#12-prerequisite-service-checks)
13. [Focus-Free Extension Testing](#13-focus-free-extension-testing)
14. [On-Demand Script Injection Verification](#14-on-demand-script-injection-verification)
15. [Network Request Tracking](#15-network-request-tracking)

---

## 1. Extension Launch & Teardown

Base pattern for every test — launches Chrome for Testing with the extension loaded.

```javascript
const { chromium } = require('playwright');
const path = require('path');

const EXTENSION_PATH = path.resolve(__dirname, '../../dist');  // or absolute path
const USER_DATA_DIR = '/tmp/extension-e2e-profile';

let context;

async function launchExtension() {
  context = await chromium.launchPersistentContext(USER_DATA_DIR, {
    channel: 'chromium',     // Chrome for Testing — supports --load-extension
    headless: false,         // Extensions require headed mode
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`,
    ],
  });
  return context;
}

async function getExtensionId(context) {
  let [serviceWorker] = context.serviceWorkers();
  if (!serviceWorker) {
    serviceWorker = await context.waitForEvent('serviceworker', { timeout: 10000 });
  }
  // Service worker URL format: chrome-extension://<id>/background.js
  return serviceWorker.url().split('/')[2];
}

async function teardown() {
  if (context) {
    await context.close();
    context = null;
  }
}

// Usage:
(async () => {
  try {
    const ctx = await launchExtension();
    const extensionId = await getExtensionId(ctx);
    console.log('Extension ID:', extensionId);
    // ... run tests ...
  } finally {
    await teardown();
  }
})();
```

---

## 2. Service Worker Testing

The MV3 service worker is the extension's background script. Playwright provides
direct access via `context.serviceWorkers()`.

```javascript
async function testServiceWorker(context) {
  let [sw] = context.serviceWorkers();
  if (!sw) {
    sw = await context.waitForEvent('serviceworker', { timeout: 10000 });
  }

  // Evaluate code inside the service worker context
  const manifest = await sw.evaluate(async () => {
    // Access chrome.runtime APIs inside the service worker
    const manifest = chrome.runtime.getManifest();
    return {
      name: manifest.name,
      version: manifest.version,
      manifestVersion: manifest.manifest_version,
      permissions: manifest.permissions,
    };
  });
  console.log('Manifest:', JSON.stringify(manifest, null, 2));

  // Send a message to the service worker
  const response = await sw.evaluate(async () => {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: 'PING' }, (response) => {
        resolve(response);
      });
    });
  });
  console.log('Service worker response:', response);

  // MV3 service workers suspend after ~30s of inactivity.
  // Playwright automatically handles this — the same Worker object
  // stays valid across suspend/restart cycles.
  // Just issue new evaluate() calls; they will wait for restart if needed.
}
```

---

## 3. Popup Page Testing

The popup page runs as an extension page. Navigate to it directly via its
`chrome-extension://` URL.

```javascript
async function testPopup(context, extensionId) {
  const popupPage = await context.newPage();
  await popupPage.goto(`chrome-extension://${extensionId}/popup.html`, {
    waitUntil: 'load',
  });

  // Read popup title
  const title = await popupPage.title();
  console.log('Popup title:', title);

  // Read popup content
  const bodyText = await popupPage.locator('body').innerText();

  // Find and interact with UI elements
  // Example: find a button by text and click it
  const buttons = popupPage.locator('button');
  const count = await buttons.count();
  console.log(`Found ${count} buttons in popup`);

  // Click a specific button
  // await popupPage.click('button:has-text("配置")');

  // Fill form inputs
  // await popupPage.fill('input[name="region"]', 'oss-cn-hangzhou');

  // Take a screenshot for debugging
  await popupPage.screenshot({ path: '/tmp/extension-popup-screenshot.png' });

  await popupPage.close();
}
```

---

## 4. Options Page Testing

The options page is a standard extension page. Same approach as popup.

```javascript
async function testOptionsPage(context, extensionId) {
  const optionsPage = await context.newPage();
  await optionsPage.goto(`chrome-extension://${extensionId}/options.html`, {
    waitUntil: 'load',
  });

  // Read options page content
  const title = await optionsPage.title();
  console.log('Options title:', title);

  // Test form interactions
  // Example: fill OSS configuration fields
  // await optionsPage.fill('input#region', 'oss-cn-hangzhou');
  // await optionsPage.fill('input#bucket', 'test-bucket');
  // await optionsPage.fill('input#stsUrl', 'https://sts.example.com');
  // await optionsPage.click('button:has-text("Save")');

  // Verify saved values
  // const savedRegion = await optionsPage.inputValue('input#region');
  // assert(savedRegion === 'oss-cn-hangzhou');

  await optionsPage.screenshot({ path: '/tmp/extension-options-screenshot.png' });
  await optionsPage.close();
}
```

---

## 5. Content Script Testing

Content scripts are injected into web pages matching `manifest.json`'s
`content_scripts.matches` pattern. Navigate to a matching URL to trigger injection.

> **This project**: only `static/js/main.js` and `static/js/clipper.js` are declared
> content scripts (auto-injected on `<all_urls>` at `document_end`). The per-platform
> scripts (`asiops/aone/qianzhou/cc/work/splc`) are **injected on demand** by the
> service worker via `chrome.scripting` when a command fires — navigating to a platform
> URL will **not** inject them. To test those, drive the command path (§6).

```javascript
async function testContentScript(context, targetUrl) {
  const page = await context.newPage();
  await page.goto(targetUrl, { waitUntil: 'load', timeout: 30000 });

  // Content scripts execute in an isolated world.
  // To verify injection, check for side effects on the page DOM.
  // For example, if the content script adds a floating button:
  // const injectedButton = await page.locator('#xuanji-float-btn').count();
  // if (injectedButton > 0) {
  //   console.log('Content script injected successfully');
  // }

  // Or check for global variables set by the content script
  // Note: content scripts run in isolated world, so page.evaluate()
  // cannot directly access their variables. Look for DOM side effects instead.

  // Listen for console messages from the content script
  page.on('console', (msg) => {
    if (msg.type() === 'log') {
      console.log('[content script console]:', msg.text());
    }
  });

  // Take a screenshot to verify visual state
  await page.screenshot({ path: '/tmp/extension-content-script.png' });

  await page.close();
}
```

---

## 6. Keyboard Command Testing

> ⚠️ **Synthetic key presses do NOT trigger `chrome.commands.onCommand`.**
> The extension's shortcuts (`fetch_asiops_data`=Ctrl+Shift+F,
> `clip_handle_selection`=Ctrl+Shift+S, `fetch_splc_data`=Ctrl+Shift+L) are
> **browser-level** bindings. `page.keyboard.press('Control+Shift+F')` reaches the
> page, not the browser command dispatcher, so it will **not** fire the handler.
> This is a known limitation — see `docs/testing/e2e-browser-testing-research.md` §5.1.

Use one of the equivalent trigger paths below instead.

### 6a. Invoke the command handler in the service worker (recommended)

The service worker's `chrome.commands.onCommand` listener does the real work: it
injects the platform script and then `chrome.tabs.sendMessage`s the active tab with a
`WindowMessageType`. Invoke that listener directly to cover the shortcut branch without
relying on synthetic keys.

```javascript
async function triggerCommand(context, command) {
  // command ∈ 'fetch_asiops_data' | 'clip_handle_selection' | 'fetch_splc_data'
  let [sw] = context.serviceWorkers();
  if (!sw) sw = await context.waitForEvent('serviceworker', { timeout: 10000 });

  // Make sure the target tab is the active one — the handler queries
  // chrome.tabs.query({ active: true, currentWindow: true }).
  await sw.evaluate((cmd) => {
    // chrome.commands.onCommand cannot be dispatched programmatically, but the
    // background registers its listener as `command_listener`; call it directly.
    // Fallback: if not exposed, replay the message the handler would send.
    return globalThis.command_listener
      ? globalThis.command_listener(cmd)
      : Promise.reject(new Error('command_listener not exposed on globalThis'));
  }, command);

  console.log(`Dispatched command: ${command}`);
}
```

> If `command_listener` is not on `globalThis`, either expose it from
> `src/service/background.ts` for testability, or use the message-replay path (6b).

### 6b. Replay the equivalent message to the content script

The handler ultimately sends `chrome.tabs.sendMessage(tabId, { type, attachment })`.
You can replay that exact message from the service worker against the active tab:

```javascript
async function replayCommandMessage(context, page) {
  let [sw] = context.serviceWorkers();
  if (!sw) sw = await context.waitForEvent('serviceworker', { timeout: 10000 });
  await page.bringToFront(); // ensure it is the active tab the handler would target

  await sw.evaluate(async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    // WindowMessageType values (from src/common/message.ts). Include the attachment
    // shape the real handler builds (e.g. { ossConfig, fetchTypes } for asiops).
    await chrome.tabs.sendMessage(tab.id, {
      type: 'FETCH_ASIOPS_DATA',
      attachment: { /* ossConfig, fetchTypes — mock or real */ },
    });
  });
}
```

### 6c. Trigger via the popup UI (closest to a real user)

If the popup exposes equivalent buttons, clicking them drives the same
`WindowMessageType` message chain and is the most faithful E2E path:

```javascript
// await popupPage.click('button:has-text("获取数据")');
```

---

## 7. Chrome Storage Testing

Test `chrome.storage` API through the popup or options page context, which has
access to the extension's storage.

```javascript
async function testChromeStorage(context, extensionId) {
  const page = await context.newPage();
  await page.goto(`chrome-extension://${extensionId}/popup.html`, {
    waitUntil: 'load',
  });

  // Read from chrome.storage.local
  const storageData = await page.evaluate(async () => {
    return new Promise((resolve) => {
      chrome.storage.local.get(null, (items) => {
        resolve(items);
      });
    });
  });
  console.log('Current storage:', JSON.stringify(storageData, null, 2));

  // Write to chrome.storage.local
  await page.evaluate(async () => {
    return new Promise((resolve) => {
      chrome.storage.local.set({
        'test-key': 'test-value',
        'test-config': { region: 'oss-cn-hangzhou', bucket: 'test' },
      }, () => {
        resolve(true);
      });
    });
  });

  // Verify the write
  const value = await page.evaluate(async () => {
    return new Promise((resolve) => {
      chrome.storage.local.get('test-key', (items) => {
        resolve(items['test-key']);
      });
    });
  });
  console.log('Verified storage value:', value);

  // Clean up test data
  await page.evaluate(async () => {
    return new Promise((resolve) => {
      chrome.storage.local.remove(['test-key', 'test-config'], () => {
        resolve(true);
      });
    });
  });

  await page.close();
}
```

---

## 8. Multi-Tab Testing

Test that the extension works independently across multiple tabs.

```javascript
async function testMultiTab(context) {
  const page1 = await context.newPage();
  await page1.goto('https://example.com', { waitUntil: 'load' });

  const page2 = await context.newPage();
  await page2.goto('https://example.org', { waitUntil: 'load' });

  // Verify extension is active on both tabs
  // (Check for content script side effects on each page)

  // Switch between tabs using bringToFront (see CDP pattern below)
  await page1.bringToFront();
  console.log('Page 1 is now active');

  await page2.bringToFront();
  console.log('Page 2 is now active');

  await page1.close();
  await page2.close();
}
```

---

## 9. CDP Session — bringToFront

For finer control over tab switching, use Chrome DevTools Protocol (CDP).

```javascript
async function bringPageToFront(page) {
  const client = await page.context().newCDPSession(page);
  await client.send('Page.bringToFront');
  await client.detach();
}

// Usage: needed when popup interaction must target the content page's tab
// e.g., set timer in popup -> verify timer appears on content page
async function testPopupContentInteraction(context, extensionId) {
  // 1. Open content page
  const contentPage = await context.newPage();
  await contentPage.goto('https://example.com', { waitUntil: 'load' });

  // 2. Open popup in a new tab
  const popupPage = await context.newPage();
  await popupPage.goto(`chrome-extension://${extensionId}/popup.html`);

  // 3. Bring content page to front (so popup messages target it)
  await bringPageToFront(contentPage);

  // 4. Trigger action in popup
  // await popupPage.click('button:has-text("获取数据")');

  // 5. Verify result on content page
  // await contentPage.waitForSelector('.xuanji-result', { timeout: 10000 });

  await popupPage.close();
  await contentPage.close();
}
```

---

## 10. Login State Reuse

Reuse an existing Chrome profile with login state for testing against
authenticated internal platforms.

```javascript
const path = require('path');

async function launchWithLoginState() {
  // Use existing profile with login state
  // WARNING: This will load the extension alongside existing profile extensions.
  // Use --disable-extensions-except to isolate.
  const userDataDir = '/Users/<user>/data/chrome/agent';  // existing profile
  const extensionPath = path.resolve(__dirname, '../../dist');

  const context = await chromium.launchPersistentContext(userDataDir, {
    channel: 'chromium',
    headless: false,
    args: [
      `--disable-extensions-except=${extensionPath}`,
      `--load-extension=${extensionPath}`,
    ],
  });

  // The context now has:
  // - Login cookies for *.alibaba-inc.com (from existing profile)
  // - The extension loaded (from --load-extension)

  return context;
}

// Navigate to authenticated platform
async function testAuthenticatedPlatform(context) {
  const page = await context.newPage();
  await page.goto('https://asiops.alibaba-inc.com/', { waitUntil: 'load' });

  // Verify login state
  const title = await page.title();
  console.log('Platform title:', title);
  // If title contains login prompt, login state was not preserved

  await page.close();
}
```

---

## 11. Network Mocking (Read-only Safety)

Per the project Constitution the extension is **read-only** toward internal platforms
and writes **only** to OSS. A real E2E collection sends live GET requests to
`*.alibaba-inc.com` and may write to OSS. Mock these at the context level so tests are
offline, deterministic, and never touch real storage. Reuse the fixtures under
`test/data/` (`asiops/`, `splc/`, `qianzhou/`).

```javascript
const fs = require('fs');
const path = require('path');

async function mockInternalNetwork(context) {
  // 1. Stub internal platform reads with recorded fixtures. Real fixtures include
  //    test/data/asiops/{app,product,template,version,version_manifest,workload}.json
  //    and test/data/splc/pageGoveDetails.json — pick the one matching the endpoint.
  await context.route(/.*(alibaba-inc\.com|aliyun-inc\.com)\/.*/, async (route) => {
    // Resolve from the project root (process.cwd()), since the test script runs from /tmp.
    const fixture = path.resolve(process.cwd(), 'test/data/asiops/app.json');
    if (fs.existsSync(fixture)) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: fs.readFileSync(fixture, 'utf-8'),
      });
    }
    return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
  });

  // 2. Intercept OSS writes so nothing is persisted to real buckets.
  await context.route(/.*\.aliyuncs\.com\/.*/, (route) => {
    // PUT/POST = write attempt — swallow it and return success.
    return route.fulfill({ status: 200, body: '' });
  });
}
```

> Call `mockInternalNetwork(context)` right after `launchPersistentContext`, before
> navigating or triggering any command. Only bypass mocking in a controlled, authorized
> smoke-test environment.

---

## 12. Prerequisite Service Checks

When a test uses real network endpoints (STS token services, dev servers, API
stubs), verify availability before launching the browser. A missing dependency
produces cascading failures — network errors, empty OSS writes, aborted data
fetches — that are hard to trace back to the root cause from browser console
output alone.

### Pattern: pre-launch curl check

```javascript
const { execSync } = require('child_process');

function checkService(name, url) {
  try {
    const code = execSync(`curl -s -o /dev/null -w '%{http_code}' ${url}`, {
      timeout: 5000,
      encoding: 'utf-8',
    }).trim();
    if (code === '000') {
      throw new Error(`connection refused — is ${name} running at ${url}?`);
    }
    if (code !== '200') {
      throw new Error(`${name} returned HTTP ${code}`);
    }
    console.log(`[PREREQ] ${name}: OK`);
  } catch (e) {
    throw new Error(`[PREREQ FAILED] ${name}: ${e.message}`);
  }
}

// Before launching the browser:
checkService('STS endpoint', 'http://127.0.0.1:8900/api/v1/aliyun/sts');
```

### Pattern: Chrome process cleanup

When reusing an existing Chrome profile, stale processes can hold a lock:

```javascript
const { execSync } = require('child_process');

function cleanupChromeProcesses() {
  try {
    execSync('pkill -f "Google Chrome for Testing" 2>/dev/null || true', {
      timeout: 5000,
    });
  } catch { /* pkill exits non-zero if no match — safe */ }
  // Wait for the OS to release the profile lock
  require('child_process').execSync('sleep 2');
  console.log('[CLEANUP] Chrome processes cleaned');
}

cleanupChromeProcesses();
```

---

## 13. Focus-Free Extension Testing

Extension E2E tests require `headless: false` (service workers and popups do
not work in headless mode). But a headed browser steals desktop focus on every
launch and tab switch, disrupting the user's active work.

### Launch args

Always add these Chromium flags to `launchPersistentContext`:

```javascript
args: [
  `--disable-extensions-except=${pathToExtension}`,
  `--load-extension=${pathToExtension}`,
  '--window-position=-32000,-32000',  // move window off-screen
  '--window-size=1280,720',            // limit window size
  '--no-default-browser-check',        // suppress default-browser prompt
  '--no-first-run',                    // suppress first-run wizard
],
```

### CDP screenshots (no focus required)

`page.screenshot()` may require the tab to be visible/focused. Use CDP instead:

```javascript
async function cdpScreenshot(page, outPath) {
  const client = await page.context().newCDPSession(page);
  const { data } = await client.send('Page.captureScreenshot', { format: 'png' });
  require('fs').writeFileSync(outPath, Buffer.from(data, 'base64'));
  await client.detach();
}
```

### Tab switching without OS focus change

Use CDP `Page.bringToFront` instead of `page.bringToFront()`:

```javascript
async function cdpBringToFront(page) {
  const client = await page.context().newCDPSession(page);
  await client.send('Page.bringToFront');
  await client.detach();
}
```

### Avoid synthetic input

Never use `page.keyboard.press()` or `page.mouse.*()` in extension tests:

- `page.keyboard.press()` sends keys to the OS input queue, disrupting the
  user's active typing. It also does **not** trigger `chrome.commands.onCommand`
  (see §6).
- `page.mouse.click(x, y)` and `page.mouse.move()` are coordinate-based and
  fragile; the mouse event propagates to the OS.

Instead, use:

| Action | Replacement |
|--------|-------------|
| Trigger a keyboard command | `sw.evaluate()` to dispatch the handler (§6a) or replay the message (§6b) |
| Click a button in popup | `popupPage.click('button:has-text("...")')` or `popupPage.locator('button').click()` |
| Fill a form field | `page.fill(selector, value)` |
| Execute page logic | `page.evaluate(() => { ... })` |

---

## 14. On-Demand Script Injection Verification

This project's per-platform scripts (`asiops.js`, `aone.js`, `qianzhou.js`, etc.)
are **not** declared in `manifest.json` `content_scripts`. The service worker
injects them on demand via `chrome.scripting.executeScript` when a command fires.

### Pattern: inject and verify via console logs

Content scripts run in an isolated world — `page.evaluate()` cannot access their
variables. Verify injection by listening for the content script's init log:

```javascript
async function injectAndVerify(context, scriptName, initLogPattern) {
  let [sw] = context.serviceWorkers();
  if (!sw) sw = await context.waitForEvent('serviceworker', { timeout: 10000 });

  const [activeTab] = await sw.evaluate(async () => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    return [tab.id];
  });

  // Collect console messages BEFORE injection
  const page = context.pages().find(p => p.url().includes('alibaba-inc.com'))
    || context.pages()[0];
  const consoleMessages = [];
  page.on('console', (msg) => consoleMessages.push(msg.text()));

  // Inject the script via the service worker
  await sw.evaluate(async (tabId, file) => {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: [file],
    });
  }, activeTab, `static/js/${scriptName}`);

  // Wait for the init log to appear
  await page.waitForTimeout(2000);
  const found = consoleMessages.some(text => initLogPattern.test(text));
  if (!found) {
    throw new Error(`${scriptName} init log not found. Messages: ${consoleMessages.join(', ')}`);
  }
  console.log(`[INJECT] ${scriptName} verified via console log`);
  return true;
}

// Usage:
await injectAndVerify(context, 'asiops.js', /ASI.?Ops.*initialized|content script loaded/i);
```

### Pattern: trigger data fetch via SW message replay

Instead of simulating a keyboard command (which doesn't work, see §6), replay
the exact message the service worker would send:

```javascript
async function triggerDataFetch(context, ossConfig, fetchTypes) {
  let [sw] = context.serviceWorkers();
  if (!sw) sw = await context.waitForEvent('serviceworker', { timeout: 10000 });

  await sw.evaluate(async (config, types) => {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    await chrome.tabs.sendMessage(tab.id, {
      type: 'FETCH_ASIOPS_DATA',
      from: 'BACKGROUND',
      to: 'CONTENT_SCRIPT',
      attachment: {
        ossConfig: config,
        fetchTypes: types,
        selectedWorkloadIds: [],
      },
    });
  }, ossConfig, fetchTypes);

  console.log('[TRIGGER] Data fetch message dispatched');
}

// Usage:
await triggerDataFetch(context, {
  region: 'oss-cn-hangzhou',
  bucket: 'code-workspace-cn-hangzhou-data-4bdc7f55',
  stsUrl: 'http://127.0.0.1:8900/api/v1/aliyun/sts',
}, ['ACCOUNT', 'PRODUCT']);
```

---

## 15. Network Request Tracking

For real-network E2E tests (not mocked), track requests and responses separately
to verify the full data flow: STS → OSS cache check → API fetch → OSS write.

### Pattern: dual-listener with URL filtering

```javascript
function setupNetworkTracking(context) {
  const requests = [];
  const responses = [];

  context.on('request', (req) => {
    const url = req.url();
    if (url.includes('127.0.0.1:8900') ||
        url.includes('aliyuncs.com') ||
        url.includes('alibaba-inc.com')) {
      requests.push({ url, method: req.method(), resourceType: req.resourceType() });
    }
  });

  context.on('response', async (res) => {
    const url = res.url();
    if (url.includes('127.0.0.1:8900') ||
        url.includes('aliyuncs.com') ||
        url.includes('alibaba-inc.com')) {
      responses.push({ url, status: res.status(), method: res.request().method() });
    }
  });

  return { requests, responses };
}

// Usage:
const { requests, responses } = setupNetworkTracking(context);
// ... run test ...
console.log('STS requests:', requests.filter(r => r.url.includes('127.0.0.1:8900')));
console.log('OSS GETs:', responses.filter(r => r.url.includes('aliyuncs.com') && r.method === 'GET'));
console.log('OSS PUTs:', responses.filter(r => r.url.includes('aliyuncs.com') && r.method === 'PUT'));
console.log('API calls:', responses.filter(r => r.url.includes('alibaba-inc.com/api/')));
```

### Pattern: error filtering

Pages on internal platforms load third-party monitoring scripts (alicdn.com,
arms.aliyun.com) that generate console errors unrelated to the extension. Filter
them out when counting "critical errors":

```javascript
function isCriticalError(msg) {
  const text = msg.text();
  // Filter out known noise from platform monitoring scripts
  if (text.includes('alicdn.com') ||
      text.includes('arms.aliyun.com') ||
      text.includes('retcode') ||
      text.includes('goldlog')) {
    return false;
  }
  // Filter out OSS 404 — cache miss is expected, not an error
  if (text.includes('404') && text.includes('aliyuncs.com')) {
    return false;
  }
  return msg.type() === 'error';
}

const criticalErrors = allConsoleMessages.filter(isCriticalError);
if (criticalErrors.length > 0) {
  console.log('Critical errors:', criticalErrors.map(e => e.text()));
}
```

---

## Troubleshooting

### Extension not loaded

- Verify `EXTENSION_PATH` points to the build output containing `manifest.json`.
- Check that the build is up to date: `pnpm build:devel`.
- Ensure `channel: 'chromium'` is set (not `'chrome'` which uses branded Chrome).
- Check console output for Chrome errors about manifest parsing.

### Service worker not found

- MV3 service workers start asynchronously. Use `waitForEvent('serviceworker')`.
- If using MV2, look for `target.type() === 'service_worker'` in browser targets
  instead.
- Service workers auto-suspend after ~30s. Playwright handles this transparently —
  the same Worker object remains valid across suspend/restart.

### Popup page blank

- Some extensions load popup content dynamically. Use `waitUntil: 'networkidle'`.
- Check for JavaScript errors: `page.on('pageerror', (err) => console.log(err))`.
- Verify the extension ID is correct — it changes on each profile reset.

### Content script not injected

- Check `manifest.json` `content_scripts.matches` covers the target URL.
- Content scripts run at `document_end` by default (per this project's manifest).
  Wait for page load to complete before checking for injection.
- Content scripts execute in an isolated world — `page.evaluate()` cannot access
  their variables directly. Look for DOM side effects instead.

### STS / dependency service errors

- `AxiosError: Network Error` from a content script usually means a local STS
  endpoint is not running. Check with `curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8900/api/v1/aliyun/sts`
  before launching the browser.
- HTTP `000` from `curl` means connection refused — the service is not running.
  Start it (e.g., `aliyun_sts_service` or `cws_daemon`) and re-check.
- If STS returns 200 but OSS operations still fail, verify the STS response
  format: it must contain `ak`, `sk`, `token`, and `expiration` fields.

### Browser steals desktop focus

- Add `--window-position=-32000,-32000` to move the browser window off-screen.
- Add `--no-default-browser-check --no-first-run` to suppress first-run dialogs.
- Use CDP `Page.captureScreenshot` instead of `page.screenshot()` — CDP does
  not require the tab to be visible/focused.
- Use CDP `Page.bringToFront` instead of `page.bringToFront()` — the Playwright
  version triggers an OS-level focus change.
- Never use `page.keyboard.press()` or `page.mouse.*()` — these send events to
  the OS input queue and disrupt the user's active typing/clicking. Use
  `sw.evaluate()` or `page.click(selector)` instead.

### Chrome profile lock failure

- Error: `ProcessSingleton` or `Profile is in use` — stale Chrome for Testing
  processes are holding the profile lock.
- Fix: `pkill -f "Google Chrome for Testing" 2>/dev/null; sleep 2` before launch.

### OSS 404 errors in console

- OSS `GET` returning 404 is **expected** when the cache is empty (cache miss).
  The extension then fetches from the API and writes to OSS via PUT.
- Do not count OSS 404 responses as test failures. Filter them out in your
  error-counting logic (see §15 Network Request Tracking).

### On-demand script injection not visible

- Per-platform scripts (`asiops.js`, `aone.js`, etc.) are not in `manifest.json`
  `content_scripts`. They are injected via `chrome.scripting.executeScript`
  when a command fires.
- `page.evaluate(() => window.ASIOPS_SCRIPT_INITIALIZED)` will return `undefined`
  from MAIN world — the variable exists only in the content script's isolated
  world.
- Verify injection by listening for the content script's init console log
  (see §14 On-Demand Script Injection Verification).
