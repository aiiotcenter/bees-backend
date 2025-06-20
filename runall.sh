#!/usr/bin/env bash
set -eEuo pipefail

# ensure libcamera can find its socket
export XDG_RUNTIME_DIR=/run/user/1000

# 1) start the camera tunnel
/home/pi/bees-backend/raspberry/stream_tunnel.sh &
STREAM_PID=$!

# 2) start your flask app
/home/pi/bees-backend/raspberry/startcore.sh &
FLASK_PID=$!

echo "[INFO] started STREAM=${STREAM_PID}  FLASK=${FLASK_PID}"

cleanup(){
  echo "[STOP ] stopping both…"
  kill "${STREAM_PID}" "${FLASK_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait -n "${STREAM_PID}" "${FLASK_PID}"
echo "[WARN] one died, exiting so systemd can restart"
exit 1
