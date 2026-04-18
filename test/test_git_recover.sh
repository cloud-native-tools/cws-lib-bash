#!/usr/bin/env bash

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/.." && pwd)"

export INJECT_DIR=""
source "${project_root}/bin/cws_bash_env"

set -u

TEST_TOTAL=0
TEST_PASSED=0
TEST_FAILED=0

function test_assert_eq() {
  local expected="$1"
  local actual="$2"
  local message="$3"

  TEST_TOTAL=$((TEST_TOTAL + 1))
  if [ "${expected}" = "${actual}" ]; then
    echo "  ✓ ${message}"
    TEST_PASSED=$((TEST_PASSED + 1))
  else
    echo "  ✗ ${message}"
    echo "    expected: ${expected}"
    echo "    actual:   ${actual}"
    TEST_FAILED=$((TEST_FAILED + 1))
  fi
}

function test_assert_success() {
  local exit_code="$1"
  local message="$2"

  TEST_TOTAL=$((TEST_TOTAL + 1))
  if [ "${exit_code}" -eq 0 ]; then
    echo "  ✓ ${message}"
    TEST_PASSED=$((TEST_PASSED + 1))
  else
    echo "  ✗ ${message}"
    echo "    exit code: ${exit_code}"
    TEST_FAILED=$((TEST_FAILED + 1))
  fi
}

function setup_git_identity() {
  local home_dir="$1"

  mkdir -p "${home_dir}"
  export HOME="${home_dir}"
  git config --global user.name "cws test"
  git config --global user.email "cws@example.com"
  git config --global protocol.file.allow always
  git config --global init.defaultBranch main
}

function create_remote_repo() {
  local temp_root="$1"
  local work_dir="${temp_root}/source-work"
  local remote_dir="${temp_root}/source-remote.git"

  mkdir -p "${work_dir}"
  git init "${work_dir}" >/dev/null

  echo "v1" >"${work_dir}/version.txt"
  git -C "${work_dir}" add version.txt
  git -C "${work_dir}" commit -m "v1" >/dev/null
  git -C "${work_dir}" tag v1

  echo "v2" >"${work_dir}/version.txt"
  git -C "${work_dir}" commit -am "v2" >/dev/null

  echo "v3" >"${work_dir}/version.txt"
  git -C "${work_dir}" commit -am "v3" >/dev/null

  git clone --bare "${work_dir}" "${remote_dir}" >/dev/null
  git --git-dir="${remote_dir}" symbolic-ref HEAD refs/heads/main >/dev/null

  echo "${remote_dir}"
}

function run_git_recover_test() {
  local temp_root
  temp_root="$(mktemp -d)"
  trap 'rm -rf "${temp_root}"' RETURN

  setup_git_identity "${temp_root}/home"

  local remote_dir
  remote_dir="$(create_remote_repo "${temp_root}")"
  local clone_dir="${temp_root}/recovered-repo"

  git clone --branch v1 --depth 1 "file://${remote_dir}" "${clone_dir}" >/dev/null
  cd "${clone_dir}" || return 1

  echo "Test 1: repository starts as shallow clone from tag"
  test_assert_eq "true" "$(git rev-parse --is-shallow-repository)" "初始仓库应为 shallow"
  test_assert_eq "" "$(git branch --show-current)" "tag depth clone 初始应处于 detached HEAD"

  echo "Test 2: git_recover restores full history and checks out main"
  git_recover main >/tmp/git_recover_main.out 2>/tmp/git_recover_main.err
  local exit_code=$?
  test_assert_success "${exit_code}" "git_recover main 应执行成功"
  test_assert_eq "false" "$(git rev-parse --is-shallow-repository)" "恢复后应为完整仓库"
  test_assert_eq "main" "$(git branch --show-current)" "恢复后当前分支应为 main"
  test_assert_eq "origin/main" "$(git rev-parse --abbrev-ref --symbolic-full-name "@{u}")" "main 应跟踪 origin/main"
  test_assert_eq "3" "$(git rev-list --count HEAD)" "恢复后应包含完整历史提交"

  local stderr_output
  stderr_output="$(cat /tmp/git_recover_main.err)"
  TEST_TOTAL=$((TEST_TOTAL + 1))
  if [[ "${stderr_output}" == *"Remote branch not found"* ]]; then
    echo "  ✗ main 分支应可被恢复并检出"
    echo "    stderr: ${stderr_output}"
    TEST_FAILED=$((TEST_FAILED + 1))
  else
    echo "  ✓ main 分支可被恢复并检出"
    TEST_PASSED=$((TEST_PASSED + 1))
  fi
}

run_git_recover_test

echo
echo "==============================================="
echo "Test Summary:"
echo "  Total tests: ${TEST_TOTAL}"
echo "  Passed: ${TEST_PASSED}"
echo "  Failed: ${TEST_FAILED}"
echo "==============================================="

if [ "${TEST_FAILED}" -eq 0 ]; then
  echo "✓ All tests passed!"
  exit 0
else
  echo "✗ ${TEST_FAILED} test(s) failed!"
  exit 1
fi
