#!/usr/bin/env bash
set -eEuo pipefail

BASE_DIR="/home/pi/bees-backend/raspberry"
VENV_DIR="/home/pi/venv"
LOG_DIR="${BASE_DIR}/logs"
LOGFILE="${LOG_DIR}/bees.log"

mkdir -p "${LOG_DIR}"
# send everything to the log
exec >>"${LOGFILE}" 2>&1

echo "[START] $(date)"

# ─── Activate the venv safely ────────────────────────────────
if [[ -f "${VENV_DIR}/bin/activate" ]]; then
  set +u
  # shellcheck source=/home/pi/venv/bin/activate
  source "${VENV_DIR}/bin/activate"
  set -u
else
  echo "[ERROR] virtualenv missing at ${VENV_DIR}"
  exit 1
fi

echo "[INFO] venv activated, launching Flask…"
export PYTHONPATH="${BASE_DIR}/sensors/hx711py"
/home/pi/venv/bin/python -u "${BASE_DIR}/app.py" &
FLASK_PID=$!
echo "[INFO] Flask PID=${FLASK_PID}"

# on exit, clean it up
cleanup(){
  echo "[STOP ] $(date) killing Flask PID=${FLASK_PID}"
  kill "${FLASK_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait "${FLASK_PID}"
