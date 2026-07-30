/**
 * browser-utils bridge — companion service worker (DEV ONLY).
 *
 * WebSocket client to the local relay server. Survives MV3 SW suspension with a
 * three-layer keepalive (ping / alarms / offscreen) and reconnects with capped
 * backoff. Executes a small whitelist of automation commands against real tabs.
 *
 * Distilled from a production browser-bridge; scoped down to testing/automation.
 */

const WS_URL = `ws://127.0.0.1:${8777}`; // must match server BRIDGE_WS_PORT
const TOKEN = ''; // set to match BRIDGE_TOKEN if the server requires one
const RECONNECT_BASE = 3000;
const RECONNECT_MAX = 8000;
const PING_INTERVAL = 20_000;
const ALARM_NAME = 'bridge-keepalive';
const ALARM_PERIOD = 0.4; // ~24s — wakes a suspended SW
const CDP_IDLE_MS = 5000;

let ws = null;
let reconnectDelay = RECONNECT_BASE;
let reconnectTimer = null;
let pingTimer = null;
let connecting = false;
let lastServerMessage = Date.now();

/** tabId -> { attached, timer } */
const cdpSessions = new Map();

// ---------------------------------------------------------------------------
// Layer 3: offscreen keepalive
// ---------------------------------------------------------------------------
async function ensureOffscreen() {
  try {
    const has = await chrome.offscreen.hasDocument().catch(() => false);
    if (!has) {
      await chrome.offscreen.createDocument({
        url: 'offscreen.html',
        reasons: ['BLOBS'],
        justification: 'Keepalive ping to prevent service worker termination',
      });
    }
  } catch (e) { /* ignore */ }
}

// ---------------------------------------------------------------------------
// WebSocket connection
// ---------------------------------------------------------------------------
function connect() {
  if (connecting || (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN))) return;
  connecting = true;
  try { ws = new WebSocket(WS_URL); }
  catch (e) { connecting = false; scheduleReconnect(); return; }

  ws.onopen = () => {
    connecting = false;
    reconnectDelay = RECONNECT_BASE;
    lastServerMessage = Date.now();
    ws.send(JSON.stringify({ type: 'extension_init', ...(TOKEN && { token: TOKEN }) }));
    clearInterval(pingTimer);
    pingTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'keepalive' }));
    }, PING_INTERVAL);
    console.log('[bridge] connected');
  };
  ws.onmessage = (ev) => {
    lastServerMessage = Date.now();
    let msg; try { msg = JSON.parse(ev.data); } catch { return; }
    handleServerMessage(msg);
  };
  ws.onclose = () => { connecting = false; clearInterval(pingTimer); scheduleReconnect(); };
  ws.onerror = () => { /* onclose will follow */ };
}

function scheduleReconnect() {
  clearTimeout(reconnectTimer);
  reconnectTimer = setTimeout(() => {
    reconnectDelay = Math.min(reconnectDelay * 1.5, RECONNECT_MAX);
    connect();
  }, reconnectDelay);
}

function reply(requestId, result) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ requestId, result }));
}
function replyError(requestId, err) {
  const payload = { requestId, error: err?.message || String(err) };
  if (err?.code) payload.code = err.code;
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(payload));
}

async function handleServerMessage(msg) {
  if (msg.type === 'connection_init') return;
  if (!msg.requestId || !msg.command) return;
  try {
    const result = await dispatch(msg.command, msg.params || {});
    reply(msg.requestId, result);
  } catch (err) {
    console.warn('[bridge] command failed:', msg.command, err?.message);
    replyError(msg.requestId, err);
  }
}

// ---------------------------------------------------------------------------
// CDP helpers (evaluate + screenshot; auto-recover on silent detach)
// ---------------------------------------------------------------------------
async function cdpAcquire(tabId) {
  const s = cdpSessions.get(tabId);
  if (s?.attached) { clearTimeout(s.timer); s.timer = setTimeout(() => cdpRelease(tabId), CDP_IDLE_MS); return; }
  try { await chrome.debugger.attach({ tabId }, '1.3'); }
  catch (e) { const err = new Error(`CDP attach failed: ${e.message}`); err.code = 'CDP_ATTACH_FAILED'; throw err; }
  cdpSessions.set(tabId, { attached: true, timer: setTimeout(() => cdpRelease(tabId), CDP_IDLE_MS) });
}
async function cdpRelease(tabId) {
  const s = cdpSessions.get(tabId);
  if (!s?.attached) return;
  clearTimeout(s.timer); cdpSessions.delete(tabId);
  await chrome.debugger.detach({ tabId }).catch(() => {});
}
async function cdpCommand(tabId, method, params = {}) {
  await cdpAcquire(tabId);
  const s = cdpSessions.get(tabId);
  if (s) { clearTimeout(s.timer); s.timer = setTimeout(() => cdpRelease(tabId), CDP_IDLE_MS); }
  try { return await chrome.debugger.sendCommand({ tabId }, method, params); }
  catch (e) {
    if (!/not attached|Detached while handling/i.test(String(e?.message))) throw e;
    cdpSessions.delete(tabId);
    await chrome.debugger.attach({ tabId }, '1.3').catch(() => {});
    cdpSessions.set(tabId, { attached: true, timer: setTimeout(() => cdpRelease(tabId), CDP_IDLE_MS) });
    return chrome.debugger.sendCommand({ tabId }, method, params);
  }
}
chrome.debugger.onDetach.addListener((src) => {
  if (typeof src?.tabId === 'number' && cdpSessions.has(src.tabId)) {
    clearTimeout(cdpSessions.get(src.tabId).timer);
    cdpSessions.delete(src.tabId);
  }
});
chrome.tabs.onRemoved.addListener((tabId) => { if (cdpSessions.has(tabId)) cdpRelease(tabId); });

// ---------------------------------------------------------------------------
// Command dispatch (whitelist)
// ---------------------------------------------------------------------------
async function resolveTabId(params) {
  if (params.tabId) return params.tabId;
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) { const e = new Error('No active tab'); e.code = 'NO_TAB'; throw e; }
  return tab.id;
}

async function execInPage(tabId, func, args = []) {
  const [res] = await chrome.scripting.executeScript({ target: { tabId }, func, args, world: 'MAIN' });
  return res?.result;
}

async function dispatch(command, params) {
  switch (command) {
    case 'status':
      return { name: chrome.runtime.getManifest().name, version: chrome.runtime.getManifest().version };

    case 'listTabs': {
      const tabs = await chrome.tabs.query({});
      return tabs.map(t => ({ id: t.id, url: t.url, title: t.title, active: t.active }));
    }

    case 'getContext': {
      const tabId = await resolveTabId(params);
      const t = await chrome.tabs.get(tabId);
      return { tabId, url: t.url, title: t.title };
    }

    case 'navigate': {
      const url = params.url;
      if (!url) { const e = new Error('navigate requires url'); e.code = 'VALIDATION_ERROR'; throw e; }
      let tabId = params.tabId;
      if (tabId) await chrome.tabs.update(tabId, { url });
      else { const t = await chrome.tabs.create({ url, active: params.active !== false }); tabId = t.id; }
      await waitForTabComplete(tabId, params.timeout || 30000);
      const t = await chrome.tabs.get(tabId);
      return { tabId, url: t.url, title: t.title };
    }

    case 'evaluate': {
      const tabId = await resolveTabId(params);
      if (!params.expression) { const e = new Error('evaluate requires expression'); e.code = 'VALIDATION_ERROR'; throw e; }
      const { result, exceptionDetails } = await cdpCommand(tabId, 'Runtime.evaluate', {
        expression: params.expression, returnByValue: true, awaitPromise: true,
      });
      if (exceptionDetails) { const e = new Error(exceptionDetails.text || 'evaluate threw'); e.code = 'EVAL_ERROR'; throw e; }
      return result?.value;
    }

    case 'click': {
      const tabId = await resolveTabId(params);
      const ok = await execInPage(tabId, (sel) => {
        const el = document.querySelector(sel); if (!el) return false; el.click(); return true;
      }, [params.selector]);
      if (!ok) { const e = new Error(`Element not found: ${params.selector}`); e.code = 'NOT_FOUND'; throw e; }
      return { clicked: params.selector };
    }

    case 'type':
    case 'fill': {
      const tabId = await resolveTabId(params);
      const ok = await execInPage(tabId, (sel, text) => {
        const el = document.querySelector(sel); if (!el) return false;
        el.focus(); el.value = text;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
      }, [params.selector, params.text ?? '']);
      if (!ok) { const e = new Error(`Element not found: ${params.selector}`); e.code = 'NOT_FOUND'; throw e; }
      return { filled: params.selector };
    }

    case 'waitFor': {
      const tabId = await resolveTabId(params);
      const deadline = Date.now() + (params.timeout || 10000);
      while (Date.now() < deadline) {
        const found = await execInPage(tabId, (sel) => !!document.querySelector(sel), [params.selector]);
        if (found) return { found: params.selector };
        await new Promise(r => setTimeout(r, 200));
      }
      const e = new Error(`Timed out waiting for ${params.selector}`); e.code = 'TIMEOUT'; throw e;
    }

    case 'getText': {
      const tabId = await resolveTabId(params);
      return execInPage(tabId, (sel) => {
        const el = sel ? document.querySelector(sel) : document.body;
        return el ? el.innerText : null;
      }, [params.selector || null]);
    }

    case 'getConsole': {
      const tabId = await resolveTabId(params);
      return execInPage(tabId, () => window.__bridgeConsole || []);
    }

    case 'screenshot': {
      const tabId = await resolveTabId(params);
      const format = params.format === 'jpg' ? 'jpeg' : (params.format || 'png');
      const args = { format };
      if (format === 'jpeg' && params.quality) args.quality = params.quality;
      const { data } = await cdpCommand(tabId, 'Page.captureScreenshot', args);
      return { format, dataBase64: data }; // controller decides where to save
    }

    case 'getStorage': {
      // Reads the COMPANION extension's own storage (not the target extension's).
      return chrome.storage.local.get(params.keys ?? null);
    }

    default: {
      const e = new Error(`Unknown command: ${command}`); e.code = 'UNKNOWN_COMMAND'; throw e;
    }
  }
}

function waitForTabComplete(tabId, timeout) {
  return new Promise((resolve) => {
    const done = () => { chrome.tabs.onUpdated.removeListener(listener); clearTimeout(timer); resolve(); };
    const listener = (id, info) => { if (id === tabId && info.status === 'complete') done(); };
    const timer = setTimeout(done, timeout);
    chrome.tabs.onUpdated.addListener(listener);
    chrome.tabs.get(tabId).then(t => { if (t.status === 'complete') done(); }).catch(() => {});
  });
}

// ---------------------------------------------------------------------------
// Keepalive Layer 2 (alarms) + self-heal, and init
// ---------------------------------------------------------------------------
// Layer 3 handshake: receiving the offscreen ping wakes/keeps the SW alive.
chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg && msg.keepAlive) { sendResponse({ alive: true }); return; }
});

chrome.alarms.create(ALARM_NAME, { periodInMinutes: ALARM_PERIOD });
chrome.alarms.onAlarm.addListener((a) => {
  if (a.name !== ALARM_NAME) return;
  ensureOffscreen();
  if (!ws || ws.readyState !== WebSocket.OPEN) { clearTimeout(reconnectTimer); reconnectDelay = RECONNECT_BASE; connect(); }
  else if (Date.now() - lastServerMessage > 45_000) { ws.close(); reconnectDelay = RECONNECT_BASE; connect(); }
});

ensureOffscreen();
connect();
console.log('[bridge] service worker initialized');
