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

function create_submodule_remote() {
  local temp_root="$1"
  local work_dir="${temp_root}/submodule-work"
  local remote_dir="${temp_root}/submodule-remote.git"

  mkdir -p "${work_dir}"
  git init "${work_dir}" >/dev/null
  git -C "${work_dir}" commit --allow-empty -m "init" >/dev/null
  echo "submodule-v1" >"${work_dir}/version.txt"
  git -C "${work_dir}" add version.txt
  git -C "${work_dir}" commit -m "submodule v1" >/dev/null
  git -C "${work_dir}" tag sub-v1

  git clone --bare "${work_dir}" "${remote_dir}" >/dev/null

  echo "submodule-v2" >"${work_dir}/version.txt"
  git -C "${work_dir}" commit -am "submodule v2" >/dev/null
  git -C "${work_dir}" push origin main >/dev/null 2>&1 || {
    git -C "${work_dir}" remote add origin "${remote_dir}"
    git -C "${work_dir}" push -u origin main >/dev/null
  }

  echo "${remote_dir}"
}

function create_main_remote() {
  local temp_root="$1"
  local submodule_remote="$2"
  local work_dir="${temp_root}/main-work"
  local remote_dir="${temp_root}/main-remote.git"

  mkdir -p "${work_dir}"
  git init "${work_dir}" >/dev/null
  echo "main" >"${work_dir}/README.md"
  git -C "${work_dir}" add README.md
  git -C "${work_dir}" commit -m "main init" >/dev/null

  git -C "${work_dir}" submodule add "${submodule_remote}" api >/dev/null
  git -C "${work_dir}/api" checkout sub-v1 >/dev/null
  git -C "${work_dir}" add api
  git -C "${work_dir}" commit -am "add submodule" >/dev/null
  git -C "${work_dir}" tag v1

  git -C "${work_dir}" checkout -b feature >/dev/null
  git -C "${work_dir}/api" pull --ff-only origin main >/dev/null
  git -C "${work_dir}" add api
  git -C "${work_dir}" commit -m "update submodule" >/dev/null

  git clone --bare "${work_dir}" "${remote_dir}" >/dev/null
  git --git-dir="${remote_dir}" symbolic-ref HEAD refs/heads/main >/dev/null

  echo "${remote_dir}"
}

function run_git_switch_submodule_recovery_test() {
  local temp_root
  temp_root="$(mktemp -d)"
  trap 'rm -rf "${temp_root}"' RETURN

  setup_git_identity "${temp_root}/home"

  local submodule_remote
  submodule_remote="$(create_submodule_remote "${temp_root}")"
  local main_remote
  main_remote="$(create_main_remote "${temp_root}" "${submodule_remote}")"
  local clone_dir="${temp_root}/repo"

  git clone --recurse-submodules "${main_remote}" "${clone_dir}" >/dev/null
  cd "${clone_dir}" || return 1

  rm -rf api

  echo "Test 1: git_switch can switch to branch with missing submodule worktree"
  git_switch feature >/tmp/git_switch_branch.out 2>/tmp/git_switch_branch.err
  local exit_code=$?
  test_assert_success "${exit_code}" "子模块目录缺失时 switch 到 feature 分支应成功"
  test_assert_eq "feature" "$(git branch --show-current)" "应切换到 feature 分支"
  test_assert_eq "submodule-v2" "$(cat api/version.txt)" "子模块内容应更新到 feature 版本"

  rm -rf .git/modules/api

  echo "Test 2: git_switch recovers broken submodule metadata and switches to tag"
  git_switch v1 >/tmp/git_switch_tag.out 2>/tmp/git_switch_tag.err
  exit_code=$?
  test_assert_success "${exit_code}" "损坏子模块元数据后切换 tag 应成功"
  test_assert_eq "" "$(git branch --show-current)" "切换到 tag 后应处于 detached HEAD"
  test_assert_eq "submodule-v1" "$(cat api/version.txt)" "子模块内容应回退到 tag 版本"

  local stderr_output
  stderr_output="$(cat /tmp/git_switch_tag.err)"
  TEST_TOTAL=$((TEST_TOTAL + 1))
  if [[ "${stderr_output}" == *"fatal: not a git repository"* ]]; then
    echo "  ✗ 不应再出现损坏子模块 gitdir 的 fatal 错误"
    echo "    stderr: ${stderr_output}"
    TEST_FAILED=$((TEST_FAILED + 1))
  else
    echo "  ✓ 不再出现损坏子模块 gitdir 的 fatal 错误"
    TEST_PASSED=$((TEST_PASSED + 1))
  fi

  rm -rf .git/modules/api api

  echo "Test 3: git_switch without args refreshes and initializes submodule"
  git_switch >/tmp/git_switch_noarg.out 2>/tmp/git_switch_noarg.err
  exit_code=$?
  test_assert_success "${exit_code}" "无参数调用 git_switch 应成功刷新子模块"
  test_assert_eq "submodule-v1" "$(cat api/version.txt)" "无参数调用后子模块内容应与当前提交一致"

  stderr_output="$(cat /tmp/git_switch_noarg.err)"
  TEST_TOTAL=$((TEST_TOTAL + 1))
  if [[ "${stderr_output}" == *"Could not access submodule"* ]]; then
    echo "  ✗ 无参数调用不应出现 Could not access submodule 错误"
    echo "    stderr: ${stderr_output}"
    TEST_FAILED=$((TEST_FAILED + 1))
  else
    echo "  ✓ 无参数调用不再出现 Could not access submodule 错误"
    TEST_PASSED=$((TEST_PASSED + 1))
  fi
}

run_git_switch_submodule_recovery_test

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
