#!/usr/bin/env bash
# chrome_open_trust — generic trusted-browser launcher (source this file).
#
# Opens a URL in a Chrome instance with web-security relaxed for trusted
# internal/test origins. Fully portable: no machine-specific dependencies.
# Origin: frozen from a profiles-style `declare -f chrome_open_trust`, with
# the launcher made self-contained (self-resolving Chrome binary).
#
# Login-state reuse convention:
#   The caller MUST define a global CHROME_USER_DATA_AGENT environment
#   variable pointing to a Chrome profile directory that already holds the
#   target site's login state, and pass it via --user-data-dir. If it is
#   unset or invalid, stop and ask the user to define it — never fall back
#   to a throwaway profile silently.
#
# Focus-safe ladder exception (human-in-the-loop):
#   This launcher opens a REAL window on the user's desktop, because a human must
#   complete the login in it. It is an exception to the ladder, not a violation of
#   it; the ladder itself is owned by references/focus-safe-launch.md (see § The
#   legitimate exceptions).
#
#   🛑 FOCUS RED LINE — even the human-login window must not YANK focus. On macOS
#   this launcher starts Chrome through `open -g -na "Google Chrome" --args ...`
#   (`-g` = do not bring to the foreground), so the window APPEARS without taking
#   keyboard focus; the human clicks it when ready. Invoking the Chrome binary
#   directly would activate Chrome and steal focus (the classic regression). Set
#   CHROME_TRUST_FOREGROUND=1 ONLY when a foreground window is explicitly wanted
#   and already announced to the user. Announce the window before launching either
#   way, and close it once the login is confirmed.
#
# Usage:
#   source ${SKILL_HOME}/scripts/chrome_open_trust.sh
#   check_chrome_user_data_agent || return 1
#   chrome_open_trust --user-data-dir="${CHROME_USER_DATA_AGENT}" --new-window <site-url>

# Validation for the CHROME_USER_DATA_AGENT environment variable.
check_chrome_user_data_agent() {
  if [[ -z "${CHROME_USER_DATA_AGENT:-}" || ! -d "${CHROME_USER_DATA_AGENT}" ]]; then
    echo "[browser-utils] CHROME_USER_DATA_AGENT is unset or not a directory." >&2
    echo "[browser-utils] Define this global environment variable to point to a Chrome profile directory containing the site's login state, then retry." >&2
    return 1
  fi
}

chrome_open_trust() {
  local url="" a; local -a args=()
  if [ $# -gt 0 ] && [[ "${1}" != -* ]]; then url="${1}"; shift; fi
  local has_profile="false"
  for a in "$@"; do case "${a}" in --user-data-dir=*) has_profile="true";; esac; done
  [ -n "${url}" ] && args+=("${url}" "--unsafely-treat-insecure-origin-as-secure=${url}")
  args+=(--allow-running-insecure-content --reduce-security-for-testing --test-type)
  [ "${has_profile}" = "false" ] && args+=("--user-data-dir=${HOME}/tmp")
  args+=("$@")
  # 🛑 Focus red line: never YANK the user's focus. On macOS launch through
  # `open -g -na` so the window appears in the BACKGROUND (no focus steal); the
  # human clicks it when ready. CHROME_TRUST_FOREGROUND=1 opts into the direct,
  # foreground binary launch ONLY for an announced human-login case. Non-macOS
  # hosts have no `open`, so they use the direct binary path (headless boxes are
  # covered by the F0/F1 ladder, not this launcher).
  local chrome_bin="${CHROME_MACOS:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
  if [[ "$(uname -s)" == "Darwin" && "${CHROME_TRUST_FOREGROUND:-0}" != "1" ]]; then
    open -g -na "Google Chrome" --args "${args[@]}"
  else
    nohup "${chrome_bin}" "${args[@]}" >/dev/null 2>&1 &
  fi
}
