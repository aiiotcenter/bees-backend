#!/bin/bash
# 1) kill any old PPP so /dev/serial0 is free
sudo poff -a                      || true
sudo pkill -9 -f pppd            || true
sudo pkill -9 -f chat            || true
sudo rm -f /var/lock/LCK..ttyS0 /var/lock/LCK..serial0 || true

# 2) start the cellular data link\ nif ! sudo pon; then
    echo "Connect script failed"
    exit 1
fi
sleep 5

# 3) add host-route for your API
API_HOST=bees-backend.aiiot.center
API_IP=$(getent ahostsv4 $API_HOST | awk 'NR==1{print $1}')
sudo ip route add $API_IP/32 dev ppp0

echo "✅ ppp0 up; routing $API_HOST → $API_IP over ppp0"