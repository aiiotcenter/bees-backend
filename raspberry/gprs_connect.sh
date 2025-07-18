#!/bin/bash
set +m

# 1) kill any old PPP so /dev/serial0 frees
sudo poff -a                 >/dev/null 2>&1 || true
sudo pkill -9 -f pppd        >/dev/null 2>&1 || true
sudo pkill -9 -f chat        >/dev/null 2>&1 || true
sudo rm -f /var/lock/LCK..ttyS0 /var/lock/LCK..serial0 >/dev/null 2>&1

# 2) start pppd in background
nohup sudo pon >/dev/null 2>&1 &

# 3) wait for ppp0
sleep 8

# 4) link resolv.conf so you get provider + public DNS
sudo ln -sf /etc/ppp/resolv.conf /etc/resolv.conf

# 5) install a host-route for every API A‑record
API_HOST=bees-backend.aiiot.center
for IP in $(getent ahostsv4 $API_HOST | awk '{print $1}' | sort -u); do
  sudo ip route add $IP/32 dev ppp0 || true
done

echo "✅ ppp0 up; host‑routed $API_HOST → $(getent ahostsv4 $API_HOST | awk '{print $1}' | paste -sd, -) over ppp0"
