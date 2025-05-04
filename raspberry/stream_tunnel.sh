#!/bin/bash
# mjpg-streamer + PageKite startup script with logging

LOGFILE="/home/pi/bees-backend/raspberry/logs/camera.log"
mkdir -p "$(dirname "$LOGFILE")"

RESOLUTION="640x480"
FPS="10"
PORT="8080"
PAGEKITE_HOST="beesscamera.pagekite.me"
PAGEKITE_SERVICE="8080"

echo "[$(date)] Starting mjpg-streamer on port $PORT at $RESOLUTION $FPS FPS..." | tee -a "$LOGFILE"

mjpg_streamer -i "input_uvc.so -r $RESOLUTION -f $FPS" \
              -o "output_http.so -w /usr/local/share/mjpg-streamer/www -p $PORT" >> "$LOGFILE" 2>&1 &

sleep 2

echo "[$(date)] Starting PageKite tunneling $PAGEKITE_HOST to local port $PAGEKITE_SERVICE..." | tee -a "$LOGFILE"
pagekite.py $PAGEKITE_SERVICE $PAGEKITE_HOST >> "$LOGFILE" 2>&1 &

echo "[$(date)] MJPG-streamer and PageKite are now running in the background." | tee -a "$LOGFILE"
