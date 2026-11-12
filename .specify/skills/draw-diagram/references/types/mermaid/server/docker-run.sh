#!/usr/bin/env bash
# docker-run.sh — 内网部署 mermaid 渲染服务器的简单运行脚本（仿 plantuml-server 的 docker-run.sh）
#
# Emitted by `.specify/scripts/python/sync-mirrors.py`; the authority for this block is
# `contracts/mirror-projection.contract.md` C-34 / C-36. It depends on nothing
# that exists only in the source tree: it re-derives its own version line (C-36).
_script_interface_guard() {
    _sig_name="${0##*/}"
    _sig_stop=0
    for _sig_arg in "$@"; do
        if [ "$_sig_stop" -eq 1 ]; then continue; fi
        case "$_sig_arg" in
            --) _sig_stop=1 ;;
            -h|--help) return 0 ;;
            --version)
                _sig_dir="$(dirname -- "$0")"
                case "$_sig_dir" in /*) ;; *) _sig_dir="./$_sig_dir" ;; esac
                _sig_ver="unknown"
                _sig_level=0
                while [ -d "$_sig_dir" ] && [ "$_sig_level" -le 12 ]; do
                    if [ -f "$_sig_dir/pyproject.toml" ] && [ -e "$_sig_dir/.git" ]; then
                        _sig_ver="$(sed -n 's/^version[[:space:]]*=[[:space:]]*"\([^"]*\)".*/\1/p' "$_sig_dir/pyproject.toml" 2>/dev/null | head -n 1)"
                        [ -n "$_sig_ver" ] || _sig_ver="unknown"
                        break
                    fi
                    if [ "$_sig_dir" = "/" ]; then break; fi
                    _sig_dir="$(dirname -- "$_sig_dir")"
                    _sig_level=$((_sig_level + 1))
                done
                printf '%s %s\n' "$_sig_name" "$_sig_ver"
                exit 0 ;;
        esac
    done
    return 0
}
_script_interface_guard "$@"

# script-interface:86:begin (feature 086 -- generated; the rule is owned by
# `.specify/shared/definitions/script-interface-definitions.md`, its bash half by
# `.specify/scripts/bash/script-interface.sh` and `.specify/scripts/python/sync-mirrors.py`. No rule of its own.)
_sig_usage() {
    printf 'usage: %s\n' 'docker-run.sh [arguments]'
    printf 'options:\n'
    printf '  -h, --help   print this help and exit\n'
    printf '  --version    print the script name and the framework version, then exit\n'
    printf ''side-effects:' %s\n' 'writes only through the options it documents; a flag-only invocation writes nothing'
    printf ''exit-codes:' %s\n' '0 the request was answered; 2 argument error; 3 a check found something to report'
}

_sig_answers() {
    _sig_want=""
    _sig_stop=0
    for _sig_tok in "$@"; do
        if [ "$_sig_stop" -eq 1 ]; then continue; fi
        case "$_sig_tok" in
            --) _sig_stop=1 ;;
            -h|--help) [ -n "$_sig_want" ] || _sig_want=help ;;
            --version) [ -n "$_sig_want" ] || _sig_want=version ;;
            -*)
                case "  " in
                    *" $_sig_tok "*) ;;
                    *)
                        if [ -z "1" ]; then
                            printf 'error: unrecognized option: %s\n' "$_sig_tok" >&2
                            _sig_usage >&2
                            exit 2
                        fi
                        ;;
                esac
                ;;
        esac
    done
    case "$_sig_want" in
        help) _sig_usage; exit 0 ;;
    esac
    return 0
}

_sig_answers "$@"
set -u
# script-interface:86:end

set -euo pipefail

IMAGE="${MERMAID_IMAGE:-reg.docker.alibaba-inc.com/cws-images/images-mermaid-server:1.0.0}"
HOST_PORT="${MERMAID_HOST_PORT:-9696}"
NAME="${MERMAID_CONTAINER_NAME:-mermaid-server}"

if ! command docker >/dev/null 2>&1; then
  echo "docker command not found" >&2
  exit 1
fi

if docker inspect "${NAME}" >/dev/null 2>&1; then
  docker rm -f "${NAME}" >/dev/null 2>&1 || true
  echo "removed existing container [${NAME}]"
fi

docker run -d --name "${NAME}" --restart unless-stopped \
  -p "${HOST_PORT}:9696" \
  "${IMAGE}" "$@"

echo "============================================================"
echo "  mermaid render server: ${NAME}"
echo "  Image:                ${IMAGE}"
echo "  URL:                  http://<host>:${HOST_PORT}/"
echo "  Protocol:             GET /svg/pako:{state} | GET /img/pako:{state}?type=png"
echo "  mermaid 接入:     export MERMAID_SERVER=http://<host>:${HOST_PORT}"
echo "============================================================"
