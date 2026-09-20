#!/usr/bin/env node
// ============================================================
// verify-deliverable.mjs — structural delivery checks for a
// draw-echarts HTML deliverable. Run BEFORE delivery; the visual
// check (open in a browser / headless screenshot) is documented in
// SKILL.md Step 5.
//
// Rationale (R1 review): deliverables were shipped with an empty
// vendor/ directory, a document.write CDN fallback, hand-synced
// config.js/config.json pairs, and unverified fixed coordinates —
// all of which only surface as blank charts in offline review.
// These checks are deterministic (program-first), no browser needed.
//
// Usage:
//   node scripts/verify-deliverable.mjs <file.html> [<file.html> ...]
//   node scripts/verify-deliverable.mjs --config <foo.config.json> [...]
//
// Checks per HTML file:
//   1. VENDOR — if the file references vendor/echarts.min.js, the
//      file must exist next to the HTML and be non-empty
//   2. LOADER — document.write must not be used for the ECharts
//      loader (blocking, deprecated, CSP-hostile)
//   3. CONFIG_SYNC — for every *.config.js next to the HTML that has
//      a *.config.json counterpart, both must be in sync
//      (see scripts/sync-config.mjs --check)
//   4. LAYOUT — every graph config found is checked for
//      out-of-bounds / overlapping nodes (see scripts/check-layout.mjs)
//
// Exit code: 0 = all checks pass, 1 = problems found, 2 = usage error.
// ============================================================
import fs from 'node:fs';
import path from 'node:path';
import { checkLayout } from './check-layout.mjs';

function loadConfig(file) {
  let text = fs.readFileSync(file, 'utf8');
  if (file.endsWith('.js')) {
    const m = text.match(/window\.CHART_CONFIG\s*=\s*([\s\S]*?);\s*$/);
    if (!m) throw new Error(`cannot find 'window.CHART_CONFIG = ...;' in ${file}`);
    text = m[1];
  }
  return JSON.parse(text);
}

function configPairs(htmlFile) {
  const dir = path.dirname(htmlFile);
  const pairs = [];
  for (const name of fs.readdirSync(dir)) {
    if (!name.endsWith('.config.js')) continue;
    const jsPath = path.join(dir, name);
    const jsonPath = jsPath.replace(/\.config\.js$/, '.config.json');
    if (fs.existsSync(jsonPath)) pairs.push([jsPath, jsonPath]);
  }
  return pairs;
}

function checkHtml(file) {
  const problems = [];
  const html = fs.readFileSync(file, 'utf8');
  const dir = path.dirname(file);
  const base = path.basename(file);

  // 1. VENDOR presence
  if (html.includes('vendor/echarts.min.js')) {
    const vendorPath = path.join(dir, 'vendor', 'echarts.min.js');
    if (!fs.existsSync(vendorPath)) {
      problems.push(`VENDOR ${base}: references vendor/echarts.min.js but ${path.relative(dir, vendorPath)} is missing`);
    } else if (fs.statSync(vendorPath).size === 0) {
      problems.push(`VENDOR ${base}: vendor/echarts.min.js exists but is EMPTY`);
    }
  }

  // 2. LOADER must not use document.write
  if (/document\.write\s*\(/.test(html)) {
    problems.push(`LOADER ${base}: uses document.write (deprecated/blocking/CSP-hostile) — use the onerror dynamic loader from the template`);
  }

  // 3. CONFIG_SYNC for js/json pairs next to the HTML
  for (const [jsPath, jsonPath] of configPairs(file)) {
    try {
      // loadConfig() already JSON.parse()s; normalize both to compact JSON
      const js = JSON.stringify(loadConfig(jsPath));
      const json = JSON.stringify(JSON.parse(fs.readFileSync(jsonPath, 'utf8')));
      if (js !== json) {
        problems.push(`CONFIG_SYNC ${path.basename(jsPath)} differs from ${path.basename(jsonPath)} (run: node scripts/sync-config.mjs ${jsonPath})`);
      }
    } catch (err) {
      problems.push(`CONFIG_SYNC ${path.basename(jsPath)}: ${err.message}`);
    }
  }

  // 4. LAYOUT for every config next to the HTML
  for (const name of fs.readdirSync(dir)) {
    if (!/\.config\.(json|js)$/.test(name)) continue;
    const cfgPath = path.join(dir, name);
    try {
      const { problems: layoutProblems, nodeCount, fixedCount } = checkLayout(loadConfig(cfgPath));
      if (nodeCount > 0 && fixedCount > 0 && layoutProblems.length > 0) {
        problems.push(`LAYOUT ${name}: ${layoutProblems.join('; ')}`);
      }
    } catch (err) {
      problems.push(`LAYOUT ${name}: ${err.message}`);
    }
  }

  return problems;
}

function main() {
  const args = process.argv.slice(2);
  if (args.length === 0) {
    console.error('usage: node scripts/verify-deliverable.mjs <file.html> [...]');
    process.exit(2);
  }

  let failed = false;
  for (const file of args) {
    if (!fs.existsSync(file)) {
      console.error(`ERROR: file not found: ${file}`);
      failed = true;
      continue;
    }
    const problems = checkHtml(file);
    if (problems.length === 0) {
      console.log(`OK ${file}: vendor/loader/config-sync/layout checks passed`);
    } else {
      failed = true;
      console.log(`PROBLEMS ${file}:`);
      for (const p of problems) console.log(`  - ${p}`);
    }
  }
  process.exit(failed ? 1 : 0);
}

main();
