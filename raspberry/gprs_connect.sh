#!/usr/bin/env bash
set -euo pipefail

# 1) Kill any old PPP so /dev/ttyS0 frees up
sudo poff -a    2>/dev/null || true
sudo pkill -9 -f pppd  2>/dev/null || true
sudo pkill -9 -f chat  2>/dev/null || true
sudo rm -f /var/lock/LCK..ttyS0 /var/lock/LCK..serial0 2>/dev/null || true

# 2) Launch pon in background
nohup sudo pon >/dev/null 2>&1 &

# 3) Wait up to 20s for ppp0 to get an address
echo "⏳ Waiting for ppp0 to have an IP…"
for i in $(seq 1 20); do
  if ip addr show ppp0 | grep -q "inet "; then
    echo "✅ ppp0 is up with IP"
    break
  fi
  sleep 1
done

# 4) Rewrite resolv.conf to use carrier+public DNS
sudo ln -sf /etc/ppp/resolv.conf /etc/resolv.conf

# 5) Yank off the old default via wlan0, make ppp0 your default
sudo ip route del default dev wlan0 2>/dev/null || true
sudo ip route replace default dev ppp0

# 6) Still keep your LAN on wlan0 for 10.101.64.0/18
sudo ip route replace 10.101.64.0/18 dev wlan0

echo "🎉 ppp0 is now your default, LAN stays on wlan0"
