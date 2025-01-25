#!/bin/bash

# Set ONOS REST API details
ONOS_IP="127.0.0.1"
ONOS_PORT="8181"
ONOS_USER="onos"
ONOS_PASS="rocks"

# Get the list of hosts
HOSTS=$(curl -u ${ONOS_USER}:${ONOS_PASS} -s http://${ONOS_IP}:${ONOS_PORT}/onos/v1/hosts)

echo $HOSTS

# Loop through each host and remove it
for HOST_ID in $(echo $HOSTS | jq -r '.hosts[].id'); do
    curl -u ${ONOS_USER}:${ONOS_PASS} -X DELETE http://${ONOS_IP}:${ONOS_PORT}/onos/v1/hosts/${HOST_ID}
done

HOSTS=$(curl -u ${ONOS_USER}:${ONOS_PASS} -s http://${ONOS_IP}:${ONOS_PORT}/onos/v1/hosts)

echo $HOSTS
