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
