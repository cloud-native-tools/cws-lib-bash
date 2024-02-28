function perf_trace_net() {
  perf trace --no-syscalls --event 'net:*' $@ >/dev/null
}

function perf_record_syscall() {
  local output=${3:-perf-record-$(date '+%s').data}
  local duration=${2:-60}
  perf record -a -e 'raw_syscalls:*' -o ${output} -- sleep ${duration}
}

function perf_trace_syscall() {
  local output=${1:-perf-trace-$(date '+%s').log}
  local duration=${2:-120}
  perf trace -a -e 'syscalls:sys_enter_*' -o ${output} -- sleep ${duration}
}

function perf_trace_report() {
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
  if [ -z "${cgroup_path}" ]; then
    echo "Usage: perf_record_by_cgroup <cgroup_path>"
    return 1
  fi
  shift
  perf record -e cpu-clock -g -G ${cgroup_path} $@
}

function perf_record_pod() {
  local pod_uuid=${1}
  local pod_sid=${2}
  if [ -z "${pod_uuid}" ] || [ -z "${pod_sid}" ]; then
    echo "Usage: perf_record_pod <pod_uuid> <pod_sid>"
    return 1
  fi
  shift 2
  perf_record_by_cgroup "kubepods/burstable/pod${pod_uuid}/${pod_sid}" -- ${@}
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

function perf_profiling_pid() {
  local pid=${1}
  local duration=${2:-600}
  perf record -o perf-${pid}.data -p ${pid} -F 999 -g -- sleep ${duration}
  perf script -i perf-${pid}.data --symfs=/proc/${pid}/root >perf-${pid}.txt
}

function perf_profiling() {
  local duration=${1:-120}
  perf record -o perf.data -a -F 999 -g -- sleep ${time}
  perf script -i perf.data >perf.txt
}
