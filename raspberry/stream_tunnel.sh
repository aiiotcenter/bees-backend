#!/bin/bash
LOGFILE="/home/pi/bees-backend/raspberry/logs/camera.log"
mkdir -p "$(dirname "$LOGFILE")"

RESOLUTION="640x480"    # Or 1296x972, 1920x1080, etc.
FPS="15"                # Use a supported FPS for your chosen resolution
PORT="8080"
PAGEKITE_HOST="bees.pagekite.me"
PAGEKITE_SERVICE="8080"
MJPG_BIN="/usr/local/bin/mjpg_streamer"

echo "[$(date)] Killing any old mjpg_streamer processes..." | tee -a "$LOGFILE"
pkill mjpg_streamer

echo "[$(date)] Starting mjpg-streamer on port $PORT at $RESOLUTION $FPS FPS using libcamera..." | tee -a "$LOGFILE"
$MJPG_BIN \
-i "input_libcamera.so --resolution $RESOLUTION --fps $FPS" \
-o "output_http.so -w /usr/local/share/mjpg-streamer/www -p $PORT" >> "$LOGFILE" 2>&1 &

sleep 2

if ! pgrep -f "$MJPG_BIN" > /dev/null; then
    echo "[$(date)] ERROR: mjpg-streamer failed to start." | tee -a "$LOGFILE"
else
    echo "[$(date)] mjpg-streamer started successfully." | tee -a "$LOGFILE"
fi

echo "[$(date)] Starting PageKite tunneling $PAGEKITE_HOST to local port $PAGEKITE_SERVICE..." | tee -a "$LOGFILE"
pagekite.py $PAGEKITE_SERVICE $PAGEKITE_HOST >> "$LOGFILE" 2>&1 &

echo "[$(date)] MJPG-streamer and PageKite are now running in the background." | tee -a "$LOGFILE"
