function ps_user() {
  ps -ef | grep -v '\[' | sort -k 8
}
