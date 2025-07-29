#!/usr/bin/env bash
set -eEo pipefail    # exit on any failure, pipefail so any stage failing bubbles up

BASE_DIR="/home/pi/bees-backend/raspberry"
VENV_PYTHON="$BASE_DIR/venv/bin/python"
LOG_DIR="$BASE_DIR/logs"
LOGFILE="$LOG_DIR/bees.log"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Log startup
echo "[START] $(date)" >> "$LOGFILE"

# Launch Flask app with virtual environment
"$VENV_PYTHON" "$BASE_DIR/app.py" >> "$LOGFILE" 2>&1 &
APP_PID=$!

echo "[INFO] Started app (PID=$APP_PID)" >> "$LOGFILE"

# Wait for the app to exit
wait $APP_PID

# Log shutdown and exit with failure so systemd restarts
echo "[STOP] App exited, stopping" >> "$LOGFILE"
exit 1