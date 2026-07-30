# Extension Bridge Patterns (WebSocket ↔ MV3 Extension)

Reliability and design patterns for driving a Chrome extension from an external process
over a **persistent WebSocket** — the architecture behind Tier 2 (MCP connector +
Chrome extension) and any custom "control Chrome from Node/Python" bridge.

Distilled from a production browser-bridge: a Node server that exposes browser
automation to an AI agent by talking to a long-lived MV3 extension service worker over
`ws://127.0.0.1`. Use this when building, operating, or debugging such a bridge — the
failure modes here (dead sockets, suspended service workers, silent CDP detach) are the
ones that make extension automation flaky in practice.

> **A runnable, dev-only implementation of these patterns ships with this skill** at
> [`../scripts/bridge/`](../scripts/bridge/) (relay `server.js`, `client.js`/`bridge-cli.js`,
> and a minimal MV3 companion `extension/`). This document is the *why*; that directory
> is the *what*. Read on to understand or extend it.

## Table of Contents

1. [Architecture](#1-architecture)
2. [Request/response correlation](#2-requestresponse-correlation)
3. [Handshake & connection lifecycle](#3-handshake--connection-lifecycle)
4. [Liveness: dual heartbeat & zombie eviction](#4-liveness-dual-heartbeat--zombie-eviction)
5. [Reconnect with capped backoff + wait-for-client](#5-reconnect-with-capped-backoff--wait-for-client)
6. [MV3 keepalive: the three layers](#6-mv3-keepalive-the-three-layers)
7. [CDP reliability](#7-cdp-reliability)
8. [Operational hardening](#8-operational-hardening)
9. [Testing a bridge: mock unit + real integration](#9-testing-a-bridge-mock-unit--real-integration)

---

## 1. Architecture

```
 external process (Node/Python)          Chrome
 ┌──────────────────────────┐      ┌───────────────────────────┐
 │ WebSocket server (ws)     │◄────►│ MV3 service worker (client)│
 │  - pendingRequests Map    │  WS  │  - WebSocket client        │
 │  - heartbeat/eviction     │      │  - keepalive layers        │
 │  - health/metrics HTTP    │      │  - CDP (chrome.debugger)   │
 └──────────────────────────┘      │  - content scripts         │
                                    └───────────────────────────┘
```

The **extension is the WS client** (it dials out to the local server); the server never
initiates the TCP connection. This survives the server restarting independently and lets
the extension reconnect on its own schedule. Bind the server to `127.0.0.1` only.

## 2. Request/response correlation

Every request carries a unique `requestId` (UUID). The server keeps a
`pendingRequests: Map<requestId, {resolve, reject, timer}>`. A response is matched by
`requestId`; on match, clear the timer and settle the promise.

```javascript
async broadcast(message, timeout = 15_000) {
  await this._waitForBrowserClient();                 // see §5
  const requestId = randomUUID();
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      this.pendingRequests.delete(requestId);
      const err = new Error(`Request timed out after ${timeout}ms`);
      err.code = 'TIMEOUT';                             // stable code, see §8
      reject(err);
    }, timeout);
    this.pendingRequests.set(requestId, { resolve, reject, timer });
    for (const [ws] of this.browserClients) this._send(ws, { ...message, requestId });
  });
}

// On inbound message:
if (msg.requestId && this.pendingRequests.has(msg.requestId)) {
  const pending = this.pendingRequests.get(msg.requestId);
  this.pendingRequests.delete(msg.requestId);
  clearTimeout(pending.timer);
  if (msg.error) { const e = new Error(msg.error); if (msg.code) e.code = msg.code; pending.reject(e); }
  else pending.resolve(msg.result ?? msg);
}
```

Key points:
- **Always** pair a pending entry with a timeout that deletes itself — otherwise a lost
  response leaks the entry and hangs the caller forever.
- Carry an error `code` end to end (see §8) so callers branch on codes, not strings.
- If you fan out to multiple clients, allocate a *fresh* inner `requestId` for the
  broadcast to avoid collisions with the caller's id.

## 3. Handshake & connection lifecycle

On connect, the server sends `connection_init` with a `clientId` and version; the client
stores it. This gives both sides a stable identity for logging, rate-limiting, and
correlating reconnects.

```javascript
// server → client on connection
this._send(ws, { type: 'connection_init', clientId: randomUUID(), serverVersion: '1.0.0' });
```

On close, delete the client from all maps, reject any of its pending requests, and emit
a disconnect event so higher layers can clean up per-session resources.

## 4. Liveness: dual heartbeat & zombie eviction

A single ping/pong is **not enough** for MV3. A half-open socket can keep answering
WS-level `pong` (handled by the OS/browser network stack) even after the service worker
that owns the app logic has died. So track **two** timestamps:

- `lastPing` — updated on WS-level `pong`. Detects network-dead sockets.
- `lastAppMsg` — updated only on **app-level messages** (a `keepalive` message or any
  real response). Detects a *zombie*: socket looks OPEN but the SW is gone.

```javascript
_checkHeartbeats() {                       // runs on an interval (~45s)
  const now = Date.now();
  for (const [ws, info] of this.browserClients) {
    if (now - (info.lastAppMsg ?? info.connectedAt) > 45_000) {   // 2 missed 20s keepalives
      ws.close(1000, 'App-level heartbeat timeout');              // evict zombie
      this.browserClients.delete(ws);
    } else if (now - info.lastPing > 120_000) {
      ws.close(1000, 'Heartbeat timeout');
      this.browserClients.delete(ws);
    } else {
      ws.ping();
    }
  }
}
```

The client sends an app-level `keepalive` every 20s, so 45s ≈ two missed beats ⇒ evict.
Idle client sessions can additionally be evicted on an activity TTL (e.g. 15 min).

## 5. Reconnect with capped backoff + wait-for-client

**Client side** — reconnect with multiplicative backoff, reset on success:

```javascript
const RECONNECT_BASE = 3000, RECONNECT_MAX = 5000;
let reconnectDelay = RECONNECT_BASE;
function scheduleReconnect() {
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(() => {
    reconnectDelay = Math.min(reconnectDelay * 1.5, RECONNECT_MAX);
    connect();
  }, reconnectDelay);
}
// on ws.onopen: reconnectDelay = RECONNECT_BASE;   // reset backoff
// Guard connect() against duplicate sockets: bail if CONNECTING or OPEN.
```

**Server side** — don't fail a request just because the extension is mid-reconnect.
Wait briefly for a client to (re)appear before sending:

```javascript
_waitForBrowserClient(timeoutMs = 5_000) {
  if (this.browserClients.size > 0) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { this.off('clientConnected', onClient); reject(new Error('No browser extension connected')); }, timeoutMs);
    const onClient = () => { if (this.browserClients.size > 0) { clearTimeout(timer); this.off('clientConnected', onClient); resolve(); } };
    this.on('clientConnected', onClient);
  });
}
```

## 6. MV3 keepalive: the three layers

An MV3 service worker is terminated after ~30s idle. To keep a *bridge* SW alive long
enough to serve requests, layer three independent mechanisms — no single one is
sufficient:

| Layer | Mechanism | Period | Role |
|-------|-----------|--------|------|
| 1 | `setInterval` sending a WS `keepalive` while OPEN | 20s | Keeps a *running* SW warm and refreshes the server's `lastAppMsg`. |
| 2 | `chrome.alarms` (`periodInMinutes: 0.4`) | ~24s | **Resurrects** a suspended SW — the only layer that reliably wakes a dead worker. Also the self-heal tick. |
| 3 | Offscreen document (`chrome.offscreen.createDocument`, `reasons:['BLOBS']`) pinging `chrome.runtime.sendMessage({keepAlive:true})` | 20s | Off-DOM page whose messages keep the SW warm; requires `offscreen` perm + Chrome ≥ 116. |

The **alarm handler doubles as recovery**: recreate the offscreen doc if Chrome killed
it; if the socket is closed, reset backoff and reconnect immediately; if the socket is
`OPEN` but silent for >45s (server heartbeats every ~30s), treat it as dead, `close()`,
and reconnect.

```javascript
chrome.alarms.create('ws-keepalive', { periodInMinutes: 0.4 });
chrome.alarms.onAlarm.addListener((a) => {
  if (a.name !== 'ws-keepalive') return;
  ensureOffscreen();
  if (!ws || ws.readyState !== WebSocket.OPEN) { reconnectDelay = RECONNECT_BASE; connect(); }
  else if (Date.now() - lastServerMessage > 45_000) { ws.close(); reconnectDelay = RECONNECT_BASE; connect(); }
});
```

Manifest needs: `"permissions": ["alarms", "offscreen", ...]`, `"minimum_chrome_version": "116"`.

## 7. CDP reliability

Driving pages via `chrome.debugger` (CDP) is powerful but the session detaches
unpredictably. Two behaviors make it reliable:

- **Idle timer refreshed on every command.** A fixed "release after 5s" timer will drop
  the debugger mid-operation during any sequence longer than the idle window. Reset the
  release timer on each `sendCommand` so it only fires after *true* quiescence.
- **Auto-recover once on silent detach.** Chrome drops sessions for `target_closed`,
  `canceled_by_user`, `replaced_with_devtools` without your code calling `detach()`.
  Your session map then lies. Catch the specific error, clear the entry, re-attach,
  retry **once**. Also add a proactive `chrome.debugger.onDetach` listener to keep the
  map honest, and clean up on `chrome.tabs.onRemoved`.

```javascript
async function cdpCommand(tabId, method, params = {}) {
  const s = cdpSessions.get(tabId);
  if (s?.attached) { clearTimeout(s.timer); s.timer = setTimeout(() => cdpRelease(tabId), 5000); }
  try { return await chrome.debugger.sendCommand({ tabId }, method, params); }
  catch (err) {
    if (!/not attached|Detached while handling/i.test(String(err?.message))) throw err;
    cdpSessions.delete(tabId);
    await chrome.debugger.attach({ tabId }, '1.3').catch(() => {});
    cdpSessions.set(tabId, { attached: true, timer: setTimeout(() => cdpRelease(tabId), 5000) });
    return chrome.debugger.sendCommand({ tabId }, method, params);   // retry once
  }
}
```

- Prefer **CDP screenshots** (`Page.captureScreenshot`) over `chrome.tabs.captureVisibleTab`
  — no window-focus requirement, works when the tab isn't foreground.
- **Cap image dimensions** (~7800px/side) if screenshots go to an LLM (Anthropic rejects > 8000px).
- Allow a **large WS `maxPayload`** (e.g. 50 MB) — base64 screenshots are big.
- Only one debugger client per tab (conflicts with open DevTools).

## 8. Operational hardening

Small, dependency-free modules that make a bridge production-grade:

- **Error-code taxonomy** — a `BridgeError extends Error { code }` and two enums:
  extension-originated (`CDP_ATTACH_FAILED`, `NO_DIALOG`, …) and server-originated
  (`TIMEOUT`, `NO_BROWSER`, `RATE_LIMITED`, `VALIDATION_ERROR`, `BROWSER_BUSY`). Codes
  propagate across the socket so callers branch on codes, never on message text.
- **Input validators** — one tiny `Validator` with per-type checks and length caps
  (`selector` ≤ 500, `url` ≤ 2048, `expression` ≤ 100k, `timeout` clamped to a range,
  `action` against an allow-list). Reject bad input before it reaches the browser.
- **Token-bucket rate limiter** — per-client bucket, `maxTokens` + refill/sec; reject
  with `RATE_LIMITED` when empty. ~25 lines, no deps.
- **Rolling metrics** — per-tool calls/successes/failures, avg + **p95** duration, and
  error-code breakdown over a 1h window, pruned every 5 min (bounded memory). Invaluable
  for spotting which operation is slow/flaky.
- **Health HTTP endpoint** — `/health` (bridge status, uptime, client counts, rate-limit
  state) and `/metrics`. Lets you check liveness without touching the WS protocol.
- **Per-operation timeout tiers** — never one global timeout. Tier by cost:
  `quick` 5s, `interactive` 10s, `heavy` 30s, `fullPage` 120s, plus longer tiers for
  known-slow flows. Pass the matching tier into `broadcast(msg, timeout)`.
- **Graceful shutdown** — on stop, reject all `pendingRequests`, close all sockets with
  code 1000, clear timers/intervals.
- **Config + rotating debug log** — centralize constants with env overrides
  (`MCP_WS_PORT`, …); append crash diagnostics to a log file that self-rotates at ~5 MB.

## 9. Testing a bridge: mock unit + real integration

Two complementary layers (both on Node's built-in runner, `node --test` +
`node:assert/strict`, zero framework):

**Layer A — mocked unit tests (no browser, no real sockets).** Use a
`MockWebSocket extends EventEmitter` (implements `readyState`, `send`, `close`, `ping`)
and inject clients straight into the bridge's internal Maps. This makes reliability
logic deterministic and fast to test:

```javascript
class MockWebSocket extends EventEmitter {
  constructor() { super(); this.readyState = 1; this.sent = []; this.closed = false; }
  send(d) { this.sent.push(JSON.parse(d)); }
  close(code, reason) { this.readyState = 3; this.closed = true; this.closeCode = code; }
  ping() { this.pinged = true; }
}
// Then assert: zombie eviction (stale lastAppMsg closes the socket), pong updates
// lastPing but NOT lastAppMsg, keepalive/response DO update lastAppMsg, request/response
// correlation resolves the right promise, TIMEOUT code on expiry, backoff math, etc.
```

**Layer B — real integration tests** against a running server
(`node server.js --standalone`): open a real `ws` client, wait for `connection_init`,
send tool calls, assert responses and the `/health` endpoint. A `nextMessage(ws, filter,
timeout)` helper keeps these readable.

> Keep Layer A large (fast, deterministic) and Layer B small (proves the wire actually
> works). Most reliability bugs — timeouts, eviction, correlation, error codes — are
> provable in Layer A without a browser at all.
