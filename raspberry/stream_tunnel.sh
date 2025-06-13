#!/bin/bash

# Go to the camera-streamer directory
cd ~/camera-streamer || { echo "camera-streamer directory not found"; exit 1; }

# Start the camera-streamer in background with specified options
sudo ./camera-streamer \
  --camera-type=libcamera \
  --camera-width=1280 \
  --camera-height=720 \
  --camera-fps=30 \
  --camera-format=H264 \
  --http-listen=0.0.0.0 \
  --http-port=8080 \
  --camera-video.options=video_bitrate=2000000 \
  --camera-video.options=h264_profile=high > /dev/null 2>&1 &

# Wait a few seconds to make sure the stream starts
sleep 3

# Start localtunnel with your custom subdomain
lt --port 8080 --subdomain camera
