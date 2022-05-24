function k8s_pass() {
  local secrets_name=$(kubectl -n kubernetes-dashboard get sa/admin-user -o jsonpath="{.secrets[0].name}")
  kubectl -n kubernetes-dashboard get secret "${secrets_name}" -o go-template="{{.data.token | base64decode}}"
}

function k8s_join_cmd() {
  echo "$(kubeadm token create --print-join-command) --v=5 --cri-socket unix:///run/containerd/containerd.io.sock"
}

function k8s_reset() {
  kubeadm reset --v=5 --cri-socket unix:///run/containerd/containerd.io.sock
}

function k8s_init() {
  kubeadm init --v=5 --cri-socket unix:///run/containerd/containerd.io.sock --pod-network-cidr=10.244.0.0/16
}

CTR_CMD="/usr/bin/ctr -a /var/run/containerd/containerd.io.sock"

function k8s_load_image() {
  local img_file=$1
  ${CTR_CMD} -n=k8s.io images import "${img_file}"
}

function k8s_load_images() {
  while IFS='=' read -r origin mirror; do
    echo "loading [${mirror}] as [${origin}"]
    #    docker pull "${mirror}"
    #    docker tag "${mirror}" "${origin}"
    #    docker rmi "${mirror}"
    #    docker save "${origin}" | ${CTR_CMD} -n=k8s.io images import -
    ${CTR_CMD} -n=k8s.io images pull "${mirror}"
    ${CTR_CMD} -n=k8s.io images tag "${mirror}" "${origin}"
  done <<EOF
k8s.gcr.io/kube-apiserver:v1.23.6=registry.cn-hangzhou.aliyuncs.com/google_containers/kube-apiserver:v1.23.6
k8s.gcr.io/kube-controller-manager:v1.23.6=registry.cn-hangzhou.aliyuncs.com/google_containers/kube-controller-manager:v1.23.6
k8s.gcr.io/kube-scheduler:v1.23.6=registry.cn-hangzhou.aliyuncs.com/google_containers/kube-scheduler:v1.23.6
k8s.gcr.io/kube-proxy:v1.23.6=registry.cn-hangzhou.aliyuncs.com/google_containers/kube-proxy:v1.23.6
k8s.gcr.io/pause:3.6=registry.cn-hangzhou.aliyuncs.com/google_containers/pause:3.6
k8s.gcr.io/pause:3.5=registry.cn-hangzhou.aliyuncs.com/google_containers/pause:3.5
k8s.gcr.io/etcd:3.5.1-0=registry.cn-hangzhou.aliyuncs.com/google_containers/etcd:3.5.1-0
k8s.gcr.io/coredns/coredns:v1.8.6=registry.cn-hangzhou.aliyuncs.com/google_containers/coredns:1.8.6
EOF
}

function k8s_get_all() {
  local namespace="${1}"
  local k8s_fields="all,cm,secret,ing,sa,pvc"
  if [ -z "${namespace}" ]; then
    kubectl get ${k8s_fields} -A -o wide
  else
    kubectl get ${k8s_fields} -n ${namespace} -o wide
  fi
}

function k8s_prune_ns() {
  local namespace="$1"
  local k8s_fields="all,cm,secret,ing"
  kubectl -n "${namespace}" delete $(kubectl get ${k8s_fields} -n "${namespace}" -o name)
  kubectl delete namespace "${namespace}"
}

function k8s_service_account() {
  local namespace="$1"
  local service_name="$2"
  local secret_name=$(kubectl -n $namespace get sa/$service_name -o jsonpath="{.secrets[0].name}")
  kubectl -n ${namespace} get secret "${secret_name}" -o go-template="{{.data.token | base64decode}}"
}

function k8s_info() {
  echo "-------  kubectl version   --------"
  kubectl version –short
  echo "-------  cluster info      --------"
  kubectl cluster-info
  echo "-------  component status  -------"
  kubectl get componentstatus

}

function k8s_ns() {
  kubectl get namespace
}

function k8s_ep() {
  local namespace="$1"
  kubectl get ep -n $namespace
}

function k8s_desc_ns() {
  local namespace=$1
  kubectl describe namespace ${namespace}
}

function k8s_desc_pod() {
  local namespace=$1
  shift
  local object=$@
  kubectl describe -n ${namespace} pods ${object}
}

function k8s_failed_pod() {
  local namespace="${1}"
  if [ -z "${namespace}" ]; then
    kubectl get pod -A -o wide | grep -v Running | grep -v Completed
  else
    kubectl get pod -n ${namespace} -o wide | grep -v Running | grep -v Completed
  fi
}

function k8s_sys_pod() {
  kubectl get pod -n kube-system $@
}

function k8s_sys_svc() {
  kubectl get service -n kube-system $@
}

function k8s_sys_deploy() {
  kubectl get deployment -n kube-system $@
}
