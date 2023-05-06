function k8s_sa_token() {
  local namespace=${1:-kube-system}
  local sa=${2:-kube-system}
  local secrets_name=$(kubectl -n ${namespace} get sa/${sa} -o jsonpath="{.secrets[0].name}")
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
  kubectl describe node $@
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
  kubectl get nodes $@ -o go-template-file=/dev/stdin <<'EOF'
{{range .items}}{{.metadata.name}}{{":"}}
  {{range $key,$value := .metadata.labels}}{{"\t"}}{{$key}}={{$value}}{{"\n"}}{{end}}
{{end}}
EOF
}

function k8s_node_taints() {
  kubectl get nodes -o go-template-file=/dev/stdin <<'EOF'
{{range .items}}{{.metadata.name}}{{":"}}
  {{range .spec.taints}}{{"\t"}}{{range $key,$value := .}}{{" "}}{{$key}}={{$value}}{{","}}{{end}}{{"\n"}}{{end}}
{{end}}
EOF
}

function k8s_node_annotations() {
  kubectl get nodes -o go-template-file=/dev/stdin <<'EOF'
{{range .items}}{{.metadata.name}}{{":"}}
  {{range $key,$value := .metadata.annotations}}{{"\t"}}{{$key}}={{$value}}{{"\n"}}{{end}}
{{end}}
EOF
}

function k8s_node_status() {
  kubectl get nodes -o go-template-file=/dev/stdin <<'EOF'
{{range .items}}{{.metadata.name}}{{":"}}
  CPU: {{.status.capacity.cpu}}
  Memory: {{.status.capacity.memory}}
  Pods: {{.status.capacity.pods}}
{{end}}
EOF
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

function k8s_delete_pod() {
  local namepsace=$1
  shift
  local pod_name=$1
  shift
  if [ -z "${namepsace}" -o -z "${pod_name}" ]; then
    echo "Usage: k8s_delete_pod <namespace> <pod name> <args...>"
  else
    kubectl -n ${namepsace} delete pod ${pod_name} -- $@
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
  printf "%-30s %-50s %-10s %-12s %-40s %-20s %-20s\n" Namespace Name Status OwnerType OwnerName Node Runtime
  kubectl get pods ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF'
{{- range .items -}}
  {{- printf "%-30s " .metadata.namespace -}}
  {{- printf "%-50s " .metadata.name -}}
  {{- printf "%-10s " .status.phase -}}
  {{- with .metadata.ownerReferences -}}
  {{- $owner := index . 0 -}}
    {{- printf "%-12s " $owner.kind -}}
    {{- printf "%-40s " $owner.name -}}
  {{- else -}}
    {{- printf "%-12s " "None" -}}
    {{- printf "%-40s " "None" -}}
  {{- end -}}
  {{- with .spec.nodeName -}}
    {{- printf "%-20s " . -}}
  {{- else -}}
    {{- printf "%-20s " "None" -}}
  {{- end -}}
  {{- with .spec.runtimeClassName -}}
    {{- printf "%-20s" . -}}
  {{- else -}}
    {{- printf "%-20s" "runc" -}}
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

function k8s_pod_by_node() {
  local node_name=${1}
  shift
  if [ -z "${node_name}" ]; then
    echo "Usage: k8s_pod_by_node <node name> [kubectl options]"
    return 1
  fi
  k8s_pods $@ --field-selector spec.nodeName=${node_name}
}

function k8s_pod_by_runtime() {
  local runtime_class=${1}
  shift
  if [ -z "${runtime_class}" ]; then
    echo "Usage: k8s_pod_by_runtime <runtime class name> [kubectl options]"
    return 1
  fi
  k8s_pods $@ -l "alibabacloud.com/runtime-class-name=${runtime_class}"
}

function k8s_pod_by_node_and_runtime() {
  local node_name=${1}
  shift
  local runtime_class=${1}
  shift
  if [ -z "${node_name}" ] || [ -z "${runtime_class}" ]; then
    echo "Usage: k8s_pod_by_node_and_runtime <node name> <runtime class name> [kubectl options]"
    return 1
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

function k8s_pods_images() {
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
}

function k8s_images_used() {
  k8s_pods_images $@ | grep -vw Image | awk '{print $3}' | sort | uniq
}

function k8s_apply() {
  local namespace=$1
  local file_dir=${2:-.}
  if [ -z "${namespace}" ]; then
    kubectl apply -R -f ${file_dir}
  else
    kubectl apply --namespace=${namespace} -R -f ${file_dir}
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
  k8s_deployment ${SYSTEM_NAMESPACE} $@
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

function k8s_kubeadm_dump_config() {
  kubectl -n ${SYSTEM_NAMESPACE} get configmap kubeadm-config -o jsonpath='{.data.ClusterConfiguration}'
}

function k8s_kubeadm_update_certs() {
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
  kubectl get configmap ${ns_opt} $@ -o go-template-file=/dev/stdin <<'EOF'
{{- range .items -}}
  {{- printf "Namespace: %-24s\n" .metadata.namespace -}}
  {{- printf "Name: %-60s\n" .metadata.name -}}
  {{- range $key, $value := .data -}}
    {{- printf "data: %s\n%-80s\n" $key $value -}}
  {{- end -}}
  {{"---\n"}}
{{- end -}}
EOF
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
        echo ${ip}
        break
      else
        if [[ ${opt} != "available" ]]; then
          echo "${ip} is not available"
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

function k8s_ds() {
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
    kubectl get daemonset -A $@
  else
    kubectl get daemonset -n ${namepsace} $@
  fi
}
