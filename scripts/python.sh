function python_build_wheel() {
  if [ ! -f "setup.py" ]; then
    return ${RETURN_FAILURE}
  fi
  local tmp_dir=$(mktemp -d)
  mkdir -p ${tmp_dir}/{build,dist}
  python3 setup.py build --build-base ${tmp_dir}/build bdist_wheel --dist-dir ${tmp_dir}/dist > ${tmp_dir}/build.log 2>&1
  echo ${tmp_dir}/dist/*.whl
}
