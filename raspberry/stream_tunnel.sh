#!/usr/bin/env bash
# stream_tunnel.sh – start MJPG-streamer with libcamera + PageKite

# Kill any leftover camera or tunnel processes to free the device\pkill -f libcamera-vid    || true
pkill -f mjpg_streamer    || true
pkill -f input_libcamera  || true
pkill -f pagekite         || true
sleep 2

set -eEuo pipefail

# Log to a world-writable location
LOGFILE=/var/log/bees-stream.log
exec >>"$LOGFILE" 2>&1

echo "[INFO] ==== STREAM TUNNEL STARTING ===="

# 1) MJPG-streamer using libcamera input plugin
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

# 4) Wait for any to exit
wait -n "$MJPG_PID" "$KITE_PID"
echo "[WARN] One component exited, triggering restart"
exit 1
