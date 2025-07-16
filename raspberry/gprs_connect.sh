#!/bin/bash
#
# gprs_connect.sh — start SIM900 PPP in background, add host‐route.

# 1) Kill any old PPP daemons so /dev/serial0 is free
sudo poff -a                    || true
sudo pkill -9 -f pppd           || true
sudo pkill -9 -f chat           || true
sudo rm -f /var/lock/LCK..ttyS0 /var/lock/LCK..serial0 || true

# 2) Start cellular link in background
nohup sudo pon > /dev/null 2>&1 &

# 3) Give it time to settle & assign ppp0
sleep 8

# 4) Add host‐route for your API
API_HOST=bees-backend.aiiot.center
API_IP=$(getent ahostsv4 $API_HOST | awk 'NR==1{print $1}')
sudo ip route add $API_IP/32 dev ppp0

echo "✅ ppp0 up; routing $API_HOST → $API_IP over ppp0"
