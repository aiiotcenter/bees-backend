#!/usr/bin/env bash
# stream_tunnel.sh – Pi camera → v4l2loopback → MJPEG-streamer → PageKite
set -eEuo pipefail

LOG_DIR="/home/pi/bees-backend/raspberry/logs"
mkdir -p "$LOG_DIR"
exec >>"$LOG_DIR/stream.log" 2>&1

echo "[INFO] ==== STREAM TUNNEL STARTING ===="

# 1) Setup loopback pair
echo "[INFO] Setting up v4l2loopback (98=out,99=in)…"
modprobe -r v4l2loopback 2>/dev/null || true
modprobe v4l2loopback devices=2 video_nr=98,99 card_label="VL_Out,VL_In" \
         max_buffers=4 exclusive_caps=1
sleep 2

# cleanup on exit
cleanup(){
  echo "[INFO] Cleaning up…"
  pkill -f libcamera-vid || true
  pkill -f ffmpeg      || true
  pkill -f mjpg_streamer|| true
  pkill -f pagekite    || true
}
trap cleanup EXIT INT TERM

# 2) Camera → /dev/video98
echo "[INFO] Launching camera pipeline → /dev/video98"
libcamera-vid -t 0 --width 640 --height 480 --framerate 25 --codec yuv420 --output - | \
ffmpeg -loglevel warning \
       -f rawvideo -pix_fmt yuv420p -s 640x480 -r 25 -i - \
       -pix_fmt yuyv422 -f v4l2 /dev/video98 &
PIPE_PID=$!
sleep 3
if ! kill -0 $PIPE_PID 2>/dev/null; then
  echo "[ERROR] Camera pipeline failed, aborting."
  exit 1
fi

# 3) MJPEG-streamer → /dev/video99
echo "[INFO] Starting MJPEG-streamer on /dev/video99 port 8080"
export LD_LIBRARY_PATH=/usr/local/lib/mjpg-streamer
mjpg_streamer \
  -i "input_uvc.so -d /dev/video99 -r 640x480 -f 25 -y -m 1" \
  -o "output_http.so -p 8080 -w /home/pi/mjpg-streamer/mjpg-streamer-experimental/www" &
MJPG_PID=$!
sleep 3
if ! kill -0 $MJPG_PID 2>/dev/null; then
  echo "[ERROR] MJPEG-streamer failed, aborting."
  exit 1
fi

# 4) PageKite tunnel
echo "[INFO] Opening PageKite → http://beesscamera.pagekite.me/?action=stream"
pagekite 8080 beesscamera.pagekite.me &
KITE_PID=$!

# 5) Wait for any to exit
wait -n $PIPE_PID $MJPG_PID $KITE_PID
echo "[WARN] One component exited, requesting restart."
exit 1
