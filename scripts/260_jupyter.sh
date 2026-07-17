function jupyter_data_path() {
  jupyter --paths | grep 'data:' -A1 | tail -n1 | awk '{print $1}'
}
