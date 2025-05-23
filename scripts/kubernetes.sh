function k8s_get_all() {
  local namespace="${1}"
  local k8s_fields="all,cm,secret,ing,sa,pvc"
  if [ -z "${namespace}" ]; then
    kubectl get ${k8s_fields} -A -o wide
  else
    kubectl get ${k8s_fields} -n ${namespace} -o wide
  fi
}

function k8s_info() {
  kubectl cluster-info
}

function k8s_ns() {
  kubectl get namespace
}

function k8s_ns_names() {
  local namespace="$1"
  local k8s_fields="all,cm,secret,ing,sa,pvc"
  if [ -z "${namespace}" ]; then
    kubectl get ${k8s_fields} -A -o name
  else
    shift
    kubectl get ${k8s_fields} -n "${namespace}" -o name $@
  fi
}

function k8s_ns_all() {
  local namespace="$1"
  kubectl api-resources --verbs=list --namespaced -o name | xargs -n 1 kubectl get -n "${namespace}" --ignore-not-found --show-kind
}

function k8s_ns_prune() {
  local namespace="$1"
  kubectl -n "${namespace}" delete $(k8s_ns_names ${namespace} | grep -v 'secret/default-token')
  kubectl delete namespace "${namespace}"
}

function k8s_desc_pod() {
  local namespace=$1
  shift
  local pods=$@
  kubectl describe -n ${namespace} pods ${pods}
}

function k8s_dump_pod() {
  local namespace=$1
  local pod=$2
  if [ -z "${namespace}" ]; then
    log warn "Usage: k8s_dump_pod <namespace> [pod name]"
    return ${RETURN_FAILURE}
  fi
  if [ -z "${pod}" ]; then
    k8s_pods ${namespace} | awk '{print "mkdir -pv "$6";kubectl get pod -n "$1" -o yaml "$2" >"$6"/"$2".yaml"}' | bash
  else
    kubectl get pod -n ${namespace} -o yaml ${pod} >${pod}.yaml
  fi
}

function k8s_desc_node() {
  kubectl describe node $@
}

function k8s_dump_node() {
  local node=$1
  if [ -z "${node}" ]; then
    log warn "Usage: k8s_dump_node <node name>"
    return ${RETURN_FAILURE}
  fi
  kubectl get node -o yaml ${node} >${node}.yaml
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

function k8s_node_images() {
  local node_name=${1}
  if [ -z "${node_name}" ]; then
    kubectl get nodes $@ -o go-template-file=/dev/stdin <<'EOF'
{{- range .items}}{{.metadata.name}}{{":\n"}}
  {{- range $image := .status.images -}}
    {{- range $name := $image.names -}}
      {{- printf "%-16d%s\n" $image.sizeBytes $name -}}
    {{- end -}}
  {{end}}
{{end}}
EOF
  else
    shift
    kubectl get nodes ${node_name} $@ -o go-template-file=/dev/stdin <<'EOF'
{{.metadata.name}}{{":\n"}}
{{- range $image := .status.images -}}
  {{- range $name := $image.names -}}
    {{- printf "%-16d%s\n" $image.sizeBytes $name -}}
  {{- end -}}
{{end}}
EOF
  fi
}

function k8s_node_labels() {
  local node_name=${1}
  if [ -z "${node_name}" ]; then
    kubectl get nodes $@ -o go-template-file=/dev/stdin <<'EOF'
{{range .items}}{{.metadata.name}}{{":"}}
  {{range $key,$value := .metadata.labels}}{{"\t"}}{{$key}}={{$value}}{{"\n"}}{{end}}
{{end}}
EOF
  else
    shift
    kubectl get nodes ${node_name} $@ -o go-template-file=/dev/stdin <<'EOF'
{{.metadata.name}}{{":"}}
  {{range $key,$value := .metadata.labels}}{{"\t"}}{{$key}}={{$value}}{{"\n"}}{{end}}
EOF
  fi
}

function k8s_node_taints() {
  local node_name=${1}
  if [ -z "${node_name}" ]; then
    kubectl get nodes $@ -o go-template-file=/dev/stdin <<'EOF'
{{range .items}}{{.metadata.name}}{{":"}}
  {{range .spec.taints}}{{"\t"}}{{range $key,$value := .}}{{" "}}{{$key}}={{$value}}{{","}}{{end}}{{"\n"}}{{end}}
{{end}}
EOF
  else
    shift
    kubectl get nodes ${node_name} $@ -o go-template-file=/dev/stdin <<'EOF'
{{.metadata.name}}{{":"}}
  {{range .spec.taints}}{{"\t"}}{{range $key,$value := .}}{{" "}}{{$key}}={{$value}}{{","}}{{end}}{{"\n"}}{{end}}
  {{end}}
EOF
  fi
}

function k8s_node_annotations() {
  local node_name=${1}
  if [ -z "${node_name}" ]; then
    kubectl get nodes $@ -o go-template-file=/dev/stdin <<'EOF'
{{range .items}}{{.metadata.name}}{{":"}}
  {{range $key,$value := .metadata.annotations}}{{"\t"}}{{$key}}={{$value}}{{"\n"}}{{end}}
{{end}}
EOF
  else
    shift
    kubectl get nodes ${node_name} $@ -o go-template-file=/dev/stdin <<'EOF'
{{.metadata.name}}{{":"}}
  {{range $key,$value := .metadata.annotations}}{{"\t"}}{{$key}}={{$value}}{{"\n"}}{{end}}
EOF
  fi
}

function k8s_node_status() {
  local node_name=${1}
  if [ -z "${node_name}" ]; then
    kubectl get nodes $@ -o go-template-file=/dev/stdin <<'EOF'
{{range .items}}{{.metadata.name}}{{":"}}
  CPU: {{.status.capacity.cpu}}
  Memory: {{.status.capacity.memory}}
  Pods: {{.status.capacity.pods}}
{{end}}
EOF
  else
    shift
    kubectl get nodes ${node_name} $@ -o go-template-file=/dev/stdin <<'EOF'
{{.metadata.name}}{{":"}}
  CPU: {{.status.capacity.cpu}}
  Memory: {{.status.capacity.memory}}
  Pods: {{.status.capacity.pods}}
EOF
  fi
}

function k8s_login_pod() {
  local namepsace=$1
  local pod_name=$2
  local cmd=${3:-sh}
  if [ -z "${namepsace}" -o -z "${pod_name}" ]; then
    log warn "Usage: k8s_login_pod <namespace> <pod name> [cmd]"
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
    log warn "Usage: k8s_login_container <namespace> <pod name> [container name] [cmd]"
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
    log warn "Usage: k8s_exec_pod <namespace> <pod name> <cmd>"
  else
    kubectl -n ${namepsace} exec -it ${pod_name} -- $@
  fi
}

function k8s_delete_pod() {
  local namepsace=$1
  shift
  local pod_name=$1
  shift
  if [ -z "${namepsace}" -o -z "${pod_name}" ]; then
    log warn "Usage: k8s_delete_pod <namespace> <pod name> <args...>"
  else
    kubectl -n ${namepsace} delete pod ${pod_name} -- $@
  fi
}

function k8s_pods() {
  local namepsace=${1}
  if [ -z "${namepsace}" ]; then
    namepsace=all
  else
    shift
  fi
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  printf "%-20s %-16s %-60s %-10s %-24s %-20s %-12s %-40s\n" Timestamp Namespace Name Status Node Runtime OwnerType OwnerName
  kubectl get pods ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF' | sort -k2,2 -k1,1
{{- range .items -}}
  {{- printf "%-20s " .metadata.creationTimestamp -}}
  {{- printf "%-16s " .metadata.namespace -}}
  {{- printf "%-60s " .metadata.name -}}
  {{- printf "%-10s " .status.phase -}}
  {{- with .spec.nodeName -}}
    {{- printf "%-24s " . -}}
  {{- else -}}
    {{- printf "%-24s " "None" -}}
  {{- end -}}
  {{- with .spec.runtimeClassName -}}
    {{- printf "%-20s" . -}}
  {{- else -}}
    {{- printf "%-20s" "runc" -}}
  {{- end -}}
  {{- with .metadata.ownerReferences -}}
    {{- $owner := index . 0 -}}
    {{- printf "%-12s " $owner.kind -}}
    {{- printf "%-40s " $owner.name -}}
  {{- else -}}
    {{- printf "%-12s " "None" -}}
    {{- printf "%-40s " "None" -}}
  {{- end -}}
  {{"\n"}}
{{- end -}}
EOF
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

function k8s_pods_by_node() {
  local node_name=${1}
  local namespace=${2}

  if [ -z "${node_name}" ]; then
    log warn "Usage: k8s_pods_by_node <node name> [namespace] [kubectl options]"
    return ${RETURN_FAILURE}
  else
    shift
  fi
  if [ -z "${namespace}" ]; then
    namespace=all
  else
    shift
  fi
  k8s_pods ${namespace} --field-selector "spec.nodeName=${node_name}" $@
}

function k8s_pods_by_runtime() {
  local runtime_class=${1}
  shift
  if [ -z "${runtime_class}" ]; then
    log warn "Usage: k8s_pods_by_runtime <runtime class name> [kubectl options]"
    return ${RETURN_FAILURE}
  fi
  k8s_pods $@ -l "alibabacloud.com/runtime-class-name=${runtime_class}"
}

function k8s_pods_by_node_and_runtime() {
  local node_name=${1}
  shift
  local runtime_class=${1}
  shift
  if [ -z "${node_name}" ] || [ -z "${runtime_class}" ]; then
    log warn "Usage: k8s_pods_by_node_and_runtime <node name> <runtime class name> [kubectl options]"
    return ${RETURN_FAILURE}
  fi
  k8s_pods $@ --field-selector spec.nodeName=${node_name} -l "alibabacloud.com/runtime-class-name=${runtime_class}"
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
  local namepsace=${1:-all}
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  shift
  local service_domain="svc.cluster.local"
  printf "%-32s %-48s %-16s %-16s %-24s %-32s\n" Namespace Service Type Target "IP:Port" "URL"
  kubectl get service ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF'
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
      {{- printf "%-32s " $namespace_name -}}
      {{- printf "%-48s " $service_name -}}
      {{- printf "%-16s " "ClusterIP" -}}
      {{- printf "%-16v " .targetPort -}}
      {{- $combine := (printf "%v:%v" $cluster_ip .port) -}}
      {{- printf "%-24s " $combine -}}
      {{- printf "%s.%s.svc.cluster.local:%v" $service_name $namespace_name .port -}}
      {{"\n"}}
    {{- end -}}
  {{- end -}}
  {{- range $external_ips -}}
    {{- $external_ip := . -}}
    {{- range $ports -}}
      {{- printf "%-32s " $namespace_name -}}
      {{- printf "%-48s " $service_name -}}
      {{- printf "%-16s " "ExternalIP" -}}
      {{- printf "%-16v " .targetPort -}}
      {{- $combine := (printf "%v:%v" $external_ip .nodePort) -}}
      {{- printf "%-24s " $combine -}}
      {{- printf "%s.%s.svc.cluster.local:%v" $service_name $namespace_name .port -}}
      {{"\n"}}
    {{- end -}}
  {{- end -}}
{{- end -}}
EOF
}

function k8s_ep() {
  local namepsace=${1:-all}
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  shift
  printf "%-24s %-40s %-24s %-48s %-24s\n" Namespace Name Node Pod Target
  kubectl get ep ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF'
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
}

function k8s_pod_images() {
  printf "%-24s %-60s %-80s \n" Namespace Name Image
  local namepsace=${1:-all}
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  shift
  kubectl get pods ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF'
{{- with .items -}}
  {{- range . -}}
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
{{- else -}}
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
}

function k8s_images_used() {
  k8s_pod_images $@ | grep -vw Image | awk '{print $3}' | sort | uniq
}

function k8s_apply() {
  local file_dir=${1:-${PWD}}
  kubectl apply -R -f ${file_dir}
}

function k8s_delete() {
  local file_dir=${1:-${PWD}}
  kubectl delete -R -f ${file_dir}
}

function k8s_logs() {
  local namepsace=${1}
  local pod=${2}
  if [ -z "${namepsace}" ] || [ -z "${pod}" ]; then
    log warn "Usage: k8s_logs <namespace> <pod> [container]"
    return ${RETURN_FAILURE}
  fi

  local container=${3}
  if [ -z "${container}" ]; then
    kubectl -n ${namepsace} logs --all-containers=true ${pod}
  else
    kubectl -n ${namepsace} logs ${pod} ${container}
  fi
}

function k8s_sys_pod() {
  k8s_pods kube-system $@
}

function k8s_sys_svc() {
  k8s_svc kube-system $@
}

function k8s_sys_deployment() {
  k8s_deployment kube-system $@
}

function k8s_sys_desc() {
  kubectl -n kube-system describe $@
}

function k8s_sys_logs() {
  k8s_logs kube-system
}

function k8s_sys_ep() {
  kubectl -n kube-system get ep $@
}

function k8s_kubeadm_dump_config() {
  local adm_conf=$1
  kubectl -n kube-system get configmap kubeadm-config -o jsonpath='{.data.ClusterConfiguration}' >${adm_conf}
}

function k8s_kubeadm_update_certs() {
  local adm_conf=$1
  local internal_ip=$2
  local external_ip=$3
  sed -i "/apiServer:/a \ \ certSANs:\n\ \ -\ ${internal_ip}\n\ \ -\ ${external_ip}" ${adm_conf}
  mv -fv /etc/kubernetes/pki/apiserver.crt /etc/kubernetes/pki/apiserver.crt.bak
  mv -fv /etc/kubernetes/pki/apiserver.key /etc/kubernetes/pki/apiserver.key.bak
  kubeadm init phase certs apiserver --v=5 --config ${adm_conf}
}

function k8s_kubeconfig() {
  kubectl config view --raw
}

function k8s_event() {
  printf "%-24s %-10s %-24s %-24s %-10s %-24s %-60s\n" Namespace Kind Time Object Type Reason Message
  local namepsace=${1:-all}
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  shift
  kubectl get event ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF'
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
}

function k8s_annotate_nodes() {
  local node_name=${1}
  local annotate_pair=${2}
  kubectl annotate nodes --overwrite ${node_name} ${annotate_pair}
}

function k8s_label_nodes() {
  local node_name=${1}
  local label_pair=${2}
  kubectl label nodes --overwrite ${node_name} ${label_pair}
}

function k8s_taint_nodes() {
  local node_name=${1}
  local taint_value=${2}
  if [ -z "${node_name}" ] || [ -z "${taint_value}" ]; then
    log warn "Usage: k8s_taint_nodes <node name> <taint value> [selector]"
    return ${RETURN_FAILURE}
  fi
  shift 2
  kubectl taint nodes $@ --overwrite ${node_name} ${taint_value}
}

function k8s_apis() {
  log notice "========== apis with namespace =========="
  kubectl api-resources --namespaced=true

  log notice "========== apis without namespace =========="
  kubectl api-resources --namespaced=false
}

function k8s_configmap() {
  local namepsace=${1:-all}
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  shift
  local cm_name=${1}
  if [ -z "${cm_name}" ]; then
    kubectl get configmap ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF'
{{- range .items -}}
  {{- printf "Namespace: %-24s\n" .metadata.namespace -}}
  {{- printf "Name: %-60s\n" .metadata.name -}}
  {{"------------------------------------------------\n"}}
  {{- range $key, $value := .data -}}
    {{- printf "%s=%s\n" $key $value -}}
  {{- end -}}
  {{"================================================\n"}}
{{- end -}}
EOF
  else
    shift
    kubectl get configmap ${ns_opt} ${cm_name} $@ -o go-template-file=/dev/stdin <<'EOF'
{{- printf "Namespace: %-24s\n" .metadata.namespace -}}
{{- printf "Name: %-60s\n" .metadata.name -}}
{{"------------------------------------------------\n"}}
{{- range $key, $value := .data -}}
  {{- printf "%s=%s\n" $key $value -}}
{{- end -}}
{{"================================================\n"}}
EOF
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

function k8s_svc_avail_external_ip() {
  local namepsace=${1}
  local service=${2}
  local opt=${3:-available}

  if [ -n "${namepsace}" -a -n "${service}" ]; then
    local list_ip_tpl=$(
      cat <<'EOF'
{{ range .spec.externalIPs }}
  {{- . }}
{{ end }}
EOF
    )
    available_ip=""
    for ip in $(kubectl -n ${namepsace} get service ${service} -o go-template --template="${list_ip_tpl}"); do
      if net_ping ${ip}; then
        log plain ${ip}
        break
      else
        if [[ ${opt} != "available" ]]; then
          log error "${ip} is not available"
        fi
      fi
    done
  fi
}

function k8s_svc_avail_external_ip_port() {
  local namepsace=${1}
  local service=${2}
  local port_name=${3}
  available_ip=$(k8s_svc_avail_external_ip ${namepsace} ${service})
  if [ -n "${available_ip}" ]; then
    local list_ip_tpl=$(
      cat <<'EOF' | sed "s/@AVAILABLE_IP@/${available_ip}/g" | sed "s/@PORT_NAME@/${port_name}/g"
{{- $external_ips := .spec.externalIPs -}}
{{- $ports := .spec.ports -}}
{{- range $external_ips -}}
  {{- $external_ip := . -}}
  {{- range $ports -}}
    {{- if and (eq (printf "%s" .targetPort) "@PORT_NAME@") (eq (printf "%s" $external_ip) "@AVAILABLE_IP@") -}}
      {{- printf "%s %d" $external_ip .nodePort }}
    {{- end -}}
  {{- end -}}
{{- end -}}
EOF
    )
    kubectl -n ${namepsace} get service ${service} -o go-template --template="${list_ip_tpl}"
  fi
}

function k8s_generate_namespace() {
  local namepsace=${1}
  kubectl create namespace --dry-run=client -o yaml ${namepsace}
}

function k8s_generate_pod() {
  local pod=${1}
  local image=${2}
  local kcmd="kubectl run ${pod} --image=${image} --dry-run=client -o yaml"
  # kcmd="${kcmd} --port=5701 " # let the container expose port 5701
  # kcmd="${kcmd} --env=\"POD_NAMESPACE=default\" " # set environment variables "DNS_DOMAIN=cluster" and "POD_NAMESPACE=default" in the container
  # kcmd="${kcmd} --labels=\"app=hazelcast,env=prod\" "  # set labels "app=hazelcast" and "env=prod" in the container
  # kcmd="${kcmd} --command -- <cmd> <arg1> ... <argN> " # pod using a different command and custom arguments
  eval $kcmd
}

function k8s_secret() {
  local namepsace=${1:-all}
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  shift
  kubectl get secret ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF'
{{- range .items -}}
  {{- printf "Namespace: %-40s\n" .metadata.namespace -}}
  {{- printf "Name: %-60s\n" .metadata.name -}}
  {{- printf "Data: \n" -}}
  {{- range $key, $value := .data -}}    
  {{- printf "    %-40s = " $key -}}
  {{- printf "%s\n" (base64decode $value) -}}
  {{- end -}}
  {{"---\n"}}
{{- end -}}
EOF
}

function k8s_pvc() {
  printf "%-40s %-60s %-8s %-8s %-12s %-12s %-20s %-20s\n" Namespace Name Status Capacity StorageClass VolumeMode CreationTime AccessModes
  local namepsace=${1:-all}
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  shift
  kubectl get pvc ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF'
{{- range .items -}}
  {{- printf "%-40s " .metadata.namespace -}}
  {{- printf "%-60s " .metadata.name -}}
  {{- printf "%-8s " .status.phase -}}
  {{- printf "%-8s " .spec.resources.requests.storage -}}
  {{- printf "%-12s " .spec.storageClassName -}}
  {{- printf "%-12s " .spec.volumeMode -}}
  {{- printf "%-20s " .metadata.creationTimestamp -}}
  {{- printf "%-20v " .spec.accessModes -}}
  {{"\n"}}
{{- end -}}
EOF
}

function k8s_pv() {
  printf "%-40s %-40s %-8s %-8s %-12s %-12s %-12s %-20s %-20s\n" Name PVC Status Capacity StorageClass Reclaim VolumeMode CreationTime AccessModes
  local namepsace=${1:-all}
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  shift
  kubectl get pv ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF'
{{- range .items -}}
  {{- printf "%-40s " .metadata.name -}}
  {{- printf "%-40s " .spec.claimRef.name -}}
  {{- printf "%-8s " .status.phase -}}
  {{- printf "%-8s " .spec.capacity.storage -}}
  {{- printf "%-12s " .spec.storageClassName -}}
  {{- printf "%-12s " .spec.persistentVolumeReclaimPolicy -}}
  {{- printf "%-12s " .spec.volumeMode -}}
  {{- printf "%-20s " .metadata.creationTimestamp -}}
  {{- printf "%-20v " .spec.accessModes -}}
  {{"\n"}}
{{- end -}}
EOF
}

function k8s_pv_pvc() {
  printf "%-64s %-64s\n" PV PVC
  kubectl get pv $@ -o go-template-file=/dev/stdin <<'EOF'
{{- range .items -}}
  {{- printf "%-40s " .metadata.name -}}
  {{- printf "%-40s " .spec.claimRef.name -}}
  {{"\n"}}
{{- end -}}
EOF
}

function k8s_pod_pvc() {
  local namepsace=${1}
  if [ -z "${namepsace}" ]; then
    namepsace=all
  else
    shift
  fi
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  printf "%-64s %-64s\n" Pod PVC
  kubectl get pods ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF' | sort -k2,2 -k1,1
{{- range .items -}}
  {{- $pod_name := .metadata.name -}}
  {{- range .spec.volumes -}}
    {{- if .persistentVolumeClaim -}}
      {{- printf "%-64s " $pod_name -}}
      {{- printf "%-64s " .persistentVolumeClaim.claimName -}}
      {{"\n"}}
    {{- end -}}
  {{- end -}}
{{- end -}}
EOF
}

function k8s_sc() {
  printf "%-40s %-40s %-20s %-20s\n" Name Provisioner ReclaimPolicy VolumeBindingMode
  local namepsace=${1:-all}
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  shift
  kubectl get storageclass ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF'
{{- range .items -}}
  {{- printf "%-40s " .metadata.name -}}
  {{- printf "%-40s " .provisioner -}}
  {{- printf "%-20s " .reclaimPolicy -}}
  {{- printf "%-20s " .volumeBindingMode -}}
  {{"\n"}}
{{- end -}}
EOF
}

function k8s_deployment() {
  local namepsace=${1}
  if [ -n "${namepsace}" ]; then
    shift
  fi
  #   printf "%-30s %-50s %-5s %-5s\n" Namespace Name Generation Replicas
  #   local tpl=$(
  #     cat <<'EOF'
  # {{- range .items -}}
  #   {{- printf "%-30s " .metadata.namespace -}}
  #   {{- printf "%-50s " .metadata.name -}}
  #   {{- printf "%-5s " .metadata.generation -}}
  #   {{- printf "%-5s " .spec.replicas: -}}
  #   {{"\n"}}
  # {{- end -}}
  # EOF
  #   )
  #   if [ -z "${namepsace}" ]; then
  #     kubectl get deployment -A -o go-template --template="${tpl}" $@
  #   else
  #     kubectl get deployment -n ${namepsace} -o go-template --template="${tpl}" $@
  #   fi
  if [ -z "${namepsace}" ]; then
    kubectl get deployment -A $@
  else
    kubectl get deployment -n ${namepsace} $@
  fi
}

function k8s_daemonset() {
  local namepsace=${1:-all}
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  shift
  kubectl get daemonset ${ns_opt} $@
}

function k8s_current_context() {
  kubectl config current-context
}

function k8s_current_cluster() {
  local current_context=$(k8s_current_context)
  kubectl config view -o jsonpath='{.contexts[?(@.name == "'"$(k8s_current_context)"'")].context.cluster}'
}

function k8s_contexts() {
  kubectl config view -o jsonpath='{range .contexts[*]}{.name} {.context.cluster}{"\n"}{end}'
}

function k8s_use_context() {
  local context=${1}
  if [ -z "${context}" ]; then
    log warn "Usage: k8s_use_context <context or cluster>"
    return ${RETURN_FAILURE}
  fi
  kubectl config use-context $(k8s_contexts | grep ${context} | awk '{print $1}')
}

function k8s_use_namespace() {
  local namespace=${1}
  kubectl config set-context --current --namespace=${namespace}
}

function k8s_runtime_class() {
  kubectl get runtimeclass -o wide
}

function k8s_pod_container() {
  local TPL=$(
    cat <<'EOF'
{{- $pod_name := .metadata.name -}}
{{- range .spec.initContainers -}}
  {{- printf "%-50s " $pod_name -}}
  {{- printf "(init) %-23s " .name -}}
  {{- printf "%-120s " .image -}}
  {{"\n"}}
{{- end -}}
{{- range .spec.containers -}}
  {{- printf "%-50s " $pod_name -}}
  {{- printf "%-30s " .name -}}
  {{- printf "%-120s " .image -}}
  {{"\n"}}
{{- end -}}
EOF
  )
  local namepsace=${1}
  if [ -z "${namepsace}" ]; then
    namepsace=all
  else
    shift
  fi
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  local pod_name=${1}
  if [ -z "${pod_name}" ]; then
    TPL=$(
      cat <<EOF
{{- range .items -}}
  ${TPL}
{{- end -}}
EOF
    )
  fi
  printf "%-50s %-30s %-120s\n" "Pod" "Container" Image
  kubectl get pods ${ns_opt} $@ --template="${TPL}"
}

function k8s_pod_hostpath() {
  printf "%-24s %-60s %-20s %-80s \n" Namespace Name Volume Hostpath
  local namepsace=${1:-all}
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  shift
  kubectl get pods ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF'
{{- range .items -}}
  {{- $namespace_name := .metadata.namespace -}}
  {{- $pod_name := .metadata.name -}}
  {{- range .spec.volumes -}}
    {{- $volume_name := .name -}}
    {{- with .hostPath -}}
      {{- printf "%-24s " $namespace_name -}}
      {{- printf "%-60s " $pod_name -}}
      {{- printf "%-20s " $volume_name -}}
      {{- printf "%-80s " .path -}}
      {{"\n"}}
    {{- end -}}
  {{- end -}}
{{- end -}}
EOF
}

function k8s_deployment_images() {
  printf "%-24s %-60s %-80s \n" Namespace Name Image
  local namepsace=${1:-all}
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  shift
  kubectl get deployment ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF'
{{- with .items -}}
  {{- range . -}}
    {{- $namespace_name := .metadata.namespace -}}
    {{- $deployment_name := .metadata.name -}}
    {{- range .spec.template.spec.containers -}}
      {{- printf "%-24s " $namespace_name -}}
      {{- printf "%-60s " $deployment_name -}}
      {{- printf "%-80s " .image -}}
      {{"\n"}}
    {{- end -}}
    {{- range .spec.template.spec.initContainers -}}
      {{- printf "%-24s " $namespace_name -}}
      {{- printf "%-60s " $deployment_name -}}
      {{- printf "%-80s " .image -}}
      {{"\n"}}
    {{- end -}}
  {{- end -}}
{{- else -}}
    {{- $namespace_name := .metadata.namespace -}}
    {{- $deployment_name := .metadata.name -}}
    {{- range .spec.template.spec.containers -}}
      {{- printf "%-24s " $namespace_name -}}
      {{- printf "%-60s " $deployment_name -}}
      {{- printf "%-80s " .image -}}
      {{"\n"}}
    {{- end -}}
    {{- range .spec.template.spec.initContainers -}}
      {{- printf "%-24s " $namespace_name -}}
      {{- printf "%-60s " $deployment_name -}}
      {{- printf "%-80s " .image -}}
      {{"\n"}}
    {{- end -}}
{{- end -}}
EOF
}

function k8s_daemonset_images() {
  printf "%-24s %-60s %-80s \n" Namespace Name Image
  local namepsace=${1:-all}
  case ${namepsace} in
  all)
    ns_opt=-A
    ;;
  *)
    ns_opt="-n ${namepsace}"
    ;;
  esac
  shift
  kubectl get daemonset ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF'
{{- with .items -}}
  {{- range . -}}
    {{- $namespace_name := .metadata.namespace -}}
    {{- $deployment_name := .metadata.name -}}
    {{- range .spec.template.spec.containers -}}
      {{- printf "%-24s " $namespace_name -}}
      {{- printf "%-60s " $deployment_name -}}
      {{- printf "%-80s " .image -}}
      {{"\n"}}
    {{- end -}}
    {{- range .spec.template.spec.initContainers -}}
      {{- printf "%-24s " $namespace_name -}}
      {{- printf "%-60s " $deployment_name -}}
      {{- printf "%-80s " .image -}}
      {{"\n"}}
    {{- end -}}
  {{- end -}}
{{- else -}}
    {{- $namespace_name := .metadata.namespace -}}
    {{- $deployment_name := .metadata.name -}}
    {{- range .spec.template.spec.containers -}}
      {{- printf "%-24s " $namespace_name -}}
      {{- printf "%-60s " $deployment_name -}}
      {{- printf "%-80s " .image -}}
      {{"\n"}}
    {{- end -}}
    {{- range .spec.template.spec.initContainers -}}
      {{- printf "%-24s " $namespace_name -}}
      {{- printf "%-60s " $deployment_name -}}
      {{- printf "%-80s " .image -}}
      {{"\n"}}
    {{- end -}}
{{- end -}}
EOF
}

function k8s_create_configmap_from() {
  local target=${1}
  if [ ! -f ${target} ] && [ ! -d ${target} ]; then
    log error "No Such File: ${target}"
    return ${RETURN_FAILURE}
  fi
  local name=${2:-$(basename ${target})}
  if k8s_valid_name ${name}; then
    kubectl create configmap ${name} --from-file=${target}
  else
    log error "Invalid Name: ${name}"
  fi
}

function k8s_valid_name() {
  local name=${1}
  if grep -Ew '[a-z0-9]([-a-z0-9]*[a-z0-9])?(\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*' >/dev/null 2>&1 <<<"${name}"; then
    return ${RETURN_SUCCESS}
  else
    return ${RETURN_FAILURE}
  fi
}

function k8s_pod_forwarding() {
  local namespace=${1}
  local pod_name=${2}
  local target_port=${3}
  if [ -z "${namespace}" ] || [ -z "${pod_name}" ] || [ -z "${target_port}" ]; then
    log error "Usage: k8s_pod_forwarding <namespace> <pod name> <target port> [local port]"
    return ${RETURN_FAILURE}
  fi

  local local_port=${4:-""} # random port
  if [ -z "${local_port}" ]; then
    log warn "No Local Port Specified, Use Random Port"
  fi

  kubectl --v=0 -n ${namespace} port-forward pods/${pod_name} ${local_port}:${target_port}
}

function k8s_service_forwarding() {
  local namespace=${1}
  local service_name=${2}
  local target_port=${3}
  if [ -z "${namespace}" ] || [ -z "${service_name}" ] || [ -z "${target_port}" ]; then
    log error "Usage: k8s_service_forwarding <namespace> <service name> <target port> [local port]"
    return ${RETURN_FAILURE}
  fi

  local local_port=${4:-""} # random port
  if [ -z "${local_port}" ]; then
    log warn "No Local Port Specified, Use Random Port"
  fi

  kubectl -n ${namespace} port-forward svc/${service_name} ${local_port}:${target_port}
}

function k8s_cluster_list() {
  kubectl config get-clusters | grep -v 'NAME' | while IFS= read -r line; do
    local cluster_name="${line%_*}"
    local cluster_id="${line##*_}"
    echo "${cluster_name} ${cluster_id}"
  done
}

function k8s_config_from_env() {
  kubectl config view --raw | sed "/client-certificate-data: REDACTED/{N;s/client-certificate-data: REDACTED\n    client-key-data: REDACTED/token: ${KUBECONFIG_TOKEN}/}"
}

function k8s_foreach_pod_exec() {
  local namepsace=${1}
  if [ -z "${namepsace}" ]; then
    log error "Usage: k8s_foreach_pod_exec <namespace> <command>"
    return ${RETURN_FAILURE}
  fi
  shift
  for pod_name in $(kubectl get pods -n ${namepsace} \
    --field-selector=status.phase=Running \
    -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}'); do
    kubectl -n ${namepsace} exec -it ${pod_name} -- $@
  done
}

function k8s_foreach_container_exec() {
  local namepsace=${1}
  local pod_name=${2}
  if [ -z "${namepsace}" ] || [ -z "${pod_name}" ]; then
    log error "Usage: k8s_foreach_container_exec <namespace> <pod name> <command>"
    return ${RETURN_FAILURE}
  fi
  shift
  shift
  for container in $(kubectl get pod -n ${namepsace} ${pod_name} -o jsonpath='{.spec.containers[*].name}'); do
    log notice "run [$*] in ${namepsace}->${pod_name}->${container}"
    kubectl exec -n ${namepsace} -it ${pod_name} -c ${container} -- $@
  done
}
