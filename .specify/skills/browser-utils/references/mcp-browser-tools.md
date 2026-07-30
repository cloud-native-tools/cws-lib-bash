# MCP Browser-Use Tools Reference (Tier 2)

Tier 2 strategy: operate the desktop Chrome browser via the `browser-use` MCP connector.
The agent communicates with a real browser through MCP tool calls — no script files needed.

This reference covers all available `browser-use` MCP tools, common operation patterns, and best practices.

---

## Available Tools

| Tool | Purpose | Key Parameters |
|------|---------|---------------|
| `navigate_page` | Navigate to a URL or browser action | `url`, `type` (url/back/forward/reload) |
| `take_snapshot` | Get page a11y tree as text (element list with uid) | `filePath` (optional save path) |
| `take_screenshot` | Capture page screenshot | `filePath`, `fullPage`, `uid` (optional) |
| `click` | Click an element by uid | `uid`, `dblClick` (optional) |
| `fill` | Fill an input or textarea by uid | `uid`, `value` |
| `press_key` | Press a key or key combination | `key` (e.g. "Enter", "Control+A") |
| `hover` | Hover over an element by uid | `uid` |
| `drag` | Drag to a target element by uid | `uid` |
| `upload_file` | Upload a file | — |
| `handle_dialog` | Accept or dismiss a dialog | — |
| `wait_for` | Wait for specific text to appear | `text`, `timeout` |
| `evaluate_script` | Execute JS in page context, return JSON | `function` (JS function body), `args` (optional) |
| `list_pages` | List all browser tabs | — |
| `select_page` | Switch to a specific tab | — |
| `list_network_requests` | List captured network requests | — |
| `list_console_messages` | List browser console messages | — |

---

## Core Operation Pattern

The MCP browser-use approach follows a **snapshot-then-act** pattern:

1. **Navigate** to the target page
2. **Take a snapshot** to get the a11y tree with element uids
3. **Act** on elements using their uids (click, fill, etc.)
4. **Verify** with screenshot or another snapshot

### Step 1: Navigate

```
navigate_page(url="https://example.com", type="url")
```

### Step 2: Take Snapshot

```
take_snapshot()
```

The returned text lists all interactive elements with their `uid` values.
Each uid is a short string like `abc123` that uniquely identifies the element.

> **Always use the latest snapshot.** After any action that changes the page
> (navigation, click that opens a modal, etc.), take a new snapshot before
> the next action.

### Step 3: Act on Elements

```
# Click a button
click(uid="abc123")

# Fill an input
fill(uid="def456", value="hello@example.com")

# Press Enter
press_key(key="Enter")
```

### Step 4: Verify

```
# Visual verification
take_screenshot(filePath="/tmp/result.png", fullPage=true)

# Or take a new snapshot to inspect the DOM state
take_snapshot()
```

---

## Common Patterns

### Login Flow

```
# 1. Navigate to login page
navigate_page(url="https://example.com/login")

# 2. Snapshot to find form fields
take_snapshot()

# 3. Fill credentials
fill(uid="<email-input-uid>", value="user@example.com")
fill(uid="<password-input-uid>", value="password123")

# 4. Submit
click(uid="<submit-button-uid>")

# 5. Wait for redirect
wait_for(text="Dashboard", timeout=10000)

# 6. Verify
take_screenshot(filePath="/tmp/login-result.png")
```

### Form Submission

```
# 1. Navigate and snapshot
navigate_page(url="https://example.com/contact")
take_snapshot()

# 2. Fill all fields
fill(uid="<name-uid>", value="John Doe")
fill(uid="<email-uid>", value="john@example.com")
fill(uid="<message-uid>", value="Hello, this is a test.")

# 3. Screenshot before submit
take_screenshot(filePath="/tmp/before-submit.png")

# 4. Submit
click(uid="<submit-uid>")

# 5. Verify success
wait_for(text="Thank you", timeout=10000)
take_screenshot(filePath="/tmp/after-submit.png")
```

### Data Extraction

```
# Navigate and wait for content
navigate_page(url="https://example.com/data")
wait_for(text="Results", timeout=15000)

# Extract structured data via evaluate_script
evaluate_script(function="""
() => {
  const rows = [];
  document.querySelectorAll('table tbody tr').forEach(tr => {
    const cells = Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim());
    rows.push(cells);
  });
  return JSON.stringify(rows);
}
""")
```

### Multi-Tab Operation

```
# List all open tabs
list_pages()

# Switch to a specific tab
select_page()

# Navigate in the new tab
navigate_page(url="https://example.com/another-page")
```

---

## Best Practices

1. **Snapshot before every action** — uids from stale snapshots may be invalid after page changes
2. **Prefer snapshot over screenshot** — snapshots give structured element data; screenshots are for visual verification only
3. **Use `wait_for` for dynamic content** — don't guess timing; wait for the text that confirms the page is ready
4. **Screenshot key states** — save screenshots before and after critical actions for debugging
5. **Handle dialogs explicitly** — if a dialog appears, use `handle_dialog` before continuing
6. **Use `evaluate_script` for bulk extraction** — faster than multiple click/fill operations for data scraping

---

## Limitations

- **No persistent sessions**: Each browser-use session starts fresh; cookies and localStorage do not persist across sessions unless the browser profile is configured to retain them
- **Snapshot size**: Large pages may produce very large snapshot text; use `evaluate_script` with targeted queries instead
- **No file download**: The MCP tools do not directly support triggering downloads; use `evaluate_script` to fetch data programmatically
- **Single tab focus**: All tools operate on the "currently selected page"; use `list_pages` + `select_page` to switch context
