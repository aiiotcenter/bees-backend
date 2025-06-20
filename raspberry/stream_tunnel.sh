#!/usr/bin/env bash
# stream_tunnel.sh – start MJPG-streamer with libcamera + PageKite
set -eEuo pipefail
(( EUID != 0 )) && exec sudo "$0" "$@"

LOG_DIR=/home/pi/bees-backend/raspberry/logs
WWW_DIR=/home/pi/mjpg-streamer/mjpg-streamer-experimental/www

mkdir -p "$LOG_DIR"
exec >>"$LOG_DIR/stream.log" 2>&1

echo "[INFO] ==== STREAM TUNNEL STARTING ===="

# 1) MJPG-streamer w/ libcamera input
echo "[INFO] Starting MJPG-streamer (libcamera) → http://localhost:8080"
export LD_LIBRARY_PATH=/usr/local/lib/mjpg-streamer
mjpg_streamer \
  -i "input_libcamera.so --width 640 --height 480 --framerate 25" \
  -o "output_http.so -p 8080 -w $WWW_DIR" &
MJPG_PID=$!

sleep 3
if ! kill -0 "$MJPG_PID" 2>/dev/null; then
  echo "[ERROR] MJPG-streamer failed to launch"
  exit 1
fi

# 2) PageKite tunnel
echo "[INFO] Opening PageKite → http://beesscamera.pagekite.me/?action=stream"
pagekite 8080 beesscamera.pagekite.me &
KITE_PID=$!

# 3) Cleanup on exit
cleanup() {
  echo "[INFO] Stopping all child processes…"
  kill "$MJPG_PID" "$KITE_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 4) Wait
wait -n "$MJPG_PID" "$KITE_PID"
echo "[WARN] One component exited, triggering restart"
exit 1
