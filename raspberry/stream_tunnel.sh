#!/usr/bin/env bash
# stream_tunnel.sh – MJPG-streamer with libcamera + PageKite

set -eEuo pipefail

# 0) Clean up any stray camera users
pkill -f libcamera-vid   || true
pkill -f mjpg_streamer   || true
sleep 2

# 1) Redirect all logs here (world‐writable)
LOGFILE=/var/log/bees-stream.log
exec >>"$LOGFILE" 2>&1

echo "[INFO] ==== STREAM TUNNEL STARTING ===="

# 2) MJPG-streamer using libcamera plugin
echo "[INFO] Starting MJPG-streamer (libcamera) → http://localhost:8080"
export LD_LIBRARY_PATH=/usr/local/lib/mjpg-streamer
mjpg_streamer \
  -i "input_libcamera.so --resolution 640x480 --fps 25" \
  -o "output_http.so -p 8080 -w /home/pi/mjpg-streamer/mjpg-streamer-experimental/www" &
MJPG_PID=$!

sleep 3
if ! kill -0 "$MJPG_PID" 2>/dev/null; then
  echo "[ERROR] MJPG-streamer failed to launch"
  exit 1
fi

# 3) PageKite tunnel
echo "[INFO] Opening PageKite → http://beesscamera.pagekite.me/?action=stream"
pagekite 8080 beesscamera.pagekite.me &
KITE_PID=$!

# 4) Cleanup on exit
cleanup(){
  echo "[INFO] Stopping all child processes…"
  kill "$MJPG_PID" "$KITE_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# 5) Wait for either to exit
wait -n "$MJPG_PID" "$KITE_PID"
echo "[WARN] One component exited, triggering restart"
exit 1
