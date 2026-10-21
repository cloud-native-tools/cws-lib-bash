#!/usr/bin/env bash

# ─── Probe Layer (探测层) ────────────────────────────────────────────
# 环境属性与能力探测的唯一归口，供提示符、安装脚本、条件分支复用。
#
# 命名分类：
#   is_*   判断「当前系统/运行环境是什么」——属性，回答"我是不是 X"
#          is_linux / is_macos                     -> 00_vars.sh（基于 BASH_OS）
#          is_bash / is_zsh / is_interactive       -> 02_utils.sh
#          is_root / is_container / is_vm / is_baremetal / is_venv -> 本文件
#   has_*  判断「是否具备某种能力（命令）」——能力，回答"我有没有 X"
#          has_cmd <name>    通用原语，其余 has_* 都是它的薄封装
#          has_mamba / has_conda / has_venv        -> 本文件
#   输出型探测（供展示/诊断/取路径）：
#          probe_env / virt_type / cmd_path / venv_python -> 本文件
#
# 约定：
#   - 谓词只返回 ${RETURN_SUCCESS}/${RETURN_FAILURE}，不打印、不写日志；
#     需要"缺命令就报错"的语义请用 have()（02_utils.sh）或由调用方自行 log
#   - is_container / is_vm / is_baremetal 互斥，构成运行环境三分；
#     探测结果在同一 shell 生命周期内不会变化，缓存在 __CWS_PROBE_ENV，
#     需要重新探测时 unset __CWS_PROBE_ENV 即可
#   - 本文件编号 02，先于 02_utils.sh / 03_prompt.sh 加载，
#     其后所有文件（含 scripts/）都可直接用这些谓词
#   - 域内谓词（如 is_git_repo）不放在本文件，留在各自域文件里，但同样遵守命名约定

# ─── 能力探测原语 ───────────────────────────────────────────────────

# 解析命令，输出其可执行标识（能取到路径时输出路径，否则输出命令名）
# 主路径 command -v（别名/函数/内建/外部命令都能识别）；
# 若 command 内建本身不可用（受限 shell、被同名函数遮蔽、被移除），
# 依次退化为 type -t / type -p（别名/函数/内建/文件）→ hash（已解析命令）→ which（外部兜底）
# Usage: cmd_path <command>
function cmd_path() {
  local cmd=${1}
  if [ -z "${cmd}" ]; then
    return ${RETURN_FAILURE:-1}
  fi

  local resolved=""
  local rc=0

  resolved=$(command -v "${cmd}" 2>/dev/null)
  rc=$?
  if [ ${rc} -eq 0 ] && [ -n "${resolved}" ]; then
    echo "${resolved}"
    return ${RETURN_SUCCESS:-0}
  fi
  if [ ${rc} -ne 127 ]; then
    # command 内建可用且已判定该命令不存在：不再退化，避免误判
    return ${RETURN_FAILURE:-1}
  fi

  # —— 以下是 command 内建不可用时的退化解析 ——
  local kind
  kind=$(type -t "${cmd}" 2>/dev/null)
  if [ -n "${kind}" ]; then
    if [ "${kind}" = "file" ]; then
      resolved=$(type -p "${cmd}" 2>/dev/null)
    fi
    echo "${resolved:-${cmd}}"
    return ${RETURN_SUCCESS:-0}
  fi

  if hash "${cmd}" >/dev/null 2>&1; then
    echo "${cmd}"
    return ${RETURN_SUCCESS:-0}
  fi

  resolved=$(which "${cmd}" 2>/dev/null)
  if [ -n "${resolved}" ]; then
    echo "${resolved}"
    return ${RETURN_SUCCESS:-0}
  fi

  return ${RETURN_FAILURE:-1}
}

# 命令是否可用（静默：不打印路径、不报错）
# 主路径 command -v 不 fork；command 内建不可用时退化为 cmd_path 的多解析器路径
# Usage: has_cmd <command>
function has_cmd() {
  local cmd=${1}
  if [ -z "${cmd}" ]; then
    return ${RETURN_FAILURE:-1}
  fi

  local rc=0
  command -v "${cmd}" >/dev/null 2>&1
  rc=$?
  if [ ${rc} -eq 0 ]; then
    return ${RETURN_SUCCESS:-0}
  fi
  if [ ${rc} -ne 127 ]; then
    return ${RETURN_FAILURE:-1}
  fi

  # 127 表示 command 自身不可用（而非目标命令不存在）：交给不依赖它的解析器
  cmd_path "${cmd}" >/dev/null 2>&1
}

# ─── 系统属性探测 ───────────────────────────────────────────────────

# 是否为 root 用户（读 EUID，不 fork `id -u`）
function is_root() {
  if [ "${EUID:-$(id -u)}" -eq 0 ]; then
    return ${RETURN_SUCCESS:-0}
  else
    return ${RETURN_FAILURE:-1}
  fi
}

# ─── 运行环境探测：容器 / 虚拟机 / 物理机 ───────────────────────────
# 主路径用 systemd-detect-virt（systemd 官方词汇：docker/podman/kvm/vmware/none...）；
# 该命令不存在时（macOS、非 systemd 发行版）退化为痕迹探测。

# 私有的退化探测：无 systemd-detect-virt 时按痕迹判断，输出环境标识或 none
function _probe_virt_fallback() {
  if is_macos; then
    # macOS：kern.hv_vmm_present 为 1 表示运行在 hypervisor 之上
    if [ "$(sysctl -n kern.hv_vmm_present 2>/dev/null)" = "1" ]; then
      echo "vm"
    else
      echo "none"
    fi
    return ${RETURN_SUCCESS:-0}
  fi

  # 容器痕迹：运行时标记文件 > 环境变量 > cgroup 归属
  if [ -f /.dockerenv ]; then
    echo "docker"
    return ${RETURN_SUCCESS:-0}
  fi
  if [ -f /run/.containerenv ]; then
    local engine
    engine=$(sed -n 's/^engine="\([^"]*\)".*/\1/p' /run/.containerenv 2>/dev/null)
    echo "${engine:-podman}"
    return ${RETURN_SUCCESS:-0}
  fi
  if [ -r /run/systemd/container ]; then
    echo "$(</run/systemd/container)"
    return ${RETURN_SUCCESS:-0}
  fi
  if [ -n "${container:-}" ]; then
    echo "${container}"
    return ${RETURN_SUCCESS:-0}
  fi
  if [ -n "${KUBERNETES_SERVICE_HOST:-}" ]; then
    echo "kubernetes"
    return ${RETURN_SUCCESS:-0}
  fi
  if [ -r /proc/1/cgroup ]; then
    local cgroup
    cgroup=$(</proc/1/cgroup)
    case "${cgroup}" in
      *kubepods* | *cri-containerd*)
        echo "kubernetes"
        return ${RETURN_SUCCESS:-0}
        ;;
      *libpod* | *podman*)
        echo "podman"
        return ${RETURN_SUCCESS:-0}
        ;;
      *docker*)
        echo "docker"
        return ${RETURN_SUCCESS:-0}
        ;;
      *lxc*)
        echo "lxc"
        return ${RETURN_SUCCESS:-0}
        ;;
      *containerd*)
        echo "containerd"
        return ${RETURN_SUCCESS:-0}
        ;;
    esac
  fi

  echo "none"
}

# 私有的原始探测：输出环境标识（归一化后的 none 表示未检出虚拟化）
function _probe_virt() {
  local virt=""
  if has_cmd systemd-detect-virt; then
    virt=$(systemd-detect-virt 2>/dev/null)
  else
    virt=$(_probe_virt_fallback)
  fi

  case "${virt}" in
    "" | none)
      echo "none"
      ;;
    *)
      echo "${virt}"
      ;;
  esac
}

# 私有的类型归类：systemd-detect-virt 词表中的容器类型
function _probe_is_container_type() {
  case "${1}" in
    docker | podman | containerd | cri-o | lxc | lxc-libvirt | systemd-nspawn | openvz | \
      rkt | wsl | proot | pouch | container-other | kubernetes)
      return ${RETURN_SUCCESS:-0}
      ;;
    *)
      return ${RETURN_FAILURE:-1}
      ;;
  esac
}

# 私有的类型归类：systemd-detect-virt 词表中的虚拟机类型
function _probe_is_vm_type() {
  case "${1}" in
    kvm | qemu | amazon | vmware | microsoft | oracle | xen | bochs | uml | parallels | \
      bhyve | qnx | acrn | powervm | zvm | google | vm)
      return ${RETURN_SUCCESS:-0}
      ;;
    *)
      return ${RETURN_FAILURE:-1}
      ;;
  esac
}

# 探测运行环境，输出 container:<type> | vm:<type> | baremetal | unknown:<type>
# 结果缓存在 __CWS_PROBE_ENV（同一 shell 内环境属性不会变化）
function probe_env() {
  if [ -z "${__CWS_PROBE_ENV:-}" ]; then
    local virt
    virt=$(_probe_virt)
    if _probe_is_container_type "${virt}"; then
      __CWS_PROBE_ENV="container:${virt}"
    elif _probe_is_vm_type "${virt}"; then
      __CWS_PROBE_ENV="vm:${virt}"
    elif [ "${virt}" = "none" ]; then
      __CWS_PROBE_ENV="baremetal"
    else
      # 未识别的虚拟化类型：如实报告，不冒充物理机
      __CWS_PROBE_ENV="unknown:${virt}"
    fi
  fi
  echo "${__CWS_PROBE_ENV}"
}

# 是否运行在容器中
function is_container() {
  case "$(probe_env)" in
    container:*) return ${RETURN_SUCCESS:-0} ;;
    *) return ${RETURN_FAILURE:-1} ;;
  esac
}

# 是否运行在虚拟机中
function is_vm() {
  case "$(probe_env)" in
    vm:*) return ${RETURN_SUCCESS:-0} ;;
    *) return ${RETURN_FAILURE:-1} ;;
  esac
}

# 是否运行在物理机上（既非容器也非虚拟机，且探测未失败）
function is_baremetal() {
  if [ "$(probe_env)" = "baremetal" ]; then
    return ${RETURN_SUCCESS:-0}
  else
    return ${RETURN_FAILURE:-1}
  fi
}

# 输出运行环境标识，用于提示符等展示场景（永不失败）
#   baremetal        -> none
#   container:docker -> docker
#   vm:kvm           -> kvm
function virt_type() {
  local env_type
  env_type=$(probe_env)
  case "${env_type}" in
    baremetal) echo "none" ;;
    *:*) echo "${env_type#*:}" ;;
    *) echo "${env_type}" ;;
  esac
}

# ─── 工具链能力探测 ─────────────────────────────────────────────────

# 是否具备 mamba（conda 的 C++ 前端）
function has_mamba() {
  has_cmd mamba
}

# 是否具备 conda
function has_conda() {
  has_cmd conda
}

# ─── Python 虚拟环境探测 ─────────────────────────────────────────────────
# 两个问题分开回答：
#   is_venv   —— 当前 shell 已激活虚拟环境（状态，看 VIRTUAL_ENV）
#   has_venv  —— 指定项目目录下有可用的 venv（能力，看 .venv/bin/python）
# conda 环境不是 venv，不进这两个谓词（用 has_conda / ${CONDA_PREFIX}）。

# 是否已激活 Python 虚拟环境（venv / virtualenv / uv）
# 判定：VIRTUAL_ENV 非空且目录仍在（悬空变量不算已激活）
function is_venv() {
  if [ -n "${VIRTUAL_ENV:-}" ] && [ -d "${VIRTUAL_ENV}" ]; then
    return ${RETURN_SUCCESS:-0}
  else
    return ${RETURN_FAILURE:-1}
  fi
}

# 输出 venv 的解释器路径（能跑就是可用），不可用时返回失败
# Usage: venv_python [venv_dir]   # venv_dir 缺省为 .venv（按当前目录解析）
function venv_python() {
  local dir=${1:-.venv}
  local python_bin
  for python_bin in "${dir}/bin/python" "${dir}/bin/python3" "${dir}/Scripts/python.exe"; do
    if [ -x "${python_bin}" ]; then
      echo "${python_bin}"
      return ${RETURN_SUCCESS:-0}
    fi
  done
  return ${RETURN_FAILURE:-1}
}

# 当前项目是否有可用的 venv：目录存在且解释器可执行（悬空符号链接不算）
# Usage: has_venv [venv_dir]
function has_venv() {
  venv_python "${1:-.venv}" >/dev/null 2>&1
}
