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
