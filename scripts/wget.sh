export WGET_VERBOSE_OPTS="--progress=dot:giga"
export WGET_DOWNLOAD_OPTS="--no-check-certificate --continue"

function wget_download() {
    wget ${WGET_VERBOSE_OPTS} ${WGET_DOWNLOAD_OPTS} $@
}
