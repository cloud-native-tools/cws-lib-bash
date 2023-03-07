function jq_array_add() {
  local field=${1}
  local new_array=${2}
  cat - | jq ".${field} = . + ${new_array}"
}

function jq_dict_add() {
  local new_dict=${1}
  cat - | jq ". = . + ${new_dict}"
}
