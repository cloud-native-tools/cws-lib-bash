#!/usr/bin/env bash

# ai-harness family tests: the ah_* helpers must drive ai-harness only, and the
# uninstall path must never remove the independent Spec Kit package.
# Structure mirrors test_specify.sh.

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
INSTALL_LOG="${STUB_DIR}/install.log"
: > "${AH_LOG}"
: > "${SPECIFY_LOG}"
: > "${PIP_LOG}"
: > "${INSTALL_LOG}"

function have() { return 0; }
function ah_ensure() { return 0; }
function ai-harness() { printf '%s\n' "$*" >> "${AH_LOG:?}"; }
function specify() { printf '%s\n' "$*" >> "${SPECIFY_LOG:?}"; }
function pip3() {
  if [[ "$1" == "show" ]]; then
    return 0
  fi
  printf '%s\n' "$*" >> "${PIP_LOG:?}"
  return 0
}

export AH_LOG SPECIFY_LOG PIP_LOG INSTALL_LOG

# --- ah_init_all drives ai-harness, never the Spec Kit CLI -----------------
ah_init_all demo >/dev/null 2>&1
assert_eq "4" "$(wc -l < "${AH_LOG}" | tr -d ' ')" \
  "ah_init_all should call ai-harness once per tool"
assert_contains "$(cat "${AH_LOG}")" \
  "init demo --ai claude --script sh --no-git --force --skip-tls --ignore-agent-tools" \
  "claude init must use ai-harness with --ignore-agent-tools"
assert_eq "" "$(cat "${SPECIFY_LOG}")" "ah_init_all must not call the Spec Kit CLI"

# --- ah_install delegates to ai-harness's install.sh (no uv required) ------
cat > "${STUB_DIR}/fake-install.sh" <<'EOS'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${INSTALL_LOG:?}"
EOS
chmod +x "${STUB_DIR}/fake-install.sh"
export AI_HARNESS_INSTALL_SH="${STUB_DIR}/fake-install.sh"

if ah_install --python /fake/python >/dev/null 2>&1; then
  install_rc=0
else
  install_rc=$?
fi
assert_eq "0" "${install_rc}" "ah_install should delegate without uv"
assert_contains "$(cat "${INSTALL_LOG}")" "--python /fake/python" \
  "ah_install must forward its arguments to install.sh"

# --- ah_uninstall never removes the Spec Kit package -----------------------
ah_uninstall >/dev/null 2>&1
assert_contains "$(cat "${PIP_LOG}")" "uninstall -y ai-harness-cli" \
  "ah_uninstall should remove ai-harness-cli"
assert_true "[[ '$(cat "${PIP_LOG}")' != *specify-cli* ]]" \
  "ah_uninstall must not remove specify-cli (Spec Kit owns that package)"

# --- deinit split: ah.* copies only ---------------------------------------
mkdir -p "${STUB_DIR}/cwd/.qoder/commands" \
  "${STUB_DIR}/cwd/.ah/scripts" \
  "${STUB_DIR}/cwd/.ah/templates" \
  "${STUB_DIR}/cwd/.ah/memory/features"
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
assert_true "[[ ! -e '${STUB_DIR}/cwd/.ah/scripts' ]]" \
  "ah_deinit should remove the installed .ah/scripts"
assert_true "[[ ! -e '${STUB_DIR}/cwd/.ah/templates' ]]" \
  "ah_deinit should remove the installed .ah/templates"

rm -rf "${STUB_DIR}"
print_summary
