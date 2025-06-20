#!/usr/bin/env bash
set -eEuo pipefail

### 1) ensure nothing is holding the camera or your old processes
pkill -f libcamera    || true
pkill -f mjpg_streamer|| true
pkill -f pagekite     || true
pkill -f app.py       || true
sleep 2

### 2) libcamera needs this
export XDG_RUNTIME_DIR=/run/user/1000

### 3) start your Flask app
BASE_DIR=/home/pi/bees-backend/raspberry
VENV_DIR=/home/pi/venv
LOG_DIR=$BASE_DIR/logs
mkdir -p "$LOG_DIR"

echo "[`date`] ▶ STARTING Flask" >> "$LOG_DIR/runall.log"
source "$VENV_DIR/bin/activate"
PYTHONPATH="$BASE_DIR/sensors/hx711py" \
  python "$BASE_DIR/app.py" >> "$LOG_DIR/runall.log" 2>&1 &
FLASK_PID=$!

### 4) start the stream + tunnel
echo "[`date`] ▶ STARTING Stream+Tunnel" >> "$LOG_DIR/runall.log"
bash "$BASE_DIR/stream_tunnel.sh" >> "$LOG_DIR/runall.log" 2>&1 &
STREAM_PID=$!
#!/usr/bin/env bash
set -eEuo pipefail

# ensure libcamera can find its socket
export XDG_RUNTIME_DIR=/run/user/1000

# 1) start the camera tunnel
/home/pi/bees-backend/raspberry/stream_tunnel.sh &
STREAM_PID=$!

# 2) start your flask app
/home/pi/bees-backend/raspberry/startcore.sh &
FLASK_PID=$!

echo "[INFO] started STREAM=${STREAM_PID}  FLASK=${FLASK_PID}"

cleanup(){
  echo "[STOP ] stopping both…"
  kill "${STREAM_PID}" "${FLASK_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait -n "${STREAM_PID}" "${FLASK_PID}"
echo "[WARN] one died, exiting so systemd can restart"
exit 1

### 5) when either one dies, shut down the other and exit
cleanup(){
  echo "[`date`] ▶ SHUTTING DOWN" >> "$LOG_DIR/runall.log"
  kill $FLASK_PID $STREAM_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait -n $FLASK_PID $STREAM_PID
exit 1
