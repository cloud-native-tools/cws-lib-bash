function docker_exec() {
  docker exec -it "$1" ${2:-bash}
}

function docker_run() {
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

function docker_image_name() {
  if [ $# -eq 1 ]; then
    local image_name_or_id=$1
  else
    local image_name_or_id=$(cat -)
  fi
  local image_name=$(docker image inspect -f '{{index .RepoTags 0}}' ${image_name_or_id} 2>/dev/null)
  if [ -z "${image_name}" ]; then
    echo ${image_name_or_id}
  else
    echo ${image_name}
  fi
}

function docker_image_change_registry() {
  if [ $# -eq 2 ]; then
    local image_name_or_id=$1
    shift
  else
    local image_name_or_id=$(cat -)
  fi
  local new_registry=$1
  if [ -z "${new_registry}" ]; then
    docker_image_name ${image_name_or_id} | sed "s@^[^/]*/@@g"
  else
    docker_image_name ${image_name_or_id} | sed "s@^[^/]*/@$new_registry/@g"
  fi
}

function docker_image_change_repository() {
  if [ $# -eq 2 ]; then
    local image_name_or_id=$1
    shift
  else
    local image_name_or_id=$(cat -)
  fi
  local new_repository=$1
  docker_image_name ${image_name_or_id} | sed "s@^\([^/]*/\)?[^/]*/@\1$new_repository/@g"
}

function docker_image_change_tag() {
  if [ $# -eq 2 ]; then
    local image_name_or_id=$1
    shift
  else
    local image_name_or_id=$(cat -)
  fi
  local new_tag=$1
  docker_image_name ${image_name_or_id} | sed "s@^\([^:]*:\).*@\1${new_tag}@g"
}

function docker_image_rename() {
  local image_name_or_id=$1
  local new_registry=$2
  local new_repository=$3
  local new_tag=$4
  local run=$5
  local old_name=$(docker_image_name ${image_name_or_id})
  local new_name=$(echo ${image_name_or_id} |
    docker_image_change_registry ${new_registry} |
    docker_image_change_repository ${new_repository} |
    docker_image_change_tag ${new_tag})
  if [ -z "${run}" ]; then
    echo ${new_name}
  else
    echo "Tag: ${old_name}  -->  ${new_name}"
    docker tag ${old_name} ${new_name}
  fi
}

function dp() {
  docker-compose $@
}

function dp_up() {
  docker-compose up -d --compatibility --remove-orphans $@
}

function dp_recreate() {
  docker-compose up -d --force-recreate --no-deps $@
}

function dp_svc() {
  docker-compose ps --services
}
