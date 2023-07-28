function yum_download() {
  yum reinstall --downloadonly --downloaddir ${PWD} $@
}

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

function yum_list() {
  yum list --showduplicates $@
}
