# browser-utils WebSocket Bridge (external, dev-only)

A reusable **external** mechanism for driving and testing a **real Chrome** (real
profile, real login state, branded or not) over a local WebSocket — without embedding
any WebSocket code in the product extension you are testing.

Use it when Playwright's Chrome-for-Testing isn't enough: you need the user's actual
logged-in browser, a specific installed extension, or interactive live control during
development. For headless/automated E2E you usually don't need this — prefer Playwright
(see `../js/run.js` and `../../references/playwright-extension-patterns.md`).

> ⚠️ **Dev-only. Never ship this and never expose the port beyond localhost.** The
> companion extension can navigate, evaluate arbitrary JS, and screenshot any tab in
> the Chrome it is loaded into. It binds to `127.0.0.1` only; set `BRIDGE_TOKEN` to
> require a shared secret from every client. Load the companion extension only in a
> Chrome instance you control, ideally a dedicated profile.

## Architecture

```
 automation script / CLI  ──WS──►  server.js (relay)  ◄──WS──  companion extension
   (controller role)                127.0.0.1:8777             (extension role, in Chrome)
        client.js                   requestId correlation        background.js + CDP
```

- The **companion extension** is the WS client and the only thing that touches the
  browser. It survives MV3 SW suspension via a 3-layer keepalive (ping + `chrome.alarms`
  + offscreen document) and reconnects with capped backoff.
- The **server** relays `command` messages from controllers to the extension and routes
  responses back, with per-request timeouts (`TIMEOUT` code) and dual heartbeat zombie
  eviction.
- **Controllers** (`client.js` / `bridge-cli.js`) issue promise-based commands.

Design rationale for each reliability choice is documented in
[`../../references/extension-bridge-patterns.md`](../../references/extension-bridge-patterns.md).

## Setup

```bash
cd scripts/bridge
npm install            # installs `ws`
```

## Usage

**1. Start the relay server** (terminal 1):

```bash
node server.js
# ws on ws://127.0.0.1:8777, health on http://127.0.0.1:8778/health
# optional: BRIDGE_TOKEN=secret BRIDGE_WS_PORT=8777 node server.js
```

**2. Load the companion extension into Chrome:**

- Open `chrome://extensions`, enable **Developer mode**.
- **Load unpacked** → select `scripts/bridge/extension/`.
- It connects automatically. (If you set `BRIDGE_TOKEN`, also set the matching `TOKEN`
  constant at the top of `extension/background.js` before loading.)
- Verify: `curl -s http://127.0.0.1:8778/health` should show `"extensions": 1`.

**3. Drive the browser** — one-shot CLI:

```bash
node bridge-cli.js status
node bridge-cli.js navigate  '{"url":"https://example.com"}'
node bridge-cli.js evaluate  '{"expression":"document.title"}'
node bridge-cli.js waitFor   '{"selector":"h1"}'
node bridge-cli.js getText   '{"selector":"h1"}'
node bridge-cli.js getConsole '{}'
node bridge-cli.js screenshot '{}' --out /tmp/shot.png
```

Or programmatically (`client.js`):

```javascript
import { BridgeClient } from './client.js';

const bridge = await BridgeClient.connect();          // { port, token } optional
await bridge.navigate('https://example.com');
console.log(await bridge.evaluate('document.title'));
await bridge.fill('input[name=q]', 'hello');
await bridge.click('button[type=submit]');
await bridge.waitFor('.results');
await bridge.saveScreenshot('/tmp/results.png');
bridge.close();
```

## Command reference

| Command | Params | Returns |
|---------|--------|---------|
| `status` | — | `{ name, version }` |
| `listTabs` | — | `[{ id, url, title, active }]` |
| `getContext` | `{tabId?}` | `{ tabId, url, title }` |
| `navigate` | `{url, tabId?, active?, timeout?}` | `{ tabId, url, title }` (waits for load) |
| `evaluate` | `{expression, tabId?}` | the expression's JSON value (via CDP `Runtime.evaluate`) |
| `click` | `{selector, tabId?}` | `{ clicked }` |
| `fill` / `type` | `{selector, text, tabId?}` | `{ filled }` |
| `waitFor` | `{selector, tabId?, timeout?}` | `{ found }` or `TIMEOUT` |
| `getText` | `{selector?, tabId?}` | element/body `innerText` |
| `getConsole` | `{tabId?}` | `[{level, text, timestamp}]` (MAIN-world buffer) |
| `screenshot` | `{tabId?, format?, quality?}` | `{ format, dataBase64 }` (CDP, no focus needed) |
| `getStorage` | `{keys?}` | the **companion** extension's own `chrome.storage.local` |

Errors carry a stable `.code` (`TIMEOUT`, `NO_BROWSER`, `NOT_FOUND`, `EVAL_ERROR`,
`CDP_ATTACH_FAILED`, `VALIDATION_ERROR`, `UNKNOWN_COMMAND`) — branch on codes, not text.

## Testing a *specific* extension with this bridge

The companion extension drives the browser (pages, DOM, console, screenshots) — it does
**not** reach into another extension's service worker. To E2E a target extension:

- Load the target extension **and** this companion in the same Chrome profile.
- Use `navigate` / `click` / `evaluate` to exercise the target's content-script and
  page-level effects, and `getConsole` / screenshots to assert outcomes.
- To drive the target's own popup/SW internals, prefer Playwright's
  `serviceWorker.evaluate()` path (see the extension-e2e-test skill) — that is the right
  tool for in-extension internals; this bridge is for real-browser, real-login flows.

## Ports & env

| Var | Default | Meaning |
|-----|---------|---------|
| `BRIDGE_WS_PORT` | `8777` | WebSocket port (also edit `extension/background.js` `WS_URL`) |
| `BRIDGE_HEALTH_PORT` | `8778` | health endpoint |
| `BRIDGE_TOKEN` | _(none)_ | shared secret required from every client |
| `BRIDGE_TIMEOUT` | `15000` | default per-request timeout (ms) |
