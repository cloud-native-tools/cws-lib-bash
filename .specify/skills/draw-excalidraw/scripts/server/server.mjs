// server.mjs — self-hosted Excalidraw render service (no framework).
//
// Endpoints:
//   GET  /health            -> {"ok":true}
//   POST /render            -> scene JSON in, SVG or PNG bytes out
//   POST /render-mermaid    -> Mermaid text in, SVG or PNG bytes out
//   POST /mermaid-to-scene  -> Mermaid text in, Excalidraw scene JSON out
//   GET  /                  -> render.html (internal page driving the exporter)
//
// Body of /render (all fields optional except the scene itself):
//   { "scene": {"elements":[...], "appState":{...}, "files":{...}},
//     "format": "svg" | "png",        // default svg
//     "scale": 2,                      // png only (default 2)
//     "padding": 16,
//     "viewBackgroundColor": "#ffffff",
//     "darkMode": false,
//     "exportBackground": true,
//     "mime": "image/png" | "image/jpeg" }
//   For convenience, {"elements":[...]} at top level is also accepted.
//
// Env:
//   EXCALIDRAW_PORT         default 8383
//   EXCALIDRAW_HOST         default 127.0.0.1 (set 0.0.0.0 in containers)
//   EXCALIDRAW_CHROMIUM_PATH  explicit browser binary; when unset we probe:
//     macOS Google Chrome -> Playwright cache -> chromium/google-chrome in PATH
//
// The browser is launched once (lazy) and reused; render requests are
// serialized to keep memory flat.

import http from "node:http";
import { readFile, stat } from "node:fs/promises";
import { existsSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import os from "node:os";
import { chromium } from "playwright-core";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const STATIC_DIR = path.join(__dirname, "static");
const PORT = Number(process.env.EXCALIDRAW_PORT || 8383);
const HOST = process.env.EXCALIDRAW_HOST || "127.0.0.1";
const MAX_BODY = 64 * 1024 * 1024;

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".woff2": "font/woff2",
  ".woff": "font/woff",
  ".ttf": "font/ttf",
  ".json": "application/json; charset=utf-8",
};

function log(...args) {
  console.log("[excalidraw-render]", ...args);
}

// ── Chromium executable resolution ────────────────────────────────────────────

function findChromium() {
  if (process.env.EXCALIDRAW_CHROMIUM_PATH) {
    return process.env.EXCALIDRAW_CHROMIUM_PATH;
  }
  const candidates = [];
  if (process.platform === "darwin") {
    candidates.push(
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    );
    // Playwright-managed builds (works with playwright-core, any revision).
    const cache = path.join(os.homedir(), "Library/Caches/ms-playwright");
    if (existsSync(cache)) {
      let dirs = [];
      try {
        dirs = readdirSync(cache)
          .filter((d) => /^chromium(-\d+)?$/.test(d))
          .sort()
          .reverse()
          .map((d) => path.join(cache, d));
      } catch {}
      for (const d of dirs) {
        candidates.push(
          path.join(d, "chrome-mac/Chromium.app/Contents/MacOS/Chromium"),
          path.join(d, "chrome-mac/headless_shell")
        );
      }
    }
  } else {
    for (const bin of [
      "chromium",
      "chromium-browser",
      "google-chrome",
      "google-chrome-stable",
    ]) {
      const p = ["/usr/bin", "/usr/local/bin", "/opt/google/chrome"]
        .map((d) => path.join(d, bin))
        .find(existsSync);
      if (p) candidates.push(p);
    }
  }
  const found = candidates.find(existsSync);
  if (!found) {
    throw new Error(
      "No Chromium/Chrome found. Install one or set EXCALIDRAW_CHROMIUM_PATH."
    );
  }
  return found;
}

// ── Browser singleton + request serialization ────────────────────────────────

let browserPromise = null;
function getBrowser() {
  if (!browserPromise) {
    const executablePath = findChromium();
    log("launching browser:", executablePath);
    browserPromise = chromium.launch({
      executablePath,
      args: ["--no-sandbox", "--disable-dev-shm-usage", "--hide-scrollbars"],
    });
  }
  return browserPromise;
}

let queue = Promise.resolve();
function serialized(fn) {
  const run = queue.then(fn, fn);
  queue = run.then(
    () => undefined,
    () => undefined
  );
  return run;
}

async function renderInBrowser(payload, entry) {
  const browser = await getBrowser();
  const context = await browser.newContext({
    viewport: { width: 1280, height: 960 },
    deviceScaleFactor: 1,
  });
  try {
    const page = await context.newPage();
    page.on("pageerror", (err) => log("page error:", String(err)));
    await page.goto(`http://${HOST === "0.0.0.0" ? "127.0.0.1" : HOST}:${PORT}/render.html`, {
      waitUntil: "load",
    });
    await page.waitForFunction("window.__renderReady === true", null, {
      timeout: 30000,
    });
    return await page.evaluate(
      ([entryFn, pl]) => window[entryFn](pl),
      [entry, payload]
    );
  } finally {
    await context.close();
  }
}

// ── HTTP plumbing ────────────────────────────────────────────────────────────

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;
    req.on("data", (c) => {
      size += c.length;
      if (size > MAX_BODY) {
        reject(new Error("body too large"));
        req.destroy();
        return;
      }
      chunks.push(c);
    });
    req.on("end", () => resolve(Buffer.concat(chunks).toString("utf-8")));
    req.on("error", reject);
  });
}

function send(res, status, body, type) {
  res.writeHead(status, {
    "Content-Type": type,
    "Access-Control-Allow-Origin": "*",
    "Cache-Control": "no-store",
  });
  res.end(body);
}

function sendJson(res, status, obj) {
  send(res, status, JSON.stringify(obj), "application/json; charset=utf-8");
}

async function serveStatic(res, urlPath) {
  const rel = urlPath === "/" ? "/render.html" : urlPath;
  const file = path.normalize(path.join(STATIC_DIR, rel));
  if (!file.startsWith(STATIC_DIR)) return sendJson(res, 403, { error: "forbidden" });
  try {
    const st = await stat(file);
    if (!st.isFile()) throw new Error("not a file");
    const data = await readFile(file);
    send(res, 200, data, MIME[path.extname(file)] || "application/octet-stream");
  } catch {
    sendJson(res, 404, { error: "not found" });
  }
}

function dataUrlToBuffer(dataUrl) {
  const m = /^data:([^;]+);base64,(.*)$/.exec(dataUrl);
  if (!m) throw new Error("unexpected data URL");
  return Buffer.from(m[2], "base64");
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);

    if (req.method === "GET" && url.pathname === "/health") {
      return sendJson(res, 200, { ok: true, service: "excalidraw-render" });
    }

    if (req.method === "GET") {
      return await serveStatic(res, url.pathname);
    }

    if (req.method === "OPTIONS") {
      res.writeHead(204, {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
      });
      return res.end();
    }

    if (req.method !== "POST") return sendJson(res, 405, { error: "method not allowed" });

    const body = await readBody(req);
    let payload;
    try {
      payload = JSON.parse(body || "{}");
    } catch {
      return sendJson(res, 400, { error: "invalid JSON body" });
    }

    if (url.pathname === "/render") {
      if (!(payload.scene?.elements ?? payload.elements)) {
        return sendJson(res, 400, { error: "missing scene.elements" });
      }
      const out = await serialized(() => renderInBrowser(payload, "__renderScene"));
      if (out.format === "svg") {
        return send(res, 200, out.data, "image/svg+xml; charset=utf-8");
      }
      return send(res, 200, dataUrlToBuffer(out.data), payload.mime === "image/jpeg" ? "image/jpeg" : "image/png");
    }

    if (url.pathname === "/render-mermaid") {
      if (!payload.mermaid) return sendJson(res, 400, { error: "missing mermaid" });
      const out = await serialized(() =>
        renderInBrowser({ ...payload, scene: undefined }, "__renderMermaidScene")
      );
      if (out.format === "svg") {
        return send(res, 200, out.data, "image/svg+xml; charset=utf-8");
      }
      return send(res, 200, dataUrlToBuffer(out.data), "image/png");
    }

    if (url.pathname === "/mermaid-to-scene") {
      if (!payload.mermaid) return sendJson(res, 400, { error: "missing mermaid" });
      const { elements, files } = await serialized(() =>
        renderInBrowser(payload, "__mermaidToScene")
      );
      return sendJson(res, 200, {
        type: "excalidraw",
        version: 2,
        source: "excalidraw-render-server",
        elements,
        appState: { viewBackgroundColor: "#ffffff", gridSize: null },
        files,
      });
    }

    return sendJson(res, 404, { error: "unknown endpoint" });
  } catch (err) {
    log("request failed:", err?.message || err);
    try {
      sendJson(res, 500, { error: String(err?.message || err) });
    } catch {}
  }
});

// /render-mermaid = mermaid -> scene -> image, all in one page round-trip.
// Implemented browser-side by composing the two exposed helpers.
// (Kept in server for API completeness; see render-entry.js for the parts.)

server.listen(PORT, HOST, () => {
  log(`listening on http://${HOST}:${PORT}`);
});

// Graceful shutdown. IMPORTANT: once playwright has launched a browser, the
// default SIGTERM termination no longer works (the process survives and holds
// the port). Handle signals explicitly: close the browser (kills chromium
// children), then exit.
let shuttingDown = false;
async function shutdown(signal) {
  if (shuttingDown) return;
  shuttingDown = true;
  log(`received ${signal}, shutting down`);
  try {
    if (browserPromise) {
      const browser = await browserPromise;
      await browser.close();
    }
  } catch {}
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 3000).unref();
}
process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
