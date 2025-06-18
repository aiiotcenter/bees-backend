#!/usr/bin/env bash
# ------------------------------------------------------------------
# stream_tunnel.sh – start mjpg-streamer (libcamera) + LocalTunnel
# ------------------------------------------------------------------

set -eEuo pipefail        # stop on any error, treat unset vars as errors
if (( EUID != 0 )); then  # re-exec as root so pkill/buffers always work
  exec sudo "$0" "$@"
fi

# ---- paths -------------------------------------------------------
BUILD_DIR="/home/pi/mjpg-streamer/mjpg-streamer-experimental/_build"
WWW_DIR="${BUILD_DIR}/../www"
export LD_LIBRARY_PATH="${BUILD_DIR}/plugins/input_libcamera:${BUILD_DIR}/plugins/output_http"

# ---- commands ----------------------------------------------------
STREAM_CMD=( "${BUILD_DIR}/mjpg_streamer"
             -i "input_libcamera.so --resolution 640x480 --fps 10"   # 1 buffer = default
             -o "output_http.so -p 8080 -w ${WWW_DIR}" )

TUNNEL_CMD=( lt --port 8080 --subdomain camera --local-host 127.0.0.1 )

# ---- helpers -----------------------------------------------------
log() { printf '[%(%F %T)T] %s\n' -1 "$*"; }

cleanup() {                # Ctrl-C or SIGTERM → kill both procs
  log "Stopping mjpg-streamer & LocalTunnel …"
  pkill -9 -x mjpg_streamer 2>/dev/null || true
  pkill -9 -x lt            2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

# ---- main loop ---------------------------------------------------
while true; do
  log "Killing stale processes …"
  pkill -9 -x mjpg_streamer lt 2>/dev/null || true

  log "Starting mjpg-streamer …"
  "${STREAM_CMD[@]}" &  STREAM_PID=$!
  sleep 3
  if ! kill -0 "$STREAM_PID" 2>/dev/null; then
    log "Streamer died immediately – retry in 5 s"
    sleep 5
    continue
  fi

  log "Opening LocalTunnel …"
  "${TUNNEL_CMD[@]}" &  LT_PID=$!

  log "LOCAL  : http://localhost:8080/?action=stream"
  log "PUBLIC : http://camera.loca.lt/?action=stream"

  # restart if either process exits
  wait -n "$STREAM_PID" "$LT_PID"
  log "A service exited – restarting in 5 s"
  kill "$STREAM_PID" "$LT_PID" 2>/dev/null || true
  sleep 5
done