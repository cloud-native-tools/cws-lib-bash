function nm_libc_version() {
    nm /lib64/libc.so* | grep 'A GLIBC' | awk '{print $NF}' | sort -h
}
