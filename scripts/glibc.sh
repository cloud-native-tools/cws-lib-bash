function ldd_lib() {
  LD_DEBUG=libs ldd $@
}
