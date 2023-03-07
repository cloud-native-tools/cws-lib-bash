function in_chroot() {
  if ! file_same /proc/1/root /; then
    return 0
  else
    return 1
  fi
}

function mount_chroot() {
  local root_dir=$1
  mkdir -p ${root_dir}/proc && mount -t proc proc ${root_dir}/proc
  mkdir -p ${root_dir}/sys && mount -t sysfs sysfs ${root_dir}/sys
  mkdir -p ${root_dir}/dev && mount -t devtmpfs devtmpfs ${root_dir}/dev
  mkdir -p ${root_dir}/dev/shm && mount -t tmpfs tmpfs ${root_dir}/dev/shm
  mkdir -p ${root_dir}/dev/pts && mount -t devpts devpts ${root_dir}/dev/pts
  touch ${root_dir}/etc/passwd
  mount -o bind /etc/passwd ${root_dir}/etc/passwd
  touch ${root_dir}/etc/hosts
  mount -o bind /etc/hosts ${root_dir}/etc/hosts
  touch ${root_dir}/etc/resolv.conf
  mount -o bind /etc/resolv.conf ${root_dir}/etc/resolv.conf
}

function umount_chroot() {
  local root_dir=$1
  umount -f ${root_dir}/etc/resolv.conf
  umount -f ${root_dir}/etc/hosts
  umount -f ${root_dir}/etc/passwd
  umount -f ${root_dir}/dev/pts
  umount -f ${root_dir}/dev/shm
  umount -f ${root_dir}/dev
  umount -f ${root_dir}/sys
  umount -f ${root_dir}/proc
}

function enter_chroot() {
  local entry="$@"
  if ! in_chroot; then
    local root_dir=$(get_root)

    if [[ ! -d "${root_dir}" ]]; then
      die "${root_dir} is not a directory"
    else
      mount_chroot ${root_dir}
      chroot ${root_dir} ${entry}
      umount_chroot ${root_dir}
    fi
  else
    echo "already in a chroot env"
  fi
}

function mount_bootable() {
  local target=${1}
  local mountpoint=${2:-/media}
  local free_loop=$(losetup -f)
  losetup ${free_loop} ${target} -o $((2048 * 512))
  mount ${free_loop} ${mountpoint}
  log info "mount: ${target} -> ${free_loop} -> ${mountpoint}"
}
