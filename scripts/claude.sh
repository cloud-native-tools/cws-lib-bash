# shellcheck shell=bash

function claude_dev() {
  claude --permission-mode acceptEdits "$@"
}

function claude_plan() {
  claude --permission-mode plan "$@"
}

function claude_auto() {
  claude --permission-mode auto "$@"
}

function claude_yolo() {
  claude --dangerously-skip-permissions "$@" || claude --permission-mode bypassPermissions "$@"
}

function claude_print() {
  claude --print "$@"
}

function claude_json() {
  claude --print --output-format json "$@"
}
