function dump_stack() {
  local TRACE=""
  local CP=$$

  while true; do
    CMDLINE=$(cat /proc/$CP/cmdline | tr '\000' ' ')
    PP=$(grep PPid /proc/$CP/status | awk '{ print $2; }')
    TRACE="${TRACE}${INDENT}[$CP]:${CMDLINE}\n"
    if [ "$CP" == "1" ]; then
      break
    fi
    CP=$PP
    INDENT="  ${INDENT}"
  done
  log plain "Backtrace of '$0'" >>${trace_log}
  log plain "$TRACE" >>${trace_log}
}

function mock_it() {
  target="$@"
  if [ ! -e "${target}" ]; then
    log error "${target} not exist"
    exit ${EXIT_FAIL}
  fi

  self_name=$(basename ${target})
  mock_log=/var/log/${self_name}-mock.log
  log plain "======================= $(date)       =======" >>${trace_log}
  dump_stack
  exec -a ${self_name} ${self_name}.ori ${ori_params}
}
