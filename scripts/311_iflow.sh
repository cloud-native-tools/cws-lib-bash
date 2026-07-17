# shellcheck shell=bash

function iflow_dev() {
  iflow --permission-mode acceptEdits "$@"
}

function iflow_yolo() {
  iflow --dangerously-skip-permissions "$@" || iflow --permission-mode bypassPermissions "$@"
}
