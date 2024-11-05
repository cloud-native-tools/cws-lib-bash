export ECS_META_URL="http://100.100.100.200/latest"

function ecs_vpc_id() {
  curl_fetch ${ECS_META_URL}/meta-data/vpc-id
}

function ecs_vswitch_id() {
  curl_fetch ${ECS_META_URL}/meta-data/vswitch-id
}

function ecs_region() {
  curl_fetch ${ECS_META_URL}/meta-data/region-id
}

function ecs_zone_id() {
  curl_fetch ${ECS_META_URL}/meta-data/zone-id
}

function ecs_instance_type() {
  curl_fetch ${ECS_META_URL}/meta-data/instance/instance-type
}

function ecs_info() {
  curl_fetch ${ECS_META_URL}/dynamic/instance-identity/document
}

function ecs_uid() {
  curl_fetch ${ECS_META_URL}/meta-data/owner-account-id
}

function ecs_private_ip() {
  curl_fetch ${ECS_META_URL}/meta-data/private-ipv4
}

function ecs_public_ip() {
  curl_fetch ${ECS_META_URL}/meta-data/eipv4
}

function ecs_cloud_init_path() {
  readlink -f /var/lib/cloud/instance
}

function ecs_cloud_init_user_data() {
  cat $(ecs_cloud_init_path)/user-data.txt
}

function ecs_cloud_init_output() {
  cat /var/log/cloud-init-output.log
}

function ecs_cloud_init_log() {
  cat /var/log/cloud-init.log
}

function ecs_in_aliyun() {
  if curl_test_server ${ECS_META_URL}; then
    return ${RETURN_SUCCESS}
  else
    return ${RETURN_FAILURE}
  fi
}

function ecs_interfaces() {
  local interface_url=${ECS_META_URL}/meta-data/network/interfaces/macs/
  # printf "%-40s %-40s %-16s %-24s\n" Namespace Service Name URL
  printf "%-30s %-30s %-30s %-30s %-16s %-16s %-16s\n" VPC VSWITCH ENI MAC IP GATEWAY NETMASK
  for mac in $(curl_fetch ${interface_url}); do
    local gateway=$(curl_fetch ${interface_url}${mac}/gateway)
    local netmask=$(curl_fetch ${interface_url}${mac}/netmask)
    local network_interface_id=$(curl_fetch ${interface_url}${mac}/network-interface-id)
    local primary_ip_address=$(curl_fetch ${interface_url}${mac}/primary-ip-address)
    local private_ipv4s=$(curl_fetch ${interface_url}${mac}/private-ipv4s)
    local vpc_cidr_block=$(curl_fetch ${interface_url}${mac}/vpc-cidr-block)
    local vpc_id=$(curl_fetch ${interface_url}${mac}/vpc-id)
    local vswitch_cidr_block=$(curl_fetch ${interface_url}${mac}/vswitch-cidr-block)
    local vswitch_id=$(curl_fetch ${interface_url}${mac}/vswitch-id)
    printf "%-30s %-30s %-30s %-30s %-16s %-16s %-16s\n" ${vpc_id} ${vswitch_id} ${network_interface_id} ${mac%/} ${primary_ip_address} ${gateway} ${netmask}
  done
}

function ecs_detect_endpoints() {
  local root_url=${1:-${ECS_META_URL}}
  if curl_available ${root_url}; then
    for resource in $(curl_fetch ${root_url}); do
      if [ "${resource}" = "user-data" ] || [ "${resource}" = "pkcs7" ]; then
        continue
      fi
      if [ "${resource}" = "source-address" ]; then
        echo "${root_url%/}/${resource} = $(curl_fetch ${root_url%/}/${resource})"
      else
        ecs_detect_endpoint ${root_url%/}/${resource}
      fi
    done
  else
    local url=$(dirname ${root_url})
    local data=$(curl_fetch ${url})
    echo "${url} = ${data}"
  fi
}
