#!/usr/bin/env bash
# ------------------------------------------------------------------
# stream_tunnel.sh – start libcamera -> ffmpeg -> mjpg-streamer + PageKite
# ------------------------------------------------------------------

set -eEuo pipefail

# If not root, re-exec with sudo so we can open the camera.
(( EUID != 0 )) && exec sudo "$0" "$@"

# ─── paths ───────────────────────────────────────────────────────
BIN="/usr/local/bin/mjpg_streamer"
PLUG_DIR="/usr/local/lib/mjpg-streamer"
WWW_DIR="/home/pi/mjpg-streamer/mjpg-streamer-experimental/www"
LOG_DIR="/home/pi/bees-backend/raspberry/logs"
mkdir -p "$LOG_DIR"
exec >>"$LOG_DIR/stream.log" 2>&1

export LD_LIBRARY_PATH="$PLUG_DIR"

# ─── virtual camera setup ────────────────────────────────────────
if ! ls /dev/video10 &>/dev/null; then
  echo "[INFO] Creating virtual camera on /dev/video10"
  modprobe v4l2loopback devices=1 video_nr=10 card_label="VirtualCam" exclusive_caps=1
  sleep 2
fi

# ─── cleanup ─────────────────────────────────────────────────────
cleanup() {
  echo "[INFO] Stopping all processes …"
  pkill -TERM -f libcamera-vid || true
  pkill -TERM -f ffmpeg || true
  pkill -TERM -x mjpg_streamer || true
  pkill -TERM -f /usr/bin/pagekite || true
}
trap cleanup SIGINT SIGTERM EXIT

# ─── start libcamera → ffmpeg → /dev/video10 ─────────────────────
echo "[INFO] Starting libcamera streaming to virtual camera"
/usr/bin/libcamera-vid -t 0 --width 640 --height 480 --framerate 25 --codec yuv420 --output - | \
/usr/bin/ffmpeg -f rawvideo -pix_fmt yuv420p -s 640x480 -r 25 -i - \
  -c:v mjpeg -f v4l2 /dev/video10 &
STREAM_BRIDGE_PID=$!

sleep 3

# ─── start mjpg-streamer on virtual camera ───────────────────────
echo "[INFO] Starting mjpg-streamer → http://localhost:8080"
"$BIN" \
  -i "input_uvc.so -d /dev/video10 -r 640x480 -f 25" \
  -o "output_http.so -p 8080 -w $WWW_DIR" &
MJPG_PID=$!

sleep 3
if ! kill -0 "$MJPG_PID" 2>/dev/null; then
  echo "[ERROR] mjpg-streamer died on startup; aborting so systemd can retry."
  exit 1
fi

# ─── start PageKite tunnel ───────────────────────────────────────
KITE_HOST="beesscamera.pagekite.me"
echo "[INFO] Opening PageKite       → http://$KITE_HOST/?action=stream"
/usr/bin/pagekite 8080 "$KITE_HOST" &
KITE_PID=$!

# ─── wait for any process to die ─────────────────────────────────
wait -n "$STREAM_BRIDGE_PID" "$MJPG_PID" "$KITE_PID"
echo "[WARN] One of the services exited – letting systemd restart us."
exit 1  # systemd will restart on non-zero
