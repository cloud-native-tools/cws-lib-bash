#!/bin/bash

# Test script for motd_render / motd_generate (scripts/010_motd.sh)
# Covers: host fact rendering, identity overlay rendering, missing overlay,
# and writing to a custom target without touching /etc/motd.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/../profile.d/00_vars.sh"
source "${SCRIPT_DIR}/../profile.d/02_utils.sh"

GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CLEAR='\033[0m'

test_count=0
passed_count=0
failed_count=0

function test_result() {
  local test_name="$1"
  local expected_code="$2"
  local actual_code="$3"

  test_count=$((test_count + 1))

  if [ "${actual_code}" -eq "${expected_code}" ]; then
    echo -e "${GREEN}✓ PASS${CLEAR}: ${test_name}"
    passed_count=$((passed_count + 1))
  else
    echo -e "${RED}✗ FAIL${CLEAR}: ${test_name} (expected: ${expected_code}, actual: ${actual_code})"
    failed_count=$((failed_count + 1))
  fi
}

function test_contains() {
  local test_name="$1"
  local haystack="$2"
  local needle="$3"

  if printf '%s' "${haystack}" | grep -qF -- "${needle}"; then
    test_result "${test_name}" 0 0
  else
    test_result "${test_name}" 0 1
  fi
}

function test_not_contains() {
  local test_name="$1"
  local haystack="$2"
  local needle="$3"

  if printf '%s' "${haystack}" | grep -qF -- "${needle}"; then
    test_result "${test_name}" 0 1
  else
    test_result "${test_name}" 0 0
  fi
}

WORK_DIR=$(mktemp -d)
trap 'rm -rf "${WORK_DIR}"' EXIT

IDENTITY_FILE="${WORK_DIR}/motd.env"
cat >"${IDENTITY_FILE}" <<'EOF'
ENV_ID=workspace_docker_common_service
ENV_KIND=ecs
ENV_ROLE=common-service
ENV_ROLE_LABEL='通用容器 + workspace mirror server'
ENV_RESPONSIBILITY='部署通用容器；所有 workspace 环境的 mirror server；运行容器，不做镜像构建'
ENV_CLASS='container-deploy'
ENV_SITE='cn'
ENV_REGION='cn-hangzhou'
ENV_LEVEL='test'
ENV_OWNER='寒枝'
ENV_POLICY='05_环境管理/artifacts/common-envs/container-deploy/README.md'
ENV_SSH_PROFILE='workspace_docker_common_service'
ENV_PROFILE_ID='root@workspace_docker_common_service'
ENV_MANAGED_BY='profiles-envs + 05_环境管理'
ENV_AS_OF=2026-11-12
ENV_SOURCE_COMMIT=deadbeef
EOF

export CWS_MOTD_ENV_FILE="${IDENTITY_FILE}"
export CWS_MOTD_TARGET="${WORK_DIR}/motd"
source "${SCRIPT_DIR}/../scripts/010_motd.sh"

echo -e "${BLUE}=== motd_render with identity overlay ===${CLEAR}"
output=$(motd_render)
rc=$?
test_result "motd_render exits 0" 0 "${rc}"
test_contains "renders IDENTITY section" "${output}" "[ IDENTITY ]"
test_contains "renders environment id" "${output}" "workspace_docker_common_service"
test_contains "renders role" "${output}" "common-service"
test_contains "renders responsibility text" "${output}" "所有 workspace 环境的 mirror server"
test_contains "renders owner" "${output}" "寒枝"
test_contains "renders policy pointer" "${output}" "container-deploy/README.md"
test_contains "renders runtime profile" "${output}" "Runtime profile"
test_contains "renders HOST section" "${output}" "[ HOST ]"
test_contains "renders CPU line" "${output}" "CPU"
test_contains "renders NET section" "${output}" "[ NET ]"
test_contains "renders RUNTIME section" "${output}" "[ RUNTIME ]"

echo -e "\n${BLUE}=== motd_render without identity overlay ===${CLEAR}"
export CWS_MOTD_ENV_FILE="${WORK_DIR}/missing.env"
output_missing=$(motd_render)
rc=$?
test_result "motd_render missing overlay exits 0" 0 "${rc}"
test_contains "missing overlay is reported" "${output_missing}" "not configured"
test_contains "host facts still render" "${output_missing}" "[ HOST ]"
test_not_contains "missing overlay drops role" "${output_missing}" "common-service"

echo -e "\n${BLUE}=== motd_generate writes a custom target ===${CLEAR}"
export CWS_MOTD_ENV_FILE="${IDENTITY_FILE}"
motd_generate >/dev/null 2>&1
test_result "motd_generate exits 0" 0 $?
test_result "motd target created" 0 $([ -f "${CWS_MOTD_TARGET}" ] && echo 0 || echo 1)
generated=$(cat "${CWS_MOTD_TARGET}")
test_contains "generated motd keeps identity" "${generated}" "workspace_docker_common_service"
test_contains "generated motd keeps host facts" "${generated}" "[ HOST ]"

echo -e "\n${BLUE}=== motd_generate rejects a missing target directory ===${CLEAR}"
motd_generate "${WORK_DIR}/no-such-dir/motd" >/dev/null 2>&1
test_result "motd_generate fails on missing directory" 1 $?

echo
echo -e "${BLUE}=== Test Results Summary ===${CLEAR}"
echo "Total tests: ${test_count}"
echo -e "Passed: ${GREEN}${passed_count}${CLEAR}"
echo -e "Failed: ${RED}${failed_count}${CLEAR}"

if [ "${failed_count}" -eq 0 ]; then
  echo -e "${GREEN}All tests passed!${CLEAR}"
  exit 0
else
  echo -e "${RED}Some tests failed.${CLEAR}"
  exit 1
fi
