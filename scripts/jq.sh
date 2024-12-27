function jq_array_add() {
  local field=${1}
  local new_array=${2}
  local json_file=${3:--}
  cat ${json_file} | jq ".${field} = . + ${new_array}"
}

function jq_dict_add() {
  local new_dict=${1}
  local json_file=${2:--}
  cat ${json_file} | jq ". = . + ${new_dict}"
}

function jq_format() {
  local json_file=${1:--}
  cat ${json_file} | jq .
}

function jq_sort_file() {
  local json_file=${1}

  if [ -f "${json_file}" ]; then
    jq -S . ${json_file} >temp.json && mv temp.json ${json_file}
  else
    log error "file not found: ${json_file}"
  fi
}

function jq_otel_logs() {
  local logs_file=${1:--}
  cat ${logs_file} | jq -r '.resourceLogs[] | .scopeLogs[] | .logRecords[] |  "\(.attributes[].value.stringValue) \(.body.stringValue)"'
}
