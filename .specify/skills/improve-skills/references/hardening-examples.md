# Worked Examples: Hardening a Reference Helper

Two before/after cases distilled from a real multi-round optimization loop of the
`browser-utils` skill. Each shows the **brittle version**, the **runtime symptom the
executor actually observed**, the **hardened version**, and the **general lesson**.
Use these as the template when Workflow Step 4 says "harden reference helpers that read
a live third-party/framework DOM". The pattern generalizes to any helper that scrapes a
DOM/API/log you do not control.

---

## Example 1 — Interaction-gated content (a loop that toggled its own state)

**Goal**: enumerate every left-nav route of an SPA to visit each module.

**Brittle version** — clicks every submenu title to reveal children:

```js
// BUG: clicks EVERY submenu, so already-open menus get toggled SHUT.
for (const el of document.querySelectorAll('.ant-menu-submenu > .ant-menu-submenu-title')) {
  el.click();
}
const routes = [...document.querySelectorAll('.ant-menu-item a')].map(a => a.getAttribute('href'));
```

**Runtime symptom the executor saw**: the run was green (no throw) but `routes.length === 0`
on the second pass — the first pass had opened the menus, the second pass clicked the
now-open titles and collapsed them, so no leaf `<a>` was in the DOM. Silent
under-extraction, not a crash.

**Hardened version** — act only on the closed nodes, gated by ground-truth state:

```js
// Only expand submenus that are actually CLOSED; read state, don't blind-toggle.
for (const t of document.querySelectorAll(
       '.ant-menu-submenu:not(.ant-menu-submenu-open) > .ant-menu-submenu-title')) {
  if (t.getAttribute('aria-expanded') === 'false') t.click();
}
```

**General lesson**: a toggle is not idempotent — never blind-click stateful controls.
Read the element's own state signal (`aria-expanded`, an `-open` class) and act only when
it disagrees with the state you want. Treat an empty result on a page you *know* has the
element as a **silent-under-extraction defect**, not as "the page is empty".

---

## Example 2 — Version-drifting selector + text scope (title body-leak)

**Goal**: capture each Grafana panel's title from an embedded dashboard.

**Brittle version** — reads the whole header's `textContent`:

```js
// BUG: textContent of the header container swallows the panel BODY too.
const title = document.querySelector('.panel-title').textContent;
```

**Runtime symptom the executor saw**: on a STAT/TABLE panel the captured "title" came out
as `告警数61189` — the label `告警数` concatenated with the metric value `61189` from the
panel body. On newer "scenes"-build dashboards `.panel-title` matched **0 nodes**
(class was renamed / emotion-hashed), so the title silently went blank.

**Hardened version** — read a ground-truth attribute scoped to the leaf, query old + new shapes:

```js
// Prefer the header's data-testid ATTRIBUTE (exact title, no body), across versions.
const el = document.querySelector(
  '[data-testid^="data-testid Panel header"], h6[class*="panel-title"], .panel-title');
const title = el?.getAttribute('data-testid')
  ? el.getAttribute('data-testid').replace(/^data-testid Panel header /, '')
  : (el?.querySelector('.panel-title-text')?.textContent ?? el?.textContent ?? '').trim();
```

**General lesson**: three compounding rules —
1. **Prefer a ground-truth/attribute signal** the framework sets deliberately
   (`data-testid`, `aria-label`) over `textContent`, which absorbs sibling/body text.
2. **Scope to the leaf/header node**, not an ancestor container; post-filtering a polluted
   string (length caps, regex trims) is a backstop, not the fix.
3. **Query the old AND current DOM shapes** for third-party embeds — they rename
   classes/`data-testid`s between versions, so a single selector silently matches 0 nodes.
   An empty result on a page known to have the element is a **drift signal to re-check**.

---

## The reusable checklist (applies to any live-DOM/API/log helper)

- Is the content **interaction-gated**? Options, tab bodies, popovers and menus that mount
  only on click — e.g. a component library's `<Select>` that renders its options into a
  **portal** outside the trigger's own subtree — cannot be read by a static-DOM scrape. The
  fix is a bounded open → read → close pass at the driver level, not a richer static selector.
- Is the control **stateful**? Read its state; act only on the nodes that need it.
- Is the value from a **convenient-but-emitted label** (a "(N panels)" header, a "3 results"
  badge, a status pill)? Derive it from the underlying **elements** instead; when they
  disagree, the elements win and you stop surfacing the label.
- Is the text from a **container**? Re-scope to the **leaf**; verify the captured field is
  the datum the doc claims (a selected *value* is not the variable's *name*). Post-filtering
  a polluted string with a length cap is a backstop, never the fix.
- Is the target **third-party/versioned**? Query old + current shapes; treat empty-on-known-present
  as drift, not absence.
- Did the run go **green but thin**? Empty/thin output is a defect — capture *which selector
  matched 0 nodes* as the reusable fact, then re-run to confirm the fix populates.
