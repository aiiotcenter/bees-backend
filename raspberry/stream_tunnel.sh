set -euo pipefail

BUILD_DIR="/home/pi/mjpg-streamer/mjpg-streamer-experimental/_build"
WWW_DIR="${BUILD_DIR}/../www"
LD_PATH="${BUILD_DIR}/plugins/input_libcamera:${BUILD_DIR}/plugins/output_http"

STREAM_CMD="${BUILD_DIR}/mjpg_streamer -i \"input_libcamera.so --resolution 640x480 --fps 10 --buffercount 3\" -o \"output_http.so -p 8080 -w ${WWW_DIR}\""
TUNNEL_CMD="lt --port 8080 --subdomain camera --local-host 127.0.0.1"

log() { printf '[%(%Y-%m-%d %H:%M:%S)T] %s\n' -1 "$*"; }

cleanup() {
  log "Stopping …"
  pkill -9 -f "${STREAM_CMD%% *}" 2>/dev/null || true
  pkill -9 -f "${TUNNEL_CMD%% *}" 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

log "Killing any stale processes …"
# (Use sudo if the old processes were started as root.)
sudo pkill -9 -f libcamera          2>/dev/null || true
sudo pkill -9 -f "${STREAM_CMD%% *}" 2>/dev/null || true
sudo pkill -9 -f "${TUNNEL_CMD%% *}" 2>/dev/null || true

export LD_LIBRARY_PATH="${LD_PATH}"

while true; do
  log "Starting mjpg-streamer …"
  bash -c "${STREAM_CMD}" &
  STREAM_PID=$!

  # Wait a bit; if streamer dies immediately (e.g. ENOMEM), loop again.
  sleep 3
  if ! kill -0 ${STREAM_PID} 2>/dev/null; then
    log "mjpg-streamer exited early; retrying in 5 s …"
    sleep 5
    continue
  fi

  log "Opening LocalTunnel …"
  bash -c "${TUNNEL_CMD}" &
  LT_PID=$!

  log "LOCAL  : http://localhost:8080/?action=stream"
  log "PUBLIC : http://camera.loca.lt/?action=stream"

  # Wait until mjpg-streamer dies; then kill tunnel and restart loop.
  wait ${STREAM_PID}
  log "mjpg-streamer exited (code=$?).  Restarting in 5 s …"
  kill ${LT_PID} 2>/dev/null || true
  sleep 5

done