function rpm_extract_file() {
  local rpm_file=${1}
  local target_file=${2}
  rpm2cpio ${rpm_file} | cpio -idmv ${target_file}
}
