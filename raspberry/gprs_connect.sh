#!/usr/bin/env bash
set -euo pipefail

# 1) kill any old PPP daemons
sudo poff -a       2>/dev/null || true
sudo pkill -9 -f pppd 2>/dev/null || true
sudo pkill -9 -f chat 2>/dev/null || true
sudo rm -f /var/lock/LCK..ttyS0 /var/lock/LCK..serial0 2>/dev/null || true

# 2) fire off pon in background
nohup sudo pon >/dev/null 2>&1 &

# 3) wait up to 20s for ppp0 to get an IP
printf "⏳ Waiting for ppp0…"
for i in $(seq 1 20); do
  if ip addr show ppp0 | grep -q "inet "; then
    echo " ✅"
    break
  fi
  printf "."
  sleep 1
done

# 4) rebuild resolv.conf (carrier DNS + public fallbacks)
sudo bash -c 'cat /etc/ppp/resolv.conf > /etc/resolv.conf'
sudo bash -c 'echo "nameserver 1.1.1.1" >> /etc/resolv.conf'
sudo bash -c 'echo "nameserver 8.8.8.8" >> /etc/resolv.conf'

# 5) flip default to ppp0, keep LAN on wlan0
sudo ip route del default dev wlan0    2>/dev/null || true
sudo ip route replace default dev ppp0
sudo ip route replace 10.101.64.0/18 dev wlan0

echo "🎉 ppp0 is now default; LAN still on wlan0"
echo "---- /etc/resolv.conf ----"
cat /etc/resolv.conf
echo "---- default route ----"
ip route show default
