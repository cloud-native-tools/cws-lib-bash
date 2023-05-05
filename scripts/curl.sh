export CURL_VERBOSE_OPTS="--progress-bar --show-error"
export CURL_DOWNLOAD_OPTS="--location --compressed --insecure"
export CURL_RETRY_OPTS="--retry 5 --retry-delay 1"
export CURL_FAILED_OPTS="--fail --continue-at -"

function curl_download() {
    curl ${CURL_VERBOSE_OPTS} ${CURL_DOWNLOAD_OPTS} ${CURL_RETRY_OPTS} ${CURL_FAILED_OPTS} $@
}

function curl_download_to_file() {
    local file=${1}
    curl_download -o "${file}"
}

function curl_download_to_dir() {
    local dir=${1:-${PWD}}
    curl_download -O --output-dir "${dir}"
}
