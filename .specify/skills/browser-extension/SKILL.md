---
name: browser-extension
description: |
  Browser extension execution with Playwright and Chrome for Testing. Loads an
  unpacked MV3 extension into a real browser, then drives the extension to do
  work: access its service worker, operate popup/options pages, trigger keyboard
  commands, run content scripts on target websites, and read/write chrome.storage.
  The extension itself is the automation vehicle — this skill executes the
  extension's features, with testing as one application. Browser-level operations
  (browser launch, page navigation, element interaction, screenshots, network
  interception) are delegated to the browser-utils skill (Tier 3 Playwright path).
  Uses Chrome for Testing (non-branded Chromium) which still supports
  --load-extension despite Chrome v137+ removing it from branded builds.
  Use when the user mentions "extension", "browser extension", "插件",
  "扩展", "execute extension", "run extension", "drive extension",
  "extension automation", "load unpacked extension", "chrome extension",
  "popup", "options page", "content script", "service worker",
  "extension test", "E2E test extension", "测试插件", "扩展测试",
  "插件执行", "扩展执行", "浏览器扩展", "Playwright extension"
skill_id: "<SKILL:.specify/skills/browser-extension/SKILL.md>"
---

# Browser Extension Execution

## Overview

Execution skill for Chrome Manifest V3 browser extensions. Provides a structured
workflow to load an unpacked extension into Chrome for Testing via Playwright,
then **execute the extension's features** to accomplish real tasks on web pages:
service worker logic, popup, options page, content scripts, keyboard commands,
and chrome.storage. The extension is the automation vehicle — this skill drives
the extension's own surfaces instead of operating the page from outside.
Extension **testing** is one application of this skill; the same machinery runs
verification, demonstration, and task execution.

### Delegation to browser-utils

This skill is **not** a general browser automation skill. Browser-level operations
are delegated to the **browser-utils** skill:

| Handled by browser-utils | Handled by this skill (browser-extension) |
|--------------------------|------------------------------------------|
| Browser launch & lifecycle (`launchPersistentContext` setup) | Loading the extension (`--load-extension`, `--disable-extensions-except`) |
| Page navigation, element interaction, form filling | Extension ID extraction from the service worker |
| Screenshots, network interception (`context.route()` / `page.route()`), console capture | Driving extension surfaces: `sw.evaluate()`, popup/options pages, `chrome.*` API calls |
| Dev-server detection, run-mode selection, Playwright installation | Content-script execution & on-demand injection via `chrome.scripting` |
| Script execution via the universal executor (`run.js`) | Reading/writing `chrome.storage` through extension pages |

In practice this means: launch the browser and run the script through
browser-utils' executor, but the script body operates the **extension**, not the
web page. When the task needs plain page automation (no extension involved),
use browser-utils directly instead.

### Key Design Decisions

- **Chrome for Testing over branded Chrome**: Chrome v137+ removed `--load-extension`
  from branded builds. Playwright's bundled Chrome for Testing (non-branded) still
  supports it. This skill always uses `channel: 'chromium'` in Playwright.
- **Persistent context required**: Extensions only work with
  `chromium.launchPersistentContext()`, not `chromium.launch()`.
- **Headed mode by default**: Extension service workers and popups require headed
  mode. Use `headless: false` unless CI with Xvfb.
- **Delegates to browser-utils**: This skill writes Playwright scripts and executes
  them via browser-utils' universal executor at
  `${SKILL_HOME_BROWSER_UTILS}/scripts/js/run.js`.

## Workflow

### Step 1: Prerequisites Check

Verify the following before starting:

1. **Extension build output exists** — check `${SKILL_WORKDIR}/dist/manifest.json`.
   If missing, run `pnpm build:devel` in the project root. (This project uses
   `BUILD_PATH=dist` in package.json scripts.)

2. **browser-utils skill is available** — confirm
   `.specify/skills/browser-utils/scripts/js/run.js` exists. If not, the browser-utils
   skill must be installed first.

3. **Playwright + Chromium installed** — the browser-utils executor auto-installs
   Playwright on first run. To pre-install:
   ```bash
   cd .specify/skills/browser-utils/scripts/js && npm run setup
   ```

4. **Dependency services running** — if the run uses real network (STS endpoints,
   dev servers, API stubs), verify each is reachable before launching the browser.
   A missing STS service, for example, causes OSS operations to fail with cryptic
   `AxiosError: Network Error` messages that are hard to trace back to the root cause.
   ```bash
   # Quick check — exit code 0 means the service is up
   curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8900/api/v1/aliyun/sts
   ```
   For a reusable Node.js pattern (with clear error messages), see
   [references/playwright-extension-patterns.md](./references/playwright-extension-patterns.md)
   § Prerequisite Service Checks.

5. **Chrome profile not locked** — when reusing an existing Chrome user data
   directory (e.g., for login state), stale Chrome for Testing processes can hold
   a profile lock and prevent `launchPersistentContext` from starting. Kill them
   before launch:
   ```bash
   pkill -f "Google Chrome for Testing" 2>/dev/null; sleep 2
   ```

### Step 2: Determine Execution Surface

Identify which extension surface must be driven to accomplish the task:

| Surface | Description | Key API |
|---------|-------------|---------|
| **Service Worker** | Background logic (MV3) — message dispatch, `chrome.scripting` injection, alarms | `context.serviceWorkers()`, `sw.evaluate()` |
| **Popup Page** | Extension popup UI — read state, trigger actions | `chrome-extension://${id}/popup.html` |
| **Options Page** | Settings page — configure the extension | `chrome-extension://${id}/options.html` |
| **Content Scripts** | Scripts injected into web pages — page-level behavior | Navigate to target URL, inspect DOM |
| **Keyboard Commands** | Shortcut-triggered actions | ⚠️ synthetic keys do **not** fire `chrome.commands.onCommand` — dispatch the equivalent message from the service worker instead (see §6 of the patterns doc) |
| **Chrome Storage** | Extension storage API — read/write state | Via popup/options page `chrome.storage` |

> **Note on this project's surfaces**: only `static/js/main.js` + `static/js/clipper.js`
> are declared content scripts (auto-injected on `<all_urls>` at `document_end`). The
> per-platform scripts (`asiops/aone/qianzhou/cc/work/splc`) are **not** auto-injected —
> the service worker injects them on demand via `chrome.scripting` when a command fires,
> then messages the tab with the matching `WindowMessageType`. Navigating to a platform
> URL alone will not inject them.

### Step 3: Write the Execution Script

Write a Playwright script to `/tmp/browser-extension-*.js` following the extension
patterns. The script must:

1. **Launch persistent context** with extension loaded (include focus-free args):
   ```javascript
   const pathToExtension = '${SKILL_WORKDIR}/dist';
   const userDataDir = '/tmp/browser-extension-profile';

   const context = await chromium.launchPersistentContext(userDataDir, {
     channel: 'chromium',
     headless: false,
     args: [
       `--disable-extensions-except=${pathToExtension}`,
       `--load-extension=${pathToExtension}`,
       '--window-position=-32000,-32000',  // off-screen — no desktop focus stealing
       '--window-size=1280,720',
       '--no-default-browser-check',
       '--no-first-run',
     ],
   });
   ```

2. **Obtain extension ID** from service worker:
   ```javascript
   let [serviceWorker] = context.serviceWorkers();
   if (!serviceWorker) {
     serviceWorker = await context.waitForEvent('serviceworker', { timeout: 10000 });
   }
   const extensionId = serviceWorker.url().split('/')[2];
   ```

3. **Drive the extension** to perform the task (popup, options, content scripts,
   keyboard commands) and capture the outcomes.

4. **Cleanup** — always close the context:
   ```javascript
   await context.close();
   ```

For complete code patterns for each surface, see
[./references/playwright-extension-patterns.md](./references/playwright-extension-patterns.md).

For a ready-to-use script template covering all surfaces, see
[./assets/extension-test-template.js](./assets/extension-test-template.js).

For advanced reliability topics — MV3 service-worker lifecycle & keepalive
(alarms/offscreen), waking a suspended SW, CDP via `newCDPSession` (focus-free
screenshots), MAIN-world console capture, timeout tiers, the two-layer
mock-unit-tests + E2E strategy, and error-code assertions — see
[./references/mv3-reliability-and-cdp.md](./references/mv3-reliability-and-cdp.md).

### Step 4: Execute via browser-utils Executor

Run the script using browser-utils' universal Playwright executor:

```bash
node ${SKILL_HOME_BROWSER_UTILS}/scripts/js/run.js /tmp/browser-extension-<timestamp>.js
```

Where `${SKILL_HOME_BROWSER_UTILS}` resolves to
`.specify/skills/browser-utils/` (relative to the project root).

> **Note**: The executor auto-installs Playwright if missing, wraps inline code in
> async IIFE if needed, and handles module resolution from the browser-utils skill
> directory.

### Step 5: Interpret Results

The executor prints `console.log` output from the script. Common patterns:

- **Success**: Script completes without errors, the extension's expected side
  effects are observed (storage writes, DOM changes, network calls, message logs).
- **Extension not loaded**: Service worker event times out — check
  `--load-extension` path and build output.
- **Popup navigation fails**: Extension ID mismatch — ensure service worker is
  fully started before extracting ID.
- **Content script not injected**: Content scripts match by URL pattern; verify
  `manifest.json` `content_scripts.matches` covers the target URL.

### Step 6: Optional — Reuse Login State

For running against internal platforms (e.g., `asiops.alibaba-inc.com`) that require
authentication, reuse an existing Chrome user data directory with login state:

```javascript
const userDataDir = '/Users/<user>/data/chrome/agent';  // existing profile with login

const context = await chromium.launchPersistentContext(userDataDir, {
  channel: 'chromium',
  headless: false,
  args: [
    `--disable-extensions-except=${pathToExtension}`,
    `--load-extension=${pathToExtension}`,
  ],
});
```

> **Warning**: Using an existing profile will load the extension alongside any
> extensions already in that profile. Use `--disable-extensions-except` to isolate.

## Strict Requirements

1. **Always use `channel: 'chromium'`** — this selects Chrome for Testing, which
   supports `--load-extension`. Branded Chrome (v137+) does not.
2. **Always use `launchPersistentContext`** — extensions do not work with
   `chromium.launch()` + `newContext()`.
3. **Always set `headless: false`** — extension service workers and popups require
   headed mode. For CI, use Xvfb.
4. **Always extract extension ID dynamically** — the ID changes between environments
   and profile resets. Never hardcode it.
5. **Always close the context** — `await context.close()` in finally block to prevent
   orphaned Chrome processes.
6. **Write scripts to `/tmp/`** — never write script files to the skill directory
   or user's project, following browser-utils conventions.
7. **Use `--disable-extensions-except`** — isolates the extension under execution by
   disabling all other extensions in the profile.
8. **Respect the read-only / OSS-only boundary** — per the project Constitution, the
   extension only reads from `*.alibaba-inc.com` and only writes to OSS. Triggering a
   real collection sends live GET requests to internal platforms and may write to OSS.
   Default to **mocking** those responses with `context.route()` / `page.route()`,
   reusing fixtures under `test/data/` (`asiops/`, `splc/`, `qianzhou/`). Only hit
   real network in a controlled, authorized environment.
9. **Treat the service worker as ephemeral** — it suspends after ~30s and loses all
   in-memory state. Get it via `waitForEvent('serviceworker')`, wake it with a cheap
   `sw.evaluate()` before asserting, and rely on durable effects (`chrome.storage`,
   DOM, mocked outputs) rather than SW-held state across a gap. Never rely on a fixed
   sleep to "keep it alive". See the reliability reference.
10. **Verify on durable effects, not transient state** — assert task outcomes via
    `chrome.storage`, DOM, network calls, or mocked outputs; message-text assertions
    should use stable **error codes**, not message-text.
11. **Add focus-free launch args** — always include `--window-position=-32000,-32000`,
    `--window-size=1280,720`, `--no-default-browser-check`, `--no-first-run` in the
    `args` array. This prevents the headed browser from stealing desktop focus and
    disrupting the user's active work. See [browser-utils patterns](../browser-utils/references/playwright-patterns.md)
    § Focus-Free Automation for CDP-based alternatives to focus-dependent APIs.
12. **Avoid synthetic keyboard/mouse input** — never use `page.keyboard.press()` or
    `page.mouse.click()` in extension scripts. Synthetic keys do not fire
    `chrome.commands.onCommand` (see §6 of the patterns doc), and synthetic mouse
    events pollute the OS input queue. Use `sw.evaluate()`, `page.evaluate()`, or
    `page.click(selector)` instead.
13. **Check prerequisite services before launch** — if the run uses real STS, API,
    or dev-server endpoints, verify each is reachable with `curl` before launching
    the browser. A missing service produces cascading failures (network errors,
    empty OSS writes) that are hard to trace.
14. **Clean up stale Chrome processes** — when reusing a profile, kill any existing
    Chrome for Testing processes first to avoid profile-lock failures.
15. **Delegate plain page automation to browser-utils** — when the task does not
    involve the extension (plain web automation, screenshots of ordinary pages,
    form filling on non-extension pages), use the browser-utils skill directly
    rather than loading an extension.

## Path Conventions

This Skill follows the canonical path conventions:

- Use `${SKILL_HOME}/<relative-path>` for every Skill-owned resource reference.
- Use `${SKILL_WORKDIR}/<relative-path>` for every runtime/user-facing path (e.g.,
  the extension build output at `${SKILL_WORKDIR}/dist/`).

Additionally, this skill references the browser-utils skill's executor:
- `${SKILL_HOME_BROWSER_UTILS}/scripts/js/run.js` — the universal Playwright runner.
  In practice, this resolves to `.specify/skills/browser-utils/scripts/js/run.js`
  relative to the project root.

## Resources

### References (`${SKILL_HOME}/references/`)
- [playwright-extension-patterns.md](./references/playwright-extension-patterns.md) —
  Complete code patterns for each extension surface (service worker, popup, options,
  content scripts, keyboard commands, Chrome Storage), plus:
  §12 Prerequisite Service Checks (curl-based pre-launch checks, Chrome process cleanup),
  §13 Focus-Free Extension Testing (off-screen launch args, CDP screenshots, synthetic
  input avoidance),
  §14 On-Demand Script Injection Verification (console-log-based verification for
  `chrome.scripting.executeScript` injected scripts),
  §15 Network Request Tracking (dual-listener with URL filtering, error noise filtering).
- [mv3-reliability-and-cdp.md](./references/mv3-reliability-and-cdp.md) —
  MV3 service-worker lifecycle & keepalive, waking a suspended SW, CDP via
  `newCDPSession`, MAIN-world console capture, timeout tiers, the two-layer
  mock-unit + E2E strategy, and error-code assertions.

### Assets (`${SKILL_HOME}/assets/`)
- [extension-test-template.js](./assets/extension-test-template.js) —
  Ready-to-use script template covering all extension surfaces.

## Dependencies

- **browser-utils skill** — provides the Playwright executor (`run.js`) and Chromium
  browser installation.
- **Playwright** (auto-installed by browser-utils) — `^1.57.0` or later.
- **Chrome for Testing** — bundled with Playwright, supports `--load-extension`.
- **Extension build output** — `${SKILL_WORKDIR}/dist/` must contain
  `manifest.json` and all extension assets. (This project uses `BUILD_PATH=dist`.)

## Feedback

**Runtime-mode gate.** If `${SKILL_WORKDIR}/.specify/` does not exist, this skill is
running in standalone mode (a non–Spec Kit deployment, e.g. a global agent skills
directory) — skip this entire Feedback step: no engine call, no feedback entry.

At wrap-up, run the feedback self-reflection step per the canonical convention in `.specify/shared/workflow/feedback-step.md`: agent self-reflection only — **never** solicit feedback content from the user; skip trivial or no-op runs; keep strictly to this skill's scope; persist one entry via `feedback-utils.py --action record --unit-id "skill:browser-extension" --unit-type skill`. Non-blocking (非阻塞) and never any 自动传输 — delivery stays manual. That file owns every rule of this step — reflection, scope, dedup, persistence, the submission prompt, the abort and nesting clauses; do not restate any of them here.
