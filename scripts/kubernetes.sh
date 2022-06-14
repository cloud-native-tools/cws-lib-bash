function k8s_admin_pass() {
  local namespace=$1
  local secrets_name=$(kubectl -n ${namespace} get sa/admin-user -o jsonpath="{.secrets[0].name}")
  kubectl -n ${namespace} get secret "${secrets_name}" -o go-template="{{.data.token | base64decode}}"
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

function k8s_desc() {
  local namespace=$1
  shift
  local object=$@
  kubectl describe -n ${namespace} ${object}
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

export SYSTEM_NAMESPACE=kube-system
function k8s_sys_pod() {
  kubectl -n ${SYSTEM_NAMESPACE} get pod $@
}

function k8s_sys_svc() {
  kubectl -n ${SYSTEM_NAMESPACE} get service $@
}

function k8s_sys_deploy() {
  kubectl -n ${SYSTEM_NAMESPACE} get deployment $@
}

function k8s_sys_desc() {
  kubectl -n ${SYSTEM_NAMESPACE} describe $@
}

function k8s_sys_logs() {
  kubectl -n ${SYSTEM_NAMESPACE} logs $@
}

function k8s_apply() {
  kubectl apply -R -f $@
}

function k8s_nodes() {
  kubectl get nodes -o wide
}

function k8s_node_labels() {
  local script=$(
    cat <<'EOF'
{
  gsub(",","\n\t",$NF);
  gsub("^","\t",$NF);
  print $1":\n"$NF
}
EOF
  )
  kubectl get node --show-labels | grep -v LABELS | awk ${script}
}

function k8s_node_taints() {
  local tpl=$(
    cat <<'EOF'
{{range .items}}{{.metadata.name}}{{":"}}
  {{range .spec.taints}}{{"\t"}}{{range $key,$value := .}}{{" "}}{{$key}}={{$value}}{{","}}{{end}}{{"\n"}}{{end}}
{{end}}
EOF
  )
  kubectl get nodes -o go-template --template="${tpl}"
}
