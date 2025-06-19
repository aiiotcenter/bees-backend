#!/usr/bin/env bash
# ------------------------------------------------------------------
# stream_tunnel.sh – start mjpg-streamer (stable build) + PageKite
# ------------------------------------------------------------------

set -eEuo pipefail

# If not root, re-exec with sudo so we can open the camera.
(( EUID != 0 )) && exec sudo "$0" "$@"

# ─── paths ───────────────────────────────────────────────────────
BIN="/usr/local/bin/mjpg_streamer"                # working binary
PLUG_DIR="/usr/local/lib/mjpg-streamer"           # after ‘sudo make install’
WWW_DIR="/home/pi/mjpg-streamer/mjpg-streamer-experimental/www"

LOG_DIR="/home/pi/bees-backend/raspberry/logs"
mkdir -p "$LOG_DIR"
exec >>"$LOG_DIR/stream.log" 2>&1

export LD_LIBRARY_PATH="$PLUG_DIR"

# ─── commands ────────────────────────────────────────────────────
STREAM_CMD=(
  "$BIN"
  -i "input_libcamera.so --width 640 --height 480 --framerate 25"
  -o "output_http.so   -p 8080 -w $WWW_DIR"
)

KITE_HOST="beesscamera.pagekite.me"
TUNNEL_CMD=( /usr/bin/pagekite 8080 "$KITE_HOST" )

# ─── cleanup handler ─────────────────────────────────────────────
cleanup() {
  echo "[INFO] Stopping mjpg-streamer and PageKite …"
  pkill -TERM -x mjpg_streamer 2>/dev/null || true
  pkill -TERM -f /usr/bin/pagekite 2>/dev/null || true
}
trap cleanup SIGINT SIGTERM EXIT

# ─── launch streamer ─────────────────────────────────────────────
echo "[INFO] Starting mjpg-streamer  → http://localhost:8080"
"${STREAM_CMD[@]}" &
STREAM_PID=$!

sleep 3
if ! kill -0 "$STREAM_PID" 2>/dev/null; then
  echo "[ERROR] mjpg-streamer died on startup; aborting so systemd can retry."
  exit 1
fi

# ─── launch tunnel ───────────────────────────────────────────────
echo "[INFO] Opening PageKite       → http://$KITE_HOST/?action=stream"
"${TUNNEL_CMD[@]}" &
KITE_PID=$!

# ─── wait for either process to exit ─────────────────────────────
wait -n "$STREAM_PID" "$KITE_PID"
echo "[WARN] One of the services exited – letting systemd restart us."
exit 1        # non-zero so systemd’s Restart=on-failure kicks in
