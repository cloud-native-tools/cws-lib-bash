#!/usr/bin/env node
// ============================================================
// sync-config.mjs — keep the dual config copies (config.js and
// config.json) consistent by GENERATING one from the other.
//
// Rationale (R1 review): hand-syncing a *.config.js and a
// *.config.json pair drifts. Pick ONE canonical format (JSON) and
// generate the JS wrapper; never hand-edit both copies.
//
// Usage:
//   node scripts/sync-config.mjs <file>          # write the counterpart
//   node scripts/sync-config.mjs --check <file>  # exit 1 if counterpart is stale
//
// Input forms:
//   foo.config.json  -> writes foo.config.js  (window.CHART_CONFIG = <json>;)
//   foo.config.js    -> writes foo.config.json (raw JSON, same content)
//
// Exit code: 0 = ok, 1 = check failed or write error.
// ============================================================
import fs from 'node:fs';
import path from 'node:path';

const JS_WRAPPER = (json) =>
  `// AUTO-GENERATED from ${path.basename(json)} by scripts/sync-config.mjs — do not hand-edit.\n` +
  `// 数据/配置外置：重生成只改本配置，HTML 壳不动。\n` +
  `window.CHART_CONFIG = ${JSON.stringify(JSON.parse(fs.readFileSync(json, 'utf8')), null, 2)};\n`;

function readJsonFromJs(file) {
  const text = fs.readFileSync(file, 'utf8');
  // Strip the window.CHART_CONFIG = ...; wrapper (and any leading comments).
  const m = text.match(/window\.CHART_CONFIG\s*=\s*([\s\S]*?);\s*$/);
  if (!m) {
    throw new Error(`cannot find 'window.CHART_CONFIG = ...;' in ${file}`);
  }
  return m[1];
}

function counterpart(file) {
  if (/\.config\.json$/.test(file)) return file.replace(/\.config\.json$/, '.config.js');
  if (/\.config\.js$/.test(file)) return file.replace(/\.config\.js$/, '.config.json');
  throw new Error(`unsupported config name (expected *.config.json or *.config.js): ${file}`);
}

function normalizedJson(file) {
  const text = file.endsWith('.json') ? fs.readFileSync(file, 'utf8') : readJsonFromJs(file);
  return JSON.stringify(JSON.parse(text), null, 2);
}

function main() {
  const args = process.argv.slice(2);
  const check = args[0] === '--check';
  const file = check ? args[1] : args[0];
  if (!file || !fs.existsSync(file)) {
    console.error('ERROR: config file not found');
    console.error('usage: node scripts/sync-config.mjs [--check] <foo.config.json|foo.config.js>');
    process.exit(1);
  }

  const target = counterpart(file);
  const current = normalizedJson(file);

  if (check) {
    if (!fs.existsSync(target)) {
      console.error(`STALE: ${target} is missing (run: node scripts/sync-config.mjs ${file})`);
      process.exit(1);
    }
    const targetNorm = normalizedJson(target);
    if (targetNorm !== current) {
      console.error(`STALE: ${target} differs from ${file} (run: node scripts/sync-config.mjs ${file})`);
      process.exit(1);
    }
    console.log(`OK: ${file} and ${target} are in sync`);
    process.exit(0);
  }

  if (target.endsWith('.js')) {
    fs.writeFileSync(target, JS_WRAPPER(file));
  } else {
    fs.writeFileSync(target, current + '\n');
  }
  console.log(`==> generated ${target} from ${file}`);
}

main();
