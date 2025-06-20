#!/usr/bin/env bash
set -eEo pipefail   # fail on errors, but don’t treat unset vars as fatal

BASE_DIR="/home/pi/bees-backend/raspberry"
VENV_PYTHON="/home/pi/venv/bin/python"
LOG_DIR="${BASE_DIR}/logs"
LOGFILE="${LOG_DIR}/bees.log"

mkdir -p "${LOG_DIR}"
echo "[START] $(date)" >> "${LOGFILE}"

# 1) Kill any old processes
pkill -f libcamera-vid    || true
pkill -f mjpg_streamer    || true
pkill -f pagekite         || true
sleep 2

# 2) Fix libcamera runtime dir
export XDG_RUNTIME_DIR="/run/user/1000"

# 3) Launch the camera stream + tunnel
"${BASE_DIR}/stream_tunnel.sh" >> "${LOGFILE}" 2>&1 &
STREAM_PID=$!

# 4) Launch Flask via the venv’s Python
PYTHONPATH="${BASE_DIR}/sensors/hx711py" \
"${VENV_PYTHON}" "${BASE_DIR}/app.py" >> "${LOGFILE}" 2>&1 &
FLASK_PID=$!

echo "[INFO] started STREAM=${STREAM_PID} FLASK=${FLASK_PID}" >> "${LOGFILE}"

# 5) Wait for either to die, then kill both & exit 1 so systemd restarts
wait -n "${STREAM_PID}" "${FLASK_PID}"
echo "[STOP ] stopping both…" >> "${LOGFILE}"
kill "${STREAM_PID}" "${FLASK_PID}" 2>/dev/null || true
exit 1
