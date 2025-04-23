#!/bin/bash
cd /home/pi/bees-backend/raspberry

# Activate virtual environment
source venv/bin/activate

# Run your main app (in background)
python app.py &

# Start the stream and tunnel
./stream_tunnel.sh &
