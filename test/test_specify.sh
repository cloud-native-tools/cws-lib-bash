#!/usr/bin/env bash

# shellcheck disable=SC2030,SC2031,SC2034,SC2329  # scoped PATH/env + sourced helpers

# Spec Kit family tests: the specify_* helpers must drive the Spec Kit CLI,
# never ai-harness (and vice versa for the ah_* family in test_ai_harness.sh).

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
: > "${SPECIFY_LOG}"
: > "${AH_LOG}"

cat > "${STUB_DIR}/specify-cli" <<'EOS'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "${SPECIFY_LOG:?}"
EOS
chmod +x "${STUB_DIR}/specify-cli"

function ai_harness_ensure() { return 0; }
function ai-harness() { printf '%s\n' "$*" >> "${AH_LOG:?}"; }
function have() { return 0; }

export SPECIFY_CLI_BIN="${STUB_DIR}/specify-cli"
export SPECIFY_LOG AH_LOG

specify_init_all demo >/dev/null 2>&1
assert_eq "4" "$(wc -l < "${SPECIFY_LOG}" | tr -d ' ')" \
  "specify_init_all should call the Spec Kit CLI once per tool"
assert_contains "$(cat "${SPECIFY_LOG}")" \
  "init demo --script sh --no-git --force --skip-tls --ai claude --ignore-agent-tools" \
  "claude init must use the Spec Kit CLI with --ignore-agent-tools"
assert_contains "$(cat "${SPECIFY_LOG}")" "--ai copilot" \
  "copilot init must use the Spec Kit CLI"
assert_eq "" "$(cat "${AH_LOG}")" "specify_init_all must not call ai-harness"

# --- deinit split: speckit.* copies only -----------------------------------
mkdir -p "${STUB_DIR}/cwd/.qoder/commands"
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

# --- PATH probe: `specify` is trusted only when it identifies as Spec Kit ---
unset SPECIFY_CLI_BIN
mkdir -p "${STUB_DIR}/fakebin"
cat > "${STUB_DIR}/fakebin/specify" <<'EOS'
#!/usr/bin/env bash
printf 'ai-harness-cli 0.0.22\n'
EOS
chmod +x "${STUB_DIR}/fakebin/specify"
if (PATH="${STUB_DIR}/fakebin:${PATH}"; specify_cli_path_bin >/dev/null 2>&1); then
  probe_result="accepted"
else
  probe_result="rejected"
fi
assert_eq "rejected" "${probe_result}" \
  "a non-Spec-Kit specify on PATH must be rejected"

cat > "${STUB_DIR}/fakebin/specify" <<'EOS'
#!/usr/bin/env bash
printf 'specify-cli 0.0.22\n'
EOS
chmod +x "${STUB_DIR}/fakebin/specify"
probe_result="$(PATH="${STUB_DIR}/fakebin:${PATH}" specify_cli_path_bin 2>/dev/null || true)"
assert_eq "${STUB_DIR}/fakebin/specify" "${probe_result}" \
  "a genuine Spec Kit specify on PATH must be accepted"

rm -rf "${STUB_DIR}"
print_summary
