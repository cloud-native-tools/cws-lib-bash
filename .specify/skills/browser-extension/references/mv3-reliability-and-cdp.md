# MV3 Reliability & CDP Patterns for E2E

Advanced patterns for testing Chrome MV3 extensions reliably. These are distilled
from a production WebSocket browser-bridge (a Node server driving a long-lived MV3
extension), adapted here for **Playwright-based E2E** of this project's extension.

Use these when a basic "load extension → open popup" test is not enough: when the
service worker suspends mid-test, when screenshots fail without window focus, when you
need the page's real console, or when you want fast, deterministic coverage of the
message-protocol logic without a browser.

## Table of Contents

1. [MV3 service worker lifecycle — what breaks tests](#1-mv3-service-worker-lifecycle--what-breaks-tests)
2. [Keeping / waking the service worker in tests](#2-keeping--waking-the-service-worker-in-tests)
3. [CDP via Playwright (`newCDPSession`)](#3-cdp-via-playwright-newcdpsession)
4. [Reading the page's real console (MAIN world)](#4-reading-the-pages-real-console-main-world)
5. [Readiness & timeout tiers (no fixed sleeps)](#5-readiness--timeout-tiers-no-fixed-sleeps)
6. [Two-layer test strategy: mock unit tests + E2E](#6-two-layer-test-strategy-mock-unit-tests--e2e)
7. [Error-code taxonomy for assertions](#7-error-code-taxonomy-for-assertions)

---

## 1. MV3 service worker lifecycle — what breaks tests

An MV3 service worker (SW) is **not** a persistent background page. Chrome terminates
it after ~30s of inactivity and restarts it on the next event. Consequences for E2E:

- The `serviceWorker` object may not exist yet at launch → always `waitForEvent`.
- Any in-memory state the SW held (Maps, counters, cached config) is **lost** across a
  suspend/restart. Tests that assume state persists between two actions can flake.
- A test that idles > ~30s (e.g. a long fixed sleep) can let the SW die, so the next
  message it should handle silently does nothing.

Production extensions fight this with a **layered keepalive** (worth knowing so you can
reason about behavior you observe, and to test extensions that rely on it):

| Layer | Mechanism | Period | Notes |
|-------|-----------|--------|-------|
| 1 | `setInterval` + a real message/WS ping from within the SW | ~20s | Only keeps a *running* SW warm; cannot resurrect a dead one on its own. |
| 2 | `chrome.alarms` (`periodInMinutes: 0.4` ≈ 24s) | ~24s | **Wakes** a suspended SW — alarms are the reliable resurrection path. Min period is 0.5 in prod builds; 0.4 works in unpacked/dev. Requires the `alarms` permission. |
| 3 | Offscreen document (`chrome.offscreen.createDocument`, `reasons: ['BLOBS']`) pinging `chrome.runtime.sendMessage({keepAlive:true})` | ~20s | An off-DOM page whose messages keep the SW alive. Requires the `offscreen` permission and `minimum_chrome_version >= 116`. |

The alarm handler is also the **self-heal tick**: it re-creates the offscreen doc if
Chrome killed it, and treats a socket that is `OPEN` but silent for >45s as dead
(reconnect). The lesson for tests: **rely on events/alarms to wake the SW, not on it
staying alive.**

## 2. Keeping / waking the service worker in tests

```javascript
// Always obtain the SW defensively — it may be starting or restarting.
async function getServiceWorker(context, timeout = 10000) {
  let [sw] = context.serviceWorkers();
  if (!sw) sw = await context.waitForEvent('serviceworker', { timeout });
  return sw;
}

// Force a suspended SW awake before asserting on it: any evaluate() re-activates it.
// Playwright keeps the same Worker handle valid across suspend/restart cycles.
async function wakeServiceWorker(context) {
  const sw = await getServiceWorker(context);
  await sw.evaluate(() => chrome.runtime.getManifest().version); // cheap wake ping
  return sw;
}
```

- **Do not** assert on SW in-memory state across a long gap; instead assert on durable
  effects (`chrome.storage`, DOM side effects, OSS/download outputs — mocked, see §6 of
  the patterns doc).
- If you must verify keepalive-dependent behavior, drive it through an event
  (`chrome.alarms` fire, a message, a command) rather than waiting in real time.

## 3. CDP via Playwright (`newCDPSession`)

Playwright exposes the Chrome DevTools Protocol, which unlocks operations the normal
API cannot do reliably in a background/unfocused test browser.

```javascript
// Screenshot WITHOUT requiring the tab to be focused/foreground.
// chrome.tabs.captureVisibleTab needs an active window; CDP does not.
async function cdpScreenshot(page, outPath) {
  const client = await page.context().newCDPSession(page);
  const { data } = await client.send('Page.captureScreenshot', { format: 'png' });
  require('fs').writeFileSync(outPath, Buffer.from(data, 'base64'));
  await client.detach();
}
```

Reliability lessons from the source bridge that also apply to raw CDP use:

- **Cap image dimensions** — keep screenshots under ~7800px per side if they will be
  sent to an LLM (Anthropic's API rejects > 8000px). Use `clip` or device metrics.
- **Sessions detach silently** — Chrome can drop a CDP/debugger session
  (`target_closed`, `canceled_by_user`, `replaced_with_devtools`) at any time. With
  raw `chrome.debugger` the robust pattern is: keep a session map, refresh an idle
  timer *on every command* (so a long op isn't released mid-flight), and on a
  `/not attached|Detached while handling/` error, clear the entry, re-attach, retry
  **once**. With Playwright's `newCDPSession`, prefer creating a fresh session per
  logical operation and `detach()` when done rather than caching one for the whole run.
- Only one debugger client per tab — Playwright's CDP session conflicts with an open
  DevTools window on the same tab.

## 4. Reading the page's real console (MAIN world)

Content scripts run in an **isolated world**, so a content-script `console` patch
cannot see the page's own `console` calls. To capture the page's real console output,
inject an interceptor into the **MAIN world** at `document_start`:

```json
// manifest content_scripts entry (how the source bridge does it)
{ "matches": ["*://*/*"], "js": ["console-interceptor.js"],
  "run_at": "document_start", "world": "MAIN" }
```

```javascript
// console-interceptor.js — patches the page's real console into a ring buffer
(function () {
  if (window.__consoleMessages) return;
  window.__consoleMessages = [];
  const MAX = 500; // bounded ring buffer — never grows unboundedly
  for (const m of ['log', 'warn', 'error', 'info']) {
    const orig = console[m].bind(console);
    console[m] = function (...args) {
      window.__consoleMessages.push({
        level: m === 'warn' ? 'warning' : m,
        text: args.map(a => { try { return typeof a === 'object' ? JSON.stringify(a) : String(a); } catch { return String(a); } }).join(' '),
        timestamp: Date.now(),
      });
      if (window.__consoleMessages.length > MAX) window.__consoleMessages.shift();
      return orig.apply(console, args);
    };
  }
})();
```

In an E2E test you usually don't need to inject this yourself — Playwright's
`page.on('console', …)` already captures page console. Use the MAIN-world buffer
technique only when testing an extension that itself relies on reading the page console
(then assert on `page.evaluate(() => window.__consoleMessages)`).

## 5. Readiness & timeout tiers (no fixed sleeps)

The source bridge never uses one global timeout; it tiers them by operation cost. Mirror
that in tests instead of scattering `waitForTimeout(2000)`:

```javascript
const T = {
  quick: 5_000,       // storage read, context query, popup open
  interactive: 10_000, // dialog handling, a click that triggers a message roundtrip
  heavy: 30_000,       // element screenshot, evaluate-heavy work
  fullPage: 120_000,   // full-page screenshot / large capture
};
```

- Prefer `waitForSelector` / `waitForFunction` / `waitForEvent` over sleeps.
- Give network-bound assertions the tier that matches the real operation, not a guess.
- A fixed sleep long enough to be "safe" is also long enough to let the SW suspend (§1).

## 6. Two-layer test strategy: mock unit tests + E2E

The source project splits testing into two complementary layers — adopt the same split
so the slow, flaky-prone browser layer stays small:

**Layer A — fast deterministic unit tests (no browser).** Use Node's built-in runner
(`node --test`, `node:assert/strict`) and **mock the `chrome.*` APIs** to test pure
message-protocol / handler logic directly. The bridge tests reliability logic (timeout,
zombie eviction, request/response correlation, error-code propagation) with a
`MockWebSocket extends EventEmitter` and by injecting clients straight into internal
Maps — no real sockets, no Chrome.

```javascript
// e.g. unit-test a WindowMessageType handler with a mocked chrome global
import { test } from 'node:test';
import assert from 'node:assert/strict';

globalThis.chrome = {
  runtime: { sendMessage: (m) => { globalThis.__last = m; } },
  storage: { local: { get: async () => ({ storage: 'oss' }) } },
};
test('handler emits FETCH_ASIOPS_DATA with attachment', async () => {
  // import and invoke the handler under test, then:
  assert.equal(globalThis.__last.type, 'FETCH_ASIOPS_DATA');
});
```

**Layer B — real E2E (Playwright + loaded extension).** Reserve this for what only a
real browser proves: the extension loads, SW starts, popup/options render, content
scripts inject, the full message chain runs end to end. Keep the count small and each
one focused.

> Rule of thumb: if a test doesn't actually need a rendered page or a real SW, write it
> as a Layer A unit test. E2E time is expensive and flakier.

## 7. Error-code taxonomy for assertions

The bridge attaches a stable `.code` to every error and carries it across process
boundaries via a `BridgeError extends Error { code }` subclass, split into
extension-originated vs server-originated codes (e.g. `CDP_ATTACH_FAILED`, `NO_DIALOG`
from the extension; `TIMEOUT`, `NO_BROWSER`, `VALIDATION_ERROR` from the server).

For tests, this means: **assert on stable codes, not on human-readable message text.**
Message strings drift (as this project's own SPLC test showed — it asserted
`"...operations score details"` while the code threw `"...score details"`). A code like
`TIMEOUT` is a contract; a sentence is not. When adding new failure branches to the
extension, give them a code and assert on the code in tests.
