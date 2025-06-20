#!/usr/bin/env bash
# ------------------------------------------------------------------
# stream_tunnel.sh – Pi camera ➜ v4l2loopback ➜ MJPEG-streamer ➜ PageKite
# ------------------------------------------------------------------
set -eEuo pipefail
((EUID != 0)) && exec sudo "$0" "$@"

# ─── Paths ────────────────────────────────────────────────────────
BIN_MJPG="/usr/local/bin/mjpg_streamer"
PLUG_DIR="/usr/local/lib/mjpg-streamer"          # after `sudo make install`
WWW_DIR="/home/pi/mjpg-streamer/mjpg-streamer-experimental/www"
LOG_DIR="/home/pi/bees-backend/raspberry/logs"
mkdir -p "$LOG_DIR"
exec >>"$LOG_DIR/stream.log" 2>&1
export LD_LIBRARY_PATH="$PLUG_DIR"

# ─── Loopback setup (write: /dev/video98, read: /dev/video99) ─────
echo "[INFO] Setting up v4l2loopback (98=out, 99=in)…"
modprobe -r v4l2loopback 2>/dev/null || true
modprobe v4l2loopback devices=2 video_nr=98,99 card_label="VL_Out,VL_In" \
         max_buffers=4 exclusive_caps=1                             # 98-out, 99-in
sleep 2

# ─── Clean-up handler ─────────────────────────────────────────────
cleanup() {
  echo "[INFO] Stopping all processes…"
  pkill -f libcamera-vid      2>/dev/null || true
  pkill -f ffmpeg             2>/dev/null || true
  pkill -x mjpg_streamer      2>/dev/null || true
  pkill -f /usr/bin/pagekite  2>/dev/null || true
}
trap cleanup SIGINT SIGTERM EXIT

# ─── Camera ➜ FFmpeg ➜ /dev/video98 (YUYV) ────────────────────────
echo "[INFO] Starting camera → /dev/video98 pipe"
libcamera-vid -t 0 --width 640 --height 480 --framerate 25 --codec yuv420 --output - | \
ffmpeg -loglevel warning \
       -f rawvideo  -pix_fmt yuv420p  -s 640x480 -r 25 -i - \
       -pix_fmt yuyv422 -f v4l2 /dev/video98 &
PIPE_PID=$!

sleep 3
if ! kill -0 "$PIPE_PID" 2>/dev/null; then
  echo "[ERROR] Camera pipe died; aborting so systemd can retry."
  exit 1
fi

# ─── MJPEG-streamer reading /dev/video99 (READ I/O) ───────────────
echo "[INFO] Starting MJPEG-streamer on /dev/video99 → http://localhost:8080"
"$BIN_MJPG" \
  -i "input_uvc.so -d /dev/video99 -r 640x480 -f 25 -y -m 1" \
  -o "output_http.so -p 8080 -w $WWW_DIR" &
MJPG_PID=$!

sleep 3
if ! kill -0 "$MJPG_PID" 2>/dev/null; then
  echo "[ERROR] MJPEG-streamer died; aborting so systemd can retry."
  exit 1
fi

# ─── PageKite tunnel ──────────────────────────────────────────────
KITE_HOST="beesscamera.pagekite.me"
echo "[INFO] Opening PageKite → http://$KITE_HOST/?action=stream"
/usr/bin/pagekite 8080 "$KITE_HOST" &
KITE_PID=$!

# ─── Wait for any process to exit ─────────────────────────────────
wait -n "$PIPE_PID" "$MJPG_PID" "$KITE_PID"
echo "[WARN] One service exited – letting systemd restart us."
exit 1           # non-zero → Restart=on-failure
