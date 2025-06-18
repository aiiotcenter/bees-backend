#!/usr/bin/env bash
# ------------------------------------------------------------------
# stream_kite.sh – start mjpg-streamer (libcamera) + PageKite tunnel
# ------------------------------------------------------------------
#  ▸ Exposes http://<KITE_NAME>.pagekite.me/?action=stream
#  ▸ Restarts automatically if either process crashes
# ------------------------------------------------------------------

set -eEuo pipefail
if (( EUID != 0 )); then exec sudo "$0" "$@"; fi   # re-exec as root

# ──── USER SETTINGS ───────────────────────────────────────────────
KITE_NAME="beesscamera"          # your sub-domain on PageKite.net
KITE_PORT=8080              # local port we’ll expose
PAGEKITE_BIN="/usr/bin/pagekite"  # adjust if it’s called pagekite.py

# ──── PATHS ───────────────────────────────────────────────────────
BUILD_DIR="/home/pi/mjpg-streamer/mjpg-streamer-experimental/_build"
WWW_DIR="${BUILD_DIR}/../www"
export LD_LIBRARY_PATH="${BUILD_DIR}/plugins/input_libcamera:${BUILD_DIR}/plugins/output_http"

# ──── COMMAND ARRAYS ──────────────────────────────────────────────
STREAM_CMD=(
  "${BUILD_DIR}/mjpg_streamer"
  -i "input_libcamera.so --resolution 640x480 --fps 10"
  -o "output_http.so -p ${KITE_PORT} -w ${WWW_DIR}"
)

TUNNEL_CMD=(
  "${PAGEKITE_BIN}"
  "${KITE_PORT}"
  "${KITE_NAME}"            # becomes <KITE_NAME>.pagekite.me
)

# ──── HELPERS ─────────────────────────────────────────────────────
log() { printf '[%(%F %T)T] %s\n' -1 "$*"; }

cleanup() {
  log "Stopping mjpg-streamer & PageKite …"
  pkill -9 -x mjpg_streamer 2>/dev/null || true
  pkill -9 -f "${PAGEKITE_BIN}" 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

# ──── MAIN LOOP ───────────────────────────────────────────────────
while true; do
  log "Killing stale processes …"
  pkill -9 -x mjpg_streamer 2>/dev/null || true
  pkill -9 -f "${PAGEKITE_BIN}" 2>/dev/null || true

  log "Starting mjpg-streamer …"
  "${STREAM_CMD[@]}" & STREAM_PID=$!
  sleep 3
  if ! kill -0 "$STREAM_PID" 2>/dev/null; then
    log "Streamer died immediately – retrying in 5 s"
    sleep 5; continue
  fi

  log "Opening PageKite …"
  "${TUNNEL_CMD[@]}" & KITE_PID=$!

  log "LOCAL  : http://localhost:${KITE_PORT}/?action=stream"
  log "PUBLIC : http://${KITE_NAME}.pagekite.me/?action=stream"

  # restart if either process exits
  wait -n "$STREAM_PID" "$KITE_PID"
  log "A service exited – restarting in 5 s"
  kill "$STREAM_PID" "$KITE_PID" 2>/dev/null || true
  sleep 5
done
