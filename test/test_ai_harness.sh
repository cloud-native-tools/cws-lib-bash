#!/usr/bin/env bash

# ai-harness family tests: the ah_* helpers must drive ai-harness only, and the
# uninstall path must never remove the independent Spec Kit package.

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/313_ai_harness.sh"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/313_specify.sh"

STUB_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cws-ah-test.XXXXXX")"
AH_LOG="${STUB_DIR}/ah.log"
SPECIFY_LOG="${STUB_DIR}/specify.log"
PIP_LOG="${STUB_DIR}/pip.log"
: > "${AH_LOG}"
: > "${SPECIFY_LOG}"
: > "${PIP_LOG}"

function ai_harness_ensure() { return 0; }
function ai-harness() { printf '%s\n' "$*" >> "${AH_LOG:?}"; }
function have() { return 0; }
function pip3() {
  if [[ "$1" == "show" ]]; then
    return 0
  fi
  printf '%s\n' "$*" >> "${PIP_LOG:?}"
  return 0
}

export AH_LOG SPECIFY_LOG PIP_LOG

# --- ah_init_all drives ai-harness, never the Spec Kit CLI -----------------
ah_init_all demo >/dev/null 2>&1
assert_eq "4" "$(wc -l < "${AH_LOG}" | tr -d ' ')" \
  "ah_init_all should call ai-harness once per tool"
assert_contains "$(cat "${AH_LOG}")" "init demo --ai claude --script sh" \
  "ah_init_all must call ai-harness init"
assert_eq "" "$(cat "${SPECIFY_LOG}")" "ah_init_all must not call the Spec Kit CLI"

# --- ah_uninstall never removes the Spec Kit package -----------------------
ah_uninstall >/dev/null 2>&1
assert_contains "$(cat "${PIP_LOG}")" "uninstall -y ai-harness-cli" \
  "ah_uninstall should remove ai-harness-cli"
assert_true "[[ '$(cat "${PIP_LOG}")' != *specify-cli* ]]" \
  "ah_uninstall must not remove specify-cli (Spec Kit owns that package)"

# --- deinit split: ah.* copies only ---------------------------------------
mkdir -p "${STUB_DIR}/cwd/.qoder/commands"
touch "${STUB_DIR}/cwd/.qoder/commands/ah.demo.md"
touch "${STUB_DIR}/cwd/.qoder/commands/speckit.demo.md"
(
  cd "${STUB_DIR}/cwd" || exit 1
  ah_deinit qoder >/dev/null 2>&1
)
assert_true "[[ ! -e '${STUB_DIR}/cwd/.qoder/commands/ah.demo.md' ]]" \
  "ah_deinit should remove ai-harness command copies"
assert_true "[[ -e '${STUB_DIR}/cwd/.qoder/commands/speckit.demo.md' ]]" \
  "ah_deinit must not remove Spec Kit command copies"

rm -rf "${STUB_DIR}"
print_summary
