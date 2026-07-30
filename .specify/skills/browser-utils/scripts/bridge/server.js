#!/usr/bin/env node
/**
 * browser-utils WebSocket bridge — relay server.
 *
 * An EXTERNAL, dev-only automation mechanism owned by the browser-utils skill.
 * It relays commands between automation scripts ("controllers") and a minimal MV3
 * companion extension loaded into a real Chrome. This lets you drive/test a real,
 * logged-in browser over WebSocket WITHOUT embedding any WS code in the product
 * extension under test.
 *
 * Roles (both connect to this same WS port):
 *   - extension : the companion MV3 service worker (browser client). Exactly the
 *                 one that actually performs browser actions.
 *   - controller: an automation script / CLI issuing commands.
 *
 * Protocol (JSON per WS message):
 *   server -> client : { type:'connection_init', clientId }
 *   client -> server : { type:'extension_init' }                     (companion SW)
 *   client -> server : { type:'controller_init' }                    (automation)
 *   controller->server: { type:'command', requestId, command, params, timeout? }
 *   server->extension : { requestId, command, params }               (fresh id)
 *   extension->server : { requestId, result } | { requestId, error, code }
 *   server->controller: { requestId, result } | { requestId, error, code }
 *   extension->server : { type:'keepalive' }                         (every ~20s)
 *
 * Security: binds 127.0.0.1 only. If BRIDGE_TOKEN is set, every client MUST send
 * it in its *_init message ({ token }) or the socket is closed. This is a local
 * developer tool — never expose the port beyond localhost, never ship it.
 */

import { WebSocketServer } from 'ws';
import { randomUUID } from 'node:crypto';
import { createServer as createHttpServer } from 'node:http';

const HOST = '127.0.0.1';
const WS_PORT = parseInt(process.env.BRIDGE_WS_PORT || '8777', 10);
const HEALTH_PORT = parseInt(process.env.BRIDGE_HEALTH_PORT || '8778', 10);
const TOKEN = process.env.BRIDGE_TOKEN || null;
const DEFAULT_TIMEOUT = parseInt(process.env.BRIDGE_TIMEOUT || '15000', 10);
const HEARTBEAT_CHECK = 15_000;
const APP_MSG_TIMEOUT = 45_000;   // zombie eviction: 2 missed 20s keepalives
const PONG_TIMEOUT = 120_000;

const log = (...a) => console.error(`[bridge ${new Date().toISOString()}]`, ...a);

/** ws -> { id, role, lastPing, lastAppMsg, connectedAt } */
const clients = new Map();
/** requestId -> { resolve, reject, timer } */
const pending = new Map();

const extensions = () => [...clients.entries()].filter(([, i]) => i.role === 'extension');

function send(ws, data) {
  if (ws.readyState === 1) ws.send(JSON.stringify(data));
}

/** Resolve once an extension client is present, or reject after timeoutMs. */
function waitForExtension(timeoutMs = 5000) {
  if (extensions().length > 0) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const started = Date.now();
    const iv = setInterval(() => {
      if (extensions().length > 0) { clearInterval(iv); resolve(); }
      else if (Date.now() - started > timeoutMs) {
        clearInterval(iv);
        const e = new Error('No companion extension connected');
        e.code = 'NO_BROWSER';
        reject(e);
      }
    }, 100);
  });
}

async function onCommand(ws, msg) {
  const controllerReqId = msg.requestId || randomUUID();
  const timeout = msg.timeout || DEFAULT_TIMEOUT;
  try {
    await waitForExtension();
  } catch (err) {
    send(ws, { requestId: controllerReqId, error: err.message, code: err.code });
    return;
  }
  // Fresh id for the extension leg to avoid collisions.
  const extReqId = randomUUID();
  const timer = setTimeout(() => {
    pending.delete(extReqId);
    send(ws, { requestId: controllerReqId, error: `Request timed out after ${timeout}ms`, code: 'TIMEOUT' });
  }, timeout);
  pending.set(extReqId, {
    resolve: (result) => send(ws, { requestId: controllerReqId, result }),
    reject: (err) => send(ws, { requestId: controllerReqId, error: err.message, code: err.code || 'ERROR' }),
    timer,
  });
  const [firstExt] = extensions();
  send(firstExt[0], { requestId: extReqId, command: msg.command, params: msg.params || {} });
}

function onMessage(ws, raw) {
  let msg;
  try { msg = JSON.parse(raw.toString()); } catch { log('bad JSON'); return; }

  const info = clients.get(ws);
  if (info) { info.lastPing = Date.now(); info.lastAppMsg = Date.now(); }

  // Role handshake
  if (msg.type === 'extension_init' || msg.type === 'controller_init') {
    if (TOKEN && msg.token !== TOKEN) { send(ws, { type: 'unauthorized' }); ws.close(1008, 'Bad token'); return; }
    if (info) info.role = msg.type === 'extension_init' ? 'extension' : 'controller';
    log(`${info?.role} identified (${info?.id?.slice(0, 8)})`);
    return;
  }
  if (TOKEN && info && !info.role) { ws.close(1008, 'Token required'); return; }

  if (msg.type === 'keepalive' || msg.type === 'pong') return;

  // Controller command
  if (msg.type === 'command') { onCommand(ws, msg); return; }

  // Extension response to a pending request
  if (msg.requestId && pending.has(msg.requestId)) {
    const p = pending.get(msg.requestId);
    pending.delete(msg.requestId);
    clearTimeout(p.timer);
    if (msg.error) { const e = new Error(msg.error); if (msg.code) e.code = msg.code; p.reject(e); }
    else p.resolve(msg.result ?? msg);
    return;
  }
}

function checkHeartbeats() {
  const now = Date.now();
  for (const [ws, info] of clients) {
    if (info.role === 'extension' && now - (info.lastAppMsg || info.connectedAt) > APP_MSG_TIMEOUT) {
      log('evict zombie extension', info.id.slice(0, 8));
      ws.close(1000, 'App heartbeat timeout'); clients.delete(ws);
    } else if (now - info.lastPing > PONG_TIMEOUT) {
      ws.close(1000, 'Heartbeat timeout'); clients.delete(ws);
    } else {
      ws.ping();
    }
  }
}

function start() {
  const wss = new WebSocketServer({ host: HOST, port: WS_PORT, maxPayload: 60_000_000 });

  wss.on('connection', (ws) => {
    const id = randomUUID();
    clients.set(ws, { id, role: null, lastPing: Date.now(), lastAppMsg: Date.now(), connectedAt: Date.now() });
    send(ws, { type: 'connection_init', clientId: id });
    ws.on('message', (raw) => onMessage(ws, raw));
    ws.on('pong', () => { const i = clients.get(ws); if (i) i.lastPing = Date.now(); });
    ws.on('close', () => { clients.delete(ws); log('client closed', id.slice(0, 8)); });
    ws.on('error', (e) => log('client error', e.message));
  });

  wss.on('listening', () => log(`WS listening on ws://${HOST}:${WS_PORT}${TOKEN ? ' (token required)' : ''}`));
  wss.on('error', (e) => { log('server error', e.message); process.exit(1); });

  const hb = setInterval(checkHeartbeats, HEARTBEAT_CHECK);

  // Minimal health endpoint
  const health = createHttpServer((req, res) => {
    if (req.url === '/health') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        status: 'ok',
        extensions: extensions().length,
        controllers: [...clients.values()].filter(i => i.role === 'controller').length,
        pending: pending.size,
        uptime: process.uptime(),
      }));
    } else { res.writeHead(404); res.end('Not Found'); }
  });
  health.listen(HEALTH_PORT, HOST, () => log(`health on http://${HOST}:${HEALTH_PORT}/health`));

  const shutdown = () => {
    log('shutting down');
    clearInterval(hb);
    for (const [, p] of pending) { clearTimeout(p.timer); p.reject(new Error('Server shutting down')); }
    pending.clear();
    for (const [ws] of clients) ws.close(1000, 'Server shutting down');
    wss.close(); health.close();
    process.exit(0);
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

start();
