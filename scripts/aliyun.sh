export ECS_META_URL="http://100.100.100.200/latest"

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
