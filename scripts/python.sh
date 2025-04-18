function python_build_wheel() {
  if [ ! -f "setup.py" ]; then
    log error "No setup.py found in the current directory. Please run this script in the directory containing setup.py."
    return ${RETURN_FAILURE}
  fi
  local tmp_dir=$(mktemp -d)
  mkdir -p ${tmp_dir}/{build,dist}
  python3 setup.py build --build-base ${tmp_dir}/build bdist_wheel --dist-dir ${tmp_dir}/dist >${tmp_dir}/build.log 2>&1
  echo ${tmp_dir}/dist/*.whl
}

function pip_show() {
  local package_name=$1
  if [ -z "${package_name}" ]; then
    log error "Usage: pip_show <package_name>"
    return ${RETURN_FAILURE}
  fi
  pip3 show -f ${package_name}
}
