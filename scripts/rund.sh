function rund_login_vm(){
  local name="$1"
  socat "stdin,raw,echo=0,escape=0x11" "unix-connect:/run/vc/vm/${name}/console.sock"
}