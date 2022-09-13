function perf_trace_net() {
  perf trace --no-syscalls --event 'net:*' $@ >/dev/null
}

function perf_syscall_record() {
  local iteration=${1:-10}
  local duration=${2:-5}
  for iter in $(seq ${iteration}); do
    echo "Iter: ${iter}"
    perf record -e 'raw_syscalls:*' -a -o node-trace-$(date '+%s').data -- sleep ${duration}
  done
}

function perf_syscall_report() {
  local input=${1}
  perf trace -S -i ${input}
}
