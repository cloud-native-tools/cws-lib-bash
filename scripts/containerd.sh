export cri_socket=/run/containerd/containerd.sock
export ctr_cmd="/usr/bin/ctr -a ${cri_socket}"
export cri_cmd="/usr/bin/crictl -r unix://${cri_socket}"
export k8s_ns="-n=k8s.io"
export docker_ns="-n=moby"

function ctr_load_k8s_image() {
    local img_file=$1
    ${ctr_cmd} ${k8s_ns} images import "${img_file}"
}

function ctr_load_k8s_images() {
    while IFS='=' read -r origin mirror; do
        echo "loading [${mirror}] as [${origin}"]
        #    docker pull "${mirror}"
        #    docker tag "${mirror}" "${origin}"
        #    docker rmi "${mirror}"
        #    docker save "${origin}" | ${ctr_cmd} -n=k8s.io images import -
        ${ctr_cmd} ${k8s_ns} images pull "${mirror}"
        ${ctr_cmd} ${k8s_ns} images tag "${mirror}" "${origin}"
    done <<EOF
k8s.gcr.io/kube-apiserver:v1.24.1=registry.cn-hangzhou.aliyuncs.com/google_containers/kube-apiserver:v1.24.1
k8s.gcr.io/kube-controller-manager:v1.24.1=registry.cn-hangzhou.aliyuncs.com/google_containers/kube-controller-manager:v1.24.1
k8s.gcr.io/kube-scheduler:v1.24.1=registry.cn-hangzhou.aliyuncs.com/google_containers/kube-scheduler:v1.24.1
k8s.gcr.io/kube-proxy:v1.24.1=registry.cn-hangzhou.aliyuncs.com/google_containers/kube-proxy:v1.24.1
k8s.gcr.io/pause:3.6=registry.cn-hangzhou.aliyuncs.com/google_containers/pause:3.6
k8s.gcr.io/pause:3.5=registry.cn-hangzhou.aliyuncs.com/google_containers/pause:3.5
k8s.gcr.io/etcd:3.5.3-0=registry.cn-hangzhou.aliyuncs.com/google_containers/etcd:3.5.3-0
k8s.gcr.io/coredns/coredns:v1.8.6=registry.cn-hangzhou.aliyuncs.com/google_containers/coredns:1.8.6
EOF
}