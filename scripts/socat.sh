function socat_tcp_to_unix() {
  local listen_port=$1
  local unix_file=$2
  socat -d "TCP4-LISTEN:${listen_port},reuseaddr,fork" "UNIX-CLIENT:${unix_file}"
}

function socat_unix_to_tcp() {
  local unix_file=$1
  local listen_port=$2
  socat -d "UNIX-LISTEN:${unix_file},reuseaddr,fork" "TCP4:localhost:${listen_port}"
}

function socat_tcp_to_tcp() {
  local listen_port=$1
  local target=$2
  socat -d "TCP4-LISTEN:${listen_port},reuseaddr,fork" "TCP4:${target}"
}

function socat_stdin_to_unix(){
  local target=$1
  socat "stdin,raw,echo=0,escape=0x11" "unix-connect:${target}/console.sock"
}