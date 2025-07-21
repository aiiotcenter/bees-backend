#!/usr/bin/env bash
set -euo pipefail

# 1) shut down any old PPP
sudo poff -a        2>/dev/null || true
sudo pkill -9 -f pppd 2>/dev/null || true
sudo pkill -9 -f chat 2>/dev/null || true
sudo rm -f /var/lock/LCK..ttyS0 /var/lock/LCK..serial0 2>/dev/null || true

# 2) bring the GPRS interface up
echo "⏳ Starting PPP link…"
sudo pon

# 3) wait up to 20 s for ppp0 to appear
for i in $(seq 1 20); do
  if ip addr show ppp0 | grep -q "inet "; then
    echo "✅ ppp0 is up"
    break
  fi
  printf "."
  sleep 1
done

# 4) at this point pppd has already written /etc/ppp/resolv.conf
#    our ip‑up.d hook will have symlinked it to /etc/resolv.conf

# 5) append public fallbacks (optional)
sudo bash -c 'echo "nameserver 1.1.1.1" >> /etc/resolv.conf'
sudo bash -c 'echo "nameserver 8.8.8.8" >> /etc/resolv.conf'

# 6) fix routing
sudo ip route del default dev wlan0   2>/dev/null || true
sudo ip route replace default dev ppp0
sudo ip route replace 10.101.64.0/18 dev wlan0

echo "✅ Routing set: default→ppp0, LAN→wlan0"
echo "---- /etc/resolv.conf ----"
cat /etc/resolv.conf
echo "---- default route ----"
ip route show default
