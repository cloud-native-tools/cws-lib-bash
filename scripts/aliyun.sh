export ECS_META_URL="http://100.100.100.200/latest"

# Retrieves the VPC ID of the current ECS instance
function ecs_vpc_id() {
  curl_fetch ${ECS_META_URL}/meta-data/vpc-id
}

# Retrieves the vSwitch ID of the current ECS instance
function ecs_vswitch_id() {
  curl_fetch ${ECS_META_URL}/meta-data/vswitch-id
}

# Gets the region ID of the current ECS instance
function ecs_region() {
  curl_fetch ${ECS_META_URL}/meta-data/region-id
}

# Gets the zone ID of the current ECS instance
function ecs_zone_id() {
  curl_fetch ${ECS_META_URL}/meta-data/zone-id
}

# Retrieves the instance type of the current ECS instance
function ecs_instance_type() {
  curl_fetch ${ECS_META_URL}/meta-data/instance/instance-type
}

# Gets detailed instance identity information in JSON format
function ecs_info() {
  curl_fetch ${ECS_META_URL}/dynamic/instance-identity/document
}

# Gets the Alibaba Cloud user ID that owns the current instance
function ecs_uid() {
  curl_fetch ${ECS_META_URL}/meta-data/owner-account-id
}

# Gets the private IPv4 address of the current instance
function ecs_private_ip() {
  curl_fetch ${ECS_META_URL}/meta-data/private-ipv4
}

# Gets the public/elastic IPv4 address of the current instance
function ecs_public_ip() {
  curl_fetch ${ECS_META_URL}/meta-data/eipv4
}

# Gets the path to cloud-init instance data
function ecs_cloud_init_path() {
  readlink -f /var/lib/cloud/instance
}

# Displays the user data provided during instance creation
function ecs_cloud_init_user_data() {
  cat $(ecs_cloud_init_path)/user-data.txt
}

# Shows cloud-init output logs
function ecs_cloud_init_output() {
  cat /var/log/cloud-init-output.log
}

# Displays cloud-init logs
function ecs_cloud_init_log() {
  cat /var/log/cloud-init.log
}

# Checks if the current environment is running in Alibaba Cloud
function ecs_in_aliyun() {
  if curl_test_server ${ECS_META_URL}; then
    return ${RETURN_SUCCESS}
  else
    return ${RETURN_FAILURE}
  fi
}

# Lists all network interfaces and their details
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

# Recursively explores and prints all available metadata endpoints
function ecs_detect_endpoints() {
  local root_url=${1:-${ECS_META_URL}}
  if curl_available ${root_url}; then
    for resource in $(curl_fetch ${root_url}); do
      if [ "${resource}" = "user-data" ] || [ "${resource}" = "pkcs7" ]; then
        continue
      fi
      if [ "${resource}" = "source-address" ] || [ "${resource}" = "vpc-cidr-block" ] || [ "${resource}" = "vswitch-cidr-block" ]; then
        echo "${root_url%/}/${resource} = $(curl_fetch ${root_url%/}/${resource})"
      else
        ecs_detect_endpoints ${root_url%/}/${resource}
      fi
    done
  else
    echo "$(dirname ${root_url}) = $(basename ${root_url})"
  fi
}
