function asi_node_info() {
    printf "%-40s %-40s %-20s %-40s %-10s %-18s %-4s\n" Name Pool Type Hostname CPU Memory Pods
    local tpl=$(
        cat <<'EOF'
{{- range .items -}}
{{- printf "%-40s " .metadata.name -}}
{{- with $nodepool := index .metadata.labels "alibabacloud.com/nodepool-id" -}}
    {{- printf "%-40s " $nodepool -}}
{{else}}
    {{- printf "%-40s " "<nil>" -}}
{{- end -}}
{{- with $instancetype := index .metadata.labels "beta.kubernetes.io/instance-type" -}}
    {{- printf "%-20s " $instancetype -}}
{{else}}
    {{- printf "%-20s " "<nil>" -}}
{{- end -}}
{{- with $hostname := index .metadata.labels "kubernetes.io/hostname" -}}
    {{- printf "%-40s " $hostname -}}
{{else}}
    {{- printf "%-40s " "<nil>" -}}
{{- end -}}
{{- printf "%-10s "  .status.capacity.cpu -}}
{{- printf "%-18s "  .status.capacity.memory -}}
{{- printf "%-4s\n"  .status.capacity.pods -}}
{{- end -}}
EOF
    )
    kubectl get nodes -o go-template --template="${tpl}"
}
