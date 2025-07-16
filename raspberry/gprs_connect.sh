#!/bin/bash
#
# gprs_connect.sh — bring up SIM900 PPP link and install host-route

# 1) Kill any old PPP daemons so /dev/serial0 is free
sudo poff -a                       || true
sudo pkill -9 -f pppd             || true
sudo pkill -9 -f chat             || true
sudo rm -f /var/lock/LCK..ttyS0 /var/lock/LCK..serial0

# 2) Start the cellular data link
if ! sudo pon; then
  echo "Connect script failed"
  exit 1
fi

# 3) Wait for ppp0 to appear
sleep 5

# 4) Add a host-route so only the hive-API goes out over ppp0
API_HOST=bees-backend.aiiot.center
API_IP=$(getent ahostsv4 $API_HOST | awk 'NR==1{print $1}')
sudo ip route add $API_IP/32 dev ppp0

echo "✅ ppp0 up; routing $API_HOST → $API_IP over ppp0"
