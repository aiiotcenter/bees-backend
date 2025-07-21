#!/bin/bash
set -e

# 1) clean up any old PPP chatter/locks
sudo poff -a   >/dev/null 2>&1 || true
sudo pkill -9 -f pppd   >/dev/null 2>&1 || true
sudo pkill -9 -f chat   >/dev/null 2>&1 || true
sudo rm -f /var/lock/LCK..ttyS0 /var/lock/LCK..serial0   >/dev/null 2>&1 || true

# 2) dial your provider (uses /etc/ppp/peers/provider)
sudo pon provider

# 3) wait until ppp0 really exists
echo "⏳ Waiting for ppp0…"
while ! ip addr show ppp0 >/dev/null 2>&1; do
  sleep 1
done

# 4) remove any lingering wlan0 default route so PPP truly wins
sudo ip route del default dev wlan0 2>/dev/null || true

echo "✅ PPP0 is up; default now via ppp0"
