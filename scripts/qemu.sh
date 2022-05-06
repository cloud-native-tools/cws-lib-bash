function qemu_aarch64_start() {
  qemu-system-aarch64 -name vm-aarch64 \
  -machine type=virt,accel=tcg \
  -cpu cortex-a57 -smp cpus=2,sockets=2 \
  -m 2048M \
  -bios /usr/local/share/qemu/aarch64/QEMU_EFI.fd \
  -drive file=/work/focal-server-cloudimg-arm64.qcow2,if=virtio,cache=writeback,discard=ignore,format=qcow2 \
  -device virtio-net,netdev=user.0 -netdev user,id=user.0,hostfwd=tcp::50022-:22 \
  -vnc 0.0.0.0:80 \
  -k en-us -serial mon:vc
}

function qemu_amd64_start() {
  qemu-system-x86_64 -name vm-amd64 \
  -machine accel=hvf \
  --cpu host -smp cpus=2,sockets=2 \
  -m 2048M \
  -drive file=/Users/liuqiming.lqm/vm/k8s-node1/k8s-node1.vhd,if=virtio,format=vpc \
  -drive file=/Users/liuqiming.lqm/vm/k8s-node1/seed.img,if=virtio,format=raw \
  -device virtio-net,netdev=user.0 -netdev user,id=user.0,hostfwd=tcp::50022-:22 \
  -vnc 0.0.0.0:80 \
  -k en-us -serial mon:vc
}
