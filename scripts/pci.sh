function pci_info() {
  local bdf=${1}
  if [ -z "${bdf}" ]; then
    echo "Usage: pci_info <bdf>"
    return ${RETURN_FAILURE}
  fi
  lspci -vvv -s ${bdf}
}

function pci_iommu_list() {
  local lastgroup=""
  if [ -d /sys/kernel/iommu_groups ]; then
    for g in $(find /sys/kernel/iommu_groups/* -maxdepth 0 -type d | sort -V); do
      for d in $g/devices/*; do
        if [ "${g##*/}" != "$lastgroup" ]; then
          echo -en "Group ${g##*/}:\t"
        else
          echo -en "\t\t"
        fi
        lastgroup=${g##*/}
        lspci -nms ${d##*/} | awk -F'"' '{printf "[%s:%s]", $4, $6}'
        if [[ -e "$d"/reset ]]; then echo -en " [R] "; else echo -en "     "; fi

        lspci -mms ${d##*/} | awk -F'"' '{printf "%s %-40s %s\n", $1, $2, $6}'
        for u in ${d}/usb*/; do
          bus=$(cat "${u}/busnum")
          lsusb -s $bus: |
            awk '{gsub(/:/,"",$4); printf "%s|%s %s %s %s|", $6, $1, $2, $3, $4; for(i=7;i<=NF;i++){printf "%s ", $i}; printf "\n"}' |
            awk -F'|' '{printf "USB:\t\t[%s]\t\t %-40s %s\n", $1, $2, $3}'
        done
      done
    done
  fi
}

function pci_ali_nvme() {
  for bdf in $(lspci -nn -v | grep 1ded:5004 | awk '{print $1}'); do echo $bdf; done
}
