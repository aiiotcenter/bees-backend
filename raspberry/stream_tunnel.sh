#!/usr/bin/env bash
# ------------------------------------------------------------------
# stream_tunnel.sh – start mjpg-streamer (libcamera) + PageKite
# ------------------------------------------------------------------

# ---- paths -------------------------------------------------------
if (( EUID != 0 )); then          # not root? – re-run with sudo
  exec sudo "$0" "$@"
fi

BUILD_DIR="/home/pi/mjpg-streamer/mjpg-streamer-experimental/_build"
WWW_DIR="${BUILD_DIR}/../www"
export LD_LIBRARY_PATH="${BUILD_DIR}/plugins/input_libcamera:${BUILD_DIR}/plugins/output_http"

# ---- streamer command (unchanged) --------------------------------
STREAM_CMD=( "${BUILD_DIR}/mjpg_streamer"
             -i "input_libcamera.so --resolution 640x480 --fps 10"
             -o "output_http.so -p 8080 -w ${WWW_DIR}" )

# ---- tunnel command (was lt … , now PageKite) --------------------
KITE_NAME="beesscamera"               # <subdomain>.pagekite.me
TUNNEL_CMD=( /usr/bin/pagekite 8080 "${KITE_NAME}" )

# ---- helpers -----------------------------------------------------
log() { printf '[%(%F %T)T] %s\n' -1 "$*"; }

cleanup() {                          # Ctrl-C or SIGTERM → kill both procs
  log "Stopping mjpg-streamer & PageKite …"
  pkill -9 -x mjpg_streamer 2>/dev/null || true
  pkill -9 -f /usr/bin/pagekite 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

# ---- main loop ---------------------------------------------------
while true; do
  log "Killing stale processes …"
  pkill -9 -x mjpg_streamer 2>/dev/null || true
  pkill -9 -f /usr/bin/pagekite 2>/dev/null || true

  log "Starting mjpg-streamer …"
  "${STREAM_CMD[@]}" & STREAM_PID=$!
  sleep 3
  if ! kill -0 "$STREAM_PID" 2>/dev/null; then
    log "Streamer died immediately – retry in 5 s"
    sleep 5; continue
  fi

  log "Opening PageKite …"
  "${TUNNEL_CMD[@]}" & KITE_PID=$!

  log "LOCAL  : http://localhost:8080/?action=stream"
  log "PUBLIC : http://${KITE_NAME}.pagekite.me/?action=stream"

  # restart if either process exits
  wait -n "$STREAM_PID" "$KITE_PID"
  log "A service exited – restarting in 5 s"
  kill "$STREAM_PID" "$KITE_PID" 2>/dev/null || true
  sleep 5
done
