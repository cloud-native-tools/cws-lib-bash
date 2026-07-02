# ─── Cross-platform Binary Detection ────────────────────────────────
# Detect platform-specific binary paths with graceful fallback
if is_macos; then
  # macOS: prefer GNU coreutils gbase64 only if it is actually GNU (supports -w0)
  # Some systems ship a non-GNU gbase64 (fourmilab) with different flags
  if command -v gbase64 >/dev/null 2>&1 && gbase64 --version 2>/dev/null | grep -q 'GNU coreutils'; then
    BASE64_BIN=gbase64
    BASE64_WRAP_OPT="-w0"
  else
    BASE64_BIN=base64
    BASE64_WRAP_OPT="" # macOS base64 wraps output; _b64_encode uses tr -d '\n'
  fi
  TAR_BIN="env COPYFILE_DISABLE=1 tar"
else
  BASE64_BIN=base64
  BASE64_WRAP_OPT="-w0"
  TAR_BIN="tar"
fi

# ─── Cross-platform Compatibility Layer ─────────────────────────────

# Cross-platform base64 encode from stdin (no line wrapping)
# Usage: echo "data" | _b64_encode
function _b64_encode() {
  if [ -n "${BASE64_WRAP_OPT}" ]; then
    ${BASE64_BIN} ${BASE64_WRAP_OPT}
  else
    ${BASE64_BIN} | tr -d '\n'
  fi
}

# Cross-platform base64 encode from file (no line wrapping)
# Usage: _b64_encode_file <file>
function _b64_encode_file() {
  local file=$1
  if [ -n "${BASE64_WRAP_OPT}" ]; then
    # GNU base64 with -w0: file as positional argument
    ${BASE64_BIN} ${BASE64_WRAP_OPT} "${file}"
  else
    # macOS/other base64: pipe file content via stdin, strip newlines
    ${BASE64_BIN} < "${file}" | tr -d '\n'
  fi
}

# Cross-platform SHA-256 checksum (output format: "<hash>  <file>")
# Usage: _sha256 <file>   |   _sha256 -c < checksum_file
function _sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$@"
  elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$@"
  else
    log error "no sha256sum or shasum found"
    return ${RETURN_FAILURE}
  fi
}

# Cross-platform SHA-256 hash only (output: just the hex digest)
# Usage: _sha256_hash <file>
function _sha256_hash() {
  _sha256 "$1" | awk '{print $1}'
}

# Cross-platform SHA-256 verify (returns 0 if checksum matches)
# Usage: _sha256_check "<hash>  <file>"
function _sha256_check() {
  local checksum_line="$1"
  if command -v sha256sum >/dev/null 2>&1; then
    echo "${checksum_line}" | sha256sum -c --status 2>/dev/null
  elif command -v shasum >/dev/null 2>&1; then
    echo "${checksum_line}" | shasum -a 256 -c >/dev/null 2>&1
  else
    return ${RETURN_FAILURE}
  fi
}

# Cross-platform stat: file size in bytes
# Usage: _stat_size <file>
function _stat_size() {
  if is_macos; then
    stat -L -f "%z" "$1"
  else
    stat -L -c "%s" "$1"
  fi
}

# Cross-platform stat: block count (512-byte blocks)
# Usage: _stat_blocks <file>
function _stat_blocks() {
  if is_macos; then
    stat -L -f "%b" "$1"
  else
    stat -L -c "%b" "$1"
  fi
}

# Cross-platform stat: device + inode (for same-file detection)
# Usage: _stat_dev_inode <file>
function _stat_dev_inode() {
  if is_macos; then
    stat -L -f "%d %i" "$1"
  else
    stat -L -c "%d %i" "$1"
  fi
}

# Cross-platform stat: file type + device + inode + uid + user
# Usage: _stat_file_info <file>
function _stat_file_info() {
  if is_macos; then
    # macOS: %HT=file type, %d=device, %i=inode, %u=uid, %Su=user name
    stat -L -f "%HT %d %i %u %Su" "$1"
  else
    # Linux: %F=file type, %D=device, %i=inode, %u=uid, %U=user name
    stat -L -c "%F %D %i %u %U" "$1"
  fi
}

# ─── Encode Functions ────────────────────────────────────────────────

function encode_tar_stream() {
  echo "echo \"$(gzip -c - | _b64_encode)\"|base64 -d|tar xz"
}

function encode_stdin() {
  echo "echo \"$(gzip -c - | _b64_encode)\"|base64 -d|gunzip -c -"
}

function encode_files() {
  local target=${@:-.}
  echo "echo \"$(${TAR_BIN} zc --exclude-vcs $(ls -d ${target}) | _b64_encode)\"|base64 -d|tar zx"
}

function encode_script() {
  local script_file=${1}
  echo "echo \"$(cat ${script_file} | gzip -c - | _b64_encode)\"|base64 -d|gunzip -c -|bash"
}

function encode_function() {
  local func_list=${@}
  if [ -z "${func_list}" ]; then
    echo "Usage: encode_function <function_name1> <function_name2> ..."
    return ${RETURN_FAILURE}
  fi
  echo "source <(echo \"$({
    for funcname in ${func_list}; do
      printf "function $(declare -f ${funcname})\n"
    done
  } | gzip -c - | _b64_encode)\"|base64 -d|gunzip -c -)"
}

function encode_packed() {
  local INPUT="$@"

  [[ -z $INPUT ]] && die "Usage: pack_file <file>"

  encode_tar=encoded.tar.xz
  encode_script=packed.sh
  part_size=64k
  merge_script=packed_merge.sh

  rm -f ${encode_tar} ${encode_script} ${merge_script}

  # add all file in ${INPUT} into tar file ${encode_tar}
  ${TAR_BIN} zcf ${encode_tar} --exclude-vcs ${INPUT}

  # split the tar file by size ${part_size}
  # cross-platform: -d (numeric suffix) not supported on BSD split (macOS)
  split -b ${part_size} -d ${encode_tar} ${encode_tar}. 2>/dev/null || split -b ${part_size} ${encode_tar} ${encode_tar}.

  # cross-platform sha256 check commands for generated scripts (inlined, no helper deps)
  # tries sha256sum (GNU) first, falls back to shasum (macOS/BSD)
  local _sha256_check_cmd='(sha256sum -c --status 2>/dev/null || shasum -a 256 -c >/dev/null 2>&1)'
  local _sha256_verify_cmd='(sha256sum -c 2>/dev/null || shasum -a 256 -c)'

  # if tar file exists but not match checksum, remove it
  log plain "[ ! -f ${encode_tar} ] || echo '$(_sha256 ${encode_tar})'|${_sha256_check_cmd} || rm -f ${encode_tar}" >>${encode_script}
  log plain "[ ! -f ${encode_tar} ] || echo '$(_sha256 ${encode_tar})'|${_sha256_check_cmd} || rm -f ${encode_tar}" >>${merge_script}

  # handle each part of the splited file
  for part in $(ls ${encode_tar}.*); do
    # if the part not exist or not match checksum, generate it
    log plain "[ ! -f ${part} ] || ! echo '$(_sha256 ${part})'|${_sha256_check_cmd} && echo '$(_b64_encode_file ${part})'|base64 -d > ${part}" >>${encode_script}

    # check sum of the part
    log plain "echo '$(_sha256 ${part})'|${_sha256_verify_cmd}" >>${encode_script}
    log plain "echo '$(_sha256 ${part})'|${_sha256_verify_cmd}" >>${merge_script}

    # this script is for upload part file only
    log plain "echo '$(_b64_encode_file ${part})'|base64 -d > ${part}" >${encode_script}${part#${encode_tar}}
    log plain "echo '$(_sha256 ${part})'|${_sha256_verify_cmd}" >>${encode_script}${part#${encode_tar}}

    # merge part file to whole tar file
    log plain "cat ${part} >> ${encode_tar}" >>${encode_script}
    log plain "cat ${part} >> ${encode_tar}" >>${merge_script}

    # remove part file locally
    rm -f ${part}
  done

  # extract tar file to original file and remove tar file
  log plain "echo '$(_sha256 ${encode_tar})'|${_sha256_verify_cmd} && tar xf ${encode_tar} && rm -f ${encode_tar}" >>${encode_script}
  log plain "echo '$(_sha256 ${encode_tar})'|${_sha256_verify_cmd} && tar xf ${encode_tar} && rm -f ${encode_tar}" >>${merge_script}

  # remove tar file locally
  rm -f ${encode_tar}
}

function file_pack_binary() {
  local file_list="$@"
  if is_macos; then
    # macOS: use otool -L to list dynamic library dependencies
    local mac_deps=""
    for bin in ${file_list}; do
      if file "${bin}" | grep -q Mach-O; then
        mac_deps+="$(otool -L "${bin}" 2>/dev/null | awk 'NF>1 && $1 ~ /^\//{print $1}' | sort -u | tr '\n' ' ')"
      fi
    done
    ${TAR_BIN} cfJ binary.tar.xz \
      --absolute-names \
      --dereference \
      --preserve-permissions \
      --overwrite \
      ${file_list} \
      ${mac_deps}
  else
    # Linux: use ldd and ldconfig
    ldconfig
    ${TAR_BIN} cfJ binary.tar.xz \
      --absolute-names \
      --dereference \
      --hard-dereference \
      --preserve-permissions \
      --overwrite \
      ${file_list} \
      $(ldd ${file_list} | awk '$3 ~ /^\//{print $3}' | sort | uniq | tr '\n' ' ')
  fi
}

function file_pack_system() {
  local output_file=${1:-chroot.tar.gz}
  local output_dir=$(dirname ${output_file})
  mkdir -p ${output_dir}
  ${TAR_BIN} -cvpzf ${output_file} --exclude=${output_dir} --exclude=/proc --exclude=/sys --exclude=/dev /
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
  local src_info=$(_stat_file_info "$1")
  local target_info=$(_stat_file_info "$2")
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
  local logical_size=$(_stat_size "${filepath}")
  local physical_size=$(_stat_blocks "${filepath}")
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
  if [ -z "${monitor_dir}" ] || [ ! -d "${monitor_dir}" ]; then
    log error "<monitor_dir> is required and must be a directory"
    log error "Usage: files_on_change <monitor_dir> <interval> <callback_script> [callback_script_args]"
    return ${RETURN_FAILURE}
  fi
  shift
  local interval=${1}
  if [ -z "${interval}" ] || [ ${interval} -lt 1 ] || [ ${interval} -gt 60 ]; then
    log error "<interval> is required and must be a number between 1 and 60"
    log error "Usage: files_on_change <monitor_dir> <interval> <callback_script> [callback_script_args]"
    return ${RETURN_FAILURE}
  fi
  shift
  local callback_script=${1}
  if [ -z "${callback_script}" ] || [ ! -f "${callback_script}" ]; then
    log error "<callback_script> is required and must be a file"
    log error "Usage: files_on_change <monitor_dir> <interval> <callback_script> [callback_script_args]"
    return ${RETURN_FAILURE}
  fi
  shift
  local callback_script_args=$@
  local state_dir="$(mktemp -d)"
  log notice "watching files in ${monitor_dir} using state directory: ${state_dir}"
  local previous_state_file=""
  local current_state_file="${state_dir}/$(date '+%s').txt"

  while true; do
    # record current state
    ls -lh "${monitor_dir}" | awk '{print $5, $1, $9}' >${current_state_file}

    if [ -z "${previous_state_file}" ] || [ ! -f "${previous_state_file}" ]; then
      # first run
      bash ${callback_script} ${callback_script_args}
    elif ! cmp -s "${previous_state_file}" "${current_state_file}"; then
      # Changes detected
      bash ${callback_script} ${callback_script_args}
      rm -rf ${previous_state_file}
    else
      log notice "monitoring files in [${monitor_dir}] and no changes detected"
      rm -rf ${previous_state_file}
    fi

    previous_state_file=${current_state_file}
    current_state_file="${state_dir}/$(date '+%s').txt"
    sleep ${interval}
  done
}

function cp_file() {
  local args=("$@")
  local last_index=$((${#args[@]} - 1))
  local src=("${args[@]:0:last_index}")
  local dest="${args[${last_index}]}"
  if [ -f "${dest}" ]; then
    if [ ${#src[@]} -gt 1 ]; then
      log error "copy multiple file [${src[*]}] into one: ${dest}"
    else
      cp -rfv ${src[@]} ${dest}
    fi
  elif [ -d "${dest}" ]; then
    cp -rfv ${src[@]} ${dest}
  else
    mkdir -p $(dirname ${dest})
    cp -rfv ${src[@]} ${dest}
  fi
}

function mv_file() {
  local args=("$@")
  local last_index=$((${#args[@]} - 1))
  local src=("${args[@]:0:last_index}")
  local dest="${args[${last_index}]}"
  if [ -f "${dest}" ]; then
    if [ ${#src[@]} -gt 1 ]; then
      log error "copy multiple file [${src[*]}] into one: ${dest}"
    else
      mv -fv ${src[@]} ${dest}
    fi
  elif [ -d "${dest}" ]; then
    mv -fv ${src[@]} ${dest}
  else
    mkdir -p $(dirname ${dest})
    mv -fv ${src[@]} ${dest}
  fi
}

function highlight_in_file() {
  local pattern=${1}
  shift
  local search_paths=("$@")

  if [ -z "${pattern}" ]; then
    log error "Usage: highlight_in_file <pattern> [file_or_dir ...]"
    return ${RETURN_FAILURE}
  fi

  if [ ${#search_paths[@]} -eq 0 ]; then
    search_paths=("${PWD}")
  fi

  for path in "${search_paths[@]}"; do
    if [ ! -e "${path}" ]; then
      log error "path not found: ${path}"
      return ${RETURN_FAILURE}
    fi
  done

  grep --color=always -RIn -E "${pattern}" "${search_paths[@]}"
}

function highlight_difference_files() {
  local target_file=${1}
  local target_dir=${2}
  shift 2
  local find_root=${@}

  if [ -z "${target_file}" ]; then
    log error "Usage: highlight_difference_files <target_file> [target_dir] [find_root]"
    return ${RETURN_FAILURE}
  fi

  if [ -z "${target_dir}" ]; then
    local file_list=$(find ${find_root} -type f -name "${target_file}")
  else
    local file_list=$(find ${find_root} -type d -name "${target_dir}" -exec find {} -type f -name "${target_file}" \;)
  fi

  local colors=("${ANSI_TERMINAL_FOREGROUND_COLORS[@]}")
  local color_count=${#colors[@]}
  local color_index=0

  declare -A checksum_map
  for file in ${file_list}; do
    local checksum=$(_sha256 "${file}" | awk '{print $1}' | cut -c 1-8)
    if [[ -z ${checksum_map["${checksum}"]} ]]; then
      checksum_map["${checksum}"]="${file}"
    else
      checksum_map["${checksum}"]+=$'\n'${file}
    fi
  done

  {
    # Print files with different colors based on checksum
    for checksum in "${!checksum_map[@]}"; do
      local files=(${checksum_map[$checksum]//$'
  '/$'\n'}) # Split the newline-separated file list into an array
      local color="${colors[${color_index}]}"
      for file in "${files[@]}"; do
        printf "%s  %b%s%b\n" "${checksum}" "${color}" "${file}" "${CLEAR}" # Print with color and reset
      done
      ((color_index = (color_index + 1) % color_count)) # Cycle through colors
    done
  } | sort
}

function archive_current() {
  local filename=${1:-$(basename ${PWD}).tar.gz}
  ${TAR_BIN} zcf "${filename}" --exclude-vcs --exclude='*.tar.gz' ./*
  mv -fv ${filename} $(_sha256 ${filename} | awk '{print $1}')-$(date_id).tar.gz
}

function find_files_by_size() {
  local size=$1
  find . -type f -size "${size}" | grep -v /.git/
}

function find_files() {
  local first_file=${1}

  if [ -z "${first_file}" ]; then
    log error "no file pattern provide"
    log error "Usage: find_files <file pattern> [file pattern]"
    return ${RETURN_FAILURE}
  else
    shift
  fi

  local find_parameters=()
  find_parameters+=("-name" "${first_file}")
  for pattern in "${@}"; do
    find_parameters+=("-o" "-name" "${pattern}")
  done

  find . \( "${find_parameters[@]}" \)
}

function dir_diff() {
  local left_dir=${1}
  local right_dir=${2}

  if [ -z "${left_dir}" ] || [ -z "${right_dir}" ]; then
    log error "Usage: dir_diff <left_dir> <right_dir>"
    return ${RETURN_FAILURE}
  fi

  if [ ! -d "${left_dir}" ]; then
    log error "left_dir not found: ${left_dir}"
    return ${RETURN_FAILURE}
  fi

  if [ ! -d "${right_dir}" ]; then
    log error "right_dir not found: ${right_dir}"
    return ${RETURN_FAILURE}
  fi

  left_dir=${left_dir%/}
  right_dir=${right_dir%/}

  local tmp_dir
  tmp_dir=$(mktemp -d) || return ${RETURN_FAILURE}
  trap 'rm -rf "${tmp_dir}"' RETURN

  local left_list="${tmp_dir}/left.tsv"
  local right_list="${tmp_dir}/right.tsv"
  local left_files="${tmp_dir}/left.files"
  local right_files="${tmp_dir}/right.files"
  local only_left="${tmp_dir}/only_left.files"
  local only_right="${tmp_dir}/only_right.files"
  local changed_files="${tmp_dir}/changed.files"

  find "${left_dir}" -type f -print0 | while IFS= read -r -d '' file; do
    local rel="${file#${left_dir}/}"
    local sum
    sum=$(_sha256 "${file}" | awk '{print $1}')
    log color "%s\t%s" "${rel}" "${sum}"
  done | sort >"${left_list}"

  find "${right_dir}" -type f -print0 | while IFS= read -r -d '' file; do
    local rel="${file#${right_dir}/}"
    local sum
    sum=$(_sha256 "${file}" | awk '{print $1}')
    log color "%s\t%s" "${rel}" "${sum}"
  done | sort >"${right_list}"

  cut -f1 "${left_list}" | sort -u >"${left_files}"
  cut -f1 "${right_list}" | sort -u >"${right_files}"

  comm -23 "${left_files}" "${right_files}" >"${only_left}"
  comm -13 "${left_files}" "${right_files}" >"${only_right}"

  join -t $'\t' -1 1 -2 1 "${left_list}" "${right_list}" |
    awk -F'\t' '$2 != $3 {print $1}' >"${changed_files}"

  local only_left_count only_right_count changed_count
  only_left_count=$(wc -l <"${only_left}" | tr -d ' ')
  only_right_count=$(wc -l <"${only_right}" | tr -d ' ')
  changed_count=$(wc -l <"${changed_files}" | tr -d ' ')

  log notice "Only in left: ${only_left_count}"
  log notice "Only in right: ${only_right_count}"
  log notice "Modified: ${changed_count}"

  if [ -s "${only_left}" ]; then
    log color "${GREEN}Only in ${left_dir}${CLEAR}"
    sed 's/^/  + /' "${only_left}"
  fi

  if [ -s "${only_right}" ]; then
    log color "${YELLOW}Only in ${right_dir}${CLEAR}"
    sed 's/^/  - /' "${only_right}"
  fi

  if [ -s "${changed_files}" ]; then
    log color "${RED}Modified (checksum mismatch)${CLEAR}"
    sed 's/^/  * /' "${changed_files}"
  fi
}
