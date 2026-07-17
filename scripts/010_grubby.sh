function grubby_set_eth_names() {
  grubby --update-kernel=/boot/vmlinuz-$(uname -r) --args="net.ifnames=0 biosdevname=0"
  grub2-mkconfig -o /boot/grub2/grub.cfg
}

function grubby_disable_audit() {
  grubby --update-kernel=/boot/vmlinuz-$(uname -r) --args="audit=0"
  grub2-mkconfig -o /boot/grub2/grub.cfg
}
