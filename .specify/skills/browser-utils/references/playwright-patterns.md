# Playwright Automation Patterns (Tier 3)

Code examples and patterns for Playwright-based headless browser automation.
These patterns are used when Tier 1 (built-in browser) and Tier 2 (MCP connector)
are not available.

For the complete Playwright API reference, see [playwright-api.md](./playwright-api.md).

---

## Preflight: verify the Playwright install actually resolves

`npm run setup` (or a prior `npm install`) can leave a **partial/corrupt** `node_modules`
that only fails at *runtime*, not at install time. The classic symptom is a missing
`playwright-core/lib/` producing `Cannot find module './lib/bootstrap'` the first time a
script requires Playwright. A file existing is not proof it loads.

Run this integrity check before the first script of a session — it repairs itself if the
require fails:

```bash
cd ${SKILL_HOME}/scripts/js
node -e "require('playwright'); console.log('playwright OK')" \
  || { echo 'playwright broken — reinstalling'; rm -rf node_modules/playwright* && npm install; }
```

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Cannot find module './lib/bootstrap'` (or similar) on first `require('playwright')` | Partial/corrupt `node_modules` (interrupted install, bad cache) | `rm -rf node_modules/playwright* && npm install` (or re-run `npm run setup`) |

---

## Run Modes (Tier 3)

Tier 3 has two mutually exclusive run modes. Pick the mode **before writing a script**
(see SKILL.md § Run Mode Selection). This section is the launch recipe for each.

### Mode 1 — Clean Test Browser (default)

Playwright's bundled Chromium / Chrome for Testing, fresh ephemeral context, default
`--use-mock-keychain`. Use for frontend/localhost automation and E2E testing. No real
login state — every run starts clean. This is the `chromium.launch()` used by every
example below (Basic Page Test, Responsive, Form Filling, etc.).

The whole recipe is: `chromium.launch()` → `newPage()` → `goto` → assert something →
`screenshot` to `/tmp` → `close()` in a `finally`. Two copy-run quickstarts follow — a
localhost/dev-server one and a self-contained `file://` one that needs zero external
dependencies (no dev server, no network), so Mode 1 itself can be validated in one command.

**Quickstart A — localhost / dev server.** Detect the server first, then drive it:

```bash
# 1) find the running dev server (SKILL.md § JavaScript Workflow):
cd ${SKILL_HOME}/scripts/js && node -e "require('./lib/helpers').detectDevServers().then(s => console.log(JSON.stringify(s)))"
# 2) put the URL in TARGET_URL below, then: cd ${SKILL_HOME}/scripts/js && node run.js /tmp/playwright-mode1-localhost.js
```

```javascript
// /tmp/playwright-mode1-localhost.js
const { chromium } = require('playwright');

// From detectDevServers() above. One server → use it; several → ask the user.
const TARGET_URL = 'http://localhost:3001';

(async () => {
  const browser = await chromium.launch({ headless: false }); // bundled Chromium, mock keychain kept
  try {
    const page = await browser.newPage();
    await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const title = await page.title();
    console.log('Title:', title);
    if (!title) throw new Error('empty <title> — dev server not serving the app?');
    await page.screenshot({ path: '/tmp/mode1-localhost.png', fullPage: true });
    console.log('OK → /tmp/mode1-localhost.png');
  } finally {
    await browser.close(); // nothing persists — next run starts clean
  }
})();
```

**Quickstart B — self-contained `file://` (zero dependencies).** Use this to confirm the
Mode 1 toolchain works before pointing it at a real app — it writes a trivial HTML fixture
and asserts against it, so it passes with no dev server and no network access:

```javascript
// /tmp/playwright-mode1-selftest.js  — run: cd ${SKILL_HOME}/scripts/js && node run.js /tmp/playwright-mode1-selftest.js
const { chromium } = require('playwright');
const fs = require('fs');

// Write a trivial fixture and drive it via file:// — validates Mode 1 end-to-end.
const FIXTURE = '/tmp/mode1-fixture.html';
fs.writeFileSync(FIXTURE,
  '<!doctype html><html><head><title>Mode 1 OK</title></head>' +
  '<body><h1 id="hello">clean browser works</h1></body></html>');

(async () => {
  const browser = await chromium.launch({ headless: false });
  try {
    const page = await browser.newPage();
    await page.goto('file://' + FIXTURE, { waitUntil: 'domcontentloaded' });
    const text = (await page.textContent('#hello')) || '';
    console.log('Read from page:', text);
    if (text.trim() !== 'clean browser works') throw new Error('assertion failed: ' + text);
    await page.screenshot({ path: '/tmp/mode1-selftest.png', fullPage: true });
    console.log('Mode 1 self-test PASSED → /tmp/mode1-selftest.png');
  } finally {
    await browser.close();
  }
})();
```

### Mode 2 — Real Chrome Profile (reuse login state)

Drives the **real Google Chrome** against an existing user-data-dir so its cookies and
localStorage (logins) are reused. Required to reach authenticated/internal sites.

Three conditions must ALL hold, or login state silently fails:

1. **Profile not in use** — Chrome is single-instance per profile. If a Chrome is
   already running on `userDataDir`, the launch is handed off to that window and the
   controllable process exits immediately (`正在现有的浏览器会话中打开`). Preflight it.
2. **`channel: 'chrome'`** — must be the real Google Chrome binary, not bundled
   Chromium/Chrome for Testing. Cookies are encrypted with a macOS Keychain "Safe
   Storage" key that is *per-app*; a different binary cannot decrypt them.
3. **`ignoreDefaultArgs: ['--use-mock-keychain']`** — Playwright injects
   `--use-mock-keychain` by default, which bypasses the real keychain. Drop it so
   Chrome uses the real key that decrypts the profile's cookies.

**Preflight (bash) — verify the profile is free before launching:**

```bash
USER_DATA_DIR="$HOME/data/chrome/agent"   # the target profile
# Any process holding the profile? (non-empty ⇒ ask the user to close it)
ps aux | grep -F "user-data-dir=$USER_DATA_DIR" | grep -v grep
# Stale singleton lock present? (informational)
ls -la "$USER_DATA_DIR" | grep -i singleton
```

**Launch recipe (JavaScript):**

```javascript
// /tmp/playwright-test-profile.js
const { chromium } = require('playwright');
const os = require('os');
const path = require('path');

const USER_DATA_DIR = path.join(os.homedir(), 'data/chrome/agent');
const TARGET_URL = 'https://internal.example.com/dashboard';

(async () => {
  let context;
  try {
    context = await chromium.launchPersistentContext(USER_DATA_DIR, {
      headless: false,
      channel: 'chrome',                              // real Chrome → keychain key matches
      ignoreDefaultArgs: ['--use-mock-keychain'],     // use the REAL keychain to decrypt cookies
      viewport: { width: 1440, height: 900 },
      args: ['--no-first-run', '--no-default-browser-check'],
    });
    const page = context.pages()[0] || (await context.newPage());
    await page.goto(TARGET_URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    console.log('Final URL:', page.url());            // if it ends on a login page, login state did NOT load
    await page.screenshot({ path: '/tmp/profile-page.png', fullPage: true });
  } catch (e) {
    console.error('ERROR:', e.message);
  } finally {
    if (context) await context.close();
  }
})();
```

**Failure-symptom table:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| `Target page, context or browser has been closed` + `正在现有的浏览器会话中打开` | A Chrome is already running on the profile | Close it (preflight #1), then relaunch |
| Page redirects to the SSO/login page despite a logged-in profile | Bundled Chromium used, or `--use-mock-keychain` kept | Add `channel: 'chrome'` **and** `ignoreDefaultArgs: ['--use-mock-keychain']` |
| `kill EPERM` in browser logs on close | Handoff process couldn't be killed (side effect of #1) | Same as the handoff row — free the profile first |

> If the profile is in use and cannot be closed, an alternative is to launch Chrome
> yourself with `--remote-debugging-port=<port>` and attach via
> `chromium.connectOverCDP('http://127.0.0.1:<port>')`, which coexists with a manually
> opened window. Confirm this approach with the user first.

---

## SPA Site Traversal & Module Extraction (Tier 3)

Use this pattern to **map every functional module of a single-page app** (left-nav +
hash routes) and produce a structured design doc: for each module, its route, label,
purpose, and key UI elements (tables/columns, filters, action buttons, charts, metrics).

It combines with a Run Mode: an internal/authenticated SPA needs **Mode 2** (real Chrome
profile), a localhost SPA uses **Mode 1**. The traversal logic below is identical for both.

### Design principles (why this shape)

- **One context, one page, reused across all routes.** Launch the browser/context
  **once**, navigate every route in the same tab, and close the context **once** in a
  `finally`. Do NOT relaunch per route: in Mode 2 each relaunch re-acquires the profile
  singleton lock (slow, and hands off to any stray window). Reusing one context also
  keeps SSO/session cookies warm.
- **Incremental, resumable output.** A 20+ module SPA is a long run; a crash mid-way must
  not lose progress. Persist a checkpoint after every module and append to the design doc
  as you go — never buffer the whole site in memory and write once at the end.
- **Hash routes are not real navigations.** `#/...` changes fire no `load` event and
  `networkidle` may never settle (polling widgets). Wait on the *route + content* changing,
  with bounded fallbacks — see the wait helper below.
- **Extract only after dynamic content settles — and scroll the iframe to force it.** Much of
  a real ops SPA is Grafana/Kibana dashboards in same-origin iframes whose panels mount *after*
  the route settles AND only when scrolled into view (lazy render). A page reads "(0 panels)"
  if you extract too early or never scroll the frame. `settleDynamicContent` (Step 2.5) scrolls
  each dashboard frame top→bottom to mount every panel, then polls the panel count to stability;
  tab bodies and expandable rows mount on activation and are revealed the same pass. Always run
  it between `gotoRoute` and `extractModule`. Per the scope split, iframe pages are documented to
  dashboard level only (src, title, panel groups, variable NAMES) — not component level.
- **Prove login state, don't assume it.** A Mode-2 crawl that silently lands on the SSO
  page catalogues the login form 50× and looks "complete". Assert the first navigation did
  NOT land on a login host (Step 0) and fail fast, and record a run log so the run is
  reproducible and self-documenting.
- **Every module gets a PURPOSE + a screenshot.** The doc's job is to explain *what each
  module is for*, not just list its widgets. Synthesize a one-line purpose per module and
  capture a per-module screenshot as evidence — treat a failed screenshot as a recorded
  problem, not a silent skip.

### Step 0 — Assert login state & open a run log (reproducibility)

Do this **once, right after the first navigation**, before enumerating. It converts a
silent "crawled the login page" failure into an immediate stop, and records the Mode-2
preflight result + landing URL so the run self-documents (D1/D2).

```javascript
const fs = require('fs');                   // (declare once at the top of your script)
const RUN_LOG = '/tmp/spa-run-log.json';   // preflight + landing URL + per-module evidence

// Fail fast if the profile did NOT carry login state. Otherwise a Mode-2 crawl silently
// catalogues the SSO login form for every route and still reports "complete".
function assertNotOnLogin(page) {
  const url = page.url();
  if (/login[^/]*\.alibaba-inc\.com|passport|\/login(\b|\/|\?)|\/sso(\b|\/)/i.test(url)) {
    throw new Error(
      `Login state NOT loaded — landed on a login page: ${url}\n` +
      `Re-check Mode 2 preflight: profile free? channel:'chrome'? ` +
      `ignoreDefaultArgs:['--use-mock-keychain']?`);
  }
  return url;
}

// runInfo carries whatever the bash preflight found (profile path, "profile free" result).
function openRunLog(runInfo) {
  const log = { startedAt: new Date().toISOString(), ...runInfo, modules: [] };
  fs.writeFileSync(RUN_LOG, JSON.stringify(log, null, 2));
  return log;
}
function saveRunLog(log) { fs.writeFileSync(RUN_LOG, JSON.stringify(log, null, 2)); }

// Usage (after the context is launched via Mode 1/Mode 2 and ONE page exists):
//   await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
//   await settleDynamicContent(page, { timeout: 8000 });         // Step 2.5
//   const landingUrl = assertNotOnLogin(page);                   // throws → stop now
//   const runLog = openRunLog({ mode: 'mode2', profile: USER_DATA_DIR,
//                               profileFreePreflight: true, baseUrl, landingUrl });
```

Record the bash profile-preflight result (from the Mode 2 recipe above) into `runInfo` so
the log states, in one place, that the profile was free and the page was authenticated.

### Step 1 — Enumerate all routes (BFS over the left-nav)

Expand every collapsible nav group first (group headers often render submenus only when
open), then collect every leaf link. Leaves have a real hash href; group toggles do not.

```javascript
// Expand all collapsible menu groups, then collect leaf routes.
async function enumerateRoutes(page, navSelector = 'nav, .ant-menu, aside') {
  // Repeatedly click ONLY still-closed group headers until no new ones appear (BFS by depth).
  // CRITICAL: select closed groups only. `.ant-menu-submenu-title` matches every submenu
  // header regardless of state, so clicking it blindly each pass TOGGLES already-open groups
  // shut again — the classic bug that makes enumeration return 0 leaves. Gate on open-state:
  // an open Ant submenu carries `.ant-menu-submenu-open` on its wrapper, and aria toggles
  // expose `aria-expanded="true"`. Re-evaluate every pass because opening a group reveals
  // nested groups that only become clickable on the next pass.
  for (let pass = 0; pass < 8; pass++) {
    const toggles = await page.locator(
      `${navSelector} [aria-expanded="false"], ` +
      `${navSelector} .ant-menu-submenu:not(.ant-menu-submenu-open) > .ant-menu-submenu-title`
    ).all();
    if (toggles.length === 0) break;
    let clicked = 0;
    for (const t of toggles) {
      try { await t.click({ timeout: 1000 }); clicked++; await page.waitForTimeout(150); }
      catch { /* not clickable / detached this pass */ }
    }
    if (clicked === 0) break;
  }
  // Collect leaf links: anchors with a hash route, deduped, preserving nav order.
  const routes = await page.$$eval(`${navSelector} a[href*="#/"]`, (as) => {
    const seen = new Set();
    const out = [];
    for (const a of as) {
      const href = a.getAttribute('href') || '';
      const m = href.match(/#\/[^\s?]*/);
      if (!m) continue;
      const route = m[0];
      if (seen.has(route)) continue;
      seen.add(route);
      out.push({ route, label: (a.textContent || '').trim() });
    }
    return out;
  });
  return routes; // [{ route: '#/common_info/view', label: '公共信息' }, ...]
}
```

If the nav is not standard anchors (e.g. clickable `<li>` with JS-driven routing), fall
back to clicking each nav item and reading `page.url()` after the route settles; build the
route list from the observed URLs.

### Step 2 — Robust SPA route wait

```javascript
// Navigate to a hash route in the SAME page and wait for the view to actually change.
async function gotoRoute(page, baseUrl, route, contentSelector = 'main, .ant-pro-page-container, #root > div') {
  const before = page.url();
  await page.evaluate((h) => { window.location.hash = h.replace(/^#/, ''); }, route);
  // 1) hash actually changed
  await page.waitForFunction((prev) => location.href !== prev, before, { timeout: 8000 }).catch(() => {});
  // 2) content container present + a brief settle for lazy chunks
  await page.waitForSelector(contentSelector, { timeout: 8000 }).catch(() => {});
  await page.waitForLoadState('networkidle', { timeout: 6000 }).catch(() => {}); // bounded — polling apps never idle
  await page.waitForTimeout(400); // final settle for animations / async table loads
}
```

### Step 2.5 — Settle dynamic content before extracting (panels, tabs, rows)

`gotoRoute` only proves the *route* changed and the outer shell exists. Grafana panels,
tab bodies, and expandable rows mount **later**; extracting now yields the "(0 panels)"
empty-shell result that hollowed out round 1. Run this between `gotoRoute` and
`extractModule`.

```javascript
// Wait until dynamic content actually rendered, then reveal hidden tabs/rows so
// extractModule sees the whole module — not just the default tab's empty shell.
async function settleDynamicContent(page, { timeout = 15000 } = {}) {
  // (a) Grafana/dashboard panels render in same-origin iframes AFTER the route settles —
  // and Grafana LAZY-renders panels only when they scroll into the iframe's viewport. So a
  // plain count poll stabilizes at "only what fits the viewport" (often 0) → the persistent
  // "(0 panels)" bug. Fix: for each dashboard frame, scroll it top→bottom each pass to force
  // every panel to mount, then poll the count until it is > 0 AND stable across two passes.
  // Panel elements across old + current Grafana (scenes use data-viz-panel-key; newer builds
  // tag each header `data-testid Panel header <title>`).
  const panelSel = '.panel-container, [data-panelid], [data-viz-panel-key], .react-grid-item, ' +
                   '[data-testid^="data-testid Panel header"]';
  // A frame is a dashboard host if its URL looks like Grafana/Kibana OR it actually contains
  // panels (some embeds use a neutral src) — probe both so we don't skip scrolling.
  const dashFrames = async () => {
    const out = [];
    for (const f of page.frames()) {
      if (f === page.mainFrame()) continue;
      if (/grafana|dashboard|kibana|d-solo|\/d\//i.test(f.url())) { out.push(f); continue; }
      try { if (await f.locator(panelSel).count() > 0) out.push(f); } catch { /* cross-origin */ }
    }
    return out;
  };
  const countPanels = async () => {
    let total = 0;
    for (const frame of page.frames()) {
      try { total += await frame.locator(panelSel).count(); } catch { /* cross-origin */ }
    }
    return total;
  };
  // Scroll every dashboard frame's own window top→bottom in steps so lazy panels mount.
  // Runs INSIDE the frame context (frame.evaluate), so window == the iframe's window.
  const scrollDashFrames = async (frames) => {
    for (const frame of frames) {
      try {
        await frame.evaluate(async () => {
          const doc = document.scrollingElement || document.documentElement;
          const step = Math.max(300, Math.floor(window.innerHeight * 0.8));
          for (let y = 0; y <= doc.scrollHeight; y += step) {
            window.scrollTo(0, y);
            await new Promise((r) => setTimeout(r, 150)); // let lazy panels mount
          }
          window.scrollTo(0, 0); // back to top so the screenshot shows the dashboard head
        });
      } catch { /* cross-origin or detached — skip */ }
    }
  };
  const frames0 = await dashFrames();
  const hasDashboardFrame = frames0.length > 0;
  const deadline = Date.now() + timeout;
  let prev = -1, stable = 0;
  while (Date.now() < deadline) {
    if (hasDashboardFrame) await scrollDashFrames(await dashFrames()); // re-resolve: frames can reload
    const n = await countPanels();
    // A page with no dashboard iframe at all → nothing to wait for; leave promptly.
    if (n === 0 && !hasDashboardFrame && Date.now() - (deadline - timeout) > 1500) break;
    if (n > 0 && n === prev) { if (++stable >= 2) break; } else { stable = 0; }
    prev = n;
    await page.waitForTimeout(500);
  }
  // (b) Panels/tables often show a spinner first — wait for known loaders to clear.
  for (const frame of page.frames()) {
    await frame.locator('.panel-loading, [aria-label="Panel loading bar"], ' +
        '[data-testid="Panel loading bar"], .ant-spin-spinning, .ant-skeleton')
      .first().waitFor({ state: 'hidden', timeout: 3000 }).catch(() => {});
  }
  // (c) Reveal inactive tabs and collapsed rows so their content mounts before extraction.
  await revealTabsAndRows(page);
}

// Click through inactive tabs and expandable table rows so their content is in the DOM.
async function revealTabsAndRows(page) {
  const tabs = await page.locator('.ant-tabs-tab:not(.ant-tabs-tab-active), [role="tab"]:not([aria-selected="true"])').all();
  for (const tab of tabs.slice(0, 12)) {
    await tab.click({ timeout: 800 }).catch(() => {});
    await page.waitForTimeout(200);
  }
  const rowToggles = await page.locator('.ant-table-row-expand-icon-collapsed, [aria-label="Expand row"]').all();
  for (const r of rowToggles.slice(0, 20)) {
    await r.click({ timeout: 500 }).catch(() => {});
  }
}

// Ant Design <Select> options are NOT in the DOM until the dropdown is opened — the listbox
// renders in a detached portal on click. So `extractDoc` (which reads the static DOM) can
// only ever see a select's PLACEHOLDER, never its options. This is the general shape of
// *interaction-gated* content: to document it you must trigger the interaction. Open each
// select, read the portal options, then Escape to close. Bounded (few selects, capped
// options) so it stays cheap on a 50-module crawl. Runs at the Playwright level (needs real
// clicks), so call it from extractModule — NOT from inside page.evaluate.
async function readSelectOptions(page, { maxSelects = 8, maxOptions = 60 } = {}) {
  const selects = await page.locator('.ant-select:not(.ant-select-disabled)').all();
  const out = [];
  for (const sel of selects.slice(0, maxSelects)) {
    let placeholder = '';
    try {
      placeholder = ((await sel.locator('.ant-select-selection-placeholder, .ant-select-selection-item')
        .first().textContent({ timeout: 500 })) || '').trim();
    } catch { /* no visible label */ }
    let options = [];
    try {
      await sel.click({ timeout: 800 });
      await page.waitForTimeout(250); // portal mount + async option load
      options = await page.locator(
        '.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option-content'
      ).allTextContents();
      options = [...new Set(options.map((o) => o.trim()).filter(Boolean))].slice(0, maxOptions);
      await page.keyboard.press('Escape'); // close before touching the next select
    } catch { await page.keyboard.press('Escape').catch(() => {}); }
    if (placeholder || options.length) out.push({ placeholder, options });
  }
  return out; // [{ placeholder: '请选择集群', options: ['acs-egs_...', ...] }, ...]
}
```

> Returning to the first tab after the reveal pass is usually unnecessary for extraction
> (all tab bodies are now in the DOM), but call `page.locator('.ant-tabs-tab').first().click()`
> before the screenshot if you want the default view captured.

### Step 3 — Extract each module's structure (main document **and** iframes)

Real SPAs frequently render the actual content inside an **iframe** (dashboards embedded
from Grafana/Kibana, external systems, doc portals). Extracting only the top document
misses the substance of those pages — in practice a large share of modules are iframe
hosts whose top-level DOM is nearly empty. So `extractModule` runs the same extraction on
the main frame **and** every child frame: for **same-origin** frames it reads the inner
DOM; for **cross-origin** frames only the `src` URL is observable (browser security), so
record that. `frame.evaluate()` throws on cross-origin access — catch it and fall back to
the URL.

```javascript
async function extractModule(page) {
  // Extraction body — runs inside ANY frame's document context and returns its structure.
  const extractDoc = () => {
    const txt = (el) => (el?.textContent || '').trim().replace(/\s+/g, ' ');
    const many = (sel) => Array.from(document.querySelectorAll(sel)).map(txt).filter(Boolean);
    // Interaction-widget noise: Ant InputNumber up/down arrows expose "Increase/Decrease
    // Value" as <button>s; Grafana dashboard chrome adds "Add panel"/"Share"/etc. These are
    // not app affordances — drop them so the button list reflects real user actions.
    const BTN_NOISE = /^(increase|decrease) value$|^(add panel|add row|add library panel|share|save dashboard|exit edit mode|search dashboards)$/i;
    // Tables: column headers
    const tables = Array.from(document.querySelectorAll('table, .ant-table')).slice(0, 10).map((t) => ({
      columns: Array.from(t.querySelectorAll('th, .ant-table-cell[role="columnheader"]'))
        .map((h) => txt(h)).filter(Boolean).slice(0, 40),
    })).filter((t) => t.columns.length);
    // ---- Grafana panels: AUTHORITATIVE count + header-scoped titles + legit-empty detection ----
    const PANEL_EL = '.panel-container, [data-panelid], [data-viz-panel-key], ' +
                     '.react-grid-item, [data-testid^="data-testid Panel header"]';
    // Ground truth = number of panel ELEMENTS in the DOM. Grafana's row-header "(N panels)"
    // text is the COLLAPSED-state count and reads 0 while a row is collapsed — it looks
    // authoritative but is wrong, so NEVER surface it as the panel count. Count elements.
    const panelCount = document.querySelectorAll(PANEL_EL).length;
    const stripCount = (s) => (s || '').replace(/\s*\(\s*\d+\s*panels?\s*\)\s*$/i, '').trim();
    // Row-GROUP titles, with the misleading "(N panels)" collapsed count stripped off.
    const panelGroups = [...new Set(
      many('.dashboard-row__title, [aria-label="Dashboard row title"], ' +
           '[data-testid="data-testid dashboard row title"]').map(stripCount))]
      .filter(Boolean).slice(0, 60);
    // Individual panel titles — scoped to the HEADER/title node ONLY. On current Grafana
    // "scenes" builds the clean title is NOT in textContent (it concatenates the panel body,
    // e.g. "告警数61189") and NOT in `aria-label` (null); the class is emotion-hashed
    // (`css-…-panel-title`, so exact `.panel-title` matches 0). The RELIABLE source is the
    // header element's `data-testid` ATTRIBUTE VALUE: `data-testid="data-testid Panel header
    // <title>"` — read the attribute and strip the prefix. Fall back to `h6[class*="panel-title"]`
    // (hashed class) / old-Grafana `.panel-title-text`, reading the title node's own text only.
    const cleanTitle = (s) => (s || '').trim().replace(/\s+/g, ' ');
    const stripHdr = (s) => cleanTitle((s || '').replace(/^data-testid Panel header\s*/i, ''));
    const panels = [...new Set([
      // Primary: the header's data-testid ATTRIBUTE value (not textContent, not aria-label).
      ...Array.from(document.querySelectorAll('[data-testid^="data-testid Panel header"]'))
        .map((el) => stripHdr(el.getAttribute('data-testid'))),
      // Fallback: hashed-class title node (h6[class*="panel-title"]) or old-Grafana span,
      // reading the title node's OWN text only — never the panel body.
      ...Array.from(document.querySelectorAll('h6[class*="panel-title"], .panel-title')).map((el) => {
        const t = el.querySelector('.panel-title-text');           // old-Grafana title span
        return cleanTitle(t ? t.textContent
          : (el.childNodes[0] && el.childNodes[0].textContent) || ''); // own text node, not body
      }),
    ])].filter((s) => s && s.length <= 60).slice(0, 120);
    // Legit zero-panel cases — so "0 panels" is not misread as extraction failure. A dashboard
    // FOLDER view lists boards (no panels of its own); a board can redirect to a secondary
    // login; a removed board renders "Not found". Detect and label these explicitly.
    let dashboardState = null;
    if (/\/dashboards\/f\//i.test(location.href)) dashboardState = 'folder-view (dashboard list, no panels)';
    else if (/\/login(\b|\/|\?)/i.test(location.href)) dashboardState = 'login-redirect (needs secondary auth)';
    else if (/not\s*found/i.test(document.title)) dashboardState = 'not-found (dashboard removed)';
    return {
      title: document.title,
      headings: [...many('h1'), ...many('h2'), ...many('h3')].slice(0, 20),
      breadcrumb: many('.ant-breadcrumb a, .ant-breadcrumb span').slice(0, 10),
      filters: [
        ...Array.from(document.querySelectorAll('input')).map((i) => i.placeholder).filter(Boolean),
        ...many('.ant-form-item-label label'),
        ...many('.ant-select-selection-placeholder'),
      ].slice(0, 40),
      buttons: [...new Set(many('button, .ant-btn'))].filter((b) => b && !BTN_NOISE.test(b)).slice(0, 40),
      // Tab labels — distinguish multi-view pages and feed the purpose line.
      tabs: [...new Set(many('.ant-tabs-tab, [role="tab"]'))].slice(0, 20),
      tables,
      charts: document.querySelectorAll('canvas, svg.recharts-surface, .echarts-for-react').length,
      metrics: many('.ant-statistic, .ant-card-head-title, .ant-descriptions-item').slice(0, 30),
      // Grafana-embedded dashboards (computed above): `panelCount` is the AUTHORITATIVE
      // DOM element count; `panelGroups` are row titles (misleading "(N panels)" stripped);
      // `panels` are header-scoped panel titles; `dashboardState` flags legit-empty boards.
      panelCount,
      panelGroups,
      panels,
      dashboardState,
      // Template-variable NAMES (labels), NOT the stale selected values. Grafana DOM DRIFTS:
      // current builds render each variable label as
      // `data-testid="data-testid Dashboard template variables submenu Label <name>"`;
      // older builds use `.template-variable label` / `.gf-form-label`. Read the LABEL text
      // (variable name like "cluster"/"namespace") — reading the combobox value instead was
      // the round-2 bug (values mislabeled as names). Enumerating each variable's option list
      // needs a click (interaction-gated) — see the note under Step 3; names are enough here.
      variables: [...new Set([
        ...Array.from(document.querySelectorAll(
          '[data-testid^="data-testid Dashboard template variables submenu Label"], ' +
          '[data-testid^="data-testid template variable"] label'))
          .map((el) => (el.getAttribute('aria-label') || el.textContent || '')
            .replace(/^data-testid.*Label\s*/i, '').trim()).filter(Boolean),
        ...many('.template-variable .template-variable__label, .gf-form-label--variable, ' +
                '.submenu-item > label'),
      ])].filter(Boolean).slice(0, 60),
    };
  };

  const main = await page.evaluate(extractDoc);
  // Interaction-gated: Ant Select options only exist once the dropdown is opened, so they
  // can't come from the evaluate() above — capture them with real clicks and attach here.
  main.selects = await readSelectOptions(page);

  // Walk every child frame; drill same-origin inner DOM, record cross-origin src only.
  const frames = [];
  for (const frame of page.frames()) {
    if (frame === page.mainFrame()) continue;
    const src = frame.url();
    if (!src || src === 'about:blank') continue;
    let inner = null;
    try {
      inner = await frame.evaluate(extractDoc);   // throws for cross-origin → caught below
    } catch {
      inner = null;                               // cross-origin: only src is observable
    }
    frames.push({ src, sameOrigin: !!inner, inner });
  }
  return { ...main, frames };
}
```

> **Grafana panels & variables — the failure modes and how this code fixes them.**
> (1) *Panels read "(0 panels)".* Three causes, all handled: (a) panels lazy-render only when
> scrolled into view — `settleDynamicContent` scrolls each dashboard frame top→bottom to mount
> them before counting; (b) the old row-title-only `panels` selector matched nothing on
> panel-only / current-Grafana dashboards — `extractDoc.panels` now reads `.panel-title` and
> current scenes' `data-testid Panel header <title>`; (c) **the number Grafana prints in the
> row header — "(N panels)" — is the COLLAPSED-state count and reads 0 while a row is
> collapsed.** It looks authoritative but is wrong, so `extractDoc` no longer surfaces it:
> `panelCount` is the count of real panel ELEMENTS (`PANEL_EL`) and is the ground truth;
> `panelGroups` keeps the row *names* only, with the misleading `(N panels)` suffix stripped.
> If panels are still empty on a dashboard you can see, raise `settleDynamicContent`'s
> `timeout` and confirm the frame is same-origin (cross-origin frames expose only `src`).
> (2) *Panel titles came out huge / garbled* (e.g. `告警数61189`, a title jammed onto a stat
> value or a whole table body). Root cause on current Grafana **scenes** builds: the clean
> title is NOT text and NOT an attribute you'd expect — `textContent` concatenates the panel
> BODY, `aria-label` is null, and the class is emotion-hashed (`css-…-panel-title`, so exact
> `.panel-title` matches 0). The ONE reliable source is the header's **`data-testid` ATTRIBUTE
> value** (`data-testid="data-testid Panel header <title>"`). Fix: `extractDoc.panels` reads
> `el.getAttribute('data-testid')` and strips the `data-testid Panel header ` prefix (primary),
> then falls back to `h6[class*="panel-title"]` / old-Grafana `.panel-title-text`, always the
> title node's OWN text only — never the panel body. Do not "fix" this by widening the length
> filter (a backstop, not the fix) or by reading textContent; read the data-testid attribute. (3) *A genuinely empty dashboard vs a failed extraction.* `dashboardState`
> flags the three legit zero-panel cases (folder view `/dashboards/f/`, `/login` redirect,
> "Not found" title) so they are reported as empty-by-design, not counted as extraction bugs.
> (4) *Variables captured as stale values, not names.* `extractDoc.variables` reads the
> variable LABEL text (`…submenu Label <name>`), giving names like "cluster"/"namespace".
> Grafana DOM drifts between versions, so treat `variables: []` on a page you *know* has a
> variable bar as a selector-drift signal, not "no variables". To read each variable's full
> option list, click the combobox open and read `[role="option"]` (the interaction-gated
> pattern from `readSelectOptions`); per the scope split (iframe pages need only src, title,
> panel groups, and variable NAMES) this deeper capture is optional.

### Step 4 — Drive the traversal with a resumable checkpoint

```javascript
// (fs and RUN_LOG helpers from Step 0 are reused here — declare fs only once.)
const CHECKPOINT = '/tmp/spa-traversal.json';   // {visited, pending, data}
const DESIGN_DOC = '/tmp/spa-design-doc.md';    // append-as-you-go output

function loadCheckpoint() {
  try { return JSON.parse(fs.readFileSync(CHECKPOINT, 'utf8')); } catch { return null; }
}
function saveCheckpoint(cp) { fs.writeFileSync(CHECKPOINT, JSON.stringify(cp, null, 2)); }

// One-line PURPOSE per module, synthesized deterministically (no LLM call) from the module's
// DISTINCTIVE signals rather than a mechanical breadcrumb+template string (the round-2 defect
// was boilerplate like "A › B — browse 1 table(s), 2 chart(s)"). Lead with the primary entity
// (heading/title), then the signals that actually differentiate this page from its siblings:
// real table COLUMN names (what data it is about), real action-button VERBS (what you can do),
// TAB names (which sub-views), and embedded dashboard panel titles. Everything is pulled from
// concrete DOM text, so two different pages produce two different sentences.
function synthesizePurpose(route, label, info) {
  // Primary entity: the most specific human name for the page.
  const entity = (info.headings && info.headings[0]) || info.title || label ||
                 (info.breadcrumb || []).filter(Boolean).slice(-1)[0] || route;
  const bits = [];
  // Embedded dashboard: name its panels (the distinctive part), not just "monitor dashboards".
  const panels = (info.frames || []).flatMap((f) => (f.inner && f.inner.panels) || []);
  const dashFrame = panels.length ||
    (info.frames || []).some((f) => /grafana|dashboard|kibana/i.test(f.src || ''));
  if (dashFrame) bits.push(panels.length ? `dashboard: ${panels.slice(0, 4).join(', ')}` : 'embedded dashboard');
  // Distinctive columns — the single strongest "what is this page about" signal.
  const cols = [...new Set((info.tables || []).flatMap((t) => t.columns || [])
    .map((c) => (c || '').trim()).filter((c) => c && c.length <= 14))].slice(0, 4);
  if (cols.length) bits.push(`lists ${cols.join('/')}`);
  // Real action verbs present on buttons — what the user can DO here.
  const actions = [...new Set((info.buttons || []).filter((b) =>
    /新增|新建|创建|添加|注册|导入|导出|下发|发布|部署|扩容|缩容|重启|回滚|删除|编辑|配置|审批|巡检|同步|approve|create|add|new|import|export|deploy|delete|edit|config|restart|rollback|scale/i
      .test(b)))].slice(0, 3);
  if (actions.length) bits.push(`actions: ${actions.join('/')}`);
  // Multiple tabs → name them so multi-view pages are distinguishable.
  const tabs = [...new Set((info.tabs || []).map((t) => (t || '').trim()).filter(Boolean))].slice(0, 4);
  if (tabs.length > 1) bits.push(`tabs: ${tabs.join('/')}`);
  // Fall back to charts/metrics only when nothing more distinctive was found.
  if (!bits.length) {
    if (info.charts) bits.push(`${info.charts} chart(s)`);
    else if (info.metrics && info.metrics.length) bits.push(`shows ${info.metrics.slice(0, 3).join('/')}`);
  }
  return bits.length ? `${entity} — ${bits.join('; ')}` : entity;
}

function appendModuleDoc(route, label, info) {
  const lines = [
    `\n## ${label || route}  \n\`${route}\``,
    `- **Purpose**: ${synthesizePurpose(route, label, info)}`,
    info.headings.length ? `- **Headings**: ${info.headings.join(' / ')}` : '',
    info.filters.length ? `- **Filters/Inputs**: ${info.filters.join(', ')}` : '',
    info.selects?.length ? info.selects.map((s) =>
      `- **Select "${s.placeholder || '(unlabeled)'}"**: ${s.options.length ? s.options.join(', ') : '(no static options)'}`).join('\n') : '',
    info.buttons.length ? `- **Actions**: ${info.buttons.join(', ')}` : '',
    info.tables.length ? info.tables.map((t, i) => `- **Table ${i + 1} columns**: ${t.columns.join(', ')}`).join('\n') : '',
    info.charts ? `- **Charts**: ${info.charts}` : '',
    info.metrics.length ? `- **Metrics/Cards**: ${info.metrics.join(', ')}` : '',
  ];
  // Embedded iframes — the real content of dashboard/external-system modules.
  for (const f of info.frames || []) {
    lines.push(`- **Embedded iframe**: ${f.src}${f.sameOrigin ? '' : ' (cross-origin — src only)'}`);
    const inner = f.inner;
    if (inner) {
      if (inner.title) lines.push(`  - Title: ${inner.title}`);
      // panelCount (DOM element count) is authoritative — emit it, not any row-header "(N panels)".
      if (inner.panelCount) lines.push(`  - Panel count (DOM, authoritative): ${inner.panelCount}`);
      if (inner.panelGroups?.length) lines.push(`  - Panel groups: ${inner.panelGroups.join('; ')}`);
      if (inner.panels?.length) lines.push(`  - Panel titles: ${inner.panels.join('; ')}`);
      if (inner.variables?.length) lines.push(`  - Variables: ${inner.variables.join(', ')}`);
      if (!inner.panelCount && inner.dashboardState) lines.push(`  - Dashboard state: ${inner.dashboardState}`);
      if (inner.tables?.length) lines.push(`  - Table columns: ${inner.tables.map((t) => t.columns.join(' | ')).join(' || ')}`);
    }
  }
  fs.appendFileSync(DESIGN_DOC, lines.filter(Boolean).join('\n') + '\n');
}

// Main flow (context already launched via Mode 1 or Mode 2 above; ONE page reused).
// runInfo = { mode, profile, profileFreePreflight } from the bash Mode-2 preflight.
async function traverse(page, baseUrl, runInfo = {}) {
  // Step 0 — prove login state ONCE, then open the run log (reproducibility).
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await settleDynamicContent(page, { timeout: 8000 });
  const landingUrl = assertNotOnLogin(page);   // throws & stops before wasting a full crawl
  const runLog = openRunLog({ ...runInfo, baseUrl, landingUrl });

  let cp = loadCheckpoint();
  if (!cp) {
    const routes = await enumerateRoutes(page);
    cp = { visited: [], pending: routes, data: {} };
    saveCheckpoint(cp);
    if (!fs.existsSync(DESIGN_DOC)) fs.writeFileSync(DESIGN_DOC, `# SPA Design Doc — ${baseUrl}\n`);
    runLog.routeCount = routes.length; saveRunLog(runLog);
  }
  while (cp.pending.length) {
    const { route, label } = cp.pending[0];
    try {
      await gotoRoute(page, baseUrl, route);
      await settleDynamicContent(page);        // Step 2.5 — wait for panels/tabs/rows
      assertNotOnLogin(page);                   // a route may bounce to login if a token lapsed
      const info = await extractModule(page);
      // Enforced per-module screenshot: record the path, or the failure — never a silent skip.
      const shot = `/tmp/module-${cp.visited.length}.png`;
      let screenshot = shot;
      try { await page.screenshot({ path: shot, fullPage: true }); }
      catch (se) { screenshot = null; console.error(`  ⚠ screenshot failed for ${route}: ${se.message}`); }
      appendModuleDoc(route, label, info);
      cp.data[route] = { label, info, screenshot };
      runLog.modules.push({ route, label, screenshot, purpose: synthesizePurpose(route, label, info) });
      console.log(`✓ ${cp.visited.length + 1}: ${label} ${route}${screenshot ? '' : ' (NO SCREENSHOT)'}`);
    } catch (e) {
      console.error(`✗ ${route}: ${e.message}`); // record failure, keep going
      cp.data[route] = { label, error: e.message };
      runLog.modules.push({ route, label, error: e.message });
    }
    cp.visited.push(cp.pending.shift());
    saveCheckpoint(cp); // persist after EVERY module → crash-safe, resumable
    saveRunLog(runLog);
  }
  runLog.finishedAt = new Date().toISOString();
  runLog.missingScreenshots = runLog.modules.filter((m) => !m.error && !m.screenshot).length;
  saveRunLog(runLog);
  console.log(`Done: ${cp.visited.length} modules → ${DESIGN_DOC} (run log: ${RUN_LOG})`);
}
```

### Assembling into one runnable script (Step 0 → 4, no missing references)

The snippets above are the pieces of a single `/tmp/spa-traverse.js`. Concatenate them into
ONE file in this order and it runs end-to-end — every helper is a `function`/`async function`
declaration, so declarations hoist and inter-helper call order does not matter; only these
three things must be right:

1. **Header (once, at top):**
   ```javascript
   const { chromium } = require('playwright');
   const fs = require('fs');
   const os = require('os');           // Mode 2 only (userDataDir path)
   const path = require('path');       // Mode 2 only
   const RUN_LOG = '/tmp/spa-run-log.json';
   const CHECKPOINT = '/tmp/spa-traversal.json';
   const DESIGN_DOC = '/tmp/spa-design-doc.md';
   const TARGET_URL = '...';            // Mode 1: dev server; Mode 2: authenticated URL
   ```
   Declare `fs` and the three path constants **exactly once** (they appear in Step 0 and
   Step 4 snippets — do not paste both copies).
2. **All helper declarations**, in any order (hoisted): `assertNotOnLogin`, `openRunLog`,
   `saveRunLog` (Step 0); `enumerateRoutes` (Step 1); `gotoRoute` (Step 2); `revealTabsAndRows`,
   `readSelectOptions`, `settleDynamicContent` (Step 2.5); `extractModule` (Step 3);
   `loadCheckpoint`, `saveCheckpoint`, `synthesizePurpose`, `appendModuleDoc`, `traverse`
   (Step 4). Call graph that must resolve: `settleDynamicContent → revealTabsAndRows`;
   `extractModule → readSelectOptions`; `appendModuleDoc`/`traverse → synthesizePurpose`;
   `traverse → assertNotOnLogin, openRunLog, saveRunLog, enumerateRoutes, gotoRoute,
   settleDynamicContent, extractModule, appendModuleDoc, loadCheckpoint, saveCheckpoint`.
   All are defined above, so the assembled file has no dangling reference.
3. **IIFE at the very end** — launch the context (Mode 1 `chromium.launch()` or Mode 2
   `chromium.launchPersistentContext(...)`), reuse ONE page, call `traverse`, close in `finally`:
   ```javascript
   (async () => {
     let context;
     try {
       context = await chromium.launch({ headless: false }); // or Mode 2 persistent context
       const page = context.pages()[0] || (await context.newPage());
       await traverse(page, TARGET_URL, { mode: 'mode1' }); // runInfo from bash preflight
     } catch (e) { console.error('FATAL:', e.message); }
     finally { if (context) await context.close(); } // release singleton lock (Mode 2)
   })();
   ```
   Run it via the universal runner: `cd ${SKILL_HOME}/scripts/js && node run.js /tmp/spa-traverse.js`
   (the runner injects `chromium`, but re-`require`ing it as above is harmless and keeps the file
   self-contained). For a long crawl, background it per the § "Long crawls" note below.

**Resuming**: on re-run, `loadCheckpoint()` returns the saved state and the loop continues
from `pending` — already-visited modules are skipped and the design doc is extended, not
overwritten. Delete `/tmp/spa-traversal.json` to force a full re-crawl.

**Long crawls (50+ modules)**: a full-site crawl runs for many minutes. macOS bash has **no
`timeout` command** (that's GNU coreutils), so do NOT wrap the run in `timeout 600 …` — it
errors `command not found` and the crawl never starts. Instead run the script in the
background and tail its progress; the resumable checkpoint means a killed run loses nothing:

```bash
cd ${SKILL_HOME}/scripts/js && nohup node run.js /tmp/spa-traverse.js > /tmp/spa-crawl.log 2>&1 &
tail -f /tmp/spa-crawl.log          # watch "✓ N: <label>" lines; Ctrl-C stops tail, not the crawl
```

**Coverage report**: at the end, `cp.data` holds every route keyed by hash; count entries
with `error` to report which modules failed vs succeeded, and diff `visited` against a fresh
`enumerateRoutes()` to catch nav items that only appear after login/permission loads.

**Run log / reproducibility**: `/tmp/spa-run-log.json` records the Mode-2 preflight result
(`profileFreePreflight`), the authenticated `landingUrl` (proving the crawl was NOT on a
login page), the route count, and per-module `{ purpose, screenshot | error }`. Use
`missingScreenshots === 0` and a non-login `landingUrl` as the two self-checks that the run
is trustworthy before writing up the design doc.

---

## JavaScript Patterns

### Basic Page Test

```javascript
// /tmp/playwright-test-page.js
const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:3001'; // Auto-detected or from user

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto(TARGET_URL);
  console.log('Page loaded:', await page.title());

  await page.screenshot({ path: '/tmp/screenshot.png', fullPage: true });
  console.log('Screenshot saved to /tmp/screenshot.png');

  await browser.close();
})();
```

### Responsive Design Testing (Multiple Viewports)

```javascript
// /tmp/playwright-test-responsive.js
const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:3001';

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  const viewports = [
    { name: 'Desktop', width: 1920, height: 1080 },
    { name: 'Tablet', width: 768, height: 1024 },
    { name: 'Mobile', width: 375, height: 667 },
  ];

  for (const viewport of viewports) {
    console.log(`Testing ${viewport.name} (${viewport.width}x${viewport.height})`);
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto(TARGET_URL);
    await page.waitForTimeout(1000);
    await page.screenshot({
      path: `/tmp/${viewport.name.toLowerCase()}.png`,
      fullPage: true,
    });
  }

  console.log('All viewports tested');
  await browser.close();
})();
```

### Login Flow

```javascript
// /tmp/playwright-test-login.js
const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:3001';

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto(`${TARGET_URL}/login`);

  await page.fill('input[name="email"]', 'test@example.com');
  await page.fill('input[name="password"]', 'password123');
  await page.click('button[type="submit"]');

  await page.waitForURL('**/dashboard');
  console.log('Login successful, redirected to dashboard');

  await browser.close();
})();
```

### Form Filling and Submission

```javascript
// /tmp/playwright-test-form.js
const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:3001';

(async () => {
  const browser = await chromium.launch({ headless: false, slowMo: 50 });
  const page = await browser.newPage();

  await page.goto(`${TARGET_URL}/contact`);

  await page.fill('input[name="name"]', 'John Doe');
  await page.fill('input[name="email"]', 'john@example.com');
  await page.fill('textarea[name="message"]', 'Test message');
  await page.click('button[type="submit"]');

  await page.waitForSelector('.success-message');
  console.log('Form submitted successfully');

  await browser.close();
})();
```

### Broken Link Checker

```javascript
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  await page.goto('http://localhost:3000');

  const links = await page.locator('a[href^="http"]').all();
  const results = { working: 0, broken: [] };

  for (const link of links) {
    const href = await link.getAttribute('href');
    try {
      const response = await page.request.head(href);
      if (response.ok()) {
        results.working++;
      } else {
        results.broken.push({ url: href, status: response.status() });
      }
    } catch (e) {
      results.broken.push({ url: href, error: e.message });
    }
  }

  console.log(`Working links: ${results.working}`);
  console.log('Broken links:', results.broken);

  await browser.close();
})();
```

### Screenshot with Error Handling

```javascript
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: false });
  const page = await browser.newPage();

  try {
    await page.goto('http://localhost:3000', {
      waitUntil: 'networkidle',
      timeout: 10000,
    });
    await page.screenshot({ path: '/tmp/screenshot.png', fullPage: true });
    console.log('Screenshot saved to /tmp/screenshot.png');
  } catch (error) {
    console.error('Error:', error.message);
  } finally {
    await browser.close();
  }
})();
```

### Inline Execution (Simple Tasks)

For quick one-off tasks, execute code inline without creating files:

```bash
cd ${SKILL_HOME}/scripts/js && node run.js "
const browser = await chromium.launch({ headless: false });
const page = await browser.newPage();
await page.goto('http://localhost:3001');
await page.screenshot({ path: '/tmp/quick-screenshot.png', fullPage: true });
console.log('Screenshot saved');
await browser.close();
"
```

**When to use inline vs files:**
- **Inline**: Quick one-off tasks (screenshot, check if element exists, get page title)
- **Files**: Complex tests, responsive design checks, anything user might want to re-run

---

## Python Patterns

### Basic Automation with Server Lifecycle

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:5173')
    page.wait_for_load_state('networkidle')
    # ... your automation logic
    browser.close()
```

### Reconnaissance-Then-Action Pattern

1. **Inspect rendered DOM**:
   ```python
   page.screenshot(path='/tmp/inspect.png', full_page=True)
   content = page.content()
   page.locator('button').all()
   ```

2. **Identify selectors** from inspection results

3. **Execute actions** using discovered selectors

---

## Cross-Language Patterns

### Taking Screenshots

**JavaScript:**
```javascript
await page.screenshot({ path: '/tmp/screenshot.png', fullPage: true });
await page.locator('.chart').screenshot({ path: '/tmp/chart.png' });
```

**Python:**
```python
page.screenshot(path='/tmp/screenshot.png', full_page=True)
page.locator('.chart').screenshot(path='/tmp/chart.png')
```

### Error Handling

**JavaScript:**
```javascript
try {
  await page.goto(url, { waitUntil: 'networkidle', timeout: 10000 });
} catch (error) {
  console.error('Error:', error.message);
  await page.screenshot({ path: '/tmp/error-screenshot.png' });
} finally {
  await browser.close();
}
```

**Python:**
```python
try:
    page.goto(url, wait_until='networkidle', timeout=10000)
except Exception as e:
    print(f'Error: {e}')
    page.screenshot(path='/tmp/error-screenshot.png')
finally:
    browser.close()
```

---

## Helper Functions

Optional utility functions in `${SKILL_HOME}/scripts/js/lib/helpers.js`:

```javascript
const helpers = require('./lib/helpers');

// Detect running dev servers (CRITICAL - use this first!)
const servers = await helpers.detectDevServers();

// Safe click with retry
await helpers.safeClick(page, 'button.submit', { retries: 3 });

// Safe type with clear
await helpers.safeType(page, '#username', 'testuser');

// Take timestamped screenshot
await helpers.takeScreenshot(page, 'test-result');

// Handle cookie banners
await helpers.handleCookieBanner(page);

// Extract table data
const data = await helpers.extractTableData(page, 'table.results');
```

---

## Custom HTTP Headers

Configure custom headers for all HTTP requests via environment variables.

### Single Header

```bash
PW_HEADER_NAME=X-Automated-By PW_HEADER_VALUE=playwright-skill \
  cd ${SKILL_HOME}/scripts/js && node run.js /tmp/my-script.js
```

### Multiple Headers (JSON)

```bash
PW_EXTRA_HEADERS='{"X-Automated-By":"playwright-skill","X-Debug":"true"}' \
  cd ${SKILL_HOME}/scripts/js && node run.js /tmp/my-script.js
```

### Using Headers in Scripts

```javascript
const context = await helpers.createContext(browser);
const page = await context.newPage();
// All requests include custom headers
```

For raw Playwright API:
```javascript
const context = await browser.newContext(
  getContextOptionsWithHeaders({ viewport: { width: 1920, height: 1080 } }),
);
```
