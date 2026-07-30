---
name: extension-e2e-test
description: |
  Chrome extension E2E testing with Playwright and Chrome for Testing.
  Manages full extension lifecycle: loads unpacked MV3 extension, accesses service worker,
  tests popup/options pages, triggers keyboard commands, and verifies content scripts
  on target websites. Delegates browser automation to the browser-utils skill (Tier 3
  Playwright path). Uses Chrome for Testing (non-branded Chromium) which still supports
  --load-extension despite Chrome v137+ removing it from branded builds.
  Use this when the user mentions "extension test", "E2E test extension",
  "测试插件", "扩展测试", "service worker test", "popup test", "options page test",
  "content script test", "插件E2E测试", "浏览器扩展测试", "Playwright extension",
  "load unpacked extension", "chrome extension automation"
skill_id: "<SKILL:.specify/skills/extension-e2e-test/SKILL.md>"
---

# Extension E2E Test

## Overview

End-to-end testing skill for Chrome Manifest V3 browser extensions. Provides a
structured workflow to load an unpacked extension into Chrome for Testing via
Playwright, then test all extension surfaces: service worker, popup, options page,
content scripts, and keyboard commands. Delegates actual browser automation to the
**browser-utils** skill's Tier 3 Playwright executor (`run.js`).

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

4. **Dependency services running** — if the test uses real network (STS endpoints,
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

### Step 2: Determine Test Scope

Identify which extension surfaces to test based on user request:

| Surface | Description | Key API |
|---------|-------------|---------|
| **Service Worker** | Background script (MV3) | `context.serviceWorkers()` |
| **Popup Page** | Extension popup UI | `chrome-extension://${id}/popup.html` |
| **Options Page** | Settings page | `chrome-extension://${id}/options.html` |
| **Content Scripts** | Scripts injected into web pages | Navigate to target URL, inspect DOM |
| **Keyboard Commands** | Shortcut-triggered actions | ⚠️ synthetic keys do **not** fire `chrome.commands.onCommand` — dispatch the equivalent message from the service worker instead (see §6 of the patterns doc) |
| **Chrome Storage** | Extension storage API | Via popup/options page `chrome.storage` |

> **Note on this project's surfaces**: only `static/js/main.js` + `static/js/clipper.js`
> are declared content scripts (auto-injected on `<all_urls>` at `document_end`). The
> per-platform scripts (`asiops/aone/qianzhou/cc/work/splc`) are **not** auto-injected —
> the service worker injects them on demand via `chrome.scripting` when a command fires,
> then messages the tab with the matching `WindowMessageType`. Navigating to a platform
> URL alone will not inject them.

### Step 3: Write the Test Script

Write a Playwright test script to `/tmp/extension-e2e-test-*.js` following the
extension testing patterns. The script must:

1. **Launch persistent context** with extension loaded (include focus-free args):
   ```javascript
   const pathToExtension = '${SKILL_WORKDIR}/dist';
   const userDataDir = '/tmp/extension-e2e-profile';

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

3. **Execute test operations** (popup, options, content scripts, keyboard commands).

4. **Cleanup** — always close the context:
   ```javascript
   await context.close();
   ```

For complete code patterns for each surface, see
[./references/playwright-extension-patterns.md](./references/playwright-extension-patterns.md).

For a ready-to-use test script template, see
[./assets/extension-test-template.js](./assets/extension-test-template.js).

For advanced reliability topics — MV3 service-worker lifecycle & keepalive
(alarms/offscreen), waking a suspended SW, CDP via `newCDPSession` (focus-free
screenshots), MAIN-world console capture, timeout tiers, the two-layer
mock-unit-tests + E2E strategy, and error-code assertions — see
[./references/mv3-reliability-and-cdp.md](./references/mv3-reliability-and-cdp.md).

### Step 4: Execute via browser-utils Executor

Run the test script using browser-utils' universal Playwright executor:

```bash
node ${SKILL_HOME_BROWSER_UTILS}/scripts/js/run.js /tmp/extension-e2e-test-<timestamp>.js
```

Where `${SKILL_HOME_BROWSER_UTILS}` resolves to
`.specify/skills/browser-utils/` (relative to the project root).

> **Note**: The executor auto-installs Playwright if missing, wraps inline code in
> async IIFE if needed, and handles module resolution from the browser-utils skill
> directory.

### Step 5: Interpret Results

The executor prints `console.log` output from the test script. Common patterns:

- **Success**: Script completes without errors, all assertions pass.
- **Extension not loaded**: Service worker event times out — check
  `--load-extension` path and build output.
- **Popup navigation fails**: Extension ID mismatch — ensure service worker is
  fully started before extracting ID.
- **Content script not injected**: Content scripts match by URL pattern; verify
  `manifest.json` `content_scripts.matches` covers the target URL.

### Step 6: Optional — Reuse Login State

For testing against internal platforms (e.g., `asiops.alibaba-inc.com`) that require
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
6. **Write test scripts to `/tmp/`** — never write test files to the skill directory
   or user's project, following browser-utils conventions.
7. **Use `--disable-extensions-except`** — isolates the extension under test by
   disabling all other extensions in the profile.
8. **Respect the read-only / OSS-only boundary** — per the project Constitution, the
   extension only reads from `*.alibaba-inc.com` and only writes to OSS. Triggering a
   real collection during E2E sends live GET requests to internal platforms and may
   write to OSS. Default to **mocking** those responses with `context.route()` /
   `page.route()`, reusing fixtures under `test/data/` (`asiops/`, `splc/`,
   `qianzhou/`). Only hit real network in a controlled, authorized environment.
9. **Treat the service worker as ephemeral** — it suspends after ~30s and loses all
   in-memory state. Get it via `waitForEvent('serviceworker')`, wake it with a cheap
   `sw.evaluate()` before asserting, and assert on durable effects (`chrome.storage`,
   DOM, mocked outputs) rather than SW-held state across a gap. Never rely on a fixed
   sleep to "keep it alive". See the reliability reference.
10. **Push logic down to fast unit tests** — only cover in Playwright E2E what needs a
    real page/SW. Test message-protocol/handler logic as `node --test` unit tests with
    mocked `chrome.*` APIs. Assert on stable **error codes**, not message-text.
11. **Add focus-free launch args** — always include `--window-position=-32000,-32000`,
    `--window-size=1280,720`, `--no-default-browser-check`, `--no-first-run` in the
    `args` array. This prevents the headed browser from stealing desktop focus and
    disrupting the user's active work. See [browser-utils patterns](../browser-utils/references/playwright-patterns.md)
    § Focus-Free Automation for CDP-based alternatives to focus-dependent APIs.
12. **Avoid synthetic keyboard/mouse input** — never use `page.keyboard.press()` or
    `page.mouse.click()` in extension tests. Synthetic keys do not fire
    `chrome.commands.onCommand` (see §6 of the patterns doc), and synthetic mouse
    events pollute the OS input queue. Use `sw.evaluate()`, `page.evaluate()`, or
    `page.click(selector)` instead.
13. **Check prerequisite services before launch** — if the test uses real STS, API,
    or dev-server endpoints, verify each is reachable with `curl` before launching
    the browser. A missing service produces cascading failures (network errors,
    empty OSS writes) that are hard to trace.
14. **Clean up stale Chrome processes** — when reusing a profile, kill any existing
    Chrome for Testing processes first to avoid profile-lock failures.

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
  Ready-to-use test script template covering all extension surfaces.

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

At the end of a substantial run of this skill, perform an agent self-reflection step (never solicit feedback content from the user), following the canonical convention in `.specify/shared/workflow/feedback-step.md`:

1. **Gate on qualification & completion.** Only proceed if this run reached a meaningful wrap-up. Skip trivial/no-op runs; for an aborted run use the abort/partial rule below.
2. **Reflect (no user input).** Review this run against this skill's declared purpose and produce a short review plus ≥1 concrete, skill-specific optimization point. If the run was clean, use exactly: `No significant optimization points identified this run.`
3. **Scope guard.** Keep strictly to this skill's operation; do NOT produce a global/whole-project assessment (that is `/speckit.review`'s job). Entries are `scope: local`.
4. **Dedup guard.** Use a stable `run_id`; if a parent flow already recorded feedback for this same `(unit_id, run_id)`, the engine no-ops.
5. **Persist** via the engine:
   ```bash
   python3 "${SKILL_WORKDIR:-.}/.specify/scripts/python/feedback-utils.py" --action record \
     --unit-id "skill:extension-e2e-test" --unit-type skill \
     --run-id "<stable-run-id>" --feature "<feature-key-if-any>" \
     --review "<review prose>" --points-file "<points file>"
   ```
6. **Consolidated submission prompt.** If the returned `should_prompt` is `true`, surface a single consolidated prompt inviting the user to submit collected feedback to the Spec Kit developers; on confirmation run `--action mark-submitted`. Below threshold, do not prompt.

**Abort / partial-run rule.** If the run failed before wrap-up, either skip recording or record with `--partial` and a `## Review` beginning `**Partial run** — `.
