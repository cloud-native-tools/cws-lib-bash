// svg-to-png-cjk.cjs — Render a Mermaid SVG to high-quality PNG with CJK font support
// Uses Playwright to render SVG in a browser with system CJK fonts.
// Use when the primary PNG output is missing/low-quality or you need a custom
// scale factor (e.g. server PNG failed, or a wide diagram needs down-scaling).
//
// Usage: node svg-to-png-cjk.cjs <input.svg> <output.png> [scaleFactor]

const { chromium } = require('playwright-core');
const { readFileSync, writeFileSync, statSync, existsSync, readdirSync } = require('fs');
const { resolve } = require('path');

const BROWSER_PATHS = [
  process.env.PLAYWRIGHT_CHROMIUM_PATH,
  process.env.PUPPETEER_EXECUTABLE_PATH,
  '/Users/liuqiming.lqm/Library/Caches/ms-playwright/chromium-1223/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/chromium-browser',
  '/usr/bin/chromium',
].filter(Boolean);

// Browser cache dirs whose contents follow a versioned subdirectory layout.
const BROWSER_CACHE_DIRS = [
  '/root/.cache/puppeteer/chrome',
  '/root/.cache/ms-playwright',
  process.env.PUPPETEER_CACHE_DIR,
].filter(Boolean);

function findBrowser() {
  for (const p of BROWSER_PATHS) {
    if (p && existsSync(p)) return p;
  }
  // Newest cached chrome/chromium binary in puppeteer/playwright cache dirs.
  for (const dir of BROWSER_CACHE_DIRS) {
    if (!dir || !existsSync(dir)) continue;
    const candidates = [];
    for (const sub of readdirSync(dir)) {
      walk(dir + '/' + sub, candidates);
    }
    if (candidates.length > 0) {
      candidates.sort();
      return candidates[candidates.length - 1];
    }
  }
  return null;
}

function walk(dir, out) {
  let entries;
  try { entries = readdirSync(dir); } catch (e) { return; }
  for (const e of entries) {
    const p = dir + '/' + e;
    if (/chrome(-headless)?(-[^/]*)?$/.test(e)) { out.push(p); continue; }
    try {
      if (require('fs').statSync(p).isDirectory()) walk(p, out);
    } catch (err) {}
  }
}

async function main() {
  const svgPath = process.argv[2];
  const pngPath = process.argv[3];
  const scaleFactor = parseInt(process.argv[4] || '2');

  if (!svgPath || !pngPath) {
    console.error('Usage: node svg-to-png-cjk.cjs <input.svg> <output.png> [scaleFactor]');
    process.exit(1);
  }

  const execPath = findBrowser();
  if (!execPath) {
    console.error('No Chromium/Chrome browser found. Set PLAYWRIGHT_CHROMIUM_PATH.');
    process.exit(1);
  }

  const svgContent = readFileSync(svgPath, 'utf-8');

  // Expand viewBox to prevent CJK text clipping
  const vbMatch = svgContent.match(/viewBox="(\d+)\s+(\d+)\s+(\d+)\s+(\d+)"/);
  let vbW = 800, vbH = 600;
  if (vbMatch) {
    vbW = parseInt(vbMatch[3]);
    vbH = parseInt(vbMatch[4]);
    const expandW = Math.ceil(vbW * 2.5);
    const expandH = Math.ceil(vbH * 1.5);
    svgContent = svgContent.replace(/viewBox="[^"]*"/, `viewBox="0 0 ${expandW} ${expandH}"`);
    svgContent = svgContent.replace(/width="[^"]*"/, `width="${expandW}"`);
    svgContent = svgContent.replace(/height="[^"]*"/, `height="${expandH}"`);
    svgContent = svgContent.replace(
      /style="width:[^;]*;height:[^;]*;/,
      `style="width:${expandW}px;height:${expandH}px;`
    );
  }

  // HTML wrapper with CJK font stack
  const html = `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  * { margin: 0; padding: 0; }
  body { background: white; }
  svg text {
    font-family: "Noto Sans CJK SC", "PingFang SC", "Hiragino Sans GB",
                 "Microsoft YaHei", "WenQuanYi Micro Hei",
                 Arial, Helvetica, sans-serif !important;
  }
</style>
</head><body>${svgContent}</body></html>`;

  const htmlPath = pngPath.replace('.png', '.cjk-render.html');
  writeFileSync(htmlPath, html);

  // Render with Playwright
  const vpW = Math.min(Math.ceil(vbW * 2.5 / scaleFactor), 5000);
  const vpH = Math.min(Math.ceil(vbH * 1.5 / scaleFactor), 4000);

  const browser = await chromium.launch({ headless: true, executablePath: execPath });
  const ctx = await browser.newContext({
    deviceScaleFactor: scaleFactor,
    viewport: { width: vpW, height: vpH }
  });
  const page = await ctx.newPage();
  await page.goto('file://' + resolve(htmlPath), { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);

  // Measure actual content bounds and trim
  const bbox = await page.evaluate(() => {
    const svg = document.querySelector('svg');
    if (!svg) return null;
    const els = svg.querySelectorAll('rect, text, line, path, polygon, polyline, ellipse, circle');
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    els.forEach(el => {
      try {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && r.height > 0) {
          minX = Math.min(minX, r.left);
          minY = Math.min(minY, r.top);
          maxX = Math.max(maxX, r.right);
          maxY = Math.max(maxY, r.bottom);
        }
      } catch(e) {}
    });
    if (minX === Infinity) return null;
    return {
      x: Math.max(0, Math.floor(minX) - 15),
      y: Math.max(0, Math.floor(minY) - 15),
      width: Math.ceil(maxX - minX) + 30,
      height: Math.ceil(maxY - minY) + 30
    };
  });

  if (bbox) {
    await page.screenshot({ path: pngPath, clip: bbox, type: 'png' });
  } else {
    await page.screenshot({ path: pngPath, fullPage: true, type: 'png' });
  }

  await browser.close();

  const fileSize = statSync(pngPath).size;
  const dims = bbox ? `${bbox.width * scaleFactor}x${bbox.height * scaleFactor}` : 'fullPage';
  console.log(`[svg-to-png-cjk] PNG saved: ${pngPath} (${dims}, ${Math.round(fileSize/1024)}KB)`);
}

main().catch(e => { console.error(e); process.exit(1); });
