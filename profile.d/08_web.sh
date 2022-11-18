function download_file() {
    local url=${1}
    local dir=${2:-~/repo}
    local path=$(dirname $(echo ${url} | sed 's@https\?://[^/]*/@@g'))
    if [ -z "${url}" ]; then
        echo "Usage: download_file [url] "
    else
        mkdir -p ${dir}/${path}
        pushd ${dir}/${path} >/dev/null 2>&1
        curl --progress-bar --show-error --location --compressed --insecure --retry 5 --retry-delay 1 -O ${url}
        popd >/dev/null 2>&1
        echo "${url} -> ${dir}/${path}"
    fi
}

