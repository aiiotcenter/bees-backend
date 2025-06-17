

set -euo pipefail

BUILD_DIR="/home/pi/mjpg-streamer/mjpg-streamer-experimental/_build"
WWW_DIR="${BUILD_DIR}/../www"

export LD_LIBRARY_PATH="${BUILD_DIR}/plugins/input_libcamera:${BUILD_DIR}/plugins/output_http"

# ----- Clean up any previous instances --------------------------------------
echo "[INFO] Stopping any running camera/tunnel processes…"
sudo pkill -9 -f libcamera  || true
sudo pkill -9 mjpg_streamer || true
sudo pkill -9 -f "lt --port 8080" || true
sleep 1

# ----- Start mjpg‑streamer ----------------------------------------------------
echo "[INFO] Starting mjpg-streamer…"
${BUILD_DIR}/mjpg_streamer \
  -i "input_libcamera.so --resolution 640x480 --fps 10 --buffercount 3" \
  -o "output_http.so   -p 8080 -w ${WWW_DIR}" &
STREAMER_PID=$!

# Give streamer a moment to initialise
sleep 3

# ----- Start LocalTunnel ------------------------------------------------------
echo "[INFO] Starting LocalTunnel on sub‑domain camera…"
lt --port 8080 --subdomain camera --local-host 127.0.0.1 &
LT_PID=$!

# -----------------------------------------------------------------------------
echo "[INFO] mjpg-streamer PID : ${STREAMER_PID}"
echo "[INFO] LocalTunnel PID  : ${LT_PID}"
echo "[READY] Stream available locally  at  http://localhost:8080/?action=stream"
echo "[READY] Public link (via LT) at  http://camera.loca.lt/?action=stream"

echo "Press Ctrl‑C to stop both processes."

# Wait on background jobs so Ctrl‑C stops everything
wait
