# shellcheck shell=bash

function opencode_dev() {
  opencode --auto-approve "$@"
}

function opencode_yolo() {
  opencode --yolo "$@" || opencode --auto-approve "$@"
}
