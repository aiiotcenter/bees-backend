#!/usr/bin/env bash
set -euo pipefail

################################
# 1) Tear down any old PPP     #
################################
sudo poff -a        || true
sudo pkill -9 -f pppd || true
sudo pkill -9 -f chat || true
sudo rm -f /var/lock/LCK..ttyS0 /var/lock/LCK..serial0 || true

################################
# 2) Dial out (in background)  #
################################
sudo pon &

################################
# 3) Wait for ppp0 to come up  #
################################
echo -n "⏳ Waiting for ppp0"
for i in {1..15}; do
  if ip addr show ppp0 | grep -q "inet "; then
    echo " ✅"
    break
  fi
  echo -n "."
  sleep 1
done

################################
# 4) Reset DNS to carrier + CF  #
################################
sudo rm -f /etc/resolv.conf
# link carrier DNS
sudo ln -s /etc/ppp/resolv.conf /etc/resolv.conf
# append public ones
printf "nameserver 1.1.1.1\nnameserver 8.8.8.8\n" \
  | sudo tee -a /etc/resolv.conf >/dev/null

################################
# 5) Flush ALL default routes  #
################################
# this will remove both the wlan0 and any other default
sudo ip route flush default

################################
# 6) Force default → ppp0      #
################################
sudo ip route add default dev ppp0

################################
# 7) Re‑add LAN (wlan0) route  #
################################
# replace the CIDR & src with your actual LAN net & IP
sudo ip route add 10.101.64.0/18 dev wlan0 proto kernel scope link src 10.101.75.176

################################
# 8) (Optional) Pin API IP     #
################################
API_IP=$(getent ahostsv4 http://100.70.97.126:9602 \
         | awk 'NR==1{print $1; exit}')
sudo ip route replace $API_IP/32 dev ppp0

echo "✅ PPP up; default→ppp0; LAN→wlan0; DNS OK"
