#!/usr/bin/env node
// mermaid-render-server — mermaid.ink-compatible render server for internal deployment.
//
// Protocol (identical to mermaid.ink, already used by render-mermaid.sh):
//   GET /svg/pako:{base64}                     -> SVG
//   GET /img/pako:{base64}?type=png|jpeg|webp  -> raster image (default png)
//   where base64 = zlib(JSON {code, mermaid:{theme, themeVariables, ...}}).
//   Raw forms are also accepted for compatibility: base64(JSON) and base64(source).
//
// Rendering: puppeteer-core + system Chromium, bundling mermaid.min.js inline.
// The container installs chromium + fonts-noto-cjk via apt (internal-mirror friendly),
// so no Chrome download happens at runtime or build time.
//
// Env: PORT (default 9696), CHROME_PATH (default /usr/bin/chromium),
//      MERMAID_JS (default ./node_modules/mermaid/dist/mermaid.min.js),
//      RENDER_TIMEOUT (ms, default 60000), MAX_STATE_BYTES (default 1048576).

const http = require('http');
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { URL } = require('url');

const PORT = parseInt(process.env.PORT || '9696', 10);
const CHROME_PATH =
  process.env.CHROME_PATH ||
  process.env.PUPPETEER_EXECUTABLE_PATH ||
  '/usr/bin/chromium';
const MERMAID_JS =
  process.env.MERMAID_JS || path.join(__dirname, 'node_modules', 'mermaid', 'dist', 'mermaid.min.js');
const RENDER_TIMEOUT = parseInt(process.env.RENDER_TIMEOUT || '60000', 10);
const MAX_STATE_BYTES = parseInt(process.env.MAX_STATE_BYTES || '1048576', 10);

let browserPromise = null;

function getBrowser() {
  if (!browserPromise) {
    const puppeteer = require('puppeteer-core');
    browserPromise = puppeteer
      .launch({
        executablePath: CHROME_PATH,
        headless: true,
        args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
      })
      .catch((err) => {
        browserPromise = null;
        throw err;
      });
  }
  return browserPromise;
}

const MERMAID_JS_CONTENT = fs.existsSync(MERMAID_JS)
  ? fs.readFileSync(MERMAID_JS, 'utf8')
  : null;

function pageHtml(svgOrEmpty) {
  return `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>*{margin:0;padding:0}html,body{background:white}</style>
</head><body>${svgOrEmpty}
<script>${MERMAID_JS_CONTENT}</script>
</body></html>`;
}

function decodeState(raw) {
  let text;
  if (raw.startsWith('pako:')) {
    const buf = zlib.inflateSync(Buffer.from(raw.slice(5), 'base64'));
    if (buf.length > MAX_STATE_BYTES) throw new Error('state too large');
    text = buf.toString('utf8');
  } else {
    text = Buffer.from(raw, 'base64').toString('utf8');
  }
  try {
    const obj = JSON.parse(text);
    return { code: String(obj.code || ''), config: obj.mermaid || {} };
  } catch (e) {
    return { code: text, config: {} };
  }
}

function withTimeout(promise, ms, message) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error(message || 'render timeout')), ms)),
  ]);
}

async function renderSvg(code, config) {
  if (!MERMAID_JS_CONTENT) throw new Error('mermaid.min.js not found (run npm install)');
  const browser = await getBrowser();
  const page = await browser.newPage();
  try {
    await page.setContent(pageHtml(''), { waitUntil: 'load', timeout: RENDER_TIMEOUT });
    const svg = await withTimeout(
      page.evaluate(
        async ({ code, config }) => {
          window.mermaid.initialize(
            Object.assign({ startOnLoad: false, securityLevel: 'loose' }, config || {})
          );
          const { svg } = await window.mermaid.render('mmd', code);
          return svg;
        },
        { code, config }
      ),
      RENDER_TIMEOUT,
      'mermaid render timeout'
    );
    return svg;
  } finally {
    await page.close();
  }
}

async function renderImage(code, config, type) {
  const svg = await renderSvg(code, config);
  const browser = await getBrowser();
  const page = await browser.newPage();
  try {
    await page.setContent(pageHtml(svg), { waitUntil: 'load', timeout: RENDER_TIMEOUT });
    const box = await withTimeout(
      page.evaluate(() => {
        const el = document.querySelector('svg');
        const r = el.getBoundingClientRect();
        return { x: r.x, y: r.y, width: r.width, height: r.height };
      }),
      RENDER_TIMEOUT,
      'measure timeout'
    );
    const pad = 12;
    const shotOpts = {
      type: type === 'jpeg' ? 'jpeg' : type === 'webp' ? 'webp' : 'png',
      clip: {
        x: Math.max(0, Math.floor(box.x) - pad),
        y: Math.max(0, Math.floor(box.y) - pad),
        width: Math.ceil(box.width) + pad * 2,
        height: Math.ceil(box.height) + pad * 2,
      },
    };
    if (type === 'jpeg') shotOpts.quality = 90; // png/webp reject 'quality'
    return await withTimeout(
      page.screenshot(shotOpts),
      RENDER_TIMEOUT,
      'screenshot timeout'
    );
  } finally {
    await page.close();
  }
}

function send(res, status, contentType, body) {
  res.writeHead(status, { 'content-type': contentType });
  res.end(body);
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, 'http://localhost');
    if (url.pathname === '/healthz') {
      return send(res, 200, 'text/plain', 'ok');
    }
    let pathname;
    try {
      pathname = decodeURIComponent(url.pathname);
    } catch (e) {
      return send(res, 400, 'text/plain', 'bad url encoding');
    }
    const m = pathname.match(/^\/(svg|img)\/(pako:)?([A-Za-z0-9+/=_-]+)$/);
    if (!m) {
      return send(res, 404, 'text/plain', 'Not Found — use /svg/pako:{state} or /img/pako:{state}?type=png');
    }
    const kind = m[1];
    const stateStr = (m[2] || '') + m[3];
    const type = (url.searchParams.get('type') || 'png').toLowerCase();
    if (kind === 'img' && !['png', 'jpeg', 'webp'].includes(type)) {
      return send(res, 400, 'text/plain', 'type must be png|jpeg|webp');
    }
    let state;
    try {
      state = decodeState(stateStr);
    } catch (e) {
      return send(res, 400, 'text/plain', 'invalid state: ' + e.message);
    }
    if (!state.code || !state.code.trim()) {
      return send(res, 400, 'text/plain', 'empty diagram source');
    }
    if (kind === 'svg') {
      const svg = await renderSvg(state.code, state.config);
      return send(res, 200, 'image/svg+xml; charset=utf-8', svg);
    }
    const img = await renderImage(state.code, state.config, type);
    const contentType =
      type === 'jpeg' ? 'image/jpeg' : type === 'webp' ? 'image/webp' : 'image/png';
    return send(res, 200, contentType, img);
  } catch (err) {
    const msg = String((err && err.message) || err);
    if (/browser|chrome|chromium|executable/i.test(msg)) {
      return send(res, 503, 'text/plain', 'renderer unavailable: ' + msg);
    }
    return send(res, 422, 'text/plain', 'render error: ' + msg.slice(0, 400));
  }
});

server.listen(PORT, () => {
  console.log(`[mermaid-render-server] listening on http://0.0.0.0:${PORT}`);
  console.log(`[mermaid-render-server] chrome: ${CHROME_PATH}`);
  console.log(`[mermaid-render-server] mermaid.js: ${MERMAID_JS}`);
});
