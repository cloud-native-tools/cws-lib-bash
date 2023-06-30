function encode_files() {
  local target=${@:-.}
  log plain "echo \"$(tar zc --exclude-vcs $(ls ${target}) | base64 -w0)\"|base64 -d|tar zx"
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

function pack_binary() {
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

function pack_system() {
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

function extract() {
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
          return 1
          ;;
        esac
      else
        log error "'$n' - file does not exist"
        return 1
      fi
    done
  fi
}

function fast_delete() {
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
    return 0
  else
    return 1
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

function extract_file_to() {
  local tar_file=${1}
  local dst_dir=${2}
  local file_in_tar=${3}
  tar --extract --verbose \
    --file ${tar_file} \
    --directory=${dst_dir} \
    --strip 1 "${file_in_tar}"
}

function file_size() {
  local filepath=${1}
  if [ -z "${filepath}" ]; then
    echo "Usage: file_size <filepath>"
    return 1
  fi
  if [ ! -e "${filepath}" ]; then
    echo "File not exist: ${filepath}"
    return 1
  fi
  local logical_size=$(stat -c "%s" ${filepath})
  local physical_size=$(stat -c "%b" ${filepath})
  echo "Logical size: ${logical_size} bytes"
  echo "Physical size: $((physical_size * 512)) bytes"
}
