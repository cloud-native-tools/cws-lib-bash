######################
# Become a Certificate Authority
######################

CA_DAYS=$((365 * 3))
CA_SUBJ="/C=CN/ST=ZHEJIANG/L=HANGZHOU/O=CWS/OU=IT/CN=www.cws.com"

function openssl_create_ca() {
  local name=${1}
  if [ -n "${name}" ]; then
    openssl genrsa -des3 -out ${name}.key 2048
    openssl req -x509 -new -nodes -key ${name}.key -sha256 -days ${CA_DAYS} -out ${name}.pem -subj "${CA_SUBJ}"
    log "CA ${name}: ${name}.key ${name}.pem"
  else
    log warn "Usage: openssl_create_ca {ca_name}"
  fi
}

function openssl_create_ca_signed_cert() {
  local name=${1}
  local ca_key=${2}
  local ca_cert=${3}

  if [ -z "${name}" -o -z "${ca_key}" -o -z "${ca_cert}" ]; then
    log warn "Usage: openssl_create_ca_signed_cert {name} {ca_key} {ca_cert} -- DNS IP ..."
  else
    openssl genrsa -out ${name}.key 2048
    openssl req -new -key ${name}.key -out ${name}.csr -subj "${CA_SUBJ}"
    cat >${name}.ext <<-EOF
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment
subjectAltName = @alt_names
[alt_names]
EOF
    shift
    shift
    shift
    ip_index=1
    dns_index=1
    for addr in $@; do
      if [ "$(net_is_ip ${addr})" = "true" ]; then
        log plain "IP.${ip_index} = ${addr}" >>${name}.ext
      else
        log plain "DNS.${dns_index} = ${addr}" >>${name}.ext
      fi
    done

    openssl x509 -req -in ${name}.csr -CA ${ca_cert} -CAkey ${ca_key} -CAcreateserial -out ${name}.crt -days ${CA_DAYS} -sha256 -extfile ${name}.ext
  fi
}

function openssl_view_crt() {
  local crt_file=${1}
  if [ -z "${crt_file}" ]; then
    log warn "Usage: openssl_view_crt {crt_file}"
  else
    openssl x509 -in ${crt_file}  
  fi
}
