#!/bin/bash

# Tests for the probe layer (profile.d/02_probe.sh): is_* properties and has_* capabilities

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "${script_dir}/.." && pwd)"
source "${project_root}/bin/cws_bash_env"

total_tests=0
passed_tests=0
failed_tests=0

function log_test_result() {
  local passed="$1"
  local desc="$2"
  if [ "${passed}" == "true" ]; then
    echo "[PASS] ${desc}"
    passed_tests=$((passed_tests + 1))
  else
    echo "[FAIL] ${desc}"
    failed_tests=$((failed_tests + 1))
  fi
  total_tests=$((total_tests + 1))
}

function check_true() {
  local desc="$1"
  shift
  if "$@"; then
    log_test_result true "${desc}"
  else
    log_test_result false "${desc}"
  fi
}

function check_false() {
  local desc="$1"
  shift
  if "$@"; then
    log_test_result false "${desc}"
  else
    log_test_result true "${desc}"
  fi
}

function check_equal() {
  local expected="$1"
  local actual="$2"
  local desc="$3"
  if [ "${expected}" == "${actual}" ]; then
    log_test_result true "${desc}"
  else
    log_test_result false "${desc} (expected: ${expected}, actual: ${actual})"
  fi
}

echo "==============================================="
echo "Testing capability primitives (has_*)"
echo "==============================================="

check_true "has_cmd finds an existing command" has_cmd bash
check_false "has_cmd rejects a missing command" has_cmd cws_no_such_command_xyz
check_false "has_cmd rejects empty input" has_cmd ""
check_equal "" "$(has_cmd bash)" "has_cmd is silent on success"
check_equal "" "$(has_cmd cws_no_such_command_xyz 2>&1)" "has_cmd is silent on failure"

check_equal "$(has_cmd mamba && echo yes || echo no)" "$(has_mamba && echo yes || echo no)" "has_mamba mirrors has_cmd mamba"
check_equal "$(has_cmd conda && echo yes || echo no)" "$(has_conda && echo yes || echo no)" "has_conda mirrors has_cmd conda"

echo ""
echo "==============================================="
echo "Testing command resolver (has_cmd / cmd_path)"
echo "==============================================="

# 模拟 command 内建不可用：用同名函数遮蔽它（等价于受限 shell / 内建被移除）
function with_broken_command() {
  (
    command() { return 127; }
    "$@"
  )
}

ls_path=$(cmd_path ls)
if [ -n "${ls_path}" ] && [ -x "${ls_path}" ]; then
  log_test_result true "cmd_path resolves an executable file (${ls_path})"
else
  log_test_result false "cmd_path resolves an executable file (got: ${ls_path})"
fi

check_equal "cd" "$(cmd_path cd)" "cmd_path keeps shell builtins as-is"
check_false "cmd_path fails for a missing command" cmd_path cws_no_such_command_xyz
check_equal "" "$(cmd_path cws_no_such_command_xyz 2>/dev/null)" "cmd_path prints nothing for a missing command"

check_true "has_cmd survives when the command builtin is unusable" with_broken_command has_cmd ls
check_true "has_cmd keeps builtins when the command builtin is unusable" with_broken_command has_cmd cd
check_false "has_cmd still rejects missing commands when command is unusable" with_broken_command has_cmd cws_no_such_command_xyz
check_equal "" "$(with_broken_command has_cmd cws_no_such_command_xyz 2>&1)" "has_cmd stays silent when command is unusable"

broken_path=$(with_broken_command cmd_path ls)
if [ -n "${broken_path}" ] && [ -x "${broken_path}" ]; then
  log_test_result true "cmd_path falls back to type/hash/which (${broken_path})"
else
  log_test_result false "cmd_path falls back to type/hash/which (got: ${broken_path})"
fi
check_equal "" "$(with_broken_command cmd_path cws_no_such_command_xyz 2>/dev/null)" "cmd_path prints nothing for a missing command when command is unusable"

echo ""
echo "==============================================="
echo "Testing property predicates (is_*)"
echo "==============================================="

if [ "$(id -u)" -eq 0 ]; then
  check_true "is_root agrees with id -u" is_root
else
  check_false "is_root agrees with id -u" is_root
fi

if is_linux && is_macos; then
  log_test_result false "is_linux and is_macos are mutually exclusive (both true)"
elif ! is_linux && ! is_macos; then
  log_test_result false "is_linux and is_macos are mutually exclusive (both false)"
else
  log_test_result true "is_linux and is_macos are mutually exclusive"
fi

echo ""
echo "==============================================="
echo "Testing run environment detection (probe_env / virt_type)"
echo "==============================================="

probe_output=$(probe_env)
case "${probe_output}" in
  container:* | vm:* | baremetal | unknown:*)
    log_test_result true "probe_env returns a known form (${probe_output})"
    ;;
  *)
    log_test_result false "probe_env returns a known form (got: ${probe_output})"
    ;;
esac

# 三分互斥：至多一个为真（unknown 时全为假）
tri_state=$(is_container && echo c; is_vm && echo v; is_baremetal && echo b)
case "${tri_state}" in
  "" | "c" | "v" | "b")
    log_test_result true "is_container/is_vm/is_baremetal are mutually exclusive"
    ;;
  *)
    log_test_result false "is_container/is_vm/is_baremetal are mutually exclusive (got: ${tri_state})"
    ;;
esac

# 缓存可被覆盖：用注入值验证分类与展示逻辑，不依赖真实环境
unset __CWS_PROBE_ENV
__CWS_PROBE_ENV="container:docker"
check_true "is_container reads cached container value" is_container
check_equal "docker" "$(virt_type)" "virt_type prints container type"

__CWS_PROBE_ENV="vm:kvm"
check_false "is_container is false for cached vm value" is_container
check_true "is_vm reads cached vm value" is_vm
check_equal "kvm" "$(virt_type)" "virt_type prints vm type"

__CWS_PROBE_ENV="baremetal"
check_true "is_baremetal reads cached baremetal value" is_baremetal
check_equal "none" "$(virt_type)" "virt_type prints none for baremetal"

__CWS_PROBE_ENV="unknown:lxc-alike"
check_false "unknown environment is not reported as baremetal" is_baremetal
check_false "unknown environment is not reported as container" is_container
check_false "unknown environment is not reported as vm" is_vm
check_equal "lxc-alike" "$(virt_type)" "virt_type prints raw type for unknown environment"

unset __CWS_PROBE_ENV

echo ""
echo "==============================================="
echo "Testing type classification helpers"
echo "==============================================="

check_true "_probe_is_container_type accepts docker" _probe_is_container_type docker
check_true "_probe_is_container_type accepts podman" _probe_is_container_type podman
check_true "_probe_is_container_type accepts kubernetes" _probe_is_container_type kubernetes
check_false "_probe_is_container_type rejects kvm" _probe_is_container_type kvm
check_false "_probe_is_container_type rejects none" _probe_is_container_type none

check_true "_probe_is_vm_type accepts kvm" _probe_is_vm_type kvm
check_true "_probe_is_vm_type accepts vmware" _probe_is_vm_type vmware
check_false "_probe_is_vm_type rejects docker" _probe_is_vm_type docker
check_false "_probe_is_vm_type rejects none" _probe_is_vm_type none

echo ""
echo "==============================================="
echo "Testing probe consumers (have / get_core_count / is_git_repo)"
echo "==============================================="

check_true "have succeeds for an existing command" have bash 2>/dev/null
have_missing_msg=$(have cws_no_such_command_xyz 2>&1)
if have cws_no_such_command_xyz >/dev/null 2>&1; then
  log_test_result false "have fails for a missing command"
else
  log_test_result true "have fails for a missing command"
fi
case "${have_missing_msg}" in
  *cws_no_such_command_xyz*) log_test_result true "have reports the missing command" ;;
  *) log_test_result false "have reports the missing command (got: ${have_missing_msg})" ;;
esac

core_count=$(get_core_count)
if [ "${core_count}" -ge 1 ] 2>/dev/null; then
  log_test_result true "get_core_count returns a positive integer (${core_count})"
else
  log_test_result false "get_core_count returns a positive integer (got: ${core_count})"
fi

check_equal "$(has_cmd git && echo yes || echo no)" "$(has_git && echo yes || echo no)" "has_git means the git command is available"

if git rev-parse --show-toplevel >/dev/null 2>&1; then
  check_true "is_git_repo agrees with git rev-parse" is_git_repo
else
  check_false "is_git_repo agrees with git rev-parse" is_git_repo
fi

tmp_dir=$(mktemp -d)
if (cd "${tmp_dir}" && is_git_repo); then
  log_test_result false "is_git_repo is false outside a git work tree"
else
  log_test_result true "is_git_repo is false outside a git work tree"
fi
rmdir "${tmp_dir}" 2>/dev/null

echo ""
echo "==============================================="
echo "Testing Python venv probes (is_venv / has_venv)"
echo "==============================================="

# is_venv：看 VIRTUAL_ENV —— 未设/悬空为假，指向真目录为真，conda 不算
saved_virtual_env="${VIRTUAL_ENV:-__cws_unset__}"
unset VIRTUAL_ENV
check_false "is_venv is false without VIRTUAL_ENV" is_venv

VIRTUAL_ENV="${project_root}"
check_true "is_venv is true for an existing env dir" is_venv

VIRTUAL_ENV="${project_root}/no_such_venv_dir"
check_false "is_venv is false for a dangling VIRTUAL_ENV" is_venv

unset VIRTUAL_ENV
export CONDA_PREFIX="/opt/cws_fake_conda"
check_false "is_venv ignores conda environments" is_venv
unset CONDA_PREFIX

if [ "${saved_virtual_env}" = "__cws_unset__" ]; then
  unset VIRTUAL_ENV
else
  export VIRTUAL_ENV="${saved_virtual_env}"
fi

# has_venv / venv_python：看项目目录下的 .venv —— 需目录存在且解释器可执行
fake_proj=$(mktemp -d)
check_false "has_venv is false without a venv dir" has_venv "${fake_proj}/.venv"
check_false "venv_python fails without a venv dir" venv_python "${fake_proj}/.venv"

mkdir -p "${fake_proj}/.venv/bin"
printf '#!/bin/sh\nexit 0\n' >"${fake_proj}/.venv/bin/python"
chmod +x "${fake_proj}/.venv/bin/python"
check_true "has_venv accepts a venv with an executable python" has_venv "${fake_proj}/.venv"
check_equal "${fake_proj}/.venv/bin/python" "$(venv_python "${fake_proj}/.venv")" "venv_python returns the interpreter path"
check_equal ".venv/bin/python" "$(cd "${fake_proj}" && venv_python)" "venv_python defaults to .venv in the current directory"

chmod -x "${fake_proj}/.venv/bin/python"
check_false "has_venv rejects a non-executable python" has_venv "${fake_proj}/.venv"

rm -f "${fake_proj}/.venv/bin/python"
ln -s /no/such/python "${fake_proj}/.venv/bin/python"
check_false "has_venv rejects a dangling interpreter symlink" has_venv "${fake_proj}/.venv"

rm -rf "${fake_proj}"

if [ -x "${project_root}/.venv/bin/python" ]; then
  if (cd "${project_root}" && has_venv); then
    log_test_result true "has_venv finds this repository's .venv"
  else
    log_test_result false "has_venv finds this repository's .venv"
  fi
fi

echo ""
echo "==============================================="
echo "Test Summary:"
echo "  Total tests: ${total_tests}"
echo "  Passed: ${passed_tests}"
echo "  Failed: ${failed_tests}"
echo "==============================================="

if [ ${failed_tests} -eq 0 ]; then
  echo "All probe tests passed!"
  exit 0
else
  echo "✗ ${failed_tests} probe test(s) failed!"
  exit 1
fi
