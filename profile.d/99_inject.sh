#!/usr/bin/env bash

is_bash && shopt -s nullglob

if [[ -n "${INJECT_DIR}" && -d ${INJECT_DIR} ]]; then
  for script in ${INJECT_DIR}/*.sh; do
    log info "Run inject script ${script} in ${INJECT_DIR}"
    source "${script}"
  done
  unset script
fi
