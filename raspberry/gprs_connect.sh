#!/usr/bin/env bash
set -euo pipefail

# 1) kill any old PPP daemons so /dev/serial0 is free
sudo poff -a 2>/dev/null || true
sudo pkill -9 -f pppd 2>/dev/null || true
sudo pkill -9 -f chat 2>/dev/null || true
sudo rm -f /var/lock/LCK..ttyS0 /var/lock/LCK..serial0 2>/dev/null || true

# 2) start PPP in background
nohup sudo pon >/dev/null 2>&1 &

# 3) wait up to 15s for ppp0 to appear
echo "⏳ Waiting for ppp0…"
for i in $(seq 1 15); do
  if ip link show ppp0 &>/dev/null; then
    echo "✅ ppp0 is up"
    break
  fi
  sleep 1
done

# 4) point resolv.conf at the PPP‑supplied file
sudo ln -sf /etc/ppp/resolv.conf /etc/resolv.conf

# 5) add a host‑route for every A‑record of your API host
API=bees-backend.aiiot.center
echo "🔀 Routing API host via ppp0"
for ip in $(getent ahostsv4 $API | awk '{print $1}' | sort -u); do
  sudo ip route replace $ip/32 dev ppp0
done

echo "--> gprs_connect done"
