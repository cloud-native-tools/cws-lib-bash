export CURL_VERBOSE_OPTS="--progress-bar --show-error"

if [ "${BASH_OS}" = "darwin" ]; then
  export CURL_DOWNLOAD_OPTS="--compressed --insecure"
else
  export CURL_DOWNLOAD_OPTS="--location --compressed --insecure"
fi
export CURL_RETRY_OPTS="--retry 5 --retry-delay 1"
export CURL_FAILED_OPTS="--fail --continue-at -"
export CURL_FETCH_OPTS="--silent --insecure --connect-timeout 1"

function curl_download() {
  curl ${CURL_VERBOSE_OPTS} ${CURL_DOWNLOAD_OPTS} ${CURL_RETRY_OPTS} ${CURL_FAILED_OPTS} $@
}

function curl_download_to_file() {
  local file=${1}
  local url=${2}
  if [ -z "${file}" ] || [ -z "${url}" ]; then
    log warn "Usage: curl_download_to_file <file> <url>"
  else
    curl_download -o "${file}" ${url}
  fi
}

function curl_download_to_dir() {
  local dir=${1}
  local url=${2}
  if [ -z "${dir}" ] || [ -z "${url}" ]; then
    log warn "Usage: curl_download_to_dir <dir> <url>"
  else
    curl_download -O --output-dir "${dir}" ${url}
  fi
}

function curl_run_shell() {
  local url=${1}
  if [ -z "${url}" ]; then
    log warn "Usage: curl_run_shell <url>"
  else
    curl -o- ${url} | bash
  fi
}

function curl_fetch() {
  curl ${CURL_FETCH_OPTS} $@
}

function mirror_file() {
  local url=${1}
  local dir=${2:-/repo}
  local path=$(dirname $(echo ${url} | sed 's@https\?://[^/]*/@@g'))
  if [ -z "${url}" ]; then
    log warn "Usage: download_file [url] "
  else
    mkdir -p ${dir}/${path}
    pushd ${dir}/${path} >/dev/null 2>&1
    if curl_download -O ${url}; then
      log notice "download [${url}] into [${dir}/${path}] success"
    else
      log error "download [${url}] into [${dir}/${path}] failed"
    fi
    popd >/dev/null 2>&1
    echo "${url} -> ${dir}/${path}"
  fi
}
