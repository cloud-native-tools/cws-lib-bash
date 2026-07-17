# shellcheck shell=bash

function codex_dev() {
  codex --approval-mode suggest "$@"
}

function codex_yolo() {
  codex --approval-mode full-auto "$@"
}

function codex_print() {
  codex --quiet "$@"
}
