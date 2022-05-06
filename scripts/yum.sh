function mk_rootfs_rpm() {
  local root_fs="${1}"
  local os_name="${2}"
  mkdir -p ${root_fs}
  #mount -t tmpfs tmpfs ${root_fs}
  rpm --root ${root_fs} --initdb

  yum reinstall --downloadonly --downloaddir /tmp alinux-release
  rpm --root ${root_fs} -ivh --nodeps /tmp/alinux-release*.rpm
  yum -y --installroot=${root_fs} --setopt=tsflags='nodocs' install yum wget
  rm -rfv ${root_fs}/var/cache/yum

  case ${os_name} in
  alinux*)
    yum reinstall --downloadonly --downloaddir /tmp alinux-release
    rpm --root ${root_fs} -ivh --nodeps /tmp/alinux-release*.rpm
    ;;
  alios*)
    yum reinstall --downloadonly --downloaddir /tmp alios-release-server
    rpm --root ${root_fs} -ivh --nodeps /tmp/alios-release-server*.rpm
    ;;
  fedora*)
    yum reinstall --downloadonly --downloaddir /tmp fedora-release
    rpm --root ${root_fs} -ivh --nodeps /tmp/fedora-release*.rpm
    ;;
  centos*)
    yum reinstall --downloadonly --downloaddir /tmp centos-release
    rpm --root ${root_fs} -ivh --nodeps /tmp/centos-release*.rpm
    ;;
  esac
  yum -y --installroot=${root_fs} --setopt=tsflags='nodocs' install yum
}
