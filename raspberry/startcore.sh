#!/usr/bin/env bash
set -eEuo pipefail

BASE_DIR="/home/pi/bees-backend/raspberry"
VENV_DIR="/home/pi/venv"
LOG_DIR="${BASE_DIR}/logs"
LOGFILE="${LOG_DIR}/bees.log"

mkdir -p "${LOG_DIR}"
# Redirect *all* stdout/stderr into the log:
exec >>"${LOGFILE}" 2>&1

echo "[START] $(date)"

# ─── Activate the virtualenv ─────────────────────────────────────
if [[ -f "${VENV_DIR}/bin/activate" ]]; then
  # disable -u so that activate can set things up
  set +u
  # shellcheck source=/home/pi/venv/bin/activate
  source "${VENV_DIR}/bin/activate"
  set -u
else
  echo "[ERROR] Virtualenv not found at ${VENV_DIR}"
  exit 1
fi

# ─── Start your Flask app ────────────────────────────────────────
export PYTHONPATH="${BASE_DIR}/sensors/hx711py"
# use the venv’s python, and force unbuffered output (-u) so logs are immediate
"${VENV_DIR}/bin/python" -u "${BASE_DIR}/app.py" &
FLASK_PID=$!
echo "[INFO] Flask app started as PID ${FLASK_PID}"

# ─── Ensure we clean up if this script ever exits ────────────────
cleanup() {
  echo "[STOP ] $(date)  Killing Flask (PID ${FLASK_PID})"
  kill "${FLASK_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# ─── Wait for the Flask process (so the script doesn’t exit) ────
wait "${FLASK_PID}"
