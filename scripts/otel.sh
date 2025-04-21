function otelcol_generate_config() {
  local config_file=${1:-/etc/otel/otelcol-contrib/dynamic.yaml}
  local log_dir=${2:-${OUTPUT_DIR}}

  if ! have yq; then
    log error "yq is not installed. Please install yq to use this function." >&2
    return ${RETURN_FAILURE}
  fi

  [[ -d "${log_dir}" ]] || {
    log error "Output directory does not exist: ${log_dir}" >&2
    return ${RETURN_FAILURE}
  }

  cd "${log_dir}" || exit 1

  if [ ! -f "${config_file}" ]; then
    mkdir -p "$(dirname ${config_file})"
    yq eval -n '
    .receivers = {}
    | .processors = {}
    | .exporters = {}
    | .extensions = {}
    | .connectors = {}
    | .service.pipelines = {}
  ' >"${config_file}"
  fi

  for file in *.stdout *.stderr; do
    [[ -e "${file}" ]] || continue
    local name="${file%.*}" type="filelog"
    [[ -p "${file}" ]] && type="namedpipe"

    local config_value
    if [[ "${type}" == "namedpipe" ]]; then
      config_value="{\"path\": \"${log_dir}/${file}\"}"
    else
      config_value="{\"include\": [\"${log_dir}/${file}\"]}"
    fi

    yq eval -i ".receivers.\"${type}/${name}\" = ${config_value}" "${config_file}"
  done

  for file in *.stdout *.stderr; do
    [[ -e "${file}" ]] || continue
    local name="${file%.*}"
    yq eval -i ".processors.\"attributes/${name}\".actions = [{\"action\": \"insert\", \"key\": \"from\", \"value\": \"${name}\"}]" "${config_file}"
  done

  for stream in stdout stderr; do
    [[ -e "/dev/${stream}" ]] || continue
    yq eval -i ".exporters.\"file/${stream}\" = {\"path\": \"/dev/${stream}\"}" "${config_file}"
  done

  for file in *.stdout *.stderr; do
    [[ -e "${file}" ]] || continue
    local name="${file%.*}" receiver_type="filelog"
    [[ -p "${file}" ]] && receiver_type="namedpipe"

    local exporter="file/${file##*.}"
    yq eval -i ".service.pipelines.\"logs/${name}\" = {
      \"receivers\": [\"${receiver_type}/${name}\"],
      \"processors\": [\"attributes/${name}\", \"transform\"],
      \"exporters\": [\"${exporter}\"]
    }" "${config_file}"
  done
}
