# shellcheck shell=bash

function qoder_cli_dev() {
  qoder --permission-mode acceptEdits "$@"
}

function qoder_cli_yolo() {
  qoder --dangerously-skip-permissions "$@" || qoder --permission-mode bypassPermissions "$@"
}
