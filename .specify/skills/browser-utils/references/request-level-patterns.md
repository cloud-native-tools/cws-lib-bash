# Request-Level Patterns (Tier 2/3 请求级方向)

The request-level direction replaces DOM click simulation with the underlying
network calls, issued **in the page's own JavaScript context** so the session
(cookies, tokens) is inherited automatically. Verified by PoC (2026-08-22):
`page.evaluate(fetch(...))` against a cookie-gated endpoint returns 200 with
the session and 401 without it — no header assembly needed.

Use it when: a `recipe.json` exists for the site (optimization/validation/
sealed states), or when exploration has already revealed the exact request a
step needs. Do not use it to skip exploration on a site with no memory.

## Capture (exploration phase)

Record the real requests the page issues while you operate it (Playwright):

```js
page.on('request',  req  => { /* method, url, postData */ });
page.on('response', res  => { /* status, top-level JSON keys */ });
```

Feed each captured call to the site-memory engine as a `kind: "network"`
record — redacted (`<cookie:name>`, `<resolve:...>` placeholders), never raw
credentials. The engine rejects raw-looking values at write time.

## Replay (all phases with a recipe)

Execute one recipe step inside the page context:

```js
const result = await page.evaluate(async ([url, body]) => {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => null);
  return { status: res.status, keys: data ? Object.keys(data) : [] };
}, [step.url, resolvedParams]);
```

- Resolve `dynamic_fields` first: `page-var` reads a JS global in the page,
  `cookie` reads `document.cookie` (or is implied by the session),
  `prev-request` takes the field from an earlier step's response.
- Judge the step against the recipe's `expect`: `status` exact match,
  `json_keys` subset of the actual top-level keys.
- A failed step in validation/sealed states means drift: record the
  expected-vs-actual pair as evidence and roll the site back to optimization.

## Tier 3 equivalent (MCP connector + Chrome extension)

The same in-page evaluation channel exists through the bridge
(`scripts/bridge/`): `evaluate` runs CDP `Runtime.evaluate` with
`awaitPromise: true, returnByValue: true`, and `execInPage` runs in the MAIN
world — both inherit the page session exactly like `page.evaluate`. Use the
same resolve → fetch → judge sequence; only the transport differs.

## Guardrails

- Write/mutation calls follow the skill's existing confirmation requirements —
  the request-level direction makes execution cheaper, not less careful.
- Never persist response bodies into site memory; only `response_shape`
  (status + key list). Business data flows to the user's task, not to disk.
- If a step cannot be request-ified (captcha, signed SDK calls you cannot
  reproduce), mark it `type: "page"` with a `reason` in the recipe instead of
  forcing it.
