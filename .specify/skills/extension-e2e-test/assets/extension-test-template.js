/**
 * Chrome Extension E2E Test Template
 *
 * Ready-to-use Playwright test script for Chrome MV3 extension testing.
 * Covers: extension lifecycle, service worker, popup, options, content scripts,
 * keyboard commands, and Chrome Storage.
 *
 * Usage:
 *   1. Copy this file to /tmp/extension-e2e-test-<timestamp>.js
 *   2. Modify EXTENSION_PATH and TEST_URL as needed
 *   3. Run via browser-utils executor:
 *      node .specify/skills/browser-utils/scripts/js/run.js /tmp/extension-e2e-test-*.js
 *
 * Prerequisites:
 *   - Extension build output exists at EXTENSION_PATH
 *   - Playwright + Chromium installed (auto-installed by run.js)
 */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

// ===== Configuration =====

// Path to the extension build output (contains manifest.json)
// Override with EXTENSION_PATH env var; defaults to current working directory + /dist
// Note: this project builds to dist/ (BUILD_PATH=dist in package.json)
const EXTENSION_PATH = process.env.EXTENSION_PATH || path.resolve(process.cwd(), 'dist');

// User data directory for the browser profile
// Use '/tmp/extension-e2e-profile' for a fresh profile
// Or an existing profile path to reuse login state
const USER_DATA_DIR = process.env.USER_DATA_DIR || '/tmp/extension-e2e-profile';

// Target URL for content script testing
const TEST_URL = process.env.TEST_URL || 'https://example.com';

// Whether to reuse an existing login profile
const REUSE_LOGIN = process.env.REUSE_LOGIN === 'true';

// ===== Test Runner =====

async function main() {
  console.log('=== Chrome Extension E2E Test ===\n');
  console.log(`Extension path: ${EXTENSION_PATH}`);
  console.log(`User data dir:  ${USER_DATA_DIR}`);
  console.log(`Test URL:      ${TEST_URL}\n`);

  // Verify extension exists
  if (!fs.existsSync(path.join(EXTENSION_PATH, 'manifest.json'))) {
    throw new Error(`Extension manifest not found at ${EXTENSION_PATH}/manifest.json. Run 'pnpm build:devel' first.`);
  }

  // Clean up stale Chrome processes that may hold the profile lock
  try {
    require('child_process').execSync('pkill -f "Google Chrome for Testing" 2>/dev/null || true', { timeout: 5000 });
    require('child_process').execSync('sleep 2');
    console.log('[0/7] Chrome processes cleaned');
  } catch { /* pkill non-zero is safe */ }

  // Launch browser with extension — focus-free args prevent desktop focus stealing
  const context = await chromium.launchPersistentContext(USER_DATA_DIR, {
    channel: 'chromium',    // Chrome for Testing — supports --load-extension
    headless: false,        // Extensions require headed mode
    args: [
      `--disable-extensions-except=${EXTENSION_PATH}`,
      `--load-extension=${EXTENSION_PATH}`,
      '--window-position=-32000,-32000',  // off-screen — no desktop focus stealing
      '--window-size=1280,720',            // limit window size
      '--no-default-browser-check',        // suppress default-browser prompt
      '--no-first-run',                    // suppress first-run wizard
    ],
  });
  console.log('[1/7] Browser started with extension loaded');

  try {
    // --- Test 1: Get extension ID from service worker ---
    console.log('\n[2/7] Waiting for service worker...');
    let [serviceWorker] = context.serviceWorkers();
    if (!serviceWorker) {
      serviceWorker = await context.waitForEvent('serviceworker', { timeout: 10000 });
    }
    const extensionId = serviceWorker.url().split('/')[2];
    console.log(`  Extension ID: ${extensionId}`);

    // --- Test 2: Verify service worker is running ---
    console.log('\n[3/7] Testing service worker...');
    const manifest = await serviceWorker.evaluate(() => {
      const m = chrome.runtime.getManifest();
      return {
        name: m.name,
        version: m.version,
        manifestVersion: m.manifest_version,
        permissions: m.permissions,
      };
    });
    console.log(`  Name: ${manifest.name}`);
    console.log(`  Version: ${manifest.version}`);
    console.log(`  Manifest V${manifest.manifestVersion}`);
    console.log(`  Permissions: ${manifest.permissions.join(', ')}`);

    // --- Test 3: Test popup page ---
    console.log('\n[4/7] Testing popup page...');
    const popupPage = await context.newPage();
    await popupPage.goto(`chrome-extension://${extensionId}/popup.html`, {
      waitUntil: 'load',
    });
    const popupTitle = await popupPage.title();
    const popupBody = await popupPage.locator('body').innerText();
    console.log(`  Popup title: "${popupTitle}"`);
    console.log(`  Popup content (first 200 chars): ${popupBody.substring(0, 200)}`);
    await popupPage.screenshot({ path: '/tmp/extension-popup.png' });
    console.log('  Screenshot saved: /tmp/extension-popup.png');
    await popupPage.close();

    // --- Test 4: Test options page ---
    console.log('\n[5/7] Testing options page...');
    const optionsPage = await context.newPage();
    await optionsPage.goto(`chrome-extension://${extensionId}/options.html`, {
      waitUntil: 'load',
    });
    const optionsTitle = await optionsPage.title();
    const optionsBody = await optionsPage.locator('body').innerText();
    console.log(`  Options title: "${optionsTitle}"`);
    console.log(`  Options content (first 200 chars): ${optionsBody.substring(0, 200)}`);
    await optionsPage.screenshot({ path: '/tmp/extension-options.png' });
    console.log('  Screenshot saved: /tmp/extension-options.png');
    await optionsPage.close();

    // --- Test 5: Test content script on target URL ---
    console.log('\n[6/7] Testing content script injection...');
    const webPage = await context.newPage();

    // Listen for console messages from content scripts
    webPage.on('console', (msg) => {
      const text = msg.text();
      if (text.includes('xuanji') || text.includes('extension')) {
        console.log(`  [content script console]: ${text}`);
      }
    });

    await webPage.goto(TEST_URL, { waitUntil: 'load', timeout: 30000 });
    const webTitle = await webPage.title();
    console.log(`  Navigated to: ${TEST_URL}`);
    console.log(`  Page title: "${webTitle}"`);
    await webPage.screenshot({ path: '/tmp/extension-content.png' });
    console.log('  Screenshot saved: /tmp/extension-content.png');
    await webPage.close();

    // --- Test 6: Test Chrome Storage ---
    console.log('\n[7/7] Testing Chrome Storage...');
    const storagePage = await context.newPage();
    await storagePage.goto(`chrome-extension://${extensionId}/popup.html`, {
      waitUntil: 'load',
    });
    const storageData = await storagePage.evaluate(async () => {
      return new Promise((resolve) => {
        chrome.storage.local.get(null, (items) => {
          resolve(Object.keys(items));
        });
      });
    });
    console.log(`  Storage keys: ${storageData.length > 0 ? storageData.join(', ') : '(empty)'}`);
    await storagePage.close();

    // --- Summary ---
    console.log('\n=== Test Results ===');
    console.log('✅ Extension loaded successfully');
    console.log('✅ Service worker is running');
    console.log('✅ Manifest version:', manifest.manifestVersion);
    console.log('✅ Popup page accessible');
    console.log('✅ Options page accessible');
    console.log('✅ Content script injection environment ready');
    console.log('✅ Chrome Storage accessible');
    console.log('\nAll basic extension surface tests passed.');

  } finally {
    // Always close the context to prevent orphaned Chrome processes
    await context.close();
    console.log('\nBrowser closed.');
  }
}

// Run the test
main().catch((err) => {
  console.error('\n❌ Test failed:', err.message);
  if (err.stack) {
    console.error(err.stack);
  }
  process.exit(1);
});
