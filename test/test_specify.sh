#!/usr/bin/env bash

# shellcheck disable=SC2034,SC2329  # env vars/functions consumed by sourced helpers

# Spec Kit family tests: the specify_* helpers must drive the Spec Kit CLI,
# never ai-harness (and vice versa for the ah_* family in test_ai_harness.sh).
# specify_install must delegate to spec-kit's own install.sh with no uv
# requirement.

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../bin/cws_bash_test"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/313_ai_harness.sh"
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/../scripts/313_specify.sh"

# --- shared specify_user helper (defined in 313_ai_harness.sh) -------------
# Container runtime: agent CLIs run as the image's develop account.
function is_container() {
  return 0
}
assert_eq "develop:develop" "$(specify_user)" "container should use develop"

CWS_DEVELOP_USER=custom
CWS_DEVELOP_GROUP=customgrp
assert_eq "custom:customgrp" "$(specify_user)" "container should honor CWS_DEVELOP_* overrides"
unset CWS_DEVELOP_USER CWS_DEVELOP_GROUP

# Docker host (physical or VM): agent CLIs run as the host operator account.
function is_container() {
  return 1
}
assert_eq "agent:agent" "$(specify_user)" "docker host should use agent"

# --- family split: specify_init_all drives Spec Kit, never ai-harness ------
STUB_DIR="$(mktemp -d "${TMPDIR:-/tmp}/cws-specify-test.XXXXXX")"
SPECIFY_LOG="${STUB_DIR}/specify.log"
AH_LOG="${STUB_DIR}/ah.log"
INSTALL_LOG="${STUB_DIR}/install.log"
: > "${SPECIFY_LOG}"
: > "${AH_LOG}"
: > "${INSTALL_LOG}"

function ai_harness_ensure() { return 0; }
function ai-harness() { printf '%s\n' "$*" >> "${AH_LOG:?}"; }
function have() { return 0; }
function specify_ensure() { return 0; }
function specify() { printf '%s\n' "$*" >> "${SPECIFY_LOG:?}"; }

export SPECIFY_LOG AH_LOG INSTALL_LOG

specify_init_all demo >/dev/null 2>&1
assert_eq "4" "$(wc -l < "${SPECIFY_LOG}" | tr -d ' ')" \
  "specify_init_all should call the Spec Kit CLI once per tool"
assert_contains "$(cat "${SPECIFY_LOG}")" \
  "init demo --ai claude --script sh --no-git --force --skip-tls --ignore-agent-tools" \
  "claude init must use the Spec Kit CLI with --ignore-agent-tools"
assert_contains "$(cat "${SPECIFY_LOG}")" "--ai copilot" \
  "copilot init must use the Spec Kit CLI"
assert_eq "" "$(cat "${AH_LOG}")" "specify_init_all must not call ai-harness"

# --- specify_install delegates to spec-kit's install.sh (no uv required) ---
cat > "${STUB_DIR}/fake-install.sh" <<'EOS'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${INSTALL_LOG:?}"
EOS
chmod +x "${STUB_DIR}/fake-install.sh"
export SPECIFY_INSTALL_SH="${STUB_DIR}/fake-install.sh"

if specify_install --python /fake/python >/dev/null 2>&1; then
  install_rc=0
else
  install_rc=$?
fi
assert_eq "0" "${install_rc}" "specify_install should delegate without uv"
assert_contains "$(cat "${INSTALL_LOG}")" "--python /fake/python" \
  "specify_install must forward its arguments to install.sh"

# --- deinit split: speckit.* copies only -----------------------------------
mkdir -p "${STUB_DIR}/cwd/.qoder/commands" \
  "${STUB_DIR}/cwd/.specify/scripts" \
  "${STUB_DIR}/cwd/.specify/templates" \
  "${STUB_DIR}/cwd/.specify/memory/features"
touch "${STUB_DIR}/cwd/.qoder/commands/speckit.demo.md"
touch "${STUB_DIR}/cwd/.qoder/commands/ah.demo.md"
(
  cd "${STUB_DIR}/cwd" || exit 1
  specify_deinit qoder >/dev/null 2>&1
)
assert_true "[[ ! -e '${STUB_DIR}/cwd/.qoder/commands/speckit.demo.md' ]]" \
  "specify_deinit should remove speckit command copies"
assert_true "[[ -e '${STUB_DIR}/cwd/.qoder/commands/ah.demo.md' ]]" \
  "specify_deinit must not remove ai-harness command copies"
assert_true "[[ ! -e '${STUB_DIR}/cwd/.specify/scripts' ]]" \
  "specify_deinit should remove the installed .specify/scripts"
assert_true "[[ ! -e '${STUB_DIR}/cwd/.specify/templates' ]]" \
  "specify_deinit should remove the installed .specify/templates"

rm -rf "${STUB_DIR}"
print_summary
