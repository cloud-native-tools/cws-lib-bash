function helm_untar() {
  local name="$1"
  helm pull "$name" --untar
}
