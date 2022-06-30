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

function k8s_sys_ep() {
  kubectl -n ${SYSTEM_NAMESPACE} get ep $@
}

function k8s_apply() {
  kubectl apply -R -f $@
}

function k8s_nodes() {
  kubectl get nodes -o wide $@
}

function k8s_node_labels() {
  local tpl=$(
    cat <<'EOF'
{{range .items}}{{.metadata.name}}{{":"}}
  {{range $key,$value := .metadata.labels}}{{"\t"}}{{$key}}={{$value}}{{"\n"}}{{end}}
{{end}}
EOF
  )
  kubectl get nodes $@ -o go-template --template="${tpl}"
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

function k8s_node_annotations() {
  local tpl=$(
    cat <<'EOF'
{{range .items}}{{.metadata.name}}{{":"}}
  {{range $key,$value := .metadata.annotations}}{{"\t"}}{{$key}}={{$value}}{{"\n"}}{{end}}
{{end}}
EOF
  )
  kubectl get nodes -o go-template --template="${tpl}"
}

function k8s_node_status() {
  local tpl=$(
    cat <<'EOF'
{{range .items}}{{.metadata.name}}{{":"}}
  CPU: {{.status.capacity.cpu}}
  Memory: {{.status.capacity.memory}}
  Pods: {{.status.capacity.pods}}
{{end}}
EOF
  )
  kubectl get nodes -o go-template --template="${tpl}"
}

function k8s_login_pod() {
  local namepsace=$1
  local pod_name=$2
  kubectl -n ${namepsace} exec -it ${pod_name} -- sh
}

function k8s_login_container() {
  local namepsace=$1
  local pod_name=$2
  local container_name=$3
  if [ -z "${container_name}" ]; then
    kubectl -n ${namepsace} exec -it ${pod_name} -- sh
  else
    kubectl -n ${namepsace} exec -it ${pod_name} -c ${container_name} -- sh
  fi
}

function k8s_get_container_in_pod() {
  local namepsace=${1:-default}
  local pod_name=$2
  printf "%-24s %-24s %-80s %-20s\n" "Pod Name" "Container Name" Image Command
  local tpl=$(
    cat <<'EOF'
{{- $pod_name := .metadata.name -}}
{{- range .spec.containers -}}
  {{- printf "%-24s " $pod_name -}}
  {{- printf "%-24s " .name -}}
  {{- printf "%-80s " .image -}}
  {{- with $cmd := index .command 0 -}}
    {{- printf "%-20s\n" $cmd -}}
  {{- end -}}
{{- end -}}
{{- range .spec.initContainers -}}
  {{- printf "%-24s " $pod_name -}}
  {{- printf "(init) %-17s " .name -}}
  {{- printf "%-80s " .image -}}
  {{- with $cmd := index .command 0 -}}
    {{- printf "%-20s\n" $cmd -}}
  {{- end -}}
{{- end -}}
EOF
  )
  if [ -z "${pod_name}" ]; then
    local tpl_list=$(
      cat <<EOF
{{- range .items -}}
  ${tpl}
{{- end -}}
EOF
    )
    kubectl -n ${namepsace} get pods -o go-template --template="${tpl_list}"
  else
    kubectl -n ${namepsace} get pods ${pod_name} -o go-template --template="${tpl}"
  fi
}

function k8s_pods() {
  local namepsace=${1}
  printf "%-24s %-60s %-16s %-40s %-12s %-10s\n" Namespace Name IP Node Runtime Status
  local tpl=$(
    cat <<'EOF'
{{- range .items -}}
  {{- printf "%-24s " .metadata.namespace -}}
  {{- printf "%-60s " .metadata.name -}}
  {{- with .status.podIP -}}
    {{- printf "%-16s " . -}}
  {{- else -}}
    {{- printf "%-16s " "None" -}}
  {{- end -}}
  {{- with .spec.nodeName -}}
    {{- printf "%-40s " . -}}
  {{- else -}}
    {{- printf "%-40s " "None" -}}
  {{- end -}}
  {{- with .spec.runtimeClassName -}}
    {{- printf "%-20s" . -}}
  {{- else -}}
    {{- printf "%-20s" "runc" -}}
  {{- end -}}
  {{- printf "%-10s " .status.phase -}}
  {{"\n"}}
{{- end -}}
EOF
  )
  if [ -z "${namepsace}" ]; then
    kubectl get pods -A -o go-template --template="${tpl}"
  else
    kubectl get pods -n ${namepsace} -o go-template --template="${tpl}"
  fi
}

function k8s_pod_life() {
  local namepsace=${1:-default}
  local pod=${2}
  local single_tpl=$(
    cat <<'EOF'
  {{- printf "Pod: %-24s\n" .metadata.name -}}
  {{- printf "  %-24s: %-24s\n" "Created" .metadata.creationTimestamp -}}
  {{- printf "  %-24s: %-24s\n" "Started" .status.startTime -}}
  {{- range .status.conditions -}}
    {{- printf "  %-16s(%-6s): %-24s\n" .type .status .lastTransitionTime -}}
  {{- end -}}
  {{- range .status.containerStatuses -}}
    {{- printf "  Container: %-24s\n" .name -}}
    {{- range $key,$value := .state -}}
    {{- printf "    %-22s startedAt: %-16s\n" $key $value.startedAt -}}
    {{- printf "    %-21s finishedAt: %-16s\n" $key $value.startedAt -}}
    {{- end -}}
  {{- end -}}
EOF
  )
  local list_tpl=$(
    cat <<EOF
{{- range .items -}}
${single_tpl}
{{- end -}}
EOF
  )
  if [ -z "${pod}" ]; then
    kubectl get pods -n ${namepsace} -o go-template --template="${list_tpl}"
  else
    kubectl get pods ${pod} -n ${namepsace} -o go-template --template="${single_tpl}"
  fi
}

function k8s_pod_by_node() {
  local node_name=${1}
  shift
  kubectl get pod --field-selector spec.nodeName=${node_name} $@
}

function k8s_pod_by_runtime() {
  local runtime_class=${1}
  shift
  kubectl get pod --field-selector .spec.runtimeClassName=${runtime_class} $@
}

function k8s_images() {
  printf "%-24s %-60s %-80s \n" Namespace Name Image
  local list_tpl=$(
    cat <<'EOF'
{{- range .items -}}
  {{- $namespace_name := .metadata.namespace -}}
  {{- $pod_name := .metadata.name -}}
  {{- range .spec.containers -}}
    {{- printf "%-24s " $namespace_name -}}
    {{- printf "%-60s " $pod_name -}}
    {{- printf "%-80s " .image -}}
    {{"\n"}}
  {{- end -}}
  {{- range .spec.initContainers -}}
    {{- printf "%-24s " $namespace_name -}}
    {{- printf "%-60s " $pod_name -}}
    {{- printf "%-80s " .image -}}
    {{"\n"}}
  {{- end -}}
{{- end -}}
EOF
  )
  kubectl get pods -A -o go-template --template="${list_tpl}" $@
}

function k8s_images_used() {
  k8s_images $@ | awk '{print $3}' | sort | uniq
}
