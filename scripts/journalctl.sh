function journalctl_clean() {
    journalctl --rotate
    journalctl --vacuum-time=1s
}
