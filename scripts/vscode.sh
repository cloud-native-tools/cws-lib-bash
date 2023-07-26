function codeopen() {
    if command -v code >/dev/null 2>&1; then
        code -r $@
    elif command -v code-server >/dev/null 2>&1; then
        code-server -r $@
    fi
}
