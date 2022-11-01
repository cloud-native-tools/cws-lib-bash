function k8s_sa_token() {
  local namespace=${1:-kube-system}
  local sa=${2:-kube-system}
  local secrets_name=$(kubectl -n ${namespace} get sa/${sa} -o jsonpath="{.secrets[0].name}")
  kubectl -n ${namespace} get secret "${secrets_name}" -o go-template="{{.data.token | base64decode}}"
}

function k8s_get_all() {
  local namespace="${1}"
  local k8s_fields="all,cm,secret,ing,sa,pvc,pv"
  if [ -z "${namespace}" ]; then
    kubectl get ${k8s_fields} -A -o wide
  else
    kubectl get ${k8s_fields} -n ${namespace} -o wide
  fi
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

function k8s_ns_all() {
  local namespace="$1"
  local k8s_fields="all,cm,secret,ing,sa,pvc"
  kubectl get ${k8s_fields} -n "${namespace}" -o name
}

function k8s_ns_prune() {
  local namespace="$1"
  kubectl -n "${namespace}" delete $(k8s_ns_all ${namespace} | grep -v 'secret/default-token')
  kubectl delete namespace "${namespace}"
}

function k8s_desc_pod() {
  local namespace=$1
  shift
  local pods=$@
  kubectl describe -n ${namespace} pods ${pods}
}

function k8s_desc_node() {
  local namespace=$1
  shift
  local node=$@
  kubectl describe -n ${namespace} node ${node}
}

function k8s_failed_pod() {
  local namespace="${1}"
  if [ -z "${namespace}" ]; then
    kubectl get pod -A -o wide | grep -v Running | grep -v Completed
  else
    kubectl get pod -n ${namespace} -o wide | grep -v Running | grep -v Completed
  fi
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
  local cmd=${3:-sh}
  if [ -z "${namepsace}" -o -z "${pod_name}" ]; then
    echo "Usage: k8s_login_pod <namespace> <pod name> [cmd]"
  else
    kubectl -n ${namepsace} exec -it ${pod_name} -- ${cmd}
  fi
}

function k8s_login_container() {
  local namepsace=$1
  local pod_name=$2
  local container_name=$3
  local cmd=${4:-sh}
  if [ -z "${namepsace}" -o -z "${pod_name}" ]; then
    echo "Usage: k8s_login_container <namespace> <pod name> [container name] [cmd]"
  else
    if [ -z "${container_name}" ]; then
      k8s_login_pod ${namepsace} ${pod_name} ${cmd}
    else
      kubectl -n ${namepsace} exec -it ${pod_name} -c ${container_name} -- ${cmd}
    fi
  fi
}

function k8s_exec_pod() {
  local namepsace=$1
  shift
  local pod_name=$1
  shift
  if [ -z "${namepsace}" -o -z "${pod_name}" ]; then
    echo "Usage: k8s_exec_pod <namespace> <pod name> <cmd>"
  else
    kubectl -n ${namepsace} exec -it ${pod_name} -- $@
  fi
}

function k8s_login_container() {
  local namepsace=$1
  shift
  local pod_name=$1
  shift
  local container_name=$1
  shift
  if [ -z "${namepsace}" -o -z "${pod_name}" -o -z "${container_name}" ]; then
    echo "Usage: k8s_login_container <namespace> <pod name> <container name> <cmd>"
  else
    kubectl -n ${namepsace} exec -it ${pod_name} -c ${container_name} -- $@
  fi
}

function k8s_containers() {
  local namepsace=${1:-default}
  local pod_name=$2
  printf "%-40s %-30s %-80s\n" "Pod Name" "Container Name" Image
  local tpl=$(
    cat <<'EOF'
{{- $pod_name := .metadata.name -}}
{{- range .spec.containers -}}
  {{- printf "%-40s " $pod_name -}}
  {{- printf "%-30s " .name -}}
  {{- printf "%-80s " .image -}}
  {{"\n"}}
{{- end -}}
{{- range .spec.initContainers -}}
  {{- printf "%-40s " $pod_name -}}
  {{- printf "(init) %-23s " .name -}}
  {{- printf "%-80s " .image -}}
  {{"\n"}}
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
  if [ -n "${namepsace}" ]; then
    shift
  fi
  printf "%-24s %-60s %-10s %-16s %-40s %-20s\n" Namespace Name Status IP Node Runtime
  local tpl=$(
    cat <<'EOF'
{{- range .items -}}
  {{- printf "%-24s " .metadata.namespace -}}
  {{- printf "%-60s " .metadata.name -}}
  {{- printf "%-10s " .status.phase -}}
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
  {{"\n"}}
{{- end -}}
EOF
  )
  if [ -z "${namepsace}" ]; then
    kubectl get pods -A -o go-template --template="${tpl}" $@
  else
    kubectl get pods -n ${namepsace} -o go-template --template="${tpl}" $@
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

function k8s_svc() {
  local namepsace=${1}
  if [ -z "${namepsace}" ]; then
    kubectl get service -A
  else
    shift
    kubectl get service -n ${namepsace} $@
  fi
}

function k8s_svc_ports() {
  local namepsace=${1}
  printf "%-24s %-40s %-16s %-12s %-24s\n" Namespace Service Type Target "IP:Port"
  local tpl=$(
    cat <<'EOF'
{{- range .items -}}
  {{- $namespace_name := .metadata.namespace -}}
  {{- $service_name := .metadata.name -}}
  {{- $cluster_ips := .spec.clusterIPs -}}
  {{- $external_ips := .spec.externalIPs -}}
  {{- $ports := .spec.ports -}}
  {{- $selector := .spec.selector -}}
  {{- range $cluster_ips -}}
    {{- $cluster_ip := . -}}
    {{- range $ports -}}
      {{- printf "%-24s " $namespace_name -}}
      {{- printf "%-40s " $service_name -}}
      {{- printf "%-16s " "ClusterIP" -}}
      {{- printf "%-12v " .targetPort -}}
      {{- $combine := (printf "%v:%v" $cluster_ip .port) -}}
      {{- printf "%-24s " $combine -}}
      {{"\n"}}
    {{- end -}}
  {{- end -}}
  {{- range $external_ips -}}
    {{- $external_ip := . -}}
    {{- range $ports -}}
      {{- printf "%-24s " $namespace_name -}}
      {{- printf "%-40s " $service_name -}}
      {{- printf "%-16s " "ExternalIP" -}}
      {{- printf "%-12v " .targetPort -}}
      {{- $combine := (printf "%v:%v" $external_ip .nodePort) -}}
      {{- printf "%-24s " $combine -}}
      {{"\n"}}
    {{- end -}}
  {{- end -}}
{{- end -}}
EOF
  )
  if [ -z "${namepsace}" ]; then
    kubectl get service -A -o go-template --template="${tpl}"
  else
    kubectl get service -n ${namepsace} -o go-template --template="${tpl}"
  fi
}

function k8s_ep() {
  local namepsace=${1}
  printf "%-24s %-40s %-24s %-48s %-24s\n" Namespace Name Node Pod Target
  local tpl=$(
    cat <<'EOF'
{{- range .items -}}
  {{- $namespace_name := .metadata.namespace -}}
  {{- $endpoint_name := .metadata.name -}}
  {{- range .subsets -}}
    {{- $addresses := .addresses -}}
    {{- $ports := .ports -}}
    {{- range $address := $addresses -}}
        {{- range $port := $ports -}}
          {{- printf "%-24s " $namespace_name -}}
          {{- printf "%-40s " $endpoint_name -}}
          {{- printf "%-24s " $address.nodeName -}}
          {{- printf "%-48s " $address.targetRef.name -}}
          {{- $combine := (printf "%s://%v:%v" $port.name $address.ip $port.port) -}}
          {{- printf "%-24s " $combine -}}
          {{"\n"}}
        {{- end -}}
    {{- end -}}
  {{- end -}}
{{- end -}}
EOF
  )
  if [ -z "${namepsace}" ]; then
    kubectl get ep -A -o go-template --template="${tpl}"
  else
    kubectl get ep -n ${namepsace} -o go-template --template="${tpl}"
  fi
}

function k8s_pods_images() {
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
  k8s_pods_images $@ | grep -vw Image | awk '{print $3}' | sort | uniq
}

function k8s_apply() {
  if [ $# -gt 1 ]; then
    local namespace=$1
    local file_dir=${2:-.}
    echo "kubectl apply --namespace=${namespace} -R -f ${file_dir}"
    kubectl apply --namespace=${namespace} -R -f ${file_dir}
  else
    local file_dir=${1:-.}
    echo "kubectl apply -R -f ${file_dir}"
    kubectl apply -R -f ${file_dir}
  fi
}

function k8s_delete() {
  local file_dir=${1:-.}
  kubectl delete -R -f ${file_dir}
}

function k8s_logs() {
  local namepsace=${1}
  local pod=${2}
  local container=${3}
  if [ -z "${container}" ]; then
    kubectl -n ${namepsace} logs --all-containers=true ${pod}
  else
    kubectl -n ${namepsace} logs ${pod} ${container}
  fi
}

export SYSTEM_NAMESPACE=kube-system
function k8s_sys_pod() {
  k8s_pods ${SYSTEM_NAMESPACE} $@
}

function k8s_sys_svc() {
  k8s_svc ${SYSTEM_NAMESPACE} $@
}

function k8s_sys_deployment() {
  kubectl -n ${SYSTEM_NAMESPACE} get deployment $@
}

function k8s_sys_desc() {
  kubectl -n ${SYSTEM_NAMESPACE} describe $@
}

function k8s_sys_logs() {
  k8s_logs ${SYSTEM_NAMESPACE}
}

function k8s_sys_ep() {
  kubectl -n ${SYSTEM_NAMESPACE} get ep $@
}

function k8s_dump_kubeadm_config() {
  kubectl -n ${SYSTEM_NAMESPACE} get configmap kubeadm-config -o jsonpath='{.data.ClusterConfiguration}'
}

function k8s_update_kubeadm_certs() {
  local adm_conf=$1
  # apiServer:
  #   certSANs:
  #   - ${INTERNAL_IP}
  #   - ${EXTERNAL_IP}
  mv -fv /etc/kubernetes/pki/apiserver.crt /etc/kubernetes/pki/apiserver.crt.bak
  mv -fv /etc/kubernetes/pki/apiserver.key /etc/kubernetes/pki/apiserver.key.bak
  kubeadm init phase certs apiserver --v=5 --config ${adm_conf}
}

function k8s_kubeconfig() {
  kubectl config view --raw
}

function k8s_event() {
  local namepsace=${1}
  if [ -n "${namepsace}" ]; then
    shift
  fi
  printf "%-24s %-10s %-24s %-24s %-10s %-24s %-60s\n" Namespace Kind Time Object Type Reason Message
  local tpl=$(
    cat <<'EOF'
{{- range .items -}}
  {{- printf "%-24s " .metadata.namespace -}}
  {{- printf "%-10s " .involvedObject.kind -}}
  {{- printf "%-24s " .metadata.creationTimestamp -}}
  {{- printf "%-24s " .involvedObject.name -}}
  {{- printf "%-10s " .type -}}
  {{- printf "%-24s " .reason -}}
  {{- printf "%-60s " .message -}}
  {{"\n"}}
{{- end -}}
EOF
  )
  if [ -z "${namepsace}" ]; then
    kubectl get event -A -o go-template --template="${tpl}" $@
  else
    kubectl get event -n ${namepsace} -o go-template --template="${tpl}" $@
  fi
}

function k8s_label_nodes() {
  local node_name=${1}
  local label_value=${2}
  kubectl label nodes --overwrite ${node_name} ${label_value}
}

function k8s_taint_nodes() {
  local node_name=${1}
  local taint_value=${2}
  kubectl taint nodes --overwrite ${node_name} ${taint_value}
}

function k8s_apis() {
  kubectl api-resources --namespaced=true
  kubectl api-resources --namespaced=false
}

function k8s_configmap() {
  local namepsace=${1}
  if [ -n "${namepsace}" ]; then
    shift
  fi
  local tpl=$(
    cat <<'EOF'
{{- range .items -}}
  {{- printf "Namespace: %-24s\n" .metadata.namespace -}}
  {{- printf "Name: %-60s\n" .metadata.name -}}
  {{- range $key, $value := .data -}}
    {{- printf "data: %s\n%-80s\n" $key $value -}}
  {{- end -}}
  {{"---\n"}}
{{- end -}}
EOF
  )
  if [ -z "${namepsace}" ]; then
    kubectl get configmap -A -o go-template --template="${tpl}" $@
  else
    kubectl get configmap -n ${namepsace} -o go-template --template="${tpl}" $@
  fi
}

function k8s_ns_export() {
  local namespace="$1"
  shift
  for n in $(k8s_ns_all ${namespace}); do
    kubectl get -o=yaml $n
  done
}

function k8s_pod_export() {
  local namespace="$1"
  shift
  kubectl -n ${namespace} get pod -o=yaml $@
}
