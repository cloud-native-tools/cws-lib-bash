function java_flags() {
  java -XX:+PrintFlagsFinal -version
}

function java_dump() {
  local pid=$1
  local output=$2
  jmap -dump:format=b,file=${output} ${pid}
}

