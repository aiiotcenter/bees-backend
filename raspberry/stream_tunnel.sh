#!/bin/bash

# Start mjpg-streamer
cd ~/mjpg-streamer/mjpg-streamer-experimental
./mjpg_streamer -i "./input_uvc.so -y -n -f 10 -r 640x480" -o "./output_http.so -w ./www" &

# Wait a bit for the stream to start
sleep 5

# Start PageKite tunnel
pagekite.py 8080 beesscamera.pagekite.me
