for sock in /run/containerd/containerd.sock /run/containerd/containerd.io.sock; do
    if [ -S ${sock} ]; then
        export CRI_SOCKET=${sock}
    fi
done
unset sock

export CTR="/usr/bin/ctr -a ${CRI_SOCKET}"
export CRI="/usr/bin/crictl -r unix://${CRI_SOCKET}"
export K8S_NS="-n=k8s.io"
export DOCKER_NS="-n=moby"

function ctr_load_k8s_image_from_file() {
    local img_file=$1
    ${CTR} ${K8S_NS} images import "${img_file}"
}

function ctr_load_k8s_image_from_docker() {
    local img=$1
    local new_name=${2:-${img}}
    if [[ "${img}" != "${new_name}" ]]; then
        docker tag ${img} ${new_name}
    fi
    docker save ${new_name} | ${CTR} ${K8S_NS} image import -
}
