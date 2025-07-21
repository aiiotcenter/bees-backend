#!/usr/bin/env bash
set -euo pipefail

# teardown
sudo poff -a 2>/dev/null || true
sudo pkill -9 -f pppd 2>/dev/null || true
sudo pkill -9 -f chat 2>/dev/null || true
sudo rm -f /var/lock/LCK..ttyS0 /var/lock/LCK..serial0 2>/dev/null || true

# start PPP
nohup sudo pon >/dev/null 2>&1 &

# wait for ppp0
for i in $(seq 1 20); do
  ip addr show ppp0 | grep -q "inet " && break
  sleep 1
done

# at this point /etc/resolv.conf has been replaced by our ip‑up.d hook

# now append public fallbacks
sudo bash -c 'echo "nameserver 1.1.1.1" >> /etc/resolv.conf'
sudo bash -c 'echo "nameserver 8.8.8.8" >> /etc/resolv.conf'

# fix routes
sudo ip route del default dev wlan0 2>/dev/null || true
sudo ip route replace default dev ppp0
sudo ip route replace 10.101.64.0/18 dev wlan0

echo "✅ PPP0 up, DNS & routing set."
