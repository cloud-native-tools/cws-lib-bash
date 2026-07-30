#!/usr/bin/env node
/**
 * browser-utils bridge — one-shot command CLI.
 *
 * Connects as a controller, runs a single command, prints the JSON result, exits.
 *
 * Examples:
 *   node bridge-cli.js status
 *   node bridge-cli.js navigate '{"url":"https://example.com"}'
 *   node bridge-cli.js evaluate '{"expression":"document.title"}'
 *   node bridge-cli.js screenshot '{}' --out /tmp/shot.png
 *   node bridge-cli.js getConsole '{}'
 *
 * Env: BRIDGE_WS_PORT (default 8777), BRIDGE_TOKEN (if the server requires one).
 */

import { BridgeClient } from './client.js';
import { writeFileSync } from 'node:fs';

async function main() {
  const [command, paramsArg, ...rest] = process.argv.slice(2);
  if (!command || command === '--help' || command === '-h') {
    console.log('Usage: node bridge-cli.js <command> [json-params] [--out file]');
    console.log('Commands: status listTabs getContext navigate evaluate click fill waitFor getText getConsole screenshot getStorage');
    process.exit(command ? 0 : 1);
  }

  let params = {};
  if (paramsArg && !paramsArg.startsWith('--')) {
    try { params = JSON.parse(paramsArg); }
    catch { console.error('Invalid JSON params:', paramsArg); process.exit(1); }
  }
  const outIdx = rest.indexOf('--out');
  const outFile = outIdx >= 0 ? rest[outIdx + 1] : (paramsArg === '--out' ? rest[0] : null);

  let bridge;
  try {
    bridge = await BridgeClient.connect();
  } catch (err) {
    console.error('Failed to connect to bridge server:', err.message);
    console.error('Is it running?  node server.js');
    process.exit(2);
  }

  try {
    const result = await bridge.send(command, params, params.timeout || 30000);
    if (command === 'screenshot' && outFile && result?.dataBase64) {
      writeFileSync(outFile, Buffer.from(result.dataBase64, 'base64'));
      console.log(JSON.stringify({ saved: outFile, format: result.format }, null, 2));
    } else {
      console.log(JSON.stringify(result, null, 2));
    }
    bridge.close();
    process.exit(0);
  } catch (err) {
    console.error(JSON.stringify({ error: err.message, code: err.code || 'ERROR' }, null, 2));
    bridge.close();
    process.exit(1);
  }
}

main();
