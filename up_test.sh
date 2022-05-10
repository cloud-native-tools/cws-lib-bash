#!/bin/bash

hosts="master node1 node2 vnode1 vnode2"
for host in ${hosts}
do
  scp profile.d/* scripts/* ${host}:/etc/profile.d
done
