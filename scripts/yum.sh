# Downloads RPM packages without installing them to the current directory
function yum_download() {
  yum reinstall --downloadonly --downloaddir ${PWD} $@
}

# Creates a minimal rootfs with basic packages
function yum_mk_rootfs() {
  local rootfs="${1:-/tmp/rootfs}"
  mkdir -pv ${rootfs}
  # # mount -t tmpfs tmpfs ${rootfs}
  # rpm --root ${rootfs} -vv --initdb
  local yum_install="yum install -y --installroot=${rootfs} --setopt=tsflags='nodocs' --setopt=install_weak_deps=False"
  local default_packages="setup basesystem filesystem bash yum"
  . /etc/os-release
  local osname="${ID:-alios}"
  case ${osname} in
  alinux*)
    ${yum_install} ${default_packages} alinux-release
    ;;
  alios*)
    ${yum_install} ${default_packages} alios-release-server
    ;;
  fedora*)
    ${yum_install} ${default_packages} fedora-release
    ;;
  centos*)
    ${yum_install} ${default_packages} centos-release
    ;;
  esac
  # umount
}

# Lists all available versions of specified packages
function yum_list() {
  yum list --showduplicates $@
}

# Installs packages with retry functionality for reliability
function yum_install_with_retry() {
  local retries=${1}
  local count=0

  if [ $# -lt 2 ]; then
    echo "Usage: yum_install_with_retry <retries> <package>"
    return ${RETURN_FAILURE}
  fi

  shift

  while [ $count -lt $retries ]; do
    if yum install -y $@; then
      return ${RETURN_SUCCESS}
    else
      echo "install failed at $count attempt, need retry: $@"
      count=$(($count + 1))
      sleep 1
    fi
  done

  if [ $count -eq $retries ]; then
    echo "Failed to install package after $retries attempts."
    return ${RETURN_FAILURE}
  fi
}

# Removes non-essential packages while preserving the base system
function yum_prune() {
  # remove packages as much as possible, only keep the base system
  rm -rv /etc/dnf/protected.d
  mkdir -p /etc/dnf/protected.d
  {
    echo 'setup'
    echo 'glibc'
    echo 'rpm'
    echo 'dnf'
  } >/etc/dnf/protected.d/keep.conf
  {
    for pkg in $(rpm -qa); do
      echo -n "try to remove ${pkg}: "
      if dnf remove -y ${pkg} >/dev/null 2>&1; then
        echo -e "\033[1;32mremoved\033[0m"
      else
        echo -e "\033[1;31mskipped\033[0m"
      fi
    done
  }
}
