function rpm_extract_file() {
  local rpm_file=${1}
  local target_file=${2}
  rpm2cpio ${rpm_file} | cpio -idmv ${target_file}
}

function rpm_get_source() {
  local spec_file=${1}
  if [ -f ${spec_file} ]; then
    rpmbuild --nodeps -v -bp ${spec_file}
  else
    log notice "Usage: rpm_get_source <spec_file>"
  fi
}
