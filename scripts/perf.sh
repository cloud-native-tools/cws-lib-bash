function perf_trace_net(){
  perf trace --no-syscalls --event 'net:*' $@ > /dev/null
}
