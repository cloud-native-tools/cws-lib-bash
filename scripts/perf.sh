function perf_trace_net() {
  perf trace --no-syscalls --event 'net:*' $@ >/dev/null
}

function perf_syscall_record() {
  local iteration=${1:-10}
  local duration=${2:-5}
  for iter in $(seq ${iteration}); do
    log info "Iter: ${iter}"
    perf record -e 'raw_syscalls:*' -a -o node-trace-$(date '+%s').data -- sleep ${duration}
  done
}

function perf_syscall_report() {
  local input=${1}
  perf trace -S -i ${input}
}

function perf_cgroup_path_of_pid() {
  local pid=${1}
  local cgroup_root=$(dirname $(mount | grep -E '^cgroup on ' | grep -w cpuset | awk '{print $3}'))
  local cgroup_perf_path=$(find ${cgroup_root} -name "*.procs" -exec grep -w "${pid}" {} /dev/null \; 2>/dev/null | grep '/perf_event/')
  printf "${cgroup_perf_path}\n" | sed 's@/sys/fs/cgroup/perf_event/\([^:]*\)/cgroup.procs:[0-9]\+@\1@g'
}

function perf_record_by_cgroup() {
  local cgroup_path=${1}
  shift
  local perf_options=${@}
  perf record -e cpu-clock -g ${perf_options} -G ${cgroup_path}
}

function perf_record_by_cgroup_of_pid() {
  local pid=${1}
  shift
  local cgroup_path=$(perf_cgroup_path_of_pid ${pid})
  perf_record_by_cgroup ${cgroup_path} $@
}

function perf_report() {
  local perf_data=${1}
  local pid=${2}
  if [ -z "${pid}" ]; then
      perf report -i ${perf_data}
  else
      perf report -i ${perf_data} --kallsyms=/proc/kallsyms --symfs=/proc/${pid}/root
  fi
}