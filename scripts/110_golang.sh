function go_work_init() {
  go work init
  for go_mod in $(find . -name 'go.mod'); do
    go work use $(dirname ${go_mod})
  done
}
