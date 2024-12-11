function qemu_get_bin() {
  if command -v qemu-system-aarch64 &>/dev/null; then
    export QEMU_BIN=$(command -v qemu-system-aarch64 &>/dev/null)
  elif command -v qemu-system-x86_64 &>/dev/null; then
    export QEMU_BIN=$(command -v qemu-system-x86_64 &>/dev/null)
  elif [ -x /usr/libexec/qemu-kvm ]; then
    export QEMU_BIN=/usr/libexec/qemu-kvm
  else
    log error "qemu not found"
    return ${RETURN_FAILURE}
  fi
}

function qemu_arm64_start() {
  local vm_name=${1:-"vm-arm64"}
  if qemu_get_bin; then
    ${QEMU_BIN} \
      -name ${vm_name} \
      -machine type=virt,accel=tcg \
      -cpu cortex-a57 \
      -smp cpus=2,sockets=2 \
      -m 2048M \
      -bios /usr/local/share/qemu/aarch64/QEMU_EFI.fd \
      -drive file=/work/focal-server-cloudimg-arm64.qcow2,if=virtio,cache=writeback,discard=ignore,format=qcow2 \
      -device virtio-net,netdev=user.0 \
      -netdev user,id=user.0,hostfwd=tcp::50022-:22 \
      -vnc 0.0.0.0:80 \
      -k en-us \
      -serial mon:vc
  fi
}

function qemu_amd64_start() {
  local vm_name=${1:-"vm-amd64"}
  if qemu_get_bin; then
    ${QEMU_BIN} \
      -name ${vm_name} \
      -machine accel=hvf \
      --cpu host \
      -smp cpus=2,sockets=2 \
      -m 2048M \
      -drive file=~/vm/k8s-node1/k8s-node1.vhd,if=virtio,format=vpc \
      -drive file=~/vm/k8s-node1/seed.img,if=virtio,format=raw \
      -device virtio-net,netdev=user.0 \
      -netdev user,id=user.0,hostfwd=tcp::50022-:22 \
      -vnc 0.0.0.0:80 \
      -k en-us \
      -serial mon:vc
  fi
}
