if [ "${BASH_OS}" = "darwin" ]; then
  alias base64="base64"
else
  alias base64="base64 -w0"
fi

function encode_stdin() {
  echo "echo \"$(gzip -c - | base64)\"|base64 -d|gunzip -c -"
}

function encode_files() {
  local target=${@:-.}
  echo "echo \"$(tar zc --exclude-vcs $(ls -d ${target}) | base64)\"|base64 -d|tar zx"
}

function encode_script() {
  local script_file=${1}
  echo "echo \"$(cat ${script_file} | gzip -c - | base64)\"|base64 -d|gunzip -c -|bash"
}

function encode_function() {
  local funcname=${1}
  if [ -z "${funcname}" ]; then
    echo "Usage: encode_function <function_name>"
    return ${RETURN_FAILURE}
  fi
  echo "echo \"$(printf "function $(declare -f ${funcname})\n${funcname}\n" | gzip -c - | base64)\"|base64 -d|gunzip -c -|bash"
}

function encode_packed() {
  local INPUT="$@"

  [[ -z "$INPUT" ]] && die "Usage: pack_file <file>"

  encode_tar=encoded.tar.xz
  encode_script=packed.sh
  part_size=64k
  merge_script=packed_merge.sh

  rm -f ${encode_tar} ${encode_script} ${merge_script}

  # add all file in ${INPUT} into tar file ${encode_tar}
  tar zcf ${encode_tar} --exclude-vcs ${INPUT}

  # split the tar file by size ${part_size}
  split -b ${part_size} -d ${encode_tar} ${encode_tar}.

  # if tar file exists but not match checksum, remove it
  log plain "[ ! -f ${encode_tar} ] || echo '$(sha256sum ${encode_tar})'|sha256sum --status -c || rm -f ${encode_tar}" >>${encode_script}
  log plain "[ ! -f ${encode_tar} ] || echo '$(sha256sum ${encode_tar})'|sha256sum --status -c || rm -f ${encode_tar}" >>${merge_script}

  # handle each part of the splited file
  for part in $(ls ${encode_tar}.*); do
    # if the part not exist or not match checksum, generate it
    log plain "[ ! -f ${part} ] || ! echo '$(sha256sum ${part})'|sha256sum --status -c && echo '$(base64 -w0 ${part})'|base64 -d > ${part}" >>${encode_script}

    # check sum of the part
    log plain "echo '$(sha256sum ${part})'|sha256sum -c" >>${encode_script}
    log plain "echo '$(sha256sum ${part})'|sha256sum -c" >>${merge_script}

    # this script is for upload part file only
    log plain "echo '$(base64 -w0 ${part})'|base64 -d > ${part}" >${encode_script}${part#${encode_tar}}
    log plain "echo '$(sha256sum ${part})'|sha256sum -c" >>${encode_script}${part#${encode_tar}}

    # merge part file to whole tar file
    log plain "cat ${part} >> ${encode_tar}" >>${encode_script}
    log plain "cat ${part} >> ${encode_tar}" >>${merge_script}

    # remove part file locally
    rm -f ${part}
  done

  # extract tar file to original file and remove tar file
  log plain "echo '$(sha256sum ${encode_tar})'|sha256sum -c && tar xf ${encode_tar} && rm -f ${encode_tar}" >>${encode_script}
  log plain "echo '$(sha256sum ${encode_tar})'|sha256sum -c && tar xf ${encode_tar} && rm -f ${encode_tar}" >>${merge_script}

  # remove tar file locally
  rm -f ${encode_tar}
}

function file_pack_binary() {
  ldconfig
  local file_list="$@"
  tar cfJ binary.tar.xz \
    --absolute-names \
    --dereference \
    --hard-dereference \
    --preserve-permissions \
    --overwrite \
    ${file_list} \
    $(ldd ${file_list} | awk '$3~/^\//{print $3}' | sort | uniq | tr '\n' ' ')
}

function file_pack_system() {
  local output_file=${1:-chroot.tar.gz}
  local output_dir=$(dirname ${output_file})
  mkdir -p ${output_dir}
  tar -cvpzf ${output_file} --exclude=${output_dir} --exclude=/proc --exclude=/sys --exclude=/dev /
}

function extract_source() {
  local archive=$1
  shift
  local output=$1
  shift

  tar xf "${archive}" --strip-components=1 -C "${output}" $@
}

function file_extract() {
  if [ -z "$1" ]; then
    die "Usage: extract <path/file_name>.<zip|rar|bz2|gz|tar|tbz2|tgz|Z|7z|xz|ex|tar.bz2|tar.gz|tar.xz>"
  else
    for n in $@; do
      if [ -f "$n" ]; then
        case "${n%,}" in
        *.tar.bz2 | *.tar.gz | *.tar.xz | *.tbz2 | *.tgz | *.txz | *.tar)
          tar xvf "$n"
          ;;
        *.lzma) unlzma ./"$n" ;;
        *.bz2) bunzip2 ./"$n" ;;
        *.rar) unrar x -ad ./"$n" ;;
        *.gz) gunzip ./"$n" ;;
        *.zip) unzip ./"$n" ;;
        *.z) uncompress ./"$n" ;;
        *.7z | *.arj | *.cab | *.chm | *.deb | *.dmg | *.iso | *.lzh | *.msi | *.rpm | *.udf | *.wim | *.xar)
          7z x ./"$n"
          ;;
        *.xz) unxz ./"$n" ;;
        *.exe) cabextract ./"$n" ;;
        *)
          log error "extract: '$n' - unknown archive method"
          return ${RETURN_FAILURE}
          ;;
        esac
      else
        log error "'$n' - file does not exist"
        return ${RETURN_FAILURE}
      fi
    done
  fi
}

function file_fast_delete() {
  local target="$@"
  if [ -z "${target}" ]; then
    find . -delete
  else
    find ${target} -delete
  fi
}

function file_size() {
  du -k "$filename" | cut -f1
}

function file_same() {
  local src_info=$(stat -L -c "%D %F %i %t %T %u %U" $1)
  local target_info=$(stat -L -c "%D %F %i %t %T %u %U" $2)
  if [ "${src_info}" = "${target_info}" ]; then
    return ${RETURN_SUCCESS}
  else
    return ${RETURN_FAILURE}
  fi
}

function file_changed() {
  local last_day=${1:-1}
  find /etc/ /lib /usr/ -type f -mtime -${last_day} -ls | awk '{print $NF}'
}

function file_mv() {
  local src=$1
  local dest=$2
  if [ ! -d $(dirname $dest) ]; then
    mkdir -p $(dirname $dest)
  fi
  mv -fv $src $dest
}

function file_extract_to() {
  local tar_file=${1}
  local dst_dir=${2}
  local file_in_tar=${3}
  tar --extract --verbose \
    --file ${tar_file} \
    --directory=${dst_dir} \
    --strip 1 "${file_in_tar}"
}

function file_real_size() {
  local filepath=${1}
  if [ -z "${filepath}" ]; then
    echo "Usage: file_size <filepath>"
    return ${RETURN_FAILURE}
  fi
  if [ ! -e "${filepath}" ]; then
    echo "File not exist: ${filepath}"
    return ${RETURN_FAILURE}
  fi
  local logical_size=$(stat -c "%s" ${filepath})
  local physical_size=$(stat -c "%b" ${filepath})
  log notice "Logical size: ${logical_size} bytes"
  log notice "Physical size: $((physical_size * 512)) bytes"
}

function file_create() {
  local filepath=${1}
  if [ -z "${filepath}" ]; then
    log error "Usage: file_create <filepath>"
    return ${RETURN_FAILURE}
  fi
  mkdir -pv $(dirname ${filepath#/})
  touch ${filepath#/}
}

function install_executable_files() {
  install -D -v -m 0755 $@
}

function install_executable_binary() {
  local binary_name=${1}
  local source_path=${2}
  local target_path=${3}
  if [ -z "${binary_name}" ] || [ -z "${source_path}" ] || [ -z "${target_path}" ]; then
    log error "Usage: install_executable_binary <binary_name> <source_path> <target_dir>"
    return ${RETURN_FAILURE}
  fi
  install_executable_files \
    $(find ${source_path} -type f -executable -name ${binary_name}) \
    ${target_path}
}

function fix_files_name() {
  local origin_pattern=${1:-'*_*'}
  for p in $(find . -type f -name ${origin_pattern}); do
    l=$(dirname $p)
    f=$(basename $p)
    pushd $l
    mv -fv ${f} $(echo $f | tr '_' '-')
    popd
  done
}

function fix_permissions() {
  for d in "$@"; do
    find "${d}" \
      ! \( \
      -group "${NB_GID}" \
      -a -perm -g+rwX \
      \) \
      -exec chgrp "${NB_GID}" -- {} \+ \
      -exec chmod g+rwX -- {} \+
    # setuid, setgid *on directories only*
    find "${d}" \
      \( \
      -type d \
      -a ! -perm -6000 \
      \) \
      -exec chmod +6000 -- {} \+
  done
}

function files_on_change() {
  local monitor_dir=${1}
  local interval=${2}
  if [ -z "${monitor_dir}" ] || [ -z "${interval}" ]; then
    log error "Usage: files_on_change <monitor_dir> <interval> <callback_script> [args]"
    return ${RETURN_FAILURE}
  fi
  shift 2
  local callback_script=${3}
  if [ -z "${callback_script}" ]; then
    log error "Usage: files_on_change <monitor_dir> <interval> <callback_script> [args]"
    return ${RETURN_FAILURE}
  fi
  shift
  local callback_script_args=$@
  local state_dir="$(mktemp -d)"
  log notice "watching files in ${monitor_dir} using state directory: ${state_dir}"
  local previous_state_file=""
  local current_state_file="${state_dir}/$(date '+%s').txt"

  while true; do
    ls -lh "${monitor_dir}" | awk '{print $5, $1, $9}' >${current_state_file}

    if [ -n "${previous_state_file}" ] && [ -f "${previous_state_file}" ]; then
      if ! cmp -s "${previous_state_file}" "${current_state_file}"; then
        # Changes detected
        bash ${callback_script} ${callback_script_args}
      fi
    fi

    rm -rf ${previous_state_file}
    previous_state_file=${current_state_file}
    current_state_file="${state_dir}/$(date '+%s').txt"
    sleep ${interval}
  done

}
