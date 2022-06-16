#!/bin/sh

function is_bash() { test -n "${BASH_VERSION}"; }
function is_zsh() { test -n "${ZSH_VERSION}"; }
function get_script_root() {
  if test -t; then
    pwd || echo ${PWD}
  else
    is_bash && echo $(readlink -f $(dirname ${BASH_SOURCE[0]}))
    is_zsh && echo $(dirname ${(%):-%N})
  fi
}
ROOT=$(get_script_root)
PROFILED=${ROOT}/profile.d
SCRIPTS=${ROOT}/scripts

for i in ${PROFILED}/*.sh ${SCRIPTS}/*.sh; do
    if [ -r "$i" ]; then
        if [ "${-#*i}" != "$-" ]; then
            . "$i"
        else
            . "$i" >/dev/null
        fi
    fi
done
unset i