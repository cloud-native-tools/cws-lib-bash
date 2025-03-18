function apt_prune() {
  # remove packages as much as possible, only keep the base system
  apt update
  apt-mark hold \
    apt \
    bash \
    coreutils \
    dpkg \
    libc6 \
    libstdc++6

  for pkg in $(apt list --installed 2>/dev/null | grep -w installed | awk -F'/' '{print $1}'); do
    echo -n "try to remove ${pkg}"
    if apt autoremove -y ${pkg} >/dev/null 2>&1; then
      echo "\033[1;32mremoved\033[0m"
    else
      echo "\033[1;31mskipped\033[0m"
    fi
  done
}
