function dssh() {
  docker exec -it "$1" bash
}
function dp() {
  docker-compose $@
}

function dp_up() {
  docker-compose --compatibility up -d --remove-orphans $@
}

function drun() {
  docker run --rm -it --privileged --network host --entrypoint /bin/sh $@
}

function docker_gc() {
  docker run --rm -v /var/run/docker.sock:/var/run/docker.sock spotify/docker-gc:latest
}

function docker_host() {
  docker run --rm -it --privileged --network host --pid=host -v /:/ busybox nsenter -t 1 -m -u -n -i sh
}

function docker_desktop_enter() {
  docker run --rm -it --privileged --network host --pid=host -v /:/media busybox chroot /media -- nsenter -t 1 -m -u -n -i sh
}

function docker_create_network() {
  IFADDR=${1}
  ip link add docker0 type bridge
  ip addr add "${IFADDR}" dev docker0
  ip link set docker0 up
  iptables -t nat -A POSTROUTING -s "${IFADDR}" ! -d "${IFADDR}" -j MASQUERADE
  echo 1 >/proc/sys/net/ipv4/ip_forward
}

function docker_list_remote_images() {
  local registry=$1
  local project=$2
  set -x
  curl -sSL -I \
    -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
    "http://${registry}/v2/${project}/manifests/$(
      curl -sSL "http://${registry}/v2/${project}/tags/list" | jq -r '.tags[0]'
    )" |
    awk '$1 == "Docker-Content-Digest:" { print $2 }' |
    tr -d $'\r'
  set +x
}

function docker_delete_remote_images() {
  local registry=$1
  local project=$2
  curl -v -sSL -X DELETE "http://${registry}/v2/${project}/manifests/$(
    curl -sSL -I \
      -H "Accept: application/vnd.docker.distribution.manifest.v2+json" \
      "http://${registry}/v2/${project}/manifests/$(
        curl -sSL "http://${registry}/v2/${project}/tags/list" | jq -r '.tags[0]'
      )" |
      awk '$1 == "Docker-Content-Digest:" { print $2 }' |
      tr -d $'\r'
  )"
}

function docker_generate_dockerfile() {
  local img=$1
  docker history --no-trunc ${img} |
    tac |
    tr -s ' ' |
    cut -d " " -f 5- |
    sed 's,^/bin/sh -c #(nop) ,,g' |
    sed 's,^/bin/sh -c,RUN,g' |
    sed 's, && ,\n  & ,g' |
    sed 's,\s*[0-9]*[\.]*[0-9]*\s*[kMG]*B\s*$,,g' |
    head -n -1
}

function docker_image_to_ctr() {
  local img=$1
  docker save ${img} | ctr image import -
}
