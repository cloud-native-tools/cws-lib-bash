function cws_build() {
  for script in $(find . -name docker-build.sh); do
    if sh $script; then
      echo "build in $(dirname $script) success"
    else
      echo "build in $(dirname $script) failed"
      break
    fi
    sleep 1
  done
}

function cws_pull() {
  for script in $(find . -name docker-pull.sh); do
    if sh $script; then
      echo "pull in $(dirname $script) success"
    else
      echo "pull in $(dirname $script) failed"
      break
    fi
    sleep 1
  done
}

function cws_push() {
  for script in $(find . -name docker-push.sh); do
    if sh $script; then
      echo "push in $(dirname $script) success"
    else
      echo "push in $(dirname $script) failed"
      break
    fi
    sleep 1
  done
}
