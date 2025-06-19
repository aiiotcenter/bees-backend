#!/usr/bin/env bash
# ------------------------------------------------------------------
# stream_tunnel.sh – start mjpg-streamer (legacy build) + PageKite
# ------------------------------------------------------------------

set -eEuo pipefail

# ─── sudo re-exec ────────────────────────────────────────────────
if (( EUID != 0 )); then
  exec sudo "$0" "$@"
fi

# ─── paths ───────────────────────────────────────────────────────
BIN="/usr/local/bin/mjpg_streamer"           # fixed, working binary
WWW_DIR="/home/pi/mjpg-streamer/mjpg-streamer-experimental/www"
LOG_DIR="/home/pi/bees-backend/raspberry/logs"
mkdir -p "$LOG_DIR"
exec >>"$LOG_DIR/stream.log" 2>&1            # append stdout+stderr

# ─── streamer & tunnel commands ─────────────────────────────────
STREAM_CMD=(
  "$BIN"
  -i "input_libcamera.so --width 640 --height 480 --framerate 25"
  -o "output_http.so   -p 8080 -w $WWW_DIR"
)

KITE_HOST="beesscamera.pagekite.me"
TUNNEL_CMD=( /usr/bin/pagekite 8080 "$KITE_HOST" )

# ─── clean exit handler ─────────────────────────────────────────
cleanup() {
  echo "[INFO] Stopping mjpg-streamer and PageKite ..."
  pkill -TERM -x mjpg_streamer 2>/dev/null || true
  pkill -TERM -f /usr/bin/pagekite 2>/dev/null || true
}
trap cleanup SIGINT SIGTERM EXIT

# ─── start services ─────────────────────────────────────────────
echo "[INFO] Starting mjpg-streamer  → http://localhost:8080"
"${STREAM_CMD[@]}" &
STREAM_PID=$!

sleep 3
if ! kill -0 "$STREAM_PID" 2>/dev/null; then
  echo "[ERROR] mjpg-streamer died on startup; aborting."
  exit 1
fi

echo "[INFO] Opening PageKite       → http://$KITE_HOST/?action=stream"
"${TUNNEL_CMD[@]}" &
KITE_PID=$!

# ─── wait for either to exit ────────────────────────────────────
wait -n "$STREAM_PID" "$KITE_PID"
echo "[WARN] One of the services exited – letting systemd restart us."
