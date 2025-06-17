#!/usr/bin/env bash
# ------------------------------------------------------------------
# stream_tunnel.sh
# ------------------------------------------------------------------
# • Starts mjpg-streamer (libcamera plugin) on a Pi Zero
# • Exposes the stream through LocalTunnel on sub-domain “camera”
# • Restarts both services if either one crashes
# • Accepts alternate mjpg-streamer options after “--”
#
#   sudo ./stream_tunnel.sh                       # default run
#   sudo ./stream_tunnel.sh -- -i "input_libcamera.so --resolution 320x240" ...
# ------------------------------------------------------------------

set -eEuo pipefail

# --- require root --------------------------------------------------
if (( EUID != 0 )); then
  echo "[ERROR] Please run as root: sudo $0" >&2
  exit 1
fi

# --- paths ---------------------------------------------------------
BUILD_DIR="/home/pi/mjpg-streamer/mjpg-streamer-experimental/_build"
WWW_DIR="${BUILD_DIR}/../www"
export LD_LIBRARY_PATH="${BUILD_DIR}/plugins/input_libcamera:${BUILD_DIR}/plugins/output_http"

# --- default mjpg-streamer command (1 buffer to save RAM) ----------
STREAM_CMD=( "${BUILD_DIR}/mjpg_streamer"
             -i "input_libcamera.so --resolution 640x480 --fps 10"
             -o "output_http.so -p 8080 -w ${WWW_DIR}" )

# --- allow overrides after "--" ------------------------------------
if [[ $# -gt 0 && $1 == "--" ]]; then
  shift
  STREAM_CMD=( "${BUILD_DIR}/mjpg_streamer" "$@" )
fi

TUNNEL_CMD=( lt --port 8080 --subdomain camera --local-host 127.0.0.1 )

log() { printf '[%(%Y-%m-%d %H:%M:%S)T] %s\n' -1 "$*"; }

# --- cleanup -------------------------------------------------------
cleanup() {
  log "Stopping mjpg-streamer and LocalTunnel …"
  pkill -9 -x mjpg_streamer 2>/dev/null || true
  pkill -9 -x lt            2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

# --- kill stray processes from previous runs ----------------------
log "Killing any stale processes …"
pkill -9 -x mjpg_streamer 2>/dev/null || true
pkill -9 -x lt            2>/dev/null || true

# --- main loop -----------------------------------------------------
while true; do
  log "Starting mjpg-streamer …"
  "${STREAM_CMD[@]}" & STREAM_PID=$!

  # give streamer a moment; restart if it exits too soon (e.g. ENOMEM)
  sleep 3
  if ! kill -0 "$STREAM_PID" 2>/dev/null; then
    log "mjpg-streamer died immediately – retrying in 5 s …"
    sleep 5
    continue
  fi

  log "Opening LocalTunnel …"
  "${TUNNEL_CMD[@]}" & LT_PID=$!

  log "LOCAL  : http://localhost:8080/?action=stream"
  log "PUBLIC : http://camera.loca.lt/?action=stream"

  # restart loop if either service dies
  wait -n "$STREAM_PID" "$LT_PID"
  log "A service exited – restarting in 5 s …"
  kill "$STREAM_PID" "$LT_PID" 2>/dev/null || true
  sleep 5
done
