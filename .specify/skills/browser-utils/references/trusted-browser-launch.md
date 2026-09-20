# Trusted Browser Launch (chrome_open_trust)

Generic, portable way to open a site in a Chrome instance with web-security
relaxed for trusted internal/test origins — the standard entry point whenever
a calling skill needs **login-state reuse** against its site.

## When to use

- The target site requires a logged-in session and the caller wants to reuse
  an existing Chrome profile that already holds that login state.
- The site only works (or works better) with relaxed security flags
  (insecure-origin treatment, mixed content) — typical for internal portals.

## Mechanism

Source the shipped function and validate the environment, then launch:

```bash
source ${SKILL_HOME}/scripts/chrome_open_trust.sh
check_chrome_user_data_agent || return 1
chrome_open_trust --user-data-dir="${CHROME_USER_DATA_AGENT}" --new-window <site-url>
```

- `chrome_open_trust()` is frozen from a `declare -f chrome_open_trust`
  original; its launcher is self-contained (self-resolving Chrome binary,
  overridable via `CHROME_MACOS`). If the runtime environment already loads
  a same-named function, prefer the environment's implementation.
- 🛑 **Focus red line (macOS):** `chrome_open_trust` opens a real window for a
  human to complete login, but it must not *yank* the user's focus. On macOS it
  therefore launches through `open -g -na "Google Chrome" --args ...` (`-g` = do
  not bring to the foreground) so the window appears in the background; the human
  clicks it when ready. Set `CHROME_TRUST_FOREGROUND=1` only when a foreground
  window is explicitly wanted and already announced. On non-macOS hosts (no
  `open`) it falls back to a direct background `nohup` binary launch. Announce the
  window before launching either way. See
  [focus-safe-launch.md § The legitimate exceptions](./focus-safe-launch.md).
- Flags applied: `--unsafely-treat-insecure-origin-as-secure=<url>` (when a
  URL is given), `--allow-running-insecure-content`,
  `--reduce-security-for-testing`, `--test-type`. Without an explicit
  `--user-data-dir`, it falls back to a throwaway `${HOME}/tmp` profile —
  for login reuse you MUST pass one explicitly.

## CHROME_USER_DATA_AGENT contract

- `CHROME_USER_DATA_AGENT` is a **user-defined global environment variable**
  pointing to a Chrome profile directory that contains the target site's
  login state.
- It is NOT provided by this skill. If it is unset or invalid,
  `check_chrome_user_data_agent` fails: stop the browser step and prompt the
  user to define the variable (e.g. in their shell rc file). Never continue
  without it and never silently fall back to a throwaway profile.

## After launch

- If the site still shows a login page, prompt the user to complete login in
  the opened window and wait for confirmation before continuing.
- Actual page operations (navigation, script injection, waits, tabs) are
  performed through browser-utils' tier strategy; after the trusted window
  is up, attach to it per the relevant tier guide. Site-specific memory goes
  through `site-memory.py` keyed by the site host (see `site-memory.md`).

## For calling skills

Upper-layer site skills MUST NOT duplicate this function or its validation
logic — reference this document and source the shipped script instead. A site
skill's own text only carries: its site URL, the launch command line, and
its login-prompt rule.
