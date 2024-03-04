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
  perf record -a -g -e cpu-clock -G ${cgroup_path} $@
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

function perf_profiling_cgroup() {
  # /sys/fs/cgroup/cpu/kubepods/burstable/pod${uuid}/
  local cgroup=${1}
  local pid=${2}
  local duration=${3:-60}
  top -d 1 -n ${duration} -b 2>&1 > top.log &
  perf record -o perf-cgroup.data -a -g -e cpu-clock -G ${cgroup} -F 99999 -- sleep ${duration}
  perf script -i perf-cgroup.data --symfs=/proc/${pid}/root >perf-cgroup.txt
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
  local duration=${2:-60}
  top -d 1 -n ${duration} -b 2>&1 > top.log &
  perf record -o perf-${pid}.data -p ${pid} -F 99999 -g -- sleep ${duration}
  perf script -i perf-${pid}.data --symfs=/proc/${pid}/root >perf-${pid}.txt
}

function perf_profiling() {
  local duration=${1:-120}
  top -d 1 -n ${duration} -b 2>&1 > top.log &
  perf record -o perf.data -a -F 999 -g -- sleep ${time}
  perf script -i perf.data >perf.txt
}

# cat top.txt |awk 'BEGIN{boot_time="2024 01 29 23 02 24";boot_timestamp = mktime(boot_time)} $1 ~ /^top/{time=$3;gsub(":", " ", time); current_time = strftime("2024 03 01 "time);current_timestamp = mktime(current_time);next}  $9>50 {print (current_timestamp - boot_timestamp)" "$0}' > top-timed.txt

# awk 'BEGIN {enable="false"} NR==FNR{cpu_usage[$1]=$10;next} {split($4,arr,".");if (arr[1] in cpu_usage){enable="true"};if ($0 ~ /^$/){if(enable=="true"){print};enable="false"};if (enable=="true"){print}}' top-timed.txt /Users/liuqiming.lqm/Downloads/perf-cgroup.txt > perf-cgroup-timed.txt
