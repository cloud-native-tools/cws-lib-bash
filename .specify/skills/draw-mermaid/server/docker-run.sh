#!/usr/bin/env bash
# docker-run.sh — 内网部署 mermaid 渲染服务器的简单运行脚本（仿 plantuml-server 的 docker-run.sh）
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
echo "  draw-mermaid 接入:     export MERMAID_SERVER=http://<host>:${HOST_PORT}"
echo "============================================================"
