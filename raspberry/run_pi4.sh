#!/usr/bin/env bash
set -eEo pipefail    # exit on any failure, pipefail so any stage failing bubbles up

BASE_DIR="/home/pi/bees-backend/raspberry"
VENV_PYTHON="$BASE_DIR/venv/bin/python"
LOG_DIR="$BASE_DIR/logs"
LOGFILE="$LOG_DIR/bees.log"

mkdir -p "$LOG_DIR"
echo "[START] $(date)" >> "$LOGFILE"

# 1) Tear down any old pppd/chat so /dev/ttyUSB* is free
pkill -f pppd    || true
pkill -f chat    || true
sleep 2

# 2) Bring up your USB mobile‐broadband via pppd (provider should be set up)
pon provider     || true
sleep 10         # give it time to get IP + DNS

# 3) Log network state
{
  echo "[NETWORK] $(date)"
  ip addr show ppp0
  echo "ROUTE:"
  ip route show default
  echo "RESOLV.CONF:"
  cat /etc/resolv.conf
} >> "$LOGFILE" 2>&1

# 4) Launch your Flask app
"$VENV_PYTHON" "$BASE_DIR/app.py" >> "$LOGFILE" 2>&1 &
APP_PID=$!
echo "[INFO] Started app (PID=$APP_PID)" >> "$LOGFILE"

# 5) If it ever exits, tear down and exit so systemd restarts us
wait $APP_PID
echo "[STOP] App exited, stopping" >> "$LOGFILE"
exit 1
