# Focus-Safe Browser Launch

> **This document is the owner** of one fact: *how browser-utils launches a browser so the
> window never contends for the user's system focus* — including the macOS **CDP-attach**
> channel (a real logged-in Chrome driven via `connectOverCDP`), which the F0–F2 ladder does
> not cover. Every other file in this skill (SKILL.md Strict Requirements, the per-agent guides,
> the launch recipes) references this ladder instead of restating it.
>
> **Focus red line (non-negotiable):** *no automation method — headless, headed, virtual display,
> CDP-attached real Chrome, MCP connector, or a shell `open` — may steal the user's system focus
> or pop a window/tab in front of their work.* Focus theft causes mistyped input and interrupts
> real work; it outranks every convenience of "just get the run to pass".

## Why this exists

A headed Chromium window mapped onto the user's desktop is activated by the window manager,
so it takes keyboard focus away from whatever the user was doing. Automation runs are long and
unattended; each run therefore interrupts real work. Two secondary facts make the interruption
unnecessary:

- **Visual evidence never needs focus.** Screenshots, video, PDF and a11y snapshots are
  captured over CDP, not by reading the screen — they are produced identically when nothing is
  visible or focused.
- **Headed mode needs a display, and fails hard without one.** Verified on a headless Linux
  box: `headless: false` aborts with
  `ERROR:ui/ozone/platform/x11/ozone_platform_x11.cc] Missing X server or $DISPLAY` →
  `The platform failed to initialize. Exiting.` So "visible by default" is not merely
  intrusive, it is broken on any container/CI/SSH host.

## The ladder

Resolve top-down and take the **first** rung that satisfies the task. Run the probe
(`§ Resolving the rung`) instead of judging the environment by eye.

| Rung | Mode | Desktop presence | Focus risk | When |
|------|------|------------------|------------|------|
| **F0** | `headless: true` | none | **impossible** | Default. Any unattended automation, scraping, assertion, screenshot, responsive sweep. |
| **F1** | headed on a **virtual display** (`xvfb-run -a …`) | none | **impossible** | Headed rendering fidelity is genuinely required (a bug reproduces only headed) **and** the host is Linux X11 with `xvfb` installed. |
| **F2** | headed on the **user's desktop** | real window | **best effort only** | The user explicitly asked to watch the run live. Never chosen silently. |

F0 is the default because it is the only rung whose focus risk is *structurally* zero rather
than mitigated. Prefer F0; escalate to F1 only for headed-only defects; escalate to F2 only on
an explicit user request.

### F0 — headless (default)

```javascript
const browser = await chromium.launch({ headless: true });
```

Modern Playwright headless drives the real browser engine (no legacy headless emulation gap),
and `page.screenshot()`, `page.video()`, `page.pdf()` and `locator.ariaSnapshot()` all
work. Verified by execution on Playwright **1.61.1** on a host with no `DISPLAY` at all: a
`file://` fixture rendered, asserted, produced an 8 KB PNG, and `page.pdf()` produced a 5.7 KB PDF.

> **Trap**: `page.accessibility.snapshot()` is gone — `page.accessibility` is `undefined` on
> 1.61.1, so calling it throws before any screenshot is written. Use `locator.ariaSnapshot()`.

### F1 — headed on a virtual display (Linux)

Real headed Chromium rendering to an off-screen X server, so nothing appears on the user's
screen while headed-only behaviour is reproduced exactly.

**The canonical F1 consumer is MV3 extension testing.** `skills/browser-extension` documents that
extension service workers and popups require headed mode, so it cannot use F0 at all — F1 is what
lets it meet that hard requirement with zero desktop presence instead of opening a window over the
user's work. Any consumer skill whose task genuinely cannot run headless belongs here, not at F2.

```bash
# -a = "Try to get a free server number, starting at 99" (Debian xvfb-run(1))
xvfb-run -a --server-args="-screen 0 1440x900x24" \
  bash -c 'cd ${SKILL_HOME}/scripts/js && node run.js /tmp/playwright-test-*.js'
```

Requires the `xvfb` package. If `xvfb-run` is missing, **do not attempt to install it and do
not silently fall back to F2** — surface the gap and the fix, then stop:

```
xvfb-run not found. Install it (Debian/Ubuntu: sudo apt-get install xvfb;
RHEL/Fedora: sudo dnf install xorg-x11-server-Xvfb) or re-run with F0 (headless).
```

### F2 — headed on the user's desktop (explicit request only)

Three obligations, all mandatory:

1. **Announce first.** Tell the user a window will appear on their desktop before launching.
2. **Keep the footprint small and fixed.** Pass `--window-size=1280,800` and
   `--window-position=<a corner>`; never `--start-maximized`, `--start-fullscreen` or
   `--kiosk`, which claim the whole screen.
3. **Disclose the residual risk.** No Chromium switch guarantees non-activation — the window
   manager decides. State that the window may still take focus once.

```javascript
const browser = await chromium.launch({
  headless: false,
  args: ['--window-size=1280,800', '--window-position=64,64'],
});
```

Never call `page.bringToFront()` to "make it visible" — capture does not need it, and it is the
one API that deliberately re-activates the window.

**What does and does not trigger F2.** The trigger is the user asking to *watch*, not the user
asking to be *convinced*:

| Counts as an F2 request | Does NOT — answer with evidence at F0 |
|-------------------------|----------------------------------------|
| "open a window so I can see it" | "make sure it actually renders" |
| "let me watch it run" | "verify the page isn't blank" |
| "don't run it headless" | "I got burned by headless before" |
| "show me the browser" | "open it properly so we know it's real" |

The right-hand column asks for **proof of rendering**, which F0 supplies without any window:
screenshot plus non-zero bounding boxes, `locator.ariaSnapshot()`, live
`fill()`/`inputValue()` round-trips, zero console/page errors, and — when blank-render is the
specific fear — a pixel check that the PNG is not a single flat colour, validated against an
`about:blank` control so the detector is proven to fire. Opening a window over the user's work to
answer that question trades their focus for evidence they could have had for free.

If it is genuinely ambiguous which column applies, **ask one question** — never resolve the
ambiguity by opening a window.

## The macOS CDP-attach channel (real logged-in Chrome)

The F0–F2 ladder governs a browser **Playwright launches itself**. On macOS there is a second,
distinct channel that the ladder's Linux-centric rungs do not describe: a **real, headed Google
Chrome** carrying the user's login state, started with `--remote-debugging-port=<port>` and driven
over `chromium.connectOverCDP('http://127.0.0.1:<port>')`. Internal/SSO sites need this because a
bundled/headless Chromium has no login state. It is focus-safe **only if** every step below holds —
the window is real and on the user's desktop, so any activation is a visible focus theft:

1. **Launch it in the background, never by invoking the binary directly.** On macOS use
   `open -g -na "Google Chrome" --args … --remote-debugging-port=<port> --user-data-dir=<profile>`;
   `-g` = "do not bring the application to the foreground", so the window appears without taking
   focus. Invoking `"/Applications/Google Chrome.app/…/Google Chrome"` directly (what
   `chrome_open_trust` and a bare Playwright `channel:'chrome'` launch do) makes macOS activate
   Chrome and steal focus — that is the classic regression this channel must avoid.
2. **Prefer attaching to an already-running Chrome over relaunching.** Probe the CDP endpoint
   first; if it is up, `connectOverCDP` onto it. Do **not** `open -na` / `--new-window` a fresh
   instance every run — repeated new windows are the "popups everywhere" symptom.
3. **Zero re-activation while attached.** Reuse an existing background tab
   (`browser.contexts()[0].pages()[0]`) instead of calling `newPage()` per step; **never call
   `page.bringToFront()`** (screenshots, aria snapshots and in-page `fetch` are CDP capture and
   need no focus); open any genuinely-needed new tab in the background without activating it.
   On macOS, `Target.createTarget` (newPage) and some navigations can raise the window, so tab
   reuse is not merely tidy — it is what keeps the run non-intrusive.

This channel is the macOS counterpart of F0's "capture never needs focus": the window stays put,
the automation drives it over CDP, and the user's keyboard focus is never touched. The front door
that owns the launch/attach sequence is `profiles-browsers` (`agent_chrome_cdp.sh`); it launches
via the `open -g` quiet path and attaches rather than relaunching.

## Considered and rejected as focus mechanisms

| Candidate | Status | Why it is not the answer |
|-----------|--------|--------------------------|
| `--start-minimized` | **does not exist** | Absent from the switch strings of the Chromium build Playwright drives (`chromium-1228`, probed with `strings`). Chromium has no switch for "create a window but do not activate it". |
| `--silent-launch`, `--no-startup-window` | present in the binary | Startup-window suppressors for background/app mode, not de-activation switches. **Not runtime-verified here** — do not rely on them. |
| `--window-position=-32000,-32000` | unverified | Off-screen placement is a Windows-minimized convention; not verified on any host in this repo, and it still maps a window. Use F0 instead. |
| `xdotool` / `wmctrl` post-launch minimize | racy | Fires after the WM has already activated the window, so the focus theft has happened. Also absent on most hosts. |
| macOS `open -g` | real, and **the mechanism for the CDP-attach channel** | `-g` = "Do not bring the application to the foreground"; `--args` forwards flags. It does not apply to F0–F2 (Playwright spawns the binary directly), but it is exactly how the real logged-in Chrome must be launched on macOS — see § The macOS CDP-attach channel. |

## Tier 3 drives the user's live Chrome — always intrusive

The `browser-use` MCP connector operates the desktop Chrome the user is already using:
`navigate_page` and `select_page` change **their** tabs and bring that window forward. There is
no non-intrusive variant, because reusing the real profile is the entire point of the tier.
Therefore Tier 3 is never a silent default — announce that the run will take over the live
browser before the first navigation, and prefer Tier 2/F0 unless the task genuinely needs the
user's session or extensions.

## The legitimate exceptions

Two paths open a window on purpose because a **human** must act in it. Both are exceptions to
the ladder, not violations of it, and both must be announced:

- `scripts/chrome_open_trust.sh` — opens a trusted Chrome so the user can complete an SSO login.
- Mode 2 (real Chrome profile) when the profile's keychain unlock or a login prompt needs a GUI
  session. Keep it headed only for that reason, and say so.

Ask the user to complete the interaction, wait for confirmation, then continue — and never
leave the window open: close the context in a `finally` block so the profile's singleton lock is
released.

## Resolving the rung

The choice is deterministic environment probing plus one judgment input, so it belongs in code:

```bash
python3 ${SKILL_HOME}/scripts/focus-safe-launch.py --help
python3 ${SKILL_HOME}/scripts/focus-safe-launch.py --headed-required false
python3 ${SKILL_HOME}/scripts/focus-safe-launch.py --headed-required true --desktop-window false
```

The script prints the resolved rung, the reason, the wrapper command (e.g. `xvfb-run -a …`) and
the Playwright launch options to use. The caller supplies only the judgment — whether the task
needs headed fidelity and whether the user asked to watch; the environment facts (OS, `DISPLAY`,
`WAYLAND_DISPLAY`, `xvfb-run`, `xdotool`/`wmctrl`) are probed, never assumed.

## Verification provenance

| Claim | How it was established |
|-------|------------------------|
| F0 renders and screenshots with no `DISPLAY` | Executed: `node run.js` against a `file://` fixture on a headless Linux host |
| Headed launch fails without a display | Executed: same probe with `headless: false`, exact error text quoted above |
| `--start-minimized` does not exist | Probed: `strings` over `~/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome` |
| `--silent-launch` / `--no-startup-window` / `--window-position` / `--window-size` / `--kiosk` / `--start-maximized` / `--start-fullscreen` exist | Same `strings` probe |
| `xvfb-run -a` semantics | Debian `xvfb-run(1)` man page |
| macOS `open -g` semantics | Apple `open(1)` documentation |
| `page.accessibility` is `undefined`; `locator.ariaSnapshot()`, `page.screenshot()`, `page.pdf()` work headless | Executed: API-surface probe through `run.js` against the installed Playwright **1.61.1** |
| The Mode 1 quickstart in `playwright-patterns.md` runs green as edited | Executed: extracted verbatim from the file and run via `run.js` — "Mode 1 self-test PASSED" |
| The F1 wrapper emitted by `focus-safe-launch.py` is valid, correctly quoted shell | Executed: the emitted string was run verbatim through `bash` and completed a real Playwright script (with a stub `xvfb-run`, since the package is absent here) |
| Actual focus behaviour on a real X11/Wayland desktop | **Not verified** — this repo's host is a headless container. F2's residual risk is disclosed rather than measured. |
| F1 with a real `xvfb-run` (not a stub) | **Not verified** — `xvfb` is not installed on this host; the install command is surfaced instead of being auto-run |
