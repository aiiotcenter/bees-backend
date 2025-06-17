#!/usr/bin/env bash
# -----------------------------------------------------------
# startcore.sh – launches the Flask backend and the camera
# stream-tunnel, writing everything to one log.
# -----------------------------------------------------------

set -eEuo pipefail

BASE_DIR="/home/pi/bees-backend/raspberry"
VENV_DIR="/home/pi/venv"
LOG_DIR="${BASE_DIR}/logs"
LOGFILE="${LOG_DIR}/bees.log"

mkdir -p "${LOG_DIR}"

echo "[START] $(date)" >> "${LOGFILE}"

# Activate virtual-env
source "${VENV_DIR}/bin/activate"

# Launch Flask app (runs in background)
PYTHONPATH="${BASE_DIR}/sensors/hx711py" \
python  "${BASE_DIR}/app.py"   >> "${LOGFILE}" 2>&1 &

# Launch camera streamer + LocalTunnel (background)
"${BASE_DIR}/stream_tunnel.sh" >> "${LOGFILE}" 2>&1 &

# Wait for both background jobs so systemd sees the service as active
wait
