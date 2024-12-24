function kind_create_cluster() {
  local name=${1}
  local image=${2}
  local worker_count=${3:-2}
  if [ -z "${name}" ] || [ -z "${image}" ]; then
    log error "Usage: kind_create_cluster_in_container <name> <image>"
    return ${RETURN_FAILURE}
  fi
  local tmpdir=$(mktemp -d)
  local kind_config=${tmpdir}/kind-config.yaml
  log notice "use kind config: ${kind_config}"
  cat >${kind_config} <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
kubeadmConfigPatches:
- |
  apiVersion: kubelet.config.k8s.io/v1beta1
  kind: KubeletConfiguration
  evictionHard:
    nodefs.available: "0%"
nodes:
- role: control-plane
EOF
for i in $(seq ${worker_count}); do
  echo "- role: worker" >> ${kind_config}
done

  kind create -v 5 cluster \
    --name ${name} \
    --image ${image} \
    --config ${kind_config} \
    --retain
}

function kind_create_cluster_in_container() {
  local network_name=$(docker inspect --format='{{json .NetworkSettings.Networks}}' $(hostname) | jq -r 'keys_unsorted | .[0]')
  if [ -n "${network_name}" ]; then
    export KIND_EXPERIMENTAL_DOCKER_NETWORK=${network_name}
  fi
  kind_create_cluster $@
}
