export ECS_META_URL="http://100.100.100.200/latest"

function ecs_region() {
  curl -s ${ECS_META_URL}/meta-data/region-id
}

function ecs_zone_id() {
  curl -s ${ECS_META_URL}/meta-data/zone-id
}

function ecs_instance_type() {
  curl -s ${ECS_META_URL}/meta-data/instance/instance-type
}

function ecs_info() {
  curl -s ${ECS_META_URL}/dynamic/instance-identity/document
}

function ecs_uid() {
  curl -s ${ECS_META_URL}/meta-data/owner-account-id
}

function ecs_private_ip() {
  curl -s ${ECS_META_URL}/meta-data/private-ipv4
}

function ecs_public_ip() {
  curl -s ${ECS_META_URL}/meta-data/eipv4
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
  printf "%-30s %-30s %-30s %-30s %-16s %-16s %-16s\n" vpc vswitch eni mac ip gateway netmask
  for mac in $(curl -s ${interface_url}); do
    # gateway
    # netmask
    # network-interface-id
    # primary-ip-address
    # private-ipv4s
    # vpc-cidr-block
    # vpc-id
    # vswitch-cidr-block
    # vswitch-id
    local gateway=$(curl -s ${interface_url}${mac}/gateway)
    local netmask=$(curl -s ${interface_url}${mac}/netmask)
    local network_interface_id=$(curl -s ${interface_url}${mac}/network-interface-id)
    local primary_ip_address=$(curl -s ${interface_url}${mac}/primary-ip-address)
    local private_ipv4s=$(curl -s ${interface_url}${mac}/private-ipv4s)
    local vpc_cidr_block=$(curl -s ${interface_url}${mac}/vpc-cidr-block)
    local vpc_id=$(curl -s ${interface_url}${mac}/vpc-id)
    local vswitch_cidr_block=$(curl -s ${interface_url}${mac}/vswitch-cidr-block)
    local vswitch_id=$(curl -s ${interface_url}${mac}/vswitch-id)
    printf "%-30s %-30s %-30s %-30s %-16s %-16s %-16s\n" ${vpc_id} ${vswitch_id} ${network_interface_id} ${mac%/} ${primary_ip_address} ${gateway} ${netmask}
  done
}
