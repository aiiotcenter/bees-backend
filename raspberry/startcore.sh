#!/bin/bash

# Activate virtual environment
cd /home/pi/
source venv/bin/activate

# Start app and camera streamer, logging output
LOGFILE="/home/pi/bees-backend/raspberry/logs/bees.log"
mkdir -p logs
echo "[START] $(date)" >> "$LOGFILE"
python app.py >> "$LOGFILE" 2>&1 &
./stream_tunnel.sh >> "$LOGFILE" 2>&1 &

# Keep script running so systemd stays active
wait
