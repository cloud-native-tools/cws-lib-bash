# shellcheck shell=bash

function qwen_dev() {
  qwen --permission-mode acceptEdits "$@"
}

function qwen_yolo() {
  qwen --dangerously-skip-permissions "$@" || qwen --permission-mode bypassPermissions "$@"
}

function qwen_print() {
  qwen --print "$@"
}

function qwen_json() {
  qwen --print --output-format json "$@"
}
