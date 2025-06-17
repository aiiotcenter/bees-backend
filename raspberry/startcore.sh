#!/usr/bin/env bash
set -eEuo pipefail

BASE_DIR="/home/pi/bees-backend/raspberry"
VENV_DIR="/home/pi/venv"
LOG_DIR="${BASE_DIR}/logs"
LOGFILE="${LOG_DIR}/bees.log"

mkdir -p "${LOG_DIR}"
echo "[START] $(date)" >> "${LOGFILE}"

# activate venv
source "${VENV_DIR}/bin/activate"

# start Flask app in the background
PYTHONPATH="${BASE_DIR}/sensors/hx711py" \
python "${BASE_DIR}/app.py" >> "${LOGFILE}" 2>&1 &

# now replace the shell with stream_tunnel.sh  (NO trailing &)
exec "${BASE_DIR}/stream_tunnel.sh" >> "${LOGFILE}" 2>&1
