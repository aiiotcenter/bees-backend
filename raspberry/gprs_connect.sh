#!/usr/bin/env bash
set -euo pipefail

# 1) Kill any old PPP daemons & free /dev/serial0
sudo poff -a    2>/dev/null || true
sudo pkill -9 -f pppd  2>/dev/null || true
sudo pkill -9 -f chat  2>/dev/null || true
sudo rm -f /var/lock/LCK..ttyS0 /var/lock/LCK..serial0 2>/dev/null || true

# 2) Start pppd in background
nohup sudo pon >/dev/null 2>&1 &

# 3) Wait for ppp0 to get an IP (20s max)
echo "⏳ Waiting for ppp0…"
for i in $(seq 1 20); do
  if ip addr show ppp0 | grep -q "inet "; then
    echo "✅ ppp0 is up"
    break
  fi
  sleep 1
done

# 4) Repoint DNS, then append public fallback
sudo ln -sf /etc/ppp/resolv.conf /etc/resolv.conf
echo 'nameserver 1.1.1.1' | sudo tee -a /etc/resolv.conf
echo 'nameserver 8.8.8.8' | sudo tee -a /etc/resolv.conf

# 5) Make ppp0 the default, but keep LAN traffic local
sudo ip route del default dev wlan0 2>/dev/null || true
sudo ip route replace default dev ppp0
sudo ip route replace 10.101.64.0/18 dev wlan0

echo "🎉 ppp0 is now default; LAN pinned to wlan0"
