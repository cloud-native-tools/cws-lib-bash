## ============================================================
## 第一层：内部辅助函数
## ============================================================

# 从cgroup路径中提取容器ID
# Usage: _ps_extract_container_id <cgroup_content>
_ps_extract_container_id() {
  local cgroup_path="$1"
  local container_id=""

  # Docker: /docker/<id> 或 /system.slice/docker-<id>.scope
  if echo "$cgroup_path" | grep -qE '/docker[/-]'; then
    container_id=$(echo "$cgroup_path" | grep -oE '[0-9a-f]{64}' | head -1)
  # containerd/k8s: /kubepods/.../<id> 或 cri-containerd-<id>.scope
  elif echo "$cgroup_path" | grep -qE '(kubepods|containerd)'; then
    container_id=$(echo "$cgroup_path" | grep -oE '[0-9a-f]{64}' | tail -1)
  # podman: /libpod-<id>
  elif echo "$cgroup_path" | grep -qE '/libpod-'; then
    container_id=$(echo "$cgroup_path" | grep -oE '[0-9a-f]{64}' | head -1)
  fi

  echo "$container_id"
}

# 根据容器ID获取容器名称
# Usage: _ps_resolve_container_name <container_id>
# 依赖: _ps_container_name_cache (调用前需 declare -A)
_ps_resolve_container_name() {
  local container_id="$1"
  local short_id="${container_id:0:12}"

  # 检查缓存
  if [[ -n "${_ps_container_name_cache[$container_id]:-}" ]]; then
    echo "${_ps_container_name_cache[$container_id]}"
    return
  fi

  local name=""

  # 尝试 docker
  if command -v docker &>/dev/null; then
    name=$(docker inspect --format '{{.Name}}' "$container_id" 2>/dev/null | sed 's|^/||')
  fi

  # 尝试 crictl (containerd/k8s)
  if [[ -z "$name" ]] && command -v crictl &>/dev/null; then
    name=$(crictl inspect --output go-template --template '{{.status.metadata.name}}' "$container_id" 2>/dev/null)
    if [[ -n "$name" ]]; then
      local pod_id
      pod_id=$(crictl inspect --output go-template --template '{{.info.sandboxID}}' "$container_id" 2>/dev/null)
      if [[ -n "$pod_id" ]]; then
        local pod_name
        pod_name=$(crictl inspectp --output go-template --template '{{.status.metadata.name}}' "$pod_id" 2>/dev/null)
        [[ -n "$pod_name" ]] && name="${name}@${pod_name}"
      fi
    fi
  fi

  # 尝试 nerdctl
  if [[ -z "$name" ]] && command -v nerdctl &>/dev/null; then
    name=$(nerdctl inspect --format '{{.Name}}' "$container_id" 2>/dev/null | sed 's|^/||')
  fi

  # 回退：使用短ID
  if [[ -z "$name" ]]; then
    name="$short_id"
  fi

  _ps_container_name_cache[$container_id]="$name"
  echo "$name"
}

# 判断容器运行时类型
# Usage: _ps_detect_runtime <cgroup_content>
_ps_detect_runtime() {
  local cgroup_path="$1"
  if echo "$cgroup_path" | grep -qE '/docker[/-]'; then
    echo "docker"
  elif echo "$cgroup_path" | grep -qE 'cri-containerd|/kubepods'; then
    echo "containerd"
  elif echo "$cgroup_path" | grep -qE '/libpod-'; then
    echo "podman"
  else
    echo "-"
  fi
}

# 从参数列表中解析scope值
# Usage: _ps_parse_scope "$@"
# 输出scope值到stdout，默认为 all
_ps_parse_scope() {
  local scope="all"
  for arg in "$@"; do
    case "$arg" in
      host|container|all) scope="$arg" ;;
    esac
  done
  echo "$scope"
}

## ============================================================
## 第一层：PID 枚举函数（核心）
## ============================================================

# 从 cgroup 层级直接收集所有容器内 PID（每行一个）
# 策略：扫描 cgroup 文件系统中容器相关路径的 cgroup.procs
# 支持 cgroupv1 和 cgroupv2
_ps_pids_container() {
  local -A _seen_pids=()

  # 收集 cgroup.procs 文件路径
  local -a procs_files=()

  # cgroupv2 统一层级 (通常挂载在 /sys/fs/cgroup)
  if [[ -f /sys/fs/cgroup/cgroup.controllers ]]; then
    # Docker (cgroupv2): system.slice/docker-<id>.scope
    while IFS= read -r -d '' f; do
      procs_files+=("$f")
    done < <(find /sys/fs/cgroup/system.slice -maxdepth 2 -name "cgroup.procs" \
      -path "*docker-*" 2>/dev/null -print0)
    # containerd/k8s (cgroupv2): kubepods.slice/**
    while IFS= read -r -d '' f; do
      procs_files+=("$f")
    done < <(find /sys/fs/cgroup/kubepods.slice -name "cgroup.procs" 2>/dev/null -print0)
    # podman (cgroupv2): libpod-*
    while IFS= read -r -d '' f; do
      procs_files+=("$f")
    done < <(find /sys/fs/cgroup -maxdepth 3 -name "cgroup.procs" \
      -path "*libpod-*" 2>/dev/null -print0)
  fi

  # cgroupv1: 扫描 memory/cpu 等子系统下的容器路径
  local cg1_base=""
  for subsys in memory cpu,cpuacct cpuacct pids; do
    if [[ -d "/sys/fs/cgroup/${subsys}" ]]; then
      cg1_base="/sys/fs/cgroup/${subsys}"
      break
    fi
  done

  if [[ -n "$cg1_base" ]]; then
    # Docker (cgroupv1): /sys/fs/cgroup/<subsys>/docker/<id>/cgroup.procs
    while IFS= read -r -d '' f; do
      procs_files+=("$f")
    done < <(find "${cg1_base}/docker" -maxdepth 2 -name "cgroup.procs" 2>/dev/null -print0)
    # containerd/k8s (cgroupv1): kubepods 层级
    while IFS= read -r -d '' f; do
      procs_files+=("$f")
    done < <(find "${cg1_base}/kubepods" -name "cgroup.procs" 2>/dev/null -print0)
    # Docker via systemd driver (cgroupv1): system.slice/docker-*.scope
    while IFS= read -r -d '' f; do
      procs_files+=("$f")
    done < <(find "${cg1_base}/system.slice" -maxdepth 2 -name "cgroup.procs" \
      -path "*docker-*" 2>/dev/null -print0)
    # podman (cgroupv1)
    while IFS= read -r -d '' f; do
      procs_files+=("$f")
    done < <(find "${cg1_base}" -maxdepth 4 -name "cgroup.procs" \
      -path "*libpod-*" 2>/dev/null -print0)
  fi

  # 读取所有 cgroup.procs 文件中的 PID（去重）
  local pid
  for f in "${procs_files[@]}"; do
    while read -r pid; do
      if [[ -n "$pid" && -z "${_seen_pids[$pid]:-}" ]]; then
        _seen_pids[$pid]=1
        echo "$pid"
      fi
    done < "$f" 2>/dev/null
  done

  # 兜底：如果 cgroup 文件系统扫描无结果，回退到逐进程检测
  if [[ ${#_seen_pids[@]} -eq 0 ]]; then
    local p cg
    for p in /proc/[0-9]*/cgroup; do
      [[ -r "$p" ]] || continue
      cg=$(cat "$p" 2>/dev/null) || continue
      if echo "$cg" | grep -qE '/docker[/-]|kubepods|containerd|/libpod-'; then
        pid="${p#/proc/}"
        pid="${pid%%/*}"
        echo "$pid"
      fi
    done
  fi
}

# 获取宿主机 PID = 全部 PID - 容器 PID
_ps_pids_host() {
  # 先收集容器 PID 集合
  local -A _container_pids=()
  local p
  while read -r p; do
    [[ -n "$p" ]] && _container_pids[$p]=1
  done < <(_ps_pids_container)

  # 输出不在容器集合中的 PID
  while read -r p; do
    [[ -z "${_container_pids[$p]:-}" ]] && echo "$p"
  done < <(ps -eo pid= --no-headers 2>/dev/null | awk '{print $1}')
}

# scope 调度器
# Usage: _ps_pids_by_scope <scope>
# scope=all: 输出所有 PID
# scope=host: 调用 _ps_pids_host
# scope=container: 调用 _ps_pids_container
_ps_pids_by_scope() {
  local scope="${1:-all}"
  case "$scope" in
    all)       ps -eo pid= --no-headers 2>/dev/null | awk '{print $1}' ;;
    host)      _ps_pids_host ;;
    container) _ps_pids_container ;;
    *)
      echo "ERROR: invalid scope '$scope', use: all|host|container" >&2
      return 1
      ;;
  esac
}

## ============================================================
## 第二层：基础展示函数（三个独立实现）
## ============================================================

# ps_container [--json]
# 仅显示容器内进程，从 cgroup 层级直接枚举（无需遍历全部进程）
# 输出列：PID, PPID, RUNTIME, CONTAINER, %MEM, %CPU, COMMAND
function ps_container() {
  local json_output=0
  for arg in "$@"; do
    [[ "$arg" == "--json" ]] && json_output=1
  done

  declare -A _ps_container_name_cache

  # 收集容器 PID
  local -a container_pids=()
  local p
  while read -r p; do
    [[ -n "$p" ]] && container_pids+=("$p")
  done < <(_ps_pids_container)

  if [[ ${#container_pids[@]} -eq 0 ]]; then
    [[ $json_output -eq 1 ]] && echo "[]" || echo "No container processes found."
    unset _ps_container_name_cache
    return 0
  fi

  # 批量获取进程详情
  local pid_list
  pid_list=$(IFS=,; echo "${container_pids[*]}")

  if [[ $json_output -eq 1 ]]; then
    echo "["
    local first=1
  else
    printf "%-8s %-8s %-12s %-20s %-6s %-6s %s\n" "PID" "PPID" "RUNTIME" "CONTAINER" "%MEM" "%CPU" "COMMAND"
    printf "%-8s %-8s %-12s %-20s %-6s %-6s %s\n" "---" "----" "-------" "---------" "----" "----" "-------"
  fi

  local pid ppid mem cpu cmd cgroup_content container_id container_name runtime
  while IFS= read -r line; do
    pid=$(echo "$line" | awk '{print $1}')
    ppid=$(echo "$line" | awk '{print $2}')
    mem=$(echo "$line" | awk '{print $3}')
    cpu=$(echo "$line" | awk '{print $4}')
    cmd=$(echo "$line" | awk '{$1=$2=$3=$4=""; print substr($0,5)}')

    [[ ! -r "/proc/$pid/cgroup" ]] && continue
    cgroup_content=$(cat "/proc/$pid/cgroup" 2>/dev/null) || continue
    container_id=$(_ps_extract_container_id "$cgroup_content")
    [[ -z "$container_id" ]] && continue

    runtime=$(_ps_detect_runtime "$cgroup_content")
    container_name=$(_ps_resolve_container_name "$container_id")

    if [[ $json_output -eq 1 ]]; then
      [[ $first -eq 0 ]] && echo ","
      printf '  {"pid":%s,"ppid":%s,"runtime":"%s","container":"%s","mem":"%s","cpu":"%s","command":"%s"}' \
        "$pid" "$ppid" "$runtime" "$container_name" "$mem" "$cpu" "$(echo "$cmd" | sed 's/"/\\"/g')"
      first=0
    else
      printf "%-8s %-8s %-12s %-20s %-6s %-6s %s\n" "$pid" "$ppid" "$runtime" "$container_name" "$mem" "$cpu" "$cmd"
    fi
  done < <(ps -p "$(IFS=,; echo "${container_pids[*]}")" -o pid=,ppid=,%mem=,%cpu=,args= --no-headers 2>/dev/null)

  if [[ $json_output -eq 1 ]]; then
    echo ""
    echo "]"
  fi

  unset _ps_container_name_cache
}

# ps_host [--json]
# 仅显示宿主机进程（全部PID减去容器PID）
# 输出列：PID, PPID, USER, %MEM, %CPU, COMMAND
function ps_host() {
  local json_output=0
  for arg in "$@"; do
    [[ "$arg" == "--json" ]] && json_output=1
  done

  # 收集容器 PID 到集合中
  local -A _container_pids=()
  local p
  while read -r p; do
    [[ -n "$p" ]] && _container_pids[$p]=1
  done < <(_ps_pids_container)

  if [[ $json_output -eq 1 ]]; then
    echo "["
    local first=1
  else
    printf "%-8s %-8s %-10s %-6s %-6s %s\n" "PID" "PPID" "USER" "%MEM" "%CPU" "COMMAND"
    printf "%-8s %-8s %-10s %-6s %-6s %s\n" "---" "----" "----" "----" "----" "-------"
  fi

  local pid ppid user mem cpu cmd
  while IFS= read -r line; do
    pid=$(echo "$line" | awk '{print $1}')
    # 排除容器进程
    [[ -n "${_container_pids[$pid]:-}" ]] && continue

    ppid=$(echo "$line" | awk '{print $2}')
    user=$(echo "$line" | awk '{print $3}')
    mem=$(echo "$line" | awk '{print $4}')
    cpu=$(echo "$line" | awk '{print $5}')
    cmd=$(echo "$line" | awk '{$1=$2=$3=$4=$5=""; print substr($0,6)}')

    if [[ $json_output -eq 1 ]]; then
      [[ $first -eq 0 ]] && echo ","
      printf '  {"pid":%s,"ppid":%s,"user":"%s","mem":"%s","cpu":"%s","command":"%s"}' \
        "$pid" "$ppid" "$user" "$mem" "$cpu" "$(echo "$cmd" | sed 's/"/\\"/g')"
      first=0
    else
      printf "%-8s %-8s %-10s %-6s %-6s %s\n" "$pid" "$ppid" "$user" "$mem" "$cpu" "$cmd"
    fi
  done < <(ps -eo pid=,ppid=,user=,%mem=,%cpu=,args= --no-headers 2>/dev/null)

  if [[ $json_output -eq 1 ]]; then
    echo ""
    echo "]"
  fi
}

# ps_all [--json]
# 显示所有进程，附带容器归属信息
# 输出列：PID, PPID, RUNTIME, CONTAINER, %MEM, %CPU, COMMAND
function ps_all() {
  local json_output=0
  for arg in "$@"; do
    [[ "$arg" == "--json" ]] && json_output=1
  done

  declare -A _ps_container_name_cache

  if [[ $json_output -eq 1 ]]; then
    echo "["
    local first=1
  else
    printf "%-8s %-8s %-12s %-20s %-6s %-6s %s\n" "PID" "PPID" "RUNTIME" "CONTAINER" "%MEM" "%CPU" "COMMAND"
    printf "%-8s %-8s %-12s %-20s %-6s %-6s %s\n" "---" "----" "-------" "---------" "----" "----" "-------"
  fi

  local pid ppid mem cpu cmd cgroup_content container_id container_name runtime
  while IFS= read -r line; do
    pid=$(echo "$line" | awk '{print $1}')
    ppid=$(echo "$line" | awk '{print $2}')
    mem=$(echo "$line" | awk '{print $3}')
    cpu=$(echo "$line" | awk '{print $4}')
    cmd=$(echo "$line" | awk '{$1=$2=$3=$4=""; print substr($0,5)}')

    if [[ -r "/proc/$pid/cgroup" ]]; then
      cgroup_content=$(cat "/proc/$pid/cgroup" 2>/dev/null) || cgroup_content=""
    else
      cgroup_content=""
    fi

    container_id=$(_ps_extract_container_id "$cgroup_content")

    if [[ -n "$container_id" ]]; then
      runtime=$(_ps_detect_runtime "$cgroup_content")
      container_name=$(_ps_resolve_container_name "$container_id")
    else
      runtime="host"
      container_name="-"
    fi

    if [[ $json_output -eq 1 ]]; then
      [[ $first -eq 0 ]] && echo ","
      printf '  {"pid":%s,"ppid":%s,"runtime":"%s","container":"%s","mem":"%s","cpu":"%s","command":"%s"}' \
        "$pid" "$ppid" "$runtime" "$container_name" "$mem" "$cpu" "$(echo "$cmd" | sed 's/"/\\"/g')"
      first=0
    else
      printf "%-8s %-8s %-12s %-20s %-6s %-6s %s\n" "$pid" "$ppid" "$runtime" "$container_name" "$mem" "$cpu" "$cmd"
    fi
  done < <(ps -eo pid=,ppid=,%mem=,%cpu=,args= --no-headers 2>/dev/null)

  if [[ $json_output -eq 1 ]]; then
    echo ""
    echo "]"
  fi

  unset _ps_container_name_cache
}

## ============================================================
## 第三层：上层进程查看函数（基于 PID 列表过滤）
## ============================================================

# pstree 参考:
#   -a, --arguments     show command line arguments
#   -A, --ascii         use ASCII line drawing characters
#   -c, --compact       don't compact identical subtrees
#   -h, --highlight-all highlight current process and its ancestors
#   -H PID, --highlight-pid=PID
#   -l, --long          don't truncate long lines
#   -n, --numeric-sort  sort output by PID
#   -N type, --ns-sort=type
#   -p, --show-pids     show PIDs; implies -c
#   -s, --show-parents  show parents of the selected process
#   -S, --ns-changes    show namespace transitions
#   -U, --unicode       use UTF-8 (Unicode) line drawing characters

# 显示用户进程
# Usage: ps_user [host|container|all]
function ps_user() {
  local scope=$(_ps_parse_scope "$@")

  # 构建 PID 集合
  local -A _scope_pids=()
  local p
  while read -r p; do
    [[ -n "$p" ]] && _scope_pids[$p]=1
  done < <(_ps_pids_by_scope "$scope")

  ps -ef | grep -v '\[' | sort -k 8 | while IFS= read -r line; do
    local pid
    pid=$(echo "$line" | awk '{print $2}')
    if [[ ! "$pid" =~ ^[0-9]+$ ]]; then
      echo "$line"
      continue
    fi
    [[ -n "${_scope_pids[$pid]:-}" ]] && echo "$line"
  done
}

# 显示进程树
# Usage: ps_tree [pid] [host|container|all]
function ps_tree() {
  local pid=""
  local scope="all"
  for arg in "$@"; do
    case "$arg" in
      host|container|all) scope="$arg" ;;
      *) pid="$arg" ;;
    esac
  done
  pid=${pid:-$$}

  # 检查 PID 是否在目标 scope 中
  if [[ "$scope" != "all" ]]; then
    local -A _scope_pids=()
    local p
    while read -r p; do
      [[ -n "$p" ]] && _scope_pids[$p]=1
    done < <(_ps_pids_by_scope "$scope")
    if [[ -z "${_scope_pids[$pid]:-}" ]]; then
      echo "PID $pid does not match scope '$scope'" >&2
      return 1
    fi
  fi

  pstree -asl -H ${pid} ${pid}
}

# 显示进程树(按namespace)
# Usage: ps_tree_ns [pid] [host|container|all]
function ps_tree_ns() {
  local pid=""
  local scope="all"
  for arg in "$@"; do
    case "$arg" in
      host|container|all) scope="$arg" ;;
      *) pid="$arg" ;;
    esac
  done
  pid=${pid:-$$}

  if [[ "$scope" != "all" ]]; then
    local -A _scope_pids=()
    local p
    while read -r p; do
      [[ -n "$p" ]] && _scope_pids[$p]=1
    done < <(_ps_pids_by_scope "$scope")
    if [[ -z "${_scope_pids[$pid]:-}" ]]; then
      echo "PID $pid does not match scope '$scope'" >&2
      return 1
    fi
  fi

  pstree -asnl -N net -H ${pid} ${pid}
}

# 显示inotify使用情况
# Usage: ps_inotify [host|container|all]
function ps_inotify() {
  local scope=$(_ps_parse_scope "$@")

  local -A _scope_pids=()
  local p
  while read -r p; do
    [[ -n "$p" ]] && _scope_pids[$p]=1
  done < <(_ps_pids_by_scope "$scope")

  find /proc/*/fd \
    -lname anon_inode:inotify \
    -printf '%hinfo/%f\n' 2>/dev/null |
    xargs grep -c '^inotify' 2>/dev/null |
    sort -n -t: -k2 -r |
    while IFS=: read -r path count; do
      local pid
      pid=$(echo "$path" | grep -oE '/proc/[0-9]+/' | grep -oE '[0-9]+')
      [[ -z "$pid" ]] && continue
      [[ -n "${_scope_pids[$pid]:-}" ]] && echo "${path}:${count}"
    done
}

# 显示进程namespace信息
# Usage: ps_ns [host|container|all] [extra ps args...]
function ps_ns() {
  local scope="all"
  local -a extra_args=()
  for arg in "$@"; do
    case "$arg" in
      host|container|all) scope="$arg" ;;
      *) extra_args+=("$arg") ;;
    esac
  done

  local -A _scope_pids=()
  local p
  while read -r p; do
    [[ -n "$p" ]] && _scope_pids[$p]=1
  done < <(_ps_pids_by_scope "$scope")

  printf "%-8s %-12s %-12s %-12s %-12s %-12s %-12s %s\n" \
    "PID" "PIDNS" "NETNS" "MNTNS" "IPCNS" "UTSNS" "USERNS" "ARGS"

  ps -eo pid=,pidns=,netns=,mntns=,ipcns=,utsns=,userns=,args= --no-headers "${extra_args[@]}" 2>/dev/null |
    while IFS= read -r line; do
      local pid
      pid=$(echo "$line" | awk '{print $1}')
      [[ -n "${_scope_pids[$pid]:-}" ]] && echo "$line"
    done
}

# 显示内存占用最高的进程
# Usage: ps_top_mem [topN] [host|container|all]
function ps_top_mem() {
  local topN=10
  local scope="all"
  for arg in "$@"; do
    case "$arg" in
      host|container|all) scope="$arg" ;;
      *[0-9]*) topN="$arg" ;;
    esac
  done

  local -A _scope_pids=()
  local p
  while read -r p; do
    [[ -n "$p" ]] && _scope_pids[$p]=1
  done < <(_ps_pids_by_scope "$scope")

  printf "%-8s %-8s %-40s %-6s %-6s\n" "PID" "PPID" "CMD" "%MEM" "%CPU"

  local count=0
  ps -eo pid=,ppid=,cmd=,%mem=,%cpu= --sort=-%mem --no-headers 2>/dev/null |
    while IFS= read -r line; do
      [[ $count -ge $topN ]] && break
      local pid
      pid=$(echo "$line" | awk '{print $1}')
      if [[ -n "${_scope_pids[$pid]:-}" ]]; then
        echo "$line"
        ((count++))
      fi
    done
}

## ============================================================
## 带scope后缀的快捷函数
## ============================================================

function ps_user_all()       { ps_user all; }
function ps_user_host()      { ps_user host; }
function ps_user_container() { ps_user container; }

function ps_tree_all()       { ps_tree "$@" all; }
function ps_tree_host()      { ps_tree "$@" host; }
function ps_tree_container() { ps_tree "$@" container; }

function ps_tree_ns_all()       { ps_tree_ns "$@" all; }
function ps_tree_ns_host()      { ps_tree_ns "$@" host; }
function ps_tree_ns_container() { ps_tree_ns "$@" container; }

function ps_inotify_all()       { ps_inotify all; }
function ps_inotify_host()      { ps_inotify host; }
function ps_inotify_container() { ps_inotify container; }

function ps_ns_all()       { ps_ns all "$@"; }
function ps_ns_host()      { ps_ns host "$@"; }
function ps_ns_container() { ps_ns container "$@"; }

function ps_top_mem_all()       { ps_top_mem "$@" all; }
function ps_top_mem_host()      { ps_top_mem "$@" host; }
function ps_top_mem_container() { ps_top_mem "$@" container; }
