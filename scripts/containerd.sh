for sock in /run/containerd/containerd.sock /run/containerd/containerd.io.sock; do
  if [ -S ${sock} ]; then
    export CRI_SOCKET=${sock}
    break
  fi
done
unset sock

export CTR="/usr/bin/ctr -a ${CRI_SOCKET}"
export CRI="/usr/bin/crictl -r unix://${CRI_SOCKET}"
export K8S_NS="-n=k8s.io"
export DOCKER_NS="-n=moby"

function ctr_load_k8s_image_from_file() {
  local img_file=$1
  ${CTR} ${K8S_NS} images import --digests --all-platforms "${img_file}"
}

function ctr_load_k8s_image_from_docker() {
  local img=$1
  local new_name=${2:-${img}}
  if [[ "${img}" != "${new_name}" ]]; then
    docker tag ${img} ${new_name}
  fi
  docker save ${new_name} | ${CTR} ${K8S_NS} images import --digests --all-platforms -
}

function cri_pods() {
  ${CRI} pods $@
}

function cri_pod_info() {
  local pod_name=${1}
  cri_pods --name ${pod_name} -o yaml
}

function cri_images() {
  ${CRI} images $@
}

function cri_prune() {
  $CRI rmi --prune
}

function ctr_export() {
  local img=${1}
  if [ -z "${img}" ]; then
    echo "Usage: ctr_export <image> [tar]"
    return ${RETURN_FAILURE}
  fi
  local tar=${2:-$(basename ${img%:*}).tar}
  ${CTR} ${K8S_NS} images export ${tar} ${img}
}

function crictl_pod_name_to_sid() {
  local pod_name=${1}
  if [ -n "${pod_name}" ]; then
    crictl pods -q --last 0 -s Ready --name ${pod_name}
  else
    echo "Usage: crictl_pod_name_to_sid <pod_name>"
  fi
}

function crictl_pod_id_to_sid() {
  local pod_id=${1}
  if [ -n "${pod_id}" ]; then
    crictl pods -q --last 0 -s Ready --id ${pod_id}
  else
    echo "Usage: crictl_pod_id_to_sid <pod_id>"
  fi
}

function crictl_sandbox_id() {
  local name_or_id=${1}
  local sid=$(crictl_pod_name_to_sid ${name_or_id})
  if [ -z "${sid}" ]; then
    local sid=$(crictl_pod_id_to_sid ${name_or_id})
  fi
  echo ${sid}
}

function crictl_sandbox_rootfs() {
  local pod_name=${1}
  local sid=$(crictl_sandbox_id ${pod_name})
  if [ -n "${sid}" ]; then
    echo "${RUND_SERVICE_ROOT}/${sid}/fs/passthru"
  fi
}

function crictl_container_ids() {
  local pod_name=${1}
  local sid=$(crictl_sandbox_id ${pod_name})
  if [ -n "${sid}" ]; then
    crictl ps -q --pod ${sid}
  else
    echo "Usage: rund_container_ids <pod_name>"
  fi
}

function crictl_container_name_to_cid() {
  local pod_id=${1}
  local container_name=${2}
  if [ -n "${pod_id}" ] && [ -n "${container_name}" ]; then
    crictl ps -q --pod ${pod_id} --name ${container_name}
  else
    echo "Usage: crictl_container_name_to_cid <pod_id> <container_name>"
  fi
}

function crictl_container_id_to_cid() {
  local pod_id=${1}
  local container_id=${2}
  if [ -n "${pod_id}" ] && [ -n "${container_id}" ]; then
    crictl ps -q --pod ${pod_id} --id ${container_id}
  else
    echo "Usage: crictl_container_id_to_cid <pod_id> <container_id>"
  fi
}

function crictl_container_id() {
  local pod_name_or_id=${1}
  local container_name_or_id=${2}
  if [ -n "${pod_name_or_id}" ] && [ -n "${container_name_or_id}" ]; then
    local sid=$(crictl_sandbox_id ${pod_name_or_id})
    if [ -n "${sid}" ]; then
      local cid=$(crictl_container_name_to_cid ${sid} ${container_name_or_id})
      if [ -z "${cid}" ]; then
        local cid=$(crictl_container_id_to_cid ${sid} ${container_name_or_id})
      fi
      echo ${cid}
    fi
  fi
}

function crictl_container_exec() {
  local pod_name=${1}
  local container_name=${2}
  if [ -z "${pod_name}" ] || [ -z "${container_name}" ]; then
    echo "Usage: rund_container_exec <pod_name> <container_name> <command> [args...]"
    return ${RETURN_FAILURE}
  fi
  local sid=$(crictl_sandbox_id ${pod_name})
  local cid=$(crictl_container_id ${pod_name} ${container_name})
  if [ -z "${sid}" ] || [ -z "${cid}" ]; then
    echo "No such container: ${pod_name}/${container_name}"
  fi
  shift
  shift
  crictl exec ${cid} $@
}

function crictl_pod_cgroup() {
  local pod_name=${1}
  local sid=$(crictl_sandbox_id ${pod_name})
  crictl inspectp ${sid} | jq -r '.info.runtimeSpec.linux.cgroupsPath'
}
