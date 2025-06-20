#!/usr/bin/env bash
set -eEo pipefail   # fail on errors, but don’t treat unset vars as fatal

BASE_DIR="/home/pi/bees-backend/raspberry"
VENV_DIR="/home/pi/venv"
LOG_DIR="${BASE_DIR}/logs"
LOGFILE="${LOG_DIR}/bees.log"

mkdir -p "${LOG_DIR}"
echo "[START] $(date)" >> "${LOGFILE}"

# 1) Cleanup any stray processes
pkill -f libcamera-vid    || true
pkill -f mjpg_streamer    || true
pkill -f pagekite         || true
sleep 2

# 2) Set libcamera runtime dir
export XDG_RUNTIME_DIR="/run/user/1000"

# 3) Activate your Python venv (temporarily disable "-u" so activate won’t error)
set +u
source "${VENV_DIR}/bin/activate"
set -u

# 4) Launch the camera stream tunnel
"${BASE_DIR}/stream_tunnel.sh" >> "${LOGFILE}" 2>&1 &
STREAM_PID=$!

# 5) Launch your Flask app
PYTHONPATH="${BASE_DIR}/sensors/hx711py" \
python "${BASE_DIR}/app.py" >> "${LOGFILE}" 2>&1 &
FLASK_PID=$!

echo "[INFO] started STREAM=${STREAM_PID} FLASK=${FLASK_PID}" >> "${LOGFILE}"

# 6) Wait for either to exit and then kill both
wait -n "${STREAM_PID}" "${FLASK_PID}"
echo "[STOP ] stopping both…" >> "${LOGFILE}"
kill "${STREAM_PID}" "${FLASK_PID}" 2>/dev/null || true
exit 1
