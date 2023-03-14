#!/bin/sh

ROOT=
if [ -n "${BASH_VERSION}" ]; then
    ROOT=$(readlink -f $(dirname "${BASH_SOURCE[0]}"))
fi
if [ -n "${ZSH_VERSION}" ]; then
    ROOT=$(readlink -f $(dirname "${(%):-%N}"))
fi
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