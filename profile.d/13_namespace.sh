
# Linux Kernel Namespace utility functions
# Note: These functions are for Linux environments and won't work directly on macOS

function ns_get_name_from_id() {
  # Get information about a Linux kernel namespace by its ID
  # Usage: ns_get_name_from_id <namespace_id> [namespace_type]
  local ns_id=$1
  local ns_type=$2
  
  if [ -z "${ns_id}" ]; then
    echo "Usage: ns_get_name_from_id <namespace_id> [namespace_type]"
    echo "  namespace_type: net, pid, mnt, uts, ipc, user, cgroup, time"
    return 1
  fi
  
  # Get basic namespace info
  echo "=== Linux Kernel Namespace Info for ID: ${ns_id} ==="
  lsns -n ${ns_id} -o NS,TYPE,NPROCS,PID,COMMAND
  
  # Find processes using this namespace
  local pid=$(lsns -n ${ns_id} -o PID | tail -n +2 | head -1)
  
  if [ -n "${pid}" ]; then
    echo -e "\n=== Process Info ==="
    ps -p ${pid} -o pid,ppid,user,cmd
    
    # Check namespace links in /proc
    if [ -d "/proc/${pid}/ns" ]; then
      echo -e "\n=== Process Namespace Links ==="
      ls -la /proc/${pid}/ns/
    fi
  fi
  
  # For network namespaces, check if it matches a named one
  if [ "${ns_type}" = "net" ] || [ -z "${ns_type}" ]; then
    echo -e "\n=== Matching Named Network Namespaces ==="
    for netns in $(ip netns list 2>/dev/null); do
      local netns_id=$(readlink /var/run/netns/${netns} 2>/dev/null | grep -o '[0-9]\+')
      if [ "${netns_id}" = "${ns_id}" ]; then
        echo "Network namespace name: ${netns}"
      fi
    done
  fi
}

function ns_get_id_from_name() {
  # Get Linux kernel namespace ID from a name
  # Note: Only network namespaces have persistent names by default
  # Usage: ns_get_id_from_name <namespace_name>
  local ns_name=$1
  
  if [ -z "${ns_name}" ]; then
    echo "Usage: ns_get_id_from_name <namespace_name>"
    return 1
  fi
  
  # Check if this is a network namespace
  if [ -e "/var/run/netns/${ns_name}" ]; then
    echo "=== Linux Network Namespace: ${ns_name} ==="
    local ns_id=$(readlink /var/run/netns/${ns_name} 2>/dev/null | grep -o '[0-9]\+')
    echo "Namespace ID: ${ns_id}"
    
    # Get details using lsns
    if [ -n "${ns_id}" ]; then
      echo -e "\n=== Namespace Details ==="
      lsns -n ${ns_id} -o NS,TYPE,NPROCS,PID,COMMAND
    fi
  else
    echo "No network namespace found with name: ${ns_name}"
    echo "Note: Only network namespaces have persistent names by default"
    echo "Other namespace types are identified by their numeric IDs"
  fi
}

function ns_list() {
  # List all Linux kernel namespaces on the system
  # Usage: ns_list [namespace_type]
  local ns_type=$1
  
  if [ -n "${ns_type}" ]; then
    echo "=== Linux Kernel Namespaces (Type: ${ns_type}) ==="
    lsns -t ${ns_type} -o NS,TYPE,NPROCS,PID,COMMAND
  else
    echo "=== All Linux Kernel Namespaces ==="
    lsns -o NS,TYPE,NPROCS,PID,COMMAND
  fi
}

function ns_info() {
  # Show information about Linux kernel namespaces for a specific process
  # Usage: ns_info <pid>
  local pid=$1
  
  if [ -z "${pid}" ]; then
    echo "Usage: ns_info <pid>"
    return 1
  fi
  
  if [ ! -d "/proc/${pid}" ]; then
    echo "Process ${pid} not found"
    return 1
  fi
  
  echo "=== Linux Kernel Namespaces for PID ${pid} ==="
  
  if [ -d "/proc/${pid}/ns" ]; then
    echo -e "\n=== Namespace Links ==="
    ls -la /proc/${pid}/ns/
    
    echo -e "\n=== Namespace Details ==="
    for ns_type in $(ls /proc/${pid}/ns/); do
      local ns_id=$(readlink /proc/${pid}/ns/${ns_type} | grep -o '[0-9]\+')
      echo "${ns_type}: ${ns_id}"
    done
  else
    echo "No namespace information available for PID ${pid}"
  fi
}
