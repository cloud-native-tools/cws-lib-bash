/**
 * browser-utils bridge — controller client library.
 *
 * Connects to the relay server as a "controller" and issues commands with
 * promise-based request/response correlation and per-request timeouts.
 *
 * Usage:
 *   import { BridgeClient } from './client.js';
 *   const bridge = await BridgeClient.connect();
 *   await bridge.navigate('https://example.com');
 *   const title = await bridge.evaluate('document.title');
 *   await bridge.saveScreenshot('/tmp/shot.png');
 *   bridge.close();
 */

import WebSocket from 'ws';
import { randomUUID } from 'node:crypto';
import { writeFileSync } from 'node:fs';

const WS_PORT = parseInt(process.env.BRIDGE_WS_PORT || '8777', 10);
const TOKEN = process.env.BRIDGE_TOKEN || null;

export class BridgeClient {
  constructor(ws) {
    this.ws = ws;
    this.pending = new Map(); // requestId -> { resolve, reject, timer }
    this.ws.on('message', (raw) => {
      let msg; try { msg = JSON.parse(raw.toString()); } catch { return; }
      if (msg.requestId && this.pending.has(msg.requestId)) {
        const p = this.pending.get(msg.requestId);
        this.pending.delete(msg.requestId);
        clearTimeout(p.timer);
        if (msg.error) { const e = new Error(msg.error); if (msg.code) e.code = msg.code; p.reject(e); }
        else p.resolve(msg.result);
      }
    });
  }

  static connect({ port = WS_PORT, token = TOKEN, timeout = 5000 } = {}) {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(`ws://127.0.0.1:${port}`, { maxPayload: 60_000_000 });
      const timer = setTimeout(() => reject(new Error('Connection timed out')), timeout);
      ws.on('error', (err) => { clearTimeout(timer); reject(err); });
      ws.on('message', function onInit(raw) {
        let msg; try { msg = JSON.parse(raw.toString()); } catch { return; }
        if (msg.type === 'connection_init') {
          clearTimeout(timer);
          ws.off('message', onInit);
          ws.send(JSON.stringify({ type: 'controller_init', ...(token && { token }) }));
          resolve(new BridgeClient(ws));
        }
      });
    });
  }

  /** Send a command and await its result. */
  send(command, params = {}, timeout = 15000) {
    const requestId = randomUUID();
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(requestId);
        const e = new Error(`Command ${command} timed out after ${timeout}ms`); e.code = 'TIMEOUT'; reject(e);
      }, timeout + 1000); // give the server's own timeout a chance to answer first
      this.pending.set(requestId, { resolve, reject, timer });
      this.ws.send(JSON.stringify({ type: 'command', requestId, command, params, timeout }));
    });
  }

  // Convenience wrappers
  status() { return this.send('status', {}, 5000); }
  listTabs() { return this.send('listTabs', {}, 5000); }
  getContext(tabId) { return this.send('getContext', { tabId }, 5000); }
  navigate(url, opts = {}) { return this.send('navigate', { url, ...opts }, opts.timeout || 35000); }
  evaluate(expression, tabId) { return this.send('evaluate', { expression, tabId }, 30000); }
  click(selector, tabId) { return this.send('click', { selector, tabId }, 10000); }
  fill(selector, text, tabId) { return this.send('fill', { selector, text, tabId }, 10000); }
  waitFor(selector, opts = {}) { return this.send('waitFor', { selector, ...opts }, (opts.timeout || 10000) + 2000); }
  getText(selector, tabId) { return this.send('getText', { selector, tabId }, 10000); }
  getConsole(tabId) { return this.send('getConsole', { tabId }, 10000); }
  screenshot(opts = {}) { return this.send('screenshot', opts, 30000); }

  /** Take a screenshot and write it to disk; returns the path. */
  async saveScreenshot(path, opts = {}) {
    const { format, dataBase64 } = await this.screenshot(opts);
    writeFileSync(path, Buffer.from(dataBase64, 'base64'));
    return { path, format };
  }

  close() { try { this.ws.close(); } catch { /* ignore */ } }
}
