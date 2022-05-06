function encode_files() {
  local target="$@"
  echo "echo \"$(tar zc --exclude-vcs $(ls -d "${target}") | base64 -w0)\"|base64 -d|tar zx"
}

function encode_file() {
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
  echo "[ ! -f ${encode_tar} ] || echo '$(sha256sum ${encode_tar})'|sha256sum --status -c || rm -f ${encode_tar}" >>${encode_script}
  echo "[ ! -f ${encode_tar} ] || echo '$(sha256sum ${encode_tar})'|sha256sum --status -c || rm -f ${encode_tar}" >>${merge_script}

  # handle each part of the splited file
  for part in $(ls ${encode_tar}.*); do
    # if the part not exist or not match checksum, generate it
    echo "[ ! -f ${part} ] || ! echo '$(sha256sum ${part})'|sha256sum --status -c && echo '$(base64 -w0 ${part})'|base64 -d > ${part}" >>${encode_script}

    # check sum of the part
    echo "echo '$(sha256sum ${part})'|sha256sum -c" >>${encode_script}
    echo "echo '$(sha256sum ${part})'|sha256sum -c" >>${merge_script}

    # this script is for upload part file only
    echo "echo '$(base64 -w0 ${part})'|base64 -d > ${part}" >${encode_script}${part#${encode_tar}}
    echo "echo '$(sha256sum ${part})'|sha256sum -c" >>${encode_script}${part#${encode_tar}}

    # merge part file to whole tar file
    echo "cat ${part} >> ${encode_tar}" >>${encode_script}
    echo "cat ${part} >> ${encode_tar}" >>${merge_script}

    # remove part file locally
    rm -f ${part}
  done

  # extract tar file to original file and remove tar file
  echo "echo '$(sha256sum ${encode_tar})'|sha256sum -c && tar xf ${encode_tar} && rm -f ${encode_tar}" >>${encode_script}
  echo "echo '$(sha256sum ${encode_tar})'|sha256sum -c && tar xf ${encode_tar} && rm -f ${encode_tar}" >>${merge_script}

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
          echo "extract: '$n' - unknown archive method"
          return 1
          ;;
        esac
      else
        echo "'$n' - file does not exist"
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
  local filename=$1
  shift
  echo $(du -k "$filename" | cut -f1)
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
