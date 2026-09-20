#!/usr/bin/env node
// ============================================================
// check-layout.mjs — coordinate hygiene check for fixed-layout
// graph configs (layout: 'none' with explicit x/y per node).
//
// Rationale (R1 review): hand-written fixed coordinates drift:
// nodes overlap or fall outside the canvas as the graph grows.
// Record the canvas size (and grid rules) in the config meta and
// run this check before delivery.
//
// Usage:
//   node scripts/check-layout.mjs <foo.config.json> [<foo.config.js> ...]
//
// Checks (graph series only, nodes with numeric x/y):
//   1. OUT_OF_BOUNDS — node bounding box outside the canvas
//      (canvas size from meta.canvasWidth / meta.canvasHeight,
//      fallback --width/--height, default 1200x800)
//   2. OVERLAP — pairwise bounding-box intersection between nodes
//
// Exit code: 0 = clean, 1 = problems found, 2 = usage/config error.
// ============================================================
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

function loadConfig(file) {
  let text = fs.readFileSync(file, 'utf8');
  if (file.endsWith('.js')) {
    const m = text.match(/window\.CHART_CONFIG\s*=\s*([\s\S]*?);\s*$/);
    if (!m) throw new Error(`cannot find 'window.CHART_CONFIG = ...;' in ${file}`);
    text = m[1];
  }
  return JSON.parse(text);
}

function toPx(value, total) {
  if (typeof value === 'number') return value;
  if (typeof value === 'string' && /^\d+(\.\d+)?%$/.test(value)) {
    return (parseFloat(value) / 100) * total;
  }
  return null;
}

function nodeSize(n) {
  const s = n.symbolSize;
  if (Array.isArray(s)) {
    const w = typeof s[0] === 'number' ? s[0] : 40;
    const h = typeof s[1] === 'number' ? s[1] : w;
    return [w, h];
  }
  const v = typeof s === 'number' ? s : 40;
  return [v, v];
}

export function checkLayout(cfg, opts = {}) {
  const problems = [];
  const W = cfg.meta?.canvasWidth ?? opts.width ?? 1200;
  const H = cfg.meta?.canvasHeight ?? opts.height ?? 800;

  // Support two config shapes:
  //  a) standard ECharts option: series[].data (graph series)
  //  b) config-driven flat shape: top-level nodes[] (this skill's
  //     recommended external config format, see sync-config.mjs)
  const series = Array.isArray(cfg.series) ? cfg.series : cfg.series ? [cfg.series] : [];
  const nodes = Array.isArray(cfg.nodes)
    ? cfg.nodes
    : series.flatMap((s) => (s.type === 'graph' ? s.data || [] : []));
  const fixed = nodes
    .map((n) => ({ ...n, px: toPx(n.x, W), py: toPx(n.y, H) }))
    .filter((n) => n.px !== null && n.py !== null);

  if (fixed.length === 0) {
    return { problems, nodeCount: nodes.length, fixedCount: 0 };
  }

  for (const n of fixed) {
    const [w, h] = nodeSize(n);
    if (n.px - w / 2 < 0 || n.px + w / 2 > W || n.py - h / 2 < 0 || n.py + h / 2 > H) {
      problems.push(`OUT_OF_BOUNDS ${n.name} (${n.px},${n.py}) size=${w}x${h} canvas=${W}x${H}`);
    }
  }

  // Partition zones (config-driven shape): rects must fit inside the canvas.
  for (const z of cfg.zones || []) {
    const zx = toPx(z.left, W);
    const zy = toPx(z.top, H);
    const zw = toPx(z.width, W);
    const zh = toPx(z.height, H);
    if (zx === null || zy === null || zw === null || zh === null) continue;
    if (zx < 0 || zy < 0 || zx + zw > W || zy + zh > H) {
      problems.push(`ZONE_OUT_OF_BOUNDS ${z.name} (${zx},${zy}) ${zw}x${zh} canvas=${W}x${H}`);
    }
  }

  for (let i = 0; i < fixed.length; i++) {
    for (let j = i + 1; j < fixed.length; j++) {
      const a = fixed[i];
      const b = fixed[j];
      const [aw, ah] = nodeSize(a);
      const [bw, bh] = nodeSize(b);
      const overlapX = Math.abs(a.px - b.px) < (aw + bw) / 2;
      const overlapY = Math.abs(a.py - b.py) < (ah + bh) / 2;
      if (overlapX && overlapY) {
        problems.push(`OVERLAP ${a.name} (${a.px},${a.py}) x ${b.name} (${b.px},${b.py})`);
      }
    }
  }
  return { problems, nodeCount: nodes.length, fixedCount: fixed.length };
}

function main() {
  const args = process.argv.slice(2);
  let width = 1200;
  let height = 800;
  const files = [];
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--width') width = Number(args[++i]);
    else if (args[i] === '--height') height = Number(args[++i]);
    else files.push(args[i]);
  }
  if (files.length === 0) {
    console.error('usage: node scripts/check-layout.mjs [--width N] [--height N] <config.json|config.js> [...]');
    process.exit(2);
  }

  let failed = false;
  for (const file of files) {
    try {
      const { problems, nodeCount, fixedCount } = checkLayout(loadConfig(file), { width, height });
      console.log(`==> ${file}: ${nodeCount} nodes (${fixedCount} fixed)`);
      if (problems.length === 0) {
        console.log('    layout OK: no out-of-bounds nodes, no overlapping nodes');
      } else {
        failed = true;
        for (const p of problems) console.log(`    ${p}`);
      }
    } catch (err) {
      failed = true;
      console.error(`ERROR ${file}: ${err.message}`);
    }
  }
  process.exit(failed ? 1 : 0);
}

// Run main() only when executed directly (not when imported by
// verify-deliverable.mjs, which reuses checkLayout()).
const isEntryPoint = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isEntryPoint) {
  main();
}
